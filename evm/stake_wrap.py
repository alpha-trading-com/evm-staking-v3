"""
StakeWrap contract interaction: ABI, XOR encoding, and transaction helpers (stake, withdraw, execute, etc.).
"""

import json
import os
from typing import Any, Dict, List, Optional

from web3 import Web3
from eth_account import Account
from eth_abi import encode
from eth_utils import keccak, to_hex

from evm.contract import get_contract as _evm_get_contract, get_stake_wrap_abi, STAKE_WRAP_ARTIFACT_PATH
from evm.address import ss58_to_bytes32
from bt_utils.constants import XOR_KEY, MAX_DELEGATE_BALANCE_RAO

# Minimal ABI for StakeWrap interaction (fallback when artifact missing)
CONTRACT_ABI: List[Dict[str, Any]] = [
    {"inputs": [{"internalType": "bytes32", "name": "hotkey", "type": "bytes32"}, {"internalType": "uint256", "name": "netuid", "type": "uint256"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "stake", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "hotkey", "type": "bytes32"}, {"internalType": "uint256", "name": "netuid", "type": "uint256"}, {"internalType": "uint256", "name": "limitPrice", "type": "uint256"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}, {"internalType": "bool", "name": "allowPartial", "type": "bool"}], "name": "stakeLimit", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "hotkey", "type": "bytes32"}, {"internalType": "uint256", "name": "netuid", "type": "uint256"}, {"internalType": "uint256", "name": "limitPrice", "type": "uint256"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}, {"internalType": "bool", "name": "allowPartial", "type": "bool"}], "name": "removeStakeLimit", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "hotkey", "type": "bytes32"}, {"internalType": "uint256", "name": "netuid", "type": "uint256"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "removeStake", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [], "name": "owner", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "withdraw", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "hotkey", "type": "bytes32"}, {"internalType": "uint256", "name": "origin_netuid", "type": "uint256"}, {"internalType": "uint256", "name": "destination_netuid", "type": "uint256"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "transferStake", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [], "name": "WITHDRAW_COLDKEY", "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "STAKE_INFO_DELEGATE", "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "LIMIT_PRICE_DELEGATE", "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "DEFAULT_HOTKEY", "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "origin_hotkey", "type": "bytes32"}, {"internalType": "bytes32", "name": "destination_hotkey", "type": "bytes32"}, {"internalType": "uint256", "name": "origin_netuid", "type": "uint256"}, {"internalType": "uint256", "name": "destination_netuid", "type": "uint256"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "moveStake", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "amount", "type": "uint256"}, {"internalType": "bytes32", "name": "delegateAddress", "type": "bytes32"}], "name": "transferToDelegate", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "uint64", "name": "execBlock", "type": "uint64"}, {"internalType": "uint256", "name": "packedBalances", "type": "uint256"}], "name": "execute", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "_id", "type": "bytes32"}], "name": "setContractAccountId32", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "stakeInfoBaseFeeRao", "type": "uint256"}, {"internalType": "uint256", "name": "limitPriceBaseFeeRao", "type": "uint256"}], "name": "setBaseFeesRao", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [], "name": "getBaseFeesRao", "outputs": [{"internalType": "uint256", "name": "stakeInfoBaseFeeRao", "type": "uint256"}, {"internalType": "uint256", "name": "limitPriceBaseFeeRao", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "_executor", "type": "address"}], "name": "setExecutor", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [], "name": "executor", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "contractAccountId32", "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "stakeAmount", "type": "uint256"}, {"internalType": "uint64", "name": "taoInPool", "type": "uint64"}], "name": "StakeExceedsTaoInPool", "type": "error"},
    {"inputs": [{"internalType": "uint256", "name": "simTao", "type": "uint256"}, {"internalType": "uint64", "name": "taoInPool", "type": "uint64"}], "name": "MoveStakeSimTaoExceedsPool", "type": "error"},
]


def xor_encode(value: int) -> int:
    """XOR encode a uint256 value using XOR_KEY (must match contract)."""
    return value ^ XOR_KEY


