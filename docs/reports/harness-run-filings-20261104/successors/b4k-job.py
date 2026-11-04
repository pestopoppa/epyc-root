#!/usr/bin/env python3
"""UFH14-B4a window collection (ws58, 2026-11-02): ONE >=200-call `missed_prefill_share` diagnostic window on the :8083 shape; NOT a B4a baseline.

Why a private replica: production :8083 has carried 14 serving records since the B4 deploy (2026-10-03..05) and the
whole LLM stack is down on 2026-11-02, so an organic >=200-call window does not exist and will not accumulate.
This job serves the EXACT production :8083 argv (logs/server_launches/8083.json, argv_sha256 pinned below; only
--port and --slot-save-path are substituted) on scratch port 18183, from the v10 kernel store, and drives it through
the production orchestrator backend code (LlamaServerBackend.infer_stream_text at the pinned orchestrator commit),
so every call writes a real `epyc.orchestrator.serving_call.v1` record with `request.prefix_fp`.

Workload (frozen, deterministic): 2 shared heads (~3k tok) x 8 sessions (> np 4 slots, so RAM-cache save/restore
is exercised) of agentic growth: base context 8k-50k tok of real orchestrator source, then turns that append the
model's answer plus ~1.5k tok of new "tool output". Concurrency 4. Calls interleave round-robin across sessions.
Target p90 prompt ~ 80-90k tok (design ufh14-b4 §3.1 :8083 workload: 8 sessions + 2 shared, p90 86,988).

Stop rule: stop after TARGET_OK (220) successful calls, or at FILLER_DEADLINE / FILLER_STOPFILE. The window is
VALID when >=200 dispatched ok calls carry prefix_fp (fp_coverage >= 0.95); then prefix_cache_report.py runs and
out/runs/<run>/REPORT.json + out/COMPLETE are written. Units: one line per call in out/runs/<run>/calls.jsonl.
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
import random
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

D = Path("/mnt/raid0/llm/tmp/agentic-serving-harness-fixes/b4k-successor")
SRC = Path("/mnt/raid0/llm/tmp/agentic-serving-harness-fixes/b4k-successor-orch")
LAUNCH = D / "prod-8083-launch.json"
ARGV_SHA = "f09f466f756884301f7286f75076582ea3d2ee1a846550d3c7f392a620e66e93"
ORCH_COMMIT = "77ba24efe7f27783a3a98be5474bace26c753f12"
PORT = 18183
PROD_PORT = 8083
TARGET_OK = 220
VALID_MIN = 200
CONC = 4
SESSIONS = 8
N_TOKENS = 128  # bounded screening workload; request explicitly disables thinking
SEED = 20261102
VERIFY_LINKAGE = "/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def listening(port: int) -> bool:
    s = socket.socket()
    s.settimeout(1)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def launch_record() -> dict:
    rec = json.loads(LAUNCH.read_text())
    if rec.get("argv_sha256") != ARGV_SHA:
        raise SystemExit(f"launch record argv_sha256 {rec.get('argv_sha256')} != pinned {ARGV_SHA}")
    return rec


def scratch_argv(rec: dict, run_dir: Path) -> list[str]:
    argv = list(rec["argv"])
    out = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--port":
            out += [a, str(PORT)]
            i += 2
            continue
        if a == "--slot-save-path":
            out += [a, str(run_dir / "kv_slots")]
            i += 2
            continue
        out.append(a)
        i += 1
    return out


def check() -> int:
    problems = []
    rec = launch_record()
    for p in (rec["binary_realpath"], rec["model_path"]):
        if not Path(p).exists():
            problems.append(f"missing {p}")
    argv = rec["argv"]
    md = argv[argv.index("-md") + 1]
    if not Path(md).exists():
        problems.append(f"missing drafter {md}")
    tmpl = argv[argv.index("--chat-template-file") + 1]
    if not Path(tmpl).exists():
        problems.append(f"missing template {tmpl}")
    prod_store = os.path.realpath("/mnt/raid0/llm/kernels/production/gpu")
    if os.path.dirname(rec["binary_realpath"]) != prod_store:
        problems.append(f"binary {rec['binary_realpath']} is not the production gpu kernel store {prod_store}")
    if subprocess.run(["git", "-C", str(SRC), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip() != ORCH_COMMIT:
        problems.append("orch-src snapshot commit mismatch")
    if listening(PROD_PORT):
        problems.append(f"production :{PROD_PORT} is serving: two 27B replicas do not fit the MI210 (64 GiB)")
    if listening(PORT):
        problems.append(f":{PORT} already in use")
    if problems:
        print("; ".join(problems))
        return 1
    print("ok")
    return 0


# ---------------------------------------------------------------- workload
def corpus() -> tuple[list[str], list[str], list[str]]:
    """Real text, frozen at the pinned commit: two shared heads, session bases, tool-output deltas."""
    files = sorted(p for p in (SRC / "src").rglob("*.py") if p.stat().st_size > 4000)
    texts = [p.read_text(errors="replace") for p in files]
    rng = random.Random(SEED)
    rng.shuffle(texts)
    blob = "\n\n".join(texts)
    pos = 0

    def take(chars: int) -> str:
        nonlocal pos
        s = blob[pos:pos + chars]
        pos += chars
        return s

    rules = (
        "You are the architect_critic of an agentic coding orchestrator. Review the repository context and the "
        "conversation so far. Answer concisely: name the defect or confirm correctness, cite file:line, and propose "
        "the smallest fix. Never restate the context.\n\n## Rules\n"
    )
    heads = [rules + "### Reference module A\n" + take(9000), rules + "### Reference module B\n" + take(9000)]
    # base contexts 8k..50k tokens (~3 chars/token), spread so the grown prompt p90 lands near 85k tokens
    base_tok = [8000, 14000, 20000, 26000, 32000, 38000, 44000, 50000]
    bases = ["\n## Repository context\n" + take(t * 3) for t in base_tok]
    deltas = ["\n## Tool output\n" + take(3600) for _ in range(40 * SESSIONS)]
    return heads, bases, deltas


class Session:
    def __init__(self, sid: int, head: str, base: str):
        self.sid = sid
        self.prefix = head + base
        self.turn = 0
        self.lock = threading.Lock()


def run(run_dir: Path) -> int:
    sys.path.insert(0, str(SRC))
    os.environ["ORCHESTRATOR_SERVING_CALLS_LOG"] = str(run_dir / "serving_calls.jsonl")
    os.environ.setdefault("ORCHESTRATOR_GIT_SHA", ORCH_COMMIT)
    from src.backends.llama_server import LlamaServerBackend, ServerConfig
    from src.backends import serving_calls
    from src.model_server import InferenceRequest
    from src.registry_loader import RegistryLoader

    role = RegistryLoader(validate_paths=False).get_role("architect_critic")
    backend = LlamaServerBackend(ServerConfig(base_url=f"http://127.0.0.1:{PORT}", timeout=3600, num_slots=4,
                                              use_chat_completions=True))
    heads, bases, deltas = corpus()
    sessions = [Session(i, heads[i % 2], bases[i]) for i in range(SESSIONS)]
    calls_path = run_dir / "calls.jsonl"
    deadline = float(os.environ.get("FILLER_DEADLINE") or (time.time() + 7200))
    stopfile = os.environ.get("FILLER_STOPFILE") or str(D / "STOP")
    ok = 0
    n = 0
    lk = threading.Lock()
    delta_i = iter(range(10**9))

    def stop() -> bool:
        return os.path.exists(stopfile) or time.time() > deadline - 120 or ok >= TARGET_OK

    def one(kind: str, s: Session | None, prompt: str) -> None:
        nonlocal ok, n
        serving_calls.stage_caller(role="architect_critic", source="primitives", priority="interactive",
                                   request_id=f"b4a-{kind}-{s.sid if s else 'h'}-{s.turn if s else 0}")
        t0 = time.time()
        res = backend.infer_stream_text(role, InferenceRequest(role="architect_critic", prompt=prompt,
                                                                n_tokens=N_TOKENS, timeout=3600, chat_template_kwargs={"enable_thinking": False}),
                                        on_chunk=lambda _c: None)
        row = {"ts": now(), "kind": kind, "session": s.sid if s else None, "turn": s.turn if s else 0,
               "prompt_chars": len(prompt), "ok": bool(res.success), "wall_s": round(time.time() - t0, 3),
               "prompt_tokens": getattr(res, "prompt_tokens", None),
               "cached_prompt_tokens": getattr(res, "cached_prompt_tokens", None),
               "tokens_generated": getattr(res, "tokens_generated", None),
               "reasoning_chars": len(getattr(res, "reasoning_content", None) or ""),
               "failure_reason": getattr(res, "failure_reason", None),
               "completion_reason": getattr(res, "completion_reason", None)}
        with lk:
            n += 1
            ok += int(row["ok"])
            with open(calls_path, "a") as f:
                f.write(json.dumps(row) + "\n")
        if s is not None and res.success:
            s.prefix = prompt + "\n## Assistant\n" + (res.output or "(no content)") + "\n"
            s.turn += 1

    # 1. warm both shared heads (A3-style client warm; also the smoke's first unit, seconds after load)
    for h in heads:
        one("warm", None, h)
    # 2. agentic turns, round-robin across 8 sessions on 4 concurrent lanes
    order = [s for _ in range(60) for s in sessions]
    it = iter(order)
    busy: set[int] = set()

    def next_job():
        for s in it:
            if s.sid not in busy:
                return s
        return None

    with cf.ThreadPoolExecutor(CONC) as ex:
        futs = {}
        while not stop():
            while len(futs) < CONC and not stop():
                s = next_job()
                if s is None:
                    break
                busy.add(s.sid)
                prompt = s.prefix + deltas[next(delta_i) % len(deltas)]
                futs[ex.submit(one, "turn", s, prompt)] = s
            if not futs:
                break
            done, _ = cf.wait(list(futs), return_when=cf.FIRST_COMPLETED, timeout=30)
            for f in done:
                s = futs.pop(f)
                busy.discard(s.sid)
                try:
                    f.result()
                except Exception as e:  # a failed call is a recorded outcome, not a crash
                    with open(run_dir / "errors.log", "a") as g:
                        g.write(f"{now()} session {s.sid}: {e!r}\n")
        cf.wait(list(futs))
    return ok


def main() -> int:
    if "--check" in sys.argv:
        return check()
    if check() != 0:
        return 5
    rec = launch_record()
    run_dir = D / "out" / "runs" / dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir.mkdir(parents=True)
    (run_dir / "kv_slots").mkdir()
    argv = scratch_argv(rec, run_dir)
    (run_dir / "argv.json").write_text(json.dumps({"argv": argv, "source": str(LAUNCH), "argv_sha256": ARGV_SHA}, indent=1))
    env = dict(os.environ, LD_LIBRARY_PATH=rec["ld_library_path"])
    log = open(run_dir / "server.log", "ab")
    srv = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    pidfile = os.environ.get("FILLER_PIDFILE")
    if pidfile:
        with open(pidfile, "a") as f:
            f.write(f"{srv.pid}\n")

    def reap(*_a):
        if srv.poll() is None:
            srv.terminate()
            try:
                srv.wait(60)
            except subprocess.TimeoutExpired:
                srv.kill()
                srv.wait(30)

    signal.signal(signal.SIGTERM, lambda *a: (reap(), sys.exit(143)))
    try:
        for _ in range(300):
            if srv.poll() is not None:
                raise SystemExit(f"server died during load rc={srv.returncode}")
            try:
                if urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2).status == 200:
                    break
            except Exception:
                pass
            time.sleep(2)
        else:
            raise SystemExit("server never became healthy")
        # residency + linkage proof of OUR pid
        kfd = Path(f"/sys/class/kfd/kfd/proc/{srv.pid}")
        vram = sum(int(p.read_text()) for p in kfd.glob("vram_*")) if kfd.is_dir() else 0
        maps = sorted({l.split()[-1] for l in open(f"/proc/{srv.pid}/maps") if "libggml" in l})
        lk = subprocess.run([VERIFY_LINKAGE, rec["binary_realpath"], os.path.dirname(rec["binary_realpath"])],
                            env=env, capture_output=True, text=True)
        proof = {"pid": srv.pid, "kfd_vram_bytes": vram, "libggml_maps": maps, "linkage_rc": lk.returncode,
                 "linkage_tail": (lk.stdout + lk.stderr)[-1500:], "at": now()}
        (run_dir / "residency-proof.json").write_text(json.dumps(proof, indent=1))
        if vram <= 0 or not any("builds/gpu-" in m for m in maps):
            raise SystemExit(f"residency proof failed: {proof}")
        ok = run(run_dir)
    finally:
        reap()
    rep = run_dir / "REPORT.json"
    subprocess.run([sys.executable, str(SRC / "scripts/analysis/prefix_cache_report.py"), "--log",
                    str(run_dir / "serving_calls.jsonl"), "--port", str(PORT), "--json", str(rep)],
                   capture_output=True, text=True)
    evictions = sum(1 for l in open(run_dir / "server.log", errors="replace") if "evict" in l.lower())
    summary = {"ok_calls": ok, "evicted_lines": evictions, "report": str(rep), "orch_commit": ORCH_COMMIT,
               "argv_sha256_source": ARGV_SHA, "workload_note": "diagnostic; 128 output tokens, enable_thinking=false; not production baseline", "ended": now()}
    try:
        port = json.loads(rep.read_text())["ports"][str(PORT)]
        summary.update({k: port.get(k) for k in ("calls", "fp_coverage", "missed_prefill_share", "hit_tok",
                                                 "cold_large_share", "concurrent_dupes", "prefill_s")})
    except Exception as e:
        summary["report_error"] = repr(e)
    valid = ok >= VALID_MIN and (summary.get("calls") or 0) >= VALID_MIN and (summary.get("fp_coverage") or 0) >= 0.95
    summary["diagnostic_window_valid"] = valid
    (run_dir / "SUMMARY.json").write_text(json.dumps(summary, indent=1))
    if valid:
        (D / "out" / "COMPLETE").write_text(json.dumps({"run": str(run_dir), **summary}, indent=1))
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
