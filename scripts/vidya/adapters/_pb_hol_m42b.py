"""Bounded M4.2b native-window projection; no protocol, grading or historical warrant.

The pure statistic below is the already-recorded launcher's verdict.py, sha256
b4d0404343392a60f75f87a66d01acc710cf21522ec9e910cc7af3c94987e6bb.
Only the complete four-planned-load ABAB layout is supported here. Its original
proofs and source hashes are checked; read-time input digests are labelled as such.
No native Python is executed. C1/C3 remain prior context, never new measurements.
"""
from __future__ import annotations

import json
import math
import re
import statistics
from pathlib import Path

from claim_tuple import ClaimTuple, ProjectionError

KIND = "pbhol-m4.2b-paired"
AMENDMENT = "AMENDMENT-M4.2b-paired.md"
SOURCE_HASHES = {
    "PREDECLARATION.md": ("predeclaration_sha256", "f8a4dce8447f47a59ff7ad5bded8f187ecc13bdafe773d31aed0f6743192b133"),
    AMENDMENT: ("amendment_paired_sha256", "f10d5fd3ca35551b8028bda33651d7a23ca1c58be855a3bc7bb31be3218c716a"),
    "verdict.py": ("verdict_py_sha256", "b4d0404343392a60f75f87a66d01acc710cf21522ec9e910cc7af3c94987e6bb"),
    "pb_hol_1.py": ("pb_hol_1_py_sha256", "9452fdfd365adff7257e278c30e292bfe606ce41e16a3ed6492de77835da0e26"),
    "diag_sampler.py": ("diag_sampler_py_sha256", "f78cf1abe6cb71e499bc55c14a1ec08e85a3b17b77abf15956cf43e6465d0a59"),
}


def _base():
    from adapters import pb_hol
    return pb_hol


def _read(path):
    return _base()._read(path)


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate JSON object key {key!r}")
        obj[key] = value
    return obj


def _reject_constant(value):
    raise ValueError(f"nonstandard JSON constant {value!r}")


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"nonfinite JSON number {value!r}")
    return number


def _strict_json(raw):
    """Input integrity only: no ambiguous keys or nonstandard NaN/Infinity values."""
    return json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant, parse_float=_finite_float)


def _json(path):
    raw, digest = _read(path)
    try:
        doc = _strict_json(raw)
    except (ValueError, RecursionError) as exc:
        raise ProjectionError(f"M4.2b invalid JSON: {path}") from exc
    if not isinstance(doc, dict):
        raise ProjectionError(f"M4.2b expected JSON object: {path}")
    return doc, digest


def _load_rows(path):
    raw, _ = _read(path)
    try:
        rows = [_strict_json(s) for s in raw.decode("utf-8").splitlines() if s.strip()]
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ProjectionError(f"M4.2b invalid JSONL: {path}") from exc
    if not rows or any(not isinstance(r, dict) for r in rows):
        raise ProjectionError(f"M4.2b expected nonempty object rows: {path}")
    return rows


def root_for(path):
    """Recognize native declarations, never infer a source identity from a directory name."""
    path = Path(path)
    if path.is_file():
        path = path.parent
    found = []
    for p in (path, *list(path.parents)[:3]):
        if (p / "RUN_RECORD.json").is_file():
            record, _ = _json(p / "RUN_RECORD.json")
            if "amendment_paired_sha256" in record:
                found.append(p)
        elif (p / AMENDMENT).is_file():
            found.append(p)  # paired declaration without a record must fail closed
    if len(found) > 1:
        raise ProjectionError("M4.2b ambiguous enclosing launcher records")
    if not found:
        return None
    root = found[0]
    record, _ = _json(root / "RUN_RECORD.json")
    out = root / str(record.get("out", ""))
    aliases = {root, root / "out", out, *(out / f"L{i}-{role}" for i, role in
                enumerate(("champion", "candidate", "champion", "candidate"), 1))}
    if path not in aliases or not path.is_dir() or path.is_symlink():
        raise ProjectionError("M4.2b path is not a native root/output/window/load alias")
    return root


def units(path):
    path = Path(path)
    root = root_for(path)
    if root is not None:
        return [root]  # canonical one-window unit, including load/root/out aliases
    return None


