#!/usr/bin/env python3
"""Score filed production science outcomes over a rolling 24-hour window.

Input is normalized JSONL emitted from retained filer receipts. This is a
science verdict ledger: scheduling READY depth and hourly publication rate are
deliberately not inputs to the score.
"""
from __future__ import annotations

import argparse
import base64
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace


class InvalidRecord(ValueError):
    pass


OUTCOMES = {
    "COMPLETE", "PARTIAL", "FAILED-RUN", "WITHDRAWN", "VALIDATOR-FAILED",
    "DIAGNOSTIC-RESULT", "READY-WAIT-DISK", "QUALIFIED",
    "QUALIFICATION-FAILED", "REFUSED-PRE-GRANT", "READY",
}
SHA256_RE = re.compile(r"[0-9a-f]{64}")
ISO_RE = re.compile(r"\b(20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d))\b")


def read_bound_file(path_value: object, expected_name: str, digest_value: object) -> bytes | None:
    if not isinstance(path_value, str) or not path_value:
        return None
    path = Path(path_value)
    if not path.is_absolute():
        root = Path(__file__).resolve().parents[2]
        path = root / path
    if path.is_symlink():
        return None
    try:
        path = path.resolve(strict=True)
        if not path.is_relative_to(Path(__file__).resolve().parents[2]):
            # Production evidence may live in the external compute store; only
            # relative paths are confined to this checkout.
            if not Path(path_value).is_absolute():
                return None
    except OSError:
        return None
    if path.name != expected_name or path.is_symlink():
        return None
    try:
        if not path.is_file():
            return None
        contents = path.read_bytes()
    except OSError:
        return None
    if not isinstance(digest_value, str) or SHA256_RE.fullmatch(digest_value) is None:
        return None
    return contents if hashlib.sha256(contents).hexdigest() == digest_value else None


def source_fields(row_id: str, body: bytes) -> tuple[str | None, str | None, str | None, str | None]:
    """Read identity, outcome, verdict and filing time from the retained FILED bytes."""
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return None, None, None, None
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = None
    if isinstance(value, dict):
        source_id = value.get("id")
        verdict = value.get("verdict")
        filed_at = value.get("filed_at") or value.get("event_time")
        text_upper = (str(value.get("outcome", "")) + " " + str(verdict or "")).upper()
        explicit = value.get("outcome")
    else:
        source_id = row_id if text.strip() else None
        verdict_match = re.search(r"(?im)\bverdict\s*[:=]\s*([^;\n]+)", text)
        verdict = verdict_match.group(1).strip() if verdict_match else None
        filed_match = ISO_RE.search(text)
        filed_at = filed_match.group(1) if filed_match else None
        text_upper = text.upper()
        explicit = None
    if not isinstance(verdict, str) or not verdict.strip():
        verdict = None
    outcome = explicit if explicit in OUTCOMES else None
    if outcome is None:
        if "FAILED-RUN" in text_upper:
            outcome = "FAILED-RUN"
        elif "READY-WAIT-DISK" in text_upper:
            outcome = "READY-WAIT-DISK"
        elif "QUALIFICATION-FAILED" in text_upper:
            outcome = "QUALIFICATION-FAILED"
        elif "REFUSED-PRE-GRANT" in text_upper:
            outcome = "REFUSED-PRE-GRANT"
        elif "VALIDATOR-FAILED" in text_upper:
            outcome = "VALIDATOR-FAILED"
        elif "DIAGNOSTIC" in text_upper:
            outcome = "DIAGNOSTIC-RESULT"
        elif "PARTIAL" in text_upper or re.search(r"\brc\s*=\s*75\b", text, re.I):
            outcome = "PARTIAL"
        elif "WITHDRAWN" in text_upper:
            outcome = "WITHDRAWN"
        elif "READY" in text_upper and "COMPLETE" not in text_upper:
            outcome = "READY"
        elif "COMPLETE" in text_upper or re.search(r"\brc\s*=\s*0\b", text, re.I):
            outcome = "COMPLETE"
    return source_id, outcome, verdict, filed_at


