#!/usr/bin/env python3
"""scenarios.py - hand-built replay fixtures, one per 2026-11-05 incident class. Each scenario is a short trace plus a
check(decisions) -> [violations]. The global INVARIANTS (replay_lib) are also checked on every scenario."""
from __future__ import annotations

import os

from replay_lib import GPU, QUARTERS, TraceWriter, _iso, contract_lite, cpu_set, qcores, tokens_to_cores  # noqa: F401

T0 = 1793836800.0   # 2026-11-05T00:00:00Z
TICK = 120
JOB = "/mnt/raid0/llm/tmp/replay-fixture"


def launcher(rid, cls="cpu", claim="", gpu_quiet="", role="", extra="", job_text=None, nofold=False):
    d = f"{JOB}/{rid}"
    a = [f"--id {rid}", f"--class {cls}", "--min-window 600", "--complete-cmd 'true'", f"--stop {d}/STOP",
         f"--cmd '{d}/job.sh'"]
    if claim:
        a.append(f"--claim-cpus {claim}")
    if gpu_quiet:
        a.append(f"--gpu-quiet {gpu_quiet}")
    if role:
        a.append(f"--role {role}")
    if nofold:
        a.append("--no-fold-siblings")
    text = "#!/bin/bash\nset -euo pipefail\n" + f"exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh {' '.join(a)}\n"
    files = {f"{d}/job.sh": job_text if job_text is not None else f"#!/bin/bash\n{extra}\n"}
    return f"{d}/launch.sh", text, files


def row(rid, lane="cpu", regions="any-cpu-quarter", est=3600, stopped=False, passed=True, rank=100, man=None, **lk):
    lp, text, files = launcher(rid, **lk)
    m = {"schema": "epyc.row.v3", "id": rid, "owner": "replay", "lane": lane, "regions": regions,
         "launcher": {"path": lp}, "engine": {"path": "/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh"},
         "window_s": est + 900, "min_window_s": 600, "estimate_s": est, "gib": 8, "priority_rank": rank, "ports": [],
         "result_path": f"{JOB}/{rid}/out/results.jsonl", "result_format": "jsonl", "decision_rule": "replay fixture",
         "handoff_task": "handoffs/active/replay.md:FIX", "published_at": _iso(T0 - 3600), "stop_file": f"{JOB}/{rid}/STOP",
         "first_progress_s": 300}
    m.update(man or {})
    blob = {"manifest": m, "launcher_text": text, "files": files, "stopped": stopped, "fails": [],
            "pass": {"id": rid, "passed_at": _iso(T0 - 1800), "units": 1, "result_path": m["result_path"]} if passed else None,
            "pass_matches": True}
    return blob


def write(path, ticks, notes=""):
    w = TraceWriter(path, "scenario", notes)
    for i, (rows, world) in enumerate(ticks):
        w.tick(T0 + i * TICK, rows, **world)
    w.close()
    return path


def _granted(decisions, rid):
    return [(d["i"], g) for d in decisions for g in d["grants"] if g["id"] == rid]


# ---------------------------------------------------------------------------------------------- scenarios
def sc_stopped(path):
    """F4: lsa-oracle-reference-build-f6dddb7's manifest carried an UNEXPANDED `$D/STOP` (launcher D=<its own dir>);
    it was granted 1,344 times while stopped. Plus a plain literal-path stopped row."""
    lsa = row("lsa-oracle-reference-build-f6dddb7", stopped=True, extra="make -j 16", man={"stop_file": "$D/STOP"})
    d = f"{JOB}/lsa-oracle-reference-build-f6dddb7"
    lsa["launcher_text"] = lsa["launcher_text"].replace("set -euo pipefail\n", 'set -euo pipefail\nD="$(cd "$(dirname "$0")" && pwd)"\n') \
        .replace(f"--stop {d}/STOP", '--stop "$D/STOP"')
    rows = {"stopped-row": row("stopped-row", stopped=True, extra="python3 x.py --workers 8"),
            "lsa-oracle-reference-build-f6dddb7": lsa}
    return write(path, [(rows, {})] * 4), lambda d: [f"granted stopped row {g['id']} at tick {i}"
                                                       for i, g in _granted(d, "stopped-row") + _granted(d, "lsa-oracle-reference-build-f6dddb7")]


