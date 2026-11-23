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
  SEALED-SPEC        FAIL  SOURCE.sha256 (or SOURCES.sha256 / SOURCE-SHA256SUMS) lists spec.json
  STALE-OUT          FAIL  out/ or out-smoke/ files older than SOURCE.sha256 (left by an earlier attempt)
  SERVER-NO-TRAP     FAIL  a script that starts a server in the background with no trap ... EXIT (shell) or no
                           atexit/finally/signal cleanup (python)
  PY-COMPILE         FAIL  a row .py that does not compile
  SELFTEST           FAIL  job.py --selftest (when job.py supports it) exits non-zero or exceeds 60 s
  CLAIM-PARSE        FAIL  launch.sh parses WS58_REGIONS with tr/grep/paste/sed/awk; use C=${WS58_CPUS:-<claim>}
  SMOKE-FAIL-SILENT  WARN  smoke code with no ak_row_harness.end_smoke(verdict, rc, reason)
  SMOKE-NO-MEASURE   WARN  smoke code with no ak_row_harness.write_smoke_measure(...)
  NO-WITNESS         WARN  the decision rule names a GGML_/LLAMA_ knob and no row code records a witness key
  REPLAY-NO-BASELINE WARN  a replay row with no baseline validation (baseline_ok / validate_baseline / replay_baseline)
Usage: ak_row_lint.py [--no-selftest] <row_dir> [<row_dir> ...]   (read-only, except job.py --selftest when present)
"""
import io
import json
import os
import re
import subprocess
import sys
import tokenize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ak_row_harness as H  # noqa: E402

GUARD_RX = re.compile(r"bench_readbw|read_sum|class\s+Probe|probe_p50|MAX_TRIES|contended", re.I)
BACKOFF_RX = re.compile(r"backoff|ak_row_harness|time\.sleep\(\s*(?:[2-9]\d|\d{3,})", re.I)
PORT_ARG_RX = re.compile(r"--port[ =]+([\d,]+)")
PORT_LIT_RX = re.compile(r"\bport\w*\s*[=:]\s*(\d{4,5})\b", re.I)
DIFFERS_RX = re.compile(r"differ", re.I)
LIB_RX = re.compile(r"lib[\w-]+\.so")
DERIVED_RX = re.compile(r"touched_libs|libs_differ|fold_row_guard")
SHA_CHECK_RX = re.compile(r"sha256sum\s+(?:--\w+\s+|-c\s+)*(?:--check|-c)\b(?:\s+--\w+)*\s+(\"[^\"]+\"|'[^']+'|[^\s<|;&]+)")
CD_RX = re.compile(r"^\s*cd\s+(\"[^\"]+\"|'[^']+'|\S+)", re.M)
VAR_RX = re.compile(r"^\s*(?:export\s+)?([A-Za-z_]\w*)=(\"[^\"$`]*\"|'[^']*'|[^\s;$`\"']+)\s*$", re.M)
SEAL_FILES = ("SOURCE.sha256", "SOURCES.sha256", "SOURCE-SHA256SUMS")
SERVER_RX = re.compile(r"llama-server|sd-server|whisper-server|qwentts-server|llama-cli")
SH_BG_SERVER_RX = re.compile(r"(?:llama-server|sd-server|whisper-server|qwentts-server)[^\n#]*&\s*(?:#.*)?$", re.M)
SH_TRAP_RX = re.compile(r"^\s*trap\s+.+\b(?:EXIT|0)\b", re.M)
PY_CLEANUP_RX = re.compile(r"\batexit\b|finally\s*:|signal\.signal\(|with\s+[\w.]*(?:Popen|server)\w*\(")
CLAIM_PARSE_RX = re.compile(r"WS58_REGIONS[^\n]*\|\s*(?:tr|grep|paste|sed|awk)\b|(?:tr|grep|paste|sed|awk)\b[^\n|]*WS58_REGIONS")
SMOKE_RX = re.compile(r"TERMINAL-smoke|FILLER_SMOKE|FILLER_DRYRUN")
KNOB_RX = re.compile(r"\b(?:GGML|LLAMA)_[A-Z0-9_]{2,}\b")
WITNESS_RX = re.compile(r"[\"']\w*witness\w*[\"']", re.I)
REPLAY_RX = re.compile(r"replay", re.I)
BASELINE_RX = re.compile(r"baseline_ok|baseline_valid|validate_baseline|replay_baseline|baseline_check|baseline_match", re.I)
SELFTEST_TIMEOUT_S = 60
# vendored, sha-pinned helper copies (own SOURCE/BIN pin): never linted for row-authoring defects
VENDORED = {"gpu_common.py", "gpuproof_row.py", "lp_common.py", "base.py", "fold_row_guard.py"}


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


def lint_dir(d, selftest=True, spec=None):
    out = []
    if spec is None:
        try:
            spec = json.loads(_read(os.path.join(d, "spec.json")) or "{}")
        except ValueError:
            spec = {}
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
            _, w = H.check_spec_estimate(spec)
            for x in w:
                out.append(("FAIL", "ESTIMATE-UNMEASURED", x))
        except ValueError as e:
            out.append(("FAIL", "ESTIMATE-UNMEASURED", str(e)))

    for f, t in code.items():
        if f not in VENDORED and _differs_proof(t) and not DERIVED_RX.search(t):
            out.append(("FAIL", "DIFFERS-FIXED", f"{f}: library 'differs' proof over a fixed list; derive it with "
                                                 "fold_row_guard.touched_libs/libs_differ"))

    out += sha_cwd(d, launch)
    out += sealed_spec(d)
    out += stale_out(d)
    out += server_no_trap(d, code)
    out += py_compile_and_selftest(d, code, selftest)
    if CLAIM_PARSE_RX.search(launch):
        out.append(("FAIL", "CLAIM-PARSE", "launch.sh parses WS58_REGIONS with tr/grep/paste/sed; use "
                                           "C=${WS58_CPUS:-<claim>} (keeper exports digit-only WS58_CPUS)"))

    own = {f: t for f, t in code.items() if f not in VENDORED}
    allc = "\n".join(own.values())
    if SMOKE_RX.search(allc):
        if "end_smoke(" not in allc:
            out.append(("WARN", "SMOKE-FAIL-SILENT", "smoke path with no ak_row_harness.end_smoke(verdict, rc, reason): "
                                                     "a failed smoke leaves no reason"))
        if "write_smoke_measure(" not in allc:
            out.append(("WARN", "SMOKE-NO-MEASURE", "smoke path with no ak_row_harness.write_smoke_measure(...): the "
                                                    "estimate cannot be derived"))
    rule = " ".join(str(spec.get(k) or "") for k in ("decision_rule", "notes"))
    knobs = sorted(set(KNOB_RX.findall(rule)))
    if knobs and not WITNESS_RX.search(allc):
        out.append(("WARN", "NO-WITNESS", f"decision rule names {knobs[:3]} but no RESULT witness key; prove the knob "
                                          "took effect or file FUTILITY_WITNESS"))
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
