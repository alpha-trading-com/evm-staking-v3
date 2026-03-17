#!/usr/bin/env python3
"""
Call the StakeWrap contract's execute() at the start of every new block.

Uses delegate addresses from bt_utils.constants (STAKE_INFO_DELEGATE, LIMIT_PRICE_DELEGATE).
Balances are read from the Bittensor chain for those delegates when bittensor is available;
otherwise uses STAKE_INFO_DELEGATE_BALANCE_RAO and LIMIT_PRICE_DELEGATE_BALANCE_RAO from
bt_utils.constants.

Requires: PRIVATE_KEY (owner), RPC_URL. Optional: BITTENSOR_NETWORK (default finney).

Run from project root: python bt_utils/auto_execute.py  or  python -m bt_utils.auto_execute
"""

import os
import sys
import json
import time
import hashlib
import importlib.util

from web3 import Web3
from eth_account import Account

# Paths: this file is in bt_utils/; project root is parent of bt_utils
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(_THIS_DIR)
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from bt_utils.constants import (
    STAKE_INFO_DELEGATE,
    LIMIT_PRICE_DELEGATE,
    STAKE_INFO_DELEGATE_BALANCE_RAO,
    LIMIT_PRICE_DELEGATE_BALANCE_RAO,
    STAKE_INFO_BASE_FEE_RAO,
    LIMIT_PRICE_BASE_FEE_RAO,
)

# Contract: MAX_DELEGATE_BALANCE = 2 TAO
MAX_DELEGATE_BALANCE_RAO = 2 * 10**9

import bittensor as bt


def load_deployment(path=None):
    if path is None:
        path = os.path.join(ROOT_DIR, "deployment.json")
    with open(path, "r") as f:
        return json.load(f)


def _load_abi_from_interact():
    """Load CONTRACT_ABI from scripts/interact.py when artifact is missing."""
    interact_path = os.path.join(SCRIPTS_DIR, "interact.py")
    if not os.path.exists(interact_path):
        raise FileNotFoundError(f"Neither StakeWrap.json artifact nor {interact_path} found")
    spec = importlib.util.spec_from_file_location("interact", interact_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CONTRACT_ABI


def get_contract(w3, contract_address):
    artifact_path = os.path.join(ROOT_DIR, "artifacts/contracts/StakeWrap.sol/StakeWrap.json")
    if os.path.exists(artifact_path):
        with open(artifact_path, "r") as f:
            abi = json.load(f)["abi"]
    else:
        abi = _load_abi_from_interact()
    return w3.eth.contract(address=contract_address, abi=abi)


def _h160_to_account_id(h160_hex: str) -> bytes:
    """EVM address -> 32-byte AccountId32: Blake2b-256(b'evm:' + h160). Matches address_convert.py."""
    raw = h160_hex.strip()
    if raw.startswith("0x") or raw.startswith("0X"):
        raw = raw[2:]
    if len(raw) != 40:
        raise ValueError("Ethereum address must be 40 hex chars (with or without 0x)")
    addr_bytes = bytes.fromhex(raw)
    combined = b"evm:" + addr_bytes
    return hashlib.blake2b(combined, digest_size=32).digest()


def contract_address_bytes32(contract_address_hex: str) -> bytes:
    """EVM contract address -> 32-byte AccountId32 (Blake2b('evm:' || h160))."""
    return _h160_to_account_id(contract_address_hex)


def get_delegate_balances_from_chain(network="finney"):
    """
    Query Bittensor chain for free balance (in rao) of STAKE_INFO_DELEGATE and LIMIT_PRICE_DELEGATE.
    Returns (stake_info_balance_rao, limit_price_balance_rao).
    """
    try:
        subtensor = bt.Subtensor(network=network)
        b1 = subtensor.get_balance(STAKE_INFO_DELEGATE)
        b2 = subtensor.get_balance(LIMIT_PRICE_DELEGATE)
        return (b1.rao, b2.rao)
    except Exception as e:
        raise RuntimeError(f"Failed to query delegate balances from Bittensor: {e}") from e


def clamp_balance(rao):
    """Cap at MAX_DELEGATE_BALANCE (2 TAO) to avoid Exploited() revert."""
    return min(rao, MAX_DELEGATE_BALANCE_RAO)


def main():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT_DIR, ".env"))

    rpc_url = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
    private_key = os.getenv("PRIVATE_KEY")
    network = os.getenv("BITTENSOR_NETWORK", "finney")

    if not private_key:
        raise SystemExit("PRIVATE_KEY environment variable is required")

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise SystemExit(f"Failed to connect to RPC: {rpc_url}")

    deployment = load_deployment()
    contract_address = Web3.to_checksum_address(deployment["contract_address"])
    contract = get_contract(w3, contract_address)
    account = Account.from_key(private_key)

    owner = contract.functions.owner().call()
    if owner.lower() != account.address.lower():
        raise SystemExit(f"Account {account.address} is not contract owner {owner}")

    contract_addr_b32 = contract_address_bytes32(contract_address)
    print(f"Contract: {contract_address}")
    print(f"Contract AccountId32: 0x{contract_addr_b32.hex()}")
    print(f"Delegates: STAKE_INFO={STAKE_INFO_DELEGATE}, LIMIT_PRICE={LIMIT_PRICE_DELEGATE}")

    # Resolve balances from chain (required)
    chain_balances = get_delegate_balances_from_chain(network)
    stake_info_balance = clamp_balance(chain_balances[0])
    limit_price_balance = clamp_balance(chain_balances[1])
    print(f"Balances from chain (rao): stake_info={stake_info_balance}, limit_price={limit_price_balance}")

    stake_info_base_fee = STAKE_INFO_BASE_FEE_RAO
    limit_price_base_fee = LIMIT_PRICE_BASE_FEE_RAO
    print(f"Base fees (rao): stake_info={stake_info_base_fee}, limit_price={limit_price_base_fee}")
    print("Polling for new blocks...")

    last_block = w3.eth.block_number
    while True:
        current = w3.eth.block_number
        if current > last_block:
            for block_num in range(last_block + 1, current + 1):
                try:
                    # Refresh balances from chain each block
                    chain_balances = get_delegate_balances_from_chain(network)
                    stake_info_balance = clamp_balance(chain_balances[0])
                    limit_price_balance = clamp_balance(chain_balances[1])
                    tx = contract.functions.execute(
                        block_num,
                        contract_addr_b32,
                        stake_info_balance,
                        limit_price_balance,
                        stake_info_base_fee,
                        limit_price_base_fee,
                    ).build_transaction({
                        "from": account.address,
                        "nonce": w3.eth.get_transaction_count(account.address),
                        "gas": 600_000,
                        "gasPrice": w3.eth.gas_price,
                    })
                    signed = account.sign_transaction(tx)
                    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
                    status = "ok" if receipt.status == 1 else "reverted"
                    print(f"Block {block_num} execute tx {tx_hash.hex()} -> {status}")
                except Exception as e:
                    print(f"Block {block_num} execute failed: {e}")
            last_block = current
        time.sleep(1.0)


if __name__ == "__main__":
    main()
