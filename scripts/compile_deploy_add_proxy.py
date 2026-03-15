#!/usr/bin/env python3
"""
One-shot: compile contract, deploy contract, add contract's SS58 as proxy (Transfer) for the proxy wallet.

Steps:
  1. Compile smart contract (npm run compile)
  2. Deploy smart contract (python scripts/deploy.py) — requires PRIVATE_KEY, writes deployment.json
  3. Add contract's SS58 as proxy (type Transfer) from the proxy wallet — may prompt for wallet password

Requires:
  - PRIVATE_KEY in .env (for deploy)
  - Proxy wallet (coldkey) under ~/.bittensor/wallets or --wallet-path; will be prompted to unlock

Usage:
  python3 scripts/compile_deploy_add_proxy.py
  python3 scripts/compile_deploy_add_proxy.py --wallet-name proxy --wallet-path ~/.bittensor/wallets
  python3 scripts/compile_deploy_add_proxy.py --skip-compile --skip-deploy   # only add proxy (use existing deployment.json)
"""

import argparse
import json
import os
import subprocess
import sys

# Project root (parent of scripts/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except ImportError:
    pass

# Use same H160→SS58 conversion as address_convert.py (evm: prefix + Blake2b-256)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))
from address_convert import h160_to_ss58


def step_compile() -> None:
    print("[1/3] Compiling smart contract...")
    r = subprocess.run(
        ["npm", "run", "compile"],
        cwd=PROJECT_ROOT,
        shell=False,
    )
    if r.returncode != 0:
        sys.exit(r.returncode)
    print("      Compile OK\n")


def step_deploy() -> str:
    print("[2/3] Deploying smart contract...")
    r = subprocess.run(
        [sys.executable, os.path.join(PROJECT_ROOT, "scripts", "deploy.py")],
        cwd=PROJECT_ROOT,
        env=os.environ,
    )
    if r.returncode != 0:
        sys.exit(r.returncode)
    with open(os.path.join(PROJECT_ROOT, "deployment.json")) as f:
        data = json.load(f)
    contract_address = data["contract_address"]
    print(f"      Deployed: {contract_address}\n")
    return contract_address


def step_add_proxy(contract_address: str) -> None:
    print("[3/3] Adding contract as proxy (Transfer) for proxy wallet...")
    contract_ss58 = h160_to_ss58(contract_address)
    print(f"      Contract EVM:  {contract_address}")
    print(f"      Contract SS58: {contract_ss58}")

    import bittensor as bt
    from bittensor.core.chain_data.proxy import ProxyType

    wallet = bt.Wallet(name="proxy")
    subtensor = bt.Subtensor(network="finney")

    # Unlock and add proxy (may prompt for password)
    response = subtensor.add_proxy(
        wallet=wallet,
        delegate_ss58=contract_ss58,
        proxy_type=ProxyType.Transfer,
        delay=0,
    )

    if not getattr(response, "success", True):
        msg = getattr(response, "message", str(response))
        print(f"      ERROR: add_proxy failed: {msg}", file=sys.stderr)
        sys.exit(1)
    print("      Proxy added (Transfer). Done.\n")


def main():
    
    os.chdir(PROJECT_ROOT)

    step_compile()
    contract_address = step_deploy()
    step_add_proxy(contract_address)

    print("All steps completed.")


if __name__ == "__main__":
    main()
