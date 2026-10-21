#!/usr/bin/env python3
"""akx27_driver.py -- AKX-ALL-27b: non-trivial replay of the width-invariance dimension on the CDNA2 Q8 route pair
(parent 732389d6d vs keep b0eb4fab4, footprint ggml/src/ggml-cuda/mmvq.cu) on the two HIP store builds produced by the
`akx-all-27b-builds` filler (kernels/builds/gpu-20261021-{732389d6d,b0eb4fab4}).

    akx27_driver.py --dry-run|--execute [--run-dir D] [--stand-in]     (--stand-in: dry-run only, uses champion C for both builds)

--execute REFUSES outside a claim (FILLER_ID from filler_run2.sh --gpu-quiet exclusive, or AKX27_INSIDE_CLAIM=1 under
`region-lock run --cpu-list 0-95 --role bench --gpu-quiet exclusive`).  Exit: 0 ok, 3 refused, 5 build-missing, 7 proof failed.
Steps: (1) builds present + linkage proof + route proof, (2) link one width_probe_hip per build (g++ against THAT build's libggml,
RUNPATH = its own bin: run_width_probe.py refuses anything else), (3) AKX-ALL-26 HIP harness per build (--threads 8 --kmax 9 --repeats 3),
(4) width_dimension relative to the parent. Decision (predeclared, mechanical):
  nontrivial_verdict          counts.new_failing + lower/higher first-fail k + fixed > 0           -> done criterion met
  unchanged_route_proven      verdict unchanged AND route proven in both binaries                    -> done criterion met (alternative clause)
  unchanged_route_unproven    anything else                                                           -> NOT met; route proof gap reported
Route proof = libggml-hip sha256 differs AND keep src contains the akm-cdna2-q8-b4-mmvq-route marker in mmvq.cu AND parent src does not
AND b0eb4fab4 is an ancestor of the keep src HEAD and not of the parent src HEAD.
"""
import argparse, json, os, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v11_driver as V

K = V.K
PARENT, KEEP = "732389d6d", "b0eb4fab4"
W = Path("/mnt/raid0/llm/worktrees/akx-all-27-20261020")          # research worktree with the harness + width_dimension (e46ba5fb2)
H = W / "scripts/benchmark/akx_width_invariance"
CASES = Path("/mnt/raid0/llm/tmp/gpu-queue-20261020/akx-all-26/predicted_fail_list.jsonl")
HDR = Path("/mnt/raid0/llm/llama.cpp-experimental-champref-4348de400-20261006/ggml/include")
SRCS = Path("/mnt/raid0/llm/tmp/fillers-3c4ca599/builds")
MARK = "akm-cdna2-q8-b4-mmvq-route"
RUNS = Path("/mnt/raid0/llm/tmp/v11-runs/akx27")

def builds(stand_in: bool):
    out = {}
    for who, sha in (("parent", PARENT), ("keep", KEEP)):
        d = K / f"gpu-20261021-{sha}"
        if not (d / "SHA256SUMS").exists() or not (d / "bin/llama-server").exists():
            if stand_in: d = V.C_GPU
            else: V.die(5, f"build-missing: {d} (akx-all-27b-builds has not produced it)")
        out[who] = d
    return out

def route_proof(b):
    r = {}
    libs = {w: sorted(p for p in (d / "bin").glob("libggml-hip.so*") if p.is_file() and not p.is_symlink()) for w, d in b.items()}
    r["hip_sha_differs"] = bool(libs["parent"] and libs["keep"] and V.sha256_file(libs["parent"][0]) != V.sha256_file(libs["keep"][0]))
    def has_marker(sha):
        f = SRCS / f"src-{sha}/ggml/src/ggml-cuda/mmvq.cu"
        return f.exists() and MARK in f.read_text(errors="replace")
    def anc(sha):
        s = SRCS / f"src-{sha}"
        if not s.exists(): return None
        return subprocess.run(["git", "-C", str(s), "merge-base", "--is-ancestor", KEEP, "HEAD"], capture_output=True).returncode == 0
    r |= {"keep_src_marker": has_marker(KEEP), "parent_src_marker": has_marker(PARENT), "keep_contains_commit": anc(KEEP), "parent_contains_commit": anc(PARENT)}
    r["proven"] = bool(r["hip_sha_differs"] and r["keep_src_marker"] and r["parent_src_marker"] is False and r["keep_contains_commit"] and r["parent_contains_commit"] is False)
    return r

