#!/usr/bin/env python3
"""ak_row_harness.py - shared, tested harness pieces for AK (autokernel) measurement rows.

Closes four row-authoring defects that ended 2026-11-22/23 AK rows INCONCLUSIVE (the fifth, cloned "differs" proofs, is
closed by scripts/champion/fold_gates/fold_row_guard.py touched_libs/libs_differ - reuse that, do not re-implement):
  (a) a quiet-host guard that retried 3x in ~2 s with no wait (ak-q38fn-cpu-gdnproj-fuse-20261123-r2)
        -> quiet_guard(): read-bandwidth REF + (c+96)%192 SMT-sibling probe, `tries` attempts, `backoff_s` between them,
           polled every 5 s for the stop file / deadline. Mid-run floor = max(floor_frac*ceiling, mid_frac*ceil-pre),
           ceil-pre persisted to out/ceil_pre.json so a resumed run keeps it. Logic copied from the verified r3
           (ak-q38fn-cpu-gdnproj-fuse-20261123-r3 ref_and_lifetime/backoff_wait/ceil_pre) and r5
           (ak-a3b-cpu-shexp-verify-gap-20261123-r5 Probe/readbw_once/ceiling_unit floor rule) rows.
  (b) a calibration row that COUNTED contended launches (ak-cpu-aa-calibration-q-20261122-c)
        -> run_quiet(): a measurement whose in-run sibling probe p50 exceeds probe_max is a contended TRY (retried after
           backoff), never a data point.
  (c) estimate_s guessed, not measured (ak-rsreplay-q4x-singleslot-repro-cpu-20261123 r1)
        -> write_smoke_measure() in the smoke; estimate_from_smoke(); check_spec_estimate() (publish_row.lint calls it).
  (d) a successor row reusing its predecessor's ports (same row, r2 smoke)
        -> alloc_ports(row_id, n): sha256(row_id) into PORT_LO..PORT_HI, excluding every ancestor id's ports
           (-r1..-r(N-1) and the bare id), bind-tested free.

  (e) a smoke that exited rc=3 with no reason (12/21 smoke failures unrecoverable, 2026-11-23 failure audit A5/A6)
        -> end_smoke(verdict, rc, reason): writes TERMINAL-smoke.json {verdict, rc, reason, ok} and logs one line to stderr.

No process management: readbw is a bounded subprocess.run of the sealed bench_readbw binary; nothing is killed.
Rows run `python3 -I`, so copy this file into the row dir (seal it in SOURCE.sha256) or sys.path.insert the installed
compute-flags/bin/rowflow dir. CLI: `ak_row_harness.py ports <row_id> <n>` | `estimate --unit-s S --units N --loads-s L`.
"""
import hashlib
import json
import math
import os
import re
import socket
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

N_CPU = 192                 # EPYC 9655: 96 physical cores, SMT sibling of c is (c + 96) % 192
CEIL_QUARTER_24T = 112.9    # GB/s, measured quarter-24t read ceiling (AK-CPU-QUARTER-READCEIL)
READBW_SHA = "9e379493494b72269bbc9c9f673f6de86a3dc15690ad0628a3960529c1a03cab"
PROBE_P50_MAX = 15.0        # % busy on the SMT siblings of the pinned cpus (idle by construction)
POLL_S = 5
PORT_LO, PORT_HI = 27000, 28999   # reserved for alloc_ports (row launchers used 8xxx/9xxx/18xxx-21xxx/25xxx as of 2026-11-23)
SMOKE_MEASURE = "smoke_measure.json"
RID_RX = re.compile(r"^(?P<base>.+?)-r(?P<n>\d+)$")


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def compress_cpus(cpus):
    cpus, out, i = sorted(set(cpus)), [], 0
    while i < len(cpus):
        j = i
        while j + 1 < len(cpus) and cpus[j + 1] == cpus[j] + 1:
            j += 1
        out.append(str(cpus[i]) if i == j else f"{cpus[i]}-{cpus[j]}")
        i = j + 1
    return ",".join(out)


