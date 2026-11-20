#!/usr/bin/python3
"""M-12k (GPU rework): frontdoor answer quality, memory-on vs memory-off, on the LIVE /chat path. Rule: PREDECLARED.md (decision rule unchanged from m12k-20261119T0208Z).

Canonical successor of scratch job.py SHA-256 94491eec07c6eaf845c17cd979390f34361d1c18cf3df39d3585ea74a233560f.
Non-200 routing evidence repair: M-12k-UNSERVED-DETECT, 2026-11-20.

Backend moved to the MI210: the row's launcher (job-gpu.sh) serves its own frontdoor (:8070) and ONE embedder (:8090) on the GPU; this stdlib HTTP client preserves error response routing evidence.
M12K_RUN_DIR and M12K_ROW_ID select a fresh row at publication. Same server for both arms, so the accuracy pairing is unaffected; latency is descriptive only.

Arms (interleaved per item, concurrency 1, same server):
  ON   POST /chat real_mode, no episodic_lookups key (production behaviour)
  OFF  same body + "episodic_lookups": false   (skips the four episodic lookups; code f644f5f7, branch m12k/episodic-lookup-switch)
  ON2  A/A floor: ON again on the first 30 shuffled items
Every request carries x_request_source=probe (no episodic scoring; routing unchanged), so the store stays at 64,514 rows.

Modes: FILLER_SMOKE=1 / FILLER_DRYRUN=1 -> plumbing smoke only (preflight + 2 pilot items x 2 arms, never scored).
Exit codes: 0 terminal verdict written | 75 STOP file / deadline (resumable) | 3 smoke failure | 2 refused (seal/identity).
Writes only under out/. Stdlib only. Runs inside the grant's host threads (taskset FILLER_CPUS = 184-191), at most 8 of them; never the production quarters.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import sys
import time
import urllib.error
import urllib.request

ID = os.environ.get("M12K_ROW_ID", "m12k-gpu-frontdoor-memory-ab-20261119")
D = os.environ.get("M12K_RUN_DIR", "/mnt/raid0/llm/tmp/m12k-gpu-20261119T1500Z")
OUT = f"{D}/out"
API = os.environ.get("M12K_API", "http://127.0.0.1:8000")
RESEARCH = "/mnt/raid0/llm/epyc-inference-research"
EPISODIC_DB = "/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/sessions/episodic.db"
EXPECTED_ROWS = 64514
CODE_COMMIT = "f644f5f726c639c4438caa0b08aac843b4f97c7d"
REQUEST_TIMEOUT_S = 400.0

PINS = {
    f"{RESEARCH}/data/kernel-v8-candidate/quality-gate/run-20260725T204443Z-fullcontract-both-mode/questions.json":
        "1532906b4a754673937027e73e2023d8eee7ed5d08f084c207a60ac81460adb1",
    f"{RESEARCH}/data/ufh13-thesis/pilot_pool.json": "0898013e86b365d89cf941205e19e3843d4d3cd21f869d4db917496f030aa3c5",
    f"{RESEARCH}/scripts/benchmark/answer_scoring.py": "4a1498cdd59c21b2e01415888b219ef529c4caf9ba24306e0285a305d298fbfd",
    f"{RESEARCH}/scripts/benchmark/thesis_ufh13/suite.py": "e63113cb895faa713ad998cf1c85956425b34310f8522ae5bb589a300b839328",
    f"{RESEARCH}/scripts/benchmark/thesis_ufh13/pilot_pool.py": "0dc5d154fce991c86bcb3028dc2f356de87838984bb22f9db8186c1307be02b3",
    f"{RESEARCH}/scripts/benchmark/thesis_ufh13/__init__.py": "7fa4ad40ebca8cf34efbcf7aff207a054949c427f8f11c5653708e31cd6a8178",
}
MEMORY_STRATEGIES = {"learned", "learned_explore", "action_outcome", "classifier", "risk_abstain_escalate"}
ITEM_SEED, ARM_SEED, BOOT_SEED, SMOKE_SEED = 20261119, 20261120, 20261119, 7
LOOKS = (100, 200, 300, 395)
N_PLANNED, N_AA = 395, 30
PRACTICAL = 0.03
# AMENDMENT 2026-11-19 (pre-data, PREDECLARED.md section 10): roles this row's :8070 server answers for (frontdoor + its aliases, launch_manifest port_map).
SERVED_ROLES = {"frontdoor", "worker", "worker_summarize", "worker_general"}
UNSERVED_RX = ("connect", "refused", "unreachable", "unavailable", "no server", "not served", "no backend", "circuit", "breaker", "all connection attempts")
UNSERVED_MAX_FRAC = 0.10
SMOKE = os.environ.get("FILLER_SMOKE") == "1" or os.environ.get("FILLER_DRYRUN") == "1"


# ---------------------------------------------------------------- small helpers
def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def append_jsonl(path: str, obj) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(obj, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())


def read_jsonl(path: str) -> list:
    if not os.path.exists(path):
        return []
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    return rows


def should_stop() -> bool:
    sf, dl = os.environ.get("FILLER_STOPFILE"), os.environ.get("FILLER_DEADLINE")
    if sf and os.path.exists(sf):
        return True
    if dl:
        try:
            return time.time() >= float(dl)
        except ValueError:
            return False
    return os.path.exists(f"{D}/STOP")


def pin_cpus() -> dict:
    """GPU row: the launcher tasksets this client to the grant's host threads (FILLER_CPUS, 184-191); the client is tiny, so keep at most 8 of the cores it was given.
    Refuse if the affinity reaches production cores 0-87 / 96-183 (a client outside its grant)."""
    allowed = sorted(os.sched_getaffinity(0))
    outside = [c for c in allowed if c not in set(range(184, 192))]
    if os.environ.get("FILLER_CPUS") and outside:
        raise SystemExit(f"refused: affinity {outside[:6]}... is outside the grant's host threads 184-191 (launch it through job-gpu.sh)")
    keep = set(allowed[:8])
    os.sched_setaffinity(0, keep)
    return {"cpus": sorted(os.sched_getaffinity(0)), "grant_cpus_env": os.environ.get("FILLER_CPUS")}


# ---------------------------------------------------------------- statistics
def mcnemar_exact_p(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2.0 ** n
    return min(1.0, 2.0 * tail)


def clopper_upper(x: int, n: int, alpha: float = 0.05) -> float:
    """Exact upper bound for a binomial proportion (two-sided 1-alpha interval)."""
    if n == 0:
        return 1.0
    if x >= n:
        return 1.0
    if x == 0:
        return 1.0 - (alpha / 2.0) ** (1.0 / n)
    lo, hi = x / n, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2.0
        cdf = sum(math.comb(n, i) * mid ** i * (1 - mid) ** (n - i) for i in range(0, x + 1))
        if cdf > alpha / 2.0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def conditional_power(s_k: int, k: int, b_plus_c: int, n_final: int = N_PLANNED, delta: float = PRACTICAL) -> float:
    """P(final two-sided 0.05 McNemar-normal rejection | data so far, true d = delta), pi_d re-estimated (floor 0.02)."""
    pi = max(0.02, b_plus_c / k) if k else 0.02
    rest = n_final - k
    thresh = 1.96 * math.sqrt(n_final * pi)
    mu, sd = rest * delta, math.sqrt(max(rest * pi, 1e-9))
    # S_N = s_k + R, R ~ N(mu, sd^2); reject if S_N > thresh or S_N < -thresh
    p_hi = 1.0 - _phi((thresh - s_k - mu) / sd)
    p_lo = _phi((-thresh - s_k - mu) / sd)
    return min(1.0, p_hi + p_lo)


def percentile(vals, q):
    s = sorted(vals)
    if not s:
        return None
    i = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
    return s[i]


def median(vals):
    return percentile(vals, 0.5)


def paired_bootstrap_ci(pairs, reps=10000, seed=BOOT_SEED):
    """pairs: list of (suite, diff in {-1,0,1}); stratified by suite; returns (lo, hi) for mean diff."""
    by = {}
    for s, dv in pairs:
        by.setdefault(s, []).append(dv)
    rng = random.Random(seed)
    n = sum(len(v) for v in by.values())
    out = []
    for _ in range(reps):
        tot = 0
        for v in by.values():
            m = len(v)
            tot += sum(v[rng.randrange(m)] for _ in range(m))
        out.append(tot / n)
    out.sort()
    return out[int(0.025 * reps)], out[int(0.975 * reps) - 1]


# ---------------------------------------------------------------- records -> pairs
def pair_up(records):
    by = {}
    for r in records:
        by.setdefault(r["item_id"], {})[r["arm"]] = r
    return {k: v for k, v in by.items() if "ON" in v and "OFF" in v}


def is_unserved(payload_ok: bool, answer: str, routed_to, role_history,
                *, http_status=None, error_detail="") -> bool:
    """Require response-local role AND backend-failure evidence, never status alone.

    HTTP errors from /chat preserve ChatResponse routing fields. Pre-routing
    errors, including bare 429/503 responses, have no such evidence and remain
    ordinary infrastructure failures. The original HTTP-200 rule is unchanged.
    """
    roles = {routed_to} if isinstance(routed_to, str) and routed_to else set()
    if isinstance(role_history, list):
        roles.update(r for r in role_history if isinstance(r, str) and r)
    if not (roles - SERVED_ROLES):
        return False
    if payload_ok:
        return answer.startswith("[ERROR") and any(k in answer.lower() for k in UNSERVED_RX)
    if not isinstance(http_status, int) or not 400 <= http_status <= 599:
        return False
    low = (answer + " " + error_detail).lower()
    backend_errors = UNSERVED_RX + ("timeout", "timed out", "backend", "admission", "queue full", "rate limit", "role_parked")
    return any(k in low for k in backend_errors)


def is_voided(pair) -> bool:
    return bool(pair["ON"].get("unserved") or pair["OFF"].get("unserved"))


def role_dist(pairs_subset):
    out = {"ON": {}, "OFF": {}}
    for p in pairs_subset:
        for arm in ("ON", "OFF"):
            k = str(p[arm].get("routed_to") or "")
            out[arm][k] = out[arm].get(k, 0) + 1
    return out


def summarize_look(records, n_pairs):
    allpairs = pair_up(records)
    ids_all = [r["item_id"] for r in records if r["arm"] == "ON" and r["item_id"] in allpairs]
    ids_all = list(dict.fromkeys(ids_all))[:n_pairs]
    voided_ids = [i for i in ids_all if is_voided(allpairs[i])]
    ids = [i for i in ids_all if i not in set(voided_ids)]
    pairs = allpairs
    b = c = div = 0
    s_k = 0
    mem_on = mem_off_bad = 0
    err = {"ON": 0, "OFF": 0}
    for i in ids:
        on, off = pairs[i]["ON"], pairs[i]["OFF"]
        dv = int(on["correct"]) - int(off["correct"])
        s_k += dv
        b += dv == 1
        c += dv == -1
        div += (on.get("routed_to") or "") != (off.get("routed_to") or "")
        mem_on += on.get("routing_strategy") in MEMORY_STRATEGIES
        mem_off_bad += off.get("routing_strategy") in MEMORY_STRATEGIES
        err["ON"] += on["status"] != "ok"
        err["OFF"] += off["status"] != "ok"
    n = len(ids)  # VALID pairs (voided UNSERVED pairs excluded from every statistic)
    return {"n_pairs": n, "n_pairs_total": len(ids_all), "n_voided_unserved": len(voided_ids), "b": int(b), "c": int(c), "s_k": s_k, "divergent_roles": int(div),
            "memory_strategy_on": int(mem_on), "memory_strategy_off_VIOLATIONS": int(mem_off_bad), "errors": err,
            "routed_role_distribution_all_pairs": role_dist([allpairs[i] for i in ids_all]),
            "routed_role_distribution_voided_pairs": role_dist([allpairs[i] for i in voided_ids])}


def decide_look(rec, n_pairs):
    """Futility-only interim verdicts. Returns (verdict | None, details). n = valid (non-voided) pairs; n_pairs = the look's total."""
    s = summarize_look(rec, n_pairs)
    n = s["n_pairs"]
    det = dict(s)
    if s["memory_strategy_off_VIOLATIONS"] > 0:
        return "FUTILITY_SWITCH_INEFFECTIVE", det
    if s["n_pairs_total"] and s["n_voided_unserved"] / s["n_pairs_total"] > UNSERVED_MAX_FRAC:
        det["reading"] = "memory routes to roles this setup does not serve; the A/B needs the full stack. The finding is the routed-role distribution."
        return "FUTILITY_UNSERVED_ROUTING", det
    if n >= 50 and s["memory_strategy_on"] == 0:
        return "FUTILITY_NO_MEMORY_PATH", det
    if n >= 50 and max(s["errors"].values()) / n > 0.10:
        return "INFRA_FAILED", det
    det["r_hat"] = s["divergent_roles"] / n if n else None
    det["r_upper95"] = clopper_upper(s["divergent_roles"], n) if n else None
    if n >= 200 and det["r_upper95"] < PRACTICAL:
        return "FUTILITY_NO_ROUTING_DIVERGENCE", det
    if n_pairs in (200, 300) and n > 0:
        cp_hi = conditional_power(s["s_k"], n, s["b"] + s["c"], delta=+PRACTICAL)
        cp_lo = conditional_power(s["s_k"], n, s["b"] + s["c"], delta=-PRACTICAL)
        det["cp_plus"], det["cp_minus"] = cp_hi, cp_lo
        if max(cp_hi, cp_lo) < 0.10:
            return "FUTILITY_CONDITIONAL_POWER", det
    return None, det


