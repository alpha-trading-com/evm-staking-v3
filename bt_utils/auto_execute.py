#!/usr/bin/env python3
"""
Call the StakeWrap contract's execute() at the start of every new block.

Uses delegate addresses from bt_utils.constants. Balances from Bittensor chain
via SubstrateInterface over BITTENSOR_WS_URL (no bittensor.Subtensor).
Requires: RPC_URL; and either EXECUTOR_PRIVATE_KEY (recommended) or PRIVATE_KEY (owner).
If using EXECUTOR_PRIVATE_KEY, the contract must have executor set (owner calls setExecutor(executorAddress)).
Optional: BITTENSOR_WS_URL (default wss://entrypoint-finney.opentensor.ai:443).

Run from project root: python bt_utils/auto_execute.py  or  python -m bt_utils.auto_execute

If you see "Failed 0x..." in logs, the contract reverted (e.g. OnlyOwnerOrExecutor, Expired, Exploited).
Ensure setExecutor(executorAddress) was called and EXECUTOR_PRIVATE_KEY matches that address.
"""

import json
import os
import sys
import time

from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
from async_substrate_interface.sync_substrate import SubstrateInterface

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(_THIS_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from evm import get_contract, load_deployment
from evm.stake_wrap import pack_execute_params
from bt_utils.constants import (
    STAKE_INFO_DELEGATE,
    LIMIT_PRICE_DELEGATE,
    EXECUTOR_ENABLED_FILENAME,
)

DEFAULT_BITTENSOR_WS_URL = "wss://entrypoint-finney.opentensor.ai:443"

BLOCK_DATA_FETCH_PAYLOAD = json.dumps({
    "jsonrpc": "2.0",
    "method": "chain_getHeader",
    "params": [None],
    "id": 0,
})

def get_current_block(substrate) -> int:
    """Current Bittensor block number via direct WS chain_getHeader (fast)."""
    ws = substrate.ws
    ws.send(BLOCK_DATA_FETCH_PAYLOAD)
    raw = ws.recv()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    response = json.loads(raw)
    num = response["result"]["number"]
    return int(num, 0)  # 0 = auto (hex or decimal)


def _get_balance_rao(substrate, ss58: str) -> int:
    """One account's free balance (rao) via substrate.query(System::Account). Uses runtime metadata for correct decode."""
    result = substrate.query(
        module="System",
        storage_function="Account",
        params=[ss58],
    )
    if result is None:
        return 0
    # result can be dict or ScaleObj with .value (decoded AccountInfo)
    obj = getattr(result, "value", result)
    data = obj.get("data") if isinstance(obj, dict) else None
    if not data:
        return 0
    free = data.get("free") if isinstance(data, dict) else None
    if free is None:
        return 0
    return int(free)


def get_delegate_balances_from_chain(substrate) -> tuple[int, int]:
    """
    Query Bittensor chain for free balance (rao) of STAKE_INFO_DELEGATE and LIMIT_PRICE_DELEGATE.
    Uses SubstrateInterface.query (same as bittensor subtensor.get_balance, correct key + decode).
    Returns (stake_info_balance_rao, limit_price_balance_rao).
    """
    b1 = _get_balance_rao(substrate, STAKE_INFO_DELEGATE)
    b2 = _get_balance_rao(substrate, LIMIT_PRICE_DELEGATE)
    return (b1, b2)


def is_executor_enabled() -> bool:
    """True if executor_enabled.json has "enabled": true. Default True if file missing."""
    path = os.path.join(ROOT_DIR, EXECUTOR_ENABLED_FILENAME)
    if not os.path.isfile(path):
        return True
    try:
        with open(path) as f:
            return json.load(f).get("enabled", True)
    except Exception:
        return True


def main():

    load_dotenv(os.path.join(ROOT_DIR, ".env"))

    rpc_url = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
    ws_url = os.getenv("BITTENSOR_WS_URL", DEFAULT_BITTENSOR_WS_URL)
    executor_key = os.getenv("EXECUTOR_PRIVATE_KEY")
    owner_key = os.getenv("PRIVATE_KEY")

    # Prefer executor wallet to avoid nonce conflict with owner (stake/unstake/withdraw from UI).
    if executor_key:
        private_key = executor_key
        use_executor_wallet = True
    elif owner_key:
        private_key = owner_key
        use_executor_wallet = False
    else:
        raise SystemExit("Set EXECUTOR_PRIVATE_KEY (recommended) or PRIVATE_KEY for the execute() signer")

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise SystemExit(f"Failed to connect to RPC: {rpc_url}")

    deployment = load_deployment()
    contract_address = Web3.to_checksum_address(deployment["contract_address"])
    contract = get_contract(w3, contract_address)
    account = Account.from_key(private_key)

    if use_executor_wallet:
        executor_addr = contract.functions.executor().call()
        if not executor_addr or executor_addr == "0x0000000000000000000000000000000000000000":
            raise SystemExit("Contract has no executor set. Owner must call setExecutor(executorAddress) first.")
        if executor_addr.lower() != account.address.lower():
            raise SystemExit(f"Account {account.address} is not contract executor {executor_addr}")
        print("Using executor wallet (EXECUTOR_PRIVATE_KEY)")
    else:
        owner = contract.functions.owner().call()
        if owner.lower() != account.address.lower():
            raise SystemExit(f"Account {account.address} is not contract owner {owner}")
        print("Using owner wallet (PRIVATE_KEY)")

    print(f"Contract: {contract_address}")
    print(f"Delegates: STAKE_INFO={STAKE_INFO_DELEGATE}, LIMIT_PRICE={LIMIT_PRICE_DELEGATE}")

    # SubstrateInterface over WS (same key/decode as bittensor, no bt.Subtensor)
    try:
        substrate = SubstrateInterface(url=ws_url)
    except Exception as e:
        raise SystemExit(f"Failed to connect to Bittensor WS {ws_url}: {e}")

    last_block = get_current_block(substrate)
    
    chain_balances = get_delegate_balances_from_chain(substrate)
    stake_info_balance = chain_balances[0]
    limit_price_balance = chain_balances[1]
    print(f"Balances from chain (rao): stake_info={stake_info_balance}, limit_price={limit_price_balance}")

    gas_limit = int(os.getenv("EXECUTOR_GAS_LIMIT", "600000"))
    print("Polling for new blocks (Bittensor chain)...")

    nonce = w3.eth.get_transaction_count(account.address)
    signed = None
    is_executor_enabled_flag = is_executor_enabled()
    while True:
        try:
            current = get_current_block(substrate)
        except Exception as e:
            print(f"get_current_block failed: {e}")
            time.sleep(2)
            continue
        if current > last_block:
            try:
                if signed is None:
                    chain_balances = get_delegate_balances_from_chain(substrate)
                    stake_info_balance = chain_balances[0]
                    limit_price_balance = chain_balances[1]
                    exec_block = current + 1
                    print(f"Balances from chain (rao): stake_info={stake_info_balance}, limit_price={limit_price_balance}")
                    packed_balances = pack_execute_params(stake_info_balance, limit_price_balance)
                    tx = contract.functions.execute(exec_block, packed_balances).build_transaction({
                        "from": account.address,
                        "nonce": nonce,
                        "gas": gas_limit,
                        "gasPrice": w3.eth.gas_price,
                    })
                    signed = account.sign_transaction(tx)
                if is_executor_enabled_flag:
                    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                    print(f"Block {current} execute(execBlock={exec_block}) tx {tx_hash.hex()}")
                    nonce += 1

                is_executor_enabled_flag = is_executor_enabled()

                chain_balances = get_delegate_balances_from_chain(substrate)
                stake_info_balance = chain_balances[0]
                limit_price_balance = chain_balances[1]
                exec_block = current + 2
                packed_balances = pack_execute_params(stake_info_balance, limit_price_balance)
                tx = contract.functions.execute(exec_block, packed_balances).build_transaction({
                    "from": account.address,
                    "nonce": nonce,
                    "gas": gas_limit,
                    "gasPrice": w3.eth.gas_price,
                })
                signed = account.sign_transaction(tx)
            except Exception as e:
                err_msg = str(e).strip()
                if "Failed 0x" in err_msg or (hasattr(e, "args") and e.args and "0x" in str(e.args)):
                    print(f"Block {current} execute reverted: {type(e).__name__}: {err_msg}")
                    print("  -> Check: contract executor is set (owner called setExecutor) and EXECUTOR_PRIVATE_KEY matches that address.")
                else:
                    print(f"Block {current} execute failed: {type(e).__name__}: {err_msg}")
            last_block = current

        time.sleep(2)


if __name__ == "__main__":
    main()
