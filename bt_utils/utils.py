import os
import random
import bittensor as bt
import threading
from typing import Optional

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


def submit_extrinsic(subtensor: bt.Subtensor, extrinsic: bt.Extrinsic, wait_for_inclusion: bool = False):
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


def send_stake_info(subtensor1: bt.Subtensor, subtensor2: bt.Subtensor, wallet1: bt.Wallet, wallet2: bt.Wallet, stake_info: int, limit_price: Optional[int] = None):
    """Submit stake_info (and optionally limit_price) via MevShield. Returns (success, message)."""
    if limit_price is None:
        stake_info_extrinsic = get_info_extrinsic(subtensor1, wallet1, stake_info)
        return submit_extrinsic(subtensor1, stake_info_extrinsic)

    stake_info_extrinsic = get_info_extrinsic(subtensor1, wallet1, stake_info)
    limit_price_extrinsic = get_info_extrinsic(subtensor2, wallet2, limit_price)

    results = []

    def run1():
        out = submit_extrinsic(subtensor1, stake_info_extrinsic)
        results.append(("stake_info", out))

    def run2():
        out = submit_extrinsic(subtensor2, limit_price_extrinsic)
        results.append(("limit_price", out))

    t1 = threading.Thread(target=run1)
    t2 = threading.Thread(target=run2)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    ok1 = results[0][1][0] if len(results) > 0 else False
    ok2 = results[1][1][0] if len(results) > 1 else False
    msg1 = results[0][1][1] if len(results) > 0 else ""
    msg2 = results[1][1][1] if len(results) > 1 else ""
    success = ok1 and ok2
    message = "ok" if success else f"stake_info={msg1}; limit_price={msg2}"
    return success, message

