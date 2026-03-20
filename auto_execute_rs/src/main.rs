use std::{fs, path::PathBuf, str::FromStr, time::Duration};

use alloy::{
    primitives::{address, keccak256, Address, U256},
    providers::{Provider, ProviderBuilder},
    signers::local::PrivateKeySigner,
    sol,
};
use anyhow::{anyhow, bail, Context, Result};
use dotenvy::dotenv;
use futures::StreamExt;
use parity_scale_codec::Decode;
use serde::Deserialize;
use subxt::{
    dynamic::{self, Value},
    utils::AccountId32,
    OnlineClient, PolkadotConfig,
};
use tokio::time::sleep;

const STAKE_INFO_DELEGATE: &str = "5FptUDrtvf6y4GmQKekEPmELeSC5MsLpRRDPFNXmHmCwfbs3";
const LIMIT_PRICE_DELEGATE: &str = "5Hh7A2qiLTQFVSGT4g7ADcSiCuqeKN1BgumDwhQBmA8dMwBX";
const EXECUTOR_ENABLED_FILENAME: &str = "executor_enabled.json";
const DEFAULT_BITTENSOR_WS_URL: &str = "wss://entrypoint-finney.opentensor.ai:443";

sol! {
    #[sol(rpc)]
    interface StakeWrap {
        function owner() external view returns (address);
        function executor() external view returns (address);
        function execute(uint64 execBlock, uint256 packedBalances) external;
    }
}

#[derive(Debug, Deserialize)]
struct DeploymentInfo {
    contract_address: String,
}

#[derive(Debug, Deserialize)]
struct ExecutorEnabled {
    enabled: bool,
}

// Minimal SCALE decode for System.Account storage value.
// This matches the common Substrate AccountInfo layout.
#[derive(Debug, Decode)]
struct AccountInfo {
    nonce: u32,
    consumers: u32,
    providers: u32,
    sufficients: u32,
    data: AccountData,
}

#[derive(Debug, Decode)]
struct AccountData {
    free: u128,
    reserved: u128,
    frozen: u128,
    flags: u128,
}

fn root_dir() -> Result<PathBuf> {
    let exe = std::env::current_exe().context("current_exe failed")?;
    let exe_dir = exe
        .parent()
        .ok_or_else(|| anyhow!("failed to get exe dir"))?
        .to_path_buf();

    Ok(exe_dir)
}

fn find_file(name: &str) -> Option<PathBuf> {
    let root = root_dir().ok();
    if let Some(root) = root {
        let p = root.join(name);
        if p.is_file() {
            return Some(p);
        }
    }

    let cwd = std::env::current_dir().ok()?;
    let p = cwd.join(name);
    if p.is_file() {
        return Some(p);
    }

    None
}

fn load_dotenv() {
    if let Some(path) = find_file(".env") {
        let _ = dotenvy::from_path(path);
    } else {
        let _ = dotenv();
    }
}

fn load_deployment() -> Result<DeploymentInfo> {
    let path = find_file("deployment.json")
        .ok_or_else(|| anyhow!("deployment.json not found in exe dir or cwd"))?;
    let raw = fs::read_to_string(&path)
        .with_context(|| format!("failed reading {}", path.display()))?;
    Ok(serde_json::from_str(&raw)?)
}

fn is_executor_enabled() -> bool {
    let Some(path) = find_file(EXECUTOR_ENABLED_FILENAME) else {
        return true;
    };

    match fs::read_to_string(path) {
        Ok(raw) => serde_json::from_str::<ExecutorEnabled>(&raw)
            .map(|v| v.enabled)
            .unwrap_or(true),
        Err(_) => true,
    }
}

fn pack_execute_params(stake_info_rao: u128, limit_price_rao: u128) -> U256 {
    let hi = U256::from(stake_info_rao) << 128;
    let lo = U256::from(limit_price_rao) & ((U256::from(1u8) << 128) - U256::from(1u8));
    hi | lo
}

async fn get_current_block(client: &OnlineClient<PolkadotConfig>) -> Result<u64> {
    let latest = client.blocks().at_latest().await?;
    Ok(latest.number().into())
}

async fn get_balance_rao(client: &OnlineClient<PolkadotConfig>, ss58: &str) -> Result<u128> {
    let account = AccountId32::from_str(ss58)
        .with_context(|| format!("invalid ss58 address: {ss58}"))?;

    let storage_addr = dynamic::storage(
        "System",
        "Account",
        vec![Value::from_bytes(account.as_ref())],
    );

    let storage = client.storage().at_latest().await?;
    let raw = storage
        .fetch_raw(&storage_addr)
        .await?
        .ok_or_else(|| anyhow!("System.Account not found for {ss58}"))?;

    let mut bytes = &raw[..];
    let account_info = AccountInfo::decode(&mut bytes)
        .with_context(|| format!("failed to decode AccountInfo for {ss58}"))?;

    Ok(account_info.data.free)
}

async fn get_delegate_balances_from_chain(
    client: &OnlineClient<PolkadotConfig>,
) -> Result<(u128, u128)> {
    let b1 = get_balance_rao(client, STAKE_INFO_DELEGATE).await?;
    let b2 = get_balance_rao(client, LIMIT_PRICE_DELEGATE).await?;
    Ok((b1, b2))
}

