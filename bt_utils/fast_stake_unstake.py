import bittensor as bt
from bt_utils.constants import (
    LIMIT_PRICE_SCALE, MAX_NETUID, RAO,
    DELETEGATE_1, DELETEGATE_2
)
from bt_utils.utils import send_stake_info

subtensor1 = bt.Subtensor(network="finney")
subtensor2 = bt.Subtensor(network="finney")
wallet1 = bt.Wallet(name=DELETEGATE_1)
wallet2 = bt.Wallet(name=DELETEGATE_2)

def fast_stake(netuid: int, amount_rao: int):
    """Submit fast stake (MevShield). Returns (success, message)."""
    amount_tao = amount_rao / RAO
    stake_info = netuid + MAX_NETUID * (amount_tao * 2)
    return send_stake_info(subtensor1, subtensor2, wallet1, stake_info, None)


def fast_stake_limit(netuid: int, amount_rao: int, limit_price: int):
    """Submit fast stake limit (MevShield). Returns (success, message)."""
    amount_tao = amount_rao / RAO
    stake_info = netuid + MAX_NETUID * (amount_tao * 2 - 1)
    limit_price_scaled = int((limit_price + LIMIT_PRICE_SCALE - 1) / LIMIT_PRICE_SCALE)
    return send_stake_info(subtensor1, subtensor2, wallet1, stake_info, limit_price_scaled)


def fast_unstake(netuid: int):
    """Submit fast unstake (MevShield). Returns (success, message)."""
    stake_info = netuid
    return send_stake_info(subtensor1, subtensor2, wallet1, stake_info, None)