def final_result(records, items_by_id):
    pairs = pair_up(records)
    ids_total = [i for i in items_by_id if i in pairs]
    voided = [i for i in ids_total if is_voided(pairs[i])]
    ids = [i for i in ids_total if i not in set(voided)]
    n = len(ids)
    b = c = 0
    diffs = []
    per_suite = {}
    arms = {"ON": [], "OFF": []}
    for i in ids:
        on, off = pairs[i]["ON"], pairs[i]["OFF"]
        dv = int(on["correct"]) - int(off["correct"])
        suite = items_by_id[i]["suite"]
        diffs.append((suite, dv))
        b += dv == 1
        c += dv == -1
        ps = per_suite.setdefault(suite, [0, 0, 0])
        ps[0] += 1
        ps[1] += dv
        arms["ON"].append(on)
        arms["OFF"].append(off)
    d = (b - c) / n if n else None
    p = mcnemar_exact_p(b, c)
    lo, hi = paired_bootstrap_ci(diffs) if n else (None, None)
    pi_d = (b + c) / n if n else None
    out = {"n_pairs": n, "n_pairs_total": len(ids_total), "n_voided_unserved": len(voided),
           "routed_role_distribution_all_pairs": role_dist([pairs[i] for i in ids_total]),
           "routed_role_distribution_voided_pairs": role_dist([pairs[i] for i in voided]),
           "b_on_right_off_wrong": int(b), "c_on_wrong_off_right": int(c), "d_on_minus_off": d,
           "mcnemar_exact_p": p, "d_ci95_paired_bootstrap": [lo, hi], "pi_d": pi_d,
           "per_suite": {s: {"n": v[0], "d": v[1] / v[0]} for s, v in per_suite.items()},
           "mde80_at_realised_pi_d": (2.8 * math.sqrt(pi_d / n) if n and pi_d else None)}
    for arm, rows in arms.items():
        ok = [r for r in rows if r["status"] == "ok"]
        walls = [r["wall_s"] for r in rows]
        out[arm] = {
            "accuracy": sum(int(r["correct"]) for r in rows) / n if n else None,
            "non_ok": n - len(ok),
            "wall_s": {"median": median(walls), "p90": percentile(walls, 0.9),
                       "mean": (sum(walls) / n if n else None), "total": sum(walls)},
            "tokens_used": {"sum": sum(r.get("tokens_used") or 0 for r in rows),
                            "mean": (sum(r.get("tokens_used") or 0 for r in rows) / n if n else None)},
            "prompt_tokens_sum": sum(r.get("prompt_tokens") or 0 for r in rows),
            "server_elapsed_s_sum": sum(r.get("server_elapsed_s") or 0 for r in rows),
            "routed_to": _count(r.get("routed_to") for r in rows),
            "routing_strategy": _count(r.get("routing_strategy") for r in rows),
        }
    out["divergent_roles"] = sum((pairs[i]["ON"].get("routed_to") or "") != (pairs[i]["OFF"].get("routed_to") or "") for i in ids)
    out["latency_paired_median_diff_on_minus_off_s"] = median([pairs[i]["ON"]["wall_s"] - pairs[i]["OFF"]["wall_s"] for i in ids])
    for first in ("ON", "OFF"):
        sel = [i for i in ids if pairs[i]["ON"]["arm_first"] == first]
        out[f"latency_when_{first}_first"] = {
            "n": len(sel), "on_median_s": median([pairs[i]["ON"]["wall_s"] for i in sel]),
            "off_median_s": median([pairs[i]["OFF"]["wall_s"] for i in sel])}
    aa = [(v["ON"], v["ON2"]) for v in pair_up_aa(records)]
    out["aa_floor"] = {"n": len(aa), "correctness_flips": sum(int(a["correct"]) != int(b2["correct"]) for a, b2 in aa),
                       "role_flips": sum((a.get("routed_to") or "") != (b2.get("routed_to") or "") for a, b2 in aa)}
    if ids_total and len(voided) / len(ids_total) > UNSERVED_MAX_FRAC:
        verdict = "FUTILITY_UNSERVED_ROUTING"
    elif len(ids_total) >= N_PLANNED:
        if p < 0.05 and d > 0:
            verdict = "MEMORY_ON_BETTER"
        elif p < 0.05 and d < 0:
            verdict = "MEMORY_ON_WORSE"
        else:
            verdict = "NO_DETECTABLE_DIFFERENCE"
        out["NI_PASS_lower_ci_ge_minus_0.03"] = (lo is not None and lo >= -PRACTICAL)
    else:
        verdict = "INCOMPLETE"
    out["verdict"] = verdict
    return out


