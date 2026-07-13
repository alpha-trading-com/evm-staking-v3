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

from evm import connect_w3, resolve_contract_address, get_contract


def main():
    try:
        w3 = connect_w3()
    except (RuntimeError, ValueError) as e:
        sys.exit(str(e))

    contract_address = resolve_contract_address()
    contract = get_contract(w3, contract_address)

    contract_account_id32 = contract.functions.contractAccountId32().call()
    stake_info_base_fee_rao, limit_price_base_fee_rao = contract.functions.getBaseFeesRao().call()

    print(f"Contract: {contract_address}")
    print(f"contractAccountId32:  {contract_account_id32.hex()}")
    print(f"stakeInfoBaseFeeRao:  {stake_info_base_fee_rao}")
    print(f"limitPriceBaseFeeRao: {limit_price_base_fee_rao}")


if __name__ == "__main__":
    main()
