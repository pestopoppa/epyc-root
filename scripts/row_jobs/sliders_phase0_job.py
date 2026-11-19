#!/usr/bin/env python3
"""SLIDERS Phase 0 (handoff knowledge-pipelines.md 0.3, operator 2026-11-07 'evaluate now, low-priority filler'), keeper custody.
Replacement bounded corpus (FinQ100 is not shipped and EDGAR returns 403 to default clients): FB5 = 5 FinanceBench open-source questions, one
10-K PDF each (pins: /mnt/raid0/llm/datasets/financebench-20261109/fb5_pins.json), PDFs -> markdown by ODL local 2.5.0 (private env, java 17 by explicit path),
SLIDERS upstream b66094d from /mnt/raid0/llm/scratch/sliders (read-only, PYTHONPATH), venv /mnt/raid0/llm/venvs/sliders-20261109, local
Qwen3-Coder-30B-A3B-Instruct Q4_K_M on the production-consolidated-v10 CPU llama-server (kernel store). Prompts unmodified.
Units = the 5 questions in pinned order, resumable per question (state/<qid>.json), per-question timeout QTIMEOUT_S; 2 consecutive non-timeout failures
(API plumbing) stop the job rc=1 for a fix + republish (not a scientific verdict). Records: out/results.jsonl. Verdict 0.4 is written by the owner from the final record."""
import hashlib, json, os, pathlib, signal, subprocess, sys, time, urllib.request

S = pathlib.Path("/mnt/raid0/llm/tmp/sliders-phase0-fb5-coder30b-r2-20261109")
OUT, WORK, STATE = S / "out", S / "work", S / "out" / "state"
PINS = json.loads(pathlib.Path("/mnt/raid0/llm/datasets/financebench-20261109/fb5_pins.json").read_text())["questions"]
PDFDIR = pathlib.Path("/mnt/raid0/llm/datasets/financebench-20261109/pdfs")
KDIR = "/mnt/raid0/llm/kernels/production/cpu"
BIN = KDIR + "/llama-server"
MODEL = "/mnt/raid0/llm/models/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"
MODEL_SHA = "fadc3e5f8d42bf7e894a785b05082e47daee4df26680389817e2093056f088ad"
VENV_PY = "/mnt/raid0/llm/venvs/sliders-20261109/bin/python"
SLIDERS_SRC = "/mnt/raid0/llm/scratch/sliders"
CFG = SLIDERS_SRC + "/configs/default_sliders.yaml"
COMMON = pathlib.Path("/mnt/raid0/llm/tmp/parser-quality-common-20261109")
WHEELS = "/mnt/raid0/llm/tmp/codex-pip05-lightonocr-20261029"
ODLPY = "/home/node/.local/share/uv/python/cpython-3.12.15-linux-x86_64-gnu/bin/python3.12"
PORT = 19472
QTIMEOUT_S = 9000
CPUS = os.environ["FILLER_CPUS"]
THR = os.environ.get("FILLER_THREADS", "24")
STOPFILE = os.environ.get("FILLER_STOPFILE", "")
DEADLINE = float(os.environ.get("FILLER_DEADLINE", "0")) or None
PIDFILE = os.environ.get("FILLER_PIDFILE", "")


def now(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
def log(m): print(now(), m, flush=True)
def stopping(): return bool((STOPFILE and os.path.exists(STOPFILE)) or (DEADLINE and time.time() >= DEADLINE))


def record(rec):
    with open(OUT / "results.jsonl", "a") as f:
        f.write(json.dumps(dict(rec, ts=now()), sort_keys=True) + "\n"); f.flush(); os.fsync(f.fileno())


def spawn(cmd, env, logname, **kw):
    lf = open(WORK / logname, "ab"); kw.setdefault("stdout", lf)
    p = subprocess.Popen(cmd, env=env, stderr=lf, start_new_session=True, **kw)
    if PIDFILE:
        try: open(PIDFILE, "a").write(f"{p.pid}\n")
        except OSError: pass
    return p


def terminate(p):
    if p is not None and p.poll() is None:
        try: os.killpg(p.pid, signal.SIGTERM)
        except ProcessLookupError: pass
        try: p.wait(30)
        except subprocess.TimeoutExpired:
            try: os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            p.wait(30)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def identity():
    if sha(MODEL) != MODEL_SHA: raise RuntimeError("model sha mismatch")
    lk = subprocess.run(["bash", "/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh", BIN, KDIR], capture_output=True, text=True,
                        env={"PATH": "/usr/bin:/bin", "LD_LIBRARY_PATH": KDIR})
    (OUT / "linkage.txt").write_text(lk.stdout + lk.stderr)
    if lk.returncode: raise RuntimeError("ggml linkage check failed")
    v = subprocess.run([BIN, "--version"], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "LD_LIBRARY_PATH": KDIR})
    vo = (v.stdout + v.stderr).strip().splitlines()
    pr = {"model_sha256": MODEL_SHA, "llama_server_version": vo[-1] if vo else "?", "kernel_realpath": os.path.realpath(BIN), "sliders_src": SLIDERS_SRC,
          "sliders_commit": "b66094d89b8068458c86a649668bed5fd0d6201c", "ts": now()}
    (OUT / "identity.json").write_text(json.dumps(pr, indent=1, sort_keys=True))
    return pr


