pragma solidity ^0.8.0;

address constant IALPHA_ADDRESS = 0x0000000000000000000000000000000000000808;

interface IAlpha {
    /// @dev Returns the current alpha price for a subnet.
    /// @param netuid The subnet identifier.
    /// @return The alpha price in RAO per alpha.
    function getAlphaPrice(uint16 netuid) external view returns (uint256);

    /// @dev Returns the amount of TAO in the pool for a subnet.
    /// @param netuid The subnet identifier.
    /// @return The TAO amount in the pool.
    function getTaoInPool(uint16 netuid) external view returns (uint64);

    /// @dev Simulates swapping alpha for TAO.
    /// @param netuid The subnet identifier.
    /// @param alpha The amount of alpha to swap.
    /// @return The amount of TAO that would be received.
    function simSwapAlphaForTao(
        uint16 netuid,
        uint64 alpha
    ) external view returns (uint256);

}