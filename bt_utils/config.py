"""
Configurable values (deployment-specific, sourced from the environment / .env).

Kept separate from bt_utils.constants, which holds immutable protocol constants.
Delegate coldkeys and wallet names must match the deployed contract; the default
hotkey is tunable per deployment. The MevShield base fees are not configured here:
they are computed live from the chain (bt_utils.fast_stake_unstake.compute_base_fees_rao).
"""
import os

from dotenv import load_dotenv

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))


def _require_ss58_env(name: str) -> str:
    """SS58 delegate coldkey from environment or .env; must match StakeWrapConstants on-chain."""
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        raise RuntimeError(
            f"{name} is not set. Add it to .env (SS58 address); must match the deployed StakeWrap delegate constants."
        )
    return str(raw).strip()


def _require_env_str(name: str, hint: str) -> str:
    """Non-empty string from environment or .env."""
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        raise RuntimeError(f"{name} is not set. Add it to .env ({hint}).")
    return str(raw).strip()


EXECUTE_HOTKEY = os.getenv("EXECUTE_HOTKEY", "5Gq2gs4ft5dhhjbHabvVbAhjMCV2RgKmVJKAFCUWiirbRT21").strip()

STAKE_INFO_DELEGATE = _require_ss58_env("STAKE_INFO_DELEGATE")
LIMIT_PRICE_DELEGATE = _require_ss58_env("LIMIT_PRICE_DELEGATE")
DELEGATE_1 = _require_env_str(
    "DELEGATE_1",
    "wallet name for stake-info delegate; SS58 must match STAKE_INFO_DELEGATE",
)
DELEGATE_2 = _require_env_str(
    "DELEGATE_2",
    "wallet name for limit-price delegate; SS58 must match LIMIT_PRICE_DELEGATE",
)
