#!/usr/bin/env python3
"""ak_row_lint.py - static lint of AK row dirs for the 2026-11-23 harness defects (see ak_row_harness.py).

Flags (one line each, exit 1 when any FAIL):
  QUIET-NO-BACKOFF   a quiet-host guard (readbw REF / sibling probe / contention retries) with no backoff wait and no
                     ak_row_harness import
  HARDCODED-PORT     launch.sh --port values (or job.py port literals) that are not ak_row_harness.expected_ports(id, n)
  ESTIMATE-UNMEASURED spec.json estimate_s with no estimate_basis (smoke measurement), or below the derived value
  DIFFERS-FIXED      a code-level "differs" library proof (not prose/comments; vendored pinned helpers skipped) with no touched_libs/libs_differ (fold_row_guard.py) derivation
2026-11-23 failure audit (ak-failure-audit-20261123/REPORT.md, A2-A12). FAIL = clear defect, WARN = advisory (existing rows
would mass-fail; tighten once mk_ak_row.py rows dominate):
  SHA-CWD            FAIL  a `sha256sum --check <list>` whose entries do not resolve against the cwd it runs in
                     (job.py: `sha256sum --check` with cwd=X whose entries do not resolve from X: FAIL; unresolvable: WARN)
  SEALED-SPEC        FAIL  SOURCE.sha256 (or SOURCES.sha256 / SOURCE-SHA256SUMS) lists spec.json
  STALE-OUT          FAIL  out/ or out-smoke/ files older than SOURCE.sha256 (left by an earlier attempt)
  SERVER-NO-TRAP     FAIL  a script that starts a server in the background with no trap ... EXIT (shell) or no
                           atexit/finally/signal cleanup (python)
  PY-COMPILE         FAIL  a row .py that does not compile
  SELFTEST           FAIL  job.py --selftest (when job.py supports it) exits non-zero or exceeds 60 s
  CLAIM-PARSE        FAIL  launch.sh parses WS58_REGIONS with tr/grep/paste/sed/awk, or its --claim-cpus / C= default is not a
                           digit/comma/dash list; use C=${WS58_CPUS:-<digits>} or omit both (CPU rows: grant's cpus)
  SMOKE-FAIL-SILENT  FAIL  smoke code with no ak_row_harness.end_smoke(verdict, rc, reason[, out_dir]) CALL (AST, not grep)
  SMOKE-NO-MEASURE   FAIL  smoke code with no write_smoke_measure(...) call and no literal smoke_measure.json write
  SMOKE-MEASURE-PATH FAIL  the smoke writes smoke_measure.json somewhere the keeper never reads. rowflow.smoke_measure_paths
                           reads exactly: <scratch_root>/out-smoke/smoke_measure.json, spec estimate_basis.rebook_from /
                           .smoke_measure, and <flags>/dryrun/<id>/smoke_measure.json (not exported to jobs). E.g.
                           out/smoke/smoke_measure.json is never read -> SMOKE-NO-MEASURE at the smoke, 5-20 min later.
  SELFTEST-MISSING   FAIL  (autokernel rows) job.py has no `--selftest` argv handler that exits before main()
  WALL-STOP-PAST     FAIL  a hard-coded absolute wall-clock deadline (deadline/stop/until/cutoff/... = ISO time or epoch)
                           that is already in the past: the row can only stop at once
D9 (operator 2026-11-24): SMOKE-NO-MEASURE / SMOKE-FAIL-SILENT were WARN, now FAIL for autokernel rows (ids ak- / c2x-,
or owner autokernel*) and stay WARN for every other owner: a row certain to fail its smoke is refused at publish.
  FRESH-SERVER-UNJUSTIFIED WARN  a server is started per loop iteration (per request/unit/visit) and spec.json does not set
                           "fresh_server_per_visit": true with a "fresh_server_reason" (default: one server per arm,
                           many requests, cache_prompt:false on every request; D9 2026-11-24)
  FRESH-SERVER-UNCAPPED WARN  fresh_server_per_visit=true but the job never reads its cap (FRESH_SERVER_STARTS /
                           fresh_server_starts, default 3 starts per arm; the rest of the requests reuse those servers), or
                           spec fresh_server_starts > 3 with no fresh_server_starts_reason
  NO-WITNESS         WARN  the decision rule names a GGML_/LLAMA_ knob and no row code records a witness key
  MECH-UNWITNESSED   WARN  (AK-MECH-WITNESS-1, D9-ack 2026-11-25; never FAIL) a row whose decision_rule can return a keep/pass on
                           a speed claim has no spec mechanism_witness {counter, direction, aa_band}, or its row code never
                           records the declared counter for both arms (intake-2958)
  REPLAY-NO-BASELINE WARN  a replay row with no baseline validation (baseline_ok / validate_baseline / replay_baseline)
  CPUS-IN-ARGV       WARN  a cpus() / grant_cpus() call placed directly inside an argv list/tuple literal or a `+` concatenation
                           with no cpu_str() / ",".join around it (a list of ints in an argv: subprocess TypeError, seen twice
                           2026-11-24). CPUS_IN_ARGV_LEVEL flips it to FAIL once no queued row hits it.
Usage: ak_row_lint.py [--no-selftest] <row_dir> [<row_dir> ...]   (read-only, except job.py --selftest when present)
"""
import ast
import io
import json
import os
import re
import subprocess
import sys
import time
import tokenize
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ak_row_harness as H  # noqa: E402

