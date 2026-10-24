"""VB-UFH12-PARITY: the EmbeddingGemma-2 reference-parity gate (REPL-EMB-2.5 / 2.6) as measurement OBSERVATIONS.

Producer: ``epyc-orchestrator`` ``scripts/benchmark/repl_emb_parity_gate.py`` (opt-in ``--belief-out``) calls
:func:`write_belief_measurements` after it has written ``parity.json``. The gate is VECTOR parity only (finite vectors
and per-item cosine against the sentence-transformers FP32 reference); it makes no recall or speed claim.

One self-hashed row per gated lane x metric, three metrics per lane:

* ``repl_embedder_parity_cos_min``        higher_better  min over the recorded per-item cosines (docs + queries)
* ``repl_embedder_parity_cos_mean``       higher_better  mean over the same per-item values
* ``repl_embedder_parity_nonfinite_vectors`` lower_better  count of vectors with a NaN/Inf anywhere

The reference lane (``st-fp32-full``) is IDENTITY, not a row: it is carried on every row (arm, index identity,
runtime, versions, argv). Lanes with no predeclared threshold (``st-fp32-textonly``, the text-only equivalence check)
are not gate subjects and yield no row.

Every value RE-DERIVES from the per-item cosines carried in the row; the gate verdict word is re-derived
(PASS iff non-finite == 0 and min >= threshold) and must equal the one the gate recorded; the input-set digest
(sha256 canonical over the items' files / chunks / queries) re-derives from the three component digests on the row.
The writer additionally re-derives the digest from ``parity.json`` and ``items.json`` and checks every chunk text
against its recorded hash. A required identity that is missing is REFUSED, never defaulted: runtime, argv, binary
sha256 (GGUF lanes), the flash_attn requested AND resolved values (GGUF lanes), runtime versions (ST lanes),
``scope_complete`` and ``query_set_kind``.

Doctrine: PROJECTION ONLY. ``protocol_id`` is always empty (no codified protocol), so the shared ladder caps the tuples;
``claim_tuple.grade()`` decides. The 2026-10-20 parity results (2.5 proxy and probe45, 2.6 BF16 / Q8_0, the champion
rebase) stay RETROSPECTIVE: a ``parity.json`` older than ``MAX_CAPTURE_LAG_S`` at emit time is refused, and the reader
refuses a row whose emit time trails the attested file's mtime by more than that.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

CAPTURE_SCHEMA = "epyc.vidya.repl_embedder_parity.v1"
SIDECAR_NAME = "repl_embedder_parity.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.repl_embedder_parity/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "repl-embedder-parity"
REFERENCE_LANE = "st-fp32-full"
#: predeclared in the gate (``GATES``) before any run; a row carrying another threshold is refused
PREDECLARED_THRESHOLDS = {"st-bf16": 0.99, "gguf-bf16": 0.99, "gguf-q8_0": 0.98}
MIN_CHUNKS = 200
UFH07_QUESTIONS = 45
MAX_CAPTURE_LAG_S = 3600
ST_VERSION_KEYS = ("torch", "transformers", "sentence_transformers")
FA_REQUESTED = frozenset({"auto", "on", "off"})
FA_RESOLVED = frozenset({"on", "off"})
RULE = "zero non-finite vectors AND min per-item cosine >= threshold vs ST FP32 reference"

M_MIN = "repl_embedder_parity_cos_min"
M_MEAN = "repl_embedder_parity_cos_mean"
M_NONFINITE = "repl_embedder_parity_nonfinite_vectors"
METRICS = {
    M_MIN: ("higher_better", "cosine (min over per-item cosines vs ST FP32 reference)"),
    M_MEAN: ("higher_better", "cosine (mean over per-item cosines vs ST FP32 reference)"),
    M_NONFINITE: ("lower_better", "vectors (count with a NaN or Inf)"),
}
SHORT = {M_MIN: "min cosine", M_MEAN: "mean cosine", M_NONFINITE: "non-finite vectors"}
REL = 1e-9
RECORDED_TOL = 2e-6  # the gate rounds each per-item cosine to 6 dp; recorded summaries are unrounded


# --------------------------------------------------------------------------------------------- derivations


def _lane_kind(lane: str) -> str:
    if lane.startswith("st-"):
        return "st"
    if lane.startswith("gguf-"):
        return "gguf"
    raise CaptureError(f"lane {lane!r} is neither an ST nor a GGUF lane")


def input_set_parts(items: Mapping[str, Any]) -> dict[str, str]:
    """Component digests of the input set: sha256 canonical over files / chunks / queries."""
    try:
        return {
            "files_digest": ns.content_hash(items["files"]),
            "chunks_digest": ns.content_hash(items["chunks"]),
            "queries_digest": ns.content_hash(items["queries"]),
        }
    except (KeyError, TypeError) as exc:
        raise CaptureError(f"items must carry files, chunks and queries: {exc}") from exc


def input_set_digest(parts: Mapping[str, str]) -> str:
    return ns.content_hash({k: parts[k] for k in ("files_digest", "chunks_digest", "queries_digest")})


def derive_verdict(nonfinite: int, cos_min: float, threshold: float) -> str:
    return "PASS" if (nonfinite == 0 and cos_min >= threshold) else "FAIL"


def derive_stats(docs_cos: list[float], queries_cos: list[float]) -> dict[str, Any]:
    allv = list(docs_cos) + list(queries_cos)
    return {"cos_min": min(allv), "cos_mean": math.fsum(allv) / len(allv)}


def derive_index_digest(identity: Mapping[str, Any]) -> str:
    body = {k: v for k, v in identity.items() if k != "digest"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def derive_scope_complete(n_chunks: int, n_queries: int, is_ufh07: bool) -> bool:
    return bool(n_chunks >= MIN_CHUNKS and is_ufh07 and n_queries >= UFH07_QUESTIONS)


def _close(a: float, b: float, tol: float = REL) -> bool:
    return math.isclose(a, b, rel_tol=tol, abs_tol=tol)


def _cos_list(xs: Any, n: Any) -> bool:
    return (isinstance(xs, list) and bool(xs) and all(ns.finite(x) and -1.0 - 1e-6 <= x <= 1.0 + 1e-6 for x in xs)
            and ns.nonneg_int(n) and len(xs) == n)


def _argv_ok(argv: Any) -> bool:
    return isinstance(argv, list) and bool(argv) and all(ns.text(a) for a in argv)


def _versions_ok(v: Any, required: tuple[str, ...]) -> bool:
    return (isinstance(v, dict) and all(isinstance(k, str) and ns.text(x) for k, x in v.items())
            and all(k in v for k in required))


def _identity_ok(ident: Any) -> bool:
    return (isinstance(ident, dict) and ns.text(ident.get("model")) and ns.text(ident.get("revision"))
            and isinstance(ident.get("dim"), int) and ns.text(ident.get("dtype")) and ns.text(ident.get("runtime"))
            and ns.text(ident.get("prompt_hash")) and ns.SHA256.match(str(ident.get("digest", ""))) is not None
            and derive_index_digest(ident) == ident["digest"])


# --------------------------------------------------------------------------------------------- reader


def _runtime_problems(e: Mapping[str, Any]) -> list[str]:
    p: list[str] = []
    kind = e.get("lane_kind")
    if kind not in ("st", "gguf"):
        return ["extra.lane_kind must be st or gguf"]
    if not ns.text(e.get("runtime")):
        p.append("extra.runtime must be declared")
    if not _argv_ok(e.get("argv")):
        p.append("extra.argv must be the recorded command line (non-empty list of strings)")
    if kind == "gguf":
        if not ns.SHA256.match(str(e.get("binary_sha256", ""))):
            p.append("extra.binary_sha256 must be the 64-hex digest of the GGUF lane's binary")
        if e.get("flash_attn_requested") not in FA_REQUESTED:
            p.append("extra.flash_attn_requested must be recorded (auto/on/off), not defaulted")
        if e.get("flash_attn_resolved") not in FA_RESOLVED:
            p.append("extra.flash_attn_resolved must be the recorded resolution (on/off), not defaulted")
        if e.get("versions") is not None and not _versions_ok(e["versions"], ()):
            p.append("extra.versions must be a map of non-empty strings")
    else:
        if e.get("binary_sha256") is not None:
            p.append("an ST lane carries no binary_sha256")
        if e.get("flash_attn_requested") != "n/a" or e.get("flash_attn_resolved") != "n/a":
            p.append("an ST lane records flash_attn as n/a")
        if not _versions_ok(e.get("versions"), ST_VERSION_KEYS):
            p.append(f"extra.versions must declare {list(ST_VERSION_KEYS)} for an ST lane")
    return p


def _reference_problems(ref: Any) -> list[str]:
    if not isinstance(ref, dict):
        return ["extra.reference must carry the reference lane identity"]
    p: list[str] = []
    if ref.get("lane") != REFERENCE_LANE:
        p.append(f"extra.reference.lane must be {REFERENCE_LANE!r}")
    if not ns.text(ref.get("arm_id")):
        p.append("extra.reference.arm_id must be recorded")
    if not _identity_ok(ref.get("index_identity")):
        p.append("extra.reference.index_identity must be a well-formed identity whose digest re-derives")
    if not ns.text(ref.get("runtime")) or not _argv_ok(ref.get("argv")):
        p.append("extra.reference runtime and argv must be recorded")
    if not _versions_ok(ref.get("versions"), ST_VERSION_KEYS):
        p.append(f"extra.reference.versions must declare {list(ST_VERSION_KEYS)}")
    if ref.get("nonfinite_vectors") != 0:
        p.append("the reference lane must have zero non-finite vectors")
    return p


def _lane_problems(e: Mapping[str, Any]) -> list[str]:
    p: list[str] = []
    lane = e.get("lane")
    if not isinstance(lane, str) or lane not in PREDECLARED_THRESHOLDS:
        return [f"extra.lane must be one of {sorted(PREDECLARED_THRESHOLDS)}"]
    try:
        kind_ok = _lane_kind(lane) == e.get("lane_kind")
    except CaptureError:
        kind_ok = False
    if not kind_ok:
        p.append("extra.lane_kind does not match the lane")
    if not ns.text(e.get("arm_id")):
        p.append("extra.arm_id must be recorded")
    if not _identity_ok(e.get("index_identity")):
        p.append("extra.index_identity must be a well-formed identity whose digest re-derives")
    if not (isinstance(e.get("threads"), int) and e["threads"] > 0) or isinstance(e.get("threads"), bool):
        p.append("extra.threads must be recorded")
    p += _runtime_problems(e)
    p += _reference_problems(e.get("reference"))
    return p


def _scope_problems(e: Mapping[str, Any]) -> list[str]:
    p: list[str] = []
    s = e.get("input_set")
    if not isinstance(s, dict) or not all(ns.SHA256.match(str(s.get(k, ""))) for k in
                                          ("files_digest", "chunks_digest", "queries_digest")):
        return ["extra.input_set must carry the files / chunks / queries digests"]
    if e.get("input_set_digest") != input_set_digest(s):
        p.append("extra.input_set_digest does not re-derive from its component digests")
    if not ns.SHA256.match(str(e.get("items_sha256", ""))):
        p.append("extra.items_sha256 must be the digest of items.json")
    if not ns.text(e.get("query_set_kind")):
        p.append("extra.query_set_kind must be recorded")
    if not isinstance(e.get("scope_complete"), bool) or not isinstance(e.get("query_set_is_ufh07"), bool):
        p.append("extra.scope_complete and extra.query_set_is_ufh07 must be recorded booleans")
        return p
    n_docs, n_q = e.get("n_docs"), e.get("n_queries")
    if not (ns.nonneg_int(n_docs) and ns.nonneg_int(n_q)):
        return p + ["extra.n_docs and extra.n_queries must be recorded counts"]
    if e["scope_complete"] != derive_scope_complete(n_docs, n_q, e["query_set_is_ufh07"]):
        p.append("extra.scope_complete does not re-derive (>=200 chunks and the 45 behavioural questions)")
    kind = str(e.get("query_set_kind"))
    named = kind.startswith("file:") and any(t in kind.lower() for t in ("probe45", "ufh07"))
    if e["query_set_is_ufh07"] and not named:
        p.append("extra.query_set_is_ufh07 is claimed but the query set is not the named probe45/ufh07 file")
    return p


def row_problems(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA, optional_text=("protocol_id",))
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    if row.get("protocol_id") != "":
        p.append("protocol_id must be empty: no codified protocol; the gate is a predeclared plan")
    metric = row.get("metric")
    if metric not in METRICS:
        return p + [f"metric must be one of {sorted(METRICS)}"] + ns.self_hash_problems(row)
    if row.get("metric_direction") != METRICS[metric][0]:
        p.append(f"metric_direction for {metric} must be {METRICS[metric][0]}")
    if row.get("unit") != METRICS[metric][1]:
        p.append("unit does not match the metric")
    if row.get("category") != "CANDIDATE":
        p.append("a gated lane is a CANDIDATE against the reference lane")
    if p:
        return p + ns.self_hash_problems(row)
    p += _lane_problems(e)
    p += _scope_problems(e)
    n_d, n_q = e.get("n_docs"), e.get("n_queries")
    if not (_cos_list(e.get("docs_cos"), n_d) and _cos_list(e.get("queries_cos"), n_q)):
        return p + ["extra.docs_cos / extra.queries_cos must be the recorded finite per-item cosines, one per item"] \
            + ns.self_hash_problems(row)
    if row.get("reps") != n_d + n_q:
        p.append("reps must be the number of items (documents + queries)")
    d = derive_stats(e["docs_cos"], e["queries_cos"])
    nf_d, nf_q = e.get("nonfinite_docs"), e.get("nonfinite_queries")
    if not (ns.nonneg_int(nf_d) and ns.nonneg_int(nf_q) and nf_d <= n_d and nf_q <= n_q):
        return p + ["extra.nonfinite_docs / extra.nonfinite_queries must be counts within the item counts"] \
            + ns.self_hash_problems(row)
    nonfinite = nf_d + nf_q
    if nonfinite and d["cos_min"] > -1.0 + 2e-6:
        p.append("non-finite vectors are recorded but no per-item cosine carries the -1.0 floor")
    if not all(ns.finite(e.get(k)) for k in ("cos_min", "cos_mean")):
        p.append("extra.cos_min and extra.cos_mean must be recorded")
    elif not (_close(e["cos_min"], d["cos_min"]) and _close(e["cos_mean"], d["cos_mean"])
              and e.get("nonfinite_vectors") == nonfinite):
        p.append("extra.cos_min / cos_mean / nonfinite_vectors do not re-derive from the per-item values")
    want = {M_MIN: d["cos_min"], M_MEAN: d["cos_mean"], M_NONFINITE: nonfinite}[metric]
    if not ns.finite(row.get("value")) or not _close(row["value"], want):
        p.append(f"value must equal the value re-derived from the per-item results ({metric})")
    thr = e.get("threshold")
    if not ns.finite(thr) or e.get("lane") not in PREDECLARED_THRESHOLDS or not _close(thr, PREDECLARED_THRESHOLDS[e["lane"]]):
        p.append("extra.threshold must equal the gate's predeclared threshold for the lane")
    elif e.get("gate_verdict") != derive_verdict(nonfinite, d["cos_min"], thr):
        p.append("extra.gate_verdict does not re-derive (PASS iff non-finite == 0 and min >= threshold)")
    if e.get("rule") != RULE:
        p.append("extra.rule must be the gate's predeclared rule")
    # retrospective guard: the record must have been captured at the run, not replayed later
    t_emit, t_file = _parse_utc(row.get("emitted_at")), _parse_utc(e.get("parity_mtime_utc"))
    if t_file is None:
        p.append("extra.parity_mtime_utc must be recorded")
    elif t_emit is not None and (t_emit - t_file).total_seconds() > MAX_CAPTURE_LAG_S:
        p.append("row was emitted long after parity.json was written: retrospective results are never back-filled")
    if not p:
        p += ns.check_identity(row, {"run_id": row["run_id"], "lane": e["lane"], "metric": metric,
                                     "results": row["results_sha256"]}, "replembparity")
    return p + ns.self_hash_problems(row)


validate_row = row_problems


def _parse_utc(value: Any) -> datetime | None:
    if not ns.utc_timestamp(value):
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, row_problems)


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("embedder parity native row must retain the producer row")
    row = native["row"]
    problems = row_problems(row)
    if problems:
        raise ProjectionError("embedder parity row is not a producer-authored capture: " + "; ".join(problems))
    e = row["extra"]
    locator = f"replembparity:{row['run_id']}:{e['lane']}:{row['metric']}:{row['results_path']}"
    tup = ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator, sidecar_path=native.get("sidecar_path", ""))
    knobs: dict[str, Any] = {"lane": e["lane"], "arm_id": e["arm_id"], "threads": e["threads"],
                             "flash_attn_resolved": e["flash_attn_resolved"], "scope_complete": e["scope_complete"]}
    applicability: dict[str, Any] = {
        "scope_basis": "native", "run_id": row["run_id"], "quant": e["index_identity"]["dtype"],
        "knob_family": "embedder_vector_parity", "knobs": knobs,
    }
    if e["lane_kind"] == "gguf":
        applicability["kernel"] = {"binary_sha256": e["binary_sha256"]}
    return dataclasses.replace(tup, observation={"outcome_native": str(e["gate_verdict"])}, applicability=applicability)


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


# --------------------------------------------------------------------------------------------- writer


def _read_json(path: Path, what: str) -> dict:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise CaptureError(f"{what} unreadable: {exc}") from exc
    if not isinstance(data, dict):
        raise CaptureError(f"{what} must be a JSON object")
    return data


def _load_meta(runtime_meta: Mapping[str, Any] | str | Path) -> Mapping[str, Any]:
    if isinstance(runtime_meta, Mapping):
        return runtime_meta
    return _read_json(Path(runtime_meta), "runtime meta")


def _lane_meta(meta: Mapping[str, Any], lane: str) -> dict[str, Any]:
    m = meta.get(lane)
    if not isinstance(m, dict):
        raise CaptureError(f"runtime meta has no entry for lane {lane!r}: runtime identity is never defaulted")
    kind = _lane_kind(lane)
    out: dict[str, Any] = {"runtime": m.get("runtime"), "argv": m.get("argv"), "versions": m.get("versions")}
    if kind == "gguf":
        out.update(binary_sha256=m.get("binary_sha256"), flash_attn_requested=m.get("flash_attn_requested"),
                   flash_attn_resolved=m.get("flash_attn_resolved"))
    else:
        out.update(binary_sha256=None, flash_attn_requested="n/a", flash_attn_resolved="n/a")
    probe = dict(out, lane_kind=kind)
    bad = _runtime_problems(probe) if lane != REFERENCE_LANE else []
    if lane == REFERENCE_LANE:
        if not ns.text(out["runtime"]) or not _argv_ok(out["argv"]) or not _versions_ok(out["versions"], ST_VERSION_KEYS):
            bad = ["runtime, argv and versions (torch/transformers/sentence_transformers) are required"]
    if bad:
        raise CaptureError(f"runtime meta for lane {lane!r} incomplete: " + "; ".join(bad))
    return out


def _check_items(parity_items: Mapping[str, Any], items_path: Path) -> str:
    """items.json must be the item set parity.json was computed over; returns the file digest."""
    full = _read_json(items_path, "items.json")
    for k in ("files", "chunks", "queries", "query_set_kind", "n_chunks", "query_set_is_ufh07"):
        if full.get(k) != parity_items.get(k):
            raise CaptureError(f"items.json disagrees with parity.json items on {k!r}")
    texts = full.get("doc_texts")
    if not isinstance(texts, list) or len(texts) != len(full["chunks"]):
        raise CaptureError("items.json doc_texts must match the chunk list")
    for i, (t, c) in enumerate(zip(texts, full["chunks"])):
        if hashlib.sha256(str(t).encode()).hexdigest() != c.get("text_sha256"):
            raise CaptureError(f"items.json doc_texts[{i}] does not match its recorded text_sha256")
    return ns.file_sha256(items_path)


def _lane_stat(rec: Mapping[str, Any], part: str, n: int) -> tuple[list[float], int]:
    s = rec.get(part)
    if not isinstance(s, dict):
        raise CaptureError(f"lane record has no {part!r} stats")
    cos = s.get("per_item_cos")
    if not _cos_list(cos, n) or s.get("n") != n:
        raise CaptureError(f"{part}.per_item_cos must be {n} finite per-item cosines")
    nf = s.get("nonfinite_vectors")
    if not ns.nonneg_int(nf):
        raise CaptureError(f"{part}.nonfinite_vectors must be a count")
    recorded = {"cos_min": min(cos), "cos_mean": math.fsum(cos) / len(cos)}
    for k, v in recorded.items():
        if not ns.finite(s.get(k)) or abs(s[k] - v) > RECORDED_TOL:
            raise CaptureError(f"{part}.{k} does not re-derive from the per-item cosines")
    return [float(x) for x in cos], nf


def write_belief_measurements(out_dir: str | Path, *, run_id: str, producer: str, parity_path: str | Path,
                              items_path: str | Path, runtime_meta: Mapping[str, Any] | str | Path,
                              emitted_at: str | None = None) -> Path:
    raw, items_file = Path(parity_path), Path(items_path)
    par = _read_json(raw, "parity.json")
    lanes, items_meta = par.get("lanes"), par.get("items")
    if not isinstance(lanes, dict) or not isinstance(items_meta, dict) or not isinstance(par.get("reference"), dict):
        raise CaptureError("parity.json must carry reference, lanes and items")
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    t_emit = _parse_utc(when)
    mtime = datetime.fromtimestamp(raw.stat().st_mtime, timezone.utc)
    if t_emit is None or (t_emit - mtime).total_seconds() > MAX_CAPTURE_LAG_S:
        raise CaptureError("parity.json is older than the capture window: retrospective results are never back-filled")
    if (mtime - t_emit).total_seconds() > 60:
        raise CaptureError("parity.json is newer than the emit time")
    mtime_s = mtime.strftime("%Y-%m-%dT%H:%M:%SZ")
    digest = ns.file_sha256(raw)
    items_sha = _check_items(items_meta, items_file)
    parts = input_set_parts(items_meta)
    set_digest = input_set_digest(parts)
    if not isinstance(par.get("scope_complete"), bool) or not ns.text(items_meta.get("query_set_kind")):
        raise CaptureError("parity.json must record scope_complete and the query_set_kind")
    n_chunks, n_queries = items_meta.get("n_chunks"), len(items_meta["queries"])
    if n_chunks != len(items_meta["chunks"]):
        raise CaptureError("items n_chunks disagrees with the chunk list")
    is_ufh07 = items_meta.get("query_set_is_ufh07")
    if not isinstance(is_ufh07, bool) or par["scope_complete"] != derive_scope_complete(n_chunks, n_queries, is_ufh07):
        raise CaptureError("scope_complete does not re-derive from the recorded item counts")
    gate = par.get("gate") or {}
    if gate.get("reference_lane") != REFERENCE_LANE or gate.get("rule") != RULE:
        raise CaptureError("parity.json gate block is not the predeclared rule / reference lane")
    meta = _load_meta(runtime_meta)

    ref_rec = (par["reference"] or {}).get("lane")
    if not isinstance(ref_rec, dict) or not ns.text(ref_rec.get("arm_id")) or not _identity_ok(ref_rec.get("index_identity")):
        raise CaptureError("reference lane record must carry arm_id and a well-formed index_identity")
    if par["reference"].get("nonfinite_vectors") != 0:
        raise CaptureError("the reference lane has non-finite vectors: the gate is void")
    ref_meta = _lane_meta(meta, REFERENCE_LANE)
    reference = {"lane": REFERENCE_LANE, "arm_id": ref_rec["arm_id"], "index_identity": ref_rec["index_identity"],
                 "runtime": ref_meta["runtime"], "argv": ref_meta["argv"], "versions": ref_meta["versions"],
                 "nonfinite_vectors": 0}

    rows: list[dict] = []
    for lane, rec in sorted(lanes.items()):
        thr = rec.get("threshold")
        if thr is None:
            continue  # not a gate subject (e.g. the text-only equivalence lane)
        if lane not in PREDECLARED_THRESHOLDS or not ns.finite(thr) or not _close(thr, PREDECLARED_THRESHOLDS[lane]):
            raise CaptureError(f"lane {lane!r} threshold {thr!r} is not the predeclared one")
        lm = _lane_meta(meta, lane)
        lrec = rec.get("lane")
        if not isinstance(lrec, dict) or not ns.text(lrec.get("arm_id")) or not _identity_ok(lrec.get("index_identity")) \
                or lrec.get("lane") != lane or not isinstance(lrec.get("threads"), int):
            raise CaptureError(f"lane {lane!r} record must carry lane, arm_id, threads and a well-formed index_identity")
        docs, nf_d = _lane_stat(rec, "docs", n_chunks)
        qs, nf_q = _lane_stat(rec, "queries", n_queries)
        d = derive_stats(docs, qs)
        nonfinite = nf_d + nf_q
        if rec.get("nonfinite_vectors_total") != nonfinite or abs(rec.get("cos_min_all_items", math.nan) - d["cos_min"]) > RECORDED_TOL:
            raise CaptureError(f"lane {lane!r}: recorded totals do not re-derive from the per-item results")
        verdict = derive_verdict(nonfinite, d["cos_min"], thr)
        if rec.get("verdict") != verdict:
            raise CaptureError(f"lane {lane!r}: recorded verdict {rec.get('verdict')!r} does not re-derive ({verdict})")
        scope = "complete" if par["scope_complete"] else "PARTIAL"
        extra_common = {
            "lane": lane, "lane_kind": _lane_kind(lane), "arm_id": lrec["arm_id"], "index_identity": lrec["index_identity"],
            "threads": lrec["threads"], **lm, "reference": reference,
            "threshold": thr, "gate_verdict": verdict, "rule": RULE,
            "input_set": parts, "input_set_digest": set_digest, "items_sha256": items_sha,
            "n_docs": n_chunks, "n_queries": n_queries, "query_set_kind": items_meta["query_set_kind"],
            "query_set_is_ufh07": is_ufh07, "scope_complete": par["scope_complete"], "scope_note": par.get("scope_note"),
            "docs_cos": docs, "queries_cos": qs, "nonfinite_docs": nf_d, "nonfinite_queries": nf_q,
            "nonfinite_vectors": nonfinite, "cos_min": d["cos_min"], "cos_mean": d["cos_mean"],
            "parity_mtime_utc": mtime_s,
        }
        values = {M_MIN: d["cos_min"], M_MEAN: d["cos_mean"], M_NONFINITE: nonfinite}
        for metric, value in values.items():
            direction, unit = METRICS[metric]
            row = {
                "schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer, "emitted_at": when, "date": when,
                "metric": metric, "value": value, "unit": unit, "metric_direction": direction, "category": "CANDIDATE",
                "claim": (f"EmbeddingGemma-2 vector parity, lane {lane} vs {REFERENCE_LANE}: {SHORT[metric]} {value:.6f} over {n_chunks} chunks + {n_queries} queries "
                          f"({items_meta['query_set_kind']}); gate {verdict} at threshold {thr}; scope {scope}; "
                          f"vector parity only, no recall or speed claim"),
                "protocol_id": "", "reps": n_chunks + n_queries,
                "reps_basis": "items (chunk documents + queries), one encode pass each",
                "results_path": str(raw), "results_sha256": digest, "extra": dict(extra_common),
            }
            row["measurement_id"] = "replembparity_" + ns.content_hash(
                {"run_id": run_id, "lane": lane, "metric": metric, "results": digest})[:24]
            ns.seal(row)
            bad = row_problems(row)
            if bad:
                raise CaptureError("refusing to emit an invalid row: " + "; ".join(bad))
            rows.append(row)
    if not rows:
        raise CaptureError("parity.json carries no gated lane: nothing to project")
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="write the embedder-parity belief sidecar from a gate run's parity.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    w.add_argument("--parity", required=True)
    w.add_argument("--items", required=True)
    w.add_argument("--runtime-meta", required=True)
    w.add_argument("--out-dir", required=True)
    w.add_argument("--run-id", required=True)
    w.add_argument("--producer", default="repl_emb_parity_gate.py")
    a = ap.parse_args(argv)
    try:
        path = write_belief_measurements(a.out_dir, run_id=a.run_id, producer=a.producer, parity_path=a.parity,
                                         items_path=a.items, runtime_meta=a.runtime_meta)
    except CaptureError as exc:
        print(f"belief sidecar NOT written: {exc}", file=sys.stderr)
        return 3
    print(json.dumps({"sidecar": str(path), "rows": len(native_rows(path))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
