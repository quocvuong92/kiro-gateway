# Multi-Account Round-Robin Load Balancing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable automatic load balancing across multiple Kiro accounts by auto-discovering `kiro-*.json` credential files and distributing requests using round-robin strategy.

**Architecture:** Create an `AccountPool` manager that scans a directory for credential files at startup, initializes a `KiroAuthManager` for each valid account, and provides a round-robin selector with health checking and automatic failover. The existing single-account flow in `main.py` will be replaced with the pool-based approach.

**Tech Stack:** Python 3.10+, asyncio, pathlib, existing KiroAuthManager

---

## Task 1: Add Configuration for Multi-Account Support

**Files:**
- Modify: `kiro/config.py:115-130`

**Step 1: Add configuration constants**

Add after line 130 (after `KIRO_CLI_DB_FILE` definition):

```python
# ==================================================================================================
# Multi-Account Settings
# ==================================================================================================

# Directory containing kiro-*.json credential files for multi-account support
# If set, the gateway will auto-discover all files matching pattern "kiro-*.json"
# and load balance requests across all valid accounts using round-robin strategy
# Leave empty to use single-account mode (KIRO_CREDS_FILE)
_raw_accounts_dir = _get_raw_env_value("KIRO_ACCOUNTS_DIR") or os.getenv("KIRO_ACCOUNTS_DIR", "")
KIRO_ACCOUNTS_DIR: str = str(Path(_raw_accounts_dir).expanduser()) if _raw_accounts_dir else ""

# Load balancing strategy for multi-account mode
# - "round_robin": Cycle through accounts evenly (default)
# - "random": Pick random account for each request
# - "least_used": Use account with fewest recent requests
KIRO_LOAD_BALANCE_STRATEGY: str = os.getenv("KIRO_LOAD_BALANCE_STRATEGY", "round_robin")

# Skip accounts with credentials expiring within N seconds
# Accounts close to expiration will be excluded from the pool
KIRO_SKIP_EXPIRING_THRESHOLD: int = int(os.getenv("KIRO_SKIP_EXPIRING_THRESHOLD", "300"))

# Enable sticky sessions (same conversation uses same account)
# When enabled, requests with the same conversation_id will route to the same account
KIRO_STICKY_SESSIONS: bool = os.getenv("KIRO_STICKY_SESSIONS", "false").lower() == "true"
```

**Step 2: Verify no syntax errors**

Run: `python -c "import kiro.config; print('Config loaded successfully')"`
Expected: "Config loaded successfully"

**Step 3: Commit**

```bash
git add kiro/config.py
git commit -m "feat(config): add multi-account configuration options"
```

---

## Task 2: Create Account Pool Manager Module

**Files:**
- Create: `kiro/account_pool.py`

**Step 1: Create the module with basic structure**

```python
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
        
        logger.info(f"Found {len(creds_files)} credential files matching pattern '{pattern}'")
        
        # Load each account
        loaded_count = 0
        for creds_file in sorted(creds_files):
            try:
                account_name = creds_file.stem  # e.g., "kiro-personal" from "kiro-personal.json"
                
                # Create auth manager for this account
                auth_manager = KiroAuthManager(creds_file=str(creds_file))
                
                # Test if credentials are valid by loading them
                # This will raise an exception if the file is invalid
                await auth_manager.get_access_token()
                
                # Add to pool
                account_info = AccountInfo(
                    name=account_name,
                    auth_manager=auth_manager,
                    file_path=str(creds_file)
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
            healthy_accounts = [acc for acc in self.accounts if self._is_account_healthy(acc)]
            
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
```

**Step 2: Verify module imports**

Run: `python -c "from kiro.account_pool import AccountPool; print('Module imported successfully')"`
Expected: "Module imported successfully"

**Step 3: Commit**

```bash
git add kiro/account_pool.py
git commit -m "feat(account-pool): create account pool manager with round-robin support"
```

---

## Task 3: Write Tests for Account Pool

**Files:**
- Create: `tests/unit/test_account_pool.py`

**Step 1: Create test file with fixtures**