def _recipe(argv):
    """Compare recorded launch recipes, excluding only native per-load endpoints."""
    if not isinstance(argv, list) or not argv or any(not isinstance(s, str) for s in argv):
        raise ProjectionError("M4.2b missing native argv readback")
    recipe, i = [], 1  # argv[0] is the role-bound binary
    while i < len(argv):
        if argv[i] in ("--slot-save-path", "--port"):
            if i + 1 == len(argv):
                raise ProjectionError("M4.2b truncated native per-load endpoint argv")
            i += 2
        else:
            recipe.append(argv[i])
            i += 1
    return recipe


def _directory(path):
    if not path.is_dir() or path.is_symlink():
        raise ProjectionError(f"M4.2b expected nonsymlink directory: {path}")


def _context(root):
    _directory(root)
    record, record_sha = _json(root / "RUN_RECORD.json")
    verdict, verdict_sha = _json(root / "VERDICT.json")
    hashes = {"RUN_RECORD.json": record_sha, "VERDICT.json": verdict_sha}
    for name, (key, supported) in SOURCE_HASHES.items():
        digest = _read(root / name)[1]
        if record.get(key) != digest or digest != supported:
            raise ProjectionError(f"M4.2b {name} recorded source hash mismatch or unsupported native rule")
        hashes[name] = digest
    for role, digest in ROLE_SHA.items():
        if record.get(f"{role}_llama_server_sha256") != digest:
            raise ProjectionError(f"M4.2b {role} recorded binary hash differs from the native rule")
    window = record.get("window_id")
    if not isinstance(window, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,120}", window):
        raise ProjectionError("M4.2b missing recorded window identity")
    relative = f"out/w-{window}"
    if record.get("out") != relative:
        raise ProjectionError("M4.2b recorded output path differs from its window")
    out = root / relative
    _directory(root / "out")
    _directory(out)
    windows = [p for p in (root / "out").iterdir() if p.name.startswith("w-")]
    if windows != [out]:
        raise ProjectionError("M4.2b missing or ambiguous native windows")
    if any(record.get(k) != v for k, v in {"planned_loads_done": 4, "planned_loads": 4,
                                          "replacements_used": 0, "stopped": None}.items()):
        raise ProjectionError("M4.2b requires the complete four planned loads without replacements or stop")
    meta, meta_sha = _json(out / "window.json")
    hashes[f"{relative}/window.json"] = meta_sha
    if (meta.get("window_id") != window or meta.get("plan") != "champion candidate champion candidate"
            or meta != verdict.get("window")):
        raise ProjectionError("M4.2b window metadata disagrees with the recorded verdict")
    prior = verdict.get("decided_from")
    if (not isinstance(prior, dict) or prior.get("sha256") != PRIOR_VERDICT_SHA
            or prior.get("path") != str(PRIOR_VERDICT)
            or record.get("decided_c1_c3_from") != f"{prior['path']} sha256 {prior['sha256']}"):
        raise ProjectionError("M4.2b prior verdict anchor is missing or inconsistent")
    # The path and hash are native recorded identities, not a read-time inferred anchor.
    anchor, anchor_sha = _json(Path(prior["path"]))
    hashes["prior:" + prior["path"]] = anchor_sha
    if anchor_sha != prior["sha256"]:
        raise ProjectionError("M4.2b prior verdict anchor hash mismatch")
    pc = anchor.get("conditions")
    if not isinstance(pc, dict) or any(k not in pc for k in DECIDED):
        raise ProjectionError("M4.2b prior verdict lacks the recorded conditions")
    return record, verdict, hashes, out, {k: pc[k] for k in DECIDED}


def native_rows(path):
    root = root_for(path)
    if root is None:
        return None
    try:
        return _native_rows(root)
    except (TypeError, ValueError, KeyError, IndexError, ZeroDivisionError, OverflowError) as exc:
        raise ProjectionError(f"M4.2b malformed or inconsistent native record: {exc}") from exc


