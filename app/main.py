"""
FastAPI app for StakeWrap: stake, stake limit, unstake, unstake limit, transfer stake, move stake, withdraw.

Run from repo root:
  uvicorn app.main:app --host 0.0.0.0 --port 8000

Or: ./run_server.sh
"""
import io
import os
import sys
import contextlib
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
os.chdir(_REPO_ROOT)

import bittensor as bt

from dotenv import load_dotenv

load_dotenv(_REPO_ROOT / ".env")

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from web3 import Web3
from eth_account import Account

from app.auth import get_current_username

from scripts.interact import (
    stake,
    stake_limit,
    remove_stake,
    remove_stake_limit,
    transfer_stake,
    move_stake,
    withdraw,
    load_deployment_info,
    get_contract,
)

# Import tolerance calculation utilities
from utils.tolerance import calculate_stake_limit_price, calculate_unstake_limit_price

app = FastAPI(title="StakeWrap Control", version="1.0.0")
templates = Jinja2Templates(directory=str(_REPO_ROOT / "app" / "templates"))
subtensor = bt.Subtensor(network="finney")

COLDKEY_SS58 = os.getenv("COLDKEY", "5GBY9k83ydqCedqg1NLrWTKy8R6afTkwz5FPSyar3tCcBGQ5")

def _get_w3_account_contract():
    rpc_url = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        raise RuntimeError("PRIVATE_KEY is required")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise RuntimeError(f"Failed to connect to {rpc_url}")
    account = Account.from_key(private_key)
    info = load_deployment_info()
    contract_address = Web3.to_checksum_address(info["contract_address"])
    return w3, account, contract_address


def _receipt_to_dict(receipt):
    h = receipt["transactionHash"]
    return {
        "transactionHash": h.hex() if hasattr(h, "hex") else str(h),
        "blockNumber": receipt["blockNumber"],
        "status": receipt["status"],
    }


def _run_quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


@app.get("/")
async def root(_: str = Depends(get_current_username)):
    return RedirectResponse(url="/ui", status_code=302)


@app.get("/ui", response_class=HTMLResponse)
async def index(request: Request, _: str = Depends(get_current_username)):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/status")
async def api_status(_: str = Depends(get_current_username)):
    try:
        w3, account, contract_address = _get_w3_account_contract()
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
    balance_wei = w3.eth.get_balance(contract_address)
    balance_tao = float(Web3.from_wei(balance_wei, "ether"))
    try:
        contract = get_contract(w3, contract_address)
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


class StakeBody(BaseModel):
    hotkey: str
    netuid: int
    amount_tao: float


class StakeLimitBody(BaseModel):
    hotkey: str
    netuid: int
    amount_tao: float
    # Tolerance-based inputs (like alpha-trading-com/staking UI)
    rate_tolerance: float = 0.5  # Default 50% tolerance
    use_min_tolerance: bool = False  # "Use Min Tolerance" checkbox
    allow_partial: bool = False


class RemoveStakeBody(BaseModel):
    hotkey: str
    netuid: int
    amount: float | None = None


class RemoveStakeLimitBody(BaseModel):
    hotkey: str
    netuid: int
    amount: float | None = None
    # Tolerance-based inputs
    rate_tolerance: float = 0.5
    use_min_tolerance: bool = False
    allow_partial: bool = False


class TransferStakeBody(BaseModel):
    hotkey: str
    origin_netuid: int
    destination_netuid: int
    amount_tao: float


class MoveStakeBody(BaseModel):
    origin_hotkey: str
    destination_hotkey: str
    origin_netuid: int
    destination_netuid: int
    amount_tao: float | None = None


class WithdrawBody(BaseModel):
    amount_tao: float


@app.post("/api/stake")
async def api_stake(body: StakeBody, _: str = Depends(get_current_username)):
    try:
        w3, account, contract_address = _get_w3_account_contract()
        amount_rao = int(body.amount_tao * 10**9)
        receipt = _run_quiet(
            stake, w3, account, contract_address, body.hotkey, body.netuid, amount_rao
        )
        return {"ok": True, "receipt": _receipt_to_dict(receipt)}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.post("/api/stake-limit")
