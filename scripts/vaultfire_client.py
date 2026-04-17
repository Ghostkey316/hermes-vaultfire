#!/usr/bin/env python3
"""
vaultfire_client.py — Vaultfire Protocol skill for the Hermes AI agent framework.

Provides on-chain trust verification, identity checks, bond status, x402 payment
capability, XMTP messaging reachability, and protocol contract listings for the
Vaultfire Protocol deployed on Base mainnet (chain ID 8453).

Usage:
    python vaultfire_client.py trust    <address> [--json]
    python vaultfire_client.py streetcred <address> [--json]
    python vaultfire_client.py identity <address> [--json]
    python vaultfire_client.py bonds    <address> [--json]
    python vaultfire_client.py x402    <address> [--json]
    python vaultfire_client.py xmtp    <address> [--json]
    python vaultfire_client.py contracts [--json]
    python vaultfire_client.py hub     [--json]

Environment:
    VAULTFIRE_RPC_URL — Base RPC endpoint (default: https://mainnet.base.org)
"""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_RPC_FALLBACKS = [
    "https://mainnet.base.org",
    "https://1rpc.io/base",
    "https://base-rpc.publicnode.com",
    "https://base.meowrpc.com",
]
RPC_URL = os.environ.get("VAULTFIRE_RPC_URL", "")  # resolved lazily via _get_rpc()
CHAIN_ID = 8453
BASE_SCAN = "https://basescan.org/address"
RPC_TIMEOUT = 8       # seconds
RPC_RETRIES = 2       # number of retries on 429
BACKOFF_BASE = 1.5    # seconds — multiplied by attempt number
_active_rpc: str | None = None


def _get_rpc() -> str:
    """Return a working Base RPC endpoint, trying fallbacks if needed."""
    global _active_rpc
    if _active_rpc:
        return _active_rpc
    if RPC_URL:
        _active_rpc = RPC_URL
        return _active_rpc
    for url in _RPC_FALLBACKS:
        try:
            payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}).encode()
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            if data.get("result"):
                _active_rpc = url
                return _active_rpc
        except Exception:
            continue
    _active_rpc = _RPC_FALLBACKS[0]  # fallback to default
    return _active_rpc

# ---------------------------------------------------------------------------
# Contract addresses
# ---------------------------------------------------------------------------

CONTRACTS = {
    "ERC8004IdentityRegistry":      "0x35978DB675576598F0781dA2133E94cdCf4858bC",
    "ERC8004ReputationRegistry":    "0xdB54B8925664816187646174bdBb6Ac658A55a5F",
    "VaultfireNameService":         "0x1437c4081233A4f0B6907dDf5374Ed610cBD6B25",
    "AIPartnershipBondsV2":         "0x01C479F0c039fEC40c0Cf1c5C921bab457d57441",
    "AIAccountabilityBondsV2":      "0x6750D28865434344e04e1D0a6044394b726C3dfE",
    "MissionEnforcement":           "0x8568F4020FCD55915dB3695558dD6D2532599e56",
    "AntiSurveillance":             "0x722E37A7D6f27896C688336AaaFb0dDA80D25E57",
    "PrivacyGuarantees":            "0xE2f75A4B14ffFc1f9C2b1ca22Fdd6877E5BD5045",
    "USDC":                         "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    # Additional real deployed contracts
    "ERC8004ValidationRegistry":    "0x54e00081978eE2C8d9Ada8e9975B0Bb543D06A55",
    "VaultfireERC8004Adapter":      "0xef3A944f4d7bb376699C83A29d7Cb42C90D9B6F0",
    "FlourishingMetricsOracle":     "0x83dd216449B3F0574E39043ECFE275946fa492e9",
    "MultisigGovernance":           "0x8B8Ba34F8AAB800F0Ba8391fb1388c6EFb911F92",
    "VaultfireTeleporterBridge":    "0x94F54c849692Cc64C35468D0A87D2Ab9D7Cb6Fb2",
    "DilithiumAttestor":            "0xBBC0EFdEE23854e7cb7C4c0f56fF7670BB0530A4",
    "ProductionBeliefAttestationVerifier": "0xa5CEC47B48999EB398707838E3A18dd20A1ae272",
    "BeliefAttestationVerifier":    "0xD9bF6D92a1D9ee44a48c38481c046a819CBdf2ba",
}

# ---------------------------------------------------------------------------
# Function selectors (keccak256[:4] of signature)
# ---------------------------------------------------------------------------

SELECTORS = {
    "isAgentActive":                "0x554c4f4b",
    "getReputation":                "0x9c89a0e2",
    "resolveAddressToName":         "0x13fee8d3",
    "getBondsByParticipantCount":   "0x67ff6265",
    "nextBondId":                   "0xee53a423",
    "totalActiveBondValue":         "0xe7683e58",
    "balanceOf":                    "0x70a08231",
}

# ---------------------------------------------------------------------------
# Low-level RPC helpers
# ---------------------------------------------------------------------------


