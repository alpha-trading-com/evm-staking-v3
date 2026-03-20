#!/bin/bash
# Install Rust and Cargo so you can build auto-execute-rs.
# Run once: bash auto_execute_rs/install_rust.sh
#
# On Linux, also install pkg-config and OpenSSL dev (required by openssl-sys):
#   sudo apt install -y pkg-config libssl-dev   # Debian/Ubuntu
#   sudo yum install -y pkg-config openssl-devel   # Fedora/RHEL

set -e
if command -v cargo &>/dev/null; then
  echo "cargo already installed: $(cargo --version)"
else
  echo "Installing Rust via rustup..."
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
fi
export PATH="$HOME/.cargo/bin:$PATH"

echo ""
echo "If build fails with 'pkg-config' or 'OpenSSL' errors, install system deps:"
echo "  sudo apt install -y pkg-config libssl-dev   # Debian/Ubuntu"
echo ""
echo "Then build:"
echo "  cd auto_execute_rs && cargo build --release"
echo "  ./target/release/auto-execute-rs"
