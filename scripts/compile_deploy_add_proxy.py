#!/usr/bin/env python3
"""
One-shot: compile contract, deploy contract, add contract's SS58 as proxy (Any) for the proxy wallet.

Steps:
  1. Compile smart contract (npm run compile)
  2. Deploy smart contract (python scripts/deploy.py) — requires PRIVATE_KEY, writes deployment.json
  3. Remove all existing proxies for the proxy wallet, then add contract's SS58 as proxy (type Any) — may prompt for wallet password

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

# H160→SS58 via evm package (Blake2b-256(b"evm:" || h160))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from evm import h160_to_ss58
from bt_utils.constants import (
    DELETEGATE_1,
    DELETEGATE_2,
)


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
    print("[3/3] Adding contract as proxy (Any) for proxy wallet...")
    contract_ss58 = h160_to_ss58(contract_address)
    print(f"      Contract EVM:  {contract_address}")
    print(f"      Contract SS58: {contract_ss58}")

    import bittensor as bt
    from bittensor.core.chain_data.proxy import ProxyType
    for wallet_name in [DELETEGATE_1, DELETEGATE_2]:
        wallet = bt.Wallet(name=wallet_name)
        wallet.coldkey_file.save_password_to_env(os.getenv(f"{wallet_name}_PASSWORD"))
        wallet.coldkey_file.decrypt()
        subtensor = bt.Subtensor(network="finney")
        real_ss58 = wallet.coldkey.ss58_address
        # Remove all existing proxies first (may prompt for password)
        proxies_list, _ = subtensor.get_proxies_for_real_account(real_ss58)
        if proxies_list:
            print(f"      Removing {len(proxies_list)} existing proxy/ies...")
            remove_resp = subtensor.remove_proxies(wallet=wallet)
            if not getattr(remove_resp, "success", True):
                msg = getattr(remove_resp, "message", str(remove_resp))
                print(f"      ERROR: remove_proxies failed: {msg}", file=sys.stderr)
                sys.exit(1)
            print("      All proxies removed.")
        else:
            print("      No existing proxies.")

        # Add contract as proxy (may prompt for password)
        response = subtensor.add_proxy(
            wallet=wallet,
            delegate_ss58=contract_ss58,
            proxy_type=ProxyType.Any,
            delay=0,
        )

        if not getattr(response, "success", True):
            msg = getattr(response, "message", str(response))
            print(f"      ERROR: add_proxy failed: {msg}", file=sys.stderr)
            sys.exit(1)
        print("      Proxy added (Any). Done.\n")


def main():
    
    os.chdir(PROJECT_ROOT)

    step_compile()
    contract_address = step_deploy()
    step_add_proxy(contract_address)

    print("All steps completed.")


if __name__ == "__main__":
    main()
