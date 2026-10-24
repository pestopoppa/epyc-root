"""PINNED strict reader (sha256 pinned in ``weight_handoff.py``, loaded by exact bytes, same mechanism as
``qwen4exp_quality_reader.py``) + projection for captured prefill/decode weight-handoff receipts (VB-NEW13-WIRE).

Producer: ``scripts/vidya/weight_handoff_capture.py`` (``qwen4exp_quality_capture.py --mode weight-handoff``)
wrapping ``llama-weight-handoff``. Receipt schema ``epyc.vidya.weight_handoff_measurement.v1``.

This module PROJECTS and never grades: each re-derived metric becomes a shared measurement
``ClaimTuple`` and ``claim_tuple.grade()`` decides. It registers no ladder and applies no
decision threshold -- the predeclared rule file is hashed and cited, never evaluated here.

What the reader re-derives from original bytes (a receipt's own numbers are never trusted):
per-arm mean KLD, R = (KLD_A - KLD_B)/KLD_A with its paired-bootstrap 95% CI, and the Gate 0 gap
KLD_A - KLD_C with its CI, all from the harness's ``kld.jsonl``; the residency verdict from the
loaded-object custody rows plus per-PID KFD samples; and the file identities of every input.
Bootstrap is the declared stdlib procedure (``random.Random(seed)``, passages resampled with
replacement, numpy-style linear percentiles); it is NOT numpy's generator, so a CI differs
slightly from a numpy re-analysis of the same data and the two must never be compared digit for digit.

Refused (ProjectionError, no rows): any other schema -- including the hand-written
``epyc.new13.receipt.v0`` (pre-hook, never backfilled) --, a refused/partial final receipt, an
incomplete passage set, a non-matching chain of resumed invocations, unknown residency, missing
compiled-IQK evidence, changed inputs, and any metric that does not re-derive.
Large model shards are checked by size/inode/mtime/ctime and their capture-time sha256 is carried,
not re-hashed (a 170 GB re-read per ingest is not proportionate); every small input is re-hashed.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError  # noqa: E402
from adapters import qwen4exp_quality as _q4  # noqa: E402  (pinned SC54 strict reader helpers)

SCHEMA = "epyc.vidya.weight_handoff_measurement.v1"
DECL_SCHEMA = "epyc.vidya.weight_handoff_metric_declaration.v1"
ARMS = ("A", "B", "C", "D")
LABELS = tuple(f"KLD[{a}]" for a in ARMS) + ("R", "G0_gap")
CI_LABELS = ("R", "G0_gap")
ARM_MEANING = {"A": "D prefill, D decode (decode-set only)", "B": "P prefill -> state copy -> D decode",
               "C": "P prefill, P decode (prefill-set only)", "D": "D prefill -> state copy -> P decode (reverse)"}
STAT_KEYS = {"path", "sha256", "size_bytes", "mode", "device", "inode", "mtime_ns", "ctime_ns"}
PARTIAL_STATUS = "partial"
MAX_CHAIN = 64
_ACCEL = re.compile(r"^libggml-(hip|cuda|vulkan|sycl|metal|opencl|musa|cann)[.-]")
_CPU = re.compile(r"^libggml-cpu[.-]")


def _reader():
    return _q4._reader()


def stat_matches(identity: Any) -> bool:
    """Cheap no-follow check that a large file still has its captured inode/size/mtime/ctime."""
    if not isinstance(identity, dict) or set(identity) != STAT_KEYS:
        return False
    try:
        st = os.stat(identity["path"], follow_symlinks=False)
    except OSError:
        return False
    return (st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns) == (
        identity["device"], identity["inode"], identity["mode"], identity["size_bytes"],
        identity["mtime_ns"], identity["ctime_ns"])


def percentile(sorted_values: list[float], q: float) -> float:
    pos = (len(sorted_values) - 1) * q / 100.0
    lo = int(math.floor(pos)); hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def load_kld_records(raw: bytes) -> dict[int, dict[str, Any]]:
    """Parse the harness per-passage JSONL; torn trailing lines are ignored, last complete record wins."""
    recs: dict[int, dict[str, Any]] = {}
    for line in raw.decode("utf-8").splitlines():
        if not line.endswith("}"):
            continue
        try:
            r = _reader()._json(line)
        except ValueError:
            continue
        if isinstance(r, dict) and r.get("complete") is True and type(r.get("passage")) is int:
            recs[r["passage"]] = r
    return recs


def derive_metrics(raw: bytes, n_expect: int, *, ref: str, n_prompt: int | None, n_cont: int | None,
                   seed: int, resamples: int) -> dict[str, Any]:
    """Re-derive every projected number from kld.jsonl bytes; raise ValueError on any gap."""
    if type(seed) is not int or type(resamples) is not int or resamples < 1000:
        raise ValueError("bootstrap seed/resamples invalid (resamples >= 1000)")
    recs = load_kld_records(raw)
    missing = [i for i in range(n_expect) if i not in recs]
    if missing:
        raise ValueError(f"{len(missing)} of {n_expect} passages missing (first {missing[:5]}); the denominator is all {n_expect}")
    pm = {a: [] for a in ARMS}
    nc = None
    for i in range(n_expect):
        r = recs[i]
        if r.get("finite") is not True:
            raise ValueError(f"non-finite logits in passage {i}")
        if r.get("ref") != ref:
            raise ValueError(f"passage {i} was scored against ref {r.get('ref')!r}, pinned {ref!r}")
        if n_prompt is not None and r.get("n_prompt") != n_prompt:
            raise ValueError(f"passage {i} n_prompt differs from the sealed manifest")
        if type(r.get("n_cont")) is not int or r["n_cont"] < 1 or (n_cont is not None and r["n_cont"] != n_cont):
            raise ValueError(f"passage {i} n_cont differs from the sealed manifest")
        nc = r["n_cont"] if nc is None else nc
        if r["n_cont"] != nc:
            raise ValueError("n_cont differs between passages")
        arms = r.get("arms")
        if not isinstance(arms, dict):
            raise ValueError(f"passage {i} lacks arms")
        for a in ARMS:
            k = arms.get(a, {}).get("kld") if isinstance(arms.get(a), dict) else None
            if not isinstance(k, list) or len(k) != nc or any(type(x) not in (int, float) or not math.isfinite(x) or x < -1e-6 for x in k):
                raise ValueError(f"passage {i} arm {a} KLD list missing, wrong length, non-finite or negative")
            pm[a].append(sum(k) / nc)
    n = n_expect
    K = {a: sum(pm[a]) / n for a in ARMS}
    if not K["A"] > 0:
        raise ValueError("KLD_A is not positive: R is undefined")
    R = (K["A"] - K["B"]) / K["A"]
    gap = K["A"] - K["C"]
    rng = random.Random(seed)
    rb: list[float] = []
    gb: list[float] = []
    for _ in range(resamples):
        idx = [rng.randrange(n) for _ in range(n)]
        ka = sum(pm["A"][j] for j in idx) / n
        if not ka > 0:
            raise ValueError("a bootstrap resample has KLD_A <= 0: R CI undefined")
        kb = sum(pm["B"][j] for j in idx) / n
        kc = sum(pm["C"][j] for j in idx) / n
        rb.append((ka - kb) / ka)
        gb.append(ka - kc)
    rb.sort(); gb.sort()
    return {"values": {**{f"KLD[{a}]": K[a] for a in ARMS}, "R": R, "G0_gap": gap},
            "ci95": {"R": [percentile(rb, 2.5), percentile(rb, 97.5)],
                     "G0_gap": [percentile(gb, 2.5), percentile(gb, 97.5)]},
            "n_passages": n, "n_cont": nc}


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)


def _verify_residency(r: dict[str, Any], started, ended) -> dict[str, Any]:
    rd = _reader()
    sub = r.get("substrate")
    kfd = r.get("kfd_residency")
    keys = {"kfd_root", "sample_interval_s", "sample_basis", "samples_total", "child_entry_samples",
            "vram_positive_samples", "max_vram_bytes", "first_sample_at_utc", "latest_sample_at_utc", "error"}
    if sub not in {"cpu", "hip"}:
        raise ValueError("substrate unknown")
    if not isinstance(kfd, dict) or set(kfd) != keys:
        raise ValueError("KFD residency block malformed")
    if kfd["error"] is not None:
        raise ValueError("KFD residency sampling had an error")
    counts = [kfd[k] for k in ("samples_total", "child_entry_samples", "vram_positive_samples", "max_vram_bytes")]
    if any(type(x) is not int or x < 0 for x in counts) or not kfd["samples_total"] >= kfd["child_entry_samples"] >= kfd["vram_positive_samples"]:
        raise ValueError("KFD residency counts invalid")
    if kfd["samples_total"] < 2:
        raise ValueError("fewer than two KFD residency samples")
    for key in ("first_sample_at_utc", "latest_sample_at_utc"):
        when = rd._aware(kfd[key], "KFD " + key)
        if not started <= when <= ended:
            raise ValueError("KFD residency sample outside measured process window")
    names = [Path(str(row.get("path", ""))).name for row in r["loaded_shared_objects"]]
    accel = [n for n in names if _ACCEL.match(n)]
    if sub == "cpu":
        if accel or not any(_CPU.match(n) for n in names) or kfd["child_entry_samples"]:
            raise ValueError("CPU residency not proven: accelerator backend mapped, no CPU backend, or child in KFD")
    elif not any(n.startswith("libggml-hip") for n in accel) or kfd["vram_positive_samples"] < 2 or kfd["max_vram_bytes"] <= 0:
        raise ValueError("HIP residency not proven: libggml-hip unmapped or fewer than two non-zero VRAM samples")
    return {"substrate": sub, "kfd_samples": kfd["samples_total"], "kfd_child_entry_samples": kfd["child_entry_samples"],
            "kfd_vram_positive_samples": kfd["vram_positive_samples"], "max_vram_bytes": kfd["max_vram_bytes"],
            "accelerator_objects": sorted(set(accel)),
            "cpu_backend_objects": sorted({n for n in names if _CPU.match(n)})}


def _verify_loaded_objects(r: dict[str, Any], started, ended) -> None:
    """Same custody contract as the SC54 reader (path/inode/maps/live-hash/compiled-IQK bytes)."""
    rd = _reader()
    rows = r.get("loaded_shared_objects")
    if not isinstance(rows, list) or not rows:
        raise ValueError("no loaded shared-object mappings observed")
    found = False
    for row in rows:
        if row.get("identity_error"):
            raise ValueError(row["identity_error"])
        if row.get("identity_state") != "matched" or str(row.get("path", "")).endswith(" (deleted)"):
            raise ValueError("loaded object custody unknown")
        ident = row.get("after")
        rd._verify_identity(ident)
        maps = row.get("mapping_observation")
        if (not isinstance(maps, dict) or maps.get("sample_basis") != "distinct maps snapshots containing this path/device/inode/deleted identity"
                or type(maps.get("sample_count")) is not int or maps["sample_count"] < 1 or maps.get("deleted_mapping_observed") is not False):
            raise ValueError("maps sample count/basis missing, invalid or deleted")
        for m in (maps.get("first"), maps.get("latest")):
            if (not isinstance(m, dict) or m.get("deleted") or m.get("inode") != ident["inode"]
                    or m.get("device_major") != os.major(ident["device"]) or m.get("device_minor") != os.minor(ident["device"])):
                raise ValueError("maps identity not contemporaneous or mismatched")
            if not started <= rd._aware(m.get("observed_at_utc"), "mapping observation timestamp") <= ended:
                raise ValueError("mapping observation outside measured process window")
        live = row.get("live_identity_observation")
        if (not isinstance(live, dict) or live.get("sample_basis") != "successful stable same-inode content hash observations while child was live"
                or type(live.get("sample_count")) is not int or live["sample_count"] < 1 or live.get("error_observed") is not False
                or live.get("identity_change_observation_count") != 0 or live.get("first_changed_identity") is not None):
            raise ValueError("shared object lacks stable in-process identity observation")
        for x in (live.get("first"), live.get("latest")):
            if not isinstance(x, dict) or x.get("identity") != ident:
                raise ValueError("shared object lacks stable in-process identity observation")
            if not started <= rd._aware(x.get("observed_at_utc"), "live identity timestamp") <= ended:
                raise ValueError("shared-object identity was not hashed during the child window")
        ev = row.get("compiled_knob_evidence", {})
        exact = rd._identity_exact_c_string(ident, b"GGML_IQK\0")
        if ev.get("required_bytes_hex") != "47474d4c5f49514b00" or ev.get("found_exact") is not exact:
            raise ValueError("compiled IQK evidence does not rederive from hashed object bytes")
        found = found or exact
    if not found:
        raise ValueError("no loaded-object compiled IQK evidence")
    env = r.get("effective_environment", {})
    state = {"0": "disabled", "1": "enabled"}.get(env.get("GGML_IQK", "unknown"), "unknown")
    knob = r.get("runtime_knobs", {}).get("GGML_IQK", {})
    if state == "unknown" or knob.get("value") != state or knob.get("raw_value") != env.get("GGML_IQK"):
        raise ValueError("effective runtime IQK state absent, unknown or inconsistent")


def _verify_receipt(path: Path, *, final: bool, depth: int = 0, final_kraw: bytes | None = None) -> dict[str, Any]:
    """Verify one receipt; final=True demands a completed passage set, False a chained partial."""
    rd = _reader()
    if depth > MAX_CHAIN:
        raise ValueError("prior-receipt chain too long")
    raw, receipt_file = rd._read_stable(path)
    r = rd._json(raw)
    if not isinstance(r, dict) or r.get("schema") != SCHEMA or r.get("schema_version") != 1:
        raise ValueError(f"unsupported receipt schema {r.get('schema') if isinstance(r, dict) else None!r}")
    unsigned = {k: v for k, v in r.items() if k != "self_sha256"}
    canon = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    if not isinstance(r.get("self_sha256"), str) or hashlib.sha256(canon).hexdigest() != r["self_sha256"]:
        raise ValueError("receipt self digest mismatch")
    want = "captured" if final else None
    if r.get("capture_status") not in ({"captured"} if final else {"captured", PARTIAL_STATUS}) or r.get("refusal_reasons"):
        raise ValueError(f"receipt capture_status {r.get('capture_status')!r} is not accepted here (want {want or 'captured/partial'})")
    if r.get("exit_code") != 0 and r.get("capture_status") == "captured":
        raise ValueError("captured receipt with nonzero exit code")
    if not isinstance(r.get("run_id"), str) or not r["run_id"]:
        raise ValueError("run identity missing")
    started = rd._aware(r.get("started_at_utc"), "started_at_utc")
    ended = rd._aware(r.get("ended_at_utc"), "ended_at_utc")
    if started > ended:
        raise ValueError("measurement start is after end")
    # --- producer binary
    pb = r.get("producer_binary", {})
    if pb.get("before") != pb.get("after") or pb.get("stable_during_capture") is not True:
        raise ValueError("producer binary did not remain stable")
    rd._verify_identity(pb["before"])
    exp = r.get("expected_binary_sha256")
    if exp is not None and exp != pb["before"]["sha256"]:
        raise ValueError("producer binary differs from the pinned expected sha256")
    # --- weights, reference, passages, predeclared
    weights = r.get("weights")
    if not isinstance(weights, dict) or set(weights) != {"P", "D", "R"}:
        raise ValueError("weights block malformed")
    for side in ("P", "D"):
        blk = weights[side]
        if not isinstance(blk, dict) or set(blk) != {"shards", "shards_after"} or blk["shards"] != blk["shards_after"] or not blk["shards"]:
            raise ValueError(f"weights.{side} changed during run or is empty")
        if not all(stat_matches(x) and re.fullmatch(r"[0-9a-f]{64}", x["sha256"]) for x in blk["shards"]):
            raise ValueError(f"weights.{side} shard no longer matches its captured inode/size/mtime")
    ref = r.get("reference", {})
    ref_blob = rd._json(rd._verify_identity(ref["json"], retain_bytes=True))
    if not isinstance(ref_blob, dict) or ref_blob.get("ref") != ref.get("choice") or ref.get("choice") not in {"P", "R"}:
        raise ValueError("reference choice does not re-derive from the pinned reference JSON")
    if ref["choice"] == "R":
        blk = weights["R"]
        if not isinstance(blk, dict) or blk["shards"] != blk["shards_after"] or not blk["shards"] or not all(stat_matches(x) for x in blk["shards"]):
            raise ValueError("reference R weights missing or changed")
    elif weights["R"] is not None:
        raise ValueError("reference P cannot carry R weights")
    ps = r.get("passages", {})
    manifest = rd._json(rd._verify_identity(ps["manifest"], retain_bytes=True))
    rd._verify_identity(ps["binary"])
    if (not isinstance(manifest, dict) or manifest.get("n") != ps.get("n") or manifest.get("n_prompt") != ps.get("n_prompt")
            or manifest.get("n_cont") != ps.get("n_cont") or manifest.get("binary_sha256") != ps["binary"]["sha256"]
            or type(ps.get("n")) is not int or ps["n"] < 2):
        raise ValueError("passage manifest does not bind the passage binary, n, n_prompt and n_cont")
    if r.get("predeclared") is not None:
        rd._verify_identity(r["predeclared"])
    # --- argv binds the sealed inputs
    argv = r.get("argv")
    if not isinstance(argv, list) or not argv or any(not isinstance(x, str) for x in argv):
        raise ValueError("exact argv missing")

    def option(*names: str) -> str:
        found = [argv[i + 1] for i, x in enumerate(argv[:-1]) if x in names]
        if len(found) != 1:
            raise ValueError(f"argv option {names[0]} missing or duplicated")
        return found[0]
    same = lambda a, b: Path(a).absolute() == Path(b).absolute()
    kld_path = r.get("kld_jsonl", {}).get("after", {}).get("path")
    if (not same(argv[0], pb["before"]["path"]) or not same(option("--model-p"), weights["P"]["shards"][0]["path"])
            or not same(option("--model-d"), weights["D"]["shards"][0]["path"]) or not same(option("--passages"), ps["binary"]["path"])
            or kld_path is None or not same(option("--out"), kld_path) or option("--ref") != ref["choice"]):
        raise ValueError("argv disagrees with the sealed weights, passages, reference or output")
    if ref["choice"] == "R" and not same(option("--model-r"), weights["R"]["shards"][0]["path"]):
        raise ValueError("argv --model-r disagrees with the sealed R weights")
    if not option("--selftest").isdigit() or int(option("--selftest")) < 1:
        raise ValueError("state-copy self-test was not requested (--selftest >= 1)")
    # --- loaded objects + residency + log
    _verify_loaded_objects(r, started, ended)
    residency = _verify_residency(r, started, ended)
    log = r.get("native_log")
    if not isinstance(log, dict) or set(log) != {"path", "sha256"}:
        raise ValueError("native log reference malformed")
    lb, _ = rd._read_stable(Path(log["path"]))
    if hashlib.sha256(lb).hexdigest() != log["sha256"]:
        raise ValueError("native log digest mismatch")
    # --- kld.jsonl, chain
    k = r.get("kld_jsonl")
    if not isinstance(k, dict) or set(k) != {"before", "after", "complete_before", "complete_after"}:
        raise ValueError("kld_jsonl block malformed")
    if final:
        kraw = rd._verify_identity(k["after"], retain_bytes=True)
    else:
        # kld.jsonl is append-only and grows across resumed invocations: an earlier receipt is checked as a
        # byte PREFIX of the file the final receipt sealed, never by re-reading the long-gone earlier inode.
        size = k["after"]["size_bytes"]
        if final_kraw is None or type(size) is not int or len(final_kraw) < size or hashlib.sha256(final_kraw[:size]).hexdigest() != k["after"]["sha256"]:
            raise ValueError("earlier invocation's kld.jsonl is not a byte prefix of the final kld.jsonl")
        kraw = final_kraw[:size]
    n = ps["n"]
    recs = load_kld_records(kraw)
    done = sum(1 for i in range(n) if i in recs)
    if done != k["complete_after"] or type(k["complete_before"]) is not int or k["complete_before"] > done:
        raise ValueError("complete passage counts do not re-derive from kld.jsonl")
    if final and done != n:
        raise ValueError(f"only {done} of {n} passages complete")
    prior = r.get("prior_receipt")
    chain = [{"run_id": r["run_id"], "receipt_sha256": receipt_file["sha256"], "substrate": residency["substrate"],
              "complete_before": k["complete_before"], "complete_after": done, "exit_code": r.get("exit_code")}]
    if prior is None:
        if k["before"] is not None and k["complete_before"] != 0:
            raise ValueError("resumed run without a prior receipt: warrant for the earlier passages is unknown")
    else:
        pr = _verify_receipt(Path(prior["path"]), final=False, depth=depth + 1, final_kraw=kraw if final else final_kraw)
        pa, kb = pr["kld_after"], k["before"]
        if (prior != pr["receipt_file"] or not isinstance(kb, dict) or (pa["sha256"], pa["size_bytes"]) != (kb["sha256"], kb["size_bytes"])
                or pr["complete_after"] != k["complete_before"]):
            raise ValueError("prior receipt does not chain: its kld.jsonl is not the one this run resumed")
        for key in ("weights", "reference", "passages"):
            if _stable_view(pr["r"][key]) != _stable_view(r[key]):
                raise ValueError(f"prior receipt {key} differs from this run")
        if pr["r"]["producer_binary"]["before"]["sha256"] != pb["before"]["sha256"]:
            raise ValueError("prior receipt used a different producer binary")
        chain = pr["chain"] + chain
    # --- declaration (pre-run author), metrics
    decl = r.get("metric_declaration")
    if not isinstance(decl, dict) or set(decl) != {"before", "after", "author", "issued_at_utc", "metrics"} or decl["before"] != decl["after"]:
        raise ValueError("metric declaration envelope missing or changed")
    src = rd._json(rd._verify_identity(decl["before"], retain_bytes=True))
    if (src.get("schema") != DECL_SCHEMA or src.get("run_id") != r["run_id"] or src.get("author") != decl["author"]
            or src.get("issued_at_utc") != decl["issued_at_utc"] or src.get("metrics") != decl["metrics"]
            or src.get("protocol_id") != r.get("protocol_id") or rd._aware(decl["issued_at_utc"], "declaration timestamp") > started):
        raise ValueError("captured declaration differs from original pre-run source-authored bytes")
    if set(decl["metrics"]) != set(LABELS):
        raise ValueError("declaration labels differ from the weight-handoff metric set")
    out: dict[str, Any] = {"r": r, "receipt_file": receipt_file, "kld_after": k["after"], "complete_after": done,
                           "residency": residency, "chain": chain}
    if final:
        bs = r.get("bootstrap")
        if not isinstance(bs, dict) or set(bs) != {"seed", "resamples", "method", "percentiles"}:
            raise ValueError("bootstrap block malformed")
        d = derive_metrics(kraw, n, ref=ref["choice"], n_prompt=ps["n_prompt"], n_cont=ps["n_cont"],
                           seed=bs["seed"], resamples=bs["resamples"])
        rows = r.get("metrics")
        if not isinstance(rows, list) or [m.get("native_label") for m in rows] != list(LABELS):
            raise ValueError("native metrics missing or reordered")
        for m in rows:
            lab = m["native_label"]
            dd = decl["metrics"][lab]
            if not isinstance(dd, dict) or set(dd) != {"unit", "metric_direction", "category", "metric"} or not all(isinstance(dd[x], str) and dd[x].strip() for x in dd):
                raise ValueError("metric declaration incomplete")
            if dd["metric_direction"] not in {"higher_better", "lower_better"} or dd["category"] not in {"OPTIMUM", "BASELINE", "CANDIDATE"}:
                raise ValueError("metric direction/category outside ClaimTuple vocabulary")
            if any(m.get(x) != dd[x] for x in dd):
                raise ValueError("metric declaration does not match captured row")
            if type(m.get("value")) not in (int, float) or not _close(m["value"], d["values"][lab]):
                raise ValueError(f"{lab} does not re-derive from kld.jsonl")
            if lab in CI_LABELS:
                ci = m.get("ci95")
                if not (isinstance(ci, list) and len(ci) == 2 and all(_close(a, b) for a, b in zip(ci, d["ci95"][lab]))):
                    raise ValueError(f"{lab} CI does not re-derive from kld.jsonl")
            elif m.get("ci95") is not None:
                raise ValueError(f"{lab} cannot carry a CI")
        out["derived"] = d
    return out


def _stable_view(block: Any) -> Any:
    return json.loads(json.dumps(block, sort_keys=True))


def read_project(receipt_path: str | Path) -> tuple[ClaimTuple, ...]:
    """Verify the sealed receipt (and its resume chain) and return fully re-derived tuples."""
    try:
        v = _verify_receipt(Path(receipt_path), final=True)
    except ProjectionError:
        raise
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        raise ProjectionError(f"weight-handoff receipt refused: {exc}") from exc
    r, d = v["r"], v["derived"]
    decl = r["metric_declaration"]["metrics"]
    weights = {s: [{"name": Path(x["path"]).name, "sha256": x["sha256"], "size_bytes": x["size_bytes"]} for x in r["weights"][s]["shards"]]
               for s in ("P", "D")}
    ref = r["reference"]
    facts = {
        "run_id": r["run_id"], "protocol_id": r.get("protocol_id"), "n_passages": d["n_passages"], "n_cont": d["n_cont"],
        "arms": ARM_MEANING, "weights": weights, "reference": {"choice": ref["choice"], "json_sha256": ref["json"]["sha256"]},
        "passages": {"manifest_sha256": r["passages"]["manifest"]["sha256"], "binary_sha256": r["passages"]["binary"]["sha256"],
                     "n": r["passages"]["n"], "n_prompt": r["passages"]["n_prompt"]},
        "predeclared_sha256": (r.get("predeclared") or {}).get("sha256"),
        "harness_source_revision": r["producer_source_revision"],
        "harness_binary_sha256": r["producer_binary"]["before"]["sha256"],
        "env": {k: v2 for k, v2 in r["effective_environment"].items()},
        "residency": v["residency"], "kld_jsonl_sha256": r["kld_jsonl"]["after"]["sha256"],
        "bootstrap": r["bootstrap"], "run_chain": v["chain"],
        "loaded_objects": sorted(Path(x["path"]).name for x in r["loaded_shared_objects"]),
        "scope": "per-passage mean KLD over scored continuation tokens, then mean over passages; R and Gate 0 CIs are paired bootstrap over passages; "
                 "no decision threshold is applied by this projection",
    }
    out = []
    for m in r["metrics"]:
        lab = m["native_label"]
        dd = decl[lab]
        ci = d["ci95"].get(lab)
        if lab.startswith("KLD["):
            arm = lab[4]
            claim = (f"Observed mean KLD={m['value']} {dd['unit']} for arm {arm} ({ARM_MEANING[arm]}) over {d['n_passages']} passages x {d['n_cont']} tokens "
                     f"against reference {ref['choice']}; weights P/D and passages per receipt {r['run_id']}.")
        else:
            claim = (f"Observed {lab}={m['value']} {dd['unit']} (95% paired-bootstrap CI {ci[0]}..{ci[1]}) over {d['n_passages']} passages "
                     f"against reference {ref['choice']}; derived from per-arm mean KLD, receipt {r['run_id']}.")
        out.append(ClaimTuple(
            measurement_id=f"weight-handoff:{r['run_id']}:{lab}", metric=dd["metric"], value=m["value"], date=r["ended_at_utc"],
            category=dd["category"], claim=claim, metric_direction=dd["metric_direction"], protocol_id=r.get("protocol_id") or "",
            reps=d["n_passages"], reps_basis="scored passages (paired across arms)", unit=dd["unit"],
            attestation_path=str(Path(receipt_path).absolute()), attestation_sha256=v["receipt_file"]["sha256"],
            attestation_locator=f"weight-handoff:{v['receipt_file']['path']}#{lab}", attestation_present=True,
            attestation_verified=True, source_kind="measurement",
            extra={"native_label": lab, "ci95": ci, "weight_handoff": facts}))
    return tuple(out)
