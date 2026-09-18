"""TD-1d measurement driver (2026-09-18).

Runs the JSON baseline and the native arms on the SAME 24-question catalogue,
SAME server (:8199, frozen-v9 HIP llama-server, Qwen3.6-35B-A3B-Q8_0) and SAME
sampling, interleaved A/B/A/B over n rounds, with GPU residency sampled DURING
the window. Writes one bench-shaped JSON per arm plus a summary.

Why a direct /completion adapter instead of LLMPrimitives:
  * `frontdoor` currently routes /v1/chat/completions in LLMPrimitives
    (use_chat_completions=True) and that path never forwards `grammar` or
    `json_schema` -> the serial native arm fails mechanically (measured today:
    515 free-form tokens vs 523 layout, 0/24 decisions). TD-1c's 523-token run
    can only have gone through /completion.
  * In-process concurrent llm_calls are serialized by the cross-process
    inference_lock (probe: parallel wall == serial wall, max 1 slot busy), so
    option (b) cannot be exercised through the primitives object at all.
The adapter mirrors LlamaServerBackend._build_payload exactly (temperature 0.0,
top_k 40, top_p 0.95, repeat_penalty 1.1, seed, cache_prompt=True, grammar /
json_schema, n_probs<=128) so every arm shares one sampling contract.
"""
from __future__ import annotations

import json
import statistics
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, "/workspace/repos/epyc-orchestrator")

from src.typed_decisions.bench import _agreement, _arm_record, _load_questions, _load_state  # noqa: E402
from src.typed_decisions.native import (  # noqa: E402
    CueStyle,
    run_typed_decisions_native,
    run_typed_decisions_native_parallel,
)
from src.typed_decisions.runner import run_typed_decisions  # noqa: E402

BASE = "http://127.0.0.1:8199"
ROLE = "frontdoor"
OUT = Path("/workspace/tmp/td1d-20260918")
QFILE = "/workspace/artifacts/typed_decisions/decision_set_v1/questions.json"
SFILE = "/workspace/artifacts/typed_decisions/decision_set_v1/state.json"
ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 4
WORKERS = 3          # slots 1..3; slot 0 is pinned to the JSON arm so its prompt never evicts a native checkpoint
JSON_SLOT = 0


class DirectCompletion:
    """Primitives-shaped seam posting straight to llama-server /completion."""

    mock_mode = False

    def __init__(self, base_url: str = BASE, slot_base: int | None = None, fixed_slot: int | None = None) -> None:
        self.base_url = base_url
        self.slot_base = slot_base      # parallel runner passes slot_id=worker; we map worker -> slot_base+worker
        self.fixed_slot = fixed_slot    # serial arms: pin every call to one slot
        self.server_urls = {ROLE: base_url}
        self._client = httpx.Client(timeout=httpx.Timeout(connect=5, read=600, write=60, pool=30))
        self._last_inference_meta: dict | None = None
        self.calls: list[dict] = []

    def llm_call(self, prompt, *, role=ROLE, n_tokens=None, json_schema=None, grammar=None,
                 temperature=None, seed=None, n_probs=None, top_k=None, top_p=None,
                 slot_id=None, **_):
        payload = {
            "prompt": prompt,
            "n_predict": int(n_tokens) if n_tokens else -1,
            "cache_prompt": True,
            "temperature": 0.0 if temperature is None else float(temperature),
            "top_k": 40 if top_k is None else int(top_k),
            "top_p": 0.95 if top_p is None else float(top_p),
            "repeat_penalty": 1.1,
            "seed": 0 if seed is None else int(seed),
            "stream": False,
        }
        if json_schema:
            payload["json_schema"] = json_schema
        if grammar:
            payload["grammar"] = grammar
        if n_probs is not None and int(n_probs) > 0:
            payload["n_probs"] = min(128, int(n_probs))
        if self.fixed_slot is not None:
            payload["id_slot"] = int(self.fixed_slot)
        elif slot_id is not None:
            payload["id_slot"] = int(slot_id) + (self.slot_base or 0)
        started = time.perf_counter()
        try:
            response = self._client.post(f"{self.base_url}/completion", json=payload)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:  # noqa: BLE001
            self._last_inference_meta = {"role": role, "transport": "direct_completion",
                                         "completion_reason": "exception", "error": str(exc)}
            return f"[ERROR: {exc}]"
        elapsed = (time.perf_counter() - started) * 1000.0
        timings = data.get("timings") or {}
        meta = {
            "role": role,
            "transport": "direct_completion",
            "elapsed_ms": elapsed,
            "tokens": data.get("tokens_predicted"),
            "prompt_n": timings.get("prompt_n"),
            "cache_n": timings.get("cache_n"),
            "prompt_ms": timings.get("prompt_ms"),
            "gen_ms": timings.get("predicted_ms"),
            "id_slot": data.get("id_slot"),
            "completion_reason": data.get("stop_type"),
            "completion_probabilities": list(data.get("completion_probabilities") or []),
        }
        self._last_inference_meta = meta
        self.calls.append({k: v for k, v in meta.items() if k != "completion_probabilities"})
        return data.get("content", "")


