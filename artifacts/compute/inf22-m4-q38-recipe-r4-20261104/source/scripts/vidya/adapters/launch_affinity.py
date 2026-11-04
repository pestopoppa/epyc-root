"""Per-task launch-affinity readings -> measurement ClaimTuples (VB-LAUNCH-AFFINITY-WIRE).

A reading answers one question for ONE pid at ONE moment: how many of its tasks may run outside the
placement it was launched on (STACKCHG-GPUPIN-20261022: a ``taskset -c 184-191`` HIP llama-server had
one ROCr thread on ``0-191``). It is per pid, per task and per moment -- a clean read at health does
not cover threads created later -- and a reading with no readable task is UNCHECKED, never clean, so
it projects nothing.

Two native shapes, both read as written:

* **Prospective** ``epyc.launch_affinity.reading.v1`` JSONL (epyc-orchestrator
  ``scripts/server/launch_affinity.py`` ``affinity_reading`` / ``--check ... --record``, and
  ``scripts/benchmark/serving_gate.py`` ``<out>/affinity_readings.jsonl``). STRICT: closed field
  set, ``content_sha256`` re-hashed, ``tasks_seen`` re-counted and every escape re-derived from the
  task masks and the declared placement; any difference refuses the whole file.
* **Pre-hook task dumps** from the 2026-10-22 diagnosis and the 2026-10-23 P1 probe (``<tid> <comm>
  <mask>`` lines: ``diag-affinity-*.out``, ``probe-*/<moment>.tasks`` + ``SUMMARY``). The dump, its
  stated counts and the launch script it names are re-read and re-counted; the declared placement
  and the ROCr knob come from that script (and, for the probe, its own ``/proc/<pid>/environ`` grep
  line). What those records never captured stays absent: no binary sha256 (the path is the script's
  declaration, not a verified identity), and the read time is the dump file's mtime, said so. These
  tuples carry ``observation.retrofit``.

PROJECTION ONLY: one tuple per reading, metric ``launch_affinity_tasks_escaping`` (tasks, lower
better), ``reps`` = tasks read. No codified protocol exists, so ``protocol_id`` is empty and every
tuple is an OBSERVATION; ``claim_tuple.grade()`` decides. No ladder here.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

ADAPTER_ID = "vidya.adapters.launch_affinity/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "launch-affinity"
READING_SCHEMA = "epyc.launch_affinity.reading.v1"
READING_FIELDS = frozenset({
    "schema", "producer", "read_at", "moment", "label", "recipe", "host", "pid", "pid_starttime_ticks",
    "exe", "exe_sha256", "declared_cpus", "rocr_env_key", "rocr_env_readable", "rocr_env_value",
    "tasks", "tasks_seen", "escapes", "pin", "content_sha256"})
MOMENTS = frozenset({"check", "post_health_pin", "pre_stop"})
ROCR_KEY = "HSA_OVERRIDE_CPU_AFFINITY_DEBUG"
MAX_BYTES = 16 << 20
_TASK = re.compile(r"^(\d+) (\S+)\s+(\S+)$")
_SHA = re.compile(r"[0-9a-f]{64}")
_BUILD = re.compile(r"/kernels/builds/(?:cpu|gpu)-\d{8}-([0-9a-f]{7,40})/")
_TASKSET = re.compile(r"taskset -c ([0-9][0-9,-]*)")
_RUNNING = re.compile(r"\[region-lock\] held .* running: /bin/bash (\S+)$")
_SUMMARY = re.compile(r"^(\w+): tasks=(\d+) outside_(\S+)=(\d+)$")
_KILLED = re.compile(r"^killed (\d+) \(verified\)$")


def _read(path: Path) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    except OSError as exc:
        raise ProjectionError(f"launch-affinity input unreadable: {path}: {exc}") from exc
    if len(raw) > MAX_BYTES:
        raise ProjectionError(f"launch-affinity input exceeds bound: {path}")
    return raw


def parse_cpu_list(spec: Any) -> frozenset[int]:
    """Strict taskset-style list; the same grammar as the producer's."""
    if not isinstance(spec, str) or not spec.strip():
        raise ProjectionError(f"launch-affinity empty cpu list: {spec!r}")
    cpus: set[int] = set()
    for part in spec.strip().split(","):
        lo, sep, hi = part.strip().partition("-")
        if not lo.isdigit() or (sep and not hi.isdigit()) or (sep and int(hi) < int(lo)):
            raise ProjectionError(f"launch-affinity malformed cpu list {spec!r}")
        cpus.update(range(int(lo), int(hi if sep else lo) + 1))
    return frozenset(cpus)


