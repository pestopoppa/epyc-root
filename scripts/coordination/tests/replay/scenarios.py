#!/usr/bin/env python3
"""scenarios.py - hand-built replay fixtures, one per 2026-11-05 incident class. Each scenario is a short trace plus a
check(decisions) -> [violations]. The global INVARIANTS (replay_lib) are also checked on every scenario."""
from __future__ import annotations

import os

from replay_lib import GPU, QUARTERS, TraceWriter, _iso, contract_lite, cpu_set, qcores, tokens_to_cores  # noqa: F401

T0 = 1793836800.0   # 2026-11-05T00:00:00Z
TICK = 120
JOB = "/mnt/raid0/llm/tmp/replay-fixture"
POCKETS = set(range(116, 120)) | set(range(140, 144)) | set(range(164, 168))   # rowflow SMOKE_POCKETS (audit 2026-11-10 #5)


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


def sc_gpu_timing_narrow_q3(path):
    """gpu-q3 NARROW (operator 2026-11-05 "Narrow + emergency deploy"): q38p4b-int8-20261105 (GPU timing, regions
    mi210_0,184-191, --role bench) was refused "needs gpu-quiet,q3,t184..t191: q3 busy" while an 8-core AITER build sat on
    80-87/176-183. An 8-core q3 CPU row and a GPU timing row must be granted CONCURRENTLY: the GPU timing grant holds
    gpu-quiet + 88-95 + 184-191 and never q3 cores 72-87. q0-q2 are foreign so q3 is the only CPU room."""
    b = row("rock-aiter-prebuild-r4", regions="80-87", claim="80-87", extra="taskset -c 80-87,176-183 make -j 8", est=7200)
    g = row("q38p4b-int8", lane="gpu", regions="mi210_0,184-191", cls="gpu", gpu_quiet="exclusive", role="bench",
            nofold=True, est=7200, extra="llama-bench -t 8", man={"shape": "gpu-q3"})
    world = {"foreign": {"q0": "foreign-a", "q1": "foreign-b", "q2": "foreign-c"}}
    # the build first (two lone ticks: an EXCLUSIVE grant needs GPU_QUIET_SAMPLES quiet samples anyway), then the timing row
    ticks = [({"rock-aiter-prebuild-r4": b}, world)] * 2 + [({"rock-aiter-prebuild-r4": b, "q38p4b-int8": g}, world)] * 4

    def check(d):
        out = []
        bg, tg = _granted(d, "rock-aiter-prebuild-r4"), _granted(d, "q38p4b-int8")
        if not bg:
            return ["8-core q3 CPU row never granted (scenario precondition)"]
        if not tg:
            return ["GPU timing row never granted beside an 8-core q3 CPU grant (the q38p4b-int8 refusal)"]
        i, g2 = tg[0]
        if "rock-aiter-prebuild-r4" not in d[i]["open_before"] and bg[0][0] != i:
            out.append(f"GPU timing row granted at tick {i} only after the q3 CPU grant closed (not concurrent)")
        held = tokens_to_cores(set(g2["holds"]))
        if held & set(range(72, 88)) or "q3" in g2["holds"]:
            out.append(f"GPU timing grant holds q3 cores 72-87: {sorted(g2['holds'])}")
        if not set(range(88, 96)) <= held or GPU not in g2["holds"]:
            out.append(f"GPU timing grant does not hold gpu-quiet + 88-95: {sorted(g2['holds'])}")
        bh = tokens_to_cores(set(bg[0][1]["holds"]))
        if not bh <= set(range(80, 88)):
            out.append(f"8-core CPU grant holds more than 80-87: {sorted(bg[0][1]['holds'])}")
        return out
    return write(path, ticks), check


