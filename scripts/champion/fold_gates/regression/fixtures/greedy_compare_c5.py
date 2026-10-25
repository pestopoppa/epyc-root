#!/usr/bin/env python3
"""greedy_compare_c5.py -- Q38FN greedy output identity across fold arms, with PER-ARM ENV OPS (C5 fold, CH-31).

Derived from /mnt/raid0/llm/tmp/fold-allkeeps-20261004/greedy_compare.py (same frozen launch, same prompts, same
request body, same near-tie classifier, same process discipline). Why a variant: the frozen Q38FN launch
(q38fn-cpu-t48-mtp-d4.launch.json) sets GGML_FUSED_DECODE_OFF=1 in its launch_env, so the original cannot test
what C5 changes -- the DEFAULT env (no OFF knob). Here each arm may edit the launch env:

  --arm NAME=BUILD_DIR[@OPS]    OPS = comma list of  -KEY (remove KEY)  |  KEY=VAL (set KEY)
  e.g. --arm CHAMP=/k/cpu-...-c3                                    frozen env as-is (OFF=1: the measured graph path)
       --arm C5DEF=/k/cpu-...-c5@-GGML_FUSED_DECODE_OFF             default env (neither knob)
       --arm C5ON=/k/cpu-...-c5@-GGML_FUSED_DECODE_OFF,GGML_FUSED_DECODE_ON=1   fused opt-in (known defective)

Per arm: ONE llama-server on the frozen argv (binary + LD_LIBRARY_PATH rebound to the arm's build, port moved, MTP
drafter stripped as in the original), optionally re-pinned with --cpus / --threads (rewrites `taskset -c` and
-t/-tb; every arm gets the same rewrite, so identity across arms stays meaningful). Env proof: the GGML_FUSED_* keys
of /proc/<server pid>/environ are recorded and must equal the arm's requested env (else REFUSED rc 3: the op did not
apply). Per prompt it records the tokens, top-2 probs and the server's timings.predicted_per_token_ms (descriptive).

--expect-identical A,B   verdict: each listed arm must be IDENTICAL to the reference (first --arm) on every prompt;
                         any divergence (near-tie or not) is FAIL -- the C5 change does not touch the graph path, so
                         no rounding-order flip is expected.
--label NAME=TEXT        printed with that arm's verdict (e.g. KNOWN-DEFECTIVE: no correctness claim).
--tmp-watch DIR          CH-24 runtime half: list files under DIR whose mtime is inside each arm's server lifetime;
                         foreign Flash-Next processes alive at the time are recorded for attribution.
--smoke-arm NAME         smoke verdict for NAME vs the reference: completed every prompt, confirmed dead, zero files
                         in --tmp-watch during its lifetime, and fused engagement shown (no "fused decode disabled"
                         refusal in its server log AND predicted_per_token_ms >= --engage-ratio x the reference's).
Exit: 0 pass, 1 identity/smoke FAIL, 3 refused, 4 a server not confirmed dead, 5 smoke INCONCLUSIVE (engagement not shown).

usage: greedy_compare_c5.py --arm NAME=BUILD[@OPS] [--arm ...] --out DIR {--dry-run|--execute} [options]
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
import urllib.request
from pathlib import Path

Q38 = Path("/mnt/raid0/llm/autokernel/campaigns/ak-q38fn-cpu-decode-20261003/inputs")
PROMPTS = [
    ("p1", "The three main reasons the EPYC memory hierarchy has an L3 cache are"),
    ("p2", "def fibonacci(n):\n    \"\"\"Return the n-th Fibonacci number iteratively.\"\"\"\n"),
]
DRAFT_FLAGS_WITH_ARG = {"-md", "-ngld", "--spec-type", "--spec-draft-n-max", "--device-draft", "--draft-p-min"}
REFUSAL_LINE = "fused decode disabled for this model"


def parse_arm(s: str) -> tuple[str, Path, list[str]]:
    name, rest = s.split("=", 1)
    build, _, ops = rest.partition("@")
    return name, Path(build), [o for o in ops.split(",") if o]


def server_argv(build: Path, ops: list[str], port: int, cpus: str | None, threads: int | None) -> tuple[list[str], dict]:
    launch = json.loads((Q38 / "q38fn-cpu-t48-mtp-d4.launch.json").read_text())
    argv, out, skip = launch["argv"], [], False
    for tok in argv:
        if skip:
            skip = False; continue
        if tok in DRAFT_FLAGS_WITH_ARG:
            skip = True; continue
        out.append(tok)
    out = [str(build / "bin/llama-server") if t.endswith("/bin/llama-server") else t for t in out]
    out[out.index("--port") + 1] = str(port)
    if cpus:
        out[out.index("taskset") + 2] = cpus          # taskset -c <list>
    if threads:
        for f in ("-t", "-tb"):
            out[out.index(f) + 1] = str(threads)
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": os.environ.get("HOME", "/home/node")}
    env.update(launch["launch_env"]); env["LD_LIBRARY_PATH"] = str(build / "bin")
    for op in ops:
        if op.startswith("-"):
            env.pop(op[1:], None)
        else:
            k, v = op.split("=", 1); env[k] = v
    return out, env


def frozen_prompt() -> list[int]:
    import ast
    p = json.loads((Q38 / "q38fn-decode.prompt-manifest.json").read_text())["prompts"][0]
    req = p["request"] if isinstance(p["request"], dict) else ast.literal_eval(p["request"])
    return list(req["prompt"])


def post(port: int, body: dict) -> dict:
    r = urllib.request.Request(f"http://127.0.0.1:{port}/completion", data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=1800) as f:
        return json.loads(f.read())


def fused_env(d: dict) -> dict:
    return {k: v for k, v in d.items() if k.startswith("GGML_FUSED_")}


def proc_env(pid: int) -> dict:
    raw = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
    return dict(x.decode(errors="replace").split("=", 1) for x in raw if b"=" in x)


def foreign_flash_next(own: int) -> list[str]:
    # read-only attribution aid: other processes whose argv names the Flash-Next model (never signalled)
    r = subprocess.run(["ps", "-eo", "pid=,args="], capture_output=True, text=True)
    return [l.strip()[:200] for l in r.stdout.splitlines()
            if "Flash-Next" in l and l.split(None, 1)[0] != str(own) and "greedy_compare" not in l]


def tmp_new(d: Path, t0: float, t1: float) -> list[str]:
    if not d.is_dir():
        return []
    return sorted(str(p) for p in d.iterdir() if p.is_file() and t0 <= p.stat().st_mtime <= t1)


def run_arm(name: str, build: Path, ops: list[str], a, prompts) -> dict:
    argv, env = server_argv(build, ops, a.port, a.cpus, a.threads)
    logp = a.out / f"server-{name}.log"
    log = open(logp, "w")
    t_start = time.time() - 1.0
    proc = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT)
    res = {"arm": name, "build": str(build), "env_ops": ops, "pid": proc.pid, "argv": argv,
           "requested_fused_env": fused_env(env), "prompts": {}, "completed": False}
    try:
        t0 = time.time()
        while time.time() - t0 < 900:
            if proc.poll() is not None:
                raise RuntimeError(f"server exited rc={proc.returncode}")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{a.port}/health", timeout=2) as f:
                    if f.status == 200: break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError("server not healthy within 900 s")
        res["load_s"] = round(time.time() - t0, 1)
        res["proc_fused_env"] = fused_env(proc_env(proc.pid))
        res["foreign_flash_next"] = foreign_flash_next(proc.pid)
        for pid_, prompt in prompts:
            body = {"prompt": prompt, "n_predict": a.n_predict, "temperature": 0, "top_k": 1, "seed": 1,
                    "cache_prompt": False, "ignore_eos": True, "return_tokens": True, "n_probs": 2}
            r = post(a.port, body)
            probs = [[(t.get("id"), t.get("prob", t.get("logprob"))) for t in (p.get("top_probs") or p.get("probs") or [])]
                     for p in r.get("completion_probabilities", [])]
            res["prompts"][pid_] = {"tokens": r.get("tokens"), "top2": probs, "text": r.get("content", "")[:200],
                                    "predicted_per_token_ms": (r.get("timings") or {}).get("predicted_per_token_ms")}
        res["completed"] = True
    except Exception as e:  # recorded, never swallowed silently: the verdict reads `completed` and `error`
        res["error"] = f"{type(e).__name__}: {e}"
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(20)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait(10)
        dead = subprocess.run(["ps", "-p", str(proc.pid)], capture_output=True).returncode != 0
        res["confirmed_dead"] = dead
        res["rc"] = proc.returncode
        log.close()
        if a.tmp_watch:
            res["tmp_new_files"] = tmp_new(Path(a.tmp_watch), t_start, time.time() + 1.0)
        res["refusal_logged"] = REFUSAL_LINE in logp.read_text(errors="replace")
    return res


def classify(ref: dict, other: dict, margin: float) -> dict:
    v = {}
    for k, r in ref["prompts"].items():
        a, b = r["tokens"] or [], (other["prompts"].get(k, {}).get("tokens") or [])
        i = next((j for j in range(min(len(a), len(b))) if a[j] != b[j]), None)
        if i is None and len(a) == len(b):
            v[k] = "IDENTICAL"; continue
        if i is None:
            v[k] = f"LENGTH {len(a)} vs {len(b)}"; continue
        top = r["top2"][i] if i < len(r["top2"]) else []
        m = (top[0][1] - top[1][1]) if len(top) >= 2 and None not in (top[0][1], top[1][1]) else None
        tie = m is not None and m < margin
        v[k] = f"DIVERGES at token {i}: ref margin {m if m is None else round(m, 4)} -> {'NEAR-TIE' if tie else 'NOT-NEAR-TIE'}"
    return v


def med_ms(arm: dict) -> float | None:
    xs = sorted(p["predicted_per_token_ms"] for p in arm["prompts"].values() if p.get("predicted_per_token_ms"))
    return xs[len(xs) // 2] if xs else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--tie-margin", type=float, default=0.02)
    ap.add_argument("--port", type=int, default=18761)
    ap.add_argument("--cpus"); ap.add_argument("--threads", type=int)
    ap.add_argument("--n-predict", type=int, default=128)
    ap.add_argument("--prompts", default="p1,p2,p3")
    ap.add_argument("--expect-identical", default="")
    ap.add_argument("--label", action="append", default=[])
    ap.add_argument("--tmp-watch")
    ap.add_argument("--smoke-arm")
    ap.add_argument("--engage-ratio", type=float, default=3.0)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true"); g.add_argument("--execute", action="store_true")
    a = ap.parse_args()
    arms = [parse_arm(s) for s in a.arm]
    labels = dict(x.split("=", 1) for x in a.label)
    want = [p for p in a.prompts.split(",") if p]
    allp = PROMPTS + [("p3", frozen_prompt())]
    prompts = [(k, v) for k, v in allp if k in want]
    if len(prompts) != len(want):
        print(f"REFUSED: unknown prompt id in {a.prompts}"); return 3
    for n, b, ops in arms:
        if not (b / "bin/llama-server").is_file():
            print(f"REFUSED: arm {n}: no llama-server in {b}"); return 3
        argv, env = server_argv(b, ops, a.port, a.cpus, a.threads)
        print(f"arm {n}: {' '.join(argv[:8])} ... port {a.port} (drafter stripped) LD_LIBRARY_PATH={env['LD_LIBRARY_PATH']} "
              f"fused-env={fused_env(env) or '{}'}{'  [' + labels[n] + ']' if n in labels else ''}")
    print(f"prompts: {','.join(k for k, _ in prompts)} (p1,p2 10-03 XFER-4; p3 frozen q38fn-decode-p01, {len(frozen_prompt())} prompt tokens); "
          f"n_predict {a.n_predict}, n_probs 2; reference arm {arms[0][0]}")
    if a.dry_run:
        print(f"DRY RUN   would launch {len(arms)} servers sequentially; nothing launched"); return 0
    a.out.mkdir(parents=True, exist_ok=True)
    results = [run_arm(n, b, ops, a, prompts) for n, b, ops in arms]
    rc = 0
    for r in results:
        if r.get("proc_fused_env") is not None and r["proc_fused_env"] != r["requested_fused_env"]:
            print(f"REFUSED: arm {r['arm']}: server env {r['proc_fused_env']} != requested {r['requested_fused_env']}"); rc = 3
    ref = results[0]
    verdict = {o["arm"]: classify(ref, o, a.tie_margin) for o in results[1:] if o["completed"] and ref["completed"]}
    for r in results:
        if not r["completed"]:
            print(f"{r['arm']}: DID NOT COMPLETE ({r.get('error')}) rc={r.get('rc')}{'  [' + labels[r['arm']] + ']' if r['arm'] in labels else ''}")
    for arm, v in verdict.items():
        print(f"{arm} vs {ref['arm']}: " + "; ".join(f"{k}: {s}" for k, s in v.items())
              + (f"  [{labels[arm]}]" if arm in labels else ""))
    ident = {}
    for arm in [x for x in a.expect_identical.split(",") if x]:
        ok = arm in verdict and all(s == "IDENTICAL" for s in verdict[arm].values()) and len(verdict[arm]) == len(prompts)
        ident[arm] = ok
        print(f"IDENTITY {arm} == {ref['arm']}: {'PASS' if ok else 'FAIL'}")
        if not ok and rc == 0:
            rc = 1
    smoke = None
    if a.smoke_arm:
        s = next((r for r in results if r["arm"] == a.smoke_arm), None)
        if s is None:
            print(f"REFUSED: smoke arm {a.smoke_arm} not among the arms"); return 3
        ms_s, ms_r = med_ms(s), med_ms(ref)
        ratio = (ms_s / ms_r) if ms_s and ms_r else None
        engaged = (not s["refusal_logged"]) and ratio is not None and ratio >= a.engage_ratio
        wrote = s.get("tmp_new_files") or []
        if not s["completed"] or not s["confirmed_dead"] or wrote:
            sv = "FAIL"
        elif not engaged:
            sv = "INCONCLUSIVE"
        else:
            sv = "PASS"
        smoke = {"arm": s["arm"], "completed": s["completed"], "confirmed_dead": s["confirmed_dead"],
                 "tmp_new_files": wrote, "foreign_flash_next": s.get("foreign_flash_next"),
                 "refusal_logged": s["refusal_logged"], "per_token_ms_median": ms_s, "ref_per_token_ms_median": ms_r,
                 "ratio": ratio, "engaged": engaged, "verdict": sv,
                 "claim": "runtime smoke of the KNOWN-DEFECTIVE fused opt-in path: it runs and writes nothing under "
                          "the watched dir; NO correctness claim"}
        print(f"SMOKE {s['arm']}: {sv}  completed={s['completed']} dead={s['confirmed_dead']} tmp_new_files={len(wrote)} "
              f"refusal_logged={s['refusal_logged']} per_token_ms {ms_s} vs ref {ms_r} (ratio {ratio if ratio is None else round(ratio, 2)}, "
              f"engaged={engaged})  [{labels.get(s['arm'], 'no correctness claim')}]")
        if wrote and s.get("foreign_flash_next"):
            print(f"SMOKE note: foreign Flash-Next processes were alive (attribution open): {s['foreign_flash_next']}")
        if rc == 0:
            rc = {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 5}[sv]
    (a.out / "greedy.json").write_text(json.dumps({"schema": "epyc.fold.greedy_compare_c5.v1", "results": results,
                                                   "verdict_vs_" + ref["arm"]: verdict, "identity": ident,
                                                   "smoke": smoke, "labels": labels}, indent=1))
    if not all(r["confirmed_dead"] for r in results):
        return 4
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
