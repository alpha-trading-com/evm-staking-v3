"""
EVM / Bittensor address conversion helpers.

- H160 (EVM address) <-> AccountId32 (32 bytes) via Blake2b-256(b"evm:" || h160).
- AccountId32 <-> SS58 (Bittensor/Substrate format).
"""

import hashlib
# Bittensor / generic Substrate prefix (chain_spec uses 42)
SS58_PREFIX = 42
SS58_CHECKSUM_LEN = 2
BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
EVM_PREFIX = b"evm:"

try:
    import bittensor as bt
    _BT_AVAILABLE = True
except ImportError:
    _BT_AVAILABLE = False


def _blake2b_256(data: bytes) -> bytes:
    return hashlib.blake2b(data, digest_size=32).digest()


def _base58_encode(data: bytes) -> str:
    leading_zeros = len(data) - len(data.lstrip(b"\x00"))
    num = int.from_bytes(data, "big")
    if num == 0:
        return BASE58_ALPHABET[0] * max(1, leading_zeros)
    result = []
    while num:
        num, r = divmod(num, 58)
        result.append(BASE58_ALPHABET[r])
    return BASE58_ALPHABET[0] * leading_zeros + "".join(reversed(result))


def h160_to_account_id(h160_hex: str) -> bytes:
    """Convert Ethereum address (20 bytes) to 32-byte AccountId32: Blake2b-256(b'evm:' + h160)."""
    raw = h160_hex.strip()
    if raw.startswith("0x") or raw.startswith("0X"):
        raw = raw[2:]
    if len(raw) != 40:
        raise ValueError("Ethereum address must be 40 hex chars (with or without 0x)")
    addr_bytes = bytes.fromhex(raw)
    if len(addr_bytes) != 20:
        raise ValueError("Address must decode to 20 bytes")
    return _blake2b_256(EVM_PREFIX + addr_bytes)


def account_id_to_ss58(account_id: bytes, prefix: int = SS58_PREFIX) -> str:
    """Encode 32-byte AccountId to SS58 with given prefix."""
    if len(account_id) != 32:
        raise ValueError("account_id must be 32 bytes")
    payload = bytes([prefix]) + account_id
    checksum = hashlib.blake2b(b"SS58PRE" + payload, digest_size=64).digest()
    return _base58_encode(payload + checksum[:SS58_CHECKSUM_LEN])


def h160_to_ss58(h160_hex: str, ss58_prefix: int = SS58_PREFIX) -> str:
    """Convert Ethereum H160 address to Bittensor SS58 address."""
    account_id = h160_to_account_id(h160_hex)
    return account_id_to_ss58(account_id, ss58_prefix)


def contract_address_bytes32(contract_address_hex: str) -> bytes:
    """EVM contract address -> 32-byte AccountId32 (for execute() etc.)."""
    return h160_to_account_id(contract_address_hex)


def ss58_to_bytes32(ss58_address: str) -> bytes:
    """
    Convert SS58 address to bytes32.
    Uses bittensor if available, else manual base58 decode.
    """
    try:
        if _BT_AVAILABLE:
            try:
                decoded_bytes = bt.utils.ss58_address_to_bytes(ss58_address)
                if len(decoded_bytes) == 32:
                    return decoded_bytes
                if len(decoded_bytes) < 32:
                    return decoded_bytes + b"\x00" * (32 - len(decoded_bytes))
                return decoded_bytes[:32]
            except Exception:
                pass
        import base58
        decoded = base58.b58decode(ss58_address)
        if len(decoded) < 2:
            raise ValueError("Invalid SS58 address: too short")
        if len(decoded) == 35:
            address_bytes = decoded[1:33]
        elif len(decoded) == 34:
            address_bytes = decoded[1:33]
        elif len(decoded) == 33:
            address_bytes = decoded[1:]
        elif len(decoded) > 35:
            prefix_len = 1 if decoded[0] < 64 else 2
            address_bytes = decoded[prefix_len : prefix_len + 32]
        else:
            raise ValueError(f"Unexpected SS58 decoded length: {len(decoded)}")
        if len(address_bytes) < 32:
            address_bytes = address_bytes + b"\x00" * (32 - len(address_bytes))
        else:
            address_bytes = address_bytes[:32]
        return address_bytes
    except Exception as e:
        raise ValueError(f"Failed to decode SS58 address '{ss58_address}': {e}") from e
