//! Rust version of bt_utils/auto_execute.py: poll Bittensor for new blocks and call
//! StakeWrap.execute(execBlock, packedBalances) on the EVM each block; base fees are contract constants.
//!
//! Env: RPC_URL (EVM); EXECUTOR_PRIVATE_KEY (recommended) or PRIVATE_KEY (owner); EXECUTOR_GAS_LIMIT (default 600000);
//! BITTENSOR_WS_URL (direct WS RPC, like Python); STAKE_INFO_DELEGATE_SS58 / LIMIT_PRICE_DELEGATE_SS58 (optional, match bt_utils/constants.py).
//! executor_enabled.json in repo root: {"enabled": true/false} to allow/skip sending (default true if missing).
//!
//! Build: cargo build --release
//! Run from repo root: ./target/release/auto-execute-rs
//!
//! If you see "execute reverted" with 0x..., the contract reverted (e.g. OnlyOwnerOrExecutor, Expired, Exploited).
//! Ensure setExecutor(executorAddress) was called and EXECUTOR_PRIVATE_KEY matches that address.

use anyhow::{Context, Result};
use auto_execute_rs::{
    get_current_block_bittensor, get_delegate_balances_bittensor, DEFAULT_BITTENSOR_WS_URL,
};
use ethers::abi::{encode, Token};
use ethers::prelude::*;
use ethers::types::transaction::eip2718::TypedTransaction;
use std::path::Path;
use std::sync::Arc;
use std::time::Duration;
// Selectors (first 4 bytes of keccak256(signature))
fn execute_selector() -> [u8; 4] {
    ethers::utils::keccak256("execute(uint64,uint256)").as_ref()[..4]
        .try_into()
        .unwrap()
}
fn executor_selector() -> [u8; 4] {
    ethers::utils::keccak256("executor()").as_ref()[..4]
        .try_into()
        .unwrap()
}
fn owner_selector() -> [u8; 4] {
    ethers::utils::keccak256("owner()").as_ref()[..4]
        .try_into()
        .unwrap()
}

const MAX_DELEGATE_BALANCE_RAO: u128 = 2_000_000_000; // 2 TAO (match bt_utils/constants.py)
const EXECUTOR_ENABLED_FILENAME: &str = "executor_enabled.json";

