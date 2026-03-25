"""Async fast stake / unstake (MevShield). Sync API: bt_utils.fast_stake_unstake."""
import asyncio
import os
import sys
from dotenv import load_dotenv
from typing import Optional, Tuple

from scalecodec import GenericExtrinsic
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

_wallet1: bt.Wallet | None = None
_wallet2: bt.Wallet | None = None


def _delegate_wallets() -> tuple[bt.Wallet, bt.Wallet]:
    """Load and decrypt DELEGATE_1 / DELEGATE_2 coldkeys once (fast stake/unstake only)."""
    global _wallet1, _wallet2
    if _wallet1 is None:
        _wallet1 = bt.Wallet(name=DELEGATE_1)
        _wallet2 = bt.Wallet(name=DELEGATE_2)
        _wallet1.coldkey_file.save_password_to_env(os.getenv("DELEGATE_1_PASSWORD"))
        _wallet2.coldkey_file.save_password_to_env(os.getenv("DELEGATE_2_PASSWORD"))
        _wallet1.coldkey_file.decrypt()
        _wallet2.coldkey_file.decrypt()
    return _wallet1, _wallet2

_delegate_wallets()


async def get_extrinsic_fee_for_tip_async(
    async_substrate: AsyncSubstrateInterface,
    wallet: bt.Wallet,
    tip_rao: int,
) -> dict:
    """
    Compute total fee (inclusion fee + tip) for a MevShield announce_next_key extrinsic with the given tip.

    Uses the chain's TransactionPaymentApi so the inclusion fee matches what will be charged.
    Returns a dict with keys (all in RAO):
      - inclusion_fee_rao: base + length + weight fee (partial_fee from chain)
      - tip_rao: the tip you passed
      - total_fee_rao: inclusion_fee_rao + tip_rao
    """
    call = await async_substrate.compose_call(
        call_module="System",
        call_function="set_heap_pages",
        call_params={"pages": 0},
    )
    if settings.USE_ERA:
        payment = await async_substrate.get_payment_info(
            call=call,
            keypair=wallet.coldkey,
            tip=tip_rao,
            era={"period": 1},
        )
    else:
        payment = await async_substrate.get_payment_info(
            call=call,
            keypair=wallet.coldkey,
            tip=tip_rao,
        )
    inclusion_rao = int(
        payment.get("partial_fee") or payment.get("partialFee") or 0
    )
    return {
        "inclusion_fee_rao": inclusion_rao,
        "tip_rao": tip_rao,
        "total_fee_rao": inclusion_rao + tip_rao,
    }


async def get_info_extrinsic_async(
    async_substrate: AsyncSubstrateInterface,
    wallet: bt.Wallet,
    info: int,
) -> GenericExtrinsic:
    """Build signed MevShield announce_next_key extrinsic with tip=info."""
    call = await async_substrate.compose_call(
        call_module="System",
        call_function="set_heap_pages",
        call_params={"pages": 0},
    )
    if settings.USE_ERA:
        extrinsic = await async_substrate.create_signed_extrinsic(
            call=call,
            keypair=wallet.coldkey,
            tip=info,
            era={"period": 1},
        )
    else:
        extrinsic = await async_substrate.create_signed_extrinsic(
            call=call,
            keypair=wallet.coldkey,
            tip=info,
        )
    return extrinsic


async def submit_extrinsic_async(
    async_substrate: AsyncSubstrateInterface,
    extrinsic: GenericExtrinsic,
    wait_for_inclusion: bool = True,
) -> Tuple[bool, str]:
    """Submit one extrinsic via AsyncSubtensor. Returns (success, error_message)."""
    try:
        receipt = await async_substrate.submit_extrinsic(
            extrinsic,
            wait_for_inclusion=wait_for_inclusion,
            wait_for_finalization=False,
        )
        if wait_for_inclusion:
            ok = await receipt.is_success
            err = await receipt.error_message
            msg = str(err) if err else ""
            return bool(ok), msg
        return True, ""
    except Exception as e:
        return False, str(e)


async def send_stake_info_async(
    async_substrate: AsyncSubstrateInterface,
    wallet1: bt.Wallet,
    wallet2: bt.Wallet,
    stake_info: int,
    limit_price: Optional[int] = None,
) -> Tuple[bool, str]:
    """Submit stake_info (and optionally limit_price) via MevShield. Returns (success, message)."""
    if limit_price is None:
        extrinsic = await get_info_extrinsic_async(async_substrate, wallet1, stake_info)
        ok, msg = await submit_extrinsic_async(async_substrate, extrinsic, wait_for_inclusion=True)
        return ok, msg

    extrinsic1 = await get_info_extrinsic_async(async_substrate, wallet1, stake_info)
    extrinsic2 = await get_info_extrinsic_async(async_substrate, wallet2, limit_price)
    (ok1, msg1), (ok2, msg2) = await asyncio.gather(
        submit_extrinsic_async(async_substrate, extrinsic1, wait_for_inclusion=True),
        submit_extrinsic_async(async_substrate, extrinsic2, wait_for_inclusion=False),
    )
    success = ok1 and ok2
    message = "ok" if success else f"stake_info={msg1}; limit_price={msg2}"
    return success, message


async def get_async_substrate() -> AsyncSubstrateInterface:
    _async_substrate = AsyncSubstrateInterface(
        url=settings.NETWORK,
        ss58_format=42,
        type_registry_preset="substrate-node-template",
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

    wallet1, wallet2 = _delegate_wallets()
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
    wallet1, wallet2 = _delegate_wallets()
    async_substrate = await get_async_substrate()
    stake_info = netuid * BLOCK_CYCLE + 1
    return await send_stake_info_async(
        async_substrate, wallet1, wallet2, stake_info, None
    )


if __name__ == "__main__":
    async def main():
        # return await fast_unstake_async(127)
        # return await fast_stake_async(127, 1 * 10**9)
        # return await fast_stake_async(128, 1000 * 10**9)
        return await fast_stake_async(127, 1 * 10**9, 0.008 * 10**9)

    success, message = asyncio.run(main())
    print(success, message)