def sc_gpu_timing_narrow_q3_reverse(path):
    """Same pair, GPU timing grant first: the 8-core q3 CPU row is granted beside it (72-87 stay grantable)."""
    g = row("q38p4b-int8", lane="gpu", regions="mi210_0,184-191", cls="gpu", gpu_quiet="exclusive", role="bench",
            nofold=True, est=7200, extra="llama-bench -t 8", man={"shape": "gpu-q3"})
    b = row("rock-aiter-prebuild-r4", regions="80-87", claim="80-87", extra="taskset -c 80-87,176-183 make -j 8", est=3600)
    world = {"foreign": {"q0": "foreign-a", "q1": "foreign-b", "q2": "foreign-c"}}
    ticks = [({"q38p4b-int8": g}, world)] * 3 + [({"q38p4b-int8": g, "rock-aiter-prebuild-r4": b}, world)] * 3

    def check(d):
        tg, bg = _granted(d, "q38p4b-int8"), _granted(d, "rock-aiter-prebuild-r4")
        if not tg:
            return ["GPU timing row never granted (scenario precondition)"]
        if not bg:
            return ["8-core q3 CPU row never granted beside an open GPU timing grant (72-87 must stay grantable)"]
        i = bg[0][0]
        if "q38p4b-int8" not in d[i]["open_before"]:
            return [f"CPU row granted at tick {i} only after the GPU timing grant closed (not concurrent)"]
        return []
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
    """(2026-11-10: a smoke pocket now also satisfies this.) PACKING (operator "fix it" 2026-11-05): a 4-core smoke and two whole-quarter rows queued; q2 foreign, q3 partly used
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
            if not (cs <= POCKETS or not {c % 96 for c in cs} - set(range(72, 88))):
                out.append(f"smoke placed on {sorted(cs)[:8]}... outside the smoke pockets and q3's non-GPU cores")
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


def sc_gpu_blocked_whole_rows_free_smokes(path):
    """CLASSFIX (2026-11-05 14:55Z keeper log): rock-aiter-build holds q3 + the MI210 host threads; three queued GPU rows that also need a
    whole CPU quarter cannot run, so they reserve nothing - the queued smokes are placed on the free quarters."""
    g1 = row("gpu-whole-a", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, est=3600,
                             role="bench", extra="llama-server -t 8")
    g2 = row("gpu-whole-b", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, est=3600,
                             role="bench", extra="llama-server -t 8")
    g3 = row("gpu-whole-c", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, est=3600,
                             role="bench", extra="llama-server -t 8")
    s1 = row("smoke-x", passed=False, extra="python3 x.py --workers 2")
    s1["smoke_queued"] = {"id": "smoke-x", "queued_at": _iso(T0), "cpus": 4}
    s2 = row("smoke-y", passed=False, extra="python3 y.py --workers 2")
    s2["smoke_queued"] = {"id": "smoke-y", "queued_at": _iso(T0), "cpus": 4}
    world = {"foreign": {"q3": "rock-aiter-build", "q1": "hil15b-heavy"}}
    rows = {"gpu-whole-a": g1, "gpu-whole-b": g2, "gpu-whole-c": g3, "smoke-x": s1, "smoke-y": s2}
    ticks = [(rows, world)] * 3

    def check(d):
        out = []
        if any(_granted(d, r) for r in ("gpu-whole-a", "gpu-whole-b", "gpu-whole-c")):
            out.append("fixture: a GPU row was granted (GPU not held)")
        for sid in ("smoke-x", "smoke-y"):
            if not any(l.startswith(f"SMOKE-PLACE {sid}") or l.startswith(f"PLAN smoke {sid}") for x in d for l in x["lines"]):
                out.append(f"{sid} starved by whole-quarter rows blocked on the held GPU")
        return out
    return write(path, ticks), check


def sc_cpu_whole_row_reservation_holds(path):
    """CLASSFIX counter-case: a CPU whole-quarter row runnable NOW keeps its reservation; with q2 + q3 foreign and two
    such rows, the smoke must not break q0/q1."""
    r1 = row("cpu-whole-a", extra="make -j 16", est=3600)
    r2 = row("cpu-whole-b", extra="make -j 16", est=3600)
    s = row("smoke-z", passed=False, extra="python3 z.py --workers 2")
    s["smoke_queued"] = {"id": "smoke-z", "queued_at": _iso(T0), "cpus": 4}
    world = {"foreign": {"q2": "foreign-c", "q3": "foreign-d"}}

    def check(d):
        out = [f"whole-quarter row {rid} not granted on tick 0" for rid in ("cpu-whole-a", "cpu-whole-b")
               if not _granted(d, rid) or _granted(d, rid)[0][0] > 0]
        import re as _re
        for l in (l for x in d[:1] for l in x["lines"] if l.startswith("SMOKE-PLACE smoke-z")):
            if not cpu_set(_re.search(r"cpus=(\S+)", l).group(1)) <= POCKETS:
                out.append("smoke broke a whole quarter a runnable CPU row needed")
        return out
    return write(path, [({"cpu-whole-a": r1, "cpu-whole-b": r2, "smoke-z": s}, world)] * 3), check


def _idle_held_rows(util_busy):
    """One GPU row (rock-aiter-tests-r3 form: gpu lane, mi210_0,184-191, class gpu, 2 h estimate) granted at tick 0 and
    then measured at util_busy % on the device every tick; q0-q2 foreign so nothing else moves."""
    g = row("rock-aiter-tests-r3", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, est=7200,
            extra="ctest --test-dir build-hip", man={"admission_class": "correctness"})
    world = {"foreign": {"q0": "foreign-a", "q1": "foreign-b", "q2": "foreign-c"},
             "util": {"q0": 90.0, "q1": 90.0, "q2": 90.0, "q3": 0.0,
                      "gpu": {"busy": util_busy, "vram_pct": 0.0 if not util_busy else 40.0, "vram_gib": 0.0, "card": "card2"}}}
    return {"rock-aiter-tests-r3": g}, world


def _warn_lines(d, rid):
    return [(x["i"], l) for x in d for l in x["lines"] if l.startswith(f"IDLE-HELD-WARN gpu-quiet {rid}:")]


def sc_idle_held_warns_once(path):
    """operator 2026-11-05 (notify-only): rock-aiter-tests-r3-20261105 held gpu-quiet at 0% for ~20 min (21:20-21:41Z,
    stale lock) and nobody was told. 8 ticks x 120 s: the grant is IDLE-HELD from tick 1 (age > 60 s) and gets EXACTLY
    ONE IDLE-HELD-WARN (owner notified) once it has been idle >= 300 s - never before, never twice within 15 min - and
    the grant is never ended."""
    rows, world = _idle_held_rows(0)
    ticks = [(rows, world)] * 8

    def check(d):
        out = []
        if not _granted(d, "rock-aiter-tests-r3"):
            return ["fixture: GPU row never granted"]
        w = _warn_lines(d, "rock-aiter-tests-r3")
        if len(w) != 1:
            out.append(f"expected exactly one IDLE-HELD-WARN over 8 ticks (16 min), got {len(w)}: {w}")
        if w and w[0][0] < 3:
            out.append(f"warned at tick {w[0][0]} (< 300 s idle)")
        if not any(l.startswith("IDLE-HELD gpu-quiet rock-aiter-tests-r3") for x in d for l in x["lines"]):
            out.append("fixture: the grant never read IDLE-HELD")
        if any(x["open_after"].get("rock-aiter-tests-r3") is None for x in d[1:]):
            out.append("the grant was ended by the keeper (notify-only: it must never be)")
        return out
    return write(path, ticks), check


def sc_idle_held_repeats_each_15min(path):
    """Same grant over 14 ticks (28 min): the second warning comes >= 900 s after the first, and no third."""
    rows, world = _idle_held_rows(0)
    ticks = [(rows, world)] * 14

    def check(d):
        w = _warn_lines(d, "rock-aiter-tests-r3")
        if len(w) != 2:
            return [f"expected exactly two IDLE-HELD-WARN over 14 ticks, got {len(w)}: {w}"]
        if (w[1][0] - w[0][0]) * TICK < 900:
            return [f"repeat warning after {(w[1][0] - w[0][0]) * TICK}s (< 900 s)"]
        return []
    return write(path, ticks), check


def sc_idle_held_busy_grant_silent(path):
    """Control: the same grant measured 95% busy on the device never warns (and never reads IDLE-HELD)."""
    rows, world = _idle_held_rows(95)
    ticks = [(rows, world)] * 8

    def check(d):
        if not _granted(d, "rock-aiter-tests-r3"):
            return ["fixture: GPU row never granted"]
        w = _warn_lines(d, "rock-aiter-tests-r3")
        return [f"a busy grant was warned: {w}"] if w else []
    return write(path, ticks), check



# ---------------------------------------------------------------------------------------------- friction pass 4 (2026-11-06)
PRECOND_LINE = ("refuse rc=12: not ready: precond-cmd failed: printf '%s %s\n' c66f05148e35355bd04292958d9a123b0a80f1db "
                "'/mnt/raid0/llm/tmp/heterogeneous-slot-fabric/kpf50/input.json' | sha256sum -c --status")
DEAD_LINE = "refuse rc=14: launcher pid {pid} of {rid} is dead (no /proc/{pid} or zombie)"


def _fails_per_tick(d):
    return [len(x["fails_new"]) for x in d]


def _lines(d, prefix):
    return [(x["i"], l) for x in d for l in x["lines"] if l.startswith(prefix)]


def sc_precond_parks_once(path):
    """P4.4 row 1: kpf50-child-evidence-main-impact-r2 was refused by its own --precond-cmd 171 times (06:34Z-09:26Z, one
    per tick) and alerted 171 times, because its live poller kept it `armed`. Rule: the FIRST refusal parks the row (one
    FAIL, one PARK line); it is never re-admitted until its manifest changes (tick 5: a republish with new notes), which
    buys exactly one more refusal episode."""
    rid = "kpf50-child-evidence-main-impact-20261104-r2"
    r = row(rid, regions="any-cpu-quarter", est=3600)
    r["admit"] = {"refuse": PRECOND_LINE}
    r2 = dict(r, manifest=dict(r["manifest"], notes="precondition input regenerated"))
    world = {"foreign": {}}
    ticks = [({rid: r}, world)] * 5 + [({rid: r2}, world)] * 3

    def check(d):
        out = []
        f = _fails_per_tick(d)
        if f != [1, 0, 0, 0, 0, 1, 0, 0]:
            out.append(f"FAIL records per tick {f}; expected one at tick 0 and one at tick 5 (the spec change), never per tick")
        park = _lines(d, f"PARK {rid}:")
        if [i for i, _ in park] != [0, 5]:
            out.append(f"PARK lines at ticks {[i for i, _ in park]}; expected [0, 5]")
        skip = _lines(d, f"SKIP {rid}:")
        if skip:
            out.append(f"the parked row was re-admitted (SKIP lines at ticks {[i for i, _ in skip]})")
        if _granted(d, rid):
            out.append("a refused row was granted")
        return out
    return write(path, ticks), check


def sc_completed_not_rc14(path):
    """P4.4 row 2: v11-122-llg-build-cpu / c6q4isum-llg-build-gpu & co: `refuse rc=14: launcher pid N is dead` was written
    as a launch FAIL (+ owner alert, + fix_task) 1 s after the poller had finished the WHOLE job (grants/<id>.complete,
    .ended rc=0 reason=complete). Rule: a receipt present at admission time makes a dead pid a COMPLETION: no FAIL, no
    alert, a COMPLETE line, and the row is `done` from the next tick (never a candidate again)."""
    rid = "v11-122-llg-build-cpu-20261105"
    r = row(rid, regions="any-cpu-quarter", est=3600)
    r["admit"] = {"refuse": DEAD_LINE, "complete_marker": True, "pid_dies": True}
    ticks = [({rid: r}, {"foreign": {}})] * 3

    def check(d):
        out = []
        if sum(_fails_per_tick(d)):
            out.append(f"a completed row got a FAIL record (per tick {_fails_per_tick(d)})")
        c = _lines(d, f"COMPLETE {rid}:")
        if [i for i, _ in c] != [0]:
            out.append(f"COMPLETE lines at ticks {[i for i, _ in c]}; expected exactly one, at tick 0")
        if any((x["cands"] or 0) > 0 for x in d[1:]):
            out.append("the completed row stayed a candidate after its receipt")
        if _granted(d, rid):
            out.append("a completed row was granted")
        return out
    return write(path, ticks), check


def sc_dead_poller_without_receipt_still_fails(path):
    """Control for the rule above: the same dead pid with NO receipt is still a launch FAIL (a real dead poller)."""
    rid = "akx-c6-n4-generic-vs-candidate-20261104"
    r = row(rid, regions="any-cpu-quarter", est=3600)
    r["admit"] = {"refuse": DEAD_LINE, "pid_dies": True}
    ticks = [({rid: r}, {"foreign": {}})] * 2

    def check(d):
        out = []
        if _fails_per_tick(d)[0] != 1:
            out.append(f"a genuinely dead poller must still FAIL at tick 0 (got {_fails_per_tick(d)})")
        if _lines(d, f"COMPLETE {rid}:"):
            out.append("COMPLETE logged without any receipt")
        return out
    return write(path, ticks), check


def _gpu_harness_rows(util_busy, regions="mi210_0,184-191", q3=0.0):
    g = row("ak-asm-t1-harness", lane="gpu", regions=regions, cls="gpu", nofold=True, est=7200,
            extra="python3 harness.py --device rocm", man={"admission_class": "correctness"})
    g["kfd_own"] = True
    world = {"foreign": {"q0": "foreign-a", "q1": "foreign-b", "q2": "foreign-c"},
             "util": {"q0": 90.0, "q1": 90.0, "q2": 90.0, "q3": q3,
                      "gpu": {"busy": util_busy, "vram_pct": 3.0, "vram_gib": 2.0, "card": "card2"}}}
    return {"ak-asm-t1-harness": g}, world


def sc_gpu_harness_with_kfd_never_idle(path):
    """P4.4 rows 3-4: ak-asm-t1-harness (a RUNNING GPU harness: own KFD client, 2 GiB VRAM) read IDLE-HELD gpu-quiet and
    warned its owner 30+ times because the device busy % sampled 0 between kernels and its host threads sat idle. Rule:
    a grant whose own process tree holds a KFD client is busy; it never reads IDLE-HELD and never warns - 8 ticks."""
    rows, world = _gpu_harness_rows(0)
    ticks = [(rows, world)] * 8

    def check(d):
        out = []
        if not _granted(d, "ak-asm-t1-harness"):
            return ["fixture: GPU row never granted"]
        held = _lines(d, "IDLE-HELD")
        if held:
            out.append(f"a GPU grant with its own KFD client read IDLE-HELD: {held[:3]}")
        return out
    return write(path, ticks), check


def sc_gpu_grant_cpu_regions_not_judged(path):
    """A GPU grant over mi210_0 + all of q3 (kvu16g3 form): q3 reads 0 % CPU while the device is 80 % busy and no KFD
    client is attributable (a fenced child container). CPU % never judges a GPU-token grant: no IDLE-HELD q3."""
    rows, world = _gpu_harness_rows(80, regions="mi210_0,72-95", q3=0.0)
    rows["ak-asm-t1-harness"]["kfd_own"] = False
    ticks = [(rows, world)] * 6

    def check(d):
        out = []
        if not _granted(d, "ak-asm-t1-harness"):
            return ["fixture: GPU row never granted"]
        held = _lines(d, "IDLE-HELD")
        if held:
            out.append(f"IDLE-HELD read on a GPU grant by CPU %: {held[:3]}")
        return out
    return write(path, ticks), check


def sc_gpu_grant_quiet_device_idle_after_two_samples(path):
    """Counter-case: no own KFD client AND the device at 0 % - IDLE-HELD gpu-quiet only from the 2nd quiet sample (tick 2:
    tick 0 grants, tick 1 is sample 1), then warns the owner once >= 300 s later (the pass-3 notify-only contract)."""
    rows, world = _gpu_harness_rows(0)
    rows["ak-asm-t1-harness"]["kfd_own"] = False
    ticks = [(rows, world)] * 8

    def check(d):
        out = []
        held = [i for i, _ in _lines(d, "IDLE-HELD gpu-quiet ak-asm-t1-harness")]
        if not held or held[0] != 2:
            out.append(f"IDLE-HELD gpu-quiet should start at tick 2 (2nd quiet sample), got ticks {held[:4]}")
        if any(l for _, l in _lines(d, "IDLE-HELD q3")):
            out.append("q3 judged by CPU % under a GPU grant")
        w = [i for i, _ in _lines(d, "IDLE-HELD-WARN gpu-quiet ak-asm-t1-harness:")]
        if len(w) != 1:
            out.append(f"expected exactly one owner warning over 8 ticks, got {w}")
        return out
    return write(path, ticks), check


def sc_p5_idle_held_logs_once(path):
    """Pass 5 item 3 (2026-11-07): a GPU grant that stays quiet reads IDLE-HELD from tick 2 and the keeper must say so ONCE
    (a state transition), not on every one of the following ticks. The grant itself is still judged idle every tick."""
    rows, world = _gpu_harness_rows(0)
    rows["ak-asm-t1-harness"]["kfd_own"] = False
    ticks = [(rows, world)] * 8

    def check(d):
        held = [i for i, _ in _lines(d, "IDLE-HELD gpu-quiet ak-asm-t1-harness")]
        if len(held) != 1 or held[0] != 2:
            return [f"IDLE-HELD logged on ticks {held} over 8 quiet ticks; expected exactly one line, at tick 2 (transition only)"]
        return []
    return write(path, ticks), check


def sc_override_multiquarter_books_two(path):
    """lsa-quality-32k-20261106-r4-pca: regions any-cpu-quarter, declared multi-quarter(2) accepted via shape_override, threads
    unknown. It was granted ONE quarter (q1) while q3 sat idle. A 2-quarter row is granted two whole quarters or waits."""
    rid = "lsa-r4-pca-override"
    r = row(rid, regions="any-cpu-quarter", extra="python3 job.py", man={
        "declared_shape": "multi-quarter(2)", "shape": "quarter",
        "shape_override": "operator: pestopoppa 2026-11-06: widen LSA pca arm to 2 quarters (longest arm)"})
    free_q1_only = {"q1": {"busy": False}}

    def check(d):
        out = []
        for i, g in _granted(d, rid):
            hq = {h for h in g["holds"] if h in QUARTERS} | _fullq(g["holds"])
            if len(hq) != 2:
                out.append(f"2-quarter row granted {sorted(hq)} at tick {i}")
        if not _granted(d, rid):
            out.append("2-quarter row never granted on an idle host")
        return out
    return write(path, [({rid: r}, {})] * 3), check


def sc_multiquarter_never_q3(path):
    """operator 2026-11-06 "Yes, both": lsa-quality-32k-20261106-r5-pca (multi-quarter(2) via shape_override) was granted q1+q3;
    its q3 lock covered 88-95 (the cores behind MI210 host threads 184-191) and a GPU row waited 600 s on it (rc75). With q0
    and q2 busy and only q1 + q3 free the row WAITS: a CPU multi-quarter booking is q0-q2 only."""
    rid = "lsa-r5-pca-override"
    r = row(rid, regions="any-cpu-quarter", extra="python3 job.py", man={
        "declared_shape": "multi-quarter(2)", "shape": "quarter",
        "shape_override": "operator: pestopoppa 2026-11-06: widen LSA pca arm to 2 quarters (longest arm)"})
    world = {"foreign": {"q0": "foreign-a", "q2": "foreign-b"}}

    def check(d):
        out = []
        for i, g in _granted(d, rid):
            hq = {h for h in g["holds"] if h in QUARTERS} | _fullq(g["holds"])
            out.append(f"multi-quarter CPU row granted {sorted(hq)} at tick {i} (q3 must never be booked)")
        return out
    return write(path, [({rid: r}, world)] * 3), check


def _backfill_rows(gpu=True):
    """2026-11-07 incident: lsa-quality-32k-20261106-r8-{dense,pca} hold q0+q1 for 10 h; the whole-host row
    c7-local-code28k-20261106-r3 (q0-q3) waits; rows that need only q2 / q3 / the GPU are ready."""
    lsa_d = row("lsa-r8-dense", regions="any-of q0", extra="python3 job.py --workers 24", est=36000, rank=20)
    lsa_p = row("lsa-r8-pca", regions="any-of q1", extra="python3 job.py --workers 24", est=36000, rank=20)
    wide = row("c7-code28k-r3", regions="q0,q1,q2,q3", claim="0-95", extra="make -j 96", est=5400, rank=40,
               man={"shape": "host", "declared_shape": "host", "baseline_ref": "replay fixture: whole-host serving"})
    wide["pass"]["passed_at"] = _iso(T0 - 4 * 3600)   # waited > DRAIN_AFTER_S: the wide row drains
    q2 = row("bf-q2-build", regions="any-of q2", extra="make -j 24", est=3 * 3600, rank=60)
    q3 = row("bf-q3-build", regions="any-of q3", extra="make -j 24", est=3 * 3600, rank=60)
    rows = {"lsa-r8-dense": lsa_d, "lsa-r8-pca": lsa_p, "c7-code28k-r3": wide, "bf-q2-build": q2, "bf-q3-build": q3}
    if gpu:
        rows["bf-gpu-tests"] = row("bf-gpu-tests", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, est=2 * 3600,
                                   rank=60, extra="ctest --test-dir build-hip", man={"admission_class": "correctness"})
    return rows


def sc_backfill_if_fits(path):
    """Backfill-if-fits (operator 2026-11-07 "Approve + deploy"): LSA holds q0+q1 (10 h left), a whole-host row waits;
    the q2 / q3 / GPU rows end long before the whole-host row's earliest feasible start (the LSA grants' end), so they
    are granted. A foreign hold with no known end on q1 (tick 1) makes the start UNKNOWN: no reservation at all."""
    rows = _backfill_rows()
    lsa = {k: rows[k] for k in ("lsa-r8-dense", "lsa-r8-pca")}
    ticks = [(lsa, {"host_after_gpu_queue": False})] + [(rows, {})] * 4

    def check(d):
        out = []
        if not _granted(d, "lsa-r8-dense") or not _granted(d, "lsa-r8-pca"):
            return ["fixture: the LSA rows were not granted on tick 0"]
        for rid in ("bf-q2-build", "bf-q3-build", "bf-gpu-tests"):
            if not _granted(d, rid):
                out.append(f"{rid} never granted: q2/q3/gpu idled behind the whole-host row's drain")
        if _granted(d, "c7-code28k-r3"):
            out.append("fixture: the whole-host row was granted while q0+q1 are busy")
        return out
    return write(path, ticks), check


def sc_backfill_reserve_binds(path):
    """Counter-case: a row that would END AFTER the whole-host row's earliest feasible start may not take its regions."""
    rows = _backfill_rows(gpu=False)
    long_q2 = row("bf-q2-long", regions="any-of q2", extra="make -j 24", est=20 * 3600, rank=60, man={"min_window_s": 100 * 3600})  # D9 2026-11-11: a T-cap would starve it below min_window, so it stays late
    rows = {k: v for k, v in rows.items() if k not in ("bf-q2-build", "bf-q3-build")}
    rows["bf-q2-long"] = long_q2
    lsa = {k: rows[k] for k in ("lsa-r8-dense", "lsa-r8-pca")}
    ticks = [(lsa, {})] + [(rows, {})] * 3

    def check(d):
        return [f"bf-q2-long (ends after the whole-host start) granted at tick {i}" for i, _ in _granted(d, "bf-q2-long")]
    return write(path, ticks), check


