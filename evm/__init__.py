"""
EVM helpers: address conversion, contract loading, and StakeWrap transaction helpers.
"""

from evm.address import (
    SS58_PREFIX,
    account_id_to_ss58,
    contract_address_bytes32,
    h160_to_account_id,
    h160_to_ss58,
    ss58_to_bytes32,
)
from evm.contract import (
    DEFAULT_DEPLOYMENT_PATH,
    PROJECT_ROOT,
    STAKE_WRAP_ARTIFACT_PATH,
    get_project_root,
    get_stake_wrap_abi,
    load_deployment,
    load_deployment_info,
)
from evm.stake_wrap import (
    CONTRACT_ABI,
    MAX_DELEGATE_BALANCE_RAO,
    XOR_KEY,
    execute_pull_and_stake,
    get_contract,
    move_stake,
    remove_stake,
    remove_stake_limit,
    stake,
    stake_limit,
    transfer_stake,
    transfer_to_delegate,
    withdraw,
    xor_encode,
)

__all__ = [
    "SS58_PREFIX",
    "account_id_to_ss58",
    "contract_address_bytes32",
    "h160_to_account_id",
    "h160_to_ss58",
    "ss58_to_bytes32",
    "DEFAULT_DEPLOYMENT_PATH",
    "PROJECT_ROOT",
    "STAKE_WRAP_ARTIFACT_PATH",
    "get_contract",
    "get_project_root",
    "get_stake_wrap_abi",
    "load_deployment",
    "load_deployment_info",
    "CONTRACT_ABI",
    "MAX_DELEGATE_BALANCE_RAO",
    "XOR_KEY",
    "execute_pull_and_stake",
    "get_contract",
    "move_stake",
    "remove_stake",
    "remove_stake_limit",
    "stake",
    "stake_limit",
    "transfer_stake",
    "transfer_to_delegate",
    "withdraw",
    "xor_encode",
]
