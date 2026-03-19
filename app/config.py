"""App-level config: repo root, contract/coldkey SS58, executor file path."""
import os
from pathlib import Path

from web3 import Web3

REPO_ROOT = Path(__file__).resolve().parent.parent


def get_coldkey_ss58() -> str:
    """SS58 of the EVM contract on Bittensor. Env CONTRACT_SS58 overrides."""
    from evm import load_deployment_info, h160_to_ss58
    deployment = load_deployment_info()
    addr = Web3.to_checksum_address(deployment["contract_address"])
    return os.getenv("CONTRACT_SS58") or h160_to_ss58(addr)