def sc_one_thread(path):
    # gitnexus impact: --workers 1, declared shape host on 0-95 (22 such grants on 11-05)
    r = row("kpf41-impact-w1", regions="0-95", claim="0-95", extra="gitnexus analyze --workers 1",
            man={"shape": "host", "busy_fraction": 0.05})
    def check(d):
        out = []
        for i, g in _granted(d, "kpf41-impact-w1"):
            if set(QUARTERS) <= ({h for h in g["holds"] if h in QUARTERS} | _fullq(g["holds"])):
                out.append(f"1-thread row got the whole host at tick {i}: {g['holds']}")
        if not _granted(d, "kpf41-impact-w1"):
            out.append("1-thread row never granted at all (must be right-sized, not starved)")
        return out
    return write(path, [({"kpf41-impact-w1": r}, {})] * 4), check


def _fullq(holds):
    from replay_lib import full_quarters
    return full_quarters(tokens_to_cores(set(holds)))


def sc_gpu_work_q3(path):
    """GPU non-timing row (kvu16g2-decstep form) running; a CPU correctness row that can only use q3 must be granted."""
    g = row("kvu16g2-decstep", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, est=7200,
            extra="llama-server -t 8", man={"admission_class": "correctness"})
    c = row("q3-build", regions="any-of q3", extra="make -j 24", est=1800)
    # q0-q2 held by foreign jobs so q3 is the only CPU room
    world = {"foreign": {"q0": "foreign-a", "q1": "foreign-b", "q2": "foreign-c"}}
    ticks = [({"kvu16g2-decstep": g}, world)] + [({"kvu16g2-decstep": g, "q3-build": c}, world)] * 3
    def check(d):
        if not _granted(d, "kvu16g2-decstep"):
            return ["GPU work row never granted"]
        return [] if _granted(d, "q3-build") else ["q3 left idle beside a GPU NON-timing grant (q3 must stay grantable)"]
    return write(path, ticks), check


def sc_gpu_timing_q3(path):
    """GPU timing row (hsf5p-profile form) running; a CPU timing row wanting q3 must NOT be placed there."""
    g = row("hsf5p-profile6-q3", lane="gpu", regions="mi210_0,184-191", cls="gpu", gpu_quiet="exclusive", claim="72-95",
            role="bench", est=7200, extra="rocprof -t 8")
    c = row("cpu-bench-q3", regions="any-of q3", role="bench", gpu_quiet="", extra="llama-bench -t 24", est=1800)
    world = {"foreign": {"q0": "foreign-a", "q1": "foreign-b", "q2": "foreign-c"}}
    # two lone ticks: an EXCLUSIVE grant needs GPU_QUIET_SAMPLES consecutive quiet host-view samples
    ticks = [({"hsf5p-profile6-q3": g}, world)] * 2 + [({"hsf5p-profile6-q3": g, "cpu-bench-q3": c}, world)] * 3
    def check(d):
        out = []
        tg = _granted(d, "hsf5p-profile6-q3")
        if not tg:
            return ["GPU timing row never granted"]
        for i, g2 in _granted(d, "cpu-bench-q3"):
            if i < tg[0][0] + 60 and tokens_to_cores(set(g2["holds"])) & set(range(72, 96)):
                out.append(f"CPU timing row placed on q3 at tick {i} beside a GPU timing grant")
        return out
    return write(path, ticks), check


NPD1_JOB = '''import subprocess
THREADS = "48"
CPUS = "0-95"
def launch(port):
    return subprocess.Popen(["taskset", "-c", CPUS, "numactl", "--interleave=all", "llama-server", "-t", THREADS, "--port", str(port)])
'''


