import bittensor as bt
from bittensor import Balance

from rich.console import Console
from rich.table import Table
from io import StringIO


def get_amount(tao_in, alpha_in, alpha_unstake_amount, netuid):
    if netuid == 0:
        return alpha_unstake_amount
    
    p = tao_in * alpha_in
    alpha_in_after = alpha_in + alpha_unstake_amount
    tao_in_after = p / alpha_in_after
    return tao_in - tao_in_after


def get_stake_list(subtensor, wallet_ss58):
    stake_infos = subtensor.get_stake_info_for_coldkey(
        coldkey_ss58=wallet_ss58
    )
    subnet_infos = subtensor.all_subnets()

    # Create a Rich Table to display the stake_infos in a readable format

    table = Table(title="Stake Infos", show_lines=True)
    table.add_column("NetUID", justify="right", no_wrap=True)
    table.add_column("Subnet Name")
    table.add_column("Value")
    table.add_column("Stake", justify="right")
    table.add_column("Price")
    table.add_column("Hotkey SS58")

    # stake_infos is a list of StakeInfo objects
    total_value = 0
    for info in stake_infos:
        subnet_info = subnet_infos[info.netuid]
        value = get_amount(
            subnet_info.tao_in.tao, 
            subnet_info.alpha_in.tao, 
            info.stake.tao,
            info.netuid)
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
    

