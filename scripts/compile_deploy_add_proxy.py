#!/usr/bin/env python3
"""
One-shot: compile contract, deploy contract, add contract's SS58 as proxy (Any) for the proxy wallet.

Steps:
  1. Compile smart contract (npm run compile)
  2. Deploy smart contract (python scripts/deploy.py) — requires PRIVATE_KEY, writes deployment.json, then calls setContractAccountId32 and setBaseFeesRao
  3. Set executor on contract (setExecutor): address from EXECUTOR_PRIVATE_KEY if set, else owner (PRIVATE_KEY)
  4. Remove all existing proxies for the proxy wallet, then add contract's SS58 as proxy (type Any) — may prompt for wallet password

Requires:
  - PRIVATE_KEY in .env (for deploy)
  - Optional: EXECUTOR_PRIVATE_KEY — executor EOA derived from this key; if unset, executor is set to the owner address
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
import bittensor as bt

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
from web3 import Web3
from eth_account import Account
from evm import h160_to_ss58
from utils.proxy_extrinsic import add_proxy_extrinsic
from bt_utils.constants import (
    DELEGATE_1,
    DELEGATE_2,
)

SET_EXECUTOR_ABI = [
    {"inputs": [{"internalType": "address", "name": "_executor", "type": "address"}], "name": "setExecutor", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
]


def step_compile() -> None:
    print("[1/4] Compiling smart contract...")
    r = subprocess.run(
        ["npm", "run", "compile"],
        cwd=PROJECT_ROOT,
        shell=False,
    )
    if r.returncode != 0:
        sys.exit(r.returncode)
    print("      Compile OK\n")


def step_deploy() -> str:
    """Run deploy.py (deploy + setContractAccountId32 + setBaseFeesRao for execute() packed params)."""
    print("[2/4] Deploying smart contract...")
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


def step_set_executor(contract_address: str) -> None:
    """Call setExecutor: executor address from EXECUTOR_PRIVATE_KEY if set, else owner address (PRIVATE_KEY)."""
    print("[3/4] Setting executor on contract...")
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        print("      PRIVATE_KEY not set; skipping setExecutor.\n")
        return
    rpc_url = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print("      RPC not connected; skipping setExecutor.\n")
        return
    account = Account.from_key(private_key)
    executor_key = os.getenv("EXECUTOR_PRIVATE_KEY")
    if executor_key:
        executor_address = Web3.to_checksum_address(Account.from_key(executor_key).address)
        print(f"      Executor address from EXECUTOR_PRIVATE_KEY: {executor_address}")
    else:
        executor_address = Web3.to_checksum_address(account.address)
        print(f"      Executor address = owner (EXECUTOR_PRIVATE_KEY unset): {executor_address}")
    contract = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=SET_EXECUTOR_ABI)
    tx = contract.functions.setExecutor(executor_address).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 100000,
        "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"      setExecutor({executor_address}) tx {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt["status"] != 1:
        print("      ERROR: setExecutor failed.", file=sys.stderr)
        sys.exit(1)
    print("      Executor set.\n")


def step_add_proxy(contract_address: str) -> None:
    print("[4/4] Adding contract as proxy (Any) for proxy wallet...")
    contract_ss58 = h160_to_ss58(contract_address)
    print(f"      Contract EVM:  {contract_address}")
    print(f"      Contract SS58: {contract_ss58}")

    for wallet_name in [DELEGATE_1, DELEGATE_2]:
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

        receipt = add_proxy_extrinsic(
            subtensor,
            wallet,
            contract_ss58,
            proxy_type="Any",
            delay=0,
        )
        if not receipt.is_success:
            msg = receipt.error_message or "unknown"
            print(f"      ERROR: add_proxy failed: {msg}", file=sys.stderr)
            sys.exit(1)
        print("      Proxy added (Any). Done.\n")


def main():
    
    os.chdir(PROJECT_ROOT)

    step_compile()
    contract_address = step_deploy()
    step_set_executor(contract_address)
    step_add_proxy(contract_address)

    print("All steps completed.")


if __name__ == "__main__":
    main()
