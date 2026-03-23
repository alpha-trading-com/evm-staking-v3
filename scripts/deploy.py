#!/usr/bin/env python3
"""
Deploy the StakeWrap contract to the blockchain.
After deploy, calls setContractAccountId32() and setBaseFeesRao() so execute() can use packed params.
"""

import os
import sys
import json
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

# Project root for evm imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()


def load_contract_abi(artifact_path):
    """Load contract ABI from Hardhat artifacts."""
    with open(artifact_path, 'r') as f:
        artifact = json.load(f)
    return artifact['abi']


def load_contract_bytecode(artifact_path):
    """Load contract bytecode from Hardhat artifacts."""
    with open(artifact_path, 'r') as f:
        artifact = json.load(f)
    return artifact['bytecode']


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
    # Load environment variables
    rpc_url = os.getenv('RPC_URL', 'https://test.finney.opentensor.ai/')
    private_key = os.getenv('PRIVATE_KEY')
    
    if not private_key:
        raise ValueError("PRIVATE_KEY environment variable is required")
    
    # Connect to blockchain
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError(f"Failed to connect to {rpc_url}")
    
    print(f"Connected to {rpc_url}")
    print(f"Chain ID: {w3.eth.chain_id}")
    
    # Load account
    account = Account.from_key(private_key)
    print(f"Deploying from account: {account.address}")
    balance = w3.eth.get_balance(account.address)
    print(f"Account balance: {Web3.from_wei(balance, 'ether')} TAO")
    
    # Load contract artifacts
    artifact_path = 'artifacts/contracts/StakeWrap.sol/StakeWrap.json'
    if not os.path.exists(artifact_path):
        raise FileNotFoundError(
            f"Contract artifact not found at {artifact_path}. "
            "Please run 'npm run compile' first."
        )
    
    contract_abi = load_contract_abi(artifact_path)
    contract_bytecode = load_contract_bytecode(artifact_path)
    
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
    from evm import contract_address_bytes32
    from bt_utils.constants import STAKE_INFO_BASE_FEE_RAO, LIMIT_PRICE_BASE_FEE_RAO
    contract_account_id32 = contract_address_bytes32(contract_address)
    deployed = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)
    nonce = w3.eth.get_transaction_count(account.address)
    set_tx = deployed.functions.setContractAccountId32(contract_account_id32).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 100000,
        "gasPrice": w3.eth.gas_price,
    })
    signed_set = account.sign_transaction(set_tx)
    set_hash = w3.eth.send_raw_transaction(signed_set.raw_transaction)
    print(f"Setting contractAccountId32... tx {set_hash.hex()}")
    set_receipt = w3.eth.wait_for_transaction_receipt(set_hash)
    if set_receipt["status"] != 1:
        raise RuntimeError("setContractAccountId32 failed")
    print("contractAccountId32 set.")
    nonce += 1
    base_fees_tx = deployed.functions.setBaseFeesRao(STAKE_INFO_BASE_FEE_RAO, LIMIT_PRICE_BASE_FEE_RAO).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 100000,
        "gasPrice": w3.eth.gas_price,
    })
    signed_bf = account.sign_transaction(base_fees_tx)
    bf_hash = w3.eth.send_raw_transaction(signed_bf.raw_transaction)
    print(f"Setting base fees (stakeInfo={STAKE_INFO_BASE_FEE_RAO}, limitPrice={LIMIT_PRICE_BASE_FEE_RAO} rao)... tx {bf_hash.hex()}")
    bf_receipt = w3.eth.wait_for_transaction_receipt(bf_hash)
    if bf_receipt["status"] != 1:
        raise RuntimeError("setBaseFeesRao failed")
    print("setBaseFeesRao done.")


if __name__ == '__main__':
    main()