```python
# -*- coding: utf-8 -*-

"""Tests for AccountPool multi-account load balancing."""

import json
import pytest
from pathlib import Path
from datetime import datetime, timedelta, timezone

from kiro.account_pool import AccountPool, AccountInfo


@pytest.fixture
def temp_accounts_dir(tmp_path):
    """Create temporary directory with test credential files."""
    accounts_dir = tmp_path / "accounts"
    accounts_dir.mkdir()
    
    # Create 3 test credential files
    for i in range(1, 4):
        creds_file = accounts_dir / f"kiro-account{i}.json"
        creds_data = {
            "access_token": f"test_access_token_{i}",
            "refresh_token": f"test_refresh_token_{i}",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "profile_arn": f"arn:aws:codewhisperer:us-east-1:123:profile/TEST{i}",
            "region": "us-east-1",
        }
        creds_file.write_text(json.dumps(creds_data))
    
    return accounts_dir


@pytest.mark.asyncio
async def test_initialize_finds_accounts(temp_accounts_dir):
    """Test that AccountPool finds and loads credential files."""
    pool = AccountPool(accounts_dir=str(temp_accounts_dir))
    
    loaded_count = await pool.initialize()
    
    assert loaded_count == 3
    assert len(pool.accounts) == 3
    assert pool.accounts[0].name == "kiro-account1"
    assert pool.accounts[1].name == "kiro-account2"
    assert pool.accounts[2].name == "kiro-account3"


@pytest.mark.asyncio
async def test_round_robin_strategy(temp_accounts_dir):
    """Test round-robin load balancing distributes requests evenly."""
    pool = AccountPool(accounts_dir=str(temp_accounts_dir), strategy="round_robin")
    await pool.initialize()
    
    # Get 6 accounts (2 full cycles)
    selected_accounts = []
    for _ in range(6):
        auth_manager = await pool.get_next_account()
        # Find which account was selected
        for acc in pool.accounts:
            if acc.auth_manager is auth_manager:
                selected_accounts.append(acc.name)
                break
    
    # Should cycle through all 3 accounts twice
    assert selected_accounts == [
        "kiro-account1", "kiro-account2", "kiro-account3",
        "kiro-account1", "kiro-account2", "kiro-account3",
    ]


@pytest.mark.asyncio
async def test_skip_expiring_accounts(tmp_path):
    """Test that accounts expiring soon are skipped."""
    accounts_dir = tmp_path / "accounts"
    accounts_dir.mkdir()
    
    # Account 1: Valid (expires in 1 hour)
    creds1 = accounts_dir / "kiro-valid.json"
    creds1.write_text(json.dumps({
        "access_token": "token1",
        "refresh_token": "refresh1",
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "profile_arn": "arn:aws:codewhisperer:us-east-1:123:profile/VALID",
        "region": "us-east-1",
    }))
    
    # Account 2: Expiring soon (expires in 2 minutes)
    creds2 = accounts_dir / "kiro-expiring.json"
    creds2.write_text(json.dumps({
        "access_token": "token2",
        "refresh_token": "refresh2",
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat(),
        "profile_arn": "arn:aws:codewhisperer:us-east-1:123:profile/EXPIRING",
        "region": "us-east-1",
    }))
    
    pool = AccountPool(
        accounts_dir=str(accounts_dir),
        skip_expiring_threshold=300  # 5 minutes
    )
    await pool.initialize()
    
    # Should have loaded both accounts
    assert len(pool.accounts) == 2
    
    # But only 1 should be healthy (the one not expiring soon)
    stats = pool.get_stats()
    assert stats["healthy_accounts"] == 1
    assert stats["unhealthy_accounts"] == 1
    
    # Getting next account should only return the healthy one
    auth_manager = await pool.get_next_account()
    # Find which account was selected
    for acc in pool.accounts:
        if acc.auth_manager is auth_manager:
            assert acc.name == "kiro-valid"
            break


@pytest.mark.asyncio
async def test_no_accounts_raises_error(tmp_path):
    """Test that empty directory raises ValueError."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    
    pool = AccountPool(accounts_dir=str(empty_dir))
    
    with pytest.raises(ValueError, match="No credential files found"):
        await pool.initialize()


@pytest.mark.asyncio
async def test_get_stats(temp_accounts_dir):
    """Test that get_stats returns correct information."""
    pool = AccountPool(accounts_dir=str(temp_accounts_dir))
    await pool.initialize()
    
    # Make some requests
    await pool.get_next_account()
    await pool.get_next_account()
    
    stats = pool.get_stats()
    
    assert stats["total_accounts"] == 3
    assert stats["healthy_accounts"] == 3
    assert stats["strategy"] == "round_robin"
    assert len(stats["accounts"]) == 3
    assert stats["accounts"][0]["request_count"] == 1
    assert stats["accounts"][1]["request_count"] == 1
```

