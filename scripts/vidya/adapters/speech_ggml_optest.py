"""VB-SPEECH-KOPT-1: speech-ggml and v11 gfx90a op-test records (CS-43.1, CH-18.d), written before
they run.

Two measured record kinds and one literature kind (``record_kind``):

* ``cs43_1_speech_ggml_optest`` -- conversation-stack CS-43.1: test-backend-ops on the upstream ggml
  carried by a NEW qwentts.cpp-experimental branch (gfx90a HIP + CPU builds), plus the HIP-graphs
  and fusion on/off identity checks and the first autoregressive divergence step.
* ``ch18d_v11_gfx90a_optest`` -- autokernel-champion-aggregate CH-18.d: the v11 candidate's gfx90a
  op tests after the speech-intake pulls (``-o ARGSORT`` 1025/2047/2048 columns, ``-o TOP_K``).
* ``upstream_statement`` -- an upstream PR statement or an author-run op-test count. LITERATURE
  only: the reader keeps it out of :func:`native_rows`, ``project()`` refuses it, and
  :func:`literature_rows` hands it to the research-intake lane.

Every measured row carries: backend, device arch, rocm_version, ggml sha and version,
local_patch_count, suite case count, op and case columns, HIP graphs on/off, fusion on/off and the
first-divergence step (null only with the number of steps checked), the pass/fail/not-supported
counts, the tree (repo, branch, commit), the binary sha256 and -- for a HIP/ROCm backend -- the
residency proof (``verify_ggml_linkage.sh`` plus VRAM sampled during the run).

WHICH LADDER. There is no separate "kernel-correctness ladder" in the substrate: the existing
test-backend-ops source (``autokernel_property.py``, row "`test-backend-ops` property-layer
residuals" in the README) registers as the ``measurement`` class and is graded by
``claim_tuple.grade()``. This adapter projects into exactly that -- same class, same single ladder,
same ``lower_better`` direction on failure counts -- and adds no grading rule.

Protocol. An op-test run inside an experimental tree is a ``P-AK-SEARCH-1`` search record ("not a
claim"), so no citation is carried into ``ClaimTuple.protocol_id`` today: every tuple is an
OBSERVATION and the producer's citation is kept verbatim in ``extra.protocol_id_native``.
``ADMISSIBLE_PROTOCOLS`` is the one place to add an id once one is ratified for these records.
"""

from __future__ import annotations

import re
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

SCHEMA = "epyc.vidya.speech_ggml_optest.v1"
SIDECAR_NAME = "speech_ggml_optest.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.speech_ggml_optest/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "speech-ggml-optest-measurement"

LITERATURE_KIND = "upstream_statement"
#: kind -> (program, substring the tree's repo must contain)
MEASURED_KINDS = {
    "meta_qwen4exp_native": ("META-qwen4exp", "llama"),
    "cs43_1_speech_ggml_optest": ("CS-43.1", "qwentts"),
    "ch18d_v11_gfx90a_optest": ("CH-18.d", "llama"),
}
RECORD_KINDS = frozenset(MEASURED_KINDS) | {LITERATURE_KIND}
#: metric -> direction. Both count failing cases out of ``suite_case_count``.
METRICS = {
    "meta_qwen4exp_failed_cases": "lower_better",
    "test_backend_ops_failed_cases": "lower_better",
    "graphs_fusion_identity_mismatch_cases": "lower_better",
}
ADMISSIBLE_PROTOCOLS: frozenset[str] = frozenset()
HIP_BACKEND = re.compile(r"(rocm|hip)", re.IGNORECASE)

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SHA_LIKE = re.compile(r"^[0-9a-f]{7,64}$")


def _hex64(v: Any) -> bool:
    return isinstance(v, str) and bool(_HEX64.match(v))


def _sha_like(v: Any) -> bool:
    return isinstance(v, str) and bool(_SHA_LIKE.match(v))


def _pos_int(v: Any) -> bool:
    return ns.nonneg_int(v) and v >= 1