async def api_stake_limit(body: StakeLimitBody, _: str = Depends(get_current_username)):
    try:
        w3, account, contract_address = _get_w3_account_contract()
        amount_rao = int(body.amount_tao * 10**9)
        
        # Calculate limit_price from tolerance
        limit_price = int(calculate_stake_limit_price(
            tao_amount=body.amount_tao,
            netuid=body.netuid,
            min_tolerance_staking=body.use_min_tolerance,
            default_rate_tolerance=body.rate_tolerance,
            subtensor=subtensor
        ))
        
        receipt = _run_quiet(
            stake_limit,
            w3,
            account,
            contract_address,
            body.hotkey,
            body.netuid,
            limit_price,
            amount_rao,
            body.allow_partial,
        )
        return {"ok": True, "receipt": _receipt_to_dict(receipt), "limit_price_used": limit_price}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.post("/api/remove-stake")
async def api_remove_stake(body: RemoveStakeBody, _: str = Depends(get_current_username)):
    try:
        w3, account, contract_address = _get_w3_account_contract()
        
        # If amount is None, unstake all balance; if 0 < amount < 1, treat as fraction of staked
        if body.amount is None:
            stake_balance = subtensor.get_stake(
                coldkey_ss58=COLDKEY_SS58,
                hotkey_ss58=body.hotkey,
                netuid=body.netuid
            )
            amount_alpha_rao = stake_balance.rao - 1
        elif 0 < body.amount < 1:
            stake_balance = subtensor.get_stake(
                coldkey_ss58=COLDKEY_SS58,
                hotkey_ss58=body.hotkey,
                netuid=body.netuid
            )
            amount_alpha_rao = int(body.amount * stake_balance.rao)
        else:
            amount_alpha_rao = int(body.amount * 10**9)
        
        receipt = _run_quiet(
            remove_stake,
            w3,
            account,
            contract_address,
            body.hotkey,
            body.netuid,
            amount_alpha_rao,
        )
        return {"ok": True, "receipt": _receipt_to_dict(receipt)}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.post("/api/remove-stake-limit")
async def api_remove_stake_limit(body: RemoveStakeLimitBody, _: str = Depends(get_current_username)):
    try:
        w3, account, contract_address = _get_w3_account_contract()
        
        # If amount is None, unstake all; if 0 < amount < 1, treat as fraction of staked
        if body.amount is None:
            stake_balance = subtensor.get_stake(
                coldkey_ss58=COLDKEY_SS58,
                hotkey_ss58=body.hotkey,
                netuid=body.netuid
            )
            amount_alpha_rao = stake_balance.rao - 1
            amount_tao = stake_balance.tao
        elif 0 < body.amount < 1:
            stake_balance = subtensor.get_stake(
                coldkey_ss58=COLDKEY_SS58,
                hotkey_ss58=body.hotkey,
                netuid=body.netuid
            )
            amount_alpha_rao = int(body.amount * stake_balance.rao)
            amount_tao = body.amount * stake_balance.tao
        else:
            amount_alpha_rao = int(body.amount * 10**9)
            amount_tao = body.amount / 10**9
        
        # Calculate limit_price from tolerance
        limit_price = int(calculate_unstake_limit_price(
            tao_amount=amount_tao,
            netuid=body.netuid,
            min_tolerance_unstaking=body.use_min_tolerance,
            default_rate_tolerance=body.rate_tolerance,
            subtensor=subtensor
        ))
        
        receipt = _run_quiet(
            remove_stake_limit,
            w3,
            account,
            contract_address,
            body.hotkey,
            body.netuid,
            limit_price,
            amount_alpha_rao,
            body.allow_partial,
        )
        return {"ok": True, "receipt": _receipt_to_dict(receipt), "limit_price_used": limit_price}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.post("/api/transfer-stake")
async def api_transfer_stake(body: TransferStakeBody, _: str = Depends(get_current_username)):
    try:
        w3, account, contract_address = _get_w3_account_contract()
        amount_rao = int(body.amount_tao * 10**9)
        receipt = _run_quiet(
            transfer_stake,
            w3,
            account,
            contract_address,
            body.hotkey,
            body.origin_netuid,
            body.destination_netuid,
            amount_rao,
        )
        return {"ok": True, "receipt": _receipt_to_dict(receipt)}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.post("/api/move-stake")