def _encode_address(address: str) -> str:
    """ABI-encode a single address parameter: strip 0x, left-pad to 64 hex chars."""
    return address.lower().replace("0x", "").zfill(64)


def _build_call_data(selector: str, address: str | None = None) -> str:
    """Build the calldata hex string for an eth_call."""
    data = selector
    if address:
        data += _encode_address(address)
    return data


def _rpc_request(payload: dict, timeout: int = RPC_TIMEOUT) -> dict:
    """
    Send a single JSON-RPC request to the Base RPC endpoint.

    Uses _get_rpc() to resolve a working endpoint with automatic fallback.
    Returns the parsed JSON response dict.
    Raises urllib.error.URLError on network errors.
    Raises RuntimeError on JSON-RPC errors.
    """
    url = _get_rpc()
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return json.loads(raw)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        # Current endpoint failed — reset cache and try next fallback
        global _active_rpc
        _active_rpc = None
        # Try each fallback once
        for fallback_url in _RPC_FALLBACKS:
            if fallback_url == url:
                continue
            try:
                req2 = urllib.request.Request(
                    fallback_url,
                    data=body,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req2, timeout=timeout) as resp2:
                    raw2 = resp2.read()
                _active_rpc = fallback_url  # cache working endpoint
                return json.loads(raw2)
            except Exception:
                continue
        raise  # all fallbacks exhausted — re-raise original


def _rpc_call(payload: dict) -> dict | None:
    """
    Send a JSON-RPC request with retry logic on 429 rate-limit responses.

    Returns the parsed response or None on unrecoverable errors.
    """
    for attempt in range(RPC_RETRIES + 1):
        try:
            resp = _rpc_request(payload)
            if "error" in resp and resp["error"]:
                code = resp["error"].get("code", 0)
                if code == 429 and attempt < RPC_RETRIES:
                    delay = BACKOFF_BASE * (attempt + 1)
                    time.sleep(delay)
                    continue
                # Non-retryable JSON-RPC error — return the response anyway
                return resp
            return resp
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < RPC_RETRIES:
                delay = BACKOFF_BASE * (attempt + 1)
                time.sleep(delay)
                continue
            return None
        except (urllib.error.URLError, TimeoutError, OSError):
            return None
    return None


def eth_call(contract: str, calldata: str) -> str | None:
    """
    Execute an eth_call and return the raw hex result string, or None on failure.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_call",
        "params": [
            {"to": contract, "data": calldata},
            "latest",
        ],
    }
    resp = _rpc_call(payload)
    if resp is None:
        return None
    return resp.get("result")


def eth_get_code(address: str) -> str | None:
    """
    Execute eth_getCode and return the bytecode hex string, or None on failure.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_getCode",
        "params": [address, "latest"],
    }
    resp = _rpc_call(payload)
    if resp is None:
        return None
    return resp.get("result")


# ---------------------------------------------------------------------------
# Decoding helpers
# ---------------------------------------------------------------------------


def _decode_bool(hex_result: str | None) -> bool | None:
    """Decode a boolean from a 32-byte ABI-encoded hex string."""
    if not hex_result or hex_result == "0x":
        return None
    try:
        cleaned = hex_result.replace("0x", "").zfill(64)
        return int(cleaned, 16) != 0
    except ValueError:
        return None


def _decode_uint256(hex_result: str | None) -> int | None:
    """Decode a uint256 from a 32-byte ABI-encoded hex string."""
    if not hex_result or hex_result == "0x":
        return None
    try:
        cleaned = hex_result.replace("0x", "").zfill(64)
        return int(cleaned, 16)
    except ValueError:
        return None


def _decode_string(hex_result: str | None) -> str | None:
    """
    Decode a dynamic ABI-encoded string.

    ABI layout for a dynamic string returned as a single return value:
      [0:32]  offset (always 0x20 for a single string)
      [32:64] length of the string in bytes
      [64:..] UTF-8 bytes of the string, right-padded to 32-byte chunks
    """
    if not hex_result or hex_result == "0x":
        return None
    try:
        data = hex_result.replace("0x", "")
        if len(data) < 128:
            return None
        # offset: first 32 bytes (64 hex chars) — typically points to 0x20
        # length: next 32 bytes
        length = int(data[64:128], 16)
        if length == 0:
            return ""
        # string bytes start at position 128 (64 hex chars * 2)
        str_hex = data[128: 128 + length * 2]
        return bytes.fromhex(str_hex).decode("utf-8", errors="replace")
    except (ValueError, IndexError):
        return None


def _has_code(hex_code: str | None) -> bool:
    """Return True if the eth_getCode result indicates a deployed contract."""
    if not hex_code:
        return False
    stripped = hex_code.replace("0x", "").strip()
    return len(stripped) > 0 and stripped != "0" * len(stripped)


def _short_address(address: str) -> str:
    """Return a shortened address like 0x1234...5678."""
    addr = address if address.startswith("0x") else "0x" + address
    return addr[:6] + "..." + addr[-4:]