def _fields_problems(kind: str, f: Mapping[str, Any], row: Mapping[str, Any]) -> list[str]:
    if kind == "meta_qwen4exp_native":
        p = []
        for key in ("backend", "device_arch", "op", "binary_sha256", "residency_proof", "source_seal_sha256", "binding_sha256"):
            if not ns.text(f.get(key)):
                p.append(f"fields.{key} is required")
        for key in ("binary_sha256", "source_seal_sha256", "binding_sha256"):
            if not _hex64(f.get(key)): p.append(f"fields.{key} must be sha256")
        if f.get("op") != "qwen4exp-meta-moe-nmse" or f.get("backend") != "ROCm0": p.append("wrong native scope")
        if f.get("suite_case_count") != 1 or f.get("n_failed") not in (0, 1) or row.get("value") != f.get("n_failed") or row.get("reps") != 1: p.append("invalid case count")
        if not ns.nonneg_int(f.get("positive_device_samples")) or f["positive_device_samples"] < 2: p.append("missing during-run residency")
        if not isinstance(f.get("tree"), dict) or f["tree"].get("commit") != "520ad4f55d805a544862be88d652ec68fcd194ab": p.append("wrong candidate")
        return p
    p = [f"fields.{k} must be a non-empty string"
         for k in ("backend", "device_arch", "rocm_version", "ggml_version", "op")
         if not ns.text(f.get(k))]
    if not _sha_like(f.get("ggml_sha")):
        p.append("fields.ggml_sha must be a hex git sha")
    if not ns.nonneg_int(f.get("local_patch_count")):
        p.append("fields.local_patch_count must be an integer >= 0")
    if not _pos_int(f.get("suite_case_count")):
        p.append("fields.suite_case_count must be an integer >= 1")
    cols = f.get("case_columns")
    if not isinstance(cols, list) or (not cols and f.get("op") != "ALL") or not all(
            ns.nonneg_int(c) or ns.text(c) for c in cols):
        p.append("fields.case_columns must list the case columns (empty only for op='ALL')")
    for k in ("hip_graphs", "fusion"):
        if not isinstance(f.get(k), bool):
            p.append(f"fields.{k} must be a boolean (on/off)")
    step, checked = f.get("first_divergence_step"), f.get("divergence_steps_checked")
    if not ns.nonneg_int(checked):
        p.append("fields.divergence_steps_checked must be an integer >= 0")
    elif "first_divergence_step" not in f or not (
            step is None or (ns.nonneg_int(step) and step < max(checked, 1))):
        p.append("fields.first_divergence_step must be recorded: the step index, or null when no "
                 "divergence occurred within divergence_steps_checked")
    counts = [f.get(k) for k in ("n_passed", "n_failed", "n_not_supported")]
    if not all(ns.nonneg_int(c) for c in counts):
        p.append("fields.n_passed / n_failed / n_not_supported must be integers >= 0")
    elif sum(counts) != f.get("suite_case_count"):
        p.append("n_passed + n_failed + n_not_supported must equal suite_case_count")
    elif row.get("value") != f["n_failed"]:
        p.append("value must equal fields.n_failed")
    tree = f.get("tree")
    _, repo_needle = MEASURED_KINDS[kind]
    if not isinstance(tree, dict) or not all(ns.text(tree.get(k)) for k in ("repo", "branch")) \
            or not _sha_like(tree.get("commit")):
        p.append("fields.tree must carry repo, branch and commit")
    elif repo_needle not in tree["repo"].lower():
        p.append(f"{kind} runs on a {repo_needle} tree (got {tree['repo']!r})")
    if not _hex64(f.get("binary_sha256")):
        p.append("fields.binary_sha256 must be a 64-hex sha256")
    if HIP_BACKEND.search(str(f.get("backend", ""))) and not ns.text(f.get("residency_proof")):
        p.append("fields.residency_proof is required on a HIP/ROCm row (verify_ggml_linkage.sh "
                 "plus VRAM sampled during the run)")
    if row.get("reps") != f.get("suite_case_count"):
        p.append("reps must equal fields.suite_case_count")
    return p


