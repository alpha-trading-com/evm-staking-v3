/**
 * Deploy StakeWrap as upgradeable (implementation + TransparentUpgradeableProxy).
 * The proxy address is the one to use in deployment.json and interact.py.
 * Requires: PRIVATE_KEY, optional RPC_URL in .env
 */
const hre = require("hardhat");
const fs = require("fs");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  if (!deployer) throw new Error("No signer. Set PRIVATE_KEY and use network finney.");
  console.log("Deploying from:", deployer.address);

  // 1. Deploy implementation
  const StakeWrap = await hre.ethers.getContractFactory("StakeWrap");
  const impl = await StakeWrap.deploy();
  await impl.waitForDeployment();
  const implAddress = await impl.getAddress();
  console.log("StakeWrap implementation:", implAddress);

  // 2. Encode initialize() for the proxy's _data
  const initData = StakeWrap.interface.encodeFunctionData("initialize");

  // 3. Deploy proxy (admin = deployer so they can upgrade later)
  const Proxy = await hre.ethers.getContractFactory(
    "@openzeppelin/contracts/proxy/transparent/TransparentUpgradeableProxy.sol:TransparentUpgradeableProxy"
  );
  const proxy = await Proxy.deploy(implAddress, deployer.address, initData);
  await proxy.waitForDeployment();
  const proxyAddress = await proxy.getAddress();
  console.log("Proxy (use this address):", proxyAddress);

  const deployment = {
    contract_address: proxyAddress,
    implementation_address: implAddress,
    deployer: deployer.address,
    chain_id: (await hre.ethers.provider.getNetwork()).chainId.toString(),
    upgradeable: true,
    proxy_admin: deployer.address,
    allowed_coldkey_ss58: "5FsDUVe2zLxTJTR1HzYp35BcNpbeFMLC76uRhwSTGj5YF36C",
    allowed_coldkey_bytes32: "0xa82db0e41db30fc3d206773f461c87c484b3ac0c25bf703567b4f1aa1ed5b350",
  };

  fs.writeFileSync("deployment.json", JSON.stringify(deployment, null, 2));
  console.log("Written deployment.json (contract_address = proxy)");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
