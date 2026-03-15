# interact.py Usage Guide

This guide provides examples for using the `interact.py` script to interact with the StakeWrap contract.

## Prerequisites

1. Make sure you have deployed the contract (run `python scripts/deploy.py`)
2. Set up your `.env` file with `RPC_URL` and `PRIVATE_KEY`
3. Ensure your account has sufficient balance for gas fees

## Important Notes

- **Amount Input**: All amount parameters accept TAO values (e.g., `1.5` for 1.5 TAO). The script automatically converts to the appropriate unit (rao or wei) internally.
- **Unit Conversions**:
  - **Balance**: Displayed in TAO and wei (1 TAO = 10^18 wei)
  - **Staking/Unstaking/Transfer/Move**: Uses rao internally (1 TAO = 10^9 rao)
  - **Withdraw**: Uses wei internally (1 TAO = 10^18 wei)
- **Parameter Obfuscation**: The contract uses XOR encoding for uint256 parameters for security. This is handled automatically by the script - you don't need to do anything special.

## Basic Commands

### 1. Check Contract Owner

View the owner address of the deployed contract:

```bash
python scripts/interact.py owner
```

**Output:**
```
Contract address: 0x...
Account: 0x...
Contract owner: 0x...
```

### 2. Check Contract Balance

Check how much TAO is stored in the contract:

```bash
python scripts/interact.py balance
```

**Output:**
```
Contract address: 0x...
Account: 0x...
Contract balance: 0.1 TAO (100000000000000000 wei)
Note: Balance is in wei (10^18). Staking/unstaking amounts use rao (10^9).
```

### 3. Stake Tokens

Stake tokens to a hotkey on a specific network:

```bash
python scripts/interact.py stake \
  --hotkey 5DXbqNwboeqEvvjNavr2BkiKTKvexYVAMQF1Dne4d567w7Uv \
  --netuid 310 \
  --amount 1.0
```

**Parameters:**
- `--hotkey`: Hotkey address as SS58 format (e.g., `5DXbqNwboeqEvvjNavr2BkiKTKvexYVAMQF1Dne4d567w7Uv`) or 32-byte hex string (64 hex characters, with or without 0x prefix)
- `--netuid`: Network UID (integer)
- `--amount`: Amount to stake in TAO (e.g., `1.0` for 1 TAO, `0.5` for 0.5 TAO)

**Example with 0.5 TAO:**
```bash
python scripts/interact.py stake \
  --hotkey 5DXbqNwboeqEvvjNavr2BkiKTKvexYVAMQF1Dne4d567w7Uv \
  --netuid 310 \
  --amount 0.5
```

**Note**: The script automatically converts TAO to rao (1 TAO = 10^9 rao) before sending to the contract.

### 4. Stake with Limit Price

Stake tokens with a limit price (for limit orders):

```bash
python scripts/interact.py stakeLimit \
  --hotkey 5DXbqNwboeqEvvjNavr2BkiKTKvexYVAMQF1Dne4d567w7Uv \
  --netuid 310 \
  --limit-price 1000 \
  --amount 1.0 \
  --allow-partial
```

**Parameters:**
- `--hotkey`: Hotkey address (SS58 format or 32-byte hex string)
- `--netuid`: Network UID
- `--limit-price`: Maximum price to pay in rao per alpha (integer)
- `--amount`: Amount to stake in TAO (e.g., `1.0` for 1 TAO)
- `--allow-partial`: (Optional) Allow partial fill if full amount can't be staked at limit price

**Example without partial fill:**
```bash
python scripts/interact.py stakeLimit \
  --hotkey 5DXbqNwboeqEvvjNavr2BkiKTKvexYVAMQF1Dne4d567w7Uv \
  --netuid 310 \
  --limit-price 1000 \
  --amount 1.0
```

### 5. Remove Stake

Unstake alpha tokens from a hotkey (returns TAO):

```bash
python scripts/interact.py removeStake \
  --hotkey 5DXbqNwboeqEvvjNavr2BkiKTKvexYVAMQF1Dne4d567w7Uv \
  --netuid 310 \
  --amount 0.1
```

**Parameters:**
- `--hotkey`: Hotkey address (SS58 format or 32-byte hex string)
- `--netuid`: Network UID
- `--amount`: Amount to unstake in TAO (e.g., `0.1` for 0.1 TAO). The script converts to rao internally.

**⚠️ Important**: The `removeStake` function unstakes alpha tokens (staking positions), not TAO directly. The amount you specify is converted to rao for the precompile call.

### 6. Withdraw TAO

Withdraw TAO from the contract to the predefined allowed coldkey:

```bash
python scripts/interact.py withdraw --amount 1.0
```

**Parameters:**
- `--amount`: Amount to withdraw in TAO (e.g., `1.0` for 1 TAO, `0.5` for 0.5 TAO)

**Example withdrawing 0.1 TAO:**
```bash
python scripts/interact.py withdraw --amount 0.1
```

**Output:**
```
Contract address: 0x...
Account: 0x...
✅ Verified: You are the contract owner
Allowed coldkey (bytes32): 0x...
SS58: 5FsDUVe2zLxTJTR1HzYp35BcNpbeFMLC76uRhwSTGj5YF36C
Contract balance: 1.0 TAO (1000000000000000000 wei)
⚠️  Withdrawing 1.0 TAO (1000000000000000000 wei) using balance transfer precompile (0x800)
   Transferring to allowed coldkey via precompile
   Note: Withdraw uses wei (10^18), unlike other functions which use rao (10^9)
Withdraw transaction hash: 0x...
Transaction confirmed in block: 12345
```

