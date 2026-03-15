// SPDX-License-Identifier: GPL-3.0
//
// This example demonstrates calling of IStaking precompile
// from another smart contract.
pragma solidity ^0.8.3;

import "./IStaking.sol";
import "./ISubtensorBalanceTransfer.sol";
import "./StakeWrapConstants.sol";
import "./IProxy.sol";
import "./IAlpha.sol";

contract StakeWrap is StakeWrapConstants {
    address public owner;

    // Balances::transfer_all encoding (Substrate pallet/call indices; verify against chain metadata)
    uint8 internal constant BALANCES_PALLET_INDEX = 5;
    uint8 internal constant TRANSFER_ALL_CALL_INDEX = 4;
    /// @dev Proxy type for proxyCall: 0 = Any (can do all things, including transfer_all). Matches add_proxy_delegate.py (ProxyType.Any).
    uint8 internal constant PROXY_TYPE_ANY = 0;

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

    /**
     * @notice Transfer a specific amount of TAO from this contract to the allowed proxied account
     * @dev Uses balance transfer precompile at 0x800. Destination = allowedProxiedAccount. Amount in wei.
     * @param amount Amount to transfer in wei
     */
    function transferToProxiedAccount(uint256 amount) external onlyOwner {
        require(amount > 0, "Amount must be greater than 0");
        require(address(this).balance >= amount, "Insufficient balance");
        // solhint-disable-next-line avoid-low-level-calls
        (bool success, ) = ISUBTENSOR_BALANCE_TRANSFER_ADDRESS.call{value: amount}(abi.encodeWithSignature("transfer(bytes32)", allowedProxiedAccount));
        require(success, "Precompile transfer failed");
    }

    /**
     * @notice Transfer all TAO from the allowed proxied account to a destination (Proxy precompile, type Any).
     * @dev allowedProxiedAccount must have added this contract as proxy (e.g. type Any).
     *      Encodes Balances::transfer_all(dest, keep_alive=true) and calls Proxy::proxyCall.
     * @param dest 32-byte AccountId32 destination (e.g. this contract's AccountId32 from Blake2b("evm:"||address), or any SS58 decoded to bytes32).
     */
    function pullFromProxiedAccount(bytes32 dest) external onlyOwner {
        bytes memory call = _encodeTransferAll(dest, true);
        _proxyTransferAll(allowedProxiedAccount, call);
    }

    // (removed pullFromProxiedAccountEncoded per instructions)

    /// @dev Proxy::proxyCall(real, ProxyType::Any, call)
    function _proxyTransferAll(bytes32 real, bytes memory call) internal {
        bytes memory forceProxyType = new bytes(1);
        forceProxyType[0] = bytes1(PROXY_TYPE_ANY);
        bytes memory data = abi.encodeWithSelector(
            IProxy.proxyCall.selector,
            real,
            forceProxyType,
            call
        );
        // solhint-disable-next-line avoid-low-level-calls
        (bool success, ) = IPROXY_ADDRESS.call(data);
        require(success, "Proxy proxyCall failed");
    }

    /**
     * @dev SCALE-encodes RuntimeCall::Balances(transfer_all(dest, keep_alive)).
     *      Layout: [pallet_index][call_index][MultiAddress::Id=0][dest 32 bytes][keep_alive 1 byte]
     */
    function _encodeTransferAll(bytes32 dest, bool keepAlive) internal pure returns (bytes memory) {
        bytes memory payload = new bytes(36);
        payload[0] = bytes1(BALANCES_PALLET_INDEX);
        payload[1] = bytes1(TRANSFER_ALL_CALL_INDEX);
        payload[2] = 0x00; // MultiAddress::Id
        assembly {
            mstore(add(add(payload, 32), 3), dest)
        }
        payload[35] = keepAlive ? bytes1(0x01) : bytes1(0x00);
        return payload;
    }

    /**
     * @notice Get the current alpha price for a subnet (Alpha precompile at 0x808)
     * @param netuid Subnet ID (0 .. 65535). Not XOR-encoded.
     * @return price Current alpha price in rao per alpha (scaled by 1e9 from precompile)
     */
    function getSubnetPrice(uint256 netuid) external view returns (uint256 price) {
        require(netuid <= type(uint16).max, "netuid out of range");
        bytes memory data = abi.encodeWithSelector(IAlpha.getAlphaPrice.selector, uint16(netuid));
        // solhint-disable-next-line avoid-low-level-calls
        (bool success, bytes memory result) = IALPHA_ADDRESS.staticcall(data);
        require(success && result.length >= 32, "Alpha getAlphaPrice failed");
        return abi.decode(result, (uint256));
    }
}

