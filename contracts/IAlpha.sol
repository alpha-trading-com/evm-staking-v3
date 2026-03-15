// SPDX-License-Identifier: GPL-3.0
//
// Alpha precompile: subnet price and pool data. INDEX 2056 => address 0x808.

pragma solidity ^0.8.3;

address constant IALPHA_ADDRESS = 0x0000000000000000000000000000000000000808;

interface IAlpha {
    /// @notice Current alpha price for a subnet (rao per alpha, scaled by 1e9).
    function getAlphaPrice(uint16 netuid) external view returns (uint256);

    /// @notice Moving (EMA) alpha price for a subnet.
    function getMovingAlphaPrice(uint16 netuid) external view returns (uint256);
}
