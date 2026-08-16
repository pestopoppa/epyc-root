#!/usr/bin/env python3
"""headless_audit.py — the P2-7 headless auditor: derive the truth, then read the claim.

Owning handoff: handoffs/active/loop-owned-fleet-implementation.md (P2-7)
Plan of record: docs/design/loop-owned-fleet.html  (red-team finding R12)
Contract:       coordination/session-bus/BUS_PROTOCOL.md (single writer)

WHY THIS FILE EXISTS AT ALL
---------------------------
`worker_runner.py` finishes a batch and emits an AUDIT PACKET containing
POINTERS ONLY — task ids, the lane worktree, a commit range, the path of the
report the worker wrote. It deliberately carries none of the worker's prose.

That asymmetry is the whole design. The project's failure ledger is full of the
F-01/F-02 instrument-error class: a REPORT was graded instead of the WORK, so a
run that never happened, or happened wrongly, passed review because its summary
was well written. R12 in the plan of record names the same shape for this
pipeline — "auditor circularity: grading the worker's own claim". An auditor
that reads only the worker's summary is a rubber stamp with a verdict enum.

So the order of operations here is inverted from the natural one:

  1. DERIVE the diff from git, in the pool worktree, over the packet's commit
     range. This is the truth. Nothing the worker wrote participates in it.
  2. Read the BRIEF (the runner's own dispatch — an input to the worker, not an
     output of it) for the task text.
  3. Run ONE MUTATION PROBE: name, from the task text, a file the diff SHOULD
     have touched, and prove the change is really in the tree — by reverse-
     applying its patch, which is exactly "would this fail if reverted?".
  4. ONLY THEN read the worker's report, and only to COMPARE its claims against
     what (1) already established. A claim that disagrees with the diff is a
     contradiction attributed to the worker, never a fact about the work.

THE PACKET CONTRACT IS ENFORCED HERE, FAIL-CLOSED
-------------------------------------------------
`parse_packet` refuses any key it does not recognise. That list is defined in
THIS file on purpose, rather than imported from the runner: the auditor's
authority over what it will accept as evidence must not be editable from the
side being audited. A packet that grows a `summary`, `notes` or `outcome` key is
refused as `blocked-evidence` naming the offending key — which is the correct
reaction to the defendant slipping a statement into the evidence bag.

WHAT THE MODEL IS AND IS NOT FOR
--------------------------------
The mechanical half computes a FLOOR. The LLM may only choose among the verdicts
at or below that floor — it can turn `accept` into `needs-rework`, never the
reverse, and it is not consulted at all once the mechanical half has proven a
defect. An unparseable, erroring or off-enum model answer is `blocked-evidence`,
never `accept`: fail-open on a reviewer is indistinguishable from no reviewer.

`--offline` runs the git-derived half alone. It returns `blocked-evidence`
rather than guessing at the half it did not run — EXCEPT when the mechanical
half already PROVED a defect (probe failed, or a claim contradicts the diff), in
which case it returns `needs-rework`, because a derived defect is evidence, not
a guess. Both cases are pinned by tests.

Verdicts: accept · accept-with-followups · needs-rework · blocked-evidence

Exit codes:
    0   accept / accept-with-followups
    2   needs-rework
    3   blocked-evidence (including every refusal of the packet itself)
    64  usage

Usage:
    headless_audit.py audit --packet /path/to/packet.json --offline
    headless_audit.py audit --packet - --emit --agent auditor      # from stdin
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.coordination import session_bus  # noqa: E402
from scripts.coordination.session_bus import (  # noqa: E402
    MSG_SCHEMA_VERSION,
    BusError,
    _append_jsonl,
    _read_jsonl,
    _require_roster_id,
    _utcnow_iso,
    get_bus_root,
    required_writer,
    validate_row,
)

AUDITOR_AGENT = "auditor"

ACCEPT = "accept"
ACCEPT_FOLLOWUPS = "accept-with-followups"
NEEDS_REWORK = "needs-rework"
BLOCKED_EVIDENCE = "blocked-evidence"
VERDICTS = (ACCEPT, ACCEPT_FOLLOWUPS, NEEDS_REWORK, BLOCKED_EVIDENCE)

# Ordered worst-to-best. `floor` semantics: the model may return a verdict no
# BETTER than the mechanical floor.
_SEVERITY = {BLOCKED_EVIDENCE: 0, NEEDS_REWORK: 1, ACCEPT_FOLLOWUPS: 2, ACCEPT: 3}

EX_NEEDS_REWORK = 2
EX_BLOCKED = 3
EX_USAGE = 64

# The packet keys this auditor will accept. DEFINED HERE, NOT IMPORTED — see the
# module docstring. Unknown key ⇒ refuse; this is the evidence bag, and only the
# reviewer says what may be in it.
ACCEPTED_PACKET_KEYS = frozenset({
    "task_ids", "worktree", "commit_range", "report_path", "brief_path",
    "transcript_path", "scrollback_path", "salvage_ref", "lane", "batch_id",
    "harness", "run_dir",
})

# Keys that would mean the runner had started shipping the worker's own account
# of itself. Named explicitly so the refusal message can say WHY, not just
# "unknown key".
CLAIM_SHAPED_KEYS = frozenset({
    "summary", "notes", "outcome", "outcomes", "report", "rows", "claims",
    "description", "result", "results", "self_assessment", "commits",
})

MAX_PATCH_CHARS = 60_000
MAX_BUNDLE_TASK_CHARS = 4_000

_PATH_TOKEN_RE = re.compile(r"[A-Za-z0-9_.@+\-/]*[A-Za-z0-9_)\]]")
_PATHY_RE = re.compile(
    r"^[A-Za-z0-9_.\-/]+\.(py|sh|md|json|yaml|yml|html|txt|toml|cfg|ini|sql|c|h|cpp|"
    r"hpp|js|ts|tsx|jsx|rs|go|css|jsonl|schema\.json)$")


class AuditError(RuntimeError):
    """Operator-facing refusal. Always resolves to `blocked-evidence`."""


# --------------------------------------------------------------------- git io


def _git(repo: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, timeout=120)
    if check and proc.returncode != 0:
        raise AuditError(f"git {' '.join(args)} failed in {repo}: "
                         f"{(proc.stderr or proc.stdout).strip()[:400]}")
    return proc.stdout


def _git_ok(repo: Path, *args: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, timeout=120).returncode == 0


# ------------------------------------------------------------------- packet


def parse_packet(raw: Any) -> dict:
    """Validate the pointer packet. Fail-closed on anything unrecognised.

    Three refusals, each with a reason that is about EVIDENCE, not tidiness:
      * a non-object packet is not a packet;
      * a claim-shaped key means the worker's account entered the evidence bag
        (R12 circularity), so the audit cannot be independent by construction;
      * an unknown key means this auditor does not know whether it is a pointer
        or a claim — and a reviewer that guesses is not a reviewer.
    """
    if not isinstance(raw, dict):
        raise AuditError(f"packet is {type(raw).__name__}, expected a JSON object of pointers")
    keys = set(raw)
    claimish = sorted(keys & CLAIM_SHAPED_KEYS)
    if claimish:
        raise AuditError(
            f"packet carries claim-shaped key(s) {claimish} — the audit packet is POINTERS "
            f"ONLY (P2-7/R12). Grading the worker's own account of its work is the failure "
            f"this auditor exists to prevent; refusing rather than reading it.")
    unknown = sorted(keys - ACCEPTED_PACKET_KEYS)
    if unknown:
        raise AuditError(
            f"packet carries unrecognised key(s) {unknown} — this auditor accepts only "
            f"{sorted(ACCEPTED_PACKET_KEYS)}. An unknown key cannot be classified as a "
            f"pointer, and unclassified evidence is not evidence.")
    worktree = raw.get("worktree")
    if not worktree:
        raise AuditError("packet has no `worktree` — there is nothing to derive a diff from")
    packet = {k: raw[k] for k in raw if raw[k] is not None}
    packet["worktree"] = str(worktree)
    return packet


def load_packet(source: str) -> dict:
    text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    try:
        return parse_packet(json.loads(text))
    except json.JSONDecodeError as exc:
        raise AuditError(f"packet is not valid JSON: {exc}") from exc


# ------------------------------------------------------- independent truth


def git_facts(worktree: Path, commit_range: Optional[str]) -> dict:
    """THE TRUTH. Computed from git alone; no worker output participates.

    `commit_range` is treated as untrusted input: a range that does not resolve,
    or that resolves outside this worktree's history, is a blocked audit rather
    than an empty diff. An empty diff and an unresolvable range must never render
    identically — that is the "vacuous pass" shape (empty input, key too wide).
    """
    facts: dict[str, Any] = {
        "worktree": str(worktree), "commit_range": commit_range,
        "resolved": False, "changed_paths": [], "numstat": [], "commits": [],
        "patch": "", "patch_truncated": False, "insertions": 0, "deletions": 0,
        "dirty_paths": [],
    }
    if not worktree.exists():
        raise AuditError(f"worktree {worktree} does not exist — nothing to audit")
    if not _git_ok(worktree, "rev-parse", "--git-dir"):
        raise AuditError(f"{worktree} is not a git worktree — the diff cannot be derived")
    if not commit_range:
        raise AuditError(
            "packet has no `commit_range` — the worker produced no commits, or the runner "
            "could not name them. Either way the diff cannot be derived independently.")

    if ".." in commit_range:
        base, head = commit_range.split("..", 1)
        base, head = base.strip(), (head.strip() or "HEAD")
    else:
        base, head = f"{commit_range}^", commit_range
    for ref, label in ((base, "base"), (head, "head")):
        if not _git_ok(worktree, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"):
            raise AuditError(f"commit range {commit_range!r}: {label} ref {ref!r} does not "
                             f"resolve in {worktree}")
    facts["base"] = _git(worktree, "rev-parse", base).strip()
    facts["head"] = _git(worktree, "rev-parse", head).strip()
    facts["resolved"] = True

    rng = f"{facts['base']}..{facts['head']}"
    facts["changed_paths"] = sorted(
        p for p in _git(worktree, "diff", "--no-renames", "--name-only", rng).splitlines()
        if p.strip())
    for line in _git(worktree, "diff", "--no-renames", "--numstat", rng).splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        add, dele, path = parts
        facts["numstat"].append({"path": path, "insertions": add, "deletions": dele})
        for key, raw in (("insertions", add), ("deletions", dele)):
            if raw.isdigit():
                facts[key] += int(raw)
    facts["commits"] = [
        {"sha": ln.split(" ", 1)[0], "subject": (ln.split(" ", 1) + [""])[1]}
        for ln in _git(worktree, "log", "--no-merges", "--format=%H %s", rng).splitlines()
        if ln.strip()
    ]
    patch = _git(worktree, "diff", "--no-renames", rng)
    facts["patch_truncated"] = len(patch) > MAX_PATCH_CHARS
    facts["patch"] = patch[:MAX_PATCH_CHARS]
    facts["dirty_paths"] = sorted(
        ln[3:].strip() for ln in _git(worktree, "status", "--porcelain").splitlines()
        if ln.strip())
    return facts


def load_brief(brief_path: Optional[str]) -> tuple[list[dict], Optional[str]]:
    """Task texts from the runner's own dispatch.

    The brief is an INPUT to the worker, authored by `worker_runner.py`. Reading
    it is not reading the worker's claim — it is reading the assignment the work
    is being measured against. Without it there is no "what should have changed",
    so the mutation probe has no target and the audit blocks.
    """
    if not brief_path:
        return [], "packet carries no `brief_path` — the task text is unavailable"
    path = Path(brief_path)
    if not path.exists():
        return [], f"brief {path} does not exist"
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], f"brief {path} is unreadable: {exc}"
    rows = obj.get("rows") if isinstance(obj, dict) else None
    if not isinstance(rows, list) or not rows:
        return [], f"brief {path} carries no rows"
    return [r for r in rows if isinstance(r, dict)], None


def load_claims(report_path: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
    """The worker's own account. Read LAST, used ONLY for comparison."""
    if not report_path:
        return None, "packet carries no `report_path`"
    path = Path(report_path)
    if not path.exists():
        return None, f"report {path} does not exist (the worker never wrote one)"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"report {path} is unreadable: {exc}"


