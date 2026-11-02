#!/usr/bin/env python3
"""CAF-2 — AI-free wrap-up for a handoff session (churn-pipeline.md, "Churn AI-free mechanization").

    python3 scripts/coordination/churn/wrapup.py --json <file.json> [--lane <dir>] [--flags <dir>] [--dry-run]

Input = the ONE turn-record schema: {slug, state, task_text, ticks: [text], progress_md, paths: [], belief,
message, question, rows_published, trailers?: [lines]}. Steps (one log line each; the first failure stops with rc 1):
validate -> merge origin/main into the lane -> resolve ticks by TEXT (exactly one open box) -> progress append ->
flip ticks (`✅ <date> [belief: ...]`, SESSION_LIFECYCLE "Two axioms") -> index_state --check (handoffs/ touched) ->
pathspec commit with trailers -> serialized_push.py --repo <lane> (retry while lock-held) -> cherry empty ->
report.json (+wrapped_sha, wrapped_at) -> `WRAPPED <sha>` as the LAST stdout line. --dry-run prints the plan and
writes nothing. Stdlib only.

Invoked as a script, the work runs in a detached child (own session, log under
<flags>/handoff-sessions/<slug>/wrapup-*.log) that the caller follows; killing the caller
does not kill the wrap-up or orphan the push lock (main_detached).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
from flip_checkbox import CheckboxFlipError, _unified_diff  # noqa: E402  (shared refusal class + diff)

STATES = ("progress", "ready", "blocked", "failed", "idle", "dropped")
BELIEF_RX = re.compile(r"^(cc|clm_[A-Za-z0-9_-]+|no-belief: \S.*)$")
LANES_DIR = "/mnt/raid0/llm/worktrees/mains"
FLAGS_DEFAULT = "/mnt/raid0/llm/tmp/compute-flags"
PUSH_RETRIES, PUSH_SLEEP_S = 5, 20
OPEN_BOX_RX = re.compile(r"^\s*- \[ \] ")


class WrapupError(RuntimeError):
    pass


def log(step: str, msg: str) -> None:
    print(f"[wrapup] {step}: {msg}", flush=True)


def _git(lane: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", lane, *args], capture_output=True, text=True, timeout=600)


def _ok(r: subprocess.CompletedProcess, what: str) -> str:
    if r.returncode != 0:
        tail = (r.stderr or r.stdout).strip().splitlines()
        raise WrapupError(f"{what} failed: {tail[-1] if tail else 'rc %d' % r.returncode}")
    return r.stdout


def _now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


# ---------------------------------------------------------------- 1. validate
def validate(rec: dict) -> None:
    for k in ("slug", "state", "task_text", "ticks", "progress_md", "paths", "belief", "message"):
        if k not in rec:
            raise WrapupError(f"missing key {k!r}")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", str(rec["slug"])):
        raise WrapupError(f"bad slug {rec['slug']!r}")
    if rec["state"] not in STATES:
        raise WrapupError(f"bad state {rec['state']!r}; expected one of {'|'.join(STATES)}")
    if not isinstance(rec["belief"], str) or not BELIEF_RX.match(rec["belief"]):
        raise WrapupError(f"bad belief {rec['belief']!r}; expected cc | clm_<id> | 'no-belief: <reason>'")
    if not isinstance(rec["ticks"], list) or not all(isinstance(t, str) and t.strip() for t in rec["ticks"]):
        raise WrapupError("ticks must be a list of non-empty strings")
    if not isinstance(rec["paths"], list) or not all(isinstance(p, str) and p and not p.startswith("/") for p in rec["paths"]):
        raise WrapupError("paths must be lane-relative strings")
    if not str(rec["message"]).strip():
        raise WrapupError("empty commit message")
    if not isinstance(rec.get("trailers", []), list):
        raise WrapupError("trailers must be a list of lines")


# ------------------------------------------------------------------- 2. merge
def merge_main(lane: str) -> str:
    if not os.path.isdir(lane) or _git(lane, "rev-parse", "--is-inside-work-tree").returncode != 0:
        raise WrapupError(f"lane {lane} is not a git worktree")
    _ok(_git(lane, "fetch", "-q", "origin"), "fetch")
    if _git(lane, "merge", "-q", "--ff-only", "origin/main").returncode == 0:
        return "fast-forwarded"
    r = _git(lane, "merge", "--no-edit", "origin/main")
    if r.returncode != 0:
        _git(lane, "merge", "--abort")
        raise WrapupError(f"merge conflict with origin/main: {(r.stdout + r.stderr).strip().splitlines()[-1]}")
    return "merged"


# ------------------------------------------------------------------- 4. ticks
def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def resolve_ticks(lane: str, ticks: list[str], extra_md: list[str]) -> list[tuple[str, int, str]]:
    """Each tick text must match EXACTLY ONE open `- [ ]` line across handoffs/**/*.md (+ listed .md paths)."""
    files = sorted({os.path.join(dp, f) for sub in ("handoffs/active", "handoffs/blocked")
                    for dp, _, fs in os.walk(os.path.join(lane, sub)) for f in fs if f.endswith(".md")}
                   | {os.path.join(lane, p) for p in extra_md if p.endswith(".md") and os.path.isfile(os.path.join(lane, p))})
    boxes = [(f, i, ln) for f in files for i, ln in enumerate(open(f, encoding="utf-8").read().splitlines())
             if OPEN_BOX_RX.match(ln)]
    out = []
    for t in ticks:
        hits = [b for b in boxes if _norm(t) in _norm(b[2])]
        if len(hits) != 1:
            where = "; ".join(f"{os.path.relpath(h[0], lane)}:{h[1] + 1}" for h in hits[:5])
            raise CheckboxFlipError(f"tick {t!r} matches {len(hits)} open boxes (need exactly 1){': ' + where if where else ''}")
        out.append(hits[0])
    return out


def belief_tag(belief: str) -> str:
    return f"[{belief}]" if belief.startswith("no-belief:") else f"[belief: {belief}]"


def apply_ticks(lane: str, hits: list[tuple[str, int, str]], date: str, belief: str) -> list[str]:
    touched: list[str] = []
    for f, i, _ in hits:
        before = open(f, encoding="utf-8").read()
        lines = before.split("\n")
        ln = lines[i].replace("- [ ]", "- [x]", 1).rstrip() + f" ✅ {date}"
        if "[belief:" not in ln and "[no-belief:" not in ln:
            ln += " " + belief_tag(belief)
        lines[i] = ln
        after = "\n".join(lines)
        open(f, "w", encoding="utf-8").write(after)
        rel = os.path.relpath(f, lane)
        log("tick", _unified_diff(before, after, rel).splitlines()[-1])
        touched.append(rel)
    return touched


# ---------------------------------------------------------------- 3. progress
def progress_target(lane: str, slug: str, now: _dt.datetime) -> str:
    return os.path.join("progress", now.strftime("%Y-%m"), f"{now.strftime('%Y-%m-%d')}-handoff-{slug}.md")


def append_progress(lane: str, rel: str, slug: str, task_text: str, body: str, now: _dt.datetime) -> None:
    p = os.path.join(lane, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    head = "" if os.path.exists(p) else f"# {now.strftime('%Y-%m-%d')} — handoff {slug}\n"
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(f"{head}\n## {now.strftime('%H:%MZ')} — {task_text}\n\n{body.rstrip()}\n")


# ------------------------------------------------------- 5/7. external steps (patchable in tests)
def run_index_check(lane: str) -> tuple[int, str]:
    r = subprocess.run([sys.executable, os.path.join(lane, "scripts/handoffs/index_state.py"), "--check"],
                       cwd=lane, capture_output=True, text=True, timeout=900)
    return r.returncode, r.stdout + r.stderr


def run_push(lane: str, slug: str) -> tuple[int, str]:
    r = subprocess.run([sys.executable, os.path.join(lane, "scripts/coordination/serialized_push.py"), "--agent",
                        f"handoff-{slug}", "--repo", lane, "--fetch", "--push"], capture_output=True, text=True, timeout=900)
    return r.returncode, r.stdout + r.stderr


def push_with_retry(lane: str, slug: str) -> None:
    for n in range(1, PUSH_RETRIES + 1):
        rc, out = run_push(lane, slug)
        if rc == 0:
            return
        if "lock-held" in out and n < PUSH_RETRIES:
            log("push", f"lock held, retry {n}/{PUSH_RETRIES} in {PUSH_SLEEP_S}s")
            time.sleep(PUSH_SLEEP_S)
            continue
        raise WrapupError(f"serialized_push rc={rc}: {out.strip().splitlines()[-1] if out.strip() else 'no output'}")


# --------------------------------------------------------------------- 6. commit
def commit(lane: str, pathspec: list[str], message: str, trailers: list[str]) -> str:
    _ok(_git(lane, "add", "--", *pathspec), "git add")
    if not _git(lane, "diff", "--cached", "--quiet").returncode:
        raise WrapupError("nothing staged under the pathspec")
    text = message.rstrip() + ("\n\n" + "\n".join(trailers) if trailers else "") + "\n"
    r = subprocess.run(["git", "-C", lane, "commit", "-q", "-F", "-", "--", *pathspec], input=text,
                       capture_output=True, text=True, timeout=600)
    _ok(r, "git commit")
    return _ok(_git(lane, "rev-parse", "HEAD"), "rev-parse").strip()


def write_report(flags: str, slug: str, rec: dict) -> str:
    d = os.path.join(flags, "handoff-sessions", slug)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "report.json")
    tmp = p + f".tmp{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, p)
    return p


# ------------------------------------------------------------------------ main
def run(rec: dict, lane: str, flags: str, dry_run: bool) -> int:
    validate(rec)
    slug, now = rec["slug"], _now()
    date = now.strftime("%Y-%m-%d")
    log("validate", f"slug={slug} state={rec['state']} ticks={len(rec['ticks'])} paths={len(rec['paths'])}")
    log("merge", merge_main(lane))
    hits = resolve_ticks(lane, rec["ticks"], rec["paths"])
    for (f, i, ln), t in zip(hits, rec["ticks"]):
        log("resolve", f"{os.path.relpath(f, lane)}:{i + 1} <- {t!r}")
    prog = progress_target(lane, slug, now)
    pathspec = sorted(set(rec["paths"]) | {prog} | {os.path.relpath(h[0], lane) for h in hits})
    handoffs_touched = any(p.startswith("handoffs/") for p in pathspec)
    if dry_run:
        log("dry-run", f"would append progress to {prog}, tick {len(hits)} box(es) with {belief_tag(rec['belief'])}, "
                       f"{'run' if handoffs_touched else 'skip'} index_state --check, commit pathspec {pathspec}, "
                       f"push lane {lane} as handoff-{slug}, write {os.path.join(flags, 'handoff-sessions', slug, 'report.json')}")
        print("DRY-RUN OK")
        return 0
    append_progress(lane, prog, slug, rec["task_text"], rec["progress_md"], now)
    log("progress", prog)
    apply_ticks(lane, hits, date, rec["belief"])
    if handoffs_touched:
        rc, out = run_index_check(lane)
        if rc != 0:
            raise WrapupError(f"index_state --check rc={rc}: {out.strip().splitlines()[-1] if out.strip() else ''}")
        log("index", "index_state --check ok")
    else:
        log("index", "skipped (no handoffs/ path touched)")
    sha = commit(lane, pathspec, rec["message"], [str(t) for t in rec.get("trailers", [])])
    log("commit", f"{sha[:12]} {len(pathspec)} path(s)")
    push_with_retry(lane, slug)
    log("push", "serialized_push ok")
    _git(lane, "fetch", "-q", "origin")
    left = _ok(_git(lane, "cherry", "origin/main"), "cherry").strip()
    if left:
        raise WrapupError(f"cherry origin/main not empty after push: {left.splitlines()[0]}")
    log("cherry", "empty")
    out = dict(rec, wrapped_sha=sha, wrapped_at=_now().strftime("%Y-%m-%dT%H:%M:%SZ"))
    log("report", write_report(flags, slug, out))
    print(f"WRAPPED {sha}", flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", required=True)
    ap.add_argument("--lane")
    ap.add_argument("--flags", default=FLAGS_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    try:
        rec = json.load(open(a.json, encoding="utf-8"))
        if not isinstance(rec, dict):
            raise WrapupError("JSON top level must be an object")
        lane = a.lane or os.path.join(LANES_DIR, f"h-{rec.get('slug', '?')}")
        return run(rec, os.path.abspath(lane), a.flags, a.dry_run)
    except (WrapupError, CheckboxFlipError, OSError, ValueError) as exc:
        print(f"[wrapup] FAIL: {exc}", file=sys.stderr, flush=True)
        return 1


def main_detached(argv=None) -> int:
    """Run the wrap-up in its OWN session, then follow it.

    Why (D9, 2026-11-01): handoff-codex-gen ran this inside a Codex exec tool call
    with yield_time_ms=10000. The wrap-up outlived the yield, the model ended its turn,
    and `codex exec` exiting tore down the still-running command — twice (23:16:49Z,
    23:44:12Z), each time ~1s after serialized_push had taken the push lock, so the
    lock was orphaned and the commit never landed. Detached with start_new_session,
    the real work survives whatever kills its caller's process group; the caller
    merely stops watching. The dispatcher (`wrapped()` in handoff_sessions.py) lands
    a clean lane's unlanded commit if nobody is left to read `WRAPPED <sha>`.
    """
    argv = sys.argv[1:] if argv is None else list(argv)
    if os.environ.get("WRAPUP_INNER") == "1" or "--dry-run" in argv or "-h" in argv or "--help" in argv:
        return main(argv)
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--json")
    ap.add_argument("--flags", default=FLAGS_DEFAULT)
    a, _ = ap.parse_known_args(argv)
    try:
        slug = json.load(open(a.json, encoding="utf-8")).get("slug") or "unknown"
        d = os.path.join(a.flags, "handoff-sessions", str(slug))
        os.makedirs(d, exist_ok=True)
    except (OSError, ValueError, TypeError, AttributeError):
        return main(argv)  # let the normal path report the bad input
    logp = os.path.join(d, f"wrapup-{_now().strftime('%Y%m%dT%H%M%SZ')}-{os.getpid()}.log")
    with open(logp, "w", encoding="utf-8") as fh:
        child = subprocess.Popen([sys.executable, os.path.abspath(__file__), *argv], stdin=subprocess.DEVNULL,
                                 stdout=fh, stderr=subprocess.STDOUT, start_new_session=True,
                                 env=dict(os.environ, WRAPUP_INNER="1"))
    log("detached", f"pid={child.pid} log={logp} (keeps running if this call is killed)")
    with open(logp, encoding="utf-8") as rd:
        while True:
            line = rd.readline()
            if line:
                sys.stdout.write(line)
                sys.stdout.flush()
                continue
            if child.poll() is not None:
                rest = rd.read()
                if rest:
                    sys.stdout.write(rest)
                    sys.stdout.flush()
                return child.returncode
            time.sleep(0.2)


if __name__ == "__main__":
    sys.exit(main_detached())
