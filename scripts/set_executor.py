#!/usr/bin/env python3
"""
Set the contract's executor address (owner only). The executor wallet can call execute()
so the owner can use the same chain for stake/unstake/withdraw without nonce conflict.

Requires: PRIVATE_KEY (owner), RPC_URL.

  export EXECUTOR_PRIVATE_KEY=0x...  # optional: separate executor EOA; address is derived from this key
  # If EXECUTOR_PRIVATE_KEY is unset, the script sets executor to the owner address (same as PRIVATE_KEY).

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

from evm import connect_w3, load_account, resolve_contract_address, get_contract, set_executor


def main():
    parser = argparse.ArgumentParser(description="Set or clear contract executor (owner only)")
    parser.add_argument("--clear", action="store_true", help="Set executor to zero")
    args = parser.parse_args()

    executor_key = os.getenv("EXECUTOR_PRIVATE_KEY")

    try:
        w3 = connect_w3()
        account = load_account()  # PRIVATE_KEY (owner)
    except (RuntimeError, ValueError) as e:
        sys.exit(str(e))

    contract_address = resolve_contract_address()
    contract = get_contract(w3, contract_address)

    if args.clear:
        addr = "0x0000000000000000000000000000000000000000"
        print("Clearing executor (only owner can call execute)...")
    elif executor_key:
        addr = Account.from_key(executor_key).address
        print(f"Setting executor to {addr} (from EXECUTOR_PRIVATE_KEY)...")
    else:
        addr = account.address
        print(f"Setting executor to owner address {addr} (EXECUTOR_PRIVATE_KEY unset)...")

    try:
        set_executor(w3, account, contract_address, addr, contract=contract)
    except (PermissionError, RuntimeError) as e:
        sys.exit(str(e))
    print("Done. Executor cleared." if args.clear else "Done. Executor set.")


if __name__ == "__main__":
    main()