GUARD_RX = re.compile(r"bench_readbw|read_sum|class\s+Probe|probe_p50|MAX_TRIES", re.I)
BACKOFF_RX = re.compile(r"backoff|ak_row_harness|time\.sleep\(\s*(?:[2-9]\d|\d{3,})", re.I)
PORT_ARG_RX = re.compile(r"--port[ =]+([\d,]+)")
PORT_LIT_RX = re.compile(r"\bport\w*\s*[=:]\s*(\d{4,5})\b", re.I)
DIFFERS_RX = re.compile(r"differ", re.I)
LIB_RX = re.compile(r"lib[\w-]+\.so")
DERIVED_RX = re.compile(r"touched_libs|libs_differ|fold_row_guard")
SHA_CHECK_RX = re.compile(r"sha256sum\s+(?:--\w+\s+|-c\s+)*(?:--check|-c)\b(?:\s+--\w+)*\s+(\"[^\"]+\"|'[^']+'|[^\s<|;&]+)")
CD_RX = re.compile(r"^\s*cd\s+(\"[^\"]+\"|'[^']+'|\S+)", re.M)
VAR_RX = re.compile(r"^\s*(?:export\s+)?([A-Za-z_]\w*)=(\"[^\"$`]*\"|'[^']*'|[^\s;$`\"']+)\s*$", re.M)
CLAIM_VAL_RX = re.compile(r"^[0-9]+(-[0-9]+)?(,[0-9]+(-[0-9]+)?)*$")
CLAIM_ARG_RX = re.compile(r"--claim-cpus[ =]+(\"[^\"]*\"|'[^']*'|[^\s\\]+)")
CLAIM_DEF_RX = re.compile(r"^\s*(?:export\s+)?C=(?:\$\{WS58_CPUS:-([^}]*)\}|(\"[^\"$`]*\"|'[^']*'|[^\s$`\"']+))\s*$", re.M)
SEAL_FILES = ("SOURCE.sha256", "SOURCES.sha256", "SOURCE-SHA256SUMS")
SERVER_RX = re.compile(r"llama-server|sd-server|whisper-server|qwentts-server|llama-cli")
SH_BG_SERVER_RX = re.compile(r"(?:llama-server|sd-server|whisper-server|qwentts-server)[^\n#]*&\s*(?:#.*)?$", re.M)
SH_TRAP_RX = re.compile(r"^\s*trap\s+.+\b(?:EXIT|0)\b", re.M)
PY_CLEANUP_RX = re.compile(r"\batexit\b|finally\s*:|signal\.signal\(|with\s+[\w.]*(?:Popen|server)\w*\(")
CLAIM_PARSE_RX = re.compile(r"WS58_REGIONS[^\n]*\|\s*(?:tr|grep|paste|sed|awk)\b|(?:tr|grep|paste|sed|awk)\b[^\n|]*WS58_REGIONS")
SMOKE_RX = re.compile(r"TERMINAL-smoke|FILLER_SMOKE|FILLER_DRYRUN")
KNOB_RX = re.compile(r"\b(?:GGML|LLAMA)_[A-Z0-9_]{2,}\b")
WITNESS_RX = re.compile(r"[\"']\w*witness\w*[\"']", re.I)
# `_` is a word char, so \bkeep\b misses KEEP_CANDIDATE / GATE_PASS: bound on letters only
SPEED_CLAIM_RX = re.compile(r"(?<![a-z])(?:keep|pass|promote)(?![a-z])", re.I)
SPEED_WORD_RX = re.compile(
    r"(?<![a-z])(?:speed|faster|slower|tok/?s|t/s|throughput|latency|bandwidth|geomean|ratio|perf|prefill|decode|e2e|gain|"
    r"ms|us|pp\d*|tg\d*)(?![a-z])|µs|\bGB/s", re.I)
# self-declared non-gating rules (diagnostic/census/screening/futility-only) cannot return a keep: no warn
EXPLICIT_KEEP_RX = re.compile(r"KEEP_CANDIDATE|GATE_PASS|\bKEEP\b|\bPROMOTE\b")  # an explicit keep beats a non-gating word
NONGATING_RX = re.compile(r"diagnostic|never\s+gates|polar\s+None|(?<![a-z])census(?![a-z])|(?<![a-z])screening(?![a-z])|"
                          r"futility[- ]only|floor[- ](?:only|census|measurement)", re.I)
MECH_FIELDS = ("counter", "direction", "aa_band")


def mech_unwitnessed(spec, allc):
    """AK-MECH-WITNESS-1: WARN-only. [] when the rule cannot return a speed keep/pass or the witness is declared and recorded."""
    rule = " ".join(str(spec.get(k) or "") for k in ("decision_rule", "notes"))
    if not (SPEED_CLAIM_RX.search(rule) and SPEED_WORD_RX.search(rule)):
        return []
    dr = str(spec.get("decision_rule") or "")
    if NONGATING_RX.search(dr) and not EXPLICIT_KEEP_RX.search(dr):
        return []
    w = spec.get("mechanism_witness")
    miss = [k for k in MECH_FIELDS if not (isinstance(w, dict) and str(w.get(k) or "").strip())]
    if miss:
        return [("WARN", "MECH-UNWITNESSED", "decision rule can return a keep/pass on a speed claim but spec "
                 f"mechanism_witness lacks {miss or list(MECH_FIELDS)}; declare {{counter, direction, aa_band}} "
                 "(the per-row mechanism_prediction.expected_counter_changes)")]
    c = str(w["counter"]).strip()
    lines = [ln for ln in allc.splitlines() if c in ln]
    if not lines or not (len(lines) >= 2 or any(re.search(r"arm|base|cand", ln, re.I) for ln in lines)):
        return [("WARN", "MECH-UNWITNESSED", f"mechanism_witness.counter {c!r} is not recorded for both arms in the row's "
                 "RESULT code")]
    return []