def pair_up_aa(records):
    by = {}
    for r in records:
        by.setdefault(r["item_id"], {})[r["arm"]] = r
    return [v for v in by.values() if "ON" in v and "ON2" in v and not v["ON"].get("unserved") and not v["ON2"].get("unserved") and not (v.get("OFF") or {}).get("unserved")]


def _count(it):
    out = {}
    for x in it:
        out[str(x)] = out.get(str(x), 0) + 1
    return out


# ---------------------------------------------------------------- HTTP
def http_get(path: str, timeout=20.0):
    with urllib.request.urlopen(f"{API}{path}", timeout=timeout) as r:
        return r.status, r.read()


def post_chat(body: dict):
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{API}/chat", data=data, headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as r:
            payload = json.loads(r.read().decode())
            return {"status": "ok", "http": r.status, "payload": payload, "wall_s": time.monotonic() - t0}
    except urllib.error.HTTPError as e:
        # Do not discard the routed role/history on non-200 ChatResponse bodies.
        raw = e.read().decode(errors="replace")
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = {}
        return {"status": "http_error", "http": e.code, "error": raw[:300],
                "payload": payload if isinstance(payload, dict) else {},
                "wall_s": time.monotonic() - t0}
    except TimeoutError as e:
        return {"status": "timeout", "error": str(e), "wall_s": time.monotonic() - t0}
    except urllib.error.URLError as e:
        kind = "timeout" if isinstance(e.reason, TimeoutError) else "transport_error"
        return {"status": kind, "error": str(e.reason), "wall_s": time.monotonic() - t0}
    except (OSError, ValueError) as e:
        return {"status": "transport_error", "error": f"{type(e).__name__}: {e}", "wall_s": time.monotonic() - t0}


