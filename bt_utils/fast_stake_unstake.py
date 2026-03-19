import asyncio
import os
import sys
from dotenv import load_dotenv
from typing import Tuple

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

load_dotenv(os.path.join(_REPO_ROOT, ".env"))

import bittensor as bt
from bt_utils.constants import (
    LIMIT_PRICE_SCALE,
    MAX_NETUID,
    RAO,
    DELETEGATE_1,
    DELETEGATE_2,
    BLOCK_CYCLE,
)
from bt_utils.utils import send_stake_info_async
from bittensor.core.async_subtensor import AsyncSubtensor

# Wallets (sync; used for signing; load once)
wallet1 = bt.Wallet(name=DELETEGATE_1)
wallet2 = bt.Wallet(name=DELETEGATE_2)
wallet1.coldkey_file.save_password_to_env(os.getenv("DELETEGATE_1_PASSWORD"))
wallet2.coldkey_file.save_password_to_env(os.getenv("DELETEGATE_2_PASSWORD"))
wallet1.coldkey_file.decrypt()
wallet2.coldkey_file.decrypt()

NETWORK = "finney"

# Global AsyncSubtensor (lazy-initialized, reused across calls; uses NETWORK)
_async_subtensor = None


async def get_async_subtensor() -> "bt.AsyncSubtensor":
    """Return the global AsyncSubtensor, initializing on first use."""
    global _async_subtensor
    if _async_subtensor is None:
        _async_subtensor = AsyncSubtensor(network=NETWORK)
        await _async_subtensor.initialize()
    return _async_subtensor


async def _block_cycle_for_execute_async(async_subtensor: bt.AsyncSubtensor) -> int:
    """Return (1 + block) % BLOCK_CYCLE for the block where execute() will run (next block)."""
    block = await async_subtensor.get_current_block()
    return (1 + block) % BLOCK_CYCLE


async def fast_stake_async(
    netuid: int,
    amount_rao: int,
    limit_price: int | None = None,
) -> Tuple[bool, str]:
    """Submit fast stake (MevShield). Returns (success, message). Async.

    If limit_price is provided, submits a fast stake limit order.
    """
    if amount_rao == 0:
        return True, "Amount is 0"

    async_subtensor = await get_async_subtensor()
    block_cycle = await _block_cycle_for_execute_async(async_subtensor)
    amount_tao = amount_rao / RAO

    if limit_price is None:
        stake_info = netuid + MAX_NETUID * (amount_tao * 2)
        limit_info = None
    else:
        stake_info = netuid + MAX_NETUID * (amount_tao * 2 - 1)
        limit_price_scaled = int((limit_price + LIMIT_PRICE_SCALE - 1) / LIMIT_PRICE_SCALE)
        limit_info = limit_price_scaled * BLOCK_CYCLE + block_cycle

    stake_info_encoded = stake_info * BLOCK_CYCLE + block_cycle
    return await send_stake_info_async(
        async_subtensor,
        wallet1,
        wallet2,
        stake_info_encoded,
        limit_info,
    )


async def fast_unstake_async(
    netuid: int,
) -> Tuple[bool, str]:
    """Submit fast unstake (MevShield). Returns (success, message). Async."""
    async_subtensor = await get_async_subtensor()
    block_cycle = await _block_cycle_for_execute_async(async_subtensor)
    stake_info = netuid * BLOCK_CYCLE + block_cycle
    return await send_stake_info_async(
        async_subtensor, wallet1, wallet2, stake_info, None
    )

if __name__ == "__main__":
    async def main():
        # await fast_unstake_async(64)
        # await fast_stake_async(64, 1 * 10**9)
        return await fast_stake_async(64, 1 * 10**9, 0.1064 * 10**9)

    success, message = asyncio.run(main())
    print(success, message)
