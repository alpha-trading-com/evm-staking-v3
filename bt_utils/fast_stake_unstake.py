import asyncio
import os
import sys
from dotenv import load_dotenv
from typing import Tuple

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

load_dotenv(os.path.join(_REPO_ROOT, ".env"))

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
from bt_utils.utils import send_stake_info_async
from eth_account import Account
from evm import load_deployment_info, remove_stake as evm_remove_stake
from web3 import Web3

# Wallets (sync; used for signing; load once)
wallet1 = bt.Wallet(name=DELETEGATE_1)
wallet2 = bt.Wallet(name=DELETEGATE_2)
wallet1.coldkey_file.save_password_to_env(os.getenv("DELETEGATE_1_PASSWORD"))
wallet2.coldkey_file.save_password_to_env(os.getenv("DELETEGATE_2_PASSWORD"))
wallet1.coldkey_file.decrypt()
wallet2.coldkey_file.decrypt()

NETWORK = "finney"


async def _block_cycle_for_execute_async(async_subtensor: bt.AsyncSubtensor) -> int:
    """Return (1 + block) % BLOCK_CYCLE for the block where execute() will run (next block)."""
    block = await async_subtensor.get_current_block()
    return (1 + block) % BLOCK_CYCLE


async def fast_stake_async(
    netuid: int,
    amount_rao: int,
    limit_price: int | None = None,
    *,
    network: str = NETWORK,
) -> Tuple[bool, str]:
    """Submit fast stake (MevShield). Returns (success, message). Async.

    If limit_price is provided, submits a fast stake limit order.
    """
    if amount_rao == 0:
        return True, "Amount is 0"

    from bittensor.core.async_subtensor import AsyncSubtensor

    async with AsyncSubtensor(network=network) as async_subtensor:
        block_cycle = await _block_cycle_for_execute_async(async_subtensor)
        amount_tao = amount_rao / RAO

        if limit_price is None:
            stake_info = netuid + MAX_NETUID * (amount_tao * 2)
            limit_info = None
        else:
            stake_info = netuid + MAX_NETUID * (amount_tao * 2 - 1)
            limit_price_scaled = int((limit_price + LIMIT_PRICE_SCALE - 1) / LIMIT_PRICE_SCALE)
            limit_info = limit_price_scaled * BLOCK_CYCLE + block_cycle

        stake_info_encoded = stake_info * BLOCK_CYCLE + block_cycle
        return await send_stake_info_async(
            async_subtensor,
            wallet1,
            wallet2,
            stake_info_encoded,
            limit_info,
        )


async def fast_unstake_async(
    netuid: int,
    *,
    network: str = NETWORK,
) -> Tuple[bool, str]:
    """Submit fast unstake (MevShield). Returns (success, message). Async."""
    from bittensor.core.async_subtensor import AsyncSubtensor

    async with AsyncSubtensor(network=network) as async_subtensor:
        block_cycle = await _block_cycle_for_execute_async(async_subtensor)
        stake_info = netuid * BLOCK_CYCLE + block_cycle
        return await send_stake_info_async(
            async_subtensor, wallet1, wallet2, stake_info, None
        )


async def fast_stake_and_unstake_async(
    netuid: int,
    amount_rao: int,
    limit_price: int | None = None,
    *,
    network: str = NETWORK,
) -> Tuple[bool, str]:
    """Fast stake via MevShield, then EVM remove_stake. Returns (success, message)."""
    success, message = await fast_stake_async(netuid, amount_rao, limit_price, network=network)
    if not success:
        return False, message
    # Unstake via EVM (amount in alpha; conversion from amount_rao may be needed depending on price)
    load_dotenv(os.path.join(_REPO_ROOT, ".env"))
    rpc_url = os.getenv("RPC_URL")
    private_key = os.getenv("PRIVATE_KEY")
    if not rpc_url or not private_key:
        return True, "fast_stake ok; EVM unstake skipped (no RPC_URL/PRIVATE_KEY)"
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        return True, "fast_stake ok; EVM unstake skipped (RPC not connected)"
    deployment = load_deployment_info()
    contract_address = deployment["contract_address"]
    account = Account.from_key(private_key)
    # amount_rao is TAO; remove_stake expects amount in ALPHA - using amount_rao as placeholder
    evm_remove_stake(w3, account, contract_address, DEFAULT_HOTKEY, netuid, amount_rao)
    return True, message


if __name__ == "__main__":
    async def main():
        # await fast_unstake_async(64)
        # await fast_stake_async(64, 1 * 10**9)
        return await fast_stake_async(64, 1 * 10**9, 0.1064 * 10**9)

    success, message = asyncio.run(main())
    print(success, message)