**Step 2: Run tests**

Run: `pytest tests/unit/test_account_pool.py -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add tests/unit/test_account_pool.py
git commit -m "test(account-pool): add comprehensive tests for multi-account pool"
```

---

## Task 4: Integrate Account Pool into Application Lifespan

**Files:**
- Modify: `main.py:342-355`
- Modify: `kiro/config.py` (import AccountPool)

**Step 1: Import AccountPool in main.py**

Add to imports section (around line 50):

```python
from kiro.account_pool import AccountPool
from kiro.config import (
    # ... existing imports ...
    KIRO_ACCOUNTS_DIR,
    KIRO_LOAD_BALANCE_STRATEGY,
    KIRO_SKIP_EXPIRING_THRESHOLD,
)
```

**Step 2: Replace single auth_manager with account pool in lifespan**

Replace the auth manager initialization (lines 342-355) with:

```python
    # Create AuthManager or AccountPool
    # Priority: Multi-account mode (KIRO_ACCOUNTS_DIR) > Single account mode
    if KIRO_ACCOUNTS_DIR:
        # Multi-account mode: Initialize account pool
        logger.info(f"Multi-account mode enabled. Scanning directory: {KIRO_ACCOUNTS_DIR}")
        try:
            app.state.account_pool = AccountPool(
                accounts_dir=KIRO_ACCOUNTS_DIR,
                strategy=KIRO_LOAD_BALANCE_STRATEGY,
                skip_expiring_threshold=KIRO_SKIP_EXPIRING_THRESHOLD,
            )
            account_count = await app.state.account_pool.initialize()
            logger.info(
                f"Account pool initialized with {account_count} account(s) "
                f"using '{KIRO_LOAD_BALANCE_STRATEGY}' strategy"
            )
            
            # For model loading, use the first healthy account
            app.state.auth_manager = await app.state.account_pool.get_next_account()
            app.state.multi_account_mode = True
            
        except Exception as e:
            logger.error(f"Failed to initialize account pool: {e}")
            logger.error("Falling back to single-account mode")
            app.state.multi_account_mode = False
            # Fall back to single account
            app.state.auth_manager = KiroAuthManager(
                refresh_token=REFRESH_TOKEN,
                profile_arn=PROFILE_ARN,
                region=REGION,
                creds_file=KIRO_CREDS_FILE if KIRO_CREDS_FILE else None,
                sqlite_db=KIRO_CLI_DB_FILE if KIRO_CLI_DB_FILE else None,
            )
    else:
        # Single-account mode (original behavior)
        logger.info("Single-account mode (KIRO_ACCOUNTS_DIR not set)")
        app.state.multi_account_mode = False
        app.state.auth_manager = KiroAuthManager(
            refresh_token=REFRESH_TOKEN,
            profile_arn=PROFILE_ARN,
            region=REGION,
            creds_file=KIRO_CREDS_FILE if KIRO_CREDS_FILE else None,
            sqlite_db=KIRO_CLI_DB_FILE if KIRO_CLI_DB_FILE else None,
        )
```

**Step 3: Verify server starts**

Run: `python main.py &`
Check logs for: "Single-account mode (KIRO_ACCOUNTS_DIR not set)"
Kill server: `pkill -f "python main.py"`

**Step 4: Commit**

```bash
git add main.py
git commit -m "feat(main): integrate account pool into application lifespan"
```

---

## Task 5: Update Routes to Use Account Pool

