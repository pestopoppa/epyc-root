"""Per-(role, mode) rolling telemetry for adaptive seeding dispatch.

Tracks recent outcomes per combo so the seeding loop can:
- Set timeouts based on observed P95 latency (avoid the 105s/120s
  pre-empt that wastes ~100s of useful inference work).
- Skip combos whose recent timeout rate is above threshold (don't
  rediscover that architect_general:repl times out by burning another
  120s on it).
- Bail out of a question early when accumulated wall-clock exceeds a
  budget (adaptive batch-size at the question level).
- Persist completed batch durations across autopilot restarts so the next
  seed wave can start with the previous batch-size signal.

Thresholds are read once at import-time from env vars so operators can
tune without code changes:
    SEEDING_TELEMETRY_WINDOW           rolling window size per combo (30)
    SEEDING_TELEMETRY_P95_MIN_SAMPLES  min successes before P95 used (5)
    SEEDING_TELEMETRY_P95_MULT         multiplier on P95 for timeout (1.30)
    SEEDING_TELEMETRY_TIMEOUT_RATIO    skip if recent timeouts >= this (0.50)
    SEEDING_TELEMETRY_TIMEOUT_MIN_N    min samples before skip kicks in (4)
"""

from __future__ import annotations

import json
import logging
import os
import statistics
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


_WINDOW = _env_int("SEEDING_TELEMETRY_WINDOW", 30)
_P95_MIN_SAMPLES = _env_int("SEEDING_TELEMETRY_P95_MIN_SAMPLES", 5)
_P95_MULT = _env_float("SEEDING_TELEMETRY_P95_MULT", 1.30)
_TIMEOUT_RATIO_SKIP = _env_float("SEEDING_TELEMETRY_TIMEOUT_RATIO", 0.50)
_TIMEOUT_MIN_N = _env_int("SEEDING_TELEMETRY_TIMEOUT_MIN_N", 4)
_MAX_RECOMMEND_TIMEOUT_S = _env_int("SEEDING_TELEMETRY_MAX_TIMEOUT_S", 600)
_PERSIST_BATCH_HISTORY = os.environ.get(
    "SEEDING_BATCH_TELEMETRY_PERSIST", "1"
).strip().lower() not in {"0", "false", "no", "off"}
_BATCH_HISTORY_PATH = os.environ.get(
    "SEEDING_BATCH_TELEMETRY_PATH",
    "/mnt/raid0/llm/tmp/seeding_batch_telemetry.jsonl",
)


@dataclass
class ComboStats:
    """Rolling window of outcomes for one (role, mode) combo."""
    elapsed_s: deque = field(default_factory=lambda: deque(maxlen=_WINDOW))
    timed_out: deque = field(default_factory=lambda: deque(maxlen=_WINDOW))
    last_record_ts: float = 0.0

    def record(self, elapsed_s: float, was_timeout: bool) -> None:
        self.elapsed_s.append(float(elapsed_s))
        self.timed_out.append(bool(was_timeout))
        self.last_record_ts = time.time()

    def successful_elapsed(self) -> list[float]:
        return [e for e, t in zip(self.elapsed_s, self.timed_out) if not t]

    def p95_seconds(self) -> Optional[float]:
        successes = self.successful_elapsed()
        if len(successes) < _P95_MIN_SAMPLES:
            return None
        if len(successes) < 20:
            # quantiles() with n=20 needs >=20 data points to give a true 95th
            # percentile; for smaller windows use max(successes) as a
            # conservative upper-bound proxy.
            return max(successes)
        try:
            return statistics.quantiles(successes, n=20)[18]
        except statistics.StatisticsError:
            return max(successes) if successes else None

    def timeout_rate(self) -> float:
        if len(self.timed_out) < _TIMEOUT_MIN_N:
            return 0.0
        return sum(self.timed_out) / len(self.timed_out)

    def should_skip(self) -> tuple[bool, str]:
        rate = self.timeout_rate()
        if rate >= _TIMEOUT_RATIO_SKIP:
            return True, (
                f"timeout rate {rate * 100:.0f}% over last "
                f"{len(self.timed_out)} attempts"
            )
        return False, ""

    def summary(self) -> dict:
        return {
            "samples": len(self.elapsed_s),
            "timeouts": int(sum(self.timed_out)),
            "timeout_rate": self.timeout_rate(),
            "p95_seconds": self.p95_seconds(),
            "median_seconds": (
                statistics.median(self.successful_elapsed())
                if self.successful_elapsed()
                else None
            ),
        }


# Single in-process store. Keyed by "role:mode".
_stats: dict[str, ComboStats] = {}


def _key(role: str, mode: str) -> str:
    return f"{role}:{mode}"


