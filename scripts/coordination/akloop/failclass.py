#!/usr/bin/env python3
"""failclass.py - AK parallel-loop P5(b): AK-FAILRULE-1 as deterministic rules over RESULT.json / FAIL-N.json + launcher.out.

Taxonomy (AK-FAILRULE-1, /mnt/raid0/llm/tmp/ak-failrule1-20261106/REPORT.md: compile, correctness_gate, timing_loss,
noise, harness_error, other) folded to the one split that decides who acts:

    side=harness    the pipeline / job wiring / instrument failed; the CANDIDATE was never judged. Routes to the
                    pipeline inbox (notify.emit, owner pipeline-mgmt). klass: admission_refused, launcher_not_started,
                    no_ended_record, residency_unproven, build_missing, job_script_error, smoke_wiring, result_contract,
                    window_or_stop, instrument_noise, incomplete_run
    side=candidate  the candidate was judged and lost. klass: compile, correctness_gate, timing_loss, noise
    side=ok         not a failure (PASS/KEEP/complete...). Never routed.
    side=unknown    no rule fires. The optional cheap-model fallback (set_fallback) is an INTERFACE ONLY: nothing registers
                    one, so unknown stays unknown.

Rules are ordered, first match wins, and every Classification names its rule. Pure functions; routing is separate.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict, field

SIDES = ("harness", "candidate", "ok", "unknown")


@dataclass
class Classification:
    side: str
    klass: str
    rule: str
    evidence: str = ""
    row_id: str = ""
    source: str = ""

    def to_dict(self):
        return asdict(self)


def _c(side, klass, rule, ev=""):
    return Classification(side, klass, rule, ev[:240])


# ---- fallback interface (UNWIRED) -----------------------------------------------------------------------------
class FallbackClassifier:
    """Interface for a cheap-model fallback. classify() gets the unknown record's compact payload and returns a
    Classification, or None to leave it unknown. Nothing in this repo registers one."""

    def classify(self, payload: dict):  # pragma: no cover - interface
        raise NotImplementedError


_FALLBACK = None


def set_fallback(fb):
    """Register a FallbackClassifier (or None to clear). Deliberately never called by this module."""
    global _FALLBACK
    _FALLBACK = fb


def _resolve_unknown(c: Classification, payload):
    if _FALLBACK is None or c.side != "unknown":
        return c
    try:
        r = _FALLBACK.classify(payload)
    except Exception:  # noqa: BLE001 - a broken fallback must not break the deterministic path
        return c
    if isinstance(r, Classification) and r.side in SIDES:
        r.rule = "fallback:" + (r.rule or "model")
        return r
    return c


# ---- launcher.out / text rules (shared) -----------------------------------------------------------------------
# (regex, side, klass, rule)  - applied to the job's own error output.
JOB_TEXT_RULES = [
    (r"undefined reference|\bld returned|make: \*\*\*|ninja: build stopped|\.(?:c|cc|cpp|cu|cuh|h|hpp):\d+(?::\d+)?: (?:fatal )?error:|"
     r"fatal error: [^\n]*\.h", "candidate", "compile", "text:compile-error"),
    (r"REJECT_CORRECTNESS|correctness gate|oracle (?:mismatch|fail)|bit-?exact[^\n]*(?:fail|differ)|NMSE[^\n]*>|"
     r"max_abs[^\n]*>|numerical mismatch|MISMATCH", "candidate", "correctness_gate", "text:correctness"),
    (r"\bNO_MOVE\b|within (?:the )?floor|effect_within_floor|decisive_regression|speedup[^\n]*<", "candidate",
     "timing_loss", "text:timing"),
    (r"compile failed rc=|CalledProcessError: Command '\['cmake', '--build'", "candidate", "compile", "text:build-failed"),
    (r"already in use|address already in use|Address already in use", "harness", "build_missing", "text:port-in-use"),
    (r"RowflowClaimError|region-lock: |wrong GPU host affinity|image metadata changed|missing own-PID GPU witness|"
     r"owned server exited before health|Remote end closed connection|fl_wait_own_port|venv python not found",
     "harness", "job_script_error", "text:pipeline-env"),
    (r"Traceback \(most recent call last\)[\s\S]{0,2500}?(?:NameError|ImportError|ModuleNotFoundError|FileNotFoundError|"
     r"AttributeError|KeyError|TypeError|PermissionError|OSError)", "harness", "job_script_error", "text:script-traceback"),
    (r"Argument list too long|argv too long|scratch[_ ]dir|destination[^\n]*already exists|Permission denied|"
     r"No such file or directory", "harness", "job_script_error", "text:env-error"),
    (r"smoke requires|AssertionError\('smoke", "harness", "smoke_wiring", "text:smoke-precondition"),
    (r"ServerDied|HTTP Error 5\d\d|Connection refused|server died|Internal Server Error", "harness", "job_script_error",
     "text:serving-infra"),
    (r"CUDA error|HIP error|out of memory|OOM|Killed\b", "harness", "job_script_error", "text:resource"),
]
_JOB_RULES = [(re.compile(p), s, k, r) for (p, s, k, r) in JOB_TEXT_RULES]


def classify_text(text):
    if not text:
        return None
    for rx, side, klass, rule in _JOB_RULES:
        m = rx.search(text)
        if m:
            return _c(side, klass, rule, m.group(0).replace("\n", " "))
    return None


# ---- server-log crash override ---------------------------------------------------------------------------------
# A dropped connection (RemoteDisconnected / "Remote end closed connection" / refused / reset) is usually the SYMPTOM of
# a llama-server that crashed under the candidate; the server log, not the client text, names the cause.
_DROP = re.compile(r"RemoteDisconnected|Remote end closed connection|Connection (?:refused|reset)|ConnectionResetError|"
                   r"ServerDied|server died", re.I)
_CRASH = re.compile(r"GGML_ASSERT|Segmentation fault|\bAborted\b|core dumped|terminate called|"
                    r"(?:HIP|ROCm|hipError|HSA)[^\n]{0,60}(?:fatal|error|abort|fault)|Memory access fault", re.I)


def scan_server_crash(row_dir):
    """First crash-marker line in out/logs/*server*.log or out/servers/* under row_dir, as (marker, line, file) or None."""
    import glob  # noqa: PLC0415
    if not row_dir:
        return None
    paths = sorted(set(glob.glob(os.path.join(row_dir, "out", "logs", "*server*.log")) +
                       glob.glob(os.path.join(row_dir, "out", "servers", "*")) +
                       glob.glob(os.path.join(row_dir, "out", "servers", "*", "*"))))
    for pth in paths:
        if not os.path.isfile(pth):
            continue
        try:
            with open(pth, errors="replace") as f:
                for ln in f:
                    m = _CRASH.search(ln)
                    if m:
                        return m.group(0), ln.strip(), pth
        except OSError:
            continue
    return None


def row_dir_from_result_path(rp):
    """<row>/out/RESULT.json -> <row>; None when it does not look like that."""
    if not rp:
        return None
    d = os.path.dirname(os.path.abspath(str(rp)))
    return os.path.dirname(d) if os.path.basename(d).startswith("out") else d


def _crash_override(c, row_dir):
    if row_dir and c.rule in ("text:pipeline-env", "text:serving-infra") and _DROP.search(c.evidence or ""):
        hit = scan_server_crash(row_dir)
        if hit:
            marker, line, _ = hit
            return _c("candidate", "candidate_crash", f"server-log:{marker}", line)
    return c


# ---- FAIL-N.json ---------------------------------------------------------------------------------------------
# Applied to the pipeline's own `reason` string. Ordered.
FAIL_REASON_RULES = [
    (r"admission refused|refuse rc=", "harness", "admission_refused", "reason:admission"),
    (r"did not log 'launcher up", "harness", "launcher_not_started", "reason:no-launcher-up"),
    (r"VRAM never showed residency", "harness", "residency_unproven", "reason:residency"),
    (r"reason=build-missing", "harness", "build_missing", "reason:build-missing"),
    (r"rc=\? \(no ended record\)|no ended record", "harness", "no_ended_record", "reason:no-ended"),
    (r"launcher-signalled|did not stop within|waits on region-lock|window \d+ s < min-window", "harness",
     "window_or_stop", "reason:window-or-stop"),
    (r"within dryrun_timeout_s|result_path is only a completion marker", "harness", "result_contract",
     "reason:result-contract"),
    (r"reason=complete after", "harness", "result_contract", "reason:complete-without-unit"),
    (r"engine never reached START", "harness", "admission_refused", "reason:never-started"),
]
_FAIL_REASON = [(re.compile(p), s, k, r) for p, s, k, r in FAIL_REASON_RULES]
_JOB_RC = re.compile(r"reason=(?:job-rc-\d+|exited)|job-rc-\d+")
_PARTIAL = re.compile(r"reason=partial-native-incomplete")
_SMOKE_NEVER = re.compile(r"smoke_predicate `[^`]*` never exited|never exited 0")


def _launcher_blob(fail, launcher_text):
    parts = []
    if launcher_text:
        parts.append(launcher_text[-6000:])
    tail = fail.get("launcher_out_tail")
    if isinstance(tail, list):
        parts.append("\n".join(str(x) for x in tail))
    return "\n".join(parts)


_TERMINAL = re.compile(r"^(FUTILITY_[A-Z0-9_]+|FAIL_[A-Z0-9_]+|PASS[A-Z0-9_]*)$")


def smoke_terminal(fail: dict):
    """AK RCA 2026-11-24 item 2: a record whose smoke wrote complete:true + a terminal verdict (rowflow SMOKE-RESULT.json,
    or a FAIL record carrying smoke_result) was DECIDED by its smoke. Returns the verdict or None."""
    sr = fail.get("smoke_result") if isinstance(fail.get("smoke_result"), dict) else fail
    v = str(sr.get("verdict") or "").strip().upper() if sr.get("result_path") else ""
    return v if _TERMINAL.match(v) else None


def classify_fail(fail: dict, launcher_text: str | None = None, row_dir: str | None = None) -> Classification:
    reason = str(fail.get("reason") or "")
    tv = smoke_terminal(fail)
    if tv and tv.startswith("FUTILITY_HARNESS_"):
        c = _c("harness", _harness_klass(tv), "result:smoke-terminal-harness", tv)
        c.row_id = str(fail.get("id") or "")
        c.source = "fail"
        return c
    if tv:   # an explicit candidate or pass verdict
        side, klass = (("ok", "pass") if tv.startswith("PASS") else
                       ("candidate", "correctness_gate" if "CORRECT" in tv else "timing_loss" if "TIM" in tv or "SPEED" in tv
                        else "candidate_verdict"))
        c = _c(side, klass, "result:smoke-terminal-verdict", tv)
        c.row_id = str(fail.get("id") or "")
        c.source = "fail"
        return c
    for rx, side, klass, rule in _FAIL_REASON:
        if rx.search(reason):
            c = _c(side, klass, rule, reason)
            break
    else:
        c = None
        blob = _launcher_blob(fail, launcher_text)
        if _PARTIAL.search(reason) or "FUTILITY" in blob:
            # the job exited by its own STOP rule (rc 75): the run declared itself futile; residency/instrument, not a verdict
            c = _c("harness", "incomplete_run", "reason:partial-native-incomplete", reason)
        elif _JOB_RC.search(reason) or "first unit written but the job ended" in reason or "before writing a unit" in reason:
            c = classify_text(blob) or _c("unknown", "job_exit_unexplained", "reason:job-rc-no-text-rule", reason)
        elif _SMOKE_NEVER.search(reason):
            c = _c("harness", "smoke_wiring", "reason:smoke-predicate-never-exited", reason)
        else:
            c = classify_text(blob) or _c("unknown", "unmatched", "none", reason)
    c = _crash_override(c, row_dir)
    c.row_id = str(fail.get("id") or "")
    c.source = "fail"
    return _resolve_unknown(c, {"reason": reason[:600], "tail": _launcher_blob(fail, launcher_text)[-1500:]})


# ---- RESULT.json ---------------------------------------------------------------------------------------------
# verdict/status token (upper-cased, parenthetical stripped) -> (side, klass)
RESULT_TOKENS = {
    "PASS": ("ok", "pass"), "KEEP": ("ok", "keep"), "COMPLETE": ("ok", "complete"), "BUILT": ("ok", "built"),
    "PROFILED": ("ok", "profiled"), "BRACKET_DONE": ("ok", "done"), "CENSUS_DONE": ("ok", "done"),
    "PASS_CORRECTNESS": ("ok", "pass"), "BIT_EXACT_PASS": ("ok", "pass"), "COMPLETE_DIAGNOSTIC_ONLY": ("ok", "complete"),
    "FUNCTIONAL-ONLY": ("ok", "complete"), "FLOOR_REGISTERED": ("ok", "complete"),
    "REJECT_CORRECTNESS": ("candidate", "correctness_gate"), "FAIL_CORRECTNESS": ("candidate", "correctness_gate"),
    "NO_KEEP": ("candidate", "timing_loss"),
    "DROP": ("candidate", "timing_loss"), "NO_MOVE": ("candidate", "timing_loss"), "NOT_OVERRIDE": ("candidate", "timing_loss"),
    "REGRESSION": ("candidate", "timing_loss"), "REJECT": ("candidate", "timing_loss"),
    "UNDERFILL": ("candidate", "noise"), "INCONCLUSIVE": ("candidate", "noise"), "NOT_JUDGEABLE": ("candidate", "noise"),
    "CONTROL_NONDETERMINISTIC": ("candidate", "noise"),
    "FUTILITY_NOISY_NOT_REGISTERED": ("harness", "instrument_noise"), "FAIL_FOREIGN_LOAD": ("harness", "instrument_noise"),
    "FAIL_WINDOW": ("harness", "window_or_stop"), "FAIL_PREFLIGHT": ("harness", "admission_refused"),
    "STOPPED": ("harness", "window_or_stop"), "FUTILITY_RESIDENCY": ("harness", "residency_unproven"),
    "FAILED": ("harness", "job_script_error"),
    "ANSWERED": ("ok", "answered"), "EQUIVALENT": ("ok", "answered"), "NEUTRAL": ("candidate", "timing_loss"),
    "NO_GAIN": ("candidate", "timing_loss"), "TESTS_FAIL": ("candidate", "correctness_gate"),
    # AK-HARNESS-CRASH-VS-VACUOUS (retarget harness job.py statuses): a kernel that ran and faulted was judged and lost;
    # VACUOUS means no kernel ran, so the candidate was never judged. Reuses existing classes, no new taxonomy.
    "CRASH": ("candidate", "correctness_gate"), "VACUOUS": ("harness", "result_contract"),
}
_TOKEN_PAREN = re.compile(r"\(([^)]*)\)")
_LEAD_WORD = re.compile(r"^[A-Z][A-Z0-9_\-]*")


def _token(v):
    s = str(v).strip()
    base = _TOKEN_PAREN.sub("", s).strip().upper()
    return base, (_TOKEN_PAREN.search(s).group(1) if _TOKEN_PAREN.search(s) else "")


def _single_verdict(v):
    """Existing single-token mapping (no composite handling): Classification or None when unrecognised."""
    base, paren = _token(v)
    if re.match(r"^KEEP(?:_|$)", base):
        return _c("ok", "keep", "result:KEEP*", v)
    if base == "FAIL" and "dup_ids" in paren:
        return _c("candidate", "correctness_gate", "result:FAIL(dup_ids)", v)
    if base == "FAIL":
        return _c("candidate", "correctness_gate", "result:FAIL", v)
    if base in RESULT_TOKENS:
        side, klass = RESULT_TOKENS[base]
        return _c(side, klass, f"result:{base}", v)
    if base.startswith("FAIL_"):
        return _c("candidate", _candidate_klass(base), "result:FAIL_*", v)
    m = _LEAD_WORD.match(base)
    if m and m.group(0) in RESULT_TOKENS:
        side, klass = RESULT_TOKENS[m.group(0)]
        return _c(side, klass, f"result:{m.group(0)}*", v)
    if base.startswith("PASS"):
        return _c("ok", "pass", "result:PASS*", v)
    return None


def _composite_verdict(v):
    """`gate:X|mtp:Y|...` -> one Classification. Any fail segment -> fail; else any inconclusive / unrecognised /
    harness segment -> inconclusive (candidate/noise); else all pass/keep -> that value. Per-segment mapping is
    recorded in the rule (and evidence)."""
    segs, kinds, first_fail = [], [], None
    for seg in str(v).split("|"):
        seg = seg.strip()
        if not seg:
            continue
        val = seg.split(":", 1)[1].strip() if ":" in seg else seg
        c = _single_verdict(val)
        if c is None or c.side not in ("ok", "candidate") or c.klass == "noise":
            kind = "inconclusive"
        elif c.side == "candidate":
            kind = "fail"
            first_fail = first_fail or c
        else:
            kind = "keep" if c.klass == "keep" else "pass"
        kinds.append(kind)
        segs.append(f"{seg}->{kind}")
    mapping = ",".join(segs)
    if "fail" in kinds:
        return _c(first_fail.side, first_fail.klass, f"result:composite[{mapping}]=fail", mapping)
    if not kinds or "inconclusive" in kinds:
        return _c("candidate", "noise", f"result:composite[{mapping}]=inconclusive", mapping)
    if "keep" in kinds:
        return _c("ok", "keep", f"result:composite[{mapping}]=keep", mapping)
    return _c("ok", "pass", f"result:composite[{mapping}]=pass", mapping)


def _fail_dups(d):
    return str(d).startswith("FAIL") and "dup_ids" in str(d)


def _candidate_klass(text):
    t = str(text).upper()
    return ("compile" if "COMPILE" in t else "correctness_gate" if ("CORRECT" in t or "ORACLE" in t or "KLD" in t)
            else "noise" if "NOISE" in t else "timing_loss")


def _harness_klass(text):
    t = str(text).upper()
    for frag, klass in (("RESIDENCY", "residency_unproven"), ("BUILD", "build_missing"), ("WINDOW", "window_or_stop"),
                        ("STOP", "window_or_stop"), ("CONTENTION", "instrument_noise"), ("INSTRUMENT", "instrument_noise"),
                        ("NOISE", "instrument_noise"), ("GRANT", "admission_refused"), ("DRIVER", "job_script_error"),
                        ("INPUT", "result_contract"), ("SOURCE", "result_contract"), ("STALE", "result_contract"),
                        ("PRODUCTION", "admission_refused")):
        if frag in t:
            return klass
    return "job_script_error"


def _polar(res):
    """AKPL-P1/P3 polar row convention (row_scaffold / akloop stage bodies), read first like gate_eval does:
    FUTILITY_HARNESS_* -> harness, FUTILITY_CANDIDATE_* -> candidate, else `polar` PASS -> ok / FAIL -> candidate."""
    v = str(res.get("verdict") or "").strip()
    tok = re.split(r"[\s:;,(]", v, maxsplit=1)[0].upper()
    polar = str(res.get("polar") or "").strip().upper()
    if polar == "PASS":
        return _c("ok", "pass", "result:polar=PASS", v)
    if tok.startswith("FUTILITY_HARNESS"):
        return _c("harness", _harness_klass(tok), "result:FUTILITY_HARNESS*", v)
    if tok.startswith("FUTILITY_CANDIDATE"):
        return _c("candidate", _candidate_klass(tok), "result:FUTILITY_CANDIDATE*", v)
    if polar == "FAIL":
        return _c("candidate", _candidate_klass(f"{tok} {res.get('stage') or ''}"), "result:polar=FAIL", v)
    return None


def classify_result(res, launcher_text: str | None = None, row_dir: str | None = None) -> Classification:
    if not isinstance(res, dict):
        c = _c("unknown", "unparseable", "result:not-an-object")
        return _resolve_unknown(c, {"result": str(res)[:600]})
    row = str(res.get("row") or res.get("id") or "")
    c = _polar(res)
    for key in (() if c else ("verdict", "status")):
        v = res.get(key)
        if isinstance(v, dict):
            v = v.get("status") or v.get("verdict")
        if isinstance(v, str) and v.strip():
            base, paren = _token(v)
            if key == "verdict" and "|" in v:
                c = _composite_verdict(v)
            elif re.match(r"^KEEP(?:_|$)", base):
                c = _c("ok", "keep", "result:KEEP*", v)
            elif base == "FAIL" and "dup_ids" in paren:
                c = _c("candidate", "correctness_gate", "result:FAIL(dup_ids)", v)  # duplicate unit ids: the patch broke id uniqueness
            elif base == "FAIL":
                c = _c("candidate", "correctness_gate", "result:FAIL", v)
            elif base in RESULT_TOKENS:
                side, klass = RESULT_TOKENS[base]
                c = _c(side, klass, f"result:{base}", v)
            elif base.startswith("FAIL_"):
                c = _c("candidate", _candidate_klass(base), "result:FAIL_*", v)
            elif _LEAD_WORD.match(base) and _LEAD_WORD.match(base).group(0) in RESULT_TOKENS:
                side, klass = RESULT_TOKENS[_LEAD_WORD.match(base).group(0)]
                c = _c(side, klass, f"result:{_LEAD_WORD.match(base).group(0)}*", v)
            elif base.startswith("PASS"):
                c = _c("ok", "pass", "result:PASS*", v)
            if c is None and key == "verdict":
                c = _c("unknown", "unrecognised_verdict", "result:verdict-token-unknown", v)  # never fall through to status=complete
            if c:
                break
    if c is None and res.get("correct") is False:
        c = _c("candidate", "correctness_gate", "result:correct=false")
    if c is None and res.get("complete") is False:
        c = classify_text(launcher_text or "") or _c("harness", "incomplete_run", "result:complete=false")
    if c is None and isinstance(res.get("rc"), int) and res["rc"] not in (0,):
        c = classify_text(launcher_text or "") or _c("unknown", "job_exit_unexplained", "result:rc-nonzero", f"rc={res['rc']}")
    if c is None and (res.get("partial") is True or str(res.get("status", "")).lower() == "partial"):
        c = _c("unknown", "partial", "result:partial")
    if c is None:
        c = classify_text(launcher_text or "") or _c("unknown", "unmatched", "none")
    c = _crash_override(c, row_dir)
    c.row_id, c.source = row, "result"
    return _resolve_unknown(c, {"result_keys": sorted(res)[:20], "verdict": str(res.get("verdict"))[:200],
                                "status": str(res.get("status"))[:200]})


# ---- routing (harness -> pipeline inbox via the existing notify path) -----------------------------------------
ROUTE_OWNER = "pipeline-mgmt"


def route(c: Classification, flags: str, owner: str = ROUTE_OWNER, notify_mod=None, rid: str = ""):
    """Harness failures only: one idempotent rowflow notification (alerts.jsonl + bus msg to the pipeline owner).
    Anything that is not side=harness is returned untouched (`None`). `flags` decides live vs scratch: notify.emit
    only writes the fleet bus for the live compute-flags tree or when ROWFLOW_BUS_ROOT is set."""
    if c.side != "harness":
        return None
    if notify_mod is None:
        here = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, os.path.join(os.path.dirname(here), "rowflow"))
        import notify as notify_mod  # noqa: PLC0415
    rid = rid or c.row_id or "unknown-row"
    summary = f"AK harness failure [{c.klass}] on {rid} (rule {c.rule}); candidate NOT judged"
    return notify_mod.emit(flags, "ak-harness-failure", rid, f"{c.klass}|{c.rule}", summary, "warning", owner=owner,
                           detail=c.to_dict(), action=True, meta={})


def _read(p):
    try:
        with open(p, errors="replace") as f:
            return f.read()
    except OSError:
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="classify an AK failure as harness vs candidate")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--fail", help="FAIL-N.json")
    g.add_argument("--result", help="RESULT.json")
    ap.add_argument("--launcher", help="launcher.out (default: next to --fail, or dryrun_log)")
    ap.add_argument("--route", action="store_true", help="emit a pipeline notification for harness failures")
    ap.add_argument("--flags", default="/mnt/raid0/llm/" + "tmp/compute-flags")
    a = ap.parse_args(argv)
    path = a.fail or a.result
    try:
        d = json.load(open(path))
    except (OSError, ValueError) as e:
        print(f"usage error: {e}", file=sys.stderr)
        return 2
    lt = _read(a.launcher) if a.launcher else None
    if lt is None and a.fail:
        lt = _read(d.get("dryrun_log") or os.path.join(os.path.dirname(path), "launcher.out"))
    rd = row_dir_from_result_path(d.get("result_path")) if isinstance(d, dict) and d.get("result_path") else os.path.dirname(os.path.abspath(path))
    c = classify_fail(d, lt, rd) if a.fail else classify_result(d, lt, rd)
    out = c.to_dict()
    if a.route:
        r = route(c, a.flags)
        out["routed"] = bool(r)
    print(json.dumps(out, indent=1))
    return 0 if c.side in ("ok", "candidate") else 1


if __name__ == "__main__":
    sys.exit(main())
