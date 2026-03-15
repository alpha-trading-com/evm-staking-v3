# Tolerance-Based Staking UI

The StakeWrap UI now integrates with `utils/tolerance.py` to provide tolerance-based staking controls, matching the UX pattern from [alpha-trading-com/staking](https://github.com/alpha-trading-com/staking).

## Features

### Rate Tolerance Instead of Raw Limit Price
- **Stake Limit** and **Unstake Limit** panels now accept **Rate Tolerance** (e.g., `0.5` = 50% slippage) instead of raw `limit_price` in rao per alpha.
- The backend automatically calculates `limit_price` using:
  - `utils.tolerance.calculate_stake_limit_price()` for staking
  - `utils.tolerance.calculate_unstake_limit_price()` for unstaking

### Use Minimum Tolerance
- Checkbox: **Use Minimum Tolerance** 
- When checked, the backend fetches real-time subnet data from Bittensor Subtensor and calculates the minimal safe tolerance for the transaction.
- Rate Tolerance field is ignored when this is enabled.

### Calculate Min Tolerance Button
- **Calculate Min Tolerance** button calls `/api/calc-min-tolerance` to preview the calculated `limit_price` before submitting.
- Useful for understanding what limit price will be used for your transaction.

## API Changes

### `POST /api/stake-limit`
**Body:**
```json
{
  "hotkey": "5Gq2gs4ft5dhhjbHabvVbAhjMCV2RgKmVJKAFCUWiirbRT21",
  "netuid": 27,
  "amount_tao": 60.0,
  "rate_tolerance": 0.5,
  "use_min_tolerance": false,
  "allow_partial": false
}
```

**Optional:** You can still pass `limit_price` directly to override tolerance calculation:
```json
{
  "hotkey": "...",
  "netuid": 27,
  "amount_tao": 60.0,
  "limit_price": 1000000000,
  "allow_partial": false
}
```

### `POST /api/remove-stake-limit`
Same pattern as stake-limit but for unstaking.

### `POST /api/calc-min-tolerance`
Preview the minimum tolerance calculation:
```json
{
  "tao_amount": 60.0,
  "netuid": 27,
  "operation": "stake"
}
```

**Response:**
```json
{
  "ok": true,
  "limit_price": 1050000000,
  "operation": "stake"
}
```

## Dependencies

The tolerance features require:
- `bittensor` Python package (for Subtensor connection)
- `utils/tolerance.py` (already in repo)
- Network access to Bittensor Subtensor RPC

If `utils.tolerance` cannot be imported, the UI falls back to requiring raw `limit_price` input.

## UI Flow (Matching alpha-trading-com/staking)

1. **User enters:**
   - Validator Hotkey
   - Network ID
   - TAO Amount
   - Rate Tolerance (e.g., `0.5`)

2. **Optional: Click "Calculate Min Tolerance"** to preview the calculated limit price

3. **Optional: Check "Use Minimum Tolerance"** to automatically use the safest tolerance (rate tolerance field ignored)

4. **Click "Stake"** → Backend calls `calculate_stake_limit_price()` and submits transaction

## Running the Server

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
./run_server.sh
# or
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Navigate to: `http://localhost:8000/ui`

## Notes

- **Rate Tolerance** = fractional slippage (0.5 = 50% above/below spot price)
- **Stake** operations allow paying up to `spot * (1 + tolerance)` rao per alpha
- **Unstake** operations accept at least `spot * (1 - tolerance)` rao per alpha
- The existing CLI (`scripts/interact.py`) still works with `--limit-price` as before

