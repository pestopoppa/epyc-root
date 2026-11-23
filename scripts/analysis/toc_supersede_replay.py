#!/usr/bin/env python3
"""TOC-SUPERSEDE-1: offline tool-supersession classifier replay (zero inference, zero model calls).

Rule (fixed before the run, see RULE below). A tool output is SUPERSEDED when a later call
in the same history segment

  * reads or edits the same file path,
  * re-runs the same normalized shell/search command,
  * is a successful build whose targets overlap an earlier build, or
  * is a passing re-run of the same normalized test command.

A ROUND (one assistant turn with >= 1 tool call) is a CANDIDATE when every one of its tool
outputs is superseded and the 2-round grace window since the LAST of those supersessions has
elapsed before the end of the segment (final history).

Token unit: chars/4 ESTIMATE.  Hash identity: sha256 of the output text; outputs shorter than
MIN_HASH_CHARS are never hash-matched (trivial "(no output)" strings would dominate).

Inputs are read read-only, bounded to the byte length recorded in the manifest, so a transcript
that is still growing cannot change the digest.  Outputs are aggregate counts only (no content).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Iterable

CHARS_PER_TOKEN = 4
GRACE_ROUNDS = 2
KEEP_RECENT = 2  # mirrors _clear_stale_tool_outputs default
BASELINE_GATE_CHARS = 12000  # its max_context_tokens=0 heuristic gate
MIN_HASH_CHARS = 40
SHARE_THRESHOLD = 0.15
TEXT_REGRET_CAP = 200  # max evicted outputs text-checked per transcript (deterministic stride)
SIG_LINES = 5
SIG_MIN_LEN = 30

RULE = (
    "later read/edit of same path | re-run of same normalized command | later successful "
    "build with overlapping targets | passing re-run of same test command; candidate round = "
    "all outputs superseded and 2-round grace elapsed before end of segment; tokens=chars/4"
)

_BUILD_RE = re.compile(
    r"^(make|ninja|cmake\s+--build|cargo\s+(build|check)|npm\s+run\s+build|yarn\s+build|tsc|gradle|"
    r"mvn|go\s+build|python3?\s+setup\.py\s+(build|develop)|pip3?\s+install|uv\s+pip\s+install)\b"
)
_TEST_RE = re.compile(
    r"^(python3?\s+-m\s+)?(pytest|py\.test|unittest|tox|ctest|npm\s+(run\s+)?test|yarn\s+test|"
    r"cargo\s+test|go\s+test|make\s+test|bash\s+\S*test\S*)\b"
)
_FAIL_RE = re.compile(r"\d+\s+failed|\bFAILED\b|Traceback \(most recent|AssertionError|\bERROR\b")
_READ_CMDS = {"cat", "head", "tail", "less", "more", "nl", "bat"}


@dataclass
class Call:
    idx: int
    rnd: int
    kind: str  # read|edit|shell|search|test|build|other
    key: str  # path or normalized command
    targets: frozenset = frozenset()
    verb: str = ""
    text: str = ""
    err: bool = False
    in_chars: int = 0
    out_chars: int = 0
    sha: str = ""


@dataclass
class Segment:
    calls: list = field(default_factory=list)
    round_acts: dict = field(default_factory=dict)  # rnd -> assistant text + tool inputs
    other_chars: int = 0  # user/assistant prose chars not in calls
    n_rounds: int = 0


def _norm_path(p: str) -> str:
    p = os.path.normpath(str(p).strip())
    return p[len("/testbed/"):] if p.startswith("/testbed/") else p


_CD_PREFIX = re.compile(r"^\s*cd\s+\S+\s*(&&|;)\s*")
_TAIL_NOISE = re.compile(r"\s*(2>&1|2>/dev/null)\s*$")


def normalize_command(cmd: str) -> str:
    cmd = _CD_PREFIX.sub("", cmd or "")
    cmd = _TAIL_NOISE.sub("", cmd.strip())
    return re.sub(r"\s+", " ", cmd)


def classify_shell(cmd: str) -> tuple[str, str, frozenset, str]:
    """Return (kind, key, targets, verb) for a shell command string."""
    n = normalize_command(cmd)
    first = re.split(r"\s*(?:&&|;|\|\|)\s*", n, maxsplit=1)[0]
    pipe_head = first.split("|", 1)[0].strip()
    toks = pipe_head.split()
    if not toks:
        return "other", n, frozenset(), ""
    if _TEST_RE.match(pipe_head):
        return "test", n, frozenset(), "test"
    m = _BUILD_RE.match(pipe_head)
    if m:
        rest = pipe_head[m.end():].split()
        tg, skip = [], False
        for t in rest:
            if skip:
                skip = False
                continue
            if t in ("-j", "-C", "--target", "-t"):
                skip = True
                continue
            if t.startswith("-") or t.isdigit():
                continue
            tg.append(t)
        return "build", n, frozenset(tg), re.sub(r"\s+", " ", m.group(1))
    if toks[0] in _READ_CMDS or (toks[0] == "sed" and "-n" in toks and "-i" not in toks):
        args = [t for t in toks[1:] if not t.startswith("-") and not t.isdigit()
                and not re.fullmatch(r"\d+(,\d+)?p", t) and not t.startswith("'")]
        if args:
            return "read", _norm_path(args[-1]), frozenset(), ""
    return "shell", n, frozenset(), ""


def passing(call: Call) -> bool:
    return (not call.err) and not _FAIL_RE.search(call.text[:20000] + call.text[-4000:])


# ---------------------------------------------------------------- classifier

def supersession(seg: Segment) -> dict[int, int]:
    """Map call idx -> idx of the FIRST later call that supersedes it."""
    sup: dict[int, int] = {}
    live_key: dict[tuple, list] = {}
    live_build: list = []
    for c in seg.calls:
        if c.kind in ("read", "edit"):
            for i in live_key.pop(("path", c.key), []):
                sup.setdefault(i, c.idx)
            live_key.setdefault(("path", c.key), []).append(c.idx)
        elif c.kind in ("shell", "search"):
            for i in live_key.pop(("cmd", c.key), []):
                sup.setdefault(i, c.idx)
            live_key.setdefault(("cmd", c.key), []).append(c.idx)
        elif c.kind == "test":
            if passing(c):
                for i in live_key.pop(("test", c.key), []):
                    sup.setdefault(i, c.idx)
            live_key.setdefault(("test", c.key), []).append(c.idx)
        elif c.kind == "build":
            if not c.err:
                keep = []
                for i in live_build:
                    o = seg.calls[i]
                    ov = (o.verb == c.verb) and ((o.targets & c.targets) or (not o.targets and not c.targets))
                    if ov:
                        sup.setdefault(i, c.idx)
                    else:
                        keep.append(i)
                live_build = keep
            live_build.append(c.idx)
    return sup


def _tok(chars: int) -> float:
    return chars / CHARS_PER_TOKEN


def _sig_lines(text: str, other: str) -> list[str]:
    seen, out = set(), []
    for ln in sorted((l.strip() for l in text.splitlines()), key=len, reverse=True):
        if len(ln) >= SIG_MIN_LEN and ln not in seen and ln not in other:
            seen.add(ln)
            out.append(ln)
            if len(out) == SIG_LINES:
                break
    return out


def analyze_segment(seg: Segment) -> dict[str, Any]:
    calls = seg.calls
    res = dict(rounds=seg.n_rounds, calls=len(calls), out_chars=0, history_chars=0,
               cand_round_chars=0, cand_output_chars=0, cand_rounds=0, n_superseded=0,
               dedup_repeats=0, dedup_chars=0, evicted=0, evicted_info_losing=0,
               regret_hash=0, text_checked=0, regret_text=0,
               base_cleared_chars=0, base_evicted=0, base_regret_hash=0,
               overlap_chars=0, by_kind={})
    if not calls:
        res["history_chars"] = seg.other_chars
        return res
    out_chars = sum(c.out_chars for c in calls)
    res["out_chars"] = out_chars
    res["history_chars"] = seg.other_chars + out_chars + sum(c.in_chars for c in calls)
    last_round = max(c.rnd for c in calls)
    sup = supersession(seg)
    res["n_superseded"] = len(sup)
    for c in calls:
        if c.idx in sup:
            k = c.kind
            d = res["by_kind"].setdefault(k, [0, 0])
            d[0] += 1
            d[1] += c.out_chars
    # per-round candidate gate
    rounds: dict[int, list] = {}
    for c in calls:
        rounds.setdefault(c.rnd, []).append(c)
    evicted_at: dict[int, int] = {}
    for r, cs in rounds.items():
        if cs and all(c.idx in sup for c in cs):
            s_last = max(calls[sup[c.idx]].rnd for c in cs)
            if s_last + GRACE_ROUNDS <= last_round:
                res["cand_rounds"] += 1
                res["cand_round_chars"] += sum(c.out_chars for c in cs)
                for c in cs:
                    evicted_at[c.idx] = calls[sup[c.idx]].rnd + GRACE_ROUNDS
    res["cand_output_chars"] = sum(
        c.out_chars for c in calls if c.idx in sup and calls[sup[c.idx]].rnd + GRACE_ROUNDS <= last_round
    )
    # hash dedup
    seen: set[str] = set()
    for c in calls:
        if len(c.text) >= MIN_HASH_CHARS:
            if c.sha in seen:
                res["dedup_repeats"] += 1
                res["dedup_chars"] += c.out_chars
            seen.add(c.sha)
    # regret on supersession-evicted outputs
    by_sha: dict[str, list] = {}
    for c in calls:
        if len(c.text) >= MIN_HASH_CHARS:
            by_sha.setdefault(c.sha, []).append(c)
    ev = [calls[i] for i in sorted(evicted_at) if len(calls[i].text) >= MIN_HASH_CHARS]
    res["evicted"] = len(ev)
    info = [c for c in ev if calls[sup[c.idx]].sha != c.sha]
    res["evicted_info_losing"] = len(info)
    for c in info:
        if any(j.idx > c.idx and j.rnd >= evicted_at[c.idx] for j in by_sha.get(c.sha, [])):
            res["regret_hash"] += 1
    # secondary textual regret (bounded)
    if info:
        step = max(1, len(info) // TEXT_REGRET_CAP)
        sample = info[::step][:TEXT_REGRET_CAP]
        for c in sample:
            sigs = _sig_lines(c.text, calls[sup[c.idx]].text)
            if not sigs:
                continue
            res["text_checked"] += 1
            later = "\n".join(seg.round_acts.get(r, "") for r in range(evicted_at[c.idx], last_round + 1))
            if any(s in later for s in sigs):
                res["regret_text"] += 1
    # baseline: age-based clearing, keep_recent=2, 12000-char gate
    cum, outs = seg.other_chars, []
    base_evict_round: dict[int, int] = {}
    for c in calls:
        cum += c.out_chars + c.in_chars
        outs.append(c)
        if len(outs) > KEEP_RECENT and cum >= BASELINE_GATE_CHARS:
            for v in outs[:-KEEP_RECENT]:
                base_evict_round.setdefault(v.idx, c.rnd)
    res["base_cleared_chars"] = sum(calls[i].out_chars for i in base_evict_round)
    bev = [calls[i] for i in base_evict_round if len(calls[i].text) >= MIN_HASH_CHARS]
    res["base_evicted"] = len(bev)
    for c in bev:
        if any(j.idx > c.idx and j.rnd >= base_evict_round[c.idx] for j in by_sha.get(c.sha, [])):
            res["base_regret_hash"] += 1
    res["overlap_chars"] = sum(calls[i].out_chars for i in evicted_at if i in base_evict_round)
    return res


# ---------------------------------------------------------------- adapters

def _flat(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


def _mk(seg: Segment, rnd: int, kind: str, key: str, targets=frozenset(), verb="", in_chars=0) -> Call:
    c = Call(idx=len(seg.calls), rnd=rnd, kind=kind, key=key, targets=targets, verb=verb, in_chars=in_chars)
    seg.calls.append(c)
    return c


def _finish(c: Call, text: str, err: bool) -> None:
    c.text = text
    c.err = err
    c.out_chars = len(text)
    c.sha = hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()


def parse_claude_code(lines: Iterable[bytes]) -> tuple[list[Segment], dict]:
    segs, seg = [], Segment()
    pending: dict[str, Call] = {}
    cur_mid, rnd = None, -1
    meta = dict(first_ts=None, bad_lines=0, records=0)
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            d = json.loads(raw)
        except ValueError:
            meta["bad_lines"] += 1
            continue
        meta["records"] += 1
        if meta["first_ts"] is None and d.get("timestamp"):
            meta["first_ts"] = d["timestamp"]
        t = d.get("type")
        if t == "system" and d.get("subtype") == "compact_boundary" or d.get("isCompactSummary"):
            if seg.calls or seg.other_chars:
                seg.n_rounds = rnd + 1
                segs.append(seg)
            seg, pending, cur_mid, rnd = Segment(), {}, None, -1
            if d.get("isCompactSummary"):
                seg.other_chars += len(_flat((d.get("message") or {}).get("content")))
            continue
        msg = d.get("message")
        if t not in ("user", "assistant") or not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if t == "assistant":
            if not isinstance(content, list):
                continue
            mid = msg.get("id") or d.get("uuid")
            for b in content:
                if not isinstance(b, dict):
                    continue
                bt = b.get("type")
                if bt == "text":
                    ln = len(b.get("text", ""))
                    seg.other_chars += ln
                    seg.round_acts[max(rnd, 0)] = seg.round_acts.get(max(rnd, 0), "") + b.get("text", "")
                elif bt == "tool_use":
                    if mid != cur_mid:
                        cur_mid, rnd = mid, rnd + 1
                    inp = b.get("input") or {}
                    name = b.get("name", "")
                    ins = json.dumps(inp, ensure_ascii=False)
                    seg.round_acts[rnd] = seg.round_acts.get(rnd, "") + ins
                    if name == "Read":
                        c = _mk(seg, rnd, "read", _norm_path(inp.get("file_path", "")), in_chars=len(ins))
                    elif name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
                        c = _mk(seg, rnd, "edit", _norm_path(inp.get("file_path") or inp.get("notebook_path", "")),
                                in_chars=len(ins))
                    elif name == "Bash":
                        k, key, tg, vb = classify_shell(inp.get("command", ""))
                        c = _mk(seg, rnd, k, key, tg, vb, in_chars=len(ins))
                    elif name in ("Grep", "Glob"):
                        c = _mk(seg, rnd, "search", name + "|" + json.dumps(inp, sort_keys=True), in_chars=len(ins))
                    else:
                        c = _mk(seg, rnd, "other", name, in_chars=len(ins))
                    pending[b.get("id", "")] = c
        else:  # user
            if isinstance(content, str):
                seg.other_chars += len(content)
                continue
            if not isinstance(content, list):
                continue
            for b in content:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_result":
                    c = pending.pop(b.get("tool_use_id", ""), None)
                    if c is not None:
                        _finish(c, _flat(b.get("content")), bool(b.get("is_error")))
                elif b.get("type") == "text":
                    seg.other_chars += len(b.get("text", ""))
    # unmatched tool_use (no result recorded): finish empty so they stay in the denominator
    for c in pending.values():
        _finish(c, "", False)
    if seg.calls or seg.other_chars:
        seg.n_rounds = rnd + 1
        segs.append(seg)
    return segs, meta


def parse_bench(lines: Iterable[bytes]) -> tuple[list[Segment], dict]:
    seg = Segment()
    meta = dict(first_ts=None, bad_lines=0, records=0)
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            d = json.loads(raw)
        except ValueError:
            meta["bad_lines"] += 1
            continue
        meta["records"] += 1
        if "turn" not in d or "action" not in d:
            continue
        rnd = len(seg.calls)
        resp = "".join(r.get("text", "") for r in d.get("assistant_responses", []) if isinstance(r, dict))
        seg.round_acts[rnd] = resp
        act, cmd = d.get("action"), d.get("command") or ""
        ro = d.get("raw_observation")
        text = ro.get("text", "") if isinstance(ro, dict) else (ro or "")
        if act == "bash":
            k, key, tg, vb = classify_shell(cmd)
        elif act == "edit":
            k, key, tg, vb = "edit", _norm_path(cmd), frozenset(), ""
        else:
            k, key, tg, vb = "other", str(act), frozenset(), ""
        c = _mk(seg, rnd, k, key, tg, vb, in_chars=len(cmd))
        seg.other_chars += len(resp)
        try:
            err = int(d.get("exit", 0) or 0) != 0
        except (TypeError, ValueError):
            err = True
        _finish(c, text or "", err)
    seg.n_rounds = len(seg.calls)
    return [seg], meta


# ---------------------------------------------------------------- driver

SUM_KEYS = ["rounds", "calls", "out_chars", "history_chars", "cand_round_chars", "cand_output_chars",
            "cand_rounds", "n_superseded", "dedup_repeats", "dedup_chars", "evicted", "evicted_info_losing",
            "regret_hash", "text_checked", "regret_text", "base_cleared_chars", "base_evicted",
            "base_regret_hash", "overlap_chars"]


def analyze_file(path: str, size: int, adapter: str) -> dict[str, Any]:
    with open(path, "rb") as fh:
        data = fh.read(size)
    sha = hashlib.sha256(data).hexdigest()
    parse = parse_claude_code if adapter == "cc" else parse_bench
    segs, meta = parse(data.split(b"\n"))
    tot = {k: 0 for k in SUM_KEYS}
    by_kind: dict[str, list] = {}
    for sg in segs:
        r = analyze_segment(sg)
        for k in SUM_KEYS:
            tot[k] += r[k]
        for k, (n, ch) in r["by_kind"].items():
            d = by_kind.setdefault(k, [0, 0])
            d[0] += n
            d[1] += ch
    tot.update(sha256=sha, bytes=size, segments=len(segs), by_kind=by_kind,
               first_ts=meta["first_ts"], bad_lines=meta["bad_lines"], records=meta["records"])
    return tot


def _div(a: float, b: float) -> float | None:
    return round(a / b, 6) if b else None


def aggregate(rows: list[dict]) -> dict[str, Any]:
    t = {k: sum(r[k] for r in rows) for k in SUM_KEYS}
    h, o = t["history_chars"], t["out_chars"]
    bk: dict[str, list] = {}
    for r in rows:
        for k, (n, ch) in r["by_kind"].items():
            d = bk.setdefault(k, [0, 0])
            d[0] += n
            d[1] += ch
    return dict(
        transcripts=len(rows), transcripts_with_calls=sum(1 for r in rows if r["calls"]),
        transcripts_zero_calls=sum(1 for r in rows if not r["calls"]),
        rounds=t["rounds"], calls=t["calls"],
        history_tokens_est=int(_tok(h)), tool_output_tokens_est=int(_tok(o)),
        candidate_share_of_history=_div(t["cand_round_chars"], h),
        candidate_share_of_tool_output=_div(t["cand_round_chars"], o),
        candidate_rounds=t["cand_rounds"],
        per_output_superseded_share_of_tool_output=_div(t["cand_output_chars"], o),
        superseded_outputs=t["n_superseded"], superseded_by_kind={k: v[0] for k, v in sorted(bk.items())},
        dedup_repeat_count=t["dedup_repeats"], dedup_share_of_tool_output=_div(t["dedup_chars"], o),
        evicted_outputs=t["evicted"], evicted_info_losing=t["evicted_info_losing"],
        regret_hash_count=t["regret_hash"],
        regret_rate_hash_all_evicted=_div(t["regret_hash"], t["evicted"]),
        regret_rate_hash_info_losing=_div(t["regret_hash"], t["evicted_info_losing"]),
        regret_text_checked=t["text_checked"], regret_text_count=t["regret_text"],
        regret_rate_text_sampled=_div(t["regret_text"], t["text_checked"]),
        baseline_age_clear_share_of_history=_div(t["base_cleared_chars"], h),
        baseline_age_clear_share_of_tool_output=_div(t["base_cleared_chars"], o),
        baseline_evicted=t["base_evicted"],
        baseline_regret_rate_hash=_div(t["base_regret_hash"], t["base_evicted"]),
        overlap_share_of_supersession_candidates=_div(t["overlap_chars"], t["cand_output_chars"]),
        no_eviction_baseline_share=0.0,
        fires_m2=(_div(t["cand_round_chars"], h) or 0.0) >= SHARE_THRESHOLD,
        fires_m2_on_tool_output_share=(_div(t["cand_round_chars"], o) or 0.0) >= SHARE_THRESHOLD,
    )


def build_manifest(items: list[tuple[str, str, str]]) -> list[dict]:
    """items = (class, path, adapter); sizes frozen NOW; digest of path,size,sha is computed on analysis."""
    return [dict(cls=c, path=p, size=os.stat(p).st_size, adapter=a) for c, p, a in items]


def manifest_digest(rows: list[dict]) -> str:
    lines = sorted(f"{r['path']}\t{r['bytes']}\t{r['sha256']}" for r in rows)
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def cc_class(path: str) -> str:
    proj = os.path.basename(os.path.dirname(path))
    if proj in ("-workspace", "-mnt-raid0-llm-epyc-root", "-mnt-raid0-llm-epyc-orchestrator",
                "-mnt-raid0-llm-llama-cpp"):
        return "claude_code_primary"
    return "claude_code_worktree_tmp"


def holdout_flag(first_ts: str | None, path: str, cutoff: str) -> bool:
    if first_ts:
        return first_ts[:10] >= cutoff
    return _dt.datetime.fromtimestamp(os.stat(path).st_mtime, _dt.timezone.utc).strftime("%Y-%m-%d") >= cutoff


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cc-glob", default=os.path.expanduser("~/.claude/projects/*/*.jsonl"))
    ap.add_argument("--bench-glob", action="append", default=[])
    ap.add_argument("--holdout-after", default="2026-11-15")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    items = [(cc_class(p), p, "cc") for p in sorted(glob.glob(a.cc_glob))]
    for g in a.bench_glob:
        items += [("agentic_bench_bash_loop", p, "bench") for p in sorted(glob.glob(g))
                  if not p.endswith(".live-status.json")]
    man = build_manifest(items)
    rows = []
    for m in man:
        r = analyze_file(m["path"], m["size"], m["adapter"])
        r.update(cls=m["cls"], path=m["path"], holdout=holdout_flag(r["first_ts"], m["path"], a.holdout_after))
        rows.append(r)
    os.makedirs(a.out_dir, exist_ok=True)
    classes = sorted({r["cls"] for r in rows})
    summary = dict(
        rule=RULE, share_threshold=SHARE_THRESHOLD, grace_rounds=GRACE_ROUNDS, holdout_after=a.holdout_after,
        token_unit="chars/4 estimate", manifest_files=len(rows), manifest_digest_sha256=manifest_digest(rows),
        classes={c: aggregate([r for r in rows if r["cls"] == c]) for c in classes},
        holdout={c: aggregate([r for r in rows if r["cls"] == c and r["holdout"]]) for c in classes},
        pooled=aggregate(rows),
    )
    with open(os.path.join(a.out_dir, "per_transcript.jsonl"), "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    with open(os.path.join(a.out_dir, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
