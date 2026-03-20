"""Web3 connection and contract helpers. Caches connection per process."""
import io
import os
import contextlib
import threading
from typing import Any

from web3 import Web3
from eth_account import Account

from evm import (
    get_contract as evm_get_contract,
    get_stake_wrap_abi,
    load_deployment_info,
    CONTRACT_ABI,
)

_w3_cache: tuple[Web3, Account, str, Any] | None = None
_w3_cache_lock = threading.Lock()


def clear_w3_cache() -> None:
    """Drop cached Web3 connection so next request opens a new one."""
    global _w3_cache
    with _w3_cache_lock:
        _w3_cache = None


def _make_w3_connection(rpc_url: str) -> Web3:
    """Create Web3 for HTTP or WebSocket RPC."""
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


def get_w3_account_contract() -> tuple[Web3, Account, str, Any]:
    """Return (w3, account, contract_address, contract), reusing cached connection and contract when still connected."""
    global _w3_cache
    with _w3_cache_lock:
        if _w3_cache is not None:
            w3, account, contract_address, contract = _w3_cache
            try:
                if w3.is_connected():
                    return w3, account, contract_address, contract
            except Exception:
                pass
            _w3_cache = None

        rpc_url = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
        private_key = os.getenv("PRIVATE_KEY")
        if not private_key:
            raise RuntimeError("PRIVATE_KEY is required")
        w3 = _make_w3_connection(rpc_url)
        account = Account.from_key(private_key)
        info = load_deployment_info()
        contract_address = Web3.to_checksum_address(info["contract_address"])
        abi = get_stake_wrap_abi() or CONTRACT_ABI
        contract = evm_get_contract(w3, contract_address, abi=abi)
        _w3_cache = (w3, account, contract_address, contract)
        return w3, account, contract_address, contract


def get_contract(w3: Web3, contract_address: str) -> Any:
    """StakeWrap contract instance. Uses cached instance when (w3, contract_address) matches cache; ABI is cached."""
    with _w3_cache_lock:
        if _w3_cache is not None:
            cached_w3, _, cached_addr, contract = _w3_cache
            if cached_w3 is w3 and cached_addr == contract_address:
                return contract
    abi = get_stake_wrap_abi() or CONTRACT_ABI
    return evm_get_contract(w3, contract_address, abi=abi)


def receipt_to_dict(receipt: dict) -> dict:
    """Normalize tx receipt for JSON response."""
    h = receipt["transactionHash"]
    return {
        "transactionHash": h.hex() if hasattr(h, "hex") else str(h),
        "blockNumber": receipt["blockNumber"],
        "status": receipt["status"],
    }


def run_quiet(fn: callable, *args: Any, **kwargs: Any) -> Any:
    """Run function with stdout redirected to avoid polluting API responses."""
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)
