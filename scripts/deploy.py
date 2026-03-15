#!/usr/bin/env python3
"""
Deploy the StakeWrap contract to the blockchain.
"""

import os
import json
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

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
    
    # Allowed coldkey is hardcoded in the contract
    # SS58: 5FsDUVe2zLxTJTR1HzYp35BcNpbeFMLC76uRhwSTGj5YF36C
    # bytes32: 0xa82db0e41db30fc3d206773f461c87c484b3ac0c25bf703567b4f1aa1ed5b350
    print("Allowed coldkey (hardcoded in contract):")
    print("  SS58:   5FsDUVe2zLxTJTR1HzYp35BcNpbeFMLC76uRhwSTGj5YF36C")
    print("  bytes32: 0xa82db0e41db30fc3d206773f461c87c484b3ac0c25bf703567b4f1aa1ed5b350")
    
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
        'allowed_coldkey_ss58': '5FsDUVe2zLxTJTR1HzYp35BcNpbeFMLC76uRhwSTGj5YF36C',
        'allowed_coldkey_bytes32': '0xa82db0e41db30fc3d206773f461c87c484b3ac0c25bf703567b4f1aa1ed5b350',
        'abi': abi
    }
    
    with open('deployment.json', 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    print(f"\nDeployment info saved to deployment.json")
    print(f"Contract Address: {contract_address}")


if __name__ == '__main__':
    main()

