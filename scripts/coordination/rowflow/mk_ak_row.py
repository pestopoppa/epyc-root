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
  * servers: ONE server per arm/condition, many requests; request() sends cache_prompt:false on every request so no
    slot/prompt-cache state carries over. A fresh server per visit only with --fresh-server-reason (spec
    fresh_server_per_visit=true + fresh_server_reason; else ak_row_lint FRESH-SERVER-UNJUSTIFIED).
  * ak_row_harness.py vendored and sealed; SOURCE.sha256 never lists spec.json (SEALED-SPEC); no out/ or out-smoke/.
  * spec.json: explicit requires_quiet_host (true for CPU timing rows, false for GPU rows), exclusive_cpu only with
    --exclusive-cpu (gate rows); a CPU row has no --claim-cpus (the grant's cpus).
  * the publish hint printed at the end names the DEPLOYED publish_row.py (compute-flags/bin/rowflow), never a checkout.
  * ak_row_lint runs (incl. job.py --selftest) BEFORE spec.json is written; any FAIL aborts with no spec.json.

The scaffold is a starting point: fill measure_unit() / decide() in job.py, re-run with --reseal to re-seal and re-lint.
Usage:
  mk_ak_row.py --id ak-x-cpu-20261124 --task file.md:TASK --model "..." --rule "KEEP iff ..." [--knob GGML_X]...
               [--lane cpu|gpu] [--claim "any-of q0,q1,q2"] [--servers 1] [--threads 24] [--estimate-s 3600]
               [--min-window 1800] [--root /mnt/raid0/llm/tmp] [--exclusive-cpu] [--no-quiet-host]
               [--served-ref <registry-role> [--orch-repo /workspace/repos/epyc-orchestrator]]
  mk_ak_row.py --reseal <row_dir>        re-seal (without spec.json) and lint an edited scaffold
  mk_ak_row.py polar new|--lint|--seal   the polar/akloop profile (the retired row_scaffold.py, same arguments)
  mk_ak_row.py gate new --knob NAME:MARKER[:LEVEL] --arm NAME:KNOB=VAL,... --metric M --keep-rule R --served-ref ROLE
                                         a DECLARED knob gate row: job.py is a declaration, ak_gate.py owns the harness

v2 (2026-11-24, RCA ak-row-robustness-rca-20261124 F1/F2) - this is the ONLY row generator:
  * job.py carries `# GENERATED-BY: mk_ak_row.py v2 harness_sha256=<sha>` and spec.json a `generator` block (publish
    refuses unstamped rows warn-first; pipeline-mgmt).
  * harness helpers: H.append_unit (fsync'd results.jsonl), H.grant_cpus (one env source), H.bench_json (llama-bench
    JSON with interleaved stderr), H.require_grant (exit 64 without FILLER_ID/FILLER_DRYRUN), H.tbo_cases.
  * smoke() starts the production server (SERVER_ARGV) and runs ONE real measure_unit(); --selftest runs smoke() against
    a stub in a tempdir; default smoke_predicate = TERMINAL-smoke.json ok:true AND mtime >= $FILLER_SMOKE_T0.
  * --served-ref ROLE: SERVER_ARGV is built by the orchestrator's own launcher (build_server_command over the registry
    role: serving_shape + canonical recipe), port/slot dir as the only argv_delta; spec.served_ref records role, argv
    sha, registry sha and orchestrator commit for the pipeline preflight diff.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ak_row_harness as H  # noqa: E402
import ak_row_lint as LINT  # noqa: E402

ROOT = "/mnt/raid0/llm/tmp"
FILLER = "/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh"
PUBLISH = "/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/publish_row.py"   # the deployed copy (deploy_rowflow.sh)
CLAIM_RX = re.compile(r"^[0-9]+(-[0-9]+)?(,[0-9]+(-[0-9]+)?)*$")
SEALED = ("job.py", "check_complete.py", "launch.sh", "ak_row_harness.py", "ak_gate.py")
GEN_VERSION = "v2"   # v2 (RCA ak-row-robustness-rca-20261124 F1/F2): stamp, harness helpers, production-argv smoke
ORCH_REPO = "/workspace/repos/epyc-orchestrator"
# Default smoke predicate: THIS run's terminal smoke record, ok:true, written at/after the launch (FILLER_SMOKE_T0; unset
# fails closed). A leftover file from an earlier attempt can never pass it (RCA RC4 / F4).
SMOKE_PRED = ("/usr/bin/grep -q '\"ok\": true' {p} && "
              "[ \"$(/usr/bin/stat -c %Y {p})\" -ge \"${{FILLER_SMOKE_T0:?}}\" ]")

LAUNCH = """#!/bin/bash
# {id} (autokernel; {task}). Scaffolded by mk_ak_row.py.
set -euo pipefail
D={d}
{claim_line}cd "$D"
ulimit -c 0
/usr/bin/sha256sum --check --status SOURCE.sha256
exec /bin/bash {filler} --id {id} \\
  --class {lane}{claim_arg} --role bench --min-window {min_window}{port_arg} \\
  --cmd "/usr/bin/python3 -I -B $D/job.py" \\
  --complete-cmd "/usr/bin/python3 -I -B $D/check_complete.py" \\
  --stop "$D/STOP" --workdir "$D"
"""