def link_cmd(b, who, out):
    hdr = HDR if HDR.exists() else SRCS / f"src-{KEEP}/ggml/include"
    return ["/usr/bin/g++", "-O2", "-std=c++17", f"-I{hdr}", str(H / "width_probe.cpp"), f"-L{b}/bin", "-lggml", "-lggml-base", "-lggml-cpu", "-lpthread",
            f"-Wl,-rpath,{b}/bin:/opt/rocm/lib", "-Wl,-rpath-link,/opt/rocm/lib", "-o", str(out / f"width_probe_hip_{who}")]

def probe_cmd(b, who, out):
    return ["/usr/bin/python3", str(H / "run_width_probe.py"), "run", "--backend", "rocm0", "--build-bin", f"{b}/bin", "--binary", str(out / f"width_probe_hip_{who}"),
            "--cases", str(CASES), "--out", str(out / who), "--threads", "8", "--kmax", "9", "--repeats", "3"]

def wd_cmd(out):
    return ["/usr/bin/python3", "-m", "scripts.kernel_rnd.autokernel.loop.width_dimension", "--anchor-table", str(out / "parent/cells.jsonl"),
            "--keep-table", str(out / "keep/cells.jsonl"), "--footprint", "ggml/src/ggml-cuda/mmvq.cu"]

def decide(wd, route):
    c = wd["comparison"]["counts"]
    nontrivial = sum(c.get(k, 0) for k in ("new_failing", "lower_first_fail_k", "higher_first_fail_k", "fixed")) > 0
    verdict = "unchanged" if not nontrivial and c.get("indeterminate", 0) == 0 else ("indeterminate" if c.get("indeterminate", 0) else "changed")
    complete = wd["comparison"].get("coverage_complete", False)
    if nontrivial and complete: dec = "nontrivial_verdict"
    elif verdict == "unchanged" and complete and route.get("proven"): dec = "unchanged_route_proven"
    else: dec = "unchanged_route_unproven"
    return {"decision": dec, "counts": c, "coverage_complete": complete, "route": route, "done_criterion_met": dec in ("nontrivial_verdict", "unchanged_route_proven")}

def selftest():
    z = {"new_failing": 0, "lower_first_fail_k": 0, "higher_first_fail_k": 0, "fixed": 0, "indeterminate": 0}
    wd = lambda **k: {"comparison": {"counts": z | k, "coverage_complete": True}}
    assert decide(wd(new_failing=3), {"proven": False})["decision"] == "nontrivial_verdict"
    assert decide(wd(), {"proven": True})["decision"] == "unchanged_route_proven"
    assert decide(wd(), {"proven": False})["decision"] == "unchanged_route_unproven"
    assert decide(wd(lower_first_fail_k=1), {"proven": False})["done_criterion_met"]
    print("akx27 selftest OK"); return 0