def sc_backfill_expired_drain(path):
    """Expired drains never block: a persisted drain T in the past (the wide row's T may only move earlier) must not
    keep q2/q3 idle. Ticks 0-16: q0+q1 foreign (no end known); from tick 16 the drain's persisted T has expired."""
    rows = _backfill_rows(gpu=False)
    wide = {"c7-code28k-r3": rows["c7-code28k-r3"]}
    world = {"foreign": {"q0": "foreign-lsa-dense", "q1": "foreign-lsa-pca"}}
    tw = TraceWriter(path, "scenario", "")
    for i in range(16):
        tw.tick(T0 + i * TICK, wide, **world)
    rest = {k: rows[k] for k in ("c7-code28k-r3", "bf-q2-build", "bf-q3-build")}
    for i in range(16, 20):
        tw.tick(T0 + i * TICK, rest, **world)
    tw.close()

    def check(d):
        return [f"{rid} never granted after the drain expired" for rid in ("bf-q2-build", "bf-q3-build") if not _granted(d, rid)]
    return path, check


def sc_deferred_multiquarter_backfills_c15(path):
    """D9 2026-11-18 (c15-fold-cpu): LSA rows hold q0+q1 for 20 h; a multi-quarter(2) row (q0-q2 only) has waited
    > DRAIN_AFTER_S, so its earliest start is ~20 h out - beyond DRAIN_RESERVE_HORIZON_S, deferred (no reservation).
    q2 backfills: the 5 h c15-fold-cpu quarter row is granted in full (PM-CAP 2026-11-21: backfill onto a deferred target
    is bounded by its real earliest start S, not the 2 h horizon), while a 30 h row that cannot be capped (min window
    30 h > S) is refused there (it would delay the target)."""
    lsa_d = row("lsa-dense-20h", regions="any-of q0", extra="python3 job.py --workers 24", est=20 * 3600, rank=20)
    lsa_p = row("lsa-pca-20h", regions="any-of q1", extra="python3 job.py --workers 24", est=20 * 3600, rank=20)
    mq = row("rka-a3b48-mq2", regions="any-cpu-quarter", extra="python3 job.py --workers 48", est=3600, rank=30,
             man={"declared_shape": "multi-quarter(2)", "shape": "multi-quarter(2)"})
    mq["pass"]["passed_at"] = _iso(T0 - 4 * 3600)
    c15 = row("c15-fold-cpu", regions="any-of q2", extra="make -j 24", est=5 * 3600, rank=60, man={"min_window_s": 3600})
    lng = row("q2-long-20h", regions="any-of q2", extra="make -j 24", est=30 * 3600, rank=50,
              man={"min_window_s": 30 * 3600})
    lsa = {"lsa-dense-20h": lsa_d, "lsa-pca-20h": lsa_p}
    rows = dict(lsa, **{"rka-a3b48-mq2": mq, "c15-fold-cpu": c15, "q2-long-20h": lng})
    ticks = [(lsa, {})] + [(rows, {})] * 3

    def check(d):
        out = []
        if not _granted(d, "lsa-dense-20h") or not _granted(d, "lsa-pca-20h"):
            return ["fixture: the LSA rows were not granted on tick 0"]
        if not _granted(d, "c15-fold-cpu"):
            out.append("c15-fold-cpu never granted: q2 idled behind a deferred multi-quarter target")
        out += [f"q2-long-20h (ends beyond the deferred target's start) granted at tick {i}" for i, _ in _granted(d, "q2-long-20h")]
        out += [f"multi-quarter target granted at tick {i} while q0+q1 are busy" for i, _ in _granted(d, "rka-a3b48-mq2")]
        return out
    return write(path, ticks), check



# ---------------------------------------------------------------------------------------------- scheduling model (audit 2026-11-10 C)
def _held_ticks(d, rid):
    """Ticks rid's simulated job was open (grant tick to the tick its engine ended it)."""
    return sum(1 for x in d if rid in x["open_after"])


def _drain_world(extra):
    """LSA rows hold q0+q1 (est 2 h -> grant end ~2 h 15 m); the whole-host row c7 drains for them; `extra` backfills."""
    rows = _backfill_rows(gpu=False)
    rows = {k: rows[k] for k in ("lsa-r8-dense", "lsa-r8-pca", "c7-code28k-r3")}
    for k in ("lsa-r8-dense", "lsa-r8-pca"):
        rows[k]["manifest"].update(estimate_s=7200, window_s=8100)
    lsa = {k: rows[k] for k in ("lsa-r8-dense", "lsa-r8-pca")}
    return lsa, dict(rows, **extra)


def sc_race_eqv_books_by_estimate(path):
    """race-eqv-gpu-r3-20261109 (11-10 04:33-06:38): a row whose estimate overstates its run could not pass a drain and ran
    7 minutes once admitted. Shape-equivalent on q2: estimate 9000 s, drain start ~2 h 15 m away; the old rule admitted by
    estimate + 25 % (11250 s, window 9900 s) and held q2 idle; book_s = 0.75 * 9000 = 6750 s fits, so it is admitted with
    its grant end capped at the drain start and runs its real 7 minutes."""
    r = row("race-eqv-r3-shape", regions="any-of q2", extra="make -j 24", est=9000, rank=60,
            man={"window_s": 9900, "min_window_s": 600})
    r["actual_s"] = 420
    lsa, rows = _drain_world({"race-eqv-r3-shape": r})
    ticks = [(lsa, {})] + [(rows, {})] * 6

    def check(d):
        g = _granted(d, "race-eqv-r3-shape")
        if not g or g[0][0] > 1:
            return ["race-eqv-r3-shape not admitted ahead of the drain by its book_s (q2 idled behind the drain)"]
        gl = [l for l in d[g[0][0]]["lines"] if l.startswith("GRANT race-eqv-r3-shape ")]
        lsa = [l for l in d[0]["lines"] if l.startswith("GRANT lsa-r8-dense ")]
        end = lambda l: l.split(" end=")[1].split()[0]   # noqa: E731
        if not gl or not lsa or end(gl[0]) != end(lsa[0]):
            return ["admitted ahead of the drain without its grant end capped at the drain start"]
        if _held_ticks(d, "race-eqv-r3-shape") * TICK > 420 + 2 * TICK:
            return ["did not end at its real 7-minute run"]
        return []
    return write(path, ticks), check


def sc_resumable_window_end(path):
    """ak-c10-q38fn-floor-r2-20261110 ran out of window at pairs-5 of 24: a resumable row whose job outlasts its window
    ends at the grant end (hard-end rc=75, a normal end for it), never a FAIL, and is not re-granted by the keeper."""
    r = row("ak-floor-resumable", regions="any-of q0", extra="make -j 24", est=4900, rank=50,
            man={"resumable": True, "window_s": 6180, "min_window_s": 600})
    r["actual_s"] = 4 * 4900
    ticks = [({"ak-floor-resumable": r}, {})] * 60

    def check(d):
        out = []
        g = _granted(d, "ak-floor-resumable")
        if len(g) != 1:
            out.append(f"granted {len(g)} times (want exactly 1)")
        if not 0 < _held_ticks(d, "ak-floor-resumable") * TICK <= 6180 + 2 * TICK:
            out.append("the job was not ended at its window")
        if any("ak-floor-resumable" in f for x in d for f in x["fails_new"]):
            out.append("a resumable window end was recorded as a FAIL")
        return out
    return write(path, ticks), check


def sc_overrun_capped_at_drain(path):
    """c10-fold-cpu-q38pp-r2-20261109 ran out of window after 4 of 6 rounds. A non-resumable row admitted ahead of a drain
    that overruns its estimate is still ended at the drain start (the kept hard-end safety): the drain row starts on time."""
    r = row("c10-fold-overrun", regions="any-of q2", extra="make -j 24", est=1800, rank=60,
            man={"window_s": 2460, "min_window_s": 600})
    r["actual_s"] = 3 * 3600
    lsa, rows = _drain_world({"c10-fold-overrun": r})
    rows["c7-code28k-r3"]["manifest"]["estimate_s"] = 600
    ticks = [(lsa, {})] + [(rows, {})] * 90

    def check(d):
        g = _granted(d, "c10-fold-overrun")
        if not g:
            return ["fixture: the overrun row was never admitted"]
        if not 0 < _held_ticks(d, "c10-fold-overrun") * TICK <= 2460 + 2 * TICK:
            return ["overrun row held q2 past its window"]
        return []
    return write(path, ticks), check


def sc_smoke_pockets_no_starvation(path):
    """142 SMOKE-WAIT in two days ("no 4 free cores outside the whole quarters N queued rows need") while regions idled:
    with q2 + q3 foreign and two whole-quarter rows queued, the rows take q0 + q1 AND both smokes run on tick 0 in the
    q0 / q1 pockets."""
    r1 = row("pk-whole-a", extra="make -j 16", est=3600)
    r2 = row("pk-whole-b", extra="make -j 16", est=3600)
    sm = {}
    for i, sid in enumerate(("pk-smoke-1", "pk-smoke-2")):
        b = row(sid, passed=False, extra="python3 x.py --workers 2")
        b["smoke_queued"] = {"id": sid, "queued_at": _iso(T0 + i), "cpus": 4}
        sm[sid] = b
    world = {"foreign": {"q2": "foreign-c", "q3": "foreign-d"}}

    def check(d):
        out = [f"{rid} not granted on tick 0" for rid in ("pk-whole-a", "pk-whole-b")
               if not _granted(d, rid) or _granted(d, rid)[0][0] > 0]
        for sid in sm:
            if not any(l.startswith(f"SMOKE-PLACE {sid}") for l in d[0]["lines"]):
                out.append(f"{sid} not placed on tick 0 (starved)")
        return out
    return write(path, [(dict({"pk-whole-a": r1, "pk-whole-b": r2}, **sm), world)] * 3), check


def sc_foreign_hold_keeps_drain(path):
    """coordinator 2026-11-10 (live, 15:05Z): the rank-2 quiet-host floor row drained for the host while a FOREIGN KFD
    process held the MI210 (no known end) and q1 / q2 were busy until known ends. The keeper logged NO-RESERVE ("a needed
    busy region has no known end") and let agg0 (until 22:21Z) and afc-v3 (until 19:39-21:11Z) take q0 / q3; the floor
    slipped 19:07Z -> 21:11Z. A foreign hold on ONE needed region keeps the reservation at T = max(known ends): rows
    whose book_s ends past T are not admitted on the floor's regions; a row booking inside T still is (capped at T)."""
    floor = row("floor-r2", lane="gpu", regions="mi210_0,0-95", cls="cpu+gpu", gpu_quiet="exclusive", claim="0-95",
                role="bench", extra="llama-server -t 48 --port 8099", est=3600, rank=2,
                man={"shape": "quiet-host", "declared_shape": "quiet-host", "admission_class": "block-timing-quiet",
                     "baseline_ref": "replay fixture: whole-host serving floor"})
    q1 = row("busy-q1", regions="any-of q1", extra="make -j 24", est=3600, rank=50)
    q2 = row("busy-q2", regions="any-of q2", extra="make -j 24", est=3600, rank=50)
    agg0 = row("agg0-l3-load", regions="any-of q0", extra="make -j 24", est=6 * 3600, rank=60, man={"min_window_s": 100 * 3600})  # D9 2026-11-11: a T-cap would starve it below min_window, so it stays late
    afc = row("afc-v3", regions="any-of q3", extra="make -j 24", est=3 * 3600, rank=60, man={"min_window_s": 100 * 3600})  # D9 2026-11-11: a T-cap would starve it below min_window, so it stays late
    short = row("short-q0", regions="any-of q0", extra="make -j 24", est=1800, rank=70)
    world = {"foreign": {GPU: "foreign-kfd"}, "kfd": {4242: 8 << 30}}
    held = {"busy-q1": q1, "busy-q2": q2}
    rows = dict(held, **{"floor-r2": floor, "agg0-l3-load": agg0, "afc-v3": afc, "short-q0": short})
    ticks = [(held, world)] + [(rows, world)] * 6

    def check(d):
        out = []
        if len(_granted(d, "busy-q1")) != 1 or len(_granted(d, "busy-q2")) != 1:
            return ["fixture: q1/q2 rows not granted on tick 0"]
        for rid in ("agg0-l3-load", "afc-v3"):
            if _granted(d, rid):
                out.append(f"{rid} admitted past the drain start although one needed region (MI210) is foreign-held")
        if not _granted(d, "short-q0"):
            out.append("short-q0 (books inside T) not backfilled")
        return out
    return write(path, ticks), check

def sc_cpu_quarter_prefers_q0_over_q3(path):
    """operator 2026-11-10 "Prefer q0-q2 for CPU rows": afc-v3-q38_flash-tools-mild (any-cpu-quarter) took q3 at 15:05Z
    while q0 was free, and the GPU rows that smoked minutes later waited for c88-c95 until 19:39Z. With q0 and q3 free, a
    GPU row smoking, and another (RAM-blocked) row wanting q0 - demand that used to push the CPU row onto q3 - the CPU
    quarter row must take q0; q3 only when it is the only fitting quarter."""
    g = row("gpu-smoking", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, passed=False, est=1800,
            role="bench", extra="llama-server -t 8")
    g["smoke_queued"] = {"id": "gpu-smoking", "queued_at": _iso(T0), "cpus": 4}
    c = row("cpu-quarter", regions="any-cpu-quarter", extra="make -j 24", est=3600, rank=50)
    w = row("q0-wanter", regions="any-of q0", extra="make -j 24", est=3600, rank=200, man={"gib": 100000})
    world = {"foreign": {"q1": "foreign-b", "q2": "foreign-c"}}
    rows = {"gpu-smoking": g, "cpu-quarter": c, "q0-wanter": w}

    def check(d):
        gs = _granted(d, "cpu-quarter")
        if not gs:
            return ["cpu-quarter never granted (q0 was free)"]
        hq = {h for h in gs[0][1]["holds"] if h in QUARTERS} | _fullq(gs[0][1]["holds"])
        return [] if "q3" not in hq else [f"CPU quarter row took q3 ({sorted(hq)}) while q0 was free"]
    return write(path, [(rows, world)] * 3), check


