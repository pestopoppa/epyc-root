"""Strict reader for C6 Q4 component microbench native run bundles.

The producer records raw CPU component timings for exact 27B Q4_K test cases and a
synthetic Q4_K reference at DS41/MXFP4 shapes. This adapter rechecks the run seals,
inputs, stores, and native summaries before projecting each individual latency as an
OBSERVATION through the shared ClaimTuple grade. It does not compare arms or create a
keep/serving conclusion. Protocol is intentionally empty: generated-input byte identity
and independent co-tenancy are explicitly UNKNOWN in the native PRE-RUN records.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import re
import sqlite3
import statistics
import sys
from pathlib import Path, PurePosixPath
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

ADAPTER_ID = "vidya.adapters.c6_q4_microbench/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "c6.35186.q4_two_cohort_component_result.v1"
RUN_SCHEMA = "c6.35186.q4_two_cohort_prerun.v1"
DEFAULT_RUNS = Path("/mnt/raid0/llm/tmp/c6-35186-q4-microbench-r2-20261031/runs")
CANONICAL_RUN_ID = "20261031T024056.425184Z-2158835"
FILLER_ID = "refactor-c6-35186-q4-two-cohort-cpu-r2-20261031"
OUTER_CAPTURE_DIR = Path(__file__).resolve().parents[3] / "artifacts/compute/c6-q4-microbench-r2-20261031/outer-custody"
OUTER_CAPTURE_MANIFEST_SHA256 = "e247342ce786b5fabbf77ceb5834295dc9f9fc2dd1fb78147d604973c2a72b7b"
OUTER_CAPTURE_SUMS_SHA256 = "cac55d7329c1fd157272a5f061f474844cb1a061b67a2125bc71e89a288d779b"
OUTER_CAPTURE_EXPECTED = {
    "keeper-ready-armed.json": ("/mnt/raid0/llm/tmp/compute-flags/ready/armed/refactor-c6-35186-q4-two-cohort-cpu-r2-20261031.json", "ff26a324094d6937c1a0e509518d3f45fe128cdf99d257eca231a765ee68f670"),
    "keeper-launcher.out": ("/mnt/raid0/llm/tmp/compute-flags/ready/refactor-c6-35186-q4-two-cohort-cpu-r2-20261031.launcher.out", "1a5b0325287b6cd8a26ef443366789e1c8c810f3bd2ed19b4238390aa2cba7b5"),
    "complete-marker.txt": ("/mnt/raid0/llm/tmp/compute-flags/grants/refactor-c6-35186-q4-two-cohort-cpu-r2-20261031.complete", "2b0200190296496ea40572dc60e42d0f929bb067ddf5f9ef255f137f0bcdaf86"),
}
MAX_JSON = 32 << 20
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_EXPECTED = (("27b", "candidate", 9), ("27b", "control", 9),
             ("ds41", "candidate", 2), ("ds41", "control", 2))
_IMAGE_SOURCE = {"candidate": ("729599d69871181d67af715a4c2f9162d5153a2e", "51b0a4fda906ffd3d029fd21bf41204675f08167"),
                 "control": ("3dbca8f4f407e21f11a2d04dcb6529ef40af9e62", "133f41328306c0c6fb43b85dda472a2858567db4")}


def _fail(msg: str):
    raise ProjectionError(f"c6-q4 microbench refused: {msg}")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
    except OSError as exc:
        _fail(f"cannot hash {path}: {exc}")
    return h.hexdigest()


def _read(path: Path, limit: int = MAX_JSON) -> bytes:
    try:
        st = path.lstat()
        if not path.is_file() or path.is_symlink() or st.st_size > limit:
            _fail(f"unsafe or oversized input {path}")
        return path.read_bytes()
    except OSError as exc:
        _fail(f"cannot read {path}: {exc}")


def _json(path: Path) -> dict:
    try:
        value = json.loads(_read(path))
    except (ValueError, UnicodeDecodeError) as exc:
        _fail(f"invalid JSON {path}: {exc}")
    if not isinstance(value, dict):
        _fail(f"expected JSON object in {path}")
    return value


def _seal(base: Path, seal_path: Path, *, exact_files: set[str] | None = None) -> dict[str, str]:
    raw = _read(seal_path)
    found: dict[str, str] = {}
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        _fail(f"invalid seal text {seal_path}: {exc}")
    for line in lines:
        m = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not m:
            _fail(f"malformed seal entry in {seal_path}")
        digest, rel = m.groups()
        p = PurePosixPath(rel)
        if p.is_absolute() or ".." in p.parts or rel in found:
            _fail(f"unsafe/duplicate sealed path {rel!r}")
        file = base.joinpath(*p.parts)
        if file.is_symlink() or not file.is_file() or _sha(file) != digest:
            _fail(f"sealed file changed or missing: {file}")
        found[rel] = digest
    if exact_files is not None and set(found) != exact_files:
        _fail(f"seal coverage differs: missing={sorted(exact_files-set(found))}, extra={sorted(set(found)-exact_files)}")
    return found


def _verify_outer_capture(package: Path, pre: dict) -> None:
    """Verify immutable archived keeper evidence; never depend on scheduler live paths."""
    if pre.get("filler_id") != FILLER_ID:
        _fail("unexpected R2 filler identity")
    grant_text = pre.get("grant_text")
    grant_sha = pre.get("grant_sha256")
    if (not isinstance(grant_text, str) or not isinstance(grant_sha, str) or
            hashlib.sha256(grant_text.encode("utf-8")).hexdigest() != grant_sha):
        _fail("PRE-RUN grant text does not rehash to its recorded digest")
    manifest_path = OUTER_CAPTURE_DIR / "CUSTODY-MANIFEST.json"
    sums_path = OUTER_CAPTURE_DIR / "CUSTODY-SHA256SUMS"
    if (_sha(manifest_path) != OUTER_CAPTURE_MANIFEST_SHA256 or
            _sha(sums_path) != OUTER_CAPTURE_SUMS_SHA256):
        _fail("archived outer custody manifest or seal changed")
    sealed = _seal(OUTER_CAPTURE_DIR, sums_path,
                   exact_files={"CUSTODY-MANIFEST.json", *OUTER_CAPTURE_EXPECTED.keys()})
    if sealed.get("CUSTODY-MANIFEST.json") != OUTER_CAPTURE_MANIFEST_SHA256:
        _fail("outer custody checksum file does not bind its manifest")
    manifest = _json(manifest_path)
    if manifest.get("schema") != "c6.q4.r2.outer-custody-snapshot.v1":
        _fail("wrong outer custody snapshot schema")
    try:
        captured = dt.datetime.fromisoformat(manifest.get("captured_at", "").replace("Z", "+00:00"))
    except (TypeError, ValueError):
        _fail("outer custody capture time is invalid")
    if captured.date().isoformat() != "2026-10-31":
        _fail("outer custody snapshot is not from the captured R2 date")
    rows = manifest.get("items")
    expected_items = {name: {"archive_path": name, "original_path": original, "sha256": digest}
                      for name, (original, digest) in OUTER_CAPTURE_EXPECTED.items()}
    if not isinstance(rows, list) or {r.get("archive_path"): r for r in rows} != expected_items:
        _fail("outer custody snapshot source paths/hashes differ from the reviewed originals")
    if manifest.get("purpose") != "byte-preserving archive of the accepted keeper row, terminal launcher log, and completion marker for the already captured R2 run; not a measurement or reconstructed warrant":
        _fail("outer custody snapshot purpose was changed")
    armed = _json(OUTER_CAPTURE_DIR / "keeper-ready-armed.json")
    if (armed.get("id") != FILLER_ID or armed.get("status") != "READY" or
            armed.get("job") != str(package / "calendar.sh") or
            armed.get("job_sha256") != _sha(package / "calendar.sh") or
            armed.get("source_manifest_sha256") != _sha(package / "PACKAGE-SHA256SUMS") or
            armed.get("launcher_log_path") != OUTER_CAPTURE_EXPECTED["keeper-launcher.out"][0]):
        _fail("archived keeper row does not bind this source package and launcher log")
    log = _read(OUTER_CAPTURE_DIR / "keeper-launcher.out", limit=8 << 20).decode("utf-8", "replace")
    parts = dict(piece.split("=", 1) for piece in grant_text.strip().split() if "=" in piece)
    if parts.get("regions") != "48-71" or parts.get("start") != "2026-10-31T02:40Z" or parts.get("end") != "2026-10-31T04:40Z":
        _fail("recorded grant coordinates differ from the accepted R2 window")
    required_log = ("START regions=48-71 cpus=48-71 threads=24 gpu=0 end=2026-10-31T04:40Z",
                    f"RESOURCE_PASS id={FILLER_ID} scope=normal-grant", "C6_Q4_TWO_COHORT_COMPONENT_COMPLETE",
                    "job rc=0", "ended rc=0 reason=complete (grant deleted)",
                    f"ALL DONE: wrote /mnt/raid0/llm/tmp/compute-flags/grants/{FILLER_ID}.complete, row marked COMPLETE")
    if any(line not in log for line in required_log):
        _fail("archived keeper log lacks exact matching grant/resource/native completion evidence")
    marker = _read(OUTER_CAPTURE_DIR / "complete-marker.txt", limit=1024).decode("utf-8").strip()
    if marker != f"complete time=2026-10-31T02:41:35Z id={FILLER_ID}":
        _fail("archived completion marker identity/time mismatch")


def _verify_package(package: Path, pre: dict) -> None:
    sums = package / "PACKAGE-SHA256SUMS"
    if not sums.is_file():
        _fail("package source checksum manifest missing")
    sealed = _seal(package, sums)
    expected = {
        "Q4-GGUF-HEADER.bin": pre.get("q4_gguf_header_sha256"),
        "PUBLISHER-PROVENANCE.json": pre.get("q4_publisher_provenance_sha256"),
        "CASE-MANIFEST.json": pre.get("q4_case_manifest_sha256"),
        "ds41/src/ds41-1017-expert-shapes.json": pre.get("ds41_expert_shape_sha256"),
        "ds41/PREDECLARED.md": pre.get("ds41_w5d_predeclared_sha256"),
        "launch-q4.sh": pre.get("instruments", {}).get("q4_wrapper_sha256"),
        "validate_perf.py": pre.get("instruments", {}).get("q4_validator_sha256"),
        "ds41/launch_ds41.py": pre.get("instruments", {}).get("ds41_wrapper_sha256"),
        "ds41/src/mb_mmid.cpp": pre.get("instruments", {}).get("ds41_harness_source_sha256"),
        "ds41/bin/mb_mmid": pre.get("instruments", {}).get("ds41_candidate_binary_sha256"),
        "ds41/bin/mb_mmid-control": pre.get("instruments", {}).get("ds41_control_binary_sha256"),
    }
    for rel, digest in expected.items():
        if not isinstance(digest, str) or sealed.get(rel) != digest:
            _fail(f"PRE-RUN input pin mismatch: {rel}")
    case = _json(package / "CASE-MANIFEST.json")
    if not isinstance(case.get("cases"), list) or len(case["cases"]) != 9:
        _fail("exact 27B case manifest absent or changed")
    testfile = _read(package / "Q4-K-27B-EXACT.testfile", limit=2 << 20)
    test_names = [line.split()[-1] for line in testfile.decode().splitlines() if line.strip()]
    manifest_names = [item.get("name") for item in case["cases"] if isinstance(item, dict)]
    if manifest_names != test_names or len(manifest_names) != 9:
        _fail("case manifest and exact testfile identities differ")
    if _sha(package / "Q4-K-27B-EXACT.testfile") not in sealed.values():
        _fail("exact Q4 testfile is not in the sealed source package")


def _verify_image(pre: dict, image: str) -> dict:
    spec = pre.get("images", {}).get(image)
    if not isinstance(spec, dict):
        _fail(f"missing {image} image identity")
    source, tree = _IMAGE_SOURCE[image]
    if spec.get("source") != source or spec.get("tree") != tree:
        _fail(f"{image} image source/tree mismatch")
    root = Path(spec.get("root", ""))
    if not root.is_absolute() or not root.is_dir():
        _fail(f"{image} store path unavailable")
    ident_path, result_path, sums_path = root / "BUILD-IDENTITY.json", root / "build-result.json", root / "SHA256SUMS"
    if _sha(ident_path) != spec.get("identity_sha256") or _sha(result_path) != spec.get("build_result_sha256") or _sha(sums_path) != spec.get("sha256sums_sha256"):
        _fail(f"{image} store custody header changed")
    ident, result = _json(ident_path), _json(result_path)
    if ident.get("source_sha") != source or ident.get("source_tree") != tree or ident.get("kind") != "cpu":
        _fail(f"{image} BUILD-IDENTITY source mismatch")
    if result.get("status") != "COMPLETE_BUILD_ONLY" or result.get("source_sha") != source or result.get("sha256sums") != _sha(sums_path):
        _fail(f"{image} build result is not terminal COMPLETE_BUILD_ONLY")
    sealed = _seal(root, sums_path)
    if len(sealed) != spec.get("signed_artifact_count") or len(ident.get("targets", [])) != 29:
        _fail(f"{image} signed target count mismatch")
    for target in ident["targets"]:
        rel = f"bin/{target}"
        if rel not in sealed:
            _fail(f"{image} target not signed: {target}")
    for alias in ("libggml-base.so", "libggml-cpu.so", "libggml.so", "libllama.so"):
        link = root / "bin" / alias
        if not link.is_symlink():
            _fail(f"{image} alias is not a symlink: {alias}")
        dest = link.resolve(strict=True)
        rel = "bin/" + dest.name
        if dest.parent != (root / "bin").resolve() or rel not in sealed:
            _fail(f"{image} alias target is not a signed local binary: {alias}")
    ops = root / "bin/test-backend-ops"
    if _sha(ops) != spec.get("test_backend_ops_sha256"):
        _fail(f"{image} test-backend-ops binary changed")
    return {"root": str(root), "source": source, "tree": tree,
            "build_result_sha256": _sha(result_path), "sha256sums_sha256": _sha(sums_path)}


def _verified_component(run: Path, package: Path, cohort: str, image: str, top_item: dict, pre: dict) -> dict:
    sub = run / f"{cohort}-{image}"
    rfile = sub / ("result-summary.json" if cohort == "27b" else "RESULT.json")
    sfile = sub / "SHA256SUMS.txt"
    if not rfile.is_file() or not sfile.is_file():
        _fail(f"missing {cohort}/{image} native component")
    component_files = _seal(sub, sfile)
    required_component_files = ({"end.utc", "input.testfile", "image.txt", "thread-config.txt", "scope.txt", "exit.rc", "perf.stderr", "start.utc", "result-summary.json", "perf.sql"}
                               if cohort == "27b" else
                               {"PRE-RUN.json", "RESULT.json", "down.jsonl", "down.rc", "down.stderr", "down.stdout", "gateup.jsonl", "gateup.rc", "gateup.stderr", "gateup.stdout"})
    if not required_component_files <= set(component_files):
        _fail(f"{cohort}/{image} component seal omits required native files")
    data = _json(rfile)
    if _sha(rfile) != top_item.get("result_sha256") or _sha(sfile) != top_item.get("component_seal_sha256"):
        _fail(f"{cohort}/{image} result/seal differs from parent RESULT")
    outer = run / f"{cohort}-{image}.outer.log"
    if _sha(outer) != top_item.get("outer_log_sha256"):
        _fail(f"{cohort}/{image} outer log differs from parent RESULT")
    if cohort == "27b":
        exact = _read(package / "Q4-K-27B-EXACT.testfile", limit=2 << 20)
        if _read(sub / "input.testfile", limit=2 << 20) != exact:
            _fail("27B component input.testfile differs from pinned exact testfile")
        expected_names = [line.split()[-1] for line in exact.decode().splitlines() if line.strip()]
        if data.get("schema") != "c6.35186.q4_cpu_perf_rows.v1" or data.get("case_count") != 9 or data.get("case_names") != expected_names:
            _fail("27B case result identities/count mismatch")
        sql = _read(sub / "perf.sql", limit=2 << 20).decode()
        db = sqlite3.connect(":memory:")
        def deny_external_database(action, arg1, arg2, database, trigger):
            if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH):
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        db.set_authorizer(deny_external_database)
        try:
            db.executescript(sql)
            rows = db.execute("select op_name, op_params, test_mode, supported, hard_failure, error_message, time_us, n_runs, backend_name from test_backend_ops").fetchall()
        except sqlite3.Error as exc:
            _fail(f"27B raw perf SQL invalid: {exc}")
        got = {}
        for op, params, mode, supported, hard, error, us, n_runs, backend in rows:
            m = re.search(r"(?:^|,)name=([^,]+)", params or "")
            name = m.group(1) if m else None
            if name not in expected_names or name in got or op != "MUL_MAT" or mode != "perf" or int(supported) != 1 or int(hard) != 0 or error:
                _fail(f"27B raw perf row invalid: {name!r}")
            if not backend or "CPU" not in backend.upper() or int(n_runs) < 1 or not math.isfinite(float(us)) or float(us) <= 0:
                _fail(f"27B raw timing invalid: {name!r}")
            got[name] = {"backend_name": backend, "time_us": float(us), "n_runs": int(n_runs)}
        if set(got) != set(expected_names) or got != data.get("results"):
            _fail("27B displayed values do not rederive from raw SQLite rows")
        if (sub / "exit.rc").read_text().strip() != "0":
            _fail("27B component exit status is not zero")
        return {name: {"value": values["time_us"], "internal_reps": values["n_runs"],
                       "unit": "us", "metric": "q4k_27b_matmul_latency_us", "case": name,
                       "native_detail": values} for name, values in got.items()}
    pr = _json(sub / "PRE-RUN.json")
    if pr.get("mode") != "--full" or pr.get("image") != image or pr.get("source_sha") != _IMAGE_SOURCE[image][0]:
        _fail(f"DS41 {image} PRE-RUN qualification/image mismatch")
    if pr.get("native_input_byte_hashes") != "UNKNOWN; seed is not byte proof":
        _fail("DS41 native generated-input identity was unexpectedly rewritten")
    for rel, k in (("src/mb_mmid.cpp", "harness_source_sha256"), ("src/ds41-1017-expert-shapes.json", "expert_shapes_sha256"),
                   ("PREDECLARED.md", "historical_predeclared_sha256")):
        if _sha(package / "ds41" / rel) != pr.get(k):
            _fail(f"DS41 pinned input changed: {rel}")
    if pr.get("harness_sha256") != pre.get("instruments", {}).get("ds41_candidate_binary_sha256" if image == "candidate" else "ds41_control_binary_sha256"):
        _fail(f"DS41 {image} native harness hash mismatch")
    image_spec = pre.get("images", {}).get(image, {})
    identity = pr.get("store_identity", {})
    if (pr.get("source_sha") != _IMAGE_SOURCE[image][0] or
            identity.get("result_sha256") != image_spec.get("build_result_sha256") or
            identity.get("seal_sha256") != image_spec.get("sha256sums_sha256")):
        _fail(f"DS41 {image} store provenance mismatch")
    rows = []
    for mode in ("gateup", "down"):
        raw_path = sub / f"{mode}.jsonl"
        raw_rows = [json.loads(x) for x in _read(raw_path).decode().splitlines() if x.strip()]
        if len(raw_rows) != 1:
            _fail(f"DS41 {image}/{mode} expected one native summary row")
        row = raw_rows[0]
        match = next((r for r in data.get("results", []) if r.get("mode") == mode), None)
        if match is None or match.get("native_row") != row or match.get("jsonl_sha256") != _sha(raw_path):
            _fail(f"DS41 {image}/{mode} summary does not match raw JSONL")
        if row.get("status") != "ok" or row.get("wtype") != "Q4_K" or row.get("buf") != "plain" or row.get("mode") != mode:
            _fail(f"DS41 {image}/{mode} native row identity invalid")
        for key in ("us_med", "us_min", "us_p25", "us_p75", "gbs_med"):
            if isinstance(row.get(key), bool) or not isinstance(row.get(key), (int, float)) or not math.isfinite(row[key]) or row[key] <= 0:
                _fail(f"DS41 {image}/{mode} invalid {key}")
        if row.get("reps") != pr.get("reps") or row.get("threads") != pr.get("threads") or row.get("n") != pr.get("n_tokens"):
            _fail(f"DS41 {image}/{mode} repeat/shape coordinate mismatch")
        rows.append({"value": row["us_med"], "internal_reps": row["reps"], "unit": "us",
                     "metric": "q4k_ds41_shape_synthetic_moe_matmul_id_node_latency_us",
                     "case": f"synthetic_q4_{mode}", "native_detail": row})
    return {x["case"]: x for x in rows}


def units(path: str | Path) -> list[Path]:
    p = Path(path)
    if p.is_file():
        return [p.parent] if p.name == "RESULT.json" else []
    if not p.is_dir():
        return []
    if all((p / name).is_file() for name in ("PRE-RUN.json", "RESULT.json", "SHA256SUMS.txt")):
        return [p]
    return sorted(q for q in p.iterdir() if q.is_dir() and all((q / n).is_file() for n in ("PRE-RUN.json", "RESULT.json", "SHA256SUMS.txt")))


def native_rows(path: str | Path) -> tuple[dict, ...]:
    run = Path(path).resolve(strict=True)
    if run.parent.name != "runs" or not run.is_dir() or run.name != CANONICAL_RUN_ID:
        _fail("unit must be the canonical completed R2 run directory under package/runs")
    pre_path, result_path, seal_path = run / "PRE-RUN.json", run / "RESULT.json", run / "SHA256SUMS.txt"
    pre, result = _json(pre_path), _json(result_path)
    if pre.get("schema") != RUN_SCHEMA or pre.get("mode") != "--full":
        _fail("not a full native run; smoke and incomplete bodies project nothing")
    try:
        date = dt.datetime.fromisoformat(pre.get("recorded_at", "").replace("Z", "+00:00")).date().isoformat()
    except (TypeError, ValueError):
        _fail("PRE-RUN timestamp is not an ISO date-time")
    if date != "2026-10-31":
        _fail("PRE-RUN timestamp is outside the captured R2 date")
    if result.get("schema") != SOURCE_KIND or result.get("status") != "COMPLETE_MICROBENCH_ONLY" or result.get("no_keep_or_serving_grade") is not True:
        _fail("run has no complete microbench-only terminal result")
    if result.get("pre_run_sha256") != _sha(pre_path):
        _fail("RESULT does not bind the captured PRE-RUN")
    if pre.get("purpose") != "diagnostic component timing only; existing DS41/Q38FN/serving gates unchanged":
        _fail("purpose changed from component-only observation")
    actual = _seal(run, seal_path, exact_files={"PRE-RUN.json", "RESULT.json", "27b-candidate.outer.log", "27b-control.outer.log", "ds41-candidate.outer.log", "ds41-control.outer.log"})
    expected_ids = [{"cohort": c, "image": i} for c, i, _ in _EXPECTED]
    items = result.get("results")
    if not isinstance(items, list) or [{"cohort": x.get("cohort"), "image": x.get("image")} for x in items] != expected_ids:
        _fail("full result cohort/image sequence missing or changed")
    if pre.get("sequence") != [{"cohort": c, "image": i} for c, i, _ in _EXPECTED]:
        _fail("PRE-RUN sequence does not match the declared full protocol")
    if pre.get("native_input_byte_hashes") != "UNKNOWN; deterministic seeds do not establish identical generated bytes across images":
        _fail("generated native input byte identity must remain UNKNOWN")
    if pre.get("filler_id") != "refactor-c6-35186-q4-two-cohort-cpu-r2-20261031" or pre.get("filler_cpus") != "48-71":
        _fail("calendar run identity/region does not match the declared R2 record")
    if pre.get("env", {}).get("GGML_IQK") != "1" or pre.get("env", {}).get("AUTOKERNEL_CPU_N_THREADS") != "24":
        _fail("recorded candidate build/runtime configuration mismatch")
    if "UNKNOWN" not in str(pre.get("co_tenancy", "")):
        _fail("co-tenancy was not preserved as UNKNOWN")
    package = run.parent.parent
    _verify_package(package, pre)
    component_values = []
    for item, (cohort, image, count) in zip(items, _EXPECTED):
        sub = run / f"{cohort}-{image}"
        if not sub.is_dir(): _fail(f"missing component {cohort}/{image}")
        bycase = _verified_component(run, package, cohort, image, item, pre)
        if len(bycase) != count: _fail(f"{cohort}/{image} case count differs")
        component_values.append((cohort, image, bycase))
    _verify_outer_capture(package, pre)
    image_receipts = {name: _verify_image(pre, name) for name in ("candidate", "control")}
    native: list[dict] = []
    for cohort, image, bycase in component_values:
        # Attach only values sourced from that exact sealed component.
        for case, val in bycase.items():
            row = {"schema": SOURCE_KIND, "run_id": run.name, "cohort": cohort, "image": image,
                   "case": case, "metric": val["metric"], "value": val["value"], "unit": val["unit"],
                   "metric_direction": "lower_better", "internal_reps": val["internal_reps"],
                   "date": pre["recorded_at"][:10], "source_sha": image_receipts[image]["source"],
                   "source_tree": image_receipts[image]["tree"], "purpose": "component timing only; no keep/serving grade",
                   "native_input_byte_identity": "UNKNOWN", "co_tenancy": "UNKNOWN",
                   "attestation_path": str(result_path), "attestation_sha256": _sha(result_path),
                   "attestation_locator": f"{run.name}/RESULT.json#{cohort}/{image}/{case}",
                   "attestation_verified": True, "native_detail": val["native_detail"]}
            native.append(row)
    return tuple(native)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    keys = {"schema", "run_id", "cohort", "image", "case", "metric", "value", "unit", "metric_direction",
            "internal_reps", "date", "source_sha", "source_tree", "purpose", "native_input_byte_identity",
            "co_tenancy", "attestation_path", "attestation_sha256", "attestation_locator", "attestation_verified", "native_detail"}
    if not isinstance(native, dict) or set(native) != keys:
        _fail("native row field set mismatch")
    if native["purpose"] != "component timing only; no keep/serving grade":
        _fail("native purpose scope changed")
    if native["schema"] != SOURCE_KIND or native["cohort"] not in ("27b", "ds41") or native["image"] not in ("candidate", "control"):
        _fail("native row identity mismatch")
    if native["metric_direction"] != "lower_better" or native["unit"] != "us" or native["native_input_byte_identity"] != "UNKNOWN" or native["co_tenancy"] != "UNKNOWN":
        _fail("direction, unit, or recorded uncertainty changed")
    detail = native["native_detail"]
    if not isinstance(detail, dict):
        _fail("native component detail missing")
    if native["cohort"] == "27b":
        if (native["metric"] != "q4k_27b_matmul_latency_us" or
                native["case"] not in {"served_q4km_27b_blk_3_ffn_gate_weight_n1", "served_q4km_27b_blk_3_ffn_gate_weight_n8", "served_q4km_27b_blk_3_ffn_gate_weight_n16", "served_q4km_27b_blk_3_ffn_up_weight_n1", "served_q4km_27b_blk_3_ffn_up_weight_n8", "served_q4km_27b_blk_3_ffn_up_weight_n16", "served_q4km_27b_blk_4_ffn_down_weight_n1", "served_q4km_27b_blk_4_ffn_down_weight_n8", "served_q4km_27b_blk_4_ffn_down_weight_n16"} or
                native["value"] != detail.get("time_us") or native["internal_reps"] != detail.get("n_runs")):
            _fail("27B case/metric/value does not match its validated native detail")
    else:
        mode = detail.get("mode")
        if (native["metric"] != "q4k_ds41_shape_synthetic_moe_matmul_id_node_latency_us" or
                mode not in ("gateup", "down") or native["case"] != f"synthetic_q4_{mode}" or
                native["value"] != detail.get("us_med") or native["internal_reps"] != detail.get("reps")):
            _fail("DS41 synthetic case/metric/value does not match its native detail")
    value = native["value"]
    reps = native["internal_reps"]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        _fail("native latency is not finite positive microseconds")
    if type(reps) is not int or reps < 1:
        _fail("internal repetition coordinate missing")
    src, tree = _IMAGE_SOURCE[native["image"]]
    if native["source_sha"] != src or native["source_tree"] != tree:
        _fail("source image identity mismatch")
    att = Path(native["attestation_path"])
    if (att.name != "RESULT.json" or att.parent.name != CANONICAL_RUN_ID or att.parent.parent.name != "runs" or
            not _SHA.fullmatch(native["attestation_sha256"]) or not att.is_file() or
            _sha(att) != native["attestation_sha256"] or native["attestation_verified"] is not True):
        _fail("run RESULT attestation changed after native read")
    category = "CANDIDATE" if native["image"] == "candidate" else "BASELINE"
    sample = ("per-call Q4_K MUL_MAT component latency" if native["cohort"] == "27b" else
              "per-node synthetic Q4_K MUL_MAT_ID latency at DS41/MXFP4 expert dimensions")
    claim = (f"C6 Q4 microbench {native['cohort']} {native['image']} {native['case']}: {sample} = {value} us. "
             f"Internal timing repetitions={reps}; these are not independent process samples. No serving/keep conclusion. "
             "Generated input byte identity and independent co-tenancy remain UNKNOWN.")
    return ClaimTuple(measurement_id=f"{native['run_id']}:{native['cohort']}:{native['image']}:{native['case']}",
                      metric=native["metric"], value=value, date=native["date"], category=category,
                      claim=claim, metric_direction="lower_better", protocol_id="", reps=1,
                      reps_basis=f"one process-level observation; native internal repetitions={reps} are within-invocation loops, not independent samples",
                      unit="us", attestation_path=str(att), attestation_sha256=native["attestation_sha256"],
                      attestation_locator=native["attestation_locator"], attestation_present=True,
                      attestation_verified=True, source_kind=SOURCE_KIND,
                      applicability={"scope_basis": "native", "build_sha": native["source_sha"][:9]},
                      observation={"outcome_native": f"{native['case']}={value} us; component only; no serving or keep grade"[:120]},
                      extra={"adapter": ADAPTER_ID, "cohort": native["cohort"], "image": native["image"],
                             "case": native["case"], "internal_reps": reps, "source_sha": native["source_sha"],
                             "source_tree": native["source_tree"], "native_detail": native["native_detail"],
                             "native_input_byte_identity": "UNKNOWN", "co_tenancy": "UNKNOWN"})


def frames_for_path(path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for row in native_rows(path):
        frames.extend(to_frames(project(row), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "units", "native_rows", "project", "frames_for_path"]