# --------------------------------------------------- claims vs derived truth


def compare_claims(claims: Optional[dict], facts: dict) -> list[dict]:
    """Every way the report can disagree with the git-derived diff.

    Direction matters and is recorded: `claim` findings are the worker asserting
    something the diff does not support; `silence` findings are the diff
    containing work the report never mentions. Both are defects, and conflating
    them would hide which one happened.
    """
    findings: list[dict] = []
    if not isinstance(claims, dict):
        return findings
    changed = set(facts.get("changed_paths") or [])
    shas = {c["sha"] for c in facts.get("commits") or []}
    short = {s[:7] for s in shas}

    rows = claims.get("rows") if isinstance(claims.get("rows"), list) else []
    claimed_paths: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        task_id = str(row.get("task_id") or "?")
        for sha in row.get("commits") or []:
            s = str(sha).strip()
            if s and s not in shas and s[:7] not in short:
                findings.append({
                    "kind": "claim", "task_id": task_id, "detail":
                    f"report claims commit {s} for {task_id}, which is not in the derived "
                    f"range {facts.get('commit_range')}"})
        for art in row.get("artifacts") or []:
            a = str(art).strip().lstrip("./")
            if not a:
                continue
            claimed_paths.add(a)
            if _PATHY_RE.match(a) and not any(c == a or c.endswith("/" + a) for c in changed):
                findings.append({
                    "kind": "claim", "task_id": task_id, "detail":
                    f"report names artifact {a!r} for {task_id}, which the derived diff "
                    f"never touched"})
        if str(row.get("outcome") or "") in {"pass", "DONE_PASS"} and not changed:
            findings.append({
                "kind": "claim", "task_id": task_id, "detail":
                f"report marks {task_id} as passing, but the derived diff over "
                f"{facts.get('commit_range')} is EMPTY — a pass with no change is a claim "
                f"about work that left no trace"})

    unmentioned = sorted(
        c for c in changed
        if not any(c == p or c.endswith("/" + p) for p in claimed_paths))
    if unmentioned and rows:
        findings.append({
            "kind": "silence", "task_id": None, "detail":
            f"{len(unmentioned)} file(s) changed that the report lists as no row's artifact: "
            f"{', '.join(unmentioned[:8])}{' …' if len(unmentioned) > 8 else ''}"})
    return findings


