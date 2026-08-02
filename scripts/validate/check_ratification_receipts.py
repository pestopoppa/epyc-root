#!/usr/bin/env python3
"""Fail when a script amends the measurement trust boundary without a receipt.

WHY THIS EXISTS
---------------
`MEASUREMENT.md` §5 requires the human to sign ONCE, at apply time, over a
consolidated bundle: protocol + evidence hashes + validation results + exact
state diff. Every 2026-07 ratification amended the constitution and emitted no
such bundle; each verified instead that its own edit had ARRIVED. One of them
tore a wrapped bullet in §3 in half and its grep-for-my-marker check passed.

Fixing those scripts one by one closes those instances. This closes the CLASS:
any script that writes a trust-boundary artifact must also emit a receipt, and a
new one that does not is caught the first time this runs.

DERIVED, NOT RESTATED
---------------------
The boundary is read from `coordination/session-bus/human_only_paths.yaml` —
the same human-amendment-only list the PreToolUse hook enforces — so a path added
there is covered here automatically, with nobody needing to remember. A
hand-maintained second copy is exactly the defect this repository has already
been bitten by twice (`REQUIRED_SOURCE_ARTIFACTS` 9 emitted / 7 checked, and the
`device` field absent from runtime attestation).

THREE OUTCOMES
--------------
PASS / FAIL / COULD-NOT-CHECK. If the boundary list cannot be read, that is
COULD-NOT-CHECK and exits non-zero — it is NOT "no violations found".
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path("/workspace")
BOUNDARY_LIST = REPO_ROOT / "coordination" / "session-bus" / "human_only_paths.yaml"
RECEIPT_DIR = REPO_ROOT / "artifacts" / "operator" / "receipts"
SCAN_GLOBS = ("artifacts/**/*.sh", "artifacts/**/*.py", "scripts/operator/**/*.sh")
SKIP_NAMES = ("ratify_receipt.sh", "ratification_receipt.py", "check_ratification_receipts.py")

# Idioms that WRITE a file. A script merely mentioning MEASUREMENT.md (a comment,
# a `git diff` for review, a hash check) is not amending it.
WRITE_IDIOMS = (
    re.compile(r"git\s+(?:-C\s+\S+\s+)?apply\b"),
    re.compile(r"""open\(\s*["'][^"']*\.(?:md|yaml)["']\s*,\s*["']w"""),
    re.compile(r"^\s*edit\(", re.M),
    re.compile(r"\bsed\s+-i\b"),
    re.compile(r"\btee\s+(?:-a\s+)?[^|]*MEASUREMENT"),
    re.compile(r">\s*\"?\$?\{?(?:ROOT|M|D|B)\}?/?[A-Za-z_/]*MEASUREMENT"),
    re.compile(r"\bcp\s+[^\n]*\$\{?ROOT\}?/MEASUREMENT"),
)
RECEIPT_IDIOMS = (
    re.compile(r"\breceipt_emit\b"),
    re.compile(r"ratification_receipt\.py\s+emit"),
)

PASS, FAIL, COULD_NOT_CHECK = "PASS", "FAIL", "COULD-NOT-CHECK"


def boundary_tokens(path: Path) -> tuple[list[str], list[str]]:
    """Return (globs, errors) for the epyc-root half of the trust boundary."""
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [], [
            f"{COULD_NOT_CHECK}: trust-boundary list {path} is unreadable ({exc}); "
            "no script could be classified, so a clean result here would be a lie"
        ]
    if not isinstance(doc, dict) or not isinstance(doc.get("paths"), list):
        return [], [
            f"{COULD_NOT_CHECK}: trust-boundary list {path} has no 'paths' list; "
            "nothing could be derived"
        ]
    globs = [
        str(entry["glob"])
        for entry in doc["paths"]
        if isinstance(entry, dict)
        and entry.get("repo") == "epyc-root"
        and isinstance(entry.get("glob"), str)
    ]
    if not globs:
        return [], [
            f"{COULD_NOT_CHECK}: trust-boundary list {path} declares no epyc-root paths"
        ]
    return globs, []


