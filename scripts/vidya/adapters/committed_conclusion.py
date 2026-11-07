"""Read the committed-conclusion register (VB-CC-1 / VB-CC-PILOT).

Design: `docs/design/committed-conclusions-belief-capture-2026-10-25.md` §2.

The native record is a row of `data/belief/committed_conclusions.jsonl`, schema
`epyc.vidya.committed_conclusion.v1`: one concluded experiment as it was COMMITTED (a ticked
handoff item or a progress line), anchored by commit + path + line-at-commit + verbatim quote +
`quote_sha256`. The adapter never parses prose: it re-reads `git show <commit_concluded>:<path>`
lines `line_start..line_end`, refuses the register unless the bytes re-hash to `quote_sha256`, and
projects the row's curator-confirmed `stated` metrics.

No measurement warrant is invented (spec §4.7). `protocol_id` is always "" and `reps` always None,
so `claim_tuple.grade()` gives every tuple `Judged/Located`; a row that tries to carry a protocol or
a rep count is REFUSED. `applicability.run_id` is never set (loop_beliefs would supersede all but
the newest run). `kind == "decision"` rows and rows with `covered_by` set are recorded and
declined (0 frames). No new ladder, no grading rule: the adapter projects, `grade()` decides.

Pilot extension (2026-11-06, VB-CC-PILOT): an optional `facet` (e.g. a model label) joins the
identity hash, so one committed item that concludes separately per model yields one row per
model: `cc_id = H(basename \\0 head_norm [\\0 facet])` (no facet = the design identity exactly).
A per-metric `outcome` may be curator-recorded; it is sign-checked against the stated effect.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import (APPLICABILITY_KEYS, CATEGORIES, OBSERVATION_OUTCOMES,  # noqa: E402
                         ClaimTuple, ProjectionError, register)

ADAPTER_ID = "vidya.adapters.committed_conclusion/v1"
AUTHORITY = "measurement"
SCHEMA = "epyc.vidya.committed_conclusion.v1"
SOURCE_KIND = "committed-conclusion"
REGISTER_REL = "data/belief/committed_conclusions.jsonl"
REPO = Path(__file__).resolve().parents[3]
NORM_RULE = "cc-norm/v1"

_TOP_KEYS = frozenset({
    "schema", "cc_id", "rev", "kind", "facet", "anchor", "also_anchored", "task_id", "stated",
    "scope", "scope_evidence", "category", "metric_direction", "raw_evidence", "covered_by",
    "supersedes", "confirmed_by", "retrofit", "mechanism"})
_REQUIRED = ("schema", "cc_id", "rev", "kind", "anchor", "stated", "scope", "category",
             "metric_direction", "confirmed_by")
_ANCHOR_KEYS = ("repo", "commit_introduced", "commit_concluded", "commit_date", "path",
                "line_start", "line_end", "quote", "quote_sha256", "head_norm", "quote_norm_rule")
_STATED_KEYS = frozenset({"verdict_native", "metrics", "n", "protocol_named", "date"})
_METRIC_KEYS = frozenset({"metric", "value", "unit", "effect_rel", "arm", "outcome",
                          "anchor_value"})
_FORBIDDEN = ("protocol_id", "reps", "reps_basis", "run_id")
_HEX40 = re.compile(r"[0-9a-f]{40}")
_CHECKBOX = re.compile(r"^\s*[-*] \[[ xX]\]")
_BULLET = re.compile(r"^(\s*)([-*]|\d+\.|\|)")
# cc-norm/v1: belief markers, ✅ dates and the artifact-lost / repointed suffixes never change identity
_NORM_STRIP = (
    re.compile(r"\[(?:no-)?belief:[^\]]*\]"),
    re.compile(r"✅\s*\d{4}-\d{2}-\d{2}"),
    re.compile(r"\s*(?:ARTIFACT LOST|REPOINTED)\b.*$", re.S),
)
# §2.4, the closed verdict-to-outcome table (applied mechanically; decision tokens map to nothing)
_IMPROVED = ("KEEP", "IMPROVED", "WIN")
_NULL = ("NULL", "INCONCLUSIVE", "DOES NOT REPLICATE", "WITHIN NOISE")
_REGRESSED = ("REGRESSED", "REGRESSION", "LOSS")


# ------------------------------------------------------------------ identity

def cc_norm(text: str) -> str:
    out = str(text or "")
    for pattern in _NORM_STRIP:
        out = pattern.sub("", out)
    return " ".join(out.split())


def head_norm(first_line: str) -> str:
    return cc_norm(first_line)[:200]


def cc_id(path: str, head: str, facet: str = "") -> str:
    key = PurePosixPath(path).name + "\0" + head + (("\0" + facet) if facet else "")
    return "cc:v1:" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


def quote_sha(quote: str) -> str:
    return hashlib.sha256(quote.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ git anchoring

def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo or REPO), *args], capture_output=True, timeout=120)
    if r.returncode != 0:
        raise ProjectionError(f"git {' '.join(args[:2])} failed: {r.stderr.decode()[:200]}")
    return r.stdout.decode("utf-8", "replace")


def blob_lines(repo: Path, commit: str, path: str) -> list[str]:
    return _git(repo, "show", f"{commit}:{path}").split("\n")


def item_extent(lines: list[str], line: int) -> tuple[int, int]:
    """1-based (start, end) of the item at `line`: the checkbox/bullet line plus its more-indented
    continuation lines, stopping at the next checkbox or a line at the same or lower indent."""
    idx = line - 1
    if not 0 <= idx < len(lines) or not lines[idx].strip():
        raise ProjectionError(f"line {line} is empty or out of range")
    m = _BULLET.match(lines[idx])
    if not m or lines[idx].lstrip().startswith("|"):
        return line, line
    indent = len(m.group(1))
    end = idx
    for j in range(idx + 1, len(lines)):
        text = lines[j]
        if not text.strip() or _CHECKBOX.match(text):
            break
        if len(text) - len(text.lstrip()) <= indent:
            break
        end = j
    return line, end + 1


def resolve_anchor(path: str, line: int, *, ref: str = "origin/main",
                   repo: Path | None = None) -> dict[str, Any]:
    """Anchor for the item at `ref:path:line`: the first commit (walking forward from the one that
    introduced the item head, never `git blame`) whose blob already holds the item verbatim."""
    lines = blob_lines(repo, ref, path)
    start, end = item_extent(lines, line)
    quote = "\n".join(lines[start - 1:end])
    head = lines[start - 1]
    # the item head without its checkbox state, ✅ date or belief marker: the text that was there
    # when the item was FILED (design §2.2: commit_introduced, never blame)
    probe = re.split(r"✅|\[(?:no-)?belief:", re.sub(r"^\s*[-*] \[[ xX]\]\s*", "", head))[0]
    probe = probe.strip()[:60] or head.strip()[:60]
    intro = _git(repo, "log", "--reverse", "--format=%H", f"-S{probe}", ref, "--", path).split()
    if not intro:
        raise ProjectionError(f"no commit introduces {probe!r} in {path}")
    first = intro[0]
    parents = _git(repo, "rev-list", "--parents", "-n1", first).split()
    rng = [f"{first}^..{ref}"] if len(parents) > 1 else [ref]
    concluded = None
    for commit in _git(repo, "rev-list", "--reverse", *rng, "--", path).split():
        blob = blob_lines(repo, commit, path)
        text = "\n".join(blob)
        if quote in text:
            concluded = commit
            pos = text.index(quote)
            c_start = text[:pos].count("\n") + 1
            break
    if concluded is None:
        raise ProjectionError(f"{path}:{line} quote not found in history of {ref}")
    last = _git(repo, "log", "-1", "--format=%H", ref, "--", path).strip()
    date = _git(repo, "show", "-s", "--format=%cI", concluded).strip()
    return {"repo": "epyc-root", "commit_introduced": first, "commit_concluded": concluded,
            "commit_last_touched": last, "commit_date": _utc(date), "path": path,
            "line_start": c_start, "line_end": c_start + (end - start), "quote": quote,
            "quote_sha256": quote_sha(quote), "head_norm": head_norm(head),
            "quote_norm_rule": NORM_RULE}


def resolve_also(path: str, line: int, *, ref: str = "origin/main", repo: Path | None = None) -> dict:
    anchor = resolve_anchor(path, line, ref=ref, repo=repo)
    return {"repo": "epyc-root", "commit": anchor["commit_concluded"], "path": path,
            "line": anchor["line_start"], "line_end": anchor["line_end"],
            "quote_sha256": anchor["quote_sha256"]}


def _utc(iso: str) -> str:
    from datetime import datetime, timezone  # noqa: PLC0415
    return datetime.fromisoformat(iso).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def audit_quote(anchor: dict, repo: Path | None = None) -> None:
    lines = blob_lines(repo, anchor["commit_concluded"], anchor["path"])
    got = "\n".join(lines[anchor["line_start"] - 1:anchor["line_end"]])
    if got != anchor["quote"] or quote_sha(got) != anchor["quote_sha256"]:
        raise ProjectionError(
            f"quote audit failed: {anchor['commit_concluded'][:9]}:{anchor['path']}"
            f"#L{anchor['line_start']} does not re-hash to quote_sha256")


def audit_also(also: dict, repo: Path | None = None) -> None:
    lines = blob_lines(repo, also["commit"], also["path"])
    got = "\n".join(lines[also["line"] - 1:also.get("line_end", also["line"])])
    if quote_sha(got) != also["quote_sha256"]:
        raise ProjectionError(f"also_anchored audit failed: {also['path']}#L{also['line']}")


# ------------------------------------------------------------------ row checks

def _forbid(obj: Any, where: str) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in _FORBIDDEN:
                raise ProjectionError(
                    f"{where} sets {key!r}: a committed conclusion carries no protocol, rep "
                    "count or run identity (no invented measurement warrant)")
            _forbid(value, where)
    elif isinstance(obj, list):
        for value in obj:
            _forbid(value, where)


def _effect(metric: dict) -> float | None:
    if isinstance(metric.get("effect_rel"), (int, float)):
        return float(metric["effect_rel"])
    if metric.get("unit") == "x" and isinstance(metric.get("value"), (int, float)):
        return float(metric["value"]) - 1.0
    return None


def outcome_for(verdict: str | None, metric: dict | None) -> str | None:
    """§2.4 mechanically; a curator-recorded per-metric outcome wins, sign-checked."""
    effect = _effect(metric) if metric else None
    curated = (metric or {}).get("outcome")
    if curated is not None:
        if curated not in OBSERVATION_OUTCOMES:
            raise ProjectionError(f"unknown outcome {curated!r}")
        if curated == "improved" and not (effect is not None and effect > 0):
            raise ProjectionError("outcome improved needs a positive stated effect")
        if curated == "regressed" and not (effect is not None and effect < 0):
            raise ProjectionError("outcome regressed needs a negative stated effect")
        return curated
    token = str(verdict or "").upper()
    if any(t in token for t in _NULL):
        return "null"
    if any(re.search(rf"\b{t}\b", token) for t in _IMPROVED):
        return "improved" if effect is not None and effect > 0 else None
    if any(re.search(rf"\b{t}\b", token) for t in _REGRESSED):
        return "regressed" if effect is not None and effect < 0 else None
    return None


def check_row(row: Any, *, repo: Path | None = None, audit: bool = True) -> dict:
    if not isinstance(row, dict) or row.get("schema") != SCHEMA:
        raise ProjectionError("register row is not epyc.vidya.committed_conclusion.v1")
    unknown = set(row) - _TOP_KEYS
    if unknown:
        raise ProjectionError(f"register row has unknown fields {sorted(unknown)}")
    missing = [k for k in _REQUIRED if k not in row]
    if missing:
        raise ProjectionError(f"register row lacks {missing}")
    _forbid(row, row.get("cc_id", "row"))
    anchor = row["anchor"]
    if not isinstance(anchor, dict) or any(k not in anchor for k in _ANCHOR_KEYS):
        raise ProjectionError("anchor lacks required fields")
    for key in ("commit_introduced", "commit_concluded"):
        if not _HEX40.fullmatch(str(anchor[key])):
            raise ProjectionError(f"anchor.{key} is not a 40-hex commit")
    if anchor["quote_norm_rule"] != NORM_RULE:
        raise ProjectionError("unknown quote_norm_rule")
    first = anchor["quote"].split("\n", 1)[0]
    if head_norm(first) != anchor["head_norm"]:
        raise ProjectionError("head_norm does not re-derive from the quote")
    if cc_id(anchor["path"], anchor["head_norm"], row.get("facet") or "") != row["cc_id"]:
        raise ProjectionError(f"cc_id {row['cc_id']} does not re-derive from its anchor")
    if type(row["rev"]) is not int or row["rev"] < 1:
        raise ProjectionError("rev must be a positive integer")
    if row["kind"] not in ("result", "decision"):
        raise ProjectionError("kind must be result or decision")
    if row["category"] not in CATEGORIES:
        raise ProjectionError(f"unknown category {row['category']!r}")
    if row["metric_direction"] not in ("higher_better", "lower_better"):
        raise ProjectionError("metric_direction must be higher_better or lower_better")
    stated = row["stated"]
    if not isinstance(stated, dict) or set(stated) - _STATED_KEYS:
        raise ProjectionError("stated carries unknown fields")
    for k, metric in enumerate(stated.get("metrics") or []):
        if not isinstance(metric, dict) or set(metric) - _METRIC_KEYS or "metric" not in metric:
            raise ProjectionError(f"stated.metrics[{k}] malformed")
        value = metric.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ProjectionError(f"stated.metrics[{k}].value is not a finite number")
        outcome_for(stated.get("verdict_native"), metric)
    scope = row["scope"]
    if not isinstance(scope, dict) or set(scope) - (APPLICABILITY_KEYS - {"run_id",
                                                                         "run_expected_keys"}):
        raise ProjectionError("scope carries keys outside the applicability vocabulary")
    if row.get("mechanism") is not None and not (
            isinstance(row["mechanism"], dict) and row["mechanism"].get("id")):
        raise ProjectionError("mechanism must be a mapping with an id")
    if audit:
        audit_quote(anchor, repo)
        for also in row.get("also_anchored") or []:
            audit_also(also, repo)
    return row


def read_register(path: Path) -> list[dict]:
    rows = []
    for n, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            rows.append(json.loads(raw))
        except ValueError as exc:
            raise ProjectionError(f"register line {n} is not JSON: {exc}") from exc
    return rows


# ------------------------------------------------------------------ projection

def native_rows(path: str | Path, *, repo: Path | None = None) -> list[dict]:
    """One native per (projected row, stated metric). The whole register is refused on any bad
    row: the register is curated and committed, so a defect is fixed at the source."""
    rows = read_register(Path(path))
    seen: set[tuple[str, int]] = set()
    out: list[dict] = []
    superseded = {r["supersedes"] for r in rows if r.get("supersedes")}
    for row in rows:
        check_row(row, repo=repo)
        key = (row["cc_id"], row["rev"])
        if key in seen:
            raise ProjectionError(f"register duplicates {row['cc_id']} r{row['rev']}")
        seen.add(key)
        if row["kind"] == "decision" or row.get("covered_by"):
            continue  # recorded, never projected (intent plane / native frames exist)
        if f"{row['cc_id']}:{row['rev']}" in superseded:
            continue  # replaced by a corrected rev (supersedes = "cc_id:rev"); kept as history
        metrics = row["stated"].get("metrics") or []
        for k in range(max(1, len(metrics))):
            out.append({"row": row, "k": k})
    return out


def declined(path: str | Path) -> list[dict]:
    """Rows recorded but not projected, with the reason (report surface)."""
    return [{"cc_id": r["cc_id"], "reason": "decision" if r["kind"] == "decision" else
             "covered_by"} for r in read_register(Path(path))
            if r.get("kind") == "decision" or r.get("covered_by")]


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or set(native) != {"row", "k"}:
        raise ProjectionError("committed-conclusion native malformed")
    row, k = native["row"], native["k"]
    _forbid(row, row.get("cc_id", "row"))
    anchor, stated = row["anchor"], row["stated"]
    metrics = stated.get("metrics") or []
    metric = metrics[k] if metrics else None
    verdict = stated.get("verdict_native")
    sha7 = anchor["commit_concluded"][:7]
    where = f"{sha7} {anchor['path']}:{anchor['line_start']}"
    label = f" [{row['facet']}]" if row.get("facet") else ""
    if metric:
        arm = f" ({metric['arm']})" if metric.get("arm") else ""
        what = f"{metric['metric']}={metric['value']}{metric.get('unit') or ''}{arm}; "
    else:
        what = ""
    text = (f"Committed conclusion ({where}){label}: {what}"
            f"{verdict + ' -- ' if verdict else ''}{cc_norm(anchor['quote'])}")
    raw = row.get("raw_evidence") or {}
    if raw.get("status") == "lost":
        text += f" [raw artifact lost: {raw.get('event', 'unknown')}]"
    observation: dict[str, Any] = {}
    if metric is not None:
        observation["retrofit"] = bool(row.get("retrofit"))
        if verdict:
            observation["outcome_native"] = str(verdict)[:120]
        outcome = outcome_for(verdict, metric)
        if outcome:
            observation["outcome"] = outcome
        if isinstance(metric.get("effect_rel"), (int, float)):
            observation["effect_rel"] = float(metric["effect_rel"])
        if isinstance(metric.get("anchor_value"), (int, float)):
            observation["anchor_value"] = float(metric["anchor_value"])
        observation["outcome_reason"] = cc_norm(anchor["quote"])[:300] or "committed conclusion"
        if row.get("mechanism"):
            observation["mechanism"] = {key: str(v)[:240 if key != "id" else 200]
                                        for key, v in row["mechanism"].items()
                                        if key in ("id", "statement", "falsifier") and v}
    applicability = dict(row["scope"])
    if applicability:
        applicability["scope_basis"] = "native"
    try:
        return ClaimTuple(
            measurement_id=f"{row['cc_id']}:r{row['rev']}#m{k}",
            metric=metric["metric"] if metric else "stated_conclusion",
            value=metric["value"] if metric else (verdict or "stated"),
            unit=(metric.get("unit") or "") if metric else "",
            date=anchor["commit_date"],
            category=row["category"],
            claim=text,
            metric_direction=row["metric_direction"] if metric else "higher_better",
            protocol_id="",
            reps=None,
            attestation_path=anchor["path"],
            attestation_locator=(f"git:{anchor['commit_concluded']}:{anchor['path']}"
                                 f"#L{anchor['line_start']}|q={anchor['quote_sha256']}"),
            source_kind=SOURCE_KIND,
            applicability=applicability,
            observation=observation,
        )
    except (TypeError, ValueError) as exc:
        raise ProjectionError(f"committed conclusion {row['cc_id']} refused: {exc}") from exc


# ------------------------------------------------------------------ register writer (cli)

def build_row(*, path: str, line: int, ref: str = "origin/main", facet: str = "",
              kind: str = "result", stated: dict, scope: dict, scope_evidence: str,
              category: str, direction: str, actor: str, at: str, retrofit: bool,
              task_id: str | None = None, also: Iterable[tuple[str, int]] = (),
              raw_paths: Iterable[str] = (), mechanism: dict | None = None,
              repo: Path | None = None, rev: int = 1,
              supersedes: str | None = None) -> dict:
    anchor = resolve_anchor(path, line, ref=ref, repo=repo)
    raw_paths = list(raw_paths)
    raw: dict[str, Any] = {}
    if raw_paths:
        digests = {}
        for p in raw_paths:
            fp = Path(p)
            digests[p] = hashlib.sha256(fp.read_bytes()).hexdigest() if fp.is_file() else None
        raw = {"paths": raw_paths, "status": "present" if all(digests.values()) else "lost",
               "sha256": digests}
    row = {
        "schema": SCHEMA, "cc_id": cc_id(path, anchor["head_norm"], facet), "rev": rev,
        "kind": kind, **({"facet": facet} if facet else {}), "anchor": anchor,
        "also_anchored": [resolve_also(p, n, ref=ref, repo=repo) for p, n in also],
        "task_id": task_id, "stated": stated, "scope": scope, "scope_evidence": scope_evidence,
        "category": category, "metric_direction": direction, "raw_evidence": raw or None,
        "covered_by": None, "supersedes": supersedes,
        "confirmed_by": {"actor": actor, "at": at, "method": "agent", "extractor": "hand"},
        "retrofit": retrofit, **({"mechanism": mechanism} if mechanism else {}),
    }
    check_row(row, repo=repo)
    return row


def append_row(register_path: Path, row: dict) -> bool:
    """Append unless (cc_id, rev) is already present. Returns True when written."""
    register_path = Path(register_path)
    existing = read_register(register_path) if register_path.exists() else []
    if any(r.get("cc_id") == row["cc_id"] and r.get("rev") == row["rev"] for r in existing):
        return False
    register_path.parent.mkdir(parents=True, exist_ok=True)
    with register_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    return True
