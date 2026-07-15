import bittensor as bt
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from bt_utils.config import (
    DELEGATE_1,
    DELEGATE_2,
)

from app.core.config import settings


def main():

    from evm import h160_to_ss58, load_deployment_info
    from utils.proxy_extrinsic import add_proxy_extrinsic

    subtensor = bt.Subtensor(settings.NETWORK)
    for delegate_name in [DELEGATE_1, DELEGATE_2]:
        real_account = bt.Wallet(name=delegate_name)
        real_account.unlock_coldkey()
        contract_address = load_deployment_info()["contract_address"]

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