def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true"); g.add_argument("--execute", action="store_true"); g.add_argument("--selftest", action="store_true"); g.add_argument("--is-done", action="store_true")
    ap.add_argument("--run-dir"); ap.add_argument("--stand-in", action="store_true")
    a = ap.parse_args()
    if a.selftest: return selftest()
    if a.is_done:   # --complete-cmd for filler_run2.sh: rc 0 once some real run reached the done criterion
        import glob
        return 0 if any(json.load(open(f)).get("done_criterion_met") for f in glob.glob(str(RUNS / "20*/DECISION.json"))) else 1
    try:
        out = Path(a.run_dir) if a.run_dir else RUNS / (("dry-" if not a.execute else "") + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
        out.mkdir(parents=True, exist_ok=True)
        log = out / "driver.log"
        b = builds(a.stand_in and not a.execute)
        for need in (W, H / "run_width_probe.py", H / "width_probe.cpp", CASES):
            if not Path(need).exists(): V.die(3, f"REFUSE: {need} missing")
        lk = {w: V.linkage_proof(d) for w, d in b.items()}
        if any(x["rc"] for x in lk.values()): V.die(7, f"linkage proof failed {lk}")
        route = route_proof(b)
        V.say(f"builds parent={b['parent']} keep={b['keep']} route={route}", log)
        plan = {"link": [link_cmd(b[w], w, out) for w in b], "probe": [probe_cmd(b[w], w, out) for w in b], "wd": wd_cmd(out), "cwd": str(W)}
        wdh = subprocess.run(["/usr/bin/python3", "-m", "scripts.kernel_rnd.autokernel.loop.width_dimension", "--help"], cwd=W, capture_output=True, text=True)
        plan["width_dimension_importable"] = wdh.returncode == 0
        (out / "plan.json").write_text(json.dumps(plan, indent=1))
        if not a.execute:
            bad = V.gpu_preflight(type("C", (), {"say": staticmethod(lambda m: V.say(m, log))})(), ports=())
            V.say(f"dry-run ok: plan.json written; width_dimension importable={plan['width_dimension_importable']}; preflight would refuse={bad}", log)
            return 0 if plan["width_dimension_importable"] else 7
        if not (os.environ.get("FILLER_ID") or os.environ.get("AKX27_INSIDE_CLAIM") == "1"):
            V.die(3, "REFUSE: --execute only inside the exclusive GPU claim (filler_run2.sh --gpu-quiet exclusive, or AKX27_INSIDE_CLAIM=1 under region-lock --gpu-quiet exclusive)")
        ctx = type("C", (), {"say": staticmethod(lambda m: V.say(m, log))})()
        bad = V.gpu_preflight(ctx, ports=())
        if bad: V.die(6, f"REFUSE preflight: {bad}")
        stop, dl = os.environ.get("FILLER_STOPFILE"), int(os.environ.get("FILLER_DEADLINE", "0")) or None
        for w in b:
            V.say(f"link probe {w}", log)
            r = subprocess.run(plan["link"][list(b).index(w)], capture_output=True, text=True)
            if r.returncode: V.die(7, f"probe link failed {w}: {r.stderr[-300:]}")
        for i, w in enumerate(b):
            if (stop and os.path.exists(stop)) or (dl and time.time() > dl - 700): V.die(0, f"stop/deadline before {w}; resume by re-granting (per-build output dirs resume)")
            V.say(f"probe {w} (~5 min/build)", log)
            p = subprocess.Popen(plan["probe"][i], stdout=open(out / f"{w}.log", "w"), stderr=subprocess.STDOUT)
            res = V.Residency(p.pid, b[w])
            try: rc = p.wait(2400)
            except subprocess.TimeoutExpired: V.kill_verified(p, log); rc = 124
            V.say(f"probe {w} rc={rc} (probe parent proc residency is host-side only; the HIP-run residency is the harness per-id evidence)", log)
            res.stop()
            if rc: V.die(7, f"probe {w} rc={rc}")
        r = subprocess.run(plan["wd"], cwd=W, capture_output=True, text=True)
        (out / "width_dimension.json").write_text(r.stdout); (out / "width_dimension.err").write_text(r.stderr)
        if r.returncode: V.die(7, f"width_dimension rc={r.returncode}")
        d = decide(json.loads(r.stdout), route) | {"builds": {k: str(v) for k, v in b.items()}, "linkage": lk, "decided_at": V.now_iso()}
        (out / "DECISION.json").write_text(json.dumps(d, indent=1))
        V.say(f"decision={d['decision']}", log)
        return 0
    except V.Refuse as e:
        print(e); return e.rc

if __name__ == "__main__":
    sys.exit(main())
