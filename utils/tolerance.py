import bittensor as bt
from bittensor import Balance

from app.core.config import settings
from typing import Union, Optional
from utils.sim_swap import sim_swap, TAO_TO_RAO



def get_stake_min_tolerance(tao_amount: float, netuid: int, subtensor: Optional[bt.Subtensor] = None) -> float:
    return get_stake_min_tolerance_v2(tao_amount, netuid, subtensor)

def get_stake_min_tolerance_v1(tao_amount: float, netuid: int, subtensor: Optional[bt.Subtensor] = None) -> float:
    """
    Calculate the minimum tolerance for staking operations.
    
    Args:
        tao_amount: Amount in TAO
        netuid: Network/subnet ID
        subtensor: Optional Subtensor instance. If not provided, creates one using settings.NETWORK
        
    Returns:
        float: Minimum tolerance value
        
    Raises:
        ValueError: If subnet with netuid does not exist
    """
    if subtensor is None:
        subtensor = bt.Subtensor(network=settings.NETWORK)
    
    subnet = subtensor.subnet(netuid=netuid)
    if subnet is None:
        raise ValueError(f"Subnet with netuid {netuid} does not exist")
    
    min_tolerance = tao_amount / subnet.tao_in.tao
    return min_tolerance


def get_stake_min_tolerance_v2(tao_amount: float, netuid: int, subtensor: Optional[bt.Subtensor] = None) -> float:
    if subtensor is None:
        subtensor = bt.Subtensor(network=settings.NETWORK)
    subnet = subtensor.subnet(netuid=netuid)
    sim_swap_result = sim_swap(subtensor, 0, netuid, tao_amount)
    
    if subnet is None:
        raise ValueError(f"Subnet with netuid {netuid} does not exist")
    
    deviation = subnet.price.tao - subnet.tao_in.tao / subnet.alpha_in.tao

    tao_amount_after = subnet.tao_in.tao + tao_amount - sim_swap_result["tao_fee"] / TAO_TO_RAO
    alpha_amount_after = subnet.alpha_in.tao - sim_swap_result["alpha_amount"] / TAO_TO_RAO
    limit_price = (tao_amount_after / alpha_amount_after) + deviation
    reference_price = subnet.price.tao
    if reference_price == 0:
        raise ValueError("Reference price cannot be zero for tolerance calculation.")

    tolerance = (limit_price / reference_price) - 1
    return tolerance

def get_unstake_min_tolerance(tao_amount: float, netuid: int, subtensor: Optional[bt.Subtensor] = None) -> float:
    """
    Calculate the minimum tolerance for unstaking operations.
    
    Args:
        tao_amount: Amount in TAO
        netuid: Network/subnet ID
        subtensor: Optional Subtensor instance. If not provided, creates one using settings.NETWORK
        
    Returns:
        float: Minimum tolerance value
        
    Raises:
        ValueError: If subnet with netuid does not exist
    """
    if subtensor is None:
        subtensor = bt.Subtensor(network=settings.NETWORK)
    
    subnet = subtensor.subnet(netuid=netuid)
    if subnet is None:
        raise ValueError(f"Subnet with netuid {netuid} does not exist")
    
    min_tolerance = tao_amount / (tao_amount + subnet.alpha_in.tao)
    return min_tolerance


