#!/usr/bin/env python
"""CT-5 option (c) measurement — operator-authorized 2026-08-21 ("hold (a), authorise (c) as a measurement").

Does Qwen3.8-27B's native think channel behave like A1/A4 did (non-termination tail), or does
thinking-ON pay on this model? Paired flag-flip on ONE GPU server, embedded (stock-config) template:
  T0: chat_template_kwargs {enable_thinking: false}                  (production posture)
  T1: chat_template_kwargs {enable_thinking: true, reasoning_effort: "medium"}  (medium = zero-token
      default; deliberately avoids the xhigh 209-char injection)
Suite: gpqa_diamond_cot, 60 pinned (seed 42). Production sampling. max_tokens 4096 both arms
(v9 has NO --reasoning-budget flag — recorded as a finding; the cited lever does not exist here).
Captures: accuracy, completion tokens, reasoning_content length, non-termination (finish=length),
latency. Scored by orchestrator debug_scorer. Incremental JSONL.
"""
import json, os, random, signal, subprocess, sys, time, urllib.request

ROOT = "/workspace/tmp/ct5c-16k"
POOL = "/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.jsonl"
MODEL = "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf"
SERVER = "/mnt/raid0/llm/llama.cpp/build-hip/bin/llama-server"
LIBDIR = "/mnt/raid0/llm/llama.cpp/build-hip/bin"
PORT = 8991
N = 60
MAXTOK = 16384

sys.path.insert(0, "/workspace/repos/epyc-orchestrator")
from scripts.benchmark.debug_scorer import score_answer

os.makedirs(ROOT, exist_ok=True)

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(f"{ROOT}/runner.log", "a") as f:
        f.write(line + "\n")

qs = []
with open(POOL) as f:
    next(f)
    for l in f:
        d = json.loads(l)
        if d.get("suite") == "gpqa_diamond_cot":
            qs.append(d)
picked = random.Random(42).sample(qs, N)
with open(f"{ROOT}/pinned_questions.json", "w") as f:
    json.dump([q["id"] for q in picked], f, indent=1)
log(f"pinned {len(picked)} gpqa_diamond_cot questions")

ENV = dict(os.environ, LD_LIBRARY_PATH=LIBDIR)
CMD = ["taskset", "-c", "184-191", SERVER, "-m", MODEL,
       "--device", "ROCm0", "-ngl", "999", "-fa", "on",
       "--spec-type", "draft-mtp", "--spec-draft-n-max", "8",
       "-t", "8", "-tb", "8", "-b", "2048", "-ub", "2048",
       "-ctk", "f16", "-ctv", "f16", "-c", "32768",
       "--jinja", "--host", "127.0.0.1", "--port", str(PORT)]

def launch():
    lf = open(f"{ROOT}/server.log", "w")
    p = subprocess.Popen(CMD, stdout=lf, stderr=subprocess.STDOUT, env=ENV)
    log(f"GPU server pid {p.pid} launching")
    deadline = time.time() + 900
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=3)
            log("GPU server healthy")
            return p
        except Exception:
            if p.poll() is not None:
                raise RuntimeError("server died at load; see server.log")
            time.sleep(5)
    raise RuntimeError("health timeout")

def vram_sample(tag):
    try:
        out = subprocess.run(["rocm-smi", "--showmemuse"], capture_output=True, text=True, timeout=20).stdout
        for line in out.splitlines():
            if "VRAM%" in line:
                log(f"VRAM DURING {tag}: {line.strip()}")
                return
    except Exception as e:
        log(f"vram sample failed: {e}")

def ask(prompt, ctk):
    body = {"model": "auto", "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.6, "top_p": 0.95, "top_k": 20, "seed": 42,
            "max_tokens": MAXTOK, "chat_template_kwargs": ctk}
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    r = json.loads(urllib.request.urlopen(req, timeout=1200).read())
    dt = time.time() - t0
    ch = r["choices"][0]
    msg = ch["message"]
    return (msg.get("content") or "", msg.get("reasoning_content") or "",
            r.get("usage", {}).get("completion_tokens"), dt, ch.get("finish_reason"))

ARMS = {"T0": {"enable_thinking": False},
        "T1": {"enable_thinking": True, "reasoning_effort": "medium"}}

def main():
    out = f"{ROOT}/results.jsonl"
    done = set()
    if os.path.exists(out):
        for l in open(out):
            try:
                d = json.loads(l); done.add((d["id"], d["arm"]))
            except Exception: pass
    p = launch()
    sampled_vram = False
    try:
        for i, q in enumerate(picked):
            for arm, ctk in ARMS.items():
                if (q["id"], arm) in done: continue
                try:
                    ans, think, ctok, dt, fin = ask(q["prompt"], ctk)
                    ok = bool(score_answer(ans, q["expected"], q["scoring_method"], {}))
                    err = None
                except Exception as e:
                    ans, think, ctok, dt, fin, ok, err = "", "", None, None, None, False, str(e)[:200]
                rec = {"id": q["id"], "arm": arm, "correct": ok,
                       "completion_tokens": ctok, "think_chars": len(think),
                       "latency_s": round(dt, 1) if dt else None,
                       "finish_reason": fin, "error": err, "answer_tail": ans[-200:]}
                with open(out, "a") as f:
                    f.write(json.dumps(rec) + "\n")
                if not sampled_vram and not err:
                    vram_sample("first completed request"); sampled_vram = True
            if (i + 1) % 10 == 0:
                log(f"{i+1}/{len(picked)} questions (both arms)")
        log("all questions complete")
    finally:
        p.send_signal(signal.SIGTERM)
        try: p.wait(timeout=30)
        except subprocess.TimeoutExpired: p.kill(); p.wait(timeout=15)
        log(f"server pid {p.pid} dead, verified")

    res = {"T0": [], "T1": []}
    for l in open(out):
        d = json.loads(l); res[d["arm"]].append(d)
    summary = {}
    for arm, rs in res.items():
        n = len(rs); c = sum(r["correct"] for r in rs)
        toks = [r["completion_tokens"] for r in rs if r["completion_tokens"]]
        summary[arm] = {"n": n, "correct": c, "acc": round(c / n, 4) if n else None,
                        "mean_tokens": round(sum(toks) / len(toks), 1) if toks else None,
                        "nonterm": sum(1 for r in rs if r.get("finish_reason") == "length"),
                        "errors": sum(1 for r in rs if r.get("error")),
                        "mean_think_chars": round(sum(r["think_chars"] for r in rs) / n, 0) if n else None,
                        "tokens_per_solved": round(sum(toks) / c, 1) if c and toks else None}
    a0 = {r["id"]: r["correct"] for r in res["T0"]}
    a1 = {r["id"]: r["correct"] for r in res["T1"]}
    both = set(a0) & set(a1)
    summary["flips_T0only"] = sum(1 for i in both if a0[i] and not a1[i])
    summary["flips_T1only"] = sum(1 for i in both if not a0[i] and a1[i])
    with open(f"{ROOT}/summary.json", "w") as f:
        json.dump(summary, f, indent=1)
    log("SUMMARY: " + json.dumps(summary))

if __name__ == "__main__":
    log("=== CT-5(c) GPU measurement start ===")
    main()
    log("=== CT-5(c) done ===")
