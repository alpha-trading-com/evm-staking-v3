"""
EVM contract helpers: deployment info, StakeWrap ABI, and contract instance.
"""

import json
import os
from typing import Any, Dict, List, Optional

# Project root: parent of evm/ package
_evm_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_evm_dir)

STAKE_WRAP_ARTIFACT_PATH = os.path.join(
    PROJECT_ROOT, "artifacts", "contracts", "StakeWrap.sol", "StakeWrap.json"
)
DEFAULT_DEPLOYMENT_PATH = os.path.join(PROJECT_ROOT, "deployment.json")


def get_project_root() -> str:
    """Return the project root directory (parent of evm/)."""
    return PROJECT_ROOT


def load_deployment(path: Optional[str] = None) -> Dict[str, Any]:
    """Load deployment info (e.g. contract_address) from deployment.json."""
    p = path or DEFAULT_DEPLOYMENT_PATH
    if not os.path.exists(p):
        raise FileNotFoundError(f"Deployment not found: {p}. Deploy the contract first.")
    with open(p, "r") as f:
        return json.load(f)


def load_deployment_info() -> Dict[str, Any]:
    """Alias for load_deployment() for compatibility with scripts."""
    return load_deployment()


_abi_cache: Optional[List[Dict]] = None


def get_stake_wrap_abi(project_root: Optional[str] = None) -> Optional[List[Dict]]:
    """
    Load StakeWrap ABI from Hardhat artifact (cached after first load). Returns None if artifact is missing.
    """
    global _abi_cache
    if _abi_cache is not None:
        return _abi_cache
    root = project_root or PROJECT_ROOT
    artifact_path = os.path.join(root, "artifacts", "contracts", "StakeWrap.sol", "StakeWrap.json")
    if not os.path.exists(artifact_path):
        return None
    with open(artifact_path, "r") as f:
        _abi_cache = json.load(f).get("abi")
    return _abi_cache


def get_contract(w3, contract_address: str, abi: Optional[List] = None, project_root: Optional[str] = None):
    """
    Return a web3 contract instance for StakeWrap at contract_address.
    If abi is None, loads ABI from artifact (project_root/artifacts/.../StakeWrap.json).
    Raises FileNotFoundError if abi is None and artifact is missing.
    """
    if abi is None:
        abi = get_stake_wrap_abi(project_root)
        if abi is None:
            raise FileNotFoundError(
                f"StakeWrap artifact not found at {STAKE_WRAP_ARTIFACT_PATH}. "
                "Run 'npm run compile' or pass abi= explicitly."
            )
    return w3.eth.contract(address=contract_address, abi=abi)