def sc_sticky_drain_e5_overnight(path):
    """PM-DRAINFIX 2026-11-22 (inf45-e5v2-stageb-r7-20261121, rank 25 quiet-host): the drain formed at 21:58Z "until
    00:01Z", then each better-ranked rank-20 AK GPU row that became placeable dropped it for a tick (DRAIN-HELD), the
    drain_state was overwritten with {} and every later drain recomputed T from the newest backfill end: 00:55Z, 01:46Z,
    ... 05:14Z; rank-35 lsa q0-q2 rows were granted in those gaps too. A drain once formed is STICKY: T only moves
    earlier, and every row - better-ranked ones included - that would end after T stays off its regions (gpu-quiet
    included); rows that end by T still backfill."""
    e5 = row("e5-stageb-qh", lane="gpu", regions="mi210_0,0-95", cls="cpu+gpu", gpu_quiet="exclusive", claim="0-95",
             role="bench", extra="llama-server -t 48 --port 8099", est=3600, rank=25,
             man={"shape": "quiet-host", "declared_shape": "quiet-host", "admission_class": "block-timing-quiet",
                  "baseline_ref": "replay fixture: E5 stage-B", "resumable": True})
    q1 = row("busy-q1", regions="any-of q1", extra="make -j 24", est=3600, rank=50)
    q2 = row("busy-q2", regions="any-of q2", extra="make -j 24", est=3600, rank=50)
    ak_long = row("ak-gpu-r20-long", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, role="bench",
                  extra="llama-server -t 8", est=4 * 3600, rank=20, man={"min_window_s": 3 * 3600})
    ak_short = row("ak-gpu-r20-short", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, role="bench",
                   extra="llama-server -t 8", est=900, rank=20)
    lsa = row("lsa-r35-q0", regions="any-of q0", extra="make -j 24", est=3 * 3600, rank=35, man={"min_window_s": 3 * 3600})
    held = {"busy-q1": q1, "busy-q2": q2}
    first = dict(held, **{"e5-stageb-qh": e5})
    rows = dict(first, **{"ak-gpu-r20-long": ak_long, "ak-gpu-r20-short": ak_short, "lsa-r35-q0": lsa})
    ticks = [(held, {"host_after_gpu_queue": False}), (first, {}), (first, {})] + [(rows, {})] * 50

    def check(d):
        out = []
        if len(_granted(d, "busy-q1")) != 1 or len(_granted(d, "busy-q2")) != 1:
            return ["fixture: q1/q2 rows not granted on tick 0"]
        ge = _granted(d, "e5-stageb-qh")
        if not ge:
            return ["e5-stageb-qh never granted: its drain was starved"]
        e5_tick = ge[0][0]
        for rid in ("ak-gpu-r20-long", "lsa-r35-q0"):
            out += [f"{rid} (ends after the drain target) granted at tick {i}, before the drained row (tick {e5_tick})"
                    for i, _ in _granted(d, rid) if i < e5_tick]
        if not _granted(d, "ak-gpu-r20-short"):
            out.append("ak-gpu-r20-short (ends by T) never backfilled")
        return out
    return write(path, ticks), check


def _e5_qh(rank=25):
    return row("e5-stageb-qh", lane="gpu", regions="mi210_0,0-95", cls="cpu+gpu", gpu_quiet="exclusive", claim="0-95",
               role="bench", extra="llama-server -t 48 --port 8099", est=3600, rank=rank,
               man={"shape": "quiet-host", "declared_shape": "quiet-host", "admission_class": "block-timing-quiet",
                    "baseline_ref": "replay fixture: E5 stage-B", "resumable": True})


ORPHAN = {"pid": 2003761, "ppid": 1, "pgid": 2003761, "birth": "123456", "comm": "llama-server",
          "cmd": "/mnt/raid0/llm/llama.cpp-experimental/build/bin/llama-server -m spec-stale1.gguf --port 8080"}


def sc_foreign_server_blocks_quiet_host(path):
    """E5 fix A 2026-11-23 (inf45-e5v2-stageb-r8-20261122): an orphaned llama-server (pid 2003761, :8080, launcher dead)
    ran outside every grant; the keeper granted E5 the whole host 4 times and its clean-runtime gate refused each time.
    While a foreign inference server runs, a quiet-host row is NOT granted (WAIT + IDLE-WHY name the pid); once it is
    gone the row is granted. Never killed by the keeper."""
    e5 = _e5_qh()
    world = {"infer_procs": [ORPHAN]}
    ticks = [({"e5-stageb-qh": e5}, world)] * 4 + [({"e5-stageb-qh": e5}, {})] * 4

    def check(d):
        out = []
        g = _granted(d, "e5-stageb-qh")
        if any(i < 4 for i, _ in g):
            out.append(f"quiet-host row granted at tick {g[0][0]} while orphan llama-server pid 2003761 ran")
        if not any(i >= 4 for i, _ in g):
            out.append("quiet-host row never granted after the foreign server left")
        if not any("pid=2003761" in l for _, l in _lines(d, "WAIT e5-stageb-qh: foreign inference server")):
            out.append("no WAIT line naming the foreign server pid")
        if not any("pid=2003761" in l for _, l in _lines(d, "IDLE-WHY")):
            out.append("no IDLE-WHY line naming the foreign server pid")
        return out
    return write(path, ticks), check


def sc_stack_server_not_foreign(path):
    """Counter-case: the same llama-server registered in the orchestrator stack state (pid + --port match) is stack-managed:
    the quiet-host row is granted as before (the stack decides about its own services)."""
    e5 = _e5_qh()
    world = {"infer_procs": [ORPHAN], "stack_pids": {"2003761": 8080}}
    ticks = [({"e5-stageb-qh": e5}, world)] * 4

    def check(d):
        out = []
        if not _granted(d, "e5-stageb-qh"):
            out.append("quiet-host row refused although the only inference server is stack-managed")
        if _lines(d, "WAIT e5-stageb-qh: foreign"):
            out.append("stack-managed server reported as foreign")
        return out
    return write(path, ticks), check


def sc_quiet_host_not_starved_by_smokes(path):
    """E5 fix B 2026-11-23: before r8 was raised to rank 15, WAIT-FOR-SMOKE kept the rank-25 quiet-host row out of
    planning while 16 rank-20 GPU smokes stayed queued, so its drain never formed. After QH_SMOKE_WAIT_MAX_S (20 min)
    behind queued smokes, it enters planning and its drain forms."""
    e5 = _e5_qh()
    q1 = row("busy-q1", regions="any-of q1", extra="make -j 24", est=7200, rank=50)
    q2 = row("busy-q2", regions="any-of q2", extra="make -j 24", est=7200, rank=50)
    held = {"busy-q1": q1, "busy-q2": q2}
    rows = dict(held, **{"e5-stageb-qh": e5})
    world = {"gpu_smoke_queued": {f"ak-smoke-{k}": 20 for k in range(16)}, "host_after_gpu_queue": False}
    ticks = [(held, {})] + [(rows, world)] * 16   # 16 ticks x 120 s = 32 min of waiting

    def check(d):
        out = []
        if len(_granted(d, "busy-q1")) != 1 or len(_granted(d, "busy-q2")) != 1:
            return ["fixture: q1/q2 rows not granted on tick 0"]
        lim = [i for i, _ in _lines(d, "SMOKE-WAIT-LIMIT e5-stageb-qh")]
        if not lim:
            return ["quiet-host row never released from WAIT-FOR-SMOKE (starved behind queued smokes)"]
        if lim[0] < 10:
            out.append(f"released at tick {lim[0]}, before 20 min of waiting")
        drained = [i for i, l in _lines(d, "IDLE-WHY") if "draining for quiet-host e5-stageb-qh" in l]
        if not drained:
            out.append("no drain formed for the quiet-host row after its smoke-wait limit")
        return out
    return write(path, ticks), check


def sc_instant_complete_suspect(path):
    """c18-fold-cpu-20261122 / c19-fold-cpu-20261123: a multi-quarter row ends rc=0 reason=complete seconds after its grant
    with no result written since the grant and no first-progress marker. The keeper must flag it COMPLETE-SUSPECT: requeue it ONCE
    (partial-blocked-stale-complete) then hold it for its owner, never let it pass as a normal completion. A 3600 s row beside it is not flagged."""
    rid, ok = "c19-fold-cpu-instant-20261123", "c19-fold-cpu-normal-20261123"
    r = row(rid, est=30, regions="any-cpu-quarter", man={"resumable": True, "workdir": f"{JOB}/{rid}"})
    o = row(ok, est=3600, regions="any-cpu-quarter")

    def check(d):
        out = []
        n, m = len(_granted(d, rid)), len(_granted(d, ok))
        if n != 2:
            out.append(f"instant complete granted {n}x; want exactly 2 (flagged COMPLETE-SUSPECT, auto-requeued ONCE, then held)")
        if m != 1:
            out.append(f"a genuine long row was granted {m}x (flagged or requeued)")
        return out
    return write(path, [({rid: r, ok: o}, {})] * 8), check


def sc_quiet_host_waits_for_foreign_busy(path):
    """PM-KEEPER3 #1 (GDNPROJ r2 / aa-calibration-q-c / shexp r2 died on foreign bandwidth load, busy up to 48%): a
    requires_quiet_host row whose only option is q1 is NOT granted while q1 (free of grants) measures 48% foreign busy;
    WAIT + IDLE-WHY name it; once q1 reads quiet the row is granted."""
    r = row("ak-q38fn-cpu-gdnproj-fuse-r2", regions="any-of q1", extra="./bench -t 24", est=1800, rank=20,
            man={"requires_quiet_host": True, "busy_fraction": 1.0})
    busy = {"util": {"q0": 2.0, "q1": 48.0, "q2": 3.0, "q3": 2.0, "gpu": {"busy": 0, "vram_pct": 0.0, "vram_gib": 0.0}}}
    quiet = {"util": {"q0": 2.0, "q1": 4.0, "q2": 3.0, "q3": 2.0, "gpu": {"busy": 0, "vram_pct": 0.0, "vram_gib": 0.0}}}
    rows = {"ak-q38fn-cpu-gdnproj-fuse-r2": r}
    ticks = [(rows, busy)] * 3 + [(rows, quiet)] * 2

    def check(d):
        out = []
        g = _granted(d, "ak-q38fn-cpu-gdnproj-fuse-r2")
        if any(i < 3 for i, _ in g):
            out.append(f"quiet-host row granted at tick {g[0][0]} onto q1 at 48% foreign busy")
        if not any(i >= 3 for i, _ in g):
            out.append("quiet-host row never granted once q1 read quiet")
        if not _lines(d, "WAIT ak-q38fn-cpu-gdnproj-fuse-r2: foreign busy 48% on q1 (quiet-host needs <15%)"):
            out.append("no WAIT line naming the foreign busy")
        if not any("foreign busy 48% on q1" in l for _, l in _lines(d, "IDLE-WHY q1")):
            out.append("no IDLE-WHY q1 line naming the foreign busy")
        return out
    return write(path, ticks), check


def sc_superseded_predecessor_never_regranted(path):
    """PM-KEEPER3 #3 (repro r1 re-granted after r2 published; the two collided on ports): once a successor that
    `supersedes` r1 is published - even before its own smoke passed - r1 is never granted again."""
    r1 = row("ak-repro-r1", regions="any-of q0", extra="./bench -t 24", est=1800, rank=20)
    r2 = row("ak-repro-r2", regions="any-of q0", extra="./bench -t 24", est=1800, rank=20, passed=False,
             man={"supersedes": "ak-repro-r1"})
    ticks = [({"ak-repro-r1": r1, "ak-repro-r2": r2}, {})] * 3

    def check(d):
        out = []
        if _granted(d, "ak-repro-r1"):
            out.append("superseded predecessor ak-repro-r1 granted after its successor was published")
        if not _lines(d, "SUPERSEDED-BLOCK ak-repro-r1 by ak-repro-r2"):
            out.append("no SUPERSEDED-BLOCK line")
        return out
    return write(path, ticks), check


def sc_quiet_row_granted_beside_gpu_grant(path):
    """2026-11-23 quiet-gate fix: a GPU grant (shape gpu-q3, busy_fraction 1.0 = the DEVICE's busy share, no declared
    bandwidth_heavy) must not count as bandwidth-heavy, so a requires_quiet_host CPU row is granted on a quiet quarter."""
    g = row("gpu-fold-r2", lane="gpu", regions="mi210_0,88-95,184-191", cls="gpu", gpu_quiet="exclusive", role="bench",
            nofold=True, est=7200, extra="llama-bench -t 8", man={"shape": "gpu-q3", "busy_fraction": 1.0})
    q = row("quiet-cpu-r1", regions="any-of q0", role="bench", extra="llama-bench -t 24", est=1800,
            man={"requires_quiet_host": True})
    ticks = [({"gpu-fold-r2": g}, {})] * 3 + [({"gpu-fold-r2": g, "quiet-cpu-r1": q}, {})] * 4

    def check(d):
        if not _granted(d, "gpu-fold-r2"):
            return ["GPU row never granted (scenario precondition)"]
        if not _granted(d, "quiet-cpu-r1"):
            return ["quiet CPU row never granted beside a GPU grant that declares no bandwidth_heavy"]
        return []
    return write(path, ticks), check


