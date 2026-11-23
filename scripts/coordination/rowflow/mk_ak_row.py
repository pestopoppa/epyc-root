#!/usr/bin/env python3
"""mk_ak_row.py - scaffold an AK (autokernel) measurement row with the 2026-11-23 failure-audit fixes baked in.

What every scaffolded row gets (ak-failure-audit-20261123/REPORT.md A2-A12; checked by ak_row_lint.py):
  * launch.sh: `cd "$D"` before `sha256sum --check --status SOURCE.sha256` (SHA-CWD); the claim is
    `C=${WS58_CPUS:-<claim>}` (digit-only, never parsed out of WS58_REGIONS: CLAIM-PARSE); --port from
    ak_row_harness.alloc_ports(id, n) (HARDCODED-PORT).
  * job.py: servers started by start_server() are killed at exit (atexit + SIGTERM handler + finally: SERVER-NO-TRAP);
    the smoke ends through ak_row_harness.end_smoke(verdict, rc, reason) (SMOKE-FAIL-SILENT) after
    write_smoke_measure(...) (SMOKE-NO-MEASURE); a knob row must record RESULT["witness"] proving the knob took effect,
    otherwise the verdict is FUTILITY_WITNESS (NO-WITNESS); `--selftest` runs the pure logic with no compute.
  * ak_row_harness.py vendored and sealed; SOURCE.sha256 never lists spec.json (SEALED-SPEC); no out/ or out-smoke/.
  * ak_row_lint runs (incl. job.py --selftest) BEFORE spec.json is written; any FAIL aborts with no spec.json.

The scaffold is a starting point: fill measure_unit() / decide() in job.py, re-run with --reseal to re-seal and re-lint.
Usage:
  mk_ak_row.py --id ak-x-cpu-20261124 --task file.md:TASK --model "..." --rule "KEEP iff ..." [--knob GGML_X]...
               [--lane cpu|gpu] [--claim "any-of q0,q1,q2"] [--servers 1] [--threads 24] [--estimate-s 3600]
               [--min-window 1800] [--root /mnt/raid0/llm/tmp]
  mk_ak_row.py --reseal <row_dir>        re-seal (without spec.json) and lint an edited scaffold
"""
import argparse
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ak_row_harness as H  # noqa: E402
import ak_row_lint as LINT  # noqa: E402

ROOT = "/mnt/raid0/llm/tmp"
FILLER = "/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh"
SEALED = ("job.py", "check_complete.py", "launch.sh", "ak_row_harness.py")

LAUNCH = """#!/bin/bash
# {id} (autokernel; {task}). Scaffolded by mk_ak_row.py.
set -euo pipefail
D={d}
C=${{WS58_CPUS:-{claim}}}
cd "$D"
ulimit -c 0
/usr/bin/sha256sum --check --status SOURCE.sha256
exec /bin/bash {filler} --id {id} \\
  --class {lane} --claim-cpus "$C" --role bench --min-window {min_window}{port_arg} \\
  --cmd "/usr/bin/python3 -I -B $D/job.py" \\
  --complete-cmd "/usr/bin/python3 -I -B $D/check_complete.py" \\
  --stop "$D/STOP" --workdir "$D"
"""