def rocm_mem_sample() -> dict:
    try:
        out = subprocess.run(["rocm-smi", "--showmemuse"], capture_output=True, text=True, timeout=20).stdout
    except Exception as exc:  # noqa: BLE001
        return {"ts": datetime.now(timezone.utc).isoformat(), "error": str(exc)}
    vram = next((line.split(":")[-1].strip() for line in out.splitlines()
                 if "GPU Memory Allocated (VRAM%)" in line), None)
    return {"ts": datetime.now(timezone.utc).isoformat(), "vram_allocated_pct": vram}


def kfd_procs() -> int | None:
    try:
        out = subprocess.run(["rocm-smi", "--showpids"], capture_output=True, text=True, timeout=20).stdout
        return sum(1 for line in out.splitlines() if "llama" in line)
    except Exception:  # noqa: BLE001
        return None


class Sampler(threading.Thread):
    def __init__(self, period_s: float = 8.0) -> None:
        super().__init__(daemon=True)
        self.period_s = period_s
        self.stop = threading.Event()
        self.samples: list[dict] = []
        self.slot_busy: list[dict] = []
        self.phase = "idle"

    def run(self) -> None:
        client = httpx.Client(timeout=2)
        last_mem = 0.0
        while not self.stop.is_set():
            now = time.monotonic()
            if now - last_mem >= self.period_s:
                sample = rocm_mem_sample()
                sample["phase"] = self.phase
                self.samples.append(sample)
                last_mem = now
            try:
                slots = client.get(f"{BASE}/slots").json()
                busy = sum(1 for s in slots if s.get("is_processing"))
                self.slot_busy.append({"t": time.time(), "phase": self.phase, "busy": busy})
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.1)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    questions = _load_questions(QFILE)
    state = _load_state(SFILE)
    health = httpx.get(f"{BASE}/health", timeout=5).json()
    props = httpx.get(f"{BASE}/props", timeout=5).json()
    assert health.get("status") == "ok", health

    json_seam = DirectCompletion(fixed_slot=JSON_SLOT)
    serial = DirectCompletion()                       # serial native arms: server picks the slot by prefix similarity
    pool = [DirectCompletion(slot_base=1) for _ in range(WORKERS)]   # worker i -> slot 1+i
    pq = dict(state=state, questions=questions, role=ROLE, pin_slots=True, warm_prefix=True)

    arms = {
        "json": lambda: run_typed_decisions(json_seam, state=state, questions=questions, role=ROLE, mode="json"),
        "native_full": lambda: run_typed_decisions_native(serial, state=state, questions=questions, role=ROLE, cue_style=CueStyle.FULL),
        "native_short": lambda: run_typed_decisions_native(serial, state=state, questions=questions, role=ROLE, cue_style=CueStyle.SHORT),
        "native_id_only": lambda: run_typed_decisions_native(serial, state=state, questions=questions, role=ROLE, cue_style=CueStyle.ID_ONLY),
        "native_pq1": lambda: run_typed_decisions_native_parallel(pool[:1], cue_style=CueStyle.FULL, **pq),
        "native_pq3": lambda: run_typed_decisions_native_parallel(pool, cue_style=CueStyle.FULL, **pq),
        "native_pq3_id_only": lambda: run_typed_decisions_native_parallel(pool, cue_style=CueStyle.ID_ONLY, **pq),
    }
    order = list(arms)

    sampler = Sampler()
    sampler.start()
    sampler.samples.append({**rocm_mem_sample(), "phase": "before", "kfd_llama_procs": kfd_procs()})

    def run_arm(name: str, round_index: int, timed: bool) -> dict:
        sampler.phase = f"r{round_index}:{name}" if timed else f"warm:{name}"
        holder = pool[0] if name.startswith("native_pq") else (json_seam if name == "json" else serial)
        started = time.perf_counter()
        result = arms[name]()
        wall_ms = (time.perf_counter() - started) * 1000.0
        meta = holder._last_inference_meta or {}
        record = _arm_record(name, result, wall_ms, meta)
        record["server_meta"] = {k: meta.get(k) for k in ("id_slot", "prompt_n", "cache_n", "prompt_ms", "gen_ms", "transport")}
        layout = getattr(holder, "_last_native_layout", None)
        if isinstance(layout, dict) and layout.get("shape") == "per_question_parallel":
            record["per_request"] = layout.get("per_request")
            record["warm_requests"] = layout.get("warm_requests")
            record["workers"] = layout.get("workers")
            record["tokens_generated"] = sum((r or {}).get("tokens") or 0 for r in layout.get("per_request") or [])
            record["server_meta"] = None
        record["round"] = round_index
        record["timed"] = timed
        record["_result"] = result
        print(f"[{'r%d' % round_index if timed else 'warm'}] {name:20s} wall={wall_ms/1000:7.2f}s "
              f"decisions={len(result.decisions):2d} failures={len(result.failures):2d} "
              f"reasons={sorted({f.reason for f in result.failures})}", flush=True)
        return record

    # Warm-up: one untimed pass per arm. Each arm's prefix lands in the prompt
    # cache (parallel arms: on all four slots; serial arms: on the slot the
    # server picks and re-selects by prefix similarity).
    warm = {name: run_arm(name, 0, timed=False) for name in order}

    rounds: list[dict[str, dict]] = []
    for r in range(1, ROUNDS + 1):
        rotated = order[(r - 1) % len(order):] + order[: (r - 1) % len(order)]
        records = {}
        for name in rotated:
            records[name] = run_arm(name, r, timed=True)
        rounds.append(records)

    sampler.phase = "after"
    sampler.samples.append({**rocm_mem_sample(), "phase": "after", "kfd_llama_procs": kfd_procs()})
    sampler.stop.set()
    sampler.join()

    # Per-arm bench-shaped artifacts + summary.
    def strip(rec: dict) -> dict:
        return {k: v for k, v in rec.items() if k != "_result"}

    summary: dict = {
        "benchmark": "typed_decisions_modes",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "server": {"base_url": BASE, "model_path": props.get("model_path"), "total_slots": props.get("total_slots"),
                   "n_ctx_per_slot": (props.get("default_generation_settings") or {}).get("n_ctx"),
                   "build": {k: props.get(k) for k in ("build_info", "version")}},
        "transport": "direct /completion (see module docstring); sampling temp=0 top_k=40 top_p=0.95 repeat_penalty=1.1 seed=0 cache_prompt=true",
        "rounds": ROUNDS,
        "questions": [q.id for q in questions],
        "arms": {},
        "residency_samples": sampler.samples,
        "slot_busy_max_by_phase": {},
        "verdict": None,
    }
    by_phase: dict[str, int] = {}
    for s in sampler.slot_busy:
        by_phase[s["phase"]] = max(by_phase.get(s["phase"], 0), s["busy"])
    summary["slot_busy_max_by_phase"] = by_phase

    json_walls = [rounds[i]["json"]["wall_ms"] for i in range(ROUNDS)]
    for name in order:
        walls = [rounds[i][name]["wall_ms"] for i in range(ROUNDS)]
        per_round = []
        agree_total = comp_total = 0
        for i in range(ROUNDS):
            j = rounds[i]["json"]["_result"]
            a = rounds[i][name]["_result"]
            ag = _agreement(questions, {"json": j, name: a}) if name != "json" else None
            if ag:
                agree_total += ag["agreeing"]
                comp_total += ag["comparable"]
            per_round.append({
                "round": i + 1,
                "arms": {"json": strip(rounds[i]["json"]), name: strip(rounds[i][name])},
                "agreement": ag,
            })
        speedups = [json_walls[i] / walls[i] for i in range(ROUNDS)]
        arm_summary = {
            "n": ROUNDS,
            "wall_ms": walls,
            "wall_mean_ms": statistics.mean(walls),
            "wall_stdev_ms": statistics.stdev(walls) if ROUNDS > 1 else 0.0,
            "wall_min_ms": min(walls), "wall_max_ms": max(walls),
            "speedup_vs_json_per_round": speedups,
            "speedup_vs_json_mean_of_means": statistics.mean(json_walls) / statistics.mean(walls),
            "agreement_pooled": {"agreeing": agree_total, "comparable": comp_total,
                                 "rate": (agree_total / comp_total) if comp_total else None} if name != "json" else None,
            "agreement_per_round": [pr["agreement"] and {"agreeing": pr["agreement"]["agreeing"], "comparable": pr["agreement"]["comparable"],
                                                        "unresolved_pairs": pr["agreement"]["unresolved_pairs"],
                                                        "disagreements": pr["agreement"]["disagreements"]} for pr in per_round],
            "decisions_per_round": [len(rounds[i][name]["_result"].decisions) for i in range(ROUNDS)],
            "failure_reasons_per_round": [sorted({f.reason for f in rounds[i][name]["_result"].failures}) for i in range(ROUNDS)],
            "tokens_generated_per_round": [rounds[i][name]["tokens_generated"] for i in range(ROUNDS)],
        }
        summary["arms"][name] = arm_summary
        artifact = {
            "benchmark": "typed_decisions_modes",
            "timestamp": summary["timestamp"],
            "state_sha256": __import__("hashlib").sha256(state.encode()).hexdigest(),
            "role": ROLE,
            "questions": summary["questions"],
            "modes": ["json", name],
            "cue_styles": [rounds[0][name].get("cue_style")],
            "arms": per_round[0]["arms"],
            "agreement": per_round[0]["agreement"],
            "agreements": {name: per_round[0]["agreement"]},
            "repeats": per_round,
            "warmup": {"json": strip(warm["json"]), name: strip(warm[name])},
            "summary": arm_summary,
            "server": summary["server"],
            "transport": summary["transport"],
        }
        (OUT / f"bench-td1d-{name}.json").write_text(json.dumps(artifact, indent=2, sort_keys=True, default=str) + "\n")

    # JSON self-consistency across rounds (is the baseline itself stable?).
    j0 = rounds[0]["json"]["_result"]
    summary["json_self_consistency"] = [
        {"round": i + 1, **{k: v for k, v in _agreement(questions, {"json_r1": j0, f"json_r{i+1}": rounds[i]["json"]["_result"]}).items()
                            if k in ("comparable", "agreeing", "disagreements")}}
        for i in range(1, ROUNDS)
    ]
    verdict = []
    for name, a in summary["arms"].items():
        if name == "json":
            continue
        ag = a["agreement_pooled"]
        min_round_rate = min((pr["agreeing"] / pr["comparable"]) if pr and pr["comparable"] else 0.0 for pr in a["agreement_per_round"])
        passes = a["speedup_vs_json_mean_of_means"] >= 10.0 and min_round_rate >= 15 / 16
        verdict.append({"arm": name, "speedup_mean": a["speedup_vs_json_mean_of_means"],
                        "agreement_pooled": ag, "min_round_agreement_rate": min_round_rate, "passes_bar": passes})
    summary["verdict"] = verdict
    (OUT / "summary-td1d.json").write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n")
    (OUT / "calls-serial.json").write_text(json.dumps(serial.calls, indent=1) + "\n")
    print(json.dumps({"verdict": verdict, "slot_busy_max_by_phase": by_phase}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
