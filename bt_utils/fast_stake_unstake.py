import bittensor as bt
from bt_utils.constants import (
    LIMIT_PRICE_SCALE, MAX_NETUID, RAO,
    DELETEGATE_1, DELETEGATE_2, BLOCK_CYCLE
)
from bt_utils.utils import send_stake_info

subtensor1 = bt.Subtensor(network="finney")
subtensor2 = bt.Subtensor(network="finney")
wallet1 = bt.Wallet(name=DELETEGATE_1)
wallet2 = bt.Wallet(name=DELETEGATE_2)

def fast_stake(netuid: int, amount_rao: int, limit_price: int | None = None):
    """Submit fast stake (MevShield). Returns (success, message).

    If `limit_price` is provided, submits a fast stake limit order.
    """
    block_cycle = subtensor1.get_block_number() % BLOCK_CYCLE
    amount_tao = amount_rao / RAO

    if limit_price is None:
        stake_info = netuid + MAX_NETUID * (amount_tao * 2)
        limit_info = None
    else:
        stake_info = netuid + MAX_NETUID * (amount_tao * 2 - 1)
        limit_price_scaled = int((limit_price + LIMIT_PRICE_SCALE - 1) / LIMIT_PRICE_SCALE)
        limit_info = limit_price_scaled * BLOCK_CYCLE + block_cycle

    return send_stake_info(
        subtensor1,
        subtensor2,
        wallet1,
        wallet2,
        stake_info * BLOCK_CYCLE + block_cycle,
        limit_info,
    )


def fast_unstake(netuid: int):
    """Submit fast unstake (MevShield). Returns (success, message)."""
    stake_info = netuid
    block_cycle = subtensor1.get_block_number() % BLOCK_CYCLE
    return send_stake_info(subtensor1, subtensor2, wallet1, wallet2, stake_info * BLOCK_CYCLE + block_cycle, None)