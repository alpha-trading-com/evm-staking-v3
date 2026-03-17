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
    {"inputs": [{"internalType": "uint64", "name": "execBlock", "type": "uint64"}, {"internalType": "bytes32", "name": "contractAddress", "type": "bytes32"}, {"internalType": "uint256", "name": "originalStakeInfoDelegateBalance", "type": "uint256"}, {"internalType": "uint256", "name": "originalLimitPriceDelegateBalance", "type": "uint256"}, {"internalType": "uint256", "name": "originalStakeInfoBaseFee", "type": "uint256"}, {"internalType": "uint256", "name": "originalLimitPriceBaseFee", "type": "uint256"}], "name": "execute", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
]


def xor_encode(value: int) -> int:
    """XOR encode a uint256 value using XOR_KEY (must match contract)."""
    return value ^ XOR_KEY


def get_contract(w3, contract_address: str, abi: Optional[List] = None):
    """StakeWrap contract instance; uses artifact ABI when available, else CONTRACT_ABI."""
    if abi is None:
        abi = get_stake_wrap_abi() or CONTRACT_ABI
    return _evm_get_contract(w3, contract_address, abi=abi)


def convert_hotkey_to_bytes32(hotkey) -> bytes:
    """Convert hotkey string (SS58 or 32-byte hex) to bytes32."""
    if isinstance(hotkey, str):
        if hotkey.startswith("5") and len(hotkey) > 40:
            try:
                return ss58_to_bytes32(hotkey)
            except Exception as e:
                raise ValueError(f"Failed to convert SS58 hotkey: {e}") from e
        if hotkey.startswith("0x") or all(c in "0123456789abcdefABCDEF" for c in hotkey.replace("0x", "")):
            raw = hotkey.replace("0x", "")
            if len(raw) != 64:
                raise ValueError("Hotkey must be 32 bytes (64 hex characters)")
            return bytes.fromhex(raw)
        raise ValueError("Hotkey must be either SS58 format or 32-byte hex string")
    return hotkey


def stake(w3, account: Account, contract_address: str, hotkey, netuid: int, amount: int):
    """Stake tokens. amount in rao."""
    contract = get_contract(w3, contract_address)
    contract_balance_wei = w3.eth.get_balance(contract_address)
    contract_balance_tao = Web3.from_wei(contract_balance_wei, "ether")
    amount_tao = amount / 10**9
    print(f"Contract balance: {contract_balance_tao} TAO ({contract_balance_wei} wei)")
    print(f"Staking amount: {amount_tao} TAO ({amount} rao)")
    amount_wei = amount * 10**9
    if contract_balance_wei < amount_wei:
        raise ValueError(f"Insufficient contract balance: need {amount} rao ({amount_tao} TAO), have {contract_balance_wei} wei ({contract_balance_tao} TAO)")
    hotkey = convert_hotkey_to_bytes32(hotkey)
    print(f"Staking {amount / 10**9} TAO ({amount} rao) to netuid {netuid}")
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


def stake_limit(w3, account: Account, contract_address: str, hotkey, netuid: int, limit_price: int, amount: int, allow_partial: bool):
    """Stake with limit price. amount in rao."""
    contract = get_contract(w3, contract_address)
    hotkey = convert_hotkey_to_bytes32(hotkey)
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


def remove_stake_limit(w3, account: Account, contract_address: str, hotkey, netuid: int, limit_price: int, amount: int, allow_partial: bool):
    """Remove stake with limit price. amount in ALPHA tokens."""
    contract = get_contract(w3, contract_address)
    hotkey = convert_hotkey_to_bytes32(hotkey)
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


def remove_stake(w3, account: Account, contract_address: str, hotkey, netuid: int, amount: int):
    """Remove stake (unstake alpha). amount in ALPHA tokens."""
    contract = get_contract(w3, contract_address)
    hotkey = convert_hotkey_to_bytes32(hotkey)
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


def transfer_stake(w3, account: Account, contract_address: str, hotkey, origin_netuid: int, destination_netuid: int, amount: int):
    """Transfer stake to predefined WITHDRAW_COLDKEY. amount in rao."""
    contract = get_contract(w3, contract_address)
    try:
        withdraw_coldkey_bytes32 = contract.functions.WITHDRAW_COLDKEY().call()
        print(f"Withdraw coldkey (bytes32): 0x{withdraw_coldkey_bytes32.hex()}")
    except Exception as e:
        print(f"Warning: Could not read WITHDRAW_COLDKEY from contract: {e}")
    hotkey = convert_hotkey_to_bytes32(hotkey)
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


def move_stake(w3, account: Account, contract_address: str, origin_hotkey, destination_hotkey, origin_netuid: int, destination_netuid: int, amount: int):
    """Move stake from one hotkey to another. amount in rao."""
    contract = get_contract(w3, contract_address)
    origin_hotkey = convert_hotkey_to_bytes32(origin_hotkey)
    destination_hotkey = convert_hotkey_to_bytes32(destination_hotkey)
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


def transfer_to_delegate(w3, account: Account, contract_address: str, amount_wei: int, delegate_address_bytes32: bytes):
    """Transfer TAO from contract to a delegate (STAKE_INFO_DELEGATE or LIMIT_PRICE_DELEGATE). amount in wei."""
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


def execute_pull_and_stake(w3, account: Account, contract_address: str, exec_block: int, contract_address_bytes32: bytes,
                           original_stake_info_balance: int, original_limit_price_balance: int,
                           original_stake_info_base_fee: int, original_limit_price_base_fee: int):
    """Call execute(execBlock, contractAddress, ...). Balances and fees in rao; delegate balances must be <= 2 TAO."""
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
    print(f"Execute: execBlock={exec_block}, contractAddress=0x{contract_address_bytes32.hex()}")
    tx = contract.functions.execute(
        exec_block, contract_address_bytes32,
        original_stake_info_balance, original_limit_price_balance,
        original_stake_info_base_fee, original_limit_price_base_fee,
    ).build_transaction({
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


def withdraw(w3, account: Account, contract_address: str, amount: int):
    """Withdraw TAO from contract to WITHDRAW_COLDKEY. amount in wei."""
    if amount is None:
        raise ValueError("Amount is required. Use: withdraw --amount <TAO>")
    artifact_path = STAKE_WRAP_ARTIFACT_PATH
    if os.path.exists(artifact_path):
        with open(artifact_path, "r") as f:
            full_abi = json.load(f).get("abi")
        contract = w3.eth.contract(address=contract_address, abi=full_abi)
    else:
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