def sc_heavy_row_held_while_quiet_waits(path):
    """2026-11-23 QUIET-RESERVE: a heavy occupant runs; a quiet row waits (host loud); a NEW heavy row arrives and is NOT
    granted while the quiet row waits; the occupant ends; the quiet row is granted; the heavy row is granted after it."""
    occ = row("occ-heavy", regions="any-of q0", extra="./bench -t 24", est=TICK * 3, rank=20,
              man={"bandwidth_heavy": True})
    q = row("quiet-r1", regions="any-of q1", extra="./bench -t 24", est=TICK * 2, rank=20, man={"requires_quiet_host": True})
    h = row("heavy-r2", regions="any-of q2", extra="./bench -t 24", est=TICK * 2, rank=20, man={"bandwidth_heavy": True})
    ticks = [({"occ-heavy": occ}, {})] + [({"occ-heavy": occ, "quiet-r1": q, "heavy-r2": h}, {})] * 16

    def check(d):
        out = []
        go, gq, gh = _granted(d, "occ-heavy"), _granted(d, "quiet-r1"), _granted(d, "heavy-r2")
        if not go:
            return ["occupant never granted (scenario precondition)"]
        if not gq:
            out.append("quiet row never granted after the loud occupant ended")
        if not gh:
            out.append("heavy row never granted after the quiet row (starved)")
        if gq and gh:
            if gh[0][0] <= gq[0][0]:
                out.append(f"heavy row granted at tick {gh[0][0]} not after the quiet row (tick {gq[0][0]})")
        for x in d:
            if x["i"] > 0 and gq and x["i"] < gq[0][0] and any(g["id"] == "heavy-r2" for g in x["grants"]):
                out.append(f"heavy row granted at tick {x['i']} while the quiet row waited")
        if not _lines(d, "QUIET-RESERVE heavy-r2 held for quiet-r1"):
            out.append("no QUIET-RESERVE line")
        return out
    return write(path, ticks), check


def sc_quiet_rows_serialize_shortest_first(path):
    """2026-11-23 QUIET-SERIAL (AK ak-shexp-r5-quietgate-20261123): three quiet rows of different lengths wait on a quiet
    host (shexp r5 / Q4X r9 / CAFE-1 ran at once and spoiled each other). Exactly one runs at a time, shortest estimate
    first; a heavy row stays reserved (QUIET-RESERVE) until the quiet rows are done."""
    mk = lambda rid, est, where: row(rid, regions=f"any-of {where}", extra="./bench -t 24", est=est, rank=20,
                                      man={"requires_quiet_host": True})
    rows = {"quiet-long": mk("quiet-long", TICK * 6, "q0"), "quiet-short": mk("quiet-short", TICK * 2, "q1"),
            "quiet-mid": mk("quiet-mid", TICK * 4, "q2"),
            "heavy-x": row("heavy-x", regions="any-of q3", extra="./bench -t 24", est=TICK * 2, rank=20, man={"bandwidth_heavy": True})}
    quiet = {"util": {"q0": 1.0, "q1": 1.0, "q2": 1.0, "q3": 1.0, "gpu": {"busy": 0, "vram_pct": 0.0, "vram_gib": 0.0}}}

    def check(d):
        out = []
        order = ["quiet-short", "quiet-mid", "quiet-long"]
        first = []
        for r in order:
            g = _granted(d, r)
            if not g:
                return [f"{r} never granted"]
            first.append(g[0][0])
        if first != sorted(first) or len(set(first)) < 3:
            out.append(f"quiet rows not granted shortest-first one after another: first ticks {dict(zip(order, first))}")
        for x in d:
            n = sum(1 for g in x["grants"] if g["id"].startswith("quiet-"))
            if n > 1:
                out.append(f"{n} quiet rows granted at once at tick {x['i']}")
        hg = _granted(d, "heavy-x")
        if hg and hg[0][0] <= first[0]:
            out.append(f"heavy row granted at tick {hg[0][0]} before the quiet rows")
        if not _lines(d, "QUIET-SERIAL quiet-long waits for running quiet"):
            out.append("no QUIET-SERIAL line")
        return out
    return write(path, [(rows, quiet)] * 30), check


def sc_build_lane_holds_quiet_grants(path):
    """BUILD LANE 2026-11-23 (QUIET-RESERVE starved 5 AK builds, a chain of quiet rows): while a build window is open no NEW quiet
    row is granted (a non-quiet row still is); after it expires the quiet row is granted."""
    q = row("quiet-chain-r1", regions="any-of q1", extra="./bench -t 24", est=TICK * 2, rank=20, man={"requires_quiet_host": True})
    c = row("plain-cpu-r1", regions="any-of q2", extra="make -j 24", est=TICK * 2, rank=30)
    quiet = {"util": {"q0": 1.0, "q1": 1.0, "q2": 1.0, "q3": 1.0, "gpu": {"busy": 0, "vram_pct": 0.0, "vram_gib": 0.0}}}
    rows = {"quiet-chain-r1": q, "plain-cpu-r1": c}
    # window = 4 ticks (TICK 120 s = 2 min -> 8 min); opened on tick 0
    ticks = [(rows, dict(quiet, build_window_min=8))] + [(rows, quiet)] * 11

    def check(d):
        out = []
        g = _granted(d, "quiet-chain-r1")
        if not g:
            return ["quiet row never granted after the build window expired"]
        if g[0][0] < 4:
            out.append(f"quiet row granted at tick {g[0][0]} while the build window was open")
        if not _granted(d, "plain-cpu-r1"):
            out.append("non-quiet row never granted during the build window")
        if not _lines(d, "BUILD-LANE open for"):
            out.append("no BUILD-LANE line")
        return out
    return write(path, ticks), check


def _e5_cpu_row(rid="e5-r8-cpu", rank=25, est=3600, man=None):
    """E5 r8 shape: lane cpu, regions 0-95, class cpu, --role bench --gpu-quiet exclusive --claim-cpus 0-95, threads 80."""
    return row(rid, regions="0-95", cls="cpu", claim="0-95", gpu_quiet="exclusive", role="bench", extra="llama-server -t 80 --port 8099",
               est=est, rank=rank, man=dict({"shape": "quiet-host", "declared_shape": "quiet-host", "baseline_ref": "replay fixture: E5 r8",
                                             "resumable": True}, **(man or {})))


def sc_b1_quiet_host_drain_leaves_gpu(path):
    """AK audit B1 2026-11-23 (E5 r8 drain 02:19-04:44Z held gpu-quiet + q3 for 145 GPU-min; GPU rows queued): a CPU-only quiet-host
    row drains / holds the CPU quarters only. A long GPU row ending after the drain target must still be granted on the idle GPU."""
    e5 = _e5_cpu_row()
    q0 = row("busy-q0", regions="any-of q0", extra="make -j 24", est=3600, rank=50)
    q1 = row("busy-q1", regions="any-of q1", extra="make -j 24", est=3600, rank=50)
    gpu = row("ak-gpu-long", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, role="bench", extra="llama-server -t 8",
              est=3 * 3600, rank=20, man={"min_window_s": 3600})
    held = {"busy-q0": q0, "busy-q1": q1}
    first = dict(held, **{"e5-r8-cpu": e5})
    rows = dict(first, **{"ak-gpu-long": gpu})
    ticks = [(held, {})] + [(first, {})] * 2 + [(rows, {})] * 6

    def check(d):
        g = _granted(d, "ak-gpu-long")
        if not g:
            return ["GPU row never granted while the quiet-host CPU row drained (GPU held by the drain)"]
        out = []
        for i, gg in _granted(d, "e5-r8-cpu"):
            if "gpu-quiet" in gg["holds"] or any(h in gg["holds"] for h in ("t184", "c88")):
                out.append(f"CPU-only quiet-host grant held the GPU / its host threads at tick {i}: {gg['holds']}")
        return out
    return write(path, ticks), check


def sc_b2_orphan_grant_released(path):
    """AK audit B2: a GPU grant whose processes are all gone (ps lists none of its pid/pgid/row id/workdir) for >= 5 min is released
    (HOLD-ORPHAN) so the next GPU row is granted before the window ends; while ps is unanswerable (tick without `ps`) it never is."""
    a = row("ak-gpu-a", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, est=7200, rank=20, extra="llama-server -t 8",
            man={"min_window_s": 3600})
    b = row("ak-gpu-b", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, est=1200, rank=30, extra="llama-server -t 8")
    rows1 = {"ak-gpu-a": a}
    rows2 = {"ak-gpu-a": a, "ak-gpu-b": b}
    other = [[4242, 4242, "S", "/usr/bin/python3 unrelated.py"]]
    ticks = [(rows1, {})] + [(rows2, {})] * 2 + [(rows2, {"ps": other})] * 5

    def check(d):
        out = []
        ev = _lines(d, "HOLD-ORPHAN ak-gpu-a")
        if not ev:
            return ["orphaned GPU grant never released (no HOLD-ORPHAN line)"]
        if ev[0][0] < 3 + 2:
            out.append(f"released after only {ev[0][0] - 3} ticks of absence (< 5 min)")
        if any(i < 3 for i, _ in _lines(d, "HOLD-ORPHAN")):
            out.append("released while ps was unanswerable (must fail closed)")
        if not _granted(d, "ak-gpu-b"):
            out.append("next GPU row not granted after the orphan release")
        return out
    return write(path, ticks), check


def sc_b4_short_row_slot(path):
    """AK audit B4 (ak-bw-gdn-gate-fold-trace-gpu, rank 100, estimate 300 s, never granted while a rank-20 smoke stayed queued): the
    queued smoke cannot start (GPU still free after the batch attempt), so the SHORT worse-ranked GPU row is granted in the gap
    (SHORT-ROW-SLOT, grant end capped), while a long worse-ranked row keeps waiting for the smoke."""
    short = row("ak-gpu-short", lane="gpu", regions="mi210_0,88-95,184-191", cls="gpu", nofold=True, role="bench", extra="llama-server -t 8",
                est=300, rank=100, man={"shape": "gpu-q3"})
    long_ = row("ak-gpu-long", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, role="bench", extra="llama-server -t 8",
                est=4 * 3600, rank=100, man={"min_window_s": 3 * 3600})
    rows = {"ak-gpu-short": short, "ak-gpu-long": long_}
    world = {"gpu_smoke_queued": {"smoke-x": 20}}
    ticks = [(rows, world)] * 6

    def check(d):
        out = []
        if not _granted(d, "ak-gpu-short"):
            out.append("short GPU row never granted in the gap (SHORT-ROW-SLOT)")
        if _granted(d, "ak-gpu-long"):
            out.append("a long worse-ranked row jumped the queued smoke")
        if not _lines(d, "SHORT-ROW-SLOT ak-gpu-short"):
            out.append("no SHORT-ROW-SLOT line")
        return out
    return write(path, ticks), check


# ---------------------------------------------------------------------------------------------- RESERVATION (2026-11-24)
# Replays of the six c21-fold-cpu-20261124 incidents (keeper log 10:03-11:43Z). Each runs in RESERVATION_MODE enforce (the
# tick key "reservation_mode") and checks the low-ranked row of the incident is NOT granted before the rank-9 head; the
# shadow twin checks that shadow changes no placement (the incident still happens) but logs RESERVE-SHADOW / WOULD-REFUSE.
_QUIET_U = {"q0": 1.0, "q1": 1.0, "q2": 1.0, "q3": 1.0, "gpu": {"busy": 0, "vram_pct": 0.0, "vram_gib": 0.0}}


def _util(**over):
    w = {k: over.pop(k) for k in ("claims", "reservation_mode") if k in over}
    return dict(w, util=dict(_QUIET_U, **over))


def _c21(rid, passed=True, est=7900, man=None):
    """c21-fold-cpu-20261124-r*: rank 9, requires_quiet_host, exclusive_cpu, shape host -> q0-q2 + 72-87 (CPU-only)."""
    return row(rid, regions="0-95", cls="cpu", claim="0-95", role="bench", extra="./bench -t 72", est=est, rank=9, passed=passed,
               man=dict({"shape": "host", "declared_shape": "host", "baseline_ref": "replay fixture: c21 fold gate",
                         "requires_quiet_host": True, "busy_fraction": 0.75, "exclusive_cpu": True}, **(man or {})))


def _ak_q(rid, rank, est, quiet=True, sensitive=False, min_window=None):
    """An AutoKernel quarter row (any-of q0,q1,q2, 24 threads): requires_quiet_host, or only quiet_sensitive; min_window_s as
    the real row's grant line (minwin=2400 / 3600) so a T-capped backfill is not admitted where the real one was not."""
    m = {"requires_quiet_host": True} if quiet else ({"quiet_sensitive": True} if sensitive else {})
    if min_window:
        m["min_window_s"] = min_window
    return row(rid, regions="any-of q0,q1,q2", extra="./bench -t 24", est=est, rank=rank, man=dict(m, busy_fraction=1.0))


def _pending(blob, i, smoke_s=600):
    """A smoke-pending blob (no PASS, SMOKE-QUEUED.json); the tick index makes it re-materialize every tick."""
    b = dict(blob)
    b["pass"] = None
    b["smoke_queued"] = {"id": blob["manifest"]["id"], "smoke_s": smoke_s, "tick": i}
    return b


def _first(d, rid):
    g = _granted(d, rid)
    return g[0][0] if g else None


def _before_head(d, head, low):
    """Violations: `low` granted on a tick before `head`'s first grant (or head never granted)."""
    h = _first(d, head)
    out = [] if h is not None else [f"head {head} never granted"]
    for i, _ in _granted(d, low):
        if h is None or i < h:
            out.append(f"{low} granted at tick {i} while head {head} waited (head first granted at tick {h})")
    return out


def _mode(ticks, mode, **kw):
    return [(r, dict(w, reservation_mode=mode, **kw)) for r, w in ticks]