def chat_body(prompt: str, arm: str) -> dict:
    body = {"prompt": prompt, "context": "", "mock_mode": False, "real_mode": True, "x_request_source": "probe"}
    if arm == "OFF":
        body["episodic_lookups"] = False
    return body


def episodic_count() -> dict:
    import sqlite3
    c = sqlite3.connect(f"file:{EPISODIC_DB}?mode=ro", uri=True)
    try:
        n = c.execute("select count(*) from memories").fetchone()[0]
    finally:
        c.close()
    st = os.stat(EPISODIC_DB)
    return {"rows": n, "mtime": st.st_mtime, "size": st.st_size}


def preflight() -> dict:
    res = {"at": now(), "api": API, "code_commit_expected": CODE_COMMIT, "problems": []}
    try:
        st, _ = http_get("/health")
        res["health_http"] = st
    except Exception as e:  # noqa: BLE001
        res["problems"].append(f"health: {type(e).__name__}: {e}")
    try:
        _, raw = http_get("/openapi.json")
        spec = json.loads(raw.decode())
        props = ((spec.get("components") or {}).get("schemas") or {}).get("ChatRequest", {}).get("properties", {})
        res["openapi_has_episodic_lookups"] = "episodic_lookups" in props
        if "episodic_lookups" not in props:
            res["problems"].append("API ChatRequest has no episodic_lookups: older build would silently ignore the off switch")
    except Exception as e:  # noqa: BLE001
        res["problems"].append(f"openapi: {type(e).__name__}: {e}")
    try:
        _, raw = http_get("/config/attest")
        att = json.loads(raw.decode())
        flags = att.get("flags") or att.get("features") or att
        res["attest_memrl"] = flags.get("memrl")
        res["attest_episodic_routing_lookups"] = flags.get("episodic_routing_lookups")
        if flags.get("memrl") is not True:
            res["problems"].append(f"memrl flag is {flags.get('memrl')!r}: memory never reaches routing")
        if flags.get("episodic_routing_lookups") is not True:
            res["problems"].append(f"episodic_routing_lookups is {flags.get('episodic_routing_lookups')!r}: the ON arm would run with lookups off")
    except Exception as e:  # noqa: BLE001
        res["problems"].append(f"attest: {type(e).__name__}: {e}")
    try:
        res["episodic_db"] = episodic_count()
        if res["episodic_db"]["rows"] != EXPECTED_ROWS:
            res["problems"].append(f"episodic.db rows {res['episodic_db']['rows']} != {EXPECTED_ROWS}")
    except Exception as e:  # noqa: BLE001
        res["problems"].append(f"episodic.db: {type(e).__name__}: {e}")
    return res


