"""HSF-5.P host KV mirror acceptance microbench -> measurement ClaimTuples (VB-HSF5P-WRITE).

Native record: ``hsf5p.beliefs.jsonl`` written by the item's own analyzer
(``/mnt/raid0/llm/tmp/f8-launchers-20261024/hsf-5p/gpu/analyze.py``) beside ``VERDICT.json``, schema
``epyc.hsf5p.microbench.row.v1``. One row per byte-verified steps-1-2 copy case (median us of the reps)
and one per DECIDED step-3 gate (G1 decode delta, G2 graphs-reused ratio, G3 restore token mismatches,
G4 replay steps). An INCONCLUSIVE run writes zero rows, so it projects nothing.

STRICT reader: closed field set, ``content_sha256`` re-hashed, every input the row names re-hashed from
the item directory (``out/bench12.jsonl``, ``out/arms.jsonl``, ``out/server.<arm>.log``, the
PREDECLARATION and BUILD_OK), the predeclaration digest checked against its input hash, and every value
RE-DERIVED from those inputs with the rule the predeclaration froze. Any difference refuses the whole
file: a sidecar that does not follow from its own inputs is not evidence.

PROJECTION ONLY: no codified protocol exists for this instrument, so ``protocol_id`` is empty and every
tuple is an OBSERVATION; ``claim_tuple.grade()`` decides. No ladder here.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

ADAPTER_ID = "vidya.adapters.hsf5p_microbench/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "hsf5p-microbench"
ROW_SCHEMA = "epyc.hsf5p.microbench.row.v1"
SIDECAR = "hsf5p.beliefs.jsonl"
ROW_FIELDS = frozenset({
    "schema", "producer", "run_id", "generated_at", "verdict", "predeclaration_sha256", "build", "inputs",
    "kind", "key", "metric", "value", "unit", "direction", "reps", "detail", "content_sha256"})
BUILD_FIELDS = frozenset({"head", "llama_server_sha256", "bench_sha256"})
GATE_METRIC = {
    "G1_decode": ("hsf5p_decode_delta_pct", "pct", "lower_better"),
    "G2_graphs_reused": ("hsf5p_graphs_reused_ratio", "ratio", "higher_better"),
    "G3_restore": ("hsf5p_restore_token_mismatch", "arms", "lower_better"),
    "G4_mirror_engaged": ("hsf5p_replay_steps", "steps", "lower_better"),
}
K = 6
MAX_BYTES = 64 << 20
_SHA = re.compile(r"[0-9a-f]{64}")
_REUSE = re.compile(r"graphs reused =\s+(\d+)")
_SAVE = re.compile(r"kv-host-mirror save: n_tokens=(\d+)/(\d+) fallback_bytes=(\d+) mirror_bytes=(\d+) "
                   r"replay_tokens=(-?\d+) replay_steps=(-?\d+) tail_copies=(\d+)")
_RESTORE = re.compile(r"kv-host-mirror restore: device_bytes=(\d+) device_frags=(\d+) fallback_bytes=(\d+)")


def _read(path: Path) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    except OSError as exc:
        raise ProjectionError(f"hsf5p input unreadable: {path}: {exc}") from exc
    if len(raw) > MAX_BYTES:
        raise ProjectionError(f"hsf5p input exceeds bound: {path}")
    return raw


def body_sha256(rec: dict) -> str:
    body = {k: v for k, v in rec.items() if k != "content_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _jsonl(raw: bytes, where: str) -> list[dict]:
    out = []
    for n, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            out.append(json.loads(line))
        except ValueError as exc:
            raise ProjectionError(f"hsf5p {where}:{n} is not JSON") from exc
    return out


# ------------------------------------------------------------------ re-derivation (the PREDECLARATION rule)

def _bench_cases(rows: list[dict]) -> dict[str, dict]:
    cases: dict[str, list[dict]] = {}
    for r in rows:
        if "case" not in r:
            continue
        if r.get("ok") is not True:
            raise ProjectionError("hsf5p bench12.jsonl holds an unverified copy: no copy row is projectable")
        cases.setdefault(f'{r["step"]}:{r["case"]}:{r["dir"]}:{r["path"]}', []).append(r)
    return {k: {"median_us": round(statistics.median(x["us"] for x in rs), 2), "reps": len(rs),
                "bytes": rs[0]["bytes"], "n_frags": rs[0]["n_frags"]} for k, rs in cases.items()}


def _arm_decode(rows: list[dict], arm: str) -> tuple[float | None, int]:
    per = []
    for w in rows:
        if w.get("kind") != "wave" or w.get("arm") != arm or w.get("wave") == "warmup":
            continue
        ms = [s["timings"].get("predicted_per_token_ms") for s in w["streams"] if s and s.get("ok")]
        ms = [m for m in ms if isinstance(m, (int, float)) and not isinstance(m, bool) and m > 0]
        if len(ms) == 4:
            per.append(sum(ms) / 4.0)
    return (statistics.median(per) if len(per) >= 4 else None), len(per)


def _restore_tokens(rows: list[dict], arm: str):
    r = next((x for x in rows if x.get("kind") == "restore" and x.get("arm") == arm), None)
    if not r or not r.get("ok"):
        return None
    return r.get("cont_tokens") if r.get("cont_tokens") else r.get("cont_content")


def _rederive(row: dict, files: dict[str, bytes]) -> tuple[Any, int]:
    """Value and reps the row must carry, recomputed from the hashed inputs."""
    key = row["key"]
    if row["kind"] == "copy":
        cases = _bench_cases(_jsonl(files["out/bench12.jsonl"], "bench12.jsonl"))
        if key not in cases:
            raise ProjectionError(f"hsf5p copy row {key}: no such case in bench12.jsonl")
        c = cases[key]
        if (row["detail"].get("bytes"), row["detail"].get("n_frags")) != (c["bytes"], c["n_frags"]):
            raise ProjectionError(f"hsf5p copy row {key}: bytes / n_frags differ from bench12.jsonl")
        return c["median_us"], c["reps"]
    arms = _jsonl(files["out/arms.jsonl"], "arms.jsonl")
    if key == "G1_decode":
        (a1, n1), (a2, n2), (b, nb) = (_arm_decode(arms, a) for a in ("A1", "A2", "B"))
        if None in (a1, a2, b):
            raise ProjectionError("hsf5p G1 row but an arm has < 4 complete waves")
        abar = (a1 + a2) / 2.0
        if abs(a1 - a2) / abar > 0.03:
            raise ProjectionError("hsf5p G1 row but the off arms' spread exceeds 3% (INCONCLUSIVE emits no row)")
        return round(100.0 * round((b - abar) / abar, 5), 3), min(n1, n2, nb)
    if key == "G3_restore":
        t = {a: _restore_tokens(arms, a) for a in ("A1", "A2", "B", "Bf")}
        if t["A1"] is None or t["A2"] is None or t["B"] is None or t["A1"] != t["A2"]:
            raise ProjectionError("hsf5p G3 row but the restore checks are missing or A1 != A2 (INCONCLUSIVE)")
        compared = [a for a in ("B", "Bf") if t[a] is not None]
        return sum(1 for a in compared if t[a] != t["A1"]), len(compared)
    logs = {a: files.get(f"out/server.{a}.log", b"").decode("utf-8", "replace") for a in ("A1", "A2", "B")}
    if key == "G2_graphs_reused":
        vals = {}
        for a, text in logs.items():
            found = _REUSE.findall(text)
            if not found:
                raise ProjectionError(f"hsf5p G2 row but server.{a}.log has no graphs reused line")
            vals[a] = int(found[-1])
        ra = (vals["A1"] + vals["A2"]) / 2.0
        return round(vals["B"] / ra if ra > 0 else 0.0, 4), 3
    if key == "G4_mirror_engaged":
        sv = _SAVE.findall(logs["B"])
        if "HSF-5.P kv host mirror ON" not in logs["B"] or not sv:
            raise ProjectionError("hsf5p G4 row but server.B.log shows no enabled mirror or no mirror save")
        return int(sv[-1][5]), 1
    raise ProjectionError(f"hsf5p unknown gate key {key!r}")


# ------------------------------------------------------------------ reader

def native_rows(path: str | Path) -> tuple[dict, ...]:
    p = Path(path)
    if p.is_dir():
        p = p / SIDECAR
    if p.name != SIDECAR or not p.is_file():
        return ()
    raw = _read(p)
    sidecar_sha = hashlib.sha256(raw).hexdigest()
    item = p.parent
    rows = _jsonl(raw, p.name)
    files: dict[str, bytes] = {}
    out = []
    run_ids = set()
    for n, rec in enumerate(rows, 1):
        where = f"{p.name}:{n}"
        if not isinstance(rec, dict) or rec.get("schema") != ROW_SCHEMA:
            raise ProjectionError(f"hsf5p {where}: schema is not {ROW_SCHEMA}")
        if set(rec) != ROW_FIELDS:
            raise ProjectionError(f"hsf5p {where}: field set differs from v1 ({sorted(set(rec) ^ ROW_FIELDS)})")
        if rec["content_sha256"] != body_sha256(rec):
            raise ProjectionError(f"hsf5p {where}: content_sha256 does not re-hash")
        if rec["verdict"] not in ("PASS", "FAIL"):
            raise ProjectionError(f"hsf5p {where}: a row from an undecided run ({rec['verdict']!r})")
        if not isinstance(rec["build"], dict) or set(rec["build"]) != BUILD_FIELDS:
            raise ProjectionError(f"hsf5p {where}: build block malformed")
        for rel, digest in rec["inputs"].items():
            if rel not in files:
                files[rel] = _read((item / rel).resolve()) if not Path(rel).is_absolute() else b""
            if not _SHA.fullmatch(str(digest)) or hashlib.sha256(files[rel]).hexdigest() != digest:
                raise ProjectionError(f"hsf5p {where}: input {rel} does not re-hash")
        if rec["predeclaration_sha256"] != rec["inputs"].get("../PREDECLARATION.md"):
            raise ProjectionError(f"hsf5p {where}: predeclaration digest is not the hashed PREDECLARATION.md")
        if rec["kind"] == "copy":
            if (rec["metric"], rec["unit"], rec["direction"]) != ("hsf5p_copy_median_us", "us", "lower_better"):
                raise ProjectionError(f"hsf5p {where}: copy row metric/unit/direction")
            if "out/bench12.jsonl" not in rec["inputs"]:
                raise ProjectionError(f"hsf5p {where}: copy row without its bench12.jsonl input")
        elif rec["kind"] == "gate":
            if GATE_METRIC.get(rec["key"]) != (rec["metric"], rec["unit"], rec["direction"]):
                raise ProjectionError(f"hsf5p {where}: gate row metric/unit/direction")
            if rec["detail"].get("status") not in ("PASS", "FAIL"):
                raise ProjectionError(f"hsf5p {where}: gate row from an undecided gate")
        else:
            raise ProjectionError(f"hsf5p {where}: unknown kind {rec['kind']!r}")
        value, reps = _rederive(rec, files)
        if value != rec["value"] or reps != rec["reps"]:
            raise ProjectionError(f"hsf5p {where}: {rec['key']} value/reps ({rec['value']}, {rec['reps']}) do not "
                                  f"re-derive ({value}, {reps})")
        run_ids.add(rec["run_id"])
        out.append({"row": rec, "path": str(p), "line": n, "sidecar_sha256": sidecar_sha})
    if len(run_ids) > 1:
        raise ProjectionError(f"hsf5p {p.name}: rows from more than one run")
    return tuple(out)


def units(path: Path) -> list[Path]:
    """ingest_sources unit discovery: sidecars under ``path`` (the item dir, its parent, or the file)."""
    path = Path(path)
    if path.is_file():
        return [path] if path.name == SIDECAR else []
    if not path.is_dir():
        return []
    return sorted(x for x in (path / SIDECAR, *path.glob(f"*/{SIDECAR}")) if x.is_file())


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("hsf5p native row missing")
    r = native["row"]
    b = r["build"]
    head = b.get("head") or ""
    if r["kind"] == "copy":
        step, case, direction, path = r["key"].split(":", 3)
        claim = (f"HSF-5.P mirror copy, step {step} {case} {direction} via {path}: median {r['value']} us over "
                 f"{r['reps']} reps ({r['detail'].get('bytes')} B in {r['detail'].get('n_frags')} fragments, "
                 f"{r['detail'].get('gbps')} GB/s), every copy byte-verified; MI210 host tier on NUMA node 3.")
    else:
        d = r["detail"]
        claim = {
            "G1_decode": lambda: (f"HSF-5.P G1: decode ms/token with the mirror ON (lag, k={K}) is {r['value']}% vs the "
                                  f"mean of two OFF arms (A {d.get('A_mean')} ms, B {d.get('B')} ms, A spread "
                                  f"{d.get('A_spread')}); gate <= 3%: {d.get('status')}."),
            "G2_graphs_reused": lambda: (f"HSF-5.P G2: graphs-reused count with the mirror ON is {r['value']} of the OFF "
                                         f"arms' mean ({d.get('values')}); gate >= 0.97: {d.get('status')}."),
            "G3_restore": lambda: (f"HSF-5.P G3: {r['value']} of {r['reps']} mirror arms ({d.get('compared')}) restore to a "
                                   f"greedy continuation that differs from the OFF slot-file restore; {d.get('status')}."),
            "G4_mirror_engaged": lambda: (f"HSF-5.P G4: a lag-mode mirror save replays {r['value']} decode steps "
                                          f"(bound k={K}), {d.get('tail_copies')} tail copies, save fallback "
                                          f"{d.get('save_fallback_bytes')} B, restore {d.get('restore_device_bytes')} B "
                                          f"by device copy; {d.get('status')}."),
        }[r["key"]]()
    claim += f" Run {r['run_id']} verdict {r['verdict']}; fork commit {head[:12] or 'unknown'}."
    applicability: dict[str, Any] = {"scope_basis": "native"}
    if b.get("llama_server_sha256"):
        applicability["kernel"] = {"binary": "build-hip-hsf5p/bin/llama-server", "binary_sha256": b["llama_server_sha256"]}
    if head:
        applicability["build_sha"] = head[:9]
    return ClaimTuple(
        measurement_id=f"{r['run_id']}:{r['kind']}:{r['key']}", metric=r["metric"], value=r["value"],
        date=r["generated_at"][:10], category="CANDIDATE", claim=claim, metric_direction=r["direction"],
        protocol_id="", reps=r["reps"],
        reps_basis=("scored: reps of this copy case, each byte-verified" if r["kind"] == "copy" else
                    "scored: complete waves / arms the predeclared rule counted"),
        unit=r["unit"], attestation_path=native["path"], attestation_sha256=native["sidecar_sha256"],
        attestation_locator=f"hsf5p:{native['path']}#L{native['line']}", attestation_present=True,
        attestation_verified=True, source_kind=SOURCE_KIND, applicability=applicability,
        observation={"outcome_native": f"{r['key']}={r['value']} {r['unit']} ({r['verdict']})"[:120]},
        extra={"adapter": ADAPTER_ID, "kind": r["kind"], "key": r["key"], "detail": r["detail"],
               "predeclaration_sha256": r["predeclaration_sha256"], "build": b, "producer": r["producer"]},
    )


def frames_for_path(path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "native_rows", "project", "units", "frames_for_path"]