def terminal_proof(record: dict) -> tuple[bool, str]:
    evidence = record.get("terminal_evidence")
    if not isinstance(evidence, dict):
        return False, "terminal-ended-grant-evidence-missing"
    ended_path = evidence.get("ended_path")
    if not isinstance(ended_path, str) or not Path(ended_path).is_absolute():
        return False, "terminal-ended-path-missing"
    ended_bytes = read_bound_file(ended_path, record["id"] + ".ended", evidence.get("ended_sha256"))
    grant_path = evidence.get("grant_path")
    if (not isinstance(grant_path, str) or not Path(grant_path).is_absolute()
            or Path(grant_path).name != record["id"] + ".grant"
            or not isinstance(ended_path, str) or Path(grant_path) != Path(ended_path).with_suffix(".grant")):
        return False, "terminal-grant-path-identity-mismatch"
    if ended_bytes is None:
        return False, "terminal-ended-file-missing-or-hash-mismatch"
    try:
        fields = dict(line.split("=", 1) for line in ended_bytes.decode("utf-8").splitlines() if "=" in line)
        # Engine terminals retain a packed first line; older normalized test
        # receipts also use separate rc/time lines. Accept both explicitly.
        first = re.fullmatch(r"rc=(-?\d+) time=(\S+) reason=.*", next(iter(ended_bytes.decode("utf-8").splitlines()), ""))
        if first:
            fields["rc"], fields["time"] = first.groups()
        rc = int(fields["rc"])
    except (UnicodeDecodeError, KeyError, ValueError):
        return False, "terminal-ended-schema-invalid"
    if fields.get("phase") != "production" or fields.get("granted") != "true":
        return False, "terminal-ended-not-production-grant"
    if (fields.get("id") != record["id"] or fields.get("owner") != record["owner"]
            or record["phase"] != "production" or record["granted"] is not True):
        return False, "normalized-production-grant-mismatch"
    try:
        grant_bytes = base64.b64decode(fields["grant_body_b64"], validate=True)
        grant_sha = hashlib.sha256(grant_bytes).hexdigest()
        grant_text = grant_bytes.decode("utf-8")
        match = re.fullmatch(r"regions=([^ ]+) start=(\d{4}-\d\d-\d\dT\d\d:\d\dZ) end=(\d{4}-\d\d-\d\dT\d\d:\d\dZ)\n?", grant_text)
        if match is None:
            return False, "grant-schema-invalid"
        regions, grant_start, grant_end = match.groups()
        if (fields.get("grant_path") != grant_path
                or fields.get("grant_sha256") != evidence.get("grant_sha256")
                or fields.get("grant_sha256") != grant_sha
                or fields.get("grant_regions") != regions
                or fields.get("grant_start") != grant_start
                or fields.get("grant_end") != grant_end):
            return False, "ended-grant-binding-mismatch"
        # If the scheduler retains the original file, it must be byte-identical
        # to the engine's immutable terminal copy. The terminal copy survives
        # scheduler cleanup of transient .grant files.
        original_grant = Path(grant_path)
        if original_grant.exists():
            if original_grant.is_symlink() or original_grant.read_bytes() != grant_bytes:
                return False, "grant-file-terminal-copy-mismatch"
    except (KeyError, ValueError, UnicodeDecodeError, OSError):
        return False, "grant-schema-invalid"
    if record["outcome"] == "COMPLETE" and rc != 0:
        return False, "terminal-rc-outcome-mismatch"
    if record["outcome"] == "PARTIAL" and rc != 75:
        return False, "terminal-rc-outcome-mismatch"
    if record["outcome"] == "FAILED-RUN" and rc in (0, 75):
        return False, "terminal-rc-outcome-mismatch"
    try:
        ended_time = parse_time(fields["time"])
        filed_time = parse_time(record["event_time"])
    except (KeyError, InvalidRecord):
        return False, "terminal-time-invalid"
    if ended_time > filed_time:
        return False, "filing-before-terminal"
    return True, ""


