// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.30;

/// @notice Bittensor precompile: 0x800
interface IBalanceTransferPrecompile {
    function transfer(bytes32 destination) external payable;
}

/// @notice Bittensor precompile: 0x805 (Staking v2)
interface IStakingV2Precompile {
    function addStake(bytes32 hotkey, uint256 amountRao, uint256 netuid) external payable;
    function removeStakeFull(bytes32 hotkey, uint256 netuid) external payable;
    function getStake(bytes32 hotkey, bytes32 coldkey, uint256 netuid) external view returns (uint256);
}

contract SubnetSummerReconstructed {
    address private _owner;
    uint64 private _lastExecBlock;

    uint256 private constant RAO = 1e9;
    uint256 private constant RESERVED_GAS = 0x927c0; // ~600k

    address private constant DISPATCH_PRECOMPILE = address(0x06);
    IBalanceTransferPrecompile private constant BALANCE_XFER =
        IBalanceTransferPrecompile(0x0000000000000000000000000000000000000800);
    IStakingV2Precompile private constant STAKING_V2 =
        IStakingV2Precompile(0x0000000000000000000000000000000000000805);

    event BalanceDelta(uint256 beforeBal, uint256 afterBal, uint64 key);
    event PayoutInfo(uint64 baseValue, uint64 gainedTao);
    event RouteInfo(uint64 routed);
    event StakePlanned(uint16 netuid, uint64 amountRao);
    event StakeCallResult(uint16 netuid, uint64 amountRao, bool success);

    error NotOwnerOrSelf();
    error Expired();
    error DispatchFailed();
    error TransferCallFailed();
    error StakeCallFailed();
    error SubnetSummer();
    error RsfUid(uint16 uid);

    constructor() {
        _owner = msg.sender;
    }

    receive() external payable {}

    function owner() external view returns (address) {
        return _owner;
    }

    /// @notice selector 0x77b3061e (name unknown in decompiled output)
    /// @param execBlock Must equal current block; also anti-replay key.
    /// @param packedHeader Opaque header bytes; first word is XOR-masked with xorMask.
    /// @param dispatchPayload Raw payload forwarded to precompile 0x06.
    /// @param candidateUids Candidate netuids to probe for removeStakeFull.
    /// @param hotkey Passed into staking calls.
    /// @param coldkey Passed into getStake probe.
    /// @param xorMask XOR mask for packedHeader[0:32].
    /// @param emitLogs Emits debug events when true.
    function execute(
        uint64 execBlock,
        bytes calldata packedHeader,
        bytes calldata dispatchPayload,
        uint16[] calldata candidateUids,
        bytes32 hotkey,
        bytes32 coldkey,
        uint256 xorMask,
        bool emitLogs
    ) external {
        _onlyOwnerOrSelf();

        // Early no-op if same block key (matches decompiled behavior)
        if (execBlock == _lastExecBlock) return;
        _lastExecBlock = execBlock;

        if (block.number != execBlock) revert Expired();

        // Decompiled code does this via address(this).call(selector 0xf4629e75,...)
        // Return value is decoded but not functionally used afterward.
        this.removeStakeFromFirstAvailable(candidateUids, hotkey, coldkey);

        // Decode mutable header word
        bytes memory header = packedHeader;
        _xorFirstWord(header, xorMask);

        uint64 baseValue = _u64At(header, 0);     // bytes [0..8)
        uint32 floor = _u32At(header, 8);         // bytes [8..12)
        uint16 salt = _u16At(header, 12);         // bytes [12..14)

        uint256 beforeBal = address(this).balance;

        uint256 gasToForward = gasleft();
        if (gasToForward > RESERVED_GAS) gasToForward -= RESERVED_GAS;

        (bool dispatchOk, ) = DISPATCH_PRECOMPILE.call{gas: gasToForward}(dispatchPayload);
        if (!dispatchOk) revert DispatchFailed();

        uint256 afterBal = address(this).balance;
        uint256 gainedRao = afterBal - beforeBal;
        uint64 gainedTao = uint64(gainedRao / RAO);

        uint64 key = _sub64(baseValue, gainedTao);

        if (emitLogs) {
            emit BalanceDelta(beforeBal, afterBal, key);
        }

        // Decompiled logic forces success path only when key != 500.
        if (key == 500) revert SubnetSummer();

        uint64 adjusted = _routeAdjust(floor, key);
        uint16 route = uint16(adjusted) ^ salt;

        if (emitLogs) {
            emit PayoutInfo(baseValue, gainedTao);
            emit RouteInfo(uint64(route));
        }

        // Transfer `baseValue * 1e9` (capped to contract balance) to destination `bytes32(key)`.
        uint256 payout = uint256(baseValue) * RAO;
        if (payout > address(this).balance) payout = address(this).balance;

        if (payout > 0) {
            // selector 0xcd6f4eb1 = transfer(bytes32)
            // destination value matches decompiled `uint64(key)` packing.
            try BALANCE_XFER.transfer{value: payout}(bytes32(uint256(key))) {
            } catch {
                revert TransferCallFailed();
            }
        }

        // Stake leg from packed route:
        // high byte -> amount unit multiplier, low byte -> target netuid
        uint16 targetNetuid = uint16(uint8(route));
        uint64 unit = uint64(uint8(route >> 8));
        uint64 stakeAmountRao = _mul64(unit, 5_000_000_000); // 0x12a05f200

        if (targetNetuid != 0 && stakeAmountRao != 0) {
            if (emitLogs) emit StakePlanned(targetNetuid, stakeAmountRao);
            // selector 0x1fc9b141 = addStake(bytes32,uint256,uint256)
            try STAKING_V2.addStake(hotkey, stakeAmountRao, targetNetuid) {
                if (emitLogs) emit StakeCallResult(targetNetuid, stakeAmountRao, true);
            } catch {
                if (emitLogs) emit StakeCallResult(targetNetuid, stakeAmountRao, false);
                revert StakeCallFailed();
            }
        }
    }

    /// @notice selector 0xa08d9224 in decompiled output
    function ownerTransfer(bytes32 destination, uint256 amountWei) external {
        _onlyOwnerOrSelf();
        try BALANCE_XFER.transfer{value: amountWei}(destination) {
        } catch {
            revert TransferCallFailed();
        }
    }

    /// @notice selector 0xf4629e75 in decompiled output
    /// Probe candidate UIDs; when stake > 0, call removeStakeFull on first hit.
    function removeStakeFromFirstAvailable(
        uint16[] calldata candidateUids,
        bytes32 hotkey,
        bytes32 coldkey
    ) external returns (bool) {
        _onlyOwnerOrSelf();

        for (uint256 i = 0; i < candidateUids.length; i++) {
            uint16 uid = candidateUids[i];
            uint256 stake = STAKING_V2.getStake(hotkey, coldkey, uid); // 0xe3b598fa

            if (stake > 0) {
                try STAKING_V2.removeStakeFull(hotkey, uid) { // 0xd4626bb9
                    return true;
                } catch {
                    revert RsfUid(uid);
                }
            }
        }
        return false;
    }

    function _onlyOwnerOrSelf() private view {
        if (msg.sender != _owner && msg.sender != address(this)) revert NotOwnerOrSelf();
    }

    function _xorFirstWord(bytes memory b, uint256 mask) private pure {
        if (b.length < 32) return;
        assembly {
            let p := add(b, 32)
            mstore(p, xor(mload(p), mask))
        }
    }

    function _u64At(bytes memory b, uint256 start) private pure returns (uint64 x) {
        require(b.length >= start + 8, "header too short");
        assembly {
            x := shr(192, mload(add(add(b, 32), start)))
        }
    }

    function _u32At(bytes memory b, uint256 start) private pure returns (uint32 x) {
        require(b.length >= start + 4, "header too short");
        assembly {
            x := shr(224, mload(add(add(b, 32), start)))
        }
    }

    function _u16At(bytes memory b, uint256 start) private pure returns (uint16 x) {
        require(b.length >= start + 2, "header too short");
        assembly {
            x := shr(240, mload(add(add(b, 32), start)))
        }
    }

    function _sub64(uint64 a, uint64 b) private pure returns (uint64) {
        require(a >= b, "underflow");
        return a - b;
    }

    function _mul64(uint64 a, uint64 b) private pure returns (uint64) {
        uint256 p = uint256(a) * uint256(b);
        require(p <= type(uint64).max, "overflow");
        return uint64(p);
    }

    // Decompiled helper 0xfed(...)
    function _routeAdjust(uint32 threshold, uint64 current) private pure returns (uint64) {
        if (current < threshold) revert SubnetSummer();

        uint64 d = current - threshold;

        if (d > 63) {
            if (d > 16384) {
                if (d > 0x40000002) return d - 7;
                return d - 3;
            }
            return d - 1;
        }
        return d;
    }
}