def _literature_problems(f: Any) -> list[str]:
    if not isinstance(f, dict):
        return ["fields must be an object"]
    p = [f"fields.{k} must be a non-empty string"
         for k in ("pr_ref", "url", "author", "statement") if not ns.text(f.get(k))]
    if not (isinstance(f.get("published_date"), str)
            and re.match(r"^\d{4}-\d{2}-\d{2}$", f["published_date"])):
        p.append("fields.published_date must be YYYY-MM-DD")
    if "author_run_case_count" in f and not ns.nonneg_int(f["author_run_case_count"]):
        p.append("fields.author_run_case_count must be an integer >= 0 when present")
    return p


def _identity(row: Mapping[str, Any]) -> str:
    prefix = "kopt_lit_" if row["record_kind"] == LITERATURE_KIND else "kopt_"
    return prefix + ns.content_hash({
        "run_id": row["run_id"], "kind": row["record_kind"], "metric": row.get("metric"),
        "results": row.get("results_sha256"), "fields": row.get("fields")})[:24]


def validate_row(row: Any) -> list[str]:
    if not isinstance(row, dict):
        return ["row is not a JSON object"]
    p: list[str] = []
    if row.get("schema") != SCHEMA:
        p.append(f"schema must be {SCHEMA!r}")
    kind = row.get("record_kind")
    if kind not in RECORD_KINDS:
        return p + [f"record_kind must be one of {sorted(RECORD_KINDS)}"]
    for key in ("run_id", "producer", "measurement_id", "claim"):
        if not ns.text(row.get(key)):
            p.append(f"{key} must be a non-empty string")
    if not ns.utc_timestamp(row.get("emitted_at")):
        p.append("emitted_at must be a UTC timestamp")
    if kind == LITERATURE_KIND:
        if row.get("source_class") != "literature":
            p.append("an upstream_statement row must say source_class='literature'")
        p += _literature_problems(row.get("fields"))
    else:
        metric = row.get("metric")
        if metric not in METRICS:
            p.append(f"metric must be one of {sorted(METRICS)}")
        elif row.get("metric_direction") != METRICS[metric]:
            p.append(f"metric {metric!r} is {METRICS[metric]}")
        if not ns.finite(row.get("value")):
            p.append("value must be a finite number")
        for key in ("unit", "date", "results_path", "reps_basis"):
            if not ns.text(row.get(key)):
                p.append(f"{key} must be a non-empty string")
        if not _hex64(row.get("results_sha256")):
            p.append("results_sha256 must be a 64-hex digest over the attested file")
        if row.get("category") not in ns.CATEGORIES:
            p.append("category must be exactly one of OPTIMUM/BASELINE/CANDIDATE")
        pid = row.get("protocol_id")
        if pid is not None and not ns.text(pid):
            p.append("protocol_id must be null or a non-empty string")
        if row.get("program") != MEASURED_KINDS[kind][0]:
            p.append(f"program must be {MEASURED_KINDS[kind][0]!r} for {kind}")
        f = row.get("fields")
        p += (_fields_problems(kind, f, row) if isinstance(f, dict)
              else ["fields must be an object"])
    if not p and row.get("measurement_id") != _identity(row):
        p.append("measurement_id does not re-derive from its identity parts")
    return p + ns.self_hash_problems(row)