def sc_npd1_step5(path):
    """Whole-host CPU serving: cpu+gpu, gpu-quiet exclusive, claim 0-95, -t THREADS (a Python variable = 48)."""
    lp, text, files = launcher("npd1-step5-20261105", cls="cpu+gpu", claim="0-95", gpu_quiet="exclusive", role="bench")
    files[f"{JOB}/npd1-step5-20261105/job.py"] = NPD1_JOB
    text = text.replace("job.sh'", "job.py'")
    r = row("npd1-step5-20261105", lane="gpu", regions="mi210_0,0-95", est=3000, rank=40,
            man={"shape": "quiet-host", "gib": 130, "declared_threads": None, "baseline_ref": None})
    r["launcher_text"], r["files"] = text, files
    r["pass"]["vram_used_max_bytes"] = 6693199872
    def check(d):
        gs = _granted(d, "npd1-step5-20261105")
        if not gs:
            return ["npd1-step5 (48-thread whole-host CPU serving) never granted: refused/starved"]
        i, g = gs[0]
        hq = {h for h in g["holds"] if h in QUARTERS} | _fullq(g["holds"])
        out = []
        if not set(QUARTERS) <= hq:
            out.append(f"npd1-step5 not admitted whole-host: holds {g['holds']}")
        if i > LIV:
            out.append(f"npd1-step5 granted only at tick {i}")
        return out
    return write(path, [({"npd1-step5-20261105": r}, {})] * 4), check


LIV = 3


def sc_coexist_lockset(path):
    """gpu-q3 GPU timing row whose engine locks ONLY its gpu threads (--no-fold-siblings) + an UNMARKED single-worker
    gitnexus row pinned to 72-79: lock sets are disjoint -> must co-run. A second gpu-q3 row whose claim locks GLOBAL.q3
    EX must NOT get a coexist row beside it (that co-run is fake: the coexist engine would block in region-lock)."""
    g = row("inf34-gpu-timing", lane="gpu", regions="mi210_0,184-191", cls="gpu", gpu_quiet="exclusive", role="bench",
            nofold=True, est=7200, extra="bench -t 8")
    x = row("kpf17-impact-sq3", regions="72-79", claim="72-79", extra="taskset -c 72-79 gitnexus analyze --workers 1",
            est=1200)
    world = {"foreign": {"q0": "foreign-a", "q1": "foreign-b", "q2": "foreign-c"}}
    ticks = [({"inf34-gpu-timing": g}, world)] + [({"inf34-gpu-timing": g, "kpf17-impact-sq3": x}, world)] * 3
    def check(d):
        if not _granted(d, "inf34-gpu-timing"):
            return ["gpu-q3 timing row never granted"]
        return [] if _granted(d, "kpf17-impact-sq3") else \
            ["lock-disjoint coexist row (72-79, --workers 1) never co-ran beside the gpu-q3 grant (declaration-gated?)"]
    return write(path, ticks), check


def sc_smoke_whole_host(path):
    """A queued smoke while a whole-host grant runs: SMOKE-WAIT each tick (never FAIL, never an exception), and placed
    within two ticks of the host freeing."""
    h = row("akx-host-48", regions="0-95", claim="0-95", extra="bench -t 96", est=TICK * 3,
            man={"shape": "host", "shape_override": "operator: replay 2026-11-05: fixture"})
    s = row("smoke-me", passed=False, extra="python3 x.py --workers 2")
    s["smoke_queued"] = {"id": "smoke-me", "queued_at": _iso(T0), "cpus": 4}
    ticks = [({"akx-host-48": h, "smoke-me": s}, {})] * 7
    def check(d):
        out, hg = [], _granted(d, "akx-host-48")
        if not hg:
            return ["whole-host row never granted (scenario precondition)"]
        if any("smoke-me" in f for x in d for f in x["fails_new"]):
            out.append("smoke FAILed under a whole-host grant")
        free_at = next((x["i"] for x in d if x["i"] > hg[0][0] and "akx-host-48" not in x["open_after"]), None)
        placed = next((x["i"] for x in d for l in x["lines"] if l.startswith("SMOKE-PLACE smoke-me") or l.startswith("PLAN smoke smoke-me")), None)
        waited = any(l.startswith("SMOKE-WAIT smoke-me") for x in d for l in x["lines"])
        if not waited and (placed is None or placed > hg[0][0]):
            out.append("smoke neither WAITed nor ran beside the whole-host grant (silent hang)")
        if free_at is not None and (placed is None or placed > free_at + 2):
            out.append(f"smoke not placed within 2 ticks of the host freeing at tick {free_at} (hang)")
        return out
    return write(path, ticks), check