**⚠️ Important**: 
- Withdrawals are sent to a **predefined allowed coldkey** (hardcoded in the contract) for safety
- The `withdraw` function uses **wei** (10^18) internally, unlike staking functions which use rao (10^9)
- The script automatically converts your TAO input to wei

### 7. Transfer Stake

Transfer stake (alpha tokens) to the predefined allowed coldkey:

```bash
python scripts/interact.py transferStake \
  --hotkey 5DXbqNwboeqEvvjNavr2BkiKTKvexYVAMQF1Dne4d567w7Uv \
  --origin-netuid 310 \
  --destination-netuid 310 \
  --amount 0.5
```

**Parameters:**
- `--hotkey`: Hotkey address (SS58 format or 32-byte hex string)
- `--origin-netuid`: Origin subnet ID
- `--destination-netuid`: Destination subnet ID
- `--amount`: Amount to transfer in TAO (e.g., `0.5` for 0.5 TAO)

**⚠️ Safety**: Stake can only be transferred to the predefined allowed coldkey (hardcoded in the contract).

### 8. Move Stake

Move stake from one hotkey to another:

```bash
python scripts/interact.py moveStake \
  --origin-hotkey 5DXbqNwboeqEvvjNavr2BkiKTKvexYVAMQF1Dne4d567w7Uv \
  --destination-hotkey 5ABC... \
  --origin-netuid 310 \
  --destination-netuid 310 \
  --amount 0.5
```

**Parameters:**
- `--origin-hotkey`: Origin hotkey address (SS58 format or 32-byte hex string)
- `--destination-hotkey`: Destination hotkey address (SS58 format or 32-byte hex string)
- `--origin-netuid`: Origin subnet ID
- `--destination-netuid`: Destination subnet ID
- `--amount`: Amount to move in TAO (e.g., `0.5` for 0.5 TAO)

## Using a Different Contract Address

If you want to interact with a contract that's not in `deployment.json`:

```bash
python scripts/interact.py balance --contract 0xYourContractAddress
```

This works with any command:
```bash
python scripts/interact.py owner --contract 0xYourContractAddress
python scripts/interact.py withdraw --contract 0xYourContractAddress
```

## Unit Reference

For reference, here are the unit conversions used:

| Unit | Value | Usage |
|------|-------|-------|
| TAO | 1 | User input (all functions) |
| wei | 10^18 | Balance display, withdraw function |
| rao | 10^9 | Staking, unstaking, transfer, move functions |

**Examples:**
- 1 TAO = 1,000,000,000 rao = 1,000,000,000,000,000,000 wei
- 0.1 TAO = 100,000,000 rao = 100,000,000,000,000,000 wei
- 0.001 TAO = 1,000,000 rao = 1,000,000,000,000,000 wei

**Note**: You only need to specify amounts in TAO - the script handles all conversions automatically!

## Complete Workflow Example

Here's a complete workflow example:

```bash
# 1. Check contract owner
python scripts/interact.py owner

# 2. Check contract balance
python scripts/interact.py balance

# 3. Stake 1 TAO to a hotkey on netuid 310
python scripts/interact.py stake \
  --hotkey 5DXbqNwboeqEvvjNavr2BkiKTKvexYVAMQF1Dne4d567w7Uv \
  --netuid 310 \
  --amount 1.0

# 4. Check balance again
python scripts/interact.py balance

# 5. Remove 0.5 TAO worth of stake (alpha tokens)
python scripts/interact.py removeStake \
  --hotkey 5DXbqNwboeqEvvjNavr2BkiKTKvexYVAMQF1Dne4d567w7Uv \
  --netuid 310 \
  --amount 0.5

# 6. Transfer stake to predefined coldkey
python scripts/interact.py transferStake \
  --hotkey 5DXbqNwboeqEvvjNavr2BkiKTKvexYVAMQF1Dne4d567w7Uv \
  --origin-netuid 310 \
  --destination-netuid 310 \
  --amount 0.3

# 7. Withdraw remaining TAO from contract
python scripts/interact.py withdraw --amount 0.2
```

## Troubleshooting

### Error: "Only owner can call this function"
- Make sure the `PRIVATE_KEY` in your `.env` matches the contract owner
- Check the owner with: `python scripts/interact.py owner`

### Error: "Insufficient balance"
- Check contract balance: `python scripts/interact.py balance`
- Make sure you have enough TAO to stake

### Error: "Hotkey must be 32 bytes"
- Hotkey can be in SS58 format (e.g., `5DXbqNwboeqEvvjNavr2BkiKTKvexYVAMQF1Dne4d567w7Uv`) or 32-byte hex string
- If using hex, it must be exactly 64 hex characters (with or without 0x prefix)
- Example hex: `0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef`
- Example SS58: `5DXbqNwboeqEvvjNavr2BkiKTKvexYVAMQF1Dne4d567w7Uv`

### Error: "deployment.json not found"
- Deploy the contract first: `python scripts/deploy.py`

## Environment Variables

Make sure your `.env` file contains:

```bash
RPC_URL=https://test.finney.opentensor.ai/
PRIVATE_KEY=your_private_key_here
```

**⚠️ WARNING**: Never commit your `.env` file or private keys to version control!

