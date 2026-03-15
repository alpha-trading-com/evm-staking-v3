import bittensor as bt
from bittensor import Balance

from rich.console import Console
from rich.table import Table
from io import StringIO

from utils.sim_swap import sim_swap, TAO_TO_RAO


def get_amount_with_sim_swap(subtensor, alpha_stake_amount, netuid):
    """
    Calculate TAO value of alpha stake using sim_swap from Bittensor SDK.
    
    Args:
        subtensor: Bittensor subtensor instance
        alpha_stake_amount: Amount of alpha tokens staked (in Balance)
        netuid: Network/subnet ID
        
    Returns:
        float: TAO amount you would receive if unstaking
    """
    if netuid == 0:
        # Root network: alpha = TAO, so value is 1:1
        return alpha_stake_amount.tao
    
    try:
        # Simulate unstaking: swap from subnet (origin) to root network (destination)
        sim_result = sim_swap(subtensor, netuid, 0, alpha_stake_amount.tao)
        # Return the TAO amount you'd receive (after fees)
        return sim_result["tao_amount"] / TAO_TO_RAO
    except Exception as e:
        print(f"Warning: sim_swap failed for netuid {netuid}: {e}")
        # Fallback to manual calculation if sim_swap fails
        subnet_info = subtensor.subnet(netuid)
        if subnet_info:
            p = subnet_info.tao_in.tao * subnet_info.alpha_in.tao
            alpha_in_after = subnet_info.alpha_in.tao + alpha_stake_amount.tao
            tao_in_after = p / alpha_in_after
            return subnet_info.tao_in.tao - tao_in_after
        return 0.0


def get_stake_list_v2(subtensor, wallet_ss58):
    stake_infos = subtensor.get_stake_info_for_coldkey(
        coldkey_ss58=wallet_ss58
    )
    subnet_infos = subtensor.all_subnets()

    # Create a Rich Table to display the stake_infos in a readable format

    table = Table(title="Stake Infos", show_lines=True)
    table.add_column("NetUID", justify="right", no_wrap=True)
    table.add_column("Subnet Name")
    table.add_column("Value (TAO)")
    table.add_column("Stake (Alpha)", justify="right")
    table.add_column("Price (TAO/Alpha)")
    table.add_column("Hotkey SS58")

    # stake_infos is a list of StakeInfo objects
    total_value = 0
    for info in stake_infos:
        subnet_info = subnet_infos[info.netuid]
        # Use sim_swap for accurate value calculation
        value = get_amount_with_sim_swap(
            subtensor,
            info.stake,
            info.netuid
        )
        table.add_row(
            str(info.netuid),
            subnet_info.subnet_name,
            f"{value:.2f}",
            f"{info.stake.tao:.2f}",
            f"{subnet_info.price.tao:.4f}",
            info.hotkey_ss58,
        )
        total_value += value



    balance = subtensor.get_balance(wallet_ss58)
    total_value = Balance.from_tao(total_value)
    
    console = Console(file=StringIO(), force_terminal=False)
    console.print(table)
    console.print("\n")
    console.print(
        f"Wallet:\n"
        f"  Coldkey SS58: {wallet_ss58}\n"
        f"  Free Balance: {balance}\n"
        f"  Total Staked Value : {total_value}\n"
        f"  Total Value : {total_value + balance}"
    )

    table_str = console.file.getvalue()
    return table_str
    

if __name__ == "__main__":
    subtensor = bt.Subtensor("finney")
    wallet_ss58 = "5F5WLLEzDBXQDdTzDYgbQ3d3JKbM15HhPdFuLMmuzcUW5xG2"
    stake_list = get_stake_list(subtensor, wallet_ss58)    
    print(stake_list)
    

