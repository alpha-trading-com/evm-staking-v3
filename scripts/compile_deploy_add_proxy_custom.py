#!/usr/bin/env python3
"""
One-shot: withdraw from existing contract, then compile, deploy, add proxy, and transfer 1.1 TAO to contract.

Steps:
  1. Withdraw full contract balance to WITHDRAW_COLDKEY (if deployment.json exists and contract has balance)
  2. Compile smart contract (npm run compile)
  3. Deploy smart contract (python scripts/deploy.py; includes setContractAccountId32 and setBaseFeesRao)
  4. Set executor on contract (setExecutor): address from EXECUTOR_PRIVATE_KEY if set, else owner (PRIVATE_KEY)
  5. Remove all existing proxies for delegate wallets, then add contract's SS58 as proxy (Any)
  6. Transfer 1.1 TAO from delegate_1 to contract SS58 (chain transfer)

Requires:
  - PRIVATE_KEY in .env (for deploy and withdraw)
  - Optional: EXECUTOR_PRIVATE_KEY — executor EOA derived from this key; if unset, executor is set to the owner address
  - DELETEGATE_1_PASSWORD, DELETEGATE_2_PASSWORD in .env (for proxy and transfer)

Usage:
  python3 scripts/compile_deploy_add_proxy_custom.py
"""

import json
import os
import subprocess
import sys

# Project root (parent of scripts/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)


if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from web3 import Web3
from eth_account import Account
from evm import h160_to_ss58
from bt_utils.constants import DELETEGATE_1, DELETEGATE_2

# Minimal ABI for setExecutor(address)
SET_EXECUTOR_ABI = [
    {"inputs": [{"internalType": "address", "name": "_executor", "type": "address"}], "name": "setExecutor", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
]

# Minimal ABI for owner(), balance, and withdraw(uint256)
WITHDRAW_ABI = [
    {"inputs": [], "name": "owner", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "withdraw", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
]


def step_withdraw_all() -> None:
    """Withdraw full contract balance to WITHDRAW_COLDKEY (if deployment.json exists and balance > 0)."""
    print("[1/5] Withdrawing existing contract balance (if any)...")
    path = os.path.join(PROJECT_ROOT, "deployment.json")
    if not os.path.isfile(path):
        print("      No deployment.json; skipping withdraw.\n")
        return
    with open(path) as f:
        deployment = json.load(f)
    contract_address = Web3.to_checksum_address(deployment["contract_address"])

    rpc_url = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        print("      PRIVATE_KEY not set; skipping withdraw.\n")
        return

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print("      RPC not connected; skipping withdraw.\n")
        return

    account = Account.from_key(private_key)
    contract = w3.eth.contract(address=contract_address, abi=WITHDRAW_ABI)
    owner = contract.functions.owner().call()
    if owner.lower() != account.address.lower():
        print("      You are not the contract owner; skipping withdraw.\n")
        return

    balance_wei = w3.eth.get_balance(contract_address)
    if balance_wei == 0:
        print("      Contract balance is 0; nothing to withdraw.\n")
        return

    balance_tao = float(Web3.from_wei(balance_wei, "ether"))
    print(f"      Contract balance: {balance_tao} TAO. Withdrawing to WITHDRAW_COLDKEY...")
    tx = contract.functions.withdraw(balance_wei).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 150000,
        "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status != 1:
        print("      ERROR: Withdraw transaction failed.", file=sys.stderr)
        sys.exit(1)
    print("      Withdraw succeeded.\n")


def step_compile() -> None:
    print("[2/6] Compiling smart contract...")
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
    print("[3/6] Deploying smart contract...")
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
    print("[4/6] Setting executor on contract...")
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


def step_add_proxy(contract_ss58: str) -> None:
    print("[5/6] Adding contract as proxy (Any) for delegate wallets...")
    print(f"      Contract SS58: {contract_ss58}")

    import bittensor as bt
    from bittensor.core.chain_data.proxy import ProxyType
    for wallet_name in [DELETEGATE_1, DELETEGATE_2]:
        wallet = bt.Wallet(name=wallet_name)
        wallet.unlock_coldkey()
        subtensor = bt.Subtensor(network="finney")
        real_ss58 = wallet.coldkey.ss58_address
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


def step_transfer_to_contract(contract_ss58: str) -> None:
    """Transfer 1.1 TAO from delegate_1 to contract SS58 (chain transfer)."""
    print("[6/6] Transferring 1.1 TAO from delegate_1 to contract SS58...")
    import bittensor as bt
    from bittensor.utils.balance import Balance

    wallet = bt.Wallet(name=DELETEGATE_1)
    wallet.unlock_coldkey()
    subtensor = bt.Subtensor(network="finney")
    amount = Balance.from_tao(1.1)
    response = subtensor.transfer(
        wallet=wallet,
        destination_ss58=contract_ss58,
        amount=amount,
        mev_protection=False,
    )
    if not getattr(response, "success", True):
        msg = getattr(response, "message", str(response))
        print(f"      ERROR: transfer failed: {msg}", file=sys.stderr)
        sys.exit(1)
    print("      Transfer 1.1 TAO to contract SS58 succeeded.\n")


def main():
    step_withdraw_all()
    step_compile()
    contract_address = step_deploy()
    step_set_executor(contract_address)

    contract_ss58 = h160_to_ss58(contract_address)
    step_add_proxy(contract_ss58)
    step_transfer_to_contract(contract_ss58)
    print("All steps completed.")


if __name__ == "__main__":
    main()
