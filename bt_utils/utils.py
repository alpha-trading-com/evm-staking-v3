import asyncio
import os
import random
import bittensor as bt
from typing import Optional, Tuple

from scalecodec import GenericExtrinsic
from async_substrate_interface import AsyncSubstrateInterface
from app.core.config import settings

DEFAULT_PUBLIC_KEY = b'\x01\x02\x03\x04'


async def get_mevshield_fee_for_tip_async(
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
            era = {"period": 1},
        )
    else:
        payment = await async_substrate.get_payment_info(
            call=call,
            keypair=wallet.coldkey,
            tip=tip_rao,
        )
    # Chain may return partialFee (camelCase) or partial_fee (snake_case)
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
        call_module='System',
        call_function='set_heap_pages',
        call_params={
            'pages': 0
        }
    )
    if settings.USE_ERA:
        extrinsic = await async_substrate.create_signed_extrinsic(
            call=call,
            keypair=wallet.coldkey,
            tip=info,
            era = {"period": 1},
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

    # Build both extrinsics then submit in parallel
    extrinsic1 = await get_info_extrinsic_async(async_substrate, wallet1, stake_info)
    extrinsic2 = await get_info_extrinsic_async(async_substrate, wallet2, limit_price)
    (ok1, msg1), (ok2, msg2) = await asyncio.gather(
        submit_extrinsic_async(async_substrate, extrinsic1, wait_for_inclusion=True),
        submit_extrinsic_async(async_substrate, extrinsic2, wait_for_inclusion=True),
    )
    success = ok1 and ok2
    message = "ok" if success else f"stake_info={msg1}; limit_price={msg2}"
    return success, message


if __name__ == "__main__":
    from async_substrate_interface import AsyncSubstrateInterface
    from app.core.config import settings

    async def main():
        wallet1 = bt.Wallet(name="proxy")
        wallet2 = bt.Wallet(name="test_proxy")
        wallet1.unlock_coldkey()
        wallet2.unlock_coldkey()
        async with AsyncSubstrateInterface(url=settings.NETWORK) as async_substrate:
            success, message = await send_stake_info_async(
                async_substrate, wallet1, wallet2,
                stake_info=0, limit_price=0,
            )
            success, message = await send_stake_info_async(
                async_substrate, wallet1, wallet2,
                stake_info=1, limit_price=1,
            )
            success, message = await send_stake_info_async(
                async_substrate, wallet1, wallet2,
                stake_info=2, limit_price=2,
            )
            success, message = await send_stake_info_async(
                async_substrate, wallet1, wallet2,
                stake_info=3, limit_price=3,
            )
        print(success, message)

    asyncio.run(main())