def _body_sha256(record: dict) -> str:
    body = {k: v for k, v in record.items() if k != "content_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _escapes(tasks: list[dict], declared: str) -> list[dict]:
    allowed = parse_cpu_list(declared)
    return [t for t in tasks if not parse_cpu_list(t["cpus"]) <= allowed]


def _check_tasks(tasks: Any, where: str) -> list[dict]:
    if not isinstance(tasks, list):
        raise ProjectionError(f"launch-affinity {where}: tasks is not a list")
    for t in tasks:
        if not (isinstance(t, dict) and set(t) == {"tid", "comm", "cpus"} and type(t["tid"]) is int
                and isinstance(t["comm"], str)):
            raise ProjectionError(f"launch-affinity {where}: malformed task row {t!r}")
        parse_cpu_list(t["cpus"])
    if len({t["tid"] for t in tasks}) != len(tasks):
        raise ProjectionError(f"launch-affinity {where}: duplicate tid")
    return tasks


# ------------------------------------------------------------------ prospective v1 readings

def _prospective(path: Path) -> list[dict]:
    raw = _read(path)
    out = []
    for n, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except ValueError as exc:
            raise ProjectionError(f"launch-affinity {path.name}:{n} is not JSON") from exc
        where = f"{path.name}:{n}"
        if not isinstance(rec, dict) or rec.get("schema") != READING_SCHEMA:
            raise ProjectionError(f"launch-affinity {where}: schema is not {READING_SCHEMA}")
        if set(rec) != READING_FIELDS:
            raise ProjectionError(f"launch-affinity {where}: field set differs from v1 "
                                  f"({sorted(set(rec) ^ READING_FIELDS)})")
        if rec["content_sha256"] != _body_sha256(rec):
            raise ProjectionError(f"launch-affinity {where}: content_sha256 does not re-hash")
        if rec["moment"] not in MOMENTS or rec["rocr_env_key"] != ROCR_KEY:
            raise ProjectionError(f"launch-affinity {where}: unknown moment or knob key")
        tasks = _check_tasks(rec["tasks"], where)
        if rec["tasks_seen"] != len(tasks):
            raise ProjectionError(f"launch-affinity {where}: tasks_seen differs from the task rows")
        if rec["escapes"] != _escapes(tasks, rec["declared_cpus"]):
            raise ProjectionError(f"launch-affinity {where}: escapes do not re-derive from the masks")
        if rec["exe_sha256"] is not None and not _SHA.fullmatch(str(rec["exe_sha256"])):
            raise ProjectionError(f"launch-affinity {where}: exe_sha256 malformed")
        try:
            datetime.datetime.strptime(rec["read_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
        except (TypeError, ValueError) as exc:
            raise ProjectionError(f"launch-affinity {where}: read_at is not a UTC timestamp") from exc
        if not tasks:
            continue                                  # pid gone / unreadable: UNCHECKED, never clean
        out.append({
            "shape": "v1", "path": str(path), "line": n, "record_sha256": rec["content_sha256"],
            "read_at": rec["read_at"], "read_at_basis": "producer clock at read",
            "moment": rec["moment"], "label": rec["label"], "recipe": rec["recipe"], "host": rec["host"],
            "pid": rec["pid"], "pid_starttime_ticks": rec["pid_starttime_ticks"],
            "exe": rec["exe"], "exe_sha256": rec["exe_sha256"], "exe_basis": "/proc/<pid>/exe at read",
            "declared_cpus": rec["declared_cpus"], "rocr_env_readable": rec["rocr_env_readable"],
            "rocr_env_value": rec["rocr_env_value"], "rocr_env_basis": "/proc/<pid>/environ at read",
            "tasks_seen": len(tasks), "escapes": rec["escapes"], "pin": rec["pin"],
            "category": "BASELINE", "retrofit": False, "producer": rec["producer"]})
    return out


# ------------------------------------------------------------------ pre-hook task dumps

def _dump_tasks(lines: list[str], where: str) -> list[dict]:
    tasks = []
    for line in lines:
        m = _TASK.match(line)
        if m:
            tasks.append({"tid": int(m.group(1)), "comm": m.group(2), "cpus": m.group(3)})
    return _check_tasks(tasks, where)


def _script(path: Path) -> dict:
    text = _read(path).decode("utf-8")
    code = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
    sets = _TASKSET.findall(code)
    if not sets or len(set(sets)) != 1:
        raise ProjectionError(f"launch-affinity {path.name}: launch script does not declare exactly one "
                              "taskset placement")
    bdir = re.search(r"^B=(\S+)$", code, re.M)
    launch = next((ln for ln in code.splitlines() if "llama-server" in ln and "taskset -c" in ln), "")
    if not bdir or "$B/llama-server" not in launch:
        raise ProjectionError(f"launch-affinity {path.name}: launch script names no $B/llama-server launch")
    return {"path": str(path), "sha256": hashlib.sha256(text.encode()).hexdigest(), "declared": sets[0],
            "exe": f"{bdir.group(1)}/llama-server", "knob_in_launch": f"{ROCR_KEY}=0" in launch,
            "repin_taskset_a": "taskset -a -p -c" in code}


def _mtime(path: Path) -> str:
    return datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ")


def _legacy_common(script: dict, evidence: Path, raw: bytes, pid: int, tasks: list[dict], moment: str,
                   label: str, knob_value: str | None, knob_readable: bool, knob_basis: str) -> dict:
    if pid not in {t["tid"] for t in tasks}:
        raise ProjectionError(f"launch-affinity {evidence.name}: the dump does not contain its own pid {pid}")
    fixed = script["knob_in_launch"] or script["repin_taskset_a"]
    return {
        "shape": "legacy-task-dump", "path": str(evidence), "line": None,
        "record_sha256": hashlib.sha256(raw).hexdigest(), "read_at": _mtime(evidence),
        "read_at_basis": "dump file mtime (the dump records no read time)", "moment": moment,
        "label": label, "recipe": None, "host": None, "pid": pid, "pid_starttime_ticks": None,
        "exe": script["exe"], "exe_sha256": None,
        "exe_basis": "launch script declaration; binary sha256 not captured at write time",
        "declared_cpus": script["declared"], "rocr_env_readable": knob_readable,
        "rocr_env_value": knob_value, "rocr_env_basis": knob_basis,
        "tasks_seen": len(tasks), "escapes": _escapes(tasks, script["declared"]), "pin": None,
        "category": "CANDIDATE" if fixed else "BASELINE", "retrofit": True,
        "producer": f"pre-hook shell dump ({Path(script['path']).name}, sha256 {script['sha256'][:16]})",
        "script": script}


def _legacy_probe(d: Path) -> list[dict]:
    summary = _read(d / "SUMMARY").decode("utf-8").splitlines()
    script = _script(d.parent / f"{d.name}.sh")
    pid = next((int(m.group(1)) for m in map(_KILLED.match, summary) if m), None)
    if pid is None:
        raise ProjectionError(f"launch-affinity {d.name}/SUMMARY names no verified pid")
    knob = any(ln == f"env: knob present in /proc/{pid}/environ" for ln in summary)
    out = []
    for m in filter(None, map(_SUMMARY.match, summary)):
        label, n_tasks, cpus, outside = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
        f = d / f"{label}.tasks"
        raw = _read(f)
        tasks = _dump_tasks(raw.decode("utf-8").splitlines(), f.name)
        if cpus != script["declared"]:
            raise ProjectionError(f"launch-affinity {f.name}: SUMMARY placement differs from the launch script")
        # the probe's own rule counts a mask != the placement as outside; it must re-count exactly
        if n_tasks != len(tasks) or outside != sum(1 for t in tasks if t["cpus"] != cpus):
            raise ProjectionError(f"launch-affinity {f.name}: SUMMARY counts do not re-derive from the dump")
        moment = "post_health" if label.endswith("health") else label.split("_", 1)[-1]
        out.append(_legacy_common(
            script, f, raw, pid, tasks, moment, f"{d.name}/{label}",
            "0" if knob else None, knob,
            "probe grep of /proc/<pid>/environ for the exact '=0' entry" if knob else
            "probe grep did not report the knob"))
    if not out:
        raise ProjectionError(f"launch-affinity {d.name}/SUMMARY has no task-dump lines")
    return out


def _legacy_diag(f: Path) -> list[dict]:
    raw = _read(f)
    lines = raw.decode("utf-8").splitlines()
    run = next((m.group(1) for m in map(_RUNNING.match, lines) if m), None)
    pid = next((int(m.group(1)) for m in map(_KILLED.match, lines) if m), None)
    if run is None or pid is None:
        raise ProjectionError(f"launch-affinity {f.name}: names no launch script or no verified pid")
    script = _script(Path(run))
    main = next((ln for ln in lines if ln.startswith(f"pid={pid} main affinity:")), None)
    if main is not None and main.split("Cpus_allowed_list:", 1)[-1].strip() != script["declared"]:
        raise ProjectionError(f"launch-affinity {f.name}: main-thread mask differs from the declared placement")
    tasks = _dump_tasks(lines, f.name)
    moment = "post_health_after_taskset_a" if script["repin_taskset_a"] else "post_health"
    knob = script["knob_in_launch"]
    return [_legacy_common(script, f, raw, pid, tasks, moment, f.stem, "0" if knob else None, False,
                           "launch script text (process environ was not read); "
                           + ("sets the knob" if knob else "sets no knob"))]


# ------------------------------------------------------------------ entry points

def native_rows(path: str | Path) -> tuple[dict, ...]:
    p = Path(path)
    if p.is_dir():
        if (p / "SUMMARY").is_file() and any(p.glob("*.tasks")):
            return tuple(_legacy_probe(p))
        return ()
    if p.name.startswith("diag-affinity-") and p.suffix == ".out":
        return tuple(_legacy_diag(p))
    if p.name == "affinity_readings.jsonl" or p.name.endswith(".affinity.jsonl"):
        return tuple(_prospective(p))
    return ()


def units(path: Path) -> list[Path]:
    """ingest_sources unit discovery: reading files, pre-hook dumps and probe dirs under ``path``."""
    path = Path(path)
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    if (path / "SUMMARY").is_file() and any(path.glob("*.tasks")):
        return [path]
    found = set()
    for pattern in ("affinity_readings.jsonl", "*/affinity_readings.jsonl", "*.affinity.jsonl",
                    "diag-affinity-*.out"):
        found.update(x for x in path.glob(pattern) if x.is_file())
    found.update(x for x in path.iterdir()
                 if x.is_dir() and (x / "SUMMARY").is_file() and any(x.glob("*.tasks")))
    return sorted(found)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or native.get("shape") not in ("v1", "legacy-task-dump"):
        raise ProjectionError("launch-affinity native reading missing")
    seen, esc = native["tasks_seen"], native["escapes"]
    k = len(esc)
    shown = ", ".join(f"{t['tid']}({t['comm']})={t['cpus']}" for t in esc[:4]) + (
        f" (+{k - 4} more)" if k > 4 else "")
    sha = native["exe_sha256"]
    exe = f"exe {native['exe']} " + (f"sha256 {sha[:12]}" if sha else "(binary sha256 not captured)")
    knob = native["rocr_env_value"]
    knob_txt = (f"{ROCR_KEY}={knob}" if knob is not None else
                f"{ROCR_KEY} not set" if native["rocr_env_readable"] or "sets no knob" in native["rocr_env_basis"]
                else f"{ROCR_KEY} unknown")
    claim = (f"Launch-affinity reading ({native['moment']}, {native['read_at']}): {seen - k}/{seen} tasks of "
             f"pid {native['pid']} ({native['label']}; {exe}"
             + (f"; recipe {native['recipe']}" if native["recipe"] else "")
             + f") inside declared {native['declared_cpus']}; {k} escaping" + (f": {shown}" if k else "")
             + f"; ROCr {knob_txt}. Covers this pid at this moment only; threads created later are not covered."
             + (" Pre-hook evidence: read time is the dump mtime, binary identity not verified."
                if native["retrofit"] else ""))
    applicability: dict[str, Any] = {}
    if native["exe"]:
        applicability["kernel"] = {"binary": native["exe"], **({"binary_sha256": sha} if sha else {})}
        build = _BUILD.search(native["exe"])
        if build:
            applicability["build_sha"] = build.group(1)
    if native["recipe"]:
        applicability["recipe"] = native["recipe"]
    if applicability:
        applicability["scope_basis"] = "native"
    ident = (f"launch-affinity:{native['host']}:{native['pid']}:{native['pid_starttime_ticks']}:"
             f"{native['moment']}:{native['read_at']}" if native["shape"] == "v1" else
             f"launch-affinity:legacy:{native['record_sha256'][:16]}:{native['moment']}")
    observation: dict[str, Any] = {"outcome_native": f"{seen - k}/{seen} inside {native['declared_cpus']}"[:120]}
    if native["retrofit"]:
        observation["retrofit"] = True
    locator = native["path"] + (f"#L{native['line']}" if native["line"] else "")
    return ClaimTuple(
        measurement_id=ident, metric="launch_affinity_tasks_escaping", value=k,
        date=native["read_at"][:10], category=native["category"], claim=claim,
        metric_direction="lower_better", protocol_id="", reps=seen,
        reps_basis=f"scored: {seen} tasks read from /proc/<pid>/task at the reading", unit="tasks",
        attestation_path=native["path"], attestation_sha256=native["record_sha256"],
        attestation_locator=f"launch-affinity:{locator}", attestation_present=True,
        attestation_verified=True, source_kind=SOURCE_KIND, applicability=applicability,
        observation=observation,
        extra={"adapter": ADAPTER_ID, "shape": native["shape"], "label": native["label"],
               "moment": native["moment"], "read_at_basis": native["read_at_basis"],
               "exe_basis": native["exe_basis"], "rocr_env_basis": native["rocr_env_basis"],
               "pid_starttime_ticks": native["pid_starttime_ticks"], "host": native["host"],
               "escapes": esc, "pin": native["pin"], "producer": native["producer"],
               "script": native.get("script")},
    )


def frames_for_path(path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "native_rows", "project", "units", "frames_for_path"]
