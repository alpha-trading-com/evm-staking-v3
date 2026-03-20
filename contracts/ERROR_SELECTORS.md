# StakeWrap.sol — Custom error selectors

Solidity custom errors use a 4-byte selector: `bytes4(keccak256("ErrorName(params)"))`.

## Errors defined in StakeWrap.sol

| Selector     | Error |
|-------------|--------|
| 0xc483c5fc | OnlyOwner() |
| 0x0f3d467e | OnlyOwnerOrExecutor() |
| 0x3d82d8d9 | Expired() |
| 0x5ba779b2 | Exploited() |
| 0x82824366 | FeeFormatError(uint256) |
| 0x0c11505d | UnexpectedFee() |
| 0xd3b896be | NoOperation() |
| 0x86360471 | InvalidDelegate() |
| 0xca5aa2ad | AmountZero() |
| 0xd678b8ce | InsufficientBalance() |
| 0xb7f1a4ec | PrecompileTransferFailed() |
| 0xa35516db | ProxyInsufficientGas() |
| 0x49d72fc7 | WithdrawFromDelegateFailed() |
| 0xa240668b | StakingCallFailed() |
| 0x56071d4b | ContractAccountId32NotSet() |
| 0x3dc66b14 | ContractAccountId32AlreadySet() |
| 0x3467baf8 | BaseFeesNotSet() |

## `Failed 0x2f9548ac`

**0x2f9548ac is not one of the above.** It does not match any error defined in StakeWrap.sol.

In `execute()`, when the contract calls the **IStaking precompile** (e.g. for stake/unstake), it forwards the precompile’s revert data:

```solidity
(bool success, bytes memory returnData) = ISTAKING_ADDRESS.call{...}(data);
if (!success && returnData.length > 0) {
    revert(add(32, returnData), returndata_size);  // forward precompile revert
}
```

So **0x2f9548ac is the error selector from the IStaking precompile** (or the chain’s staking logic), not from StakeWrap. The precompile reverted and that revert was passed through.

To interpret it you’d need the precompile/chain’s error definitions (e.g. Bittensor staking precompile ABI or docs).
