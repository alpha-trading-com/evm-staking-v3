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




STAKE_INFO_DELEGATE = "5GF98kTXSaGPRE5wMJfjqZ5kooMMzvZRpbaQ7YEawxaCQyZk"
LIMIT_PRICE_DELEGATE = "5H3MFE2fg4FTRRcReET1uzAVLLzVBeJnzxgHw63nZxtGwWtk"
# On-chain delegates (must match StakeWrapConstants): STAKE_INFO = delegate_1, LIMIT_PRICE = delegate_2.
# Wallet names for proxy/MevShield ops; coldkey SS58 must match the strings above (or override names via DELETEGATE_1 / DELETEGATE_2 in .env).
DELETEGATE_1 = os.getenv("DELETEGATE_1", "proxy").strip() or "proxy"
DELETEGATE_2 = os.getenv("DELETEGATE_2", "test_proxy").strip() or "test_proxy"

