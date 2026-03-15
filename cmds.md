# interact.py – Example commands

Use the deployed StakeWrap contract. Requires `PRIVATE_KEY` in `.env` (or environment). Contract address is read from `deployment.json` unless overridden with `--contract`.

---

## Setup

```bash
# Optional: override RPC (default: https://test.finney.opentensor.ai/)
export RPC_URL=https://test.finney.opentensor.ai/

# Optional: use a specific contract instead of deployment.json
# Add: --contract 0xYourContractAddress
```

---

## Read-only

### Check owner

```bash
python3 scripts/interact.py owner
```

### Check contract balance (TAO in wei)

```bash
python3 scripts/interact.py balance
```

### Get subnet price (alpha price for a netuid)

Uses the Alpha precompile (0x808). Returns current alpha price in rao per alpha (scaled by 1e9).

```bash
python3 scripts/interact.py subnetPrice --netuid 1
```

---

## Staking

### Stake TAO to a hotkey

Amount in **TAO** (converted to rao internally). Hotkey: SS58 or 32-byte hex.

```bash
python3 scripts/interact.py stake \
  --hotkey 5F3sa2TJAWMqDhXG6jhV4N8ko9SxwGy8TpaNS1repo5EYjQX \
  --netuid 1 \
  --amount 1.0
```

### Stake with limit price

```bash
python3 scripts/interact.py stakeLimit \
  --hotkey 5F3sa2TJAWMqDhXG6jhV4N8ko9SxwGy8TpaNS1repo5EYjQX \
  --netuid 1 \
  --limit-price 1000000 \
  --amount 0.5 \
  --allow-partial
```

### Unstake (remove stake) – amount in **ALPHA** (not TAO)

```bash
python3 scripts/interact.py removeStake \
  --hotkey 5F3sa2TJAWMqDhXG6jhV4N8ko9SxwGy8TpaNS1repo5EYjQX \
  --netuid 1 \
  --amount 1.0
```

### Unstake with limit price – amount in **ALPHA**

```bash
python3 scripts/interact.py removeStakeLimit \
  --hotkey 5F3sa2TJAWMqDhXG6jhV4N8ko9SxwGy8TpaNS1repo5EYjQX \
  --netuid 1 \
  --limit-price 1000000 \
  --amount 0.5 \
  --allow-partial
```

---

## Transfer & move stake

### Transfer stake to the contract’s allowed coldkey

Amount in **TAO** (rao). Only the predefined allowed coldkey can receive.

```bash
python3 scripts/interact.py transferStake \
  --hotkey 5F3sa2TJAWMqDhXG6jhV4N8ko9SxwGy8TpaNS1repo5EYjQX \
  --origin-netuid 1 \
  --destination-netuid 1 \
  --amount 0.5
```

### Move stake between hotkeys

Amount in **TAO** (rao).

```bash
python3 scripts/interact.py moveStake \
  --origin-hotkey 5F3sa2TJAWMqDhXG6jhV4N8ko9SxwGy8TpaNS1repo5EYjQX \
  --destination-hotkey 5FHneW46xGXgs5mUivUemYskMwEeHktR6R4gLZ4R5YqJq8f \
  --origin-netuid 1 \
  --destination-netuid 1 \
  --amount 0.25
```

---

## Withdraw

Send TAO from the contract to the allowed coldkey (balance transfer precompile). Amount in **TAO**. Only owner.

```bash
python3 scripts/interact.py withdraw --amount 1.0
```

---

## Transfer to proxied account

Send a specific amount of TAO from the contract to the **allowed proxied account** (constant `allowedProxiedAccount` in the contract). Amount in **TAO**. Only owner.

```bash
python3 scripts/interact.py transferToProxiedAccount --amount 0.5
```

---

## Add contract as proxy (type Any)

