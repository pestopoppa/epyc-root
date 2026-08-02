#!/usr/bin/env python3
"""Emit the consolidated ratification receipt that `MEASUREMENT.md` §5 requires.

WHY THIS EXISTS
---------------
§5 ("Consolidated apply-time ratification") says the human signs ONCE, at apply
time, over a consolidated bundle:

    protocol + evidence hashes + validation results + exact state diff

No 2026-07 ratification emitted one. Each script verified *that its own edit had
arrived* — a grep for the marker it had just inserted — and called that
verification. That check is fail-open twice over:

  * it passes on a torn document. `ratify_measurement_amendment_20260731.sh`
    inserted a block between the two physical lines of a WRAPPED bullet in §3,
    stranding the continuation line 16 lines from its sentence. Its own
    `grep -qF category=OPTIMUM` passed, because the insertion HAD arrived. The
    tear was found by a human reading the file, and repaired by
    `artifacts/operator/repair_measurement_torn_bullet_20260731.sh`.
  * it is passable by DELETING what it inspects — rename the anchor, drop the
    evidence, and a presence check has nothing to say.

The self-referential part is the reason this is worth closing properly: these
scripts amend the document that DEFINES what a valid verification is, using a
verification weaker than that definition.

WHAT THE RECEIPT CARRIES
------------------------
  protocol_id        the §2 protocol the amendment governs
  evidence[]         every cited artifact, with sha256, size, and a DURABILITY
                     verdict from the research repo's
                     `scripts/validate/check_evidence_durability.py` (reused —
                     this file deliberately implements no second copy)
  validation[]       each validation command actually EXECUTED here, with its
                     exit code and output tail. Not a claim that it was run.
  state_diff[]       the exact before/after of every amended file: sha256 both
                     sides, line counts, and the full unified diff inline
  coherence[]        a POST-STATE structural check, not a presence check: every
                     multi-line markdown block that existed before must still be
                     contiguous after. This is the check that would have caught
                     the 2026-07-31 torn bullet.

THREE OUTCOMES, NOT TWO
-----------------------
The receipt reports PASS / FAIL / COULD-NOT-CHECK and exits non-zero on either
of the last two. A receipt that cannot evaluate one of its own sections says so
in the artifact the human signs; it never omits the section and reports clean.

USAGE (from a ratify script)
----------------------------
    R=scripts/operator/ratification_receipt.py

    # BEFORE touching anything — the pre-state is what makes the diff exact.
    python3 $R capture --state MEASUREMENT.md \
                       --state measurement/protocols/bench-cpu.md \
                       --out /tmp/pre.json

    ... apply the amendment ...

    python3 $R emit \
        --pre /tmp/pre.json \
        --protocol-id P-BENCH-PREFILL-1 \
        --ratification-id cpu-prefill-protocol-20260724 \
        --script artifacts/ratify_cpu_prefill_protocol_20260724.sh \
        --evidence data/cpu-prefill-20260724/samples.json \
        --validation 'scripts/validate/check_claims_grammar.sh MEASUREMENT.md' \
        --out artifacts/operator/receipts/cpu-prefill-protocol-20260724.receipt.json

Exit codes: 0 RATIFIED · 1 REFUSED (errors) · 2 COULD-NOT-CHECK.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

RECEIPT_VERSION = "1.0"
REPO_ROOT = Path("/workspace")
EVIDENCE_REPO = Path("/mnt/raid0/llm/epyc-inference-research")
DURABILITY_CHECKER = EVIDENCE_REPO / "scripts" / "validate" / "check_evidence_durability.py"
DEFAULT_RECEIPT_DIR = REPO_ROOT / "artifacts" / "operator" / "receipts"

PASS = "PASS"
FAIL = "FAIL"
COULD_NOT_CHECK = "COULD-NOT-CHECK"

BULLET_RE = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s)")


# --------------------------------------------------------------------------- util


def sha256_of(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


@dataclass
class Section:
    """One checked section of the receipt. Three outcomes, never two."""

    name: str
    verdict: str = PASS
    detail: list[str] = field(default_factory=list)
    data: object = None

    def fail(self, msg: str) -> None:
        self.verdict = FAIL
        self.detail.append(msg)

    def unknown(self, msg: str) -> None:
        # FAIL outranks COULD-NOT-CHECK: a known violation is not softened by an
        # unrelated blind spot.
        if self.verdict != FAIL:
            self.verdict = COULD_NOT_CHECK
        self.detail.append(f"{COULD_NOT_CHECK}: {msg}")


# ------------------------------------------------------------------ block parsing


def markdown_blocks(text: str) -> list[list[str]]:
    """Group a markdown document into blocks that must stay contiguous.

    A block is a bullet (or numbered item) together with its wrapped
    continuation lines, or a plain paragraph. Only multi-line blocks matter:
    those are the ones an insertion can tear in half, which is exactly what
    happened to `MEASUREMENT.md` §3 on 2026-07-31.
    """
    lines = text.split("\n")
    blocks: list[list[str]] = []
    current: list[str] = []
    in_code = False
    for line in lines:
        if line.lstrip().startswith("```"):
            in_code = not in_code
            if current:
                blocks.append(current)
                current = []
            continue
        if in_code:
            continue
        if not line.strip():
            if current:
                blocks.append(current)
                current = []
            continue
        if BULLET_RE.match(line):
            if current:
                blocks.append(current)
            current = [line]
            continue
        if line.startswith("#") or line.startswith("|"):
            if current:
                blocks.append(current)
                current = []
            continue
        if current:
            current.append(line)
        else:
            current = [line]
    if current:
        blocks.append(current)
    return blocks


def _contiguous(haystack: list[str], needle: list[str]) -> bool:
    n = len(needle)
    for i in range(len(haystack) - n + 1):
        if haystack[i : i + n] == needle:
            return True
    return False


def _line_to_block(blocks: list[list[str]]) -> dict[str, int]:
    """First-occurrence map from a line to the block that contains it."""
    index: dict[str, int] = {}
    for number, block in enumerate(blocks):
        for line in block:
            index.setdefault(line, number)
    return index


def check_block_coherence(
    before: str, after: str, allow_restructure: list[str] | None = None
) -> tuple[list[dict], list[dict], list[dict]]:
    """Post-state structural check: did the amendment tear anything in half?

    The failure mode this exists for is precise, so the test is too. Editing text
    INSIDE a block is ordinary amendment work and must not be flagged; what
    happened on 2026-07-31 is different in kind: a line survived VERBATIM but
    ended up in a DIFFERENT block from the one it belonged to, because an
    insertion landed between a bullet and its own wrapped continuation.

    So for each multi-line block in the before-state whose first line survives,
    every surviving continuation line must still live in the SAME after-block.
    An edit that rewrites the wrapped text keeps its survivors in one block and
    passes; an insertion that splits the block strands them elsewhere and fails.

    Deliberate restructuring (the 2026-07-31 REPAIR moved a line back across a
    block boundary, which is a real cross-block move) is declarable via
    `--allow-restructure`; the declaration is recorded in the receipt so the
    human signs over it rather than never seeing it.
    """
    allow = allow_restructure or []
    after_lines = after.split("\n")
    after_blocks = markdown_blocks(after)
    after_index = _line_to_block(after_blocks)
    torn: list[dict] = []
    replaced: list[dict] = []
    declared: list[dict] = []
    for block in markdown_blocks(before):
        if len(block) < 2 or _contiguous(after_lines, block):
            continue
        head = block[0]
        if head not in after_index:
            replaced.append({"first_line": head, "lines": len(block)})
            continue
        home = after_index[head]
        stranded = [
            line
            for line in block[1:]
            if line in after_index and after_index[line] != home
        ]
        if not stranded:
            continue  # rewritten in place; survivors stayed in their block
        record = {
            "first_line": head,
            "block_lines": len(block),
            "stranded_continuation": stranded,
            "detail": (
                "the block's first line survives but a continuation line that also "
                "survives verbatim now lives in a DIFFERENT block — an insertion "
                "landed inside a wrapped block"
            ),
        }
        if any(marker in head for marker in allow):
            record["declared_restructure"] = True
            declared.append(record)
        else:
            torn.append(record)
    return torn, replaced, declared


# ------------------------------------------------------------------- durability


def load_durability_checker(section: Section):
    """Import the research repo's durability validator. Never reimplement it."""
    if not DURABILITY_CHECKER.exists():
        section.unknown(
            f"evidence-durability validator not found at {DURABILITY_CHECKER}; "
            "MEASUREMENT.md §5 (2026-08-02) names it as the enforcer, so its absence "
            "means durability was NOT verified"
        )
        return None
    try:
        spec = importlib.util.spec_from_file_location(
            "check_evidence_durability", DURABILITY_CHECKER
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["check_evidence_durability"] = module
        spec.loader.exec_module(module)
        return module
    except Exception as exc:  # noqa: BLE001 — report, never skip silently
        section.unknown(
            f"evidence-durability validator did not import "
            f"({type(exc).__name__}: {exc}); durability was NOT verified"
        )
        return None


def evidence_records(
    citations: list[str], section: Section, evidence_repo: Path
) -> list[dict]:
    checker = load_durability_checker(section)
    records: list[dict] = []
    for raw in citations:
        cite, _, label = raw.partition("=")
        cite = cite.strip()
        path = Path(cite) if cite.startswith("/") else evidence_repo / cite
        record: dict = {
            "citation": cite,
            "label": label or None,
            "resolved": str(path),
            "exists": path.exists(),
            "sha256": sha256_of(path) if path.is_file() else None,
            "bytes": path.stat().st_size if path.is_file() else None,
            "durability": None,
        }
        if path.is_dir():
            # A campaign directory: hash its manifest if it has one, and record
            # the file count. A directory with no SHA256SUMS is not durable
            # evidence under the 2026-08-02 clause.
            sums = path / "SHA256SUMS"
            record["is_directory"] = True
            record["file_count"] = sum(1 for _ in path.rglob("*") if _.is_file())
            record["sha256sums"] = sha256_of(sums) if sums.exists() else None
            if not sums.exists():
                section.fail(
                    f"evidence directory {cite} has no SHA256SUMS; "
                    "MEASUREMENT.md §5 (2026-08-02) requires one"
                )
            if not (path / "README.md").exists():
                section.fail(
                    f"evidence directory {cite} has no README.md stating what was "
                    "measured, when, and which claim it backs"
                )
        elif not path.exists():
            section.fail(
                f"evidence {cite} does not exist at {path}; a hash over a missing "
                "artifact proves nothing — there is nothing left to check it against"
            )
        if checker is not None:
            try:
                citation = checker.Citation(
                    raw=raw, path=cite, line=0, lineref="ratification receipt", context=raw
                )
                classified = checker.classify(citation, evidence_repo)
                record["durability"] = {
                    "verdict": classified.verdict,
                    "severity": classified.severity,
                    "hint": classified.hint,
                }
                if classified.severity == "error":
                    section.fail(
                        f"evidence {cite}: {classified.verdict} — {classified.hint}"
                    )
            except Exception as exc:  # noqa: BLE001
                section.unknown(
                    f"durability classification failed for {cite} "
                    f"({type(exc).__name__}: {exc})"
                )
        records.append(record)
    return records


# ------------------------------------------------------------------- validations


def run_validations(commands: list[str], section: Section, cwd: Path) -> list[dict]:
    results: list[dict] = []
    for command in commands:
        entry: dict = {"command": command}
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=900,
            )
        except Exception as exc:  # noqa: BLE001
            entry.update({"outcome": COULD_NOT_CHECK, "error": f"{type(exc).__name__}: {exc}"})
            section.unknown(f"validation could not be executed: {command} ({exc})")
            results.append(entry)
            continue
        tail = (proc.stdout + proc.stderr).strip().split("\n")[-20:]
        entry.update(
            {
                "exit_code": proc.returncode,
                "outcome": PASS if proc.returncode == 0 else FAIL,
                "output_tail": tail,
            }
        )
        if proc.returncode != 0:
            section.fail(f"validation failed (exit {proc.returncode}): {command}")
        results.append(entry)
    return results


