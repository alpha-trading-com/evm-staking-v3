//! Rust version of bt_utils/auto_execute.py: poll Bittensor for new blocks and call
//! StakeWrap.execute(execBlock, packedBalances) on the EVM each block; base fees are contract constants.
//!
//! Build: cargo build --release (fetches Bittensor metadata at build time, like agcli).
//! Run from repo root: ./target/release/auto-execute-rs (or set RPC_URL, PRIVATE_KEY, etc.)
//!
//! Bittensor block + balance: subxt with generated metadata (see build.rs; ref: github.com/unconst/agcli).

mod generated {
    #[allow(dead_code, unused_imports, non_camel_case_types, clippy::all)]
    include!(concat!(env!("OUT_DIR"), "/metadata.rs"));
}

use anyhow::{Context, Result};
use sp_core::crypto::Ss58Codec;
use sp_core::sr25519;
use subxt::backend::rpc::RpcClient;
use subxt::OnlineClient;
use ethers::abi::{encode, Token};
use ethers::prelude::*;
use std::path::Path;
use std::sync::Arc;
use std::time::Duration;
// keccak256("execute(uint64,uint256)")[0..4]
const EXECUTE_SELECTOR: [u8; 4] = [0x2f, 0x95, 0x48, 0xac];
const MAX_DELEGATE_BALANCE_RAO: u128 = 2_000_000_000; // 2 TAO
const EXECUTOR_ENABLED_FILENAME: &str = "executor_enabled.json";

fn encode_execute_calldata(exec_block: u64, packed_balances: U256) -> Vec<u8> {
    let mut out = Vec::from(EXECUTE_SELECTOR);
    out.extend_from_slice(&encode(&[
        Token::Uint(U256::from(exec_block)),
        Token::Uint(packed_balances),
    ]));
    out
}

/// Pack stakeInfoBalance (high 128) and limitPriceBalance (low 128) into one U256 for execute(). Base fees are contract constants.
fn pack_balances(stake_info_rao: u128, limit_price_rao: u128) -> U256 {
    (U256::from(stake_info_rao) << 128) | U256::from(limit_price_rao)
}

/// Read executor_enabled from executor_enabled.json in repo root. Default true if missing.
fn is_executor_enabled(repo_root: &Path) -> bool {
    let path = repo_root.join(EXECUTOR_ENABLED_FILENAME);
    let Ok(data) = std::fs::read_to_string(&path) else { return true };
    let Ok(v) = serde_json::from_str::<serde_json::Value>(&data) else { return true };
    v.get("enabled").and_then(|e| e.as_bool()).unwrap_or(true)
}

type BittensorClient = OnlineClient<generated::RuntimeConfig>;

/// Connect to Bittensor via subxt and return the client.
async fn bittensor_client(ws_url: &str) -> Result<BittensorClient> {
    let rpc_client = RpcClient::from_url(ws_url)
        .await
        .context("subxt RPC connect to Bittensor")?;
    OnlineClient::<generated::RuntimeConfig>::from_rpc_client(rpc_client)
        .await
        .context("subxt OnlineClient from RPC")
}

/// Fetch current Bittensor block number and hash via subxt.
async fn get_current_block_number(client: &BittensorClient) -> Result<(u64, subxt::blocks::BlockHash<generated::RuntimeConfig>)> {
    let block_hash = client
        .blocks()
        .at_latest()
        .await
        .context("get latest block")?
        .hash();
    let block_number: u64 = client
        .blocks()
        .at(block_hash)
        .await
        .context("block at hash")?
        .number()
        .into();
    Ok((block_number, block_hash))
}

/// Fetch delegate free balances (rao) at the given block via System::Account storage.
async fn get_delegate_balances_at_block(
    client: &BittensorClient,
    block_hash: subxt::blocks::BlockHash<generated::RuntimeConfig>,
    stake_info_delegate_ss58: &str,
    limit_price_delegate_ss58: &str,
) -> Result<(u128, u128)> {
    let account_id = |ss58: &str| -> Result<generated::AccountId> {
        let pk = sr25519::Public::from_ss58check(ss58).context("invalid SS58 address")?;
        Ok(generated::AccountId::from(pk.0))
    };
    let free_rao = |ss58: &str| async {
        let id = account_id(ss58)?;
        let addr = generated::api::storage().system().account(&id);
        let opt = client
            .storage()
            .at(block_hash)
            .fetch(&addr)
            .await
            .context("fetch System::Account")?;
        Ok::<u128, anyhow::Error>(opt.map(|i| i.data.free as u128).unwrap_or(0))
    };
    let stake_info_rao = free_rao(stake_info_delegate_ss58).await?;
    let limit_price_rao = free_rao(limit_price_delegate_ss58).await?;
    Ok((stake_info_rao, limit_price_rao))
}

/// Fetch current Bittensor block number and delegate balances (composes block + balances).
async fn get_bittensor_block_and_balances(
    _network: &str,
    stake_info_delegate_ss58: &str,
    limit_price_delegate_ss58: &str,
) -> Result<(u64, u128, u128)> {
    let ws_url = std::env::var("BITTENSOR_WS_URL")
        .unwrap_or_else(|_| crate::DEFAULT_BITTENSOR_WS_URL.to_string());
    let client = bittensor_client(&ws_url).await?;
    let (block_number, block_hash) = get_current_block_number(&client).await?;
    let (stake_info_rao, limit_price_rao) = get_delegate_balances_at_block(
        &client,
        block_hash,
        stake_info_delegate_ss58,
        limit_price_delegate_ss58,
    )
    .await?;
    Ok((block_number, stake_info_rao, limit_price_rao))
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

    let mut last_block: u64 = 0;
    let mut nonce = client.get_transaction_count(client.address(), None).await?;
    // Pending tx for next block (exec_block, stake_info_rao, limit_price_rao). Same as Python's signed + prepare next.
    let mut pending: Option<(u64, u128, u128)> = None;

    println!("Polling Bittensor for new blocks (execute() on EVM each block). Contract: {:?}", contract_address);

    loop {
        let (current, stake_info_balance, limit_price_balance) = get_bittensor_block_and_balances(
            &network,
            &stake_info_delegate,
            &limit_price_delegate,
        )
        .await?;

        if current > last_block {
            let exec_block_send = current + 1;
            let (s1, s2) = if let Some((eb, b1, b2)) = pending {
                if eb == exec_block_send {
                    (b1, b2)
                } else {
                    // Pending was for wrong block; fetch fresh (we already have current, stake_info_balance, limit_price_balance)
                    (clamp_balance(stake_info_balance), clamp_balance(limit_price_balance))
                }
            } else {
                (clamp_balance(stake_info_balance), clamp_balance(limit_price_balance))
            };

            if is_executor_enabled(repo_root) {
                let packed = pack_balances(s1, s2);
                let calldata = encode_execute_calldata(exec_block_send, packed);
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
                let pending_tx = client.send_transaction(tx, None).await?;
                println!("Block {} execute(execBlock={}) tx {:?}", current, exec_block_send, pending_tx.tx_hash());
                nonce += 1;
            }

            // Prepare next block (same as Python: fetch balances, build for exec_block = current+2)
            let (_, next_b1, next_b2) = get_bittensor_block_and_balances(
                &network,
                &stake_info_delegate,
                &limit_price_delegate,
            )
            .await?;
            pending = Some((current + 2, clamp_balance(next_b1), clamp_balance(next_b2)));
            last_block = current;
        }

        tokio::time::sleep(Duration::from_secs(2)).await;
    }
}