def build_row(rec: Mapping[str, Any], *, run_id: str, producer: str, emitted_at: str,
              results_path: str | None = None, results_sha256: str | None = None) -> dict:
    kind = rec.get("record_kind")
    if kind not in RECORD_KINDS:
        raise CaptureError(f"unknown record_kind {kind!r}")
    f = dict(rec.get("fields") or {})
    row: dict[str, Any] = {"schema": SCHEMA, "run_id": run_id, "producer": producer,
                           "emitted_at": emitted_at, "record_kind": kind, "fields": f}
    if kind == LITERATURE_KIND:
        row["source_class"] = "literature"
        row["claim"] = (f"LITERATURE (upstream {f.get('pr_ref')}, {f.get('author')}, "
                        f"{f.get('published_date')}): {f.get('statement')} -- not our measurement")
    else:
        metric = rec.get("metric", "meta_qwen4exp_failed_cases" if kind == "meta_qwen4exp_native" else "test_backend_ops_failed_cases")
        program = MEASURED_KINDS[kind][0]
        row.update(program=program, metric=metric, value=f.get("n_failed"), unit="cases",
                   metric_direction=METRICS.get(metric), date=emitted_at[:10],
                   category=rec.get("category", "CANDIDATE"),
                   protocol_id=rec.get("protocol_id"), reps=f.get("suite_case_count"),
                   reps_basis="scored:cases", results_path=results_path,
                   results_sha256=results_sha256)
        tree = f.get("tree") if isinstance(f.get("tree"), dict) else {}
        row["claim"] = (
            f"{program} {metric}={f.get('n_failed')} of {f.get('suite_case_count')} cases "
            f"(op {f.get('op')} cols {f.get('case_columns')}) on {f.get('backend')} "
            f"{f.get('device_arch')} rocm {f.get('rocm_version')}, ggml {f.get('ggml_version')}@"
            f"{f.get('ggml_sha')} with {f.get('local_patch_count')} local patches, hip_graphs="
            f"{f.get('hip_graphs')} fusion={f.get('fusion')}, first divergence step "
            f"{f.get('first_divergence_step')}/{f.get('divergence_steps_checked')} "
            f"[{tree.get('repo')}@{tree.get('branch')} {tree.get('commit')}]")
    if kind == "meta_qwen4exp_native":
        row["claim"] = f"Synthetic qwen4exp Meta MoE NMSE fixture: {f.get('n_failed')} failed of one; not a full C5 gate or model-quality claim"
    try:
        row["measurement_id"] = _identity(row)
    except CaptureError as exc:
        raise CaptureError(f"{kind}: {exc}") from exc
    ns.seal(row)
    problems = validate_row(row)
    if problems:
        raise CaptureError(f"{kind}: refusing to emit an invalid row: " + "; ".join(problems))
    return row


def write_belief_measurements(
    out_dir: str | Path, *, run_id: str, producer: str, results_path: str | Path,
    records: list[Mapping[str, Any]], emitted_at: str | None = None,
) -> Path:
    """``records``: ``{record_kind, metric?, category?, protocol_id?, fields}``. Raises CaptureError."""
    results = Path(results_path)
    if not results.is_file():
        raise CaptureError(f"results artifact missing: {results}")
    if not records:
        raise CaptureError("at least one record is required")
    digest = ns.file_sha256(results)
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = [build_row(r, run_id=run_id, producer=producer, emitted_at=when,
                      results_path=str(results), results_sha256=digest) for r in records]
    if len({r["measurement_id"] for r in rows}) != len(rows):
        raise CaptureError("duplicate measurement identity in one write")
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


def _load(sidecar_path: str | Path) -> list[dict]:
    path = Path(sidecar_path)
    return (ns.load_rows(path, validate_row) or []) if path.is_file() else []


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    """Measured rows only; an invalid row voids the whole file (the writer is atomic)."""
    return tuple({"row": r, "sidecar_path": str(sidecar_path),
                  "attestation_present": ns.results_present(r)}
                 for r in _load(sidecar_path) if r["record_kind"] != LITERATURE_KIND)


def literature_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    """Upstream PR statements and author-run counts, for the research-intake lane only."""
    return tuple(r for r in _load(sidecar_path) if r["record_kind"] == LITERATURE_KIND)


