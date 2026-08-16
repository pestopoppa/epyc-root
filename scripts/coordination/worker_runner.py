#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""worker_runner.py — one assignment, one visible worker, one typed report, then exit.

Owning handoff: handoffs/active/loop-owned-fleet-implementation.md (P2-1, P2-4, P2-6)
Plan of record: docs/design/loop-owned-fleet.html  (runner lifecycle diagram)
Contract:       coordination/session-bus/BUS_PROTOCOL.md
Ratified decisions this file implements: D1 (bounds), D2/D2b (harness knob +
permission profile), D6 (kill-with-salvage), D8 (visible, human-authoritative panes).

WHY THIS EXISTS, AND WHY IT IS EPHEMERAL
----------------------------------------
The fleet's measured failure class is *committed-not-live*: a fix is written,
committed, and never actually executing in the long-lived process that was
supposed to run it (INC-20260727-stale-heartbeat; the H-4 SHA deploy-marker
check in P0-5 exists solely to re-detect it). Every long-lived supervisor in
this repo has produced at least one instance of it.

So this runner is **exec'd fresh by the daemon per assignment and exits when the
assignment is done**. There is no resident runner to go stale: the code that
runs a batch is the code on disk at the moment the batch started, by
construction, and a `git pull` is a deploy. The only "persistent" piece is this
process blocking on its own child — a wait, not a supervisor.

THE MACHINE'S CHANNEL TO THE WORKER IS TYPED AND ONE-WAY (D8)
------------------------------------------------------------
Spawn args + a brief file in. A schema-valid report file and a process exit
status out. **This module never types into a pane and never reads pane text to
make a decision.** Those two channels produced the entire C51–C56 / F-33–F-43
delivery-plane defect class and a 94%-false-positive perception class; deleting
them is the point of the restructure, not an incidental cleanup. Pane scrollback
IS captured — but only as evidence attached to a failed row, for a human to
read. `test_worker_runner.py::test_no_pane_io_decision_channel` enforces this at
the source level so the guard survives a future edit.

The pane is VISIBLE because the operator must be able to watch a worker and
answer a permission prompt by hand. Human authority over the pane is the design;
machine authority over the pane is the defect.