def _native_rows(root):
    record, verdict, hashes, out, prior_conditions = _context(root)
    recs = _load_rows(out / "loads.jsonl")
    hashes[f"{record['out']}/loads.jsonl"] = _read(out / "loads.jsonl")[1]
    expected = [(i, role, f"L{i}-{role}") for i, role in enumerate(
        ("champion", "candidate", "champion", "candidate"), 1)]
    if [(r.get("load"), r.get("role"), r.get("dir")) for r in recs] != expected:
        raise ProjectionError("M4.2b missing, duplicate, extra or non-ABAB load records")
    dirs = {p.name for p in out.iterdir() if p.name.startswith("L")}
    if dirs != {d for _, _, d in expected}:
        raise ProjectionError("M4.2b unrecorded or missing load directory")
    stats, summaries, servers = [], [], []
    for rec in recs:
        if (rec.get("kind") != "planned" or rec.get("window_id") != record["window_id"]
                or rec.get("status") != "complete" or rec.get("harness_rc") != 0 or rec.get("trip")):
            raise ProjectionError("M4.2b incomplete or cross-window load")
        load = out / rec["dir"]
        _directory(load)
        summary, sd = _json(load / "summary.json")
        rows = _load_rows(load / "pb_hol_1.jsonl")
        if summary.get("schema") != _base().SCHEMA or summary.get("status") != "complete":
            raise ProjectionError("M4.2b incomplete or foreign summary")
        role, phase = rec["role"], ROLE_PHASE[rec["role"]]
        if set(summary.get("arms") or {}) != {f"{a}-{phase}" for a in ("A", "B", "C")}:
            raise ProjectionError("M4.2b summary phase differs from recorded role")
        _base()._m4_check_summary_arms(summary, rows)
        server = _base()._m4_server(summary)
        rb = server.get("readback") or {}
        if (server.get("binary_sha256") != ROLE_SHA[role] or server.get("binary") != rec.get("binary")
                or rb.get("exe") != rec.get("binary") or rb.get("exe_matches_binary") is not True
                or rb.get("proc_cmdline_matches_argv") is not True):
            raise ProjectionError("M4.2b native summary binary/readback disagrees with its load")
        po = [r for r in rows if r.get("kind") == "port_ownership"]
        if (len(po) != 1 or po[0].get("argv") != rb.get("proc_cmdline")
                or po[0].get("binary") != rec.get("binary") or po[0].get("pid") != rb.get("pid")):
            raise ProjectionError("M4.2b summary readback is not its native ownership proof")
        if servers and _recipe(rb.get("proc_cmdline")) != _recipe(servers[0]["readback"]["proc_cmdline"]):
            raise ProjectionError("M4.2b compared loads use inconsistent recorded launch recipes")
        _recipe(rb.get("proc_cmdline"))
        for r in rows:
            if r.get("kind") == "run":
                v = r.get("short_ttft_ms")
                if v is not None and (type(v) not in (int, float) or not math.isfinite(v) or v <= 0):
                    raise ProjectionError("M4.2b collision/solo TTFT must be finite and positive")
        st = load_stats(out, rec, record["window_id"])
        if st["why_invalid"]:
            raise ProjectionError(f"M4.2b invalid load: {st['why_invalid']}")
        stats.append(st)
        summaries.append(summary)
        servers.append(server)
        prefix = f"{record['out']}/{rec['dir']}"
        hashes[f"{prefix}/summary.json"] = sd
        hashes[f"{prefix}/pb_hol_1.jsonl"] = _read(load / "pb_hol_1.jsonl")[1]
    c2 = c2_from(stats)
    loads = [{"load": s["load"], "role": s["role"], "kind": s["kind"], "valid": not s["why_invalid"],
              "why_invalid": s["why_invalid"], "drift_flag": s["drift_flag"], "invalid_reps": s["invalid_reps"]}
             for s in stats]
    c2c = {"PASS": "PASS", "PASS_WINDOW_DRIFT": "PASS", "FAIL_LOW": "FAIL", "FAIL_HIGH": "FAIL"}.get(
        c2["cond"], "NOT_MEASURED")
    conds = {**prior_conditions, "C2_off_identity_paired": c2c}
    gate = [conds["C1_srpf_B_over_A_lt_2"], c2c, conds["C3_off_completions_byte_identical"]]
    overall = "FAIL" if "FAIL" in gate else ("PASS" if all(x == "PASS" for x in gate) else "INCOMPLETE")
    outcome = OUTCOME.get(c2["cond"], "INCOMPLETE") if overall != "FAIL" or c2c == "FAIL" else "FAIL_PRIOR"
    if (verdict.get("c2") != c2 or verdict.get("loads") != loads or verdict.get("conditions") != conds
            or verdict.get("verdict") != overall or record.get("verdict") != overall
            or verdict.get("outcome") != outcome or record.get("outcome") != outcome):
        raise ProjectionError("M4.2b paired statistic/partition/conditions/verdict do not re-derive")
    # Check native per-load non-gating details too; never silently carry forged diagnostics.
    per_load = [{k: s.get(k) for k in ("load", "role", "kind", "ratio", "rep_ratios", "c_drift_ms", "drift_flag",
                                      "C_start", "C_end", "solo_64k_s", "vram_peak_mib", "own_vram_gib_at_ready")}
                for s in stats]
    if (verdict.get("NON_GATING") or {}).get("per_load") != per_load:
        raise ProjectionError("M4.2b non-gating per-load detail does not re-derive")
    return [{"kind": KIND, "root": str(root), "record": record, "verdict": verdict,
             "read_time_sha256": hashes, "summary": summaries[-1], "server": servers[-1]}]