fn encode_execute_calldata(exec_block: u64, packed_balances: U256) -> Vec<u8> {
    let mut out = Vec::from(execute_selector());
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

/// Fetch current Bittensor block number and delegate balances via direct WS RPC (like Python).
async fn get_bittensor_block_and_balances(
    _network: &str,
    stake_info_delegate_ss58: &str,
    limit_price_delegate_ss58: &str,
) -> Result<(u64, u128, u128)> {
    let ws_url = std::env::var("BITTENSOR_WS_URL")
        .unwrap_or_else(|_| DEFAULT_BITTENSOR_WS_URL.to_string());
    let block_number = get_current_block_bittensor(&ws_url).await?;
    let (stake_info_rao, limit_price_rao) =
        get_delegate_balances_bittensor(&ws_url, stake_info_delegate_ss58, limit_price_delegate_ss58)
            .await?;
    Ok((block_number, stake_info_rao, limit_price_rao))
}

fn clamp_balance(rao: u128) -> u128 {
    rao.min(MAX_DELEGATE_BALANCE_RAO)
}

/// Call contract executor() or owner() (view), decode 32-byte return as Address.
async fn contract_view_address<M: Middleware>(
    client: &M,
    contract_address: Address,
    selector: [u8; 4],
) -> Result<Address> {
    let tx = TransactionRequest::new()
        .to(contract_address)
        .data(selector);
    let typed_tx: TypedTransaction = tx.into();
    let bytes = client.call(&typed_tx, None).await.context("contract view call")?;
    let b = bytes.as_ref();
    if b.len() >= 32 {
        Ok(Address::from_slice(&b[b.len() - 20..]))
    } else {
        anyhow::bail!("contract returned {} bytes, expected 32", b.len())
    }
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

    let use_executor_wallet = std::env::var("EXECUTOR_PRIVATE_KEY").is_ok();
    let executor_addr = contract_view_address(client.as_ref(), contract_address, executor_selector()).await?;
    let owner_addr = contract_view_address(client.as_ref(), contract_address, owner_selector()).await?;
    let signer_addr = client.address();

    if use_executor_wallet {
        let zero = Address::zero();
        if executor_addr == zero {
            anyhow::bail!("Contract has no executor set. Owner must call setExecutor(executorAddress) first.");
        }
        if executor_addr != signer_addr {
            anyhow::bail!(
                "Account {:?} is not contract executor {:?}",
                signer_addr,
                executor_addr
            );
        }
        println!("Using executor wallet (EXECUTOR_PRIVATE_KEY)");
    } else {
        if owner_addr != signer_addr {
            anyhow::bail!(
                "Account {:?} is not contract owner {:?}",
                signer_addr,
                owner_addr
            );
        }
        println!("Using owner wallet (PRIVATE_KEY)");
    }

    // Delegate SS58s – match bt_utils/constants.py (STAKE_INFO_DELEGATE, LIMIT_PRICE_DELEGATE)
    let stake_info_delegate = std::env::var("STAKE_INFO_DELEGATE_SS58").unwrap_or_else(|_| "5FptUDrtvf6y4GmQKekEPmELeSC5MsLpRRDPFNXmHmCwfbs3".to_string());
    let limit_price_delegate = std::env::var("LIMIT_PRICE_DELEGATE_SS58").unwrap_or_else(|_| "5Hh7A2qiLTQFVSGT4g7ADcSiCuqeKN1BgumDwhQBmA8dMwBX".to_string());

    println!("Contract: {:?}", contract_address);
    println!(
        "Delegates: STAKE_INFO={}, LIMIT_PRICE={}",
        stake_info_delegate, limit_price_delegate
    );

    // Initial balances (match Python)
    let (_, init_s1, init_s2) = get_bittensor_block_and_balances(
        &network,
        &stake_info_delegate,
        &limit_price_delegate,
    )
    .await?;
    println!(
        "Balances from chain (rao): stake_info={}, limit_price={}",
        clamp_balance(init_s1),
        clamp_balance(init_s2)
    );
    println!("Polling for new blocks (Bittensor chain)...");

    let mut last_block: u64 = 0;
    let mut nonce = client.get_transaction_count(client.address(), None).await?;
    // Pending tx for next block (exec_block, stake_info_rao, limit_price_rao). Same as Python's signed + prepare next.
    let mut pending: Option<(u64, u128, u128)> = None;

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
                println!(
                    "Balances from chain (rao): stake_info={}, limit_price={}",
                    s1, s2
                );
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
                match client.send_transaction(tx, None).await {
                    Ok(pending_tx) => {
                        println!(
                            "Block {} execute(execBlock={}) tx {:?}",
                            current,
                            exec_block_send,
                            pending_tx.tx_hash()
                        );
                        nonce += 1;
                    }
                    Err(e) => {
                        let msg = e.to_string();
                        if msg.contains("Failed 0x") || msg.contains("0x") {
                            eprintln!("Block {} execute reverted: {}", current, msg);
                            eprintln!("  -> Check: contract executor is set (owner called setExecutor) and EXECUTOR_PRIVATE_KEY matches that address.");
                        } else {
                            eprintln!("Block {} execute failed: {}", current, msg);
                        }
                    }
                }
            }

            // Re-read executor_enabled (match Python: is_executor_enabled_flag = is_executor_enabled() after send)
            // Next iteration will use fresh value from is_executor_enabled(repo_root).

            // Prepare next block (same as Python: fetch balances, build for exec_block = current+2)
            match get_bittensor_block_and_balances(
                &network,
                &stake_info_delegate,
                &limit_price_delegate,
            )
            .await
            {
                Ok((_, next_b1, next_b2)) => {
                    pending = Some((current + 2, clamp_balance(next_b1), clamp_balance(next_b2)));
                }
                Err(e) => {
                    eprintln!("Block {} failed to fetch next balances: {}", current, e);
                }
            }
            last_block = current;
        }

        tokio::time::sleep(Duration::from_secs(2)).await;
    }
}