KILL IS ALLOWED. LOSS IS FORBIDDEN. (D6)
----------------------------------------
A lease that cannot be enforced is not a lease, so lease expiry kills:
SIGTERM → grace → SIGKILL, **of a pid this process captured itself** (project
hard rule: no name-pattern kills, ever — INC-20260731-broad-process-pattern-kills
killed another session's `llama-server` twice off a `pkill` pattern). Every kill
is then FOLLOWED BY A MANDATORY SALVAGE: the lane worktree's uncommitted state
is committed to `refs/salvage/<task_id>`, the harness transcript and captured
pane scrollback are committed alongside it under `.salvage-evidence/`, and the
row is marked FAILED with a `salvage_ref`. `salvage_worktree()` then RE-READS
the ref it just wrote and compares every file byte-for-byte against the working
tree; a salvage that loses one file raises `SalvageError` instead of returning a
reassuring ref. Nothing is ever discarded silently.

Salvage builds its tree in a TEMPORARY INDEX (`GIT_INDEX_FILE`), never the lane
worktree's own index and never its HEAD: a dead worker's tree is left exactly as
it was found, so the salvage is non-destructive and re-runnable.

FAIL-CLOSED GATES (all refuse BEFORE anything is spawned)
---------------------------------------------------------
* `workerpool` must be a roster id (P2-5) — a runner that cannot record its
  results must not start work it cannot report.
* the rule-8 amendment ack must be present in config before ANY kill path may
  run (D6: "merged BEFORE the kill path first runs"). Absent ⇒ refuse to spawn.
* the lane must resolve UNDER the pool root, must not match `*.orphan*` (R15:
  five `.orphan` worktrees sit beside live lanes and were destroyed once by a
  `git worktree prune`), must exist (creating lanes is P2-0's job, not this
  runner's), and must be a git worktree (salvage needs one).
* D1 bounds: concurrency ≤ 4 (hard ceiling; config may lower, never raise),
  batch cap 3, ~250k tokens per batch, pinned paid provider.

Exit codes:
    0   the batch ran (pass OR fail) and every outcome was recorded on the bus,
        or the batch was parked before spawning (premise not still-needed)
    2   REFUSED before spawn — a guard said no; nothing was started
    3   SALVAGE FAILED — a kill happened and state may be at risk. The loudest
        code in this module; it means a human must look at the lane NOW.
    4   internal error

Usage:
    worker_runner.py run --assignment /path/to/assignment.json --lane lane0
    worker_runner.py run --lane lane0 --task-id RTG-51 --row-text "..." \
                         --source-handoff handoffs/active/foo.md
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.coordination import session_bus  # noqa: E402
from scripts.coordination.session_bus import (  # noqa: E402
    MSG_SCHEMA_VERSION,
    BusError,
    _append_jsonl,
    _claim_key,
    _read_jsonl,
    _require_roster_id,
    _utcnow_iso,
    _write_atomic,
    get_bus_root,
    validate_row,
)

# --------------------------------------------------------------- identity

WORKERPOOL_AGENT = "workerpool"
REPORT_SCHEMA_VERSION = "worker_report.v1"
BRIEF_SCHEMA_VERSION = "worker_brief.v1"

# D1, enforced in code and NOT raisable from config. Config may set a LOWER
# value; a config asking for more than this is refused rather than clamped
# silently, because a silent clamp reads as compliance to whoever wrote it.
HARD_MAX_CONCURRENT = 4
HARD_BATCH_CAP = 3                       # P2-6
HARD_TOKEN_CEILING = 250_000             # D1, ~250k per batch

# AUD-2. The brief is the dispatch; a dispatch too big to read gets skimmed.
BRIEF_MAX_BYTES = 4096

# config.yaml's `worker_pool:` block is authored by P2-5 and is THE policy
# surface; these are the names it uses. This module's internal names are the
# short forms, so the aliases are resolved once, here, rather than by every
# reader — two spellings of one bound is how a cap gets enforced at one value
# and reported at another.
CONFIG_ALIASES = {
    "max_concurrent_workers": "max_concurrent",
    "max_rows_per_batch": "batch_cap",
    "lease_grace_s": "grace_s",
}

DEFAULTS: dict[str, Any] = {
    # THE MASTER SWITCH, and it starts OFF (P2-5). The roster row makes the pool
    # SCHEDULABLE; this flag makes it EXECUTABLE. A schedulable-but-not-
    # executable pool is the 2026-08-14 shape: the daemon assigns, nothing runs,
    # the lease expires, the row dies.
    "enabled": False,
    "pool_root": "/mnt/raid0/llm/worktrees/pool",
    "runtime_root": "/mnt/raid0/llm/worker-pool",
    "max_concurrent": HARD_MAX_CONCURRENT,
    "batch_cap": HARD_BATCH_CAP,
    "token_ceiling_per_batch": HARD_TOKEN_CEILING,
    "provider": "anthropic-paid",
    "lease_s": 5400.0,
    "grace_s": 30.0,
    "poll_s": 2.0,
    "spawn_timeout_s": 30.0,
    "post_report_grace_s": 60.0,
    "rule8_amendment_ack": None,
    "tmux_session": "agent",
    "permission_profile": {"allow": [], "deny": []},
    "lanes": {},
    "harnesses": {},
}

# D2. Adding a harness is ONE dict entry: a template argv. `{...}` fields are
# substituted from the spawn context. The pilot uses `claude`; `codex` is the
# scale-out default; `stub` exists so the whole lifecycle is testable with no
# LLM, no tokens and no network.
BUILTIN_HARNESSES: dict[str, list[str]] = {
    "claude": [
        "claude", "-p", "{prompt}",
        "--settings", "{permissions_path}",
        "--output-format", "stream-json", "--verbose",
    ],
    "codex": [
        "codex", "exec", "--cd", "{worktree}", "{prompt}",
    ],
    "stub": [
        "{python}", "{stub_cmd}", "--brief", "{brief_path}", "--report", "{report_path}",
    ],
}

# Providers whose presence in the environment would silently route a "pinned
# paid provider" run somewhere else. Mechanically checkable, so it is checked.
PROVIDER_ESCAPE_ENV = (
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_AUTH_TOKEN",
)


class RefusalError(RuntimeError):
    """A guard said no. Nothing has been spawned; exit 2."""


class SalvageError(RuntimeError):
    """A kill happened and the salvage could not be PROVEN lossless. Exit 3."""


# ------------------------------------------------------------------ config


def load_pool_config(bus_root: Path, lane: Optional[str] = None) -> dict:
    """Merge DEFAULTS < config.yaml `worker_pool` < per-lane override.

    `worker_harness` is read at the TOP level of config.yaml (D2 names it there)
    and may be overridden per lane, so a single lane can be flipped to `codex`
    for a scale-out A/B without touching the other three.
    """
    try:
        import yaml
        raw = yaml.safe_load((bus_root / "config.yaml").read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001 — operator-facing
        raise RefusalError(f"could not read {bus_root/'config.yaml'}: {exc}") from exc
    if not isinstance(raw, dict):
        raise RefusalError("config.yaml did not parse to a mapping")

    cfg = dict(DEFAULTS)
    # tmux topology is policy that already exists in config.yaml; this reads it
    # rather than forking a second copy. Applied BEFORE the worker_pool overlay
    # so precedence is DEFAULTS < tmux: < worker_pool: < per-lane — the module's
    # own default must never outrank a value the operator wrote down.
    tmux = raw.get("tmux") if isinstance(raw.get("tmux"), dict) else {}
    if tmux.get("live_session"):
        cfg["tmux_session"] = tmux["live_session"]
    cfg["tmux_allow_session_creation"] = bool(tmux.get("allow_session_creation", False))

    cfg["worker_harness"] = raw.get("worker_harness", "claude")
    pool = raw.get("worker_pool")
    if isinstance(pool, dict):
        for key, value in pool.items():
            cfg[CONFIG_ALIASES.get(key, key)] = value
    # Per-lane override, two accepted spellings: `lane_harness: {lane0: codex}`
    # (P2-5's shape, harness only) and `lanes: {lane0: {...}}` (any key).
    lane_harness = cfg.get("lane_harness") if isinstance(cfg.get("lane_harness"), dict) else {}
    if lane and lane_harness.get(lane):
        cfg["worker_harness"] = lane_harness[lane]
    lanes = cfg.get("lanes") if isinstance(cfg.get("lanes"), dict) else {}
    if lane and isinstance(lanes.get(lane), dict):
        cfg.update({CONFIG_ALIASES.get(k, k): v for k, v in lanes[lane].items()})

    return cfg


def check_enabled(cfg: dict, pilot_override: bool = False) -> None:
    """P2-5's master switch. Schedulable (roster row present) and EXECUTABLE
    (this flag) are deliberately separate: with the flag off the daemon treats
    the endpoint as not-ready and leaves rows READY and visible, instead of
    assigning work into a pool that cannot run it and watching the lease expire.

    `pilot_override` exists to break one specific circularity: the flag says
    "flip only after the runner is proven end-to-end", and proving it requires
    running it. The override covers a SUPERVISED, HAND-DISPATCHED run only. It
    does not touch the daemon's gate (which reads the config, not this argument)
    and it does NOT bypass the rule-8 ack — a runner may not kill without the
    amendment, override or no override.
    """
    if pilot_override:
        print("worker_runner: PILOT OVERRIDE — supervised manual run with "
              "worker_pool.enabled=false. The daemon remains gated.", file=sys.stderr)
        return
    if not cfg.get("enabled"):
        raise RefusalError(
            "worker_pool.enabled is false — the pool is schedulable but not executable. "
            "Flip it to true in coordination/session-bus/config.yaml only after this runner "
            "has been proven end-to-end on this host (P2-5).")


def check_bounds(cfg: dict) -> None:
    """D1, fail-closed. A config asking for MORE than the ratified bound is
    refused, never clamped: a silent clamp reads as compliance to its author."""
    if int(cfg["max_concurrent"]) > HARD_MAX_CONCURRENT:
        raise RefusalError(
            f"worker_pool.max_concurrent={cfg['max_concurrent']} exceeds the D1 ceiling "
            f"{HARD_MAX_CONCURRENT}. The bound is ratified standing spawn authority, not a "
            f"tunable; lower the config or take a new operator decision.")
    if int(cfg["batch_cap"]) > HARD_BATCH_CAP:
        raise RefusalError(
            f"worker_pool.batch_cap={cfg['batch_cap']} exceeds the P2-6 cap {HARD_BATCH_CAP}.")
    if float(cfg["token_ceiling_per_batch"]) > HARD_TOKEN_CEILING:
        raise RefusalError(
            f"worker_pool.token_ceiling_per_batch={cfg['token_ceiling_per_batch']} exceeds the "
            f"D1 ceiling {HARD_TOKEN_CEILING} (which doubles as the Phase-2 cost gate).")


def check_provider_pin(cfg: dict, env: Optional[dict] = None) -> None:
    """D1 pins the paid provider. `provider: null` disables the pin explicitly
    (tests, `stub`); a pin that is SET must not be silently re-routed."""
    if not cfg.get("provider"):
        return
    env = os.environ if env is None else env
    escaped = sorted(k for k in PROVIDER_ESCAPE_ENV if env.get(k))
    if escaped:
        raise RefusalError(
            f"provider is pinned to {cfg['provider']!r} but the environment sets {escaped} — "
            f"that silently routes the run to a different provider than the one the D1 "
            f"authority was granted for. Unset them or clear worker_pool.provider.")


def check_rule8_ack(cfg: dict) -> None:
    """D6: the BUS_PROTOCOL rule-8 amendment (pool-worker salvage-kill exception)
    must be operator-acked BEFORE the kill path first runs. The runner cannot
    honour a lease without killing, so an un-acked amendment refuses the SPAWN —
    fail-closed at the earliest point, not at the moment of the kill."""
    ack = cfg.get("rule8_amendment_ack")
    if not (isinstance(ack, str) and ack.strip()):
        raise RefusalError(
            "worker_pool.rule8_amendment_ack is unset. D6 requires the BUS_PROTOCOL rule-8 "
            "amendment (lease-expiry salvage-kill exception, POOL WORKERS ONLY — interactive "
            "reclaim stays quiesce-and-drain) to be operator-acked before the kill path first "
            "runs. This runner enforces a lease, therefore it may kill, therefore it refuses to "
            "spawn until the ack is recorded. Set the key to the ratification reference.")


# ------------------------------------------------------------------- lanes


def resolve_lane(cfg: dict, lane: str) -> Path:
    """Resolve and GUARD a pool lane path.

    Four refusals, each with a named origin:
      * outside the pool root       — P2-0: pilot workers never spawn into
        mainA–D's lanes while their interactive mains are live (commit-sweep).
      * `*.orphan*`                 — R15/P0-8: five `.orphan` worktrees sit
        beside live lanes and a `git worktree prune` destroyed them once.
      * missing                     — creating lanes is P2-0, an operator-visible
        step. A runner that creates its own lane hides a missing precondition.
      * not a git worktree          — salvage (D6) needs one; discovering that
        at kill time is discovering it too late.
    """
    pool_root = Path(str(cfg["pool_root"]))
    candidate = Path(lane) if os.path.isabs(lane) else pool_root / lane
    resolved = candidate.resolve() if candidate.exists() else candidate.absolute()
    root = pool_root.resolve() if pool_root.exists() else pool_root.absolute()

    if ".orphan" in str(resolved):
        raise RefusalError(
            f"lane {resolved} matches *.orphan* — orphan worktrees are disposal candidates "
            f"(P0-8), never spawn targets. Refusing.")
    try:
        inside = resolved == root or root in resolved.parents
    except (OSError, ValueError):
        inside = False
    if not inside:
        raise RefusalError(
            f"lane {resolved} is not under the pool root {root} — pool workers spawn ONLY into "
            f"worktrees/pool/laneN. mainA–D lanes are off limits while their interactive mains "
            f"are live (P2-0: a worker's commit-per-unit or salvage commit in an occupied "
            f"worktree is the documented commit-sweep hazard).")
    if not resolved.is_dir():
        raise RefusalError(
            f"lane directory {resolved} does not exist. Creating pool lanes is P2-0, an "
            f"operator-visible step — this runner will not create one silently. Run the lane "
            f"setup first.")
    if not (resolved / ".git").exists():
        raise RefusalError(
            f"lane {resolved} is not a git worktree (no .git) — D6 salvage commits the lane's "
            f"uncommitted state to a git ref, so a non-git lane makes the no-loss guarantee "
            f"unenforceable. Refusing to spawn work that could not be salvaged.")
    return resolved


LANE_LOCK_NAME = ".worker.lock"


class LaneLock:
    """One live worker per worktree — acquired with `flock`, readable as a pid.

    TWO CONSUMERS, ONE FILE. The coordinator-daemon's `_free_pool_lane` picks a
    lane by reading `<lane>/.worker.lock` and checking `/proc/<pid>`; this runner
    ACQUIRES the same file with `flock`. That is deliberate, not redundancy: a
    lock you *observe* is TOCTOU (invariant 5, "claims are ACQUIRED, never
    observed") and a pid file outlives its writer — the shape of the 8 claims
    found 300 hours stale on 2026-08-12 — so the flock is the real exclusion and
    the pid text is the daemon's read-only hint. Putting them in two different
    files would let the daemon see a lane as free while a worker held it, and
    every launch into that lane would then bounce off the flock. One file, two
    readings that cannot disagree.

    The kernel drops the flock when the holder dies, so a crashed runner cannot
    wedge a lane even though the file remains.
    """

    def __init__(self, lane_path: Path) -> None:
        self.lane_path = lane_path
        self.path = lane_path / LANE_LOCK_NAME
        self._fh = None

    def acquire(self) -> "LaneLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self._fh.close()
            self._fh = None
            raise RefusalError(
                f"lane {self.lane_path.name} is already held by a live worker ({self.path}) — "
                f"one worker per worktree. Refusing.") from exc
        self._fh.seek(0)
        self._fh.truncate()
        # pid FIRST WHITESPACE-SEPARATED TOKEN: that is the daemon's contract.
        self._fh.write(f"{os.getpid()} {_utcnow_iso()} workerpool\n")
        self._fh.flush()
        return self

    def release(self) -> None:
        if self._fh is not None:
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            finally:
                self._fh.close()
                self._fh = None
        try:
            self.path.unlink()
        except OSError:
            pass

    def __enter__(self) -> "LaneLock":
        return self.acquire()

    def __exit__(self, *exc: Any) -> None:
        self.release()


def live_lane_count(pool_root: Path) -> int:
    """How many lanes are held RIGHT NOW, measured by TRYING the lock.

    Probing rather than counting files: a lockfile is a birth certificate, the
    lock is the liveness signal (INC-20260727-stale-heartbeat, same lesson).
    """
    if not pool_root.is_dir():
        return 0
    held = 0
    for lane in sorted(d for d in pool_root.iterdir() if d.is_dir()):
        path = lane / LANE_LOCK_NAME
        if not path.exists():
            continue
        try:
            with path.open("a+", encoding="utf-8") as fh:
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                except OSError:
                    held += 1
        except OSError:
            continue
    return held


def check_concurrency(cfg: dict, pool_root: Path) -> None:
    limit = min(int(cfg["max_concurrent"]), HARD_MAX_CONCURRENT)
    live = live_lane_count(pool_root)
    if live >= limit:
        raise RefusalError(
            f"{live} pool worker(s) already live, cap is {limit} (D1: concurrency ≤ "
            f"{HARD_MAX_CONCURRENT}). Refusing to spawn.")


# ------------------------------------------------------------------- brief


def build_brief(rows: list[dict], *, batch_id: str, lane: str, worktree: Path,
                report_path: Path, cfg: dict, lease_expires_ts: str) -> dict:
    """The typed dispatch (AUD-2 shape). `task_text` is the identity.

    `row_ref` (`file.md:LINE`) is carried as a HINT only and labelled as one:
    anchor rot measured 34.5% queue-wide on 2026-08-11 (27% twelve days
    earlier), so a line number names a different row every few weeks. Every
    constraint carries `.source` — a restated constraint that cites nothing is
    prose in disguise (F-20).
    """
    brief_rows = []
    for row in rows:
        text = str(row.get("task_text") or "").strip()
        if not text:
            raise RefusalError(
                "a batch row has no task_text — the dispatch IDENTITY. A row_ref is a hint, "
                "not an identity. Re-resolve with scripts/coordination/backlog_row_check.py.")
        entry = {
            "task_id": str(row["task_id"]),
            "task_text": text,
            "row_ref_hint": row.get("row_ref"),
            "screened_by": row.get("screened_by"),
            "expected_occupancy": row.get("expected_occupancy"),
            "constraints": normalize_constraints(row.get("constraints")),
            "source_handoff": row.get("source_handoff"),
        }
        brief_rows.append({k: v for k, v in entry.items() if v not in (None, [], {})})

    brief = {
        "schema_version": BRIEF_SCHEMA_VERSION,
        "batch_id": batch_id,
        "lane": lane,
        "worktree": str(worktree),
        "report_path": str(report_path),
        "lease_expires_ts": lease_expires_ts,
        "token_ceiling": int(cfg["token_ceiling_per_batch"]),
        "rows": brief_rows,
    }
    size = len(json.dumps(brief, sort_keys=True).encode("utf-8"))
    if size > BRIEF_MAX_BYTES:
        raise RefusalError(
            f"brief is {size} bytes, cap {BRIEF_MAX_BYTES} (AUD-2). A dispatch too big to read "
            f"gets read as a wall and skimmed. Shorten task_text, move detail behind a "
            f"constraint `source` pointer, or reduce the batch from {len(brief_rows)} rows.")
    return brief


def normalize_constraints(raw: Any) -> list[dict]:
    """Every constraint must cite the line it derives from (`source`).

    A prose string is accepted structurally but marked `source: "unsourced"` so
    the defect is VISIBLE in the brief rather than indistinguishable from a
    sourced one — F-20: a brief asserted a constraint no artifact contained, and
    nothing downstream could tell.
    """
    if not raw:
        return []
    if isinstance(raw, str):
        return [{"text": raw, "source": "unsourced"}]
    out = []
    for item in raw:
        if isinstance(item, str):
            out.append({"text": item, "source": "unsourced"})
        elif isinstance(item, dict):
            out.append({"text": str(item.get("text", "")), "source": str(item.get("source") or "unsourced")})
    return out


def build_prompt(brief_path: Path, report_path: Path, worktree: Path) -> str:
    """The bootstrap the harness is started with. Deliberately tiny: the brief
    file is the dispatch, this only tells the worker where it is and what the
    completion signal is. The completion signal is the REPORT FILE — never
    anything the worker prints, because printed text is pane text (D8)."""
    return (
        f"You are a pool worker. Your working tree is {worktree}.\n"
        f"1. Read your brief: {brief_path}\n"
        f"2. Do the work for every row in brief.rows, committing per completed unit "
        f"(pathspec-limited commits only — this is a shared clone).\n"
        f"3. Write your completion report to {report_path} as JSON matching "
        f"schema_version \"{REPORT_SCHEMA_VERSION}\": "
        f"{{schema_version, batch_id, harness, subagents_spawned, tokens_used, "
        f"denials: [{{tool, reason}}], rows: [{{task_id, outcome: "
        f"pass|fail|blocked|skipped, summary, commits: [], artifacts: []}}]}}.\n"
        f"4. Append {{\"task_id\": ..., \"event\": \"start\"|\"complete\"}} to "
        f"{report_path.parent / 'progress.jsonl'} as you enter and finish each row, so a "
        f"timeout can tell which row was in progress.\n"
        f"The report file is the ONLY completion signal. Record every DENIED tool call in "
        f"`denials` — a silent denial is scored as a failure, never as a pass.\n"
    )


# --------------------------------------------------------- premise preflight


def screen_premise_safe(row: dict) -> dict:
    """Call `premise_screener.screen_premise`, treating EVERY failure as UNKNOWN.

    P2-2 is being built in parallel; this module must not import-fail because a
    sibling does not exist yet, and must not fail OPEN either. Fail-open is the
    defect class this repo has the longest ledger on (C3, C6, C8 in the bus
    module alone; `feedback_fail_open_defaults_conceal_their_own_corruption`),
    so an absent, broken, throwing, or malformed screener returns UNKNOWN — and
    UNKNOWN parks the row. A screener that cannot answer must never be
    indistinguishable from a screener that said yes.
    """
    def unknown(reason: str) -> dict:
        return {"verdict": "unknown", "evidence": "", "reason": reason}

    try:
        from scripts.coordination.premise_screener import screen_premise  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        return unknown(f"premise_screener unavailable: {type(exc).__name__}: {exc}")
    try:
        verdict = screen_premise(row)
    except Exception as exc:  # noqa: BLE001
        return unknown(f"premise_screener raised: {type(exc).__name__}: {exc}")
    if not isinstance(verdict, dict):
        return unknown(f"premise_screener returned {type(verdict).__name__}, expected dict")
    value = str(verdict.get("verdict") or "").strip().lower()
    if value not in {"still-needed", "stale", "unknown"}:
        return unknown(f"premise_screener returned unrecognised verdict {value!r}")
    return {
        "verdict": value,
        "evidence": str(verdict.get("evidence") or ""),
        "reason": str(verdict.get("reason") or ""),
    }


# ----------------------------------------------------------- permissions D2b


def write_permission_profile(cfg: dict, run_dir: Path) -> Path:
    """D2b. The allowlist the worker runs under, materialised as a settings file.

    Injected as DATA, never baked into this module: the profile is policy
    (policy-data-never-code, fabric contract axiom), so widening a worker's
    authority is a config edit that shows up in a diff.
    """
    profile = cfg.get("permission_profile") or {}
    settings = {
        "permissions": {
            "allow": list(profile.get("allow") or []),
            "deny": list(profile.get("deny") or []),
        }
    }
    path = run_dir / "permissions.json"
    path.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------- harnesses


def resolve_harness(cfg: dict) -> str:
    name = str(cfg.get("worker_harness") or "claude")
    known = set(BUILTIN_HARNESSES) | set((cfg.get("harnesses") or {}))
    if name not in known:
        raise RefusalError(
            f"worker_harness={name!r} is not a known harness (have: {sorted(known)}). D2 makes "
            f"the harness a config knob; adding one is a template argv entry under "
            f"worker_pool.harnesses, not a code change here.")
    return name


def build_harness_argv(harness: str, cfg: dict, ctx: dict) -> list[str]:
    """Template argv → concrete argv. One dict entry per harness (D2)."""
    template = (cfg.get("harnesses") or {}).get(harness) or BUILTIN_HARNESSES[harness]
    if isinstance(template, str):
        template = shlex.split(template)
    argv = []
    for part in template:
        try:
            argv.append(str(part).format(**ctx))
        except KeyError as exc:
            raise RefusalError(
                f"harness {harness!r} argv template references unknown field {exc} — "
                f"available: {sorted(ctx)}") from exc
    return argv


# -------------------------------------------------------------------- spawn


class WorkerHandle:
    """Everything the machine is allowed to know about a running worker."""

    def __init__(self, pid: int, run_dir: Path, *, window_id: Optional[str] = None,
                 tmux_session: Optional[str] = None, popen: Optional[subprocess.Popen] = None):
        self.pid = pid
        self.run_dir = run_dir
        self.window_id = window_id
        self.tmux_session = tmux_session
        self.popen = popen

    @property
    def rc_path(self) -> Path:
        return self.run_dir / "harness.rc"

    @property
    def transcript_path(self) -> Path:
        return self.run_dir / "harness-transcript.log"

    def alive(self) -> bool:
        try:
            os.kill(self.pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def returncode(self) -> Optional[int]:
        try:
            return int(self.rc_path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None


_WRAPPER = """#!/bin/bash
# GENERATED by scripts/coordination/worker_runner.py — do not edit.
# Why a wrapper: the runner must own a pid it captured ITSELF (project hard rule:
# no name-pattern kills, ever). `$!` of the harness is that pid, written to a file
# the runner polls. The wrapper also tees the harness transcript to disk so the
# machine has EVIDENCE without ever reading pane text (D8).
set -u
exec > >(tee -a {transcript}) 2>&1
{argv} &
_pid=$!
printf '%s\\n' "$_pid" > {pidfile}
wait "$_pid"
_rc=$?
printf '%s\\n' "$_rc" > {rcfile}
exit "$_rc"
"""


def _write_wrapper(run_dir: Path, argv: list[str]) -> Path:
    path = run_dir / "spawn.sh"
    path.write_text(_WRAPPER.format(
        transcript=shlex.quote(str(run_dir / "harness-transcript.log")),
        pidfile=shlex.quote(str(run_dir / "harness.pid")),
        rcfile=shlex.quote(str(run_dir / "harness.rc")),
        argv=" ".join(shlex.quote(a) for a in argv),
    ), encoding="utf-8")
    path.chmod(0o755)
    return path


def _await_pid(run_dir: Path, timeout_s: float,
               popen: Optional[subprocess.Popen] = None) -> int:
    pidfile = run_dir / "harness.pid"
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            return int(pidfile.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            if popen is not None and popen.poll() is not None:
                # the wrapper itself died before writing a pid: fail now rather
                # than spin out the timeout on a process that no longer exists
                break
            time.sleep(0.05)
    raise RefusalError(
        f"worker did not report its pid within {timeout_s}s ({pidfile}). Refusing to run "
        f"unsupervised: without a pid captured by this process there is no lease to enforce, "
        f"and the only alternative — matching a process by name — is forbidden.")


def spawn_worker(argv: list[str], run_dir: Path, worktree: Path, cfg: dict,
                 *, mode: str = "tmux", harness: str = "claude",
                 window_name: str = "wpool") -> WorkerHandle:
    """Start the worker. VISIBLE by default (D8).

    `direct` mode exists so the whole lifecycle is testable with no tmux server;
    it is refused for any harness but `stub`, because a production worker the
    operator cannot watch or steer is the thing D8 forbids.
    """
    wrapper = _write_wrapper(run_dir, argv)

    if mode == "direct":
        if harness != "stub":
            raise RefusalError(
                f"spawn mode 'direct' requested for harness {harness!r} — direct spawn has no "
                f"visible pane, and D8 makes worker panes operator-watchable and "
                f"operator-steerable. Only the test `stub` harness may spawn headless.")
        popen = subprocess.Popen(
            ["/bin/bash", str(wrapper)], cwd=str(worktree),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        pid = _await_pid(run_dir, float(cfg["spawn_timeout_s"]), popen=popen)
        return WorkerHandle(pid, run_dir, popen=popen)

    session = str(cfg["tmux_session"])
    probe = subprocess.run(["tmux", "has-session", "-t", session],
                           capture_output=True, text=True)
    if probe.returncode != 0:
        raise RefusalError(
            f"tmux session {session!r} does not exist and this runner never creates one "
            f"(config tmux.allow_session_creation is authoritative). Refusing.")
    created = subprocess.run(
        ["tmux", "new-window", "-d", "-t", session, "-n", window_name,
         "-c", str(worktree), "-P", "-F", "#{window_id}", "/bin/bash", str(wrapper)],
        capture_output=True, text=True)
    if created.returncode != 0:
        raise RefusalError(f"tmux new-window failed: {created.stderr.strip()}")
    window_id = created.stdout.strip()
    try:
        pid = _await_pid(run_dir, float(cfg["spawn_timeout_s"]))
    except RefusalError:
        subprocess.run(["tmux", "kill-window", "-t", window_id], capture_output=True)
        raise
    return WorkerHandle(pid, run_dir, window_id=window_id, tmux_session=session)


def capture_scrollback(handle: WorkerHandle) -> Optional[Path]:
    """Capture pane scrollback AS EVIDENCE FOR A HUMAN.

    This is the ONLY place in this module that touches pane text, and its output
    is never parsed, matched, or branched on — it is written to a file, attached
    to a failed row, and read by a person. `capture-pane` here is not a decision
    channel; making it one would re-open the 94%-false-positive perception class.
    """
    if not handle.window_id:
        return None
    out = subprocess.run(["tmux", "capture-pane", "-p", "-S", "-", "-t", handle.window_id],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return None
    path = handle.run_dir / "pane-scrollback.log"
    path.write_text(out.stdout, encoding="utf-8")
    return path


# ------------------------------------------------------------- kill (D6)


def kill_owned(pid: int, grace_s: float, *, sig_term=signal.SIGTERM, sig_kill=signal.SIGKILL) -> dict:
    """SIGTERM → grace → SIGKILL, on a pid THIS process captured, then VERIFY.

    Signals go to the pid's process GROUP so the worker's subagents die with it —
    but the group is derived from the captured pid (`os.getpgid(pid)`), never
    matched by name. Two hard refusals guard that derivation: the runner never
    signals its own process group, and never signals group 1. A `pkill`-shaped
    kill on this shared host took out another session's `llama-server` twice and
    killed `earlyoom` (INC-20260731); the rule that came out of it is absolute.

    Death is VERIFIED, never assumed — the project rule is "never report success
    until confirmed".
    """
    def _dead() -> bool:
        # Reap first if this pid is our own child: a zombie IS dead, but
        # `os.kill(pid, 0)` succeeds against one, so an unreaped child reads as
        # alive forever and the SIGKILL escalation never terminates.
        try:
            os.waitpid(pid, os.WNOHANG)
        except (ChildProcessError, OSError):
            pass
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        return False

    result: dict[str, Any] = {"pid": pid, "term": False, "kill": False, "dead": False}
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        result["dead"] = True
        return result
    if pgid in (0, 1) or pgid == os.getpgrp():
        # Fall back to the single pid rather than signalling a group that
        # contains this runner (or init). Refusing to widen the blast radius.
        target, use_group = pid, False
    else:
        target, use_group = pgid, True
    result["pgid"] = pgid
    result["group_signalled"] = use_group

    def _signal(sig) -> None:
        if use_group:
            os.killpg(target, sig)
        else:
            os.kill(target, sig)

    try:
        _signal(sig_term)
        result["term"] = True
    except ProcessLookupError:
        result["dead"] = True
        return result

    deadline = time.monotonic() + grace_s
    while time.monotonic() < deadline:
        if _dead():
            result["dead"] = True
            return result
        time.sleep(0.1)

    try:
        _signal(sig_kill)
        result["kill"] = True
    except ProcessLookupError:
        result["dead"] = True
        return result

    for _ in range(50):
        if _dead():
            result["dead"] = True
            return result
        time.sleep(0.1)
    result["dead"] = False
    return result


# ----------------------------------------------------------- salvage (D6)


def _git(worktree: Path, *args: str, env: Optional[dict] = None, check: bool = True) -> str:
    full = dict(os.environ)
    if env:
        full.update(env)
    out = subprocess.run(["git", "-C", str(worktree), *args],
                         capture_output=True, text=True, env=full)
    if check and out.returncode != 0:
        raise SalvageError(f"git {' '.join(args)} failed in {worktree}: {out.stderr.strip()}")
    return out.stdout


def _git_hash_blob(worktree: Path, data: bytes, env: Optional[dict] = None) -> str:
    """Write `data` into the object store and return its sha.

    Via `--stdin` rather than a path: the evidence files live in the runner's
    runtime root, OUTSIDE the lane worktree, and `hash-object -- <abs path>`
    refuses a path outside the repository.
    """
    full = dict(os.environ)
    if env:
        full.update(env)
    out = subprocess.run(["git", "-C", str(worktree), "hash-object", "-w", "--stdin"],
                         input=data, capture_output=True, env=full)
    if out.returncode != 0:
        raise SalvageError(f"git hash-object failed in {worktree}: "
                           f"{out.stderr.decode('utf-8', 'replace').strip()}")
    return out.stdout.decode("utf-8").strip()


def dirty_paths(worktree: Path) -> list[str]:
    """Every path git considers changed or untracked, `-uall` so a new directory
    is enumerated file-by-file rather than collapsed to one directory entry.

    `--no-renames` deliberately: rename detection makes the enumeration a
    HEURISTIC, and the no-loss proof must compare a definite set.
    """
    raw = _git(worktree, "status", "--porcelain=v1", "-uall", "--no-renames", "-z")
    out, fields = [], raw.split("\0")
    for field in fields:
        if len(field) > 3:
            path = field[3:]
            # the runner's OWN lane lock is runner state, not the worker's work.
            # It is the one exclusion, and it is named here rather than pattern-
            # matched, so the exclusion set cannot quietly grow.
            if path == LANE_LOCK_NAME:
                continue
            out.append(path)
    return sorted(set(out))


def salvage_worktree(worktree: Path, task_id: str, *, evidence: Optional[dict] = None,
                     message: Optional[str] = None,
                     _stage_filter: Optional[Callable[[list[str]], list[str]]] = None) -> dict:
    """Commit a dead worker's uncommitted state to `refs/salvage/<task_id>`, and
    PROVE nothing was lost.

    Non-destructive by construction: the tree is assembled in a temporary index
    (`GIT_INDEX_FILE`), so the lane worktree's own index, HEAD and working files
    are untouched. Re-runnable; a second salvage of the same lane produces the
    same tree.

    THE PROOF. After writing the ref, this re-reads the committed tree and
    compares every enumerated path against the working tree byte-for-byte:
    present files must match their blob exactly, deleted files must be absent.
    Any mismatch raises `SalvageError`. That is the property the mutation test
    attacks via `_stage_filter` — a salvage that silently drops one file must
    FAIL, not return a plausible ref. Kill is allowed; loss is not.

    IGNORED FILES are outside the salvage set by design (build outputs, venvs,
    `__pycache__` — committing them would make salvage unusable at size) but
    they are ENUMERATED into the returned manifest, so "excluded" is visible
    rather than silent.
    """
    paths = dirty_paths(worktree)
    staged = list(paths) if _stage_filter is None else list(_stage_filter(list(paths)))

    index = worktree.parent / f".salvage-index-{task_id}-{os.getpid()}"
    env = {"GIT_INDEX_FILE": str(index)}
    try:
        head = _git(worktree, "rev-parse", "--verify", "HEAD", check=False).strip()
        if head:
            _git(worktree, "read-tree", head, env=env)
        else:
            _git(worktree, "read-tree", "--empty", env=env)

        if staged:
            _git(worktree, "add", "-A", "--", *staged, env=env)

        for name, path in sorted((evidence or {}).items()):
            if not path:
                continue
            src = Path(path)
            if not src.is_file():
                continue
            blob = _git_hash_blob(worktree, src.read_bytes(), env=env)
            _git(worktree, "update-index", "--add", "--cacheinfo",
                 f"100644,{blob},.salvage-evidence/{name}", env=env)

        tree = _git(worktree, "write-tree", env=env).strip()
        args = ["commit-tree", tree]
        if head:
            args += ["-p", head]
        args += ["-m", message or f"salvage: {task_id} (D6 kill-with-salvage, no loss)"]
        commit = _git(worktree, *args, env={**env,
                                            "GIT_AUTHOR_NAME": "worker_runner",
                                            "GIT_AUTHOR_EMAIL": "workerpool@epyc.local",
                                            "GIT_COMMITTER_NAME": "worker_runner",
                                            "GIT_COMMITTER_EMAIL": "workerpool@epyc.local"}).strip()
        ref = f"refs/salvage/{task_id}"
        _git(worktree, "update-ref", ref, commit)
    finally:
        try:
            index.unlink()
        except OSError:
            pass

    verify_salvage(worktree, commit, paths)
    ignored = [p for p in _git(worktree, "status", "--porcelain=v1", "--ignored=matching",
                               "-uall", "--no-renames", "-z").split("\0")
               if p.startswith("!! ")]
    return {
        "salvage_ref": ref,
        "commit": commit,
        "files": paths,
        "files_committed": len(paths),
        "ignored_excluded": [p[3:] for p in ignored],
        "evidence": sorted((evidence or {})),
        "verified": True,
    }


def verify_salvage(worktree: Path, commit: str, paths: list[str]) -> None:
    """Re-read what was written and compare it to the working tree.

    This is the whole no-loss guarantee. It reads the COMMITTED OBJECT, not the
    index it was built from — verifying the artifact, not your own intent to
    produce it (`feedback_verify_integrity_not_presence_of_own_edit`).
    """
    listing = _git(worktree, "ls-tree", "-r", "-z", "--name-only", commit)
    in_tree = {p for p in listing.split("\0") if p}
    missing, differing = [], []
    for rel in paths:
        src = worktree / rel
        if src.is_symlink():
            # a symlink's blob is its target string; compare that, never the
            # bytes it points at (which may be outside the tree entirely)
            if rel not in in_tree:
                missing.append(rel)
                continue
            blob = subprocess.run(["git", "-C", str(worktree), "cat-file", "blob", f"{commit}:{rel}"],
                                  capture_output=True)
            if blob.returncode != 0 or blob.stdout.decode("utf-8", "replace") != os.readlink(src):
                differing.append(rel)
        elif src.is_file():
            if rel not in in_tree:
                missing.append(rel)
                continue
            blob = subprocess.run(["git", "-C", str(worktree), "cat-file", "blob", f"{commit}:{rel}"],
                                  capture_output=True)
            if blob.returncode != 0 or blob.stdout != src.read_bytes():
                differing.append(rel)
        elif not src.exists():
            # a deletion: recoverable from the parent commit, must not reappear
            if rel in in_tree:
                differing.append(rel)
    if missing or differing:
        raise SalvageError(
            f"SALVAGE LOST WORK — commit {commit[:12]} in {worktree} is missing {missing} and "
            f"differs on {differing}. D6: kill is allowed, LOSS IS FORBIDDEN. The lane has NOT "
            f"been cleaned up; a human must inspect it before anything else touches it.")


# ------------------------------------------------------------------ report


REPORT_OUTCOMES = {"pass", "fail", "blocked", "skipped"}


def validate_report(obj: Any, expected_task_ids: list[str]) -> list[str]:
    """Schema check for `worker_report.v1`. Returns a list of errors (empty = valid).

    Hand-rolled and stdlib-only, matching session_bus.py's mini-validator posture.
    Three checks earn their place beyond structure:
      * `subagents_spawned` REQUIRED — the two-level fan-out multiplier is the
        point of the pool tier, and RTG-49/F-15 exist because it was
        self-reported in prose and therefore unmeasurable.
      * `tokens_used` REQUIRED — it is the D1 ceiling's only input.
      * `denials` REQUIRED (possibly empty) — an absent denial list and a clean
        run must not render identically (P2-3: never silent parity).
    """
    errors: list[str] = []
    if not isinstance(obj, dict):
        return [f"report is {type(obj).__name__}, expected object"]
    if obj.get("schema_version") != REPORT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {REPORT_SCHEMA_VERSION!r}, "
                      f"got {obj.get('schema_version')!r}")
    for key, kind in (("subagents_spawned", int), ("tokens_used", int)):
        value = obj.get(key)
        if isinstance(value, bool) or not isinstance(value, kind):
            errors.append(f"{key} is required and must be an integer (got {value!r})")
        elif value < 0:
            errors.append(f"{key} must be >= 0 (got {value!r})")
    denials = obj.get("denials")
    if not isinstance(denials, list):
        errors.append("denials is required and must be a list (empty list = no denials; an "
                      "ABSENT list and a clean run must not read identically)")
    else:
        for i, d in enumerate(denials):
            if not isinstance(d, dict) or not str(d.get("tool") or "").strip():
                errors.append(f"denials[{i}] must be an object with a non-empty `tool`")
    rows = obj.get("rows")
    if not isinstance(rows, list) or not rows:
        errors.append("rows is required and must be a non-empty list")
        return errors
    seen = set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"rows[{i}] must be an object")
            continue
        task_id = str(row.get("task_id") or "")
        if not task_id:
            errors.append(f"rows[{i}] has no task_id")
        elif task_id not in expected_task_ids:
            errors.append(f"rows[{i}].task_id {task_id!r} was not in this batch "
                          f"{expected_task_ids} — a worker may not report on a row it was "
                          f"not dispatched")
        elif task_id in seen:
            errors.append(f"rows[{i}].task_id {task_id!r} reported twice")
        seen.add(task_id)
        if row.get("outcome") not in REPORT_OUTCOMES:
            errors.append(f"rows[{i}].outcome must be one of {sorted(REPORT_OUTCOMES)} "
                          f"(got {row.get('outcome')!r})")
        for key in ("commits", "artifacts"):
            if key in row and not isinstance(row[key], list):
                errors.append(f"rows[{i}].{key} must be a list")
    return errors


def read_progress(run_dir: Path) -> tuple[Optional[str], set[str]]:
    """(row currently in progress, rows the worker declared complete).

    P2-6's timeout rule needs to distinguish the row a timed-out worker was
    ACTUALLY on from rows it never touched. `progress.jsonl` is a file the
    worker writes; it is not pane text and is not a completion signal — it only
    narrows blame at a timeout.
    """
    path = run_dir / "progress.jsonl"
    started: list[str] = []
    done: set[str] = set()
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            task_id, event = str(row.get("task_id") or ""), row.get("event")
            if not task_id:
                continue
            if event == "start":
                started.append(task_id)
            elif event == "complete":
                done.add(task_id)
    except OSError:
        return None, set()
    for task_id in reversed(started):
        if task_id not in done:
            return task_id, done
    return None, done


def classify_outcomes(brief: dict, report: Optional[dict], *, watch_result: str,
                      cfg: dict, run_dir: Path, salvage_ref: Optional[str],
                      report_errors: Optional[list[str]] = None) -> list[dict]:
    """Per-row outcomes. THE P2-6 RULE LIVES HERE.

    Static batching means one invocation can hold three rows. If it times out,
    exactly ONE row failed — the one in progress. The other two were never
    started, and marking them FAILED would manufacture two spurious defects and
    burn two rows' worth of premise screening. So: rows with a completion record
    keep their reported outcome, the in-progress row is FAILED with the salvage
    ref, and untouched rows go back to READY *unmarked* (no attempt increment,
    no failure_reason) — the row returns to the queue as if it had never been
    dispatched, because it hadn't.

    Denial audit (P2-3): a denied tool call NEVER renders as a pass. A denial
    carrying a `task_id` fails that row; an unattributed denial fails the whole
    batch, because "some tool call was refused somewhere in this run" is not a
    result anybody may accept as green.
    """
    briefed = [row["task_id"] for row in brief["rows"]]
    text_by_id = {row["task_id"]: row["task_text"] for row in brief["rows"]}
    ceiling = float(cfg["token_ceiling_per_batch"])

    in_progress, _progress_done = read_progress(run_dir)
    reported: dict[str, dict] = {}
    # An INVALID report is not a partially-trustworthy report. Reading rows out
    # of a document that failed its own schema is how a malformed field becomes
    # a green row; the whole document is set aside and every row falls to the
    # `report-invalid` branch below.
    if not report_errors and isinstance(report, dict) and isinstance(report.get("rows"), list):
        for row in report["rows"]:
            if isinstance(row, dict) and row.get("task_id"):
                reported[str(row["task_id"])] = row

    # P2-6 blame attribution at a timeout. `progress.jsonl` names the row the
    # worker was actually on. Without it, the deterministic fallback is "the
    # first briefed row with no completion record" — rows are worked in brief
    # order — and the rest are UNTOUCHED. Guessing wider would manufacture
    # spurious defects on rows that were never started.
    blamed: Optional[str] = None
    if watch_result == "lease-expired":
        unreported = [t for t in briefed if t not in reported]
        if in_progress in unreported:
            blamed = in_progress
        elif unreported:
            blamed = unreported[0]

    denials = (report or {}).get("denials") or []
    denied_ids = {str(d.get("task_id")) for d in denials
                  if isinstance(d, dict) and d.get("task_id")}
    batch_denied = bool(denials) and not denied_ids
    tokens = (report or {}).get("tokens_used")
    over_ceiling = isinstance(tokens, (int, float)) and float(tokens) > ceiling

    results = []
    for task_id in briefed:
        entry: dict[str, Any] = {"task_id": task_id, "task_text": text_by_id[task_id]}
        row = reported.get(task_id)

        if watch_result == "lease-expired" and task_id not in reported:
            if task_id == blamed:
                entry.update(status="FAILED", failure_reason="lease-expired",
                             salvage_ref=salvage_ref)
            else:
                entry.update(status="READY", requeued=True,
                             note="untouched at lease expiry — returned READY unmarked")
            results.append(entry)
            continue

        if row is None:
            if report_errors:
                entry.update(status="FAILED", failure_reason="report-invalid",
                             detail="; ".join(report_errors[:5]), salvage_ref=salvage_ref)
            elif report is None:
                entry.update(status="FAILED", failure_reason="no-report", salvage_ref=salvage_ref)
            else:
                entry.update(status="FAILED", failure_reason="row-unreported",
                             salvage_ref=salvage_ref)
            results.append(entry)
            continue

        outcome = row.get("outcome")
        if batch_denied or task_id in denied_ids:
            entry.update(status="FAILED", failure_reason="permission-denied",
                         denials=[d for d in denials
                                  if not d.get("task_id") or str(d.get("task_id")) == task_id])
        elif over_ceiling:
            entry.update(status="FAILED", failure_reason="token-ceiling-breach",
                         detail=f"tokens_used={tokens} > ceiling={ceiling:.0f} (D1)")
        elif outcome == "pass":
            entry.update(status="DONE_PASS")
        elif outcome == "skipped":
            entry.update(status="READY", requeued=True,
                         note="worker skipped the row — returned READY unmarked")
        else:
            entry.update(status="FAILED", failure_reason=f"worker-{outcome}")
        entry["commits"] = list(row.get("commits") or [])
        entry["artifacts"] = list(row.get("artifacts") or [])
        results.append(entry)
    return results


# ------------------------------------------------------------------ bus IO


def emit(bus_root: Path, agent: str, msg: dict) -> dict:
    """Append ONE message to `outbox/<agent>.jsonl`, schema-validated.

    Single writer, path-derived authorship (invariant 1): this module writes the
    workerpool outbox and its own heartbeat, and NOTHING else. It never writes
    `queue.jsonl` — that file is the coordinator-daemon's, and a runner that
    wrote queue rows directly would be the second writer the whole protocol is
    built to prevent. Status transitions are PROPOSED here and transcribed by
    the daemon.
    """
    path = bus_root / "outbox" / f"{agent}.jsonl"
    existing, _ = _read_jsonl(path)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    row = dict(msg)
    row.setdefault("schema_version", MSG_SCHEMA_VERSION)
    row.setdefault("ts", _utcnow_iso())
    row.setdefault("from", agent)
    row.setdefault("to", "coordinator-agent")
    row.setdefault("id", f"msg-{stamp}-{len(existing) + 1}-{agent}")
    validate_row(bus_root, row, "msg")
    session_bus._check_routing_intent(bus_root, row)
    _append_jsonl(path, row)
    return row


def heartbeat(bus_root: Path, agent: str, state: str, task_id: str = "") -> None:
    _write_atomic(bus_root / "heartbeats" / f"{agent}.json",
                  {"agent": agent, "state": state, "task_id": task_id, "ts": _utcnow_iso()})


def claim_row(bus_root: Path, agent: str, task_text: str) -> bool:
    """Reuse session_bus's O_EXCL claim. Not reimplemented — the whole point of
    that mechanism is that there is exactly ONE of it; a second implementation
    with its own key derivation would collide on nothing."""
    ns = argparse.Namespace(bus_root=str(bus_root), agent=agent, row=task_text,
                            list=False, release=False)
    return session_bus.cmd_claim(ns) == 0


def release_row(bus_root: Path, agent: str, task_text: str) -> None:
    ns = argparse.Namespace(bus_root=str(bus_root), agent=agent, row=task_text,
                            list=False, release=True)
    try:
        session_bus.cmd_claim(ns)
    except BusError as exc:
        print(f"worker_runner: WARN could not release claim: {exc}", file=sys.stderr)


# --------------------------------------------------------- audit + promotion


AUDIT_POINTER_KEYS = ("task_ids", "worktree", "commit_range", "report_path", "brief_path",
                      "transcript_path", "scrollback_path", "salvage_ref", "lane", "batch_id",
                      "harness", "run_dir")


def audit_packet(ctx: dict) -> dict:
    """POINTERS ONLY. Never the worker's own claims.

    P2-7's auditor derives the diff from git independently and runs its own
    mutation probe. If this packet carried the worker's summary, the audit would
    be anchored on the assertion it exists to test — the reviewer would be
    reading the defendant's statement of the case. So the packet is built from a
    WHITELIST of pointer keys, and a test asserts that a sentinel string planted
    in the worker's summary appears nowhere in it.
    """
    return {k: ctx[k] for k in AUDIT_POINTER_KEYS if ctx.get(k) is not None}


def promotion_row(ctx: dict, results: list[dict]) -> Optional[dict]:
    """A typed promotion row for the merge gate — only for rows that PASSED and
    actually produced commits. Serialized through merge_gate.py / serialized_push
    one at a time (P2-8); this proposes, it never merges."""
    passed = [r for r in results if r["status"] == "DONE_PASS" and r.get("commits")]
    if not passed:
        return None
    return {
        "task_ids": [r["task_id"] for r in passed],
        "worktree": ctx["worktree"],
        "commit_range": ctx.get("commit_range"),
        "commits": sorted({c for r in passed for c in r["commits"]}),
        "gate": "scripts/coordination/merge_gate.py",
        "serializer": "scripts/coordination/serialized_push.py",
    }


# ------------------------------------------------------------------- parking


def park_rows(bus_root: Path, agent: str, rows: list[dict], verdicts: dict,
              runtime_root: Path) -> list[dict]:
    """Park a row whose premise is not `still-needed`, and emit ONCE.

    A screener that refuses every tick is a screener nobody reads. So the
    refusal is de-duplicated on (row identity, verdict): the same row parked for
    the same reason emits nothing the second time, and a CHANGED verdict emits
    again. Emit-once-on-state-change is the same discipline the alarm channel
    uses; a per-tick refusal is noise wearing a defect's clothes.
    """
    state_dir = runtime_root / "parked"
    state_dir.mkdir(parents=True, exist_ok=True)
    emitted = []
    for row in rows:
        verdict = verdicts[row["task_id"]]
        key = _claim_key(row["task_text"])
        state_path = state_dir / f"{key}.json"
        previous = None
        try:
            previous = json.loads(state_path.read_text(encoding="utf-8")).get("verdict")
        except (OSError, json.JSONDecodeError):
            previous = None
        _write_atomic(state_path, {"verdict": verdict["verdict"], "task_id": row["task_id"],
                                   "reason": verdict["reason"], "ts": _utcnow_iso()})
        if previous == verdict["verdict"]:
            continue
        emitted.append(emit(bus_root, agent, {
            "kind": "requeue",
            "task_id": row["task_id"],
            "to": "coordinator-agent",
            "payload": {
                "status": "READY",
                "parked_reason": f"premise-{verdict['verdict']}",
                "task_text": row["task_text"],
                "screener_evidence": verdict["evidence"][:500],
                "screener_reason": verdict["reason"][:500],
            },
        }))
        emitted.append(emit(bus_root, agent, {
            "kind": "task-propose",
            "task_id": f"{row['task_id']}-premise-fix",
            "to": "coordinator-agent",
            "needs_routing_to": ["coordinator-agent"],
            "action_required": True,
            "assignee": "coordinator-agent",
            "payload": {
                "lane": "none",
                "gating": "none",
                "spec_ref": str(row.get("source_handoff")
                                or "handoffs/active/loop-owned-fleet-implementation.md#P2-2"),
                "summary": (f"Re-verify the premise of {row['task_id']} "
                            f"(screener: {verdict['verdict']})"),
                "task_text": (f"Premise check on {row['task_id']} returned "
                              f"{verdict['verdict']}: re-verify the row's premise against "
                              f"current reality and either re-screen it or close it. "
                              f"Row: {row['task_text'][:300]}"),
                "row_ref": row.get("row_ref"),
                "screener_evidence": verdict["evidence"][:500],
            },
        }))
    return emitted


# ---------------------------------------------------------------- lifecycle


def load_assignment(args: argparse.Namespace) -> dict:
    if args.assignment:
        data = json.loads(Path(args.assignment).read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("rows"), list):
            return data
        raise RefusalError("assignment file must be an object with a `rows` list")
    if not (args.task_id and args.row_text):
        raise RefusalError("need --assignment <file>, or --task-id and --row-text")
    return {"rows": [{"task_id": args.task_id, "task_text": args.row_text,
                      "row_ref": args.row_ref, "source_handoff": args.source_handoff,
                      "screened_by": args.screened_by}]}


def check_batch(rows: list[dict], cfg: dict) -> None:
    """P2-6. Batching is STATIC: the batch is fixed before the worker starts and
    never grows. The cap is 3 and every row must come from the SAME source
    handoff — batching unrelated rows into one invocation makes a timeout blame
    a context the other rows never shared."""
    cap = min(int(cfg["batch_cap"]), HARD_BATCH_CAP)
    if not rows:
        raise RefusalError("assignment has no rows")
    if len(rows) > cap:
        raise RefusalError(
            f"batch of {len(rows)} rows exceeds the P2-6 cap of {cap}. Static batching shares "
            f"ONE invocation across rows from one source handoff; beyond the cap a timeout "
            f"destroys more screened work than the invocation saved.")
    sources = {str(r.get("source_handoff") or "") for r in rows}
    if len(rows) > 1 and len(sources) > 1:
        raise RefusalError(
            f"batch mixes source handoffs {sorted(sources)} — P2-6 batches rows from the SAME "
            f"source handoff only.")
    ids = [str(r.get("task_id") or "") for r in rows]
    if "" in ids or len(set(ids)) != len(ids):
        raise RefusalError(f"batch task_ids must be present and unique (got {ids})")


def run(args: argparse.Namespace) -> int:
    bus_root = Path(args.bus_root)
    agent = args.agent
    cfg = load_pool_config(bus_root, args.lane)
    if args.harness:
        cfg["worker_harness"] = args.harness

    # ---- fail-closed preflight; nothing is spawned until every gate passes ----
    _require_roster_id(bus_root, agent)            # P2-5 wiring must exist first
    check_enabled(cfg, getattr(args, 'pilot_override', False))
    check_bounds(cfg)
    check_provider_pin(cfg)
    check_rule8_ack(cfg)
    harness = resolve_harness(cfg)
    worktree = resolve_lane(cfg, args.lane)
    runtime_root = Path(str(cfg["runtime_root"]))
    check_concurrency(cfg, Path(str(cfg["pool_root"])))

    assignment = load_assignment(args)
    rows = assignment["rows"]
    check_batch(rows, cfg)

    batch_id = args.batch_id or f"{rows[0]['task_id']}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = runtime_root / "runs" / batch_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # ---- 1. claim (O_EXCL, reused from session_bus) ----
    claimed: list[dict] = []
    for row in rows:
        if claim_row(bus_root, agent, row["task_text"]):
            claimed.append(row)
        else:
            print(f"worker_runner: row already claimed, dropping from batch: "
                  f"{row['task_id']}", file=sys.stderr)
    if not claimed:
        print("worker_runner: every row in the batch is claimed by someone else; nothing to do")
        return 0
    rows = claimed

    def _release_all() -> None:
        for row in rows:
            release_row(bus_root, agent, row["task_text"])

    heartbeat(bus_root, agent, "working", batch_id)
    try:
        # ---- 3. premise preflight ----
        verdicts = {row["task_id"]: screen_premise_safe(row) for row in rows}
        not_needed = [r for r in rows if verdicts[r["task_id"]]["verdict"] != "still-needed"]
        if not_needed:
            park_rows(bus_root, agent, not_needed, verdicts, runtime_root)
            for row in not_needed:
                release_row(bus_root, agent, row["task_text"])
            rows = [r for r in rows if r not in not_needed]
            if not rows:
                print(f"worker_runner: parked {len(not_needed)} row(s); no worker spawned")
                heartbeat(bus_root, agent, "idle", batch_id)
                return 0

        # ---- 2. typed brief ----
        report_path = run_dir / "report.json"
        lease_expires = datetime.now(timezone.utc) + timedelta(seconds=float(cfg["lease_s"]))
        brief = build_brief(rows, batch_id=batch_id, lane=args.lane, worktree=worktree,
                            report_path=report_path, cfg=cfg,
                            lease_expires_ts=lease_expires.isoformat())
        for row in brief["rows"]:
            row["premise"] = verdicts[row["task_id"]]["verdict"]
        brief_path = run_dir / "brief.json"
        brief_path.write_text(json.dumps(brief, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        # ---- 4. permission profile (D2b) ----
        permissions_path = write_permission_profile(cfg, run_dir)

        # ---- 5. lane lockfile ----
        with LaneLock(worktree) as _lock:
            base_commit = _git(worktree, "rev-parse", "HEAD", check=False).strip() or None

            # ---- 6. spawn in a VISIBLE pane (D8) ----
            ctx = {
                "prompt": build_prompt(brief_path, report_path, worktree),
                "brief_path": str(brief_path),
                "report_path": str(report_path),
                "permissions_path": str(permissions_path),
                "worktree": str(worktree),
                "run_dir": str(run_dir),
                "python": sys.executable,
                "stub_cmd": str(cfg.get("stub_cmd") or ""),
                "batch_id": batch_id,
            }
            argv = build_harness_argv(harness, cfg, ctx)
            handle = spawn_worker(argv, run_dir, worktree, cfg, mode=args.spawn_mode,
                                  harness=harness, window_name=f"wpool-{args.lane}")
            print(f"worker_runner: spawned {harness} pid={handle.pid} "
                  f"window={handle.window_id or '(direct)'} lane={args.lane}")

            # ---- 7. watch ----
            watch_result = watch(handle, report_path, cfg, lease_expires)

            # ---- D6 kill-with-salvage ----
            salvage: Optional[dict] = None
            kill_record: Optional[dict] = None
            if handle.alive():
                scrollback = capture_scrollback(handle)
                kill_record = kill_owned(handle.pid, float(cfg["grace_s"]))
                if not kill_record["dead"]:
                    raise SalvageError(
                        f"pid {handle.pid} survived SIGTERM+grace+SIGKILL. Not proceeding: an "
                        f"undead worker may still be writing the tree this salvage would "
                        f"claim to have captured.")
                try:
                    salvage = salvage_worktree(
                        worktree, batch_id,
                        evidence={"harness-transcript.log": handle.transcript_path,
                                  "pane-scrollback.log": scrollback,
                                  "brief.json": brief_path},
                        message=f"salvage: {batch_id} killed at lease expiry (D6)")
                except SalvageError:
                    raise
                if handle.window_id:
                    subprocess.run(["tmux", "kill-window", "-t", handle.window_id],
                                   capture_output=True)

            # ---- 8. collect ----
            report, report_errors = read_report(report_path, [r["task_id"] for r in rows])
            results = classify_outcomes(
                brief, report, watch_result=watch_result, cfg=cfg, run_dir=run_dir,
                salvage_ref=(salvage or {}).get("salvage_ref"), report_errors=report_errors)
            head_commit = _git(worktree, "rev-parse", "HEAD", check=False).strip() or None

        # ---- 9. bus writes, audit packet (pointers only), promotion row ----
        ctx_out = {
            "task_ids": [r["task_id"] for r in rows],
            "worktree": str(worktree),
            "lane": args.lane,
            "batch_id": batch_id,
            "harness": harness,
            "run_dir": str(run_dir),
            "brief_path": str(brief_path),
            "report_path": str(report_path),
            "transcript_path": str(handle.transcript_path),
            "scrollback_path": str(run_dir / "pane-scrollback.log")
                               if (run_dir / "pane-scrollback.log").exists() else None,
            "commit_range": (f"{base_commit}..{head_commit}"
                             if base_commit and head_commit and base_commit != head_commit
                             else None),
            "salvage_ref": (salvage or {}).get("salvage_ref"),
        }
        write_results(bus_root, agent, results, report, ctx_out, salvage, kill_record, cfg)
        for row in rows:
            release_row(bus_root, agent, row["task_text"])
        heartbeat(bus_root, agent, "idle", batch_id)
        print(json.dumps({"batch_id": batch_id, "watch": watch_result,
                          "results": [{"task_id": r["task_id"], "status": r["status"]}
                                      for r in results],
                          "salvage_ref": (salvage or {}).get("salvage_ref")}, indent=2))
        return 0
    except SalvageError:
        heartbeat(bus_root, agent, "idle", batch_id)
        raise
    except Exception:
        _release_all()
        heartbeat(bus_root, agent, "idle", batch_id)
        raise


def watch(handle: WorkerHandle, report_path: Path, cfg: dict,
          lease_expires: datetime) -> str:
    """Poll for: a valid-looking report, process exit, or lease expiry.

    Three signals, no fourth: pane text is not consulted (D8). A report that
    appears while the process still runs starts a bounded grace for the process
    to exit on its own; if it does not, the lease path takes it — every kill is
    followed by salvage, so a lingering worker cannot lose work either.
    """
    poll = float(cfg["poll_s"])
    post_grace = float(cfg["post_report_grace_s"])
    report_seen_at: Optional[float] = None
    while True:
        if not handle.alive():
            return "exit"
        if report_path.exists():
            if report_seen_at is None:
                report_seen_at = time.monotonic()
            elif time.monotonic() - report_seen_at > post_grace:
                return "report"
        if datetime.now(timezone.utc) >= lease_expires:
            return "lease-expired"
        time.sleep(poll)


def read_report(report_path: Path, expected_ids: list[str]) -> tuple[Optional[dict], list[str]]:
    if not report_path.exists():
        return None, ["report file was never written"]
    try:
        obj = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"report is unreadable/invalid JSON: {exc}"]
    return obj, validate_report(obj, expected_ids)


def write_results(bus_root: Path, agent: str, results: list[dict], report: Optional[dict],
                  ctx: dict, salvage: Optional[dict], kill_record: Optional[dict],
                  cfg: dict) -> list[dict]:
    """The `workerpool` identity's report to the bus: one message per row, plus
    the pointer packet for the auditor and (when anything passed) a promotion
    row. Row status is PROPOSED — the daemon transcribes into queue.jsonl."""
    written = []
    for row in results:
        payload: dict[str, Any] = {
            "status": row["status"],
            "task_text": row["task_text"],
            "batch_id": ctx["batch_id"],
            "lane": ctx["lane"],
            "worktree": ctx["worktree"],
            "report_path": ctx["report_path"],
        }
        for key in ("failure_reason", "salvage_ref", "parked_reason", "detail", "note",
                    "commits", "artifacts", "denials"):
            if row.get(key):
                payload[key] = row[key]
        if row["status"] == "READY" and row.get("requeued"):
            payload["unmarked"] = True
        if isinstance(report, dict):
            payload["subagents_spawned"] = report.get("subagents_spawned")
            payload["tokens_used"] = report.get("tokens_used")
        kind = "requeue" if row["status"] == "READY" else "task-complete"
        written.append(emit(bus_root, agent, {
            "kind": kind, "task_id": row["task_id"], "to": "coordinator-agent",
            "payload": payload,
        }))

    written.append(emit(bus_root, agent, {
        "kind": "finding", "task_id": ctx["batch_id"], "to": "auditor",
        "needs_routing_to": ["auditor"], "action_required": True, "assignee": "auditor",
        "payload": {"audit_packet": audit_packet(ctx),
                    "note": "pointers only — derive the diff from git independently"},
    }))

    promo = promotion_row(ctx, results)
    if promo:
        written.append(emit(bus_root, agent, {
            "kind": "task-propose", "task_id": f"{ctx['batch_id']}-promote",
            "to": "coordinator-agent", "needs_routing_to": ["coordinator-agent"],
            "action_required": True, "assignee": "coordinator-agent",
            "payload": {"lane": "none", "gating": "none",
                        "spec_ref": "handoffs/active/loop-owned-fleet-implementation.md#P2-8",
                        "summary": f"Merge-gate promotion for batch {ctx['batch_id']}",
                        "task_text": f"Promote pool-worker batch {ctx['batch_id']} "
                                     f"({', '.join(promo['task_ids'])}) through the merge gate",
                        "promotion": promo},
        }))

    if salvage or kill_record:
        written.append(emit(bus_root, agent, {
            "kind": "defect", "task_id": ctx["batch_id"], "to": "coordinator-agent",
            "needs_routing_to": ["coordinator-agent"], "action_required": True,
            "assignee": "coordinator-agent",
            "payload": {"kill": kill_record, "salvage": salvage,
                        "note": "D6 kill-with-salvage executed; state is preserved at the "
                                "salvage ref and must not be discarded"},
        }))
    return written


# ------------------------------------------------------------------- parser


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run ONE pool-worker assignment and exit.")
    p.add_argument("--bus-root", default=str(get_bus_root()))
    p.add_argument("--agent", default=WORKERPOOL_AGENT)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="claim → brief → screen → spawn → watch → collect")
    r.add_argument("--lane", required=True, help="pool lane name (lane0..lane3) or absolute path")
    r.add_argument("--assignment", help="JSON file: {rows: [{task_id, task_text, ...}]}")
    r.add_argument("--task-id")
    r.add_argument("--row-text")
    r.add_argument("--row-ref", help="file.md:LINE — a HINT; task_text is the identity")
    r.add_argument("--source-handoff")
    r.add_argument("--screened-by")
    r.add_argument("--batch-id")
    r.add_argument("--harness", help="override worker_harness for this run (D2)")
    r.add_argument("--pilot-override", action="store_true",
                   help="supervised manual run while worker_pool.enabled is false (P2-5 proving "
                        "run); never bypasses the rule-8 ack")
    r.add_argument("--spawn-mode", choices=("tmux", "direct"), default="tmux",
                   help="direct is test-only and refused for any harness but `stub`")
    r.set_defaults(func=run)
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except RefusalError as exc:
        print(f"worker_runner: REFUSED — {exc}", file=sys.stderr)
        return 2
    except SalvageError as exc:
        print(f"worker_runner: SALVAGE FAILURE — {exc}", file=sys.stderr)
        return 3
    except BusError as exc:
        print(f"worker_runner: BUS — {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"worker_runner: ERROR — {type(exc).__name__}: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