def record_outcome(
    role: str,
    mode: str,
    elapsed_s: float,
    was_timeout: bool,
) -> None:
    """Record one combo dispatch outcome. Safe to call from any thread
    (single-threaded seeder, but defensive in case of future parallelism)."""
    if not role:
        return
    _stats.setdefault(_key(role, mode), ComboStats()).record(elapsed_s, was_timeout)


def recommended_timeout(role: str, mode: str, base_timeout: int) -> int:
    """Return a timeout in seconds that's adapted to observed P95 latency.

    Returns `base_timeout` if we don't have enough samples yet to compute
    P95. Otherwise returns `max(base_timeout, p95 * P95_MULT + 5)` clamped
    to MAX_RECOMMEND_TIMEOUT_S. The +5s padding gives a small grace window
    above the P95 to absorb jitter.
    """
    s = _stats.get(_key(role, mode))
    if s is None:
        return base_timeout
    p95 = s.p95_seconds()
    if p95 is None:
        return base_timeout
    adapted = int(p95 * _P95_MULT + 5)
    return min(_MAX_RECOMMEND_TIMEOUT_S, max(base_timeout, adapted))


def should_skip(role: str, mode: str) -> tuple[bool, str]:
    """Return (True, reason) if this combo should be skipped based on
    recent timeout rate; otherwise (False, "")."""
    s = _stats.get(_key(role, mode))
    if s is None:
        return False, ""
    return s.should_skip()


def get_stats(role: str | None = None, mode: str | None = None) -> dict:
    """Read-only view of current stats, optionally filtered to one role/mode."""
    out = {}
    for key, s in _stats.items():
        r, m = key.split(":", 1)
        if role and r != role:
            continue
        if mode and m != mode:
            continue
        out[key] = s.summary()
    return out


def reset(clear_persisted: bool = False) -> None:
    """Clear all stats. Useful in tests; not used in production."""
    global _loaded_persisted_batches
    _stats.clear()
    _recent_batches.clear()
    _loaded_persisted_batches = True
    if clear_persisted:
        try:
            _batch_history_path().unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass


# ── Lock-pressure heuristic ─────────────────────────────────────────────
#
# Before enqueueing another heavy request when the previous one has been
# running for a long time, the seeder can call lock_pressure_too_high().
# Uses /proc/locks via the same helper the orchestrator's inference_lock
# module exposes — cheap, accurate, no extra syscall path.

_HEAVY_LOCK_PATH = "/mnt/raid0/llm/tmp/heavy_model.lock"


# ── Batch-level telemetry ───────────────────────────────────────────────
#
# Tracks recent seed_batch wall-clock durations + their question counts so
# the autopilot can adapt n_questions for future batches. A batch that
# burns 2400s for 10 questions = 240s/question. Under a 900s budget, the
# right next batch is 3-4 questions, not 10. Without this, the autopilot
# keeps requesting 10-question batches and the seeder keeps grinding for
# 40 minutes per trial.

_recent_batches: deque = deque(maxlen=20)  # [(n_questions, duration_s, ts), ...]
_loaded_persisted_batches = False


def _batch_history_path() -> Path:
    return Path(_BATCH_HISTORY_PATH)


def _load_persisted_batches_once() -> None:
    global _loaded_persisted_batches
    if _loaded_persisted_batches or not _PERSIST_BATCH_HISTORY:
        return
    _loaded_persisted_batches = True
    path = _batch_history_path()
    if not path.exists():
        return
    try:
        for line in path.read_text().splitlines()[-_recent_batches.maxlen:]:
            if not line.strip():
                continue
            rec = json.loads(line)
            n = int(rec.get("n_questions", 0))
            d = float(rec.get("duration_s", 0.0))
            ts = float(rec.get("ts", 0.0) or 0.0)
            if n > 0 and d > 0:
                _recent_batches.append((n, d, ts))
    except Exception as exc:
        logger.debug("could not load persisted seed batch telemetry: %s", exc)


def _append_persisted_batch(n_questions: int, duration_s: float, ts: float) -> None:
    if not _PERSIST_BATCH_HISTORY:
        return
    path = _batch_history_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "ts": ts,
                        "n_questions": int(n_questions),
                        "duration_s": float(duration_s),
                    },
                    separators=(",", ":"),
                )
                + "\n"
            )
    except Exception as exc:
        logger.debug("could not persist seed batch telemetry: %s", exc)


def record_batch_duration(n_questions: int, duration_s: float) -> None:
    """Record a completed seed_batch's question count + wall-clock duration."""
    if n_questions <= 0 or duration_s <= 0:
        return
    _load_persisted_batches_once()
    ts = time.time()
    _recent_batches.append((int(n_questions), float(duration_s), ts))
    _append_persisted_batch(n_questions, duration_s, ts)


