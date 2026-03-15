# EVM Staking - Bittensor Staking Contract

This repository contains a Solidity smart contract for staking and unstaking on Bittensor using EVM, along with Python scripts to deploy and interact with the contract.

## Overview

The `StakeWrap` contract wraps the Bittensor IStaking precompile (at address `0x0000000000000000000000000000000000000805`) and provides a simple interface for:
- Staking tokens (`stake`)
- Staking with limit price (`stakeLimit`)
- Removing stake (`removeStake`)

The contract uses low-level calls to interact with the precompile, as direct interface calls don't work with runtime precompiles.

## Project Structure

```
evm-staking/
├── contracts/
│   └── StakeWrap.sol          # Main contract
├── python/
│   ├── deploy.py              # Deployment script
│   └── interact.py            # Interaction script
├── scripts/                    # Hardhat scripts (optional)
├── hardhat.config.js          # Hardhat configuration
├── package.json               # Node.js dependencies
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Prerequisites

- Node.js (v16 or higher)
- Python 3.8+
- Access to a Bittensor EVM-compatible network

## Setup

### 1. Install Node.js Dependencies

```bash
npm install
```

### 2. Compile the Contract

```bash
npm run compile
```

This will create the contract artifacts in the `artifacts/` directory.

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` and set:
- `RPC_URL`: The RPC endpoint for your blockchain network
- `PRIVATE_KEY`: The private key of the account that will deploy/interact with the contract

**⚠️ WARNING**: Never commit your `.env` file or private keys to version control!

## Usage

### Deploy the Contract

```bash
python python/deploy.py
```

This will:
1. Connect to the blockchain using the RPC_URL
2. Deploy the StakeWrap contract
3. Save deployment information to `deployment.json`

### Interact with the Contract

#### Check Contract Owner

```bash
python python/interact.py owner
```

#### Stake Tokens

```bash
python python/interact.py stake \
  --hotkey 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef \
  --netuid 1 \
  --amount 1000000000000000000
```

#### Stake with Limit Price

```bash
python python/interact.py stakeLimit \
  --hotkey 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef \
  --netuid 1 \
  --limit-price 1000 \
  --amount 1000000000000000000 \
  --allow-partial
```

#### Remove Stake

```bash
python python/interact.py removeStake \
  --hotkey 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef \
  --netuid 1 \
  --amount 1000000000000000000
```

### Using a Different Contract Address

If you want to interact with an already deployed contract:

```bash
python python/interact.py owner --contract 0xYourContractAddress
```

## Contract Details

### Functions

- **`stake(bytes32 hotkey, uint256 netuid, uint256 amount)`**: Stake tokens to a hotkey
- **`stakeLimit(bytes32 hotkey, uint256 netuid, uint256 limitPrice, uint256 amount, bool allowPartial)`**: Stake tokens with a limit price
- **`removeStake(bytes32 hotkey, uint256 netuid, uint256 amount)`**: Remove stake from a hotkey

All functions are protected by the `onlyOwner` modifier, meaning only the contract owner can call them.

### Precompile Address

The contract interacts with the Bittensor IStaking precompile at:
```
0x0000000000000000000000000000000000000805
```

## Development

### Compile Contracts

```bash
npm run compile
```

### Run Tests

```bash
npm test
```

## Security Notes

- The contract uses low-level `call()` to interact with the precompile, which is necessary for runtime precompiles
- All staking functions are restricted to the contract owner
- Always verify the precompile address matches your network
- Test thoroughly on testnets before deploying to mainnet

## License

GPL-3.0