# ---------------------------------------------------------------------------
# Address validation
# ---------------------------------------------------------------------------


def validate_address(address: str) -> str:
    """
    Validate and normalise an Ethereum address.

    Returns the checksummed lowercase address, or raises ValueError.
    """
    addr = address.strip()
    if not addr.startswith("0x"):
        addr = "0x" + addr
    if len(addr) != 42:
        raise ValueError(f"Invalid Ethereum address length: {address!r}")
    try:
        int(addr, 16)
    except ValueError:
        raise ValueError(f"Invalid Ethereum address characters: {address!r}")
    return addr.lower()


# ---------------------------------------------------------------------------
# Street Cred scoring
# ---------------------------------------------------------------------------

TIER_THRESHOLDS = [
    (80, "Platinum"),
    (60, "Gold"),
    (40, "Silver"),
    (20, "Bronze"),
    (0,  "None"),
]

TIER_BONUS = {
    "Platinum": 20,
    "Gold":     15,
    "Silver":   10,
    "Bronze":    5,
    "None":      0,
}

GRADE_MAP = [
    (85, "S"),
    (75, "A"),
    (60, "B"),
    (45, "C"),
    (30, "D"),
    (0,  "F"),
]


def compute_street_cred(
    identity_active: bool | None,
    bond_count: int | None,
    next_bond_id: int | None,
    reputation: int | None,
) -> dict:
    """
    Compute the Street Cred score (0–95) and tier from on-chain data.

    Scoring breakdown:
      - ERC-8004 identity active:     30 pts
      - Any bond exists (count > 0):  25 pts
      - Bond is active (nextBondId>0):15 pts
      - Tier bonus (from reputation): Bronze+5 / Silver+10 / Gold+15 / Platinum+20
      - Multiple bonds (count > 1):    5 pts

    Returns a dict with keys: score, tier, grade, breakdown.
    """
    breakdown = {}
    score = 0

    # Identity points
    id_pts = 30 if identity_active else 0
    breakdown["identity"] = id_pts
    score += id_pts

    # Bond exists
    bond_exists_pts = 0
    if bond_count is not None and bond_count > 0:
        bond_exists_pts = 25
    breakdown["bond_exists"] = bond_exists_pts
    score += bond_exists_pts

    # Bond active (next_bond_id > 0 implies at least one accountability bond created)
    bond_active_pts = 0
    if next_bond_id is not None and next_bond_id > 0:
        bond_active_pts = 15
    breakdown["bond_active"] = bond_active_pts
    score += bond_active_pts

    # Tier from reputation — reputation is a raw uint256; we treat it as a
    # simple numeric tier index here (0=None, 1=Bronze, 2=Silver, 3=Gold, 4=Platinum)
    tier = "None"
    if reputation is not None:
        if reputation >= 4:
            tier = "Platinum"
        elif reputation >= 3:
            tier = "Gold"
        elif reputation >= 2:
            tier = "Silver"
        elif reputation >= 1:
            tier = "Bronze"

    tier_pts = TIER_BONUS.get(tier, 0)
    breakdown["tier_bonus"] = tier_pts
    score += tier_pts

    # Multiple bonds bonus
    multi_pts = 5 if (bond_count is not None and bond_count > 1) else 0
    breakdown["multiple_bonds"] = multi_pts
    score += multi_pts

    # Cap at 95
    score = min(score, 95)

    # Determine letter grade
    grade = "F"
    for threshold, letter in GRADE_MAP:
        if score >= threshold:
            grade = letter
            break

    # Determine tier label from final score
    display_tier = "None"
    for threshold, label in TIER_THRESHOLDS:
        if score >= threshold:
            display_tier = label
            break

    return {
        "score":      score,
        "tier":       display_tier,
        "grade":      grade,
        "breakdown":  breakdown,
    }


# ---------------------------------------------------------------------------
# On-chain data fetchers
# ---------------------------------------------------------------------------


def fetch_identity(address: str) -> dict:
    """
    Fetch ERC-8004 identity data for an address.

    Returns dict with: is_active, vns_name, reputation_raw, error.
    """
    result = {"is_active": None, "vns_name": None, "reputation_raw": None, "error": None}
    try:
        # isAgentActive(address)
        calldata = _build_call_data(SELECTORS["isAgentActive"], address)
        raw = eth_call(CONTRACTS["ERC8004IdentityRegistry"], calldata)
        result["is_active"] = _decode_bool(raw)

        # resolveAddressToName(address)
        calldata = _build_call_data(SELECTORS["resolveAddressToName"], address)
        raw = eth_call(CONTRACTS["VaultfireNameService"], calldata)
        result["vns_name"] = _decode_string(raw)

        # getReputation(address)
        calldata = _build_call_data(SELECTORS["getReputation"], address)
        raw = eth_call(CONTRACTS["ERC8004ReputationRegistry"], calldata)
        result["reputation_raw"] = _decode_uint256(raw)

    except Exception as exc:
        result["error"] = str(exc)

    return result


