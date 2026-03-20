//! Library for Bittensor block and balance fetch via direct WebSocket JSON-RPC (like Python auto_execute).

use anyhow::{Context, Result};
use blake2::{Blake2b256, Digest};
use futures_util::{SinkExt, StreamExt};
use parity_scale_codec::Decode;
use sp_core::crypto::Ss58Codec;
use sp_core::hashing::twox_128;
use sp_core::sr25519;
use tokio_tungstenite::{connect_async, tungstenite::Message};

/// Default Bittensor Finney WebSocket URL (override with BITTENSOR_WS_URL).
pub const DEFAULT_BITTENSOR_WS_URL: &str = "wss://entrypoint-finney.opentensor.ai:443";

/// Send one JSON-RPC request over a fresh WebSocket, return the "result" field as parsed JSON.
async fn ws_rpc_call(ws_url: &str, method: &str, params: serde_json::Value) -> Result<serde_json::Value> {
    let (ws_stream, _) = connect_async(ws_url)
        .await
        .context("WebSocket connect to Bittensor")?;
    let (mut write, mut read) = ws_stream.split();
    let request = serde_json::json!({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 0u32
    });
    write
        .send(Message::Text(request.to_string()))
        .await
        .context("ws send")?;
    let msg = read.next().await.context("ws recv")??;
    let text = msg.to_text().context("ws response not text")?;
    let v: serde_json::Value = serde_json::from_str(text).context("parse response")?;
    v.get("result")
        .cloned()
        .context("result not found")
}

/// Get current Bittensor/Substrate block number via WebSocket JSON-RPC chain_getHeader.
/// Same as Python auto_execute.get_current_block.
pub async fn get_current_block_bittensor(ws_url: &str) -> Result<u64> {
    let result = ws_rpc_call(ws_url, "chain_getHeader", serde_json::json!([null])).await?;
    let number = result
        .get("number")
        .and_then(|n| n.as_str())
        .context("result.number not found")?;
    let block = if number.starts_with("0x") || number.starts_with("0X") {
        u64::from_str_radix(number.trim_start_matches("0x").trim_start_matches("0X"), 16)
    } else {
        number.parse::<u64>()
    }
    .context("parse block number")?;
    Ok(block)
}

/// Build System::Account storage key for a 32-byte account id (Blake2_128Concat map).
fn system_account_storage_key(account_id: &[u8; 32]) -> Vec<u8> {
    let mut key = Vec::with_capacity(32 + 48);
    key.extend_from_slice(&twox_128(b"System"));
    key.extend_from_slice(&twox_128(b"Account"));
    let hash = Blake2b256::digest(account_id);
    key.extend_from_slice(&hash[..16]); // blake2_128
    key.extend_from_slice(account_id);
    key
}

/// Decode Substrate AccountInfo storage value and return the "free" balance (first u128 in data).
fn decode_account_info_free(data: &[u8]) -> Result<u128> {
    let mut cursor = data;
    let _nonce = parity_scale_codec::Compact::<u32>::decode(&mut cursor).context("decode nonce")?;
    let _consumers = u32::decode(&mut cursor).context("decode consumers")?;
    let _providers = u32::decode(&mut cursor).context("decode providers")?;
    let _sufficients = u32::decode(&mut cursor).context("decode sufficients")?;
    let free = u128::decode(&mut cursor).context("decode free")?;
    Ok(free)
}

/// Get free balance (rao) for one SS58 address via state_getStorage (System::Account).
/// Same idea as Python subtensor.get_balance(ss58).rao.
pub async fn get_balance_bittensor(ws_url: &str, ss58: &str) -> Result<u128> {
    let pk = sr25519::Public::from_ss58check(ss58).context("invalid SS58 address")?;
    let key = system_account_storage_key(&pk.0);
    let key_hex = format!("0x{}", hex::encode(&key));
    let result = ws_rpc_call(ws_url, "state_getStorage", serde_json::json!([key_hex]))
        .await?;
    let Some(hex_val) = result.as_str() else {
        return Ok(0);
    };
    let storage_bytes = hex::decode(hex_val.trim_start_matches("0x"))
        .context("decode storage hex")?;
    decode_account_info_free(&storage_bytes)
}

/// Query Bittensor chain for free balance (rao) of both delegates via direct WS RPC.
/// Returns (stake_info_balance_rao, limit_price_balance_rao). Same as Python get_delegate_balances_from_chain.
pub async fn get_delegate_balances_bittensor(
    ws_url: &str,
    stake_info_ss58: &str,
    limit_price_ss58: &str,
) -> Result<(u128, u128)> {
    let b1 = get_balance_bittensor(ws_url, stake_info_ss58).await?;
    let b2 = get_balance_bittensor(ws_url, limit_price_ss58).await?;
    Ok((b1, b2))
}
