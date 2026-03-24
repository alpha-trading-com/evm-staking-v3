import asyncio
import os
import sys
from dotenv import load_dotenv
from typing import Tuple
from async_substrate_interface import AsyncSubstrateInterface
from app.core.config import settings

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

load_dotenv(os.path.join(_REPO_ROOT, ".env"))

import bittensor as bt

from bt_utils.constants import (
    LIMIT_PRICE_SCALE,
    MAX_NETUID,
    RAO,
    DELEGATE_1,
    DELEGATE_2,
    BLOCK_CYCLE,
)
from bt_utils.utils import send_stake_info_async    


# Wallets (sync; used for signing; load once)
wallet1 = bt.Wallet(name=DELEGATE_1)
wallet2 = bt.Wallet(name=DELEGATE_2)
wallet1.coldkey_file.save_password_to_env(os.getenv("DELEGATE_1_PASSWORD"))
wallet2.coldkey_file.save_password_to_env(os.getenv("DELEGATE_2_PASSWORD"))
wallet1.coldkey_file.decrypt()
wallet2.coldkey_file.decrypt()


async def get_async_substrate() -> AsyncSubstrateInterface:
    _async_substrate = AsyncSubstrateInterface(
        url=settings.NETWORK,
        ss58_format=42,
        type_registry_preset='substrate-node-template',
    )
    return _async_substrate

"""
MAX_STAKING_INFO = 4 * (128 * (amount_tao * 2)) + 1, 1_024_001
MAX_LIMIT_PRICE = 4 * (1e9/ LIMIT_PRICE_SCALE) + 1, 400_001

0        1061770
64       1061771
16384    1061773
"""

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

    async_substrate = await get_async_substrate()
    amount_tao = amount_rao / RAO

    if limit_price is None:
        stake_info = netuid + MAX_NETUID * (amount_tao * 2)
        limit_info = None
    else:
        stake_info = netuid + MAX_NETUID * (amount_tao * 2 - 1)
        limit_price_scaled = int((limit_price + LIMIT_PRICE_SCALE - 1) / LIMIT_PRICE_SCALE)
        limit_info = limit_price_scaled * BLOCK_CYCLE + 1

    stake_info_encoded = stake_info * BLOCK_CYCLE + 1
    return await send_stake_info_async(
        async_substrate,
        wallet1,
        wallet2,
        stake_info_encoded,
        limit_info,
    )


async def fast_unstake_async(
    netuid: int,
) -> Tuple[bool, str]:
    """Submit fast unstake (MevShield). Returns (success, message). Async."""
    async_substrate = await get_async_substrate()
    stake_info = netuid * BLOCK_CYCLE + 1
    return await send_stake_info_async(
        async_substrate, wallet1, wallet2, stake_info, None
    )

if __name__ == "__main__":
    async def main():
        #return await fast_unstake_async(127)
        # return await fast_stake_async(127, 1 * 10**9)
        # return await fast_stake_async(128, 1000 * 10**9)
        return await fast_stake_async(127, 1 * 10**9, 0.008 * 10**9)

    success, message = asyncio.run(main())
    print(success, message)
