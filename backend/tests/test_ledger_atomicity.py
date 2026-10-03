"""Atomic ledger behavior tests for reservation race and idempotency semantics."""

import asyncio
import sys
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import db
from ledger import mutate


@pytest.mark.anyio
async def test_simultaneous_reservations_only_one_wins_and_cleanup():
    user_id = f'TEST_LEDGER_{uuid.uuid4()}'
    asset_id = 'native-sol'
    await db.vaults.insert_one({
        'user_id': user_id,
        'balances': {asset_id: {'available': 10, 'reserved': 0}},
        'journal': [],
    })
    try:
        async def reserve(ref):
            try:
                return await mutate(user_id, asset_id, 8, 'reserve', ref)
            except HTTPException:
                return 'error'

        first, second = await asyncio.gather(reserve('race-a'), reserve('race-b'))
        assert sorted([first, second], key=str).count(True) == 1
        assert sorted([first, second], key=str).count('error') == 1

        winner = 'race-a' if first is True else 'race-b'

        vault = await db.vaults.find_one({'user_id': user_id}, {'_id': 0})
        balance = vault['balances'][asset_id]
        assert balance['available'] == 2
        assert balance['reserved'] == 8

        # Duplicate reserve for existing reference is idempotent false.
        assert await mutate(user_id, asset_id, 8, 'reserve', winner) is False

        # settle/release must be mutually exclusive for same reservation reference.
        assert await mutate(user_id, asset_id, 8, 'settle', winner) is True
        with pytest.raises(HTTPException):
            await mutate(user_id, asset_id, 8, 'release', winner)
    finally:
        await db.vaults.delete_one({'user_id': user_id})
