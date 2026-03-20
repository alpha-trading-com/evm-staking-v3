import asyncio
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import bittensor as bt
from bt_utils.utils import get_mevshield_fee_for_tip_async


async def get_diff(
    async_subtensor: bt.AsyncSubtensor,
    wallet: bt.Wallet,
    tip_rao: int,
) -> int:
    """Inclusion fee (total_fee - tip) for the given tip_rao."""
    fee = await get_mevshield_fee_for_tip_async(
        async_subtensor, wallet,
        tip_rao=tip_rao,
    )
    return fee["total_fee_rao"] - tip_rao


async def find_next_change(
    async_subtensor: bt.AsyncSubtensor,
    wallet: bt.Wallet,
    lo: int,
    hi: int,
    base_diff: int,
) -> int | None:
    """Binary search: smallest tip_rao in (lo, hi] with diff != base_diff, or None."""
    if lo >= hi:
        return None
    diff_hi = await get_diff(async_subtensor, wallet, hi)
    if diff_hi == base_diff:
        return None
    # diff(hi) != base_diff, so there is at least one change in (lo, hi]
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        diff_mid = await get_diff(async_subtensor, wallet, mid)
        if diff_mid != base_diff:
            hi = mid
        else:
            lo = mid
    return hi


async def find_all_diff_changes(
    async_subtensor: bt.AsyncSubtensor,
    wallet: bt.Wallet,
    max_tip_rao: int = 1000,
) -> list[tuple[int, int]]:
    """Find all tip_rao where inclusion fee (diff) changes. Returns [(tip_rao, diff), ...]."""
    changes: list[tuple[int, int]] = []
    base_diff = await get_diff(async_subtensor, wallet, 0)
    changes.append((0, base_diff))
    lo = 0
    while lo < max_tip_rao:
        next_tip = await find_next_change(
            async_subtensor, wallet, lo, max_tip_rao, base_diff
        )
        if next_tip is None:
            break
        base_diff = await get_diff(async_subtensor, wallet, next_tip)
        changes.append((next_tip, base_diff))
        lo = next_tip
    return changes


async def main():
    async with bt.AsyncSubtensor(network="finney") as async_subtensor:
        wallet = bt.Wallet(name="proxy")
        wallet.unlock_coldkey()
        print("Finding tip_rao positions where diff (inclusion fee) changes...")
        changes = await find_all_diff_changes(
            async_subtensor, wallet, max_tip_rao=1_024_001 * 4
        )
        print("tip_rao\t diff (inclusion_fee_rao)")
        for tip_rao, diff in changes:
            print(tip_rao, "\t", diff)
        print("Done.")

        for tip_rao, diff in changes:
            fee = await get_mevshield_fee_for_tip_async(
                async_subtensor, wallet,
                tip_rao= max(0, tip_rao - 1),
            )
            print(tip_rao - 1,  fee)

            fee = await get_mevshield_fee_for_tip_async(
                async_subtensor, wallet,
                tip_rao=tip_rao + 1,
            )
            print(tip_rao + 1,  fee)

asyncio.run(main())