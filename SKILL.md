---
name: vaultfire
description: "Vaultfire Protocol KYA (Know Your Agent) trust layer for Hermes agents. Verify agent trust on-chain, check Street Cred scores, manage bonds, x402 USDC payments, XMTP encrypted messaging, and query all 17 live Base mainnet contracts. No API key required for read operations."
version: 0.1.0
author: Ghostkey316
license: MIT
metadata:
  hermes:
    tags: [Vaultfire, Trust, KYA, Base, Blockchain, Identity, Bonds, x402, XMTP, ERC-8004, Web3, AI-Safety]
    related_skills: [base]
---

# Vaultfire Protocol — KYA Trust Layer for Hermes

On-chain KYA (Know Your Agent) trust verification, identity, bonds, payments,
and messaging for Hermes AI agents. Queries real deployed Vaultfire Protocol
contracts on Base mainnet (chain ID 8453).

**17 live contracts. Real on-chain data.**

No API key needed for read operations. Uses only Python standard library.

---

## When to Use

- User asks to verify an AI agent's trust level or reputation
- User wants to check an agent's Street Cred score or tier
- User asks about ERC-8004 identity registration status
- User wants to check bond status (accountability or partnership bonds)
- User asks about x402 payment capability or USDC balance
- User wants to check XMTP messaging reachability
- User asks for Vaultfire contract addresses on Base
- User wants Vaultfire protocol stats (agent count, bonds, ETH bonded)
- User mentions "KYA", "Know Your Agent", "Vaultfire", "trust verification"
- User wants to verify if an agent is safe to interact with
- User asks about AI accountability or trust infrastructure

---

## Prerequisites

The helper script uses only Python standard library (urllib, json, argparse).
No external packages required.

RPC endpoint (default): https://mainnet.base.org
Override: export VAULTFIRE_RPC_URL=https://your-private-rpc.com

Hub API: https://theloopbreaker.com (no key required)

---

## Quick Reference

Helper script path: ~/.hermes/skills/vaultfire/scripts/vaultfire_client.py

```
python3 vaultfire_client.py trust      <address>              # Full trust verification
python3 vaultfire_client.py streetcred <address>              # Street Cred score (0-95)
python3 vaultfire_client.py identity   <address>              # ERC-8004 identity check
python3 vaultfire_client.py bonds      <address>              # Bond status
python3 vaultfire_client.py x402       <address>              # x402 payment readiness
python3 vaultfire_client.py xmtp       <address>              # XMTP messaging check
python3 vaultfire_client.py contracts                         # List all 17 Base contracts
python3 vaultfire_client.py hub                               # Protocol stats from hub API
```

Add `--json` to any command for machine-readable JSON output.

---

## Procedure

### 0. Setup Check

```bash
python3 --version

# Optional: set a private RPC for better rate limits
export VAULTFIRE_RPC_URL="https://mainnet.base.org"

# Confirm connectivity
python3 ~/.hermes/skills/vaultfire/scripts/vaultfire_client.py hub
```

### 1. Full Trust Verification

Comprehensive on-chain trust check. Queries 8 contract calls in parallel:
ERC-8004 identity, reputation, VNS name, partnership bonds, accountability
bonds, and protocol commitment contracts.

Computes a Trust Grade (A–F) and Street Cred score (0–95).

```bash
python3 ~/.hermes/skills/vaultfire/scripts/vaultfire_client.py \
  trust 0xA054f831B562e729F8D268291EBde1B2EDcFb84F
```

Output includes: trust grade, street cred score and tier, bond status,
identity registration, VNS name, x402 payment capability, XMTP
reachability, and protocol commitment verification.

### 2. Street Cred Score

Quick reputation check — just the score and tier.

```bash
python3 ~/.hermes/skills/vaultfire/scripts/vaultfire_client.py \
  streetcred 0xA054f831B562e729F8D268291EBde1B2EDcFb84F
```

Scoring breakdown:
- ERC-8004 Identity Registered: 30 pts
- Partnership Bond Exists: 25 pts
- Partnership Bond Active: 15 pts
- Bond Tier Bonus: Bronze +5, Silver +10, Gold +15, Platinum +20
- Multiple Bonds: 5 pts (more than one active bond)

Tiers: Bronze (20+), Silver (40+), Gold (60+), Platinum (80+)

### 3. ERC-8004 Identity Check

Check if an address is registered in the Vaultfire ERC-8004 Identity
Registry. Shows registration status, VNS name, and reputation data.

```bash
python3 ~/.hermes/skills/vaultfire/scripts/vaultfire_client.py \
  identity 0xA054f831B562e729F8D268291EBde1B2EDcFb84F
```

### 4. Bond Status

Check accountability bonds and partnership bonds for an address.

```bash
python3 ~/.hermes/skills/vaultfire/scripts/vaultfire_client.py \
  bonds 0xA054f831B562e729F8D268291EBde1B2EDcFb84F
```

Shows: accountability bond count, partnership bond count, total active
bond value in ETH.

### 5. x402 Payment Check

Verify x402 payment readiness — checks address validity and USDC
balance on Base.

```bash
python3 ~/.hermes/skills/vaultfire/scripts/vaultfire_client.py \
  x402 0xA054f831B562e729F8D268291EBde1B2EDcFb84F
```

x402 is Vaultfire's trust-gated payment standard using EIP-712 signed
USDC transfers on Base.

### 6. XMTP Messaging Check

Check if an address is reachable on the XMTP encrypted messaging network.

```bash
python3 ~/.hermes/skills/vaultfire/scripts/vaultfire_client.py \
  xmtp 0xA054f831B562e729F8D268291EBde1B2EDcFb84F
```

### 7. Contract Addresses

List all 17 Vaultfire contracts deployed on Base mainnet with BaseScan links.

```bash
python3 ~/.hermes/skills/vaultfire/scripts/vaultfire_client.py contracts
```

### 8. Hub Stats

Query the Vaultfire hub for live protocol statistics.

```bash
python3 ~/.hermes/skills/vaultfire/scripts/vaultfire_client.py hub
```

Shows: registered agent count, active partnership bonds, total ETH bonded.

---

## Pitfalls

- **Public RPC rate limits** — Base's public RPC limits requests.
  For production use, set VAULTFIRE_RPC_URL to a private endpoint.
- **Read-only by default** — write operations (bond creation, x402 signing)
  require VAULTFIRE_AGENT_KEY to be set with a valid private key.
- **Street Cred max is 95** — not 100. This is intentional per protocol.
- **Accountability Bonds are LIVE** — yield pools funded and operational on all 4 chains (Base 0.005 ETH, Avalanche 0.005 AVAX, Arbitrum 0.005 ETH, Polygon 10 MATIC).
- **XMTP reachability** — checks the production XMTP network. May return
  false if the network is temporarily unavailable.
- **Retry on 429** — RPC calls retry up to 2 times with exponential
  backoff on rate-limit errors.

---

## Verification

```bash
# Should display protocol stats (agent count, bonds, ETH bonded)
python3 ~/.hermes/skills/vaultfire/scripts/vaultfire_client.py hub

# Should display trust verification for the Vaultfire deployer
python3 ~/.hermes/skills/vaultfire/scripts/vaultfire_client.py \
  trust 0xA054f831B562e729F8D268291EBde1B2EDcFb84F
```