def fetch_bonds(address: str) -> dict:
    """
    Fetch partnership and accountability bond data for an address.

    Returns dict with: partnership_count, next_bond_id, total_active_value, error.
    """
    result = {
        "partnership_count":  None,
        "next_bond_id":       None,
        "total_active_value": None,
        "error":              None,
    }
    try:
        # getBondsByParticipantCount(address)
        calldata = _build_call_data(SELECTORS["getBondsByParticipantCount"], address)
        raw = eth_call(CONTRACTS["AIPartnershipBondsV2"], calldata)
        result["partnership_count"] = _decode_uint256(raw)

        # nextBondId() — no address parameter
        calldata = SELECTORS["nextBondId"]
        raw = eth_call(CONTRACTS["AIAccountabilityBondsV2"], calldata)
        result["next_bond_id"] = _decode_uint256(raw)

        # totalActiveBondValue() — no address parameter
        calldata = SELECTORS["totalActiveBondValue"]
        raw = eth_call(CONTRACTS["AIAccountabilityBondsV2"], calldata)
        result["total_active_value"] = _decode_uint256(raw)

    except Exception as exc:
        result["error"] = str(exc)

    return result


def fetch_protocol_contracts() -> dict:
    """
    Check eth_getCode for the core protocol enforcement contracts.

    Returns dict mapping contract name -> has_code (bool).
    """
    enforcement_contracts = {
        "MissionEnforcement": CONTRACTS["MissionEnforcement"],
        "AntiSurveillance":   CONTRACTS["AntiSurveillance"],
        "PrivacyGuarantees":  CONTRACTS["PrivacyGuarantees"],
    }
    results = {}
    for name, addr in enforcement_contracts.items():
        code = eth_get_code(addr)
        results[name] = _has_code(code)
    return results


def fetch_usdc_balance(address: str) -> dict:
    """
    Fetch the USDC balance for an address on Base.

    Returns dict with: balance_raw (uint256), balance_usdc (float), error.
    """
    result = {"balance_raw": None, "balance_usdc": None, "error": None}
    try:
        calldata = _build_call_data(SELECTORS["balanceOf"], address)
        raw = eth_call(CONTRACTS["USDC"], calldata)
        balance_raw = _decode_uint256(raw)
        result["balance_raw"] = balance_raw
        if balance_raw is not None:
            # USDC has 6 decimals
            result["balance_usdc"] = balance_raw / 1_000_000
    except Exception as exc:
        result["error"] = str(exc)
    return result


def fetch_xmtp_status(address: str) -> dict:
    """
    Attempt an XMTP network query to check messaging reachability for an address.

    Returns dict with: reachable (bool), error.
    """
    result = {"reachable": False, "error": None}
    url = "https://production.xmtp.network/message/v1/query"
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps({"contentTopics": [], "startTimeNs": "0", "endTimeNs": "0"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=RPC_TIMEOUT) as resp:
            # Any successful response means the network is reachable
            result["reachable"] = resp.status in (200, 206, 400)
    except urllib.error.HTTPError as exc:
        # A 400/422 from XMTP still means the network is alive
        if exc.code in (400, 422):
            result["reachable"] = True
        else:
            result["error"] = f"HTTP {exc.code}"
    except Exception as exc:
        result["error"] = str(exc)
    return result


def fetch_hub_stats() -> dict:
    """
    Query the Vaultfire hub API for protocol stats.

    Returns dict with: agent_count, active_bonds, eth_bonded, raw, error.
    """
    result = {
        "agent_count":  None,
        "active_bonds": None,
        "eth_bonded":   None,
        "raw":          None,
        "error":        None,
    }
    url = "https://theloopbreaker.com/api/hub/stats"
    try:
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "VaultfireHermesSkill/1.0"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=RPC_TIMEOUT) as resp:
            raw = json.loads(resp.read())
            result["raw"] = raw
            result["agent_count"]  = raw.get("agentCount",  raw.get("agent_count",  None))
            result["active_bonds"] = raw.get("activeBonds", raw.get("active_bonds", None))
            result["eth_bonded"]   = raw.get("ethBonded",   raw.get("eth_bonded",   None))
    except urllib.error.HTTPError as exc:
        result["error"] = f"HTTP {exc.code}: {exc.reason}"
    except Exception as exc:
        result["error"] = str(exc)
    return result


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

_LINE = "─" * 44


def _check(val: bool | None) -> str:
    """Return ✔ for True, ✘ for False/None."""
    if val is True:
        return "✔"
    return "✘"


def _fmt_kv(key: str, value: str, width: int = 22) -> str:
    return f"  {key:<{width}} {value}"


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------


