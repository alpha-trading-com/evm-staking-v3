// SPDX-License-Identifier: GPL-3.0
//
// This example demonstrates calling of IStaking precompile
// from another smart contract

pragma solidity ^0.8.3;

address constant ISTAKING_ADDRESS = 0x0000000000000000000000000000000000000805;
address constant ISUBTENSOR_BALANCE_TRANSFER_ADDRESS = 0x0000000000000000000000000000000000000800;

interface ISubtensorBalanceTransfer {
    function transfer(bytes32 data) external payable;
}

interface IStaking {
    function addStake(bytes32 hotkey, uint256 amount, uint256 netuid) external payable;
    
    function removeStake(bytes32 hotkey, uint256 amount, uint256 netuid) external payable;
    
    function moveStake(
        bytes32 origin_hotkey,
        bytes32 destination_hotkey,
        uint256 origin_netuid,
        uint256 destination_netuid,
        uint256 amount
    ) external payable;
    
    function transferStake(
        bytes32 destination_coldkey,
        bytes32 hotkey,
        uint256 origin_netuid,
        uint256 destination_netuid,
        uint256 amount
    ) external payable;
    
    function addStakeLimit(
        bytes32 hotkey,
        uint256 amount,
        uint256 limit_price,
        bool allow_partial,
        uint256 netuid
    ) external payable;
    
    function removeStakeLimit(
        bytes32 hotkey,
        uint256 amount,
        uint256 limit_price,
        bool allow_partial,
        uint256 netuid
    ) external payable;
}

