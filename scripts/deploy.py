#!/usr/bin/env python3
"""
Deploy the StakeWrap contract to the blockchain.
After deploy, calls setContractAccountId32() and setBaseFeesRao() so execute() can use packed params.
"""

import os
import sys
import json
from web3 import Web3
from dotenv import load_dotenv

# Project root for evm imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from evm import connect_w3, load_account, load_stake_wrap_artifact

load_dotenv()


def deploy_contract(w3, account, contract_abi, contract_bytecode):
    """Deploy the contract and return the contract instance."""
    # Create contract instance
    contract = w3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)
    
    # Build transaction - no constructor parameters needed (allowedColdkey is hardcoded)
    construct_txn = contract.constructor().build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 2000000,  # Adjust based on your needs
        'gasPrice': w3.eth.gas_price,
    })
    
    # Sign transaction
    signed_txn = account.sign_transaction(construct_txn)
    
    # Send transaction
    print(f"Deploying contract from {account.address}...")
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"Transaction hash: {tx_hash.hex()}")
    
    # Wait for receipt
    print("Waiting for transaction receipt...")
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Contract deployed at address: {tx_receipt.contractAddress}")
    
    return tx_receipt.contractAddress, contract_abi, tx_hash


def main():
    # Connect to blockchain and load the deploying account (shared evm bootstrap)
    w3 = connect_w3()
    print(f"Connected. Chain ID: {w3.eth.chain_id}")

    account = load_account()  # PRIVATE_KEY
    print(f"Deploying from account: {account.address}")
    balance = w3.eth.get_balance(account.address)
    print(f"Account balance: {Web3.from_wei(balance, 'ether')} TAO")

    # Load contract artifacts (from repo: compile on build server, or `npm run compile` locally)
    artifact = load_stake_wrap_artifact(PROJECT_ROOT)
    contract_abi = artifact['abi']
    contract_bytecode = artifact['bytecode']

    # Deploy contract
    contract_address, abi, tx_hash = deploy_contract(
        w3, account, contract_abi, contract_bytecode
    )
    
    # Save deployment info
    deployment_info = {
        'contract_address': contract_address,
        'deployer': account.address,
        'chain_id': w3.eth.chain_id,
        'transaction_hash': tx_hash.hex(),
        'abi': abi
    }
    
    with open('deployment.json', 'w') as f:
        json.dump(deployment_info, f, indent=2)

    print(f"\nDeployment info saved to deployment.json")
    print(f"Contract Address: {contract_address}")

    # Set contract's AccountId32 and base fees (required for execute(); set once after deploy)
    from evm import contract_address_bytes32, set_contract_account_id32, set_base_fees_rao
    from bt_utils.fast_stake_unstake import compute_base_fees_rao
    deployed = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)
    contract_account_id32 = contract_address_bytes32(contract_address)
    set_contract_account_id32(w3, account, contract_address, contract_account_id32, contract=deployed)
    print("contractAccountId32 set.")
    stake_info_base_fee_rao, limit_price_base_fee_rao = compute_base_fees_rao()
    set_base_fees_rao(w3, account, contract_address, stake_info_base_fee_rao, limit_price_base_fee_rao, contract=deployed)
    print("setBaseFeesRao done.")


if __name__ == '__main__':
    main()

