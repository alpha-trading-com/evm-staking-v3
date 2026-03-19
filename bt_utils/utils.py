import asyncio
import os
import random
import bittensor as bt
from typing import Optional, Tuple

from scalecodec import GenericExtrinsic

DEFAULT_PUBLIC_KEY = b'\x01\x02\x03\x04'


async def get_info_extrinsic_async(
    async_subtensor: "bt.AsyncSubtensor",
    wallet: bt.Wallet,
    info: int,
) -> GenericExtrinsic:
    """Build signed MevShield announce_next_key extrinsic with tip=info."""
    call = await async_subtensor.substrate.compose_call(
        call_module='MevShield',
        call_function='announce_next_key',
        call_params={
            'public_key': DEFAULT_PUBLIC_KEY
        }
    )
    extrinsic = await async_subtensor.substrate.create_signed_extrinsic(
        call=call,
        keypair=wallet.coldkey,
        tip=info,
    )
    return extrinsic


async def submit_extrinsic_async(
    async_subtensor: "bt.AsyncSubtensor",
    extrinsic: GenericExtrinsic,
    wait_for_inclusion: bool = True,
) -> Tuple[bool, str]:
    """Submit one extrinsic via AsyncSubtensor. Returns (success, error_message)."""
    try:
        receipt = await async_subtensor.substrate.submit_extrinsic(
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
    async_subtensor: "bt.AsyncSubtensor",
    wallet1: bt.Wallet,
    wallet2: bt.Wallet,
    stake_info: int,
    limit_price: Optional[int] = None,
) -> Tuple[bool, str]:
    """Submit stake_info (and optionally limit_price) via MevShield. Returns (success, message)."""
    if limit_price is None:
        extrinsic = await get_info_extrinsic_async(async_subtensor, wallet1, stake_info)
        ok, msg = await submit_extrinsic_async(async_subtensor, extrinsic, wait_for_inclusion=True)
        return ok, msg

    # Build both extrinsics then submit in parallel
    extrinsic1 = await get_info_extrinsic_async(async_subtensor, wallet1, stake_info)
    extrinsic2 = await get_info_extrinsic_async(async_subtensor, wallet2, limit_price)
    (ok1, msg1), (ok2, msg2) = await asyncio.gather(
        submit_extrinsic_async(async_subtensor, extrinsic1, wait_for_inclusion=True),
        submit_extrinsic_async(async_subtensor, extrinsic2, wait_for_inclusion=True),
    )
    success = ok1 and ok2
    message = "ok" if success else f"stake_info={msg1}; limit_price={msg2}"
    return success, message


if __name__ == "__main__":
    from bittensor.core.async_subtensor import AsyncSubtensor

    async def main():
        wallet1 = bt.Wallet(name="proxy")
        wallet2 = bt.Wallet(name="test_proxy")
        wallet1.unlock_coldkey()
        wallet2.unlock_coldkey()
        async with AsyncSubtensor(network="finney") as async_subtensor:
            success, message = await send_stake_info_async(
                async_subtensor, wallet1, wallet2,
                stake_info=0, limit_price=None,
            )
        print(success, message)

    asyncio.run(main())
