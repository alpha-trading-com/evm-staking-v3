import os

from dotenv import load_dotenv

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))

DEFAULT_HOTKEY = "5Gq2gs4ft5dhhjbHabvVbAhjMCV2RgKmVJKAFCUWiirbRT21"

STAKE_INFO_BASE_FEE_RAO = 105612   # 0.1 TAO tip used for MevShield announce_next_key (stake-info)
LIMIT_PRICE_BASE_FEE_RAO = 105611  # 0.1 TAO tip used for MevShield announce_next_key (limit-price)
XOR_KEY = 0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef
MAX_DELEGATE_BALANCE_RAO = 2 * 10**9
LIMIT_PRICE_SCALE = 10000
MAX_NETUID = 129
RAO = 10**9
BLOCK_CYCLE = 4
EXECUTOR_ENABLED_FILENAME = "executor_enabled.json"


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


# SS58 coldkeys — required in .env (must match StakeWrapConstants).
STAKE_INFO_DELEGATE = _require_ss58_env("STAKE_INFO_DELEGATE")
LIMIT_PRICE_DELEGATE = _require_ss58_env("LIMIT_PRICE_DELEGATE")
# On-chain delegates (must match StakeWrapConstants): STAKE_INFO = delegate_1, LIMIT_PRICE = delegate_2.
# Bittensor wallet names (~/.bittensor/wallets/<name>); coldkey SS58 must match STAKE_INFO_DELEGATE / LIMIT_PRICE_DELEGATE.
DELETEGATE_1 = _require_env_str(
    "DELETEGATE_1",
    "wallet name for stake-info delegate; SS58 must match STAKE_INFO_DELEGATE",
)
DELETEGATE_2 = _require_env_str(
    "DELETEGATE_2",
    "wallet name for limit-price delegate; SS58 must match LIMIT_PRICE_DELEGATE",
)

