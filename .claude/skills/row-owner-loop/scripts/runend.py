#!/usr/bin/env python3
"""runend.py — owner-side run-end triage for one rowflow row (row-owner-loop skill, step 4).

  runend.py <row>                 draft <rowdir>/verdict.json from out/RESULT.json + grants/<row>.ended
  runend.py <row> --gate-eval     draft it with the deterministic gate evaluator instead (AKPL-P1, no LLM):
                                  epyc-inference-research autokernel.loop.gate_eval — graph_kld_policy.json,
                                  bench speed floors, PPL contract, declared-verdict vocabulary
  runend.py <row> --gate-eval --file
                                  ZERO-LLM filing: draft with gate_eval and, when the evaluator marks the verdict
                                  policy_decided (policy gate, lifecycle, the no-result rule, a polar token), file
                                  it at once; otherwise write the draft and exit 4 (owner review)
  runend.py <row> --file          after review: run file_result.py from a pinned detached origin/main
                                  worktree, confirm filing-done/<row>.FILED, print the tick-line draft
  runend.py --check-cc <file.md>  list `[belief: cc]` lines in <file.md> with no register row

Verdict mapping (mirrors file_result.coerce_declared_nonpass, stricter): a native verdict or ended
reason that declares DROP / FUTILITY* / STOPPED / INCONCLUSIVE / rc 75 / rc 143 / partial is NEVER
`pass`; FAIL* / crash -> fail; PASS / KEEP -> pass only when the run ended reason=complete.
The draft's rationale must cite at least one number (lint_verdict refuses one that doesn't).

NO RESULT -> NO CLAIM (operator ruling 2026-11-21): a row with no finished RESULT files SUPERSEDED (a successor
row exists) or WITHDRAWN, never inconclusive; inconclusive is for a row that ran but could not decide.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time

TMP = "/mnt/raid0/llm/tmp"
FLAGS = "/mnt/raid0/llm/tmp/compute-flags"
ROOT = "/workspace"
REGISTER_REL = "data/belief/committed_conclusions.jsonl"

NONPASS = re.compile(r"\b(DROP|FUTILITY\w*|STOPPED|INCONCLUSIVE|NOT_ATTRIBUTED|diagnostic|partial)\b", re.I)
FAILISH = re.compile(r"\b(FAIL\w*|crash\w*|REFUSED|ERROR)\b", re.I)
PASSISH = re.compile(r"^\s*(PASS|KEEP|CALIBRATED)\b", re.I)
NUMBER = re.compile(r"\d")


def parse_ended(text: str) -> dict:
    out = {}
    for tok in re.split(r"\s+", text.strip()):
        if "=" in tok:
            k, v = tok.split("=", 1)
            out[k] = v
    return out


def map_verdict(native: str, ended: dict | None = None) -> str:
    """native RESULT verdict string (+ .ended record) -> pass | fail | inconclusive. Never pass on a non-pass."""
    native = (native or "").strip()
    ended = ended or {}
    rc = str(ended.get("rc", "0"))
    reason = ended.get("reason", "complete")
    if rc in ("75", "143") or (reason and reason != "complete"):
        return "fail" if FAILISH.search(native) and not NONPASS.search(native) else "inconclusive"
    if not native:
        return "inconclusive"
    if FAILISH.search(native) and not NONPASS.search(native):
        return "fail"
    if NONPASS.search(native):
        # DROP(futility) is a measured negative for the hypothesis, but it is not a `pass`; an
        # explicitly declared DROP with a measured number files fail, everything else inconclusive.
        return "fail" if re.match(r"^\s*DROP\b", native, re.I) else "inconclusive"
    if PASSISH.match(native):
        return "pass"
    return "inconclusive"


def lint_verdict(v: dict) -> list[str]:
    errs = []
    if v.get("verdict") not in ("pass", "fail", "inconclusive"):
        errs.append(f"verdict must be pass|fail|inconclusive, got {v.get('verdict')!r}")
    rat = str(v.get("rationale") or "")
    if not NUMBER.search(rat):
        errs.append("rationale cites no number")
    if v.get("verdict") == "pass" and NONPASS.search(rat + " " + str(v.get("answer") or "")):
        errs.append("pass with a DROP/FUTILITY/STOPPED/diagnostic rationale (files inconclusive)")
    if "TODO" in rat:
        errs.append("rationale still has TODO")
    return errs


def row_dir(row: str, flags: str = FLAGS, loader=None) -> str:
    """The row's working dir. `<tmp>/<row>` when it exists; else resolved from the manifest's workdir, scratch_root
    or result_path (r8b: tf1-cpu-r8b-canary-35b-q0q2-20261122 lives in taskflow-stage1-cpu-r8-20261120, and the
    old `<tmp>/<row>` assumption crashed --file). Falls back to `<tmp>/<row>` when nothing resolves."""
    d = os.path.join(TMP, row)
    if os.path.isdir(d):
        return d
    m = {}
    try:
        if loader is None:
            sys.path.insert(0, os.path.realpath(CHURN))
            import filing
            loader = filing.load_manifest
        m = (loader(flags, row) or (None, {}))[1] or {}
    except Exception:   # noqa: BLE001 - best effort; the caller reports the missing file
        m = {}
    cands = [m.get("workdir"), m.get("scratch_root")]
    rp = str(m.get("result_path") or "")
    if rp:
        rd = os.path.dirname(rp)
        cands.append(os.path.dirname(rd) if os.path.basename(rd) == "out" else rd)
    for c in cands:
        if c and os.path.isabs(str(c)) and os.path.isdir(str(c)):
            return str(c)
    return d


def complete_result(row: str) -> dict | None:
    """The keeper's no-requeue rule (smoke_verdict.complete_result): complete: true + polar or a verdict, not a smoke,
    read from <scratch_root|workdir>/out/RESULT.json or the declared result_path. None when absent/incomplete/on error.
    Rows sealed by the old verdict-prefix check_complete ended rc=75 with such a RESULT and were misfiled WITHDRAWN."""
    try:
        m = {}
        try:
            sys.path.insert(0, os.path.realpath(CHURN))
            import filing
            m = (filing.load_manifest(FLAGS, row) or (None, {}))[1] or {}
        except Exception:   # noqa: BLE001 - manifest is best effort; the row dir still resolves
            m = {}
        m = dict(m)
        m.setdefault("workdir", row_dir(row))
        sys.path.insert(0, os.path.join(os.path.realpath(CHURN), "..", "rowflow"))
        import smoke_verdict
        return smoke_verdict.complete_result(m)
    except Exception:   # noqa: BLE001
        return None


def draft(row: str) -> dict:
    d = row_dir(row)
    res = json.load(open(os.path.join(d, "out", "RESULT.json")))
    ep = os.path.join(FLAGS, "grants", f"{row}.ended")
    ended = parse_ended(open(ep).read()) if os.path.exists(ep) else {}
    if ended and complete_result(row):
        ended = {}   # a complete RESULT beats the .ended rc/reason (rc=75 from the old check_complete)
    native = str(res.get("verdict") or "")
    v = map_verdict(native, ended)
    nums = {k: res[k] for k in res if isinstance(res[k], (int, float)) and not isinstance(res[k], bool)}
    rat = f"RESULT {native or '(none)'}; ended rc={ended.get('rc', '?')} reason={ended.get('reason', '?')}"
    if nums:
        rat += "; " + ", ".join(f"{k}={nums[k]}" for k in list(nums)[:8])
    rat += ". TODO: cite the numbers the pre-registered RULE decided on."
    return {"verdict": v, "rationale": rat, "native_verdict": native, "answer": "TODO"}


RESEARCH_KERNEL_RND = os.environ.get("AK_RESEARCH_KERNEL_RND",
                                    "/mnt/raid0/llm/epyc-inference-research/scripts/kernel_rnd")


CHURN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "scripts", "coordination", "churn")


def successor(row: str, flags: str = FLAGS) -> str | None:
    """The row's successor (filing.no_result_successor), or None. Best effort: None on any import/read failure."""
    try:
        sys.path.insert(0, os.path.realpath(CHURN))
        import filing
        return filing.no_result_successor(flags, row)
    except Exception:   # noqa: BLE001
        return None