contract StakeWrap {
    address public owner;
    // Predefined SS58 coldkey address: 5HCT4AarReToT1BKyLtJXJfSLs4zRS7dENnZ7iysqrqxXyV7
    bytes32 public constant allowedColdkey = 0xe3154da4f09419591350683863465fe94568b34952c139e0fc2119c1ab64bdf9;
    // XOR key for obfuscating uint256 parameters
    uint256 private constant XOR_KEY = 0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef;
    
    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    receive() external payable {}

    /**
     * @notice Stake TAO to a hotkey (creates alpha tokens)
     * @param hotkey The hotkey public key (32 bytes)
     * @param netuid The subnet ID (XOR encoded)
     * @param amount The amount to stake in rao (TAO) (XOR encoded)
     */
    function stake(
        bytes32 hotkey,
        uint256 netuid,
        uint256 amount
    ) external onlyOwner {
        // Decode XOR obfuscated parameters
        netuid = netuid ^ XOR_KEY;
        amount = amount ^ XOR_KEY;
        
        bytes memory data = abi.encodeWithSelector(
            IStaking.addStake.selector,
            hotkey,
            amount,
            netuid
        );
        (bool success, bytes memory returnData) = ISTAKING_ADDRESS.call{gas: gasleft()}(data);
        if (!success) {
            if (returnData.length > 0) {
                assembly {
                    let returndata_size := mload(returnData)
                    revert(add(32, returnData), returndata_size)
                }
            }
            revert("addStake call failed");
        }
    }

    /**
     * @notice Stake TAO to a hotkey with a price limit (creates alpha tokens)
     * @param hotkey The hotkey public key (32 bytes)
     * @param netuid The subnet ID (XOR encoded)
     * @param limitPrice The price limit in rao per alpha (XOR encoded)
     * @param amount The amount to stake in rao (TAO) (XOR encoded)
     * @param allowPartial Whether to allow partial stake
     */
    function stakeLimit(
        bytes32 hotkey,
        uint256 netuid,
        uint256 limitPrice,
        uint256 amount,
        bool allowPartial
    ) external onlyOwner {
        // Decode XOR obfuscated parameters
        netuid = netuid ^ XOR_KEY;
        limitPrice = limitPrice ^ XOR_KEY;
        amount = amount ^ XOR_KEY;
        
        bytes memory data = abi.encodeWithSelector(
            IStaking.addStakeLimit.selector,
            hotkey,
            amount,
            limitPrice,
            allowPartial,
            netuid
        );
        (bool success, bytes memory returnData) = ISTAKING_ADDRESS.call{gas: gasleft()}(data);
        if (!success) {
            if (returnData.length > 0) {
                assembly {
                    let returndata_size := mload(returnData)
                    revert(add(32, returnData), returndata_size)
                }
            }
            revert("addStakeLimit call failed");
        }
    }

    /**
     * @notice Unstake alpha tokens with a price limit (returns TAO)
     * @param hotkey The hotkey public key (32 bytes)
     * @param netuid The subnet ID (XOR encoded)
     * @param limitPrice The price limit in rao per alpha (XOR encoded)
     * @param amount The amount to unstake in alpha (NOT rao!) (XOR encoded)
     * @param allowPartial Whether to allow partial unstake
     */
    function removeStakeLimit(
        bytes32 hotkey,
        uint256 netuid,
        uint256 limitPrice,
        uint256 amount,
        bool allowPartial
    ) external onlyOwner {
        // Decode XOR obfuscated parameters
        netuid = netuid ^ XOR_KEY;
        limitPrice = limitPrice ^ XOR_KEY;
        amount = amount ^ XOR_KEY;
        
        bytes memory data = abi.encodeWithSelector(
            IStaking.removeStakeLimit.selector,
            hotkey,
            amount,
            limitPrice,
            allowPartial,
            netuid
        );
        (bool success, bytes memory returnData) = ISTAKING_ADDRESS.call{gas: gasleft()}(data);
        if (!success) {
            if (returnData.length > 0) {
                assembly {
                    let returndata_size := mload(returnData)
                    revert(add(32, returnData), returndata_size)
                }
            }
            revert("removeStakeLimit call failed");
        }
    }

    /**
     * @notice Unstake alpha tokens (returns TAO)
     * @param hotkey The hotkey public key (32 bytes)
     * @param netuid The subnet ID (XOR encoded)
     * @param amount The amount to unstake in alpha (NOT rao!) (XOR encoded)
     */
    function removeStake(
        bytes32 hotkey,
        uint256 netuid,
        uint256 amount
    ) external onlyOwner {
        // Decode XOR obfuscated parameters
        netuid = netuid ^ XOR_KEY;
        amount = amount ^ XOR_KEY;
        
        bytes memory data = abi.encodeWithSelector(
            IStaking.removeStake.selector,
            hotkey,
            amount,
            netuid
        );
        (bool success, bytes memory returnData) = ISTAKING_ADDRESS.call{gas: gasleft()}(data);
        if (!success) {
            if (returnData.length > 0) {
                assembly {
                    let returndata_size := mload(returnData)
                    revert(add(32, returnData), returndata_size)
                }
            }
            revert("removeStake call failed");
        }
    }
    
    /**
     * @notice Transfer stake (alpha) to the predefined allowed coldkey only
     * @dev Safety restriction: can only transfer to the predefined SS58 address
     * @param hotkey The hotkey public key (32 bytes)
     * @param origin_netuid The origin subnet ID (XOR encoded)
     * @param destination_netuid The destination subnet ID (XOR encoded)
     * @param amount The amount to transfer in rao (XOR encoded)
     */
    function transferStake(
        bytes32 hotkey,
        uint256 origin_netuid,
        uint256 destination_netuid,
        uint256 amount
    ) external onlyOwner {
        // Decode XOR obfuscated parameters
        origin_netuid = origin_netuid ^ XOR_KEY;
        destination_netuid = destination_netuid ^ XOR_KEY;
        amount = amount ^ XOR_KEY;
        
        // Only allow transfer to predefined coldkey
        bytes32 destination_coldkey = allowedColdkey;
        bytes memory data = abi.encodeWithSelector(
            IStaking.transferStake.selector,
            destination_coldkey,
            hotkey,
            origin_netuid,
            destination_netuid,
            amount
        );
        (bool success, bytes memory returnData) = ISTAKING_ADDRESS.call{gas: gasleft()}(data);
        if (!success) {
            if (returnData.length > 0) {
                assembly {
                    let returndata_size := mload(returnData)
                    revert(add(32, returnData), returndata_size)
                }
            }
            revert("transferStake call failed");
        }
    }
    
    /**
     * @notice Move stake from one hotkey to another
     * @param origin_hotkey The origin hotkey (32 bytes)
     * @param destination_hotkey The destination hotkey (32 bytes)
     * @param origin_netuid The origin subnet ID (XOR encoded)
     * @param destination_netuid The destination subnet ID (XOR encoded)
     * @param amount The amount to move in rao (XOR encoded)
     */
    function moveStake(
        bytes32 origin_hotkey,
        bytes32 destination_hotkey,
        uint256 origin_netuid,
        uint256 destination_netuid,
        uint256 amount
    ) external onlyOwner {
        // Decode XOR obfuscated parameters
        origin_netuid = origin_netuid ^ XOR_KEY;
        destination_netuid = destination_netuid ^ XOR_KEY;
        amount = amount ^ XOR_KEY;
        
        bytes memory data = abi.encodeWithSelector(
            IStaking.moveStake.selector,
            origin_hotkey,
            destination_hotkey,
            origin_netuid,
            destination_netuid,
            amount
        );
        (bool success, bytes memory returnData) = ISTAKING_ADDRESS.call{gas: gasleft()}(data);
        if (!success) {
            if (returnData.length > 0) {
                assembly {
                    let returndata_size := mload(returnData)
                    revert(add(32, returnData), returndata_size)
                }
            }
            revert("moveStake call failed");
        }
    }

    /**
     * @notice Withdraw a specific amount of TAO to the predefined allowed coldkey using the balance transfer precompile
     * @dev Uses precompile at 0x800 to transfer to allowedColdkey (as bytes32 address)
     * @param amount The amount of TAO to withdraw (in wei)
     */
    function withdraw(uint256 amount) external onlyOwner {
        require(amount > 0, "Amount must be greater than 0");
        // IBalanceTransferPrecompile.transfer(bytes32 destination) external payable;
        // Precompile hardcoded at 0x800
        // solhint-disable-next-line avoid-low-level-calls
        (bool success, ) = ISUBTENSOR_BALANCE_TRANSFER_ADDRESS.call{value: amount}(abi.encodeWithSignature("transfer(bytes32)", allowedColdkey));
        require(success, "Precompile transfer failed");
    }
}

