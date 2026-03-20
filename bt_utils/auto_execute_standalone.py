#!/usr/bin/env python3
"""
Single-file auto-execute: call StakeWrap.execute() at the start of every new block.

No project imports: run from any directory. Expects in current directory:
  - .env (RPC_URL, EXECUTOR_PRIVATE_KEY or PRIVATE_KEY, optional BITTENSOR_WS_URL, EXECUTOR_GAS_LIMIT)
  - deployment.json (contract_address)
  - executor_enabled.json (optional, {"enabled": true/false})

Uses SubstrateInterface over BITTENSOR_WS_URL for block + balances (no bittensor.Subtensor).
"""

import json
import os
import sys
import time

# Resolve root: directory containing this script (for deployment.json / .env when run as script)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = _SCRIPT_DIR

# Delegate SS58 addresses (Bittensor)
STAKE_INFO_DELEGATE = "5FptUDrtvf6y4GmQKekEPmELeSC5MsLpRRDPFNXmHmCwfbs3"
LIMIT_PRICE_DELEGATE = "5Hh7A2qiLTQFVSGT4g7ADcSiCuqeKN1BgumDwhQBmA8dMwBX"
EXECUTOR_ENABLED_FILENAME = "executor_enabled.json"
DEFAULT_BITTENSOR_WS_URL = "wss://entrypoint-finney.opentensor.ai:443"

