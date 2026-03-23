"""Fast stake/unstake via MevShield (Bittensor extrinsics) and combined fast-stake-then-unstake."""
from typing import Tuple

from bt_utils.fast_stake_unstake import fast_stake_async, fast_unstake_async
from bt_utils.constants import DEFAULT_HOTKEY
from app.services.stake_service import SN28_NETUID, compute_contract_stake_all_amount_rao
from utils.tolerance import (
    calculate_stake_limit_price,
    calculate_unstake_limit_price,
    get_stake_min_tolerance,
    get_unstake_min_tolerance,
)
from app.globals import get_coldkey_ss58, get_subtensor
from app.services.evm_service import get_w3_account_contract, run_quiet, receipt_to_dict
from evm import remove_stake


async def do_fast_stake(netuid: int, amount_rao: int) -> Tuple[bool, str]:
    """Fast stake via MevShield. Returns (success, message)."""
    return await fast_stake_async(netuid, amount_rao)


async def do_fast_stake_limit(
    netuid: int,
    amount_rao: int,
    rate_tolerance: float,
    use_min_tolerance: bool,
) -> Tuple[bool, str, int | None]:
    """Fast stake limit via MevShield. Returns (success, message, limit_price_used)."""
    limit_price = int(calculate_stake_limit_price(
        tao_amount=amount_rao / 10**9,
        netuid=netuid,
        min_tolerance_staking=use_min_tolerance,
        default_rate_tolerance=rate_tolerance,
        subtensor=get_subtensor(),
    ))
    success, message = await fast_stake_async(netuid, amount_rao, limit_price)
    return success, message, limit_price if success else None


async def do_fast_stake_limit_all_sn28() -> Tuple[bool, str, int | None, int, float]:
    """
    Fast stake-limit on subnet 28 for the same spendable amount as EVM “stake all”
    (compute_contract_stake_all_amount_rao). Min tolerance; MevShield delegates must be funded.
    """
    amount_rao = int(compute_contract_stake_all_amount_rao())
    if amount_rao <= 0:
        raise ValueError("Spendable amount is zero or negative; nothing to fast-stake.")
    success, message, limit_price = await do_fast_stake_limit(
        SN28_NETUID, amount_rao, 0.0, True,
    )
    return success, message, limit_price, amount_rao, amount_rao / 10**9


async def do_fast_unstake(netuid: int) -> Tuple[bool, str]:
    """Fast unstake via MevShield. Returns (success, message)."""
    return await fast_unstake_async(netuid)


async def do_fast_stake_and_unstake(
    netuid: int, amount_rao: int, limit_price: int | None
) -> Tuple[bool, str]:
    """Fast stake via MevShield, then normal unstake via EVM. Returns (success, message)."""
    success, message = await fast_stake_async(netuid, amount_rao, limit_price)
    if not success:
        return False, message
    w3, account, contract_address, contract = get_w3_account_contract()
    # Unstake all for this netuid (contract expects alpha amount; we pull max)
    subtensor = get_subtensor()
    stake_balance = subtensor.get_stake(
        coldkey_ss58=get_coldkey_ss58(),
        hotkey_ss58=DEFAULT_HOTKEY,
        netuid=netuid,
    )
    amount_alpha_rao = stake_balance.rao - 1
    receipt = run_quiet(
        remove_stake, w3, account, contract_address,
        DEFAULT_HOTKEY,
        netuid,
        amount_alpha_rao,
        contract=contract,
    )
    return True, f"Fast stake submitted; unstake tx {receipt_to_dict(receipt).get('transactionHash', '')}"


def calc_min_tolerance_stake(tao_amount: float, netuid: int) -> Tuple[int, float]:
    """Returns (limit_price, rate_tolerance) for stake min tolerance."""
    limit_price = int(calculate_stake_limit_price(
        tao_amount=tao_amount, netuid=netuid,
        min_tolerance_staking=True, default_rate_tolerance=0.0,
        subtensor=get_subtensor(),
    ))
    rate = get_stake_min_tolerance(tao_amount, netuid, get_subtensor())
    return limit_price, rate


def calc_min_tolerance_unstake(tao_amount: float, netuid: int) -> Tuple[int, float]:
    """Returns (limit_price, rate_tolerance) for unstake min tolerance."""
    limit_price = int(calculate_unstake_limit_price(
        tao_amount=tao_amount, netuid=netuid,
        min_tolerance_unstaking=True, default_rate_tolerance=0.0,
        subtensor=get_subtensor(),
    ))
    rate = get_unstake_min_tolerance(tao_amount, netuid, get_subtensor())
    return limit_price, rate