def project(native):
    # A native row passed by a caller is re-read, just like source ingestion; caller dictionaries
    # cannot skip the native record/hash checks or upgrade the warrant.
    fresh = native_rows(Path(native.get("root", "")))
    if not fresh or fresh[0] != native:
        raise ProjectionError("M4.2b native row changed or did not come from the recorded window")
    record, verdict, hashes = native["record"], native["verdict"], native["read_time_sha256"]
    c2 = verdict["c2"]
    window = record["window_id"]
    native_scope = {"server": native["server"], "phase": "off512", "ctx": {"record": record}}
    obs = {"retrofit": True, "anchor_value": REF_RATIO, "effect_rel": c2["pooled_paired_ratio"] - 1,
           "n_pairs": c2["n_pairs"], "outcome_native": c2["cond"],
           "outcome_reason": "C2_off_identity_paired; native two-sided identity band 19.845-24.255 on 22.05 x pooled paired ratio"}
    # Existing C2 PASS -> null mapping only. FAIL_LOW is NOT an improvement.
    if verdict["verdict"] in ("PASS", "FAIL") and c2["cond"] in ("PASS", "PASS_WINDOW_DRIFT"):
        obs["outcome"] = _base()._M4_OUTCOME["C2"]["PASS"]
    return ClaimTuple(
        measurement_id=f"pbhol-m42b:v1:{window}:{hashes['VERDICT.json'][:16]}:C2_off_identity_paired",
        metric="pbhol_m42b_c2_paired_ratio", value=c2["C2_paired"], unit="ratio",
        date=str(native["summary"].get("finished") or ""), category="CANDIDATE", metric_direction="lower_better",
        claim=(f"M4.2b paired off-path C2 {c2['C2_paired']}x (22.05 x native pooled adjacent-pair ratio "
               f"{c2['pooled_paired_ratio']}; {c2['n_pairs']} overlapping pairs from four ABAB loads); "
               f"native two-sided identity condition {c2['cond']}; run verdict {verdict['verdict']}; "
               "harness-local predeclaration, retrospective observation without a ratified protocol"),
        protocol_id="", reps=c2["n_pairs"], reps_basis="overlapping adjacent champion/candidate load pairs; not independent repetitions",
        attestation_locator=f"pbhol-m42b:{window}:VERDICT.json#C2_off_identity_paired",
        attestation_sha256=hashes["VERDICT.json"], attestation_present=True, attestation_verified=True,
        source_kind=_base().SOURCE_KIND, applicability=_base()._m4_scope(native_scope, ["kernel_build"]),
        observation=obs, extra={"kind": KIND, "run_dir": native["root"], "window_id": window,
            "c2": c2, "loads": verdict["loads"], "prior_decided_from": verdict["decided_from"],
            "native_record": record, "read_time_sha256": hashes,
            "digest_caveat": "input digests computed on read are not original run-time recorded measurement warrants"})


