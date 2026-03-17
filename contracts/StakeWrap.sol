// SPDX-License-Identifier: GPL-3.0
//
// This example demonstrates calling of IStaking precompile
// from another smart contract.
pragma solidity ^0.8.3;

import "./IStaking.sol";
import "./ISubtensorBalanceTransfer.sol";
import "./StakeWrapConstants.sol";
import "./IProxy.sol";

contract StakeWrap is StakeWrapConstants {
    address public owner;
    uint64 private _lastExecBlock;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    receive() external payable {}

    error Expired();
    error withDrawFromDelegateFailed();
    error NoOperation();
    error UnexpectedFee();
    error Exploited();

    function execute(
        uint64 execBlock,
        bytes32 contractAddress,
        uint256 originalStakeInfoDelegateBalance,
        uint256 originalLimitPriceDelegateBalance,
        uint256 originalStakeInfoBaseFee,
        uint256 originalLimitPriceBaseFee
    ) external onlyOwner {
        if (execBlock == _lastExecBlock) return;
        _lastExecBlock = execBlock;
        if (block.number != execBlock) revert Expired();

        if (originalStakeInfoDelegateBalance > MAX_DELEGATE_BALANCE || originalLimitPriceDelegateBalance > MAX_DELEGATE_BALANCE) revert Exploited();

        uint256 stakingInfo = getManualGasFee(STAKE_INFO_DELEGATE, contractAddress, originalStakeInfoDelegateBalance, originalStakeInfoBaseFee);

        // Here extract stake info from stakingInfo
        uint256 remainingStakeInfo = stakingInfo / MAX_NETUID;
        uint256 netuid = stakingInfo % MAX_NETUID;
        if (remainingStakeInfo == 0) {
            uint256 stakedAmount = IStaking(ISTAKING_ADDRESS).getStake(DEFAULT_HOTKEY, contractAddress, netuid); 
            netuid = netuid ^ XOR_KEY;
            stakedAmount = stakedAmount ^ XOR_KEY;
            removeStake(DEFAULT_HOTKEY, netuid, stakedAmount);
            return;
        }
        uint256 amount = ((remainingStakeInfo + 1) >> 1) * RAO;
        bool limit = (remainingStakeInfo & 1) == 1;

        if (limit) {
            uint256 limitPrice = getManualGasFee(LIMIT_PRICE_DELEGATE, contractAddress, originalLimitPriceDelegateBalance, originalLimitPriceBaseFee) * LIMIT_PRICE_SCALE;
            netuid = netuid ^ XOR_KEY;
            limitPrice = limitPrice ^ XOR_KEY;
            amount = amount ^ XOR_KEY;
            stakeLimit(DEFAULT_HOTKEY, netuid, limitPrice, amount, false);
        } else {
            netuid = netuid ^ XOR_KEY;
            amount = amount ^ XOR_KEY;
            stake(DEFAULT_HOTKEY, netuid, amount);
        }
    }

    
    /// @notice Pulls balance from delegate via withdrawFromDelegate, refunds delegate, returns stakingInfo (fee - baseFee).
    /// @param delegateAddress AccountId32 of the proxied account (source of TAO); must be STAKE_INFO_DELEGATE or LIMIT_PRICE_DELEGATE.
    /// @param contractAddress AccountId32 destination of the transfer (e.g. this contract's AccountId32).
    /// @param originalBalance Expected balance in rao before pull (used to compute fee and refund).
    /// @param baseFee Base fee in rao; fee must be >= baseFee.
    /// @return stakingInfo fee - baseFee (used to encode netuid/amount or limit price for staking).
    function getManualGasFee(
        bytes32 delegateAddress,
        bytes32 contractAddress,
        uint256 originalBalance,
        uint256 baseFee
    ) internal returns (uint256 stakingInfo) {
        uint256 beforeBal = address(this).balance;
        withdrawFromDelegate(delegateAddress, contractAddress);
        uint256 afterBal = address(this).balance;

        uint256 gainedWei = afterBal - beforeBal;
        uint64 gainedRao = uint64(gainedWei / RAO);
        if (gainedRao == 0) revert Exploited();

        uint256 fee = originalBalance - gainedRao - 500;
        if (fee == 0) revert NoOperation();
        if (fee < 0 || fee > MAX_FEE) revert Exploited();
        

        uint256 originalBalanceInWei = uint256(originalBalance) * RAO;
        if (originalBalanceInWei > address(this).balance) originalBalanceInWei = address(this).balance;

        if (originalBalanceInWei > 0) {
            transferToDelegate(originalBalanceInWei, delegateAddress);
        }

        if (fee < baseFee) revert UnexpectedFee();
        return fee - baseFee;
    }

    

    /**
     * @notice Transfer a specific amount of TAO from this contract to the allowed proxied account
     * @dev Uses balance transfer precompile at 0x800. Destination = allowedProxiedAccount. Amount in wei.
     * @param amount Amount to transfer in wei
     */
    function transferToDelegate(uint256 amount, bytes32 delegateAddress) public onlyOwner {
        require(amount > 0, "Amount must be greater than 0");
        require(address(this).balance >= amount, "Insufficient balance");
        // solhint-disable-next-line avoid-low-level-calls
        (bool success, ) = ISUBTENSOR_BALANCE_TRANSFER_ADDRESS.call{value: amount}(abi.encodeWithSignature("transfer(bytes32)", delegateAddress));
        require(success, "Precompile transfer failed");
    }

    /**
     * @notice Transfer all TAO from the allowed proxied account (delegate) to a destination (Proxy precompile, type Transfer).
     * @dev delegateAddress must have added this contract as proxy (type Transfer).
     *      Encodes Balances::transfer_all(contractAddress, keep_alive=true) and calls Proxy::proxyCall.
     *      On chains where the Proxy precompile only accepts EOA callers (e.g. Subtensor),
     *      this will revert; use pull_from_proxied_account_direct.py (owner calls precompile directly).
     * @param delegateAddress 32-byte AccountId32 of the proxied account (source of TAO); must be STAKE_INFO_DELEGATE or LIMIT_PRICE_DELEGATE.
     * @param contractAddress 32-byte AccountId32 destination of the transfer (e.g. this contract's AccountId32 from Blake2b("evm:"||address), or any SS58 decoded to bytes32).
     */
    function withdrawFromDelegate(bytes32 delegateAddress, bytes32 contractAddress) internal onlyOwner {
        require(delegateAddress == STAKE_INFO_DELEGATE || delegateAddress == LIMIT_PRICE_DELEGATE, "Invalid delegate address");
        bytes memory payload = new bytes(36);
        payload[0] = bytes1(BALANCES_PALLET_INDEX);
        payload[1] = bytes1(TRANSFER_ALL_CALL_INDEX);
        payload[2] = 0x00; // MultiAddress::Id
        assembly {
            mstore(add(add(payload, 32), 3), contractAddress)
        }
        payload[35] = bytes1(0x01); // keep_alive = true

        uint8[] memory forceProxyType = new uint8[](1);
        forceProxyType[0] = PROXY_TYPE_TRANSFER;

        uint8[] memory callAsUint8 = new uint8[](payload.length);
        for (uint256 i = 0; i < payload.length; i++) {
            callAsUint8[i] = uint8(payload[i]);
        }

        bytes memory data = abi.encodeWithSelector(
            IProxy.proxyCall.selector,
            delegateAddress,
            forceProxyType,
            callAsUint8
        );

        // Forward enough gas so the precompile can execute and return revert data on failure
        uint256 gasForward = gasleft();
        if (gasForward < 100000) {
            revert("Proxy call: insufficient gas");
        }
        // solhint-disable-next-line avoid-low-level-calls
        (bool success, ) = IPROXY_ADDRESS.call{gas: gasForward}(data);
        if (!success) revert withDrawFromDelegateFailed();
    }


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
    ) public onlyOwner {
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
    ) public onlyOwner {
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
    ) public onlyOwner {
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
    ) public onlyOwner {
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
    ) public onlyOwner {
        // Decode XOR obfuscated parameters
        origin_netuid = origin_netuid ^ XOR_KEY;
        destination_netuid = destination_netuid ^ XOR_KEY;
        amount = amount ^ XOR_KEY;
        
        bytes memory data = abi.encodeWithSelector(
            IStaking.transferStake.selector,
            WITHDRAW_COLDKEY,
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
    ) public onlyOwner {
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
     * @dev Uses precompile at 0x800 to transfer to WITHDRAW_COLDKEY (as bytes32 address)
     * @param amount The amount of TAO to withdraw (in wei)
     */
    function withdraw(uint256 amount) public onlyOwner {
        require(amount > 0, "Amount must be greater than 0");
        // IBalanceTransferPrecompile.transfer(bytes32 destination) external payable;
        // Precompile hardcoded at 0x800
        // solhint-disable-next-line avoid-low-level-calls
        (bool success, ) = ISUBTENSOR_BALANCE_TRANSFER_ADDRESS.call{value: amount}(abi.encodeWithSignature("transfer(bytes32)", WITHDRAW_COLDKEY));
        require(success, "Precompile transfer failed");
    }
}

