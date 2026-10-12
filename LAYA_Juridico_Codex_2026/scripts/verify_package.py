"""Offline planning checks; release mode checks artifacts/attestations, not legal truth."""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDERS = {"unknown", "not_run", "unverified", "template", "pending"}


class VerificationError(ValueError):
    pass


def read_json(path: Path):
    if path.stat().st_size > 16 * 1024 * 1024:
        raise VerificationError("JSON artifact exceeds 16 MiB")
    def invalid_constant(value):
        raise VerificationError("Non-finite JSON number")
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise VerificationError("Duplicate JSON key")
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8-sig"),
                      parse_constant=invalid_constant, object_pairs_hook=unique_object)


def meaningful(value) -> bool:
    return (isinstance(value, str) and bool(value.strip()) and
            value.strip().lower() not in PLACEHOLDERS and "<" not in value)


def reviewed(record: dict) -> bool:
    if not meaningful(record.get("reviewed_by")):
        return False
    value = record.get("reviewed_at")
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def artifact_path(root: Path, reference: dict) -> Path:
    if not isinstance(reference, dict):
        raise VerificationError("Artifact reference must be an object")
    relative = reference.get("path")
    digest = reference.get("sha256")
    if (not isinstance(relative, str) or
            not relative.replace("\\", "/").startswith("verification/evidence/") or
            Path(relative).is_absolute()):
        raise VerificationError("Artifacts must be within verification/evidence/")
    target = (root / relative).resolve()
    if not target.is_relative_to((root / "verification/evidence").resolve()):
        raise VerificationError("Artifact path escapes evidence directory")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        raise VerificationError("Artifact SHA256 is absent or invalid")
    if not target.is_file() or target.stat().st_size == 0:
        raise VerificationError("Artifact is absent or empty")
    hasher = hashlib.sha256()
    with target.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    if hasher.hexdigest() != digest.lower():
        raise VerificationError("Artifact SHA256 does not match")
    return target


def check_source_audit(root: Path, audit: dict) -> None:
    if not isinstance(audit, dict) or audit.get("status") != "verified" or not reviewed(audit):
        raise VerificationError("Source audit lacks verified independent review")
    if not meaningful(audit.get("source_id")):
        raise VerificationError("Source ID is missing")
    reuse = audit.get("reuse", {})
    if (reuse.get("approved") is not True or not meaningful(reuse.get("terms_url")) or
            not meaningful(reuse.get("reviewed_by"))):
        raise VerificationError("Source reuse terms are unapproved")
    current = audit.get("current_range", {})
    if current.get("complete") is not True:
        raise VerificationError("Source current range is incomplete")
    start = datetime.fromisoformat(current["start"])
    end = datetime.fromisoformat(current["end"])
    if start > end:
        raise VerificationError("Source current range is reversed")
    history = audit.get("available_history", {})
    if history.get("complete") is not True:
        raise VerificationError("Available history is incomplete")
    if history.get("start") is not None or history.get("end") is not None:
        if datetime.fromisoformat(history["start"]) > datetime.fromisoformat(history["end"]):
            raise VerificationError("Historical range is reversed")
    elif not history.get("unavailable_ranges"):
        raise VerificationError("Absent historical range has no reviewed limitation")
    for limitation in history.get("unavailable_ranges", []):
        if not isinstance(limitation, dict) or not reviewed(limitation):
            raise VerificationError("Unavailable history lacks review")
    reconciliation = audit.get("reconciliation", {})
    if (reconciliation.get("complete") is not True or
            reconciliation.get("missing_required_periods", ["unknown"]) != []):
        raise VerificationError("Source has required reconciliation gaps")
    expected = reconciliation.get("expected_publications")
    integrated = reconciliation.get("integrated_publications")
    if (type(expected) is not int or type(integrated) is not int or
            expected < 0 or integrated != expected):
        raise VerificationError("Source publication counts are missing or unreconciled")
    fixtures = audit.get("fixtures", [])
    evidence = reconciliation.get("evidence", [])
    if not fixtures or not evidence:
        raise VerificationError("Source lacks original fixtures or reconciliation evidence")
    for reference in fixtures + evidence:
        artifact_path(root, reference)


