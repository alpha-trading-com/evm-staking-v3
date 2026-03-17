#!/usr/bin/env python3
"""
Convert an Ethereum H160 address to a Bittensor SS58 address.

Matches the Bittensor/snow-address-converter and evm-bittensor logic.
Implementation lives in evm.address.

Usage:
    python scripts/address_convert.py 0x742d35Cc6634C0532925a3b844Bc454e4438f44e
    python scripts/address_convert.py 742d35Cc6634C0532925a3b844Bc454e4438f44e
"""

import argparse
import os
import sys

# Ensure project root is on path when run as script
_script_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_script_dir)
if _root not in sys.path:
    sys.path.insert(0, _root)

from evm import SS58_PREFIX, h160_to_ss58


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert Ethereum H160 to Bittensor SS58 (matches snow-address-converter / evm-bittensor)."
    )
    parser.add_argument("address", help="Ethereum address (0x...) to convert")
    parser.add_argument("--prefix", type=int, default=SS58_PREFIX, help=f"SS58 prefix (default: {SS58_PREFIX})")
    args = parser.parse_args()

    try:
        ss58 = h160_to_ss58(args.address, args.prefix)
        print(f"Ethereum: {args.address}")
        print(f"SS58:     {ss58}")
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
