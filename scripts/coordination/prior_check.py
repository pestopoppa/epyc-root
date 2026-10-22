#!/usr/bin/env python3
"""prior_check.py -- zero-compute "has this already been measured?" lookup.

PROPOSED 2026-10-21, pending workspace-58 / stage-3 agreement (see
docs/guides/agent-workflows/compute-fillers.md, "Prior check").  Origin: process change (B) of
/mnt/raid0/llm/tmp/inference-backlog-audit-20261021/REPORT.md section 4 -- bookings were filed and
armed without anyone checking prior results, so the same instrument was booked twice on one build.

Run it BEFORE an inference booking enters the shared queue (FILLERS.md / a GRANT line).  It reads,
never writes, and does no inference.  It runs at nice 19 (os.nice) and stops itself at --budget-s
(default 20 s) so the whole call stays under 30 s on a loaded host.

CLI
---
    prior_check.py [--model FILE|BASENAME] [--model-sha256 HEX64]
                   [--recipe FILE|HASH|NAME] [--argv "<launch argv string>"]
                   [--metric KW]... [--decision KW]...    (repeatable; free keywords, e.g. a
                                                           metric name, an item id "KVU-12.1",
                                                           "floor", "ppl")
                   [--build GITSHA(7-40 hex)] [--digest EXECUTION_DIGEST(hex, >=12)]
                   [--tag T]...        (extra identity aliases, e.g. "ds41", "q38fn")
                   [--top N=12] [--json] [--budget-s S=20]
                   [--ledger P] [--tmp-root P] [--ak-root P] [--research-root P]
                   [--extra-root P]... [--no-nice]

At least one of model / recipe / argv / metric / decision / build / digest / tag is required;
otherwise (or on a malformed hex value, or a --recipe/--model that looks like a path but does not
exist as a non-empty value) the exit code is 2.  Every other situation -- no candidates, a source
that is missing or unreadable, a truncated walk -- exits 0 and says so in the notes.

Sources (all READ-ONLY, all bounded)
------------------------------------
1. Belief ledger (default /mnt/raid0/llm/state/vidya/ledger.jsonl): source_observed frames carry
   `applicability` {model_file, model_sha256, quant, backend, recipe, build_sha,
   execution_digest, knob_family, varied, kernel{execution_digest,build_path}, ...} and `title`
   (the metric, old schema); evidence frames of the new schema (root branch
   f8/belief-p1-integrated, scripts/vidya/claim_tuple.py) additionally carry
   metric/value/unit/observation.  Both are handled: frames are grouped by `source_id`, claim
   text and evidence metrics are joined in, and a retracted claim marks the candidate RETRACTED.
2. AutoKernel campaign stores (default /mnt/raid0/llm/autokernel/campaigns/*/store*/):
   serving-floor.*.json (recipe, recipe_hash, median_tok_s, floor_pct ...), serving-beliefs/ (one
   candidate per receipt directory) and experiments.db (sqlite opened `mode=ro`, never scanning
   the payload column; rows are summarised per status).
3. Research artifacts (default /workspace/repos/epyc-inference-research/artifacts) and any
   --extra-root: depth <= 3, filename + head-of-file grep only.
4. Run records under the tmp root (default /mnt/raid0/llm/tmp): RUN_RECORD.json, summary.json /
   summary.md, records/*.json (schema epyc.kpf.run.v1), result/verdict/report files and *.jsonl
   (arm/metric lines).  Depth <= 4, source/build trees pruned, newest files first, per-file head
   read only; a walk that runs out of budget says how many files it did not read.

Matching
--------
Plain case-insensitive substring tests on the file text + path (ledger: the frame text), with
weights: execution digest 4.0, recipe hash 3.5 (a recipe FILE is hashed sha256; --argv is
whitespace-normalised and hashed), model stem 3.0 (family prefix of the first three name tokens
1.5), tag 1.5, argv-flag overlap 1.0, build 2.0, each --metric keyword 1.0 (cap 3), each
--decision keyword 2.0 (cap 4; decisions are item ids such as KVU-12.1, i.e. specific).
If any of model/recipe/digest/tag was supplied, a candidate must match at least one of them (a
metric-only hit on an unrelated model is noise).  Candidates that do not mention a supplied
keyword are kept but marked `metric-not-seen`.  Nothing is inferred from the absence of a
field: a file that states no build is `build-unknown`, never "same".

Staleness (era rules)
---------------------
MEASUREMENT.md section 6a (era registry: within-era comparisons only) and MEASUREMENT_POLICY.md
("Quality scores transfer across kernel eras once parity is proven; kernel era-fencing exists for
the speed axis").  Note: MEASUREMENT.md has no rule labelled "A4" -- bench-cpu.md's A4 is a fleet
shape, not an era rule; this tool implements the 6a/POLICY rule.  With --build/--digest:
  same-build            the candidate states a build/digest that prefix-matches the request
  build-unknown         the candidate states none (cannot be certified either way)
  STALE-speed           states other build(s) and the metric reads as speed (tok/s, latency,
                        floor, prefill/decode, speedup): era-fenced, must re-measure
  STALE-transferable    states other build(s) and the metric reads as quality (ppl, nmse,
                        accuracy, parity, identity): transfers once parity is proven
  STALE                 states other build(s), axis unclear
Byte-equivalent builds (tests-only commits, same CMake recipe) are NOT detected here; that is a
human call -- the flag only says the sha differs.

The `prior=` contract (queue rows / GRANT lines)
-------------------------------------------------
The last text line (and the `prior` key of --json) is exactly one of

    prior=<absolute path> [(<flag>)]        a candidate that scored >= 3.5 and, when a
                                            tag/recipe/digest/decision was given, matched
                                            one of THOSE (model + a generic metric alone is
                                            only a lead), and is not STALE-speed; <flag> is
                                            absent for a clean same-build hit, else one of
                                            STALE-transferable | STALE | build-unknown |
                                            RETRACTED
    prior=none (checked <UTC ts, Z>)        nothing qualified, or the only strong
                                            candidates are STALE-speed / RETRACTED

Booking-source documents are never emitted as `prior=` (they stay in the list, flagged
`TASK-DOC`): FILLERS.md*, files named *booking*, *-index.md, *handoff*, master-handoff-index.md,
CURRENT-CAMPAIGN.md, any .md under handoffs/, compute-flags/ or bookings/, and REPORT.md under an
audit/booking directory.  They describe a task; they are not results.

A validator parses the first whitespace-delimited token after `prior=`.  `none (checked ...)`
means "the lookup ran and found nothing citable", not "nobody has looked": the timestamp is the
evidence of when.  A path is a LEAD the booker must open and cite or reject in the row's
`decision=` text; this tool never decides that a booking is redundant.

Exit codes: 0 always, except 2 for malformed inputs.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

DEFAULT_LEDGER = "/mnt/raid0/llm/state/vidya/ledger.jsonl"
DEFAULT_TMP = "/mnt/raid0/llm/tmp"
DEFAULT_AK = "/mnt/raid0/llm/autokernel/campaigns"
DEFAULT_RESEARCH = "/workspace/repos/epyc-inference-research/artifacts"

PRIOR_MIN_SCORE = 3.5
W_DIGEST, W_RECIPE, W_MODEL, W_FAMILY = 4.0, 3.5, 3.0, 1.5
W_TAG, W_ARGV, W_BUILD, W_METRIC, METRIC_CAP = 1.5, 1.0, 2.0, 1.0, 3.0
W_DECISION, DECISION_CAP = 2.0, 4.0

HEAD_JSON = 256 * 1024
HEAD_JSONL, TAIL_JSONL = 128 * 1024, 32 * 1024
HEAD_RESEARCH = 128 * 1024
MAX_RESEARCH_FILE = 4 * 1024 * 1024
MAX_JSONL = 512 * 1024 * 1024
TMP_DEPTH, RESEARCH_DEPTH = 4, 3
MAX_DIRS = 30000
PRUNE_DIRS = {".git", "worktree", "research-wt", "node_modules", "__pycache__", ".venv", "venv", "models", "worktrees",
              "src-store", ".gemini", ".mypy_cache", ".pytest_cache", "site-packages"}
PRUNE_PREFIXES = ("build", "src", "llama.cpp", "ik_llama", "cmake-build")
RECORD_NAME = re.compile(r"^(run_record|summary|results?|verdict|report|decision)[^/]*\.(json|md)$",
                         re.I)
RESEARCH_EXT = {".json", ".md", ".jsonl", ".csv", ".txt"}

HEX = re.compile(r"^[0-9a-fA-F]+$")
HEXTOK = re.compile(r"(?<![0-9a-zA-Z])([0-9a-f]{7,40})(?![0-9a-zA-Z])")
BUILD_KEY = re.compile(
    r"(?:build_sha|build|code_head|git_sha|commit|kernel_sha|anchor_build|head)[\"']?\s*[:=]\s*"
    r"[\"']?([0-9a-f]{7,40})", re.I)
DATE_KEY = re.compile(
    r"\"(?:recorded_at|created_at|start|date|ts|timestamp|as_of|finished|end|revision_observed)\""
    r"\s*:\s*\"(\d{4}-\d{2}-\d{2}[T0-9:.Z+-]*)\"")
SPEED_WORDS = ("tok/s", "tok_s", "t/s", "tps", "latency", "floor", "decode", "prefill",
               "speedup", "throughput", "ms/", "pp512", "tg128", "bandwidth")
QUALITY_WORDS = ("ppl", "perplexity", "nmse", "accuracy", "parity", "identical", "identity",
                 "pass_rate", "kld", "coherence", "score", "exact_match")


def utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_mtime(path: str) -> str:
    try:
        return dt.datetime.fromtimestamp(os.stat(path).st_mtime, dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
    except OSError:
        return ""


# --------------------------------------------------------------------------- query

class Query:
    def __init__(self, a: argparse.Namespace):
        self.model_raw = a.model or ""
        self.stem = ""
        self.family = ""
        self.model_sha = (a.model_sha256 or "").lower()
        self.metrics = [m.lower() for m in (a.metric or []) if m.strip()]
        self.decisions = [m.lower() for m in (a.decision or []) if m.strip()]
        self.tags = [t.lower() for t in (a.tag or []) if t.strip()]
        self.build = (a.build or "").lower()
        self.digest = (a.digest or "").lower()
        self.recipe_hashes: set[str] = set()
        self.recipe_names: set[str] = set()
        self.argv_flags: list[str] = []
        if self.model_raw:
            self.stem = model_stem(self.model_raw)
            toks = [t for t in re.split(r"[-_ ]+", self.stem) if t]
            self.family = "-".join(toks[:3]) if len(toks) >= 3 and len(self.stem) > 8 else ""
        if a.recipe:
            self._load_recipe(a.recipe)
        if a.argv:
            norm = " ".join(a.argv.split())
            self.recipe_hashes.add(hashlib.sha256(norm.encode()).hexdigest())
            self.argv_flags = sorted({t for t in a.argv.split() if t.startswith("-") and len(t) > 1})

    def _load_recipe(self, r: str) -> None:
        p = Path(r)
        if p.is_file():
            data = p.read_bytes()
            self.recipe_hashes.add(hashlib.sha256(data).hexdigest())
            self.recipe_names.add(p.stem.lower())
        elif "/" in r:
            raise ValueError(f"--recipe looks like a path but is not a file: {r}")
        elif HEX.match(r) and len(r) >= 12:
            self.recipe_hashes.add(r.lower())
        else:
            self.recipe_names.add(r.lower())

    @property
    def has_specific(self) -> bool:
        """Terms that single out ONE piece of work (not just the model + a generic metric)."""
        return bool(self.digest or self.recipe_hashes or self.recipe_names or self.tags
                    or self.decisions)

    @property
    def ident_supplied(self) -> bool:
        return bool(self.stem or self.model_sha or self.recipe_hashes or self.recipe_names
                    or self.digest or self.tags)

    def terms(self) -> list[str]:
        """Substrings; a ledger line / file head is only parsed when it contains one."""
        t = [x for x in (self.stem, self.family, self.model_sha[:16], self.digest[:16],
                         self.build) if x]
        t += [h[:16] for h in self.recipe_hashes] + list(self.recipe_names) + self.tags
        t += self.metrics + self.decisions
        return t


def model_stem(model: str) -> str:
    base = os.path.basename(model.rstrip("/")).lower()
    base = re.sub(r"-\d{5}-of-\d{5}", "", base)
    base = re.sub(r"\.gguf$", "", base)
    return base


# --------------------------------------------------------------------------- scoring

def build_tokens(text: str, path: str) -> set[str]:
    """Build-ish shas a candidate STATES: keyed values, plus hex tokens in its path."""
    found = {m.group(1).lower() for m in BUILD_KEY.finditer(text)}
    for m in HEXTOK.finditer(path.lower()):
        tok = m.group(1)
        if re.search(r"[a-f]", tok) and re.search(r"\d", tok):
            found.add(tok)
    return found


def prefix_eq(a: str, b: str) -> bool:
    n = min(len(a), len(b))
    return n >= 7 and a[:n] == b[:n]


def classify_axis(text: str) -> str:
    low = text.lower()
    s = sum(w in low for w in SPEED_WORDS)
    q = sum(w in low for w in QUALITY_WORDS)
    if s == q:
        return "unclear"
    return "speed" if s > q else "quality"


def score_candidate(q: Query, text: str, path: str, extra_builds: set[str] | None = None,
                    axis_text: str = "") -> dict | None:
    low = text.lower()
    plow = path.lower()
    hay = low + "\n" + plow
    matched: list[str] = []
    ident = 0.0
    score = 0.0

    def hit(label: str, w: float, is_ident: bool = True) -> None:
        nonlocal score, ident
        matched.append(label)
        score += w
        if is_ident:
            ident += w

    if q.digest and q.digest[:16] in hay:
        hit("execution_digest", W_DIGEST)
    for h in sorted(q.recipe_hashes):
        if h[:16] in hay:
            hit("recipe_hash", W_RECIPE)
            break
    else:
        for nme in sorted(q.recipe_names):
            if nme in hay:
                hit(f"recipe:{nme}", W_RECIPE - 0.5)
                break
    if q.model_sha and q.model_sha[:16] in hay:
        hit("model_sha256", W_MODEL)
    elif q.stem and q.stem in hay:
        hit("model", W_MODEL)
    elif q.family and q.family in hay:
        hit("model-family", W_FAMILY)
    tag_hits = [t for t in q.tags if t in hay]
    if tag_hits:
        hit("tag:" + ",".join(tag_hits), min(W_TAG * len(tag_hits), 3.0))
    if q.argv_flags:
        frac = sum(f in low for f in q.argv_flags) / len(q.argv_flags)
        if len(q.argv_flags) >= 3 and frac >= 0.8:
            hit("argv-flags", W_ARGV)

    builds = build_tokens(text, path) | (extra_builds or set())
    stale = "n/a (no build requested)"
    if q.build or q.digest:
        same = (q.build and (any(prefix_eq(q.build, b) for b in builds) or q.build in hay)) \
            or (q.digest and q.digest[:16] in hay)
        if same:
            stale = "same-build"
            if q.build:
                hit("build", W_BUILD, is_ident=False)
        elif builds:
            ax = classify_axis(axis_text or text)
            stale = {"speed": "STALE-speed", "quality": "STALE-transferable"}.get(ax, "STALE")
        else:
            stale = "build-unknown"

    kw_hits = [m for m in q.metrics if m in hay]
    dec_hits = [m for m in q.decisions if m in hay]
    if kw_hits:
        matched.append("kw:" + ",".join(kw_hits[:4]))
        score += min(W_METRIC * len(kw_hits), METRIC_CAP)
    if dec_hits:
        matched.append("decision:" + ",".join(dec_hits[:4]))
        score += min(W_DECISION * len(dec_hits), DECISION_CAP)
    specific = bool(dec_hits or any(
        m.split(":")[0] in ("execution_digest", "recipe_hash", "tag", "argv-flags")
        or m.startswith("recipe:") for m in matched))
    any_kw = bool(kw_hits or dec_hits)

    if q.ident_supplied:
        if ident <= 0:
            return None
    else:
        if not any_kw and not ("build" in " ".join(matched)):
            return None
    if (q.metrics or q.decisions) and not any_kw:
        matched.append("metric-not-seen")
        score -= 1.0
    if score <= 0:
        return None
    return {"score": round(score, 2), "matched": matched, "stale": stale,
            "builds_found": sorted(builds)[:4], "axis": classify_axis(axis_text or text),
            "specific": specific}


def file_date(text: str, path: str) -> str:
    m = DATE_KEY.search(text)
    if m:
        return m.group(1)
    return iso_mtime(path)


# --------------------------------------------------------------------------- sources

def read_head(path: str, n: int) -> str:
    with open(path, "rb") as f:
        return f.read(n).decode("utf-8", "replace")


def read_tail(path: str, n: int, size: int) -> str:
    if size <= n:
        return ""
    with open(path, "rb") as f:
        f.seek(size - n)
        return f.read(n).decode("utf-8", "replace")


def walk(root: str, max_depth: int, deadline: float, notes: list[str], label: str):
    """Yield (path, st) for regular files; prunes build/source trees; bounded by depth/dirs/time."""
    stack = [(root, 0)]
    dirs = 0
    while stack:
        if time.monotonic() > deadline:
            notes.append(f"{label}: walk stopped at the time budget")
            return
        d, depth = stack.pop()
        dirs += 1
        if dirs > MAX_DIRS:
            notes.append(f"{label}: walk stopped at {MAX_DIRS} directories")
            return
        try:
            it = list(os.scandir(d))
        except OSError:
            continue
        if depth >= 1 and any(x.name == ".git" for x in it):
            continue  # a repo checkout / worktree copy: source files, not run records
        for e in it:
            try:
                if e.is_symlink():
                    continue
                if e.is_dir(follow_symlinks=False):
                    n = e.name
                    if n in PRUNE_DIRS or (depth >= 1 and n.startswith(PRUNE_PREFIXES)):
                        continue
                    if depth + 1 <= max_depth:
                        stack.append((e.path, depth + 1))
                elif e.is_file(follow_symlinks=False):
                    yield e.path, e.stat(follow_symlinks=False)
            except OSError:
                continue


def src_ledger(q: Query, path: str, deadline: float, notes: list[str]) -> list[dict]:
    if not os.path.isfile(path):
        notes.append(f"ledger: {path} not found")
        return []
    terms = q.terms()
    src: dict[str, dict] = {}
    claims: dict[str, dict] = {}
    retracted: set[str] = set()   # frame_ids named by retraction frames (`retracts`)
    frame_src: dict[str, str] = {}  # frame_id -> source_id, for mapping a retraction to its source
    n = parsed = 0
    try:
        f = open(path, "rb")
    except OSError as exc:
        notes.append(f"ledger: unreadable ({exc})")
        return []
    with f:
        for raw in f:
            n += 1
            if n % 4096 == 0 and time.monotonic() > deadline:
                notes.append("ledger: stopped at the time budget")
                break
            if b"/frame/" not in raw:
                continue
            if b"source_observed" in raw or b"claim_proposed" in raw \
                    or b"evidence_supports_claim" in raw or b"/retraction/" in raw:
                try:
                    fr = json.loads(raw)
                except ValueError:
                    continue
                parsed += 1
                ft = fr.get("frame", {}).get("frame_type", "")
                a = fr.get("frame", {}).get("assertion", {}) or {}
                fid = fr.get("frame", {}).get("frame_id", "")
                if a.get("source_id"):
                    frame_src[fid] = a["source_id"]
                pub = fr.get("frame", {}).get("pubinfo", {}) or {}
                if ft.endswith("source_observed/v1"):
                    sid = a.get("source_id", "")
                    src[sid] = {"a": a, "seq": fr.get("seq"), "created": pub.get("created_at", "")}
                elif ft.endswith("claim_proposed/v1"):
                    claims.setdefault(a.get("source_id", ""), {}).setdefault(
                        "claim", []).append((a.get("claim_id", ""), a.get("display_text", "")))
                elif ft.endswith("evidence_supports_claim/v1"):
                    claims.setdefault(a.get("source_id", ""), {}).setdefault(
                        "evid", []).append(a)
                elif ft.endswith("retraction/v1"):
                    if a.get("retracts"):
                        retracted.add(a["retracts"])
    retracted_src = {frame_src[f] for f in retracted if f in frame_src}
    out = []
    for sid, rec in src.items():
        a = rec["a"]
        app = a.get("applicability") or {}
        cl = claims.get(sid, {})
        evid = cl.get("evid", [])
        parts = [json.dumps(app, sort_keys=True), a.get("title"), a.get("locator"),
                 a.get("source_kind"), sid]
        parts += [t for _, t in cl.get("claim", [])]
        parts = [str(x) for x in parts if x]  # frames may carry null title/locator/display_text
        metric_vals = []
        for e in evid:
            if e.get("metric"):
                parts.append(str(e["metric"]))
                metric_vals.append(f"{e.get('metric')}={e.get('value')}{e.get('unit') or ''}")
            if e.get("observation"):
                parts.append(json.dumps(e["observation"], sort_keys=True))
        text = "\n".join(parts)
        low = text.lower()
        if terms and not any(t in low for t in terms):
            continue
        extra_builds = set()
        for key, val in _walk_kv(app):
            if key in ("build_sha", "epoch") and isinstance(val, str) and HEX.match(val):
                extra_builds.add(val.lower())
        res = score_candidate(q, text, str(a.get("locator") or ""), extra_builds,
                              axis_text=str(a.get("title") or "") + " " + " ".join(metric_vals))
        if not res:
            continue
        dig = [v for k, v in _walk_kv(app) if k == "execution_digest" and isinstance(v, str)]
        if q.digest and dig and not any(prefix_eq(q.digest, d.lower()) for d in dig):
            if res["stale"] == "same-build":
                res["stale"] = "STALE"
        res["matched"].append("ledger-applicability" if app else "ledger-no-applicability")
        is_ret = sid in retracted_src
        res.update(source="ledger", path=a.get("locator") or f"{path}#{sid}",
                   ref=f"{path}#seq={rec['seq']}", date=a.get("revision_observed") or rec["created"],
                   note=("; ".join(metric_vals[:2]) or str(a.get("title") or "")),
                   retracted=is_ret)
        out.append(res)
    notes.append(f"ledger: parsed {parsed} measurement frames, {len(src)} sources")
    return out


def _walk_kv(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, v
            yield from _walk_kv(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_kv(v)


def _open_ro(db: str) -> sqlite3.Connection:
    for uri in (f"file:{db}?mode=ro", f"file:{db}?mode=ro&immutable=1"):
        try:
            c = sqlite3.connect(uri, uri=True, timeout=1.0)
            c.execute("select 1 from experiments limit 1")
            return c
        except sqlite3.Error:
            continue
    raise sqlite3.Error("cannot open read-only")


def src_autokernel(q: Query, root: str, deadline: float, notes: list[str]) -> list[dict]:
    out: list[dict] = []
    if not os.path.isdir(root):
        notes.append(f"autokernel: {root} not found")
        return out
    stores: list[str] = []
    try:
        for c in os.scandir(root):
            if not c.is_dir(follow_symlinks=False):
                continue
            stores.append(c.path)
            try:
                for s in os.scandir(c.path):
                    if s.is_dir(follow_symlinks=False) and s.name.startswith("store"):
                        stores.append(s.path)
            except OSError:
                pass
    except OSError as exc:
        notes.append(f"autokernel: {exc}")
        return out
    nterms = q.metrics + q.decisions
    for d in stores:
        if time.monotonic() > deadline:
            notes.append("autokernel: stopped at the time budget")
            break
        try:
            entries = list(os.scandir(d))
        except OSError:
            continue
        for e in entries:
            try:
                if e.name.startswith("serving-floor") and e.name.endswith(".json") and e.is_file():
                    text = read_head(e.path, 64 * 1024)
                    summ = ""
                    try:
                        j = json.loads(read_head(e.path, 2 * 1024 * 1024))
                        summ = (f"{j.get('metric')} median={j.get('median_tok_s')} n={j.get('n')} "
                                f"floor_pct={j.get('floor_pct')} recipe={j.get('recipe')}")
                        text += f"\n{j.get('recipe_hash','')} {j.get('request_digest','')}"
                    except ValueError:
                        pass
                    res = score_candidate(q, text, e.path, axis_text="floor tok/s " + summ)
                    if res:
                        res.update(source="autokernel-floor", path=e.path, ref=e.path,
                                   date=iso_mtime(e.path), note=summ, retracted=False)
                        out.append(res)
                elif e.name == "serving-beliefs" and e.is_dir():
                    res = score_candidate(q, "serving-beliefs receipts", e.path,
                                          axis_text="tok/s")
                    if res:
                        try:
                            cnt = sum(1 for _ in os.scandir(e.path))
                        except OSError:
                            cnt = 0
                        res.update(source="autokernel-beliefs", path=e.path, ref=e.path,
                                   date=iso_mtime(e.path), retracted=False,
                                   note=f"{cnt} serving receipts (pointers into the ledger)")
                        out.append(res)
                elif e.name == "experiments.db" and e.is_file():
                    res = score_candidate(q, "", d, axis_text="")
                    id_ok = res is not None or not q.ident_supplied
                    if not id_ok:
                        continue
                    rows = _ak_rows(e.path, nterms, deadline, notes) if nterms else None
                    base = res or {"score": 1.0, "matched": [], "stale": "n/a (no build requested)",
                                   "builds_found": [], "axis": "unclear"}
                    if rows is None:
                        if not res:
                            continue
                        note = "campaign store matched by name only"
                    elif not rows["n"]:
                        continue
                    else:
                        base = dict(base)
                        base["score"] = round(base["score"] + min(1.0 * len(nterms), 3.0), 2)
                        base["specific"] = base.get("specific") or bool(q.decisions)
                        if "metric-not-seen" in base["matched"]:
                            base["score"] = round(base["score"] + 1.0, 2)  # undo the penalty
                        base["matched"] = [m for m in base["matched"] if m != "metric-not-seen"] \
                            + [f"experiments:{rows['n']} rows"]
                        note = f"{rows['n']} experiment rows ({rows['by']}); latest {rows['latest']}"
                    if q.build or q.digest:
                        # an AK store's epochs are not git shas: only the store directory name
                        # can speak for a build, so anything else is build-unknown, not STALE.
                        if base["stale"] not in ("same-build",):
                            base["stale"] = "build-unknown" if not base["builds_found"] \
                                else base["stale"]
                    base.update(source="autokernel-db", path=e.path, ref=e.path,
                                date=(rows or {}).get("latest") or iso_mtime(e.path), note=note,
                                retracted=False)
                    out.append(base)
            except (OSError, sqlite3.Error) as exc:
                notes.append(f"autokernel: {e.path}: {exc}")
    return out


def _ak_rows(db: str, terms: list[str], deadline: float, notes: list[str]) -> dict | None:
    try:
        con = _open_ro(db)
    except sqlite3.Error as exc:
        notes.append(f"autokernel: {db}: {exc}")
        return None
    try:
        stop = min(deadline, time.monotonic() + 5.0)
        con.set_progress_handler(lambda: 1 if time.monotonic() > stop else 0, 20000)
        cols = ("coalesce(statement,'')||' '||coalesce(mechanism_id,'')||' '||"
                "coalesce(hypothesis_id,'')||' '||coalesce(target_symbol,'')||' '||"
                "coalesce(target_surface,'')||' '||coalesce(deployment,'')")
        where = " OR ".join(f"lower({cols}) LIKE ?" for _ in terms)
        params = [f"%{t}%" for t in terms]
        cur = con.execute(
            f"SELECT status, count(*), max(recorded_at) FROM experiments WHERE {where} "
            f"GROUP BY status", params)
        rows = cur.fetchall()
    except sqlite3.Error as exc:
        notes.append(f"autokernel: {db}: query stopped ({exc})")
        return None
    finally:
        con.close()
    n = sum(r[1] for r in rows)
    by = ", ".join(f"{s}:{c}" for s, c, _ in sorted(rows, key=lambda r: -r[1])[:4])
    latest = max((r[2] or "" for r in rows), default="")
    return {"n": n, "by": by, "latest": latest}


def src_files(q: Query, root: str, label: str, depth: int, deadline: float, notes: list[str],
              kind: str) -> list[dict]:
    """tmp run records (kind='tmp') and research artifacts (kind='research')."""
    out: list[dict] = []
    if not os.path.isdir(root):
        notes.append(f"{label}: {root} not found")
        return out
    cands = []
    # the walk may use only 40% of what is left, so there is always time left to READ files
    walk_deadline = time.monotonic() + 0.4 * max(deadline - time.monotonic(), 0.0)
    for p, st in walk(root, depth, walk_deadline, notes, label):
        name = os.path.basename(p)
        low = name.lower()
        parent = os.path.basename(os.path.dirname(p))
        if kind == "tmp":
            ok = (RECORD_NAME.match(name) is not None
                  or (parent == "records" and low.endswith(".json"))
                  or (low.endswith(".jsonl") and st.st_size <= MAX_JSONL))
            if not ok or st.st_size == 0:
                continue
        else:
            if os.path.splitext(low)[1] not in RESEARCH_EXT or st.st_size > MAX_RESEARCH_FILE:
                continue
        cands.append((st.st_mtime, p, st.st_size))
    cands.sort(reverse=True)
    unread = 0
    for i, (_, p, size) in enumerate(cands):
        if time.monotonic() > deadline:
            unread = len(cands) - i
            break
        try:
            if p.endswith(".jsonl"):
                text = read_head(p, HEAD_JSONL) + "\n" + read_tail(p, TAIL_JSONL, size)
            else:
                text = read_head(p, HEAD_JSON if kind == "tmp" else HEAD_RESEARCH)
        except OSError:
            continue
        res = score_candidate(q, text, p)
        if not res:
            continue
        note = ""
        if p.endswith(".jsonl"):
            kws = q.terms()
            lines = [ln for ln in text.splitlines() if any(t in ln.lower() for t in kws)]
            res["matched"].append(f"{len(lines)} matching lines in sampled head/tail")
            note = lines[0][:200] if lines else ""
        else:
            try:
                j = json.loads(text)
                if isinstance(j, dict) and j.get("schema"):
                    note = f"schema={j['schema']}"
            except ValueError:
                pass
        res.update(source=label, path=p, ref=p, date=file_date(text, p), note=note,
                   retracted=False)
        out.append(res)
    notes.append(f"{label}: scanned {len(cands) - unread} of {len(cands)} candidate files"
                 + (f" ({unread} NOT read: budget)" if unread else ""))
    return out


# --------------------------------------------------------------------------- output

TASK_DOC_NAMES = {"master-handoff-index.md", "current-campaign.md", "fillers.md"}


def is_task_document(path: str) -> bool:
    """True for files that DESCRIBE work (a booking, a handoff, an index, an audit report):
    they mention a task id and a model, but they are not a result of running it."""
    low = path.lower()
    name = os.path.basename(low)
    comps = set(low.split("/"))
    if name in TASK_DOC_NAMES or name.startswith("fillers.md."):
        return True
    if "booking" in name or name.endswith("-index.md") or "handoff" in name:
        return True
    if name.endswith(".md") and comps & {"handoffs", "compute-flags", "bookings"}:
        return True
    if name == "report.md" and any("audit" in c or "booking" in c for c in comps):
        return True
    return False


def decide_prior(cands: list[dict], ts: str, q: Query | None = None) -> tuple[str, dict | None]:
    for c in cands:
        if c["score"] < PRIOR_MIN_SCORE:
            break
        if c.get("retracted"):
            continue
        if c.get("task_doc"):
            continue  # a booking/handoff/index/audit document describes a task; it is not a result
        if "ledger-no-applicability" in c.get("matched", []):
            continue  # an intake/claim record with no measurement scope is not a prior result
        if q is not None and q.has_specific and not c.get("specific"):
            continue  # model + a generic metric alone is a lead, not a prior
        if c["stale"] == "STALE-speed":
            continue
        flag = ""
        if c["stale"] in ("STALE-transferable", "STALE", "build-unknown"):
            flag = f" ({c['stale']})"
        return f"prior={c['path']}{flag}", c
    return f"prior=none (checked {ts})", None


def run(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="zero-compute prior-results lookup (see module docstring)")
    ap.add_argument("--model")
    ap.add_argument("--model-sha256")
    ap.add_argument("--recipe")
    ap.add_argument("--argv")
    ap.add_argument("--metric", action="append")
    ap.add_argument("--decision", action="append")
    ap.add_argument("--build")
    ap.add_argument("--digest")
    ap.add_argument("--tag", action="append")
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--budget-s", type=float, default=20.0)
    ap.add_argument("--ledger", default=DEFAULT_LEDGER)
    ap.add_argument("--tmp-root", default=DEFAULT_TMP)
    ap.add_argument("--ak-root", default=DEFAULT_AK)
    ap.add_argument("--research-root", default=DEFAULT_RESEARCH)
    ap.add_argument("--extra-root", action="append")
    ap.add_argument("--no-nice", action="store_true")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    err = None
    for name, val, minlen in (("--build", a.build, 7), ("--digest", a.digest, 12),
                              ("--model-sha256", a.model_sha256, 12)):
        if val and (not HEX.match(val) or len(val) < minlen):
            err = f"{name} must be hex of at least {minlen} characters: {val!r}"
    if a.build and len(a.build) > 40:
        err = "--build is a git sha (<= 40 hex)"
    if not any([a.model, a.model_sha256, a.recipe, a.argv, a.metric, a.decision, a.build,
                a.digest, a.tag]):
        err = "give at least one of --model/--recipe/--argv/--metric/--decision/--build/--digest/--tag"
    q = None
    if not err:
        try:
            q = Query(a)
        except (ValueError, OSError) as exc:
            err = str(exc)
    if err:
        print(f"prior_check: malformed input: {err}", file=sys.stderr)
        return 2
    if not a.no_nice:
        try:
            os.nice(19)
        except OSError:
            pass

    t0 = time.monotonic()
    b = max(a.budget_s, 1.0)
    ts = utcnow()
    notes: list[str] = []
    cands: list[dict] = []
    plan = [("ledger", 0.25, lambda dl: src_ledger(q, a.ledger, dl, notes)),
            ("autokernel", 0.45, lambda dl: src_autokernel(q, a.ak_root, dl, notes)),
            ("research", 0.65, lambda dl: src_files(q, a.research_root, "research", RESEARCH_DEPTH,
                                                    dl, notes, "research")),
            ("tmp-run-records", 1.0, lambda dl: src_files(q, a.tmp_root, "run-records", TMP_DEPTH,
                                                          dl, notes, "tmp"))]
    for er in (a.extra_root or []):
        plan.insert(3, (f"extra:{er}", 0.85, lambda dl, er=er: src_files(
            q, er, "extra", RESEARCH_DEPTH, dl, notes, "research")))
    for name, frac, fn in plan:
        try:
            cands += fn(t0 + b * frac)
        except Exception as exc:  # a source failing must never hide the others
            notes.append(f"{name}: failed ({type(exc).__name__}: {exc})")
    # tie-break: stronger score first, then newest
    for c in cands:
        if is_task_document(str(c.get("path", ""))):
            c["task_doc"] = True
            c["matched"].append("TASK-DOC (describes a task, not a result; never prior=)")
    cands.sort(key=lambda c: (c["score"], c.get("date") or ""), reverse=True)
    prior, best = decide_prior(cands, ts, q)
    top = cands[:max(a.top, 1)]
    elapsed = round(time.monotonic() - t0, 2)
    if a.json:
        print(json.dumps({"schema": "epyc.prior_check.v1", "checked": ts, "elapsed_s": elapsed,
                          "query": {"model": a.model, "recipe": a.recipe, "argv": a.argv,
                                    "metric": a.metric or [], "decision": a.decision or [],
                                    "build": a.build, "digest": a.digest, "tag": a.tag},
                          "prior": prior, "candidates": top, "notes": notes,
                          "total_candidates": len(cands)}, indent=1))
        return 0
    print(f"prior_check {ts}  ({elapsed}s, {len(cands)} candidates, showing {len(top)})")
    for i, c in enumerate(top, 1):
        flag = c["stale"] + (" RETRACTED" if c.get("retracted") else "")
        print(f"{i:>2}. [{c['score']:>5}] {c['source']}  {c['path']}")
        print(f"      date={c.get('date') or '?'}  build={flag}  axis={c['axis']}"
              f"  builds_seen={','.join(c['builds_found']) or '-'}")
        print(f"      matched: {'; '.join(c['matched'])}")
        if c.get("note"):
            print(f"      note: {c['note'][:200]}")
    for n in notes:
        print(f"note: {n}")
    print(prior)
    return 0


if __name__ == "__main__":
    sys.exit(run())
