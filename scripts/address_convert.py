#!/usr/bin/env python3
"""
Convert an Ethereum H160 address to a Bittensor SS58 address.

Matches the Bittensor/snow-address-converter and evm-bittensor logic:
  combined = b"evm:" + address_bytes (20 bytes)
  AccountId32 = Blake2b-256(combined)
  SS58 encode with network prefix 42.

Usage:
    python address_convert.py 0x742d35Cc6634C0532925a3b844Bc454e4438f44e
    python address_convert.py 742d35Cc6634C0532925a3b844Bc454e4438f44e

Uses only the standard library (hashlib). No extra deps.
"""

import argparse
import hashlib
import sys

# SS58 checksum length for 32-byte AccountId
SS58_CHECKSUM_LEN = 2
# Bittensor / generic Substrate prefix (chain_spec uses 42)
SS58_PREFIX = 42

# Base58 alphabet (no 0, O, I, l)
BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def blake2b_256(data: bytes) -> bytes:
    return hashlib.blake2b(data, digest_size=32).digest()


def base58_encode(data: bytes) -> str:
    """Encode bytes to Base58 (no 0OIl)."""
    leading_zeros = len(data) - len(data.lstrip(b"\x00"))
    num = int.from_bytes(data, "big")
    if num == 0:
        return BASE58_ALPHABET[0] * max(1, leading_zeros)
    result = []
    while num:
        num, r = divmod(num, 58)
        result.append(BASE58_ALPHABET[r])
    return BASE58_ALPHABET[0] * leading_zeros + "".join(reversed(result))


def ss58_encode(account_id: bytes, prefix: int = SS58_PREFIX) -> str:
    """Encode 32-byte AccountId to SS58 with given prefix."""
    if len(account_id) != 32:
        raise ValueError("account_id must be 32 bytes")
    payload = bytes([prefix]) + account_id
    checksum = hashlib.blake2b(b"SS58PRE" + payload, digest_size=64).digest()
    return base58_encode(payload + checksum[:SS58_CHECKSUM_LEN])


# Prefix used by Bittensor/snow converter and evm-bittensor (hash is of "evm:" + address)
EVM_PREFIX = b"evm:"


def h160_to_account_id(h160_hex: str) -> bytes:
    """Convert Ethereum address to 32-byte AccountId: Blake2b-256(b"evm:" + address)."""
    raw = h160_hex.strip()
    if raw.startswith("0x") or raw.startswith("0X"):
        raw = raw[2:]
    if len(raw) != 40:
        raise ValueError("Ethereum address must be 40 hex chars (with or without 0x)")
    try:
        addr_bytes = bytes.fromhex(raw)
    except Exception as e:
        raise ValueError(f"Invalid hex: {e}") from e
    if len(addr_bytes) != 20:
        raise ValueError("Address must decode to 20 bytes")
    combined = EVM_PREFIX + addr_bytes
    return blake2b_256(combined)


def h160_to_ss58(h160_hex: str, ss58_prefix: int = SS58_PREFIX) -> str:
    """Convert Ethereum H160 address to Bittensor SS58 address."""
    account_id = h160_to_account_id(h160_hex)
    return ss58_encode(account_id, ss58_prefix)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert Ethereum H160 to Bittensor SS58 (matches snow-address-converter / evm-bittensor)."
    )
    parser.add_argument(
        "address",
        help="Ethereum address (0x...) to convert",
    )
    parser.add_argument(
        "--prefix",
        type=int,
        default=SS58_PREFIX,
        help=f"SS58 prefix (default: {SS58_PREFIX} for Bittensor)",
    )
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