JOB = '''#!/usr/bin/python3
"""{id} (autokernel; {task}).
RULE: {rule}
KNOBS (witness required): {knobs}
Scaffolded by mk_ak_row.py: fill measure_unit() and decide(); keep start_server/end_smoke/write_smoke_measure/witness."""
# GENERATED-BY: mk_ak_row.py {gen_version} harness_sha256={harness_sha}
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
# fresh server starts per arm (only when spec fresh_server_per_visit): at most this many process samples, the remaining
# requests reuse those servers with cache_prompt:false (D9 2026-11-24)
FRESH_SERVER_STARTS = {fresh_starts}
OUT = os.path.join(D, "out")
OUT_SMOKE = os.path.join(D, "out-smoke")
SMOKE = os.environ.get("FILLER_SMOKE") == "1" or os.environ.get("FILLER_DRYRUN") == "1"
_SERVERS = []
# The production server argv. With mk_ak_row --served-ref it is DERIVED from the orchestrator registry (spec.served_ref
# records role, registry sha and orchestrator commit; pipeline preflight re-derives and diffs it). "{{PORT}}" and
# "{{SLOTDIR}}" are the only allowed deltas (spec.served_ref.argv_delta). Empty = not a served-path row: fill it from the canonical recipe.
SERVER_ARGV = {server_argv!r}


def server_argv(port):
    slots = os.path.join(OUT, "kv_slots")
    return [str(port) if a == "{{PORT}}" else slots if a == "{{SLOTDIR}}" else a for a in SERVER_ARGV]


def cpus():
    """The granted cpus (ONE env source: WS58_CPUS, then FILLER_CPUS)."""
    return H.grant_cpus()


def cpu_str():
    """The granted cpus as a compact taskset/numactl string ('0-23,48-71'). cpus() is a LIST of ints: never put it in an
    argv (subprocess TypeError); use cpu_str() for `taskset -c` / `numactl --physcpubind`."""
    return H.cpu_str(cpus())


def ports():
    env = [int(x) for x in os.environ.get("FILLER_PORTS", "").split(",") if x.strip().isdigit()]
    return env[:N_SERVERS] if len(env) >= N_SERVERS else H.alloc_ports(ROW_ID, N_SERVERS)


def _kill_servers(*_a):
    """Kill only the servers this job started (captured Popen handles) and their children, TERM then KILL, by pid."""
    while _SERVERS:
        p = _SERVERS.pop()
        H.kill_tree(p)


def _on_term(signum, _frame):
    _kill_servers()
    sys.exit(128 + signum)


atexit.register(_kill_servers)
signal.signal(signal.SIGTERM, _on_term)


def start_server(argv, log_path, env=None):
    """Start a server process owned (and killed at exit) by this job."""
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    log = open(log_path, "ab")
    p = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, env=env)   # same session/pgrp as the job: the keeper attributes GPU/KFD use to the grant
    _SERVERS.append(p)
    return p


def request(port, payload, timeout=1800):
    """POST one completion to the arm's (reused) server. cache_prompt is forced False: no slot/prompt-cache carry-over."""
    import urllib.request
    body = dict(payload, cache_prompt=False)
    req = urllib.request.Request(f"http://127.0.0.1:{{port}}/completion", data=json.dumps(body).encode(),
                                 headers={{"Content-Type": "application/json"}})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


{kld_block}def measure_unit(port, unit):
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


def start_production_server(port):
    """The smoke and main() start the SAME server: server_argv(port) (the production argv), log under out/."""
    if not SERVER_ARGV:
        raise RuntimeError("SERVER_ARGV is empty: mk_ak_row --served-ref <role> or fill it from the canonical recipe")
    return start_server(server_argv(port), os.path.join(OUT, f"server-{{port}}.log"))


def smoke():
    """ONE real measure_unit() on the production argv: the smoke exercises the decisive path, not a version probe."""
    t0 = time.time()
    try:
        port = ports()[0]
        start_production_server(port)
        u0 = time.time()
        r = measure_unit(port, 0)
        H.append_unit(dict(r, unit=0, smoke=True), OUT_SMOKE)
        unit_s = time.time() - u0
        H.write_smoke_measure(OUT_SMOKE, unit_s, 1, u0 - t0)
        if KNOBS and not witness_ok(r.get("witness") or {{}}):
            return H.end_smoke("FAIL", 3, f"knob witness missing for {{KNOBS}}", OUT)
{kld_smoke}        return H.end_smoke("PASS", 0, f"1 unit in {{unit_s:.1f}} s", OUT)
    except Exception as e:  # noqa: BLE001 - the smoke must always say why it failed
        return H.end_smoke("FAIL", 3, f"{{e.__class__.__name__}}: {{e}}", OUT)
    finally:
        _kill_servers()


def main():
    H.require_grant()   # no FILLER_ID/FILLER_DRYRUN -> exit 64: never run a row (or its smoke) by hand
    if SMOKE:
        return smoke()
    try:
        units, witness = [], {{}}
        # TODO: start ONE server per arm/condition (start_production_server / start_server), then loop units against it
        # via request() (cache_prompt False), H.append_unit(rec, OUT) after each; H.run_quiet for CPU quiet-host rows;
        # H.bench_json / H.tbo_cases parse llama-bench / test-backend-ops output; fill witness from the server's own
        # output. A server per unit needs spec fresh_server_per_visit + fresh_server_reason (--fresh-server-reason).
        finish(units, witness)
        return 0
    finally:
        _kill_servers()


def selftest():
    """No compute: the witness rule, then smoke() itself against a stub server + stub unit in a tempdir."""
    import tempfile
    global KNOBS, OUT, OUT_SMOKE, start_production_server, measure_unit{kld_global}
    saved = (KNOBS, OUT, OUT_SMOKE, start_production_server, measure_unit)
    try:
        KNOBS = ["GGML_TEST_KNOB"]
        assert not witness_ok({{}}) and witness_ok({{"GGML_TEST_KNOB": "on in log"}})
        with tempfile.TemporaryDirectory() as t:
            assert H.end_smoke("FAIL", 3, "selftest", t, stream=open(os.devnull, "w")) == 3
            assert json.load(open(os.path.join(t, H.TERMINAL_SMOKE)))["reason"] == "selftest"
        with tempfile.TemporaryDirectory() as t:
            OUT, OUT_SMOKE = os.path.join(t, "out"), os.path.join(t, "out-smoke")
            start_production_server = lambda port: None  # noqa: E731 - stub: no process
            measure_unit = lambda port, unit: {{"witness": {{"GGML_TEST_KNOB": "stub"}}, "value": 1.0}}  # noqa: E731
{kld_selftest}            assert smoke() == 0, "smoke() against the stub did not PASS"
            term = json.load(open(os.path.join(OUT, H.TERMINAL_SMOKE)))
            assert term["ok"] is True, term
            assert os.path.exists(os.path.join(OUT_SMOKE, H.SMOKE_MEASURE))
            assert os.path.exists(os.path.join(OUT_SMOKE, H.RESULTS_JSONL))
    finally:
        KNOBS, OUT, OUT_SMOKE, start_production_server, measure_unit = saved
    print("selftest ok")
    return 0


def decide_from(path):
    """R4/R1 replay (no server, no grant): decide() over a previous run's results.jsonl; prints `DECIDE {{json}}`."""
    p = path if os.path.isfile(os.path.join(path, H.RESULTS_JSONL)) else os.path.join(path, "out")
    units = []
    try:
        for ln in open(os.path.join(p, H.RESULTS_JSONL)):
            try:
                units.append(json.loads(ln))
            except ValueError:
                pass
    except OSError:
        pass
    try:
        v = decide(units)
    except Exception as e:  # noqa: BLE001 - a crashing decide() is the finding
        print("DECIDE " + json.dumps({{"error": f"{{e.__class__.__name__}}: {{e}}", "n_units": len(units)}}), flush=True)
        return 3
    print("DECIDE " + json.dumps({{"prev_id": os.path.basename(os.path.dirname(os.path.abspath(p))), "n_units": len(units),
                                  "observed": {{"verdict": v, "n_units": len(units)}}}}), flush=True)
    return 0


if __name__ == "__main__":
    if "--decide-from" in sys.argv[1:]:
        sys.exit(decide_from(sys.argv[sys.argv.index("--decide-from") + 1]))
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


def seal(d, extra=()):
    """SOURCE.sha256 over the row's code, never spec.json. Keeps every file the existing SOURCE.sha256 already lists
    (own_port_proof.py, lp_common.py, ...) plus the defaults and `extra` (a gate row's copied inputs/...)."""
    files = [f for f in SEALED if os.path.exists(os.path.join(d, f))] + [x for x in extra if os.path.isfile(os.path.join(d, x))]
    try:
        with open(os.path.join(d, "SOURCE.sha256")) as f:
            for ln in f:
                q = ln.strip().split(None, 1)
                if len(q) == 2:
                    n = q[1].lstrip("*")
                    if n not in files and os.path.basename(n) != "spec.json" and os.path.isfile(os.path.join(d, n)):
                        files.append(n)
    except OSError:
        pass
    with open(os.path.join(d, "SOURCE.sha256"), "w") as f:
        f.write("".join(f"{_sha(os.path.join(d, x))}  {x}\n" for x in files))


def lint(d):
    res = LINT.lint_dir(d)
    for lvl, code, msg in res:
        print(f"{lvl} {code} {d}: {msg}")
    return [r for r in res if r[0] == "FAIL"]


def harness_sha():
    return _sha(os.path.join(HERE, "ak_row_harness.py"))


RESOLVE_PY = r"""
import hashlib, json, os, sys
role, port = sys.argv[1], int(sys.argv[2])
sys.argv = ["orchestrator_stack"]
sys.path.insert(0, os.getcwd())
import scripts.server.orchestrator_stack as stack
from src.registry_loader import RegistryLoader
reg = RegistryLoader()
rc = reg.get_role(role)
argv = stack.build_server_command(rc, port, prepare_runtime_dirs=False)
shape = None
try:
    import yaml
    y = yaml.safe_load(open("orchestration/model_registry.yaml"))
    def walk(o):
        if isinstance(o, dict):
            if role in o and isinstance(o[role], dict) and "serving_shape" in o[role]:
                return o[role]["serving_shape"]
            for v in o.values():
                r = walk(v)
                if r is not None:
                    return r
    shape = walk(y)
except Exception:
    pass
try:
    from scripts.server import stack_manifest
    rport = int(stack_manifest.PORT_MAP[role]) if role in getattr(stack_manifest, "PORT_MAP", {}) else None
except Exception:
    rport = None
print("RESOLVED " + json.dumps({"argv": [str(x) for x in argv], "serving_shape": shape, "port": rport,
      "registry_sha256": hashlib.sha256(open("orchestration/model_registry.yaml", "rb").read()).hexdigest()}))
"""


DEFAULT_ARM_REASON = "arm-scoped lever delta (mk_ak_row --arm-delta)"


def parse_arm_delta(text):
    """'ARM:flag=value[:reason]' -> {arm, flag, value, reason} (preflight check 11's canonical arm-scoped delta).
    A value without '=' (`ON:--no-warmup`) is a bare flag (value true)."""
    arm, sep, rest = str(text).partition(":")
    if not sep or not arm.strip() or not rest.strip():
        raise SystemExit(f"mk_ak_row: --arm-delta {text!r}: want ARM:flag=value[:reason]")
    if "=" in rest:
        flag, _, tail = rest.partition("=")
        value, _, reason = tail.partition(":")
    else:
        flag, _, reason = rest.partition(":")
        value = True
    if not flag.strip():
        raise SystemExit(f"mk_ak_row: --arm-delta {text!r}: empty flag")
    return {"arm": arm.strip(), "flag": flag.strip(), "value": value, "reason": reason.strip() or DEFAULT_ARM_REASON}


def resolve_served(role, repo=ORCH_REPO, probe_port=27999, timeout=120):
    """The production server argv for registry `role`, built by the orchestrator's OWN launcher
    (orchestrator_stack.build_server_command over RegistryLoader, i.e. serving_shape + the canonical recipe), run in a
    subprocess in `repo` so nothing is imported here. The --port value is replaced by the "{PORT}" placeholder (the row's
    own port is the one allowed delta). Returns the served_ref dict; raises SystemExit with the launcher's error."""
    import subprocess
    p = subprocess.run([sys.executable, "-c", RESOLVE_PY, role, str(probe_port)], cwd=repo, capture_output=True,
                       text=True, timeout=timeout)
    line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESOLVED ")), None)
    if p.returncode != 0 or not line:
        raise SystemExit(f"mk_ak_row: --served-ref {role}: orchestrator launcher failed (rc {p.returncode}): "
                         f"{(p.stderr or p.stdout).strip()[-400:]}")
    r = json.loads(line[len("RESOLVED "):])
    argv = r["argv"]
    reg_port = r.get("port")
    if "--port" in argv:
        i = argv.index("--port") + 1
        argv[i] = "{PORT}"
    if "--slot-save-path" in argv:
        argv[argv.index("--slot-save-path") + 1] = "{SLOTDIR}"
    head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "-C", repo, "status", "--porcelain", "--", "orchestration", "scripts/server",
                                 "src"], capture_output=True, text=True).stdout.strip())
    return {"registry_role": role, "port": reg_port, "argv": argv, "argv_sha256": hashlib.sha256(
                json.dumps(argv).encode()).hexdigest(),
            "argv_delta": [{"flag": "--port", "value": "{PORT}", "reason": "row-owned port (alloc_ports/FILLER_PORTS)"}]
            + ([{"flag": "--slot-save-path", "value": "{SLOTDIR}",
                 "reason": "row-private slot dir (never the production kv_slots)"}] if "{SLOTDIR}" in argv else []),
            "serving_shape": r.get("serving_shape"), "registry_sha256": r.get("registry_sha256"),
            "orchestrator_commit": head, "orchestrator_dirty": dirty, "resolved_utc": H.now(),
            "resolver": "orchestrator_stack.build_server_command(RegistryLoader().get_role(role))"}


def add_witness_loglevel(served):
    """A knob witness is an INFO log line: llama-server needs -lv 4 or it never prints (ak-c22-i8pc-gate-gpu-20261124-r3).
    Adds `-lv 4` to the served argv as a declared argv delta when no log level is given."""
    argv = list(served["argv"])
    if any(t in ("-lv", "--verbosity", "--log-verbose", "--log-verbosity") or t.startswith("--verbosity=") for t in argv):
        return served
    argv += ["-lv", "4"]
    served = dict(served, argv=argv, argv_sha256=hashlib.sha256(json.dumps(argv).encode()).hexdigest())
    served["argv_delta"] = list(served.get("argv_delta") or []) + [
        {"flag": "-lv", "value": "4", "reason": "witness log level"}]
    return served

KLD_BLOCK = '''# KLD unit (mk_ak_row --kld-unit): llama-perplexity. A knob witness is an INFO line, so a knob row runs it with -lv 4
# (spec.tool_argv_delta records it); unit_kld() MUST build its argv with kld_argv() or the witness never prints
# (ak-c22-q8mc-gate-gpu-20261124: the server had -lv 4, unit_kld did not).
KLD_BIN = "/mnt/raid0/llm/llama.cpp/kernels/production/gpu/bin/llama-perplexity"   # TODO: the row's store binary
KLD_MODEL = {model!r}
KLD_CORPUS = "TODO-corpus.txt"   # TODO: the row's KLD corpus
KLD_LV = {kld_lv!r}   # [] when the row declares no knob