JOB = '''#!/usr/bin/python3
"""{id} (autokernel; {task}).
RULE: {rule}
KNOBS (witness required): {knobs}
Scaffolded by mk_ak_row.py: fill measure_unit() and decide(); keep start_server/end_smoke/write_smoke_measure/witness."""
import atexit
import json
import os
import signal
import subprocess
import sys
import time

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
import ak_row_harness as H  # noqa: E402

ROW_ID = {id!r}
KNOBS = {knob_list!r}
N_SERVERS = {servers}
OUT = os.path.join(D, "out")
OUT_SMOKE = os.path.join(D, "out-smoke")
SMOKE = os.environ.get("FILLER_SMOKE") == "1" or os.environ.get("FILLER_DRYRUN") == "1"
_SERVERS = []


def ports():
    env = [int(x) for x in os.environ.get("FILLER_PORTS", "").split(",") if x.strip().isdigit()]
    return env[:N_SERVERS] if len(env) >= N_SERVERS else H.alloc_ports(ROW_ID, N_SERVERS)


def _kill_servers(*_a):
    """Kill only the servers this job started (captured Popen handles), TERM then KILL, and confirm they are gone."""
    while _SERVERS:
        p = _SERVERS.pop()
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(30)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(30)


def _on_term(signum, _frame):
    _kill_servers()
    sys.exit(128 + signum)


atexit.register(_kill_servers)
signal.signal(signal.SIGTERM, _on_term)


def start_server(argv, log_path, env=None):
    """Start a server process owned (and killed at exit) by this job."""
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    log = open(log_path, "ab")
    p = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
    _SERVERS.append(p)
    return p


def measure_unit(port, unit):
    """TODO: one measured unit. Return a dict; for a knob row include proof the knob took effect under "witness"."""
    raise NotImplementedError("fill measure_unit() before publishing")


def decide(units):
    """TODO: the RULE above over the measured units. Returns a terminal verdict string."""
    raise NotImplementedError("fill decide() before publishing")


def witness_ok(witness):
    """Every knob in KNOBS must be witnessed (present and truthy) in RESULT["witness"]."""
    return all(witness.get(k) for k in KNOBS)


def finish(units, witness, extra=None):
    verdict = decide(units)
    if KNOBS and not witness_ok(witness):
        verdict = "FUTILITY_WITNESS"
    res = {{"complete": True, "verdict": verdict, "witness": witness, "units": units, "row": ROW_ID,
            "utc": H.now(), **(extra or {{}})}}
    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join(OUT, "RESULT.json.tmp")
    with open(tmp, "w") as f:
        json.dump(res, f, indent=1)
    os.replace(tmp, os.path.join(OUT, "RESULT.json"))
    return res


def smoke():
    t0 = time.time()
    try:
        # TODO: start the server(s) on ports(), run ONE unit, time it.
        u0 = time.time()
        r = measure_unit(ports()[0], 0)
        unit_s = time.time() - u0
        H.write_smoke_measure(OUT_SMOKE, unit_s, 1, u0 - t0)
        if KNOBS and not witness_ok(r.get("witness") or {{}}):
            return H.end_smoke("FAIL", 3, f"knob witness missing for {{KNOBS}}", OUT)
        return H.end_smoke("PASS", 0, f"1 unit in {{unit_s:.1f}} s", OUT)
    except Exception as e:  # noqa: BLE001 - the smoke must always say why it failed
        return H.end_smoke("FAIL", 3, f"{{e.__class__.__name__}}: {{e}}", OUT)
    finally:
        _kill_servers()


def main():
    if SMOKE:
        return smoke()
    try:
        units, witness = [], {{}}
        # TODO: start servers, loop units (H.run_quiet for CPU quiet-host rows), fill witness from the server's own output.
        finish(units, witness)
        return 0
    finally:
        _kill_servers()


def selftest():
    """No compute: the witness rule and the smoke terminal record."""
    import tempfile
    global KNOBS
    saved = KNOBS
    try:
        KNOBS = ["GGML_TEST_KNOB"]
        assert not witness_ok({{}}) and witness_ok({{"GGML_TEST_KNOB": "on in log"}})
        with tempfile.TemporaryDirectory() as t:
            assert H.end_smoke("FAIL", 3, "selftest", t, stream=open(os.devnull, "w")) == 3
            assert json.load(open(os.path.join(t, H.TERMINAL_SMOKE)))["reason"] == "selftest"
    finally:
        KNOBS = saved
    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv[1:] else main())
'''

CHECK = '''#!/usr/bin/python3
"""rc 0 iff out/RESULT.json is complete, terminal, and (knob rows) witnessed or FUTILITY_WITNESS."""
import json, sys
try:
    r = json.load(open({result!r}))
except (OSError, ValueError):
    sys.exit(1)
v = str(r.get("verdict") or "")
sys.exit(0 if r.get("complete") is True and v and not v.startswith(("SMOKE", "STOPPED")) else 1)
'''


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def seal(d):
    """SOURCE.sha256 over the row's code, never spec.json."""
    files = [f for f in SEALED if os.path.exists(os.path.join(d, f))]
    with open(os.path.join(d, "SOURCE.sha256"), "w") as f:
        f.write("".join(f"{_sha(os.path.join(d, x))}  {x}\n" for x in files))


