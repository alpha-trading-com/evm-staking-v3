//! Fetch Bittensor runtime metadata and generate subxt API (same approach as agcli).
//! See: https://github.com/unconst/agcli/tree/main/src

use std::env;
use std::fs::File;
use std::io::Write;
use std::path::Path;
use std::process::Stdio;
use std::process::Command;

use parity_scale_codec::Decode;
use subxt_codegen::CodegenBuilder;
use subxt_metadata::Metadata;
use subxt_utils_fetchmetadata::{self as fetch_metadata, MetadataVersion};

#[tokio::main]
async fn main() {
    let endpoint = env::var_os("METADATA_CHAIN_ENDPOINT")
        .map(|s| s.into_string().unwrap())
        .unwrap_or_else(|| "wss://entrypoint-finney.opentensor.ai:443".into());

    let out_dir = env::var_os("OUT_DIR").unwrap();
    let metadata_path = Path::new(&out_dir).join("metadata.rs");

    if metadata_path.exists() && env::var("SKIP_METADATA_FETCH").is_ok() {
        eprintln!("auto-execute-rs: reusing cached metadata (SKIP_METADATA_FETCH set)");
        return;
    }

    eprintln!("auto-execute-rs: fetching chain metadata from {endpoint}...");

    let url = endpoint.as_str().try_into().unwrap();
    let fetch_result = match fetch_metadata::from_url(url, MetadataVersion::Version(15)).await {
        Ok(bytes) => Ok(bytes),
        Err(e) => {
            eprintln!("auto-execute-rs: V15 failed ({e}), trying V14...");
            let url = endpoint.as_str().try_into().unwrap();
            fetch_metadata::from_url(url, MetadataVersion::Version(14)).await
        }
    };

    let metadata_bytes = match fetch_result {
        Ok(bytes) => bytes,
        Err(e) => {
            if metadata_path.exists() {
                eprintln!(
                    "auto-execute-rs: metadata fetch failed ({e}), reusing cached metadata at {}",
                    metadata_path.display()
                );
                return;
            }
            panic!("Failed to fetch metadata and no cache available: {e}");
        }
    };

    let mut slice: &[u8] = &metadata_bytes;
    let metadata = Metadata::decode(&mut slice).unwrap();

    let codegen = CodegenBuilder::new();
    let code = codegen.generate(metadata).unwrap();

    match Command::new("rustfmt")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
    {
        Ok(process) => {
            write!(process.stdin.as_ref().unwrap(), "{code}").unwrap();
            let output = process.wait_with_output().unwrap();
            std::fs::write(&metadata_path, &output.stdout).unwrap();
        }
        Err(_) => {
            let mut file = File::create(&metadata_path).unwrap();
            write!(file, "{code}").unwrap();
        }
    }

    eprintln!(
        "auto-execute-rs: metadata codegen complete → {}",
        metadata_path.display()
    );
}
