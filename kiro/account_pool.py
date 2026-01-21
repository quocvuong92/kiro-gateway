# -*- coding: utf-8 -*-

# Kiro Gateway
# https://github.com/jwadow/kiro-gateway
# Copyright (C) 2025 Jwadow
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""
Account Pool Manager for Multi-Account Load Balancing.

Auto-discovers kiro-*.json credential files and provides round-robin
load balancing with health checking and automatic failover.
"""

import asyncio
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from kiro.auth import KiroAuthManager
from kiro.config import KIRO_SKIP_EXPIRING_THRESHOLD


class AccountInfo:
    """Information about a single Kiro account in the pool."""

    def __init__(self, name: str, auth_manager: KiroAuthManager, file_path: str):
        """
        Initialize account info.

        Args:
            name: Account name (extracted from filename)
            auth_manager: KiroAuthManager instance for this account
            file_path: Path to the credentials file
        """
        self.name = name
        self.auth_manager = auth_manager
        self.file_path = file_path
        self.request_count = 0
        self.last_used = None
        self.is_healthy = True
        self.last_error = None


class AccountPool:
    """
    Manages a pool of Kiro accounts for load balancing.

    Features:
    - Auto-discovery of kiro-*.json files
    - Round-robin load balancing
    - Health checking (skip expired/invalid accounts)
    - Automatic failover
    - Request counting and metrics

    Example:
        >>> pool = AccountPool(accounts_dir="~/.cli-proxy-api")
        >>> await pool.initialize()
        >>> auth_manager = await pool.get_next_account()
    """

    def __init__(
        self,
        accounts_dir: str,
        strategy: str = "round_robin",
        skip_expiring_threshold: int = KIRO_SKIP_EXPIRING_THRESHOLD,
    ):
        """
        Initialize the account pool.

        Args:
            accounts_dir: Directory containing kiro-*.json files
            strategy: Load balancing strategy (round_robin, random, least_used)
            skip_expiring_threshold: Skip accounts expiring within N seconds
        """
        self.accounts_dir = Path(accounts_dir).expanduser()
        self.strategy = strategy
        self.skip_expiring_threshold = skip_expiring_threshold

        self.accounts: List[AccountInfo] = []
        self.current_index = 0
        self._lock = asyncio.Lock()

    async def initialize(self) -> int:
        """
        Scan directory and initialize all accounts.

        Returns:
            Number of accounts successfully loaded

        Raises:
            ValueError: If accounts_dir doesn't exist or no valid accounts found
        """
        if not self.accounts_dir.exists():
            raise ValueError(f"Accounts directory does not exist: {self.accounts_dir}")

        # Scan for kiro-*.json files
        pattern = "kiro-*.json"
        creds_files = list(self.accounts_dir.glob(pattern))

        if not creds_files:
            raise ValueError(
                f"No credential files found matching pattern '{pattern}' "
                f"in directory: {self.accounts_dir}"
            )

        logger.info(
            f"Found {len(creds_files)} credential files matching pattern '{pattern}'"
        )

        # Load each account
        loaded_count = 0
        for creds_file in sorted(creds_files):
            try:
                account_name = (
                    creds_file.stem
                )  # e.g., "kiro-personal" from "kiro-personal.json"

                # Create auth manager for this account
                auth_manager = KiroAuthManager(creds_file=str(creds_file))

                # Test if credentials are valid by loading them
                # This will raise an exception if the file is invalid
                await auth_manager.get_access_token()

                # Add to pool
                account_info = AccountInfo(
                    name=account_name,
                    auth_manager=auth_manager,
                    file_path=str(creds_file),
                )
                self.accounts.append(account_info)
                loaded_count += 1

                logger.info(
                    f"Loaded account '{account_name}' from {creds_file.name} "
                    f"(auth_type: {auth_manager.auth_type.value})"
                )

            except Exception as e:
                logger.warning(
                    f"Failed to load account from {creds_file.name}: {e}. Skipping."
                )
                continue

        if loaded_count == 0:
            raise ValueError("No valid accounts could be loaded")

        logger.info(
            f"Account pool initialized with {loaded_count} account(s) "
            f"using '{self.strategy}' strategy"
        )

        return loaded_count

    def _is_account_healthy(self, account: AccountInfo) -> bool:
        """
        Check if account is healthy and usable.

        Args:
            account: Account to check

        Returns:
            True if account is healthy, False otherwise
        """
        # Check if manually marked as unhealthy
        if not account.is_healthy:
            return False

        # Check if credentials are expiring soon
        auth_manager = account.auth_manager
        if auth_manager._expires_at:
            time_until_expiry = (
                auth_manager._expires_at - datetime.now(timezone.utc)
            ).total_seconds()

            if time_until_expiry < self.skip_expiring_threshold:
                logger.warning(
                    f"Account '{account.name}' credentials expire in "
                    f"{int(time_until_expiry)}s (threshold: {self.skip_expiring_threshold}s). "
                    f"Skipping."
                )
                return False

        return True

    async def get_next_account(self) -> KiroAuthManager:
        """
        Get next account using the configured strategy.

        Returns:
            KiroAuthManager for the selected account

        Raises:
            RuntimeError: If no healthy accounts are available
        """
        async with self._lock:
            # Filter healthy accounts
            healthy_accounts = [
                acc for acc in self.accounts if self._is_account_healthy(acc)
            ]

            if not healthy_accounts:
                raise RuntimeError(
                    "No healthy accounts available. All accounts are either expired, "
                    "invalid, or marked as unhealthy."
                )

            # Select account based on strategy
            if self.strategy == "round_robin":
                selected = healthy_accounts[self.current_index % len(healthy_accounts)]
                self.current_index += 1
            elif self.strategy == "random":
                selected = random.choice(healthy_accounts)
            elif self.strategy == "least_used":
                selected = min(healthy_accounts, key=lambda a: a.request_count)
            else:
                # Default to round-robin
                selected = healthy_accounts[self.current_index % len(healthy_accounts)]
                self.current_index += 1

            # Update metrics
            selected.request_count += 1
            selected.last_used = datetime.now(timezone.utc)

            logger.debug(
                f"Selected account '{selected.name}' "
                f"(request #{selected.request_count}, strategy: {self.strategy})"
            )

            return selected.auth_manager

    def get_stats(self) -> Dict:
        """
        Get statistics about the account pool.

        Returns:
            Dictionary with pool statistics
        """
        healthy_count = sum(1 for acc in self.accounts if self._is_account_healthy(acc))

        return {
            "total_accounts": len(self.accounts),
            "healthy_accounts": healthy_count,
            "unhealthy_accounts": len(self.accounts) - healthy_count,
            "strategy": self.strategy,
            "accounts": [
                {
                    "name": acc.name,
                    "file_path": acc.file_path,
                    "request_count": acc.request_count,
                    "is_healthy": self._is_account_healthy(acc),
                    "last_used": acc.last_used.isoformat() if acc.last_used else None,
                    "auth_type": acc.auth_manager.auth_type.value,
                }
                for acc in self.accounts
            ],
        }
