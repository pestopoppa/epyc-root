"""VB-AKX-LB32-WRITE: AKX-ALL-LB3.2 attribution run (Q38FN, CPU long-context lane seed) as measurement OBSERVATIONS.

Source: ``akx_lb32.beliefs.jsonl``, written beside ``VERDICT.json`` by research
``scripts/benchmark/akx_lb3_attribution/verdict.py --predeclaration`` (launcher
``/mnt/raid0/llm/tmp/f8-launchers-20261024/akx-lb3-2/``). Two row kinds:

* ``cell``    one per (threads, N): ``value`` = F(N), the FLASH_ATTN_EXT node-wall share of the timed pp-N step at depth
  65536. It is the critical path through the graph barrier, measured on the GGML_CPU_PROF measurement build (M arm).
  S(N), the measurement-build overhead against the champion store image (G arm), the coverage defect and the class
  table ride in ``extra``, verbatim.
* ``verdict`` one per run: ``value`` = max F(N) for N=2..5; the predeclared verdict, seed class and max S ride in
  ``extra``.

Doctrine: PROJECTION ONLY (``claim_tuple.grade()`` decides; no ladder here).

* The reader re-derives what it can and refuses on any difference. ``value`` must equal the row's own F. A verdict
  row's verdict must follow from its own max F / max S and the 10% thresholds. ``measurement_id`` must re-derive from
  run, kind, threads, N and the VERDICT digest.
* ``protocol_id`` is always empty: a predeclared rule is not a codified protocol, and there is one run. The ladder
  therefore caps the tuple.
* An INVALID verdict never yields a row: the writer emits nothing, and this reader refuses a row carrying one.
* Two attestations. ``results_sha256`` covers ``VERDICT.json`` and is re-hashed on read. ``extra.predeclaration_sha256``
  covers the frozen rule; when the rule file is present it must still hash to that value, or the row is void.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402

CAPTURE_SCHEMA = "epyc.vidya.akx_lb32_capture.v1"
SIDECAR_NAME = "akx_lb32.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.akx_lb32/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "akx-lb32-attribution"
METRIC_CELL = "akx_lb32_fa_wall_share_d65536"
METRIC_VERDICT = "akx_lb32_max_fa_wall_share_n2to5_d65536"
VERDICTS = ("LANE_LARGE", "LANE_SMALL", "SPLIT_UNRESOLVED")
NS_ALL = (1, 2, 3, 4, 5, 8)
THRESH = 0.10


def _share(v: Any) -> bool:
    return ns.finite(v) and 0.0 <= v <= 1.5      # a share; >1 tolerated only as a measured overshoot, never negative


def row_problems(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA, optional_text=("protocol_id",))
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    if row.get("protocol_id") != "":
        p.append("protocol_id must be empty: a predeclared one-run rule is an OBSERVATION")
    if not ns.SHA256.match(str(e.get("predeclaration_sha256", ""))) or not ns.text(e.get("predeclaration_path")):
        p.append("extra.predeclaration_path/sha256 must name the frozen rule")
    if not ns.nonneg_int(row.get("reps")):
        p.append("reps must be a non-negative integer")
    kind, threads = e.get("kind"), e.get("threads")
    if threads not in (48, 96):
        p.append("extra.threads must be 48 or 96")
    if kind == "cell":
        if row.get("metric") != METRIC_CELL:
            p.append(f"cell metric must be {METRIC_CELL}")
        if e.get("n_prompt") not in NS_ALL:
            p.append(f"extra.n_prompt must be one of {list(NS_ALL)}")
        if not _share(e.get("F_fa_wall_share")):
            p.append("extra.F_fa_wall_share must be a finite share")
        elif ns.finite(row.get("value")) and abs(row["value"] - e["F_fa_wall_share"]) > 1e-12:
            p.append("value must equal extra.F_fa_wall_share")
        if row.get("reps") != e.get("reps_used_d64k"):
            p.append("reps must equal extra.reps_used_d64k")
        if e.get("run_verdict") not in VERDICTS:
            p.append("extra.run_verdict must be a non-INVALID predeclared verdict")
        if e.get("gating") is not (threads == 48):
            p.append("extra.gating must be true exactly for t48")
        n_id = e.get("n_prompt")
    elif kind == "verdict":
        if row.get("metric") != METRIC_VERDICT:
            p.append(f"verdict metric must be {METRIC_VERDICT}")
        v, Fm, Sm = e.get("verdict"), e.get("max_F_N2to5"), e.get("max_S_N2to5")
        if v not in VERDICTS:
            p.append("extra.verdict must be LANE_LARGE / LANE_SMALL / SPLIT_UNRESOLVED (INVALID never projects)")
        if not (_share(Fm) and ns.finite(Sm)):
            p.append("extra.max_F_N2to5 / max_S_N2to5 must be finite")
        else:
            if ns.finite(row.get("value")) and abs(row["value"] - Fm) > 1e-12:
                p.append("value must equal extra.max_F_N2to5")
            want = "LANE_LARGE" if Fm >= THRESH else ("LANE_SMALL" if Sm < THRESH else "SPLIT_UNRESOLVED")
            if v in VERDICTS and v != want:
                p.append(f"verdict {v} does not follow from max F {Fm} / max S {Sm} (rule gives {want})")
        if v == "SPLIT_UNRESOLVED" and not ns.text(e.get("seed_class")):
            p.append("SPLIT_UNRESOLVED must name its seed class")
        if threads != 48 or e.get("gating") is not True:
            p.append("the verdict row is the t48 gating verdict")
        n_id = None
    else:
        p.append("extra.kind must be cell or verdict")
        n_id = None
    if not p:
        p += ns.check_identity(row, {"run_id": row["run_id"], "kind": kind, "threads": threads, "n_prompt": n_id,
                                     "results": row["results_sha256"]}, "akxlb32")
        pre = Path(e["predeclaration_path"])
        if pre.is_file() and ns.file_sha256(pre) != e["predeclaration_sha256"]:
            p.append("the frozen predeclaration no longer hashes to extra.predeclaration_sha256 (rule edited)")
    return p + ns.self_hash_problems(row)


validate_row = row_problems


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, row_problems)


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("AKX-LB3.2 native row must retain the producer row")
    row = native["row"]
    problems = row_problems(row)
    if problems:
        raise ProjectionError("AKX-LB3.2 row is not a producer-authored capture: " + "; ".join(problems))
    e = row["extra"]
    where = f"t{e['threads']}:" + (f"pp{e['n_prompt']}@d65536" if e["kind"] == "cell" else "verdict")
    locator = f"akxlb32:{row['run_id']}:{where}:{row['results_path']}"
    tup = ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator, sidecar_path=native.get("sidecar_path", ""))
    knobs = {"model": "Qwen3.8-Flash-Next UD-IQ4_XS", "kv": "f16", "GGML_FA_SPLIT_KV": "0", "threads": e["threads"],
             "n_depth": 65536}
    if e["kind"] == "cell":
        knobs["n_prompt"] = e["n_prompt"]
        outcome = f"F={e['F_fa_wall_share']:.4f} S={e.get('S_depth_share')} run={e['run_verdict']}"
    else:
        outcome = f"{e['verdict']} seed={e.get('seed_class')}"
    return dataclasses.replace(
        tup,
        applicability={"scope_basis": "native", "backend": "cpu", "knob_family": "akx_cpu_longctx_attention",
                       "knobs": knobs, "varied": ["n_prompt", "n_depth"]},
        observation={"outcome_native": outcome[:120]})


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames

