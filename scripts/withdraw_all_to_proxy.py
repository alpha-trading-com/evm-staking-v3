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

from evm import connect_w3, load_account, resolve_contract_address, get_contract, is_owner, withdraw


def main():
    parser = argparse.ArgumentParser(description="Withdraw full contract balance to WITHDRAW_COLDKEY.")
    parser.add_argument("--contract", type=str, help="Contract address (default: from deployment.json)")
    args = parser.parse_args()

    try:
        w3 = connect_w3()
        account = load_account()
    except (RuntimeError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    contract_address = resolve_contract_address(args.contract)
    contract = get_contract(w3, contract_address)

    if not is_owner(contract, account):
        owner = contract.functions.owner().call()
        print(f"ERROR: You are not the contract owner. Owner: {owner}", file=sys.stderr)
        sys.exit(1)

    balance_wei = w3.eth.get_balance(contract_address)
    if balance_wei == 0:
        print("Contract balance is 0. Nothing to withdraw.")
        return 0

    print("Withdrawing full contract balance to WITHDRAW_COLDKEY...")
    receipt = withdraw(w3, account, contract_address, balance_wei, contract=contract)
    if receipt is None or receipt["status"] != 1:
        print("ERROR: Transaction failed.", file=sys.stderr)
        sys.exit(1)

    print("Withdraw succeeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