def sibling_cpus(cpus):
    """The SMT siblings of `cpus`: (c + 96) % 192."""
    return [(c + N_CPU // 2) % N_CPU for c in cpus]


# ------------------------------------------------------------------------------------------------------------ stop/deadline
def should_stop(stop_file=None, deadline=None, clock=time.time):
    """True when the stop file exists or the deadline (epoch s) passed. Defaults: FILLER_STOPFILE / FILLER_DEADLINE."""
    stop_file = stop_file if stop_file is not None else os.environ.get("FILLER_STOPFILE")
    if deadline is None and os.environ.get("FILLER_DEADLINE"):
        deadline = int(os.environ["FILLER_DEADLINE"])
    return bool((stop_file and os.path.exists(stop_file)) or (deadline and clock() > float(deadline)))


def backoff_wait(backoff_s, stop_file=None, deadline=None, sleep=time.sleep, clock=time.time, poll_s=POLL_S):
    """Wait backoff_s, checking stop/deadline every poll_s. True = stop (r3 backoff_wait)."""
    t_end = clock() + backoff_s
    while clock() < t_end:
        if should_stop(stop_file, deadline, clock):
            return True
        sleep(min(poll_s, max(0.0, t_end - clock())))
    return should_stop(stop_file, deadline, clock)


# ------------------------------------------------------------------------------------------------------------ probe + REF
def read_stat(path="/proc/stat"):
    d = {}
    with open(path) as f:
        for ln in f:
            if ln.startswith("cpu") and ln[3:4].isdigit():
                q = ln.split()
                v = [int(x) for x in q[1:9]]
                d[int(q[0][3:])] = (sum(v), v[3] + v[4])
    return d


class Probe:
    """SMT-sibling busy% over `cpus` (pass sibling_cpus(pinned)), sampled every `period` s in a thread (r3/r5 Probe)."""

    def __init__(self, cpus, period=0.25, stat=read_stat):
        self.cpus, self.vals, self.period, self.stat = list(cpus), [], period, stat
        self.ev = threading.Event()
        self.t = threading.Thread(target=self.run, daemon=True)

    def run(self):
        prev = self.stat()
        while not self.ev.wait(self.period):
            cur = self.stat()
            tot = sum(cur[c][0] - prev[c][0] for c in self.cpus if c in cur and c in prev)
            idle = sum(cur[c][1] - prev[c][1] for c in self.cpus if c in cur and c in prev)
            if tot > 0:
                self.vals.append(100.0 * (tot - idle) / tot)
            prev = cur

    def __enter__(self):
        self.t.start()
        return self

    def __exit__(self, *a):
        self.ev.set()
        self.t.join(2)

    def p50(self):
        return statistics.median(self.vals) if self.vals else 0.0


def make_readbw(binary, gib="2", reps="3", sha=READBW_SHA, env=None, timeout=900):
    """The verified REF: taskset -c <cpus> [numactl --membind=<node>] bench_readbw <gib> <reps> 0, OMP = len(cpus).
    Refuses a binary whose sha256 is not `sha` (r3/r5 READBW_SHA)."""
    if sha:
        h = hashlib.sha256(Path(binary).read_bytes()).hexdigest()
        if h != sha:
            raise ValueError(f"bench_readbw {binary} sha256 {h[:12]} != {sha[:12]}")

    def readbw(cpus, node=None):
        mem = ["/usr/bin/numactl", f"--membind={node}"] if node is not None else []
        cmd = ["/usr/bin/taskset", "-c", compress_cpus(cpus)] + mem + [str(binary), str(gib), str(reps), "0"]
        e = dict(env or {"PATH": "/usr/bin:/bin", "HIP_VISIBLE_DEVICES": "-1", "ROCR_VISIBLE_DEVICES": "-1"})
        e["OMP_NUM_THREADS"] = str(len(cpus))
        t0 = time.time()
        p = subprocess.run(cmd, capture_output=True, text=True, env=e, timeout=timeout)
        m = re.search(r"^read-sum\s+([\d.]+)", p.stdout, re.M)
        return {"rc": p.returncode, "read_sum": float(m.group(1)) if m else None, "wall_s": round(time.time() - t0, 2),
                "tail": p.stdout[-300:]}
    return readbw


# ------------------------------------------------------------------------------------------------------------ ceil-pre
def ceil_pre(out_dir):
    try:
        return json.loads((Path(out_dir) / "ceil_pre.json").read_text()).get("read_sum")
    except (OSError, ValueError):
        return None


def set_ceil_pre(out_dir, v, unit=None):
    p = Path(out_dir) / "ceil_pre.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"read_sum": v, "unit": unit, "utc": now()}))


def guard_floor(out_dir, floor_frac=0.70, ceiling_gbps=CEIL_QUARTER_24T, mid_frac=0.70):
    """max(floor_frac x ceiling, mid_frac x ceil-pre); ceil-pre absent -> floor_frac x ceiling."""
    base = round(floor_frac * ceiling_gbps, 2)
    cp = ceil_pre(out_dir) if out_dir else None
    return (max(base, round(mid_frac * cp, 2)) if cp else base), cp


def _log(out_dir, name, rec):
    if out_dir:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        with (Path(out_dir) / name).open("a") as f:
            f.write(json.dumps(rec) + "\n")


class GuardResult(dict):
    """{'status': 'ok'|'contended'|'stop', 'samples': [...], 'floor', 'ceil_pre', 'tries'}; truthy only when ok."""

    def __bool__(self):
        return self.get("status") == "ok"


def quiet_guard(cpus, readbw, out_dir, *, node=None, floor_frac=0.70, ceiling_gbps=CEIL_QUARTER_24T, tries=4,
                backoff_s=90, stop_file=None, deadline=None, probe_max=PROBE_P50_MAX, mid_frac=0.70, unit=None,
                probe_factory=None, sleep=time.sleep, clock=time.time):
    """Quiet-host gate before a measurement. Each try: REF (readbw) with the SMT-sibling probe running. A try passes when
    rc 0, read_sum >= floor (see guard_floor) and probe p50 <= probe_max. The first passing REF of the row is persisted as
    ceil-pre. Failed tries go to out/contended.jsonl; between tries wait backoff_s polled every 5 s for stop/deadline."""
    probe_factory = probe_factory or (lambda c: Probe(sibling_cpus(c)))
    samples = []
    floor = cp = None
    for n in range(1, tries + 1):
        if should_stop(stop_file, deadline, clock):
            return GuardResult(status="stop", samples=samples, floor=floor, ceil_pre=cp, tries=n - 1)
        if n > 1 and backoff_wait(backoff_s, stop_file, deadline, sleep, clock):
            return GuardResult(status="stop", samples=samples, floor=floor, ceil_pre=cp, tries=n - 1)
        floor, cp = guard_floor(out_dir, floor_frac, ceiling_gbps, mid_frac)
        with probe_factory(cpus) as pb:
            ref = readbw(cpus, node)
        s = {"try": n, "ref": ref.get("read_sum"), "rc": ref.get("rc"), "probe_p50": round(pb.p50(), 2), "floor": floor,
             "ceil_pre": cp, "utc": now()}
        why = []
        if ref.get("rc") != 0 or not ref.get("read_sum"):
            why.append("readbw failed")
        elif ref["read_sum"] < floor:
            why.append(f"ref {ref['read_sum']:.1f} < floor {floor:.1f}")
        if s["probe_p50"] > probe_max:
            why.append(f"sibling p50 {s['probe_p50']:.1f} > {probe_max}")
        s["ok"], s["why"] = not why, why
        samples.append(s)
        if not why:
            if not cp:
                set_ceil_pre(out_dir, ref["read_sum"], unit)
                cp = ref["read_sum"]
            return GuardResult(status="ok", samples=samples, floor=floor, ceil_pre=cp, tries=n)
        _log(out_dir, "contended.jsonl", {"unit": unit, "stage": "ref", **s})
    return GuardResult(status="contended", samples=samples, floor=floor, ceil_pre=cp, tries=tries)


def run_quiet(measure, cpus, readbw, out_dir, *, tries=4, backoff_s=90, probe_max=PROBE_P50_MAX, stop_file=None,
              deadline=None, unit=None, probe_factory=None, sleep=time.sleep, clock=time.time, **guard_kw):
    """quiet_guard, then measure() under the sibling probe. A measurement whose probe p50 > probe_max is a contended TRY
    (logged, retried after backoff) and is NEVER returned as data. All tries share one budget. Returns
    {'status': 'ok'|'contended'|'stop', 'result', 'probe_p50', 'guard', 'tries'}."""
    probe_factory = probe_factory or (lambda c: Probe(sibling_cpus(c)))
    used = 0
    last = None
    while used < tries:
        g = quiet_guard(cpus, readbw, out_dir, tries=tries - used, backoff_s=backoff_s, stop_file=stop_file,
                        deadline=deadline, probe_max=probe_max, unit=unit, probe_factory=probe_factory, sleep=sleep,
                        clock=clock, **guard_kw)
        used += g["tries"]
        last = g
        if g["status"] != "ok":
            return {"status": g["status"], "result": None, "probe_p50": None, "guard": g, "tries": used}
        with probe_factory(cpus) as pb:
            res = measure()
        p50 = round(pb.p50(), 2)
        if p50 <= probe_max:
            return {"status": "ok", "result": res, "probe_p50": p50, "guard": g, "tries": used}
        _log(out_dir, "contended.jsonl", {"unit": unit, "stage": "measure", "probe_p50": p50, "max": probe_max, "utc": now()})
        if used >= tries:
            break
        if backoff_wait(backoff_s, stop_file, deadline, sleep, clock):
            return {"status": "stop", "result": None, "probe_p50": p50, "guard": g, "tries": used}
    return {"status": "contended", "result": None, "probe_p50": None, "guard": last, "tries": used}


# ------------------------------------------------------------------------------------------------------------ ports
def _bind_free(port, host="127.0.0.1"):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def ancestor_ids(row_id):
    """Every earlier attempt of row_id: 'x-r3' -> ['x', 'x-r1', 'x-r2']; 'x' -> []."""
    m = RID_RX.match(row_id)
    if not m:
        return []
    base, n = m.group("base"), int(m.group("n"))
    return [base] + [f"{base}-r{k}" for k in range(1, n)]


def _candidates(row_id):
    span = PORT_HI - PORT_LO + 1
    start = int(hashlib.sha256(row_id.encode()).hexdigest(), 16) % span
    return [PORT_LO + (start + i) % span for i in range(span)]


def _raw_ports(row_id, n, exclude=()):
    out = []
    for p in _candidates(row_id):
        if p not in exclude:
            out.append(p)
            if len(out) == n:
                return out
    raise RuntimeError(f"port range {PORT_LO}-{PORT_HI} exhausted for {row_id}")


def alloc_ports(row_id, n, bind_test=_bind_free):
    """n ports for row_id: deterministic (sha256 of the id, -rN included), disjoint from every ancestor attempt's ports
    (so a re-granted resumable predecessor cannot collide), each bind-tested free. Raises if fewer than n are free."""
    if n < 1:
        raise ValueError("n must be >= 1")
    taken = set()
    for a in ancestor_ids(row_id):
        taken |= set(_raw_ports(a, n, exclude=taken))
    out = []
    for p in _candidates(row_id):
        if p in taken:
            continue
        if bind_test(p):
            out.append(p)
            if len(out) == n:
                return out
    raise RuntimeError(f"fewer than {n} free ports in {PORT_LO}-{PORT_HI} for {row_id}")


def expected_ports(row_id, n):
    """alloc_ports without the bind test (what the lint compares a launcher's --port against)."""
    return alloc_ports(row_id, n, bind_test=lambda p: True)


# ------------------------------------------------------------------------------------------------------------ estimate
def estimate_from_smoke(smoke_measured_unit_s, units, loads_s, margin=1.25):
    """estimate_s = ceil((unit_s x units + loads_s) x margin) from a smoke-MEASURED per-unit time."""
    if not smoke_measured_unit_s or smoke_measured_unit_s <= 0:
        raise ValueError("smoke_measured_unit_s must be a positive measured value")
    if units < 1 or loads_s < 0 or margin < 1.0:
        raise ValueError("units >= 1, loads_s >= 0, margin >= 1.0")
    return int(math.ceil((float(smoke_measured_unit_s) * units + float(loads_s)) * margin))


def write_smoke_measure(out_dir, unit_s, units_measured, loads_s, unit_name="unit", extra=None):
    """The smoke calls this with what it MEASURED (wall per unit, how many units, model/server load seconds)."""
    if not unit_s or unit_s <= 0 or units_measured < 1:
        raise ValueError("write_smoke_measure needs a positive measured unit_s over >= 1 unit")
    p = Path(out_dir) / SMOKE_MEASURE
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = {"unit_s": float(unit_s), "units_measured": int(units_measured), "loads_s": float(loads_s), "unit": unit_name,
           "utc": now(), **(extra or {})}
    p.write_text(json.dumps(rec, indent=1))
    return str(p)


TERMINAL_SMOKE = "TERMINAL-smoke.json"


def end_smoke(verdict, rc, reason, out_dir="out", extra=None, stream=None):
    """The ONE way a smoke ends: writes <out_dir>/TERMINAL-smoke.json {verdict, rc, reason, ok, utc} and logs
    `SMOKE <verdict> rc=<rc>: <reason>` to stderr, so a failed smoke always says why. Returns rc (sys.exit(end_smoke(...))).
    A non-PASS verdict or non-zero rc with an empty reason is recorded as reason 'UNSPECIFIED ...' (and still written)."""
    verdict = str(verdict or "FAIL").upper()
    rc = int(rc)
    reason = str(reason or "").strip()
    ok = verdict == "PASS" and rc == 0
    if not reason:
        reason = "ok" if ok else "UNSPECIFIED (end_smoke called without a reason)"
    p = Path(out_dir) / TERMINAL_SMOKE
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = {"verdict": verdict, "rc": rc, "reason": reason, "ok": ok, "utc": now(), **(extra or {})}
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(rec, indent=1))
    os.replace(tmp, p)
    print(f"SMOKE {verdict} rc={rc}: {reason} ({p})", file=stream or sys.stderr, flush=True)
    return rc


PROVISIONAL_TAG = "ESTIMATE-PROVISIONAL"


def check_spec_estimate(spec, base_dir=None):
    """publish-time check. spec.estimate_basis = {"smoke_measure": <path to a smoke_measure.json>, "units": N,
    "margin": 1.25 (opt), "loads_s": (opt, overrides the measured load only when larger)}.
    Returns (derived or None, [warnings]); raises ValueError when estimate_s < derived or the basis is unreadable."""
    b = spec.get("estimate_basis")
    if not b:
        return None, ["estimate_s is not derived from a smoke measurement (no estimate_basis); see "
                      "ak_row_harness.estimate_from_smoke"]
    if not isinstance(b, dict):
        raise ValueError(f"estimate_basis must be a dict ({{smoke_measure, units}} or a provisional basis), "
                         f"got {type(b).__name__}")
    if b.get("provisional"):
        # Pre-smoke basis: allowed only while the smoke has not produced its measurement; after that, re-book.
        reason = str(b.get("reason") or "").strip()
        rebook = b.get("rebook_from")
        if not reason or not isinstance(rebook, str) or not rebook.strip():
            raise ValueError("provisional estimate_basis needs a non-empty 'reason' and 'rebook_from' "
                             "(the smoke_measure.json path the estimate is re-booked from)")
        root = base_dir or spec.get("workdir") or spec.get("scratch_root") or "."
        rp = Path(rebook)
        if not rp.is_absolute():
            rp = Path(root) / rp
        if rp.exists():
            raise ValueError(f"provisional estimate_basis but {rp} exists: re-book estimate_s from it "
                             "(estimate_basis = {smoke_measure, units})")
        return None, [f"{PROVISIONAL_TAG}: estimate_s {spec.get('estimate_s')} is provisional ({reason}); "
                      f"re-book from {rebook} after the smoke"]
    path = b.get("smoke_measure")
    try:
        m = json.loads(Path(path).read_text())
    except (OSError, TypeError, ValueError) as e:
        raise ValueError(f"estimate_basis.smoke_measure {path!r} unreadable: {e}")
    loads = max(float(m.get("loads_s") or 0), float(b.get("loads_s") or 0))
    derived = estimate_from_smoke(m.get("unit_s"), int(b.get("units") or 0), loads, float(b.get("margin") or 1.25))
    est = int(spec.get("estimate_s") or 0)
    if est < derived:
        raise ValueError(f"estimate_s {est} < {derived} derived from the smoke measurement ({m.get('unit_s')} s/unit x "
                         f"{b.get('units')} + {loads} s loads) x {b.get('margin') or 1.25}")
    return derived, []


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ports")
    p.add_argument("row_id")
    p.add_argument("n", type=int)
    e = sub.add_parser("estimate")
    e.add_argument("--unit-s", type=float, required=True)
    e.add_argument("--units", type=int, required=True)
    e.add_argument("--loads-s", type=float, default=0.0)
    e.add_argument("--margin", type=float, default=1.25)
    a = ap.parse_args(argv)
    if a.cmd == "ports":
        print(",".join(str(x) for x in alloc_ports(a.row_id, a.n)))
    else:
        print(estimate_from_smoke(a.unit_s, a.units, a.loads_s, a.margin))
    return 0


if __name__ == "__main__":
    sys.exit(main())