REPLAY_RX = re.compile(r"replay", re.I)
BASELINE_RX = re.compile(r"baseline_ok|baseline_valid|validate_baseline|replay_baseline|baseline_check|baseline_match", re.I)
SELFTEST_TIMEOUT_S = 60
# vendored, sha-pinned helper copies (own SOURCE/BIN pin): never linted for row-authoring defects
VENDORED = {"gpu_common.py", "gpuproof_row.py", "lp_common.py", "base.py", "fold_row_guard.py",
            "ak_gate.py"}   # ak_gate.py: the tested gate harness (mk_ak_row gate new), vendored + sealed


def _differs_proof(t):
    """True only for a CODE construct: a NAME token containing 'differ' plus a lib*.so string literal.
    Comments, docstrings and message strings are ignored."""
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(t).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return False
    has_name = any(k.type == tokenize.NAME and DIFFERS_RX.search(k.string) for k in toks)
    has_lib = False
    prev = tokenize.NEWLINE
    for k in toks:
        if k.type == tokenize.STRING and prev not in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.NL) \
                and LIB_RX.search(k.string):
            has_lib = True
        if k.type not in (tokenize.COMMENT,):
            prev = k.type
    return has_name and has_lib


def _read(p):
    try:
        with open(p, errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _unq(x):
    return x[1:-1] if len(x) >= 2 and x[0] == x[-1] and x[0] in "\"'" else x


def _subst(x, vars_):
    for k, v in vars_.items():
        x = x.replace("${%s}" % k, v).replace("$" + k, v)
    return x


def sha_cwd(d, launch):
    """SHA-CWD: every `sha256sum --check <list>` in launch.sh, resolved against the cwd in force at that line (the last
    `cd` before it; none = the launcher's caller cwd, unknown). Lists read from stdin/heredocs are skipped."""
    out = []
    vars_ = {"D": d}
    for m in VAR_RX.finditer(launch):
        if m.group(1) != "D":
            vars_[m.group(1)] = _subst(_unq(m.group(2)), vars_)
    for m in SHA_CHECK_RX.finditer(launch):
        arg = _unq(m.group(1))
        if arg.startswith("-"):
            continue                                    # stdin / heredoc list
        cds = [c for c in CD_RX.finditer(launch) if c.start() < m.start()]
        cwd = os.path.normpath(_subst(_unq(cds[-1].group(1)), vars_)) if cds else None
        lst = _subst(arg, vars_)
        if "$" in lst or (cwd and "$" in cwd):
            continue                                    # unresolvable variable: not judged
        if not os.path.isabs(lst):
            if cwd is None:
                out.append(("FAIL", "SHA-CWD", f"launch.sh: sha256sum --check {arg} with no `cd` before it: the list "
                                                "resolves against the caller's cwd"))
                continue
            lst = os.path.join(cwd, lst)
        if not os.path.isfile(lst):
            out.append(("FAIL", "SHA-CWD", f"launch.sh: sha256sum --check list {lst} does not exist"))
            continue
        base = cwd
        miss = []
        for ln in _read(lst).splitlines():
            q = ln.strip().split(None, 1)
            if len(q) != 2:
                continue
            f = q[1].lstrip("*")
            if os.path.isabs(f):
                ok = os.path.exists(f)
            else:
                ok = base is not None and os.path.exists(os.path.join(base, f))
            if not ok:
                miss.append(f)
        if miss:
            out.append(("FAIL", "SHA-CWD", f"launch.sh: sha256sum --check {arg} run from cwd {base}: {len(miss)} entr"
                                            f"{'y' if len(miss) == 1 else 'ies'} do not resolve there ({miss[:3]})"))
    return out


def claim_parse(launch):
    """CLAIM-PARSE: a literal --claim-cpus value, or the C= default it expands to, must be a digit/comma/dash list."""
    out = []
    defaults = [(m.group(1) if m.group(1) is not None else _unq(m.group(2))) for m in CLAIM_DEF_RX.finditer(launch)]
    for v in defaults:
        if v and "$" not in v and not CLAIM_VAL_RX.match(v):
            out.append(("FAIL", "CLAIM-PARSE", f"launch.sh: C= default {v!r} is not a digit/comma/dash cpu list "
                                               "(filler_run15.sh rejects it as 'bad --claim-cpus'); omit C= and "
                                               "--claim-cpus on a CPU row to use the grant's cpus"))
    for m in CLAIM_ARG_RX.finditer(launch):
        v = _unq(m.group(1))
        if v in ("$C", "${C}") or ("$" in v):
            continue                                    # expands to the C= default, judged above
        if not CLAIM_VAL_RX.match(v):
            out.append(("FAIL", "CLAIM-PARSE", f"launch.sh: --claim-cpus {v!r} is not a digit/comma/dash cpu list"))
    return out


def _const(node, env, seen=()):
    """Statically evaluate a str/Path expression from literals and module-level constants; None when not resolvable."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    rowdir = env.get("__rowdir__")
    if rowdir is not None and _is_file_dir(node):
        return rowdir.value
    if isinstance(node, ast.Attribute) and node.attr == "parent" and rowdir is not None:
        inner = node.value
        if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute) and inner.func.attr in ("resolve", "absolute"):
            inner = inner.func.value
        if isinstance(inner, ast.Call) and ast.unparse(inner.func) in ("Path", "pathlib.Path") and \
                len(inner.args) == 1 and isinstance(inner.args[0], ast.Name) and inner.args[0].id == "__file__":
            return rowdir.value
    if isinstance(node, ast.Name) and node.id in env and node.id not in seen:
        return _const(env[node.id], env, seen + (node.id,))
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Div)):
        a, b = _const(node.left, env, seen), _const(node.right, env, seen)
        if a is None or b is None:
            return None
        return a + b if isinstance(node.op, ast.Add) else a.rstrip("/") + "/" + b.lstrip("/")
    if isinstance(node, ast.Call) and not node.keywords:
        fn = ast.unparse(node.func)
        vals = [_const(x, env, seen) for x in node.args]
        if None in vals or not vals:
            return None
        if fn in ("str", "Path", "pathlib.Path"):
            return vals[0] if len(vals) == 1 else None
        if fn == "os.path.join":
            return os.path.join(*vals)
        if fn == "os.path.normpath" and len(vals) == 1:
            return os.path.normpath(vals[0])
    return None


def _is_file_dir(node):
    """os.path.dirname(os.path.abspath|realpath(__file__)) / os.path.dirname(__file__)."""
    if not (isinstance(node, ast.Call) and ast.unparse(node.func) == "os.path.dirname" and len(node.args) == 1):
        return False
    a = node.args[0]
    if isinstance(a, ast.Call) and ast.unparse(a.func) in ("os.path.abspath", "os.path.realpath") and len(a.args) == 1:
        a = a.args[0]
    return isinstance(a, ast.Name) and a.id == "__file__"


def _env(tree, d):
    """Name -> value node for every simple assignment (module level wins), plus the row dir for __file__ idioms."""
    env = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            env.setdefault(n.targets[0].id, n.value)
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            env.setdefault(n.targets[0].id, n.value)
    env["__rowdir__"] = ast.Constant(d)
    return env


def _callname(n):
    f = n.func
    return f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")


def _cands(node, env, seen=()):
    """Every statically resolvable value of a path expression (both arms of an `a if c else b`)."""
    if isinstance(node, ast.IfExp):
        return _cands(node.body, env, seen) + _cands(node.orelse, env, seen)
    if isinstance(node, ast.Name) and node.id in env and node.id not in seen and isinstance(env[node.id], ast.IfExp):
        return _cands(env[node.id], env, seen + (node.id,))
    v = _const(node, env)
    return [v] if v is not None else []


def keeper_measure_rels(spec, d):
    """The smoke_measure.json paths rowflow.smoke_measure_paths reads, relative to the row's scratch_root."""
    root = str(spec.get("scratch_root") or d)
    rels = {os.path.join("out-smoke", H.SMOKE_MEASURE)}
    b = spec.get("estimate_basis")
    if isinstance(b, dict):
        decl = b.get("rebook_from") or b.get("smoke_measure")
        if isinstance(decl, str) and decl:
            rels.add(os.path.normpath(os.path.relpath(decl, root) if os.path.isabs(decl) else decl))
    return rels


def _vendored_gate_smoke(d, own):
    """True iff the job `import ak_gate`s and the vendored ak_gate.py beside it really calls end_smoke(>=3 args) and
    write_smoke_measure (a gate row's smoke lives in the sealed harness, not in the declaration)."""
    if not any(re.search(r"^\s*import ak_gate\b|^\s*from ak_gate import", t, re.M) for t in own.values()):
        return False
    try:
        tree = ast.parse(_read(os.path.join(d, "ak_gate.py")))
    except (OSError, SyntaxError, ValueError):
        return False
    names = [(_callname(n), len(n.args) + len(n.keywords)) for n in ast.walk(tree) if isinstance(n, ast.Call)]
    return any(c == "end_smoke" and k >= 3 for c, k in names) and any(c == "write_smoke_measure" for c, _ in names)


def smoke_checks(d, spec, own):
    """SMOKE-FAIL-SILENT / SMOKE-NO-MEASURE / SMOKE-MEASURE-PATH over real call sites (AST), not text matches."""
    out = []
    if _vendored_gate_smoke(d, own):
        return out        # the vendored ak_gate.py owns end_smoke + write_smoke_measure (out-smoke/), proven by its own tests
    ends, writes, unresolved = 0, [], []
    for f, t in sorted(own.items()):
        try:
            tree = ast.parse(t)
        except (SyntaxError, ValueError):
            continue
        env = _env(tree, d)
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                nm = _callname(n)
                if nm == "end_smoke" and len(n.args) + len(n.keywords) >= 3:
                    ends += 1
                if nm == "write_smoke_measure":
                    arg = n.args[0] if n.args else next((k.value for k in n.keywords if k.arg == "out_dir"), None)
                    vs = _cands(arg, env) if arg is not None else []
                    if vs:
                        writes += [(f, n.lineno, os.path.join(v, H.SMOKE_MEASURE)) for v in vs]
                    else:
                        unresolved.append((f, n.lineno, ast.unparse(arg) if arg is not None else "?"))
            lit = isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.endswith(H.SMOKE_MEASURE)
            if isinstance(n, (ast.Call, ast.BinOp)) and not (isinstance(n, ast.Call) and _callname(n) == "write_smoke_measure"):
                parts = n.args if isinstance(n, ast.Call) else [n.right]
                if any(isinstance(x, ast.Constant) and x.value == H.SMOKE_MEASURE for x in parts):
                    v = _const(n, env)
                    if v is not None:
                        writes.append((f, n.lineno, v))
            elif lit and n.value != H.SMOKE_MEASURE and "/" in n.value:
                writes.append((f, n.lineno, n.value))
    if not ends:
        out.append(("FAIL", "SMOKE-FAIL-SILENT", "smoke path with no ak_row_harness.end_smoke(verdict, rc, reason, out_dir) "
                                                 "call: a failed smoke leaves no reason"))
    if not writes and not unresolved:
        out.append(("FAIL", "SMOKE-NO-MEASURE", "smoke path with no ak_row_harness.write_smoke_measure(...) call: the keeper "
                                                "refuses the smoke PASS (SMOKE-NO-MEASURE) and the estimate cannot be derived"))
        return out
    rels = keeper_measure_rels(spec, d)
    dn = os.path.normpath(d)
    got = []
    for f, ln, p in writes:
        p = os.path.normpath(p if os.path.isabs(p) else os.path.join(d, p))
        got.append((f, ln, os.path.relpath(p, dn)))
    if any(r in rels for _, _, r in got):
        return out
    if unresolved and not got:
        alltxt = "\n".join(own.values())
        if "out-smoke" in alltxt:
            return out                                  # dynamic out_dir built from an out-smoke literal: not judged
        f, ln, a = unresolved[0]
        out.append(("FAIL", "SMOKE-MEASURE-PATH", f"{f}:{ln}: write_smoke_measure({a}, ...) path is not statically "
                                                  f"resolvable and names no out-smoke dir; the keeper reads only "
                                                  f"{sorted(rels)} (relative to scratch_root)"))
        return out
    f, ln, r = got[0]
    out.append(("FAIL", "SMOKE-MEASURE-PATH", f"{f}:{ln}: smoke writes {r} but the keeper reads only {sorted(rels)} "
                                              "(relative to scratch_root; rowflow.smoke_measure_paths): write to out-smoke/ "
                                              "or declare estimate_basis.smoke_measure"))
    return out


SELFTEST_FLAG = "--selftest"


def _mentions_selftest(node):
    for x in ast.walk(node):
        if isinstance(x, ast.Constant) and x.value == SELFTEST_FLAG:
            return True
        if isinstance(x, ast.Attribute) and x.attr == "selftest":
            return True
    return False


def _reads_argv(node):
    return any((isinstance(x, ast.Attribute) and x.attr == "argv") or (isinstance(x, ast.Name) and x.id in ("argv", "args", "a", "ns", "opts"))
               or isinstance(x, ast.Attribute) and x.attr == "selftest" for x in ast.walk(node))


def _exits(stmts):
    for s in stmts:
        for x in ast.walk(s):
            if isinstance(x, (ast.Return, ast.Raise)):
                return True
            if isinstance(x, ast.Call) and (_callname(x) in ("exit", "_exit", "SystemExit", "quit")):
                return True
    return False


def selftest_missing(job):
    """SELFTEST-MISSING: True unless job.py has an argv `--selftest` branch that exits (or selects selftest() over main())."""
    try:
        tree = ast.parse(job)
    except (SyntaxError, ValueError):
        return False                                     # PY-COMPILE reports it
    has_flag = any(isinstance(x, ast.Constant) and x.value == SELFTEST_FLAG for x in ast.walk(tree))
    if not has_flag:
        return True
    for n in ast.walk(tree):
        if isinstance(n, ast.IfExp) and _mentions_selftest(n.test) and _reads_argv(n.test):
            return False
        if isinstance(n, ast.If) and _mentions_selftest(n.test) and _reads_argv(n.test) and _exits(n.body):
            return False
    return True


DEADLINE_RX = re.compile(r"\b(\w*(?:deadline|wall_?stop|stop_?(?:at|utc|by|epoch|ts|time)|hard_?stop|until|cutoff|not_?after|"
                         r"end_?by|expires?(?:_at)?)\w*)\b[\"']?\s*[:=]\s*(?:[\w.]+\()?\s*[\"']?"
                         r"(\d{4}-\d\d-\d\d[T ]\d\d:\d\d(?::\d\d)?(?:Z|[+-]00:?00)?|1[7-9]\d{8}|2[01]\d{8})\b", re.I)


def _abs_time(v):
    if v.isdigit():
        return float(v)
    v = v.replace(" ", "T").rstrip("Z")
    v = re.sub(r"[+-]00:?00$", "", v)
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(v, fmt).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            pass
    return None


def wall_stop_past(texts, clock=time.time):
    """WALL-STOP-PAST: a deadline-named variable bound to an absolute time (ISO / epoch) that is already past."""
    out, t_now = [], clock()
    for f, t in sorted(texts.items()):
        for ln_no, ln in enumerate(t.splitlines(), 1):
            s = ln.lstrip()
            if s.startswith("#"):
                continue
            for m in DEADLINE_RX.finditer(ln):
                ts = _abs_time(m.group(2))
                if ts is not None and ts < t_now:
                    out.append(("FAIL", "WALL-STOP-PAST", f"{f}:{ln_no}: {m.group(1)} = {m.group(2)} is already in the past; "
                                                          "derive the deadline from the grant start (time.time() + budget)"))
    return out


SERVER_CTOR_RX = re.compile(r"(?:^|_)(?:srv|server)$", re.I)


def _starts_server(fn_node):
    """A node whose subtree starts a server: start_server(...), Server/Srv(...) construction, or a Popen of a server binary."""
    for x in ast.walk(fn_node):
        if isinstance(x, ast.Call):
            nm = _callname(x)
            if nm == "start_server" or SERVER_CTOR_RX.search(nm or ""):
                return True
            if nm == "Popen" and SERVER_RX.search(ast.unparse(x)):
                return True
    return False


def fresh_server_per_iter(code):
    """FRESH-SERVER-UNJUSTIFIED: (file, line) of a loop that starts a server per iteration, directly or via a function."""
    hits = []
    for f, t in sorted(code.items()):
        if f in VENDORED:
            continue
        try:
            tree = ast.parse(t)
        except (SyntaxError, ValueError):
            continue
        starters = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and _starts_server(n)}
        for n in ast.walk(tree):
            if not isinstance(n, (ast.For, ast.While, ast.AsyncFor)):
                continue
            body = ast.Module(body=n.body, type_ignores=[])
            if _starts_server(body) or any(isinstance(x, ast.Call) and _callname(x) in starters for x in ast.walk(body)):
                hits.append((f, n.lineno))
    return hits


