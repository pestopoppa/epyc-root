#!/usr/bin/env python3
"""DF2-9 request driver for df29_server.sh / df2_e2e.sh (stdlib only).

Modes
  seq   send prompts one at a time; per prompt attribute the server-log lines written during
        that request (byte window) and classify: non-finite log hits, garbage/empty text, HTTP error.
        Exit 0 = all requested prompts done, 10 = server died (resume index in <out>/resume_at),
        11 = deadline reached (untested prompts remain).
  conc  fire C identical-shape requests concurrently (one per prompt in the list, C at a time),
        report aggregate generated tok/s and acceptance (df2_e2e.sh).
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import time
import urllib.error
import urllib.request

PAT_NONFINITE = re.compile(r"non-finite target features")
PAT_SANITIZED = re.compile(r"sanitized \d+ isolated non-finite")
PAT_SPECFAIL = re.compile(r"failed to process speculative batch")
PAT_NAN = re.compile(r"\b(nan|inf)\b", re.IGNORECASE)
PAT_ERR = re.compile(r"(^| )E (?!.*this warning is normal)|GGML_ASSERT|terminate called|Aborted|error:", re.MULTILINE)
PAT_ACC = re.compile(r"draft acceptance\s*=\s*([0-9.]+)\s*\(\s*(\d+) accepted /\s*(\d+) generated\)")


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        with open(f"/proc/{pid}/stat") as fh:
            return fh.read().split()[2] != "Z"
    except OSError:
        return False


def log_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def log_window(path: str, a: int, b: int) -> str:
    try:
        with open(path, "rb") as fh:
            fh.seek(a)
            return fh.read(max(0, b - a)).decode("utf-8", "replace")
    except OSError:
        return ""


def garbage(text: str) -> str:
    """'' if plausible text, else a reason. NaN logits on Qwen decode to token 0 = '!'."""
    if text is None or not text.strip():
        return "empty"
    t = text.strip()
    if t.count("!") >= max(4, 0.5 * len(t)):
        return "bang-run(NaN-logits-signature)"
    if len(set(t)) <= 2 and len(t) >= 8:
        return "single-char-run"
    return ""


def post(port: int, body: dict, timeout: float):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read()), time.time() - t0, ""
    except urllib.error.HTTPError as e:
        try:
            msg = e.read().decode("utf-8", "replace")[:400]
        except Exception:
            msg = ""
        return e.code, None, time.time() - t0, msg
    except Exception as e:  # timeout, connection reset (server died), ...
        return 0, None, time.time() - t0, f"{type(e).__name__}: {e}"[:400]


def make_body(item: dict, sampling: str, max_tokens: int) -> dict:
    body = {"messages": [{"role": "user", "content": item["content"]}],
            "max_tokens": max_tokens, "stream": False, "seed": 42,
            "chat_template_kwargs": {"enable_thinking": False}}
    if sampling == "orig":   # DF2-5 runner / df2_req_bisect.sh
        body.update({"temperature": 0.6, "top_p": 0.95, "top_k": 20})
    else:                    # greedy
        body.update({"temperature": 0.0, "top_k": 1})
    return body


def run_seq(a) -> int:
    items = json.load(open(a.prompts))
    if a.kinds:
        kinds = set(a.kinds.split(","))
        items = [it for it in items if it["kind"] in kinds]
    rows_path = os.path.join(a.out, "requests.jsonl")
    start = a.start
    rc = 0
    with open(rows_path, "a") as rows:
        for idx in range(start, len(items)):
            it = items[idx]
            remaining = a.deadline - time.time()
            if remaining < 5:
                open(os.path.join(a.out, "resume_at"), "w").write(str(idx))
                return 11
            if not alive(a.pid):
                open(os.path.join(a.out, "resume_at"), "w").write(str(idx))
                return 10
            off0 = log_size(a.log)
            status, d, dt, err = post(a.port, make_body(it, a.sampling, a.max_tokens), min(a.req_timeout, remaining - 2))
            time.sleep(0.3)  # let the server flush its log lines for this task
            off1 = log_size(a.log)
            win = log_window(a.log, off0, off1)
            text, t = "", {}
            if d:
                try:
                    text = d["choices"][0]["message"].get("content") or ""
                except Exception:
                    text = ""
                t = d.get("timings") or {}
            acc = PAT_ACC.findall(win)
            row = {
                "idx": idx, "id": it["id"], "kind": it["kind"], "chars": len(it["content"]),
                "http": status, "err": err, "wall_s": round(dt, 2),
                "log_nonfinite": len(PAT_NONFINITE.findall(win)),
                "log_sanitized": len(PAT_SANITIZED.findall(win)),
                "log_specfail": len(PAT_SPECFAIL.findall(win)),
                "log_nan_words": len(PAT_NAN.findall(win)),
                "garbage": garbage(text) if status == 200 else "",
                "text_head": text[:160],
                "prompt_n": t.get("prompt_n"), "predicted_n": t.get("predicted_n"),
                "prompt_per_second": t.get("prompt_per_second"),
                "predicted_per_second": t.get("predicted_per_second"),
                "draft_n": t.get("draft_n"), "draft_n_accepted": t.get("draft_n_accepted"),
                "log_acceptance": acc[-1] if acc else None,
                "server_alive_after": alive(a.pid),
            }
            bad = (row["log_nonfinite"] > 0 or row["log_specfail"] > 0 or status != 200 or row["garbage"] != "")
            row["finite_ok"] = not bad
            rows.write(json.dumps(row) + "\n")
            rows.flush()
            print(f"  [{idx:2d}] {it['kind']:7s} {it['id'][:38]:38s} http={status} nonfinite_log={row['log_nonfinite']} "
                  f"sanitized={row['log_sanitized']} garbage={row['garbage'] or '-'} pn={row['prompt_n']} "
                  f"tg={row['predicted_n']} tps={row['predicted_per_second']} draft={row['draft_n_accepted']}/{row['draft_n']} "
                  f"{'OK' if not bad else 'BAD'}", flush=True)
            if not row["server_alive_after"]:
                open(os.path.join(a.out, "resume_at"), "w").write(str(idx + 1))
                return 10
    return rc


def run_conc(a) -> int:
    items = json.load(open(a.prompts))
    if a.kinds:
        kinds = set(a.kinds.split(","))
        items = [it for it in items if it["kind"] in kinds]
    items = (items * ((a.conc + len(items) - 1) // len(items)))[: a.conc]
    t0 = time.time()
    remaining = a.deadline - time.time()
    with cf.ThreadPoolExecutor(max_workers=a.conc) as ex:
        futs = [ex.submit(post, a.port, make_body(it, a.sampling, a.max_tokens), min(a.req_timeout, remaining - 2)) for it in items]
        res = [f.result() for f in futs]
    wall = time.time() - t0
    n_gen = sum((d or {}).get("timings", {}).get("predicted_n", 0) or 0 for _, d, _, _ in res)
    dn = sum((d or {}).get("timings", {}).get("draft_n", 0) or 0 for _, d, _, _ in res)
    da = sum((d or {}).get("timings", {}).get("draft_n_accepted", 0) or 0 for _, d, _, _ in res)
    ok = sum(1 for s, _, _, _ in res if s == 200)
    bad_text = sum(1 for s, d, _, _ in res if s == 200 and garbage(((d or {}).get("choices") or [{}])[0].get("message", {}).get("content")))
    out = {"conc": a.conc, "ok": ok, "n": len(res), "garbage": bad_text, "wall_s": round(wall, 2),
           "gen_tokens": n_gen, "agg_tok_s": round(n_gen / wall, 2) if wall > 0 else None,
           "draft_n": dn, "draft_accepted": da, "acceptance": round(da / dn, 4) if dn else None,
           "per_req_tps": [round(((d or {}).get("timings") or {}).get("predicted_per_second") or 0, 2) for _, d, _, _ in res]}
    with open(os.path.join(a.out, "conc.jsonl"), "a") as fh:
        fh.write(json.dumps(out) + "\n")
    print(f"  conc={a.conc} ok={ok}/{len(res)} garbage={bad_text} agg_tok_s={out['agg_tok_s']} acceptance={out['acceptance']} wall={out['wall_s']}s", flush=True)
    return 0 if ok == len(res) else 12


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["seq", "conc"], default="seq")
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--pid", type=int, required=True)
    p.add_argument("--log", required=True)
    p.add_argument("--prompts", required=True)
    p.add_argument("--kinds", default="")
    p.add_argument("--out", required=True)
    p.add_argument("--sampling", choices=["orig", "greedy"], default="greedy")
    p.add_argument("--max-tokens", type=int, default=32)
    p.add_argument("--req-timeout", type=float, default=60)
    p.add_argument("--deadline", type=float, required=True, help="epoch seconds")
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--conc", type=int, default=1)
    a = p.parse_args()
    return run_seq(a) if a.mode == "seq" else run_conc(a)


if __name__ == "__main__":
    raise SystemExit(main())
