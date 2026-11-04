"""Independent replay checks for CH-26 native observer loss/coverage receipts.

This verifies packet consistency and the documented perf counter/ring fields.
It does not authenticate the producer or kernel semantics and never admits a
measurement, placement, or contention claim.
"""
from __future__ import annotations

import base64
import hashlib
import struct

from perf_ring import decode

EVENTS = frozenset(("sched_switch", "irq_handler_entry", "irq_handler_exit",
                    "softirq_entry", "softirq_exit"))


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _raw_ring(row):
    ring = row.get("ring")
    _require(isinstance(ring, dict), "ring object missing")
    snap = ring.get("snapshot")
    if isinstance(snap, dict) and snap.get("encoding") == "base64":
        try:
            snap = base64.b64decode(snap["data"], validate=True)
        except (KeyError, ValueError) as exc:
            raise ValueError("invalid base64 ring snapshot") from exc
    _require(isinstance(snap, bytes), "raw ring snapshot missing")
    return ring, snap


def verify(document, *, expected_cpus, expected_events=EVENTS):
    """Replay exact source inventory, every ring interval, and terminal counters.

    Expected CPU set is supplied by the caller from the declared request. The
    report remains diagnostic even on PASS because the producer/kernel trust
    boundary and meaning of perf's loss/counter fields are outside this check.
    """
    _require(isinstance(expected_cpus, (set, frozenset)) and expected_cpus
             and all(type(c) is int and c >= 0 for c in expected_cpus),
             "exact expected CPU set required")
    _require(isinstance(document, dict), "evidence object required")
    _require(document.get("measurement_admission") == "none", "admission field changed")
    _require(document.get("errors") == [], "producer reported errors")
    markers = document.get("markers")
    _require(isinstance(markers, list) and len(markers) == 2, "marker pair missing")
    begin, end = markers
    _require(type(begin.get("timestamp_ns")) is int and type(end.get("timestamp_ns")) is int
             and 0 < begin["timestamp_ns"] < end["timestamp_ns"], "invalid request window")
    window = (begin["timestamp_ns"], end["timestamp_ns"])

    _require(isinstance(expected_events, (set, frozenset)) and expected_events
             and all(isinstance(e, str) and e for e in expected_events),
             "exact expected event set required")
    expected = {(cpu, event) for cpu in expected_cpus for event in expected_events}
    sources = document.get("source_provenance")
    _require(isinstance(sources, list) and len(sources) == len(expected), "source inventory size")
    by_id = {}
    for source in sources:
        _require(isinstance(source, dict), "source receipt malformed")
        pair = (source.get("cpu"), source.get("name"))
        _require(pair in expected, "unexpected CPU/event source")
        eid = source.get("event_id")
        _require(type(eid) is int and eid > 0 and eid not in by_id, "duplicate/invalid event ID")
        _require(type(source.get("tracepoint_id")) is int and source["tracepoint_id"] > 0,
                 "tracepoint ID missing")
        by_id[eid] = source
    _require({(s["cpu"], s["name"]) for s in sources} == expected, "CPU/event coverage gap")

    snapshots = document.get("snapshots")
    terminal = document.get("rings")
    _require(isinstance(snapshots, list) and snapshots, "ring snapshots missing")
    _require(isinstance(terminal, list) and len(terminal) == len(expected), "terminal ring inventory")
    expected_tail = {eid: 0 for eid in by_id}
    prior_head = {eid: 0 for eid in by_id}
    sample_counts = {eid: 0 for eid in by_id}
    last_snapshot = {}

    for item in snapshots:
        _require(isinstance(item, dict), "snapshot row malformed")
        eid = item.get("event_id")
        source = by_id.get(eid)
        _require(source is not None and item.get("cpu") == source["cpu"]
                 and item.get("name") == source["name"], "snapshot source identity mismatch")
        ring, raw = _raw_ring(item)
        _require(ring.get("errors") == [], "producer ring error/loss indication")
        tail, head = ring.get("tail"), ring.get("head")
        _require(type(tail) is int and type(head) is int, "ring positions missing")
        _require(tail == expected_tail[eid] and head >= prior_head[eid],
                 "ring sequence gap, overlap, or head regression")
        parsed = decode(raw, head=head, tail=tail)
        _require(parsed.get("errors") == [] and parsed.get("new_tail") == head,
                 "raw ring has loss, malformed data, or incomplete drain")
        for event in parsed["events"]:
            _require(event.get("type") == "sample", "loss/throttle/unknown ring record")
            body = event.get("body")
            _require(isinstance(body, bytes) and len(body) >= 54, "short perf sample")
            ident, _, _, _, stamp, cpu, reserved, period, rawsize = struct.unpack_from("=QQIIQIIQI", body)
            _require(ident == eid and cpu == source["cpu"] and reserved == 0 and period == 1
                     and type(stamp) is int and stamp > 0 and rawsize >= 2
                     and rawsize <= len(body) - 52, "sample identity/layout mismatch")
            tracepoint = struct.unpack_from("=H", body, 52)[0]
            _require(tracepoint == source["tracepoint_id"], "sample tracepoint ID mismatch")
            sample_counts[eid] += 1
        expected_tail[eid] = head
        prior_head[eid] = head
        last_snapshot[eid] = (head, tail, hashlib.sha256(raw).hexdigest())

    seen_terminal = set()
    for row in terminal:
        _require(isinstance(row, dict), "terminal ring row malformed")
        eid = row.get("event_id")
        source = by_id.get(eid)
        _require(source is not None and eid not in seen_terminal and row.get("cpu") == source["cpu"]
                 and row.get("name") == source["name"], "terminal source identity mismatch")
        seen_terminal.add(eid)
        _require(row.get("errors") == [] and row.get("lost_samples") == 0,
                 "terminal loss/error field nonzero")
        for key in ("enable_after_ns", "disable_before_ns", "enabled_ns", "running_ns", "count"):
            _require(type(row.get(key)) is int, "terminal counter field missing: " + key)
        _require(row["enable_after_ns"] <= window[0] < window[1] <= row["disable_before_ns"],
                 "request window outside conservative perf enable interval")
        _require(row["enabled_ns"] > 0 and row["running_ns"] == row["enabled_ns"],
                 "counter does not show continuous enabled/running interval")
        _require(row["count"] == sample_counts[eid], "counter/sample count disagreement")
        ring, raw = _raw_ring(row)
        _require(ring.get("errors") == [], "terminal producer ring error")
        parsed = decode(raw, head=ring.get("head"), tail=ring.get("tail"))
        _require(parsed.get("errors") == [] and parsed.get("new_tail") == ring.get("head"),
                 "terminal raw ring did not decode completely")
        _require(last_snapshot.get(eid) == (ring.get("head"), ring.get("tail"), hashlib.sha256(raw).hexdigest()),
                 "terminal ring differs from final retained snapshot")
    _require(seen_terminal == set(by_id), "terminal source coverage gap")
    return {"schema": "epyc.ch26.loss-coverage-replay.v1", "status": "structural_pass",
            "source_count": len(expected), "ring_snapshots": len(snapshots),
            "request_window_ns": list(window), "measurement_admission": "none",
            "losslessness": "unproven", "coverage": "unproven",
            "limitations": ["producer and kernel are not independently authenticated",
                            "perf loss/counter semantics are assumed, not validated",
                            "structural continuity does not prove all CPUs were serviced",
                            "does not prove continuous execution placement or absence of competing inference"]}
