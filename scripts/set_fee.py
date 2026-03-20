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

from web3 import Web3

from evm import get_contract, load_deployment
from bt_utils.constants import STAKE_INFO_BASE_FEE_RAO as DEFAULT_STAKE_INFO_RAO
from bt_utils.constants import LIMIT_PRICE_BASE_FEE_RAO as DEFAULT_LIMIT_PRICE_RAO


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

    owner_key = os.getenv("PRIVATE_KEY")
    if not owner_key:
        sys.exit("PRIVATE_KEY (owner) is required")

    rpc_url = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        sys.exit(f"Failed to connect to RPC: {rpc_url}")

    from eth_account import Account
    account = Account.from_key(owner_key)

    deployment = load_deployment()
    contract_address = Web3.to_checksum_address(deployment["contract_address"])
    contract = get_contract(w3, contract_address)

    owner = contract.functions.owner().call()
    if owner.lower() != account.address.lower():
        sys.exit(f"PRIVATE_KEY is not contract owner (owner={owner})")

    print(f"Setting base fees: stakeInfo={stake_info_rao} rao, limitPrice={limit_price_rao} rao...")
    tx = contract.functions.setBaseFeesRao(stake_info_rao, limit_price_rao).build_transaction({
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
    print("Done. Base fees set.")


if __name__ == "__main__":
    main()
