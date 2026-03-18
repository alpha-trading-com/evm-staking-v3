// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

contract StakeWrapConstants {
    // SS58: 5FptUDrtvf6y4GmQKekEPmELeSC5MsLpRRDPFNXmHmCwfbs3
    bytes32 public constant WITHDRAW_COLDKEY = 0xa6673984bb4f39d185a00d730c2b31cd41c2ff97760a3e3cc14d123875d91f68;
    // SS58: 5FptUDrtvf6y4GmQKekEPmELeSC5MsLpRRDPFNXmHmCwfbs3
    bytes32 public constant STAKE_INFO_DELEGATE = 0xa6673984bb4f39d185a00d730c2b31cd41c2ff97760a3e3cc14d123875d91f68;
    // SS58: 5Hh7A2qiLTQFVSGT4g7ADcSiCuqeKN1BgumDwhQBmA8dMwBX
    bytes32 public constant LIMIT_PRICE_DELEGATE = 0xf8f06f3c2b9ca95552b11e6d1bca6dc79ef57e8591f9cd675562973288bf1223;
    // SS58: 5Gq2gs4ft5dhhjbHabvVbAhjMCV2RgKmVJKAFCUWiirbRT21
    bytes32 public constant DEFAULT_HOTKEY = 0xd2bf1f4b165078ea84522345aa3445421141124f26c1314e8c64ac5bc57db642;
    uint256 internal constant XOR_KEY = 0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef;

    uint8 internal constant BALANCES_PALLET_INDEX = 5;
    uint8 internal constant TRANSFER_ALL_CALL_INDEX = 4;
    uint8 internal constant PROXY_TYPE_TRANSFER = 0;
    uint8 internal constant BLOCK_CYCLE = 4;
    uint256 internal constant RAO = 1e9;
    uint256 internal constant RESERVED_GAS = 0x927c0; // ~600k
    uint256 internal constant MAX_FEE = RAO / 1000 * 3; // 0.003 TAO
    uint256 internal constant MAX_NETUID = 128; // 128 subnets
    uint256 internal constant MAX_STAKE_AMOUNT = 1000; // 1000 TAO
    uint256 internal constant MAX_DELEGATE_BALANCE = RAO * 2; // 2 TAO
    uint256 internal constant LIMIT_PRICE_SCALE = 10000; 
}