def kld_argv(extra=(), ctx=None, chunks=None):
    """The llama-perplexity argv of every KLD unit (and of the smoke witness check): witness log level included."""
    a = [KLD_BIN, "-m", KLD_MODEL, "-f", KLD_CORPUS, *KLD_LV, *extra]
    if ctx:
        a += ["-c", str(ctx)]
    if chunks:
        a += ["--chunks", str(chunks)]
    return a


def kld_witness_check(timeout=55):
    """Smoke: ONE tiny ON perplexity run (1 chunk, -c 128) must print every KNOBS marker. Env ON values come from KLD_ON_ENV."""
    if KLD_CORPUS.startswith("TODO"):
        raise RuntimeError("KLD_CORPUS is still the TODO placeholder: fill it before publishing")
    env = dict(os.environ, **KLD_ON_ENV)
    p = subprocess.run(kld_argv(ctx=128, chunks=1), capture_output=True, text=True, timeout=timeout, env=env)
    out = p.stdout + p.stderr
    return {{k: (k in out) for k in KNOBS}}


KLD_ON_ENV = {{}}   # TODO: the knob env vars in their ON state, e.g. {{"GGML_HIP_Q8MC": "1"}}


'''
KLD_SMOKE = '''        if KNOBS:
            w = kld_witness_check()
            if not witness_ok(w):
                return H.end_smoke("FAIL", 3, f"KLD-path knob witness missing (llama-perplexity -lv): {{w}}", OUT)
'''
KLD_SELFTEST = '''            kld_witness_check = lambda: {{"GGML_TEST_KNOB": True}}  # noqa: E731 - stub: no perplexity process
'''


def add_tool_witness_loglevel(tool, argv):
    """argv delta for a non-server llama binary (llama-perplexity/bench/cli): `-lv 4` unless a log level is already given.
    Returns (argv, [delta]); delta = {tool, flag, value, reason: "witness log level"}."""
    argv = list(argv)
    if any(t in ("-lv", "--verbosity", "--log-verbose", "--log-verbosity") or t.startswith("--verbosity=") for t in argv):
        return argv, []
    return argv + ["-lv", "4"], [{"tool": tool, "flag": "-lv", "value": "4", "reason": "witness log level"}]


def scaffold(a, served=None):
    d = os.path.join(a.root, a.id)
    if os.path.exists(d):
        raise SystemExit(f"mk_ak_row: {d} exists; pick a new -rN id")
    os.makedirs(d)
    port_list = H.alloc_ports(a.id, a.servers) if a.servers else []
    port_arg = f" --port {','.join(map(str, port_list))}" if port_list else ""
    if a.claim is not None and not CLAIM_RX.match(a.claim):
        raise SystemExit(f"mk_ak_row: --claim {a.claim!r} must be a digit/range list like 184-191 or 0-3,8")
    # CPU lane without an explicit --claim: no C= and no --claim-cpus, so the launcher defaults to the grant's cpus
    claim = a.claim or ("any-of q0,q1,q2" if a.lane == "cpu" else "184-191")
    pin = a.claim is not None or a.lane != "cpu"
    claim_line = "C=${WS58_CPUS:-%s}\n" % claim if pin else ""
    claim_arg = ' --claim-cpus "$C"' if pin else ""
    with open(os.path.join(d, "launch.sh"), "w") as f:
        f.write(LAUNCH.format(id=a.id, task=a.task, d=d, claim_line=claim_line, claim_arg=claim_arg, filler=FILLER, lane=a.lane,
                              min_window=a.min_window, port_arg=port_arg))
    os.chmod(os.path.join(d, "launch.sh"), 0o755)
    kld = bool(getattr(a, "kld_unit", False))
    kld_lv, tool_delta = add_tool_witness_loglevel("llama-perplexity", []) if (kld and a.knob) else ([], [])
    kld_lv = kld_lv if tool_delta else []
    with open(os.path.join(d, "job.py"), "w") as f:
        f.write(JOB.format(kld_block=KLD_BLOCK.format(model=a.model, kld_lv=kld_lv) if kld else "",
                           kld_smoke=KLD_SMOKE.format() if kld else "", kld_selftest=KLD_SELFTEST.format() if kld else "",
                           kld_global=", kld_witness_check" if kld else "",
id=a.id, task=a.task, rule=a.rule, knobs=", ".join(a.knob) or "none", knob_list=list(a.knob),
                           servers=a.servers, fresh_starts=a.fresh_server_starts, gen_version=GEN_VERSION,
                           harness_sha=harness_sha(), server_argv=list(served["argv"]) if served else []))
    with open(os.path.join(d, "check_complete.py"), "w") as f:
        f.write(CHECK.format(result=os.path.join(d, "out", "RESULT.json")))
    shutil.copy(os.path.join(HERE, "ak_row_harness.py"), os.path.join(d, "ak_row_harness.py"))
    seal(d)
    spec = {"owner": "autokernel", "schema": "epyc.row.v3", "kind": "compute", "lane": a.lane, "id": a.id,
            "regions": claim, "claim_cpus": claim, "verdict_by": "agent", "launcher": os.path.join(d, "launch.sh"),
            "result_path": os.path.join(d, "out", "RESULT.json"), "result_format": "json", "scratch_root": d,
            "workdir": d, "stop_file": os.path.join(d, "STOP"), "estimate_s": a.estimate_s,
            "min_window_s": a.min_window, "declared_threads": a.threads, "handoff_task": a.task, "model": a.model,
            "smoke_predicate": SMOKE_PRED.format(p=os.path.join(d, "out", H.TERMINAL_SMOKE)),
            "decision_rule": a.rule + (" | knobs: " + ", ".join(a.knob) if a.knob else ""),
            "requires_quiet_host": bool(a.lane == "cpu" and not a.no_quiet_host),
            "notes": "scaffolded by mk_ak_row.py; estimate_basis: add after the smoke (ak_row_harness.estimate_from_smoke)"}
    spec["generator"] = {"tool": "mk_ak_row.py", "version": GEN_VERSION, "harness_sha256": harness_sha(),
                         "utc": H.now()}
    if served:
        spec["served_ref"] = served
    if tool_delta:
        spec["tool_argv_delta"] = tool_delta
    if a.exclusive_cpu:
        spec["exclusive_cpu"] = True
    spec["fresh_server_per_visit"] = bool(a.fresh_server_reason)
    if a.fresh_server_reason:
        spec["fresh_server_reason"] = a.fresh_server_reason
        spec["fresh_server_starts"] = a.fresh_server_starts
    return d, spec


# ======================================================================================================================
# GATE PROFILE (2026-11-25, pipeline-mgmt for AutoKernel): `mk_ak_row.py gate new ...` writes a row whose job.py is a
# thin DECLARATION calling ak_gate.main(SPEC, D). ak_gate.py (vendored + sealed beside ak_row_harness.py) owns fresh
# servers, -lv, ABBA order, per-knob witness, correctness first, A/A guard, smoke, resume and replay.
# ======================================================================================================================
import pprint  # noqa: E402

import ak_gate as G  # noqa: E402

GATE_JOB = '''#!/usr/bin/python3
"""{id} (autokernel gate; {task}). DECLARED gate row (mk_ak_row.py gate new): this file only DECLARES the gate.
ak_gate.py (vendored, sealed) owns the fresh server per visit, -lv >= {lv} on every llama argv, ABBA order, the per-knob
per-arm witness, correctness first, the OFF/OFF2 A/A guard, the smoke, resume and replay. Edit the declaration, then
`mk_ak_row.py --reseal <dir>` (re-seal + lint + --selftest).
RULE: {rule}
KNOBS (witness required, judged per knob per arm): {knobs}
FIX LOOP: python3 -I -B job.py --replay <prior row dir> prints the verdict this declaration reaches on that run's logs"""
# GENERATED-BY: mk_ak_row.py {gen_version} harness_sha256={harness_sha} gate_sha256={gate_sha} profile=gate
import os
import sys

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
import ak_gate as G  # noqa: E402

