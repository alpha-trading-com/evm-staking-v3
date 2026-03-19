//! Test binary: fetch current Bittensor block via WebSocket chain_getHeader (same as Python).
//! Run: cargo run --bin get_block   or   BITTENSOR_WS_URL=wss://... cargo run --bin get_block

use anyhow::Result;
use auto_execute_rs::get_current_block_bittensor;
use auto_execute_rs::DEFAULT_BITTENSOR_WS_URL;

#[tokio::main]
async fn main() -> Result<()> {
    dotenvy::dotenv().ok();
    let ws_url = std::env::var("BITTENSOR_WS_URL").unwrap_or_else(|_| DEFAULT_BITTENSOR_WS_URL.to_string());
    println!("Connecting to {} ...", ws_url);
    let block = get_current_block_bittensor(&ws_url).await?;
    println!("Current block: {}", block);
    Ok(())
}
