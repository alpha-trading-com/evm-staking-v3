"""
Synchronous fast stake / unstake (MevShield) using SubstrateInterface.

Mirrors bt_utils.fast_stake_unstake_async for use outside an asyncio event loop.
"""
import os
import sys
from dotenv import load_dotenv
from typing import Optional, Tuple

from scalecodec import GenericExtrinsic
from async_substrate_interface.sync_substrate import SubstrateInterface
from app.core.config import settings

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

load_dotenv(os.path.join(_REPO_ROOT, ".env"))

import bittensor as bt

from bt_utils.constants import (
    LIMIT_PRICE_SCALE,
    MAX_NETUID,
    RAO,
    DELEGATE_1,
    DELEGATE_2,
    BLOCK_CYCLE,
)


_wallet1: bt.Wallet | None = None
_wallet2: bt.Wallet | None = None


def _delegate_wallets() -> tuple[bt.Wallet, bt.Wallet]:
    """Load and decrypt DELEGATE_1 / DELEGATE_2 coldkeys once."""
    global _wallet1, _wallet2
    if _wallet1 is None:
        _wallet1 = bt.Wallet(name=DELEGATE_1)
        _wallet2 = bt.Wallet(name=DELEGATE_2)
        _wallet1.coldkey_file.save_password_to_env(os.getenv("DELEGATE_1_PASSWORD"))
        _wallet2.coldkey_file.save_password_to_env(os.getenv("DELEGATE_2_PASSWORD"))
        _wallet1.coldkey_file.decrypt()
        _wallet2.coldkey_file.decrypt()
    return _wallet1, _wallet2

_delegate_wallets()

def get_extrinsic_fee_for_tip(
    substrate: SubstrateInterface,
    wallet: bt.Wallet,
    tip_rao: int,
) -> dict:
    """
    Compute total fee (inclusion fee + tip) for a MevShield announce_next_key extrinsic with the given tip.

    Returns a dict with keys (all in RAO):
      - inclusion_fee_rao, tip_rao, total_fee_rao
    """
    call = substrate.compose_call(
        call_module="System",
        call_function="set_heap_pages",
        call_params={"pages": 0},
    )
    if settings.USE_ERA:
        payment = substrate.get_payment_info(
            call=call,
            keypair=wallet.coldkey,
            tip=tip_rao,
            era={"period": 1},
        )
    else:
        payment = substrate.get_payment_info(
            call=call,
            keypair=wallet.coldkey,
            tip=tip_rao,
        )
    inclusion_rao = int(
        payment.get("partial_fee") or payment.get("partialFee") or 0
    )
    return {
        "inclusion_fee_rao": inclusion_rao,
        "tip_rao": tip_rao,
        "total_fee_rao": inclusion_rao + tip_rao,
    }


def get_info_extrinsic(
    substrate: SubstrateInterface,
    wallet: bt.Wallet,
    info: int,
) -> GenericExtrinsic:
    """Build signed MevShield announce_next_key extrinsic with tip=info."""
    call = substrate.compose_call(
        call_module="System",
        call_function="set_heap_pages",
        call_params={"pages": 0},
    )
    if settings.USE_ERA:
        extrinsic = substrate.create_signed_extrinsic(
            call=call,
            keypair=wallet.coldkey,
            tip=info,
            era={"period": 1},
        )
    else:
        extrinsic = substrate.create_signed_extrinsic(
            call=call,
            keypair=wallet.coldkey,
            tip=info,
        )
    return extrinsic


def submit_extrinsic(
    substrate: SubstrateInterface,
    extrinsic: GenericExtrinsic,
    wait_for_inclusion: bool = True,
) -> Tuple[bool, str]:
    """Submit one extrinsic. Returns (success, error_message)."""
    try:
        receipt = substrate.submit_extrinsic(
            extrinsic,
            wait_for_inclusion=wait_for_inclusion,
            wait_for_finalization=False,
        )
        if wait_for_inclusion:
            ok = receipt.is_success
            err = receipt.error_message
            msg = str(err) if err else ""
            return bool(ok), msg
        return True, ""
    except Exception as e:
        return False, str(e)


def send_stake_info(
    substrate: SubstrateInterface,
    wallet1: bt.Wallet,
    wallet2: bt.Wallet,
    stake_info: int,
    limit_price: Optional[int] = None,
) -> Tuple[bool, str]:
    """Submit stake_info (and optionally limit_price) via MevShield. Returns (success, message)."""
    if limit_price is None:
        extrinsic = get_info_extrinsic(substrate, wallet1, stake_info)
        return submit_extrinsic(substrate, extrinsic, wait_for_inclusion=True)

    extrinsic1 = get_info_extrinsic(substrate, wallet1, stake_info)
    extrinsic2 = get_info_extrinsic(substrate, wallet2, limit_price)
    # Same ordering intent as async gather: fire no-wait submit, then wait on stake_info path.
    ok2, msg2 = submit_extrinsic(substrate, extrinsic2, wait_for_inclusion=False)
    ok1, msg1 = submit_extrinsic(substrate, extrinsic1, wait_for_inclusion=True)
    success = ok1 and ok2
    message = "ok" if success else f"stake_info={msg1}; limit_price={msg2}"
    return success, message



def _sync_substrate() -> SubstrateInterface:
    return SubstrateInterface(
        url=settings.NETWORK,
        ss58_format=42,
        type_registry_preset="substrate-node-template"
    )


def fast_stake(
    netuid: int,
    amount_rao: int,
    limit_price: int | None = None,
) -> Tuple[bool, str]:
    """Submit fast stake (MevShield). Returns (success, message)."""
    if amount_rao == 0:
        return True, "Amount is 0"

    wallet1, wallet2 = _delegate_wallets()
    substrate = _sync_substrate()
    try:
        amount_tao = amount_rao / RAO

        if limit_price is None:
            stake_info = netuid + MAX_NETUID * (amount_tao * 2)
            limit_info = None
        else:
            stake_info = netuid + MAX_NETUID * (amount_tao * 2 - 1)
            limit_price_scaled = int((limit_price + LIMIT_PRICE_SCALE - 1) / LIMIT_PRICE_SCALE)
            limit_info = limit_price_scaled * BLOCK_CYCLE + 1

        stake_info_encoded = stake_info * BLOCK_CYCLE + 1
        return send_stake_info(
            substrate,
            wallet1,
            wallet2,
            stake_info_encoded,
            limit_info,
        )
    finally:
        substrate.close()


def fast_unstake(netuid: int) -> Tuple[bool, str]:
    """Submit fast unstake (MevShield). Returns (success, message)."""
    wallet1, wallet2 = _delegate_wallets()
    substrate = _sync_substrate()
    try:
        stake_info = netuid * BLOCK_CYCLE + 1
        return send_stake_info(substrate, wallet1, wallet2, stake_info, None)
    finally:
        substrate.close()


if __name__ == "__main__":
    success, message = fast_stake(127, 1 * 10**9, int(0.008 * 10**9))
    print(success, message)