def sc_dryrun_deadline(path):
    """codex-ifbench-cj6a-27b-v4-20261104: dry run started 11-04 15:30Z, engine never reached START, pid alive -> must
    be reaped (killed / WAIT / FAIL, RUNNING.json gone, cpus freed) once past its deadline."""
    rid = "codex-ifbench-cj6a-27b-v4-20261104"
    r = row(rid, passed=False, regions="0-3", claim="0-3", extra="python3 ifbench.py --workers 4", man={"first_progress_s": 900})
    r["running"] = {"id": rid, "started": "2026-11-04T15:30:02Z", "regions": "0-3", "at": "2026-11-04T15:30:02Z"}
    r["running_alive"] = True
    r["dry_grant"] = f"regions=0-3 start=2026-11-04T15:29Z end=2026-11-04T16:04Z holds=c0,c1,c2,c3\n"
    def check(d):
        last = d[-1]["running_json"].get(rid)
        if last and last["pid_alive"]:
            return [f"wedged dry run (alive since 11-04 15:30Z) not reaped after {len(d)} ticks"]
        return []
    return write(path, [({rid: r}, {})] * 4), check


def sc_deadpid_release(path):
    """Same row, pid DEAD (stale dryrun grant + RUNNING.json): its cpus c0-c3 must be free again within one tick, so a
    row that needs exactly 0-3 is granted."""
    rid = "codex-ifbench-cj6a-27b-v4-20261104"
    r = row(rid, passed=False, regions="0-3", claim="0-3", extra="python3 ifbench.py --workers 4", man={"first_progress_s": 900})
    r["running"] = {"id": rid, "started": "2026-11-04T15:30:02Z", "regions": "0-3", "at": "2026-11-04T15:30:02Z"}
    r["running_alive"] = False
    r["dry_grant"] = "regions=0-3 start=2026-11-04T15:29Z end=2026-11-04T16:04Z holds=c0,c1,c2,c3\n"
    w = row("needs-c0-3", regions="0-3", claim="0-3", extra="python3 y.py --workers 4", est=1200)
    world = {"foreign": {"q1": "f1", "q2": "f2", "q3": "f3"}}
    def check(d):
        gs = _granted(d, "needs-c0-3")
        return [] if gs and gs[0][0] <= 1 else ["c0-c3 held by a dead dry run past one tick (needs-c0-3 not granted by tick 1)"]
    return write(path, [({rid: r, "needs-c0-3": w}, world)] * 4), check


def sc_idle_named(path):
    """Every quarter free, one grantable row that fits nowhere for a reason (RAM): every free region must carry an
    IDLE-WHY naming the rule, every tick."""
    r = row("big-ram", extra="python3 z.py --workers 8", man={"gib": 2000})
    return write(path, [({"big-ram": r}, {"mem_gib": 500.0})] * 5), lambda d: []


def sc_declared_shape(path):
    """inf34 v15: shape 'gpu' declared over mi210_0,0-95, launcher class gpu, claim 0-95, no evidence -> never books
    q0-q2 (the declared shape must not bypass the evidence check)."""
    r = row("refactor-inf34-a2-gpu-qual-v15", lane="gpu", regions="mi210_0,0-95", cls="gpu", gpu_quiet="exclusive",
            claim="0-95", extra="python3 qual.py", man={"shape": "gpu"})
    def check(d):
        out = []
        for i, g in _granted(d, "refactor-inf34-a2-gpu-qual-v15"):
            hq = {h for h in g["holds"] if h in QUARTERS} | _fullq(g["holds"])
            if hq & {"q0", "q1", "q2"}:
                out.append(f"declared shape=gpu booked {sorted(hq)} without evidence at tick {i}")
        return out
    return write(path, [({"refactor-inf34-a2-gpu-qual-v15": r}, {})] * 3), check