# Existing native arithmetic: constants and pure functions transcribed from the pinned
# verdict.py. Only input reading is replaced by the adapter's bounded JSONL reader.
MIN_VALID = 2                      # valid A and valid B reps per load
MIN_LOADS = 2                      # valid loads per binary
MIN_PAIRS = 2                      # adjacent champion/candidate pairs
MIN_COLLIDE_FRAC = 0.40
C_REPS = 3                         # solo shorts at each end of a load
PBHOL1_C = (278.4, 281.2)          # PB-HOL-1 C-solo (runs/20261021T160010Z), the ONLY C-solo values PB-HOL-1 has
DRIFT_BAR_MS = round(max(PBHOL1_C) - min(PBHOL1_C), 3)   # 2.8 ms (task text: "the C-solo spread of PB-HOL-1"): a FLAG now
VRAM_GUARD_MIB = 61440
RES_MIN_GIB = 40.0
ROLE_SHA = {"champion": "f0fe65c83f397dae0f40cb2bbf15223bef9be3df455f338409d5037699093882",    # gpu-20261023-141e4bcf5-lbh
            "candidate": "901743a0fc26bc2b4e9cfcabe3c3f8d46c9cbd7d6249e088f41ba2af417e3d90"}   # gpu-20261023-c6ca031ac-m4 (= M4.1)
ROLE_PHASE = {"champion": "off512ch", "candidate": "off512"}
REF_RATIO, REF_TOL = 22.05, 0.10   # PB-HOL-1 band, UNCHANGED (operator 2026-10-24): applied to C2_paired = 22.05 x P
SENS_REL_BARS = (0.05, 0.10)       # NON-GATING: relative drift bars, and P over unflagged pairs only
PRIOR_VERDICT = Path("/mnt/raid0/llm/tmp/f8-launchers-20261023/m4-srpf-pbhol/VERDICT.json")
PRIOR_VERDICT_SHA = "4b47d4b766fbb194a7ca69d04b72c8668a9a20b5982305f52c8bd79f580c2078"
DECIDED = ["C1_srpf_B_over_A_lt_2", "C1_srpf512", "C1_srpf2048", "C3_off_completions_byte_identical"]
OUTCOME = {"PASS": "PASS", "PASS_WINDOW_DRIFT": "WINDOW_DRIFT_ONLY", "FAIL_LOW": "FAIL_CANDIDATE", "FAIL_HIGH": "FAIL_CANDIDATE",
           "NOT_MEASURED": "INCOMPLETE"}

def in_band(x: float) -> bool:
    """The M4.2a comparison code, unchanged."""
    return REF_RATIO * (1 - REF_TOL) <= x <= REF_RATIO * (1 + REF_TOL)


def valid_run(r: dict) -> tuple:
    """M4.2a AMENDMENT section 2 predicate, unchanged (byte-for-byte logic of ../m4-srpf-pbhol-2a/verdict.py valid_run)."""
    if r.get("skipped"):
        return False, "skipped: " + str(r["skipped"])
    if r.get("short_http") != 200 or r.get("short_error") or r.get("short_ttft_ms") is None:
        return False, f"short failed (http {r.get('short_http')}, {str(r.get('short_error'))[:60]})"
    p = r.get("long_progress_at_send")
    if not p or p[1] < MIN_COLLIDE_FRAC:
        return False, f"no collision: long progress at send {p}"
    if r.get("long_error"):
        return False, f"no collision: long errored ({str(r.get('long_error'))[:60]})"
    lt, ls, ss = r.get("long_ttft_ms"), r.get("long_t_send"), r.get("short_t_send")
    if lt is not None:
        if ls is None or ss is None:
            return False, "no collision proof: long_t_send/short_t_send missing"
        if ls + lt / 1000.0 <= ss:
            return False, f"no collision: long first token {ls + lt / 1000.0 - ss:+.2f} s vs short send (not after it)"
    return True, ""