**Files:**
- Modify: `kiro/routes_openai.py:172-180`
- Modify: `kiro/routes_anthropic.py` (similar changes)

**Step 1: Modify chat_completions to use account pool**

In `kiro/routes_openai.py`, find the chat_completions function (around line 172).

Replace the auth_manager usage:

```python
@router.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    chat_request: ChatCompletionRequest,
) -\u003e Union[StreamingResponse, ChatCompletionResponse]:
    # ... existing code ...
    
    # Get auth manager (from pool if multi-account mode)
    if request.app.state.multi_account_mode:
        auth_manager = await request.app.state.account_pool.get_next_account()
    else:
        auth_manager = request.app.state.auth_manager
    
    # ... rest of function uses auth_manager as before ...
```

**Step 2: Apply same pattern to Anthropic routes**

In `kiro/routes_anthropic.py`, find the messages function and apply the same pattern:

```python
@router.post("/v1/messages")
async def messages(
    request: Request,
    anthropic_request: AnthropicMessageRequest,
) -\u003e Union[StreamingResponse, AnthropicMessageResponse]:
    # ... existing code ...
    
    # Get auth manager (from pool if multi-account mode)
    if request.app.state.multi_account_mode:
        auth_manager = await request.app.state.account_pool.get_next_account()
    else:
        auth_manager = request.app.state.auth_manager
    
    # ... rest of function uses auth_manager as before ...
```

**Step 3: Verify routes work**

Run: `pytest tests/integration/ -v -k "test_chat_completions or test_messages"`
Expected: Tests pass

**Step 4: Commit**

```bash
git add kiro/routes_openai.py kiro/routes_anthropic.py
git commit -m "feat(routes): use account pool for load balancing in routes"
```

---

## Task 6: Add Pool Stats Endpoint (Optional)

**Files:**
- Modify: `kiro/routes_openai.py` (add new endpoint)

**Step 1: Add stats endpoint**

Add to `kiro/routes_openai.py` after the health check endpoint:

```python
@router.get("/v1/accounts/stats")
async def get_account_stats(request: Request) -\u003e dict:
    """
    Get statistics about the account pool (multi-account mode only).
    
    Returns account pool information including:
    - Total accounts
    - Healthy vs unhealthy accounts
    - Request counts per account
    - Load balancing strategy
    
    Returns 404 if single-account mode is active.
    """
    if not request.app.state.multi_account_mode:
        raise HTTPException(
            status_code=404,
            detail="Account pool stats not available in single-account mode"
        )
    
    return request.app.state.account_pool.get_stats()
```

**Step 2: Test the endpoint manually**

With multi-account mode enabled:
Run: `curl http://localhost:8000/v1/accounts/stats | python3 -m json.tool`
Expected: JSON with pool statistics

**Step 3: Commit**

```bash
git add kiro/routes_openai.py
git commit -m "feat(routes): add account pool stats endpoint"
```

---

## Task 7: Update Documentation

**Files:**
- Modify: `README.md` (add multi-account section)
- Modify: `.env.example` (add new configuration options)

**Step 1: Add configuration to .env.example**

Add to `.env.example` after the KIRO_CLI_DB_FILE section:

```env
# ===========================================
# MULTI-ACCOUNT LOAD BALANCING
# ===========================================

# Directory containing kiro-*.json credential files for multi-account support
# When set, the gateway will automatically discover all files matching "kiro-*.json"
# and distribute requests across accounts using round-robin load balancing
#
# Example structure:
#   ~/.cli-proxy-api/
#   ├── kiro-personal.json
#   ├── kiro-work.json
#   └── kiro-backup.json
#
# Leave empty to use single-account mode (KIRO_CREDS_FILE)
# KIRO_ACCOUNTS_DIR="~/.cli-proxy-api"

# Load balancing strategy (default: round_robin)
# - round_robin: Cycle through accounts evenly
# - random: Pick random account for each request
# - least_used: Use account with fewest requests
# KIRO_LOAD_BALANCE_STRATEGY="round_robin"

# Skip accounts expiring within N seconds (default: 300 = 5 minutes)
# KIRO_SKIP_EXPIRING_THRESHOLD="300"
```

