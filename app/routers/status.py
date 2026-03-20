"""Contract/account status API."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from web3 import Web3

from app.auth import get_current_username
from app.services.evm_service import get_w3_account_contract

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/status")
async def api_status(_: str = Depends(get_current_username)):
    """Contract address, account, owner, balance, chain_id."""
    try:
        w3, account, contract_address, contract = get_w3_account_contract()
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
    balance_wei = w3.eth.get_balance(contract_address)
    balance_tao = float(Web3.from_wei(balance_wei, "ether"))
    try:
        owner = contract.functions.owner().call()
    except Exception:
        owner = None
    return {
        "ok": True,
        "contract": contract_address,
        "account": account.address,
        "owner": owner,
        "is_owner": bool(owner and owner.lower() == account.address.lower()),
        "balance_wei": str(balance_wei),
        "balance_tao": balance_tao,
        "chain_id": w3.eth.chain_id,
    }
