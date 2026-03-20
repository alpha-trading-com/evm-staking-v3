"""
FastAPI app for StakeWrap: stake, stake limit, unstake, transfer, move, withdraw, fast stake/unstake.

Run from repo root:
  uvicorn app.main:app --host 0.0.0.0 --port 8000

Or: ./run_server.sh

Structure (SOC):
  app/
    main.py         – bootstrap, create app, include routers
    config.py       – REPO_ROOT
    globals.py      – cached state (subtensor, coldkey_ss58, w3/contract)
    schemas.py      – Pydantic request bodies
    auth.py         – HTTP Basic auth
    services/       – business logic (evm, executor, stake, fast_stake, stake_info)
    routers/        – ui, executor, tolerance-offset, heartbeat (settings), status, stake, fast, tolerance, stake_info
"""
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

from fastapi import FastAPI

from app.routers import ui, executor, status, stake, fast, tolerance, stake_info, settings, tolerance_offset

app = FastAPI(title="StakeWrap Control", version="1.0.0")

app.include_router(ui.router)
app.include_router(executor.router)
app.include_router(status.router)
app.include_router(stake.router)
app.include_router(fast.router)
app.include_router(tolerance.router)
app.include_router(stake_info.router)
app.include_router(settings.router)
app.include_router(tolerance_offset.router)
