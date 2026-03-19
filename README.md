# StakeWrap setup 

## Introduction

This staking and unstaking tool uses the same idea as MEV: a transaction submitted in the middle of a block can be injected at the start of that block. The contract and MevShield flow let you stake or unstake with that timing so your intent is applied at block start.

## Behind the scenes

We use the **MevShield.announce_next_key** extrinsic to encode stake/unstake intent in its **tip**, even if the extrinsic itself fails. Sudo-level extrinsics like this have higher priority; the block builder can include them at block start. The tip (and thus the encoded intent) is observable from the chain (e.g. delegate balance change). The StakeWrap contract’s **execute()** then runs each block and applies that intent by calling the staking precompile.

### How fast stake and fast unstake work

Two things happen in sequence: (1) your intent is encoded by submitting **MevShield.announce_next_key** with tip = encoded(netuid, amount, etc.)—the intent is encoded this way even if the extrinsic fails; (2) each block, the contract’s **execute()** runs and applies that intent by calling the staking precompile.

```mermaid
sequenceDiagram
    participant User
    participant UI as UI / API
    participant Backend as Backend (FastAPI)
    participant MevShield as Bittensor (MevShield)
    participant AutoExec as auto_execute.py
    participant Contract as StakeWrap contract
    participant IStaking as IStaking precompile

    Note over User,IStaking: 1. Encode intent via MevShield.announce_next_key (even if extrinsic fails)
    User->>UI: Fast Stake (amount, netuid) or Fast Unstake (netuid)
    UI->>Backend: POST /api/fast-stake or /api/fast-unstake
    Backend->>Backend: Encode intent as stake_info (or limit_price for limit orders)
    Backend->>MevShield: MevShield.announce_next_key(tip = encoded intent)
    Note over MevShield: Intent encoded in tip (tip from delegate).<br/>Included at block start; intent is encoded even if extrinsic fails.

    Note over User,IStaking: 2. Each block: execute() applies intent on chain
    loop Every Bittensor block
        AutoExec->>MevShield: Read delegate balances (stake-info & limit-price)
        AutoExec->>Contract: execute(execBlock, packedBalances)
        Contract->>MevShield: withdrawFromDelegate (pull TAO from delegate → contract)
        Contract->>Contract: Decode fee → (netuid, amount) or unstake or limit order
        Contract->>IStaking: addStake() / removeStake() / addStakeLimit()
        IStaking->>IStaking: Stake or unstake applied on Bittensor staking pallet
    end
```

**In short:**

| Step | What happens |
|------|----------------|
| **Intent** | You click Fast Stake (e.g. 50 TAO, netuid 1). The backend submits **MevShield.announce_next_key** with **tip** = encoded (netuid, amount). The intent is encoded in this way even if the extrinsic fails. The block builder includes it at block start; the tip is taken from the delegate wallet. |
| **Apply** | `auto_execute.py` runs every block. It reads the two delegate balances, calls the contract’s **execute()**. The contract pulls TAO from the delegate, decodes the “fee” (the tip that was consumed) to recover (netuid, amount), then calls the **IStaking** precompile to perform addStake, removeStake, or addStakeLimit. |

Fast **unstake** uses the same flow with a different encoding (stake_info = netuid only, meaning “unstake all for this netuid”). Fast **stake limit** uses both delegates: one tip encodes (netuid, amount), the other encodes the limit price.

## Prerequisites

- **Node.js** and **npm** (for Hardhat contract compile)
- **Python 3.10+** with venv recommended
- **Bittensor** wallets for delegates and (optionally) proxy

## 1. Python environment

From the project root:

```bash
python3 -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## 2. Environment (.env)

Create a `.env` file in the project root. Required and optional variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `PRIVATE_KEY` | Yes | EVM private key (hex, no 0x) used to deploy and as contract owner; also used by the UI for stake/unstake/withdraw |
| `EXECUTOR_PRIVATE_KEY` | No | Optional separate key for auto_execute; avoids nonce conflict with owner (see Executor below) |
| `EXECUTOR_GAS_LIMIT` | No | Gas limit for execute() txs in auto_execute (default: 600000). Lower = cheaper if the chain uses less. |
| `RPC_URL` | No | EVM RPC (default: `https://test.finney.opentensor.ai/`) |
| `BITTENSOR_NETWORK` | No | Bittensor network for auto_execute (default: `finney`) |

Example:

```
PRIVATE_KEY=your_hex_private_key
RPC_URL=https://test.finney.opentensor.ai/
BITTENSOR_NETWORK=finney
```

## 3. Delegate wallets and withdraw coldkey

- **Execute flow:** The contract’s `execute()` uses two delegate addresses (stake-info and limit-price). Their **free balance on the Bittensor chain must not exceed 2 TAO** (enforced in the contract).
- **Constants in contract:** In `contracts/StakeWrapConstants.sol` set `STAKE_INFO_DELEGATE` and `LIMIT_PRICE_DELEGATE` (bytes32) to your two delegate coldkeys. Set `WITHDRAW_COLDKEY` to a **separate** coldkey that you keep safe for withdrawals—it does not need to match the delegates; it only needs to be stored securely.
- **Fast stake/unstake (MevShield):** Uses Bittensor wallets named in `bt_utils/constants.py` (`DELETEGATE_1`, `DELETEGATE_2`; e.g. `"soon"`, `"soon_2"`). Create these under `~/.bittensor/wallets/` and fund them; do not exceed 2 TAO per delegate as above. Intent is encoded by calling **MevShield.announce_next_key** with tip = encoded(netuid, amount, etc.), even if that extrinsic fails. The base fees `STAKE_INFO_BASE_FEE_RAO` and `LIMIT_PRICE_BASE_FEE_RAO` (both 0.1 TAO) in `bt_utils/constants.py` are the tips used for that call (no extra gas fee specified).

