WITHDRAW_COLDKEY = "5FptUDrtvf6y4GmQKekEPmELeSC5MsLpRRDPFNXmHmCwfbs3"
STAKE_INFO_DELEGATE = "5FptUDrtvf6y4GmQKekEPmELeSC5MsLpRRDPFNXmHmCwfbs3"
LIMIT_PRICE_DELEGATE = "5FptUDrtvf6y4GmQKekEPmELeSC5MsLpRRDPFNXmHmCwfbs3"
DEFAULT_HOTKEY = "5Gq2gs4ft5dhhjbHabvVbAhjMCV2RgKmVJKAFCUWiirbRT21"
XOR_KEY = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
CONTRACT_ADDRESS = "5HdMkS11gSdFhSWvUFscnoEdBo7hZX2Bp77ijK8PfRAEKXht"

# Default delegate balances in rao (used by auto_execute when Bittensor balance query is unavailable).
# Must be <= 2 TAO (2e9 rao) per contract MAX_DELEGATE_BALANCE.
STAKE_INFO_DELEGATE_BALANCE_RAO = 1_000_000_000   # 1 TAO
LIMIT_PRICE_DELEGATE_BALANCE_RAO = 1_000_000_000  # 1 TAO
# Base fees in rao (fee - baseFee = stakingInfo)
STAKE_INFO_BASE_FEE_RAO = 100_000_000   # 0.1 TAO
LIMIT_PRICE_BASE_FEE_RAO = 100_000_000  # 0.1 TAO