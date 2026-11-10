"""Prospective R23-4 one-factor DFlash serving sweep (VB-AK-R23-4-SWEEP-WIRE); never retrofits.

Native input: a producer run directory holding `results.jsonl` (63 `epyc.r23-4.request.v1`
rows: seven ordered fresh server arms x 3 prompts x 3 repeats, each with its raw SSE stream,
the original request, the server acceptance window, own-PID KFD samples, the mapped DSO
closure and the captured `native_identity`) and the producer-authored `native-comparisons.json`.

The reader reopens every request, re-derives the stream rate and the acceptance counts from
their raw bytes, re-derives each adjacent-baseline comparison (the median of the fresh
baseline before, the intervention arm, the fresh baseline after) and refuses (ProjectionError)
unless the producer's `native-comparisons.json` equals the re-derivation exactly. Acceptance is
a serial single-slot WINDOW association: it is never response-ID proof, so attribution stays
UNKNOWN on every tuple. Grading is the shared `claim_tuple.grade()`; this module carries no
ladder and emits no protocol id, p-value, causal or generalisation claim. An incomplete,
failed, reordered, mixed-identity, unwitnessed or outside-window sweep is refused, never
partially projected.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

AUTHORITY = "measurement"
SOURCE_KIND = "autokernel-r234-native-sweep"
ADAPTER_ID = "vidya.adapters.autokernel_r234_sweep/v1"
REQUEST_SCHEMA = "epyc.r23-4.request.v1"
IDENTITY_SCHEMA = "epyc.r234.native_identity.v1"
PACKET_SCHEMA = "epyc.r234.native_comparisons.v1"
ORDER = ("baseline", "context", "baseline", "kv", "baseline", "affinity", "baseline")
PINNED = frozenset(range(184, 192))
DESIGNED_BROAD = frozenset(range(24)) | PINNED
# The v10 private image this sweep was built against (a reproduction, not historical 9e18beb0).
SOURCE = "ffc1bac82eeca6f9099e1ccd9ba49703c460a115"
_BIN = "/mnt/raid0/llm/tmp/autokernel-rebuild/v10-verified"
HIP = _BIN + "/bin/libggml-hip.so.0.16.0"
HIP_SHA = "f26a166b8ea3089d19a395ae00afa22e917df8eba71ca6ef4be5235d65ea8079"
MODEL = "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf"
MODEL_SHA = "a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348"
DRAFT = "/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf"
DRAFT_SHA = "7f1c9a31a6ed40044c69f6508b50fd63b87abd8e1fb7fe4290303df549153751"
PROBE_SHA = "3feb7382f07acc1abb149c5d8dc8b94527f08768f385fccf15909496923a98b0"
SERVER = _BIN + "/bin/llama-server"
MANIFEST = _BIN + "/SHA256SUMS"
LIMITATION = ("Window association is not response-ID proof. No p-value, causal or "
              "generalization claim.")
_ACCEPT = re.compile(r"slot\s+print_timing:\s*id\s+(\d+)\s*\|\s*task\s+(\d+)\s*\|\s*draft acceptance\s*="
                     r"\s*([\d.]+)\s*\(\s*(\d+) accepted\s*/\s*(\d+) generated\s*\)")


def _canonical(x) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _require(ok, reason):
    if not ok:
        raise ProjectionError("R23-4 sweep refused: " + reason)


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _argv(i):
    argv = [SERVER, "-m", MODEL, "-md", DRAFT, "-c", str(4096 if i == 1 else 32768),
            "--host", "127.0.0.1", "--port", "18746", "-np", "1", "-t", "8", "-tb", "8",
            "-b", "2048", "-ub", "2048", "-ctk", "f16", "-ctv", "f16", "--device", "ROCm0",
            "-ngl", "99", "-fa", "on", "--metrics", "--slots", "-ngld", "99",
            "--spec-type", "draft-dflash", "--spec-draft-n-max", "8"]
    if i == 3:
        argv += ["--no-kv-unified"]
    if i == 5:
        argv = ["taskset", "-c", "184-191"] + argv
    return argv


def acceptance_window(text) -> dict:
    """Exactly one consistent `draft acceptance` line in the request window, else unknown."""
    found = list(_ACCEPT.finditer(text))
    if len(found) != 1:
        return {"state": "unknown"}
    slot, task, ratio, accepted, generated = found[0].groups()
    a, g = int(accepted), int(generated)
    if g <= 0 or a > g or abs(float(ratio) - a / g) > 0.00002:
        return {"state": "unknown"}
    return {"state": "window_correlated", "slot": int(slot), "task": int(task), "accepted": a,
            "generated": g, "ratio": float(ratio)}


def _spans(cpus):
    out = []
    for x in sorted(cpus):
        if out and out[-1][1] == x - 1:
            out[-1][1] = x
        else:
            out.append([x, x])
    return ",".join(str(a) if a == b else f"{a}-{b}" for a, b in out)


def _summarize(rows) -> dict:
    """Structural eligibility of the 63 requests and each adjacent-baseline comparison."""
    ident = (rows[0].get("native_identity") or {}) if rows else {}
    broad, grant = DESIGNED_BROAD, ident.get("grant") or {}
    if grant.get("allowed_cpus") is not None:
        cpus = grant["allowed_cpus"]
        _require(isinstance(cpus, list) and all(type(x) is int for x in cpus) and PINNED <= set(cpus),
                 "unusable recorded grant CPUs")
        broad = frozenset(cpus)
    seen, first_packet, previous_end = {}, None, None
    keys = [(i, p, k) for i in range(7) for p in range(3) for k in range(3)]
    for index, r in enumerate(rows):
        _require(not r.get("failure") and r.get("schema") == REQUEST_SCHEMA, "failed or wrong-schema request")
        i, p, k = r.get("arm_index"), r.get("prompt_index"), r.get("repeat")
        _require(all(type(x) is int for x in (i, p, k)) and 0 <= i < 7 and 0 <= p < 3 and 0 <= k < 3
                 and r.get("arm") == ORDER[i], "invalid arm or request key")
        _require((i, p, k) not in seen, "duplicate request")
        _require(index < len(keys) and (i, p, k) == keys[index], "unexpected actual request order")
        start, end = r.get("started_monotonic_s"), r.get("ended_monotonic_s")
        _require(_num(start) and _num(end) and start >= 0 and end > start
                 and (previous_end is None or start >= previous_end),
                 "missing, overlapping or invalid monotonic request interval")
        previous_end = end
        a, res = r.get("acceptance") or {}, r.get("residency") or {}
        _require(a.get("state") == "window_correlated" and res.get("resident"), "unknown acceptance or residency")
        ratio, rate = a.get("ratio"), r.get("client_stream_events_s")
        _require(_num(ratio) and _num(rate) and 0 <= ratio <= 1 and rate > 0, "invalid observation")
        packet = r.get("input_packet")
        _require(isinstance(packet, dict) and (
            packet.get("source_commit"), packet.get("model_sha256"), packet.get("draft_sha256"),
            packet.get("probe_sha256"), packet.get("expected_hip_sha256"), packet.get("expected_hip"),
        ) == (SOURCE, MODEL_SHA, DRAFT_SHA, PROBE_SHA, HIP_SHA, HIP), "missing or unexpected input identity")
        _require(packet.get("server") == SERVER and packet.get("closure_manifest") == MANIFEST,
                 "unexpected executable or manifest path")
        _require(r.get("argv") == _argv(i), "unexpected server invocation for arm")
        if first_packet is None:
            first_packet = packet
        _require(packet == first_packet, "mixed input identity")
        _require(r.get("run_id") and r.get("mapped_hip") == [HIP], "unexpected mapped HIP")
        pid, samples = r.get("server_pid"), res.get("samples")
        _require(type(pid) is int and pid > 0 and res.get("own_pid") == pid and isinstance(samples, list),
                 "missing own-PID GPU proof")
        readable = [x for x in samples if x is not None]
        _require(all(type(x) is int and x >= (1 << 30) for x in readable) and len(readable) >= 2
                 and res.get("readable") == len(readable), "invalid own-PID GPU proof")
        mask = r.get("host_affinity")
        _require(isinstance(mask, list) and all(type(x) is int for x in mask) and len(mask) == len(set(mask))
                 and set(mask) == (PINNED if i == 5 else broad), "unexpected host affinity")
        acc, gen = a.get("accepted"), a.get("generated")
        _require(type(acc) is int and type(gen) is int and gen > 0 and 0 <= acc <= gen
                 and abs(ratio - acc / gen) <= 0.00002, "inconsistent acceptance counts")
        seen[i, p, k] = r
    _require(len(seen) == 63 and len({r["run_id"] for r in seen.values()}) == 1, "incomplete or mixed runs")
    out = []
    for i in (1, 3, 5):
        for p in range(3):
            for label, get in (("acceptance_ratio", lambda r: r["acceptance"]["ratio"]),
                               ("client_stream_events_s", lambda r: r["client_stream_events_s"])):
                raw = [[get(seen[j, p, k]) for k in range(3)] for j in (i - 1, i, i + 1)]
                before, mid, after = (statistics.median(x) for x in raw)
                where = ("outside-observed-baseline" if mid < min(before, after) or mid > max(before, after)
                         else "within-observed-baseline")
                out.append({"factor": ORDER[i], "prompt_index": p, "metric": label,
                            "baseline_before_median": before, "intervention_median": mid,
                            "baseline_after_median": after, "classification": where, "raw_repetitions": raw})
    dev = ({"design_deviation": f"broad arm {len(broad)} CPUs ({_spans(broad)}) vs designed "
                                f"{len(DESIGNED_BROAD)} ({_spans(DESIGNED_BROAD)})"}
           if broad != DESIGNED_BROAD else {})
    return {**dev, "status": "complete-descriptive", "units": 63,
            "run_id": next(iter(seen.values()))["run_id"], "comparisons": out, "limitations": LIMITATION}


def _closure_approved(identity):
    """The captured source closure must equal the producer's own SOURCE.json pin, and the files still match."""
    closure = identity.get("source_closure")
    _require(isinstance(closure, dict) and closure, "missing captured source closure")
    entry = next(iter(closure.values()))
    pin = Path(str(entry.get("path", ""))).parent / "SOURCE.json"
    try:
        expected = json.loads(pin.read_text())
    except (OSError, ValueError) as exc:
        raise ProjectionError(f"R23-4 sweep refused: producer SOURCE.json unreadable: {exc}") from exc
    _require(set(closure) == set(expected) and all(
        isinstance(closure[k], dict) and closure[k].get("sha256") == v for k, v in expected.items()),
        "captured source closure is not the approved candidate")
    for k, v in expected.items():
        try:
            now = hashlib.sha256(Path(closure[k]["path"]).read_bytes()).hexdigest()
        except OSError as exc:
            raise ProjectionError(f"R23-4 sweep refused: pinned producer file unreadable: {k}") from exc
        _require(now == v, f"pinned producer file changed since capture: {k}")


