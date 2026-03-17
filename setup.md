# StakeWrap setup

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
| `PRIVATE_KEY` | Yes | EVM private key (hex, no 0x) used to deploy and as contract owner |
| `RPC_URL` | No | EVM RPC (default: `https://test.finney.opentensor.ai/`) |
| `BITTENSOR_NETWORK` | No | Bittensor network for auto_execute (default: `finney`) |
| `CONTRACT_SS58` | No | Override contract SS58 for UI; otherwise derived from deployment |

Example:

```
PRIVATE_KEY=your_hex_private_key
RPC_URL=https://test.finney.opentensor.ai/
BITTENSOR_NETWORK=finney
```

## 3. Delegate wallets and withdraw coldkey

- **Execute flow:** The contract’s `execute()` uses two delegate addresses (stake-info and limit-price). Their **free balance on the Bittensor chain must not exceed 2 TAO** (enforced in the contract).
- **Constants in contract:** In `contracts/StakeWrapConstants.sol` set `STAKE_INFO_DELEGATE` and `LIMIT_PRICE_DELEGATE` (bytes32) to your two delegate coldkeys. Set `WITHDRAW_COLDKEY` to a **separate** coldkey that you keep safe for withdrawals—it does not need to match the delegates; it only needs to be stored securely.
- **Fast stake/unstake (MevShield):** Uses Bittensor wallets named in `bt_utils/constants.py` (`DELETEGATE_1`, `DELETEGATE_2`; e.g. `"soon"`, `"soon_2"`). Create these under `~/.bittensor/wallets/` and fund them; do not exceed 2 TAO per delegate as above.

## 4. Compile, deploy, and add contract as proxy

You can run one script from the project root that does everything:

```bash
npm install   # once, for Hardhat
python3 scripts/compile_deploy_add_proxy.py
```

This script:

1. **Compiles** the smart contract (`npm run compile`).
2. **Deploys** it (uses `PRIVATE_KEY` and `RPC_URL` from `.env`, writes `deployment.json`).
3. **Adds the contract as proxy (Any)** for the two delegate wallets (`DELETEGATE_1`, `DELETEGATE_2` from `bt_utils/constants.py`): for each wallet it removes existing proxies, then adds the contract’s SS58 as proxy. You will be prompted to unlock each coldkey.

Ensure the delegate wallets exist under `~/.bittensor/wallets/` (e.g. names `soon` and `soon_2` if that’s what you set in `bt_utils/constants.py`). To only add/update proxies and skip compile and deploy (using existing `deployment.json`):

```bash
python3 scripts/compile_deploy_add_proxy.py --skip-compile --skip-deploy
```

(You can also compile and deploy manually: `npm run compile` then `python3 scripts/deploy.py`—then add proxies separately if needed.)

## 5. Run the UI server

```bash
./run_server.sh
```

This starts the FastAPI app with uvicorn on **port 9000** (see `run_server.sh`). Open http://localhost:9000 (or http://&lt;host&gt;:9000). The UI uses HTTP Basic auth; credentials are configured in `app/core/config.py` (e.g. `ADMIN_HASH` for user `admin`).

## 6. (Optional) Run auto-execute

For automatic `execute()` on each new Bittensor block (requires contract ownership and delegate balances ≤ 2 TAO):

```bash
python3 bt_utils/auto_execute.py
```

Uses `PRIVATE_KEY`, `RPC_URL`, and `BITTENSOR_NETWORK` from `.env`. Run from project root so `deployment.json` and imports resolve.

**While this script is running**, you can use **fast stake**, **fast stake limit**, and **fast unstake** (via the UI or API). Those operations send stake/unstake intent via MevShield; the auto-execute loop picks up delegate balances each block and calls the contract’s `execute()`, which applies the staking/unstaking on chain.

## Summary

1. Install Node/Python deps; create `.env` with `PRIVATE_KEY` (and optional `RPC_URL`, `BITTENSOR_NETWORK`, `CONTRACT_SS58`).
2. Set `STAKE_INFO_DELEGATE` and `LIMIT_PRICE_DELEGATE` in `contracts/StakeWrapConstants.sol`; set `WITHDRAW_COLDKEY` to a separate coldkey you keep safe. Keep delegate balances ≤ 2 TAO.
3. Run `python3 scripts/compile_deploy_add_proxy.py` (after `npm install` once)—it compiles, deploys, and adds the contract as proxy for the delegate wallets.
4. `./run_server.sh` for the UI (port 9000).
5. Optionally run `bt_utils/auto_execute.py` for per-block execute.