# ---------------------------------------------------------- mutation probe


def candidate_paths(text: str) -> list[str]:
    """Path-like tokens in the task text, most-specific first.

    Deliberately conservative: a token must look like a real file (an extension
    this repo actually uses, or a slash-bearing path), because a probe aimed at
    a word is a probe that passes on nothing.
    """
    out: list[str] = []
    for raw in _PATH_TOKEN_RE.findall(text or ""):
        tok = raw.strip().strip("`'\"(),;:").lstrip("./")
        if not tok or len(tok) < 4:
            continue
        if _PATHY_RE.match(tok) or ("/" in tok and "." in tok.rsplit("/", 1)[-1]):
            if tok not in out:
                out.append(tok)
    out.sort(key=lambda t: (t.count("/") == 0, -len(t)))
    return out


def choose_probe_target(task_rows: list[dict], facts: dict,
                        worktree: Optional[Path] = None) -> dict:
    """Name ONE file the diff should have touched, and say where the name came from.

    The name comes from the TASK TEXT — the thing that was asked for — never from
    the diff and never from the report. Choosing the target from the diff would
    make the probe a tautology ("the diff touched a file the diff touched"), which
    is precisely the vacuity the anti-vacuity test exists to rule out.

    Returns {target, source_quote, task_id} or {target: None, reason: ...}.
    """
    for row in task_rows:
        text = str(row.get("task_text") or "")
        for cand in candidate_paths(text):
            quote = _quote_around(text, cand)
            return {"target": cand, "task_id": row.get("task_id"), "source_quote": quote,
                    "derived_from": "task_text"}
    return {"target": None, "task_id": (task_rows[0].get("task_id") if task_rows else None),
            "reason": "no file path is named in any task text, so no file can be asserted "
                      "as one the diff SHOULD have touched"}