def gate_eval_draft(row: str, kernel_rnd: str = RESEARCH_KERNEL_RND) -> dict:
    """verdict.json draft from autokernel.loop.gate_eval (pure, deterministic). Raises on evaluator failure."""
    res = os.path.join(row_dir(row), "out", "RESULT.json")
    ep = os.path.join(FLAGS, "grants", f"{row}.ended")
    cmd = [sys.executable, "-m", "autokernel.loop.gate_eval", res, "--row", row]
    if os.path.exists(ep) and not complete_result(row):   # complete RESULT: rc is not evidence of "no result"
        cmd += ["--ended", ep]
    succ = successor(row)
    if succ and not complete_result(row):
        cmd += ["--successor", succ]
    out = subprocess.run(cmd, cwd=kernel_rnd, capture_output=True, text=True, timeout=120, check=True).stdout
    g = json.loads(out)
    return {"verdict": g["filed_verdict"], "rationale": f"gate_eval {g['gate_id']} ({g['verdict']}): {g['rationale']}",
            "native_verdict": g.get("native_verdict") or "", "answer": g["verdict"], "gate_eval": g,
            "drafted_by": "gate_eval", "policy_decided": bool(g.get("policy_decided")),
            "superseded_by": g.get("successor"), "filed_by": "runend --gate-eval (policy-decided, 0 LLM turns)"}