ROW_ID = {id!r}
KNOBS = {knob_names!r}
# The production server argv ({argv_source}); "{{PORT}}" / "{{SLOTDIR}}" are filled per visit by ak_gate.
SERVER_ARGV = {server_argv}
{extra_argvs}SPEC = {spec}

if __name__ == "__main__":
    sys.exit(G.selftest(SPEC, D) if "--selftest" in sys.argv[1:] else G.main(SPEC, D, sys.argv[1:]))
'''

GATE_CHECK = '''#!/usr/bin/python3
"""rc 0 iff out/RESULT.json is an ak_gate terminal result (complete:true, a verdict, a polar field). Smoke never counts."""
import json, sys
try:
    r = json.load(open({result!r}))
except (OSError, ValueError):
    sys.exit(1)
v = str(r.get("verdict") or "")
sys.exit(0 if r.get("complete") is True and v and "polar" in r and not v.startswith(("SMOKE", "STOPPED", "INCOMPLETE"))
         else 1)
'''

GATE_FRESH_REASON = ("ak_gate: one fresh server per arm visit (resident-server arm bias: the first OFF arm ran slow; "
                     "load-time knobs are read once per process)")


def parse_knob(text, kind=None):
    """'NAME:MARKER[::LEVEL[:CAP]]' -> (name, {kind, marker, level, cap}). The marker may contain ':' (and end in ':8');
    only a '::' separator introduces LEVEL / CAP."""
    name, sep, rest = str(text).partition(":")
    if not sep or not name.strip() or not rest.strip():
        raise SystemExit(f"mk_ak_row gate: --knob {text!r}: want NAME:MARKER[::LEVEL[:CAP]]")
    level, cap = G.MIN_LV, -1
    m = re.match(r"^(.*?)::(\d+)(?::(-?\d+))?$", rest)
    if m and m.group(1).strip():
        rest, level = m.group(1), int(m.group(2))
        cap = int(m.group(3)) if m.group(3) is not None else -1
    k = kind or ("flag" if name.startswith("-") else "env")
    return name.strip(), {"kind": k, "marker": rest, "level": max(level, G.MIN_LV), "cap": cap}


def parse_arm(text, knobs):
    """'ARM:KNOB=VAL,KNOB2=VAL' (or 'ARM' / 'ARM:' for no knob) -> (arm, {knob: value}). Flag knobs: true -> bare flag."""
    arm, _, rest = str(text).partition(":")
    if not arm.strip():
        raise SystemExit(f"mk_ak_row gate: --arm {text!r}: want ARM:KNOB=VAL,...")
    setting = {}
    for part in [x for x in rest.split(",") if x.strip()]:
        k, eq, v = part.partition("=")
        k = k.strip()
        if k not in knobs:
            raise SystemExit(f"mk_ak_row gate: --arm {text!r}: knob {k} is not declared with --knob")
        if knobs[k]["kind"] == "flag":
            setting[k] = True if (not eq or v.strip().lower() in ("true", "1", "on")) else v.strip()
        else:
            if not eq:
                raise SystemExit(f"mk_ak_row gate: --arm {text!r}: env knob {k} needs =VALUE")
            setting[k] = v.strip()
    return arm.strip(), setting


def derive_expect(knobs, arms, overrides=()):
    """Explicit expect table. Default: a knob the arm sets (to anything but '0'/'false') -> present, else absent; an
    observe-only marker -> present in every arm. --expect ARM:KNOB=present|absent,... overrides cells."""
    exp = {}
    for a, setting in arms.items():
        exp[a] = {}
        for k, v in knobs.items():
            if v["kind"] == "observe":
                exp[a][k] = "present"
            else:
                val = setting.get(k)
                exp[a][k] = "present" if (val not in (None, False) and str(val).lower() not in ("0", "false", "off")) \
                    else "absent"
    for o in overrides:
        arm, _, rest = str(o).partition(":")
        if arm not in exp:
            raise SystemExit(f"mk_ak_row gate: --expect {o!r}: unknown arm {arm}")
        for part in [x for x in rest.split(",") if x.strip()]:
            k, _, v = part.partition("=")
            if k.strip() not in knobs or v.strip() not in G.EXPECT_VALUES:
                raise SystemExit(f"mk_ak_row gate: --expect {o!r}: want ARM:KNOB=present|absent")
            exp[arm][k.strip()] = v.strip()
    return exp


def parse_keep_rule(text):
    """'ci_lower>1.01,n=8[,look=4][,aa=0.02|aa=none][,dummy=1]' -> keep dict."""
    k = {}
    for part in [x.strip() for x in str(text or "").split(",") if x.strip()]:
        m = re.match(r"^(?:ci_lower|threshold)\s*[>=]+\s*([\d.]+)$", part)
        if m:
            k["threshold"] = float(m.group(1))
            continue
        key, _, v = part.partition("=")
        key = key.strip()
        if key in ("n", "n_blocks"):
            k["n_blocks"] = int(v)
        elif key in ("look", "look_blocks"):
            k["look_blocks"] = int(v)
        elif key in ("aa", "aa_max"):
            k["aa_max"] = None if v.strip().lower() in ("none", "null", "off") else float(v)
        elif key in ("dummy", "dummy_block"):
            k["dummy_block"] = v.strip().lower() in ("1", "true", "yes", "on")
        else:
            raise SystemExit(f"mk_ak_row gate: --keep-rule part {part!r} not ci_lower>X|n=|look=|aa=|dummy=")
    if "threshold" not in k:
        raise SystemExit("mk_ak_row gate: --keep-rule needs ci_lower>X (the KEEP threshold on the CI lower bound)")
    return k


def _argv_lit(argv, indent=14):
    return pprint.pformat([str(x) for x in argv], width=118, indent=1, compact=True).replace("\n", "\n" + " " * indent)


def gate_scaffold(a, served=None):
    """Write the gate row. Returns (row dir, spec.json dict). Raises SystemExit on a bad declaration."""
    knobs = dict(parse_knob(x) for x in a.knob)
    for x in a.observe:
        n, v = parse_knob(x, kind="observe")
        knobs[n] = v
    if not knobs:
        raise SystemExit("mk_ak_row gate: declare >= 1 --knob NAME:MARKER[:LEVEL]")
    arms = dict(parse_arm(x, knobs) for x in a.arm)
    if len(arms) < 2:
        raise SystemExit("mk_ak_row gate: declare >= 2 --arm (e.g. OFF: OFF2: ON:GGML_X=1)")
    baseline = [x.strip() for x in a.baseline.split(",")] if a.baseline else [k for k, v in arms.items() if not v]
    expect = derive_expect(knobs, arms, a.expect)
    lv = max([G.MIN_LV] + [v["level"] for v in knobs.values()])
    if served:
        argv = list(served["argv"])
        src = f"orchestrator registry role {served['registry_role']}, spec.served_ref"
    elif a.server_argv_json:
        argv = json.loads(a.server_argv_json)
        src = "declared with --server-argv-json"
    else:
        raise SystemExit("mk_ak_row gate: --served-ref ROLE (preferred) or --server-argv-json '[...]' is required")
    argv = G.ensure_lv(argv, lv)
    if served:
        served = add_witness_loglevel(dict(served, argv=argv)) if G.argv_lv(served["argv"]) is None else \
            dict(served, argv=argv, argv_sha256=hashlib.sha256(json.dumps(argv).encode()).hexdigest())
        if G.argv_lv(served["argv"]) != G.argv_lv(argv):
            served["argv_delta"] = list(served.get("argv_delta") or []) + [
                {"flag": "-lv", "value": str(lv), "reason": "witness log level"}]
    m = G.METRICS.get(a.metric)
    if m is None:
        raise SystemExit(f"mk_ak_row gate: --metric {a.metric!r} not one of {sorted(G.METRICS)}")
    keep = parse_keep_rule(a.keep_rule)
    if not a.model:
        mp = next((argv[i + 1] for i, t in enumerate(argv[:-1]) if t in ("-m", "--model")), "")
        a.model = os.path.basename(mp)[:-5] if mp.endswith(".gguf") else os.path.basename(mp)
        if not a.model:
            raise SystemExit("mk_ak_row gate: --model not given and the server argv has no -m <gguf>")
    if not a.rule.strip():
        a.rule = (f"KEEP iff {a.metric} ({'higher' if m[1] else 'lower'} is better) speedup CI lower > "
                  f"{keep['threshold']} over the ABBA blocks, witness + correctness + A/A first")
    d = os.path.join(a.root, a.id)
    if os.path.exists(d):
        raise SystemExit(f"mk_ak_row: {d} exists; pick a new -rN id")
    bindir = os.path.dirname(str(argv[G.llama_index(argv) or 0]))
    env = {"PATH": "/usr/bin:/bin" + (":/opt/rocm/bin" if a.lane == "gpu" else ""),
           "LD_LIBRARY_PATH": bindir + (":/opt/rocm/lib" if a.lane == "gpu" else "")}
    if a.lane == "gpu":
        env.update(HIP_VISIBLE_DEVICES="0", ROCM_PATH="/opt/rocm")
    else:
        env.update(HIP_VISIBLE_DEVICES="-1", ROCR_VISIBLE_DEVICES="-1")
    for kv in a.server_env:
        k, _, v = kv.partition("=")
        env[k.strip()] = v
    os.makedirs(os.path.join(d, "inputs"))
    inputs = {}
    for ci in a.copy_input:
        srcp, _, rel = ci.partition(":")
        rel = rel or os.path.join("inputs", os.path.basename(srcp))
        dst = os.path.join(d, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(srcp, dst)
        inputs[rel] = _sha(dst)
    workload = {"n_predict": a.n_predict}
    if a.prompt:
        workload["prompts"] = list(a.prompt)
    elif a.workload_input:
        if a.workload_input not in inputs:
            raise SystemExit(f"mk_ak_row gate: --workload-input {a.workload_input} must be a --copy-input destination")
        workload.update(input=a.workload_input, offsets=[int(x) for x in a.offsets.split(",")], win_chars=a.win_chars,
                        suffix=a.prompt_suffix)
    else:
        raise SystemExit("mk_ak_row gate: declare the workload: --prompt TEXT (repeatable) or --workload-input inputs/X")
    corr = json.loads(open(a.correctness[1:]).read() if a.correctness.startswith("@") else a.correctness) \
        if a.correctness else None
    extra_argvs, tool_delta = "", []
    if corr and corr.get("argv"):
        ca = [str(x) for x in corr["argv"]]
        if corr.get("kind") != "tbo" or corr.get("lv"):
            new = G.ensure_lv(ca, lv, force=bool(corr.get("lv")) or corr.get("kind") == "identity")
            if new != ca:
                tool_delta.append({"tool": os.path.basename(ca[0]), "flag": "-lv", "value": str(lv),
                                   "reason": "witness log level"})
            ca = new
        corr["argv"] = "@@CORRECTNESS_ARGV@@"
        extra_argvs = f"CORRECTNESS_ARGV = {_argv_lit(ca, 19)}\n"
    kc = dict(G.keep_cfg({"keep": keep}))
    starts = kc["n_blocks"] + (1 if kc["dummy_block"] else 0)
    spec_g = {"row_id": a.id, "task": a.task, "rule": a.rule, "lane": a.lane, "knobs": knobs, "arms": arms,
              "baseline": baseline, "expect": expect,
              "witness_rule": "each knob judged alone per arm against expect (ak_gate.witness_for); never an AND",
              "server": {"argv": "@@SERVER_ARGV@@", "env": env, "warmup": a.warmup, "ready_timeout_s": a.ready_timeout_s,
                         "membind": a.membind if a.membind is not None else (3 if a.lane == "gpu" else None),
                         "kfd_min_vram_gib": a.kfd_min_vram_gib if a.kfd_min_vram_gib is not None else
                         (1 if a.lane == "gpu" else None)},
              "workload": workload, "metric": {"name": a.metric, "higher_is_better": m[1]}, "keep": keep,
              "correctness": corr, "smoke": {"prompt_chars": a.smoke_prompt_chars, "n_predict": a.smoke_n_predict,
                                             "budget_s": a.smoke_budget_s, **({"arm": a.smoke_arm} if a.smoke_arm else {})},
              "inputs": inputs, "dirs": list(a.dir)}
    if a.verdict_map:
        spec_g["verdict_map"] = json.loads(a.verdict_map)
    G.validate_spec(dict(spec_g, server=dict(spec_g["server"], argv=argv),
                         correctness=dict(corr, argv=["x"]) if corr else None))
    body = pprint.pformat(spec_g, width=118, indent=1, sort_dicts=False)
    body = body.replace("'@@SERVER_ARGV@@'", "SERVER_ARGV").replace("'@@CORRECTNESS_ARGV@@'", "CORRECTNESS_ARGV")
    with open(os.path.join(d, "job.py"), "w") as f:
        f.write(GATE_JOB.format(id=a.id, task=a.task, rule=a.rule, lv=lv, knobs=", ".join(knobs), knob_names=list(knobs),
                                gen_version=GEN_VERSION, harness_sha=harness_sha(), gate_sha=gate_sha(),
                                argv_source=src, server_argv=_argv_lit(argv), extra_argvs=extra_argvs, spec=body))
    port_list = H.alloc_ports(a.id, 1)
    claim = a.claim or ("any-of q0,q1,q2" if a.lane == "cpu" else "184-191")
    pin = a.claim is not None or a.lane != "cpu"
    with open(os.path.join(d, "launch.sh"), "w") as f:
        f.write(LAUNCH.format(id=a.id, task=a.task, d=d, claim_line=("C=${WS58_CPUS:-%s}\n" % claim) if pin else "",
                              claim_arg=' --claim-cpus "$C"' if pin else "", filler=FILLER, lane=a.lane,
                              min_window=a.min_window, port_arg=f" --port {port_list[0]}"))
    os.chmod(os.path.join(d, "launch.sh"), 0o755)
    with open(os.path.join(d, "check_complete.py"), "w") as f:
        f.write(GATE_CHECK.format(result=os.path.join(d, "out", "RESULT.json")))
    for lib in ("ak_row_harness.py", "ak_gate.py"):
        shutil.copy(os.path.join(HERE, lib), os.path.join(d, lib))
    seal(d, extra=sorted(inputs))
    visits = starts * len(arms) + len(G.plan_correctness(dict(spec_g, server=dict(spec_g["server"], argv=argv))))
    spec = {"owner": "autokernel", "schema": "epyc.row.v3", "kind": "compute", "lane": a.lane, "id": a.id,
            "regions": claim, "claim_cpus": claim, "verdict_by": "agent", "launcher": os.path.join(d, "launch.sh"),
            "result_path": os.path.join(d, "out", "RESULT.json"), "result_format": "json", "scratch_root": d,
            "workdir": d, "stop_file": os.path.join(d, "STOP"), "estimate_s": a.estimate_s, "min_window_s": a.min_window,
            "declared_threads": a.threads, "handoff_task": a.task, "model": a.model, "ports": port_list,
            "smoke_predicate": SMOKE_PRED.format(p=os.path.join(d, "out", H.TERMINAL_SMOKE)),
            "decision_rule": a.rule + " | knobs: " + ", ".join(knobs) + f" | metric {a.metric} "
                             f"({'higher' if m[1] else 'lower'} is better), KEEP iff CI lower > {keep['threshold']} over "
                             f"{kc['n_blocks']} ABBA blocks; A/A guard {kc['aa_max']}",
            "requires_quiet_host": bool(a.lane == "cpu" and not a.no_quiet_host), "resumable": True,
            "estimate_basis": {"provisional": True, "rebook_from": os.path.join(d, "out-smoke", H.SMOKE_MEASURE),
                               "reason": f"pre-smoke: {visits} fresh-server visits/units; re-book from the smoke"},
            "fresh_server_per_visit": True, "fresh_server_reason": GATE_FRESH_REASON,
            "witness_lines": [{"line": v["marker"][3:] if v["marker"].startswith("re:") else v["marker"], "needs": 1,
                               "cap": v["cap"], "knob": k} for k, v in knobs.items() if not v["marker"].startswith("re:")],
            "keep": list(G.EVIDENCE_PATHS),   # the replay input of a failed gate; the reaper honours spec.keep
            "notes": "scaffolded by mk_ak_row.py gate new (declared gate row; ak_gate owns the harness)"}
    spec["generator"] = {"tool": "mk_ak_row.py", "version": GEN_VERSION, "profile": "gate",
                         "harness_sha256": harness_sha(), "gate_sha256": gate_sha(), "utc": H.now()}
    if served:
        spec["served_ref"] = served
    if tool_delta:
        spec["tool_argv_delta"] = tool_delta
    if a.exclusive_cpu:
        spec["exclusive_cpu"] = True
    return d, spec


def gate_sha():
    return _sha(os.path.join(HERE, "ak_gate.py"))


def gate_main(argv=None):
    ap = argparse.ArgumentParser(prog="mk_ak_row.py gate new",
                                 description="declare an AK knob gate row; ak_gate.py owns the harness")
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("--id", required=True)
    n.add_argument("--task", required=True, help="handoff file.md:BOX")
    n.add_argument("--rule", default="", help="the pre-registered rule in words (the mechanics come from --keep-rule)")
    n.add_argument("--model", help="default: the -m GGUF of the served / declared argv")
    n.add_argument("--lane", choices=("cpu", "gpu"), default="gpu")
    n.add_argument("--knob", action="append", default=[], metavar="NAME:MARKER[:LEVEL[:CAP]]",
                   help="env var (GGML_/LLAMA_...) or --flag knob with its witness marker ('re:' prefix = regex)")
    n.add_argument("--observe", action="append", default=[], metavar="NAME:MARKER[:LEVEL]",
                   help="a marker no arm sets but every arm must show (e.g. the served V5I stage line)")
    n.add_argument("--arm", action="append", default=[], metavar="NAME:KNOB=VAL,...")
    n.add_argument("--expect", action="append", default=[], metavar="ARM:KNOB=present|absent,...",
                   help="override derived expect cells (default: set -> present, unset -> absent)")
    n.add_argument("--baseline", default="", help="baseline arms, comma list (default: the arms that set no knob)")
    n.add_argument("--metric", required=True, choices=sorted(G.METRICS))
    n.add_argument("--keep-rule", required=True, metavar="ci_lower>X,n=N[,look=L][,aa=A][,dummy=1]")
    n.add_argument("--served-ref", metavar="ROLE")
    n.add_argument("--orch-repo", default=ORCH_REPO)
    n.add_argument("--server-argv-json", help="the server argv as JSON when the row is not a registry role")
    n.add_argument("--server-env", action="append", default=[], metavar="K=V")
    n.add_argument("--correctness", help="JSON (or @file): {kind: tbo|kld|identity, argv, arms, ...}")
    n.add_argument("--verdict-map", help='JSON {"PASS": {"KEEP": "PASS_X"}, "FAIL": {"FAIL_CORRECTNESS": "FAIL_Y"}}: '
                   "the row's own verdict names; polar = the side")
    n.add_argument("--prompt", action="append", default=[])
    n.add_argument("--workload-input", help="inputs/X (a --copy-input destination) cut into windows")
    n.add_argument("--offsets", default="0")
    n.add_argument("--win-chars", type=int, default=6000)
    n.add_argument("--prompt-suffix", default="")
    n.add_argument("--copy-input", action="append", default=[], metavar="SRC[:inputs/NAME]",
                   help="copy an input into the row dir and pin its sha256")
    n.add_argument("--dir", action="append", default=[], help="extra dir the harness creates (relative to the row)")
    n.add_argument("--n-predict", type=int, default=256)
    n.add_argument("--warmup", type=int, default=1)
    n.add_argument("--ready-timeout-s", type=int, default=900)
    n.add_argument("--membind", type=int)
    n.add_argument("--kfd-min-vram-gib", type=float)
    n.add_argument("--smoke-arm")
    n.add_argument("--smoke-prompt-chars", type=int, default=2000)
    n.add_argument("--smoke-n-predict", type=int, default=32)
    n.add_argument("--smoke-budget-s", type=int, default=300)
    n.add_argument("--claim")
    n.add_argument("--threads", type=int, default=8)
    n.add_argument("--estimate-s", type=int, default=7200)
    n.add_argument("--min-window", type=int, default=1800)
    n.add_argument("--root", default=ROOT)
    n.add_argument("--exclusive-cpu", action="store_true")
    n.add_argument("--no-quiet-host", action="store_true")
    a = ap.parse_args(argv)
    if a.claim is not None and not CLAIM_RX.match(a.claim):
        ap.error(f"--claim {a.claim!r} must be a digit/range list")
    served = resolve_served(a.served_ref, a.orch_repo) if a.served_ref else None
    d, spec = gate_scaffold(a, served)
    fails = lint(d)
    if fails:
        print(f"mk_ak_row gate: {d} fails ak_row_lint; spec.json NOT written", file=sys.stderr)
        return 1
    with open(os.path.join(d, "spec.json"), "w") as f:
        json.dump(spec, f, indent=1)
    print(f"mk_ak_row gate: scaffolded {d} (declaration only; lint + --selftest clean; spec.json written last)")
    print(f"mk_ak_row gate: publish with the DEPLOYED tool: /usr/bin/python3 {PUBLISH} {os.path.join(d, 'spec.json')}")
    return 0


# ======================================================================================================================
# POLAR PROFILE (akloop / gate_eval rows). Moved here verbatim from the retired row-owner-loop row_scaffold.py
# (RCA ak-row-robustness-rca-20261124 F1: ONE generator). row_scaffold.py is now a shim over these names.
# CLI: mk_ak_row.py polar new|--lint|--seal ...  (same arguments as the old row_scaffold.py)
# ======================================================================================================================
import math  # noqa: E402

GPU_HOST = set(range(88, 96)) | set(range(184, 192))
PATH_RE = re.compile(r"/mnt/raid0/llm/tmp/[A-Za-z0-9._/-]+")
ALLOWED_OUTSIDE = ("/mnt/raid0/llm/tmp/compute-flags/",)


def cpus(spec):
    out: set[int] = set()
    for part in (spec or "").split(","):
        part = part.strip()
        m = re.fullmatch(r"(\d+)-(\d+)", part)
        q = re.fullmatch(r"q([0-3])", part)
        if q:
            out |= set(range(24 * int(q[1]), 24 * int(q[1]) + 24))
        elif m:
            out |= set(range(int(m[1]), int(m[2]) + 1))
        elif part.isdigit():
            out.add(int(part))
    return out


def foreign_paths(text: str, rowdir: str) -> list[str]:
    rowdir = rowdir.rstrip("/") + "/"
    bad = []
    for p in PATH_RE.findall(text or ""):
        if p.rstrip("/") + "/" == rowdir or p.startswith(rowdir) or p.startswith(ALLOWED_OUTSIDE):
            continue
        bad.append(p)
    return sorted(set(bad))


def find_box(text: str, box_id: str) -> str | None:
    lines = text.splitlines()
    cands = [i for i, ln in enumerate(lines) if re.match(r"\s*[-*] \[[ xX]\]", ln) and box_id in ln]
    bold = [i for i in cands if re.search(r"\*\*" + re.escape(box_id) + r"\b", lines[i])]
    for i in (bold or cands)[:1]:
        ln = lines[i]
        if True:
            j = i + 1
            while j < len(lines) and lines[j].startswith(("  ", "\t")) and not re.match(r"\s*[-*] \[", lines[j]):
                j += 1
            return "\n".join(lines[i:j])
    return None


def lint_box(box: str | None, box_id: str) -> list[str]:
    if box is None:
        return [f"BOX-MISSING: no checkbox for {box_id}"]
    errs = []
    if not re.search(r"\*\*[A-Z0-9][A-Za-z0-9._-]*(\*\*|\s)", box.splitlines()[0]):
        errs.append("BOX-ID: first line has no bold **ID**")
    if "model:" not in box:
        errs.append("BOX-MODEL: no `model:`")
    if not re.search(r"(?i)\bstop[- ](rule|on)|stop-on|\bSTOP\b", box):
        errs.append("BOX-STOP: no stop rule")
    if not re.search(r"\best\.?\s*~?\s*\d+\s*s\b", box):
        errs.append("BOX-EST: no `est N s`")
    return errs


def lint_seal(rowdir: str) -> list[str]:
    p = os.path.join(rowdir, "SOURCE.sha256")
    if not os.path.exists(p):
        return ["SEAL: SOURCE.sha256 missing"]
    errs = []
    for ln in open(p):
        parts = ln.split()
        if len(parts) != 2:
            continue
        h, name = parts
        f = os.path.join(rowdir, name.lstrip("*"))
        if not os.path.exists(f):
            errs.append(f"SEAL: {name} listed but missing")
        elif hashlib.sha256(open(f, "rb").read()).hexdigest() != h:
            errs.append(f"SEAL: {name} changed since sealed (reseal after review)")
    return errs


def literal_threads(launch: str, spec: dict) -> int | None:
    vals = [int(x) for x in re.findall(r"(?:-t|--threads|--gpu-threads-n)\s+(\d+)\b", launch)]
    if spec.get("declared_threads"):
        vals.append(int(spec["declared_threads"]))
    return max(vals) if vals else None


def polar_lint(rowdir, box_file=None, repo="/workspace"):
    rowdir = os.path.abspath(rowdir)
    errs: list[str] = []
    sp = os.path.join(rowdir, "spec.json")
    if not os.path.exists(sp):
        return ["SPEC: spec.json missing"]
    spec = json.load(open(sp))
    launch = open(os.path.join(rowdir, "launch.sh")).read() if os.path.exists(os.path.join(rowdir, "launch.sh")) else ""
    # ID
    m = re.search(r"--id\s+([A-Za-z0-9._-]+)", launch)
    if m and m[1] != spec.get("id"):
        errs.append(f"ID: launch.sh --id {m[1]} != spec id {spec.get('id')}")
    # EST arithmetic
    just = " ".join(str(spec.get(k, "")) for k in ("estimate_justification", "notes"))
    if not spec.get("estimate_s") or not re.search(r"\d[\w .~]{0,20}?\s(x|×|\*)\s*~?\d|\d\s*(x|×|\*)\s*~?\d", just):
        errs.append("EST-ARITH: estimate_s without `units x rate` arithmetic in estimate_justification/notes")
    # predicate / completion provenance
    texts = {"smoke_predicate": spec.get("smoke_predicate", "")}
    cc = os.path.join(rowdir, "check_complete.py")
    if os.path.exists(cc):
        texts["check_complete.py"] = open(cc).read()
    cm = re.search(r"--complete-cmd\s+\"([^\"]+)\"", launch)
    if cm:
        texts["--complete-cmd"] = cm[1].replace("$D", rowdir)
    for name, t in texts.items():
        for p in foreign_paths(t, rowdir):
            errs.append(f"PRED-PATH: {name} references {p} outside the row dir")
    # CPU lane must not touch MI210 host threads
    lane = spec.get("lane", "")
    claimed = cpus(spec.get("claim_cpus") or "") | cpus(re.sub(r"mi210_\d+,?", "", spec.get("regions", "")))
    if lane == "cpu" and claimed & GPU_HOST:
        errs.append(f"CPU-GPUTHR: cpu lane claims {sorted(claimed & GPU_HOST)[:4]}… (88-95/184-191 are MI210 host threads)")
    # width
    thr = literal_threads(launch, spec)
    phys = {c for c in claimed if c < 96}
    if thr and lane == "cpu" and phys:
        quarters = {c // 24 for c in phys}
        need = math.ceil(thr / 24)
        if len(quarters) > need and not spec.get("width_justification"):
            errs.append(f"WIDTH: {len(quarters)} quarters claimed for {thr} literal threads (need {need})")
    errs += lint_seal(rowdir)
    # box
    ht = spec.get("handoff_task", "")
    if ":" in ht:
        fname, box_id = ht.split(":", 1)
        path = box_file or os.path.join(repo, "handoffs/active", fname)
        if os.path.exists(path):
            errs += lint_box(find_box(open(path).read(), box_id), box_id)
        else:
            errs.append(f"BOX-MISSING: {path} not found")
    else:
        errs.append("BOX-MISSING: spec.handoff_task is not file.md:ID")
    return errs


LAUNCH_T = """#!/bin/bash
# {id} ({owner}, {handoff}:{box}). Threads literal: {threads}.
set -euo pipefail
D={dir}
C={regions}
cd "$D"
ulimit -c 0
/usr/bin/sha256sum --check --status SOURCE.sha256
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id {id} \\
  --class {lane} --claim-cpus "$C" --role bench --min-window {minw} \\
  --cmd "/usr/bin/python3 -I -B $D/job.py" \\
  --complete-cmd "/usr/bin/python3 -I -B $D/check_complete.py" \\
  --stop "$D/STOP" --workdir "$D"
"""
JOB_T = '''#!/usr/bin/python3
"""{id}
QUESTION  {model}
          TODO: the one question this row answers.
SOURCE    TODO: binary/tree + content proof (sha / symbol).
STEPS     TODO: units ({units} x ~{unit_s} s).
RULE      TODO: pre-registered, first match wins. RESULT.json carries ONE polar token per row:
          "polar": "PASS" | "FAIL" (beside the named answer in "verdict"); a futility outcome is split:
          FUTILITY_HARNESS_<WHY> (instrument/harness/input, candidate not judged -> inconclusive) vs
          FUTILITY_CANDIDATE_<WHY> (a measured negative about the candidate -> fail). gate_eval reads these.
          No finished RESULT -> no claim: the row files SUPERSEDED/WITHDRAWN, never inconclusive.
STOP      on-answer: TODO. on-futility: TODO. rc 75 only on STOP file / FILLER_DEADLINE.
"""
{gpu_block}raise SystemExit("TODO: implement job (write out/results.jsonl and out/RESULT.json with complete, verdict, polar)")
'''
RESEARCH_REPO = "/mnt/raid0/llm/epyc-inference-research"  # shared clone: fetch + `git show` only, never its tree/branch/index
HARNESS_PATH = "scripts/kernel_rnd/autokernel/harness"
HARNESS_FILES = ("gpu_common.py", "gpuproof_row.py")
GPU_JOB_T = '''
# GPU lane: the canonical row helpers were copied INTO this row dir by mk_ak_row.py (polar profile) from research {gpu_ref} @ {gpu_commit}
# ({harness_path}); never hand-edit them. The sha256 pins below are checked at start, so an edited copy is a
# FUTILITY_HARNESS_MISSING_INPUT, not a silent change. Both files are also listed in SOURCE.sha256.
import hashlib, os, sys
ROW_DIR = os.path.dirname(os.path.abspath(__file__))
GPU_COMMON_SHA256 = "{gpu_common_sha}"
GPUPROOF_ROW_SHA256 = "{gpuproof_row_sha}"
for _n, _s in (("gpu_common.py", GPU_COMMON_SHA256), ("gpuproof_row.py", GPUPROOF_ROW_SHA256)):
    if hashlib.sha256(open(os.path.join(ROW_DIR, _n), "rb").read()).hexdigest() != _s:
        raise SystemExit(f"FUTILITY_HARNESS_MISSING_INPUT: {{_n}} sha256 differs from the scaffold pin")
