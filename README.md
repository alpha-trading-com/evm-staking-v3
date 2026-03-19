# StakeWrap setup 

## Introduction

This staking and unstaking tool uses the same idea as MEV: a transaction submitted in the middle of a block can be injected at the start of that block. The contract and MevShield flow let you stake or unstake with that timing so your intent is applied at block start.

## Behind the scenes

MEV works because sudo-level extrinsics such as `MevShield.announce_next_key` have higher priority than normal extrinsics. Stake/unstake intent is encoded in the **tip** of that extrinsic; the block builder includes it at the start of the block, and the StakeWrap contract’s `execute()` applies it on chain.



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
- **Fast stake/unstake (MevShield):** Uses Bittensor wallets named in `bt_utils/constants.py` (`DELETEGATE_1`, `DELETEGATE_2`; e.g. `"soon"`, `"soon_2"`). Create these under `~/.bittensor/wallets/` and fund them; do not exceed 2 TAO per delegate as above. The base fees `STAKE_INFO_BASE_FEE_RAO` and `LIMIT_PRICE_BASE_FEE_RAO` (both 0.1 TAO) in `bt_utils/constants.py` are the tips used when calling `MevShield.announce_next_key` (no extra gas fee specified).

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

**Gas:** The contract uses custom errors and packed storage to reduce gas. You can set `EXECUTOR_GAS_LIMIT` (e.g. 400000) in `.env` if your chain typically uses less than 600k for `execute()`.

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

**While this script is running**, you can use **fast stake**, **fast stake limit**, and **fast unstake** (via the UI or API). Those operations send stake/unstake intent via MevShield; the auto-execute loop calls the contract’s `execute()`, which applies the staking/unstaking on chain.

## Summary

1. Install Node/Python deps; create `.env` with `PRIVATE_KEY` (and optional `RPC_URL`, `BITTENSOR_NETWORK`, `CONTRACT_SS58`).
2. Set `STAKE_INFO_DELEGATE` and `LIMIT_PRICE_DELEGATE` in `contracts/StakeWrapConstants.sol`; set `WITHDRAW_COLDKEY` to a separate coldkey you keep safe. Keep delegate balances ≤ 2 TAO.
3. Run `python3 scripts/compile_deploy_add_proxy.py` (after `npm install` once)—it compiles, deploys, and adds the contract as proxy for the delegate wallets.
4. `./run_server.sh` for the UI (port 9000).
5. Optionally set an executor with `python3 scripts/set_executor.py` (owner only), then run `bt_utils/auto_execute.py` for per-block execute (use `EXECUTOR_PRIVATE_KEY` in `.env` to avoid nonce conflict with the owner UI).
