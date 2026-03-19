import bittensor as bt
from bittensor.utils.balance import Balance
from bittensor.core.chain_data.proxy import ProxyType


def main():
    # --- Example parameters (edit these for your test) ---
    network = "finney"
    proxy_wallet_name = "test_proxy"  # delegate that was added as proxy
    real = "5FptUDrtvf6y4GmQKekEPmELeSC5MsLpRRDPFNXmHmCwfbs3"  # delegator (real) SS58
    hotkey = "5Cd6htiu44dqQUUBoqu6B9kjPLs575XTCkwRf2mAhfpXsn11"  # hotkey to stake to
    netuid = 1
    amount_tao = 4.42
    # -----------------------------------------------------

    subtensor = bt.Subtensor(network=network)
    wallet = bt.Wallet(name=proxy_wallet_name)
    wallet.unlock_coldkey()

    amount_balance = bt.Balance.from_tao(amount_tao)

    # Inner staking call: SubtensorModule::add_stake(real, hotkey, netuid, amount_staked)
    call = subtensor.substrate.compose_call(
        call_module="SubtensorModule",
        call_function="remove_stake",
        call_params={
            "hotkey": hotkey,
            "netuid": netuid,
            "amount_unstaked": amount_balance.rao,
        },
    )

    # Wrap in Proxy.proxy(real, force_proxy_type=Staking, call)
    proxy_call = subtensor.substrate.compose_call(
        call_module="Proxy",
        call_function="proxy",
        call_params={
            "real": real,
            "force_proxy_type": ProxyType.Any.value,
            "call": call,
        },
    )

    extrinsic = subtensor.substrate.create_signed_extrinsic(
        call=proxy_call,
        keypair=wallet.coldkey,
    )

    print(f"Submitting Proxy.proxy from delegate {wallet.coldkey.ss58_address} for real {real}...")
    receipt = subtensor.substrate.submit_extrinsic(
        extrinsic,
        wait_for_inclusion=True,
        wait_for_finalization=False,
    )
    print("Inclusion:", receipt.is_success)
    print("Error:", receipt.error_message)
    print("Events:", receipt.triggered_events)


if __name__ == "__main__":
    main()