def sha_cwd_py(d, code):
    """SHA-CWD (job.py): subprocess `sha256sum --check <list>` run with cwd=X; FAIL when the list's entries do not resolve
    from X (e.g. cwd=BIN with `bin/llama-server` entries); WARN when the paths cannot be resolved statically."""
    out = []
    for f, t in sorted(code.items()):
        if f in VENDORED or "sha256sum" not in t:
            continue
        try:
            tree = ast.parse(t)
        except (SyntaxError, ValueError):
            continue
        env = {}
        for n in tree.body:
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                env.setdefault(n.targets[0].id, n.value)
        env["__rowdir__"] = ast.Constant(d)
        for n in ast.walk(tree):
            if not (isinstance(n, ast.Call) and n.args and isinstance(n.args[0], (ast.List, ast.Tuple))):
                continue
            el = n.args[0].elts
            if not (el and isinstance(el[0], ast.Constant) and str(el[0].value).endswith("sha256sum")):
                continue
            flags = [x.value for x in el[1:] if isinstance(x, ast.Constant) and isinstance(x.value, str)]
            if not ({"--check", "-c"} & set(flags)):
                continue
            rest = [x for x in el[1:] if not (isinstance(x, ast.Constant) and str(x.value).startswith("-"))]
            if not rest:
                continue                                # list from stdin
            kw = {k.arg: k.value for k in n.keywords}
            lst = _const(rest[-1], env)
            cwd = _const(kw["cwd"], env) if "cwd" in kw else d
            if lst is None or cwd is None:
                out.append(("WARN", "SHA-CWD", f"{f}:{n.lineno}: sha256sum --check list/cwd not statically resolvable; "
                                               "confirm its entries resolve from the cwd it runs in"))
                continue
            lst = lst if os.path.isabs(lst) else os.path.join(cwd, lst)
            if not os.path.isfile(lst):
                out.append(("WARN", "SHA-CWD", f"{f}:{n.lineno}: sums file {lst} not on disk; cannot check its entries "
                                               f"against cwd {cwd}"))
                continue
            miss = []
            for ln in _read(lst).splitlines():
                q = ln.strip().split(None, 1)
                if len(q) == 2:
                    e = q[1].lstrip("*")
                    if not os.path.exists(e if os.path.isabs(e) else os.path.join(cwd, e)):
                        miss.append(e)
            if miss:
                out.append(("FAIL", "SHA-CWD", f"{f}:{n.lineno}: sha256sum --check {os.path.basename(lst)} run with "
                                               f"cwd={cwd}: {len(miss)} entr{'y' if len(miss) == 1 else 'ies'} do not "
                                               f"resolve there ({miss[:3]})"))
    return out


