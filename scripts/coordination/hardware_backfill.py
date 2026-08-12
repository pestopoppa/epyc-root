#!/usr/bin/env python3
"""hardware_backfill.py — bounded backfill queue runner + queue-empty detector.

WHY (task hardware-idle-supervisor, verified at source 2026-08-12). On the
overnight run, 19 READY compute-gated tasks existed, nothing translated them
into queued jobs, the hardware sat idle 3h47m, and the daemon wrote 590
consecutive all-idle records into coordination/session-bus/advisory.jsonl —
which nothing reads. The gap was never "no detector"; it was "nothing turns
READY work into something that actually claims CPU, and nothing surfaces the
gap to somewhere a human or agent will see it."

DESIGN: the detector below watches the QUEUE (this file's own queue.jsonl),
NOT the hardware. Hardware occupancy is `region-lock status`'s business and
is inherently racy to poll from outside; queue depth is a fact this process
owns outright. "Queue empty while READY work is known to exist" is the
signal that matters — it means the translation step (READY task -> queued
backfill spec) isn't happening, which is exactly 2026-08-11's failure mode.

BOUNDED RUNTIME IS THE OWNER-PRESSURE MITIGATION, not a nicety. Every job
this runner launches goes through `region-lock run --timeout-s 0`, which
blocks in a ~50ms poll loop and admits the instant its regions free — so if
a real inference owner ever drops a region between campaign legs, a queued
backfill job can slip in and start occupying it almost immediately. That is
fine IF the job is bounded: the `timeout(1)` wrapper below is MANDATORY, and
`validate_spec` REFUSES any job spec without `max_runtime_s`, or with
`max_runtime_s > MAX_RUNTIME_S_CEILING` (3600s). This runner depends on the
standing fleet rule that makes that safe: the 2026-07-27 no-concurrent-
inference amendment, under which the compute owner holds its CPU-region
claim for the WHOLE campaign, not per individual run. Because the owner's
claim persists across legs, this runner can only ever wedge itself into a
gap the owner voluntarily released — and because every job it runs is
`timeout`-bounded to at most one hour, the worst-case wait that imposes on
that owner reclaiming the region is exactly ONE bounded backfill job, never
an unbounded one and never a queue of them (the concurrency cap plus
per-job bound compose: at most `max_concurrent` jobs, each capped at
`MAX_RUNTIME_S_CEILING`).

WHAT THIS RUNNER NEVER DOES: it never claims a region for itself (every
region-lock acquisition happens inside the `region-lock run` subprocess it
launches, which is the SAME lock implementation the rest of the fleet uses —
see epyc-orchestrator/src/runtime/cpu_region_lock.py); it never touches GPU
(the region set is validated against CPU-quarter ids only, `VALID_REGIONS`
below); and it never preempts anything — it only ever wraps `region-lock
run`, which waits its turn exactly like any other caller.

FAIL-CLOSED CONTRACT. Every unknown fails closed, never toward "empty" or
"safe to act":
  * queue.jsonl or done.jsonl EXISTS but cannot be read/parsed at the file
    level -> depth is UNKNOWN (None), dispatch is skipped this tick, and the
    detector's streak counter is left untouched (never incremented, never
    reset) rather than inferring emptiness from a read error. A genuinely
    MISSING file is the one legitimate "empty" reading (nothing has ever
    been written there).
  * ready_hint.txt exists but cannot be read -> no finding is emitted this
    check; a genuinely missing or empty hint file means "no known READY
    work", also no finding.
  * the session_bus append call fails (non-roster agent, daemon down,
    whatever) -> logged locally to LOG_FILE and the runner keeps going; the
    dedup state is NOT updated on failure, so the next detector check
    retries rather than silently giving up.

DEDUP / ANTI-590-RECORDS DESIGN. The detector emits at most once per
UNBROKEN (sustained-empty-streak, hint-content) pair: reaching the
threshold with a given hint content emits once, then holds — no further
bus writes — until either the queue is observed non-empty again (streak
resets) or the hint content changes. That is the fix for the 590-records
failure: writing an identical record every poll into a file nobody reads is
not a detector, it's a firehose. One row, addressed via needs_routing_to,
is the whole point.

TEST SEAMS (both documented here so tests never touch real fleet state):
  * `HARDWARE_BACKFILL_REGION_LOCK_BIN` env var overrides the path to the
    `region-lock` executable used to build launch commands. Tests point this
    at a throwaway shim that execs its trailing `-- <cmd>` directly, so no
    test ever touches the real cpu_region.occupancy.json.
  * `BackfillRunner(..., bus_emit_fn=<callable>)` overrides how the detector
    attempts to deliver its finding. The callable takes the message dict and
    returns True/False (success/failure); the default
    (`_default_bus_emit`) shells out to `session_bus.py append`. Tests pass
    a stub so dedup/retry logic is exercised deterministically without
    depending on the live roster (as of this writing, `hardware-backfill`
    is NOT a roster id in coordination/session-bus/config.yaml, so the real
    call fails closed by design — see the runner's own header note in the
    committed README for the follow-up this implies).

Usage:
    hardware_backfill.py run  [--queue-dir DIR] [--max-concurrent N]
                               [--tick-interval-s S] [--detector-interval-s S]
                               [--detector-threshold M]
    hardware_backfill.py once [same flags]   # single reap+dispatch+detector pass

Queue spec shape (one JSON object per line in queue.jsonl — see
coordination/backfill/README.md for the authored contract):
    {"id": "...", "regions": ["q2"], "role": "backfill-<name>",
     "cmd": [...], "max_runtime_s": N, "enqueued_by": "...", "ts": "..."}
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUEUE_DIR = REPO_ROOT / "coordination" / "backfill"
SESSION_BUS_PY = REPO_ROOT / "scripts" / "coordination" / "session_bus.py"
LOG_FILE = REPO_ROOT / "logs" / "hardware_backfill.log"

DEFAULT_REGION_LOCK_BIN = "/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock"
AGENT_ID = "hardware-backfill"

# CPU quarters ONLY — there is no GPU region (verified at source, task brief).
VALID_REGIONS = frozenset({"q0", "q1", "q2", "q3"})

MAX_RUNTIME_S_CEILING = 3600
REQUIRED_FIELDS = ("id", "regions", "role", "cmd", "max_runtime_s", "enqueued_by", "ts")
# Never a real serving-role name: attribution in region-lock's payload must be
# unmistakably a backfill job, not confusable with a stack role.
ROLE_RE = re.compile(r"^backfill-[A-Za-z0-9_.-]+$")

DEFAULT_MAX_CONCURRENT = 2
DEFAULT_TICK_INTERVAL_S = 5.0
DEFAULT_DETECTOR_INTERVAL_S = 300.0
DEFAULT_DETECTOR_THRESHOLD = 3


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path, default: object) -> object:
    """Best-effort JSON read. Returns `default` for a MISSING file (legitimate
    empty state) and raises OSError/ValueError for a present-but-broken one so
    callers can tell the two apart and fail closed on the latter."""
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


class QueueUnreadable(RuntimeError):
    """queue.jsonl or done.jsonl exists but could not be read — fail closed."""


# --------------------------------------------------------------------- spec validation


def validate_spec(obj: object) -> tuple[bool, str]:
    """Pure validation of one queue-line JSON object. Returns (ok, reason).

    Refuses ANY spec without a numeric `max_runtime_s` in (0, MAX_RUNTIME_S_CEILING] —
    this is the bounded-runtime owner-pressure mitigation described in the module
    header, and it is refused here, at parse time, never merely warned about.
    """
    if not isinstance(obj, dict):
        return False, "spec is not a JSON object"

    missing = [f for f in REQUIRED_FIELDS if f not in obj]
    if missing:
        return False, f"missing required field(s): {', '.join(missing)}"

    if not isinstance(obj["id"], str) or not obj["id"].strip():
        return False, "id must be a non-empty string"

    regions = obj["regions"]
    if not isinstance(regions, list) or not regions or not all(isinstance(r, str) for r in regions):
        return False, "regions must be a non-empty list of strings"
    unknown = sorted(set(regions) - VALID_REGIONS)
    if unknown:
        return False, (f"unknown region(s) {unknown}; valid: {sorted(VALID_REGIONS)} "
                        "(CPU quarters only — there is no GPU region)")

    role = obj["role"]
    if not isinstance(role, str) or not ROLE_RE.match(role):
        return False, ("role must match 'backfill-<name>' — never a real serving-role "
                        "name, so region-lock attribution is unmistakable")

    cmd = obj["cmd"]
    if not isinstance(cmd, list) or not cmd or not all(isinstance(c, str) and c for c in cmd):
        return False, "cmd must be a non-empty list of non-empty strings"

    mrs = obj["max_runtime_s"]
    if isinstance(mrs, bool) or not isinstance(mrs, (int, float)):
        return False, "max_runtime_s must be a number of seconds"
    if not (0 < mrs <= MAX_RUNTIME_S_CEILING):
        return False, (
            f"max_runtime_s must satisfy 0 < max_runtime_s <= {MAX_RUNTIME_S_CEILING}s — "
            "bounded runtime is the owner-pressure mitigation this runner depends on "
            "(see module header); REFUSED, not merely flagged"
        )

    if not isinstance(obj["enqueued_by"], str) or not obj["enqueued_by"].strip():
        return False, "enqueued_by must be a non-empty string"
    if not isinstance(obj["ts"], str) or not obj["ts"].strip():
        return False, "ts must be a non-empty string"

    return True, "ok"


# ------------------------------------------------------------------------- the runner


class BackfillRunner:
    def __init__(
        self,
        *,
        queue_dir: Path = DEFAULT_QUEUE_DIR,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
        detector_threshold: int = DEFAULT_DETECTOR_THRESHOLD,
        agent_id: str = AGENT_ID,
        region_lock_bin: Optional[str] = None,
        bus_emit_fn: Optional[Callable[[dict], bool]] = None,
        log_file: Optional[Path] = None,
    ) -> None:
        self.queue_dir = Path(queue_dir)
        self.queue_file = self.queue_dir / "queue.jsonl"
        self.done_file = self.queue_dir / "done.jsonl"
        self.hint_file = self.queue_dir / "ready_hint.txt"
        self.inflight_file = self.queue_dir / "inflight.json"
        self.detector_state_file = self.queue_dir / "detector_state.json"
        self.heartbeat_file = self.queue_dir / "heartbeat.json"
        self.job_log_dir = self.queue_dir / "logs"

        self.max_concurrent = max(1, int(max_concurrent))
        self.detector_threshold = max(1, int(detector_threshold))
        self.agent_id = agent_id
        self._region_lock_bin_override = region_lock_bin
        self.bus_emit_fn = bus_emit_fn or self._default_bus_emit
        self.log_file = log_file or LOG_FILE

        # id -> subprocess.Popen, for jobs THIS process instance launched.
        self.jobs: dict[str, subprocess.Popen] = {}
        # id -> {"spec":, "started_at":, "pid":}
        self.job_meta: dict[str, dict] = {}

        self._stopping = False

        # Detector state, persisted so a supervisor restart doesn't lose the
        # streak or re-emit a finding that already went out.
        self._consecutive_empty = 0
        self._emitted_signature: Optional[str] = None
        self._load_detector_state()

        # Crash recovery: MUST run before the first tick.
        self.reconcile_orphans()

    # ---------------------------------------------------------------- logging

    def _log(self, msg: str) -> None:
        line = f"{_utcnow_iso()} {msg}"
        print(line, file=sys.stderr)
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with self.log_file.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass  # local logging is best-effort; never let it crash the runner

    # ------------------------------------------------------------- region-lock

    def region_lock_bin(self) -> str:
        return (
            self._region_lock_bin_override
            or os.environ.get("HARDWARE_BACKFILL_REGION_LOCK_BIN")
            or DEFAULT_REGION_LOCK_BIN
        )

    def build_command(self, spec: dict) -> list[str]:
        regions = ",".join(sorted(set(spec["regions"])))
        return [
            self.region_lock_bin(), "run",
            "--regions", regions,
            "--role", spec["role"],
            "--timeout-s", "0",
            "--",
            "timeout", str(int(spec["max_runtime_s"])),
            *spec["cmd"],
        ]

    # -------------------------------------------------------------- queue I/O

    def load_queue(self) -> tuple[list[dict], list[dict]]:
        """Returns (valid_specs, refusals). Raises QueueUnreadable if the FILE
        itself cannot be read (never on a per-line parse failure — that is a
        refusal, not a whole-file failure). A missing file is legitimately
        empty."""
        if not self.queue_file.exists():
            return [], []
        try:
            text = self.queue_file.read_text(encoding="utf-8")
        except OSError as e:
            raise QueueUnreadable(f"{self.queue_file}: {e}") from e

        specs: list[dict] = []
        refusals: list[dict] = []
        for i, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                refusals.append({
                    "id": f"malformed-L{i}-{hashlib.sha256(line.encode()).hexdigest()[:12]}",
                    "reason": f"invalid JSON at line {i}: {e}",
                    "spec": {"raw": line[:500]},
                })
                continue
            ok, reason = validate_spec(obj)
            if ok:
                specs.append(obj)
            else:
                refusals.append({
                    "id": obj.get("id") if isinstance(obj, dict) and obj.get("id") else f"invalid-L{i}",
                    "reason": reason,
                    "spec": obj,
                })
        return specs, refusals

    def load_done_ids(self) -> set[str]:
        if not self.done_file.exists():
            return set()
        try:
            text = self.done_file.read_text(encoding="utf-8")
        except OSError as e:
            raise QueueUnreadable(f"{self.done_file}: {e}") from e
        ids: set[str] = set()
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue  # a corrupt DONE line is not grounds to fail closed on depth
            rid = row.get("id") if isinstance(row, dict) else None
            if rid:
                ids.add(rid)
        return ids

    def _append_jsonl(self, path: Path, row: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    def record_done(
        self, spec: dict, rc: Optional[int], started_at: Optional[float],
        ended_at: Optional[float], *, status: str = "completed", reason: Optional[str] = None,
    ) -> None:
        row = {
            "id": spec.get("id"),
            "role": spec.get("role"),
            "regions": spec.get("regions"),
            "status": status,
            "exit_code": rc,
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_s": (ended_at - started_at) if (started_at is not None and ended_at is not None) else None,
            "enqueued_by": spec.get("enqueued_by"),
            "ts": _utcnow_iso(),
        }
        if reason:
            row["reason"] = reason
        self._append_jsonl(self.done_file, row)

    def _record_refusal(self, refusal_id: str, raw_spec: object, reason: str) -> None:
        """Writes the id EXPLICITLY rather than deriving it from `raw_spec`
        (which `record_done` does) — a malformed line, or a spec missing its
        own `id` field, has no `id` to derive, and deriving None there would
        write an unrecoverable `id: null` row. `load_done_ids` then treats
        that row as invisible (a falsy id is skipped), so the SAME refusal
        would be re-parsed and re-written every single tick — the exact
        repeated-record anti-pattern this runner exists to avoid (see module
        header, 590-records)."""
        spec = raw_spec if isinstance(raw_spec, dict) else {}
        row = {
            "id": refusal_id,
            "role": spec.get("role"),
            "regions": spec.get("regions"),
            "status": "refused",
            "exit_code": None,
            "started_at": None,
            "ended_at": None,
            "duration_s": None,
            "enqueued_by": spec.get("enqueued_by"),
            "reason": reason,
            "ts": _utcnow_iso(),
        }
        self._append_jsonl(self.done_file, row)

    def _persist_refusals(self, refusals: list[dict], done_ids: set[str]) -> None:
        for r in refusals:
            if r["id"] in done_ids:
                continue  # already recorded on a prior tick — refusal is terminal
            self._log(f"REFUSING spec {r['id']}: {r['reason']}")
            self._record_refusal(r["id"], r["spec"], r["reason"])
            done_ids.add(r["id"])

    # ---------------------------------------------------------------- inflight

    def load_inflight(self) -> dict[str, dict]:
        try:
            data = _read_json(self.inflight_file, {})
        except (OSError, ValueError) as e:
            self._log(f"inflight.json unreadable ({e}); resetting to empty "
                      "(worst case: a still-alive job is redispatched — bounded and "
                      "region-lock-serialized, never unsafe)")
            return {}
        return data if isinstance(data, dict) else {}

    def _save_inflight(self, inflight: dict[str, dict]) -> None:
        _write_atomic_json(self.inflight_file, inflight)

    def reconcile_orphans(self) -> list[str]:
        """Startup crash-recovery: ANY entry surviving in inflight.json belongs
        to a previous runner instance (this fresh instance has zero live
        `self.jobs` handles by construction), so it is orphaned by definition.
        Clearing it makes the id eligible for re-dispatch. Safe because
        region-lock's own live-PID pruning already guarantees a dead runner's
        children release their regions — see module header."""
        inflight = self.load_inflight()
        if not inflight:
            return []
        orphans = sorted(inflight)
        for job_id in orphans:
            self._log(f"re-queuing orphaned in-flight job {job_id!r} "
                      "(no live handle in this runner instance)")
        self._save_inflight({})
        return orphans

    # ------------------------------------------------------------ dispatching

    def _sync_and_get_pending(self) -> Optional[list[dict]]:
        """Reconciles refusals, then returns pending specs, or None if either
        queue.jsonl or done.jsonl could not be read (fail closed: no dispatch,
        no depth reading, this tick)."""
        try:
            specs, refusals = self.load_queue()
            done_ids = self.load_done_ids()
        except QueueUnreadable as e:
            self._log(f"UNREADABLE: {e} — depth unknown, dispatch skipped this cycle "
                      "(never inferring emptiness from a read error)")
            return None
        self._persist_refusals(refusals, done_ids)
        inflight = self.load_inflight()
        return [s for s in specs if s["id"] not in done_ids and s["id"] not in inflight]

    def queue_depth(self) -> Optional[int]:
        pending = self._sync_and_get_pending()
        return None if pending is None else len(pending)

    def launch(self, spec: dict) -> None:
        cmd = self.build_command(spec)
        self.job_log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.job_log_dir / f"{spec['id']}.log"
        started = time.time()
        try:
            log_fh = log_path.open("ab")
        except OSError:
            log_fh = subprocess.DEVNULL
        proc = subprocess.Popen(cmd, stdout=log_fh, stderr=subprocess.STDOUT)
        if log_fh not in (None, subprocess.DEVNULL):
            log_fh.close()  # child holds its own dup'd fd; safe to close ours
        self.jobs[spec["id"]] = proc
        self.job_meta[spec["id"]] = {"spec": spec, "started_at": started, "pid": proc.pid}
        inflight = self.load_inflight()
        inflight[spec["id"]] = {
            "pid": proc.pid, "started_at": started,
            "role": spec["role"], "regions": spec["regions"],
        }
        self._save_inflight(inflight)
        self._log(f"launched {spec['id']} (pid={proc.pid}, role={spec['role']}, "
                  f"regions={spec['regions']}, max_runtime_s={spec['max_runtime_s']})")

    def reap(self) -> None:
        finished = [jid for jid, proc in self.jobs.items() if proc.poll() is not None]
        if not finished:
            return
        inflight = self.load_inflight()
        for job_id in finished:
            proc = self.jobs.pop(job_id)
            meta = self.job_meta.pop(job_id)
            ended = time.time()
            self.record_done(meta["spec"], proc.returncode, meta["started_at"], ended)
            inflight.pop(job_id, None)
            self._log(f"reaped {job_id} rc={proc.returncode} "
                      f"duration_s={ended - meta['started_at']:.1f}")
        self._save_inflight(inflight)

    def tick(self) -> None:
        """One reap+dispatch pass. Never claims a region itself — every launch
        is a `region-lock run` subprocess, which waits its turn like anyone
        else."""
        self.reap()
        pending = self._sync_and_get_pending()
        if pending is None:
            return
        slots = self.max_concurrent - len(self.jobs)
        for spec in pending[: max(0, slots)]:
            self.launch(spec)

    # ------------------------------------------------------------ detector state

    def _load_detector_state(self) -> None:
        try:
            data = _read_json(self.detector_state_file, {})
        except (OSError, ValueError) as e:
            self._log(f"detector_state.json unreadable ({e}); starting fresh (streak=0)")
            data = {}
        if isinstance(data, dict):
            self._consecutive_empty = int(data.get("consecutive_empty") or 0)
            self._emitted_signature = data.get("emitted_signature")

    def _save_detector_state(self) -> None:
        _write_atomic_json(self.detector_state_file, {
            "consecutive_empty": self._consecutive_empty,
            "emitted_signature": self._emitted_signature,
            "ts": _utcnow_iso(),
        })

    # -------------------------------------------------------------- bus emit

    def _default_bus_emit(self, message: dict) -> bool:
        """REAL seam (see also HARDWARE_BACKFILL_REGION_LOCK_BIN in the module
        header): shells out to `session_bus.py append`, exactly the command
        this runner's owning task brief specifies. Returns True iff the append
        succeeded (rc 0). Tests should override via
        `BackfillRunner(bus_emit_fn=...)` rather than monkeypatching this."""
        cmd = ["python3", str(SESSION_BUS_PY), "append",
               "--agent", self.agent_id, "--target", "outbox",
               "--json", json.dumps(message)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as e:
            self._log(f"session_bus append raised {e!r} — treated as failure (fail-closed)")
            return False
        if result.returncode != 0:
            self._log(f"session_bus append FAILED rc={result.returncode}: "
                      f"{(result.stderr or '').strip()[:500]}")
            return False
        return True

    def _read_hint(self) -> Optional[str]:
        """None => no hint (missing OR unreadable — caller distinguishes via
        `.hint_file.exists()` if it needs to log the unreadable case)."""
        if not self.hint_file.exists():
            return None
        try:
            content = self.hint_file.read_text(encoding="utf-8")
        except OSError as e:
            self._log(f"ready_hint.txt exists but is unreadable ({e}); fail-closed, "
                      "no finding emitted this check")
            return None
        return content

    def _build_finding_message(self, depth: int, hint: str) -> dict:
        hint = hint.strip()
        return {
            "to": "coordinator-agent",
            "kind": "finding",
            "needs_routing_to": ["coordinator-agent"],
            "action_required": True,
            "payload": {
                "detail": (
                    f"hardware-backfill queue has been empty for "
                    f"{self._consecutive_empty} consecutive checks "
                    f"(threshold {self.detector_threshold}) while ready_hint.txt names "
                    f"outstanding compute-gated READY work: {hint}"
                ),
                "queue_depth": depth,
                "consecutive_empty_checks": self._consecutive_empty,
                "ready_hint": hint,
            },
        }

    def detector_tick(self) -> None:
        """One detector check. Advances the sustained-empty streak by exactly
        one call — callers (the `run` loop) decide the real-world cadence by
        deciding how often to call this."""
        depth = self.queue_depth()
        if depth is None:
            return  # unreadable this check — streak counters untouched, fail closed

        if depth > 0:
            if self._consecutive_empty or self._emitted_signature:
                self._consecutive_empty = 0
                self._emitted_signature = None
                self._save_detector_state()
            return

        self._consecutive_empty += 1
        if self._consecutive_empty < self.detector_threshold:
            self._save_detector_state()
            return

        hint = self._read_hint()
        if not hint or not hint.strip():
            self._save_detector_state()
            return  # sustained-empty with NO known ready work — nothing to report

        sig = hashlib.sha256(hint.strip().encode("utf-8")).hexdigest()
        if sig == self._emitted_signature:
            return  # HOLD: same unchanged (streak, hint) state already reported

        message = self._build_finding_message(depth, hint)
        if self.bus_emit_fn(message):
            self._emitted_signature = sig
            self._save_detector_state()
            self._log(f"emitted idle-queue finding (streak={self._consecutive_empty}, "
                      f"hint_sig={sig[:12]})")
        else:
            self._log("finding emission FAILED — will retry next detector check; "
                      "dedup state NOT advanced")

    # -------------------------------------------------------------- lifecycle

    def request_stop(self) -> None:
        self._stopping = True

    def write_heartbeat(self) -> None:
        depth = None
        try:
            depth = self.queue_depth()
        except Exception:  # noqa: BLE001 — heartbeat must never crash the loop
            pass
        _write_atomic_json(self.heartbeat_file, {
            "pid": os.getpid(),
            "ts": _utcnow_iso(),
            "state": "draining" if self._stopping else "working",
            "jobs_running": len(self.jobs),
            "queue_depth": depth,
        })

    def shutdown(self, grace_s: float = 10.0) -> None:
        """SIGTERM in-flight children (region-lock forwards it down to the
        wrapped `timeout`+cmd, releasing the region lock cleanly on exit —
        fabric axiom 4's quiesce model), then reap. A dead runner whose
        children are ALSO dead is exactly what `reconcile_orphans` assumes."""
        if not self.jobs:
            return
        self._log(f"shutdown: SIGTERM to {len(self.jobs)} in-flight job(s)")
        for proc in self.jobs.values():
            try:
                proc.terminate()
            except ProcessLookupError:
                pass
        deadline = time.time() + grace_s
        while time.time() < deadline and any(p.poll() is None for p in self.jobs.values()):
            time.sleep(0.2)
        for job_id, proc in list(self.jobs.items()):
            if proc.poll() is None:
                self._log(f"shutdown: {job_id} did not exit within {grace_s}s; SIGKILL")
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
        self.reap()

    def loop(
        self, *, tick_interval_s: float = DEFAULT_TICK_INTERVAL_S,
        detector_interval_s: float = DEFAULT_DETECTOR_INTERVAL_S,
        max_iterations: Optional[int] = None, sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._log(f"loop start: max_concurrent={self.max_concurrent} "
                  f"tick_interval_s={tick_interval_s} detector_interval_s={detector_interval_s} "
                  f"detector_threshold={self.detector_threshold}")
        last_detector = 0.0
        n = 0
        while not self._stopping:
            self.tick()
            self.write_heartbeat()
            now = time.time()
            if now - last_detector >= detector_interval_s:
                self.detector_tick()
                last_detector = now
            n += 1
            if max_iterations is not None and n >= max_iterations:
                break
            if self._stopping:
                break
            sleep_fn(tick_interval_s)
        self.shutdown()
        self.write_heartbeat()
        self._log("loop stopped")


# ------------------------------------------------------------------------------ CLI


def _runner_from_args(args: argparse.Namespace) -> BackfillRunner:
    return BackfillRunner(
        queue_dir=Path(args.queue_dir),
        max_concurrent=args.max_concurrent,
        detector_threshold=args.detector_threshold,
    )


def cmd_once(args: argparse.Namespace) -> int:
    runner = _runner_from_args(args)
    runner.tick()
    runner.detector_tick()
    runner.write_heartbeat()
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    queue_dir = Path(args.queue_dir)
    queue_dir.mkdir(parents=True, exist_ok=True)
    lock_path = queue_dir / "backfill_runner.lock"
    lock_fh = lock_path.open("a+b")
    try:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("hardware-backfill: another instance holds the lock; exiting.", file=sys.stderr)
        return 0

    runner = _runner_from_args(args)

    def _stop(signum, _frame):
        runner.request_stop()
        print(f"hardware-backfill: signal {signum}, draining", file=sys.stderr)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    runner.loop(tick_interval_s=args.tick_interval_s, detector_interval_s=args.detector_interval_s)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hardware_backfill.py",
        description="Bounded backfill queue runner + queue-empty detector.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    def _common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--queue-dir", default=str(DEFAULT_QUEUE_DIR))
        sp.add_argument("--max-concurrent", type=int, default=DEFAULT_MAX_CONCURRENT)
        sp.add_argument("--tick-interval-s", type=float, default=DEFAULT_TICK_INTERVAL_S)
        sp.add_argument("--detector-interval-s", type=float, default=DEFAULT_DETECTOR_INTERVAL_S)
        sp.add_argument("--detector-threshold", type=int, default=DEFAULT_DETECTOR_THRESHOLD)

    run_p = sub.add_parser("run", help="continuous loop until SIGTERM/SIGINT")
    _common(run_p)
    run_p.set_defaults(func=cmd_run)

    once_p = sub.add_parser("once", help="single reap+dispatch+detector pass, then exit")
    _common(once_p)
    once_p.set_defaults(func=cmd_once)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