def tick_line(row: str, v: dict, sha: str = "<commit>") -> str:
    tag = "[belief: cc]"
    return (f"- [x] (YYYY-MM-DD, <owner>) row `{row}` **{v.get('native_verdict') or v['verdict'].upper()}**"
            f" (filed {v['verdict']}): {v['rationale']} Evidence: `{row_dir(row)}/out/RESULT.json`, {sha}. {tag}")


def file_row(row: str, owner: str, run=subprocess.run) -> int:
    vpath = os.path.join(row_dir(row), "verdict.json")
    v = json.load(open(vpath))
    terminal = v.get("verdict") in ("SUPERSEDED", "WITHDRAWN")
    errs = [] if terminal else lint_verdict(v)
    if errs:
        print("REFUSED verdict.json: " + "; ".join(errs))
        return 2
    run(["git", "-C", ROOT, "fetch", "-q", "origin"], check=True)
    # unique NON-EXISTENT path (git worktree add creates it): no mkdtemp + rmdir, whose delete primitive the
    # destructive-scratch hook matched on this file's text and blocked even `--check-cc` (AK 2026-11-24)
    wt = os.path.join(TMP, f"runend-{row}-{os.getpid()}-{time.time_ns()}")
    run(["git", "-C", ROOT, "worktree", "add", "--detach", wt, "origin/main"], check=True, stdout=subprocess.DEVNULL)
    try:
        # file_result.py takes {verdict: SUPERSEDED|WITHDRAWN, superseded_by, rationale} through --verdict-json too
        rc = run([sys.executable, os.path.join(wt, "scripts/coordination/churn/file_result.py"), row,
                  "--verdict-json", vpath, "--filed-by", owner]).returncode
    finally:
        run(["git", "-C", ROOT, "worktree", "remove", wt])
    filed = os.path.join(FLAGS, "filing-done", f"{row}.FILED")
    if rc != 0 or not os.path.exists(filed):
        print(f"NOT FILED rc={rc} ({filed} missing)")
        return 1
    print(f"FILED {filed}")
    print("tick draft (re-read the box's done-when first):")
    print(tick_line(row, v))
    print("then: register row via `python3 scripts/vidya/cli.py conclusion add …` and re-arm watch_rows.sh")
    return 0


