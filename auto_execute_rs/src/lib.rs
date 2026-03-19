//! Library for Bittensor block fetch and execute calldata (used by main and get_block binary).

use anyhow::{Context, Result};
use futures_util::{SinkExt, StreamExt};
use tokio_tungstenite::{connect_async, tungstenite::Message};

/// Default Bittensor Finney WebSocket URL (override with BITTENSOR_WS_URL).
pub const DEFAULT_BITTENSOR_WS_URL: &str = "wss://entrypoint-finney.opentensor.ai:443";

/// Get current Bittensor/Substrate block number via WebSocket JSON-RPC chain_getHeader.
/// Same as Python auto_execute.get_current_block: send chain_getHeader, parse result.number.
/// Substrate returns number as hex string (e.g. "0x1a2b"); we parse it.
pub async fn get_current_block_bittensor(ws_url: &str) -> Result<u64> {
    let (ws_stream, _) = connect_async(ws_url)
        .await
        .context("WebSocket connect to Bittensor")?;
    let (mut write, mut read) = ws_stream.split();

    let request = serde_json::json!({
        "jsonrpc": "2.0",
        "method": "chain_getHeader",
        "params": [null],
        "id": 0u32
    });
    write
        .send(Message::Text(request.to_string()))
        .await
        .context("ws send")?;

    let msg = read.next().await.context("ws recv")??;
    let text = msg.to_text().context("ws response not text")?;
    let v: serde_json::Value = serde_json::from_str(text).context("parse chain_getHeader response")?;
    let number = v
        .get("result")
        .and_then(|r| r.get("number"))
        .and_then(|n| n.as_str())
        .context("result.number not found")?;
    // Substrate returns hex "0x1234"; Python int(s, 0) accepts that
    let block = if number.starts_with("0x") || number.starts_with("0X") {
        u64::from_str_radix(number.trim_start_matches("0x").trim_start_matches("0X"), 16)
    } else {
        number.parse::<u64>()
    }
    .context("parse block number")?;
    Ok(block)
}