def _rederive_request(r, identity, grant):
    _require(r.get("native_identity") == identity and r.get("disposition") == "complete", "mixed identity or disposition")
    _require(grant["captured_at"] <= r["started_at"] <= float(grant["environment"]["FILLER_DEADLINE"]),
             "request outside captured grant deadline")
    cap = r.get("stream_capture") or {}
    _require(cap.get("completed") is True and (cap.get("request") or {}).get("messages")
             == [{"role": "user", "content": r.get("prompt")}], "missing original request")
    times, done = [], False
    for e in cap.get("events", []):
        line, ts = e["raw"].strip(), e["elapsed_s"]
        _require(_num(ts) and ts >= 0, "invalid event time")
        if line == "data: [DONE]":
            done = True
            continue
        if line.startswith("data: "):
            delta = json.loads(line[6:])["choices"][0].get("delta", {})
            if delta.get("content") or delta.get("reasoning_content"):
                times.append(ts)
    _require(done and len(times) >= 2 and times == sorted(times) and times[-1] > times[0], "incomplete stream")
    _require(math.isclose(len(times) / (times[-1] - times[0]), r["client_stream_events_s"], rel_tol=0.0001),
             "stream rate does not rederive")
    a = acceptance_window(r["acceptance"]["raw"])
    _require(all(a.get(k) == r["acceptance"].get(k) for k in ("state", "accepted", "generated", "ratio", "slot", "task")),
             "acceptance does not rederive")
    _require(r.get("response_id_attribution") == "UNKNOWN", "window attribution overclaim")
    ts = r["residency"].get("sample_monotonic_s", [])
    _require(len(ts) == len(r["residency"]["samples"]) and len(ts) >= 2 and ts == sorted(ts)
             and all(_num(t) and r["started_monotonic_s"] <= t <= r["ended_monotonic_s"] for t in ts),
             "residency window mismatch")
    dsos = r.get("mapped_closure") or []
    _require(any(d.get("path") == r["mapped_hip"][0] and d.get("sha256") == r["input_packet"]["expected_hip_sha256"]
                 for d in dsos), "mapped DSO digest missing")


