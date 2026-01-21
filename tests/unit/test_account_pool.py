# -*- coding: utf-8 -*-

"""Tests for AccountPool multi-account load balancing."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from kiro.account_pool import AccountInfo, AccountPool


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
        "kiro-account1",
        "kiro-account2",
        "kiro-account3",
        "kiro-account1",
        "kiro-account2",
        "kiro-account3",
    ]


@pytest.mark.asyncio
async def test_skip_expiring_accounts(temp_accounts_dir):
    """Test that accounts expiring soon are skipped."""
    # Use the temp_accounts_dir fixture which has accounts expiring in 1 hour
    pool = AccountPool(
        accounts_dir=str(temp_accounts_dir),
        skip_expiring_threshold=300,  # 5 minutes
    )
    await pool.initialize()

    # All 3 accounts should load successfully (they expire in 1 hour)
    assert len(pool.accounts) == 3

    # All should be healthy since they expire in 1 hour (well beyond 5 minute threshold)
    stats = pool.get_stats()
    assert stats["healthy_accounts"] == 3

    # Now manually set one account's expiry to be soon
    pool.accounts[1].auth_manager._expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=2
    )

    # Now only 2 should be healthy
    stats = pool.get_stats()
    assert stats["healthy_accounts"] == 2
    assert stats["unhealthy_accounts"] == 1

    # Getting next account should skip the unhealthy one
    # With round-robin, we should get account1, account3, account1, account3 (skipping account2)
    selected_names = []
    for _ in range(4):
        auth_manager = await pool.get_next_account()
        for acc in pool.accounts:
            if acc.auth_manager is auth_manager:
                selected_names.append(acc.name)
                break

    # Should only use the 2 healthy accounts
    assert "kiro-account2" not in selected_names
    assert selected_names.count("kiro-account1") == 2
    assert selected_names.count("kiro-account3") == 2


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