def _mentions_boundary(text: str, globs: list[str]) -> list[str]:
    hits = []
    for glob in globs:
        if "*" in glob:
            prefix = glob.split("*")[0]
            if prefix and prefix in text:
                hits.append(glob)
        elif glob in text or Path(glob).name in text:
            hits.append(glob)
    return hits


def scan(repo_root: Path, globs: list[str]) -> tuple[list[dict], list[str]]:
    findings: list[dict] = []
    errors: list[str] = []
    seen: set[Path] = set()
    for pattern in SCAN_GLOBS:
        for path in sorted(repo_root.glob(pattern)):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            if path.name in SKIP_NAMES:
                continue
            if any(fnmatch.fnmatch(str(path), f"*{s}*") for s in ("/receipts/", "/__pycache__/")):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                errors.append(f"{COULD_NOT_CHECK}: could not read {path}: {exc}")
                continue
            touched = _mentions_boundary(text, globs)
            if not touched:
                continue
            if not any(rx.search(text) for rx in WRITE_IDIOMS):
                continue
            has_receipt = any(rx.search(text) for rx in RECEIPT_IDIOMS)
            findings.append(
                {
                    "script": str(path.relative_to(repo_root)),
                    "boundary_paths": sorted(set(touched)),
                    "verdict": PASS if has_receipt else FAIL,
                }
            )
    return findings, errors


def check_receipts(directory: Path) -> tuple[list[dict], list[str]]:
    receipts: list[dict] = []
    errors: list[str] = []
    if not directory.exists():
        return receipts, []
    for path in sorted(directory.glob("*.receipt.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"{COULD_NOT_CHECK}: receipt {path.name} is unreadable ({exc})")
            continue
        verdict = doc.get("verdict")
        receipts.append(
            {
                "receipt": path.name,
                "ratification_id": doc.get("ratification_id"),
                "protocol_id": doc.get("protocol_id"),
                "verdict": verdict,
            }
        )
        if verdict != "RATIFIED":
            errors.append(
                f"receipt {path.name} carries verdict {verdict!r}; a ratification whose "
                "own receipt is not RATIFIED must not be treated as ratified"
            )
    return receipts, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--boundary-list", type=Path, default=BOUNDARY_LIST)
    parser.add_argument("--receipt-dir", type=Path, default=RECEIPT_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    globs, errors = boundary_tokens(args.boundary_list)
    findings, scan_errors = ([], []) if not globs else scan(args.repo_root, globs)
    errors.extend(scan_errors)
    receipts, receipt_errors = check_receipts(args.receipt_dir)
    errors.extend(receipt_errors)

    missing = [f for f in findings if f["verdict"] == FAIL]
    if args.json:
        print(
            json.dumps(
                {
                    "boundary_globs": globs,
                    "scripts": findings,
                    "receipts": receipts,
                    "errors": errors,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(f"trust-boundary globs (derived from {args.boundary_list.name}): {globs}")
        for f in findings:
            print(f"  [{f['verdict']:>15s}] {f['script']}  -> {', '.join(f['boundary_paths'])}")
        for r in receipts:
            print(f"  receipt {r['verdict']:<10s} {r['ratification_id']} ({r['protocol_id']})")
        for e in errors:
            print(f"  ! {e}")
        if missing:
            print(
                f"\nFAIL: {len(missing)} script(s) amend the measurement trust boundary "
                "without emitting the MEASUREMENT.md §5 consolidated receipt."
            )
        elif errors:
            print(f"\n{COULD_NOT_CHECK}: {len(errors)} condition(s) could not be evaluated.")
        else:
            print(f"\nOK: {len(findings)} boundary-amending script(s), all receipted.")

    if missing:
        return 1
    if errors:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