## 4. Compile, deploy, and add contract as proxy

You can run one script from the project root that does everything:

```bash
npm install   # once, for Hardhat
python3 scripts/compile_deploy_add_proxy.py
```

This script:

1. **Compiles** the smart contract (`npm run compile`).
2. **Deploys** it (uses `PRIVATE_KEY` and `RPC_URL` from `.env`, writes `deployment.json`), then calls **setContractAccountId32** so `execute()` uses packed params (smaller calldata).
3. **Adds the contract as proxy (Any)** for the two delegate wallets (`DELETEGATE_1`, `DELETEGATE_2` from `bt_utils/constants.py`): for each wallet it removes existing proxies, then adds the contract’s SS58 as proxy. You will be prompted to unlock each coldkey.

Ensure the delegate wallets exist under `~/.bittensor/wallets/` (e.g. names `soon` and `soon_2` if that’s what you set in `bt_utils/constants.py`). To only add/update proxies and skip compile and deploy (using existing `deployment.json`):

```bash
python3 scripts/compile_deploy_add_proxy.py --skip-compile --skip-deploy
```

(You can also compile and deploy manually: `npm run compile` then `python3 scripts/deploy.py`—then add proxies separately if needed.)

**Gas:** The contract uses custom errors and packed storage to reduce gas. The two base fees (stake-info and limit-price) are contract constants, so `execute(execBlock, packedBalances)` uses one fewer calldata word than before. You can set `EXECUTOR_GAS_LIMIT` (e.g. 400000) in `.env` if your chain typically uses less than 600k for `execute()`.

## 5. Run the UI server

```bash
./run_server.sh
```

This starts the FastAPI app with uvicorn on **port 9000** (see `run_server.sh`). Open http://localhost:9000 (or http://&lt;host&gt;:9000). The UI uses HTTP Basic auth; credentials are configured in `app/core/config.py` (e.g. `ADMIN_HASH` for user `admin`).

## 6. (Optional) Executor and auto-execute

The contract allows an optional **executor** address. When set, that wallet (instead of the owner) can call `execute()`, so the owner can use the same chain for stake/unstake/withdraw from the UI without nonce conflicts with the auto-execute loop.

### 6.1 Set the executor (owner only, one-time)

As the contract owner, set the executor to the wallet you will use for auto-execute:

```bash
# Set executor to the address that will run auto_execute (use that wallet’s address or its private key)
export EXECUTOR_ADDRESS=0x...   # executor wallet address
python3 scripts/set_executor.py
```

Or derive the address from the executor key (do not put `EXECUTOR_PRIVATE_KEY` in the same env as the script; use a separate terminal or unset after):

```bash
export EXECUTOR_PRIVATE_KEY=0x...   # executor wallet key
python3 scripts/set_executor.py
```

To clear the executor (only the owner can call `execute()` again):

```bash
python3 scripts/set_executor.py --clear
```

### 6.2 Run auto-execute

For automatic `execute()` on each new Bittensor block (delegate balances must be ≤ 2 TAO):

```bash
python3 bt_utils/auto_execute.py
```

- If **`EXECUTOR_PRIVATE_KEY`** is set in `.env`, that wallet is used; it must be the contract’s current executor (set in 6.1).
- If not set, **`PRIVATE_KEY`** (owner) is used.

Run from project root so `deployment.json` and imports resolve. The UI can turn execution on/off via the **Executor** toggle; when ON, the script sends `execute()` each block when enabled.

**While this script is running**, you can use **fast stake**, **fast stake limit**, and **fast unstake** (via the UI or API). Those operations encode intent by submitting **MevShield.announce_next_key** (tip = encoded intent, even if the extrinsic fails); the auto-execute loop calls the contract’s `execute()`, which applies the staking/unstaking on chain.

### 8. Rust alternative for auto-execute (optional)

You can run the same “see block → call execute()” loop in **Rust** for lower latency and a single binary. The repo includes a minimal Rust crate in **`auto_execute_rs/`**.

- **EVM part:** Implemented (ethers-rs: connect to RPC, build `execute(execBlock, packedBalances)`, sign with `EXECUTOR_PRIVATE_KEY` or `PRIVATE_KEY`, send tx). Uses the same `.env` and `deployment.json` as the Python script.
- **Bittensor part:** Not implemented. The Rust binary needs the current Bittensor block number and the two delegate balances. To finish the Rust version you can: (1) use [subxt](https://docs.rs/subxt) with Bittensor/Finney metadata to query the chain (block number and `Balances::Account` for the delegate SS58 addresses), or (2) use raw JSON-RPC to the Bittensor node, or (3) keep using the Python script.

See **`auto_execute_rs/README.md`** for build/run and how to implement the Bittensor query in Rust.

## Summary

1. Install Node/Python deps; create `.env` with `PRIVATE_KEY` (and optional `RPC_URL`, `BITTENSOR_NETWORK`, `CONTRACT_SS58`).
2. Set `STAKE_INFO_DELEGATE` and `LIMIT_PRICE_DELEGATE` in `contracts/StakeWrapConstants.sol`; set `WITHDRAW_COLDKEY` to a separate coldkey you keep safe. Keep delegate balances ≤ 2 TAO.
3. Run `python3 scripts/compile_deploy_add_proxy.py` (after `npm install` once)—it compiles, deploys, and adds the contract as proxy for the delegate wallets.
4. `./run_server.sh` for the UI (port 9000).
5. Optionally set an executor with `python3 scripts/set_executor.py` (owner only), then run `bt_utils/auto_execute.py` for per-block execute (use `EXECUTOR_PRIVATE_KEY` in `.env` to avoid nonce conflict with the owner UI).
