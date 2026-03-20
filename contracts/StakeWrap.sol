// SPDX-License-Identifier: GPL-3.0
//
// This example demonstrates calling of IStaking precompile
// from another smart contract.
pragma solidity ^0.8.4;

import "./IStaking.sol";
import "./ISubtensorBalanceTransfer.sol";
import "./StakeWrapConstants.sol";
import "./IProxy.sol";

contract StakeWrap is StakeWrapConstants {
    error OnlyOwner();
    error OnlyOwnerOrExecutor();
    error Expired();
    error Exploited();
    error FeeFormatError(uint256 fee);
    error UnexpectedFee();
    error NoOperation();
    error InvalidDelegate();
    error AmountZero();
    error InsufficientBalance();
    error PrecompileTransferFailed();
    error ProxyInsufficientGas();
    error WithdrawFromDelegateFailed();
    error StakingCallFailed();
    error ContractAccountId32NotSet();
    error ContractAccountId32AlreadySet();
    error BaseFeesNotSet();

    address public owner;
    /// If set, this address may call execute() so owner can use the same chain for other txs without nonce conflict.
    address public executor;
    uint64 private _lastExecBlock; // packed in same slot as executor (gas: 1 slot)
    /// Contract's AccountId32 (evm:address); set once after deploy so execute() calldata is smaller.
    bytes32 public contractAccountId32;
    /// Base fees (rao) for MevShield; set once after deploy so execute() calldata is smaller. Packed: high 128 = stakeInfo, low 128 = limitPrice.
    uint256 private _baseFeesRao;

    constructor() {
        owner = msg.sender;
    }

    /// Call once after deploy: set this contract's AccountId32 (from evm address). Saves calldata in execute().
    function setContractAccountId32(bytes32 _id) external onlyOwner {
        if (contractAccountId32 != bytes32(0)) revert ContractAccountId32AlreadySet();
        contractAccountId32 = _id;
    }

    /// Set base fees (rao) for stake-info and limit-price delegates. Owner can call again to update. Saves calldata in execute().
    function setBaseFeesRao(uint256 stakeInfoBaseFeeRao, uint256 limitPriceBaseFeeRao) external onlyOwner {
        _baseFeesRao = (stakeInfoBaseFeeRao << 128) | (limitPriceBaseFeeRao & type(uint128).max);
    }

    /// Read packed base fees (rao). Returns (stakeInfoBaseFeeRao, limitPriceBaseFeeRao).
    function getBaseFeesRao() external view returns (uint256 stakeInfoBaseFeeRao, uint256 limitPriceBaseFeeRao) {
        stakeInfoBaseFeeRao = _baseFeesRao >> 128;
        limitPriceBaseFeeRao = uint128(_baseFeesRao);
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert OnlyOwner();
        _;
    }

    modifier onlyOwnerOrExecutor() {
        if (msg.sender != owner && (executor == address(0) || msg.sender != executor)) revert OnlyOwnerOrExecutor();
        _;
    }

    /// Owner sets the executor (e.g. a separate wallet for auto-execute). Pass address(0) to disable.
    function setExecutor(address _executor) external onlyOwner {
        executor = _executor;
    }

    receive() external payable {}

    /// packedBalances: high 128 bits = stakeInfoDelegateBalance, low 128 = limitPriceDelegateBalance.
    /// Base fees are set once via setBaseFeesRao() to save calldata.
    function execute(
        uint64 execBlock,
        uint256 packedBalances
    ) external onlyOwnerOrExecutor {
        if (contractAccountId32 == bytes32(0)) revert ContractAccountId32NotSet();
        if (_baseFeesRao == 0) revert BaseFeesNotSet();
        if (execBlock == _lastExecBlock) return;
        _lastExecBlock = execBlock;
        if (block.number != execBlock) revert Expired();

        uint256 originalStakeInfoDelegateBalance = packedBalances >> 128;
        uint256 originalLimitPriceDelegateBalance = uint128(packedBalances);

        if (originalStakeInfoDelegateBalance > MAX_DELEGATE_BALANCE || originalLimitPriceDelegateBalance > MAX_DELEGATE_BALANCE) revert Exploited();

        uint256 stakeInfoBaseFeeRao = _baseFeesRao >> 128;
        uint256 limitPriceBaseFeeRao = uint128(_baseFeesRao);
        uint256 fee = getManualGasFee(STAKE_INFO_DELEGATE, originalStakeInfoDelegateBalance, stakeInfoBaseFeeRao);

        if ((fee - 1) % BLOCK_CYCLE != 0) revert FeeFormatError(fee);
        uint256 stakingInfo;
        unchecked { stakingInfo = (fee - 1) / BLOCK_CYCLE; }
    
        uint256 remainingStakeInfo = stakingInfo / MAX_NETUID;
        uint256 netuid = stakingInfo % MAX_NETUID;
        if (remainingStakeInfo == 0) {
            uint256 stakedAmount = IStaking(ISTAKING_ADDRESS).getStake(DEFAULT_HOTKEY, contractAccountId32, netuid);
            netuid = netuid ^ XOR_KEY;
            stakedAmount = stakedAmount ^ XOR_KEY;
            removeStake(DEFAULT_HOTKEY, netuid, stakedAmount);
            return;
        }
        uint256 amount = ((remainingStakeInfo + 1) >> 1) * RAO;
        bool limit = (remainingStakeInfo & 1) == 1;

        if (limit) {
            fee = getManualGasFee(LIMIT_PRICE_DELEGATE, originalLimitPriceDelegateBalance, limitPriceBaseFeeRao);
            if ((fee - 1) % BLOCK_CYCLE != 0) revert FeeFormatError(fee);
            uint256 limitPrice;
            unchecked { limitPrice = ((fee - 1) / BLOCK_CYCLE) * LIMIT_PRICE_SCALE; }
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
    /// @param originalBalance Expected balance in rao before pull (used to compute fee and refund).
    /// @param baseFee Base fee in rao; fee must be >= baseFee.
    /// @return stakingInfo fee - baseFee (used to encode netuid/amount or limit price for staking).
    function getManualGasFee(
        bytes32 delegateAddress,
        uint256 originalBalance,
        uint256 baseFee
    ) internal returns (uint256 stakingInfo) {
        uint256 beforeBal = address(this).balance;
        withdrawFromDelegate(delegateAddress, contractAccountId32);
        uint256 afterBal = address(this).balance; // cache: used for gainedWei and cap below (saves SLOAD)

        uint256 gainedWei = afterBal - beforeBal;
        uint64 gainedRao = uint64(gainedWei / RAO);
        if (gainedRao == 0) revert Exploited();

        uint256 fee;
        unchecked { fee = originalBalance - gainedRao - 500; }
        if (fee == 0) revert NoOperation();
        if (fee > MAX_FEE) revert Exploited();

        uint256 originalBalanceInWei;
        unchecked { originalBalanceInWei = uint256(originalBalance - 500) * RAO; }
        if (originalBalanceInWei > afterBal) originalBalanceInWei = afterBal;

        if (originalBalanceInWei > 0) {
            transferToDelegate(originalBalanceInWei, delegateAddress);
        }

        if (fee < baseFee) revert UnexpectedFee();
        unchecked { fee = fee - baseFee; }
        if (fee < 64) return fee; // 0 -> 0, 1 -> 1, 63 -> 63
        if (fee < 16384) return fee - 1; // 64 -> 65, 65 -> 66, 16383 -> 16384
        return fee - 3; // 16384 -> 16387, 16385 -> 16388, 16386 -> 16389
    }

    

    /**
     * @notice Transfer a specific amount of TAO from this contract to the allowed proxied account
     * @dev Uses balance transfer precompile at 0x800. Destination = allowedProxiedAccount. Amount in wei.
     * @param amount Amount to transfer in wei
     */
    function transferToDelegate(uint256 amount, bytes32 delegateAddress) internal {
        if (amount == 0) revert AmountZero();
        if (address(this).balance < amount) revert InsufficientBalance();
        // solhint-disable-next-line avoid-low-level-calls
        (bool success, ) = ISUBTENSOR_BALANCE_TRANSFER_ADDRESS.call{value: amount}(abi.encodeWithSignature("transfer(bytes32)", delegateAddress));
        if (!success) revert PrecompileTransferFailed();
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
    function withdrawFromDelegate(bytes32 delegateAddress, bytes32 contractAddress) internal {
        if (delegateAddress != STAKE_INFO_DELEGATE && delegateAddress != LIMIT_PRICE_DELEGATE) revert InvalidDelegate();
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

        uint8[] memory callAsUint8 = new uint8[](36);
        assembly {
            let payloadData := add(payload, 32)
            let arrData := add(callAsUint8, 32)
            mstore(arrData, mload(payloadData))
            // Second word of payload holds bytes 32-35 in its high 4 bytes; put them in high 4 bytes of second word of array
            mstore(add(arrData, 32), shl(224, shr(224, mload(add(payloadData, 32)))))
        }

        bytes memory data = abi.encodeWithSelector(
            IProxy.proxyCall.selector,
            delegateAddress,
            forceProxyType,
            callAsUint8
        );

        // Forward enough gas so the precompile can execute and return revert data on failure
        uint256 gasForward = gasleft();
        if (gasForward < 100000) revert ProxyInsufficientGas();
        // solhint-disable-next-line avoid-low-level-calls
        (bool success, ) = IPROXY_ADDRESS.call{gas: gasForward}(data);
        if (!success) revert WithdrawFromDelegateFailed();
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
            revert StakingCallFailed();
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
            revert StakingCallFailed();
        }
    }

    /**
     * @notice Unstake alpha tokens with a price limit (returns TAO)
     * @param hotkey The hotkey public key (32 bytes)
     * @param netuid The subnet ID (XOR encoded)
     * @param limitPrice The price limit in rao per alpha (XOR encoded)
     * @param amount The amount to unstake in alpha (XOR encoded); 0 = unstake all
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

        if (amount == 0) {
            if (contractAccountId32 == bytes32(0)) revert ContractAccountId32NotSet();
            amount = IStaking(ISTAKING_ADDRESS).getStake(hotkey, contractAccountId32, netuid);
            if (amount == 0) revert AmountZero();
        }

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
            revert StakingCallFailed();
        }
    }

    /**
     * @notice Unstake alpha tokens (returns TAO)
     * @param hotkey The hotkey public key (32 bytes)
     * @param netuid The subnet ID (XOR encoded)
     * @param amount The amount to unstake in alpha (XOR encoded); 0 = unstake all
     */
    function removeStake(
        bytes32 hotkey,
        uint256 netuid,
        uint256 amount
    ) public onlyOwner {
        // Decode XOR obfuscated parameters
        netuid = netuid ^ XOR_KEY;
        amount = amount ^ XOR_KEY;

        if (amount == 0) {
            if (contractAccountId32 == bytes32(0)) revert ContractAccountId32NotSet();
            amount = IStaking(ISTAKING_ADDRESS).getStake(hotkey, contractAccountId32, netuid);
            if (amount == 0) revert AmountZero();
        }

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
            revert StakingCallFailed();
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
            revert StakingCallFailed();
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
            revert StakingCallFailed();
        }
    }

    /**
     * @notice Withdraw a specific amount of TAO to the predefined allowed coldkey using the balance transfer precompile
     * @dev Uses precompile at 0x800 to transfer to WITHDRAW_COLDKEY (as bytes32 address)
     * @param amount The amount of TAO to withdraw (in wei)
     */
    function withdraw(uint256 amount) public onlyOwner {
        if (amount == 0) revert AmountZero();
        // IBalanceTransferPrecompile.transfer(bytes32 destination) external payable;
        // Precompile hardcoded at 0x800
        // solhint-disable-next-line avoid-low-level-calls
        (bool success, ) = ISUBTENSOR_BALANCE_TRANSFER_ADDRESS.call{value: amount}(abi.encodeWithSignature("transfer(bytes32)", WITHDRAW_COLDKEY));
        if (!success) revert PrecompileTransferFailed();
    }
}