def _ticks_1003():
    """10:03Z: c21-r1 (rank 9) runs, ends; its successor r2 is still in smoke; gdn-state-fwd-r2 (rank 100, quiet-sensitive,
    4.9 h) took q0 until 14:55Z. A 16-core AutoKernel build claim arrived the same minute (the HEAL double-book race)."""
    r1 = _c21("c21-fold-cpu-r1", est=2 * TICK)
    r2 = _c21("c21-fold-cpu-r2")
    gdn = _ak_q("ak-cpu-gdn-state-fwd-r2", 100, 17580, quiet=False, sensitive=True)
    ticks = [({"c21-fold-cpu-r1": r1, "ak-cpu-gdn-state-fwd-r2": gdn}, _util())]
    ticks += [({"c21-fold-cpu-r1": r1, "c21-fold-cpu-r2": _pending(r2, 1), "ak-cpu-gdn-state-fwd-r2": gdn}, _util())]
    for i in range(2, 6):
        w = _util(claims=[{"owner": "autokernel", "cpus": "16", "minutes": 30}]) if i == 2 else _util()
        ticks.append(({"c21-fold-cpu-r2": _pending(r2, i), "ak-cpu-gdn-state-fwd-r2": gdn}, w))
    ticks += [({"c21-fold-cpu-r2": r2, "ak-cpu-gdn-state-fwd-r2": gdn}, _util())] * 4
    return ticks


def _no_double_book(d):
    import re as _re
    out = []
    for x in d:
        rows_ = {g["id"]: set(g["holds"]) for g in x["grants"]}
        for l in x["lines"]:
            if not l.startswith("CLAIM-GRANT"):
                continue
            m = _re.search(r"holds=(\S+)", l)
            ch = set(m.group(1).split(",")) if m else set()
            for rid, h in rows_.items():
                if ch & h:
                    out.append(f"tick {x['i']}: claim {l.split()[1]} and row {rid} granted on the same tokens {sorted(ch & h)[:4]}")
    return out


def sc_res_1003_gdn_vs_c21_r2(path):
    def check(d):
        out = _before_head(d, "c21-fold-cpu-r2", "ak-cpu-gdn-state-fwd-r2") + _no_double_book(d)
        h = _first(d, "c21-fold-cpu-r2")
        for i, l in _lines(d, "CLAIM-GRANT"):
            if h is None or i < h:
                out.append(f"tick {i}: the loud build claim was granted while the quiet head waited ({l[:100]})")
        if not _lines(d, "RESERVE c21-fold-cpu-r2"):
            out.append("no RESERVE line for the smoke-pending head (phantom)")
        return out
    return write(path, _mode(_ticks_1003(), "enforce")), check


def _ticks_noise(low, low_rid, noise):
    """c21 head grantable; a quarter it needs reads foreign noise for 3 ticks (quiet_gate drops it), then quiet."""
    c21 = _c21("c21-fold-cpu-r3")
    rows_ = {"c21-fold-cpu-r3": c21, low_rid: low}
    return [(rows_, _util(**noise))] * 3 + [(rows_, _util())] * 3


def sc_res_1026_calib_a3b(path):
    """10:26Z: c21-r2 dropped by quiet_gate (foreign busy on q0); calib-a3b (rank 60, quiet-sensitive, 1 h) took q0."""
    low = _ak_q("ak-cpu-aa-calibration-q-a3b", 60, 3600, quiet=False, sensitive=True)

    def check(d):
        out = _before_head(d, "c21-fold-cpu-r3", "ak-cpu-aa-calibration-q-a3b")
        if not _lines(d, "RESERVE c21-fold-cpu-r3"):
            out.append("no RESERVE line for the gate-held head")
        return out
    return write(path, _mode(_ticks_noise(low, "ak-cpu-aa-calibration-q-a3b", {"q0": 50.0}), "enforce")), check


def sc_res_1120_specpit_r4(path):
    """11:20Z: c21-r3 dropped by quiet_gate (unclaimed pytest 31% on q3); specpit-r4 (rank 40, quiet, 7.7 h) took q0."""
    low = _ak_q("ak-specpit1-t1p100-r4", 40, 28020)
    return write(path, _mode(_ticks_noise(low, "ak-specpit1-t1p100-r4", {"q3": 31.0}), "enforce")), \
        (lambda d: _before_head(d, "c21-fold-cpu-r3", "ak-specpit1-t1p100-r4"))


def sc_res_1135_shadow_changes_nothing(path):
    """Shadow twin of 11:35Z: placement is today's (the low row IS granted on q0-q2 while c21-r3 waits: RANK-SKIP with the wrong
    T) and the reservation is only logged (RESERVE-SHADOW for c21-r3, WOULD-REFUSE for the low row). The low row is a plain
    quarter row here: with the full quiet set the live QUIET-RESERVE / QUIET-SERIAL pair holds both low rows in the fixture."""
    def check(d):
        out = []
        lows = [r for r in ("ak-cpu-aa-calibration-q-c18-r3", "ak-specpit1-t1p095") if _granted(d, r)]
        h = _first(d, "c21-fold-cpu-r3")
        if not any(h is None or _first(d, r) < h for r in lows):
            out.append("shadow changed placement: no low row was granted ahead of c21-r3 as the live keeper does")
        if not _lines(d, "RESERVE-SHADOW c21-fold-cpu-r3"):
            out.append("no RESERVE-SHADOW line")
        if not any(_lines(d, f"WOULD-REFUSE {r}") for r in lows):
            out.append("no WOULD-REFUSE line for the low row")
        return out
    return write(path, _mode(_ticks_1135(plain_low=True), "shadow", host_drain=False, host_after_gpu_queue=False)), check


def _ticks_1135(plain_low=False):
    """11:35/11:39Z: q0 held by a short row (ends in 3 ticks), an unrelated GPU grant runs 3 h; c21-r3 grantable. RANK-SKIP used
    T = the GPU grant's end (> 1 h) and calib-c18 (rank 60, 1 h) then specpit-t1p095 (rank 40, 24 h) took quarters."""
    occ = row("rka-a3b-remeasure-r5", regions="any-of q0", extra="./bench -t 24", est=3 * TICK, rank=20)
    gpu = row("c21-fold-gpu-r2", lane="gpu", regions="mi210_0,184-191", cls="gpu", nofold=True, est=3 * 3600, rank=9,
              extra="llama-server -t 8", man={"min_window_s": 3600})
    c21 = _c21("c21-fold-cpu-r3")
    c18 = _ak_q("ak-cpu-aa-calibration-q-c18-r3", 60, 3600, quiet=False, sensitive=not plain_low, min_window=2400)
    t1 = _ak_q("ak-specpit1-t1p095", 40, 85800, min_window=3600)
    first = {"rka-a3b-remeasure-r5": occ, "c21-fold-gpu-r2": gpu}
    rest = dict(first, **{"c21-fold-cpu-r3": c21, "ak-cpu-aa-calibration-q-c18-r3": c18})
    if not plain_low:
        rest["ak-specpit1-t1p095"] = t1
    return [(first, _util())] + [(rest, _util())] * 9


def sc_res_1135_rank_skip(path):
    def check(d):
        return (_before_head(d, "c21-fold-cpu-r3", "ak-cpu-aa-calibration-q-c18-r3")
                + _before_head(d, "c21-fold-cpu-r3", "ak-specpit1-t1p095"))
    return write(path, _mode(_ticks_1135(), "enforce", host_after_gpu_queue=False)), check


def _ticks_light():
    """11:13-11:43Z: pm-lc.sh light claims on 84-87 (15 min each, retried) kept c21-r3 (then booked 72-87) unplaceable. Tick 0:
    one claim is granted on the spot (today's path); then a new 15-min request arrives every tick, queued (enforce). Since
    LIGHT-POCKET (16:5xZ, draftwin-r2 held 84-87 until 22:48Z) the host booking is 0-83: c21 starts at once BESIDE the claim,
    and claims keep flowing beside it (light = not loud)."""
    c21 = _c21("c21-fold-cpu-r3")
    lc = [{"owner": "pipeline-mgmt", "cpus": "84-87", "minutes": 15, "light": True}]
    ticks = [({}, _util(claims=lc, reservation_mode="shadow"))]
    ticks += [({"c21-fold-cpu-r3": c21}, _util(claims=lc, reservation_mode="enforce")) for _ in range(13)]
    return ticks


def sc_res_light_claim_84_87(path):
    def check(d):
        out = []
        h = _first(d, "c21-fold-cpu-r3")
        if h is None:
            return ["c21-r3 never granted: light claims on 84-87 kept it out"]
        if h > 1:   # LIGHT-POCKET: the host booking leaves 84-87 free, so the tick-0 light claim never delays the head
            out.append(f"c21-r3 granted only at tick {h} (a light claim on 84-87 delayed the whole-host head)")
        for x in d:
            for g in x["grants"]:
                if g["id"] == "c21-fold-cpu-r3" and set(g["holds"]) & {"c84", "c85", "c86", "c87", "t180", "t181", "t182", "t183"}:
                    out.append(f"tick {x['i']}: the host grant holds the light pocket 84-87: {sorted(g['holds'])[:6]}")
        if not [i for i, _ in _lines(d, "CLAIM-GRANT") if i > h]:
            out.append("no light claim granted beside the running quiet host row (light claims are not loud)")
        return out + _no_double_book(d)
    return write(path, _ticks_light()), check


# REPLAN "C" (operator 2026-11-24 "Keep B shadow, build C"): the same 10:27 / 11:20 / 11:39Z incidents through the full
# allocate() in SHADOW (RESERVATION_MODE and REPLAN_MODE shadow, the deployed modes). Placement must stay today's (the low row
# IS granted ahead of c21 as the live keeper did), and C's would-place decisions must show the fix: a REPLAN-SHADOW place line
# for the head, a REPLAN-SHADOW diff naming the low row the live keeper started, C's start-now never holding a low row while
# the head waits, no solver failure / violation, every solve under the 1 s budget. (15:51Z GPU and 16:19Z draftwin are
# replayed on the pure solver in test_rowflow_replan.py: the GPU quiet-device gate and live smokes are not in this harness.)
def _replan_check(head, lows, live_low=True):
    import re as _re

    def check(d):
        out = []
        h = _first(d, head)
        if live_low and not any(_granted(d, lo) and (h is None or _first(d, lo) < h) for lo in lows):
            out.append(f"shadow changed placement: no low row of {lows} was granted ahead of {head} as the live keeper does")
        if not _lines(d, f"REPLAN-SHADOW place {head} at"):
            out.append(f"no REPLAN-SHADOW place line for {head}")
        early = [lo for lo in lows if _granted(d, lo) and (h is None or _first(d, lo) < h)]
        for lo in early:   # every low row the live keeper started ahead of the head is a named diff
            if not [l for _, l in _lines(d, f"REPLAN-SHADOW diff live={lo} ")]:
                out.append(f"no REPLAN-SHADOW diff line naming the live low row {lo}")
        solves = _lines(d, "REPLAN-SHADOW solve ")
        if len(solves) < len(d):
            out.append(f"REPLAN-SHADOW solve on {len(solves)} of {len(d)} ticks")
        for i, l in solves:
            m = _re.search(r"start-now=(\S+)", l)
            sn = set(m.group(1).split(",")) if m else set()
            if (h is None or i < h) and sn & set(lows):
                out.append(f"tick {i}: C would start {sorted(sn & set(lows))} while {head} waits: {l[:160]}")
            ms = _re.search(r"solve (\d+) ms", l)
            if ms and int(ms.group(1)) >= 1000:
                out.append(f"tick {i}: solve {ms.group(1)} ms >= 1 s budget")
        for pre in ("REPLAN-SHADOW failed", "REPLAN-SHADOW VIOLATION", "REPLAN candidate set failed"):
            out += [f"tick {i}: {l[:160]}" for i, l in _lines(d, pre)]
        return out
    return check


def sc_replan_1027_calib_a3b(path):
    """10:27Z: c21 gate-dropped (foreign busy on q0); live 10:27Z granted calib-a3b (rank 60) - in this fixture today's later
    QUIET-URGENT-WAITING patch already holds it. C: c21 planned first (gate-held, re-decided next tick), the low row never in
    C's start-now while c21 waits."""
    low = _ak_q("ak-cpu-aa-calibration-q-a3b", 60, 16560, quiet=False, sensitive=True)
    return (write(path, _mode(_ticks_noise(low, "ak-cpu-aa-calibration-q-a3b", {"q0": 50.0}), "shadow")),
            _replan_check("c21-fold-cpu-r3", ["ak-cpu-aa-calibration-q-a3b"], live_low=False))


def sc_replan_1120_specpit_r4(path):
    """11:20Z: c21 gate-dropped (unclaimed pytest 31% on q3); live 11:20Z granted specpit-r4 (rank 40, 7.7 h) - held here by
    today's QUIET-URGENT-WAITING. C: c21 planned first, specpit never in C's start-now while c21 waits."""
    low = _ak_q("ak-specpit1-t1p100-r4", 40, 28020)
    return (write(path, _mode(_ticks_noise(low, "ak-specpit1-t1p100-r4", {"q3": 31.0}), "shadow")),
            _replan_check("c21-fold-cpu-r3", ["ak-specpit1-t1p100-r4"], live_low=False))


def sc_replan_1139_rank_skip(path):
    """11:35/11:39Z: RANK-SKIP with T = the GPU grant's end -> live GRANT calib-c18 / specpit-t1p095 ahead of c21-r3 (the low
    rows plain quarter rows, as in the shadow twin above); C plans c21-r3 at its own regions' end, never the 3 h GPU end."""
    return (write(path, _mode(_ticks_1135(plain_low=True), "shadow", host_drain=False, host_after_gpu_queue=False)),
            _replan_check("c21-fold-cpu-r3", ["ak-cpu-aa-calibration-q-c18-r3", "ak-specpit1-t1p095"]))



