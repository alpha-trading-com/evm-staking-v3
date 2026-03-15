import bittensor as bt

TAO_TO_RAO = 1_000_000_000

def sim_swap(
    subtensor: bt.Subtensor,
    origin_netuid: int,
    destination_netuid: int,
    amount: float
) -> float:
    if origin_netuid == 0:
        amount = int(amount * TAO_TO_RAO)
        query = subtensor.substrate.runtime_call(
            api="SwapRuntimeApi",
            method="sim_swap_tao_for_alpha",
            params=[destination_netuid, amount]
        )
        decoded = query.decode()

        return decoded
    elif destination_netuid == 0:
        amount = int(amount * TAO_TO_RAO)
        query = subtensor.substrate.runtime_call(
            api="SwapRuntimeApi",
            method="sim_swap_alpha_for_tao",
            params=[origin_netuid, amount]
        )
        decoded = query.decode()
        return decoded
    else:
        raise ValueError("Invalid netuid")

if __name__ == "__main__":
    subtensor = bt.Subtensor(network="finney")
    print(sim_swap(subtensor, 0, 30, 10))
    print(sim_swap(subtensor, 30, 0, 1000000))