def stop_parked(row: str) -> bool:
    """Use the keeper's decision so owner pauses are never sent to the evaluator."""
    sys.path.insert(0, os.path.realpath(os.path.join(CHURN, "..", "rowflow")))
    import rowflow
    if rowflow.autorequeue_decision(FLAGS, row)[0] == "stop-parked":
        print(f"STOP-PARKED {row} (resumable; owner stop); not filed")
        return True
    return False


def auto_file(row: str, owner: str, force: bool = False, draft_fn=None, file_fn=None) -> int:
    """`--gate-eval --file`: zero-LLM filing of a policy-decided verdict; anything else -> draft + exit 4."""
    if stop_parked(row):
        return 0
    v = (draft_fn or gate_eval_draft)(row)
    vpath = os.path.join(row_dir(row), "verdict.json")
    if os.path.exists(vpath) and not force:
        print(f"{vpath} exists (owner draft); review it and run --file, or pass --force-draft")
        return 1
    with open(vpath, "w") as f:
        json.dump(v, f, indent=1)
    if not v.get("policy_decided"):
        print(f"OWNER-REVIEW {row}: {v['verdict']} via {v['gate_eval'].get('gate_id')} is not policy-decided; "
              f"draft at {vpath}, review then --file")
        return 4
    print(f"AUTO-FILE {row}: {v['verdict']} ({v['gate_eval'].get('gate_id')}), 0 LLM turns")
    return (file_fn or file_row)(row, owner)


def check_cc(md: str, repo: str = ROOT) -> list[tuple[int, str]]:
    reg = os.path.join(repo, REGISTER_REL)
    quotes = []
    if os.path.exists(reg):
        for line in open(reg):
            try:
                quotes.append(re.sub(r"\s+", " ", json.loads(line)["anchor"]["quote"]))
            except (ValueError, KeyError):
                pass
    missing = []
    for n, line in enumerate(open(md), 1):
        if "[belief: cc]" not in line:
            continue
        frag = re.sub(r"\s+", " ", line).strip()[2:90]
        if not any(frag in q for q in quotes):
            missing.append((n, line.strip()[:120]))
    return missing


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("row", nargs="?")
    ap.add_argument("--file", action="store_true")
    ap.add_argument("--owner", default="autokernel")
    ap.add_argument("--check-cc", metavar="FILE_MD")
    ap.add_argument("--force-draft", action="store_true", help="overwrite an existing verdict.json draft")
    ap.add_argument("--gate-eval", action="store_true", help="draft with the deterministic gate evaluator (no LLM)")
    a = ap.parse_args(argv)
    if a.check_cc:
        miss = check_cc(a.check_cc)
        for n, t in miss:
            print(f"NO-REGISTER-ROW {a.check_cc}:{n} {t}")
        return 1 if miss else 0
    if not a.row:
        ap.error("row required")
    if a.file and a.gate_eval:
        return auto_file(a.row, a.owner, a.force_draft)
    if a.file:
        return file_row(a.row, a.owner)
    if a.gate_eval and stop_parked(a.row):
        return 0
    vpath = os.path.join(row_dir(a.row), "verdict.json")
    if os.path.exists(vpath) and not a.force_draft:
        print(f"{vpath} exists; review it or pass --force-draft")
        return 1
    v = gate_eval_draft(a.row) if a.gate_eval else draft(a.row)
    if v["verdict"] in ("SUPERSEDED", "WITHDRAWN"):
        print(f"LIFECYCLE {a.row}: {v['verdict']} — {v['rationale']}; not a filable pass/fail/inconclusive draft")
        return 3
    with open(vpath, "w") as f:
        json.dump(v, f, indent=1)
    print(f"DRAFT {vpath}: verdict={v['verdict']} (native {v['native_verdict']!r}); edit rationale/answer, then --file")
    return 0


if __name__ == "__main__":
    sys.exit(main())
