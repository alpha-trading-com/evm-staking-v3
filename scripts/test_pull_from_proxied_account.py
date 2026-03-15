#!/usr/bin/env python3
"""
Test pullFromProxiedAccount: call the contract method with dest = contract's SS58 and report balance before/after.

Uses the contract's SS58 address (Blake2b("evm:"||address) encoded) as the destination so TAO is pulled into this contract.

Prerequisites:
  - deployment.json with contract_address
  - PRIVATE_KEY in .env (contract owner)
  - Allowed proxied account (allowedProxiedAccount) must have added this contract
    as a proxy (Transfer) on Subtensor and must have TAO to pull

Usage:
  python3 scripts/test_pull_from_proxied_account.py
  python3 scripts/test_pull_from_proxied_account.py --contract 0x...
  python3 scripts/test_pull_from_proxied_account.py --dry-run   # don't send tx, only show pre-checks
"""

import argparse
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except ImportError:
    pass

from web3 import Web3


def load_deployment_info():
    if not os.path.exists("deployment.json"):
        raise FileNotFoundError("deployment.json not found. Deploy the contract first.")
    with open("deployment.json", "r") as f:
        import json
        return json.load(f)


def get_contract(w3, contract_address, abi=None):
    import json
    if abi is None:
        path = os.path.join(PROJECT_ROOT, "artifacts/contracts/StakeWrap.sol/StakeWrap.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                abi = json.load(f)["abi"]
        else:
            from interact import CONTRACT_ABI
            abi = CONTRACT_ABI
    return w3.eth.contract(address=contract_address, abi=abi)


def main():
    parser = argparse.ArgumentParser(description="Test pullFromProxiedAccount")
    parser.add_argument("--contract", type=str, help="Contract address (default: from deployment.json)")
    parser.add_argument("--dry-run", action="store_true", help="Only run pre-checks, do not send tx")
    args = parser.parse_args()

    rpc_url = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        print("Error: PRIVATE_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print(f"Error: Cannot connect to {rpc_url}", file=sys.stderr)
        sys.exit(1)

    if args.contract:
        contract_address = Web3.to_checksum_address(args.contract)
    else:
        deployment = load_deployment_info()
        contract_address = Web3.to_checksum_address(deployment["contract_address"])

    from eth_account import Account
    account = Account.from_key(private_key)
    contract = get_contract(w3, contract_address)

    # Pre-checks
    owner = contract.functions.owner().call()
    if owner.lower() != account.address.lower():
        print("Error: Current account is not the contract owner.", file=sys.stderr)
        print(f"  Owner:   {owner}", file=sys.stderr)
        print(f"  Account: {account.address}", file=sys.stderr)
        sys.exit(1)
    print("Contract:", contract_address)
    print("Owner:   ", account.address)
    print("OK: caller is owner")

    balance_before_wei = w3.eth.get_balance(contract_address)
    balance_before_tao = float(Web3.from_wei(balance_before_wei, "ether"))
    print(f"Contract balance before: {balance_before_tao} TAO ({balance_before_wei} wei)")

    if args.dry_run:
        print("Dry-run: not sending pullFromProxiedAccount.")
        return 0

    # Dest = contract's SS58 address (decode to bytes32 for pullFromProxiedAccount(dest))
    from address_convert import h160_to_ss58
    from interact import pull_from_proxied_account, ss58_to_bytes32
    contract_ss58 = h160_to_ss58(contract_address)
    dest_bytes32 = ss58_to_bytes32(contract_ss58)
    print(f"Dest: contract SS58: {contract_ss58}")
    receipt = pull_from_proxied_account(w3, account, contract_address, dest_bytes32)
    if receipt is None:
        sys.exit(1)
    if receipt.status != 1:
        print("Tx failed (status != 1).", file=sys.stderr)
        sys.exit(1)

    balance_after_wei = w3.eth.get_balance(contract_address)
    balance_after_tao = float(Web3.from_wei(balance_after_wei, "ether"))
    delta_wei = balance_after_wei - balance_before_wei
    delta_tao = float(Web3.from_wei(delta_wei, "ether"))
    print(f"Contract balance after:  {balance_after_tao} TAO ({balance_after_wei} wei)")
    print(f"Delta: +{delta_tao} TAO (+{delta_wei} wei)")
    print("Test completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
