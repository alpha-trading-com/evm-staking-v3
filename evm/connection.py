"""
Shared Web3 connection / account / contract bootstrap used by both the uvicorn app
and the CLI scripts so the "connect + load signer + resolve contract" boilerplate
lives in one place.
"""

import os
from typing import Any, Optional, Tuple

from web3 import Web3
from eth_account import Account

from evm.contract import load_deployment_info
from evm.stake_wrap import get_contract

DEFAULT_RPC_URL = "https://test.finney.opentensor.ai/"


def connect_w3(rpc_url: Optional[str] = None) -> Web3:
    """Return a connected Web3 for an HTTP(S) or WS(S) RPC. Env RPC_URL is the default."""
    rpc_url = rpc_url or os.getenv("RPC_URL", DEFAULT_RPC_URL)
    if rpc_url.startswith(("ws://", "wss://")):
        provider = Web3.LegacyWebSocketProvider(rpc_url)
    elif rpc_url.startswith(("http://", "https://")):
        provider = Web3.HTTPProvider(rpc_url)
    else:
        raise ValueError(f"Unsupported RPC URL scheme: {rpc_url}")
    w3 = Web3(provider)
    if not w3.is_connected():
        raise RuntimeError(f"Failed to connect to {rpc_url}")
    return w3


def load_account(private_key: Optional[str] = None) -> Account:
    """Load the signing account from `private_key` or the PRIVATE_KEY env var."""
    private_key = private_key or os.getenv("PRIVATE_KEY")
    if not private_key:
        raise RuntimeError("PRIVATE_KEY is required")
    return Account.from_key(private_key)


def resolve_contract_address(override: Optional[str] = None) -> str:
    """Resolve the StakeWrap address: explicit override, then CONTRACT_ADDRESS env, then deployment.json."""
    addr = override or os.getenv("CONTRACT_ADDRESS")
    if not addr:
        addr = load_deployment_info()["contract_address"]
    return Web3.to_checksum_address(addr)


def get_w3_account_contract(
    rpc_url: Optional[str] = None,
    private_key: Optional[str] = None,
    contract_address: Optional[str] = None,
) -> Tuple[Web3, Account, str, Any]:
    """One-shot bootstrap: (w3, account, contract_address, contract). Signer required."""
    w3 = connect_w3(rpc_url)
    account = load_account(private_key)
    address = resolve_contract_address(contract_address)
    contract = get_contract(w3, address)
    return w3, account, address, contract