#[tokio::main]
async fn main() -> Result<()> {
    load_dotenv();

    let rpc_url = std::env::var("RPC_URL")
        .unwrap_or_else(|_| "https://test.finney.opentensor.ai/".to_string());
    let ws_url = std::env::var("BITTENSOR_WS_URL")
        .unwrap_or_else(|_| DEFAULT_BITTENSOR_WS_URL.to_string());

    let executor_key = std::env::var("EXECUTOR_PRIVATE_KEY").ok();
    let owner_key = std::env::var("PRIVATE_KEY").ok();
    let gas_limit: u64 = std::env::var("EXECUTOR_GAS_LIMIT")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(600_000);

    let (private_key, use_executor_wallet) = if let Some(k) = executor_key {
        (k, true)
    } else if let Some(k) = owner_key {
        (k, false)
    } else {
        bail!("Set EXECUTOR_PRIVATE_KEY (recommended) or PRIVATE_KEY");
    };

    let deployment = load_deployment()?;
    let contract_address: Address = deployment
        .contract_address
        .parse()
        .with_context(|| format!("invalid contract_address {}", deployment.contract_address))?;

    let signer = PrivateKeySigner::from_str(&private_key)
        .context("failed to parse private key")?;

    let provider = ProviderBuilder::new()
        .wallet(signer.clone())
        .connect_http(
            rpc_url
                .parse()
                .with_context(|| format!("invalid RPC_URL: {rpc_url}"))?,
        );

    let account = signer.address();

    let contract = StakeWrap::new(contract_address, provider.clone());

    if use_executor_wallet {
        let executor = contract.executor().call().await?;
        if executor == Address::ZERO {
            bail!("Contract has no executor set. Owner must call setExecutor(executorAddress) first.");
        }
        if executor != account {
            bail!("Account {account:?} is not contract executor {executor:?}");
        }
        println!("Using executor wallet (EXECUTOR_PRIVATE_KEY)");
    } else {
        let owner = contract.owner().call().await?;
        if owner != account {
            bail!("Account {account:?} is not contract owner {owner:?}");
        }
        println!("Using owner wallet (PRIVATE_KEY)");
    }

    println!("Contract: {contract_address:?}");
    println!(
        "Delegates: STAKE_INFO={}, LIMIT_PRICE={}",
        STAKE_INFO_DELEGATE, LIMIT_PRICE_DELEGATE
    );

    let substrate =
        OnlineClient::<PolkadotConfig>::from_url(ws_url.clone())
            .await
            .with_context(|| format!("failed to connect to Bittensor WS {ws_url}"))?;

    let mut last_block = get_current_block(&substrate).await?;
    let (mut stake_info_balance, mut limit_price_balance) =
        get_delegate_balances_from_chain(&substrate).await?;

    println!(
        "Balances from chain (rao): stake_info={}, limit_price={}",
        stake_info_balance, limit_price_balance
    );
    println!("Polling for new best blocks (Bittensor chain)...");

    let chain_id = provider.get_chain_id().await?;
    let mut nonce = provider.get_transaction_count(account).await?;
    let mut signed_raw: Option<Vec<u8>> = None;
    let mut next_exec_block: Option<u64> = None;
    let mut enabled_flag = is_executor_enabled();

    let mut blocks = substrate.blocks().subscribe_best().await?;

    loop {
        tokio::select! {
            maybe_block = blocks.next() => {
                let Some(block_res) = maybe_block else {
                    eprintln!("best-block subscription ended, reconnecting in 2s...");
                    sleep(Duration::from_secs(2)).await;
                    let substrate = OnlineClient::<PolkadotConfig>::from_url(ws_url.clone()).await?;
                    blocks = substrate.blocks().subscribe_best().await?;
                    continue;
                };

                let block = match block_res {
                    Ok(b) => b,
                    Err(e) => {
                        eprintln!("block subscription error: {e}");
                        sleep(Duration::from_secs(2)).await;
                        continue;
                    }
                };

                let current: u64 = block.number().into();
                if current <= last_block {
                    continue;
                }

                println!("new block: {}", current);

                if let Some(raw) = signed_raw.take() {
                    if enabled_flag {
                        let tx_hash = keccak256(&raw);
                        match provider.send_raw_transaction(&raw).await {
                            Ok(_) => {
                                println!(
                                    "Block {} execute(execBlock={}) tx 0x{}",
                                    current,
                                    next_exec_block.unwrap_or_default(),
                                    hex::encode(tx_hash)
                                );
                                nonce += 1;
                            }
                            Err(e) => {
                                eprintln!("Block {} execute failed to send: {}", current, e);
                            }
                        }
                    }

                    enabled_flag = is_executor_enabled();
                }

                match get_delegate_balances_from_chain(&substrate).await {
                    Ok((b1, b2)) => {
                        stake_info_balance = b1;
                        limit_price_balance = b2;
                        println!(
                            "Balances from chain (rao): stake_info={}, limit_price={}",
                            stake_info_balance, limit_price_balance
                        );
                    }
                    Err(e) => {
                        eprintln!("failed fetching balances at block {}: {}", current, e);
                        last_block = current;
                        continue;
                    }
                }

                let exec_block = current + 2;
                let packed = pack_execute_params(stake_info_balance, limit_price_balance);
                next_exec_block = Some(exec_block);

                let gas_price = provider.get_gas_price().await?;

                let call = contract
                    .execute(exec_block, packed)
                    .from(account)
                    .nonce(nonce)
                    .gas(gas_limit)
                    .gas_price(gas_price)
                    .chain_id(chain_id);

                match call.build_raw_transaction(signer.clone()).await {
                    Ok(raw) => {
                        signed_raw = Some(raw);
                    }
                    Err(e) => {
                        eprintln!("Block {} execute build failed: {}", current, e);
                        signed_raw = None;
                    }
                }

                last_block = current;
            }

            _ = sleep(Duration::from_secs(2)) => {
                // lightweight periodic tick, mainly to keep behavior similar to Python loop
            }
        }
    }
}