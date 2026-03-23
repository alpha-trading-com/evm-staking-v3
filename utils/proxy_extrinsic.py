"""Submit Proxy pallet calls via composed extrinsics (substrate)."""

import bittensor as bt


def add_proxy_extrinsic(
    subtensor: bt.Subtensor,
    wallet: bt.Wallet,
    delegate_ss58: str,
    *,
    proxy_type: str,
    delay: int = 0,
    wait_for_inclusion: bool = True,
    wait_for_finalization: bool = False,
):
    """
    Sign and submit `Proxy::add_proxy` as the wallet coldkey (real account).

    Returns the substrate extrinsic receipt from `submit_extrinsic`.
    """
    call = subtensor.substrate.compose_call(
        call_module="Proxy",
        call_function="add_proxy",
        call_params={
            "delegate": delegate_ss58,
            "proxy_type": proxy_type,
            "delay": delay,
        },
    )
    extrinsic = subtensor.substrate.create_signed_extrinsic(
        call=call,
        keypair=wallet.coldkey,
    )
    return subtensor.substrate.submit_extrinsic(
        extrinsic,
        wait_for_inclusion=wait_for_inclusion,
        wait_for_finalization=wait_for_finalization,
    )