def load_stats(out: Path, rec: dict, window: str) -> dict:
    """One load: its numbers, its validity reasons (empty list = VALID) and its drift flag (never a validity reason)."""
    role = rec.get("role")
    st = {"load": rec.get("load"), "role": role, "kind": rec.get("kind"), "dir": rec.get("dir"), "why_invalid": [],
          "A": [], "B": [], "C_start": [], "C_end": [], "invalid_reps": [], "drift_flag": None}
    why = st["why_invalid"]
    if role not in ROLE_SHA:
        why.append(f"unknown role {role!r}")
        return st
    if rec.get("window_id") != window:
        why.append(f"window {rec.get('window_id')} != {window} (never pooled across windows)")
    if rec.get("harness_rc") != 0 or rec.get("status") != "complete":
        why.append(f"harness rc={rec.get('harness_rc')} status={rec.get('status')}")
    if rec.get("trip"):
        why.append(f"guard trip: {rec['trip']}")
    pk = rec.get("vram_peak_mib")
    st["vram_peak_mib"] = pk
    if pk is None:
        why.append("own-pid VRAM peak is null (no residency proof from the job watcher)")
    elif pk > VRAM_GUARD_MIB:
        why.append(f"own-pid VRAM peak {pk} MiB > guard {VRAM_GUARD_MIB}")
    f = out / str(rec.get("dir", "")) / "pb_hol_1.jsonl"
    rows = _load_rows(f)
    if not rows:
        why.append(f"no rows in {f}")
        return st
    phase = ROLE_PHASE[role]
    po = [r for r in rows if r.get("kind") == "port_ownership"]
    if len(po) != 1 or not po[0].get("ok"):
        why.append(f"port ownership proof: {len(po)} rows, ok={[r.get('ok') for r in po]}")
    if po and po[0].get("binary_sha256") != ROLE_SHA[role]:
        why.append(f"binary sha {po[0].get('binary_sha256')} != the {role} store sha")
    if po and po[0].get("phase") != phase:
        why.append(f"phase {po[0].get('phase')} != {phase} for role {role}")
    gp = [r for r in rows if r.get("kind") == "graphs_proof"]
    if not gp or any(r.get("graphs") != "ON" or r.get("HSA_OVERRIDE_CPU_AFFINITY_DEBUG") != "0" for r in gp):
        why.append(f"graphs/HSA proof: {[(r.get('graphs'), r.get('HSA_OVERRIDE_CPU_AFFINITY_DEBUG')) for r in gp]}")
    rs = [r for r in rows if r.get("kind") == "residency"]
    st["own_vram_gib_at_ready"] = [r.get("own_vram_gib") for r in rs]
    if not rs or any(not r.get("ok") or (r.get("own_vram_gib") or 0) < RES_MIN_GIB for r in rs):
        why.append(f"residency: {st['own_vram_gib_at_ready']}")
    runs = [r for r in rows if r.get("kind") == "run"]
    cs = [r for r in runs if r.get("arm") == "C"]
    # clause 5, AMENDED: a FLAG, never a validity reason
    if len(cs) != 2 * C_REPS or any(r.get("short_ttft_ms") is None or r.get("short_error") or r.get("short_http") != 200 for r in cs):
        st["drift_flag"] = f"C-solo drift not measurable: {len(cs)} solo rows (want {2 * C_REPS}, all answered)"
    else:
        st["C_start"] = [r["short_ttft_ms"] for r in cs[:C_REPS]]
        st["C_end"] = [r["short_ttft_ms"] for r in cs[C_REPS:]]
        st["c_drift_ms"] = round(statistics.median(st["C_end"]) - statistics.median(st["C_start"]), 3)
        if st["c_drift_ms"] > DRIFT_BAR_MS:
            st["drift_flag"] = f"C-solo drift {st['c_drift_ms']:+.1f} ms > {DRIFT_BAR_MS} ms (PB-HOL-1 C-solo spread)"
    for r in runs:
        arm = str(r.get("arm", "")).split("-")[0]
        if arm not in ("A", "B"):
            continue
        ok, w = valid_run(r)
        if ok:
            st[arm].append(r["short_ttft_ms"])
        else:
            st["invalid_reps"].append({"arm": r.get("arm"), "rep": r.get("rep"), "why": w})
    if len(st["A"]) < MIN_VALID or len(st["B"]) < MIN_VALID:
        why.append(f"valid reps A={len(st['A'])} B={len(st['B'])} (< {MIN_VALID})")
    cal = [r.get("long_ttft_s") for r in rows if r.get("kind") == "calibration" and r.get("long_ttft_s")]
    st["solo_64k_s"] = cal[0] if cal else None
    if st["A"] and st["B"]:
        ma = statistics.median(st["A"])
        st["medA"], st["medB"] = ma, statistics.median(st["B"])
        st["c2_raw"] = st["medB"] / ma
        st["ratio"] = round(st["c2_raw"], 3)
        st["rep_ratios"] = [round(b / ma, 3) for b in st["B"]]
    return st


