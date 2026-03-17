#!/usr/bin/env python3
"""
Call the StakeWrap contract's execute() at the start of every new block.

Uses delegate addresses from bt_utils.constants. Balances from Bittensor chain.
Requires: PRIVATE_KEY (owner), RPC_URL. Optional: BITTENSOR_NETWORK (default finney).

Run from project root: python bt_utils/auto_execute.py  or  python -m bt_utils.auto_execute

While this script is running, you can use fast stake, fast stake limit, and fast unstake
(UI or API): they send intent via MevShield; this loop calls execute() each block to
apply staking/unstaking on chain.
"""

import os
import sys
import time

from web3 import Web3
from eth_account import Account

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(_THIS_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from evm import contract_address_bytes32, get_contract, load_deployment
from bt_utils.constants import (
    STAKE_INFO_DELEGATE,
    LIMIT_PRICE_DELEGATE,
    STAKE_INFO_BASE_FEE_RAO,
    LIMIT_PRICE_BASE_FEE_RAO,
)

# Contract: MAX_DELEGATE_BALANCE = 2 TAO
MAX_DELEGATE_BALANCE_RAO = 2 * 10**9

import bittensor as bt


def get_delegate_balances_from_chain(network="finney"):
    """
    Query Bittensor chain for free balance (in rao) of STAKE_INFO_DELEGATE and LIMIT_PRICE_DELEGATE.
    Returns (stake_info_balance_rao, limit_price_balance_rao).
    """
    try:
        subtensor = bt.Subtensor(network=network)
        b1 = subtensor.get_balance(STAKE_INFO_DELEGATE)
        b2 = subtensor.get_balance(LIMIT_PRICE_DELEGATE)
        return (b1.rao, b2.rao)
    except Exception as e:
        raise RuntimeError(f"Failed to query delegate balances from Bittensor: {e}") from e


def clamp_balance(rao):
    """Cap at MAX_DELEGATE_BALANCE (2 TAO) to avoid Exploited() revert."""
    return min(rao, MAX_DELEGATE_BALANCE_RAO)


def main():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT_DIR, ".env"))

    rpc_url = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
    private_key = os.getenv("PRIVATE_KEY")
    network = os.getenv("BITTENSOR_NETWORK", "finney")

    if not private_key:
        raise SystemExit("PRIVATE_KEY environment variable is required")

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise SystemExit(f"Failed to connect to RPC: {rpc_url}")

    deployment = load_deployment()
    contract_address = Web3.to_checksum_address(deployment["contract_address"])
    contract = get_contract(w3, contract_address)
    account = Account.from_key(private_key)

    owner = contract.functions.owner().call()
    if owner.lower() != account.address.lower():
        raise SystemExit(f"Account {account.address} is not contract owner {owner}")

    contract_addr_b32 = contract_address_bytes32(contract_address)
    print(f"Contract: {contract_address}")
    print(f"Contract AccountId32: 0x{contract_addr_b32.hex()}")
    print(f"Delegates: STAKE_INFO={STAKE_INFO_DELEGATE}, LIMIT_PRICE={LIMIT_PRICE_DELEGATE}")

    # Resolve balances from chain (required)
    chain_balances = get_delegate_balances_from_chain(network)
    stake_info_balance = clamp_balance(chain_balances[0])
    limit_price_balance = clamp_balance(chain_balances[1])
    print(f"Balances from chain (rao): stake_info={stake_info_balance}, limit_price={limit_price_balance}")

    stake_info_base_fee = STAKE_INFO_BASE_FEE_RAO
    limit_price_base_fee = LIMIT_PRICE_BASE_FEE_RAO
    print(f"Base fees (rao): stake_info={stake_info_base_fee}, limit_price={limit_price_base_fee}")
    print("Polling for new blocks (Bittensor chain)...")

    subtensor = bt.Subtensor(network=network)
    last_block = subtensor.get_current_block()
    while True:
        current = subtensor.get_current_block()
        if current > last_block:
            try:
                # Refresh balances from chain each block
                chain_balances = get_delegate_balances_from_chain(network)
                stake_info_balance = clamp_balance(chain_balances[0])
                limit_price_balance = clamp_balance(chain_balances[1])
                tx = contract.functions.execute(
                    current,
                    contract_addr_b32,
                    stake_info_balance,
                    limit_price_balance,
                    stake_info_base_fee,
                    limit_price_base_fee,
                ).build_transaction({
                    "from": account.address,
                    "nonce": w3.eth.get_transaction_count(account.address),
                    "gas": 600_000,
                    "gasPrice": w3.eth.gas_price,
                })
                signed = account.sign_transaction(tx)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
                status = "ok" if receipt.status == 1 else "reverted"
                print(f"Block {current} execute tx {tx_hash.hex()} -> {status}")
            except Exception as e:
                print(f"Block {current} execute failed: {e}")
            last_block = current
        time.sleep(1.0)


if __name__ == "__main__":
    main()