def check_coverage(root: Path) -> list[str]:
    try:
        inventory = read_json(root / "verification/coverage-inventory.json")
        if inventory.get("status") != "verified" or not reviewed(inventory):
            raise VerificationError("Official coverage inventory is not reviewed/verified")
        if not meaningful(inventory.get("inventory_revision")):
            raise VerificationError("Official inventory revision is missing")
        authority = artifact_path(root, inventory["authoritative_inventory"])
        with authority.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            fields = {"jurisdiction_id", "level", "parent_id", "name", "official_source_url"}
            if not fields.issubset(reader.fieldnames or []):
                raise VerificationError("Official inventory CSV lacks required columns")
            rows = list(reader)
        ids = [row["jurisdiction_id"] for row in rows]
        if not ids or any(not meaningful(i) for i in ids) or len(set(ids)) != len(ids):
            raise VerificationError("Official inventory has absent/duplicate entity IDs")
        required_levels = {"state", "autonomous_community", "autonomous_city", "province", "municipality"}
        if not required_levels.issubset({row["level"] for row in rows}):
            raise VerificationError("Official inventory omits a required territorial tier")
        entities = inventory.get("entities", [])
        mapped_ids = [entry["jurisdiction_id"] for entry in entities]
        if len(set(mapped_ids)) != len(mapped_ids) or set(mapped_ids) != set(ids):
            raise VerificationError("Coverage mappings do not equal official entity inventory")
        official_rows = {row["jurisdiction_id"]: row for row in rows}
        for entry in entities:
            official = official_rows[entry["jurisdiction_id"]]
            if (entry.get("level") != official["level"] or
                    entry.get("parent_id", "") != official["parent_id"]):
                raise VerificationError("Coverage hierarchy differs from authoritative inventory")
            if entry.get("current_normative_status") != "verified" or not reviewed(entry):
                raise VerificationError("A required jurisdiction lacks verified current coverage")
            audits = entry.get("source_audits", [])
            if not audits:
                raise VerificationError("A required jurisdiction has no source audit evidence")
            for reference in audits:
                audit = read_json(artifact_path(root, reference))
                check_source_audit(root, audit)
                if entry["jurisdiction_id"] not in audit.get("territory_ids", []):
                    raise VerificationError("Source audit does not cover its mapped jurisdiction")
        return []
    except (OSError, ValueError, KeyError, TypeError, AttributeError, csv.Error):
        # No artifact body or private data is included in error output.
        return ["National inventory/source coverage is missing, malformed, incomplete or unreviewed"]


