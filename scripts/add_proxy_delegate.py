import bittensor as bt
import os
import json 
from bittensor.core.chain_data.proxy import ProxyType

def main():
    subtensor = bt.Subtensor(network="finney")
    real_account = bt.Wallet(name="proxy")
    # Load contract_address from deployment.json (written by deployment/deploy.py in PROJECT_ROOT)
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    deployment_path = os.path.join(PROJECT_ROOT, "deployment.json")
    with open(deployment_path, "r") as f:
        deployment = json.load(f)
    contract_address = deployment["contract_address"]

    # Convert EVM H160 address (hex) to Bittensor SS58
    import sys
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from evm import h160_to_ss58

    delegate_address = h160_to_ss58(contract_address)
    print(f"Delegate address: {delegate_address}")

    response = subtensor.add_proxy(
        wallet=real_account,
        delegate_ss58="5H3MFE2fg4FTRRcReET1uzAVLLzVBeJnzxgHw63nZxtGwWtk",
        proxy_type=ProxyType.Any,
        delay=0,
    )
    

    print(response)

if __name__ == "__main__":
    main()