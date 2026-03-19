#!/usr/bin/env python3
"""
Set the contract's executor address (owner only). The executor wallet can call execute()
so the owner can use the same chain for stake/unstake/withdraw without nonce conflict.

Requires: PRIVATE_KEY (owner), RPC_URL. Set either EXECUTOR_ADDRESS or EXECUTOR_PRIVATE_KEY.

  export EXECUTOR_ADDRESS=0x...   # executor wallet address
  # or
  export EXECUTOR_PRIVATE_KEY=0x...  # address will be derived

  python scripts/set_executor.py
  python scripts/set_executor.py --clear   # set executor to zero (only owner can execute)
"""

import argparse
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from eth_account import Account
from web3 import Web3

from evm import get_contract, load_deployment


def main():
    parser = argparse.ArgumentParser(description="Set or clear contract executor (owner only)")
    parser.add_argument("--clear", action="store_true", help="Set executor to zero")
    args = parser.parse_args()

    rpc_url = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
    owner_key = os.getenv("PRIVATE_KEY")
    executor_address = os.getenv("EXECUTOR_ADDRESS")
    executor_key = os.getenv("EXECUTOR_PRIVATE_KEY")

    if not owner_key:
        sys.exit("PRIVATE_KEY (owner) is required")
    if not args.clear and not executor_address and not executor_key:
        sys.exit("Set EXECUTOR_ADDRESS or EXECUTOR_PRIVATE_KEY (or use --clear)")

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        sys.exit(f"Failed to connect to RPC: {rpc_url}")

    deployment = load_deployment()
    contract_address = Web3.to_checksum_address(deployment["contract_address"])
    contract = get_contract(w3, contract_address)
    account = Account.from_key(owner_key)

    owner = contract.functions.owner().call()
    if owner.lower() != account.address.lower():
        sys.exit(f"PRIVATE_KEY is not contract owner (owner={owner})")

    if args.clear:
        addr = "0x0000000000000000000000000000000000000000"
        print("Clearing executor (only owner can call execute)...")
    else:
        if executor_address:
            addr = Web3.to_checksum_address(executor_address)
        else:
            addr = Account.from_key(executor_key).address
        print(f"Setting executor to {addr}...")

    tx = contract.functions.setExecutor(Web3.to_checksum_address(addr)).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 100_000,
        "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Tx: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt["status"] != 1:
        sys.exit("Transaction reverted")
    print("Done. Executor set." if not args.clear else "Done. Executor cleared.")


if __name__ == "__main__":
    main()
