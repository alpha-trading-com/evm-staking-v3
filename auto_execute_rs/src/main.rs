//! Rust version of bt_utils/auto_execute.py: poll Bittensor for new blocks and call
//! StakeWrap.execute(execBlock, stakeInfoPacked, limitPricePacked) on the EVM each block.
//!
//! Build: cargo build --release
//! Run from repo root: ./target/release/auto-execute-rs (or set RPC_URL, PRIVATE_KEY, etc.)
//!
//! Bittensor block/balance query: get_current_block is implemented via WebSocket chain_getHeader;
//! delegate balances still need subxt or another RPC method.

use anyhow::{Context, Result};
use ethers::abi::{encode, Token};
use ethers::prelude::*;
use std::path::Path;
use std::sync::Arc;
use std::time::Duration;
// keccak256("execute(uint64,uint256,uint256)")[0..4]
const EXECUTE_SELECTOR: [u8; 4] = [0x9c, 0x42, 0x7b, 0x6e];
const MAX_DELEGATE_BALANCE_RAO: u128 = 2_000_000_000; // 2 TAO
const EXECUTOR_ENABLED_FILENAME: &str = "executor_enabled.json";

fn encode_execute_calldata(exec_block: u64, stake_info_packed: U256, limit_price_packed: U256) -> Vec<u8> {
    let mut out = Vec::from(EXECUTE_SELECTOR);
    out.extend_from_slice(&encode(&[
        Token::Uint(U256::from(exec_block)),
        Token::Uint(stake_info_packed),
        Token::Uint(limit_price_packed),
    ]));
    out
}

/// Pack balance (high 128) and base_fee (low 128) into one U256 for execute().
fn pack_balance_fee(balance_rao: u128, base_fee_rao: u128) -> U256 {
    let balance = U256::from(balance_rao);
    let fee = U256::from(base_fee_rao);
    (balance << 128) | fee
}

/// Read executor_enabled from executor_enabled.json in repo root. Default true if missing.
fn is_executor_enabled(repo_root: &Path) -> bool {
    let path = repo_root.join(EXECUTOR_ENABLED_FILENAME);
    let Ok(data) = std::fs::read_to_string(&path) else { return true };
    let Ok(v) = serde_json::from_str::<serde_json::Value>(&data) else { return true };
    v.get("enabled").and_then(|e| e.as_bool()).unwrap_or(true)
}

/// Fetch current Bittensor block number and delegate balances (stake_info_rao, limit_price_rao).
/// Block is fetched via WebSocket chain_getHeader; balances still need subxt or Balances::Account RPC.
#[allow(dead_code)]
async fn get_bittensor_block_and_balances(
    _network: &str,
    _stake_info_delegate_ss58: &str,
    _limit_price_delegate_ss58: &str,
) -> Result<(u64, u128, u128)> {
    let ws_url = std::env::var("BITTENSOR_WS_URL")
        .unwrap_or_else(|_| crate::DEFAULT_BITTENSOR_WS_URL.to_string());
    let block = crate::get_current_block_bittensor(&ws_url).await?;
    // TODO: Query Balances::Account for each delegate (e.g. subxt) to get stake_info_rao, limit_price_rao.
    anyhow::bail!(
        "Delegate balance query not implemented in Rust (block {} fetched). \
         Use subxt with Bittensor metadata for Balances::Account, or run bt_utils/auto_execute.py.",
        block
    );
}

fn clamp_balance(rao: u128) -> u128 {
    rao.min(MAX_DELEGATE_BALANCE_RAO)
}

