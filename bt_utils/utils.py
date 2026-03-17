import os
import random
import bittensor as bt

DEFAULT_PUBLIC_KEY = b'\x01\x02\x03\x04'

def get_info_extrinsic(subtensor: bt.Subtensor, wallet: bt.Wallet, info: int):
    call = subtensor.substrate.compose_call(
        call_module='MevShield',
        call_function='announce_next_key',
        call_params={
            'public_key': DEFAULT_PUBLIC_KEY
        }
    )

    # Create signed extrinsic with dynamic tip
    extrinsic = subtensor.substrate.create_signed_extrinsic(
        call=call,
        keypair=wallet.coldkey,
        tip=info,
    )
    return extrinsic


def submit_extrinsic(subtensor: bt.Subtensor, extrinsic: bt.Extrinsic, wait_for_inclusion: bool = True):
    try:
        receipt = subtensor.substrate.submit_extrinsic(
            extrinsic,
            wait_for_inclusion=wait_for_inclusion,
            wait_for_finalization=False,
        )
        if wait_for_inclusion:
            print("Extrinsic '{}' sent and included in block '{}'".format(receipt.extrinsic_hash, receipt.block_hash))
        else:
            print("Extrinsic '{}' submitted (payload sent)".format(receipt.extrinsic_hash))
    except Exception as e:
        print("Failed to submit extrinsic:", e)
        return False, str(e)
    return receipt.is_success, receipt.error_message