# --------------------------------------------------------------------- capture


def cmd_capture(args: argparse.Namespace) -> int:
    root = Path(args.repo_root)
    snapshot = {
        "captured_at_utc": _now(),
        "repo_root": str(root),
        "git_head": _git_head(root),
        "states": {},
    }
    missing = []
    for raw in args.state:
        path = (root / raw) if not raw.startswith("/") else Path(raw)
        rel = _rel(path, root)
        if not path.is_file():
            missing.append(rel)
            continue
        text = path.read_text(encoding="utf-8")
        snapshot["states"][rel] = {
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "lines": len(text.split("\n")),
            "bytes": len(text.encode("utf-8")),
            "content": text,
        }
    if missing:
        print(f"{COULD_NOT_CHECK}: cannot snapshot missing state file(s): {missing}", file=sys.stderr)
        return 2
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"captured pre-amendment state of {len(snapshot['states'])} file(s) -> {out}")
    return 0


def _git_head(root: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return proc.stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


# ------------------------------------------------------------------------ emit


def cmd_emit(args: argparse.Namespace) -> int:
    root = Path(args.repo_root)
    evidence_repo = Path(args.evidence_repo)

    sections: dict[str, Section] = {}

    def section(name: str) -> Section:
        return sections.setdefault(name, Section(name))

    # ---- pre-state -------------------------------------------------------
    diff_section = section("state_diff")
    pre_path = Path(args.pre)
    snapshot: dict = {}
    if not pre_path.is_file():
        diff_section.unknown(
            f"pre-amendment snapshot {pre_path} is missing, so NO exact state diff can be "
            "produced. MEASUREMENT.md §5 requires one; run `capture` before amending."
        )
    else:
        try:
            snapshot = json.loads(pre_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            diff_section.unknown(f"pre-amendment snapshot {pre_path} is unreadable: {exc}")

    state_diffs: list[dict] = []
    coherence_section = section("coherence")
    for rel, before_rec in sorted((snapshot.get("states") or {}).items()):
        path = root / rel
        before = before_rec.get("content")
        if not isinstance(before, str):
            diff_section.unknown(f"pre-state for {rel} carries no content; diff not exact")
            continue
        if not path.is_file():
            diff_section.fail(f"amended file {rel} no longer exists after the amendment")
            continue
        after = path.read_text(encoding="utf-8")
        before_lines = before.split("\n")
        after_lines = after.split("\n")
        unified = list(
            difflib.unified_diff(before_lines, after_lines, f"a/{rel}", f"b/{rel}", lineterm="")
        )
        added = sum(1 for l in unified if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in unified if l.startswith("-") and not l.startswith("---"))
        state_diffs.append(
            {
                "path": rel,
                "sha256_before": before_rec.get("sha256"),
                "sha256_after": hashlib.sha256(after.encode("utf-8")).hexdigest(),
                "lines_before": len(before_lines),
                "lines_after": len(after_lines),
                "lines_added": added,
                "lines_removed": removed,
                "unchanged": before == after,
                "unified_diff": unified,
            }
        )
        if rel.endswith(".md"):
            torn, replaced, declared = check_block_coherence(
                before, after, args.allow_restructure
            )
            coherence_section.detail.extend(
                f"{rel}: block replaced ({r['lines']} lines): {r['first_line'][:70]}"
                for r in replaced
            )
            coherence_section.detail.extend(
                f"{rel}: DECLARED restructure: {r['first_line'][:80]}" for r in declared
            )
            for t in torn:
                coherence_section.fail(
                    f"{rel}: TORN BLOCK — {t['detail']}: {t['first_line'][:90]!r}"
                )
            if coherence_section.data is None:
                coherence_section.data = {}
            coherence_section.data[rel] = {
                "torn": torn,
                "replaced": replaced,
                "declared_restructure": declared,
            }

    if snapshot and not state_diffs:
        diff_section.unknown("pre-state snapshot listed no files; nothing could be diffed")
    if state_diffs and all(d["unchanged"] for d in state_diffs):
        diff_section.fail(
            "no state file changed — a ratification that amends nothing is not a "
            "ratification; the amendment did not apply"
        )

    # ---- evidence --------------------------------------------------------
    evidence_section = section("evidence")
    if not args.evidence:
        if args.no_evidence_reason:
            evidence_section.detail.append(
                f"no evidence cited, declared reason: {args.no_evidence_reason}"
            )
        else:
            evidence_section.fail(
                "no evidence cited and no --no-evidence-reason given. An amendment with "
                "no evidence is a legitimate thing to ratify, but it must be SAID, not "
                "left as an empty section"
            )
    evidence = evidence_records(args.evidence or [], evidence_section, evidence_repo)

    # ---- validations -----------------------------------------------------
    validation_section = section("validation")
    if not args.validation:
        validation_section.unknown(
            "no validation command was given, so the amended artifact was not checked "
            "by anything except this receipt's own structural test"
        )
    validations = run_validations(args.validation or [], validation_section, root)

    # ---- protocol identity ----------------------------------------------
    # Anchors are a FLOOR, not the verification. "My marker arrived" is exactly
    # the check that passed on a torn document in 2026-07; it stays because a
    # ratification whose text did NOT land is still a failure worth naming, but
    # the weight is carried by the coherence and state_diff sections above.
    protocol_section = section("protocol")
    protocol_id = args.protocol_id
    constitution = root / "MEASUREMENT.md"
    if not constitution.is_file():
        protocol_section.unknown(f"{constitution} not readable; protocol id unverified")
    else:
        text = constitution.read_text(encoding="utf-8")
        anchors = list(args.anchor or [])
        if protocol_id in text:
            protocol_section.detail.append(f"protocol id {protocol_id} present in MEASUREMENT.md")
            if args.protocol_new:
                protocol_section.detail.append("declared NEW by this amendment")
        elif anchors:
            protocol_section.detail.append(
                f"protocol id {protocol_id} is a clause reference, not a registered "
                f"protocol name; verified via {len(anchors)} anchor(s) instead"
            )
        elif args.protocol_new:
            protocol_section.fail(
                f"protocol id {protocol_id} is declared new but does not appear in "
                "MEASUREMENT.md after the amendment — the amendment did not land"
            )
        else:
            protocol_section.fail(
                f"protocol id {protocol_id} does not appear in MEASUREMENT.md; pass "
                "--protocol-new if this amendment introduces it, or --anchor if the id "
                "is a clause reference"
            )
        for anchor in anchors:
            if anchor in text:
                protocol_section.detail.append(f"anchor present: {anchor[:70]}")
            else:
                protocol_section.fail(f"anchor NOT present after the amendment: {anchor[:90]}")

    script_record = None
    if args.script:
        script_path = (root / args.script) if not args.script.startswith("/") else Path(args.script)
        script_record = {
            "path": _rel(script_path, root),
            "sha256": sha256_of(script_path),
            "exists": script_path.is_file(),
        }
        if not script_path.is_file():
            section("protocol").fail(f"ratify script {args.script} does not exist")

    # ---- verdict ---------------------------------------------------------
    verdicts = {name: s.verdict for name, s in sections.items()}
    if FAIL in verdicts.values():
        overall = "REFUSED"
        exit_code = 1
    elif COULD_NOT_CHECK in verdicts.values():
        overall = COULD_NOT_CHECK
        exit_code = 2
    else:
        overall = "RATIFIED"
        exit_code = 0

    receipt = {
        "receipt_version": RECEIPT_VERSION,
        "verdict": overall,
        "ratification_id": args.ratification_id,
        "protocol_id": protocol_id,
        "supersedes": args.supersedes,
        "emitted_at_utc": _now(),
        "operator": args.operator or os.environ.get("RATIFY_OPERATOR") or os.environ.get("USER"),
        "repo_root": str(root),
        "git_head_before": snapshot.get("git_head"),
        "git_head_at_emit": _git_head(root),
        "ratify_script": script_record,
        "constitution_clause": (
            "MEASUREMENT.md §5 — Consolidated apply-time ratification: the human signs "
            "ONCE over protocol + evidence hashes + validation results + exact state diff; "
            "and §5 (2026-08-02) — evidence must be DURABLE, not merely hashed."
        ),
        "sections": {
            name: {"verdict": s.verdict, "detail": s.detail, "data": s.data}
            for name, s in sorted(sections.items())
        },
        "evidence": evidence,
        "evidence_durability_checker": {
            "path": str(DURABILITY_CHECKER),
            "sha256": sha256_of(DURABILITY_CHECKER),
        },
        "validation": validations,
        "state_diff": state_diffs,
    }

    out = Path(args.out) if args.out else (
        DEFAULT_RECEIPT_DIR / f"{args.ratification_id}.receipt.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    _render(receipt, out)
    return exit_code


def _render(receipt: dict, out: Path) -> None:
    print()
    print("=" * 78)
    print(f"RATIFICATION RECEIPT  —  {receipt['verdict']}")
    print("=" * 78)
    print(f"  ratification_id : {receipt['ratification_id']}")
    print(f"  protocol_id     : {receipt['protocol_id']}")
    print(f"  emitted         : {receipt['emitted_at_utc']}  operator={receipt['operator']}")
    print()
    for name, sec in receipt["sections"].items():
        print(f"  [{sec['verdict']:>15s}] {name}")
        for line in sec["detail"][:8]:
            print(f"                    - {line[:150]}")
    print()
    for ev in receipt["evidence"]:
        dur = (ev.get("durability") or {}).get("verdict", "?")
        digest = ev["sha256"] or ev.get("sha256sums") or "(no hash — nothing to check against)"
        suffix = " [SHA256SUMS]" if not ev["sha256"] and ev.get("sha256sums") else ""
        print(f"  evidence  {dur:<16s} {digest:<64s} {ev['citation']}{suffix}")
    for v in receipt["validation"]:
        print(f"  validation {str(v.get('outcome')):<15s} exit={v.get('exit_code')}  {v['command'][:90]}")
    for d in receipt["state_diff"]:
        print(
            f"  state     {d['path']:<44s} +{d['lines_added']}/-{d['lines_removed']}  "
            f"{(d['sha256_before'] or '')[:12]} -> {(d['sha256_after'] or '')[:12]}"
        )
    print()
    print(f"  receipt: {out}")
    print("=" * 78)


# ------------------------------------------------------------------------ main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    sub = parser.add_subparsers(dest="command", required=True)

    cap = sub.add_parser("capture", help="snapshot the pre-amendment state")
    cap.add_argument("--state", action="append", required=True)
    cap.add_argument("--out", required=True)
    cap.add_argument("--repo-root", default=str(REPO_ROOT))
    cap.set_defaults(func=cmd_capture)

    emit = sub.add_parser("emit", help="emit the consolidated receipt")
    emit.add_argument("--pre", required=True, help="snapshot written by `capture`")
    emit.add_argument("--protocol-id", required=True)
    emit.add_argument("--protocol-new", action="store_true")
    emit.add_argument(
        "--anchor",
        action="append",
        default=[],
        help="literal text that must be present in MEASUREMENT.md after the amendment; "
        "a FLOOR alongside the coherence and state-diff sections, never the verification",
    )
    emit.add_argument("--ratification-id", required=True)
    emit.add_argument("--supersedes", default=None)
    emit.add_argument("--script", default=None)
    emit.add_argument("--evidence", action="append", default=[])
    emit.add_argument("--no-evidence-reason", default=None)
    emit.add_argument(
        "--allow-restructure",
        action="append",
        default=[],
        help="substring of a block's first line whose cross-block restructuring is "
        "INTENDED; recorded verbatim in the receipt so the human signs over it",
    )
    emit.add_argument("--validation", action="append", default=[])
    emit.add_argument("--operator", default=None)
    emit.add_argument("--evidence-repo", default=str(EVIDENCE_REPO))
    emit.add_argument("--out", default=None)
    emit.add_argument("--repo-root", default=str(REPO_ROOT))
    emit.set_defaults(func=cmd_emit)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