def _native(rows) -> dict:
    result = _summarize(rows)
    identity = rows[0].get("native_identity")
    _require(isinstance(identity, dict) and identity.get("schema") == IDENTITY_SCHEMA, "pre-hook source: no prospective identity")
    _closure_approved(identity)
    grant = identity.get("grant") or {}
    _require(grant.get("raw") and grant.get("environment") and _num(grant.get("captured_at")), "missing grant")
    arm_pids = {}
    for r in rows:
        _rederive_request(r, identity, grant)
        arm_pids.setdefault(r["arm_index"], set()).add(r["server_pid"])
    _require(all(len(v) == 1 for v in arm_pids.values()) and len({next(iter(v)) for v in arm_pids.values()}) == 7,
             "fresh server arms missing")
    result["response_id_attribution"] = "UNKNOWN"
    return result


def _outcome(c) -> str:
    """The carrier's normalized outcome word for one descriptive comparison (outcome_native keeps the
    producer's own). Both metrics are higher-is-better. The intervention median outside the range of
    its two adjacent fresh-baseline medians is `improved` above and `regressed` below; inside it is
    `null`. Descriptive only: no p-value, no causal claim, no `decisive` flag; grade() is untouched."""
    mid, lo, hi = c["intervention_median"], min(c["baseline_before_median"], c["baseline_after_median"]), \
        max(c["baseline_before_median"], c["baseline_after_median"])
    if c["classification"] == "within-observed-baseline":
        return "null"
    return "improved" if mid > hi else "regressed"