def sc_smoke_packing(path):
    """PACKING (operator "fix it" 2026-11-05): a 4-core smoke and two whole-quarter rows queued; q2 foreign, q3 partly used
    by a GPU row's host threads. The smoke must land on q3's non-GPU cores and both whole-quarter rows get q0 + q1 the
    same tick; with no partly used quarter (variant: q2 + q3 foreign) the smoke waits rather than break a quarter."""
    gpu = row("kvu-gpu-work", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, est=7200, extra="llama-server -t 8")
    r1 = row("whole-q-a", extra="make -j 16", est=3600)
    r2 = row("whole-q-b", extra="make -j 16", est=3600)
    s = row("smoke-4c", passed=False, extra="python3 x.py --workers 2")
    s["smoke_queued"] = {"id": "smoke-4c", "queued_at": _iso(T0), "cpus": 4}
    world = {"foreign": {"q2": "foreign-c"}}
    rows = {"kvu-gpu-work": gpu, "whole-q-a": r1, "whole-q-b": r2, "smoke-4c": s}
    ticks = [({"kvu-gpu-work": gpu}, world)] + [(rows, world)] * 3

    def check(d):
        out = []
        for rid in ("whole-q-a", "whole-q-b"):
            gs = _granted(d, rid)
            if not gs or gs[0][0] > 1:
                out.append(f"whole-quarter row {rid} not granted on tick 1 (starved by the smoke?)")
        pl = [l for x in d for l in x["lines"] if l.startswith("SMOKE-PLACE smoke-4c")]
        if not pl:
            out.append("smoke never placed although q3 had 16 free non-GPU cores")
        else:
            import re as _re
            cs = cpu_set(_re.search(r"cpus=(\S+)", pl[0]).group(1))
            if {c % 96 for c in cs} - set(range(72, 88)):
                out.append(f"smoke placed on {sorted(cs)[:8]}... outside q3's non-GPU cores")
        return out
    return write(path, ticks), check


def sc_smoke_waits_for_whole(path):
    """Variant: q2 + q3 foreign, two whole-quarter rows + a smoke: the smoke never breaks q0/q1 (it waits)."""
    r1 = row("whole-q-a", extra="make -j 16", est=3600)
    r2 = row("whole-q-b", extra="make -j 16", est=3600)
    s = row("smoke-4c", passed=False, extra="python3 x.py --workers 2")
    s["smoke_queued"] = {"id": "smoke-4c", "queued_at": _iso(T0), "cpus": 4}
    world = {"foreign": {"q2": "foreign-c", "q3": "foreign-d"}}

    def check(d):
        return [f"whole-quarter row {rid} not granted on tick 0" for rid in ("whole-q-a", "whole-q-b")
                if not _granted(d, rid) or _granted(d, rid)[0][0] > 0]
    return write(path, [({"whole-q-a": r1, "whole-q-b": r2, "smoke-4c": s}, world)] * 3), check


def sc_subquarter_free_cores(path):
    """20 free cores (q0-q2 foreign, a 2-thread row on 4 of q3's cores) + a 4-thread any-cpu-quarter row: the contract
    says 4 cores, so it is placed on the free q3 cores the same tick - not starved waiting for a whole quarter."""
    a = row("small-a", extra="python3 a.py --workers 2", est=7200)
    b = row("small-b", extra="python3 b.py --workers 4", est=3600)
    world = {"foreign": {"q0": "f0", "q1": "f1", "q2": "f2"}}

    def check(d):
        out = []
        ga, gb = _granted(d, "small-a"), _granted(d, "small-b")
        if not ga:
            out.append("2-thread row never placed on q3's free cores")
        if not gb or gb[0][0] > 1:
            out.append("4-thread row not placed on the 20 free q3 cores on tick 1")
        for i, g in ga + gb:
            if _fullq(g["holds"]) or set(g["holds"]) & set(QUARTERS):
                out.append(f"sub-quarter row {g['id']} held a whole quarter: {g['holds'][:6]}")
        return out
    return write(path, [({"small-a": a}, world)] + [({"small-a": a, "small-b": b}, world)] * 3), check


