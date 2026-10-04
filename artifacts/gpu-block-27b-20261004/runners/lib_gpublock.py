"""Shared helpers for the 2026-10-03 27B GPU-window block (stdlib only).

Used by q38_t7.py, kvu16b_residency.py, b4g_entry_cost.py, deploy_ec2_lease.py and
b4i_idle_slots_ab.py in this directory. Nothing here starts, stops or signals a
process. The only subprocess is `ss -ltnp` (read-only socket listing) to map a port
to its server PID for the KFD VRAM read.

Network calls happen only in RUN mode. Every script's --dry-run path uses the
offline helpers (file checks, char-based token estimates) and sends nothing.
"""
from __future__ import annotations

import collections
import json
import os
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable

ROOT = Path("/mnt/raid0/llm/tmp/gpu-block-27b-20261003")
RESULTS = ROOT / "results"
ORCH = Path("/mnt/raid0/llm/epyc-orchestrator")
LOG_8083 = ORCH / "logs" / "llama-server-8083.log"
SERVING_LOG = ORCH / "logs" / "serving_calls" / "serving_calls.jsonl"
LAUNCH_RECORD_8083 = ORCH / "logs" / "server_launches" / "8083.json"
WINDOW_FILE = Path(os.environ.get("ORCHESTRATOR_GPU_WINDOW_FILE", "/mnt/raid0/llm/tmp/gpu-window/mi210.json"))
CONTEXTS = Path("/mnt/raid0/llm/tmp/ds41-c95/contexts")
PROD_MIX = Path("/mnt/raid0/llm/tmp/inf70/agents/e3-alpha/prompts.json")  # 24-prompt production mix
X0_ARGV = Path("/mnt/raid0/llm/tmp/ds41-c95/X0_ARGV_8083.txt")
VRAM_CARD = Path("/sys/class/drm/card2/device/mem_info_vram_used")  # the MI210 (card2)
KFD_PROC = Path("/sys/class/kfd/kfd/proc")
GIB = 1024 ** 3
EST_CHARS_PER_TOKEN = 3.2  # dry-run estimate only; RUN mode calibrates with POST /tokenize

BAD_LINE_PATTERNS = {
    "failed to find a memory slot": re.compile(r"failed to find a memory slot"),
    "Context size has been exceeded": re.compile(r"Context size has been exceeded"),
}


# --------------------------------------------------------------------------- time / io
def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def ts_tag() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def out_dir(script: str, label: str | None = None) -> Path:
    d = RESULTS / script / (f"{label}-{ts_tag()}" if label else ts_tag())
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=str) + "\n")
    tmp.replace(path)