#: Operator ruling 2026-11-10: R23-4 claims are low-confidence descriptive evidence. The carrier has no
#: confidence field and the planner line renders only `outcome_native` and `decisive`, so the marker
#: rides in both (the producer's own word stays first in `outcome_native` and verbatim in `extra`).
LOW_CONFIDENCE = "descriptive, low confidence, no causal claim"


def _mappings(rows, result, sha, locator, *, marked=True) -> list[dict]:
    first, out = rows[0], []
    for c in result["comparisons"]:
        out.append(dict(
            measurement_id=f"r234:{result['run_id']}:{c['factor']}:{c['prompt_index']}:{c['metric']}",
            metric=c["metric"], value=c["intervention_median"],
            date=datetime.fromtimestamp(first["started_at"], timezone.utc).date().isoformat(),
            category="CANDIDATE",
            claim=(f"R23-4 {c['factor']} prompt {c['prompt_index']} {c['metric']} median over three requests "
                   "with adjacent fresh baselines; response-ID attribution UNKNOWN"),
            metric_direction="higher_better", protocol_id="", reps=3,
            reps_basis="scored:requests within one fresh server arm; not independent launches",
            unit="ratio" if c["metric"] == "acceptance_ratio" else "events/s",
            attestation_path=locator, attestation_locator=locator, attestation_sha256=sha,
            attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
            applicability=dict(model_file=first["native_identity"]["model"]["path"],
                               model_sha256=first["input_packet"]["model_sha256"], quant="Q8_0",
                               build_sha=first["input_packet"]["source_commit"], backend="gpu",
                               run_id=result["run_id"], scope_basis="native", knob_family=c["factor"]),
            observation=dict(outcome=_outcome(c),
                             outcome_native=(f"{c['classification']}; {LOW_CONFIDENCE}" if marked
                                             else c["classification"]),
                             anchor_value=c["baseline_before_median"],
                             **({"decisive": False} if marked else {}),
                             outcome_reason="Descriptive adjacent-baseline comparison; "
                                            "window-only acceptance attribution UNKNOWN"),
            extra=dict(adapter=ADAPTER_ID, adjacent_baselines=[c["baseline_before_median"], c["baseline_after_median"]],
                       raw_repetitions=c["raw_repetitions"], response_id_attribution="UNKNOWN",
                       producer_outcome_native=c["classification"], confidence=LOW_CONFIDENCE,
                       drafter=Path(first["native_identity"]["drafter"]["path"]).name,
                       drafter_sha256=first["input_packet"]["draft_sha256"],
                       grant_id=first["native_identity"]["grant"]["environment"].get("FILLER_ID"),
                       design_deviation=result.get("design_deviation"))))
    return out