def sealed_spec(d):
    out = []
    for n in SEAL_FILES:
        for ln in _read(os.path.join(d, n)).splitlines():
            q = ln.strip().split(None, 1)
            if len(q) == 2 and os.path.basename(q[1].lstrip("*")) == "spec.json":
                out.append(("FAIL", "SEALED-SPEC", f"{n} lists spec.json; publish edits spec.json, so the seal breaks "
                                                   "(seal without it)"))
    return out


def stale_out(d):
    seal = [os.path.join(d, n) for n in SEAL_FILES if os.path.exists(os.path.join(d, n))]
    if not seal:
        return []
    t_seal = max(os.path.getmtime(p) for p in seal)
    out = []
    for sub in ("out", "out-smoke"):
        root = os.path.join(d, sub)
        if not os.path.isdir(root):
            continue
        old = []
        for r, dirs, files in os.walk(root):
            dirs[:] = [x for x in dirs if not x.startswith("stale-")]
            old += [os.path.relpath(os.path.join(r, f), d) for f in files
                    if os.path.getmtime(os.path.join(r, f)) < t_seal]
        if old:
            out.append(("FAIL", "STALE-OUT", f"{len(old)} file(s) in {sub}/ older than the seal ({sorted(old)[:3]}); move "
                                             "them aside (fold_row_guard.move_stale) before publishing"))
    return out