def sc_gpu_exclusive_no_kfd(path):
    """GPU EXCLUSIVITY (kvu16g2-ab-20261105, 12:52Z: 41.17e9 B foreign VRAM + 83 foreign KFD pids under a gpu-quiet
    EXCLUSIVE grant). While the exclusive grant is open, nothing else that can open /dev/kfd may start: not a cpu-lane HIP
    build row, not an -ngl > 0 row, not the smoke of either. After the grant ends they run."""
    ab = row("kvu16g2-ab", lane="gpu", regions="mi210_0,184-191", cls="gpu", gpu_quiet="exclusive", nofold=True,
             est=TICK * 3, extra="llama-server -ngl 99 -t 8", man={"admission_class": "correctness"})
    hip = row("llg-build-gpu", extra="cmake -B build-hip -DGGML_HIP=ON && cmake --build build-hip -j 16", est=1200)
    ngl = row("cpu-lane-ngl", extra="llama-server -ngl 40 -t 8", est=1200)
    sm = row("hip-smoke", passed=False, extra="hipcc -o t t.cpp && ./t --workers 2")
    sm["smoke_queued"] = {"id": "hip-smoke", "queued_at": _iso(T0), "cpus": 4}
    rows = {"kvu16g2-ab": ab, "llg-build-gpu": hip, "cpu-lane-ngl": ngl, "hip-smoke": sm}
    ticks = [({"kvu16g2-ab": ab}, {})] + [(rows, {})] * 30   # GPU holders serialize: smoke, then each row

    def check(d):
        gs = _granted(d, "kvu16g2-ab")
        if not gs:
            return ["exclusive GPU row never granted (precondition)"]
        out = []
        for x in d:
            if "kvu16g2-ab" not in x["open_before"]:
                continue
            for g in x["grants"]:
                if g["id"] != "kvu16g2-ab":
                    out.append(f"{g['id']} granted at tick {x['i']} beside the gpu-quiet EXCLUSIVE grant (holds {g['holds'][:4]})")
            for l in x["lines"]:
                if l.startswith("SMOKE-PLACE hip-smoke"):
                    out.append(f"HIP smoke placed at tick {x['i']} beside the gpu-quiet EXCLUSIVE grant")
        for rid in ("llg-build-gpu", "cpu-lane-ngl"):
            if not _granted(d, rid):
                out.append(f"{rid} never granted after the exclusive grant ended (starved)")
        return out
    return write(path, ticks), check


def sc_gpu_foreign_vram(path):
    """kvu16g2-ab-20261105: foreign VRAM from ANOTHER container (twyne-root / sangha-root map the MI210; no keeper lock or
    grant names them). An EXCLUSIVE row is not granted while a foreign KFD client holds >= 1 GiB (IDLE-WHY names it), is
    granted after two quiet samples, and a foreign client appearing mid-grant raises GPU-CONTAMINATED."""
    ex = row("kvu16g2-ab", lane="gpu", regions="mi210_0,184-191", cls="gpu", gpu_quiet="exclusive", nofold=True,
             role="bench", est=TICK * 20, extra="llama-server -ngl 99 -t 8")
    foreign = {"kfd": {"3449271": 41170000000}, "vram_bytes": 41170000000}
    ticks = [({"kvu16g2-ab": ex}, foreign)] * 3 + [({"kvu16g2-ab": ex}, {})] * 4 + [({"kvu16g2-ab": ex}, foreign)] * 3

    def check(d):
        out = []
        gs = _granted(d, "kvu16g2-ab")
        if any(i < 3 for i, _ in gs):
            out.append(f"EXCLUSIVE grant at tick {gs[0][0]} while 41 GB foreign VRAM was resident")
        if not gs or gs[0][0] > 5:
            out.append("EXCLUSIVE row not granted within two quiet samples after the foreign VRAM left")
        if not any(l.startswith("IDLE-WHY gpu-quiet") and "3449271" in l for x in d[:3] for l in x["lines"]):
            out.append("no IDLE-WHY gpu-quiet naming the foreign KFD pid while it held the device")
        if not any(l.startswith("GPU-CONTAMINATED kvu16g2-ab") for x in d[7:] for l in x["lines"]):
            out.append("foreign VRAM under an open EXCLUSIVE grant raised no GPU-CONTAMINATED")
        return out
    return write(path, ticks), check


