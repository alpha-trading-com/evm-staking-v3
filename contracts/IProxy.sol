// SPDX-License-Identifier: GPL-3.0
//
// Proxy precompile: allows this contract (as delegate) to execute calls on behalf of
// an account that has added this contract as a proxy. INDEX 2059 => address 0x80b.
//
// Proxy types (forceProxyType): 0 = Any (allows transfer). The other account must
// call addProxy(delegate=this contract's account ID, proxyType, delay) first.

pragma solidity ^0.8.3;

address constant IPROXY_ADDRESS = 0x000000000000000000000000000000000000080b;

interface IProxy {
    /// @notice Execute a call on behalf of the real account (the account that set this contract as proxy).
    /// @param real The real account ID (32 bytes, e.g. SS58 public key)
    /// @param forceProxyType Optional: restrict to this proxy type (e.g. [0] for Any). Empty to use delegation type.
    /// @param call SCALE-encoded RuntimeCall as uint8[] (must match precompile: proxyCall(bytes32,uint8[],uint8[]))
    function proxyCall(
        bytes32 real,
        uint8[] memory forceProxyType,
        uint8[] memory call
    ) external;
}