def lint(d):
    res = LINT.lint_dir(d)
    for lvl, code, msg in res:
        print(f"{lvl} {code} {d}: {msg}")
    return [r for r in res if r[0] == "FAIL"]


def scaffold(a):
    d = os.path.join(a.root, a.id)
    if os.path.exists(d):
        raise SystemExit(f"mk_ak_row: {d} exists; pick a new -rN id")
    os.makedirs(d)
    port_list = H.alloc_ports(a.id, a.servers) if a.servers else []
    port_arg = f" --port {','.join(map(str, port_list))}" if port_list else ""
    claim = a.claim or ("any-of q0,q1,q2" if a.lane == "cpu" else "184-191")
    with open(os.path.join(d, "launch.sh"), "w") as f:
        f.write(LAUNCH.format(id=a.id, task=a.task, d=d, claim=claim, filler=FILLER, lane=a.lane,
                              min_window=a.min_window, port_arg=port_arg))
    os.chmod(os.path.join(d, "launch.sh"), 0o755)
    with open(os.path.join(d, "job.py"), "w") as f:
        f.write(JOB.format(id=a.id, task=a.task, rule=a.rule, knobs=", ".join(a.knob) or "none", knob_list=list(a.knob),
                           servers=a.servers))
    with open(os.path.join(d, "check_complete.py"), "w") as f:
        f.write(CHECK.format(result=os.path.join(d, "out", "RESULT.json")))
    shutil.copy(os.path.join(HERE, "ak_row_harness.py"), os.path.join(d, "ak_row_harness.py"))
    seal(d)
    spec = {"owner": "autokernel", "schema": "epyc.row.v3", "kind": "compute", "lane": a.lane, "id": a.id,
            "regions": claim, "claim_cpus": claim, "verdict_by": "agent", "launcher": os.path.join(d, "launch.sh"),
            "result_path": os.path.join(d, "out", "RESULT.json"), "result_format": "json", "scratch_root": d,
            "workdir": d, "stop_file": os.path.join(d, "STOP"), "estimate_s": a.estimate_s,
            "min_window_s": a.min_window, "declared_threads": a.threads, "handoff_task": a.task, "model": a.model,
            "smoke_predicate": "/usr/bin/test -s " + os.path.join(d, "out", H.TERMINAL_SMOKE),
            "decision_rule": a.rule + (" | knobs: " + ", ".join(a.knob) if a.knob else ""),
            "notes": "scaffolded by mk_ak_row.py; estimate_basis: add after the smoke (ak_row_harness.estimate_from_smoke)"}
    return d, spec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--reseal")
    ap.add_argument("--id")
    ap.add_argument("--task", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--rule", default="")
    ap.add_argument("--knob", action="append", default=[])
    ap.add_argument("--lane", choices=("cpu", "gpu"), default="cpu")
    ap.add_argument("--claim")
    ap.add_argument("--servers", type=int, default=1)
    ap.add_argument("--threads", type=int, default=24)
    ap.add_argument("--estimate-s", type=int, default=3600)
    ap.add_argument("--min-window", type=int, default=1800)
    ap.add_argument("--root", default=ROOT)
    a = ap.parse_args(argv)
    if a.reseal:
        seal(a.reseal)
        return 1 if lint(a.reseal) else 0
    if not (a.id and a.task and a.rule):
        ap.error("--id, --task and --rule are required")
    d, spec = scaffold(a)
    fails = lint(d)
    if fails:
        print(f"mk_ak_row: {d} fails ak_row_lint; spec.json NOT written", file=sys.stderr)
        return 1
    with open(os.path.join(d, "spec.json"), "w") as f:
        json.dump(spec, f, indent=1)
    print(f"mk_ak_row: scaffolded {d} (lint clean, spec.json written last; fill job.py then --reseal)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
