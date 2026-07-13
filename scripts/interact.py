#!/usr/bin/env python3
"""
CLI for the deployed StakeWrap contract. Contract logic lives in evm.stake_wrap.
"""

import os
import sys
import argparse
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

_script_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_script_dir)
if _root not in sys.path:
    sys.path.insert(0, _root)

from evm import (
    connect_w3,
    load_account,
    resolve_contract_address,
    get_contract,
    h160_to_ss58,
    stake,
    stake_limit,
    remove_stake,
    remove_stake_limit,
    transfer_stake,
    move_stake,
    transfer_to_delegate,
    execute_pull_and_stake,
    withdraw,
    CONTRACT_ABI,
)

load_dotenv()

# Legacy: for test_pull_from_proxied_account (contract may not expose proxyWithdrawAll on current deploy)
def proxy_withdraw_all(w3, account, contract_address, dest_bytes32, skip_verify=False):
    """Call proxyWithdrawAll(dest). Legacy helper for tests."""
    _abi = CONTRACT_ABI + [
        {"inputs": [{"internalType": "bytes32", "name": "dest", "type": "bytes32"}], "name": "proxyWithdrawAll", "outputs": [], "stateMutability": "nonpayable", "type": "function"}
    ]
    contract = w3.eth.contract(address=contract_address, abi=_abi)
    tx = contract.functions.proxyWithdrawAll(dest_bytes32).build_transaction({
        "from": account.address, "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 400000, "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Transaction hash: {tx_hash.hex()}")
    return w3.eth.wait_for_transaction_receipt(tx_hash)


def main():
    parser = argparse.ArgumentParser(description='Interact with StakeWrap contract')
    parser.add_argument('action', choices=['stake', 'stakeLimit', 'removeStake', 'removeStakeLimit', 'transferStake', 'moveStake', 'owner', 'withdraw', 'balance', 'transferToDelegate', 'execute'],
                        help='Action to perform')
    parser.add_argument('--hotkey', type=str, help='Hotkey (SS58 or 32 bytes hex string)')
    parser.add_argument('--origin-hotkey', type=str, help='Origin hotkey for moveStake (SS58 or 32 bytes hex string)')
    parser.add_argument('--destination-hotkey', type=str, help='Destination hotkey for moveStake (SS58 or 32 bytes hex string)')
    parser.add_argument('--netuid', type=int, help='Network UID')
    parser.add_argument('--origin-netuid', type=int, help='Origin netuid for transferStake/moveStake')
    parser.add_argument('--destination-netuid', type=int, help='Destination netuid for transferStake/moveStake')
    parser.add_argument('--amount', type=float, help='Amount: TAO for stake/transferStake/moveStake/withdraw; ALPHA tokens for removeStake/removeStakeLimit')
    parser.add_argument('--limit-price', type=int, dest='limit_price',
                       help='Limit price for stakeLimit')
    parser.add_argument('--allow-partial', action='store_true',
                       help='Allow partial fill for stakeLimit')
    parser.add_argument('--contract', type=str, help='Contract address (overrides deployment.json)')
    parser.add_argument('--delegate', type=str, choices=['stake-info', 'limit-price'], default='stake-info',
                        help='transferToDelegate: which delegate (stake-info or limit-price)')
    parser.add_argument('--exec-block', type=int, dest='exec_block', help='execute: block number for execution (must equal current block)')
    parser.add_argument('--original-stake-info-balance', type=int, dest='original_stake_info_balance', help='execute: original stake-info delegate balance in rao')
    parser.add_argument('--original-limit-price-balance', type=int, dest='original_limit_price_balance', help='execute: original limit-price delegate balance in rao')

    args = parser.parse_args()
    
    # Shared bootstrap: connect, load signer (PRIVATE_KEY), resolve contract address
    w3 = connect_w3()
    account = load_account()
    contract_address = resolve_contract_address(args.contract)

    print(f"Contract address: {contract_address}")
    print(f"Account: {account.address}")
    
    # Execute action
    if args.action == 'owner':
        contract = get_contract(w3, contract_address)
        owner = contract.functions.owner().call()
        print(f"Contract owner: {owner}")
        print(f"Your account: {account.address}")
        if owner.lower() == account.address.lower():
            print("✅ You are the contract owner")
        else:
            print("❌ You are NOT the contract owner")
            print("   You need to use the owner's private key to withdraw")
    
    elif args.action == 'balance':
        balance_wei = w3.eth.get_balance(contract_address)  # Balance is in wei (10^18)
        balance_tao = Web3.from_wei(balance_wei, 'ether')
        print(f"Contract balance: {balance_tao} TAO ({balance_wei} wei)")
        print(f"Note: Balance is in wei (10^18). Staking/unstaking amounts use rao (10^9).")

    elif args.action == 'stake':
        if not all([args.hotkey, args.netuid is not None, args.amount is not None]):
            parser.error("stake requires --hotkey, --netuid, and --amount")
        # Convert TAO to rao (1 TAO = 10^9 rao)
        amount_rao = int(args.amount * 10**9)
        stake(w3, account, contract_address, args.hotkey, args.netuid, amount_rao)
    
    elif args.action == 'stakeLimit':
        if not all([args.hotkey, args.netuid is not None, args.limit_price is not None,
                   args.amount is not None]):
            parser.error("stakeLimit requires --hotkey, --netuid, --limit-price, and --amount")
        # Convert TAO to rao (1 TAO = 10^9 rao)
        amount_rao = int(args.amount * 10**9)
        stake_limit(w3, account, contract_address, args.hotkey, args.netuid,
                   args.limit_price, amount_rao, args.allow_partial)
    
    elif args.action == 'removeStakeLimit':
        if not all([args.hotkey, args.netuid is not None, args.limit_price is not None,
                   args.amount is not None]):
            parser.error("removeStakeLimit requires --hotkey, --netuid, --limit-price, and --amount")
        # Amount is in ALPHA tokens (contract expects raw alpha, XOR-encoded inside)
        amount_alpha = int(args.amount)
        remove_stake_limit(w3, account, contract_address, args.hotkey, args.netuid,
                          args.limit_price, amount_alpha, args.allow_partial)

    elif args.action == 'removeStake':
        if not all([args.hotkey, args.netuid is not None, args.amount is not None]):
            parser.error("removeStake requires --hotkey, --netuid, and --amount")
        # Amount is in ALPHA tokens (contract expects raw alpha, XOR-encoded inside)
        amount_alpha = int(args.amount * 10**9)
        remove_stake(w3, account, contract_address, args.hotkey, args.netuid, amount_alpha)
    
    elif args.action == 'transferStake':
        if not all([args.hotkey, args.origin_netuid is not None, 
                   args.destination_netuid is not None, args.amount is not None]):
            parser.error("transferStake requires --hotkey, --origin-netuid, --destination-netuid, and --amount")
        # Convert TAO to rao (1 TAO = 10^9 rao)
        amount_rao = int(args.amount * 10**9)
        transfer_stake(w3, account, contract_address, args.hotkey,
                       args.origin_netuid, args.destination_netuid, amount_rao)
    
    elif args.action == 'moveStake':
        if not all([args.origin_hotkey, args.destination_hotkey, args.origin_netuid is not None,
                   args.destination_netuid is not None, args.amount is not None]):
            parser.error("moveStake requires --origin-hotkey, --destination-hotkey, --origin-netuid, --destination-netuid, and --amount")
        # Convert TAO to rao (1 TAO = 10^9 rao)
        amount_rao = int(args.amount * 10**9)
        move_stake(w3, account, contract_address, args.origin_hotkey, args.destination_hotkey,
                  args.origin_netuid, args.destination_netuid, amount_rao)
    
    elif args.action == 'withdraw':
        if args.amount is None:
            parser.error("withdraw requires --amount")
        # Withdraw amount should be in wei (10^18) - withdraw function expects wei
        amount_wei = int(args.amount * 10**18)
        withdraw(w3, account, contract_address, amount_wei)

    elif args.action == 'transferToDelegate':
        if args.amount is None:
            parser.error("transferToDelegate requires --amount")
        amount_wei = int(args.amount * 10**18)
        contract = get_contract(w3, contract_address)
        if args.delegate == 'stake-info':
            delegate_bytes32 = contract.functions.STAKE_INFO_DELEGATE().call()
        else:
            delegate_bytes32 = contract.functions.LIMIT_PRICE_DELEGATE().call()
        transfer_to_delegate(w3, account, contract_address, amount_wei, delegate_bytes32)

    elif args.action == 'execute':
        if None in (args.exec_block, args.original_stake_info_balance, args.original_limit_price_balance):
            parser.error("execute requires --exec-block, --original-stake-info-balance, --original-limit-price-balance")
        execute_pull_and_stake(
            w3, account, contract_address,
            args.exec_block,
            args.original_stake_info_balance, args.original_limit_price_balance,
        )

if __name__ == '__main__':
    main()

