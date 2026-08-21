#!/usr/bin/env python
"""CT-1 A/B: embedded template (arm0) vs epyc-qwen3x-v1 (arm1), CPU, per-suite.

Design (handoffs/active/qwen-chat-template-evaluation.md CT-1/CT-1a, 2026-08-21):
- Model: Qwen3.6-35B-A3B-MTP-Q8_0 (frontdoor's model), CPU, canonical recipe
  (taskset 0-95 + numactl --interleave=all, OMP spread/cores/active/false,
  GGML_IQK=1, --no-mmap), identical both arms; ONLY the template differs.
- 4 suites x 40 pinned questions (seed 42), same rows both arms.
- Production sampling: temp 0.6, top_p 0.95, top_k 20, seed 42;
  chat_template_kwargs.enable_thinking=false (stack posture).
- Scored with the orchestrator's own debug_scorer (never a hand-rolled one).
- Per-question JSONL written incrementally -> any interruption is a drain point.
"""
import json, os, random, signal, subprocess, sys, time, urllib.request, ast

ROOT = "/workspace/tmp/ct1b"
POOL = "/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.jsonl"
MODEL = "/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf"
SERVER = "/mnt/raid0/llm/llama.cpp/build/bin/llama-server"
TEMPLATE = "/workspace/artifacts/chat-templates/epyc-qwen3x-v1/chat_template_terse_arm2.jinja"
ARM0_RESULTS = "/workspace/tmp/ct1-ab/results_arm0.jsonl"
PORT = 8990
SUITES = {"math": 40, "mmlu_pro": 40, "gpqa_diamond": 40, "cruxeval": 40}
MAXTOK = 900

sys.path.insert(0, "/workspace/repos/epyc-orchestrator")
from scripts.benchmark.debug_scorer import score_answer  # the tower's scorer

os.makedirs(ROOT, exist_ok=True)

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(f"{ROOT}/runner.log", "a") as f:
        f.write(line + "\n")

# ---- pinned question draw (identical both arms) ----
rows = {s: [] for s in SUITES}
with open(POOL) as f:
    next(f)
    for l in f:
        d = json.loads(l)
        if d.get("suite") in rows:
            rows[d["suite"]].append(d)
picked = {}
for s, n in SUITES.items():
    rng = random.Random(42)
    picked[s] = rng.sample(rows[s], n)
with open(f"{ROOT}/pinned_questions.json", "w") as f:
    json.dump({s: [q["id"] for q in qs] for s, qs in picked.items()}, f, indent=1)
log(f"pinned {sum(len(v) for v in picked.values())} questions across {len(picked)} suites")

CANON_ENV = dict(os.environ, OMP_PROC_BIND="spread", OMP_PLACES="cores",
                 OMP_WAIT_POLICY="active", OMP_DYNAMIC="false", GGML_IQK="1")
PREFIX = ["taskset", "-c", "0-95", "numactl", "--interleave=all"]

def launch(arm):
    cmd = PREFIX + [SERVER, "-m", MODEL, "--jinja", "-t", "96", "-c", "8192",
                    "--no-mmap", "-fa", "on", "--host", "127.0.0.1", "--port", str(PORT)]
    if arm == 1:
        cmd += ["--chat-template-file", TEMPLATE]
    lf = open(f"{ROOT}/server_arm{arm}.log", "w")
    p = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, env=CANON_ENV)
    log(f"arm{arm} server pid {p.pid} launching (no-mmap load ~1-2 min)")
    deadline = time.time() + 900
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=3)
            log(f"arm{arm} server healthy")
            return p
        except Exception:
            if p.poll() is not None:
                raise RuntimeError(f"arm{arm} server died at load; see server_arm{arm}.log")
            time.sleep(5)
    raise RuntimeError("health timeout")

def stop(p):
    p.send_signal(signal.SIGTERM)
    try:
        p.wait(timeout=30)
    except subprocess.TimeoutExpired:
        p.kill(); p.wait(timeout=15)
    assert p.poll() is not None
    log(f"server pid {p.pid} dead, verified")