async def api_move_stake(body: MoveStakeBody, _: str = Depends(get_current_username)):
    try:
        w3, account, contract_address = _get_w3_account_contract()
        # If amount is None, move all alpha; if 0 < amount_tao < 1, treat as fraction of staked
        if body.amount_tao is None:
            stake_balance = subtensor.get_stake(
                coldkey_ss58=COLDKEY_SS58,
                hotkey_ss58=body.origin_hotkey,
                netuid=body.origin_netuid,
            )
            amount_rao = stake_balance.rao - 1
        elif 0 < body.amount_tao < 1:
            stake_balance = subtensor.get_stake(
                coldkey_ss58=COLDKEY_SS58,
                hotkey_ss58=body.origin_hotkey,
                netuid=body.origin_netuid,
            )
            amount_rao = int(body.amount_tao * stake_balance.rao)
        else:
            amount_rao = int(body.amount_tao * 10**9)
        receipt = _run_quiet(
            move_stake,
            w3,
            account,
            contract_address,
            body.origin_hotkey,
            body.destination_hotkey,
            body.origin_netuid,
            body.destination_netuid,
            amount_rao,
        )
        return {"ok": True, "receipt": _receipt_to_dict(receipt)}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.post("/api/withdraw")
async def api_withdraw(body: WithdrawBody, _: str = Depends(get_current_username)):
    try:
        w3, account, contract_address = _get_w3_account_contract()
        amount_wei = int(body.amount_tao * 10**18)
        receipt = _run_quiet(withdraw, w3, account, contract_address, amount_wei)
        return {"ok": True, "receipt": _receipt_to_dict(receipt)}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


class CalcToleranceBody(BaseModel):
    tao_amount: float
    netuid: int
    operation: str = "stake"  # "stake" or "unstake"


@app.post("/api/calc-min-tolerance")
async def api_calc_min_tolerance(body: CalcToleranceBody, _: str = Depends(get_current_username)):
    """Calculate minimum tolerance for staking/unstaking operations."""
    try:
        if body.operation == "stake":
            limit_price = int(calculate_stake_limit_price(
                tao_amount=body.tao_amount,
                netuid=body.netuid,
                min_tolerance_staking=True,
                default_rate_tolerance=0.0,  # Ignored when min_tolerance=True
                subtensor=subtensor
            ))
        else:  # unstake
            limit_price = int(calculate_unstake_limit_price(
                tao_amount=body.tao_amount,
                netuid=body.netuid,
                min_tolerance_unstaking=True,
                default_rate_tolerance=0.0,
                subtensor=subtensor
            ))
        return {"ok": True, "limit_price": limit_price, "operation": body.operation}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.get("/api/stake-info")
async def api_stake_info(_: str = Depends(get_current_username)):
    """Get stake info for the configured coldkey."""
    try:
        from bittensor import Balance
        
        stake_infos = subtensor.get_stake_info_for_coldkey(coldkey_ss58=COLDKEY_SS58)
        subnet_infos = subtensor.all_subnets()
        
        # Import sim_swap utility for accurate value calculation
        from utils.stake_list_v2 import get_amount_with_sim_swap
        
        # Get wallet balance first
        balance = subtensor.get_balance(COLDKEY_SS58)
        
        stake_list = []
        total_staked_value = 0.0
        for info in stake_infos:
            subnet_info = subnet_infos[info.netuid]
            value = get_amount_with_sim_swap(
                subtensor,
                info.stake,
                info.netuid
            )
            total_staked_value += value
            stake_list.append({
                "netuid": info.netuid,
                "subnet_name": subnet_info.subnet_name,
                "value_tao": round(value, 2),
                "stake_alpha_tao": round(info.stake.tao, 2),
                "stake_alpha_rao": info.stake.rao,
                "price_tao": round(subnet_info.price.tao, 4),
                "hotkey_ss58": info.hotkey_ss58,
            })
        
        # Calculate totals
        total_staked_value_balance = Balance.from_tao(total_staked_value)
        total_value = total_staked_value_balance + balance
        
        return {
            "ok": True,
            "stakes": stake_list,
            "coldkey": COLDKEY_SS58,
            "free_balance_tao": round(balance.tao, 9),
            "total_staked_value_tao": round(total_staked_value_balance.tao, 9),
            "total_value_tao": round(total_value.tao, 9),
        }
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)