# ---------------------------------------------------------------- identity / items
def load_everything():
    for path, want in PINS.items():
        got = sha256_file(path)
        if got != want:
            raise SystemExit(f"refused: {path} sha256 {got} != pinned {want}")
    sys.path.insert(0, RESEARCH)
    sys.path.insert(0, f"{RESEARCH}/scripts/benchmark")
    from scripts.benchmark.thesis_ufh13.suite import load_suite  # noqa: E402
    from scripts.benchmark.thesis_ufh13.pilot_pool import load_pool, mix_matched_sample  # noqa: E402
    import answer_scoring  # noqa: E402
    frozen = load_suite()
    return frozen, load_pool, mix_matched_sample, answer_scoring.extract_letter_answer


def arm_first(item_id: str) -> str:
    return "ON" if int(hashlib.sha256(f"{ARM_SEED}:{item_id}".encode()).hexdigest(), 16) % 2 == 0 else "OFF"


def run_request(item, arm: str, score_fn, first: str, unit_extra=None) -> dict:
    res = post_chat(chat_body(item.prompt, "OFF" if arm == "OFF" else "ON"))
    rec = {"unit_id": f"{item.item_id}|{arm}", "item_id": item.item_id, "suite": item.suite, "arm": arm,
           "arm_first": first, "expected": item.expected, "status": res["status"], "wall_s": res["wall_s"], "at": now()}
    p = res.get("payload") or {}
    ans = str(p.get("answer") or "")
    detail = str(p.get("error_detail") or p.get("detail") or "")
    unserved = is_unserved(res["status"] == "ok", ans, p.get("routed_to"),
                           p.get("role_history"), http_status=res.get("http"),
                           error_detail=detail)
    rec.update({"unserved": unserved, "http": res.get("http"),
                "routed_to": p.get("routed_to"), "routing_strategy": p.get("routing_strategy"),
                "role_history": p.get("role_history"), "error_detail": detail[:400]})
    if res["status"] == "ok":
        got = (score_fn(ans) or "") if not unserved else None
        rec.update({"answer": ans[:400], "extracted": got,
                    "correct": None if unserved else bool(got and got.upper() == item.expected),
                    "tokens_used": p.get("tokens_used"),
                    "prompt_tokens": p.get("prompt_tokens"), "server_elapsed_s": p.get("elapsed_seconds")})
    else:
        rec.update({"answer": ans[:400], "extracted": None,
                    "correct": None if unserved else False, "error": res.get("error")})
    if unit_extra:
        rec.update(unit_extra)
    return rec


