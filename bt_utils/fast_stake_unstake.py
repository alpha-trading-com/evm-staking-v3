import bittensor as bt
from bt_utils.constants import LIMIT_PRICE_SCALE, MAX_NETUID
from bt_utils.utils import send_stake_info

subtensor1 = bt.Subtensor(network="finney")
subtensor2 = bt.Subtensor(network="finney")
wallet1 = bt.Wallet(name="soon")
wallet2 = bt.Wallet(name="soon")

def fast_stake(netuid: int, amount_tao: int):
    stake_info = netuid + MAX_NETUID * (amount_tao * 2)
    send_stake_info(subtensor1, subtensor2, wallet1, stake_info, None)

def fast_stake_limit(netuid: int, amount_tao: float, limit_price: int):
   stake_info = netuid  + MAX_NETUID * (amount_tao * 2 - 1)
   limit_price = int((limit_price + LIMIT_PRICE_SCALE - 1) / LIMIT_PRICE_SCALE)
   send_stake_info(subtensor1, subtensor2, wallet1, stake_info, limit_price)
    

def fast_unstake(netuid: int):
    stake_info = netuid
    send_stake_info(subtensor1, subtensor2, wallet1, stake_info, None)