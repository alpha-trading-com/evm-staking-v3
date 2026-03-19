# auto-execute-rs

Rust reimplementation of `bt_utils/auto_execute.py`: on each new Bittensor block, call the StakeWrap contract’s `execute(execBlock, packedBalances)` on the EVM (base fees are contract constants).

**Why Rust:** Lower latency (see block → build and send tx with minimal overhead), single binary, no Python runtime.

## Status

- **EVM side:** Implemented (ethers-rs: connect, build execute calldata, sign, send). Same env as Python: `RPC_URL`, `EXECUTOR_PRIVATE_KEY` or `PRIVATE_KEY`, `EXECUTOR_GAS_LIMIT`, `EXECUTOR_GAS_PRICE_MULTIPLIER`, `deployment.json`.
- **Bittensor side:** Implemented via [subxt](https://docs.rs/subxt) with generated runtime API (same approach as [agcli](https://github.com/unconst/agcli/tree/main/src)). At **build time** (`build.rs`) the crate fetches Bittensor/Finney metadata and generates type-safe storage access; at runtime we query current block and `System::Account` (free balance) for the two delegate SS58 addresses. The `get_block` binary still uses a raw WebSocket `chain_getHeader` call (no subxt) for a quick block-only test.

## Build and run

**First build** fetches Bittensor chain metadata (requires network). Set `METADATA_CHAIN_ENDPOINT` to use a different WS URL, or `SKIP_METADATA_FETCH=1` to reuse cached metadata.

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
- `BITTENSOR_NETWORK` – e.g. `finney` (informational).
- `BITTENSOR_WS_URL` – optional; WebSocket URL for Bittensor (default: Finney entrypoint). Used for subxt connection and for `get_block` binary (`chain_getHeader`).
- `EXECUTOR_GAS_LIMIT`, `EXECUTOR_GAS_PRICE_MULTIPLIER` – optional.
- `executor_enabled.json` in repo root – read each block; if `enabled: false`, do not send the tx.

Optional: `STAKE_INFO_DELEGATE_SS58` and `LIMIT_PRICE_DELEGATE_SS58` (defaults in code).
