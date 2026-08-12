#!/usr/bin/env python3
"""TOKEN 2 / BLOCK A — add a structured `binary_version` + `kernel_commit` to the
cpu_bench KERNEL-CUTOVER era rows.

Run with the orchestrator venv interpreter (it has PyYAML AND jsonschema):

    /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python \
        /mnt/raid0/llm/tmp/era-repair/ratify_cpu_bench_binary_version_20260811.py --dry-run

Drop --dry-run to apply. Idempotent, refuses on drift, and each row is validated and
applied INDEPENDENTLY, so striking one row from the token cannot invalidate the rest.

WHY: `attestation.binary_version` is the only field that witnesses which kernel actually
executed a run, but the era registry records the binary version only inside free-prose
`note:`. Nothing can bind a stamp to a witness by parsing prose, so the A7 repair has
nothing to bind to. This adds the field, taking every value FROM THE ROW'S OWN NOTE —
no value is typed in by hand; the script re-extracts and cross-checks.

SCOPE COLLISION, solved by this field rather than by a new one: `cpu_bench` now carries
two kinds of boundary — kernel cutovers and the E8-cpu-bench-throttle-scope ELIGIBILITY
correction. After this block, "the kernel era at instant T" = the latest cpu_bench row
that HAS a `binary_version` and whose `from` <= T. The eligibility row has no binary and
is therefore correctly invisible to kernel-era derivation, while remaining a real
cpu_bench boundary for eligibility purposes. No discriminator field needed.

E5-cpu-kernel IS DELIBERATELY EXCLUDED: its note records no binary version and no commit
sha, so there is nothing to witness and inventing one would be the exact failure this
repair exists to stop. Consequence, stated rather than papered over: kernel-era
derivation FAILS CLOSED for instants in [2026-06-26T22:07:11Z, 2026-07-20T13:30:13Z).
That is correct — we cannot name a binary we never recorded. Every E5 artifact
pre-registers from 2026-07-23 onward, so no banked manifest falls in that gap.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

REGISTRY = Path("/mnt/raid0/llm/epyc-orchestrator/orchestration/instrument_eras.yaml")

# Row id -> (binary_version, kernel_commit). Values are ASSERTIONS about what the row's
# own note already says; the script re-extracts from the note and refuses on mismatch,
# so this table cannot silently disagree with the registry.
TARGETS = {
    "E6-cpu-kernel": (10098, "6ad45fa3ff6718c07c000061dbc6e29c1771f6e3"),
    "E8-cpu-kernel": (10107, "67a433bf45a8a091d83b4ea0b32ff0735fd51800"),
    "E9-cpu-kernel": (10125, "0db32c06e3e550065b78311a6031ef3dd2c4f27c"),
}

ROW_START = re.compile(r"^  - id: (?P<id>\S+)\s*$", re.MULTILINE)


class Refuse(Exception):
    """Any refusal. Always fatal, always before any write."""


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def row_blocks(raw: str) -> dict[str, tuple[int, int]]:
    """id -> (start_offset, end_offset) for every era row, in file order."""
    marks = [(m.group("id"), m.start()) for m in ROW_START.finditer(raw)]
    if not marks:
        raise Refuse("no era rows found — registry shape is not what this block expects")
    out: dict[str, tuple[int, int]] = {}
    for i, (era_id, start) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(raw)
        if era_id in out:
            raise Refuse(f"duplicate era id {era_id!r} — refusing to guess which row is meant")
        out[era_id] = (start, end)
    return out


def plan_row(raw: str, era_id: str, span: tuple[int, int]) -> dict:
    """Validate ONE row and return its edit plan. Never mutates."""
    want_version, want_commit = TARGETS[era_id]
    start, end = span
    block = raw[start:end]
    plan = {"id": era_id, "block_sha256": sha256(block), "status": None, "insert_at": None,
            "text": None, "version": want_version, "commit": want_commit}

    # Idempotence: already applied?
    have_version = re.search(r"^    binary_version:\s*(\d+)\s*$", block, re.MULTILINE)
    have_commit = re.search(r"^    kernel_commit:\s*\"?([0-9a-f]{40})\"?\s*$", block, re.MULTILINE)
    if have_version or have_commit:
        if not (have_version and have_commit):
            raise Refuse(f"{era_id}: half-applied — one of binary_version/kernel_commit is "
                         "present without the other; refusing to complete a partial edit")
        if int(have_version.group(1)) != want_version or have_commit.group(1) != want_commit:
            raise Refuse(f"{era_id}: DRIFT — registry already carries "
                         f"binary_version={have_version.group(1)} commit={have_commit.group(1)[:12]}…, "
                         f"token asserts {want_version} / {want_commit[:12]}…")
        plan["status"] = "already-applied"
        return plan

    # Cross-check the asserted values against the row's OWN note.
    note_version = re.search(r"binary version (\d+)", block)
    note_commit = re.search(r"llama\.cpp commit ([0-9a-f]{40})", block)
    if not note_version or not note_commit:
        raise Refuse(f"{era_id}: note records no binary version and/or commit sha — "
                     "nothing to witness; this row must not be in the token")
    if int(note_version.group(1)) != want_version:
        raise Refuse(f"{era_id}: note says binary {note_version.group(1)}, token asserts {want_version}")
    if note_commit.group(1) != want_commit:
        raise Refuse(f"{era_id}: note says commit {note_commit.group(1)[:12]}…, "
                     f"token asserts {want_commit[:12]}…")

    scope_line = re.search(r"^    scope: cpu_bench\s*$", block, re.MULTILINE)
    if not scope_line:
        raise Refuse(f"{era_id}: no `    scope: cpu_bench` line — wrong scope or wrong shape")

    plan["status"] = "will-apply"
    plan["insert_at"] = start + scope_line.end() + 1  # just after the newline
    plan["text"] = (f"    binary_version: {want_version}\n"
                    f"    kernel_commit: \"{want_commit}\"\n")
    return plan


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="validate and print; write nothing")
    ap.add_argument("--only", action="append", default=None,
                    help="apply only this era id (repeatable). Omit for all three.")
    ap.add_argument("--attest", default=None, metavar="GATE_ID",
                    help="human attestation id. REQUIRED to write; without it this "
                         "script can only --dry-run.")
    args = ap.parse_args()
    if not args.dry_run and not args.attest:
        raise Refuse("refusing to amend a human-only registry without --attest <GATE_ID>")

    try:
        import yaml
    except ImportError:
        raise Refuse("PyYAML unavailable — run under "
                     "/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python")

    raw = REGISTRY.read_text(encoding="utf-8")
    source_sha = sha256(raw)
    print(f"registry     : {REGISTRY}")
    print(f"source sha256: {source_sha}")

    spans = row_blocks(raw)
    wanted = list(TARGETS) if not args.only else args.only
    for era_id in wanted:
        if era_id not in TARGETS:
            raise Refuse(f"{era_id!r} is not in this token block")
        if era_id not in spans:
            raise Refuse(f"{era_id!r} not present in the registry")

    # Validate EVERY requested row before writing ANY of them.
    plans = [plan_row(raw, era_id, spans[era_id]) for era_id in wanted]
    print()
    for p in plans:
        print(f"  {p['id']:16s} {p['status']:15s} binary_version={p['version']} "
              f"kernel_commit={p['commit'][:12]}…  row_sha256={p['block_sha256'][:16]}…")

    todo = [p for p in plans if p["status"] == "will-apply"]
    if not todo:
        print("\nALREADY APPLIED — nothing to do. Idempotent no-op, exit 0.")
        return 0

    # Apply back-to-front so earlier offsets stay valid.
    out = raw
    for p in sorted(todo, key=lambda p: p["insert_at"], reverse=True):
        out = out[:p["insert_at"]] + p["text"] + out[p["insert_at"]:]

    # Post-conditions, all before any write.
    doc = yaml.safe_load(out)
    if not isinstance(doc, dict) or not isinstance(doc.get("eras"), list):
        raise Refuse("result does not parse as an era registry")
    by_id = {r.get("id"): r for r in doc["eras"] if isinstance(r, dict)}
    for p in todo:
        row = by_id.get(p["id"])
        if row is None or row.get("binary_version") != p["version"] \
                or row.get("kernel_commit") != p["commit"]:
            raise Refuse(f"post-condition failed for {p['id']}")
    before = yaml.safe_load(raw)
    if len(before["eras"]) != len(doc["eras"]):
        raise Refuse("row count changed — refusing")
    added = len(out.splitlines()) - len(raw.splitlines())
    if added != 2 * len(todo):
        raise Refuse(f"expected {2*len(todo)} added lines, got {added} — refusing")
    # Nothing outside the target rows may change.
    for era_id, row in {r["id"]: r for r in before["eras"] if isinstance(r, dict)}.items():
        other = by_id.get(era_id)
        if era_id in [p["id"] for p in todo]:
            continue
        if other != row:
            raise Refuse(f"row {era_id} changed but is not in the token — refusing")

    candidate_sha = sha256(out)
    print(f"\ncandidate sha256: {candidate_sha}")
    print(f"lines added     : {added} (2 per row × {len(todo)} row(s))")

    if args.dry_run:
        print("\nDRY RUN — no write performed.")
        for p in todo:
            print(f"\n--- {p['id']} would gain ---")
            print(p["text"].rstrip("\n"))
        return 0

    REGISTRY.write_text(out, encoding="utf-8")
    print(f"\nAPPLIED to {REGISTRY}")

    # Receipts, in the house shape: a detailed record plus a keyed index entry.
    # Both are git-tracked paths — check_ratifier_receipt_contract.sh verifies
    # tracking, not mere presence, because a committed index asserting "ratified"
    # over an untracked receipt loses its evidence on a fresh checkout.
    import json, datetime as _dt
    root = Path("/mnt/raid0/llm/epyc-root/artifacts/operator")
    detail = root / "ratify_cpu_bench_binary_version_20260811.json"
    detail.write_text(json.dumps({
        "schema": "epyc.operator_cpu_bench_binary_version.v1",
        "human_attestation": args.attest,
        "status": "ratified",
        "ratified_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "target": str(REGISTRY),
        "target_sha256_before": source_sha,
        "target_sha256_after": sha256(out),
        "applied_rows": sorted(p["id"] for p in todo),
        "already_applied_rows": sorted(p["id"] for p in plans
                                       if p["status"] == "already-applied"),
        "struck_rows": sorted(set(TARGETS) - {p["id"] for p in plans}),
        "excluded_by_design": {
            "E5-cpu-kernel": "note records no binary version or commit sha; nothing to "
                             "witness. Kernel-era derivation fails closed for instants in "
                             "[2026-06-26T22:07:11Z, 2026-07-20T13:30:13Z)."},
        "row_sha256_before": {p["id"]: p["block_sha256"] for p in plans},
        "fields_added_per_row": ["binary_version", "kernel_commit"],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    index = root / "receipts" / f"{args.attest}.json"
    index.write_text(json.dumps({
        "gate_id": args.attest,
        "indexed_by": "attest",
        "receipt": str(detail),
        "schema_version": "session_bus.receipt_index.v1",
        "status": "ratified",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"receipt      : {detail}")
    print(f"receipt index: {index}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Refuse as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        sys.exit(2)
