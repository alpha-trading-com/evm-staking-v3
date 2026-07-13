#!/usr/bin/env python3
"""
Read StakeWrap config: contractAccountId32 and base fees (stakeInfoBaseFeeRao, limitPriceBaseFeeRao).

No private key needed (view calls only).

  python scripts/read_contract_config.py
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from web3 import Web3

from evm import get_contract, load_deployment


def main():
    rpc_url = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        sys.exit(f"Failed to connect to RPC: {rpc_url}")

    deployment = load_deployment()
    contract_address = Web3.to_checksum_address(deployment["contract_address"])
    contract = get_contract(w3, contract_address)

    contract_account_id32 = contract.functions.contractAccountId32().call()
    stake_info_base_fee_rao, limit_price_base_fee_rao = contract.functions.getBaseFeesRao().call()

    print(f"Contract: {contract_address}")
    print(f"contractAccountId32:  {contract_account_id32.hex()}")
    print(f"stakeInfoBaseFeeRao:  {stake_info_base_fee_rao}")
    print(f"limitPriceBaseFeeRao: {limit_price_base_fee_rao}")


if __name__ == "__main__":
    main()