def qualification_proof(record: dict) -> tuple[bool, str]:
    evidence = record.get("qualification_receipt")
    if not isinstance(evidence, dict):
        return False, "sealed-qualification-receipt-missing"
    receipt_path = evidence.get("receipt_path")
    receipt_sha = evidence.get("receipt_sha256")
    if not isinstance(receipt_path, str) or not Path(receipt_path).is_absolute():
        return False, "qualification-receipt-path-missing"
    if SHA256_RE.fullmatch(receipt_sha or "") is None or Path(receipt_path).is_symlink():
        return False, "qualification-receipt-binding-invalid"
    try:
        receipt_bytes = Path(receipt_path).read_bytes()
        receipt = json.loads(receipt_bytes)
    except (OSError, json.JSONDecodeError):
        return False, "qualification-receipt-unreadable"
    if hashlib.sha256(receipt_bytes).hexdigest() != receipt_sha:
        return False, "qualification-receipt-hash-mismatch"
    if receipt.get("kind") != "epyc.qual.pass.v1" or receipt.get("id") != record["id"]:
        return False, "qualification-receipt-identity-mismatch"
    required = ("manifest_path", "nonce_store", "allowlist_path", "policy_path", "flags_dir")
    if any(not isinstance(evidence.get(key), str) or not evidence[key] for key in required):
        return False, "qualification-verifier-input-missing"
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import qualify_launcher
        manifest = qualify_launcher.load(evidence["manifest_path"])
        args = SimpleNamespace(
            allowlist=evidence["allowlist_path"], nonce_store=evidence["nonce_store"],
            policy=evidence["policy_path"], fingerprint_now=True, flags_dir=evidence["flags_dir"],
        )
        if str(qualify_launcher.receipt_path(manifest).resolve()) != str(Path(receipt_path).resolve(strict=True)):
            return False, "qualification-receipt-path-mismatch"
        verified = qualify_launcher.verify(manifest, args)
    except Exception:
        return False, "sealed-qualification-verification-failed"
    if verified.get("id") != record["id"]:
        return False, "qualification-row-identity-mismatch"
    if manifest.get("owner") != record["owner"]:
        return False, "qualification-owner-mismatch"
    return True, ""