def calculate_stake_limit_price(
    tao_amount: float,
    netuid: int,
    min_tolerance_staking: bool,
    default_rate_tolerance: float,
    subtensor: Optional[bt.Subtensor] = None,
    tolerance_offset: Optional[Union[float, str]] = None
) -> int:
    """
    Calculate the rate tolerance for staking operations.
    If min_tolerance_staking is True, calculates minimum tolerance.
    - If TOLERANCE_OFFSET starts with '*', multiplies min_tolerance by that value
    - Otherwise, adds TOLERANCE_OFFSET to min_tolerance
    Otherwise, returns the default_rate_tolerance.
    
    Args:
        tao_amount: Amount in TAO
        netuid: Network/subnet ID
        min_tolerance_staking: Whether to use minimum tolerance
        default_rate_tolerance: Default tolerance value to use if not using min tolerance
        subtensor: Optional Subtensor instance. If not provided, creates one using settings.NETWORK
        tolerance_offset: Tolerance offset value
        
    Returns:
        int: Limit price value
    """
    if tolerance_offset is None:
        tolerance_offset = settings.TOLERANCE_OFFSET
    print(f"Tolerance offset: {tolerance_offset}")
    if netuid == 0:
        return TAO_TO_RAO + 1

    if not min_tolerance_staking:
        if default_rate_tolerance > 0.89:
            return TAO_TO_RAO + 1

    if subtensor is None:
        subtensor = bt.Subtensor(network=settings.NETWORK)
    
    subnet = subtensor.subnet(netuid=netuid)

    tolerance = default_rate_tolerance
    print(f"Tolerance: {tolerance}")
    print(min_tolerance_staking)
    if min_tolerance_staking:
        deviation = subnet.price.tao - subnet.tao_in.tao / subnet.alpha_in.tao      
        sim_swap_result = sim_swap(subtensor, 0, netuid, tao_amount)

        tao_amount_after = subnet.tao_in.tao + tao_amount - sim_swap_result["tao_fee"] / TAO_TO_RAO
        alpha_amount_after = subnet.alpha_in.tao - sim_swap_result["alpha_amount"] / TAO_TO_RAO
        limit_price = (tao_amount_after / alpha_amount_after) + deviation
        reference_price = subnet.price.tao

        min_tolerance = (limit_price / reference_price) - 1
        if isinstance(tolerance_offset, str) and tolerance_offset.startswith('*'):
            multiplier = float(tolerance_offset[1:])
            tolerance = min_tolerance * multiplier
            print(f"Multiplier: {multiplier}")
            print(f"Tolerance: {tolerance}")
        else:
            tolerance = min_tolerance + float(tolerance_offset)
  
    rate = 1 / subnet.price.tao or 1
    _rate_with_tolerance = rate * (
        1 + tolerance
    )  # Rate only for display
    price_with_tolerance = subnet.price.rao * (
        1 + tolerance
    )
    return price_with_tolerance
 

def calculate_unstake_limit_price(
    tao_amount: float,
    netuid: int,
    min_tolerance_unstaking: bool,
    default_rate_tolerance: float,
    subtensor: Optional[bt.Subtensor] = None,
    tolerance_offset: Optional[Union[float, str]] = None
) -> int:
    """
    Calculate the rate tolerance for unstaking operations.
    If min_tolerance_unstaking is True, calculates minimum tolerance.
    - If TOLERANCE_OFFSET starts with '*', multiplies min_tolerance by that value
    - Otherwise, adds TOLERANCE_OFFSET to min_tolerance
    Otherwise, returns the default_rate_tolerance.
    
    Args:
        tao_amount: Amount in TAO
        netuid: Network/subnet ID
        min_tolerance_unstaking: Whether to use minimum tolerance
        default_rate_tolerance: Default tolerance value to use if not using min tolerance
        subtensor: Optional Subtensor instance. If not provided, creates one using settings.NETWORK
        tolerance_offset: Tolerance offset to use for unstaking operations 
    Returns:
        int: Limit price value
    """
    if tolerance_offset is None:
        tolerance_offset = settings.TOLERANCE_OFFSET

    if netuid == 0:
        return 1

    if not min_tolerance_unstaking:
        if default_rate_tolerance > 0.89:
            return 1
        
    tolerance = default_rate_tolerance
    if min_tolerance_unstaking:
        min_tolerance = get_unstake_min_tolerance(tao_amount, netuid, subtensor)
        if isinstance(tolerance_offset, str) and tolerance_offset.startswith('*'):
            multiplier = float(tolerance_offset[1:])
            tolerance = min_tolerance * multiplier
        else:
            tolerance = min_tolerance + float(tolerance_offset)

    subnet = subtensor.subnet(netuid=netuid)
    rate = 1 / subnet.price.tao or 1
    _rate_with_tolerance = rate * (
        1 - tolerance
    )
    price_with_tolerance = subnet.price.rao * (
        1 - tolerance
    )
    return price_with_tolerance