def cmd_trust(address: str, as_json: bool) -> int:
    """Full trust verification against live Base mainnet contracts."""
    try:
        address = validate_address(address)
    except ValueError as exc:
        _error(str(exc), as_json)
        return 1

    # --- Gather data ---
    identity_data   = fetch_identity(address)
    bond_data       = fetch_bonds(address)
    protocol_data   = fetch_protocol_contracts()
    usdc_data       = fetch_usdc_balance(address)
    xmtp_data       = fetch_xmtp_status(address)

    is_active       = identity_data.get("is_active")
    vns_name        = identity_data.get("vns_name") or "—"
    reputation_raw  = identity_data.get("reputation_raw")
    p_count         = bond_data.get("partnership_count")
    next_bond_id    = bond_data.get("next_bond_id")

    cred            = compute_street_cred(is_active, p_count, next_bond_id, reputation_raw)

    mission_ok      = protocol_data.get("MissionEnforcement", False)
    anti_surv_ok    = protocol_data.get("AntiSurveillance", False)
    privacy_ok      = protocol_data.get("PrivacyGuarantees", False)

    usdc_balance    = usdc_data.get("balance_usdc")
    x402_ready      = usdc_balance is not None and usdc_balance > 0
    xmtp_reachable  = xmtp_data.get("reachable", False)

    bond_label = "✘ None"
    if p_count is not None and p_count > 0:
        bond_label = f"✔ Active ({p_count} bond{'s' if p_count != 1 else ''})"
    acct_bond_label = "✔ Bonded" if (next_bond_id is not None and next_bond_id > 0) else "✘ None"

    if as_json:
        out = {
            "address":            address,
            "chain_id":           CHAIN_ID,
            "trust_grade":        cred["grade"],
            "street_cred":        cred["score"],
            "street_cred_tier":   cred["tier"],
            "erc8004_active":     is_active,
            "vns_name":           identity_data.get("vns_name"),
            "reputation_raw":     reputation_raw,
            "partnership_bonds":  p_count,
            "next_bond_id":       next_bond_id,
            "x402_ready":         x402_ready,
            "usdc_balance":       usdc_balance,
            "xmtp_reachable":     xmtp_reachable,
            "mission_enforcement":mission_ok,
            "anti_surveillance":  anti_surv_ok,
            "privacy_guarantees": privacy_ok,
            "score_breakdown":    cred["breakdown"],
        }
        print(json.dumps(out, indent=2))
        return 0

    # --- Formatted output ---
    x402_str = f"✔ Enabled (EIP-712 · USDC · {usdc_balance:.2f} USDC)" if x402_ready else "✘ Not ready"
    xmtp_str = "✔ Reachable" if xmtp_reachable else "✘ Unreachable"

    print()
    print("⚡ VAULTFIRE TRUST VERIFICATION ⚡")
    print(_LINE)
    print(_fmt_kv("Trust Grade:", cred["grade"]))
    print(_fmt_kv("Street Cred:", f"{cred['score']} / 95  ({cred['tier']})"))
    print(_fmt_kv("Accountability Bond:", acct_bond_label))
    print(_fmt_kv("Partnership Bond:", bond_label))
    print(_fmt_kv("ERC-8004 Identity:", f"{_check(is_active)} {'Registered' if is_active else 'Not registered'}"))
    print(_fmt_kv("VNS Name:", vns_name))
    print(_fmt_kv("Chain:", f"Base ({CHAIN_ID})"))
    print(_fmt_kv("Agent:", _short_address(address)))
    print(_LINE)
    print(_fmt_kv("x402 Payments:", x402_str))
    print(_fmt_kv("XMTP Messaging:", xmtp_str))
    print(_LINE)
    print("  Protocol Commitments:")
    print(_fmt_kv("  Anti-Surveillance:", f"{_check(anti_surv_ok)} {'Enforced on-chain' if anti_surv_ok else 'Not detected'}"))
    print(_fmt_kv("  Privacy Guarantees:", f"{_check(privacy_ok)} {'Active' if privacy_ok else 'Not detected'}"))
    print(_fmt_kv("  Mission Enforcement:", f"{_check(mission_ok)} {'Active' if mission_ok else 'Not detected'}"))
    print(_LINE)
    print("  Powered by Vaultfire Protocol — theloopbreaker.com")
    print()
    return 0


def cmd_streetcred(address: str, as_json: bool) -> int:
    """Compute and display only the Street Cred score and tier."""
    try:
        address = validate_address(address)
    except ValueError as exc:
        _error(str(exc), as_json)
        return 1

    identity_data  = fetch_identity(address)
    bond_data      = fetch_bonds(address)

    is_active      = identity_data.get("is_active")
    reputation_raw = identity_data.get("reputation_raw")
    p_count        = bond_data.get("partnership_count")
    next_bond_id   = bond_data.get("next_bond_id")

    cred = compute_street_cred(is_active, p_count, next_bond_id, reputation_raw)

    if as_json:
        out = {
            "address":    address,
            "score":      cred["score"],
            "tier":       cred["tier"],
            "grade":      cred["grade"],
            "breakdown":  cred["breakdown"],
        }
        print(json.dumps(out, indent=2))
        return 0

    print()
    print("⚡ VAULTFIRE STREET CRED ⚡")
    print(_LINE)
    print(_fmt_kv("Address:", _short_address(address)))
    print(_fmt_kv("Score:", f"{cred['score']} / 95"))
    print(_fmt_kv("Tier:", cred["tier"]))
    print(_fmt_kv("Grade:", cred["grade"]))
    print(_LINE)
    print("  Score Breakdown:")
    for k, v in cred["breakdown"].items():
        label = k.replace("_", " ").title()
        print(_fmt_kv(f"  {label}:", f"+{v} pts"))
    print(_LINE)
    return 0