class JsonlSink:
    """Append-and-flush per record (persist per call, never only at the end)."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.Lock()

    def add(self, rec: dict) -> None:
        line = json.dumps({"at": now_iso(), **rec}, default=str)
        with self._lock, open(self.path, "a") as fh:
            fh.write(line + "\n")
            fh.flush()


# --------------------------------------------------------------------------- http
def http_json(url: str, body: dict | None = None, timeout: float = 30.0,
              headers: dict | None = None, method: str | None = None) -> tuple[int, Any]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method or ("POST" if data else "GET"),
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw[:500].decode(errors="replace")}


def get_json(url: str, timeout: float = 5.0) -> Any:
    return http_json(url, None, timeout)[1]


def tokenize_count(base: str, text: str) -> int:
    _, body = http_json(f"{base}/tokenize", {"content": text}, timeout=300)
    return len((body or {}).get("tokens") or [])


def tokenize_ids(base: str, text: str) -> list[int]:
    _, body = http_json(f"{base}/tokenize", {"content": text}, timeout=300)
    return list((body or {}).get("tokens") or [])


def stream_request(url: str, body: dict, timeout: float = 3600.0, headers: dict | None = None,
                   on_first_token: Callable[[], None] | None = None,
                   stop: threading.Event | None = None,
                   on_event: Callable[[dict], None] | None = None) -> dict:
    """POST with stream=true; handles llama-native /completion and OpenAI chat SSE.

    Returns ttfb/ttft, content and reasoning text, final timings/usage, finish reason, and
    `aborted` when `stop` was set mid-stream (closing the connection cancels the task
    server-side)."""
    body = {**body, "stream": True}
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **(headers or {})})
    t0 = time.time()
    out: dict[str, Any] = {"t_send": t0, "ttfb_s": None, "ttft_s": None, "timings": None, "usage": None,
                           "finish": None, "aborted": False, "http_status": None, "error": None,
                           "n_events": 0}
    content: list[str] = []
    reasoning: list[str] = []
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out["http_status"] = r.status
            for raw in r:
                if out["ttfb_s"] is None:
                    out["ttfb_s"] = round(time.time() - t0, 3)
                if stop is not None and stop.is_set():
                    out["aborted"] = True
                    break
                line = raw.strip()
                if not line.startswith(b"data:"):
                    continue
                payload = line[5:].strip()
                if not payload or payload == b"[DONE]":
                    continue
                try:
                    ev = json.loads(payload)
                except ValueError:
                    continue
                out["n_events"] += 1
                got = False
                if isinstance(ev.get("timings"), dict):
                    out["timings"] = ev["timings"]
                if isinstance(ev.get("usage"), dict):
                    out["usage"] = ev["usage"]
                if "content" in ev and "choices" not in ev:  # llama-native /completion
                    if ev.get("content"):
                        content.append(ev["content"])
                        got = True
                    if ev.get("stop"):
                        out["finish"] = ev.get("stop_type") or "stop"
                for ch in ev.get("choices") or []:
                    d = ch.get("delta") or {}
                    if d.get("reasoning_content"):
                        reasoning.append(d["reasoning_content"])
                        got = True
                    if d.get("content"):
                        content.append(d["content"])
                        got = True
                    if ch.get("finish_reason"):
                        out["finish"] = ch["finish_reason"]
                if got and out["ttft_s"] is None:
                    out["ttft_s"] = round(time.time() - t0, 3)
                    if on_first_token:
                        on_first_token()
                if on_event:
                    on_event(ev)
    except urllib.error.HTTPError as e:
        out["http_status"] = e.code
        out["error"] = e.read()[:800].decode(errors="replace")
    except Exception as exc:  # noqa: BLE001 - recorded, never raised into a worker thread
        out["error"] = f"{type(exc).__name__}: {exc}"[:800]
    out["wall_s"] = round(time.time() - t0, 3)
    out["content"] = "".join(content)
    out["reasoning"] = "".join(reasoning)
    return out


def timing_summary(t: dict | None) -> dict:
    t = t or {}
    dn, da = t.get("draft_n"), t.get("draft_n_accepted")
    return {"prompt_n": t.get("prompt_n"), "cache_n": t.get("cache_n"),
            "prompt_ms": t.get("prompt_ms"),
            "prefill_tps": round(t["prompt_per_second"], 1) if t.get("prompt_per_second") else None,
            "decode_tps": round(t["predicted_per_second"], 2) if t.get("predicted_per_second") else None,
            "predicted_n": t.get("predicted_n"), "draft_n": dn, "draft_n_accepted": da,
            "draft_acc": round(da / dn, 4) if dn else None}


# --------------------------------------------------------------------------- prompts
def context_corpus() -> list[tuple[str, str]]:
    """The DS41 planner contexts C1..C7 (prompt.inline.txt): real production-shaped text."""
    return [(p.parent.name, p.read_text()) for p in sorted(CONTEXTS.glob("C*/prompt.inline.txt"))]


def rotated_text(start: int, chars: int, corpus: list[tuple[str, str]] | None = None) -> str:
    corpus = corpus or context_corpus()
    parts, total, i = [], 0, start
    while total < chars:
        name, txt = corpus[i % len(corpus)]
        parts.append(f"\n\n===== context {name} =====\n{txt}")
        total += len(parts[-1])
        i += 1
    return "".join(parts)[:chars]


def corpus_chars() -> int:
    return sum(len(t) for _, t in context_corpus())


def fit_prompt(base: str | None, target_tokens: int, head: str, start: int, tail: str = "",
               tol: float = 0.01) -> tuple[str, int, bool]:
    """head + rotated corpus + tail, trimmed to target_tokens (+-tol) with POST /tokenize.

    base=None -> offline estimate (dry-run): returns (text, estimated_tokens, False)."""
    corpus = context_corpus()
    chars = int(target_tokens * EST_CHARS_PER_TOKEN)
    if base is None:
        text = head + rotated_text(start, chars, corpus) + tail
        return text, int(len(text) / EST_CHARS_PER_TOKEN), False
    for _ in range(8):
        text = head + rotated_text(start, chars, corpus) + tail
        n = tokenize_count(base, text)
        if abs(n - target_tokens) <= target_tokens * tol:
            return text, n, True
        chars = max(1000, int(chars * target_tokens / max(1, n)))
    return text, n, True


def nonce(tag: str) -> str:
    return f"[{tag} {uuid.uuid4().hex}]\n"


# --------------------------------------------------------------------------- server / gpu facts
def port_pid(port: int) -> int | None:
    try:
        out = subprocess.run(["ss", "-ltnp", f"sport = :{port}"], capture_output=True, text=True,
                             timeout=5).stdout
    except Exception:  # noqa: BLE001
        return None
    m = re.search(r"pid=(\d+)", out)
    return int(m.group(1)) if m else None


def proc_cmdline(pid: int) -> list[str]:
    try:
        return [a for a in Path(f"/proc/{pid}/cmdline").read_bytes().decode().split("\0") if a]
    except OSError:
        return []


def proc_environ(pid: int) -> dict[str, str]:
    try:
        raw = Path(f"/proc/{pid}/environ").read_bytes().decode(errors="replace").split("\0")
    except OSError:
        return {}
    return dict(kv.split("=", 1) for kv in raw if "=" in kv)


def proc_lstart(pid: int) -> str | None:
    try:
        return subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True,
                              timeout=5).stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def kfd_procs() -> list[dict]:
    rows = []
    if not KFD_PROC.exists():
        return rows
    for d in sorted(KFD_PROC.iterdir()):
        try:
            pid = int(d.name)
        except ValueError:
            continue
        vram = 0
        for f in d.glob("vram_*"):
            try:
                vram += int(f.read_text())
            except (OSError, ValueError):
                pass
        cmd = " ".join(proc_cmdline(pid))[:160]
        rows.append({"pid": pid, "vram_gib": round(vram / GIB, 3), "cmd": cmd})
    return rows


def card_vram_bytes() -> int | None:
    try:
        return int(VRAM_CARD.read_text())
    except (OSError, ValueError):
        return None


def kfd_pid_vram_bytes(pid: int | None) -> int | None:
    if pid is None:
        return None
    d = KFD_PROC / str(pid)
    if not d.exists():
        return None
    total = 0
    for f in d.glob("vram_*"):
        try:
            total += int(f.read_text())
        except (OSError, ValueError):
            pass
    return total


class VramSampler(threading.Thread):
    def __init__(self, pid: int | None, interval: float = 0.5, sink: JsonlSink | None = None) -> None:
        super().__init__(daemon=True)
        self.pid, self.interval, self.sink = pid, interval, sink
        self.stop_ev = threading.Event()
        self.samples: list[tuple[float, int | None, int | None]] = []

    def run(self) -> None:
        while not self.stop_ev.is_set():
            s = (time.time(), card_vram_bytes(), kfd_pid_vram_bytes(self.pid))
            self.samples.append(s)
            self.stop_ev.wait(self.interval)

    def summary(self) -> dict:
        proc = [p for _, _, p in self.samples if p is not None]
        card = [c for _, c, _ in self.samples if c is not None]
        return {"n_samples": len(self.samples), "interval_s": self.interval, "pid": self.pid,
                "kfd_peak_gib": round(max(proc) / GIB, 3) if proc else None,
                "kfd_min_gib": round(min(proc) / GIB, 3) if proc else None,
                "card_peak_gib": round(max(card) / GIB, 3) if card else None}


def slot_view(s: dict) -> dict:
    nt = (s.get("next_token") or [{}])
    nt = nt[0] if isinstance(nt, list) and nt else (nt if isinstance(nt, dict) else {})
    return {"id": s.get("id"), "proc": bool(s.get("is_processing")),
            "n_tok": int(s.get("n_prompt_tokens") or 0),  # = prompt.tokens.size(): prompt + generated
            "n_proc": int(s.get("n_prompt_tokens_processed") or 0),
            "n_cache": int(s.get("n_prompt_tokens_cache") or 0),
            "n_dec": int(nt.get("n_decoded") or 0), "n_remain": nt.get("n_remain"),
            "id_task": s.get("id_task")}


class SlotsSampler(threading.Thread):
    def __init__(self, base: str, interval: float = 2.0, sink: JsonlSink | None = None,
                 on_sample: Callable[[float, list[dict]], None] | None = None) -> None:
        super().__init__(daemon=True)
        self.base, self.interval, self.sink, self.on_sample = base, interval, sink, on_sample
        self.stop_ev = threading.Event()
        self.samples: list[tuple[float, list[dict]]] = []
        self.errors = 0

    def run(self) -> None:
        while not self.stop_ev.is_set():
            try:
                body = get_json(f"{self.base}/slots", 5.0)
                rows = [slot_view(s) for s in (body or [])]
                t = time.time()
                self.samples.append((t, rows))
                if self.sink:
                    self.sink.add({"t": round(t, 3), "slots": rows})
                if self.on_sample:
                    self.on_sample(t, rows)
            except Exception:  # noqa: BLE001 - a missed sample is not a verdict
                self.errors += 1
            self.stop_ev.wait(self.interval)


# --------------------------------------------------------------------------- server log
class LogWindow:
    """Byte-offset window over a llama-server log: lines written after `start`."""

    def __init__(self, path: Path, start: int | None = None) -> None:
        self.path = path
        self.start = path.stat().st_size if start is None else start

    def lines(self, end: int | None = None) -> list[str]:
        with self.path.open("rb") as fh:
            fh.seek(self.start)
            data = fh.read() if end is None else fh.read(max(0, end - self.start))
        return data.decode(errors="replace").splitlines()

    def counts(self, patterns: dict[str, re.Pattern] | None = None) -> dict[str, int]:
        pats = patterns or BAD_LINE_PATTERNS
        ls = self.lines()
        return {k: sum(1 for ln in ls if p.search(ln)) for k, p in pats.items()}


RE_SAVE = re.compile(r"saving prompt with length (\d+), total state size = ([\d.]+) MiB \(draft: ([\d.]+) MiB\)")
RE_ENTRY = re.compile(r"- prompt (0x[0-9a-f]+):\s+(\d+) tokens, checkpoints:\s+(\d+),\s+([\d.]+) MiB")
RE_CKPT = re.compile(r"created context checkpoint (\d+) of (\d+) \(pos_min = (\d+), pos_max = (\d+), "
                     r"n_tokens = (\d+), size = ([\d.]+) MiB\)")
RE_EVICT = re.compile(r"making room for prompt cache entry, removing oldest entry \(size = ([\d.]+) MiB\)")
RE_CACHE_STATE = re.compile(r"cache state: (\d+) prompts, ([\d.]+) MiB \(limits: ([\d.]+) MiB")
RE_CLEAR = re.compile(r"id\s+(\d+) \| task -?\d+ \| clearing prompt with (\d+) tokens")
RE_LOAD_BETTER = re.compile(r"found better prompt with f_keep = ([\d.]+), sim = ([\d.]+)")
RE_LOAD_FAIL = re.compile(r"failed to restore state with size (\d+)")
RE_DRAFT_ACC = re.compile(r"id\s+(\d+) \| task (\d+) \| draft acceptance = ([\d.]+) \(\s*(\d+) accepted /\s*(\d+) generated\)")
RE_LAUNCH = re.compile(r"load_model: initializing, n_slots = (\d+), n_ctx_slot = (\d+), kv_unified = '(\w+)'")


def prompt_cache_events(lines: list[str]) -> dict:
    ev = {"idle_saves": 0, "clear_nonzero": 0, "clear_nonzero_tokens": 0, "restores_better": 0,
          "restore_failures": 0, "evictions": 0, "evicted_mib": 0.0, "prompt_saves": 0,
          "last_cache_state": None}
    for ln in lines:
        if "saving idle slot to prompt cache" in ln:
            ev["idle_saves"] += 1
        m = RE_CLEAR.search(ln)
        if m and int(m.group(2)) > 0:
            ev["clear_nonzero"] += 1
            ev["clear_nonzero_tokens"] += int(m.group(2))
        if RE_LOAD_BETTER.search(ln):
            ev["restores_better"] += 1
        if RE_LOAD_FAIL.search(ln):
            ev["restore_failures"] += 1
        m = RE_EVICT.search(ln)
        if m:
            ev["evictions"] += 1
            ev["evicted_mib"] += float(m.group(1))
        if RE_SAVE.search(ln):
            ev["prompt_saves"] += 1
        m = RE_CACHE_STATE.search(ln)
        if m:
            ev["last_cache_state"] = {"prompts": int(m.group(1)), "mib": float(m.group(2)),
                                      "limit_mib": float(m.group(3))}
    ev["evicted_mib"] = round(ev["evicted_mib"], 1)
    return ev


# --------------------------------------------------------------------------- gpu window file
def window_status() -> dict:
    try:
        d = json.loads(WINDOW_FILE.read_text())
    except FileNotFoundError:
        return {"file": str(WINDOW_FILE), "exists": False, "parked_8083": False}
    except (OSError, ValueError) as exc:
        return {"file": str(WINDOW_FILE), "exists": True, "error": str(exc), "parked_8083": False}
    parked = d.get("holder") not in (None, "production") and (
        8083 in (d.get("parked_ports") or []) or "architect_critic" in (d.get("parked_roles") or []))
    return {"file": str(WINDOW_FILE), "exists": True, "holder": d.get("holder"),
            "parked_roles": d.get("parked_roles"), "parked_ports": d.get("parked_ports"),
            "preempt_requested_at": d.get("preempt_requested_at"), "parked_8083": parked}


# --------------------------------------------------------------------------- coherence classifier
# Copied verbatim in logic from /mnt/raid0/llm/tmp/inf70/agents/gdn-rowexact/classify.py (the
# INF-70 corrected degeneracy classifier, classes by REASON). Token ids come from the server's
# /tokenize of the returned text, since chat completions do not return ids.
MIN_N = 16
EOS_MAX_N = 4


def classify(text: str, toks: list[int], finish: str | None, http_ok: bool = True) -> dict:
    if not http_ok:
        return {"cls": "HTTP-ERROR", "n": 0}
    n = len(toks)
    eos = finish in ("stop", "eos")
    st = {"n": n, "finish": finish}
    if n == 0:
        return {"cls": "EARLY-EOS" if eos else "EMPTY", **st}
    if n <= EOS_MAX_N and eos:
        return {"cls": "EARLY-EOS", **st}
    if n < MIN_N:
        return {"cls": "EARLY-EOS" if eos else "SHORT", **st}
    uniq = len(set(toks)) / n
    top = collections.Counter(toks).most_common(1)[0][1] / n
    run = best = 1
    for a, b in zip(toks, toks[1:]):
        run = run + 1 if a == b else 1
        best = max(best, run)
    words = text.split()
    ok_chars = sum(ch.isascii() and (ch.isalnum() or ch in " .,;:'\"-()!?\n") for ch in text) / max(1, len(text))
    reasons = [r for r, bad in (("uniq", uniq < 0.35), ("top", top >= 0.25), ("run", best >= 6),
                                ("words", len(words) < 0.25 * n), ("ascii", ok_chars < 0.85)) if bad]
    st.update(uniq=round(uniq, 3), top=round(top, 3), run=best, words=len(words), ascii_ok=round(ok_chars, 3),
              salad_reasons=reasons)
    # Classes are the codified ones. A SALAD whose ONLY reason is the ascii share (code-heavy
    # text: _ {} <> = are outside the classifier's "ordinary text" set) is flagged `review`
    # so a human eyeballs it instead of the gate failing on symbol density alone.
    return {"cls": "SALAD" if reasons else "COHERENT", "review": reasons == ["ascii"], **st}


# --------------------------------------------------------------------------- run-mode guards
def require_owner(args: Any, what: str) -> None:
    if args.dry_run:
        return
    if not getattr(args, "i_own_the_window", False):
        raise SystemExit(f"REFUSING: {what}. Run with --dry-run to see the plan, or with "
                         "--i-own-the-window as the session that owns this GPU window.")


def check_file(path: Path, label: str, problems: list[str], must_write: bool = False) -> str:
    if not path.exists():
        problems.append(f"missing {label}: {path}")
        return f"MISSING {path}"
    if must_write and not os.access(path, os.W_OK):
        problems.append(f"not writable {label}: {path}")
    return f"ok {path} ({path.stat().st_size} bytes)"


def print_plan(title: str, sections: list[tuple[str, list[str]]], problems: list[str]) -> int:
    print(f"=== DRY RUN: {title} (no requests sent) ===")
    for head, rows in sections:
        print(f"\n[{head}]")
        for r in rows:
            print(f"  {r}")
    print(f"\n[input validation] {'OK' if not problems else 'PROBLEMS'}")
    for p in problems:
        print(f"  - {p}")
    return 0 if not problems else 3
