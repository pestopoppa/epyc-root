"""Strict projection of prospective owned CPU target-profile receipts.

The profile worker authors both native claim mappings before the controller publishes
``PROFILE_VERIFIED``.  This reader joins that publication to its original accepted worker
terminal and reopens the compact capture.  It never interprets profile integrity as production
validation and never grades; :mod:`claim_tuple` remains the sole grading authority.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.autokernel_profile/v1"
JOURNAL_SCHEMA = "epyc.autokernel.journal_entry.v1"
PROFILE_KIND = "ACTOR_PREPARATION"
LIFECYCLE_KIND = "WORKER_LIFECYCLE"
PROFILE_SCHEMA = "epyc.autokernel.target_profile_verified.v1"
LIFECYCLE_SCHEMA = "epyc.autokernel.worker_lifecycle_event.v1"
CAPTURE_SCHEMA = "epyc.autokernel.cpu_profile_capture.v1"
LOOP_PROFILE_SCHEMA = "epyc.autokernel.loop_cpu_profile.v1"
LOOP_CAPTURE_SCHEMA = "epyc.autokernel.loop_cpu_profile_capture.v1"
LOOP_MODE = "original_serving_requests_observation"
DIRECT_CPU_SOURCE_DIGEST = "6b2f6060df5b5d36980bc9ea7137168bd9ca978959b22038dfba88b12c50b146"
# Reviewed current serving implementation, including factual CPU invalid-arm
# handling. Historical captured bytes keep their original identities above/below.
FACTUAL_CPU_SOURCE_DIGEST = "18a9d42bb35949ce2b9a6752f639957ba70469b851d70e003a526e14b8c012cd"
# Production command aliases and the frozen v9 omitted-ubatch default (512).
CURRENT_CPU_SOURCE_DIGEST = "926f9cce5fa92598e5120006611be5d97189952907af06c7561f6f5628c3b2ba"
# Same serving profiler with the reviewed direct runtime response recorder.
RUNTIME_CPU_SOURCE_DIGEST = "95dcf5179f7eb1e26b4f481e790de740577d30baebe27c939a548a1abf9ffe48"
# Reviewed prospective matched source comparison plus the exact GPU runtime
# fallback predicate. The CPU profiler's _measure_once implementation is unchanged.
MATCHED_CPU_SOURCE_DIGEST = "09e804897a555d19e6b3f37ba56cbc493e5c02b57fc7bc09e41bfdf03e345fc7"
CARRIER_SCHEMA = "epyc.autokernel.profile_measurement_carrier.v1"
PROFILE_SOURCE_ID = "VB-AK-UNIFIED-PROFILE"
VALIDATION_SOURCE_ID = "VB-AK-UNIFIED-VALIDATION"
CPU_SOURCE_SCHEMA = "epyc.autokernel.cpu_profile_source.v1"
CPU_SOURCE_DIGEST = "c8c1184429e07d8d692f1e698232814169c21beeeeff88f10286f148a38feec5"
MODE = "independent_full_request_v1"
LIMITATIONS = (
    "sampled-period totals are estimated user-cycle attribution, not exact CPU cost",
    "worker self attribution is not wall-time share or an optimization gain",
    "totals are not a comparable performance objective across windows, exposure or unknown sample loss",
    "full-request warmup/measurement only; setup/load are not profiled",
    "counter totals cover their own enable/disable window, not the exact request or sample window; no cross-window IPC",
    "no exact generated-token, MTP, correctness, contention or GPU warrant",
    "no ratified measurement protocol or opportunity is supplied",
)
# The legacy (pre-research-07333b884) capture scope. ``LIMITATIONS`` keeps its name so the
# legacy reader and its callers are byte-for-byte what they were before the v2 reader.
LEGACY_LIMITATIONS = LIMITATIONS
# Research 07333b884 (2026-09-17, "Capture sampled CPU topology in original-request CPU
# profiles") inserts exactly one limitation before the last, as the producer's own
# ``LEGACY_LIMITATIONS = LIMITATIONS[:-2] + LIMITATIONS[-1:]`` records.
SAMPLED_CPU_LIMITATIONS = LIMITATIONS[:-1] + (
    "sampled CPU/NUMA attribution is execution location, not remote-memory traffic or a causal diagnosis",
) + LIMITATIONS[-1:]
# Source-closure digests of the sampled-CPU producer, computed with the producer's own method
# (``lifecycle_observation._digest(cpu_profile.source_identity())``) on a ``git archive`` of the
# named research commit. The closure includes the interpreter identity; both were computed under
# /usr/bin/python3.13 (sha256 efb29ce53d36ebaeee80e3aa44fd6c7f9d71bbded5fe1665240b2ed8ecaeee0e),
# the interpreter that produced the legacy pins (research 83334d892 reproduces
# MATCHED_CPU_SOURCE_DIGEST under it). No other sampled-CPU closure is pinned.
# Research 07333b884 (2026-09-17): the first producer that writes ``--sample-cpu`` captures.
SAMPLED_CPU_SOURCE_DIGEST_07333B884 = (
    "54b4a0ef0df78ddda4ed22802ad84bd498381c00d329fe999c99b7e3678f9686")
# Research main b93017dc9 (2026-10-22): same capture shape; closure files changed after
# 07333b884 (cpu_profile.py c3a727bf2, f4a5d240b, dc1828a0a, plus closure dependencies).
SAMPLED_CPU_SOURCE_DIGEST_MAIN_B93017DC9 = (
    "69dea977d0b0c62e30e5cb7f128e2b26090fcda510b436ec3c357d107146ca19")
TOPOLOGY_SCHEMA = "epyc.autokernel.cpu_topology.v1"
SAMPLED_CPU_FLAG = "--sample-cpu"
LEGACY_SCRIPT_FIELDS = "pid,tid,time,period,event,ip,sym,dso"
SAMPLED_CPU_SCRIPT_FIELDS = "pid,tid,cpu,time,period,event,ip,sym,dso"
PROPOSITION = (
    "This original CPU profile receipt reopens with the recorded request, artifact, source and "
    "window joins"
)
_SHA = re.compile(r"^[0-9a-f]{64}$")
_MAX_CAPTURE_BYTES = 16 * 1024 * 1024
_MAX_TIDS = 4096
_MAX_SYMBOLS = 4096
_MAX_CPU_IDS = 4096
_MAX_LOCATION_GROUPS = 16384
_ENVELOPE = {"journal_schema", "event_id", "seq", "kind", "campaign_id", "record_id",
             "written_at", "payload"}
_PROFILE_FIELDS = {
    "schema", "event", "campaign_id", "config_generation", "config_digest",
    "supervisor_id", "supervisor_incarnation", "control_revision", "catalog_id",
    "transition_id", "stage_plan_digest", "profile_request_digest",
    "target_revision_digest", "target_profile_digest", "profile_request", "profile_content",
    "artifact_identity", "loaded_identity", "measurement_carrier", "clock_domain",
    "verifier_ref", "verified_at", "valid_until", "occurred_at",
}
_LIFECYCLE_FIELDS = {
    "schema", "event", "campaign_id", "config_digest", "config_generation", "supervisor_id",
    "supervisor_incarnation", "worker_id", "worker_generation", "request_id", "plan_digest",
    "lineage_id", "stage_id", "grant_id", "grant_generation", "container_id",
    "control_revision", "occurred_at", "data",
}
_CAPTURE_FIELDS = {"schema", "request_digest", "target_revision_digest", "source_closure",
                   "loaded_identity", "model_verification", "profiler", "processes", "phases",
                   "completion", "limitations"}
_PHASE_FIELDS = {"phase", "enabled_interval", "target_before", "target_after", "tids", "tools",
                 "response", "observed_predicted_n", "parser", "counter_scope", "counters",
                 "script", "samples"}
_TOOL_FIELDS = {"kind", "identity", "returncode", "process_observation", "command", "controls",
                "stderr", "artifact"}
_ARTIFACT_FIELDS = {"path", "size", "sha256", "dev", "ino", "mtime_ns", "ctime_ns"}
_SAMPLE_FIELDS = {"samples", "sampled_period_total", "outside_request_samples", "lost_records",
                  "symbol_periods", "tid_periods"}
_TOPOLOGY_FIELDS = {"schema", "logical_cpus", "physical_sibling_groups", "cpu_to_physical_group",
                    "cpu_to_numa_node", "topology_digest"}
_LOCATION_FIELDS = {"tid", "cpu", "numa_node", "family", "period"}
_PROFILE_CONTENT_FIELDS = {"schema", "target_revision_digest", "freshness", "quant", "hotspots",
                           "observation_states", "kept_scope", "resource_cost", "opportunities"}
_PROFILE_TUPLE_FIELDS = {"date", "category", "protocol_id", "reps", "reps_basis",
                         "attestation_locator", "attestation_sha256", "attestation_present",
                         "attestation_verified", "measurement_id", "metric", "value",
                         "metric_direction", "unit", "claim", "source_class", "extra"}
_VALIDATION_TUPLE_FIELDS = _PROFILE_TUPLE_FIELDS | {"decided_proposition", "binding_kind"}


@dataclass(frozen=True)
class CaptureVersion:
    """One closed capture shape. A record is read under exactly one of these or refused."""
    name: str
    limitations: tuple[str, ...]
    sampled_cpu: bool
    phase_fields: frozenset[str]
    sample_fields: frozenset[str]
    bundle_source_digests: frozenset[str]
    loop_source_digests: frozenset[str]


# Exactly the pre-07333b884 reader: same fields, limitations and source allow-lists.
LEGACY_CAPTURE = CaptureVersion(
    name="legacy-v1", limitations=LEGACY_LIMITATIONS, sampled_cpu=False,
    phase_fields=frozenset(_PHASE_FIELDS), sample_fields=frozenset(_SAMPLE_FIELDS),
    bundle_source_digests=frozenset({
        CPU_SOURCE_DIGEST, DIRECT_CPU_SOURCE_DIGEST, CURRENT_CPU_SOURCE_DIGEST,
        FACTUAL_CPU_SOURCE_DIGEST, RUNTIME_CPU_SOURCE_DIGEST, MATCHED_CPU_SOURCE_DIGEST}),
    loop_source_digests=frozenset({
        DIRECT_CPU_SOURCE_DIGEST, CURRENT_CPU_SOURCE_DIGEST, FACTUAL_CPU_SOURCE_DIGEST,
        RUNTIME_CPU_SOURCE_DIGEST, MATCHED_CPU_SOURCE_DIGEST}))
# Research 07333b884 onward: ``perf record --sample-cpu``, a per-phase sampled topology and
# per-TID x family x sampled-CPU/NUMA location periods. Only these sampled fields are added.
SAMPLED_CPU_CAPTURE = CaptureVersion(
    name="sampled-cpu-topology-v2", limitations=SAMPLED_CPU_LIMITATIONS, sampled_cpu=True,
    phase_fields=frozenset(_PHASE_FIELDS | {"topology"}),
    sample_fields=frozenset(_SAMPLE_FIELDS | {"location_periods"}),
    bundle_source_digests=frozenset({SAMPLED_CPU_SOURCE_DIGEST_07333B884,
                                     SAMPLED_CPU_SOURCE_DIGEST_MAIN_B93017DC9}),
    loop_source_digests=frozenset({SAMPLED_CPU_SOURCE_DIGEST_07333B884,
                                   SAMPLED_CPU_SOURCE_DIGEST_MAIN_B93017DC9}))
CAPTURE_VERSIONS = (LEGACY_CAPTURE, SAMPLED_CPU_CAPTURE)


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError, UnicodeError, RecursionError) as exc:
        raise ProjectionError("profile evidence is not finite canonical JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _exact(value: Any, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise ProjectionError(f"{label} has missing or unknown fields")
    return value


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        raise ProjectionError(f"{label} must be lowercase SHA-256")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\0" in value:
        raise ProjectionError(f"{label} must be nonempty text")
    return value


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ProjectionError(f"{label} must be an integer >= {minimum}")
    return value


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ProjectionError(f"{label} must be finite")
    return float(value)


def _envelope(value: Any, kind: str, label: str) -> tuple[dict, dict]:
    row = _exact(value, _ENVELOPE, label)
    if row["journal_schema"] != JOURNAL_SCHEMA or row["kind"] != kind:
        raise ProjectionError(f"{label} schema/kind differs")
    _text(row["event_id"], f"{label}.event_id")
    _integer(row["seq"], f"{label}.seq", minimum=1)
    _text(row["campaign_id"], f"{label}.campaign_id")
    if row["record_id"] is not None:
        _text(row["record_id"], f"{label}.record_id")
    _text(row["written_at"], f"{label}.written_at")
    if not isinstance(row["payload"], dict):
        raise ProjectionError(f"{label}.payload must be an object")
    return row, row["payload"]


def _open_directory(path: Path) -> tuple[int, int, str]:
    if ".." in path.parts:
        raise ProjectionError("profile artifact root contains a parent traversal")
    absolute = path if path.is_absolute() else Path.cwd() / path
    components = absolute.parts[1:]
    if not components:
        raise ProjectionError("profile artifact root cannot be the filesystem root")
    parent = os.open("/", os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        for component in components[:-1]:
            child = os.open(
                component,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=parent,
            )
            os.close(parent)
            parent = child
        root = os.open(
            components[-1],
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent,
        )
        return root, parent, components[-1]
    except Exception:
        os.close(parent)
        raise


def _artifact(root: Path, reference: Any, *, fields=None) -> dict:
    ref = _exact(reference, {"locator", "sha256", "verified"}, "profile artifact")
    locator = _text(ref["locator"], "profile artifact locator")
    digest = _sha(ref["sha256"], "profile artifact digest")
    if ref["verified"] is not True or "/" in locator or locator.startswith(".") \
            or not locator.endswith(".json") or len(locator) > 256:
        raise ProjectionError("profile artifact is not a verified private-store leaf")
    root_fd = parent_fd = fd = -1
    root_name = ""
    try:
        root_fd, parent_fd, root_name = _open_directory(Path(root))
        root_before = os.fstat(root_fd)
        fd = os.open(locator, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0),
                     dir_fd=root_fd)
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_size > _MAX_CAPTURE_BYTES):
            raise ProjectionError("profile capture must be a bounded single-link regular file")
        remaining, chunks = before.st_size, []
        while remaining:
            chunk = os.read(fd, min(remaining, 1024 * 1024))
            if not chunk:
                raise ProjectionError("profile capture ended before its pinned size")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(fd, 1):
            raise ProjectionError("profile capture grew while being verified")
        raw = b"".join(chunks)
        after = os.fstat(fd)
        named = os.stat(locator, dir_fd=root_fd, follow_symlinks=False)
        root_after = os.fstat(root_fd)
        named_root = os.stat(root_name, dir_fd=parent_fd, follow_symlinks=False)
        identity = lambda item: (item.st_dev, item.st_ino, item.st_mode, item.st_uid,
                                 item.st_nlink, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
        if identity(before) != identity(after) or identity(after) != identity(named):
            raise ProjectionError("profile capture changed while being verified")
        if identity(root_before) != identity(root_after) or identity(root_after) != identity(named_root):
            raise ProjectionError("profile artifact root changed while being verified")
    except OSError as exc:
        raise ProjectionError("profile capture is missing or unsafe") from exc
    finally:
        if fd >= 0:
            os.close(fd)
        if root_fd >= 0:
            os.close(root_fd)
        if parent_fd >= 0:
            os.close(parent_fd)
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ProjectionError("profile capture byte digest differs")
    try:
        body = json.loads(raw, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise ProjectionError("profile capture is not strict JSON") from exc
    return _exact(body, _CAPTURE_FIELDS if fields is None else fields, "profile capture")


def capture_version(phases: Any) -> CaptureVersion:
    """Read the capture version from the record's own perf record commands.

    This is the producer's own discriminator (``"--sample-cpu" in phases[0].tools[0].command``),
    required here to agree across every phase whose record command is readable. A phase whose
    command cannot be read decides nothing: the selected reader's structural checks refuse it
    (with that check's own message), so such a record can never be accepted under either version.
    A record with no readable command is handed to the legacy reader only to be refused there.
    """
    flags = set()
    for phase in phases if isinstance(phases, list) else ():
        tools = phase.get("tools") if isinstance(phase, dict) else None
        record = tools[0] if isinstance(tools, list) and tools else None
        command = record.get("command") if isinstance(record, dict) else None
        if isinstance(command, list):
            flags.add(SAMPLED_CPU_FLAG in command)
    if len(flags) > 1:
        raise ProjectionError("profile capture mixes sampled-CPU and legacy perf record phases")
    return SAMPLED_CPU_CAPTURE if flags == {True} else LEGACY_CAPTURE


def _validate_source(value: Any, version: CaptureVersion = LEGACY_CAPTURE) -> dict:
    source = _exact(value, {"schema", "callables", "files", "python", "constants"},
                    "CPU profile source closure")
    if source["schema"] != CPU_SOURCE_SCHEMA or _digest(source) not in version.bundle_source_digests:
        raise ProjectionError("CPU profile source closure is not the supported producer"
                              + ("" if version is LEGACY_CAPTURE
                                 else f" for capture version {version.name}"))
    constants = source["constants"]
    if (not isinstance(constants, dict) or constants.get("mode") != MODE
            or constants.get("limitations") != list(version.limitations)
            or constants.get("target_tid_limit") != _MAX_TIDS
            or constants.get("limits", {}).get("max_metadata_bytes") != _MAX_CAPTURE_BYTES):
        raise ProjectionError("CPU profile source constants differ")
    return source


def _validate_topology(value: Any) -> dict:
    if value is None:
        raise ProjectionError("sampled CPU topology is absent")
    topology = _exact(value, _TOPOLOGY_FIELDS, "sampled CPU topology")
    if topology["schema"] != TOPOLOGY_SCHEMA:
        raise ProjectionError("sampled CPU topology schema differs")
    cpus = topology["logical_cpus"]
    if (not isinstance(cpus, list) or not cpus or len(cpus) > _MAX_CPU_IDS
            or any(type(item) is not int or item < 0 for item in cpus)
            or cpus != sorted(set(cpus))):
        raise ProjectionError("sampled CPU topology CPU set is malformed or exceeds its bound")
    keys = {str(item) for item in cpus}
    nodes = topology["cpu_to_numa_node"]
    if (not isinstance(nodes, dict) or set(nodes) != keys
            or any(type(item) is not int or item < 0 for item in nodes.values())):
        raise ProjectionError("sampled CPU topology NUMA mapping is malformed")
    siblings, groups = topology["cpu_to_physical_group"], topology["physical_sibling_groups"]
    sibling_error = ProjectionError("sampled CPU topology sibling mapping is malformed")
    if (not isinstance(siblings, dict) or set(siblings) != keys
            or not isinstance(groups, list) or len(groups) > _MAX_CPU_IDS):
        raise sibling_error
    for cpu, group in siblings.items():
        if (not isinstance(group, list) or int(cpu) not in group or group != sorted(set(group))
                or any(type(item) is not int or str(item) not in keys for item in group)):
            raise sibling_error
    # The physical groups partition the logical CPUs and agree with every per-CPU sibling set.
    covered = []
    for group in groups:
        if not isinstance(group, list) or not group or type(group[0]) is not int \
                or siblings.get(str(group[0])) != group:
            raise sibling_error
        covered.extend(group)
    if sorted(covered) != cpus:
        raise sibling_error
    _sha(topology["topology_digest"], "sampled CPU topology digest")
    if topology["topology_digest"] != _digest(
            {key: item for key, item in topology.items() if key != "topology_digest"}):
        raise ProjectionError("sampled CPU topology digest does not rederive")
    return topology


def _validate_locations(samples: dict, tids: list, topology: dict) -> None:
    rows = samples["location_periods"]
    if not isinstance(rows, list) or not rows or len(rows) > _MAX_LOCATION_GROUPS:
        raise ProjectionError("sampled CPU location table exceeds its bound")
    nodes, members = topology["cpu_to_numa_node"], set(tids)
    keys, by_tid, total = [], {}, 0
    for row in rows:
        _exact(row, _LOCATION_FIELDS, "sampled CPU location period")
        tid = _integer(row["tid"], "sampled location TID", minimum=1)
        cpu = _integer(row["cpu"], "sampled location CPU")
        period = _integer(row["period"], "sampled location period", minimum=1)
        family = _text(row["family"], "sampled location family")
        if tid not in members or nodes.get(str(cpu)) != row["numa_node"] \
                or type(row["numa_node"]) is not int:
            raise ProjectionError("sampled CPU location differs from its captured topology/TIDs")
        keys.append((tid, cpu, row["numa_node"], family))
        by_tid[str(tid)] = by_tid.get(str(tid), 0) + period
        total += period
    if keys != sorted(set(keys)):
        raise ProjectionError("sampled CPU location table order/uniqueness differs")
    if total != samples["sampled_period_total"] or by_tid != samples["tid_periods"]:
        raise ProjectionError("sampled CPU location periods do not rederive")


def _validate_sampled_cpu_phase(phase: dict) -> dict:
    parser = phase["parser"]
    command = parser.get("command") if isinstance(parser, dict) else None
    if (not isinstance(command, list) or "-F" not in command
            or command.index("-F") + 1 >= len(command)
            or command[command.index("-F") + 1] != SAMPLED_CPU_SCRIPT_FIELDS):
        raise ProjectionError("sampled CPU perf script fields differ from its record command")
    topology = _validate_topology(phase["topology"])
    _validate_locations(phase["samples"], phase["tids"], topology)
    return topology


def _validate_phase(value: Any, expected_phase: str, raw_limit: int,
                    version: CaptureVersion = LEGACY_CAPTURE) -> dict:
    if version.sampled_cpu and isinstance(value, dict) and value.get("topology") is None:
        raise ProjectionError("sampled CPU topology is absent")
    phase = _exact(value, set(version.phase_fields), f"{expected_phase} phase")
    if phase["phase"] != expected_phase:
        raise ProjectionError("profile capture phase order differs")
    interval = phase["enabled_interval"]
    if (not isinstance(interval, list) or len(interval) != 2
            or any(_finite(item, "profile enabled interval") != item for item in interval)
            or interval != sorted(interval)):
        raise ProjectionError("profile enabled interval is invalid")
    tids = phase["tids"]
    if (not isinstance(tids, list) or len(tids) > _MAX_TIDS
            or any(type(item) is not int or item < 1 for item in tids)
            or tids != sorted(set(tids))):
        raise ProjectionError("profile target TID set exceeds its bound")
    tools = phase["tools"]
    if (not isinstance(tools, list) or len(tools) != 2
            or any(not isinstance(item, dict) for item in tools)
            or [item.get("kind") for item in tools] != ["record", "stat"]):
        raise ProjectionError("profile tool cardinality/order differs")
    for tool in tools:
        _exact(tool, _TOOL_FIELDS, "profile tool")
        if tool["returncode"] != 0 or not isinstance(tool["stderr"], str):
            raise ProjectionError("profile tool terminal differs")
        if (not isinstance(tool["command"], list) or not tool["command"]
                or any(not isinstance(item, str) or not item for item in tool["command"])):
            raise ProjectionError("profile tool command is malformed")
        controls = tool["controls"]
        if (not isinstance(controls, list) or len(controls) != 2
                or any(not isinstance(item, dict) for item in controls)
                or [item.get("command") for item in controls] != ["enable", "disable"]):
            raise ProjectionError("profile tool control order differs")
        for control in controls:
            _exact(control, {"command", "sent", "acknowledged"}, "profile tool control")
            _finite(control["sent"], "profile tool control timestamp")
            _finite(control["acknowledged"], "profile tool acknowledgement")
        artifact = _exact(tool["artifact"], _ARTIFACT_FIELDS, "profile raw artifact reference")
        _text(artifact["path"], "profile raw artifact path")
        _sha(artifact["sha256"], "profile raw artifact digest")
        for name in ("size", "dev", "ino", "mtime_ns", "ctime_ns"):
            _integer(artifact[name], f"profile raw artifact {name}")
        if artifact["size"] > raw_limit:
            raise ProjectionError("profile raw artifact exceeds producer bound")
    samples = _exact(phase["samples"], set(version.sample_fields), "profile sample reduction")
    _integer(samples["samples"], "profile samples", minimum=1)
    total = _integer(samples["sampled_period_total"], "sampled period total", minimum=1)
    _integer(samples["outside_request_samples"], "outside-request samples")
    if samples["lost_records"] != "not_independently_quantified":
        _integer(samples["lost_records"], "lost profile records")
    symbols = samples["symbol_periods"]
    if not isinstance(symbols, list) or len(symbols) > _MAX_SYMBOLS:
        raise ProjectionError("profile symbol table exceeds its bound")
    symbol_total = 0
    for item in symbols:
        _exact(item, {"dso", "symbol", "period"}, "profile symbol")
        _text(item["dso"], "profile symbol DSO")
        _text(item["symbol"], "profile symbol name")
        symbol_total += _integer(item["period"], "profile symbol period", minimum=1)
    periods = samples["tid_periods"]
    if (not isinstance(periods, dict) or len(periods) > _MAX_TIDS
            or not periods or not set(periods).issubset({str(item) for item in tids})):
        raise ProjectionError("profile reduced TID set differs")
    tid_total = sum(_integer(item, "profile TID period", minimum=1)
                    for item in periods.values())
    if symbol_total != total or tid_total != total:
        raise ProjectionError("profile period totals do not rederive")
    if version.sampled_cpu:
        _validate_sampled_cpu_phase(phase)
    return phase


def joined_journal_pair(native: Any) -> tuple[dict, dict]:
    """Validate the exact durable publication/terminal join without artifact I/O."""
    bundle = _exact(native, {"terminal", "profile"}, "profile evidence bundle")
    terminal_envelope, terminal = _envelope(bundle["terminal"], LIFECYCLE_KIND,
                                             "profile terminal envelope")
    profile_envelope, profile = _envelope(bundle["profile"], PROFILE_KIND,
                                           "profile publication envelope")
    _exact(terminal, _LIFECYCLE_FIELDS, "profile terminal")
    _exact(profile, _PROFILE_FIELDS, "profile publication")
    data = terminal.get("data")
    if (not isinstance(data, dict)
            or terminal["schema"] != LIFECYCLE_SCHEMA
            or terminal["event"] != "WORKER_RESULT_ACCEPTED"
            or data != {"result_digest": data.get("result_digest"),
                                     "accepted": True, "reason": None}):
        raise ProjectionError("profile terminal is not an original accepted worker result")
    _sha(terminal["data"]["result_digest"], "terminal result digest")
    if profile["schema"] != PROFILE_SCHEMA or profile["event"] != "PROFILE_VERIFIED":
        raise ProjectionError("profile publication schema/event differs")
    request_digest = _digest(profile["profile_request"])
    worker_ref = f"controller-worker:{terminal['worker_id']}:{terminal['worker_generation']}"
    request_id = "profile-" + request_digest[:24]
    stage_id = "target-profile-" + request_digest[:24]
    shared = ("campaign_id", "config_digest", "config_generation", "supervisor_id",
              "supervisor_incarnation", "control_revision")
    if (profile_envelope["campaign_id"] != profile["campaign_id"]
            or terminal_envelope["campaign_id"] != terminal["campaign_id"]
            or any(profile[name] != terminal[name] for name in shared)
            or profile["profile_request_digest"] != request_digest
            or profile["verifier_ref"] != worker_ref
            or terminal["request_id"] != request_id or terminal["stage_id"] != stage_id
            or terminal["plan_digest"] != profile["stage_plan_digest"]
            or terminal["lineage_id"] != profile["transition_id"]):
        raise ProjectionError("profile publication and original terminal identity differ")
    for name in ("catalog_id", "transition_id", "stage_plan_digest", "profile_request_digest",
                 "target_revision_digest", "target_profile_digest", "config_digest"):
        _sha(profile[name], f"profile.{name}")
    if profile_envelope["record_id"] != profile["target_profile_digest"]:
        raise ProjectionError("profile publication record identity differs")
    return profile, terminal


def _validate_bundle(native: Any, *, corpus_root: Path
                     ) -> tuple[dict, dict, dict, dict, dict, CaptureVersion]:
    profile, terminal = joined_journal_pair(native)
    request_digest = profile["profile_request_digest"]
    content = _exact(profile["profile_content"], _PROFILE_CONTENT_FIELDS, "target profile")
    loaded = profile["loaded_identity"]
    if not isinstance(loaded, dict):
        raise ProjectionError("profile loaded identity must be an object")
    if (content["schema"] != "epyc.autokernel.target_profile.v1"
            or content["target_revision_digest"] != profile["target_revision_digest"]
            or content["freshness"] != "fresh" or content["observation_states"] != ["unknown"]
            or content["opportunities"] != [] or content["quant"] != loaded.get("quantization")
            or content["kept_scope"] not in [[MODE, *item.limitations] for item in CAPTURE_VERSIONS]):
        raise ProjectionError("target profile exceeds the original CPU observation scope")
    expected_profile_digest = _digest({"profile_content": content,
                                       "loaded_identity": profile["loaded_identity"],
                                       "artifact_identity": profile["artifact_identity"]})
    if expected_profile_digest != profile["target_profile_digest"]:
        raise ProjectionError("target profile digest does not rederive")
    capture = _artifact(Path(corpus_root), profile["artifact_identity"])
    version = capture_version(capture["phases"])
    if content["kept_scope"] != [MODE, *version.limitations]:
        raise ProjectionError("target profile exceeds the original CPU observation scope")
    _validate_source(capture["source_closure"], version)
    if (capture["schema"] != CAPTURE_SCHEMA or capture["completion"] != "complete"
            or capture["request_digest"] != request_digest
            or capture["target_revision_digest"] != profile["target_revision_digest"]
            or capture["loaded_identity"] != profile["loaded_identity"]
            or capture["limitations"] != list(version.limitations)):
        raise ProjectionError("profile capture differs from original publication")
    phases = capture["phases"]
    if not isinstance(phases, list) or len(phases) != 2:
        raise ProjectionError("profile capture phase cardinality/order differs")
    raw_limit = capture["source_closure"]["constants"]["limits"]["max_raw_file_bytes"]
    _integer(raw_limit, "profile raw artifact limit", minimum=1)
    _validate_phase(phases[0], "warmup", raw_limit, version)
    measured = _validate_phase(phases[1], "measurement", raw_limit, version)["samples"]
    sampled = measured["sampled_period_total"]
    symbols = measured["symbol_periods"]
    hotspots = [item["dso"] + ":" + item["symbol"]
                for item in sorted(symbols, key=lambda item: (-item["period"], item["dso"], item["symbol"]))]
    if content["hotspots"] != hotspots:
        raise ProjectionError("target profile hotspots do not rederive")
    carrier = _exact(profile["measurement_carrier"], {"schema", "profile_source_id",
        "validation_source_id", "run_id", "profile_claim_tuple", "validation_claim_tuple"},
        "profile measurement carrier")
    run_id = "cpu-profile:" + request_digest
    if (carrier["schema"] != CARRIER_SCHEMA or carrier["profile_source_id"] != PROFILE_SOURCE_ID
            or carrier["validation_source_id"] != VALIDATION_SOURCE_ID
            or carrier["run_id"] != run_id):
        raise ProjectionError("profile measurement carrier identity differs")
    profile_tuple = _exact(carrier["profile_claim_tuple"], _PROFILE_TUPLE_FIELDS,
                           "profile measurement tuple")
    validation_tuple = _exact(carrier["validation_claim_tuple"], _VALIDATION_TUPLE_FIELDS,
                              "profile integrity tuple")
    common = {"category": "CANDIDATE", "protocol_id": "", "reps": 1,
              "reps_basis": "one completed profiled request; samples are not repetitions",
              "attestation_locator": profile["artifact_identity"]["locator"],
              "attestation_sha256": profile["artifact_identity"]["sha256"],
              "attestation_present": True, "attestation_verified": True}
    try:
        date.fromisoformat(profile_tuple["date"])
    except (TypeError, ValueError) as exc:
        raise ProjectionError("profile tuple date is invalid") from exc
    if validation_tuple.get("date") != profile_tuple["date"]:
        raise ProjectionError("profile tuple dates differ")
    expected_profile = {**common, "date": profile_tuple["date"],
        "measurement_id": run_id + ":profile", "metric": "request_sampled_period_total",
        "value": sampled, "metric_direction": "lower_better",
        "unit": "sampled user-cycle periods",
        "claim": "Recorded sampled-period total for this exact full request; estimated attribution, not exact CPU cost",
        "source_class": "measurement", "extra": {"limitations": list(version.limitations)}}
    expected_validation = {**common, "date": profile_tuple["date"],
        "measurement_id": run_id + ":integrity", "metric": "original_profile_receipt_integrity",
        "value": 1, "metric_direction": "higher_better", "unit": "checked proposition",
        "claim": PROPOSITION, "decided_proposition": PROPOSITION, "source_class": "verifier",
        "binding_kind": "identity",
        "extra": {"not_model_correctness": True, "not_trial_validation": True}}
    if profile_tuple != expected_profile or validation_tuple != expected_validation:
        raise ProjectionError("producer-authored profile tuples do not rederive")
    return profile, terminal, capture, profile_tuple, validation_tuple, version


def _sampled_cpu_projection(phases: list, version: CaptureVersion) -> dict:
    """Projection fields that exist only because the capture sampled CPUs (none for legacy)."""
    if not version.sampled_cpu:
        return {}
    return {"capture_version": version.name,
            "sampled_cpu_topology_digests": [item["topology"]["topology_digest"]
                                             for item in phases]}


def _loop_rows(native: Any, *, corpus_root: Path) -> tuple[dict]:
    record = _exact(native, {"schema", "mode", "capture", "source_id", "run_id",
                             "profile_claim_tuple"}, "direct loop profile")
    if (record["schema"] != LOOP_PROFILE_SCHEMA or record["mode"] != LOOP_MODE
            or record["source_id"] != PROFILE_SOURCE_ID):
        raise ProjectionError("direct loop profile identity differs")
    body = _artifact(corpus_root, record["capture"], fields={"schema", "request", "settings",
        "profiler", "processes", "phases", "completion", "limitations"})
    version = capture_version(body["phases"])
    if (body["schema"] != LOOP_CAPTURE_SCHEMA or body["completion"] != "complete"
            or body["limitations"] != list(version.limitations)):
        raise ProjectionError("direct loop capture identity/scope differs")
    settings = _exact(body["settings"], {"resolved_recipe", "prompt_manifest", "profiler",
                                       "source_closure", "budgets"}, "direct capture settings")
    source_digest = _digest(settings["source_closure"])
    if source_digest not in version.loop_source_digests:
        raise ProjectionError("direct CPU profile source closure differs"
                              + ("" if version is LEGACY_CAPTURE
                                 else f" for capture version {version.name}"))
    request = _exact(body["request"], {"mode", "execution_digest", "prompt_manifest_digest",
        "producer_pid", "started_monotonic_ns"}, "direct original request identity")
    recipe, prompts = settings["resolved_recipe"], settings["prompt_manifest"]
    if (not isinstance(recipe, dict) or not isinstance(prompts, dict)
            or request["mode"] != LOOP_MODE or recipe.get("backend") != "cpu"
            or request["execution_digest"] != recipe.get("execution_digest")
            or request["prompt_manifest_digest"] != prompts.get("digest")
            or prompts.get("digest") != _digest({k: v for k, v in prompts.items() if k != "digest"})):
        raise ProjectionError("direct original workload identity differs")
    _integer(request["producer_pid"], "direct producer PID", minimum=1)
    _integer(request["started_monotonic_ns"], "direct start", minimum=1)
    members = prompts.get("prompts")
    phases = body["phases"]
    if not isinstance(members, list) or len(members) != 1 or not isinstance(phases, list) or len(phases) != 2:
        raise ProjectionError("direct profile requires one request and two original phases")
    processes = _exact(body["processes"], {"producer", "ancestor", "server"}, "direct processes")
    if (processes["producer"].get("pid") != request["producer_pid"]
            or processes["server"].get("ppid") != request["producer_pid"]):
        raise ProjectionError("direct original process ownership differs")
    for value, phase_name in zip(phases, ("warmup", "measurement")):
        phase = _validate_phase(value, phase_name, 128 * 1024**2, version)
        response = phase["response"]
        try:
            raw = bytes.fromhex(response["request_hex"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ProjectionError("direct original request bytes malformed") from exc
        if (response.get("phase") != phase_name or response.get("slot") != 0
                or response.get("prompt_id") != members[0].get("prompt_id")
                or hashlib.sha256(raw).hexdigest() != members[0].get("request_digest")
                or response.get("error") is not None or response.get("response_hex") is None):
            raise ProjectionError("direct original response/request join differs")
        if not phase["enabled_interval"][0] <= _finite(response["start"], "request start") <= _finite(
                response["end"], "request end") <= phase["enabled_interval"][1]:
            raise ProjectionError("direct original request window differs")
    run_id = "loop-cpu-profile:" + _digest(request)
    claim = _exact(record["profile_claim_tuple"], _PROFILE_TUPLE_FIELDS, "direct profile claim")
    try:
        date.fromisoformat(claim["date"])
    except (ValueError, TypeError) as exc:
        raise ProjectionError("direct profile date malformed") from exc
    expected = {"date": claim["date"], "category": "CANDIDATE", "protocol_id": "", "reps": 1,
        "reps_basis": "one completed profiled request; samples are not repetitions",
        "attestation_locator": record["capture"]["locator"],
        "attestation_sha256": record["capture"]["sha256"],
        "attestation_present": True, "attestation_verified": True,
        "measurement_id": run_id + ":profile", "metric": "request_sampled_period_total",
        "value": phases[1]["samples"]["sampled_period_total"], "metric_direction": "lower_better",
        "unit": "sampled user-cycle periods",
        "claim": "Recorded sampled-period total for this exact full request; estimated attribution, not exact CPU cost",
        "source_class": "measurement", "extra": {"limitations": list(version.limitations),
            "mode": LOOP_MODE, "not_performance_comparison": True,
            "model_inventory_verification": "not performed by direct profiler"}}
    if record["run_id"] != run_id or claim != expected:
        raise ProjectionError("direct producer-authored measurement differs")
    return ({"native": native, "corpus_root": str(Path(corpus_root).absolute()),
        "projection": "loop_profile", "claim": claim,
        "capture_source_digest": source_digest,
        "execution_digest": request["execution_digest"],
        "prompt_manifest_digest": request["prompt_manifest_digest"],
        **_sampled_cpu_projection(phases, version)},)


def native_rows(native: Any, *, corpus_root: Path) -> tuple[dict, ...]:
    if isinstance(native, dict) and native.get("schema") == LOOP_PROFILE_SCHEMA:
        return _loop_rows(native, corpus_root=corpus_root)
    profile, terminal, capture, profile_tuple, validation_tuple, version = _validate_bundle(
        native, corpus_root=corpus_root)
    shared = {"native": native, "corpus_root": str(Path(corpus_root).absolute()),
              "profile_event_digest": _digest(profile),
              "terminal_result_digest": terminal["data"]["result_digest"],
              "capture_source_digest": _digest(capture["source_closure"]),
              **_sampled_cpu_projection(capture["phases"], version)}
    return ({**shared, "projection": "profile", "claim": profile_tuple},
            {**shared, "projection": "integrity", "claim": validation_tuple})


_SAMPLED_CPU_ROW_KEYS = ("capture_version", "sampled_cpu_topology_digests")


def _sampled_cpu_extra(row: dict) -> dict:
    return {key: row[key] for key in _SAMPLED_CPU_ROW_KEYS if key in row}


def _base_claim(native: Any, expected: str) -> tuple[dict, dict, dict]:
    if not isinstance(native, dict) or native.get("projection") != expected:
        raise ProjectionError(f"CPU profile {expected} row is malformed")
    rows = native_rows(native.get("native"), corpus_root=Path(str(native.get("corpus_root", ""))))
    row = rows[0 if expected == "profile" else 1]
    for key in ("profile_event_digest", "terminal_result_digest", "capture_source_digest", "claim",
                *_SAMPLED_CPU_ROW_KEYS):
        if native.get(key) != row.get(key):
            raise ProjectionError(f"CPU profile {expected} row mutated {key}")
    return native["claim"], native["native"]["profile"]["payload"], row


@register("autokernel-unified-profile-measurement")
def project_profile(native: Any) -> ClaimTuple:
    if isinstance(native, dict) and native.get("projection") == "loop_profile":
        rows = _loop_rows(native.get("native"), corpus_root=Path(str(native.get("corpus_root", ""))))
        if native != rows[0]:
            raise ProjectionError("direct profile projected row changed")
        values = dict(native["claim"])
        values["extra"] = {**values["extra"], "applicability": "profile_observation_only",
            "not_production_validation": True, "not_profile_verified": True,
            "execution_digest": native["execution_digest"],
            "prompt_manifest_digest": native["prompt_manifest_digest"],
            "capture_source_digest": native["capture_source_digest"],
            **_sampled_cpu_extra(native)}
        return ClaimTuple(**values, source_kind="autokernel-unified-profile-measurement")
    claim, event, row = _base_claim(native, "profile")
    extra = {**claim["extra"], "profile_event_digest": row["profile_event_digest"],
             "terminal_result_digest": row["terminal_result_digest"],
             "target_revision_digest": event["target_revision_digest"],
             "loaded_identity": event["loaded_identity"],
             "capture_source_digest": row["capture_source_digest"],
             "applicability": "profile_observation_only",
             "not_performance_comparison": True, "not_production_validation": True,
             **_sampled_cpu_extra(row)}
    values = dict(claim)
    values["extra"] = extra
    values.pop("attestation_verified")
    return ClaimTuple(**values, attestation_verified=True,
                      source_kind="autokernel-unified-profile-measurement")


@register("autokernel-unified-profile-integrity", source_class="verifier",
          decided_proposition_field="decided_proposition")
def project_integrity(native: Any) -> ClaimTuple:
    claim, event, row = _base_claim(native, "integrity")
    extra = {**claim["extra"], "profile_event_digest": row["profile_event_digest"],
             "terminal_result_digest": row["terminal_result_digest"],
             "target_revision_digest": event["target_revision_digest"],
             "loaded_identity": event["loaded_identity"],
             "capture_source_digest": row["capture_source_digest"],
             "applicability": "profile_receipt_integrity_only",
             "not_performance_comparison": True, "not_production_validation": True,
             **_sampled_cpu_extra(row)}
    values = dict(claim)
    values["extra"] = extra
    values.pop("attestation_verified")
    return ClaimTuple(**values, attestation_verified=True,
                      source_kind="autokernel-unified-profile-integrity")


def project_journal_pair(native: Any, *, corpus_root: Path) -> tuple[ClaimTuple, ClaimTuple]:
    rows = native_rows(native, corpus_root=corpus_root)
    return project_profile(rows[0]), project_integrity(rows[1])


def project(native: Any) -> ClaimTuple:
    """Corpus route for the direct measurement only; no new grading or verifier."""
    return project_profile(native)


__all__ = ["ADAPTER_ID", "CAPTURE_SCHEMA", "CAPTURE_VERSIONS", "CARRIER_SCHEMA",
           "CPU_SOURCE_DIGEST", "LEGACY_CAPTURE", "LIFECYCLE_KIND", "PROFILE_KIND",
           "SAMPLED_CPU_CAPTURE", "capture_version", "joined_journal_pair", "native_rows",
           "project_integrity", "project_journal_pair", "project_profile"]