def _quote_around(text: str, token: str, width: int = 120) -> str:
    idx = text.find(token)
    if idx < 0:
        return text[:width]
    start = max(0, idx - width // 2)
    return text[start:idx + len(token) + width // 2].strip()


def mutation_probe(worktree: Path, facts: dict, target: dict) -> dict:
    """ONE probe, three recorded checks. Concrete, and non-vacuous by construction.

    Given `target.target` — a file the TASK TEXT says should have changed:

      1. PRESENT   the NET diff over the range touches that exact path. Net, not
                   the commit log: a change made and then undone inside the range
                   names the file in `git log --name-only` while the range's
                   actual effect on it is nothing. A probe reading the log passes
                   there; this one fails, and a test pins exactly that case.
      2. NONEMPTY  the net patch for that path has content (a path reported
                   changed whose patch is empty is not evidence of a change).
      3. REVERTIBLE `git apply --reverse --check` succeeds against the worktree.
                   This is literally "would this fail if reverted": reverse-
                   applying is reverting, and the check succeeds only if the
                   post-image is actually present in the tree. A patch that
                   cannot be un-applied describes a change that is not there.

    All three must pass. Every check is recorded with its verdict so the probe is
    auditable rather than a boolean somebody has to trust.
    """
    record: dict[str, Any] = {"target": target.get("target"),
                              "task_id": target.get("task_id"),
                              "source_quote": target.get("source_quote"),
                              "derived_from": target.get("derived_from"),
                              "checks": [], "passed": False}
    if not target.get("target"):
        record["reason"] = target.get("reason", "no probe target could be derived")
        record["undetermined"] = True
        return record

    path = target["target"]
    changed = facts.get("changed_paths") or []
    match = next((c for c in changed if c == path or c.endswith("/" + path)), None)
    record["checks"].append({
        "check": "present", "expected": path, "actual": match,
        "passed": match is not None,
        "detail": (f"derived diff touches {match}" if match else
                   f"derived diff over {facts.get('commit_range')} does NOT touch {path}; "
                   f"it touched {changed[:8] or 'nothing'}")})
    if match is None:
        return record

    rng = f"{facts['base']}..{facts['head']}"
    patch = _git(worktree, "diff", "--no-renames", "--binary", rng, "--", match)
    record["checks"].append({
        "check": "nonempty-net-patch", "expected": f"non-empty net diff for {match}",
        "passed": bool(patch.strip()), "patch_bytes": len(patch),
        "detail": ("net patch is non-empty" if patch.strip() else
                   f"{match} appears in the range's commits but the NET diff for it is "
                   f"EMPTY — the change was made and then undone inside the range")})
    if not patch.strip():
        return record

    proc = subprocess.run(["git", "-C", str(worktree), "apply", "--reverse", "--check", "-"],
                          input=patch, capture_output=True, text=True, timeout=120)
    record["checks"].append({
        "check": "revertible", "expected": "reverse-apply of the net patch checks clean",
        "passed": proc.returncode == 0,
        "detail": ("the change is present in the worktree and would be undone by reverting "
                   "this patch" if proc.returncode == 0 else
                   f"reverse-apply FAILED ({(proc.stderr or '').strip()[:200]}) — the diff "
                   f"describes a change that is not actually present in the tree")})
    record["passed"] = all(c["passed"] for c in record["checks"])
    return record


# ---------------------------------------------------------- mechanical half


def mechanical_audit(packet: dict) -> dict:
    """Everything derivable without a model. Returns the evidence bundle + floor."""
    worktree = Path(packet["worktree"])
    bundle: dict[str, Any] = {"packet": packet, "blocked": [], "contradictions": []}
    try:
        facts = git_facts(worktree, packet.get("commit_range"))
    except AuditError as exc:
        bundle["blocked"].append(str(exc))
        bundle["facts"] = None
        bundle["probe"] = {"passed": False, "undetermined": True, "reason": str(exc)}
        bundle["floor"] = BLOCKED_EVIDENCE
        return bundle
    bundle["facts"] = facts

    task_rows, brief_err = load_brief(packet.get("brief_path"))
    bundle["task_rows"] = task_rows
    if brief_err:
        bundle["blocked"].append(brief_err)

    claims, claim_err = load_claims(packet.get("report_path"))
    bundle["claims"] = claims
    if claim_err:
        bundle["blocked"].append(claim_err)

    probe = mutation_probe(worktree, facts, choose_probe_target(task_rows, facts, worktree))
    bundle["probe"] = probe
    if probe.get("undetermined"):
        bundle["blocked"].append(
            f"mutation probe could not run: {probe.get('reason')}")

    bundle["contradictions"] = compare_claims(claims, facts)

    # Only a `claim` finding sets the floor. A `silence` finding — the diff
    # contains work the report never mentions — is a REPORTING defect, and
    # forcing rework over it would fail good work for a bad write-up. It stays
    # in the bundle for the model to weigh (and in the verdict, for the record),
    # which is where a follow-up belongs.
    hard = [c for c in bundle["contradictions"] if c["kind"] == "claim"]
    if not probe.get("undetermined") and not probe.get("passed"):
        bundle["floor"] = NEEDS_REWORK
    elif hard:
        bundle["floor"] = NEEDS_REWORK
    elif bundle["blocked"]:
        bundle["floor"] = BLOCKED_EVIDENCE
    else:
        bundle["floor"] = None       # open — a model may adjudicate
    return bundle


# -------------------------------------------------------------- the LLM half


class HarnessCLIClient:
    """The headless agent CLI on this host. `claude -p` is verified working.

    Deliberately NOT premise_screener's richer resolver: that one's HTTP tiers
    point at whatever small local model is serving, which is right for a
    one-bit forced choice and wrong for reading a patch. The auditor wants the
    strong model, and it is invoked once per completion, so the cost is bounded
    by the pool's own concurrency cap.
    """

    def __init__(self, exe: str = "claude", args: Optional[list[str]] = None):
        resolved = shutil.which(exe)
        if not resolved:
            raise AuditError(f"headless agent CLI {exe!r} is not on PATH")
        self.exe, self.args = resolved, list(args if args is not None else ["-p"])

    def __call__(self, prompt: str, *, timeout_s: float = 300.0) -> str:
        proc = subprocess.run([self.exe, *self.args], input=prompt,
                              capture_output=True, text=True, timeout=timeout_s)
        if proc.returncode != 0:
            raise AuditError(f"{self.exe} exited {proc.returncode}: "
                             f"{(proc.stderr or '')[:300]}")
        out = (proc.stdout or "").strip()
        if not out:
            raise AuditError(f"{self.exe} produced no output")
        return out


def build_bundle(mech: dict) -> dict:
    """The evidence handed to the model. Derived facts first, claims last and LABELLED."""
    facts = mech.get("facts") or {}
    return {
        "derived_truth": {
            "commit_range": facts.get("commit_range"),
            "base": facts.get("base"), "head": facts.get("head"),
            "commits": facts.get("commits"),
            "changed_paths": facts.get("changed_paths"),
            "numstat": facts.get("numstat"),
            "insertions": facts.get("insertions"), "deletions": facts.get("deletions"),
            "patch": facts.get("patch"), "patch_truncated": facts.get("patch_truncated"),
        },
        "assignment": [
            {"task_id": r.get("task_id"),
             "task_text": str(r.get("task_text") or "")[:MAX_BUNDLE_TASK_CHARS],
             "constraints": r.get("constraints")}
            for r in (mech.get("task_rows") or [])
        ],
        "mutation_probe": mech.get("probe"),
        "mechanical_contradictions": mech.get("contradictions"),
        "worker_claims_UNVERIFIED": mech.get("claims"),
    }


PROMPT_HEADER = """\
You are the headless auditor for a pool worker's completed batch. You are NOT
reading a summary and deciding whether it sounds right. The diff below was
derived from git independently of anything the worker said; the worker's own
report appears last, under `worker_claims_UNVERIFIED`, and exists ONLY so you can
compare its claims against the derived diff.

Decide whether the DERIVED DIFF actually does what the ASSIGNMENT asked for.

Answer with ONE JSON object and nothing else:

  {"verdict": "accept" | "accept-with-followups" | "needs-rework",
   "rationale": "<= 400 chars, citing the diff, not the report",
   "followups": ["..."],
   "claim_check": "<= 300 chars: where the report and the diff agree or differ"}

Rules:
  * "accept" only if the diff satisfies the assignment as written.
  * "accept-with-followups" if it satisfies it but leaves named, concrete
    follow-up work; list them.
  * "needs-rework" if the diff does not do what was asked, or contradicts the
    report in a way that matters.
  * A claim in the report that the diff does not support is never evidence FOR
    the work. Cite the diff.

EVIDENCE:
"""


def llm_adjudicate(bundle: dict, client: Optional[Callable[..., str]] = None,
                   *, timeout_s: float = 300.0) -> dict:
    """The ONE model call. Everything it sees is in `bundle`.

    Returns {verdict, rationale, followups, claim_check, raw}. Any failure —
    exception, timeout, unparseable output, off-enum verdict — becomes
    `blocked-evidence`. There is no path from a broken model to `accept`.
    """
    if client is None:
        client = HarnessCLIClient()
    prompt = PROMPT_HEADER + json.dumps(bundle, indent=2, default=str)
    try:
        raw = client(prompt, timeout_s=timeout_s)
    except Exception as exc:  # noqa: BLE001 — every failure is one verdict
        return {"verdict": BLOCKED_EVIDENCE,
                "rationale": f"model call failed: {type(exc).__name__}: {exc}",
                "followups": [], "claim_check": "", "raw": None}
    obj = _extract_json(raw)
    if obj is None:
        return {"verdict": BLOCKED_EVIDENCE,
                "rationale": "model output contained no parseable JSON object",
                "followups": [], "claim_check": "", "raw": raw[:1000]}
    verdict = obj.get("verdict")
    if verdict not in (ACCEPT, ACCEPT_FOLLOWUPS, NEEDS_REWORK):
        return {"verdict": BLOCKED_EVIDENCE,
                "rationale": f"model returned off-enum verdict {verdict!r}; a reviewer that "
                             f"guesses at its own verdict is not a reviewer",
                "followups": [], "claim_check": "", "raw": raw[:1000]}
    followups = obj.get("followups")
    followups = [str(f) for f in followups] if isinstance(followups, list) else []
    if verdict == ACCEPT_FOLLOWUPS and not followups:
        return {"verdict": BLOCKED_EVIDENCE,
                "rationale": "model chose accept-with-followups but named no follow-up; an "
                             "unnamed follow-up is an accept wearing a hedge",
                "followups": [], "claim_check": "", "raw": raw[:1000]}
    return {"verdict": verdict, "rationale": str(obj.get("rationale") or "")[:400],
            "followups": followups, "claim_check": str(obj.get("claim_check") or "")[:300],
            "raw": None}


def _extract_json(text: str) -> Optional[dict]:
    depth, start = 0, None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    obj = json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    start = None
                    continue
                if isinstance(obj, dict) and "verdict" in obj:
                    return obj
                start = None
    return None


# ------------------------------------------------------------------ verdict


def audit(packet: dict, *, offline: bool = False,
          client: Optional[Callable[..., str]] = None,
          timeout_s: float = 300.0) -> dict:
    """The whole audit. Mechanical floor first; the model may only lower it."""
    mech = mechanical_audit(packet)
    floor = mech["floor"]
    result: dict[str, Any] = {
        "schema_version": "audit_verdict.v1",
        "ts": _utcnow_iso(),
        "batch_id": packet.get("batch_id"),
        "task_ids": packet.get("task_ids"),
        "worktree": packet.get("worktree"),
        "commit_range": packet.get("commit_range"),
        "mechanical_floor": floor,
        "blocked_reasons": mech["blocked"],
        "contradictions": mech["contradictions"],
        "mutation_probe": mech["probe"],
        "derived": {k: (mech["facts"] or {}).get(k) for k in
                    ("base", "head", "changed_paths", "insertions", "deletions", "commits")},
        "llm": None,
        "offline": bool(offline),
    }

    if floor in (BLOCKED_EVIDENCE, NEEDS_REWORK):
        result["verdict"] = floor
        result["rationale"] = _floor_rationale(floor, mech)
        return result

    if offline:
        # The mechanical half found nothing wrong — but "nothing wrong
        # mechanically" is not "the diff does what was asked", and that second
        # question is exactly the half offline mode did not run.
        result["verdict"] = BLOCKED_EVIDENCE
        result["rationale"] = (
            "offline: the git-derived half found no defect (mutation probe passed, no "
            "claim/diff contradiction), but whether the diff SATISFIES the assignment was "
            "not adjudicated. Refusing to guess.")
        return result

    llm = llm_adjudicate(build_bundle(mech), client=client, timeout_s=timeout_s)
    result["llm"] = llm
    result["verdict"] = llm["verdict"]
    result["rationale"] = llm["rationale"]
    result["followups"] = llm["followups"]
    return result


def _floor_rationale(floor: str, mech: dict) -> str:
    if floor == NEEDS_REWORK:
        probe = mech["probe"]
        if not probe.get("passed") and not probe.get("undetermined"):
            failed = [c for c in probe.get("checks") or [] if not c["passed"]]
            detail = failed[0]["detail"] if failed else "probe failed"
            return (f"mutation probe FAILED on {probe.get('target')!r} "
                    f"(named by the task text): {detail}")
        hard = [c for c in mech["contradictions"] if c["kind"] == "claim"]
        return ("the worker's report contradicts the git-derived diff: "
                + "; ".join(c["detail"] for c in hard[:3]))
    return "; ".join(mech["blocked"]) or "evidence could not be derived"


# --------------------------------------------------------------- bus write


def emit_verdict(bus_root: Path, agent: str, result: dict,
                 to: str = "coordinator-agent") -> dict:
    """Append the typed verdict to the AUDITOR's OWN outbox. Single writer, checked.

    `required_writer()` is consulted rather than assumed: this module must be
    incapable of writing another agent's file even by a caller's mistake, which
    is invariant 1 and the one violation that revokes the pool's authority
    outright. `queue.jsonl` is never touched — a verdict is PROPOSED here and
    transcribed by the coordinator-daemon.
    """
    path = bus_root / "outbox" / f"{agent}.jsonl"
    writer = required_writer(bus_root, path)
    if writer != agent:
        raise AuditError(f"single-writer violation: {agent!r} may not write {path} "
                         f"(that file belongs to {writer!r})")
    _require_roster_id(bus_root, agent)

    verdict = result["verdict"]
    actionable = verdict in (NEEDS_REWORK, BLOCKED_EVIDENCE)
    existing, _ = _read_jsonl(path)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    row: dict[str, Any] = {
        "schema_version": MSG_SCHEMA_VERSION,
        "id": f"msg-{stamp}-{len(existing) + 1}-{agent}",
        "ts": _utcnow_iso(),
        "from": agent,
        "to": to,
        "kind": "finding",
        "task_id": str(result.get("batch_id") or (result.get("task_ids") or ["unknown"])[0]),
        "payload": {
            "audit_verdict": verdict,
            "mechanical_floor": result.get("mechanical_floor"),
            "rationale": str(result.get("rationale") or "")[:800],
            "mutation_probe": result.get("mutation_probe"),
            "contradictions": result.get("contradictions"),
            "blocked_reasons": result.get("blocked_reasons"),
            "commit_range": result.get("commit_range"),
            "worktree": result.get("worktree"),
            "task_ids": result.get("task_ids"),
            "followups": result.get("followups") or [],
            "derived_independently": True,
            "note": ("verdict derived from the git diff and one mutation probe; the worker's "
                     "report was read only to compare its claims against that diff (P2-7/R12)"),
        },
    }
    if actionable:
        row["needs_routing_to"] = [to]
        row["assignee"] = to
        row["action_required"] = True
    validate_row(bus_root, row, "msg")
    session_bus._check_routing_intent(bus_root, row)
    _append_jsonl(path, row)
    return row


# ------------------------------------------------------------------- CLI


def cmd_audit(args: argparse.Namespace) -> int:
    try:
        packet = load_packet(args.packet)
        result = audit(packet, offline=args.offline, timeout_s=args.timeout_s)
    except AuditError as exc:
        result = {"schema_version": "audit_verdict.v1", "ts": _utcnow_iso(),
                  "verdict": BLOCKED_EVIDENCE, "rationale": str(exc),
                  "mechanical_floor": BLOCKED_EVIDENCE, "blocked_reasons": [str(exc)],
                  "mutation_probe": None, "contradictions": [], "derived": {},
                  "offline": bool(args.offline)}
        packet = {}

    if args.emit:
        try:
            emit_verdict(Path(args.bus_root), args.agent, result)
            result["emitted"] = True
        except (AuditError, BusError) as exc:
            result["emitted"] = False
            result["emit_error"] = str(exc)
            print(f"headless_audit: WARN could not emit verdict: {exc}", file=sys.stderr)

    print(json.dumps(result, indent=2, default=str))
    if result["verdict"] == BLOCKED_EVIDENCE:
        return EX_BLOCKED
    if result["verdict"] == NEEDS_REWORK:
        return EX_NEEDS_REWORK
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="headless_audit.py",
                                description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit", help="audit one pointer packet")
    a.add_argument("--packet", required=True,
                   help="path to the audit packet JSON, or '-' for stdin")
    a.add_argument("--offline", action="store_true",
                   help="git-derived half only; blocked-evidence rather than a guess")
    a.add_argument("--emit", action="store_true",
                   help="append the verdict to the auditor's own bus outbox")
    a.add_argument("--bus-root", default=str(get_bus_root()))
    a.add_argument("--agent", default=AUDITOR_AGENT)
    a.add_argument("--timeout-s", type=float, default=300.0)
    a.set_defaults(func=cmd_audit)
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