def finite_number(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def evaluate_release(root: Path, gate_ids: list[str], evidence: dict) -> dict:
    blockers = []
    records = evidence.get("gates", {}) if isinstance(evidence, dict) else {}
    if not isinstance(records, dict):
        records = {}
    if set(records) != set(gate_ids):
        blockers.append("Release gate IDs do not match the acceptance matrix")
    for gate_id in gate_ids:
        gate = records.get(gate_id, {})
        if not isinstance(gate, dict) or gate.get("status") != "passed":
            blockers.append(f"{gate_id}: not passed (unexecuted/failed/missing)")
            continue
        if not reviewed(gate):
            blockers.append(f"{gate_id}: missing reviewer or valid review timestamp")
        references = gate.get("evidence", [])
        if not isinstance(references, list) or not references:
            blockers.append(f"{gate_id}: no substantive evidence artifacts")
        else:
            for reference in references:
                try:
                    artifact_path(root, reference)
                except (OSError, ValueError, TypeError):
                    blockers.append(f"{gate_id}: invalid, missing or tampered evidence artifact")
        assessment = gate.get("assessment", {})
        if not isinstance(assessment, dict):
            assessment = {}
        if gate_id == "G13":
            blockers.extend(check_coverage(root))
        if gate_id == "G16":
            hours, days = assessment.get("live_purge_max_hours"), assessment.get("backup_max_age_days")
            if (assessment.get("retention_mode") != "until_tenant_deletion" or
                    assessment.get("immediate_revocation") is not True or
                    not finite_number(hours) or not 0 <= hours <= 24 or
                    not finite_number(days) or not 0 <= days <= 30):
                blockers.append("G16: retention/deletion deadlines are not satisfied")
        if gate_id == "G17" and assessment.get("tombstones_reapplied_before_access") is not True:
            blockers.append("G17: restoration does not attest deletion barrier")
        if gate_id == "G21":
            count = assessment.get("reviewed_query_count")
            languages, tiers = assessment.get("languages"), assessment.get("territorial_tiers")
            temporal, negative = assessment.get("temporal_cases"), assessment.get("negative_cases")
            if (not finite_number(count) or count < 200 or
                    not isinstance(languages, list) or not {"es", "ca", "gl", "eu"}.issubset(str(x) for x in languages) or
                    not isinstance(tiers, list) or not {"state", "regional", "provincial", "municipal", "island_foral"}.issubset(str(x) for x in tiers) or
                    not finite_number(temporal) or temporal <= 0 or
                    not finite_number(negative) or negative <= 0 or
                    assessment.get("thresholds_frozen_before_holdout") is not True):
                blockers.append("G21: professional dataset/strata/frozen-threshold minimums missing")
    return {"status": "blocked" if blockers else "artifact_checks_passed",
            "blockers": blockers,
            "limitation": "Integrity and attestations only; not proof of legal completeness, reviewer authenticity or deployment state."}


def package_checks(root: Path) -> tuple[list[dict], list[str]]:
    checks = []
    gate_ids = []
    try:
        manifest = read_json(root / "verification/package-manifest.json")
        expected = [f"R{i:02}" for i in range(1, 25)]
        if manifest["requirements"] != expected:
            raise VerificationError("Requirement inventory differs from R01..R24")
        if manifest["mandatory_tools"] != ["FastAPI", "LangChain Core", "LangGraph", "local LAYA"]:
            raise VerificationError("Mandatory stack inventory changed")
        for relative in manifest["required_files"]:
            path = (root / relative).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file() or path.stat().st_size == 0:
                raise VerificationError("Required package file is missing/empty or escapes root")
            if path.suffix == ".json":
                read_json(path)
            if path.suffix == ".py":
                ast.parse(path.read_text(encoding="utf-8-sig"), filename=relative)
            if path.suffix == ".md":
                body = path.read_text(encoding="utf-8-sig")
                for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", body):
                    if "://" in target or target.startswith("#"):
                        continue
                    link = target.split("#", 1)[0]
                    linked = (path.parent / link).resolve()
                    generated = {(root / name).resolve() for name in manifest["generated_reports"]}
                    if not linked.is_file() and linked not in generated:
                        raise VerificationError("Local documentation link is broken")
        checks.append({"name": "Package files, JSON and Python syntax", "status": "passed"})
        spec = (root / "docs/SPECIFICATION.md").read_text(encoding="utf-8")
        if set(re.findall(r"\| (R\d{2}) \|", spec)) != set(expected):
            raise VerificationError("Specification requirement IDs are incomplete")
        for tool in manifest["mandatory_tools"]:
            if tool not in spec:
                raise VerificationError("Specification omits a mandatory tool")
        tasks = manifest["task_plans"]
        for task, relative in tasks.items():
            body = (root / relative).read_text(encoding="utf-8")
            if f"### Task {task}:" not in body or "## Global Constraints" not in body or "- [ ]" not in body:
                raise VerificationError("Task plan lacks matching task/constraints/checklist")
        with (root / "docs/verification/ACCEPTANCE_MATRIX.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        gate_ids = [row["gate_id"] for row in rows]
        if len(set(gate_ids)) != len(gate_ids) or set(gate_ids) != {f"G{i:02}" for i in range(1, 23)}:
            raise VerificationError("Acceptance matrix gate IDs must be G01..G22 exactly once")
        covered = set()
        for row in rows:
            reqs, owners = row["requirement_ids"].split(";"), row["task_ids"].split(";")
            if not set(reqs).issubset(expected) or not set(owners).issubset(tasks):
                raise VerificationError("Acceptance matrix has unknown requirement/task")
            if not row["procedure"].strip() or not row["evidence_policy"].strip():
                raise VerificationError("Acceptance matrix lacks procedure/evidence policy")
            covered.update(reqs)
        if covered != set(expected):
            raise VerificationError("Acceptance matrix leaves requirements uncovered")
        checks.append({"name": "R01..R24 task/gate traceability", "status": "passed"})
        api = read_json(root / "docs/contracts/api-contract.json")
        route_keys = [(r["method"], r["path"]) for r in api["endpoints"]]
        if len(set(route_keys)) != len(route_keys) or len(route_keys) != 10:
            raise VerificationError("API endpoint inventory is duplicated/incomplete")
        if (api["generative_llms"] is not False or api["private_search_checkpointing"] is not False or
                api["default_laya_mode"] != "shadow" or api["embedding_dimensions"] != 1024 or
                set(api["languages"]) != {"es", "ca", "gl", "eu"}):
            raise VerificationError("API contract violates confirmed architecture")
        if any(r["auth"] != "tenant" for r in api["endpoints"] if r["path"].startswith("/v1/")):
            raise VerificationError("Business endpoints must declare authorized tenant context")
        checks.append({"name": "Planned API contract invariants (not live routes)", "status": "passed"})
    except (OSError, ValueError, KeyError, TypeError, AttributeError, SyntaxError, csv.Error) as error:
        checks.append({"name": "Package structure/contracts", "status": "failed", "detail": type(error).__name__})
    return checks, gate_ids


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", action="store_true", help="also require reviewed product release evidence")
    args = parser.parse_args()
    checks, gate_ids = package_checks(ROOT)
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                               cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
        checks.append({"name": "Example and verifier unittest suite", "status": "passed" if tests.returncode == 0 else "failed",
                       "command": "python -m unittest discover -s tests -v", "output": tests.stdout + tests.stderr})
    except (OSError, subprocess.TimeoutExpired) as error:
        checks.append({"name": "Example and verifier unittest suite", "status": "failed", "detail": type(error).__name__})
    try:
        evidence = read_json(ROOT / "verification/release-evidence.json")
        release = evaluate_release(ROOT, gate_ids, evidence)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        release = {"status": "blocked", "blockers": ["Release evidence is missing/malformed"], "limitation": "No real product readiness established."}
    offline_ok = all(check["status"] == "passed" for check in checks)
    report = {"specification_date": "2026-10-11", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "selected_scope": "release" if args.release else "offline_package",
              "offline_status": "passed" if offline_ok else "failed", "checks": checks, "release": release,
              "not_executed_by_this_command": ["Running FastAPI/LangChain/LangGraph product", "Live database auth RLS and storage", "Real local LAYA/BGE-M3 inference",
                               "Official source ingestion and nationwide historical coverage", "Professional multilingual review and load pilot",
                               "Document OCR/UI workflows", "Deletion backups and restore rehearsal", "Dependency/model/source license approval", "Application deployment"]}
    directory = ROOT / "verification/reports"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "latest.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    lines = ["# Observed verification report", "", "Specification date: 2026-10-11.", "",
             f"Selected scope: **{report['selected_scope']}**. Offline package: **{report['offline_status']}**. Product release: **{release['status']}**.", "",
             "This offline command validates package artifacts and example/verifier tests. Actual implementation tests, database/model/browser results are recorded separately in pytest.xml, runtime.json and browser-check.json. Offline success does not establish release readiness.", "", "## Executed offline checks", ""]
    lines.extend(f"- {check['name']}: {check['status']}" for check in checks)
    lines += ["", "## Release blockers", ""] + [f"- {item}" for item in release["blockers"]]
    lines += ["", "## Not executed by this offline command", ""] + [f"- {item}" for item in report["not_executed_by_this_command"]]
    lines += ["", "Evidence validation checks file integrity and minimum attestations; professional review and real infrastructure tests remain mandatory.", "",
              "Full test output and the UTC execution timestamp are in latest.json.", ""]
    (directory / "latest.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Offline package: {report['offline_status']}; product release: {release['status']}")
    for check in checks:
        print(f"  {check['status']}: {check['name']}")
    print(f"Release blockers: {len(release['blockers'])}; report: verification/reports/latest.md")
    return 0 if offline_ok and (not args.release or release["status"] == "artifact_checks_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