# ---------------------------------------------------------------- modes
def smoke() -> int:
    os.makedirs(f"{OUT}/smoke", exist_ok=True)
    result = {"id": ID, "at": now(), "ok": False, "cpu": pin_cpus()}
    frozen, load_pool, mix, score_fn = load_everything()
    pf = preflight()
    result["preflight"] = pf
    if pf["problems"]:
        result["reason"] = "preflight"
        write_json(f"{OUT}/smoke/{ID}.json", result)
        return 3
    pool, _ = load_pool()
    items = mix(pool, frozen, 2, SMOKE_SEED)
    before = episodic_count()
    recs = []
    for it in items:
        for arm in ("ON", "OFF"):
            recs.append(run_request(it, arm, score_fn, "n/a"))
    after = episodic_count()
    result["records"] = [{k: r.get(k) for k in ("item_id", "arm", "status", "http", "error", "error_detail", "routed_to", "role_history", "routing_strategy", "unserved", "extracted", "wall_s", "tokens_used")} for r in recs]
    result["routed_roles_smoke"] = [{"arm": r["arm"], "routed_to": r.get("routed_to"), "role_history": r.get("role_history"), "unserved": r.get("unserved")} for r in recs]
    result["episodic_custody"] = {"before": before, "after": after, "unchanged": before["rows"] == after["rows"]}
    problems = []
    if any(r["status"] != "ok" and not r["unserved"] for r in recs):
        problems.append("a smoke request was not ok and lacks unserved-backend evidence")
    if any(r["arm"] == "OFF" and r.get("routing_strategy") in MEMORY_STRATEGIES for r in recs):
        problems.append("OFF arm shows a memory routing strategy")
    if before["rows"] != after["rows"]:
        problems.append("episodic.db row count moved during smoke")
    result["problems"] = problems
    result["ok"] = not problems
    write_json(f"{OUT}/smoke/{ID}.json", result)
    return 0 if result["ok"] else 3