def preflight_record(rp, pr, ready_s):
    """The server-up record. It carries NUMERIC fields so the keeper's smoke sees real first progress: the first run's preflight record was
    all strings, the first question needs far longer than first_progress_s on a 4-core smoke quarter, and the smoke failed
    ("1 new record(s) ignored: no numeric field outside the bookkeeping keys") although the server and the question were running."""
    return {"kind": "preflight", "unit": "preflight", "reply": (rp["choices"][0]["message"].get("content") or "")[:40], "identity": pr,
            "server_ready_s": round(ready_s, 1), "preflight_tokens": int((rp.get("usage") or {}).get("completion_tokens", 0)),
            "n_questions_planned": len(PINS)}


def convert(q):
    d = WORK / "md" / q["doc"]
    md = d / (q["doc"] + ".md")
    if md.is_file() and md.stat().st_size > 1000: return d
    if sha(PDFDIR / (q["doc"] + ".pdf")) != q["pdf_sha256"]: raise RuntimeError("pdf sha mismatch " + q["doc"])
    d.mkdir(parents=True, exist_ok=True)
    env = {"PATH": WHEELS + "/private-env-v2/bin:/usr/bin:/bin", "HOME": str(WORK / "home"), "TMPDIR": str(WORK / "tmp"), "BOOT_WORK": str(WORK / "boot"),
           "PYTHONDONTWRITEBYTECODE": "1", "JAVA_TOOL_OPTIONS": "-Djava.io.tmpdir=" + str(WORK / "tmp")}
    r = subprocess.run(["taskset", "-c", CPUS, ODLPY, "-B", "-I", str(COMMON / "odl_boot.py"), "odl", "--format", "markdown", "--image-output", "off", "--quiet",
                        "--output-dir", str(d), str(PDFDIR / (q["doc"] + ".pdf"))], env=env, capture_output=True, text=True, timeout=900)
    if r.returncode or not md.is_file() or md.stat().st_size < 1000:
        raise RuntimeError(f"odl convert {q['doc']} rc={r.returncode}: {r.stderr[-300:]}")
    return d