sys.path.insert(0, ROW_DIR)
import gpu_common as G  # noqa: E402  (residency_from_proof gates < 2 s children on the in-process witness + LD_DEBUG proof)
'''


def fetch_harness(repo: str, ref: str = "origin/main") -> tuple[str, dict[str, bytes]] | str:
    """(commit, {name: bytes}) for HARNESS_FILES at `ref` of `repo`, via `git fetch` + `git show` only (never touches the
    working tree, branch or index). Returns an error string on failure."""
    import subprocess
    remote, _, branch = ref.partition("/")
    f = subprocess.run(["git", "-C", repo, "fetch", "-q", remote, branch], capture_output=True, text=True)
    if f.returncode != 0:
        return f"git fetch {remote} {branch} failed: {f.stderr.strip()[:200]}"
    c = subprocess.run(["git", "-C", repo, "rev-parse", "--verify", ref + "^{commit}"], capture_output=True, text=True)
    if c.returncode != 0:
        return f"{ref} not resolvable in {repo}"
    out = {}
    for n in HARNESS_FILES:
        r = subprocess.run(["git", "-C", repo, "show", f"{ref}:{HARNESS_PATH}/{n}"], capture_output=True)
        if r.returncode != 0:
            return f"{ref}:{HARNESS_PATH}/{n} missing"
        out[n] = r.stdout
    return c.stdout.strip(), out


CHECK_T = '''#!/usr/bin/python3
"""rc 0 iff THIS row's out/RESULT.json is complete:true AND carries a polar field, whatever the verdict text
(CEILING_OPEN, ANSWERED, ... decide the row too: AK bug 2026-11-24); a split futility verdict
FUTILITY_HARNESS_* / FUTILITY_CANDIDATE_* also counts as polar. Smoke never counts."""
import json, sys
try:
    r = json.load(open("{dir}/out/RESULT.json"))
