# auto-execute-rs

Rust reimplementation of `bt_utils/auto_execute.py`: on each new Bittensor block, call the StakeWrap contract’s `execute(execBlock, packedBalances)` on the EVM (base fees are contract constants).

**Why Rust:** Lower latency (see block → build and send tx with minimal overhead), single binary, no Python runtime.

## Status

- **EVM side:** Implemented (ethers-rs: connect, build execute calldata, sign, send). Uses same env as Python: `RPC_URL`, `EXECUTOR_PRIVATE_KEY` or `PRIVATE_KEY`, `EXECUTOR_GAS_LIMIT`, `EXECUTOR_GAS_PRICE_MULTIPLIER`, `deployment.json`.
- **Bittensor side:** **Block only.** Current block is fetched via WebSocket `chain_getHeader` (same as Python). Delegate balances are not implemented; `get_bittensor_block_and_balances()` fetches the block then returns an error. You can:
  1. **Implement it in Rust** using [subxt](https://docs.rs/subxt) with Bittensor/Finney metadata to query current block and `Balances::Account` for the two delegate SS58 addresses, or use raw JSON-RPC (`chain_getBlock`, and balance storage keys).
  2. **Keep using the Python script** (`python3 bt_utils/auto_execute.py`) which already has Bittensor support via the `bittensor` crate.

## Build and run

From the **repo root** (so `deployment.json` and `.env` are found):

```bash
cd auto_execute_rs
cargo build --release
# Run from repo root so deployment.json path is correct:
cd .. && ./auto_execute_rs/target/release/auto-execute-rs
```

Or run from `auto_execute_rs` with `CARGO_MANIFEST_DIR` parent = repo root (the code uses `env!("CARGO_MANIFEST_DIR")` to locate `deployment.json` and `executor_enabled.json`).

**Test block fetch only (no EVM, no balances):**

```bash
cargo run --bin get_block
```

Uses `BITTENSOR_WS_URL` (default: Finney entrypoint) and prints the current Bittensor block.

## Env and config

Same as the Python script:

- `RPC_URL` – EVM RPC (contract chain).
- `EXECUTOR_PRIVATE_KEY` or `PRIVATE_KEY` – signer for `execute()`.
- `BITTENSOR_NETWORK` – e.g. `finney` (used once balance query is implemented).
- `BITTENSOR_WS_URL` – optional; WebSocket URL for Bittensor (default: Finney entrypoint). Used for `chain_getHeader` block fetch.
- `EXECUTOR_GAS_LIMIT`, `EXECUTOR_GAS_PRICE_MULTIPLIER` – optional.
- `executor_enabled.json` in repo root – read each block; if `enabled: false`, do not send the tx.

Optional: `STAKE_INFO_DELEGATE_SS58` and `LIMIT_PRICE_DELEGATE_SS58` (defaults in code).