def server_no_trap(d, code):
    out = []
    for f in sorted(x for x in os.listdir(d) if x.endswith(".sh")):
        t = _read(os.path.join(d, f))
        if SH_BG_SERVER_RX.search(t) and not SH_TRAP_RX.search(t):
            out.append(("FAIL", "SERVER-NO-TRAP", f"{f}: background server with no `trap ... EXIT`; it outlives the row"))
    for f, t in code.items():
        if f not in VENDORED and "Popen" in t and SERVER_RX.search(t) and not PY_CLEANUP_RX.search(t):
            out.append(("FAIL", "SERVER-NO-TRAP", f"{f}: server Popen with no atexit/finally/signal cleanup"))
    return out


def py_compile_and_selftest(d, code, selftest=True, timeout=SELFTEST_TIMEOUT_S):
    out = []
    for f, t in code.items():
        try:
            compile(t, os.path.join(d, f), "exec")      # no .pyc written
        except (SyntaxError, ValueError) as e:
            out.append(("FAIL", "PY-COMPILE", f"{f}: {e.__class__.__name__}: {e}"))
    job = code.get("job.py", "")
    if selftest and job and "--selftest" in job and not any(r[1] == "PY-COMPILE" and r[2].startswith("job.py")
                                                            for r in out):
        env = {"PATH": "/usr/bin:/bin", "HIP_VISIBLE_DEVICES": "-1", "ROCR_VISIBLE_DEVICES": "-1",
               "AK_ROW_SELFTEST": "1"}
        try:
            p = subprocess.run([sys.executable, "-I", "-B", os.path.join(d, "job.py"), "--selftest"], cwd=d, env=env,
                               capture_output=True, text=True, timeout=timeout)
            if p.returncode != 0:
                out.append(("FAIL", "SELFTEST", f"job.py --selftest rc {p.returncode}: "
                                                f"{(p.stderr or p.stdout).strip()[-200:]}"))
        except subprocess.TimeoutExpired:
            out.append(("FAIL", "SELFTEST", f"job.py --selftest exceeded {timeout} s"))
    return out


