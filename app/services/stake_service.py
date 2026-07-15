"""Stake/unstake amount resolution and EVM stake calls. Depends on subtensor for chain state."""
import os

from web3 import Web3

from bt_utils.constants import DEFAULT_HOTKEY
from app.globals import get_coldkey_ss58, get_subtensor
from app.services.evm_service import get_w3_account_contract, receipt_to_dict, run_quiet
from evm import stake, stake_limit, remove_stake, remove_stake_limit, transfer_stake, move_stake, withdraw, set_default_hotkey, get_default_hotkey
from evm.address import account_id_to_ss58
from utils.tolerance import calculate_stake_limit_price, calculate_unstake_limit_price

SN28_NETUID = 28


def compute_contract_stake_all_amount_rao() -> int:
    """
    Max TAO (rao) the StakeWrap contract coldkey can stake: free balance minus ED
    """
    subtensor = get_subtensor()
    coldkey_ss58 = get_coldkey_ss58()
    balance = subtensor.get_balance(coldkey_ss58)
    return balance.rao - 10**9 # 1tao remaining on the contract coldkey

def resolve_remove_stake_amount(
    hotkey: str, netuid: int, amount: float | None
) -> int:
    """Convert remove_stake amount (None = all, 0<x<1 = fraction) to alpha rao."""
    coldkey_ss58 = get_coldkey_ss58()
    subtensor = get_subtensor()
    if amount is None:
        return 0
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


def get_current_default_hotkey() -> dict:
    """Read the contract's current default hotkey, returned as both bytes32 hex and SS58."""
    w3, _account, contract_address, contract = get_w3_account_contract()
    hotkey_bytes32 = get_default_hotkey(w3, contract_address, contract=contract)
    return {
        "ok": True,
        "hotkey_hex": "0x" + hotkey_bytes32.hex(),
        "hotkey_ss58": account_id_to_ss58(hotkey_bytes32),
    }


def do_set_default_hotkey(hotkey: str) -> dict:
    """Owner-only: update the default hotkey used by execute(). `hotkey` is an SS58 address."""
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(set_default_hotkey, w3, account, contract_address, hotkey, contract=contract)
    if receipt is None:
        raise RuntimeError("setDefaultHotkey did not complete. Ensure the signer is the contract owner.")
    return {"ok": True, "receipt": receipt_to_dict(receipt), "hotkey_ss58": hotkey}


def do_stake(hotkey: str, netuid: int, amount_rao: int) -> dict:
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(stake, w3, account, contract_address, hotkey, netuid, amount_rao, contract=contract)
    return {"ok": True, "receipt": receipt_to_dict(receipt)}


def do_stake_limit_all_sn28() -> dict:
    """
    Stake-limit entire spendable contract balance to subnet 28 using DEFAULT_HOTKEY and min tolerance.
    Partial fills are disabled (allow_partial=False).
    Reserve leaves dust on the contract coldkey (fees / keep-alive); override with STAKE_ALL_RESERVE_RAO or SN28_STAKE_RESERVE_RAO.
    """
    amount_rao = compute_contract_stake_all_amount_rao()
    out = do_stake_limit(
        DEFAULT_HOTKEY,
        SN28_NETUID,
        amount_rao,
        rate_tolerance=0.0,
        use_min_tolerance=True,
        allow_partial=False,
    )
    out["amount_rao"] = amount_rao
    out["amount_tao"] = amount_rao / 10**9
    out["hotkey_ss58"] = DEFAULT_HOTKEY
    out["netuid"] = SN28_NETUID
    return out


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


def do_withdraw(amount_tao: float | None) -> dict:
    """Withdraw TAO. amount_tao None = full contract native balance (wei). Otherwise amount in TAO (18-decimal wei conversion)."""
    w3, account, contract_address, contract = get_w3_account_contract()
    balance_wei = w3.eth.get_balance(contract_address)
    if amount_tao is None:
        amount_wei = balance_wei
    else:
        if amount_tao <= 0:
            raise ValueError("Amount must be positive, or omit it to withdraw the full contract balance.")
        amount_wei = int(amount_tao * 10**18)
    if amount_wei == 0:
        raise ValueError("Contract balance is zero; nothing to withdraw.")
    if amount_wei > balance_wei:
        avail = Web3.from_wei(balance_wei, "ether")
        raise ValueError(f"Withdraw amount exceeds contract balance ({avail} TAO available).")
    receipt = run_quiet(withdraw, w3, account, contract_address, amount_wei, contract=contract)
    if receipt is None:
        raise RuntimeError("Withdraw did not complete. Ensure the signer is the contract owner.")
    return {"ok": True, "receipt": receipt_to_dict(receipt)}