def rows_for_run(run_dir: str | Path) -> tuple[dict, ...]:
    return native_rows(Path(run_dir) / SIDECAR_NAME)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    """Projection only, into the measurement class -- the same class and the same single ladder as
    the existing test-backend-ops source. ``claim_tuple.grade()`` decides."""
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("speech op-test native row must retain the producer row")
    row = native["row"]
    if row.get("record_kind") == LITERATURE_KIND:
        raise ProjectionError(
            "upstream_statement refused as a measurement: upstream PR statements and author-run "
            "op-test counts enter only as literature-class claims (research intake)")
    problems = validate_row(row)
    if problems:
        raise ProjectionError("speech op-test row is not a producer-authored capture: "
                              + "; ".join(problems))
    f = row["fields"]
    if row["record_kind"] == "meta_qwen4exp_native":
        try:
            result_path = Path(row["results_path"])
            if not ns.results_present(row): raise ValueError("result digest")
            result = json.loads(result_path.read_text())
            if result.get("schema") != "epyc.model_free_backend_correctness.v1" or result.get("source_commit") != f["tree"]["commit"] or result.get("source_seal_sha256") != f["source_seal_sha256"] or result.get("binding_sha256") != f["binding_sha256"]: raise ValueError("result identity")
            if result.get("gates", {}).get("fixture_process_rc") != 0 or result["gates"].get("meta_moe_nmse") != "OK" or not result.get("reaped"): raise ValueError("fixture status")
            for filename, digest in result["raw_sha256"].items():
                if filename not in ("stdout", "stderr", "residency.jsonl", "linkage.log") or ns.file_sha256(result_path.parent / filename) != digest: raise ValueError("raw digest")
            if set(result["raw_sha256"]) != {"stdout", "stderr", "residency.jsonl", "linkage.log"}: raise ValueError("raw set")
            samples = [json.loads(line) for line in (result_path.parent / "residency.jsonl").read_text().splitlines()]
            positive = sum(x.get("pid") == result["pid"] and x.get("start_ticks") == result["start_ticks"] and type(x.get("time_ns")) is int and result["start_ns"] <= x["time_ns"] <= result["end_ns"] and x.get("kfd_gpu_id") == result["kfd_gpu_id"] and x.get("pid_in_kfd") is True and isinstance(x.get("vram_bytes"), int) and x["vram_bytes"] > 0 for x in samples)
            if positive < 2 or positive != f["positive_device_samples"] or positive != result["gates"]["positive_device_samples"]: raise ValueError("during-run residency")
        except (OSError, KeyError, TypeError, ValueError) as exc:
            raise ProjectionError("META native proof invalid: " + str(exc)) from exc
    native_pid = row.get("protocol_id")
    protocol_id = native_pid if native_pid in ADMISSIBLE_PROTOCOLS else ""
    present = ns.results_present(row)
    locator = f"speech-ggml-optest:{row['run_id']}:{row['record_kind']}:{f['op']}:{row['results_path']}"
    return ClaimTuple(
        measurement_id=row["measurement_id"], metric=row["metric"], value=row["value"],
        date=row["date"], category=row["category"], claim=row["claim"],
        metric_direction=row["metric_direction"], protocol_id=protocol_id, reps=row["reps"],
        reps_basis=row["reps_basis"], unit=row["unit"],
        attestation_sha256=row["results_sha256"], attestation_locator=locator,
        attestation_present=present, attestation_verified=True if present else None,
        source_kind=SOURCE_KIND,
        applicability={"backend": ("gpu" if row["record_kind"] == "meta_qwen4exp_native" else f["backend"]), "device": f["device_arch"], "op": f["op"],
                       "build_sha": f["tree"]["commit"], "scope_basis": "native"},
        extra={"schema": row["schema"], "record_kind": row["record_kind"],
               "program": row["program"], "producer": row["producer"],
               "emitted_at": row["emitted_at"], "run_id": row["run_id"],
               "row_sha256": row["row_sha256"], "sidecar_path": native.get("sidecar_path", ""),
               "protocol_id_native": native_pid,
               "protocol_status": ("admissible" if protocol_id else
                                   "none_cited" if not native_pid else
                                   "search_record_not_a_claim"),
               "fields": f},
    )


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "SCHEMA", "SIDECAR_NAME", "SOURCE_KIND", "build_row", "frames_for_sidecar",
           "literature_rows", "native_rows", "project", "rows_for_run", "validate_row",
           "write_belief_measurements"]