def pack_execute_params(original_stake_info_balance: int, original_limit_price_balance: int) -> int:
    """Pack the two delegate balances into one uint256 (high 128 = stakeInfo, low 128 = limitPrice). Base fees are contract constants."""
    return (original_stake_info_balance << 128) | (original_limit_price_balance & ((1 << 128) - 1))


def get_contract(w3, contract_address: str, abi: Optional[List] = None):
    """StakeWrap contract instance; uses artifact ABI when available, else CONTRACT_ABI."""
    if abi is None:
        abi = get_stake_wrap_abi() or CONTRACT_ABI
    return _evm_get_contract(w3, contract_address, abi=abi)


def is_owner(contract, account: Account) -> bool:
    """True if `account` is the contract owner (best-effort; False if the call fails)."""
    try:
        return contract.functions.owner().call().lower() == account.address.lower()
    except Exception as e:
        print(f"⚠️  Warning: Could not verify ownership: {e}")
        return False


def assert_owner(contract, account: Account) -> None:
    """Raise PermissionError unless `account` is the contract owner."""
    owner = contract.functions.owner().call()
    if owner.lower() != account.address.lower():
        raise PermissionError(f"Signer {account.address} is not the contract owner (owner={owner}).")


def stake(w3, account: Account, contract_address: str, hotkey, netuid: int, amount: int, contract=None):
    """Stake tokens. amount in rao. Pass contract to reuse a cached instance."""
    if contract is None:
        contract = get_contract(w3, contract_address)
    hotkey = ss58_to_bytes32(hotkey)
    print(f"Staking {amount} rao to netuid {netuid}")
    print(f"Hotkey (bytes32): 0x{hotkey.hex()}")
    tx = contract.functions.stake(hotkey, xor_encode(netuid), xor_encode(amount)).build_transaction({
        "from": account.address, "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 200000, "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Stake transaction hash: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction confirmed in block: {receipt.blockNumber}")
    if receipt.status == 0:
        print("❌ Transaction failed!")
        try:
            contract.functions.stake(hotkey, xor_encode(netuid), xor_encode(amount)).call({"from": account.address})
        except Exception as e:
            msg = str(e)
            if "execution reverted" in msg.lower() and ":" in msg:
                print(f"Revert reason: {msg.split(':', 1)[1].strip()}")
            else:
                print(f"Error: {msg}")
        return receipt
    print("✅ Stake transaction successful!")
    return receipt


def stake_limit(w3, account: Account, contract_address: str, hotkey, netuid: int, limit_price: int, amount: int, allow_partial: bool, contract=None):
    """Stake with limit price. amount in rao. Pass contract to reuse a cached instance."""
    if contract is None:
        contract = get_contract(w3, contract_address)
    hotkey = ss58_to_bytes32(hotkey)
    tx = contract.functions.stakeLimit(hotkey, xor_encode(netuid), xor_encode(limit_price), xor_encode(amount), allow_partial).build_transaction({
        "from": account.address, "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 200000, "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"StakeLimit transaction hash: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction confirmed in block: {receipt.blockNumber}")
    return receipt


def remove_stake_limit(w3, account: Account, contract_address: str, hotkey, netuid: int, limit_price: int, amount: int, allow_partial: bool, contract=None):
    """Remove stake with limit price. amount in ALPHA tokens. Pass contract to reuse a cached instance."""
    if contract is None:
        contract = get_contract(w3, contract_address)
    hotkey = ss58_to_bytes32(hotkey)
    print(f"Unstaking {amount} ALPHA tokens from netuid {netuid} with limit price {limit_price}")
    print(f"Hotkey (bytes32): 0x{hotkey.hex()}")
    tx = contract.functions.removeStakeLimit(hotkey, xor_encode(netuid), xor_encode(limit_price), xor_encode(amount), allow_partial).build_transaction({
        "from": account.address, "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 200000, "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"RemoveStakeLimit transaction hash: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction confirmed in block: {receipt.blockNumber}")
    return receipt


def remove_stake(w3, account: Account, contract_address: str, hotkey, netuid: int, amount: int, contract=None):
    """Remove stake (unstake alpha). amount in ALPHA tokens. Pass contract to reuse a cached instance."""
    if contract is None:
        contract = get_contract(w3, contract_address)
    hotkey = ss58_to_bytes32(hotkey)
    print(f"Unstaking {amount} ALPHA tokens from netuid {netuid}")
    print(f"Hotkey (bytes32): 0x{hotkey.hex()}")
    tx = contract.functions.removeStake(hotkey, xor_encode(netuid), xor_encode(amount)).build_transaction({
        "from": account.address, "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 200000, "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"RemoveStake transaction hash: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction confirmed in block: {receipt.blockNumber}")
    return receipt


def transfer_stake(w3, account: Account, contract_address: str, hotkey, origin_netuid: int, destination_netuid: int, amount: int, contract=None):
    """Transfer stake to predefined WITHDRAW_COLDKEY. amount in rao. Pass contract to reuse a cached instance."""
    if contract is None:
        contract = get_contract(w3, contract_address)
    try:
        withdraw_coldkey_bytes32 = contract.functions.WITHDRAW_COLDKEY().call()
        print(f"Withdraw coldkey (bytes32): 0x{withdraw_coldkey_bytes32.hex()}")
    except Exception as e:
        print(f"Warning: Could not read WITHDRAW_COLDKEY from contract: {e}")
    hotkey = ss58_to_bytes32(hotkey)
    print(f"Transferring {amount / 10**9} TAO ({amount} rao) worth of stake (alpha)")
    print(f"From netuid {origin_netuid} to netuid {destination_netuid}")
    print(f"Hotkey (bytes32): 0x{hotkey.hex()}")
    print("⚠️  Safety: Transferring to predefined WITHDRAW_COLDKEY only")
    tx = contract.functions.transferStake(hotkey, xor_encode(origin_netuid), xor_encode(destination_netuid), xor_encode(amount)).build_transaction({
        "from": account.address, "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 200000, "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"TransferStake transaction hash: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction confirmed in block: {receipt.blockNumber}")
    return receipt


def move_stake(w3, account: Account, contract_address: str, origin_hotkey, destination_hotkey, origin_netuid: int, destination_netuid: int, amount: int, contract=None):
    """Move stake from one hotkey to another. amount in rao. Pass contract to reuse a cached instance."""
    if contract is None:
        contract = get_contract(w3, contract_address)
    origin_hotkey = ss58_to_bytes32(origin_hotkey)
    destination_hotkey = ss58_to_bytes32(destination_hotkey)
    print(f"Moving {amount / 10**9} TAO ({amount} rao) worth of stake")
    print(f"From hotkey 0x{origin_hotkey.hex()} (netuid {origin_netuid})")
    print(f"To hotkey 0x{destination_hotkey.hex()} (netuid {destination_netuid})")
    tx = contract.functions.moveStake(origin_hotkey, destination_hotkey, xor_encode(origin_netuid), xor_encode(destination_netuid), xor_encode(amount)).build_transaction({
        "from": account.address, "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 200000, "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"MoveStake transaction hash: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction confirmed in block: {receipt.blockNumber}")
    return receipt


def transfer_to_delegate(w3, account: Account, contract_address: str, amount_wei: int, delegate_address_bytes32: bytes, contract=None):
    """Transfer TAO from contract to a delegate. amount in wei. Pass contract to reuse a cached instance."""
    if contract is None:
        contract = get_contract(w3, contract_address)
    try:
        owner = contract.functions.owner().call()
        if owner.lower() != account.address.lower():
            print("❌ ERROR: You are not the contract owner!")
            return None
    except Exception as e:
        print(f"⚠️  Warning: Could not verify ownership: {e}")
    balance_wei = w3.eth.get_balance(contract_address)
    if amount_wei > balance_wei:
        raise ValueError(f"Insufficient contract balance: have {balance_wei} wei, need {amount_wei} wei")
    amount_tao = Web3.from_wei(amount_wei, "ether")
    print(f"Transfer {amount_tao} TAO ({amount_wei} wei) to delegate 0x{delegate_address_bytes32.hex()}")
    tx = contract.functions.transferToDelegate(amount_wei, delegate_address_bytes32).build_transaction({
        "from": account.address, "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 150000, "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Transaction hash: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction confirmed in block: {receipt.blockNumber}")
    if receipt.status != 0:
        print("✅ transferToDelegate succeeded.")
    return receipt


def execute_pull_and_stake(w3, account: Account, contract_address: str, exec_block: int,
                           original_stake_info_balance: int, original_limit_price_balance: int, contract=None):
    """Call execute(execBlock, packedBalances). Balances in rao; delegate balances must be <= 2 TAO. Pass contract to reuse a cached instance."""
    if contract is None:
        contract = get_contract(w3, contract_address)
    try:
        owner = contract.functions.owner().call()
        if owner.lower() != account.address.lower():
            print("❌ ERROR: You are not the contract owner!")
            return None
    except Exception as e:
        print(f"⚠️  Warning: Could not verify ownership: {e}")
    if original_stake_info_balance > MAX_DELEGATE_BALANCE_RAO or original_limit_price_balance > MAX_DELEGATE_BALANCE_RAO:
        raise ValueError(
            f"Delegate balances must be <= 2 TAO ({MAX_DELEGATE_BALANCE_RAO} rao). "
            f"Got stake_info={original_stake_info_balance}, limit_price={original_limit_price_balance} rao."
        )
    packed_balances = pack_execute_params(original_stake_info_balance, original_limit_price_balance)
    print(f"Execute: execBlock={exec_block}, packedBalances")
    tx = contract.functions.execute(exec_block, packed_balances).build_transaction({
        "from": account.address, "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 500000, "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Transaction hash: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction confirmed in block: {receipt.blockNumber}")
    if receipt.status != 0:
        print("✅ execute succeeded.")
    return receipt


def withdraw(w3, account: Account, contract_address: str, amount: int, contract=None):
    """Withdraw TAO from contract to WITHDRAW_COLDKEY. amount in wei. Pass contract to reuse a cached instance."""
    if amount is None:
        raise ValueError("Amount is required. Use: withdraw --amount <TAO>")
    if contract is None:
        contract = get_contract(w3, contract_address)
    try:
        owner = contract.functions.owner().call()
        if owner.lower() != account.address.lower():
            print("❌ ERROR: You are not the contract owner!")
            print(f"   Contract owner: {owner}")
            print(f"   Your account: {account.address}")
            return None
        print("✅ Verified: You are the contract owner")
    except Exception as e:
        print(f"⚠️  Warning: Could not verify ownership: {e}")
    try:
        withdraw_coldkey_bytes32 = contract.functions.WITHDRAW_COLDKEY().call()
        print(f"Withdraw coldkey (bytes32): 0x{withdraw_coldkey_bytes32.hex()}")
    except Exception as e:
        print(f"Warning: Could not read WITHDRAW_COLDKEY from contract: {e}")
    balance_wei = w3.eth.get_balance(contract_address)
    balance_tao = Web3.from_wei(balance_wei, "ether")
    print(f"Contract balance: {balance_tao} TAO ({balance_wei} wei)")
    if balance_wei == 0:
        print("No funds to withdraw")
        return None
    if amount > balance_wei:
        amount_tao = Web3.from_wei(amount, "ether")
        raise ValueError(f"Amount ({amount_tao} TAO = {amount} wei) exceeds contract balance ({balance_tao} TAO = {balance_wei} wei)")
    amount_tao = Web3.from_wei(amount, "ether")
    print(f"⚠️  Withdrawing {amount_tao} TAO ({amount} wei) using balance transfer precompile (0x800)")
    print("   Note: Withdraw uses wei (10^18), unlike other functions which use rao (10^9)")
    try:
        tx = contract.functions.withdraw(amount).build_transaction({
            "from": account.address, "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 150000, "gasPrice": w3.eth.gas_price,
        })
    except Exception as e:
        error_str = str(e)
        if "was not found" in error_str or "not found" in error_str.lower():
            print("❌ ERROR: The withdraw function is not available on the deployed contract!")
            return None
        print(f"Error building transaction: {e}")
        print("Trying alternative method using function selector...")
        func_selector = keccak(b"withdraw(uint256)")[:4]
        encoded_params = encode(["uint256"], [amount])
        data = to_hex(func_selector + encoded_params)
        tx = {
            "to": contract_address, "from": account.address, "data": data,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 100000, "gasPrice": w3.eth.gas_price,
        }
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Withdraw transaction hash: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction confirmed in block: {receipt.blockNumber}")
    if receipt.status == 0:
        print("❌ Transaction failed!")
        try:
            contract.functions.withdraw(amount).call({"from": account.address})
        except Exception as revert_error:
            msg = str(revert_error)
            if "execution reverted" in msg and ":" in msg:
                print(f"Revert reason: {msg.split(':', 1)[1].strip()}")
            else:
                print(f"Error: {msg}")
        except Exception:
            print("Transaction reverted. Could not decode revert reason.")
        return receipt
    final_balance_wei = w3.eth.get_balance(contract_address)
    final_balance_tao = Web3.from_wei(final_balance_wei, "ether")
    print(f"Contract balance after withdrawal: {final_balance_tao} TAO ({final_balance_wei} wei)")
    return receipt


def _send_owner_tx(w3, account: Account, contract, fn_call, label: str, gas: int):
    """Verify owner, build/sign/send `fn_call`, wait for receipt, raise on revert. Returns receipt."""
    assert_owner(contract, account)
    tx = fn_call.build_transaction({
        "from": account.address, "nonce": w3.eth.get_transaction_count(account.address),
        "gas": gas, "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"{label} tx: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction confirmed in block: {receipt.blockNumber}")
    if receipt["status"] != 1:
        raise RuntimeError(f"{label} reverted (tx {tx_hash.hex()}).")
    return receipt


def set_executor(w3, account: Account, contract_address: str, executor_address: str, contract=None):
    """Owner-only: set the contract executor (pass the zero address to clear). Returns receipt."""
    if contract is None:
        contract = get_contract(w3, contract_address)
    executor_address = Web3.to_checksum_address(executor_address)
    print(f"Setting executor to {executor_address}")
    return _send_owner_tx(w3, account, contract, contract.functions.setExecutor(executor_address), "setExecutor", 100_000)


def set_base_fees_rao(w3, account: Account, contract_address: str,
                      stake_info_base_fee_rao: int, limit_price_base_fee_rao: int, contract=None):
    """Owner-only: set the base fees (rao) used by execute() for the two delegates. Returns receipt."""
    if contract is None:
        contract = get_contract(w3, contract_address)
    print(f"Setting base fees: stakeInfo={stake_info_base_fee_rao} rao, limitPrice={limit_price_base_fee_rao} rao")
    return _send_owner_tx(
        w3, account, contract,
        contract.functions.setBaseFeesRao(stake_info_base_fee_rao, limit_price_base_fee_rao),
        "setBaseFeesRao", 100_000,
    )


def set_contract_account_id32(w3, account: Account, contract_address: str, account_id32: bytes, contract=None):
    """Owner-only: set the contract's AccountId32 (once, after deploy) for smaller execute() calldata. Returns receipt."""
    if contract is None:
        contract = get_contract(w3, contract_address)
    print(f"Setting contractAccountId32 to 0x{account_id32.hex()}")
    return _send_owner_tx(
        w3, account, contract,
        contract.functions.setContractAccountId32(account_id32),
        "setContractAccountId32", 100_000,
    )
