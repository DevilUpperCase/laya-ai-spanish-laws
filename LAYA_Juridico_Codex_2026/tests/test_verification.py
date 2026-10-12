"""Release evidence must fail closed; these tests do not certify product readiness."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_package import VerificationError, artifact_path, check_coverage, check_source_audit, evaluate_release, read_json


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "verification/evidence").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def artifact(self, name, content):
        path = self.root / "verification/evidence" / name
        path.write_text(content, encoding="utf-8")
        return {"path": "verification/evidence/" + name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def passed_gate(self, reference):
        return {"status": "passed", "reviewed_by": "reviewer-01", "reviewed_at": "2026-10-11",
                "evidence": [reference], "assessment": {}}

    def test_unexecuted_gate_blocks_release(self):
        result = evaluate_release(self.root, ["G01"], {"gates": {"G01": {"status": "not_run"}}})
        self.assertEqual(result["status"], "blocked")

    def test_marking_pass_without_evidence_cannot_pass(self):
        gate = self.passed_gate(None)
        gate["evidence"] = []
        result = evaluate_release(self.root, ["G01"], {"gates": {"G01": gate}})
        self.assertEqual(result["status"], "blocked")

    def test_tampered_artifact_blocks(self):
        ref = self.artifact("review.json", '{"result":"passed"}')
        (self.root / ref["path"]).write_text('{"result":"failed"}', encoding="utf-8")
        with self.assertRaises(VerificationError):
            artifact_path(self.root, ref)

    def test_artifact_cannot_escape_evidence_directory(self):
        ref = {"path": "verification/evidence/../../outside.txt", "sha256": "a" * 64}
        with self.assertRaises(VerificationError):
            artifact_path(self.root, ref)

    def test_reviewed_hash_is_only_an_integrity_pass(self):
        gate = self.passed_gate(self.artifact("review.json", '{"review":"synthetic test"}'))
        result = evaluate_release(self.root, ["G01"], {"gates": {"G01": gate}})
        self.assertEqual(result["status"], "artifact_checks_passed")
        self.assertIn("not proof", result["limitation"])

    def test_empty_or_malformed_inventory_cannot_verify_coverage(self):
        inventory = {"status": "verified", "entities": []}
        (self.root / "verification/coverage-inventory.json").write_text(json.dumps(inventory), encoding="utf-8")
        self.assertTrue(check_coverage(self.root))

    def test_missing_municipality_mapping_blocks_even_with_verified_flag(self):
        csv_text = "jurisdiction_id,level,parent_id,name,official_source_url\n" + "\n".join(
            f"{i},{level},,fixture,https://example.invalid/fixture"
            for i, level in enumerate(["state", "autonomous_community", "autonomous_city", "province", "municipality"]))
        authority = self.artifact("jurisdictions.csv", csv_text)
        inventory = {"status": "verified", "reviewed_by": "reviewer-01", "reviewed_at": "2026-10-11",
                     "inventory_revision": "synthetic-test", "authoritative_inventory": authority,
                     "entities": [{"jurisdiction_id": str(i)} for i in range(4)]}
        (self.root / "verification/coverage-inventory.json").write_text(json.dumps(inventory), encoding="utf-8")
        self.assertTrue(check_coverage(self.root))

    def test_duplicate_and_nonfinite_json_are_rejected(self):
        for content in ['{"status":"passed","status":"failed"}', '{"count":NaN}']:
            ref = self.artifact("invalid.json", content)
            with self.assertRaises(VerificationError):
                read_json(self.root / ref["path"])

    def test_retention_and_review_minimums_cannot_be_boolean_shortcuts(self):
        ref = self.artifact("review.json", '{"review":"synthetic test"}')
        gate = self.passed_gate(ref)
        gate["assessment"] = {"immediate_revocation": True, "retention_mode": "until_tenant_deletion",
                              "live_purge_max_hours": True, "backup_max_age_days": 31}
        self.assertEqual(evaluate_release(self.root, ["G16"], {"gates": {"G16": gate}})["status"], "blocked")
        gate["assessment"] = {"reviewed_query_count": 199, "languages": ["es", "ca", "gl", "eu"],
                              "territorial_tiers": ["state", "regional", "provincial", "municipal", "island_foral"],
                              "temporal_cases": 1, "negative_cases": 1, "thresholds_frozen_before_holdout": True}
        self.assertEqual(evaluate_release(self.root, ["G21"], {"gates": {"G21": gate}})["status"], "blocked")

    def test_missing_gate_and_missing_reviewer_block(self):
        gate = self.passed_gate(self.artifact("review.json", '{}'))
        gate["reviewed_by"] = "pending"
        result = evaluate_release(self.root, ["G01", "G02"], {"gates": {"G01": gate}})
        self.assertEqual(result["status"], "blocked")
        self.assertGreaterEqual(len(result["blockers"]), 3)

    def test_source_verified_flag_cannot_replace_terms_or_fixtures(self):
        audit = {"status": "verified", "source_id": "synthetic",
                 "reviewed_by": "reviewer-01", "reviewed_at": "2026-10-11",
                 "reuse": {"approved": False}}
        with self.assertRaises(VerificationError):
            check_source_audit(self.root, audit)

    def test_failed_and_unknown_extra_gates_block(self):
        ref = self.artifact("review.json", '{}')
        failed = self.passed_gate(ref)
        failed["status"] = "failed"
        result = evaluate_release(self.root, ["G01"], {"gates": {"G01": failed, "G99": self.passed_gate(ref)}})
        self.assertEqual(result["status"], "blocked")

    def test_bad_review_dataset_types_fail_closed(self):
        gate = self.passed_gate(self.artifact("review.json", '{}'))
        gate["assessment"] = {"reviewed_query_count": 200, "languages": None,
                              "territorial_tiers": None, "temporal_cases": 1, "negative_cases": 1,
                              "thresholds_frozen_before_holdout": True}
        self.assertEqual(evaluate_release(self.root, ["G21"], {"gates": {"G21": gate}})["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