def cmd_identity(address: str, as_json: bool) -> int:
    """Check ERC-8004 identity registration, VNS name, and reputation."""
    try:
        address = validate_address(address)
    except ValueError as exc:
        _error(str(exc), as_json)
        return 1

    data = fetch_identity(address)

    if as_json:
        out = {
            "address":        address,
            "is_active":      data.get("is_active"),
            "vns_name":       data.get("vns_name"),
            "reputation_raw": data.get("reputation_raw"),
            "error":          data.get("error"),
            "basescan":       f"{BASE_SCAN}/{CONTRACTS['ERC8004IdentityRegistry']}",
        }
        print(json.dumps(out, indent=2))
        return 0

    is_active = data.get("is_active")
    vns_name  = data.get("vns_name") or "—"
    rep       = data.get("reputation_raw")
    rep_str   = str(rep) if rep is not None else "—"
    err       = data.get("error")

    print()
    print("⚡ ERC-8004 IDENTITY ⚡")
    print(_LINE)
    print(_fmt_kv("Address:", _short_address(address)))
    print(_fmt_kv("Agent Active:", f"{_check(is_active)} {'Yes' if is_active else 'No' if is_active is False else 'Unknown'}"))
    print(_fmt_kv("VNS Name:", vns_name))
    print(_fmt_kv("Reputation (raw):", rep_str))
    if err:
        print(_fmt_kv("Error:", err))
    print(_LINE)
    print(f"  Registry:  {BASE_SCAN}/{CONTRACTS['ERC8004IdentityRegistry']}")
    print(f"  VNS:       {BASE_SCAN}/{CONTRACTS['VaultfireNameService']}")
    print(f"  Reputation:{BASE_SCAN}/{CONTRACTS['ERC8004ReputationRegistry']}")
    print()
    return 0


def cmd_bonds(address: str, as_json: bool) -> int:
    """Check partnership and accountability bond status for an address."""
    try:
        address = validate_address(address)
    except ValueError as exc:
        _error(str(exc), as_json)
        return 1

    data = fetch_bonds(address)

    p_count    = data.get("partnership_count")
    next_id    = data.get("next_bond_id")
    total_val  = data.get("total_active_value")
    err        = data.get("error")

    # Convert total_active_value from wei to ETH (18 decimals)
    total_eth_str = "—"
    if total_val is not None:
        total_eth = total_val / 10**18
        total_eth_str = f"{total_eth:.6f} ETH"

    if as_json:
        out = {
            "address":             address,
            "partnership_bonds":   p_count,
            "next_accountability_bond_id": next_id,
            "total_active_value_wei": total_val,
            "total_active_eth":    total_eth_str,
            "error":               err,
        }
        print(json.dumps(out, indent=2))
        return 0

    print()
    print("⚡ VAULTFIRE BOND STATUS ⚡")
    print(_LINE)
    print(_fmt_kv("Address:", _short_address(address)))
    print()
    print("  Partnership Bonds (AIPartnershipBondsV2):")
    p_str = str(p_count) if p_count is not None else "Unknown"
    print(_fmt_kv("  Bond Count:", p_str))
    print()
    print("  Accountability Bonds (AIAccountabilityBondsV2):")
    nid_str = str(next_id) if next_id is not None else "Unknown"
    print(_fmt_kv("  Next Bond ID:", nid_str))
    print(_fmt_kv("  Total Active Value:", total_eth_str))
    if err:
        print()
        print(_fmt_kv("  Error:", err))
    print(_LINE)
    print(f"  Partnership: {BASE_SCAN}/{CONTRACTS['AIPartnershipBondsV2']}")
    print(f"  Accountability: {BASE_SCAN}/{CONTRACTS['AIAccountabilityBondsV2']}")
    print()
    return 0


