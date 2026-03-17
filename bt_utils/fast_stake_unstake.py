import os

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


def _get_w3_account_contract():
    """Shared helper to get Web3, account, and StakeWrap contract address."""
    # Ensure env is loaded (matches app.main and bt_utils.auto_execute behavior)
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(repo_root, ".env"))

    rpc_url = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        raise RuntimeError("PRIVATE_KEY is required")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise RuntimeError(f"Failed to connect to {rpc_url}")
    account = Account.from_key(private_key)
    info = load_deployment_info()
    contract_address = Web3.to_checksum_address(info["contract_address"])
    return w3, account, contract_address

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


def fast_stake_and_unstake(netuid: int, amount_rao: int, limit_price: int | None = None):
    """Submit fast stake and unstake (MevShield). Returns (success, message)."""
    # First, send fast stake intent via MevShield (Bittensor extrinsic).
    fast_stake(netuid, amount_rao, limit_price)

    # Then, perform a normal unstake via EVM StakeWrap.removeStake.
    # We use DEFAULT_HOTKEY from bt_utils.constants and treat `amount_rao`
    # as the alpha amount in rao, matching the existing EVM helpers.
    w3, account, contract_address = _get_w3_account_contract()
    evm_remove_stake(w3, account, contract_address, DEFAULT_HOTKEY, netuid, amount_rao)

