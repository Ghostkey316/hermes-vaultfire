# Hermes × Vaultfire

> Every Hermes agent deserves a trust score. This is how they get one.

A [Hermes Agent](https://github.com/NousResearch/hermes-agent) skill that integrates the [Vaultfire Protocol](https://github.com/Ghostkey316/ghostkey-316-vaultfire-init) — giving every Hermes agent on-chain identity, trust verification, accountability bonds, x402 payments, and XMTP encrypted messaging on Base mainnet.

---

## Why This Exists

AI agents are everywhere. But there's no standard way to know if an agent is trustworthy, accountable, or even who it claims to be.

**KYA (Know Your Agent)** solves this. It's the HTTPS of trust for AI agents — a verifiable, on-chain trust layer that any agent framework can plug into.

This skill brings KYA to Hermes by querying 17 real deployed Vaultfire contracts on Base mainnet. No API keys. No external dependencies. Just Python standard library and live blockchain data.

---

## What You Get

| Capability | Command | Description |
|------------|---------|-------------|
| Trust Verification | `trust <address>` | Full on-chain trust panel — grade (A–F), Street Cred, bonds, identity, x402, XMTP |
| Street Cred | `streetcred <address>` | Composite reputation score (0–95) with tier |
| Identity Check | `identity <address>` | ERC-8004 registration, VNS name, reputation data |
| Bond Status | `bonds <address>` | Accountability + partnership bonds, total ETH staked |
| x402 Payments | `x402 <address>` | Trust-gated USDC payment readiness (EIP-712) |
| XMTP Messaging | `xmtp <address>` | Encrypted messaging reachability on XMTP network |
| Contract List | `contracts` | All 17 live Base contracts with BaseScan links |
| Hub Stats | `hub` | Protocol stats — agent count, active bonds, ETH bonded |

---

## Quick Start

### Install as a Hermes Skill

```bash
# Copy to your Hermes skills directory
cp -r . ~/.hermes/skills/vaultfire/

# Or install via Hermes CLI (when published to Skills Hub)
hermes skills install vaultfire
```

### Verify It Works

```bash
# Check protocol stats
python3 ~/.hermes/skills/vaultfire/scripts/vaultfire_client.py hub

# Full trust verification for the Vaultfire deployer
python3 ~/.hermes/skills/vaultfire/scripts/vaultfire_client.py \
  trust 0xA054f831B562e729F8D268291EBde1B2EDcFb84F
```

### Use in Hermes

Once installed, just talk to your Hermes agent naturally:

- *"Check the trust level of 0x1234..."*
- *"What's the Street Cred score for this agent?"*
- *"Is this address registered on Vaultfire?"*
- *"Show me all Vaultfire contracts on Base"*
- *"Can this agent accept x402 payments?"*

---

## How Street Cred Scoring Works

Composite on-chain reputation score (0–95 max) computed from live Base mainnet data.

| Component | Max Points | Description |
|-----------|-----------|-------------|
| ERC-8004 Identity Registered | 30 pts | Registered = 30, unregistered = 0 |
| Partnership Bond Exists | 25 pts | Has at least one bond |
| Partnership Bond Active | 15 pts | Bond is currently active |
| Bond Tier Bonus | 20 pts | Bronze +5, Silver +10, Gold +15, Platinum +20 |
| Multiple Bonds | 5 pts | More than one active partnership bond |

**Tiers:** Bronze (20+), Silver (40+), Gold (60+), Platinum (80+)

---

## Contracts Queried (Base Mainnet — Chain ID 8453)

| Contract | Address | Status |
|----------|---------|--------|
| ERC8004IdentityRegistry | [`0x35978DB675576598F0781dA2133E94cdCf4858bC`](https://basescan.org/address/0x35978DB675576598F0781dA2133E94cdCf4858bC) | LIVE |
| AIPartnershipBondsV2 | [`0xC574CF2a09B0B470933f0c6a3ef422e3fb25b4b4`](https://basescan.org/address/0xC574CF2a09B0B470933f0c6a3ef422e3fb25b4b4) | LIVE |
| AIAccountabilityBondsV2 | [`0xf92baef9523BC264144F80F9c31D5c5C017c6Da8`](https://basescan.org/address/0xf92baef9523BC264144F80F9c31D5c5C017c6Da8) | Deployed |
| ERC8004ReputationRegistry | [`0xdB54B8925664816187646174bdBb6Ac658A55a5F`](https://basescan.org/address/0xdB54B8925664816187646174bdBb6Ac658A55a5F) | LIVE |
| ERC8004ValidationRegistry | [`0x54e00081978eE2C8d9Ada8e9975B0Bb543D06A55`](https://basescan.org/address/0x54e00081978eE2C8d9Ada8e9975B0Bb543D06A55) | Deployed |
| VaultfireERC8004Adapter | [`0xef3A944f4d7bb376699C83A29d7Cb42C90D9B6F0`](https://basescan.org/address/0xef3A944f4d7bb376699C83A29d7Cb42C90D9B6F0) | Deployed |
| VaultfireNameService | [`0x1437c4081233A4f0B6907dDf5374Ed610cBD6B25`](https://basescan.org/address/0x1437c4081233A4f0B6907dDf5374Ed610cBD6B25) | LIVE |
| FlourishingMetricsOracle | [`0x83dd216449B3F0574E39043ECFE275946fa492e9`](https://basescan.org/address/0x83dd216449B3F0574E39043ECFE275946fa492e9) | Deployed |
| MultisigGovernance | [`0x8B8Ba34F8AAB800F0Ba8391fb1388c6EFb911F92`](https://basescan.org/address/0x8B8Ba34F8AAB800F0Ba8391fb1388c6EFb911F92) | Deployed |
| VaultfireTeleporterBridge | [`0x94F54c849692Cc64C35468D0A87D2Ab9D7Cb6Fb2`](https://basescan.org/address/0x94F54c849692Cc64C35468D0A87D2Ab9D7Cb6Fb2) | Deployed |
| DilithiumAttestor | [`0xBBC0EFdEE23854e7cb7C4c0f56fF7670BB0530A4`](https://basescan.org/address/0xBBC0EFdEE23854e7cb7C4c0f56fF7670BB0530A4) | Deployed |
| ProductionBeliefAttestationVerifier | [`0xa5CEC47B48999EB398707838E3A18dd20A1ae272`](https://basescan.org/address/0xa5CEC47B48999EB398707838E3A18dd20A1ae272) | Deployed |
| BeliefAttestationVerifier | [`0xD9bF6D92a1D9ee44a48c38481c046a819CBdf2ba`](https://basescan.org/address/0xD9bF6D92a1D9ee44a48c38481c046a819CBdf2ba) | Deployed |
| MissionEnforcement | [`0x8568F4020FCD55915dB3695558dD6D2532599e56`](https://basescan.org/address/0x8568F4020FCD55915dB3695558dD6D2532599e56) | Deployed |
| AntiSurveillance | [`0x722E37A7D6f27896C688336AaaFb0dDA80D25E57`](https://basescan.org/address/0x722E37A7D6f27896C688336AaaFb0dDA80D25E57) | Deployed |
| PrivacyGuarantees | [`0xE2f75A4B14ffFc1f9C2b1ca22Fdd6877E5BD5045`](https://basescan.org/address/0xE2f75A4B14ffFc1f9C2b1ca22Fdd6877E5BD5045) | Deployed |

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                  HERMES AI AGENT                     │
│            (NousResearch/hermes-agent)               │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │          Vaultfire Trust Skill                │   │
│  │         vaultfire_client.py                   │   │
│  ├──────────────────────────────────────────────┤   │
│  │                                              │   │
│  │  trust      — Full on-chain verification     │   │
│  │  streetcred — Reputation score (0–95)        │   │
│  │  identity   — ERC-8004 registration check    │   │
│  │  bonds      — Accountability + partnership   │   │
│  │  x402       — USDC payment readiness         │   │
│  │  xmtp       — Encrypted messaging check      │   │
│  │  contracts  — All 17 Base addresses          │   │
│  │  hub        — Live protocol stats            │   │
│  │                                              │   │
│  └──────────────┬───────────────────────────────┘   │
│                 │                                     │
│         ┌───────┴───────┐                            │
│         │ Base RPC      │                            │
│         │ (eth_call)    │                            │
│         └───────┬───────┘                            │
│                 │                                     │
└─────────────────┼────────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────────────────┐
│            BASE MAINNET (Chain ID: 8453)             │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ERC8004IdentityRegistry    ←─ Agent identity        │
│  ERC8004ReputationRegistry  ←─ On-chain ratings      │
│  VaultfireNameService       ←─ .vns names            │
│  AIPartnershipBondsV2       ←─ Mutual stakes         │
│  AIAccountabilityBondsV2    ←─ Risk bonds            │
│  MissionEnforcement         ←─ Protocol commitment   │
│  AntiSurveillance           ←─ Privacy enforcement   │
│  PrivacyGuarantees          ←─ Data protection       │
│  + 8 more contracts                                  │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `VAULTFIRE_RPC_URL` | No | Custom Base RPC endpoint (default: https://mainnet.base.org) |
| `VAULTFIRE_AGENT_KEY` | No | Agent private key for write operations (bond creation, x402 signing) |
| `VAULTFIRE_AGENT_ADDRESS` | No | Agent address for read-only bond status checks |

---

## Links

- **Vaultfire Protocol:** [github.com/Ghostkey316/ghostkey-316-vaultfire-init](https://github.com/Ghostkey316/ghostkey-316-vaultfire-init)
- **Vaultfire on Base:** [github.com/Ghostkey316/vaultfire-base](https://github.com/Ghostkey316/vaultfire-base)
- **Hermes Agent:** [github.com/NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
- **Hub:** [theloopbreaker.com](https://theloopbreaker.com)

---

## Mission

> Morals over metrics. Privacy over surveillance. Freedom over control.

---

## License

MIT
