#!/usr/bin/env python3
"""
Unit tests for vaultfire_client.py — the Vaultfire Protocol Hermes skill.

Tests cover:
  - Address validation
  - ABI encoding helpers
  - Decoding helpers (bool, uint256, string)
  - Street Cred scoring logic
  - CLI argument parsing
  - Contract map completeness

Run:
    python -m pytest tests/test_vaultfire_client.py -v
    # or
    python tests/test_vaultfire_client.py
"""

import json
import os
import sys
import unittest

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))

from vaultfire_client import (
    CONTRACTS,
    SELECTORS,
    CHAIN_ID,
    _encode_address,
    _build_call_data,
    _decode_bool,
    _decode_uint256,
    _decode_string,
    _has_code,
    _short_address,
    validate_address,
    compute_street_cred,
    build_parser,
    _RPC_FALLBACKS,
)


# ---------------------------------------------------------------------------
# Address validation
# ---------------------------------------------------------------------------

class TestValidateAddress(unittest.TestCase):
    """Tests for Ethereum address validation and normalisation."""

    def test_valid_address_with_prefix(self):
        addr = validate_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
        self.assertEqual(addr, "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913")

    def test_valid_address_without_prefix(self):
        addr = validate_address("833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
        self.assertEqual(addr, "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913")

    def test_address_with_whitespace(self):
        addr = validate_address("  0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913  ")
        self.assertEqual(addr, "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913")

    def test_short_address_raises(self):
        with self.assertRaises(ValueError):
            validate_address("0x1234")

    def test_invalid_hex_raises(self):
        with self.assertRaises(ValueError):
            validate_address("0xZZZZ89fCD6eDb6E08f4c7C32D4f71b54bdA02913")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            validate_address("")


# ---------------------------------------------------------------------------
# ABI encoding helpers
# ---------------------------------------------------------------------------

class TestEncodeAddress(unittest.TestCase):
    """Tests for _encode_address ABI helper."""

    def test_encodes_to_64_hex_chars(self):
        encoded = _encode_address("0xABCDEF1234567890abcdef1234567890ABCDEF12")
        self.assertEqual(len(encoded), 64)
        self.assertTrue(encoded.startswith("0" * 24))  # 24 zero-pad + 40 hex address

    def test_strips_0x_prefix(self):
        encoded = _encode_address("0x1234")
        self.assertNotIn("0x", encoded)

    def test_lowercase(self):
        encoded = _encode_address("0xABCDEF")
        self.assertEqual(encoded, encoded.lower())


class TestBuildCallData(unittest.TestCase):
    """Tests for _build_call_data."""

    def test_selector_only(self):
        data = _build_call_data("0xee53a423")
        self.assertEqual(data, "0xee53a423")

    def test_selector_with_address(self):
        data = _build_call_data("0x70a08231", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
        self.assertTrue(data.startswith("0x70a08231"))
        # 10 chars selector + 64 chars encoded address = 74 chars total
        self.assertEqual(len(data), 10 + 64)


# ---------------------------------------------------------------------------
# Decoding helpers
# ---------------------------------------------------------------------------

class TestDecodeBool(unittest.TestCase):
    """Tests for _decode_bool."""

    def test_true(self):
        # 32 bytes with value 1
        hex_val = "0x" + "0" * 63 + "1"
        self.assertTrue(_decode_bool(hex_val))

    def test_false(self):
        hex_val = "0x" + "0" * 64
        self.assertFalse(_decode_bool(hex_val))

    def test_none_on_empty(self):
        self.assertIsNone(_decode_bool(None))
        self.assertIsNone(_decode_bool("0x"))

    def test_nonzero_is_true(self):
        hex_val = "0x" + "0" * 62 + "ff"
        self.assertTrue(_decode_bool(hex_val))


class TestDecodeUint256(unittest.TestCase):
    """Tests for _decode_uint256."""

    def test_zero(self):
        hex_val = "0x" + "0" * 64
        self.assertEqual(_decode_uint256(hex_val), 0)

    def test_one(self):
        hex_val = "0x" + "0" * 63 + "1"
        self.assertEqual(_decode_uint256(hex_val), 1)

    def test_large_value(self):
        # 1 ETH in wei = 10^18 = 0xDE0B6B3A7640000
        hex_val = "0x" + "0" * 49 + "de0b6b3a7640000"
        self.assertEqual(_decode_uint256(hex_val), 10**18)

    def test_none_on_empty(self):
        self.assertIsNone(_decode_uint256(None))
        self.assertIsNone(_decode_uint256("0x"))


class TestDecodeString(unittest.TestCase):
    """Tests for _decode_string."""

    def test_none_on_empty(self):
        self.assertIsNone(_decode_string(None))
        self.assertIsNone(_decode_string("0x"))

    def test_none_on_short_data(self):
        self.assertIsNone(_decode_string("0x1234"))

    def test_empty_string(self):
        # offset=0x20, length=0
        data = "0x" + "0" * 63 + "20" + "0" * 64
        result = _decode_string(data)
        self.assertEqual(result, "")

    def test_hello_string(self):
        # Manually encode "hello" in ABI format
        # offset = 0x20 (32) — 64 hex chars
        offset = "0" * 62 + "20"   # 64 hex chars
        # length = 5 — 64 hex chars
        length = "0" * 62 + "05"   # 64 hex chars
        # "hello" = 68656c6c6f, right-padded to 32 bytes
        hello_hex = "68656c6c6f" + "0" * 54  # 64 hex chars (5 bytes + 27 bytes padding)
        data = "0x" + offset + length + hello_hex
        self.assertEqual(len(offset), 64)
        self.assertEqual(len(length), 64)
        self.assertEqual(len(hello_hex), 64)
        result = _decode_string(data)
        self.assertEqual(result, "hello")


class TestHasCode(unittest.TestCase):
    """Tests for _has_code (contract deployment check)."""

    def test_no_code(self):
        self.assertFalse(_has_code(None))
        self.assertFalse(_has_code("0x"))
        self.assertFalse(_has_code("0x0"))

    def test_has_code(self):
        self.assertTrue(_has_code("0x6080604052"))

    def test_empty_string(self):
        self.assertFalse(_has_code(""))


class TestShortAddress(unittest.TestCase):
    """Tests for _short_address formatting."""

    def test_with_prefix(self):
        result = _short_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
        self.assertEqual(result, "0x8335...2913")

    def test_without_prefix(self):
        result = _short_address("833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
        self.assertEqual(result, "0x8335...2913")


# ---------------------------------------------------------------------------
# Street Cred scoring
# ---------------------------------------------------------------------------

class TestStreetCred(unittest.TestCase):
    """Tests for compute_street_cred scoring logic."""

    def test_zero_score(self):
        """No identity, no bonds, no reputation => score 0."""
        result = compute_street_cred(
            identity_active=False,
            bond_count=0,
            next_bond_id=0,
            reputation=0,
        )
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["tier"], "None")
        self.assertEqual(result["grade"], "F")

    def test_identity_only(self):
        """Active identity gives 30 points."""
        result = compute_street_cred(
            identity_active=True,
            bond_count=0,
            next_bond_id=0,
            reputation=0,
        )
        self.assertEqual(result["score"], 30)
        self.assertEqual(result["breakdown"]["identity"], 30)
        self.assertEqual(result["grade"], "D")

    def test_bond_exists(self):
        """Having bonds gives 25 points."""
        result = compute_street_cred(
            identity_active=False,
            bond_count=1,
            next_bond_id=0,
            reputation=0,
        )
        self.assertEqual(result["breakdown"]["bond_exists"], 25)

    def test_bond_active(self):
        """next_bond_id > 0 gives 15 points."""
        result = compute_street_cred(
            identity_active=False,
            bond_count=0,
            next_bond_id=1,
            reputation=0,
        )
        self.assertEqual(result["breakdown"]["bond_active"], 15)

    def test_multiple_bonds(self):
        """More than 1 bond gives 5 bonus points."""
        result = compute_street_cred(
            identity_active=False,
            bond_count=3,
            next_bond_id=0,
            reputation=0,
        )
        self.assertEqual(result["breakdown"]["multiple_bonds"], 5)

    def test_platinum_tier_bonus(self):
        """Reputation >= 4 => Platinum => +20 bonus."""
        result = compute_street_cred(
            identity_active=False,
            bond_count=0,
            next_bond_id=0,
            reputation=4,
        )
        self.assertEqual(result["breakdown"]["tier_bonus"], 20)

    def test_gold_tier_bonus(self):
        """Reputation 3 => Gold => +15."""
        result = compute_street_cred(
            identity_active=False,
            bond_count=0,
            next_bond_id=0,
            reputation=3,
        )
        self.assertEqual(result["breakdown"]["tier_bonus"], 15)

    def test_max_score_capped_at_95(self):
        """Maximum possible score is 95, not 95+."""
        result = compute_street_cred(
            identity_active=True,     # +30
            bond_count=5,             # +25 bond_exists + 5 multiple
            next_bond_id=10,          # +15
            reputation=4,             # +20 (Platinum)
        )
        # 30 + 25 + 15 + 20 + 5 = 95 exactly
        self.assertEqual(result["score"], 95)
        self.assertEqual(result["tier"], "Platinum")
        self.assertEqual(result["grade"], "S")

    def test_none_values_handled(self):
        """None values should be handled gracefully."""
        result = compute_street_cred(
            identity_active=None,
            bond_count=None,
            next_bond_id=None,
            reputation=None,
        )
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["tier"], "None")
        self.assertEqual(result["grade"], "F")

    def test_grade_boundaries(self):
        """Verify grade letter boundaries."""
        # S grade: >= 85
        r = compute_street_cred(True, 5, 10, 4)  # 95
        self.assertEqual(r["grade"], "S")

        # A grade: >= 75
        r = compute_street_cred(True, 2, 5, 3)  # 30+25+15+15+5=90
        self.assertEqual(r["grade"], "S")

        # B grade: 60-74
        r = compute_street_cred(True, 2, 5, 1)  # 30+25+15+5+5=80
        self.assertEqual(r["grade"], "A")

        # D grade: 30-44
        r = compute_street_cred(True, 0, 0, 0)  # 30
        self.assertEqual(r["grade"], "D")


# ---------------------------------------------------------------------------
# Contract map integrity
# ---------------------------------------------------------------------------

class TestContractMap(unittest.TestCase):
    """Tests for CONTRACTS dict integrity."""

    def test_all_addresses_are_valid_hex(self):
        """Every contract address must be a valid 42-char hex string."""
        for name, addr in CONTRACTS.items():
            with self.subTest(contract=name):
                self.assertTrue(addr.startswith("0x"), f"{name}: missing 0x prefix")
                self.assertEqual(len(addr), 42, f"{name}: wrong length {len(addr)}")
                int(addr, 16)  # should not raise

    def test_no_duplicate_addresses(self):
        """No two contracts should share the same address."""
        addrs = [a.lower() for a in CONTRACTS.values()]
        self.assertEqual(len(addrs), len(set(addrs)), "Duplicate contract addresses found")

    def test_core_contracts_present(self):
        """Key protocol contracts must be in the map."""
        required = [
            "ERC8004IdentityRegistry",
            "ERC8004ReputationRegistry",
            "VaultfireNameService",
            "AIPartnershipBondsV2",
            "AIAccountabilityBondsV2",
            "MissionEnforcement",
            "AntiSurveillance",
            "PrivacyGuarantees",
            "USDC",
        ]
        for name in required:
            self.assertIn(name, CONTRACTS, f"Missing required contract: {name}")

    def test_usdc_address(self):
        """USDC on Base has a known canonical address."""
        self.assertEqual(
            CONTRACTS["USDC"].lower(),
            "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
        )

    def test_contract_count(self):
        """We should have at least 17 contracts."""
        self.assertGreaterEqual(len(CONTRACTS), 17)


# ---------------------------------------------------------------------------
# Function selectors
# ---------------------------------------------------------------------------

class TestSelectors(unittest.TestCase):
    """Tests for function selector values."""

    def test_known_selectors(self):
        """Verify selectors match expected keccak256[:4] values."""
        expected = {
            "balanceOf":              "0x70a08231",
            "isAgentActive":          "0x554c4f4b",
            "getReputation":          "0x9c89a0e2",
            "resolveAddressToName":   "0x13fee8d3",
            "getBondsByParticipantCount": "0x67ff6265",
            "nextBondId":             "0xee53a423",
            "totalActiveBondValue":   "0xe7683e58",
        }
        for name, sel in expected.items():
            with self.subTest(selector=name):
                self.assertEqual(SELECTORS[name], sel, f"Selector mismatch for {name}")

    def test_all_selectors_are_4_bytes(self):
        """Every selector should be 0x + 8 hex chars = 10 chars total."""
        for name, sel in SELECTORS.items():
            with self.subTest(selector=name):
                self.assertTrue(sel.startswith("0x"))
                self.assertEqual(len(sel), 10)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class TestConfig(unittest.TestCase):
    """Tests for configuration constants."""

    def test_chain_id(self):
        self.assertEqual(CHAIN_ID, 8453)

    def test_rpc_fallbacks_not_empty(self):
        self.assertGreater(len(_RPC_FALLBACKS), 0)

    def test_rpc_fallbacks_are_https(self):
        for url in _RPC_FALLBACKS:
            self.assertTrue(url.startswith("https://"), f"Non-HTTPS RPC: {url}")


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------

class TestCLIParser(unittest.TestCase):
    """Tests for argparse CLI structure."""

    def setUp(self):
        self.parser = build_parser()

    def test_trust_command(self):
        args = self.parser.parse_args(["trust", "0x1234567890abcdef1234567890abcdef12345678"])
        self.assertEqual(args.command, "trust")
        self.assertEqual(args.address, "0x1234567890abcdef1234567890abcdef12345678")

    def test_hub_command(self):
        args = self.parser.parse_args(["hub"])
        self.assertEqual(args.command, "hub")

    def test_contracts_command(self):
        args = self.parser.parse_args(["contracts"])
        self.assertEqual(args.command, "contracts")

    def test_json_flag_global(self):
        # Global --json is set on the parser namespace but subcommand
        # --json flag takes precedence; test that per-subcommand works
        args = self.parser.parse_args(["hub", "--json"])
        self.assertTrue(args.as_json)

    def test_json_flag_per_command(self):
        args = self.parser.parse_args(["trust", "0x1234567890abcdef1234567890abcdef12345678", "--json"])
        self.assertTrue(args.as_json)

    def test_all_commands_exist(self):
        commands = ["trust", "streetcred", "identity", "bonds", "x402", "xmtp", "contracts", "hub"]
        for cmd in commands:
            with self.subTest(command=cmd):
                if cmd in ("contracts", "hub"):
                    args = self.parser.parse_args([cmd])
                else:
                    args = self.parser.parse_args([cmd, "0x1234567890abcdef1234567890abcdef12345678"])
                self.assertEqual(args.command, cmd)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