def median_seconds_per_question() -> Optional[float]:
    """Median (duration_s / n_questions) across recent batches, or None
    if no batches recorded yet."""
    _load_persisted_batches_once()
    if not _recent_batches:
        return None
    rates = [d / n for n, d, _ in _recent_batches if n > 0]
    if not rates:
        return None
    return statistics.median(rates)


def adaptive_batch_size(
    requested_n: int,
    budget_s: Optional[float] = None,
    min_n: int = 2,
) -> tuple[int, str]:
    """Recommend an n_questions value that should fit within `budget_s`
    based on recent observed seconds-per-question.

    Args:
        requested_n: The autopilot's requested batch size.
        budget_s: Wall-clock budget in seconds. None = read env var.
        min_n: Floor on recommended n (keep at least this many for signal).

    Returns:
        (recommended_n, reason) — recommended_n <= requested_n; reason is
        a one-line human explanation. If telemetry is empty or signal
        favors the request, recommended_n == requested_n.
    """
    if budget_s is None:
        budget_s = float(
            os.environ.get("SEEDING_BATCH_BUDGET_S", "900")
        )
    if requested_n <= min_n or budget_s <= 0:
        return requested_n, "below floor or no budget — using requested"

    rate = median_seconds_per_question()
    if rate is None:
        return requested_n, "no batch history yet — using requested"

    # Per-batch fixed overhead (T0 eval after batch, _wait_for_heavy_models
    # at start, etc.) — empirically 30-60s. Reserve 60s of the budget for
    # this so the per-question math stays honest.
    OVERHEAD_S = 60.0
    workable_budget = max(budget_s - OVERHEAD_S, 60.0)
    fits = int(workable_budget / rate)
    if fits >= requested_n:
        return requested_n, (
            f"recent rate {rate:.0f}s/q × {requested_n}q = "
            f"{rate * requested_n:.0f}s ≤ budget {budget_s:.0f}s"
        )
    recommended = max(min_n, fits)
    return recommended, (
        f"recent rate {rate:.0f}s/q × {requested_n}q = "
        f"{rate * requested_n:.0f}s > budget {budget_s:.0f}s — "
        f"scaled to {recommended}q ({rate * recommended:.0f}s)"
    )


def batch_summary() -> dict:
    """Snapshot of recent batches for diagnostics."""
    _load_persisted_batches_once()
    return {
        "n_recent": len(_recent_batches),
        "median_s_per_q": median_seconds_per_question(),
        "recent": [
            {"n_questions": n, "duration_s": d, "rate_s_per_q": d / max(n, 1)}
            for n, d, _ in list(_recent_batches)[-5:]
        ],
    }


def lock_pressure_too_high(min_holder_age_s: float = 60.0) -> tuple[bool, str]:
    """Check if any process has been holding the heavy lock for >=
    min_holder_age_s seconds.

    Best-effort: returns (False, "") on any error so caller can fall through
    to the normal _wait_for_heavy_models_idle() loop. Uses ps to get the
    holder's elapsed time (which is process-start age, not lock-acquire age
    — but if the holder is a llama-server subprocess started by the bench,
    they're equivalent within a few seconds).
    """
    try:
        import subprocess
        from pathlib import Path

        lock_path = Path(_HEAVY_LOCK_PATH)
        if not lock_path.exists():
            return False, ""
        inode = str(lock_path.stat().st_ino)

        owner_pids: list[str] = []
        try:
            with open("/proc/locks", "r") as fh:
                for line in fh:
                    parts = line.split()
                    if len(parts) < 6:
                        continue
                    pid, dev_inode = parts[4], parts[5]
                    if not pid.isdigit():
                        continue
                    if dev_inode.rsplit(":", 1)[-1] == inode:
                        owner_pids.append(pid)
        except Exception:
            return False, ""

        if not owner_pids:
            return False, ""

        # Get etimes (elapsed seconds) for each holder
        result = subprocess.run(
            ["ps", "-o", "pid=,etimes=,comm="] + ["-p"] + [",".join(owner_pids)],
            capture_output=True, text=True, timeout=2,
        )
        if result.returncode != 0:
            return False, ""

        for line in result.stdout.strip().splitlines():
            parts = line.split(None, 2)
            if len(parts) < 2:
                continue
            try:
                etimes = int(parts[1])
            except ValueError:
                continue
            if etimes >= min_holder_age_s:
                comm = parts[2] if len(parts) > 2 else "?"
                return True, (
                    f"lock held by pid={parts[0]} ({comm}) "
                    f"for {etimes}s (>={min_holder_age_s:.0f}s threshold)"
                )

        return False, ""
    except Exception:
        return False, ""
