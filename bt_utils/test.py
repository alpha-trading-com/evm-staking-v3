#!/usr/bin/env python3
"""
Test that auto_execute's get_current_block (Bittensor chain) works.
Requires: bittensor (pip install -r requirements.txt), .env optional (BITTENSOR_NETWORK, default finney).
Run from repo root with venv active: python3 bt_utils/test.py   or   python3 -m bt_utils.test
"""
import json
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(_THIS_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT_DIR, ".env"))
except ImportError:
    pass

import bittensor as bt


def get_current_block(subtensor: bt.Subtensor) -> int:
    """Same as in auto_execute.py: chain_getHeader via substrate ws."""
    ws = subtensor.substrate.ws
    payload = {
        "jsonrpc": "2.0", "method": "chain_getHeader", "params": [None], "id": 0
    }
    ws.send(json.dumps(payload))
    response = json.loads(ws.recv())
    return int(response["result"]["number"], 0)


def main():
    network = os.getenv("BITTENSOR_NETWORK", "finney")
    print(f"Connecting to Bittensor network={network}...")
    subtensor = bt.Subtensor(network=network)


    while True:
        # Test 1: get_current_block (chain_getHeader via ws)
        try:
            block_ws = get_current_block(subtensor)
            print(f"get_current_block(subtensor) (chain_getHeader): {block_ws}")
        except Exception as e:
            print(f"get_current_block failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
