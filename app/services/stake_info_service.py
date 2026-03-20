"""Stake info for coldkey (stakes list, balances)."""
from bittensor import Balance
import bittensor as bt
from app.globals import get_coldkey_ss58
from utils.stake_list_v2 import get_amount_with_sim_swap

_stake_info_subtensor = bt.Subtensor(network="finney")

def get_stake_info_response() -> dict:
    """Build /api/stake-info response with stakes, coldkey, balances."""
    coldkey_ss58 = get_coldkey_ss58()
    subtensor = _stake_info_subtensor
    stake_infos = subtensor.get_stake_info_for_coldkey(coldkey_ss58=coldkey_ss58)
    subnet_infos = subtensor.all_subnets()
    balance = subtensor.get_balance(coldkey_ss58)

    stake_list = []
    total_staked_value = 0.0
    for info in stake_infos:
        subnet_info = subnet_infos[info.netuid]
        value = get_amount_with_sim_swap(subtensor, info.stake, info.netuid)
        total_staked_value += value
        stake_list.append({
            "netuid": info.netuid,
            "subnet_name": subnet_info.subnet_name,
            "value_tao": round(value, 2),
            "stake_alpha_tao": round(info.stake.tao, 2),
            "stake_alpha_rao": info.stake.rao,
            "price_tao": round(subnet_info.price.tao, 4),
            "hotkey_ss58": info.hotkey_ss58,
        })

    total_staked_value_balance = Balance.from_tao(total_staked_value)
    total_value = total_staked_value_balance + balance

    return {
        "ok": True,
        "stakes": stake_list,
        "coldkey": coldkey_ss58,
        "free_balance_tao": round(balance.tao, 9),
        "total_staked_value_tao": round(total_staked_value_balance.tao, 9),
        "total_value_tao": round(total_value.tao, 9),
    }