# Minimal ABI for execute + owner/executor checks
STAKE_WRAP_ABI = [
    {"inputs": [], "name": "owner", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "executor", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint64", "name": "execBlock", "type": "uint64"}, {"internalType": "uint256", "name": "packedBalances", "type": "uint256"}], "name": "execute", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
]

BLOCK_DATA_FETCH_PAYLOAD = json.dumps({
    "jsonrpc": "2.0", "method": "chain_getHeader", "params": [None], "id": 0,
})


def _find_file(*names):
    """First path that exists: under _ROOT, then cwd."""
    for base in (_ROOT, os.getcwd()):
        for name in names:
            p = os.path.join(base, name)
            if os.path.isfile(p):
                return p
    return None


def load_dotenv():
    path = _find_file(".env")
    if path:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_deployment():
    path = _find_file("deployment.json")
    if not path:
        raise FileNotFoundError("deployment.json not found in script dir or cwd. Deploy the contract first.")
    with open(path) as f:
        return json.load(f)


def pack_execute_params(stake_info_rao: int, limit_price_rao: int) -> int:
    """Pack delegate balances into one uint256 (high 128 = stakeInfo, low 128 = limitPrice)."""
    return (stake_info_rao << 128) | (limit_price_rao & ((1 << 128) - 1))


def get_contract(w3, contract_address: str):
    return w3.eth.contract(address=contract_address, abi=STAKE_WRAP_ABI)


def get_current_block(substrate) -> int:
    """Current Bittensor block number via direct WS chain_getHeader."""
    ws = substrate.ws
    ws.send(BLOCK_DATA_FETCH_PAYLOAD)
    raw = ws.recv()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    response = json.loads(raw)
    num = response["result"]["number"]
    return int(num, 0)


def _get_balance_rao(substrate, ss58: str) -> int:
    result = substrate.query(module="System", storage_function="Account", params=[ss58])
    if result is None:
        return 0
    obj = getattr(result, "value", result)
    data = obj.get("data") if isinstance(obj, dict) else None
    if not data:
        return 0
    free = data.get("free") if isinstance(data, dict) else None
    return 0 if free is None else int(free)


def get_delegate_balances_from_chain(substrate) -> tuple:
    b1 = _get_balance_rao(substrate, STAKE_INFO_DELEGATE)
    b2 = _get_balance_rao(substrate, LIMIT_PRICE_DELEGATE)
    return (b1, b2)


def is_executor_enabled() -> bool:
    path = _find_file(EXECUTOR_ENABLED_FILENAME)
    if not path:
        return True
    try:
        with open(path) as f:
            return json.load(f).get("enabled", True)
    except Exception:
        return True


def main():
    load_dotenv()

    from web3 import Web3
    from eth_account import Account
    from async_substrate_interface.sync_substrate import SubstrateInterface

    rpc_url = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
    ws_url = os.getenv("BITTENSOR_WS_URL", DEFAULT_BITTENSOR_WS_URL)
    executor_key = os.getenv("EXECUTOR_PRIVATE_KEY")
    owner_key = os.getenv("PRIVATE_KEY")

    if executor_key:
        private_key = executor_key
        use_executor_wallet = True
    elif owner_key:
        private_key = owner_key
        use_executor_wallet = False
    else:
        raise SystemExit("Set EXECUTOR_PRIVATE_KEY (recommended) or PRIVATE_KEY")

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise SystemExit(f"Failed to connect to RPC: {rpc_url}")

    deployment = load_deployment()
    contract_address = Web3.to_checksum_address(deployment["contract_address"])
    contract = get_contract(w3, contract_address)
    account = Account.from_key(private_key)

    if use_executor_wallet:
        executor_addr = contract.functions.executor().call()
        if not executor_addr or executor_addr == "0x0000000000000000000000000000000000000000":
            raise SystemExit("Contract has no executor set. Owner must call setExecutor(executorAddress) first.")
        if executor_addr.lower() != account.address.lower():
            raise SystemExit(f"Account {account.address} is not contract executor {executor_addr}")
        print("Using executor wallet (EXECUTOR_PRIVATE_KEY)")
    else:
        owner = contract.functions.owner().call()
        if owner.lower() != account.address.lower():
            raise SystemExit(f"Account {account.address} is not contract owner {owner}")
        print("Using owner wallet (PRIVATE_KEY)")

    print(f"Contract: {contract_address}")
    print(f"Delegates: STAKE_INFO={STAKE_INFO_DELEGATE}, LIMIT_PRICE={LIMIT_PRICE_DELEGATE}")

    try:
        substrate = SubstrateInterface(url=ws_url)
    except Exception as e:
        raise SystemExit(f"Failed to connect to Bittensor WS {ws_url}: {e}")

    last_block = get_current_block(substrate)
    chain_balances = get_delegate_balances_from_chain(substrate)
    stake_info_balance = chain_balances[0]
    limit_price_balance = chain_balances[1]
    print(f"Balances from chain (rao): stake_info={stake_info_balance}, limit_price={limit_price_balance}")

    gas_limit = int(os.getenv("EXECUTOR_GAS_LIMIT", "600000"))
    print("Polling for new blocks (Bittensor chain)...")

    nonce = w3.eth.get_transaction_count(account.address)
    signed = None
    is_executor_enabled_flag = is_executor_enabled()

    while True:
        try:
            current = get_current_block(substrate)
        except Exception as e:
            print(f"get_current_block failed: {e}")
            time.sleep(2)
            continue
        if current > last_block:
            try:
                if signed is None:
                    chain_balances = get_delegate_balances_from_chain(substrate)
                    stake_info_balance = chain_balances[0]
                    limit_price_balance = chain_balances[1]
                    exec_block = current + 1
                    print(f"Balances from chain (rao): stake_info={stake_info_balance}, limit_price={limit_price_balance}")
                    packed_balances = pack_execute_params(stake_info_balance, limit_price_balance)
                    tx = contract.functions.execute(exec_block, packed_balances).build_transaction({
                        "from": account.address, "nonce": nonce, "gas": gas_limit, "gasPrice": w3.eth.gas_price,
                    })
                    signed = account.sign_transaction(tx)
                if is_executor_enabled_flag:
                    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                    print(f"Block {current} execute(execBlock={exec_block}) tx {tx_hash.hex()}")
                    nonce += 1
                is_executor_enabled_flag = is_executor_enabled()
                chain_balances = get_delegate_balances_from_chain(substrate)
                stake_info_balance = chain_balances[0]
                limit_price_balance = chain_balances[1]
                exec_block = current + 2
                packed_balances = pack_execute_params(stake_info_balance, limit_price_balance)
                tx = contract.functions.execute(exec_block, packed_balances).build_transaction({
                    "from": account.address, "nonce": nonce, "gas": gas_limit, "gasPrice": w3.eth.gas_price,
                })
                signed = account.sign_transaction(tx)
            except Exception as e:
                err_msg = str(e).strip()
                if "Failed 0x" in err_msg or (hasattr(e, "args") and e.args and "0x" in str(e.args)):
                    print(f"Block {current} execute reverted: {type(e).__name__}: {err_msg}")
                    print("  -> Check: contract executor set and EXECUTOR_PRIVATE_KEY matches.")
                else:
                    print(f"Block {current} execute failed: {type(e).__name__}: {err_msg}")
            last_block = current
        time.sleep(2)


if __name__ == "__main__":
    main()