def sc_host_after_gpu_queue(path):
    """Whole-host work waits for queued GPU smoke while a quarter backfills, then starts."""
    h = _c21("c21-fold-cpu-r3")
    q = _ak_q("gpu-queue-backfill", 60, TICK, quiet=False, sensitive=False)
    rows = {"c21-fold-cpu-r3": h, "gpu-queue-backfill": q}
    ticks = [(rows, {"gpu_smoke_queued": {"gpu-smoke": 20}})] + [(rows, {})] * 8
    def check(d):
        out = []
        if not _granted(d, "gpu-queue-backfill") or _first(d, "gpu-queue-backfill") != 0:
            out.append("quarter did not backfill while GPU smoke was queued")
        hstart = _first(d, "c21-fold-cpu-r3")
        if hstart is None or hstart == 0:
            out.append("host did not wait for the GPU queue to empty and then start")
        if not any("DEFERRED-AFTER-GPU-QUEUE (1 GPU rows queued)" in line for _, line in _lines(d, "IDLE-WHY")):
            out.append("no IDLE-WHY explaining GPU queue deferral")
        return out
    return write(path, ticks), check


def sc_host_drain_1135(path):
    """HOST-DRAIN (operator 2026-11-25): the 11:35Z twin with HOST-DRAIN on (the deployed default). c21-r3 (whole host) has
    waited > 30 min: no worse-ranked low row is granted ahead of it, a HOST-DRAIN line names the held row."""
    lows = ("ak-cpu-aa-calibration-q-c18-r3", "ak-specpit1-t1p095")

    def check(d):
        out = []
        h = _first(d, "c21-fold-cpu-r3")
        early = [r for r in lows if _granted(d, r) and (h is None or _first(d, r) < h)]
        if early:
            out.append(f"low row(s) {early} granted ahead of c21-r3 under HOST-DRAIN")
        if not _lines(d, "HOST-DRAIN c21-fold-cpu-r3 "):
            out.append("no HOST-DRAIN line for c21-r3")
        return out
    return write(path, _mode(_ticks_1135(plain_low=True), "shadow", host_drain=True, host_after_gpu_queue=False)), check


SCENARIOS = {
    "host-after-gpu-queue": sc_host_after_gpu_queue,
    "host-drain-1135": sc_host_drain_1135,
    "replan-1027-calib-a3b-shadow": sc_replan_1027_calib_a3b,
    "replan-1120-specpit-r4-shadow": sc_replan_1120_specpit_r4,
    "replan-1139-rank-skip-shadow": sc_replan_1139_rank_skip,
    "res-1003-gdn-vs-c21-r2-smoke-pending": sc_res_1003_gdn_vs_c21_r2,
    "res-1026-calib-a3b-gate-dropped-head": sc_res_1026_calib_a3b,
    "res-1120-specpit-r4-noise-dropped-head": sc_res_1120_specpit_r4,
    "res-1135-shadow-changes-nothing": sc_res_1135_shadow_changes_nothing,
    "res-1135-1139-rank-skip-wrong-T": sc_res_1135_rank_skip,
    "res-light-claim-84-87-queue": sc_res_light_claim_84_87,
    "build-lane-holds-quiet-grants": sc_build_lane_holds_quiet_grants,
    "b1-quiet-host-drain-leaves-gpu": sc_b1_quiet_host_drain_leaves_gpu,
    "b2-orphan-grant-released": sc_b2_orphan_grant_released,
    "b4-short-row-slot": sc_b4_short_row_slot,
    "quiet-rows-serialize-shortest-first": sc_quiet_rows_serialize_shortest_first,
    "heavy-row-held-while-quiet-waits": sc_heavy_row_held_while_quiet_waits,
    "quiet-row-granted-beside-gpu-grant": sc_quiet_row_granted_beside_gpu_grant,
    "instant-complete-is-suspect": sc_instant_complete_suspect,
    "quiet-host-waits-for-foreign-busy": sc_quiet_host_waits_for_foreign_busy,
    "superseded-predecessor-never-regranted": sc_superseded_predecessor_never_regranted,
    "foreign-server-blocks-quiet-host": sc_foreign_server_blocks_quiet_host,
    "stack-server-not-foreign": sc_stack_server_not_foreign,
    "quiet-host-not-starved-by-smokes": sc_quiet_host_not_starved_by_smokes,
    "sched-sticky-drain-e5-overnight": sc_sticky_drain_e5_overnight,
    "cpu-quarter-prefers-q0-over-q3": sc_cpu_quarter_prefers_q0_over_q3,
    "sched-foreign-hold-keeps-drain": sc_foreign_hold_keeps_drain,
    "sched-race-eqv-books-by-estimate": sc_race_eqv_books_by_estimate,
    "sched-resumable-window-end": sc_resumable_window_end,
    "sched-overrun-capped-at-drain": sc_overrun_capped_at_drain,
    "sched-smoke-pockets-no-starvation": sc_smoke_pockets_no_starvation,
    "backfill-if-fits-lsa-whole-host": sc_backfill_if_fits,
    "backfill-reserve-binds-long-row": sc_backfill_reserve_binds,
    "backfill-expired-drain-never-blocks": sc_backfill_expired_drain,
    "deferred-multiquarter-backfills-c15": sc_deferred_multiquarter_backfills_c15,
    "multiquarter-never-q3": sc_multiquarter_never_q3,
    "override-multiquarter-books-two": sc_override_multiquarter_books_two,
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
    "gpu-blocked-whole-rows-free-smokes": sc_gpu_blocked_whole_rows_free_smokes,
    "cpu-whole-row-reservation-holds": sc_cpu_whole_row_reservation_holds,
    "gpu-timing-narrow-q3-concurrent-with-8core-build": sc_gpu_timing_narrow_q3,
    "gpu-timing-narrow-q3-build-beside-open-timing": sc_gpu_timing_narrow_q3_reverse,
    "idle-held-warns-owner-once": sc_idle_held_warns_once,
    "idle-held-repeat-warning-15min": sc_idle_held_repeats_each_15min,
    "idle-held-busy-grant-silent": sc_idle_held_busy_grant_silent,
    "p4-precond-refusal-parks-once": sc_precond_parks_once,
    "p4-completed-row-not-rc14": sc_completed_not_rc14,
    "p4-dead-poller-without-receipt-still-fails": sc_dead_poller_without_receipt_still_fails,
    "p4-gpu-harness-with-kfd-never-idle-held": sc_gpu_harness_with_kfd_never_idle,
    "p4-gpu-grant-cpu-regions-not-judged": sc_gpu_grant_cpu_regions_not_judged,
    "p4-gpu-grant-quiet-device-idle-after-two-samples": sc_gpu_grant_quiet_device_idle_after_two_samples,
    "p5-idle-held-logs-once": sc_p5_idle_held_logs_once,
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
    "gpu-timing-narrow-q3-concurrent-with-8core-build": ["INV-GPU-TIMING-Q3", "INV-LOCKSET"],
    "gpu-timing-narrow-q3-build-beside-open-timing": ["INV-GPU-TIMING-Q3", "INV-LOCKSET"],
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
            "first_progress_s": 900, "priority_rank": 40,
            "estimate_basis": {"provisional": True, "reason": "replay fixture", "units": 1,
                               "rebook_from": "out-smoke/smoke_measure.json"}}

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
            "estimate_s": 3000, "handoff_task": "handoffs/active/x.md:INF75", "ram_gib": 64, "first_progress_s": 900,
            "estimate_basis": {"provisional": True, "reason": "replay fixture", "units": 1,
                               "rebook_from": "out-smoke/smoke_measure.json"}}

    def check(row, err):
        if err is not None:
            return [f"refused at publish: {err[:200]}"]
        return [] if row.get("declared_threads") == 48 else [f"threads {row.get('declared_threads')} != 48 (helper OMP taken as evidence)"]
    return spec, check


YARN_JOB_SIDE = """import os, subprocess
def job(port):
    env = os.environ
    if env.get('FILLER_THREADS') != '24' or len(os.sched_getaffinity(0)) != 48:
        raise ValueError("affinity")
    procenv = {'PATH': '/usr/bin:/bin', 'OMP_NUM_THREADS': '24', 'OMP_PROC_BIND': 'spread'}
    return subprocess.run(['llama-server', '--port', str(port)], env=procenv).returncode
def smoke():
    procenv = {'PATH': '/usr/bin:/bin', 'OMP_NUM_THREADS': '1'}
    return subprocess.run(['python3', '-c', 'pass'], env=procenv).returncode
"""


def pub_yarn_job_side_threads(root):
    """yarn-oolong-s1/s2-import-eligible29-v38 (2026-11-05): launch.sh's blanket `export OMP_NUM_THREADS=1` was the
    only evidence read; the compute process (job_side.py, imported by boot.py) runs llama-server with OMP 24 and
    refuses FILLER_THREADS != 24 -> contract sub-quarter, granted 4 cores. The compute process's declared threads win."""
    rid = "yarn-like-job-side-24t"
    d = os.path.join(root, rid)
    os.makedirs(d, exist_ok=True)
    eng = os.path.join(root, "filler_run15.sh")
    open(eng, "w").write("#!/bin/bash\n")
    open(os.path.join(d, "job_side.py"), "w").write(YARN_JOB_SIDE)
    open(os.path.join(d, "boot.py"), "w").write("import sys\nimport job_side\nraise SystemExit(job_side.job(19412))\n")
    open(os.path.join(d, "job.sh"), "w").write(f"#!/bin/bash\nD={d}\nexport PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 "
                                                "OPENBLAS_NUM_THREADS=1\nexec taskset -c \"${FILLER_CPUS:?}\" python3 \"$D/boot.py\"\n")
    lp = os.path.join(d, "launch.sh")
    open(lp, "w").write(f"#!/bin/bash\nset -euo pipefail\nD={d}\nexec /bin/bash {eng} --id {rid} --class cpu --role build "
                        f"--min-window 3600 --cmd 'bash {d}/job.sh --job' --complete-cmd \"true\" --stop \"$D/STOP\" --workdir \"$D\"\n")
    spec = {"id": rid, "owner": "t", "launcher": lp, "lane": "cpu", "regions": "any-cpu-quarter",
            "result_path": os.path.join(d, "out", "results.jsonl"), "decision_rule": "replay publish fixture",
            "estimate_s": 3000, "handoff_task": "handoffs/active/x.md:YARN", "first_progress_s": 900}

    def check(row, err):
        if err is not None:
            return [f"refused at publish: {err[:200]}"]
        bad = []
        if row.get("declared_threads") != 24:
            bad.append(f"threads {row.get('declared_threads')} != 24 (wrapper OMP 1 taken over the compute process's 24)")
        if row.get("shape") != "quarter":
            bad.append(f"shape {row.get('shape')} != quarter")
        return bad
    return spec, check


def _mk_cpu_row(root, rid, job, cmd_extra=""):
    d = os.path.join(root, rid)
    os.makedirs(d, exist_ok=True)
    eng = os.path.join(root, "filler_run15.sh")
    open(eng, "w").write("#!/bin/bash\n")
    open(os.path.join(d, "job.py"), "w").write(job)
    lp = os.path.join(d, "launch.sh")
    open(lp, "w").write(f"#!/bin/bash\nset -euo pipefail\nD={d}\nexport OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1\n"
                        f"exec /bin/bash {eng} --id {rid} --class cpu --role build --min-window 900 "
                        f"--cmd \"/usr/bin/python3 -B $D/job.py{cmd_extra}\" --complete-cmd \"true\" --stop \"$D/STOP\" --workdir \"$D\"\n")
    return d, lp


def _quarter_only(row, err, rf, want_gpu=False):
    if err is not None:
        return [f"refused at publish: {err[:200]}"]
    c = rf.contract_of(row)
    bad = [] if c["shape"] == "quarter" else [f"shape {c['shape']} != quarter"]
    if any(rf.GPU in x for x in c["options"]) != want_gpu:
        bad.append(f"gpu-quiet in options {c['options'][:1]}")
    return bad


def pub_stt5_cpu_declared_no_gpu(root):
    """STT5 r5 (2026-11-05): --class cpu, device cpu, whisper-cli -ng whose path sits under a HIP-capable tree, -t =
    affinity width; granted holds=c72..c75,gpu-quiet: 4 cores AND the GPU token. A cpu-declared row never holds it."""
    rid = "stt5-like-cpu-declared"
    d, lp = _mk_cpu_row(root, rid, "import os\nBIN='/mnt/raid0/llm/whisper.cpp/build-hip/bin/whisper-cli'\n"
                                    "cmd=[BIN,'-ng','-t',str(len(os.sched_getaffinity(0)))]\n")
    spec = {"id": rid, "owner": "t", "launcher": lp, "lane": "cpu", "regions": "any-cpu-quarter", "device": "cpu",
            "shape": "quarter", "gpu_fence_override": "owner: t 2026-11-05: -ng, HIP_VISIBLE_DEVICES=-1",
            "result_path": os.path.join(d, "out", "r.json"), "decision_rule": "replay publish fixture",
            "estimate_s": 3000, "handoff_task": "handoffs/active/x.md:STT5", "first_progress_s": 600}
    return spec, lambda row, err, rf: _quarter_only(row, err, rf)


def pub_iqk_declared_quarter_floor(root):
    """iqk-q8-prefill-ab/-step0 (2026-11-05): declared shape quarter (CPU timing), smoke measured ~2 threads on its 4
    cpus -> granted 72-75 + 168-171, jobs refused rc 8 "not a whole quarter". A declared quarter is never shrunk."""
    rid = "iqk-like-declared-quarter"
    d, lp = _mk_cpu_row(root, rid, "import os\nassert len(os.sched_getaffinity(0)) == 48, 'not a whole quarter'\n")
    os.makedirs(os.path.join(root, "compute-flags", "dryrun", rid), exist_ok=True)
    spec = {"id": rid, "owner": "t", "launcher": lp, "lane": "cpu", "regions": "any-cpu-quarter", "shape": "quarter",
            "result_path": os.path.join(d, "out", "r.json"), "decision_rule": "replay publish fixture",
            "estimate_s": 3000, "handoff_task": "handoffs/active/x.md:IQK", "first_progress_s": 600}

    def check(row, err, rf):
        return _quarter_only(dict(row or {}, measured_threads=2.2), err, rf)
    return spec, check