def sc_pass_is_terminal(path):
    """q38p4c-cpu-int8-20261105: the smoke PASSed (12:52:12Z) but its queue record and a dead RUNNING.json remained; the
    keeper reaped + requeued it and 'state grantable; nothing to do' counted as never-started -> FAIL-1 overrode the PASS.
    A PASS for the current launcher is terminal: never re-smoked, never FAILed, the row is granted."""
    rid = "q38p4c-cpu-int8-20261105"
    r = row(rid, extra="python3 bench.py --workers 4", est=1800)
    r["smoke_queued"] = {"id": rid, "queued_at": _iso(T0 - 300), "cpus": 4, "waits": 2}
    r["running"] = {"id": rid, "started": _iso(T0 - 200), "regions": "72-75", "at": _iso(T0 - 200)}
    r["running_alive"] = False
    r["dry_grant"] = f"regions=72-75 start={_iso(T0 - 240)[:16]}Z end={_iso(T0 + 1800)[:16]}Z holds=c72,c73,c74,c75\n"

    def check(d):
        out = []
        if any(rid in f for x in d for f in x["fails_new"]):
            out.append("a FAIL was recorded after the row's PASS")
        if any(l.startswith(f"SMOKE-PLACE {rid}") for x in d for l in x["lines"]):
            out.append("a grantable (PASSed) row was re-smoked")
        if not _granted(d, rid):
            out.append("PASSed row never granted")
        return out
    return write(path, [({rid: r}, {})] * 4), check


SCENARIOS = {
    "stopped-never-granted": sc_stopped,
    "one-thread-not-whole-host": sc_one_thread,
    "gpu-work-leaves-q3-grantable": sc_gpu_work_q3,
    "gpu-timing-keeps-q3-quiet": sc_gpu_timing_q3,
    "npd1-step5-whole-host-admitted": sc_npd1_step5,
    "coexist-by-lockset": sc_coexist_lockset,
    "smoke-under-whole-host-waits": sc_smoke_whole_host,
    "dryrun-deadline-reaped": sc_dryrun_deadline,
    "dead-dryrun-releases-in-one-tick": sc_deadpid_release,
    "idle-regions-named": sc_idle_named,
    "declared-shape-no-bypass": sc_declared_shape,
    "smoke-packs-onto-partly-used-q3": sc_smoke_packing,
    "smoke-never-breaks-needed-whole-quarter": sc_smoke_waits_for_whole,
    "subquarter-row-on-20-free-cores": sc_subquarter_free_cores,
    "gpu-exclusive-admits-no-kfd-holder": sc_gpu_exclusive_no_kfd,
    "gpu-foreign-vram-blocks-exclusive": sc_gpu_foreign_vram,
    "smoke-pass-is-terminal": sc_pass_is_terminal,
}

# which global invariants each scenario is ABOUT (the others are still checked; these are its subject)
SUBJECT = {
    "stopped-never-granted": ["INV-STOP", "INV-REGRANT"],
    "one-thread-not-whole-host": ["INV-1THREAD", "INV-EVIDENCE"],
    "gpu-timing-keeps-q3-quiet": ["INV-GPU-TIMING-Q3"],
    "coexist-by-lockset": ["INV-LOCKSET"],
    "dryrun-deadline-reaped": ["INV-DRYRUN-DEADLINE"],
    "dead-dryrun-releases-in-one-tick": ["INV-DEADPID-RELEASE"],
    "idle-regions-named": ["INV-IDLE-WHY-ALL", "INV-IDLE-NAMED"],
    "declared-shape-no-bypass": ["INV-EVIDENCE"],
}


# ---------------------------------------------------------------------------------------------- PUBLISH-path scenarios
# The allocation replay never runs rowflow.publish; these run the candidate's publish() on a temp tree.
NPD1_STEP5_JOB = '''import subprocess
SMOKE = False
THREADS = "48" if not SMOKE else "4"
CPUS = "0-95"
def launch(port):
    return subprocess.Popen(["taskset", "-c", CPUS, "numactl", "--interleave=all", "llama-server", "-t", THREADS, "--port", str(port)])
'''


