"""
Real constants: protocol / math values that MUST match the on-chain
StakeWrapConstants (XOR_KEY, LIMIT_PRICE_SCALE, MAX_NETUID, RAO, BLOCK_CYCLE,
delegate balance cap). Do not change without redeploying the contract with
matching values.

Deployment-specific, env-driven settings live in bt_utils.config.
"""

XOR_KEY = 0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef
MAX_DELEGATE_BALANCE_RAO = 2 * 10**9
LIMIT_PRICE_SCALE = 10000
MAX_NETUID = 129
RAO = 10**9
BLOCK_CYCLE = 4

# Fixed internal filename (not deployment-specific).
EXECUTOR_ENABLED_FILENAME = "executor_enabled.json"