#[tokio::main]
async fn main() -> Result<()> {
    dotenvy::dotenv().ok();
    let repo_root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().context("repo root")?;

    let rpc_url = std::env::var("RPC_URL").unwrap_or_else(|_| "https://test.finney.opentensor.ai/".to_string());
    let private_key = std::env::var("EXECUTOR_PRIVATE_KEY")
        .or_else(|_| std::env::var("PRIVATE_KEY"))
        .context("Set EXECUTOR_PRIVATE_KEY or PRIVATE_KEY")?;
    let network = std::env::var("BITTENSOR_NETWORK").unwrap_or_else(|_| "finney".to_string());
    let gas_limit: u64 = std::env::var("EXECUTOR_GAS_LIMIT").ok().and_then(|s| s.parse().ok()).unwrap_or(600_000);
    let gas_price_mult: f64 = std::env::var("EXECUTOR_GAS_PRICE_MULTIPLIER").ok().and_then(|s| s.parse().ok()).unwrap_or(1.0);

    let deployment_path = repo_root.join("deployment.json");
    let deployment: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(&deployment_path)?)?;
    let contract_address_hex = deployment.get("contract_address").context("contract_address")?.as_str().context("string")?;
    let contract_address: Address = contract_address_hex.parse().context("contract address")?;

    let provider = Provider::<Http>::try_from(rpc_url.as_str())?;
    let chain_id = provider.get_chainid().await?;
    let wallet = private_key.trim_start_matches("0x").parse::<LocalWallet>().context("private key")?.with_chain_id(chain_id.as_u64());
    let client = SignerMiddleware::new(provider, wallet);
    let client = Arc::new(client);

    // Delegate SS58s – should match bt_utils/constants.py or StakeWrapConstants.sol
    let stake_info_delegate = std::env::var("STAKE_INFO_DELEGATE_SS58").unwrap_or_else(|_| "5FptUDrtvf6y4GmQKekEPmELeSC5MsLpRRDPFNXmHmCwfbs3".to_string());
    let limit_price_delegate = std::env::var("LIMIT_PRICE_DELEGATE_SS58").unwrap_or_else(|_| "5Hh7A2qiLTQFVSGT4g7ADcSiCuqeKN1BgumDQBmA8dMwBX".to_string());

    let stake_info_base_fee: u128 = 1_061_771;   // STAKE_INFO_BASE_FEE_RAO
    let limit_price_base_fee: u128 = 1_061_770; // LIMIT_PRICE_BASE_FEE_RAO

    let mut last_block: u64 = 0;
    let mut nonce = client.get_transaction_count(client.address(), None).await?;
    let mut exec_block: u64 = 0;
    let mut is_executor_enabled = is_executor_enabled(repo_root);

    println!("Polling Bittensor for new blocks (execute() on EVM each block). Contract: {:?}", contract_address);

    loop {
        let (current, stake_info_balance, limit_price_balance) = get_bittensor_block_and_balances(
            &network,
            &stake_info_delegate,
            &limit_price_delegate,
        ).await?;

        if current > last_block {
            let stake_info_balance = clamp_balance(stake_info_balance);
            let limit_price_balance = clamp_balance(limit_price_balance);
            exec_block = current + 1;

            let stake_info_packed = pack_balance_fee(stake_info_balance, stake_info_base_fee);
            let limit_price_packed = pack_balance_fee(limit_price_balance, limit_price_base_fee);
            let calldata = encode_execute_calldata(exec_block, stake_info_packed, limit_price_packed);

            let base_gas = client.get_gas_price().await?;
            let gas_price = if gas_price_mult != 1.0 {
                U256::from((base_gas.as_u128() as f64 * gas_price_mult) as u128)
            } else {
                base_gas
            };
            let tx = TransactionRequest::new()
                .to(contract_address)
                .data(calldata)
                .gas(gas_limit)
                .gas_price(gas_price)
                .nonce(nonce);

            is_executor_enabled = is_executor_enabled(repo_root);
            if is_executor_enabled {
                let pending = client.send_transaction(tx, None).await?;
                println!("Block {} execute(execBlock={}) tx {:?}", current, exec_block, pending.tx_hash());
                nonce += 1;
            }
            last_block = current;
        }

        tokio::time::sleep(Duration::from_secs(2)).await;
    }
}