def pub_npd1_step5(root):
    """keeper-hotfix D14: npd1-step5's spec (cpu+gpu, gpu-quiet exclusive, claim 0-95, role bench, -t THREADS = 48,
    numactl --interleave=all) is whole-host CPU serving and MUST be accepted at publish (8fbe18182 refused it)."""
    d = os.path.join(root, "npd1-step5-20261105")
    os.makedirs(d, exist_ok=True)
    eng = os.path.join(root, "filler_run15.sh")
    open(eng, "w").write("#!/bin/bash\n")
    open(os.path.join(d, "job.py"), "w").write(NPD1_STEP5_JOB)
    lp = os.path.join(d, "launch.sh")
    open(lp, "w").write(f"#!/bin/bash\nset -euo pipefail\nD={d}\ncd \"$D\"\nexec /bin/bash {eng} --id npd1-step5-20261105 "
                        "--class cpu+gpu --gpu-quiet exclusive --claim-cpus 0-95 --role bench --min-window 3600 "
                        "--cmd \"/usr/bin/python3 -I $D/job.py\" --complete-cmd \"true\" --stop \"$D/STOP\" --workdir \"$D\"\n")
    spec = {"id": "npd1-step5-20261105", "owner": "ws58", "launcher": lp, "lane": "gpu", "regions": "mi210_0,0-95",
            "result_path": os.path.join(d, "out", "results.jsonl"), "decision_rule": "replay publish fixture",
            "estimate_s": 3000, "handoff_task": "handoffs/active/mi210-serving-program.md:NPD1-STEP5", "ram_gib": 130,
            "first_progress_s": 900, "priority_rank": 40}

    def check(row, err):
        if err is not None:
            return [f"npd1-step5 refused at publish: {err}"]
        out = []
        if row.get("shape") not in ("quiet-host", "host"):
            out.append(f"npd1-step5 published as {row.get('shape')}, not whole-host")
        if row.get("declared_threads") != 48:
            out.append(f"npd1-step5 threads {row.get('declared_threads')} != 48 (-t THREADS not resolved)")
        return out
    return spec, check


INF75_JOB = """import os, subprocess
def helper():
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
    return subprocess.run(["python3", "census.py"], env=env)
def serve(port):
    return subprocess.Popen(["llama-server", "-t", "48", "--port", str(port)])
"""


def pub_inf75_helper_omp(root):
    """inf75-c5-w3-halfb-census-c6-r2 (2026-11-05): llama-server -t 48 on 48-95,144-191 (cpu+gpu, gpu-quiet exclusive)
    was refused as 'threads 1: OMP_NUM_THREADS 1' - the OMP knob belonged to a Python helper's env. Thread evidence is
    the compute binary's own argv; a helper's OMP_NUM_THREADS is never evidence."""
    rid = "inf75-c5-w3-halfb-census-c6-r2-20261105"
    d = os.path.join(root, rid)
    os.makedirs(d, exist_ok=True)
    eng = os.path.join(root, "filler_run15.sh")
    open(eng, "w").write("#!/bin/bash\n")
    open(os.path.join(d, "job.py"), "w").write(INF75_JOB)
    lp = os.path.join(d, "launch.sh")
    open(lp, "w").write(f"#!/bin/bash\nset -euo pipefail\nD={d}\nexec /bin/bash {eng} --id {rid} --class cpu+gpu "
                        "--gpu-quiet exclusive --claim-cpus 48-95,144-191 --min-window 3600 --cmd \"/usr/bin/python3 -B $D/job.py\" "
                        "--complete-cmd \"true\" --stop \"$D/STOP\" --workdir \"$D\"\n")
    spec = {"id": rid, "owner": "inf22", "launcher": lp, "lane": "gpu", "regions": "mi210_0,48-95,144-191",
            "result_path": os.path.join(d, "out", "results.jsonl"), "decision_rule": "replay publish fixture",
            "estimate_s": 3000, "handoff_task": "handoffs/active/x.md:INF75", "ram_gib": 64, "first_progress_s": 900}

    def check(row, err):
        if err is not None:
            return [f"refused at publish: {err[:200]}"]
        return [] if row.get("declared_threads") == 48 else [f"threads {row.get('declared_threads')} != 48 (helper OMP taken as evidence)"]
    return spec, check


PUBLISH_SCENARIOS = {"publish-npd1-step5-accepted": pub_npd1_step5,
                     "publish-helper-omp-not-thread-evidence": pub_inf75_helper_omp}


def build_all(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    return {name: fn(os.path.join(out_dir, name + ".trace.jsonl")) for name, fn in SCENARIOS.items()}
