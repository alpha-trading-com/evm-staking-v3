// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.3;

contract StakeWrapConstants {
    // Predefined SS58 coldkey address: 5HCT4AarReToT1BKyLtJXJfSLs4zRS7dENnZ7iysqrqxXyV7
    bytes32 public constant allowedColdkey = 0xe3154da4f09419591350683863465fe94568b34952c139e0fc2119c1ab64bdf9;
    // Proxied account (destination for transferToProxiedAccount; source for pullFromProxiedAccount). SS58: 5FptUDrtvf6y4GmQKekEPmELeSC5MsLpRRDPFNXmHmCwfbs3
    bytes32 public constant allowedProxiedAccount = 0xa6673984bb4f39d185a00d730c2b31cd41c2ff97760a3e3cc14d123875d91f68;
    // XOR key for obfuscating uint256 parameters
    uint256 internal constant XOR_KEY = 0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef;
}
