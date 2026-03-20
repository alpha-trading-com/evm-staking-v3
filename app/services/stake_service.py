"""Stake/unstake amount resolution and EVM stake calls. Depends on subtensor for chain state."""
from app.globals import get_coldkey_ss58, get_subtensor
from app.services.evm_service import get_w3_account_contract, receipt_to_dict, run_quiet
from evm import stake, stake_limit, remove_stake, remove_stake_limit, transfer_stake, move_stake, withdraw
from utils.tolerance import calculate_stake_limit_price, calculate_unstake_limit_price


def resolve_remove_stake_amount(
    hotkey: str, netuid: int, amount: float | None
) -> int:
    """Convert remove_stake amount (None = all, 0<x<1 = fraction) to alpha rao."""
    coldkey_ss58 = get_coldkey_ss58()
    subtensor = get_subtensor()
    if amount is None:
        stake_balance = subtensor.get_stake(coldkey_ss58=coldkey_ss58, hotkey_ss58=hotkey, netuid=netuid)
        return stake_balance.rao - 1
    if 0 < amount < 1:
        stake_balance = subtensor.get_stake(coldkey_ss58=coldkey_ss58, hotkey_ss58=hotkey, netuid=netuid)
        return int(amount * stake_balance.rao)
    return int(amount * 10**9)


def resolve_remove_stake_limit_amounts(
    hotkey: str, netuid: int, amount: float | None
) -> tuple[int, float]:
    """Return (amount_alpha_rao, amount_tao) for remove_stake_limit."""
    coldkey_ss58 = get_coldkey_ss58()
    subtensor = get_subtensor()
    if amount is None:
        stake_balance = subtensor.get_stake(coldkey_ss58=coldkey_ss58, hotkey_ss58=hotkey, netuid=netuid)
        return stake_balance.rao - 1, stake_balance.tao
    if 0 < amount < 1:
        stake_balance = subtensor.get_stake(coldkey_ss58=coldkey_ss58, hotkey_ss58=hotkey, netuid=netuid)
        return int(amount * stake_balance.rao), amount * stake_balance.tao
    return int(amount * 10**9), amount / 10**9


def resolve_move_stake_amount(
    origin_hotkey: str, origin_netuid: int, amount_tao: float | None
) -> int:
    """Convert move_stake amount (None = all, 0<x<1 = fraction) to rao."""
    coldkey_ss58 = get_coldkey_ss58()
    subtensor = get_subtensor()
    if amount_tao is None:
        stake_balance = subtensor.get_stake(
            coldkey_ss58=coldkey_ss58, hotkey_ss58=origin_hotkey, netuid=origin_netuid
        )
        return stake_balance.rao - 1
    if 0 < amount_tao < 1:
        stake_balance = subtensor.get_stake(
            coldkey_ss58=coldkey_ss58, hotkey_ss58=origin_hotkey, netuid=origin_netuid
        )
        return int(amount_tao * stake_balance.rao)
    return int(amount_tao * 10**9)


def do_stake(hotkey: str, netuid: int, amount_rao: int) -> dict:
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(stake, w3, account, contract_address, hotkey, netuid, amount_rao, contract=contract)
    return {"ok": True, "receipt": receipt_to_dict(receipt)}


def do_stake_limit(
    hotkey: str, netuid: int, amount_rao: int,
    rate_tolerance: float, use_min_tolerance: bool, allow_partial: bool,
) -> dict:
    subtensor = get_subtensor()
    limit_price = int(calculate_stake_limit_price(
        tao_amount=amount_rao / 10**9,
        netuid=netuid,
        min_tolerance_staking=use_min_tolerance,
        default_rate_tolerance=rate_tolerance,
        subtensor=subtensor,
    ))
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(
        stake_limit, w3, account, contract_address,
        hotkey, netuid, limit_price, amount_rao, allow_partial,
        contract=contract,
    )
    return {"ok": True, "receipt": receipt_to_dict(receipt), "limit_price_used": limit_price}


def do_remove_stake(hotkey: str, netuid: int, amount_alpha_rao: int) -> dict:
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(
        remove_stake, w3, account, contract_address, hotkey, netuid, amount_alpha_rao,
        contract=contract,
    )
    return {"ok": True, "receipt": receipt_to_dict(receipt)}


def do_remove_stake_limit(
    hotkey: str, netuid: int, amount_alpha_rao: int,
    rate_tolerance: float, use_min_tolerance: bool, allow_partial: bool,
    amount_tao: float,
) -> dict:
    subtensor = get_subtensor()
    limit_price = int(calculate_unstake_limit_price(
        tao_amount=amount_tao,
        netuid=netuid,
        min_tolerance_unstaking=use_min_tolerance,
        default_rate_tolerance=rate_tolerance,
        subtensor=subtensor,
    ))
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(
        remove_stake_limit, w3, account, contract_address,
        hotkey, netuid, limit_price, amount_alpha_rao, allow_partial,
        contract=contract,
    )
    return {"ok": True, "receipt": receipt_to_dict(receipt), "limit_price_used": limit_price}


def do_transfer_stake(hotkey: str, origin_netuid: int, destination_netuid: int, amount_rao: int) -> dict:
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(
        transfer_stake, w3, account, contract_address,
        hotkey, origin_netuid, destination_netuid, amount_rao,
        contract=contract,
    )
    return {"ok": True, "receipt": receipt_to_dict(receipt)}


def do_move_stake(
    origin_hotkey: str, destination_hotkey: str,
    origin_netuid: int, destination_netuid: int, amount_rao: int,
) -> dict:
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(
        move_stake, w3, account, contract_address,
        origin_hotkey, destination_hotkey, origin_netuid, destination_netuid, amount_rao,
        contract=contract,
    )
    return {"ok": True, "receipt": receipt_to_dict(receipt)}


def do_withdraw(amount_wei: int) -> dict:
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(withdraw, w3, account, contract_address, amount_wei, contract=contract)
    return {"ok": True, "receipt": receipt_to_dict(receipt)}
