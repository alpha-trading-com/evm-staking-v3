import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import bittensor as bt
from bt_utils.constants import (
    LIMIT_PRICE_SCALE,
    MAX_NETUID,
    RAO,
    DELETEGATE_1,
    DELETEGATE_2,
    BLOCK_CYCLE,
    DEFAULT_HOTKEY,
)
from bt_utils.utils import send_stake_info
from dotenv import load_dotenv
from eth_account import Account
from evm import load_deployment_info, remove_stake as evm_remove_stake
from web3 import Web3

subtensor1 = bt.Subtensor(network="finney")
subtensor2 = bt.Subtensor(network="finney")
wallet1 = bt.Wallet(name=DELETEGATE_1)
wallet2 = bt.Wallet(name=DELETEGATE_2)

def fast_stake(netuid: int, amount_rao: int, limit_price: int | None = None):
    """Submit fast stake (MevShield). Returns (success, message).

    If `limit_price` is provided, submits a fast stake limit order.
    """
    block_cycle = (1 + subtensor1.get_current_block()) % BLOCK_CYCLE
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
    block_cycle = (1 + subtensor1.get_current_block()) % BLOCK_CYCLE
    return send_stake_info(subtensor1, subtensor2, wallet1, wallet2, stake_info * BLOCK_CYCLE + block_cycle, None)


if __name__ == "__main__":
    fast_stake(64, 1 * 10**9)