CPUS_IN_ARGV_LEVEL = "WARN"
_CPU_CALLS = {"cpus", "grant_cpus"}


def cpus_in_argv(code):
    """CPUS-IN-ARGV: cpus()/grant_cpus() as a direct element of a list/tuple literal or operand of `+` (AST)."""
    out = []
    for f, t in sorted(code.items()):
        try:
            tree = ast.parse(t)
        except (SyntaxError, ValueError):
            continue
        for par in ast.walk(tree):
            kids = (par.elts if isinstance(par, (ast.List, ast.Tuple)) else
                    [par.left, par.right] if isinstance(par, ast.BinOp) and isinstance(par.op, ast.Add) else [])
            for k in kids:
                if isinstance(k, ast.Call) and _callname(k) in _CPU_CALLS:
                    out.append((CPUS_IN_ARGV_LEVEL, "CPUS-IN-ARGV",
                                f"{f}:{k.lineno}: {ast.unparse(k)} is a list of ints placed in an argv/concatenation; "
                                "wrap it in cpu_str() (or \",\".join(map(str, ...)))"))
    return out


def lint_dir(d, selftest=True):
    out = []
    spec = {}
    try:
        spec = json.loads(_read(os.path.join(d, "spec.json")) or "{}")
    except ValueError:
        out.append(("FAIL", "SPEC", "spec.json is not JSON"))
    rid = spec.get("id") or os.path.basename(os.path.normpath(d))
    pys = sorted(f for f in os.listdir(d) if f.endswith(".py") and f != "ak_row_harness.py")
    code = {f: _read(os.path.join(d, f)) for f in pys}
    launch = _read(os.path.join(d, "launch.sh"))

    for f, t in code.items():
        if GUARD_RX.search(t) and not BACKOFF_RX.search(t):
            out.append(("FAIL", "QUIET-NO-BACKOFF", f"{f}: quiet-host guard retries with no backoff; use ak_row_harness.quiet_guard"))

    ports = [int(x) for m in PORT_ARG_RX.finditer(launch) for x in m.group(1).split(",") if x]
    if ports:
        exp = H.expected_ports(rid, len(ports))
        if sorted(ports) != sorted(exp):
            out.append(("FAIL", "HARDCODED-PORT", f"launch.sh --port {ports} != alloc_ports({rid!r}, {len(ports)}) = {exp}"))
    for f, t in code.items():
        lits = sorted({int(m.group(1)) for m in PORT_LIT_RX.finditer(t)} - set(ports))
        if lits and "alloc_ports" not in t and "FILLER_PORTS" not in t:
            out.append(("FAIL", "HARDCODED-PORT", f"{f}: port literal(s) {lits}; take them from FILLER_PORTS / alloc_ports"))

    if spec.get("estimate_s") is not None:
        try:
            estimate_spec = spec
            if not spec.get("lane") and re.search(r"--class[ =]+(?:gpu|cpu\+gpu)(?:\s|$)", launch):
                estimate_spec = dict(spec, lane="gpu")
            _, w = H.check_spec_estimate(estimate_spec, base_dir=d)
            for x in w:
                if x.startswith("ESTIMATE-PROVISIONAL"):
                    out.append(("WARN", "ESTIMATE-PROVISIONAL", x))
                else:
                    out.append(("FAIL", "ESTIMATE-UNMEASURED", x))
        except ValueError as e:
            out.append(("FAIL", "ESTIMATE-UNMEASURED", str(e)))

    for f, t in code.items():
        if f not in VENDORED and _differs_proof(t) and not DERIVED_RX.search(t):
            out.append(("FAIL", "DIFFERS-FIXED", f"{f}: library 'differs' proof over a fixed list; derive it with "
                                                 "fold_row_guard.touched_libs/libs_differ"))

    out += sha_cwd(d, launch)
    out += sha_cwd_py(d, code)
    out += sealed_spec(d)
    out += stale_out(d)
    out += server_no_trap(d, code)
    out += py_compile_and_selftest(d, code, selftest)
    out += claim_parse(launch)
    if CLAIM_PARSE_RX.search(launch):
        out.append(("FAIL", "CLAIM-PARSE", "launch.sh parses WS58_REGIONS with tr/grep/paste/sed; use "
                                           "C=${WS58_CPUS:-<claim>} (keeper exports digit-only WS58_CPUS)"))

    own = {f: t for f, t in code.items() if f not in VENDORED}
    allc = "\n".join(own.values())
    is_ak = str(spec.get("owner") or "").startswith("autokernel") or str(rid).startswith("ak-")
    if SMOKE_RX.search(allc):
        # D9-ack 2026-11-24: SMOKE-FAIL-SILENT / SMOKE-NO-MEASURE FAIL only for autokernel rows (ak-, c2x-); WARN otherwise
        sm_fail = is_ak or re.match(r"c2[0-9]-", str(rid))
        out += [(l if (l != "FAIL" or c not in ("SMOKE-FAIL-SILENT", "SMOKE-NO-MEASURE") or sm_fail) else "WARN", c, m)
                for l, c, m in smoke_checks(d, spec, own)]
    if is_ak and "job.py" in code and selftest_missing(code["job.py"]):
        out.append(("FAIL", "SELFTEST-MISSING", "job.py has no `--selftest` argv handler that exits before main() "
                                                "(e.g. sys.exit(selftest() if '--selftest' in sys.argv[1:] else main())); "
                                                "a function named selftest alone does not count"))
    sh = {f: _read(os.path.join(d, f)) for f in sorted(os.listdir(d)) if f.endswith(".sh")}
    out += wall_stop_past(dict(own, **sh))
    out += cpus_in_argv(own)
    if not (spec.get("fresh_server_per_visit") is True and str(spec.get("fresh_server_reason") or "").strip()):
        for f, ln in fresh_server_per_iter(code)[:1]:
            out.append(("WARN", "FRESH-SERVER-UNJUSTIFIED", f"{f}:{ln}: a server is started per loop iteration; default is one "
                                                            "server per arm/condition with cache_prompt:false on every request, "
                                                            "or set spec fresh_server_per_visit=true + fresh_server_reason"))
    elif fresh_server_per_iter(code):
        cap = spec.get("fresh_server_starts", 3)
        if not re.search(r"fresh_server_starts", allc, re.I):
            out.append(("WARN", "FRESH-SERVER-UNCAPPED", f"fresh_server_per_visit=true but no code reads the cap "
                                                         f"(FRESH_SERVER_STARTS / spec fresh_server_starts = {cap} per arm): "
                                                         "starts beyond the cap must reuse a server with cache_prompt:false"))
        if isinstance(cap, int) and cap > 3 and not str(spec.get("fresh_server_starts_reason") or "").strip():
            out.append(("WARN", "FRESH-SERVER-UNCAPPED", f"fresh_server_starts={cap} > 3 per arm with no "
                                                         "fresh_server_starts_reason"))
    rule = " ".join(str(spec.get(k) or "") for k in ("decision_rule", "notes"))
    knobs = sorted(set(KNOB_RX.findall(rule)))
    if knobs and not WITNESS_RX.search(allc):
        out.append(("WARN", "NO-WITNESS", f"decision rule names {knobs[:3]} but no RESULT witness key; prove the knob "
                                          "took effect or file FUTILITY_WITNESS"))
    out += mech_unwitnessed(spec, allc)
    if (REPLAY_RX.search(rid) or REPLAY_RX.search(rule)) and not BASELINE_RX.search(allc):
        out.append(("WARN", "REPLAY-NO-BASELINE", "replay row with no baseline validation (baseline_ok / "
                                                  "validate_baseline): an unvalidated replay baseline is not a control"))
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    selftest = "--no-selftest" not in argv
    argv = [a for a in argv if a != "--no-selftest"]
    if not argv:
        print(__doc__)
        return 2
    bad = 0
    for d in argv:
        res = lint_dir(d, selftest=selftest)
        for lvl, code, msg in res:
            print(f"{lvl} {code} {d}: {msg}")
        bad += sum(1 for r in res if r[0] == "FAIL")
        if not res:
            print(f"OK {d}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