def _covers(authored, derived) -> bool:
    """Every field the producer authored at write time equals the re-derivation (the locator is
    location, not content; nested declarations are compared field by field, extra fields are ours)."""
    if not isinstance(authored, dict):
        return False
    for key, value in authored.items():
        if key == "attestation_locator":
            continue
        if key not in derived:
            return False
        if isinstance(value, dict):
            if not _covers(value, derived[key]):
                return False
        elif value != derived[key]:
            return False
    return True


def _results_path(unit) -> Path:
    p = Path(unit)
    return p / "results.jsonl" if p.is_dir() else p


@lru_cache(maxsize=8)
def _derive(path: str, sha: str) -> tuple:
    p = Path(path)
    try:
        raw = p.read_bytes()
        rows = [json.loads(s) for s in raw.splitlines() if s.strip()]
        packet = json.loads(p.with_name("native-comparisons.json").read_text())
    except (OSError, ValueError) as exc:
        raise ProjectionError(f"R23-4 sweep refused: unreadable capture or native comparisons: {exc}") from exc
    _require(hashlib.sha256(raw).hexdigest() == sha and len(raw) <= 64 << 20 and rows, "capture changed or empty")
    try:
        result = _native(rows)
        expected = _mappings(rows, result, sha, str(p))
        producer_view = _mappings(rows, result, sha, str(p), marked=False)
    except ProjectionError:
        raise
    except (KeyError, TypeError, IndexError, ValueError, AttributeError) as exc:
        raise ProjectionError(f"R23-4 sweep refused: malformed record: {type(exc).__name__}: {exc}") from exc
    _require(isinstance(packet, dict) and packet.get("schema") == PACKET_SCHEMA and packet.get("request_sha256") == sha
             and packet.get("comparison") == result, "native comparison does not rederive from the requests")
    mapped = packet.get("belief_measurements")
    _require(isinstance(mapped, list) and len(mapped) == len(expected)
             and all(_covers(m, e) for m, e in zip(mapped, producer_view)), "native measurement mapping mismatch")
    return tuple(json.dumps(m, sort_keys=True) for m in expected)


def native_rows(unit):
    """One native row per re-derived adjacent-baseline comparison; any defect refuses the whole sweep."""
    p = _results_path(unit)
    try:
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError as exc:
        raise ProjectionError(f"R23-4 sweep refused: unreadable capture: {exc}") from exc
    derived = _derive(str(p), sha)
    return tuple({"path": str(p), "sha256": sha, "measurement_id": json.loads(m)["measurement_id"]}
                 for m in derived)


@register(SOURCE_KIND)
def project(row):
    derived = [json.loads(m) for m in _derive(row["path"], row["sha256"])]
    match = [m for m in derived if m["measurement_id"] == row["measurement_id"]]
    _require(len(match) == 1, "unknown measurement id")
    return ClaimTuple(**match[0])
