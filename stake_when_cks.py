import bittensor as bt
import time
import threading


COLDKEY_SWAP_EVENT_TYPE = "COLDKEY_SWAP"
IDENTITY_CHANGE_EVENT_TYPE = "IDENTITY_CHANGE"
COLDKEY_SWAP_FINISHED_EVENT_TYPE = "COLDKEY_SWAP_FINISHED"
DEREGISTERED_EVENT_TYPE = "DEREGISTERED"

NETWORK = "finney"

class ColdkeySwapFetcherFromMemPool:
    def __init__(self):
        self.subtensor = bt.Subtensor(NETWORK)
        self.subtensor_finney = bt.Subtensor("finney")

        self.last_checked_block = self.subtensor.get_current_block()
        self.subnet_names = []
        self.owner_coldkeys = []
        self.cache = []
  
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
 
    def run(self):
        while True:
            try:
                events = self.fetch_extrinsic_data(self.last_checked_block)
                if len(events) > 0:
                    try:
                        message = self.format_message(events)
                        send_webhook_message(
                            webhook_url=WEBHOOK_URL_SS_EVENTS,
                            content=message
                        )
                        # threading.Timer(30, lambda: send_webhook_message(
                        #     webhook_url=WEBHOOK_URL_AETH_CHAIN_EVENT,
                        #     content=message
                        # )).start()
                    except Exception as e:
                        print(f"Error sending message: {e}")
                else:
                    print("No coldkey swaps found")
            except Exception as e:
                print(f"Error fetching coldkey swaps: {e}")
                time.sleep(1)


    def format_message(self, events):
        message = "Hey @everyone! Mempool events:\n"
        for event in events:
            if event['event_type'] == COLDKEY_SWAP_EVENT_TYPE:
                message += f"Subnet {event['subnet']} is swapping coldkey from {event['old_coldkey']} to {event['new_coldkey']}\n"
            elif event['event_type'] == IDENTITY_CHANGE_EVENT_TYPE:
                message += f"Subnet {event['subnet']} has changed identity from {event['old_identity']} to {event['new_identity']}\n"
            elif event['event_type'] == COLDKEY_SWAP_FINISHED_EVENT_TYPE:
                message += f"Subnet {event['subnet']} has finished swapping coldkey\n"
            elif event['event_type'] == DEREGISTERED_EVENT_TYPE:
                message += f"Subnet {event['subnet']} has deregistered from the network. :cry:\n"
        return message


if __name__ == "__main__":
    fetcher = ColdkeySwapFetcherFromMemPool()
    fetcher.run()