def ask(prompt):
    body = {"model": "auto",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.6, "top_p": 0.95, "top_k": 20, "seed": 42,
            "max_tokens": MAXTOK,
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    r = json.loads(urllib.request.urlopen(req, timeout=600).read())
    dt = time.time() - t0
    ch = r["choices"][0]
    content = ch["message"].get("content") or ""
    usage = r.get("usage", {})
    return content, usage.get("completion_tokens"), dt, ch.get("finish_reason")

def parse_cfg(s):
    if not s or s in ("{}", "[]", "None"):
        return {}
    try:
        v = ast.literal_eval(s)
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}

def run_arm(arm):
    out = f"{ROOT}/results_arm{arm}.jsonl"
    done = set()
    if os.path.exists(out):
        for l in open(out):
            try: done.add(json.loads(l)["id"])
            except Exception: pass
    p = launch(arm)
    try:
        for s, qs in picked.items():
            for i, q in enumerate(qs):
                if q["id"] in done:
                    continue
                try:
                    ans, ctok, dt, fin = ask(q["prompt"])
                    ok = bool(score_answer(ans, q["expected"], q["scoring_method"],
                                           parse_cfg(q.get("scoring_config"))))
                    err = None
                except Exception as e:
                    ans, ctok, dt, fin, ok, err = "", None, None, None, False, str(e)[:200]
                rec = {"id": q["id"], "suite": s, "arm": arm, "correct": ok,
                       "completion_tokens": ctok, "latency_s": round(dt, 2) if dt else None,
                       "finish_reason": fin, "error": err,
                       "answer_tail": ans[-300:]}
                with open(out, "a") as f:
                    f.write(json.dumps(rec) + "\n")
                if (i + 1) % 10 == 0:
                    log(f"arm{arm} {s} {i+1}/{len(qs)}")
        log(f"arm{arm} complete")
    finally:
        stop(p)

def summarize():
    res = {}
    for arm in (0, 1):
        for l in open(f"{ROOT}/results_arm{arm}.jsonl"):
            d = json.loads(l)
            res.setdefault((d["suite"], arm), []).append(d)
    summary = {}
    for s in SUITES:
        row = {}
        for arm in (0, 1):
            rs = res.get((s, arm), [])
            n = len(rs); c = sum(r["correct"] for r in rs)
            toks = [r["completion_tokens"] for r in rs if r["completion_tokens"]]
            trunc = sum(1 for r in rs if r.get("finish_reason") == "length")
            errs = sum(1 for r in rs if r.get("error"))
            row[f"arm{arm}"] = {"n": n, "correct": c,
                                "acc": round(c / n, 4) if n else None,
                                "mean_tokens": round(sum(toks) / len(toks), 1) if toks else None,
                                "truncated": trunc, "errors": errs}
        # paired flips over the shared pinned ids
        a0 = {r["id"]: r["correct"] for r in res.get((s, 0), [])}
        a1 = {r["id"]: r["correct"] for r in res.get((s, 1), [])}
        both = set(a0) & set(a1)
        row["flips_01"] = sum(1 for i in both if a0[i] and not a1[i])
        row["flips_10"] = sum(1 for i in both if not a0[i] and a1[i])
        summary[s] = row
    with open(f"{ROOT}/summary.json", "w") as f:
        json.dump(summary, f, indent=1)
    log("SUMMARY: " + json.dumps(summary))

def summarize_vs_arm0():
    import shutil
    shutil.copy(ARM0_RESULTS, f"{ROOT}/results_arm0.jsonl")
    summarize()

if __name__ == "__main__":
    log("=== CT-1b (terseness arm 2 vs existing arm 0) start ===")
    run_arm(1)          # arm index 1 slot reused; template above is the ARM-2 terse build
    summarize_vs_arm0()
    log("=== CT-1b done ===")
