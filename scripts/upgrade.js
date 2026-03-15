/**
 * Upgrade the StakeWrap proxy to a new implementation.
 * Reads proxy address from deployment.json; deploys new StakeWrap and points proxy at it.
 * Requires: PRIVATE_KEY (must be the proxy admin), optional RPC_URL.
 */
const hre = require("hardhat");
const fs = require("fs");

const PROXY_ABI_UPGRADE = [
  "function upgradeTo(address newImplementation) external",
  "function implementation() external view returns (address)",
  "function admin() external view returns (address)",
];

async function main() {
  let deployment;
  try {
    deployment = JSON.parse(fs.readFileSync("deployment.json", "utf8"));
  } catch (e) {
    throw new Error("deployment.json not found or invalid. Deploy with deploy-upgradeable.js first.");
  }
  const proxyAddress = deployment.contract_address;
  if (!deployment.upgradeable) {
    throw new Error("deployment.json does not have upgradeable: true. Use proxy deployment.");
  }

  const [deployer] = await hre.ethers.getSigners();
  if (!deployer) throw new Error("No signer. Set PRIVATE_KEY and use network finney.");
  console.log("Upgrading from admin:", deployer.address);
  console.log("Proxy:", proxyAddress);

  const proxy = await hre.ethers.getContractAt(PROXY_ABI_UPGRADE, proxyAddress);
  const currentImpl = await proxy.implementation();
  console.log("Current implementation:", currentImpl);

  // Deploy new implementation
  const StakeWrap = await hre.ethers.getContractFactory("StakeWrap");
  const newImpl = await StakeWrap.deploy();
  await newImpl.waitForDeployment();
  const newImplAddress = await newImpl.getAddress();
  console.log("New implementation:", newImplAddress);

  const tx = await proxy.upgradeTo(newImplAddress);
  await tx.wait();
  console.log("Upgrade tx:", tx.hash);

  deployment.implementation_address = newImplAddress;
  deployment.last_upgrade_tx = tx.hash;
  fs.writeFileSync("deployment.json", JSON.stringify(deployment, null, 2));
  console.log("Updated deployment.json");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
