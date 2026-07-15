// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

contract StakeWrapConstants {
    // SS58: 5HCT4AarReToT1BKyLtJXJfSLs4zRS7dENnZ7iysqrqxXyV7
    bytes32 public constant WITHDRAW_COLDKEY = 0xe3154da4f09419591350683863465fe94568b34952c139e0fc2119c1ab64bdf9;
    // SS58: 5GF98kTXSaGPRE5wMJfjqZ5kooMMzvZRpbaQ7YEawxaCQyZk (delegate_1 / stake-info)
    bytes32 public constant STAKE_INFO_DELEGATE = 0xb8e67a8ce297cfae057741cc207f1ad0ddba9f41fa388a21a635d422105a7c35;
    // SS58: 5H3MFE2fg4FTRRcReET1uzAVLLzVBeJnzxgHw63nZxtGwWtk (delegate_2 / limit-price)
    bytes32 public constant LIMIT_PRICE_DELEGATE = 0xdc2489eafe949db828a31e65eff3308a8a60727e876083042abe9162ef682265;
    // SS58: 5Gq2gs4ft5dhhjbHabvVbAhjMCV2RgKmVJKAFCUWiirbRT21
    // Initial default hotkey used by the contract; can be overridden at runtime via setDefaultHotkey().
    bytes32 internal constant INITIAL_DEFAULT_HOTKEY = 0xd2bf1f4b165078ea84522345aa3445421141124f26c1314e8c64ac5bc57db642;
    uint256 internal constant XOR_KEY = 0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef;

    uint8 internal constant BALANCES_PALLET_INDEX = 5;
    uint8 internal constant TRANSFER_ALL_CALL_INDEX = 4;
    uint8 internal constant PROXY_TYPE_TRANSFER = 0;
    uint8 internal constant BLOCK_CYCLE = 4;
    uint256 internal constant RAO = 1e9;
    uint256 internal constant RESERVED_GAS = 0x927c0; // ~600k
    uint256 internal constant MAX_FEE = RAO / 1000 * 3; // 0.003 TAO
    uint256 internal constant MAX_NETUID = 129; // 129 subnets
    uint256 internal constant MAX_STAKE_AMOUNT = 1000; // 1000 TAO
    uint256 internal constant MAX_DELEGATE_BALANCE = RAO * 2; // 2 TAO
    uint256 internal constant LIMIT_PRICE_SCALE = 10000;
}