def pub_iqk_ab_r3_explicit_q2(root):
    """iqk-q8-prefill-ab-r3-20261105: regions "q2", shape quarter, operator shape_override -> GRANTED 80-83,176-179
    (4 cores on q3). Explicit regions + shape_override are honoured verbatim: exactly q2."""
    rid = "iqk-q8-prefill-ab-r3-like"
    d, lp = _mk_cpu_row(root, rid, "import os\nassert len(os.sched_getaffinity(0)) >= 24, 'not a whole quarter'\n")
    spec = {"id": rid, "owner": "t", "launcher": lp, "lane": "cpu", "regions": "q2", "shape": "quarter",
            "shape_override": "operator: op 2026-11-05: CPU timing A/B needs one whole quarter",
            "result_path": os.path.join(d, "out", "r.json"), "decision_rule": "replay publish fixture",
            "estimate_s": 3000, "handoff_task": "handoffs/active/x.md:IQK", "first_progress_s": 600}

    def check(row, err, rf):
        if err is not None:
            return [f"refused at publish: {err[:200]}"]
        c = rf.contract_of(dict(row, measured_threads=3.1))
        bad = [] if [set(x) - {rf.GPU} for x in c["options"]] == [{"q2"}] else [f"options {c['options']} != [q2]"]
        g = rf.grant_regions(row, c["options"][0])
        if rf._cpu_set(g) != rf._cpu_set(rf.cpu_list("q2")):
            bad.append(f"grant regions {g} != q2")
        return bad
    return spec, check


def pub_inf75_c6_r2_explicit_override(root):
    """inf75-c5-w3-halfb-census-c6-r2-20261105: regions mi210_0,48-95,144-191 + operator shape_override -> GRANTED
    mi210_0,80-83,176-179; admission refused "missing q2". Granted regions and lock are the declared ones verbatim."""
    spec, _ = pub_inf75_helper_omp(root)
    spec["shape_override"] = "operator: op 2026-11-05: canonical INF-75 half-B placement"

    def check(row, err, rf):
        if err is not None:
            return [f"refused at publish: {err[:200]}"]
        c = rf.contract_of(dict(row, measured_threads=1.2, declared_threads=1))
        bad = []
        if len(c["options"]) != 1 or not {"q2", "q3", rf.GPU} <= set(c["options"][0]):
            bad.append(f"options {c['options']} do not hold q2+q3+gpu")
        g = rf.grant_regions(row, c["options"][0])
        if g != row["regions"]:
            bad.append(f"grant regions {g} != {row['regions']}")
        if c.get("explicit_cpus") and rf._cpu_set(c["explicit_cpus"]) != rf._cpu_set("48-95,144-191"):
            bad.append(f"lock {c['explicit_cpus']} != 48-95,144-191")
        return bad
    return spec, check


def _wj_spec(root, rid, **kw):
    d, lp = _mk_cpu_row(root, rid, "import os\nassert len(os.sched_getaffinity(0)) >= 48, 'width-agnostic prefill'\n")
    txt = open(lp).read().replace("export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1\n", "")   # width-agnostic: no thread knob
    open(lp, "w").write(txt)
    spec = {"id": rid, "owner": "t", "launcher": lp, "lane": "cpu", "regions": "any-cpu-quarter", "shape": "multi-quarter(2)",
            "result_path": os.path.join(d, "out", "r.json"), "decision_rule": "replay publish fixture",
            "estimate_s": 3000, "handoff_task": "handoffs/active/x.md:LSA", "first_progress_s": 600}
    spec.update(kw)
    return spec


def pub_wj_justified_accepted(root):
    """lsa-quality-32k-20261106-r4-pca: width-agnostic CPU prefill, multi-quarter(2), width_justification, NO shape_override."""
    spec = _wj_spec(root, "lsa-wj-ok", width_justification="width-agnostic prefill; throughput scales with threads")

    def check(row, err, rf):
        if err is not None:
            return [f"refused at publish: {err[:200]}"]
        c = rf.contract_of(row)
        return [] if row.get("width_justification") and str(c["shape"]).startswith("multi-quarter") else [f"contract {c['shape']} / no justification"]
    return spec, check


def pub_wj_unjustified_refused(root):
    spec = _wj_spec(root, "lsa-wj-none")

    def check(row, err):
        return [] if err is not None and "books" in err and "width_justification" in err else [f"expected the width refusal, got row={bool(row)} err={err}"]
    return spec, check


def pub_wj_short_refused(root):
    spec = _wj_spec(root, "lsa-wj-short", width_justification="faster")

    def check(row, err):
        return [] if err is not None and "width_justification" in err else [f"expected refusal of a short justification, got {err}"]
    return spec, check



def pub_override_multiquarter_persisted(root):
    spec = _wj_spec(root, "lsa-ovr-ok", shape_override="operator: pestopoppa 2026-11-06: widen LSA pca arm to 2 quarters (longest arm)")

    def check(row, err, rf):
        if err is not None:
            return [f"refused at publish: {err[:200]}"]
        c = rf.contract_of(row)
        return [] if row.get("shape") == "multi-quarter(2)" and c["shape"] == "multi-quarter(2)" else [f"persisted shape {row.get('shape')} / contract {c['shape']}"]
    return spec, check


def pub_gpu_wj_q0(root):
    d = os.path.join(root, "gpu-wj")
    os.makedirs(d, exist_ok=True)
    eng = os.path.join(root, "filler_run15.sh")
    open(eng, "w").write("#!/bin/bash\n")
    open(os.path.join(d, "job.py"), "w").write("print(1)\n")
    lp = os.path.join(d, "launch.sh")
    open(lp, "w").write(f"#!/bin/bash\nset -euo pipefail\nD={d}\nexec /bin/bash {eng} --id gpu-wj --class gpu --no-fold-siblings --gpu-quiet shared "
                        f"--min-window 900 --cmd \"/usr/bin/python3 -B $D/job.py\" --complete-cmd \"true\" --stop \"$D/STOP\" --workdir \"$D\"\n")
    spec = {"id": "gpu-wj", "owner": "t", "launcher": lp, "lane": "gpu", "regions": "mi210_0,0-23,72-87,184-191",
            "result_path": os.path.join(d, "out", "r.json"), "decision_rule": "replay publish fixture", "estimate_s": 3000,
            "handoff_task": "handoffs/active/x.md:GPU", "first_progress_s": 600,
            "width_justification": "correctness reference runs on the ggml CPU backend and needs a quarter",
            "estimate_basis": {"provisional": True, "reason": "replay fixture", "units": 1,
                               "rebook_from": "out-smoke/smoke_measure.json"}}

    def check(row, err, rf):
        if err is not None:
            return [f"refused at publish: {err[:200]}"]
        opt = rf.contract_of(row)["options"][0]
        bad = [] if "q0" in opt else ["justified q0 not booked"]
        if "q3" in opt or {"c72", "c80"} & rf.expand(opt):
            bad.append("q3 72-87 booked")
        return bad
    return spec, check


def pub_gpu_unjustified_q0_refused(root):
    spec, _ = pub_gpu_wj_q0(root)
    spec = {**spec, "regions": "mi210_0,0-23,184-191"}
    spec.pop("width_justification")
    return spec, (lambda row, err: [] if err is not None and "width_justification" in err else [f"expected refusal, got {err}"])


PUBLISH_SCENARIOS = {"publish-override-multiquarter-persisted": pub_override_multiquarter_persisted,
                     "publish-gpu-wj-q0-q2-only": pub_gpu_wj_q0,
                     "publish-gpu-unjustified-q0-refused": pub_gpu_unjustified_q0_refused,
                     "publish-wj-justified-multiquarter-accepted": pub_wj_justified_accepted,
                     "publish-wj-unjustified-multiquarter-refused": pub_wj_unjustified_refused,
                     "publish-wj-short-justification-refused": pub_wj_short_refused,
                     "publish-npd1-step5-accepted": pub_npd1_step5,
                     "publish-helper-omp-not-thread-evidence": pub_inf75_helper_omp,
                     "publish-yarn-compute-process-threads-win": pub_yarn_job_side_threads,
                     "publish-stt5-cpu-declared-never-gpu-quiet": pub_stt5_cpu_declared_no_gpu,
                     "publish-iqk-declared-quarter-never-shrunk": pub_iqk_declared_quarter_floor,
                     "publish-iqk-ab-r3-explicit-q2-verbatim": pub_iqk_ab_r3_explicit_q2,
                     "publish-inf75-c6-r2-explicit-override-verbatim": pub_inf75_c6_r2_explicit_override}


# ---------------------------------------------------------------------------------------------- CLAIM-path scenarios
# `claim --build --light` (AutoKernel 2026-11-23) is not an allocator decision, so like the PUBLISH family it runs the
# candidate's own code (claim_build + quiet_gate) on a temp tree: fn(root, rf) -> [violations].
def claim_light_beside_quiet(root, rf):
    import json
    import tempfile
    flags = tempfile.mkdtemp(prefix="light-replay-", dir=root)
    os.makedirs(os.path.join(flags, "grants"))
    quiet = {"id": "quiet-a", "requires_quiet_host": True, "shape": "quarter", "result_path": os.path.join(flags, "q", "results.jsonl")}
    rf.write_grant(flags, "quiet-a", "q0", {"q0"}, 3600)   # a quiet row running on q0

    def snap(flags_, grants):
        all_ = set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)
        busy = set()
        for g in grants:
            busy |= rf.expand(set(g["holds"]))
        busy |= {q for q in rf.QUARTERS if rf.expand({q}) & busy}
        return None, all_ - busy, None
    rf.host_snapshot = snap
    out = []
    if not hasattr(rf, "_claim_light_locked"):
        return ["candidate has no light claim (claim_build(..., light=True))"]
    kw = dict(log=lambda m: None, allrows={"quiet-a": quiet})
    try:
        gid, _ = rf.claim_build(flags, "autokernel", "84-87", 10, light=True, **kw)
    except rf.Refused as e:
        return [f"light claim refused beside a running quiet row: {e}"]
    bj = json.load(open(os.path.join(flags, "grants", gid + ".build.json")))
    if bj.get("bandwidth_class") != "light":
        out.append(f"grant record lacks bandwidth_class: light ({bj})")
    kl = open(os.path.join(flags, "ws58-calendar-keeper.log")).read()
    if f"LIGHT-CLAIM {gid} cpus=84-87 beside quiet quiet-a" not in kl:
        out.append("keeper log lacks the LIGHT-CLAIM line")
    cand = {"id": "q-next", "options": [{"q3"}], "rank": 1, "kind": "row", "shape": "quarter"}
    g = [x for x in rf.open_grants(flags) if x["id"] == gid]
    kept, _, _ = rf.quiet_gate([cand], {"q-next": {"requires_quiet_host": True}}, g, {"q3": 0.0}, flags=flags)
    if kept != [cand]:
        out.append("a light claim delayed a quiet candidate in quiet_gate (it must not be bandwidth-heavy)")
    for label, args in (("second light claim", ("86", 5)), ):
        try:
            rf.claim_build(flags, "other", args[0], args[1], light=True, **kw)
            out.append(f"{label} was granted")
        except rf.Refused:
            pass
    try:
        rf.claim_build(flags, "autokernel", "72-87", 10, **kw)
        out.append("a non-light claim was granted beside a running quiet row")
    except rf.Refused:
        pass
    return out


def claim_q3_build_yields_to_gpu_row(root, rf):
    """AK audit B3: a NEW non-light q3 build claim yields to a grantable GPU row waiting only on q3 host cores; q0-q2 builds, a light
    claim on 84-87 (no overlap) and an already-open build are unaffected."""
    import tempfile
    flags = tempfile.mkdtemp(prefix="b3-replay-", dir=root)
    os.makedirs(os.path.join(flags, "grants"))
    if not hasattr(rf, "gpu_rows_waiting_on_q3"):
        return ["candidate has no B3 (gpu_rows_waiting_on_q3)"]
    opt = frozenset(rf.GPU_Q3_TOKENS)
    rf.runnable, rf.status = (lambda st: True), (lambda *a, **k: {})
    rf.contract_of = lambda d, o=None, flags=None: {"options": [opt]}
    busy = {f"c{k}" for k in range(88, 96)}
    free = (set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)) - busy
    rf.host_snapshot = lambda f, g: (None, set(free), None)
    allrows = {"gpu-row": {"id": "gpu-row", "lane": "gpu"}}
    kw = dict(log=lambda m: None, allrows=allrows)
    out = []
    try:
        rf.claim_build(flags, "autokernel", "72-87", 10, **kw)
        out.append("a new q3 build claim was granted while a GPU row waited only on q3 host cores")
    except rf.Refused:
        pass
    try:
        rf.claim_build(flags, "autokernel", "84-87", 5, light=True, **kw)
    except rf.Refused as e:
        out.append(f"light claim 84-87 (no overlap) refused: {e}")
    try:
        rf.claim_build(flags, "autokernel", "24", 10, **kw)
    except rf.Refused as e:
        out.append(f"q0-q2 build refused: {e}")
    return out


CLAIM_SCENARIOS = {"light-test-claim-beside-quiet": claim_light_beside_quiet,
                   "b3-q3-build-yields-to-gpu-row": claim_q3_build_yields_to_gpu_row}


def build_all(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    return {name: fn(os.path.join(out_dir, name + ".trace.jsonl")) for name, fn in SCENARIOS.items()}
