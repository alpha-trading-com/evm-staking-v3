import os
import sys
import time

import bittensor as bt
from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

load_dotenv(os.path.join(_REPO_ROOT, ".env"))

from bt_utils.constants import DEFAULT_HOTKEY

from evm.address import h160_to_ss58
from evm.contract import load_deployment_info
from evm.stake_wrap import stake

COLDKEY_SWAP_EVENT_TYPE = "COLDKEY_SWAP"
IDENTITY_CHANGE_EVENT_TYPE = "IDENTITY_CHANGE"
COLDKEY_SWAP_FINISHED_EVENT_TYPE = "COLDKEY_SWAP_FINISHED"
DEREGISTERED_EVENT_TYPE = "DEREGISTERED"

NETWORK = "finney"
SN28_NETUID = 28

class ColdkeySwapFetcherFromMemPool:
    def __init__(self):
        self.subtensor = bt.Subtensor(NETWORK)
        self.subtensor_finney = bt.Subtensor("finney")

        self.last_checked_block = self.subtensor.get_current_block()
        self.subnet_names = []
        self.owner_coldkeys = []
        self.cache = []

        rpc_url = os.getenv("RPC_URL", "https://lite.chain.opentensor.ai").strip()
        private_key = os.getenv("PRIVATE_KEY")
        if not private_key or not str(private_key).strip():
            raise RuntimeError("PRIVATE_KEY is required in .env to submit StakeWrap stake txs")
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        self.evm_account = Account.from_key(str(private_key).strip())

        contract_raw = os.getenv("STAKE_CONTRACT_ADDRESS", "").strip()
        if contract_raw:
            self.stake_contract_address = Web3.to_checksum_address(contract_raw)
        else:
            deployment = load_deployment_info()
            self.stake_contract_address = Web3.to_checksum_address(deployment["contract_address"])

        # Validator hotkey SS58 on subnet 28 — defaults to bt_utils.constants.DEFAULT_HOTKEY.
        self.sn28_hotkey_ss58 = os.getenv("SN28_STAKE_HOTKEY_SS58", "").strip() or DEFAULT_HOTKEY

        # Extra TAO (rao) left on the contract’s coldkey after staking (fees / keep-alive buffer).
        self.sn28_stake_reserve_rao = int(
            os.getenv("SN28_STAKE_RESERVE_RAO", "50000000"), 10
        )
  
    def fetch_extrinsic_data(self, block_number):
        """Extract ColdkeySwapScheduled events from the data"""
        events = []
        print(f"Fetching events from mempool")

        extrinsics = self.subtensor.substrate.retrieve_pending_extrinsics()
        
        print(f"Fetched {len(extrinsics)} events from mempool")

        for ex in extrinsics:
            call = ex.value.get('call', {})
            extrinsic_hash = ex.value.get('extrinsic_hash', None)
            print(f"Extrinsic hash: {extrinsic_hash}")
            if extrinsic_hash in self.cache:
                continue
            self.cache.append(extrinsic_hash)
            if len(self.cache) > 1500:
                self.cache = self.cache[-1500:]
            
            if (
                call.get('call_module') == 'SubtensorModule' and
                call.get('call_function') == 'schedule_swap_coldkey'
            ):
                # Get the new coldkey from call_args
                args = call.get('call_args', [])
                new_coldkey = next((a['value'] for a in args if a['name'] == 'new_coldkey'), None)
                from_coldkey = ex.value.get('address', None)
                print(f"Swap scheduled: from {from_coldkey} to {new_coldkey}")
                
                try:
                    subnet_infos = self.subtensor.all_subnets()
                    owner_coldkeys = [subnet_info.owner_coldkey for subnet_info in subnet_infos]
                    subnet_id = owner_coldkeys.index(from_coldkey)
                    event_info = {
                        'event_type': COLDKEY_SWAP_EVENT_TYPE,
                        'old_coldkey': from_coldkey,
                        'new_coldkey': new_coldkey,
                        'subnet': subnet_id,
                    }
                    
                    events.append(event_info)
                except ValueError:
                    print(f"From coldkey {from_coldkey} not found in owner coldkeys")

            if (
                call.get('call_module') == 'SubtensorModule' and
                call.get('call_function') == 'set_subnet_identity'
            ):
                
                # Get the new coldkey from call_args
                address = ex.value.get('address', None)
                # To get the old identity, use the current subnet identity from subnet_infos[subnet_id].
                # To get the new identity, get from call_args['subnet_name'].
                try:
                    subnet_infos = self.subtensor.all_subnets()
                    owner_coldkeys = [subnet_info.owner_coldkey for subnet_info in subnet_infos]
                    subnet_id = owner_coldkeys.index(address)
                    old_identity = subnet_infos[subnet_id].subnet_name
                    call_args = call.get('call_args', [])
                    new_identity = next((a['value'] for a in call_args if a['name'] == 'subnet_name'), None)
                    event_info = {
                        'event_type': IDENTITY_CHANGE_EVENT_TYPE,
                        'subnet': subnet_id,
                        'old_identity': old_identity,
                        'new_identity': new_identity,
                    }
                    events.append(event_info)
                except ValueError:
                    print(f"Address {address} not found in owner coldkeys")

        return events

    def _balance_rao(self, bal) -> int:
        if isinstance(bal, int):
            return bal
        r = getattr(bal, "rao", None)
        if r is not None:
            return int(r)
        return int(bal)

    def sn28_stake_all_amount_rao(self) -> int:
        """
        StakeWrap debits the contract’s Substrate free balance (AccountId32 from EVM address).
        Use all of it minus existential deposit and reserve, capped by sn28 TAO pool (contract check).
        """
        contract_ss58 = h160_to_ss58(self.stake_contract_address)
        free_rao = self._balance_rao(self.subtensor.get_balance(contract_ss58))
        ed_rao = self._balance_rao(self.subtensor.get_existential_deposit())

        available = free_rao - ed_rao - self.sn28_stake_reserve_rao
        if available <= 0:
            return 0

        subnet = self.subtensor.subnet(netuid=SN28_NETUID)
        pool_rao = self._balance_rao(subnet.tao_in)
        return min(available, pool_rao)
 
    def run(self):
        while True:
            try:
                events = self.fetch_extrinsic_data(self.last_checked_block)
                if len(events) > 0:
                    try:
                        self.process_events(events)
                    except Exception as e:
                        print(f"Error sending message: {e}")
                else:
                    print("No coldkey swaps found")
            except Exception as e:
                print(f"Error fetching coldkey swaps: {e}")
                time.sleep(1)


    def process_events(self, events):
        for event in events:
            event_type = event["event_type"]
            subnet = event["subnet"]
            if event_type != IDENTITY_CHANGE_EVENT_TYPE or subnet != SN28_NETUID:
                continue

            amount_rao = self.sn28_stake_all_amount_rao()
            if amount_rao <= 0:
                print(
                    f"SN28 mempool identity change: "
                    f"{event.get('old_identity')!r} -> {event.get('new_identity')!r} — "
                    f"skip stake: no spendable balance on contract coldkey "
                    f"(reserve {self.sn28_stake_reserve_rao} rao + ED after subtracting from free)"
                )
                continue

            print(
                f"SN28 mempool identity change: "
                f"{event.get('old_identity')!r} -> {event.get('new_identity')!r} "
                f"(staking all available: {amount_rao} rao via StakeWrap)"
            )
            stake(
                self.web3,
                self.evm_account,
                self.stake_contract_address,
                self.sn28_hotkey_ss58,
                SN28_NETUID,
                amount_rao,
            )


if __name__ == "__main__":
    fetcher = ColdkeySwapFetcherFromMemPool()
    fetcher.run()