def main():
    for d in (OUT, STATE, WORK / "home", WORK / "tmp", WORK / "boot", WORK / "md"): d.mkdir(parents=True, exist_ok=True)
    pr = identity(); log("identity ok " + json.dumps(pr))
    env = {"PATH": "/usr/bin:/bin", "LD_LIBRARY_PATH": KDIR, "GGML_IQK": "1", "OMP_NUM_THREADS": "1"}
    argv = ["taskset", "-c", CPUS, BIN, "--alias", "local-coder-30b", "-m", MODEL, "--host", "127.0.0.1", "--port", str(PORT), "-np", "2", "-c", "131072",
            "-t", THR, "--flash-attn", "on", "--device", "none", "-ngl", "0", "--jinja"]
    t_srv = time.time()
    srv = spawn(argv, env, "llama-server.log")
    consec = 0; code = 0
    try:
        t = time.time() + 1800
        while True:
            if srv.poll() is not None: raise RuntimeError("llama-server exited rc=%s" % srv.returncode)
            try:
                if urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2).status == 200: break
            except Exception: pass
            if time.time() > t or stopping(): raise RuntimeError("server health timeout/stop")
            time.sleep(3)
        # first-reply preflight (non-empty content)
        body = json.dumps({"model": "local-coder-30b", "messages": [{"role": "user", "content": "Reply with the single word OK."}], "max_tokens": 8, "temperature": 0}).encode()
        rp = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", body, {"Content-Type": "application/json"}), timeout=600).read())
        if not rp["choices"][0]["message"].get("content", "").strip(): raise RuntimeError("preflight: empty reply")
        log("server healthy, preflight ok")
        record(preflight_record(rp, pr, time.time() - t_srv))
        for q in PINS:
            sf = STATE / (q["id"] + ".json")
            if sf.exists() and json.loads(sf.read_text()).get("status") in ("ok", "timeout"): continue
            if stopping() or (DEADLINE and DEADLINE - time.time() < 1200): log("stop/deadline: no new question"); break
            d = convert(q)
            qdir = OUT / "q" / q["id"]
            to = QTIMEOUT_S if not DEADLINE else min(QTIMEOUT_S, max(600, DEADLINE - time.time() - 600))
            cmd = ["taskset", "-c", CPUS, VENV_PY, "-B", str(S / "sliders_q.py"), q["id"], str(d), q["question"], CFG, str(qdir), f"http://127.0.0.1:{PORT}/v1"]
            cenv = {"PATH": "/usr/bin:/bin", "HOME": str(WORK / "home"), "TMPDIR": str(WORK / "tmp"), "PYTHONPATH": SLIDERS_SRC, "PYTHONDONTWRITEBYTECODE": "1",
                    "SLIDERS_LOGS_DIR": str(WORK / "slog"), "OMP_NUM_THREADS": "2", "SLIDERS_LLM_PROVIDER": "openai"}
            t0 = time.time(); p = spawn(cmd, cenv, f"q-{q['id']}.log")
            try: p.wait(to); status = "ok" if p.returncode == 0 else "fail"
            except subprocess.TimeoutExpired: terminate(p); status = "timeout"
            terminate(p)
            res = {}
            for f in ("result.json", "counters.json"):
                try: res[f.split(".")[0]] = json.loads((qdir / f).read_text())
                except Exception: pass
            ctr = res.get("counters") or res.get("result", {}).get("counters") or {}
            rec = {"kind": "question", "unit": "q:" + q["id"], "qid": q["id"], "status": status, "wall_s": round(time.time() - t0, 1), "gold": q["gold"],
                   "answer": (res.get("result") or {}).get("answer"), "error": (res.get("result") or {}).get("error"), "counters": ctr,
                   "schema_halluc_rate": (ctr.get("sql_schema_errors", 0) / ctr["sql_total"]) if ctr.get("sql_total") else None,
                   "note": "FB5 replacement corpus; raw counts only, gates (>20% schema-halluc, >5x calls) are applied by the verdict step 0.4"}
            sf.write_text(json.dumps({"status": status})); record(rec); log(f"{q['id']} {status} {rec['wall_s']}s calls={ctr.get('llm_calls')}")
            consec = consec + 1 if status == "fail" else 0
            if consec >= 2: log("2 consecutive failures: plumbing, stop"); code = 1; break
    finally:
        terminate(srv)
    done = [json.loads((STATE / (q["id"] + ".json")).read_text())["status"] for q in PINS if (STATE / (q["id"] + ".json")).exists()]
    if code == 0 and len(done) == len(PINS) and all(s in ("ok", "timeout") for s in done):
        rows = [json.loads(l) for l in (OUT / "results.jsonl").read_text().splitlines() if '"kind": "question"' in l]
        tot = lambda k: sum((r["counters"] or {}).get(k, 0) for r in rows)
        record({"kind": "final", "questions": len(rows), "ok": sum(r["status"] == "ok" for r in rows), "timeouts": sum(r["status"] == "timeout" for r in rows),
                "llm_calls_total": tot("llm_calls"), "sql_total": tot("sql_total"), "sql_schema_errors": tot("sql_schema_errors"),
                "schema_halluc_rate": (tot("sql_schema_errors") / tot("sql_total")) if tot("sql_total") else None})
        (OUT / "COMPLETE").write_text(now() + "\n"); log("COMPLETE")
    return code


if __name__ == "__main__":
    sys.exit(main())