except (OSError, ValueError):
    sys.exit(1)
v = str(r.get("verdict") or "")
polar = "polar" in r or v.startswith(("FUTILITY_HARNESS", "FUTILITY_CANDIDATE"))
sys.exit(0 if r.get("complete") is True and polar and r.get("smoke") is not True else 1)
'''


def polar_seal(rowdir, names):
    with open(os.path.join(rowdir, "SOURCE.sha256"), "w") as f:
        for n in names:
            f.write(f"{hashlib.sha256(open(os.path.join(rowdir, n), 'rb').read()).hexdigest()}  {n}\n")


ESTIMATE_HISTORY_DIR = HERE


def history_suggestion(row_id: str, units: int | None = None, flags: str | None = None):
    """estimate_history.suggest() for this row's family, or None (no / too little history)."""
    sys.path.insert(0, os.path.normpath(ESTIMATE_HISTORY_DIR))
    try:
        import estimate_history
    finally:
        sys.path.pop(0)
    kw = {"flags": flags} if flags else {}
    return estimate_history.suggest(row_id, units=units, **kw)


def resolve_estimate(a) -> tuple:
    """(estimate_s, justification). A measured `--units x --unit-s` always wins; without it the
    default is estimate-from-history (family p75 x 1.25, or units x per-unit p75 x 1.25)."""
    if a.units and a.unit_s:
        est = math.ceil(a.units * a.unit_s * 1.25)
        return est, f"{a.units} units x {a.unit_s} s measured x 1.25 margin = {est} s"
    sug = history_suggestion(a.row_id, a.units, getattr(a, "flags", None))
    if not sug:
        return None, ("no measured estimate (--units N --unit-s S) and no estimate-from-history "
                      "for this row family (needs >= 3 completed runs)")
    return sug["estimate_s"], sug["estimate_justification"]


def polar_scaffold(a, fetch=None) -> int:
    """The polar/akloop row profile (formerly .claude/skills/row-owner-loop/scripts/row_scaffold.py `new`, retired
    2026-11-24 RCA F1: one generator). `fetch` resolves the canonical GPU harness (default fetch_harness)."""
    fetch = fetch or fetch_harness
    d = os.path.join(a.root, a.row_id)
    if os.path.exists(d):
        print(f"REFUSED: {d} exists")
        return 1
    if a.lane == "cpu" and cpus(a.regions) & GPU_HOST:
        print("REFUSED: cpu lane regions touch 88-95/184-191")
        return 1
    harness, got = {}, None
    if a.lane == "gpu":  # resolve the canonical harness BEFORE creating anything, so a refusal leaves no dir behind
        got = fetch(a.research_repo, a.research_ref)
        if isinstance(got, str):
            print(f"REFUSED: canonical gpu_common.py: {got}")
            return 1
    est, just = resolve_estimate(a)
    if est is None:
        print(f"REFUSED: {just}")
        return 1
    os.makedirs(os.path.join(d, "out"))
    fmt = dict(id=a.row_id, owner=a.owner, handoff=a.handoff, box=a.box, threads=a.threads, dir=d,
               regions=a.regions, lane=a.lane, minw=math.ceil(est * 0.8), model=a.model, units=a.units or '?', unit_s=a.unit_s or '?', gpu_block="")
    if a.lane == "gpu":
        commit, harness = got
        for n, b in harness.items():
            with open(os.path.join(d, n), "wb") as f:
                f.write(b)
        sh = {n: hashlib.sha256(b).hexdigest() for n, b in harness.items()}
        fmt["gpu_block"] = GPU_JOB_T.format(gpu_ref=a.research_ref, gpu_commit=commit, harness_path=HARNESS_PATH,
                                            gpu_common_sha=sh["gpu_common.py"], gpuproof_row_sha=sh["gpuproof_row.py"])
    for name, t, mode in (("launch.sh", LAUNCH_T, 0o755), ("job.py", JOB_T, 0o755), ("check_complete.py", CHECK_T, 0o755)):
        with open(os.path.join(d, name), "w") as f:
            f.write(t.format(**fmt))
        os.chmod(os.path.join(d, name), mode)
    spec = {"owner": a.owner, "schema": "epyc.row.v3", "kind": "compute", "lane": a.lane, "id": a.row_id,
            "regions": a.regions, "claim_cpus": a.regions, "verdict_by": "agent",
            "launcher": f"{d}/launch.sh", "result_path": f"{d}/out/RESULT.json", "result_format": "json",
            "scratch_root": d, "workdir": d, "stop_file": f"{d}/STOP", "estimate_s": est,
            "min_window_s": math.ceil(est * 0.8), "declared_threads": a.threads,
            "estimate_justification": just,
            "handoff_task": f"{os.path.basename(a.handoff)}:{a.box}", "model": a.model,
            "smoke_predicate": f"/usr/bin/test -s {d}/out/TERMINAL-smoke.json",
            "decision_rule": "see job.py docstring (RULE)", "notes": f"scaffolded by mk_ak_row.py (polar profile) for {a.owner}",
            "generator": {"tool": "mk_ak_row.py", "profile": "polar", "version": GEN_VERSION, "utc": H.now()}}
    with open(os.path.join(d, "spec.json"), "w") as f:
        json.dump(spec, f, indent=1)
    polar_seal(d, ["job.py", "check_complete.py", "launch.sh", "spec.json"] + sorted(harness))
    print(f"SCAFFOLDED {d} estimate_s={est}; fill job.py TODOs, reseal (row_scaffold.py --seal {d}), then --lint")
    return 0


def polar_main(argv=None, fetch=None) -> int:
    ap = argparse.ArgumentParser(prog="mk_ak_row.py polar", description="polar/akloop row profile")
    ap.add_argument("--lint", metavar="ROWDIR")
    ap.add_argument("--box-file")
    ap.add_argument("--repo", default="/workspace")
    ap.add_argument("--seal", metavar="ROWDIR", help="rewrite SOURCE.sha256 over the files it already lists")
    sub = ap.add_subparsers(dest="cmd")
    n = sub.add_parser("new")
    n.add_argument("row_id")
    n.add_argument("--handoff", required=True)
    n.add_argument("--box", required=True)
    n.add_argument("--lane", choices=["cpu", "gpu"], required=True)
    n.add_argument("--regions", required=True)
    n.add_argument("--threads", type=int, required=True)
    n.add_argument("--units", type=int, help="units of work; with --unit-s a measured estimate")
    n.add_argument("--unit-s", type=float, help="measured seconds per unit; omit to default to estimate-from-history")
    n.add_argument("--flags", help="compute-flags root for estimate-from-history (default: the live one)")
    n.add_argument("--model", required=True)
    n.add_argument("--owner", default="autokernel")
    n.add_argument("--root", default="/mnt/raid0/llm/tmp")
    n.add_argument("--research-repo", default=RESEARCH_REPO, help="gpu lane: repo to fetch the canonical harness from (fetch + show only)")
    n.add_argument("--research-ref", default="origin/main", help="gpu lane: remote ref holding the canonical harness")
    a = ap.parse_args(argv)
    if a.cmd == "new":
        return polar_scaffold(a, fetch)
    if a.seal:
        names = [ln.split()[1].lstrip("*") for ln in open(os.path.join(a.seal, "SOURCE.sha256")) if len(ln.split()) == 2]
        polar_seal(a.seal, names)
        print(f"SEALED {len(names)} files")
        return 0
    if a.lint:
        errs = polar_lint(a.lint, a.box_file, a.repo)
        for e in errs:
            print(f"LINT {e}")
        print("LINT OK" if not errs else f"LINT {len(errs)} problem(s)")
        return 1 if errs else 0
    ap.print_help()
    return 2


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ["polar"]:
        return polar_main(argv[1:])
    if argv[:1] == ["gate"]:
        return gate_main(argv[1:])
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
    ap.add_argument("--kld-unit", action="store_true",
                    help="row has a KLD (llama-perplexity) unit: emit kld_argv() with -lv 4 for knob rows + a smoke witness check")
    ap.add_argument("--exclusive-cpu", action="store_true", help="gate rows: spec exclusive_cpu=true")
    ap.add_argument("--fresh-server-reason", default="",
                    help="only when a server per visit is required (load-time kernel selection, per-process effects)")
    ap.add_argument("--fresh-server-starts", type=int, default=3, help="cap of fresh server starts per arm")
    ap.add_argument("--no-quiet-host", action="store_true", help="CPU row that is not a timing row")
    ap.add_argument("--served-ref", metavar="ROLE", help="derive SERVER_ARGV from the orchestrator registry role")
    ap.add_argument("--arm-delta", action="append", default=[], metavar="ARM:flag=value[:reason]",
                    help="with --served-ref: an arm-scoped served argv delta (repeatable), written to served_ref.argv_delta "
                         "as {arm, flag, value, reason}; flag argv[0] swaps the binary (lever rows)")
    ap.add_argument("--orch-repo", default=ORCH_REPO, help="orchestrator checkout --served-ref resolves in")
    a = ap.parse_args(argv)
    if a.reseal:
        seal(a.reseal)
        return 1 if lint(a.reseal) else 0
    if not (a.id and a.task and a.rule):
        ap.error("--id, --task and --rule are required")
    served = resolve_served(a.served_ref, a.orch_repo) if a.served_ref else None
    if a.arm_delta:
        if not served:
            ap.error("--arm-delta needs --served-ref")
        served["argv_delta"] = list(served.get("argv_delta") or []) + [parse_arm_delta(x) for x in a.arm_delta]
    if served and a.knob:
        served = add_witness_loglevel(served)
    d, spec = scaffold(a, served)
    fails = lint(d)
    if fails:
        print(f"mk_ak_row: {d} fails ak_row_lint; spec.json NOT written", file=sys.stderr)
        return 1
    with open(os.path.join(d, "spec.json"), "w") as f:
        json.dump(spec, f, indent=1)
    print(f"mk_ak_row: scaffolded {d} (lint clean, spec.json written last; fill job.py then --reseal)")
    print(f"mk_ak_row: publish with the DEPLOYED tool: /usr/bin/python3 {PUBLISH} {os.path.join(d, 'spec.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
