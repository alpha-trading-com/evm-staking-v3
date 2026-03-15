#!/usr/bin/env python3
"""
Encode balances.transferAll(dest, keepAlive) as SCALE bytes for use with
pullFromProxiedAccount --encoded-call.

dest = destination of the transfer (this contract's Substrate account ID).
Use the contract's 32-byte account ID (hex) or its SS58 if the chain maps it.

Example (bash):
  ENCODED=$(python scripts/encode_transfer_all.py --dest 0x<contract_32byte_account_id>)
  python scripts/interact.py pullFromProxiedAccount --proxied-account <proxied_ss58> --encoded-call "$ENCODED"

With keepAlive=false (as in Polkadot.js "No"):
  python scripts/encode_transfer_all.py --dest 0x... --no-keep-alive
"""

import argparse
import os
import sys

# Add project root for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _dest_to_account_id(dest):
    """Convert dest (SS58 or 0x hex 32 bytes) to 32-byte account ID."""
    if isinstance(dest, bytes) and len(dest) == 32:
        return dest
    s = dest.strip()
    if s.startswith("0x") or all(c in "0123456789abcdefABCDEF" for c in s.replace("0x", "")):
        b = bytes.fromhex(s.replace("0x", ""))
        if len(b) != 32:
            raise ValueError("dest hex must be 32 bytes (64 hex characters)")
        return b
    # SS58
    try:
        import bittensor as bt
        return bytes(bt.utils.ss58_address_to_bytes(s))
    except Exception:
        pass
    try:
        import base58
        decoded = base58.b58decode(s)
        if len(decoded) >= 33:
            return bytes(decoded[1:33])  # 1 byte prefix + 32 bytes account
        raise ValueError("SS58 decoded length too short")
    except Exception as e:
        raise ValueError(f"dest must be SS58 or 32-byte hex: {e}") from e


def encode_transfer_all(dest, keep_alive=True, rpc_url=None):
    """
    Encode Balances::transfer_all(dest, keep_alive) as SCALE bytes (hex).

    dest: SS58 address or 32-byte hex (0x...) for the destination account (e.g. contract's account ID).
    keep_alive: True = keep sender alive (default); False = allow reaping.
    rpc_url: Optional. If not set, uses RPC_URL env or Bittensor finney network.
    """
    from substrateinterface import SubstrateInterface

    rpc = rpc_url or os.getenv("RPC_URL")
    if not rpc:
        # Bittensor finney; substrate-interface expects ws for some calls
        rpc = "wss://entrypoint-finney.opentensor.ai:443"
    if rpc.startswith("https://"):
        rpc = rpc.replace("https://", "wss://", 1).rstrip("/") if "wss://" not in rpc else rpc
    if not rpc.startswith("wss://"):
        rpc = "wss://" + rpc

    substrate = SubstrateInterface(url=rpc)
    account_id = _dest_to_account_id(dest)

    # MultiAddress::Id(AccountId) - dest as 0x-prefixed hex (32 bytes)
    call_params = {
        "dest": {"Id": "0x" + account_id.hex()},
        "keep_alive": keep_alive,
    }

    call = substrate.compose_call(
        call_module="Balances",
        call_function="transfer_all",
        call_params=call_params,
    )
    # Encoded Call is in call.data (ScaleBytes)
    raw = bytes(call.data)
    return raw.hex()


def main():
    parser = argparse.ArgumentParser(
        description="Encode balances.transferAll(dest, keepAlive) for pullFromProxiedAccount --encoded-call"
    )
    parser.add_argument(
        "--dest",
        required=True,
        help="Destination account: SS58 address or 32-byte hex (0x...)",
    )
    parser.add_argument(
        "--no-keep-alive",
        action="store_true",
        help="Set keepAlive to false (default is true)",
    )
    parser.add_argument(
        "--rpc",
        default=os.getenv("RPC_URL"),
        help="Substrate RPC URL (default: RPC_URL env or finney)",
    )
    args = parser.parse_args()

    keep_alive = not args.no_keep_alive
    try:
        hex_encoded = encode_transfer_all(args.dest, keep_alive=keep_alive, rpc_url=args.rpc)
        print(hex_encoded)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
