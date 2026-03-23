#!/usr/bin/env node
/**
 * Write abi/StakeWrap.abi.json from the Hardhat StakeWrap artifact (run after compile).
 */
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const artifactPath = path.join(
  root,
  "artifacts",
  "contracts",
  "StakeWrap.sol",
  "StakeWrap.json"
);
const outDir = path.join(root, "abi");
const outPath = path.join(outDir, "StakeWrap.abi.json");

const art = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
if (!Array.isArray(art.abi)) {
  console.error("StakeWrap.json missing abi array");
  process.exit(1);
}
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(outPath, JSON.stringify(art.abi, null, 2) + "\n");
console.log("Wrote", path.relative(root, outPath));