def parse_time(value: object) -> datetime:
    if not isinstance(value, str) or not value:
        raise InvalidRecord("event_time-required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidRecord("event_time-invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InvalidRecord("event_time-must-include-timezone")
    return parsed.astimezone(timezone.utc)


def validate(record: object) -> dict:
    if not isinstance(record, dict):
        raise InvalidRecord("record-must-be-object")
    for key in ("id", "owner", "event_time", "phase", "outcome", "granted", "qualified", "verdict", "source_receipt"):
        if key not in record:
            raise InvalidRecord("missing:" + key)
    for key in ("id", "owner"):
        if not isinstance(record[key], str) or not record[key].strip():
            raise InvalidRecord("invalid:" + key)
    if record["phase"] not in ("production", "qualification", "ready"):
        raise InvalidRecord("invalid:phase")
    if record["outcome"] not in OUTCOMES:
        raise InvalidRecord("invalid:outcome")
    if type(record["granted"]) is not bool or type(record["qualified"]) is not bool:
        raise InvalidRecord("invalid:grant-or-qualification-flag")
    if record["verdict"] is not None and (not isinstance(record["verdict"], str) or not record["verdict"].strip()):
        raise InvalidRecord("invalid:verdict")
    src = record["source_receipt"]
    if (not isinstance(src, dict) or not isinstance(src.get("path"), str) or not src["path"].strip()
            or not isinstance(src.get("body"), str)):
        raise InvalidRecord("invalid:source-receipt-path")
    if not isinstance(src.get("sha256"), str) or SHA256_RE.fullmatch(src["sha256"]) is None:
        raise InvalidRecord("invalid:source-receipt-sha256")
    source_bytes = read_bound_file(src["path"], record["id"] + ".FILED", src["sha256"])
    source_id, source_outcome, source_verdict, source_time = source_fields(record["id"], source_bytes or b"")
    source_valid = (source_bytes is not None and source_bytes == src["body"].encode("utf-8")
                    and source_id == record["id"] and source_outcome == record["outcome"]
                    and source_verdict == record["verdict"] and source_time is not None)
    if source_valid:
        try:
            source_valid = parse_time(source_time) == parse_time(record["event_time"])
        except InvalidRecord:
            source_valid = False
    ended_valid, ended_reason = terminal_proof(record)
    qual_valid, qual_reason = qualification_proof(record)
    normalized = dict(record)
    normalized["_event_time"] = parse_time(record["event_time"])
    normalized["_source_valid"] = source_valid
    normalized["_terminal_valid"] = ended_valid
    normalized["_terminal_reason"] = ended_reason
    normalized["_qualification_valid"] = qual_valid
    normalized["_qualification_reason"] = qual_reason
    normalized["_source_reason"] = "" if source_valid else "source-receipt-unavailable-or-row-mismatch"
    return normalized


def score(record: dict) -> int:
    """Return -1/0/+1 only when source and terminal evidence support the row."""
    if not record.get("_source_valid") or not record.get("_terminal_valid"):
        return 0
    return policy_score(
        phase=record["phase"], outcome=record["outcome"], granted=record["granted"],
        qualified=record["qualified"] is True and record.get("_qualification_valid") is True,
        verdict=record["verdict"],
    )


def policy_score(*, phase: str, outcome: str, granted: bool, qualified: bool, verdict: str | None) -> int:
    """Pure D2 policy, separated from evidence validation for unit tests."""
    if phase != "production":
        return 0
    if outcome == "FAILED-RUN" and granted is True:
        return -1
    if (qualified and granted is True and isinstance(verdict, str) and verdict.strip()
            and outcome in ("COMPLETE", "PARTIAL", "DIAGNOSTIC-RESULT")):
        return 1
    return 0


def summarize(records: list[dict], as_of: datetime, window: timedelta) -> dict:
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of-must-include-timezone")
    end = as_of.astimezone(timezone.utc)
    start = end - window
    owners = defaultdict(lambda: {"science_score": 0, "verdict_rows": 0, "failed_runs": 0, "unscored_rows": 0, "unscored_reasons": {}})
    seen_ids: set[str] = set()
    for raw in records:
        record = validate(raw)
        if record["id"] in seen_ids:
            raise InvalidRecord("duplicate-run-id:" + record["id"])
        seen_ids.add(record["id"])
        when = record["_event_time"]
        if when > end:
            raise InvalidRecord("event_time-in-future:" + record["id"])
        if when < start:
            continue
        value = score(record)
        bucket = owners[record["owner"]]
        bucket["science_score"] += value
        if value == -1:
            bucket["failed_runs"] += 1
        elif value == 1:
            bucket["verdict_rows"] += 1
        else:
            bucket["unscored_rows"] += 1
            reason = (record["_source_reason"] or record["_terminal_reason"] or
                      record["_qualification_reason"] or "no-qualified-terminal-verdict")
            bucket["unscored_reasons"][reason] = bucket["unscored_reasons"].get(reason, 0) + 1
    return {
        "kind": "epyc.science-quota.v1",
        "window_start": start.isoformat().replace("+00:00", "Z"),
        "window_end": end.isoformat().replace("+00:00", "Z"),
        "window_hours": window.total_seconds() / 3600,
        "owners": {owner: values for owner, values in sorted(owners.items())},
    }


def read_jsonl(path: Path) -> list[dict]:
    result = []
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            result.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise InvalidRecord(f"{path}:{line_no}:invalid-json") from exc
    return result


def _ended_fields(path: Path) -> dict[str, str]:
    """Read primitive terminal fields; terminal_proof remains the authority."""
    try:
        return dict(line.split("=", 1) for line in path.read_text().splitlines() if "=" in line)
    except OSError:
        return {}


def _manifests_by_id(manifest_dir: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for path in sorted(manifest_dir.rglob("*.json")):
        try:
            value = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and isinstance(value.get("id"), str):
            if value["id"] in found:
                # Ambiguous current qualification is not silently selected.
                found[value["id"]] = Path()
            else:
                found[value["id"]] = path.resolve()
    return found


def _artifact(root: Path, filename: str) -> Path:
    direct = root / filename
    if direct.is_file():
        return direct
    matches = sorted(root.rglob(filename))
    return matches[0] if len(matches) == 1 else direct


def collect_records(filed_dir: Path, ended_dir: Path, manifest_dir: Path, *,
                    nonce_store: str, allowlist: str, policy: str, flags_dir: str) -> list[dict]:
    """Derive scorer rows from retained filing/terminal/qualification artifacts.

    FILED content determines the event, while grant status and phase come from
    the immutable `.ended`; no metadata supplied by a normalized input is read.
    """
    manifests = _manifests_by_id(manifest_dir)
    records = []
    for filed in sorted(filed_dir.glob("*.FILED")):
        run_id = filed.name[:-len(".FILED")]
        raw = filed.read_bytes()
        src_id, outcome, verdict, filed_at = source_fields(run_id, raw)
        ended_path = _artifact(ended_dir, f"{run_id}.ended")
        terminal = _ended_fields(ended_path)
        manifest_path = manifests.get(run_id)
        manifest = {}
        if manifest_path and manifest_path != Path():
            try:
                manifest = json.loads(manifest_path.read_text())
            except (OSError, json.JSONDecodeError):
                manifest = {}
        receipt_path = Path(manifest.get("scratch_root", "/__missing__")) / "qualification" / f"QUAL-{run_id}.json"
        receipt_evidence = None
        try:
            receipt_bytes = receipt_path.read_bytes()
            receipt_evidence = {
                "receipt_path": str(receipt_path.resolve()),
                "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
                "manifest_path": str(manifest_path), "nonce_store": nonce_store,
                "allowlist_path": allowlist, "policy_path": policy, "flags_dir": flags_dir,
            }
        except OSError:
            pass
        owner = terminal.get("owner") or "unknown"
        try:
            event_time = parse_time(filed_at).isoformat()
        except InvalidRecord:
            # Keep malformed historical filings inspectable; validation will
            # refuse scoring and the command reports the malformed timestamp.
            event_time = filed_at or ""
        ended_sha = hashlib.sha256(ended_path.read_bytes()).hexdigest() if ended_path.is_file() else ""
        grant_path = ended_path.with_suffix(".grant")
        grant_sha = hashlib.sha256(grant_path.read_bytes()).hexdigest() if grant_path.is_file() else terminal.get("grant_sha256", "")
        record = {
            "id": src_id or run_id, "owner": owner, "event_time": event_time,
            "phase": terminal.get("phase", "production"), "outcome": outcome or "READY",
            "granted": terminal.get("granted") == "true", "qualified": False,
            "verdict": verdict, "source_receipt": {"path": str(filed.resolve()),
                "body": raw.decode("utf-8", errors="replace"),
                "sha256": hashlib.sha256(raw).hexdigest()},
            "terminal_evidence": {"ended_path": str(ended_path.resolve()),
                "ended_sha256": ended_sha, "grant_path": str(grant_path.resolve()),
                "grant_sha256": grant_sha},
            "qualification_receipt": receipt_evidence,
        }
        # Derive the qualification marker by running the exact verifier used by
        # score; input fields can never assert this bit.
        try:
            validated = validate(record)
            record["qualified"] = validated["_qualification_valid"] is True
        except (InvalidRecord, OSError):
            pass
        records.append(record)
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path, nargs="?", help="normalized JSONL for score mode")
    parser.add_argument("--collect-filed-dir", type=Path, help="authoritative filing-done directory; enables collect then score")
    parser.add_argument("--ended-dir", type=Path, help="directory containing retained <id>.ended and grant copies")
    parser.add_argument("--manifest-dir", type=Path, help="directory tree containing current qualification manifests")
    parser.add_argument("--nonce-store", default="/nonexistent")
    parser.add_argument("--allowlist", default="/nonexistent")
    parser.add_argument("--policy", default="/nonexistent")
    parser.add_argument("--flags-dir", default="/nonexistent")
    parser.add_argument("--normalized-out", type=Path, help="write derived normalized JSONL before scoring")
    parser.add_argument("--as-of", help="timezone-aware ISO timestamp; defaults to current UTC")
    parser.add_argument("--window-hours", type=float, default=24.0)
    args = parser.parse_args(argv)
    if args.collect_filed_dir:
        if not args.ended_dir or not args.manifest_dir:
            parser.error("collect mode requires --ended-dir and --manifest-dir")
    elif not args.records:
        parser.error("records is required unless --collect-filed-dir is set")
    if args.window_hours <= 0:
        parser.error("--window-hours must be positive")
    try:
        as_of = parse_time(args.as_of) if args.as_of else datetime.now(timezone.utc)
        records = (collect_records(args.collect_filed_dir, args.ended_dir, args.manifest_dir,
                                   nonce_store=args.nonce_store, allowlist=args.allowlist,
                                   policy=args.policy, flags_dir=args.flags_dir)
                   if args.collect_filed_dir else read_jsonl(args.records))
        if args.normalized_out:
            args.normalized_out.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in records))
        output = summarize(records, as_of, timedelta(hours=args.window_hours))
    except (OSError, InvalidRecord, ValueError) as exc:
        print("REFUSED " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(output, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