Before the contract can use **pullFromProxiedAccount**, the **coldkey** (the allowedProxiedAccount, e.g. `5FptUDrtvf6y4GmQKekEPmELeSC5MsLpRRDPFNXmHmCwfbs3`) must add the contract as a proxy with type **Any** on the Subtensor chain.

**Option A – script (recommended)**  
Set the coldkey mnemonic or seed, then run:

```bash
# One-time: set coldkey (use mnemonic or seed, not both)
export COLDKEY_MNEMONIC="word1 word2 ..."
# or: export COLDKEY_SEED="0x..."

# Default: contract from deployment.json, coldkey 5FptUDrtvf6y4GmQKekEPmELeSC5MsLpRRDPFNXmHmCwfbs3
python3 scripts/add_proxy_delegate.py

# Override contract or coldkey
python3 scripts/add_proxy_delegate.py --contract 0x3c62... --coldkey-ss58 5FptUDrtvf6y4GmQKekEPmELeSC5MsLpRRDPFNXmHmCwfbs3

# Dry run (no submit)
python3 scripts/add_proxy_delegate.py --dry-run
```

**Option B – Polkadot.js**  
Connect to the Bittensor/Subtensor network (e.g. finney), select the coldkey wallet, then: **Developer → Extrinsics → proxy → addProxy**. Set delegate to the contract’s SS58 (e.g. from `python3 scripts/address_convert.py 0x<contract_evm_address>`), proxy type **Any**, delay **0**, sign and submit.

---

## Pull from proxied account

Transfer all TAO from an account that has set this contract as its proxy into the contract. Requires a SCALE-encoded `balances.transferAll(dest, keepAlive)` call.

### 1. Encode the transfer_all call

`--dest` is the destination SS58 address (e.g. this contract’s SS58). Default `keep_alive=true`.

```bash
# Output hex for --encoded-call (default keep_alive=true)
python3 scripts/encode_transfer_all.py --dest 5HCT4AarReToT1BKyLtJXJfSLs4zRS7dENnZ7iysqrqxXyV7

# keep_alive=false
python3 scripts/encode_transfer_all.py --dest 5HCT4AarReToT1BKyLtJXJfSLs4zRS7dENnZ7iysqrqxXyV7 --no-keep-alive
```

### 2. Call pullFromProxiedAccount

Uses the contract constant **allowedProxiedAccount** as the source account. Encode `transfer_all` with **dest** = this contract’s SS58.

```bash
ENCODED=$(python3 scripts/encode_transfer_all.py --dest 5HCT4AarReToT1BKyLtJXJfSLs4zRS7dENnZ7iysqrqxXyV7)
python3 scripts/interact.py pullFromProxiedAccount --encoded-call "$ENCODED"
```

With explicit hex encoded call:

```bash
python3 scripts/interact.py pullFromProxiedAccount --encoded-call 0x0404...
```

---

## Using a different contract

Append `--contract <address>` to any command to use that contract instead of the one in `deployment.json`:

```bash
python3 scripts/interact.py balance --contract 0x1234567890123456789012345678901234567890
python3 scripts/interact.py stake --hotkey 5F3s... --netuid 1 --amount 1.0 --contract 0x1234...
```

---

## Upgradeable deployment

To deploy an **upgradeable** StakeWrap (implementation + proxy), use the Hardhat script. The proxy address is what you use in `deployment.json` and with `interact.py`.

**Deploy (first time):**

```bash
# Set PRIVATE_KEY (and optionally RPC_URL) in .env, then:
npm run compile
npm run deploy:upgradeable
```

This writes `deployment.json` with `contract_address` = proxy and `implementation_address` = implementation. Use the proxy address everywhere.

**Upgrade to a new implementation:**

After changing the StakeWrap contract (e.g. new logic), deploy the new implementation and point the proxy at it:

```bash
npm run compile
npm run upgrade
```

Only the account that was set as proxy admin (the deployer) can run `upgrade`. `deployment.json` is updated with the new `implementation_address`.
