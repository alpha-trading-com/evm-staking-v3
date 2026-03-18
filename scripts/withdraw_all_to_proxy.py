#!/usr/bin/env python3
"""
Withdraw the full contract balance (TAO) to the contract's WITHDRAW_COLDKEY.

Calls withdraw(contract_balance) as the contract owner. The contract sends TAO
to its hardcoded WITHDRAW_COLDKEY via the balance transfer precompile.
Requires PRIVATE_KEY in .env (must be the contract owner).

Usage:
  python3 scripts/withdraw_all_to_proxy.py
  python3 scripts/withdraw_all_to_proxy.py --contract 0xYourContractAddress
"""

import argparse
import json
import os
import sys

# Project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except ImportError:
    pass

from web3 import Web3
from eth_account import Account


# Minimal ABI for owner() and withdraw(uint256)
ABI = [
    {"inputs": [], "name": "owner", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "withdraw", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
]


def main():
    parser = argparse.ArgumentParser(description="Withdraw full contract balance to WITHDRAW_COLDKEY.")
    parser.add_argument("--contract", type=str, help="Contract address (default: from deployment.json)")
    args = parser.parse_args()

    rpc_url = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        print("ERROR: Set PRIVATE_KEY in .env", file=sys.stderr)
        sys.exit(1)

    contract_address = args.contract or os.getenv("CONTRACT_ADDRESS")
    if not contract_address:
        path = os.path.join(PROJECT_ROOT, "deployment.json")
        if not os.path.isfile(path):
            print("ERROR: deployment.json not found and CONTRACT_ADDRESS not set", file=sys.stderr)
            sys.exit(1)
        with open(path) as f:
            deployment = json.load(f)
        contract_address = deployment["contract_address"]

    contract_address = Web3.to_checksum_address(contract_address)
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print(f"ERROR: Cannot connect to {rpc_url}", file=sys.stderr)
        sys.exit(1)

    account = Account.from_key(private_key)
    contract = w3.eth.contract(address=contract_address, abi=ABI)

    owner = contract.functions.owner().call()
    if owner.lower() != account.address.lower():
        print(f"ERROR: You are not the contract owner. Owner: {owner}", file=sys.stderr)
        sys.exit(1)

    balance_wei = w3.eth.get_balance(contract_address)
    if balance_wei == 0:
        print("Contract balance is 0. Nothing to withdraw.")
        return 0

    balance_tao = float(Web3.from_wei(balance_wei, "ether"))
    print(f"Contract balance: {balance_tao} TAO ({balance_wei} wei)")
    print("Withdrawing full amount to WITHDRAW_COLDKEY...")

    tx = contract.functions.withdraw(balance_wei).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 150000,
        "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Transaction hash: {tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Block: {receipt.blockNumber}")

    if receipt.status != 1:
        print("ERROR: Transaction failed.", file=sys.stderr)
        sys.exit(1)

    print("Withdraw succeeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
