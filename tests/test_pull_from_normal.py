import bittensor as bt
from bittensor.core.chain_data.proxy import ProxyType


def main():
    subtensor = bt.Subtensor(network="finney")
    wallet = bt.Wallet(name="test_proxy")
    
    call = subtensor.substrate.compose_call(
        call_module='Balances',
        call_function='transfer_all',
        call_params={
            'dest': "5Hh7A2qiLTQFVSGT4g7ADcSiCuqeKN1BgumDwhQBmA8dMwBX",
            'keep_alive': True,
        }
    )

    
    proxy_call = subtensor.compose_call(
        call_module='Proxy',
        call_function='proxy',
        call_params={
            'real': "5FptUDrtvf6y4GmQKekEPmELeSC5MsLpRRDPFNXmHmCwfbs3",
            'force_proxy_type': ProxyType.Any.value,
            'call': call,
        }
    )

    extrinsic = subtensor.substrate.create_signed_extrinsic(
        call=proxy_call,
        keypair=wallet.coldkey,
    )

    receipt = subtensor.substrate.submit_extrinsic(
        extrinsic,
        wait_for_inclusion=True,
        wait_for_finalization=False,
    )
    print(receipt)

if __name__ == "__main__":
    main()