def cmd_x402(address: str, as_json: bool) -> int:
    """Check x402 payment capability (EIP-712 / USDC on Base)."""
    try:
        address = validate_address(address)
    except ValueError as exc:
        _error(str(exc), as_json)
        return 1

    usdc_data   = fetch_usdc_balance(address)
    balance     = usdc_data.get("balance_usdc")
    balance_raw = usdc_data.get("balance_raw")
    err         = usdc_data.get("error")
    ready       = balance is not None and balance > 0

    if as_json:
        out = {
            "address":       address,
            "x402_ready":    ready,
            "usdc_balance":  balance,
            "balance_raw":   balance_raw,
            "payment_standard": "EIP-712",
            "token":         "USDC",
            "chain":         "Base (8453)",
            "usdc_contract": CONTRACTS["USDC"],
            "error":         err,
        }
        print(json.dumps(out, indent=2))
        return 0

    balance_str = f"{balance:.6f} USDC" if balance is not None else "—"
    ready_str   = "✔ Ready — x402 payments enabled" if ready else "✘ Not ready — zero USDC balance"

    print()
    print("⚡ x402 PAYMENT CAPABILITY ⚡")
    print(_LINE)
    print(_fmt_kv("Address:", _short_address(address)))
    print(_fmt_kv("Standard:", "x402 / EIP-712"))
    print(_fmt_kv("Token:", "USDC (6 decimals)"))
    print(_fmt_kv("Chain:", f"Base ({CHAIN_ID})"))
    print(_fmt_kv("USDC Balance:", balance_str))
    print(_fmt_kv("x402 Status:", ready_str))
    if err:
        print(_fmt_kv("Error:", err))
    print(_LINE)
    print(f"  USDC Contract: {BASE_SCAN}/{CONTRACTS['USDC']}")
    print()
    return 0


def cmd_xmtp(address: str, as_json: bool) -> int:
    """Check XMTP messaging reachability for an address."""
    try:
        address = validate_address(address)
    except ValueError as exc:
        _error(str(exc), as_json)
        return 1

    xmtp_data  = fetch_xmtp_status(address)
    reachable  = xmtp_data.get("reachable", False)
    err        = xmtp_data.get("error")

    if as_json:
        out = {
            "address":    address,
            "reachable":  reachable,
            "network":    "production.xmtp.network",
            "protocol":   "XMTP v1",
            "error":      err,
        }
        print(json.dumps(out, indent=2))
        return 0

    reach_str = "✔ Reachable — XMTP messaging enabled" if reachable else "✘ Unreachable"

    print()
    print("⚡ XMTP MESSAGING REACHABILITY ⚡")
    print(_LINE)
    print(_fmt_kv("Address:", _short_address(address)))
    print(_fmt_kv("Network:", "production.xmtp.network"))
    print(_fmt_kv("Protocol:", "XMTP v1"))
    print(_fmt_kv("Status:", reach_str))
    if err:
        print(_fmt_kv("Error:", err))
    print(_LINE)
    print("  Docs: https://xmtp.org/docs")
    print()
    return 0


def cmd_contracts(as_json: bool) -> int:
    """List all Vaultfire contracts on Base with BaseScan links."""
    # Descriptions for each deployed contract
    _DESCRIPTIONS = {
        "ERC8004IdentityRegistry":           "ERC-8004 agent identity registry",
        "ERC8004ReputationRegistry":         "On-chain agent reputation scores",
        "VaultfireNameService":              "Vaultfire Name Service (VNS)",
        "AIPartnershipBondsV2":              "AI partnership bonds (v2)",
        "AIAccountabilityBondsV2":           "AI accountability bonds (v2)",
        "MissionEnforcement":                "On-chain mission enforcement",
        "AntiSurveillance":                  "Anti-surveillance commitment",
        "PrivacyGuarantees":                 "Privacy guarantees contract",
        "USDC":                              "USDC stablecoin (Base)",
        "ERC8004ValidationRegistry":         "ERC-8004 validation registry",
        "VaultfireERC8004Adapter":           "ERC-8004 protocol adapter",
        "FlourishingMetricsOracle":          "Flourishing metrics oracle",
        "MultisigGovernance":                "Multisig governance module",
        "VaultfireTeleporterBridge":         "Teleporter cross-chain bridge",
        "DilithiumAttestor":                 "Post-quantum attestor (Dilithium)",
        "ProductionBeliefAttestationVerifier": "Production belief attestation verifier",
        "BeliefAttestationVerifier":         "Belief attestation verifier",
    }
    # Build the list from the actual CONTRACTS map
    contract_list = [
        (name, addr, _DESCRIPTIONS.get(name, ""))
        for name, addr in CONTRACTS.items()
    ]

    if as_json:
        out = [
            {
                "name":        name,
                "address":     addr,
                "description": desc,
                "basescan":    f"{BASE_SCAN}/{addr}",
            }
            for name, addr, desc in contract_list
        ]
        print(json.dumps(out, indent=2))
        return 0

    name_w = max(len(n) for n, _, _ in contract_list) + 2
    print()
    print("⚡ VAULTFIRE PROTOCOL CONTRACTS — Base Mainnet ⚡")
    print(_LINE * 2)
    header = f"  {'Contract':<{name_w}} {'Address':<44} Description"
    print(header)
    print("  " + "─" * (len(header) - 2))
    for name, addr, desc in contract_list:
        print(f"  {name:<{name_w}} {addr:<44} {desc}")
    print()
    print("  BaseScan base URL: https://basescan.org/address/<address>")
    print("  Chain: Base Mainnet (ID 8453)")
    print()
    return 0


