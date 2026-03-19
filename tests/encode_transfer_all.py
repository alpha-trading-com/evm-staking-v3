#!/usr/bin/env python3
"""
Encode balances.transferAll(dest, keepAlive) as SCALE bytes for use with
pullFromProxiedAccount --encoded-call.

dest = destination of the transfer (this contract's SS58 address).

Example (bash):
  ENCODED=$(python scripts/encode_transfer_all.py --dest 5HCT4AarReToT1BKyLtJXJfSLs4zRS7dENnZ7iysqrqxXyV7)
  python scripts/interact.py pullFromProxiedAccount --proxied-account <proxied_ss58> --encoded-call "$ENCODED"

With keepAlive=false (as in Polkadot.js "No"):
  python scripts/encode_transfer_all.py --dest 5HCT4... --no-keep-alive
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


def _ss58_to_account_id(ss58_address):
    """Convert SS58 address string to 32-byte account ID."""
    s = ss58_address.strip()
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
        raise ValueError(f"Invalid SS58 address: {e}") from e


# Contract constants (StakeWrap.sol) - used to verify alignment with metadata
BALANCES_PALLET_INDEX = 5
TRANSFER_ALL_CALL_INDEX = 4


def encode_transfer_all(dest, keep_alive=True, rpc_url=None):
    """
    Encode Balances::transfer_all(dest, keep_alive) as SCALE bytes (hex).

    Uses chain metadata (compose_call) so indices are correct for the connected chain.
    Optionally verifies that the first two bytes match StakeWrap.sol constants (5, 4).

    dest: SS58 address string for the destination account (e.g. contract's SS58).
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
    account_id = _ss58_to_account_id(dest)

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
    # Encoded Call is in call.data (ScaleBytes); .data attribute is bytearray
    scale_data = call.data
    raw = getattr(scale_data, "data", None)
    if raw is None or not isinstance(raw, (bytes, bytearray)):
        raise RuntimeError("Could not get bytes from composed call (ScaleBytes format may have changed)")

    # Verify alignment with StakeWrap.sol _encodeTransferAll (pallet=5, call=4, then MultiAddress::Id + 32 bytes + bool)
    if len(raw) >= 2:
        if raw[0] != BALANCES_PALLET_INDEX or raw[1] != TRANSFER_ALL_CALL_INDEX:
            import warnings
            warnings.warn(
                f"Chain metadata has Balances::transfer_all as [{raw[0]}, {raw[1]}]; "
                f"StakeWrap.sol uses [{BALANCES_PALLET_INDEX}, {TRANSFER_ALL_CALL_INDEX}]. "
                "Contract and script may be misaligned for this chain.",
                UserWarning,
                stacklevel=2,
            )
    if len(raw) != 36:
        import warnings
        warnings.warn(
            f"Composed call length is {len(raw)} bytes; StakeWrap.sol expects 36. "
            "Layout may differ (e.g. compact indices).",
            UserWarning,
            stacklevel=2,
        )

    return raw.hex()


def main():
    parser = argparse.ArgumentParser(
        description="Encode balances.transferAll(dest, keepAlive) for pullFromProxiedAccount --encoded-call"
    )
    parser.add_argument(
        "--dest",
        required=True,
        help="Destination account: SS58 address string (e.g. contract's SS58)",
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
