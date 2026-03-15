#!/usr/bin/env python3
"""
Convert Ethereum addresses to SS58 format (used by Bittensor/Substrate).
"""

import argparse
import base58
import hashlib


def ss58_encode(address_bytes, prefix=42):
    """
    Encode bytes to SS58 format.
    
    Args:
        address_bytes: The address as bytes (20 bytes for Ethereum address)
        prefix: SS58 prefix (42 for Substrate/Bittensor)
    
    Returns:
        SS58 encoded address string
    """
    # Add prefix byte(s)
    if prefix < 64:
        prefix_bytes = bytes([prefix])
    elif prefix < 16384:
        prefix_bytes = bytes([
            ((prefix & 0xfc) >> 2) | 0x40,
            ((prefix & 0x03) << 6) | ((prefix >> 8) & 0x3f)
        ])
    else:
        raise ValueError("Prefix too large")
    
    # Combine prefix and address
    payload = prefix_bytes + address_bytes
    
    # Calculate checksum (blake2b-512, take first 2 bytes)
    checksum = hashlib.blake2b(
        b'SS58PRE' + payload,
        digest_size=64
    ).digest()[:2]
    
    # Combine payload and checksum
    full_payload = payload + checksum
    
    # Base58 encode
    return base58.b58encode(full_payload).decode('utf-8')


def eth_to_ss58(eth_address, prefix=42):
    """
    Convert Ethereum address (0x...) to SS58 format.
    
    Args:
        eth_address: Ethereum address as hex string (with or without 0x)
        prefix: SS58 prefix (42 for Substrate/Bittensor)
    
    Returns:
        SS58 encoded address string
    """
    # Remove 0x prefix if present
    if eth_address.startswith('0x') or eth_address.startswith('0X'):
        eth_address = eth_address[2:]
    
    # Convert hex string to bytes
    try:
        address_bytes = bytes.fromhex(eth_address)
    except ValueError as e:
        raise ValueError(f"Invalid hex address: {eth_address}") from e
    
    # Ethereum addresses are 20 bytes
    if len(address_bytes) != 20:
        raise ValueError(f"Ethereum address must be 20 bytes, got {len(address_bytes)}")
    
    # Encode to SS58
    return ss58_encode(address_bytes, prefix)


def main():
    parser = argparse.ArgumentParser(
        description='Convert Ethereum address to SS58 format'
    )
    parser.add_argument(
        'address',
        help='Ethereum address (0x...) to convert'
    )
    parser.add_argument(
        '--prefix',
        type=int,
        default=42,
        help='SS58 prefix (default: 42 for Substrate/Bittensor)'
    )
    
    args = parser.parse_args()
    
    try:
        ss58_address = eth_to_ss58(args.address, args.prefix)
        print(f"Ethereum: {args.address}")
        print(f"SS58:     {ss58_address}")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())



