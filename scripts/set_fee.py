#!/usr/bin/env python3
"""
Set the contract's base fees in rao (owner only). Used by execute() for stake-info and limit-price delegates.

Requires: PRIVATE_KEY (owner), RPC_URL.

  python scripts/set_fee.py
  python scripts/set_fee.py --stake-info 105612 --limit-price 105611
  export STAKE_INFO_BASE_FEE_RAO=105612 LIMIT_PRICE_BASE_FEE_RAO=105611; python scripts/set_fee.py

If --stake-info / --limit-price are not set, uses env STAKE_INFO_BASE_FEE_RAO and LIMIT_PRICE_BASE_FEE_RAO,
or falls back to bt_utils.constants values.
"""

import argparse
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from evm import connect_w3, load_account, resolve_contract_address, get_contract, set_base_fees_rao
from bt_utils.config import STAKE_INFO_BASE_FEE_RAO as DEFAULT_STAKE_INFO_RAO
from bt_utils.config import LIMIT_PRICE_BASE_FEE_RAO as DEFAULT_LIMIT_PRICE_RAO


def main():
    parser = argparse.ArgumentParser(description="Set contract base fees in rao (owner only)")
    parser.add_argument("--stake-info", type=int, default=None, metavar="RAO", help="Stake-info base fee (rao)")
    parser.add_argument("--limit-price", type=int, default=None, metavar="RAO", help="Limit-price base fee (rao)")
    args = parser.parse_args()

    stake_info_rao = args.stake_info
    if stake_info_rao is None:
        stake_info_rao = int(os.getenv("STAKE_INFO_BASE_FEE_RAO", str(DEFAULT_STAKE_INFO_RAO)))
    limit_price_rao = args.limit_price
    if limit_price_rao is None:
        limit_price_rao = int(os.getenv("LIMIT_PRICE_BASE_FEE_RAO", str(DEFAULT_LIMIT_PRICE_RAO)))

    try:
        w3 = connect_w3()
        account = load_account()  # PRIVATE_KEY (owner)
    except (RuntimeError, ValueError) as e:
        sys.exit(str(e))

    contract_address = resolve_contract_address()
    contract = get_contract(w3, contract_address)

    try:
        set_base_fees_rao(w3, account, contract_address, stake_info_rao, limit_price_rao, contract=contract)
    except (PermissionError, RuntimeError) as e:
        sys.exit(str(e))
    print("Done. Base fees set.")


if __name__ == "__main__":
    main()
