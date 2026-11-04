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
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402

CAPTURE_SCHEMA = "epyc.vidya.akx_lb32_capture.v1"
CONTROL_SCHEMA = "epyc.vidya.akx_lb32_capture.v2"
CONTROL_VERSION = "akx-lb32-same-source-control-v2"
IDENTITY_KEYS = ("version", "source", "research", "run", "pair", "order", "G", "M", "threads",
                 "reported_threads", "grant", "champion")
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


def _bound(ref: Any) -> Path:
    if not isinstance(ref, dict) or not ns.text(ref.get("path")) or not ns.SHA256.fullmatch(str(ref.get("sha256", ""))):
        raise ValueError("malformed file reference")
    path = Path(ref["path"])
    if not path.is_absolute() or not path.is_file() or ns.file_sha256(path) != ref["sha256"]:
        raise ValueError("missing or changed evidence: " + str(path))
    return path.resolve()


def _json(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return value


def _manifest(path: Path) -> dict:
    fields = {}
    for line in path.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and key in IDENTITY_KEYS:
            if key in fields:
                raise ValueError("duplicate manifest identity")
            fields[key] = value
    if set(fields) != set(IDENTITY_KEYS) or not all(ns.text(v) for v in fields.values()):
        raise ValueError("incomplete manifest identity")
    if (fields["version"] != CONTROL_VERSION or fields["source"] != "c72ec82f5417bb2937310326120f149b665e8400"
            or fields["order"] not in ("GM", "MG") or fields["threads"] != "48" or fields["reported_threads"] != "96"):
        raise ValueError("unexpected control identity")
    return fields


def _native_verdict(value: dict) -> str:
    part = value["gating"]
    cells = part["cells"]
    if set(cells) != {str(n) for n in NS_ALL}:
        raise ValueError("native verdict lacks complete cells")
    for n in (2, 3, 4, 5):
        cell = cells[str(n)]
        if (not _share(cell["F_fa_wall_share"]) or not ns.finite(cell["S_depth_share"])
                or not ns.nonneg_int(cell["reps_used_d64k"]) or cell["reps_used_d64k"] < 8
                or not ns.finite(cell["overhead_d64k"]) or abs(cell["overhead_d64k"]) > .05
                or not ns.finite(cell["coverage_defect_d64k"]) or not 0 <= cell["coverage_defect_d64k"] <= .10):
            raise ValueError("native gating cell is invalid")
    fm = max(cells[str(n)]["F_fa_wall_share"] for n in (2, 3, 4, 5))
    sm = max(cells[str(n)]["S_depth_share"] for n in (2, 3, 4, 5))
    want = "LANE_LARGE" if fm >= THRESH else ("LANE_SMALL" if sm < THRESH else "SPLIT_UNRESOLVED")
    if (part["max_F_N2to5"] != fm or part["max_S_N2to5"] != sm
            or part["verdict"] != want or value["verdict"] != want or part.get("why")):
        raise ValueError("native verdict does not re-derive")
    return want


def _control_problems(row: dict) -> list[str]:
    """v2 requires retained provenance; v1's absent-attestation behavior is unchanged."""
    try:
        e = row["extra"]
        c = e["control_instrument"]
        identity = c["identity"]
        start_path, manifest_path, record_path, pair_path = (_bound(c[k]) for k in
                                                           ("start", "manifest", "run_record", "pair_result"))
        root = manifest_path.parent
        if (start_path != root / "CONTROL_CAPTURE_START.json" or manifest_path != root / "INSTRUMENT.txt"
                or record_path != root / "RUN_RECORD.json" or Path(row["results_path"]).resolve() != root / "VERDICT.json"):
            raise ValueError("control files do not belong to this run")
        if identity != _manifest(manifest_path) or identity["run"] != row["run_id"]:
            raise ValueError("row/manifest identity mismatch")
        start = _json(start_path)
        if (start["schema"] != CONTROL_SCHEMA or start["instrument"] != identity
                or c["baseline_kind"] != "champion_store_profiler_off"
                or start["baseline_kind"] != c["baseline_kind"]
                or not ns.text(c["baseline_claim"]) or c["baseline_claim"] != start["baseline_claim"]):
            raise ValueError("start/control identity mismatch")
        for refs in (start["evidence"], c["evidence"]):
            if not isinstance(refs, list) or not refs:
                raise ValueError("missing control evidence")
            paths = [_bound(item) for item in refs]
            if len(set(paths)) != len(paths):
                raise ValueError("duplicate evidence")
        if any(not _bound(item).is_relative_to(root / "out") for item in c["evidence"]):
            raise ValueError("native evidence escapes run output")
        start_refs = {str(_bound(item)): item["sha256"] for item in start["evidence"]}
        if start_refs.get(str(manifest_path)) != c["manifest"]["sha256"]:
            raise ValueError("start does not bind manifest")
        pre = _bound({"path": e["predeclaration_path"], "sha256": e["predeclaration_sha256"]})
        if start_refs.get(str(pre)) != e["predeclaration_sha256"]:
            raise ValueError("start does not bind predeclaration")
        rules = pre.parent
        required = [manifest_path, pre, rules / "AMENDMENT-control-v2.md", rules / "AMENDMENT-control-v2.sha256",
                    rules / "PAIR-DECLARATION.sh", rules / "AMENDMENT-affinity-v3.md",
                    rules / "REBASED-INSTRUMENTATION.patch", rules / "pair-state/GRANT.txt"]
        required += [root / "out" / ("B0." + arm + suffix) for arm in ("G", "M")
                     for suffix in (".cache-options.txt", ".compiler-identity.txt", ".compiler-executables.txt", ".sha256")]
        if set(start_refs) != {str(path.resolve()) for path in required} or pair_path != rules / "PAIR_VERDICT.json":
            raise ValueError("start evidence or pair location differs from declared instrument")
        pair = _json(pair_path)
        if (pair["schema"] != "epyc.akx_lb32.pair_verdict.v1" or pair["pair_id"] != identity["pair"]
                or pair["grant"] != identity["grant"] or pair["one_fixed_pair"] is not True
                or pair["no_averaging"] is not True or pair["pair_verdict"] not in VERDICTS
                or pair["GM"] != pair["MG"] or pair["GM"] != pair["pair_verdict"]
                or not isinstance(pair["runs"], list) or len(pair["runs"]) != 2):
            raise ValueError("invalid fixed pair")
        paths = [_bound(item) for item in pair["runs"]]
        if len(set(paths)) != 2:
            raise ValueError("pair duplicates a run")
        current = _bound({"path": row["results_path"], "sha256": row["results_sha256"]})
        index = 0 if identity["order"] == "GM" else 1
        if paths[index] != current or pair["runs"][index]["sha256"] != row["results_sha256"]:
            raise ValueError("current run is not its exact pair member")
        run_ids = set()
        for order, path in zip(("GM", "MG"), paths):
            if path.name != "VERDICT.json":
                raise ValueError("pair member is not a native verdict")
            fields = _manifest(path.parent / "INSTRUMENT.txt")
            for key in ("version", "source", "research", "pair", "grant", "champion", "G", "threads", "reported_threads"):
                if fields[key] != identity[key]:
                    raise ValueError("pair crosses instrument identity")
            if fields["order"] != order:
                raise ValueError("pair order mismatch")
            run_ids.add(fields["run"])
            record = _json(path.parent / "RUN_RECORD.json")
            expected = dict(schema="epyc.akx_lb32.run_record.v2", instrument=CONTROL_VERSION,
                            run_id=fields["run"], pair_id=fields["pair"], arm_order=order,
                            manifest_sha256=ns.file_sha256(path.parent / "INSTRUMENT.txt"),
                            source_sha=fields["source"], measurement_sha=fields["source"],
                            research_sha=fields["research"], control_build=fields["G"], measurement_build=fields["M"],
                            verdict=pair["pair_verdict"])
            if any(record.get(k) != v for k, v in expected.items()):
                raise ValueError("run record identity mismatch")
            if _native_verdict(_json(path)) != pair["pair_verdict"]:
                raise ValueError("pair native verdict mismatch")
        if len(run_ids) != 2:
            raise ValueError("pair run ids are not distinct")
        native = _json(current)
        part = native["gating"] if e["threads"] == 48 else native["reported_t96"]
        if e["kind"] == "cell":
            source = part["cells"][str(e["n_prompt"])]
            keys = ("F_fa_wall_share", "S_depth_share", "S_M_depth_share", "overhead_d64k", "overhead_d512",
                    "coverage_defect_d64k", "reps_used_d64k", "t_ms", "F_cpu_sample_share_G",
                    "class_share_d64k", "class_depth_delta_share")
            if part["verdict"] not in VERDICTS or e["run_verdict"] != part["verdict"]:
                raise ValueError("row/native verdict mismatch")
        else:
            source = part
            keys = ("verdict", "seed_class", "max_F_N2to5", "max_S_N2to5", "mean_depth_delta_share_N2to5", "thresholds")
        if any(e.get(k) != source.get(k) for k in keys):
            raise ValueError("row differs from native results")
        return []
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError) as exc:
        return ["invalid v2 control provenance: " + str(exc)]


def row_problems(row: Any) -> list[str]:
    schema = CONTROL_SCHEMA if isinstance(row, dict) and row.get("schema") == CONTROL_SCHEMA else CAPTURE_SCHEMA
    p = ns.common_problems(row, schema=schema, optional_text=("protocol_id",))
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
    if schema == CONTROL_SCHEMA and not p:
        p += _control_problems(row)
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