def run() -> int:
    os.makedirs(OUT, exist_ok=True)
    cpu = pin_cpus()
    frozen, _lp, _mix, score_fn = load_everything()
    items_by_id = {it.item_id: {"suite": it.suite} for it in frozen}
    order = list(frozen)
    random.Random(ITEM_SEED).shuffle(order)
    assert len(order) == N_PLANNED
    pf = preflight()
    write_json(f"{OUT}/preflight-{int(time.time())}.json", {**pf, "cpu": cpu})
    rec_path = f"{OUT}/records.jsonl"
    if pf["problems"]:
        write_json(f"{OUT}/RESULT.json", {"id": ID, "status": "incomplete", "verdict": "INFRA_FAILED", "problems": pf["problems"], "at": now()})
        return 3
    if not os.path.exists(f"{OUT}/custody-before.json"):
        write_json(f"{OUT}/custody-before.json", pf["episodic_db"])
    done = {r["unit_id"] for r in read_jsonl(rec_path)}
    aa_ids = {it.item_id for it in order[:N_AA]}
    for idx, it in enumerate(order):
        first = arm_first(it.item_id)
        seq = [first, "OFF" if first == "ON" else "ON"] + (["ON2"] if it.item_id in aa_ids else [])
        for arm in seq:
            if f"{it.item_id}|{arm}" in done:
                continue
            if should_stop():
                write_json(f"{OUT}/PROGRESS.json", {"at": now(), "stopped_at_item_index": idx, "units_done": len(done)})
                return 75
            rec = run_request(it, arm, score_fn, first)
            append_jsonl(rec_path, rec)
            done.add(rec["unit_id"])
        n_done = idx + 1
        if n_done in LOOKS:
            recs = read_jsonl(rec_path)
            if n_done == N_PLANNED:
                break
            verdict, det = decide_look(recs, n_done)
            append_jsonl(f"{OUT}/looks.jsonl", {"at": now(), "look_pairs": n_done, "verdict": verdict, "details": det})
            if verdict:
                status = "incomplete" if verdict == "INFRA_FAILED" else "complete"
                write_json(f"{OUT}/RESULT.json", {"id": ID, "status": status, "verdict": verdict, "look_pairs": n_done, "details": det,
                                                  "label": "futility-only interim stop; not a gate result", "at": now()})
                return 0 if status == "complete" else 3
    recs = read_jsonl(rec_path)
    res = final_result(recs, items_by_id)
    after = episodic_count()
    res.update({"id": ID, "status": "complete", "at": now(), "custody_after": after,
                "custody_unchanged": after["rows"] == EXPECTED_ROWS, "code_commit": CODE_COMMIT})
    write_json(f"{OUT}/RESULT.json", res)
    append_jsonl(f"{OUT}/looks.jsonl", {"at": now(), "look_pairs": N_PLANNED, "verdict": res["verdict"], "details": {"final": True}})
    return 0


def selftest() -> int:
    """Pure-function checks, no network: python3 job.py --selftest"""
    assert mcnemar_exact_p(10, 10) == 1.0 and mcnemar_exact_p(0, 0) == 1.0 and mcnemar_exact_p(0, 12) < 0.001
    assert abs(clopper_upper(0, 200) - 0.0183) < 5e-4 and abs(clopper_upper(0, 100) - 0.0362) < 5e-4
    assert 0.0 < clopper_upper(5, 100) < 0.15
    assert conditional_power(0, 200, 16, delta=0.03) < 0.15
    assert conditional_power(10, 200, 16, delta=0.03) > conditional_power(0, 200, 16, delta=0.03)
    lo, hi = paired_bootstrap_ci([("a", 1)] * 5 + [("a", 0)] * 95, reps=500)
    assert lo >= 0.0 and hi > 0.05
    recs = []
    for i in range(200):
        for arm in ("ON", "OFF"):
            recs.append({"item_id": f"i{i}", "suite": "s", "arm": arm, "arm_first": "ON", "status": "ok", "correct": True,
                         "routed_to": "frontdoor", "routing_strategy": ("learned" if arm == "ON" and i % 5 == 0 else "rules"),
                         "wall_s": 1.0})
    v, det = decide_look(recs, 200)
    assert v == "FUTILITY_NO_ROUTING_DIVERGENCE" and det["divergent_roles"] == 0, (v, det)
    recs[1]["routing_strategy"] = "learned"  # OFF record of item 0
    assert decide_look(recs, 200)[0] == "FUTILITY_SWITCH_INEFFECTIVE"
    assert is_unserved(True, "[ERROR: Direct LLM call failed after retry: All connection attempts failed]", "coder_escalation", ["frontdoor", "coder_escalation"])
    assert not is_unserved(True, "[ERROR: Direct LLM call failed after retry: connection refused]", "frontdoor", ["frontdoor"])  # frontdoor failure stays wrong
    assert not is_unserved(True, "The answer is B", "coder_escalation", [])
    recs = []
    for i in range(100):
        for arm in ("ON", "OFF"):
            bad = arm == "ON" and i < 11
            recs.append({"item_id": f"u{i}", "suite": "s", "arm": arm, "arm_first": "ON", "status": "ok", "correct": not bad, "unserved": bad,
                         "routed_to": "coder_escalation" if bad else "frontdoor", "routing_strategy": "learned" if arm == "ON" else "rules", "wall_s": 1.0})
    v, det = decide_look(recs, 100)
    assert v == "FUTILITY_UNSERVED_ROUTING" and det["n_voided_unserved"] == 11 and det["n_pairs"] == 89, (v, det)
    assert det["routed_role_distribution_voided_pairs"]["ON"] == {"coder_escalation": 11}
    for r in recs:
        if r["item_id"] == "u10":
            r["unserved"] = False
            r["correct"] = True
    v2, det2 = decide_look(recs, 100)
    assert v2 is None and det2["n_voided_unserved"] == 10 and det2["n_pairs"] == 90, (v2, det2)
    print("selftest ok")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if not os.environ.get("M12K_RUN_DIR") or not os.environ.get("M12K_ROW_ID"):
        sys.exit("refused: set M12K_RUN_DIR and M12K_ROW_ID for a fresh published row")
    sys.exit(smoke() if SMOKE else run())