def _flag(s: dict, rel=None):
    """Gating flag (rel None: the 2.8 ms bar) or a NON-GATING relative bar."""
    if rel is None:
        return s.get("drift_flag")
    if "c_drift_ms" not in s or not s["C_start"]:
        return s.get("drift_flag")
    return "drift" if s["c_drift_ms"] > rel * statistics.median(s["C_start"]) else None


def adjacent_pairs(valid: list, rel=None) -> list:
    pairs = []
    for x, y in zip(valid, valid[1:]):
        if x["role"] == y["role"]:
            continue
        c, h = (x, y) if x["role"] == "candidate" else (y, x)
        fl = [f"L{s['load']}: {_flag(s, rel)}" for s in (x, y) if _flag(s, rel)]
        pairs.append({"loads": [x["load"], y["load"]], "order": f"{x['role']}->{y['role']}",
                      "candidate_c2": round(c["c2_raw"], 3), "champion_c2": round(h["c2_raw"], 3),
                      "p": c["c2_raw"] / h["c2_raw"], "drift_flag": fl or None})
    return pairs


def pooled(pairs: list) -> float:
    return math.exp(statistics.fmean(math.log(q["p"]) for q in pairs))


def c2_from(loads: list) -> dict:
    valid = sorted([s for s in loads if not s["why_invalid"]], key=lambda s: s["load"])
    ch = [s for s in valid if s["role"] == "champion"]
    m4 = [s for s in valid if s["role"] == "candidate"]
    res = {"valid_champion_loads": [s["load"] for s in ch], "valid_candidate_loads": [s["load"] for s in m4],
           "band": [round(REF_RATIO * (1 - REF_TOL), 3), round(REF_RATIO * (1 + REF_TOL), 3)]}
    if len(ch) < MIN_LOADS or len(m4) < MIN_LOADS:
        res.update(cond="NOT_MEASURED", why=f"valid loads champion={len(ch)} candidate={len(m4)} (< {MIN_LOADS} of either)")
        return res
    pairs = adjacent_pairs(valid)
    res["pairs"] = [{**q, "p": round(q["p"], 4)} for q in pairs]
    if len(pairs) < MIN_PAIRS:
        res.update(cond="NOT_MEASURED", why=f"{len(pairs)} adjacent champion/candidate pair(s) among the valid loads (< {MIN_PAIRS})")
        return res
    P = pooled(pairs)
    C2p = round(REF_RATIO * P, 3)
    cha = [x for s in ch for x in s["A"]]
    chb = [x for s in ch for x in s["B"]]
    m4a = [x for s in m4 for x in s["A"]]
    m4b = [x for s in m4 for x in s["B"]]
    champ = round(statistics.median(chb) / statistics.median(cha), 3)
    cand = round(statistics.median(m4b) / statistics.median(m4a), 3)
    flagged = [q["loads"] for q in pairs if q["drift_flag"]]
    window_drift = []
    if flagged:
        window_drift.append(f"{len(flagged)}/{len(pairs)} pairs drift-flagged {flagged}")
    if not in_band(champ):
        window_drift.append(f"champion pooled C2 {champ} outside the band")
    if not in_band(C2p):
        cond = "FAIL_LOW" if C2p < REF_RATIO * (1 - REF_TOL) else "FAIL_HIGH"
    else:
        cond = "PASS_WINDOW_DRIFT" if window_drift else "PASS"
    res.update(cond=cond, pooled_paired_ratio=round(P, 4), C2_paired=C2p, n_pairs=len(pairs), flagged_pairs=flagged,
               window_drift=window_drift or None, champion_pooled_c2=champ, champion_pooled_c2_in_band=in_band(champ),
               candidate_pooled_c2_raw=cand, candidate_pooled_c2_raw_in_band=in_band(cand))
    return res