**Step 2: Add section to README.md**

Add new section after "Configuration":

```markdown
## 🔄 Multi-Account Load Balancing

Distribute requests across multiple Kiro accounts for higher throughput and automatic failover.

### Setup

1. **Create accounts directory:**
   ```bash
   mkdir -p ~/.cli-proxy-api
   ```

2. **Add credential files** matching pattern `kiro-*.json`:
   ```
   ~/.cli-proxy-api/
   ├── kiro-personal.json
   ├── kiro-work.json
   └── kiro-backup.json
   ```

3. **Configure .env:**
   ```env
   KIRO_ACCOUNTS_DIR="~/.cli-proxy-api"
   KIRO_LOAD_BALANCE_STRATEGY="round_robin"
   ```

4. **Restart gateway:**
   ```bash
   ./kiro-gateway-daemon.sh restart
   ```

### Features

- ✅ **Auto-discovery** - Automatically finds all `kiro-*.json` files
- ✅ **Round-robin** - Distributes load evenly across accounts
- ✅ **Health checking** - Skips expired/invalid accounts
- ✅ **Automatic failover** - Routes around failing accounts
- ✅ **Single API key** - Clients use one key for all accounts

### View Statistics

```bash
curl http://localhost:8000/v1/accounts/stats
```

Shows:
- Total accounts loaded
- Healthy vs unhealthy accounts
- Request count per account
- Load balancing strategy

### Strategies

| Strategy | Behavior |
|----------|----------|
| `round_robin` | Cycle through accounts evenly (default) |
| `random` | Pick random account each request |
| `least_used` | Use account with fewest requests |
```

**Step 3: Commit**

```bash
git add README.md .env.example
git commit -m "docs: add multi-account load balancing documentation"
```

---

## Task 8: End-to-End Testing

**Files:**
- Manual testing with actual credential files

**Step 1: Create test accounts directory**

```bash
mkdir -p ~/.cli-proxy-api-test
cp ~/.cli-proxy-api/kiro-google-EHGA3GRVQMUK.json ~/.cli-proxy-api-test/kiro-account1.json
cp ~/.cli-proxy-api/kiro-google-EHGA3GRVQMUK.json ~/.cli-proxy-api-test/kiro-account2.json
```

**Step 2: Update .env**

```env
KIRO_ACCOUNTS_DIR="~/.cli-proxy-api-test"
KIRO_LOAD_BALANCE_STRATEGY="round_robin"
```

**Step 3: Start server and test**

```bash
./kiro-gateway-daemon.sh restart
sleep 5

# Check logs for multi-account mode
tail -20 daemon/kiro-gateway.log | grep "Multi-account"

# Test stats endpoint
curl http://localhost:8000/v1/accounts/stats | python3 -m json.tool

# Make multiple requests and verify round-robin
for i in {1..6}; do
  curl -s http://localhost:8000/v1/chat/completions \
    -H "Authorization: Bearer dummy" \
    -H "Content-Type: application/json" \
    -d '{"model": "claude-haiku-4.5", "messages": [{"role": "user", "content": "Test '$i'"}], "max_tokens": 10}'
  echo ""
done

# Check stats again to see request distribution
curl http://localhost:8000/v1/accounts/stats | python3 -m json.tool
```

Expected:
- Server starts with "Multi-account mode enabled"
- Stats show 2 accounts
- Requests are distributed evenly

**Step 4: Clean up test directory**

```bash
rm -rf ~/.cli-proxy-api-test
```

**Step 5: Final commit**

```bash
git add -A
git commit -m "test: verify multi-account load balancing end-to-end"
```

---

## Summary

This plan implements:

1. ✅ Auto-discovery of `kiro-*.json` files
2. ✅ Round-robin load balancing
3. ✅ Health checking (skip expired accounts)
4. ✅ Automatic failover
5. ✅ Single API key for clients
6. ✅ Statistics endpoint
7. ✅ Comprehensive tests
8. ✅ Documentation

**Total Tasks:** 8
**Estimated Time:** 2-3 hours
**Files Created:** 2 new files
**Files Modified:** 6 files
