import bittensor as bt
from bittensor.core.chain_data.proxy import ProxyType

def main():
    subtensor = bt.Subtensor(network="finney")

    subtensor = bt.Subtensor()

    real_account = bt.Wallet(name="proxy")
    delegate_address = "5GcPeHLZ3PiTb3rbnqNJiqp5kaoBr5WcYy2UsuNTVutN6vp7"

    response = subtensor.add_proxy(
        wallet=real_account,
        delegate_ss58=delegate_address,
        proxy_type=ProxyType.Any,
        delay=0,
    )

    print(response)

if __name__ == "__main__":
    main()