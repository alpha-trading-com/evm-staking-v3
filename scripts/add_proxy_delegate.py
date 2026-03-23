import bittensor as bt
import os
import json
import sys


def main():
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

    from evm import h160_to_ss58
    from utils.proxy_extrinsic import add_proxy_extrinsic

    subtensor = bt.Subtensor(network="finney")
    real_account = bt.Wallet(name="proxy")
    real_account.unlock_coldkey()

    deployment_path = os.path.join(PROJECT_ROOT, "deployment.json")
    with open(deployment_path, "r") as f:
        deployment = json.load(f)
    contract_address = deployment["contract_address"]

    delegate_address = h160_to_ss58(contract_address)
    print(f"Delegate address: {delegate_address}")

    receipt = add_proxy_extrinsic(
        subtensor,
        real_account,
        delegate_address,
        proxy_type="Any",
        delay=0,
    )
    print("success:", receipt.is_success)
    print("error:", receipt.error_message)


if __name__ == "__main__":
    main()