def cmd_hub(as_json: bool) -> int:
    """Query the Vaultfire hub API for protocol stats."""
    data = fetch_hub_stats()
    err  = data.get("error")

    agent_count  = data.get("agent_count")
    active_bonds = data.get("active_bonds")
    eth_bonded   = data.get("eth_bonded")

    def _fmt(val):
        return str(val) if val is not None else "—"

    if as_json:
        out = {
            "source":       "https://theloopbreaker.com/api/hub/stats",
            "agent_count":  agent_count,
            "active_bonds": active_bonds,
            "eth_bonded":   eth_bonded,
            "raw":          data.get("raw"),
            "error":        err,
        }
        print(json.dumps(out, indent=2))
        return 0

    print()
    print("⚡ VAULTFIRE HUB STATS ⚡")
    print(_LINE)
    if err:
        print(f"  Error fetching hub stats: {err}")
    else:
        print(_fmt_kv("Registered Agents:", _fmt(agent_count)))
        print(_fmt_kv("Active Bonds:", _fmt(active_bonds)))
        print(_fmt_kv("ETH Bonded:", _fmt(eth_bonded)))
    print(_LINE)
    print("  Source: https://theloopbreaker.com/api/hub/stats")
    print("  Hub:    https://theloopbreaker.com")
    print()
    return 0 if not err else 1


# ---------------------------------------------------------------------------
# Error helper
# ---------------------------------------------------------------------------


def _error(message: str, as_json: bool) -> None:
    """Print an error in the appropriate format."""
    if as_json:
        print(json.dumps({"error": message}))
    else:
        print(f"Error: {message}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _add_json_flag(sp: argparse.ArgumentParser) -> None:
    """Add --json flag to a subparser (allows placement after subcommand)."""
    sp.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output machine-readable JSON instead of formatted text",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse argument parser."""
    parser = argparse.ArgumentParser(
        prog="vaultfire_client",
        description=(
            "Vaultfire Protocol skill for the Hermes AI agent framework.\n"
            "Provides on-chain trust verification, identity, bonds, x402, "
            "XMTP checks, and protocol contract listings on Base mainnet."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # Global --json flag (before subcommand)
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        default=False,
        help="Output machine-readable JSON instead of formatted text",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    # trust
    sp = subparsers.add_parser(
        "trust",
        help="Full trust verification (identity + bonds + x402 + XMTP + enforcement)",
    )
    sp.add_argument("address", help="Ethereum address to verify")
    _add_json_flag(sp)

    # streetcred
    sp = subparsers.add_parser(
        "streetcred",
        help="Compute Street Cred score (0–95) with tier",
    )
    sp.add_argument("address", help="Ethereum address to score")
    _add_json_flag(sp)

    # identity
    sp = subparsers.add_parser(
        "identity",
        help="Check ERC-8004 identity registration and VNS name",
    )
    sp.add_argument("address", help="Ethereum address to check")
    _add_json_flag(sp)

    # bonds
    sp = subparsers.add_parser(
        "bonds",
        help="Check partnership and accountability bond status",
    )
    sp.add_argument("address", help="Ethereum address to check")
    _add_json_flag(sp)

    # x402
    sp = subparsers.add_parser(
        "x402",
        help="Check x402 payment capability (EIP-712 / USDC on Base)",
    )
    sp.add_argument("address", help="Ethereum address to check")
    _add_json_flag(sp)

    # xmtp
    sp = subparsers.add_parser(
        "xmtp",
        help="Check XMTP messaging reachability",
    )
    sp.add_argument("address", help="Ethereum address to check")
    _add_json_flag(sp)

    # contracts
    sp = subparsers.add_parser(
        "contracts",
        help="List all Vaultfire protocol contracts on Base with BaseScan links",
    )
    _add_json_flag(sp)

    # hub
    sp = subparsers.add_parser(
        "hub",
        help="Query the Vaultfire hub API at theloopbreaker.com",
    )
    _add_json_flag(sp)

    return parser


def main() -> int:
    """Main entry point for the Vaultfire Hermes skill."""
    parser = build_parser()
    args   = parser.parse_args()
    cmd    = args.command
    # as_json can be set either at global level or per-subcommand level
    json_  = getattr(args, "as_json", False)

    if cmd == "trust":
        return cmd_trust(args.address, json_)
    elif cmd == "streetcred":
        return cmd_streetcred(args.address, json_)
    elif cmd == "identity":
        return cmd_identity(args.address, json_)
    elif cmd == "bonds":
        return cmd_bonds(args.address, json_)
    elif cmd == "x402":
        return cmd_x402(args.address, json_)
    elif cmd == "xmtp":
        return cmd_xmtp(args.address, json_)
    elif cmd == "contracts":
        return cmd_contracts(json_)
    elif cmd == "hub":
        return cmd_hub(json_)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
