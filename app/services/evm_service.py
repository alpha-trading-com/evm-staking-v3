"""Web3/contract helpers. Re-exports from app.globals; receipt and run_quiet stay here."""
import io
import contextlib
from typing import Any

from app.globals import clear_w3_cache, get_contract, get_w3_account_contract


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
