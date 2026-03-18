import json
import os
import random
import bittensor as bt
import threading
from typing import Optional, Tuple

from scalecodec import GenericExtrinsic

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


def submit_extrinsic(subtensor: bt.Subtensor, extrinsic: GenericExtrinsic, wait_for_inclusion: bool = False):
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


def _submit_two_extrinsics_batch(
    substrate,
    extrinsic1: GenericExtrinsic,
    extrinsic2: GenericExtrinsic,
) -> Tuple[bool, bool, str, str]:
    """
    Submit two extrinsics in one JSON-RPC batch (single ws send).
    Returns (ok1, ok2, msg1, msg2). Uses substrate's connection; both extrinsics
    are sent to the same node.
    """
    batch = [
        {"jsonrpc": "2.0", "method": "author_submitExtrinsic", "params": [str(extrinsic1.data)], "id": 1},
        {"jsonrpc": "2.0", "method": "author_submitExtrinsic", "params": [str(extrinsic2.data)], "id": 2},
    ]
    ws = substrate.connect(init=False)
    ws.send(json.dumps(batch))
    raw = ws.recv(timeout=substrate.retry_timeout, decode=False)
    if hasattr(raw, "decode"):
        raw = raw.decode()
    response = json.loads(raw)

    # Server may return a batch response (list) or a single object (error or some nodes)
    if isinstance(response, list):
        by_id = {r.get("id"): r for r in response if "id" in r}
        r1 = by_id.get(1, {})
        r2 = by_id.get(2, {})
    else:
        r1 = response if response.get("id") == 1 else {}
        r2 = response if response.get("id") == 2 else {}

    def result_for(r):
        if not r:
            return False, "no response"
        if "error" in r:
            return False, r["error"].get("message", str(r["error"]))
        if "result" in r:
            return True, ""
        return False, str(r)

    ok1, msg1 = result_for(r1)
    ok2, msg2 = result_for(r2)
    print(ok1, msg1, ok2, msg2)
    return ok1, ok2, msg1, msg2


def send_stake_info(subtensor1: bt.Subtensor, subtensor2: bt.Subtensor, wallet1: bt.Wallet, wallet2: bt.Wallet, stake_info: int, limit_price: Optional[int] = None):
    """Submit stake_info (and optionally limit_price) via MevShield. Returns (success, message)."""
    if limit_price is None:
        stake_info_extrinsic = get_info_extrinsic(subtensor1, wallet1, stake_info)
        return submit_extrinsic(subtensor1, stake_info_extrinsic)

    stake_info_extrinsic = get_info_extrinsic(subtensor1, wallet1, stake_info)
    limit_price_extrinsic = get_info_extrinsic(subtensor2, wallet2, limit_price)

    # Prefer one JSON-RPC batch on the first subtensor (same chain) so both extrinsics
    # are sent in a single payload
    ok1, ok2, msg1, msg2 = _submit_two_extrinsics_batch(
        subtensor1.substrate,
        stake_info_extrinsic,
        limit_price_extrinsic,
    )
    success = ok1 and ok2
    message = "ok" if success else f"stake_info={msg1}; limit_price={msg2}"
    return success, message

if __name__ == "__main__":
    subtensor1 = bt.Subtensor(network="finney")
    subtensor2 = bt.Subtensor(network="finney")
    wallet1 = bt.Wallet(name="proxy")
    wallet2 = bt.Wallet(name="test_proxy")
    wallet1.unlock_coldkey()
    wallet2.unlock_coldkey()
    stake_info = 2
    limit_price = 2
    success, message = send_stake_info(subtensor1, subtensor2, wallet1, wallet2, stake_info, limit_price)
    print(success, message)