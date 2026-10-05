#!/usr/bin/env python3
"""Run or plan the A7 EvalTower eval-batch serving A/B window.

This is the representative follow-up to the eval-batch serving activation
smoke. It keeps the production path default-off, packages the current-vs-
eval-batch EvalTower comparison, and always rolls back the temporary API flag
unless ``--keep-enabled`` is explicit.

Default mode is plan-only. Live mutation/evaluation requires both ``--apply``
and ``--confirm-clean-window``.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import signal
import sys
import time
from typing import Any, Callable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
AUTOPILOT_DIR = PROJECT_ROOT / "scripts" / "autopilot"
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_EVAL_BATCH_URL = "http://localhost:18070"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "orchestration" / "reports"
TIER_REPORT_SCHEMA_VERSION = "eval_batch_serving_evaltower.tier.v1"
VERIFIER_REPORT_SCHEMA_VERSION = "eval_batch_serving_evaltower.verifier.v1"

for path in (SCRIPT_DIR, AUTOPILOT_DIR):
    path_s = str(path)
    if path_s not in sys.path:
        sys.path.insert(0, path_s)

import eval_batch_serving_activation_window as activation_window  # noqa: E402
from eval_tower import (  # noqa: E402
    EvalTower,
    _default_eval_timeout,
    _eval_concurrency,
    compute_calibration_metrics as _compute_calibration_metrics,
    draw_shortfall,
)


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def default_output_dir(stamp: str | None = None) -> Path:
    return DEFAULT_OUTPUT_ROOT / f"eval_batch_serving_evaltower_{stamp or utc_stamp()}"


def _bool_blocker_rc(blockers: list[str]) -> int:
    return 75 if any("AutoPilot appears active" in item for item in blockers) else 2


def _activation_args(args: argparse.Namespace) -> argparse.Namespace:
    """Return the subset expected by eval_batch_serving_activation_window."""
    return argparse.Namespace(
        api_url=args.api_url,
        eval_batch_url=args.eval_batch_url,
        apply=args.apply,
        confirm_clean_window=args.confirm_clean_window,
        allow_autopilot_active=args.allow_autopilot_active,
        keep_enabled=True,
        skip_rollback=False,
        tap_events=args.tap_events,
        attest_samples=args.attest_samples,
        http_timeout_s=args.http_timeout_s,
        command_timeout_s=args.command_timeout_s,
        start_mode=args.start_mode,
        output_dir=None,
        summary_only=True,
    )


def _planned_eval_arm(name: str, args: argparse.Namespace) -> dict[str, Any]:
    return {
        "name": name,
        "tier": args.tier,
        "n": args.n,
        "seed": args.seed,
        "api_url": args.api_url.rstrip("/"),
        "timeout_s": args.evaltower_timeout_s,
    }


def _resolved_eval_concurrency(roles: Sequence[str] | None = None) -> int:
    try:
        return max(1, int(_eval_concurrency(roles)))
    except Exception:
        return 1


class _RunInterrupted(BaseException):
    pass


def _install_interrupt_handlers() -> Callable[[], None]:
    previous: dict[int, Any] = {}

    def _handler(signum: int, _frame: object) -> None:
        try:
            name = signal.Signals(signum).name
        except ValueError:
            name = str(signum)
        raise _RunInterrupted(name)

    for sig in (signal.SIGINT, signal.SIGTERM):
        previous[sig] = signal.getsignal(sig)
        signal.signal(sig, _handler)

    def _restore() -> None:
        for sig, handler in previous.items():
            signal.signal(sig, handler)

    return _restore


def _effective_min_eval_concurrency(args: argparse.Namespace) -> int:
    raw = getattr(args, "min_eval_concurrency", None)
    if raw is None:
        return 1
    return max(1, int(raw))


def _missing_concurrency_guard(args: argparse.Namespace) -> bool:
    return (
        bool(getattr(args, "apply", False))
        and getattr(args, "min_eval_concurrency", None) is None
        and not bool(getattr(args, "allow_serial", False))
    )


def _int_metric(metrics: dict[str, Any], key: str) -> int:
    try:
        return int(metrics.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def _has_metric(metrics: dict[str, Any], key: str) -> bool:
    return key in metrics and metrics.get(key) is not None


def _float_metric(metrics: dict[str, Any], key: str) -> float:
    try:
        return float(metrics.get(key, 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _arm_decision_blocker(name: str, arm: dict[str, Any] | None, *, expected_n: int) -> str | None:
    if not isinstance(arm, dict) or not arm.get("ok"):
        return None
    metrics = arm.get("metrics") or {}
    # EV-14d: `n_questions` is the REQUESTED draw, so the expected-n compare below can
    # no longer detect a short draw on its own. A recorded requested/completed gap is a
    # decision blocker in its own right: the arm scored a subset without saying so.
    shortfall = draw_shortfall(metrics)
    if shortfall is not None:
        return (
            f"{name} EvalTower arm draw incomplete: completed {shortfall[1]}/"
            f"{shortfall[0]} requested questions"
        )
    n_questions = _int_metric(metrics, "n_questions")
    n_scored = _int_metric(metrics, "n_scored")
    if not _has_metric(metrics, "n_scored"):
        n_scored = _int_metric(metrics, "quality_denominator") or _int_metric(
            metrics, "question_results_count"
        )
    reliability = _float_metric(metrics, "reliability")
    if (
        n_scored <= 0
        and n_questions > 0
        and reliability >= 1.0
        and _int_metric(metrics, "errors") <= 0
    ):
        n_scored = n_questions
    if n_questions <= 0 or n_scored <= 0 or reliability <= 0:
        return (
            f"{name} EvalTower arm is degenerate "
            f"(n_questions={n_questions}, n_scored={n_scored}, reliability={reliability})"
        )
    if expected_n > 0 and n_questions < expected_n:
        return f"{name} EvalTower arm scored {n_questions}/{expected_n} questions"
    # REL-1 alignment (2026-07-23): errors are HONEST exclusions, not automatic
    # degeneracy — zero-tolerance predates the REL-1 era and refused arms at
    # 45/50 (90%) while the verifier modes bank at reliability 0.895-0.996
    # under the same instrument. Floor: >= 0.9 of the expected draw scored
    # (stricter than SafetyGate's 0.8 gating floor; decision_grade machinery
    # applies its own checks downstream).
    if expected_n > 0 and n_scored < 0.9 * expected_n:
        return (
            f"{name} EvalTower arm scored {n_scored}/{expected_n} non-error "
            f"questions (reliability {n_scored / expected_n:.3f} < 0.9 floor)"
        )
    return None


def _verifier_result_counts(result: dict[str, Any] | None) -> dict[str, int]:
    if not isinstance(result, dict):
        return {"n_questions": 0, "n_scored": 0}
    n_questions = _int_metric(result, "n_questions") or _int_metric(result, "n")
    n_scored = _int_metric(result, "n_scored")
    has_top_level_n_scored = _has_metric(result, "n_scored")
    per_role = result.get("per_role") or {}
    if isinstance(per_role, dict):
        if n_questions <= 0:
            n_questions = sum(
                _int_metric(payload, "n") or _int_metric(payload, "n_questions")
                for payload in per_role.values()
                if isinstance(payload, dict)
            )
        if n_scored <= 0 and not has_top_level_n_scored:
            n_scored = sum(
                _int_metric(payload, "n_scored")
                if _has_metric(payload, "n_scored")
                else _int_metric(payload, "n")
                for payload in per_role.values()
                if isinstance(payload, dict)
            )
    return {"n_questions": n_questions, "n_scored": n_scored}


def _verifier_result_blocker(result: dict[str, Any] | None, *, expected_n: int | None) -> str | None:
    counts = _verifier_result_counts(result)
    # EV-14d: block on a RECORDED requested/completed gap — at the top level or in any
    # per-role block — before the expected-n compare. `n_questions` now reports what was
    # requested, so without this a mode report whose role drew 40 of 50 would clear an
    # expected_n=50 check on the requested count alone. Silent on pre-EV-14d payloads,
    # which carry no counts to disagree.
    shortfall = draw_shortfall(result if isinstance(result, dict) else None)
    if shortfall is None and isinstance(result, dict):
        for role, payload in sorted((result.get("per_role") or {}).items()):
            role_shortfall = draw_shortfall(payload if isinstance(payload, dict) else None)
            if role_shortfall is not None:
                return (
                    f"verifier-mode eval role {role} draw incomplete: completed "
                    f"{role_shortfall[1]}/{role_shortfall[0]} requested questions"
                )
    if shortfall is not None:
        return (
            f"verifier-mode eval draw incomplete: completed {shortfall[1]}/"
            f"{shortfall[0]} requested questions"
        )
    if expected_n is not None and counts["n_questions"] < expected_n:
        return (
            f"verifier-mode eval scored {counts['n_questions']}/{expected_n} questions"
        )
    if counts["n_questions"] <= 0 or counts["n_scored"] <= 0:
        return (
            "verifier-mode eval is degenerate "
            f"(n_questions={counts['n_questions']}, n_scored={counts['n_scored']})"
        )
    if expected_n is not None and counts["n_scored"] < expected_n:
        return (
            f"verifier-mode eval scored {counts['n_scored']}/{expected_n} "
            "non-error questions"
        )
    return None


# EV-11c incident (2026-07-22): a verifier-mode run stamped decision_grade:true
# despite a worker_math arm at reliability 0.708 (< this floor) whose calibration
# was a placeholder (ECE/AUROC 0.0 with no real confidence). Decision-grade
# evidence must clear a reliability floor AND carry real confidence provenance.
DECISION_GRADE_RELIABILITY_FLOOR = 0.8


def _decision_grade_quality_reasons(
    result: dict[str, Any] | None,
    *,
    reliability_floor: float = DECISION_GRADE_RELIABILITY_FLOOR,
) -> list[str]:
    """Reasons a *completed* verifier-mode result is NOT decision-grade.

    Demotes decision_grade on POSITIVE evidence of a quality failure in any arm:
      * an arm whose reliability is present and below ``reliability_floor``; or
      * an arm whose confidence provenance is present and explicitly not-real
        (fake / placeholder calibration).
    Absent fields (legacy or mock rows that never stamped the metric) are lenient
    — the check fires only on present-and-bad evidence, so it never fabricates a
    demotion from missing metadata.
    """
    reasons: list[str] = []
    if not isinstance(result, dict):
        return reasons
    per_role = result.get("per_role")
    if not isinstance(per_role, dict):
        return reasons
    for role, arm in sorted(per_role.items()):
        if not isinstance(arm, dict):
            continue
        reliability = arm.get("reliability")
        if isinstance(reliability, (int, float)) and not isinstance(reliability, bool):
            if float(reliability) < reliability_floor:
                reasons.append(
                    f"arm {role} reliability {float(reliability):.3f} < "
                    f"{reliability_floor} decision-grade floor"
                )
        # Fake/placeholder calibration: the arm carries a confidence_is_real stamp
        # AND it is falsy. Absent stamp ⇒ no claim (lenient).
        if "confidence_is_real" in arm and not arm.get("confidence_is_real"):
            reasons.append(
                f"arm {role} calibration is not decision-grade "
                f"(confidence_is_real={arm.get('confidence_is_real')!r})"
            )
    return reasons


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    with tmp.open("w", encoding="utf-8") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    _fsync_parent(path)


def _atomic_write_text(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    _fsync_parent(path)


def _fsync_parent(path: Path) -> None:
    try:
        dir_fd = os.open(path.parent, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def _optimized_live_stack_status() -> dict[str, Any]:
    """Return whether live llama-server PIDs match the generated launch contract.

    This is deliberately stricter than a health check: it validates the live
    command lines against stack_priors.yaml, covering the v7 max-speed contract
    (binary path, model/draft paths, spec-decode flags, KV quant, reasoning,
    slot-save, and related launch flags). A non-empty warning list means the
    run would measure a drifted/non-operative stack and must not execute.
    """
    try:
        from scripts.server.stack_commands import runtime_attestation_warnings
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "warnings": [f"live stack contract checker unavailable: {exc}"]}

    try:
        warnings = runtime_attestation_warnings()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "warnings": [f"live stack contract check failed: {exc}"]}
    return {"ok": not warnings, "warnings": warnings}


def _progress_writer(output_dir: Path, *, run_context: dict[str, Any]) -> Callable[[dict[str, Any]], None]:
    output_dir.mkdir(parents=True, exist_ok=True)
    progress_jsonl = output_dir / "progress.jsonl"
    current_json = output_dir / "progress.current.json"
    state = {"seq": 0}

    def _write(event: dict[str, Any]) -> None:
        state["seq"] += 1
        payload = {
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "seq": state["seq"],
            "context": run_context,
            "event": event,
        }
        with progress_jsonl.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True) + "\n")
        _atomic_write_json(current_json, payload)

    return _write


def _details_float(details: dict[str, Any], key: str, fallback: float = 0.0) -> float:
    value = details.get(key, fallback)
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _details_float_or_none(details: dict[str, Any], key: str) -> float | None:
    """A detail that may legitimately be UNMEASURED — carried as None, never 0.0.

    RTG-23: `goodput_qph` is quality-scaled, and quality is `None` (not 0.0) on a
    trial whose eval never ran, so the producer now journals `null` there. Coercing
    that null to 0.0 here would re-assert the very measurement the producer refused
    to make — the same gap-handling doctrine `_arm_decision_blocker` applies to
    n_scored / reliability.
    """
    value = details.get(key)
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if number != number else number  # NaN is absence, not a value


def eval_result_metrics(result: Any, *, wall_s: float) -> dict[str, Any]:
    details = getattr(result, "details", {}) or {}
    eval_wall_s = float(getattr(result, "eval_wall_s", 0.0) or 0.0)
    if not eval_wall_s:
        eval_wall_s = _details_float(details, "eval_wall_s")
    n_questions = int(getattr(result, "n_questions", 0) or 0)
    reliability = float(getattr(result, "reliability", 0.0) or 0.0)
    question_results = getattr(result, "question_results", []) or []
    n_scored = _int_metric(details, "n_scored")
    if not _has_metric(details, "n_scored"):
        n_scored = _int_metric(details, "quality_denominator")
    if n_scored <= 0 and not (
        _has_metric(details, "n_scored") or _has_metric(details, "quality_denominator")
    ):
        n_scored = sum(
            1
            for row in question_results
            if not (isinstance(row, dict) and row.get("error"))
        )
    if n_scored <= 0 and n_questions > 0 and reliability >= 1.0 and _int_metric(details, "errors") <= 0:
        n_scored = n_questions
    return {
        "tier": int(getattr(result, "tier", 0) or 0),
        "quality": float(getattr(result, "quality", 0.0) or 0.0),
        "speed": float(getattr(result, "speed", 0.0) or 0.0),
        "cost": float(getattr(result, "cost", 0.0) or 0.0),
        "reliability": reliability,
        "errors": _int_metric(details, "errors"),
        "n_questions": n_questions,
        "n_scored": n_scored,
        "core_id": str(getattr(result, "core_id", "") or ""),
        "speed_metric_mode": str(
            getattr(result, "speed_metric_mode", "")
            or details.get("speed_metric_mode", "")
            or ""
        ),
        "median_request_tps": float(getattr(result, "median_request_speed", 0.0) or 0.0)
        or _details_float(details, "median_request_tps"),
        "aggregate_tps": float(getattr(result, "aggregate_speed", 0.0) or 0.0)
        or _details_float(details, "aggregate_tps"),
        "eval_concurrency": int(getattr(result, "eval_concurrency", 0) or 0)
        or int(details.get("eval_concurrency", 0) or 0),
        "eval_wall_s": eval_wall_s,
        "wall_s": wall_s,
        "wall_minutes_per_eval": wall_s / 60.0,
        "task_rate_qph": _details_float(details, "task_rate_qph"),
        "goodput_qph": _details_float_or_none(details, "goodput_qph"),
        "per_suite_quality": dict(getattr(result, "per_suite_quality", {}) or {}),
        "per_suite_counts": dict(
            getattr(result, "per_suite_counts", {}) or details.get("per_suite_counts", {}) or {}
        ),
        "partition_quality": dict(details.get("partition_quality", {}) or {}),
        "partition_counts": dict(details.get("partition_counts", {}) or {}),
        "mean_tools_used": float(getattr(result, "mean_tools_used", 0.0) or 0.0),
        "tool_use_rate": float(getattr(result, "tool_use_rate", 0.0) or 0.0),
        "total_tool_calls": int(getattr(result, "total_tool_calls", 0) or 0),
        "question_results_count": len(question_results),
    }


def _evaluate(tower: EvalTower, *, tier: int, n: int, seed: int) -> Any:
    if tier == 1:
        return tower.eval_t1(n=n, seed=seed)
    if tier == 2:
        return tower.eval_t2(n=n, seed=seed)
    if tier == 3:
        return tower.eval_t3(n=n, seed=seed)
    raise ValueError(f"unsupported tier: {tier}")


def run_eval_arm(
    name: str, args: argparse.Namespace, *, output_dir: Path | None = None
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        tower = EvalTower(
            url=args.api_url.rstrip("/"),
            timeout=args.evaltower_timeout_s,
        )
        # EV-11c: durably persist per-arm question rows into this run's output-dir
        # so a burned/errored tier arm's error rows are identifiable and can be
        # requeued with --retry-errors-from (vs a full multi-hour arm rerun). Mirrors
        # the verifier/retry/resume paths; the tier arm routes through _eval_batch, so
        # setting the dir engages the same append-only, fsync'd sidecar writer.
        # Best-effort (matches _eval_batch's fail-soft sidecar contract).
        if output_dir is not None and hasattr(tower, "set_question_artifact_dir"):
            tower.set_question_artifact_dir(output_dir)
        result = _evaluate(tower, tier=args.tier, n=args.n, seed=args.seed)
        wall_s = time.perf_counter() - started
        return {
            "name": name,
            "ok": True,
            "error": None,
            "metrics": eval_result_metrics(result, wall_s=wall_s),
        }
    except _RunInterrupted:
        raise
    except Exception as exc:  # noqa: BLE001 - report artifact must capture failures
        return {
            "name": name,
            "ok": False,
            "error": str(exc),
            "metrics": {
                "tier": args.tier,
                "n_questions": 0,
                "wall_s": time.perf_counter() - started,
            },
        }


def comparison_metrics(
    current_arm: dict[str, Any] | None,
    eval_batch_arm: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not current_arm or not eval_batch_arm:
        return None
    if not current_arm.get("ok") or not eval_batch_arm.get("ok"):
        return None
    current = current_arm.get("metrics") or {}
    batch = eval_batch_arm.get("metrics") or {}
    current_wall = float(current.get("wall_s") or 0.0)
    batch_wall = float(batch.get("wall_s") or 0.0)
    speedup = current_wall / batch_wall if current_wall > 0 and batch_wall > 0 else 0.0
    return {
        "wall_speedup_current_over_eval_batch": speedup,
        "wall_s_delta_eval_batch_minus_current": batch_wall - current_wall,
        "quality_delta_eval_batch_minus_current": float(batch.get("quality") or 0.0)
        - float(current.get("quality") or 0.0),
        "reliability_delta_eval_batch_minus_current": float(batch.get("reliability") or 0.0)
        - float(current.get("reliability") or 0.0),
        "objective_speed_delta_eval_batch_minus_current": float(batch.get("speed") or 0.0)
        - float(current.get("speed") or 0.0),
        "current": {
            "quality": current.get("quality"),
            "reliability": current.get("reliability"),
            "wall_s": current_wall,
            "speed": current.get("speed"),
        },
        "eval_batch": {
            "quality": batch.get("quality"),
            "reliability": batch.get("reliability"),
            "wall_s": batch_wall,
            "speed": batch.get("speed"),
        },
    }


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Eval-Batch Serving EvalTower Window",
        "",
        f"- status: `{report['status']}`",
        f"- decision_grade: `{report['decision_grade']}`",
        f"- applied: `{report['applied']}`",
        f"- tier/n/seed: `T{report['eval_spec']['tier']} / {report['eval_spec']['n']} / {report['eval_spec']['seed']}`",
        f"- skip_current_arm: `{report['skip_current_arm']}`",
        f"- keep_enabled: `{report['keep_enabled']}`",
        f"- eval_batch_url: `{report['eval_batch_url']}`",
        f"- eval_concurrency: resolved=`{report.get('resolved_eval_concurrency')}` min=`{report.get('min_eval_concurrency')}`",
        f"- autopilot_active: `{report['preflight'].get('autopilot_active')}`",
    ]
    if report.get("blockers"):
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- {blocker}" for blocker in report["blockers"])
    lines.extend(["", "## Planned Activation", ""])
    lines.extend(f"```bash\n{cmd}\n```" for cmd in report["activation_commands"])
    lines.extend(["", "## Planned Rollback", ""])
    lines.extend(f"```bash\n{cmd}\n```" for cmd in report["rollback_commands"])
    for key in ("current_arm", "eval_batch_arm"):
        arm = report.get(key)
        if isinstance(arm, dict):
            lines.extend(["", f"## {key.replace('_', ' ').title()}", ""])
            lines.append(f"- ok: `{arm.get('ok')}`")
            if arm.get("error"):
                lines.append(f"- error: `{arm['error']}`")
            metrics = arm.get("metrics") or {}
            for metric in (
                "quality",
                "speed",
                "reliability",
                "wall_s",
                "n_questions",
                "n_scored",
                "errors",
            ):
                if metric in metrics:
                    lines.append(f"- {metric}: `{metrics[metric]}`")
    if isinstance(report.get("comparison"), dict):
        comparison = report["comparison"]
        lines.extend(["", "## Comparison", ""])
        for metric in (
            "wall_speedup_current_over_eval_batch",
            "quality_delta_eval_batch_minus_current",
            "reliability_delta_eval_batch_minus_current",
            "objective_speed_delta_eval_batch_minus_current",
        ):
            lines.append(f"- {metric}: `{comparison.get(metric)}`")
    if report.get("rollback_steps"):
        lines.extend(["", "## Rollback Steps", ""])
        for step in report["rollback_steps"]:
            lines.append(
                f"- `{step['name']}` rc=`{step['returncode']}` elapsed_s=`{step['elapsed_s']:.3f}`"
            )
    _atomic_write_text(path, "\n".join(lines) + "\n")


def write_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "summary.json"
    md_path = output_dir / "summary.md"
    report.setdefault("schema_version", TIER_REPORT_SCHEMA_VERSION)
    _atomic_write_json(json_path, report)
    _write_markdown(md_path, report)
    return json_path, md_path


def build_report(args: argparse.Namespace, *, output_dir: Path) -> tuple[dict[str, Any], int]:
    activation_args = _activation_args(args)
    activation_dir = output_dir / "activation"
    preflight = activation_window.build_preflight(activation_args)
    plan = activation_window.activation_plan(activation_args, output_dir=activation_dir)
    blockers = activation_window.pre_apply_blockers(activation_args, preflight) if args.apply else []
    current_arm: dict[str, Any] | None = None
    eval_batch_arm: dict[str, Any] | None = None
    activation_steps: list[Any] = []
    rollback_steps: list[Any] = []
    probe_summary: dict[str, Any] | None = None
    status = "plan_only"
    rc = 0
    resolved_eval_concurrency: int | None = None
    min_eval_concurrency = _effective_min_eval_concurrency(args)
    restore_handlers = _install_interrupt_handlers() if args.apply else (lambda: None)
    activation_armed = False

    try:
        if not args.apply:
            pass
        else:
            resolved_eval_concurrency = _resolved_eval_concurrency()
            if _missing_concurrency_guard(args):
                blockers.append(
                    "--apply requires explicit --min-eval-concurrency N or --allow-serial; "
                    "refusing to silently serialize an eval-fanout run"
                )
            if (
                min_eval_concurrency > 1
                and resolved_eval_concurrency < min_eval_concurrency
            ):
                blockers.append(
                    f"resolved EvalTower concurrency {resolved_eval_concurrency} is below "
                    f"--min-eval-concurrency {min_eval_concurrency}; refresh the "
                    "contention matrix/topology certification or intentionally run a serial entry"
                )
            if blockers:
                status = "blocked"
                rc = _bool_blocker_rc(blockers)
            else:
                if not args.skip_current_arm:
                    current_arm = run_eval_arm("current", args, output_dir=output_dir)
                    if not current_arm.get("ok"):
                        blockers.append(f"current EvalTower arm failed: {current_arm.get('error')}")
                        status = "current_eval_failed"
                        rc = 75
                    else:
                        degenerate = _arm_decision_blocker(
                            "current", current_arm, expected_n=int(args.n or 0)
                        )
                        if degenerate:
                            blockers.append(degenerate)
                            status = "current_eval_degenerate"
                            rc = 75

                if not blockers and args.skip_batch_arm:
                    # Current-arm-only re-baseline: never arm activation, so the
                    # finally-block rollback stays a no-op and no batch-shaped
                    # server is ever launched.
                    status = "current_arm_complete"
                if not blockers and not args.skip_batch_arm:
                    activation_armed = True
                    activation_steps, activation_errors = activation_window.execute_activation(
                        activation_args,
                        output_dir=activation_dir,
                    )
                    probe_summary = activation_window._load_probe_summary(activation_dir)
                    probe_passed = bool(probe_summary and probe_summary.get("decision_grade"))
                    if activation_errors or not probe_passed:
                        blockers.extend(
                            activation_errors or ["smoke probe did not produce decision-grade evidence"]
                        )
                        status = "activation_failed"
                        rc = 75
                    else:
                        eval_batch_arm = run_eval_arm("eval_batch", args, output_dir=output_dir)
                        if not eval_batch_arm.get("ok"):
                            blockers.append(
                                f"eval-batch EvalTower arm failed: {eval_batch_arm.get('error')}"
                            )
                            status = "eval_failed"
                            rc = 75
                        else:
                            degenerate = _arm_decision_blocker(
                                "eval-batch", eval_batch_arm, expected_n=int(args.n or 0)
                            )
                            if degenerate:
                                blockers.append(degenerate)
                                status = "eval_degenerate"
                                rc = 75

                if not blockers and status == "plan_only":
                    status = "comparison_complete_enabled_left_on" if args.keep_enabled else "comparison_complete_rolled_back"
                    if args.skip_current_arm:
                        status = "eval_batch_arm_complete_enabled_left_on" if args.keep_enabled else "eval_batch_arm_complete_rolled_back"

    except _RunInterrupted as exc:
        blockers.append(f"interrupted by {exc}; rollback attempted before writing summary")
        status = "interrupted"
        rc = 130
    finally:
        if (activation_armed or activation_steps) and not args.keep_enabled and not rollback_steps:
            rollback_steps = activation_window.execute_rollback(activation_args)
            failed_rollback = [step for step in rollback_steps if not step.ok]
            if failed_rollback:
                blockers.extend(f"rollback step {step.name} failed" for step in failed_rollback)
                status = f"{status}_rollback_failed"
                rc = 75
        restore_handlers()

    comparison = comparison_metrics(current_arm, eval_batch_arm)
    decision_grade = bool(
        args.apply
        and args.confirm_clean_window
        and not args.allow_autopilot_active
        and not blockers
        and current_arm
        and eval_batch_arm
        and current_arm.get("ok")
        and eval_batch_arm.get("ok")
        and comparison
    )
    report = {
        "schema_version": TIER_REPORT_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": status,
        "decision_grade": decision_grade,
        "applied": bool(args.apply),
        "confirm_clean_window": bool(args.confirm_clean_window),
        "allow_autopilot_active": bool(args.allow_autopilot_active),
        "skip_current_arm": bool(args.skip_current_arm),
        "skip_batch_arm": bool(getattr(args, "skip_batch_arm", False)),
        "keep_enabled": bool(args.keep_enabled),
        "allow_serial": bool(args.allow_serial),
        "eval_batch_url": args.eval_batch_url.rstrip("/"),
        "eval_spec": {"tier": args.tier, "n": args.n, "seed": args.seed},
        "min_eval_concurrency": int(min_eval_concurrency),
        "resolved_eval_concurrency": resolved_eval_concurrency,
        "blockers": blockers,
        "preflight": preflight,
        "planned_current_arm": None
        if args.skip_current_arm
        else _planned_eval_arm("current", args),
        "planned_eval_batch_arm": _planned_eval_arm("eval_batch", args),
        "activation_commands": [command.display() for command in plan["activation"]],
        "rollback_commands": [command.display() for command in plan["rollback"]],
        "activation_steps": [asdict(step) for step in activation_steps],
        "rollback_steps": [asdict(step) for step in rollback_steps],
        "probe_summary": probe_summary,
        "current_arm": current_arm,
        "eval_batch_arm": eval_batch_arm,
        "comparison": comparison,
        "decision_grade_notes": [
            "requires --apply --confirm-clean-window",
            "requires AutoPilot inactive unless --allow-autopilot-active is set",
            "requires successful current and eval-batch EvalTower arms",
        ],
    }
    return report, rc


# ── verifier-mode (EV-4 / EV-5/7/8 / EV-11) additive surface ─────────────────
# BUILD-evalbatch-verifier-mode. --mode {calibration,math_rebaseline} runs the
# EvalTower verifier-mode entrypoints instead of the tier A/B path. Execution is
# gated identically to the tier path (needs --apply --confirm-clean-window, and
# an inactive AutoPilot unless --allow-autopilot-active). The verifier-MODEL pass
# (EV-5/7/8) is additionally MODEL-DOWNLOAD gated: --verifier <model> is accepted,
# but if the model is not on disk the run refuses with a MODEL-DOWNLOAD-<x> error
# rather than fabricating verifier scores.

MODEL_ROOTS = (Path("/mnt/raid0/llm/models"),)

# Known cross-family verifier candidates → stable MODEL-DOWNLOAD tokens.
KNOWN_VERIFIER_TOKENS = {
    "thinkprm": "THINKPRM-1.5B",
    "thinkprm-1.5b": "THINKPRM-1.5B",
    "aletheia": "ALETHEIA-1.5B",
    "aletheia-1.5b": "ALETHEIA-1.5B",
    "ouro": "OURO-2.6B",
    "ouro-2.6b": "OURO-2.6B",
    "sae": "QWEN-SCOPE-SAE",
    "qwen-scope": "QWEN-SCOPE-SAE",
    "qwen-scope-sae": "QWEN-SCOPE-SAE",
}


def _verifier_token(model: str) -> str:
    key = str(model).strip().lower()
    if key in KNOWN_VERIFIER_TOKENS:
        return KNOWN_VERIFIER_TOKENS[key]
    sanitized = re.sub(r"[^A-Za-z0-9]+", "-", str(model).strip()).strip("-").upper()
    return sanitized or "VERIFIER"


def _verifier_on_disk(model: str) -> bool:
    key = str(model).strip().lower()
    if not key:
        return False
    for root in MODEL_ROOTS:
        if not root.exists():
            continue
        for entry in root.iterdir():
            if key in entry.name.lower():
                return True
    return False


def verifier_download_gate(model: str | None) -> dict[str, Any] | None:
    """Report whether a requested verifier model is on disk (None ⇒ none requested)."""
    if not model:
        return None
    on_disk = _verifier_on_disk(model)
    token = _verifier_token(model)
    return {
        "verifier": model,
        "on_disk": on_disk,
        "token": token,
        "status": "on_disk" if on_disk else "download_required",
        "required_download": None if on_disk else f"MODEL-DOWNLOAD-{token}",
        "model_roots": [str(root) for root in MODEL_ROOTS],
    }


def require_verifier_on_disk(model: str) -> None:
    """Raise a MODEL-DOWNLOAD-<x> error unless the verifier model is on disk."""
    if not _verifier_on_disk(model):
        token = _verifier_token(model)
        raise RuntimeError(
            f"MODEL-DOWNLOAD-{token} required: verifier model {model!r} is not present "
            f"under {MODEL_ROOTS[0]}. EV-5/7/8 verifier-model validation is download-gated; "
            "download + quantize the model before running the verifier pass. Refusing to "
            "fabricate verifier scores."
        )


def verifier_pin_command(args: argparse.Namespace) -> str:
    """The exact runnable pin command for this verifier-mode arm."""
    min_eval_concurrency = args.min_eval_concurrency
    if min_eval_concurrency is None and not args.allow_serial:
        min_eval_concurrency = 3
    parts = [
        "scripts/benchmark/eval_batch_serving_evaltower_window.py",
        f"--mode {args.mode}",
    ]
    if args.suite:
        parts.append(f"--suite {args.suite}")
    if args.split:
        parts.append(f"--split {args.split}")
    if args.roles:
        parts.append(f"--roles {args.roles}")
    if args.mode == "math_rebaseline":
        parts.append(f"--scoring {args.scoring}")
    if args.full:
        parts.append("--full")
    if args.verifier:
        parts.append(f"--verifier {args.verifier}")
    if args.n is not None and not args.full:
        parts.append(f"--n {args.n}")
    if min_eval_concurrency is not None and min_eval_concurrency > 1:
        parts.append(f"--min-eval-concurrency {min_eval_concurrency}")
    if args.allow_serial:
        parts.append("--allow-serial")
    parts.append(f"--seed {args.seed}")
    parts.append(f"--api-url {args.api_url.rstrip('/')}")
    parts.append("--apply --confirm-clean-window")
    return ".venv/bin/python " + " ".join(parts)


def build_verifier_report(
    args: argparse.Namespace, *, output_dir: Path
) -> tuple[dict[str, Any], int]:
    """Plan (default) or run an EV-4 / EV-11 verifier-mode arm.

    Plan-only unless ``--apply --confirm-clean-window`` (and AutoPilot inactive
    unless overridden). The verifier-model pass stays MODEL-DOWNLOAD gated.
    """
    mode = args.mode
    roles = [part.strip() for part in (args.roles or "").split(",") if part.strip()] or [
        "worker_general"
    ]
    gate = verifier_download_gate(args.verifier)
    pin_command = verifier_pin_command(args)
    n_arg = None if args.full else args.n

    preflight = activation_window.build_preflight(_activation_args(args))
    autopilot_active = bool(preflight.get("autopilot_active"))

    blockers: list[str] = []
    status = "plan_only"
    rc = 0
    result: dict[str, Any] | None = None
    resolved_eval_concurrency: int | None = None
    live_stack_contract: dict[str, Any] | None = None
    min_eval_concurrency = _effective_min_eval_concurrency(args)
    verifier_counts = {"n_questions": 0, "n_scored": 0}

    if not args.apply:
        status = "plan_only"
    else:
        resolved_eval_concurrency = _resolved_eval_concurrency(roles)
        live_stack_contract = _optimized_live_stack_status()
        if _missing_concurrency_guard(args):
            blockers.append(
                "--apply requires explicit --min-eval-concurrency N or --allow-serial; "
                "refusing to silently serialize an eval-fanout run"
            )
        if not args.confirm_clean_window:
            blockers.append("verifier-mode execution requires --confirm-clean-window")
        if autopilot_active and not args.allow_autopilot_active:
            blockers.append(
                "AutoPilot appears active; pass --allow-autopilot-active to override"
            )
        if not live_stack_contract.get("ok", False):
            warning_count = len(live_stack_contract.get("warnings") or [])
            blockers.append(
                f"live stack launch contract has {warning_count} warning(s); "
                "refusing to measure a drifted/non-optimized v7 stack"
            )
        if (
            min_eval_concurrency > 1
            and resolved_eval_concurrency < min_eval_concurrency
        ):
            blockers.append(
                f"resolved EvalTower concurrency {resolved_eval_concurrency} is below "
                f"--min-eval-concurrency {min_eval_concurrency}; refresh the "
                "contention matrix/topology certification or intentionally run a serial entry"
            )
        if args.verifier and gate and not gate["on_disk"]:
            blockers.append(
                f"{gate['required_download']} required: verifier model "
                f"{args.verifier!r} is not on disk"
            )
        if blockers:
            status = "blocked"
            rc = _bool_blocker_rc(blockers)
        else:
            try:
                if args.verifier:
                    require_verifier_on_disk(args.verifier)
                progress_cb = _progress_writer(
                    output_dir,
                    run_context={
                        "mode": mode,
                        "suite": args.suite,
                        "split": args.split,
                        "roles": roles,
                        "full": bool(args.full),
                        "n": n_arg,
                        "seed": args.seed,
                        "api_url": args.api_url.rstrip("/"),
                        "resolved_eval_concurrency": resolved_eval_concurrency,
                    },
                )
                tower = EvalTower(
                    url=args.api_url.rstrip("/"),
                    timeout=args.evaltower_timeout_s,
                    on_progress=progress_cb,
                )
                # EV-11c: durably persist per-arm question rows into this run's
                # output-dir so a burned arm's error rows are identifiable and can be
                # requeued with --retry-errors-from (vs a full multi-hour arm rerun).
                # Best-effort (matches _eval_batch's fail-soft sidecar contract).
                if hasattr(tower, "set_question_artifact_dir"):
                    tower.set_question_artifact_dir(output_dir)
                if mode == "calibration":
                    if not args.suite:
                        raise ValueError("--mode calibration requires --suite")
                    result = tower.eval_calibration(
                        suite=args.suite,
                        split=args.split,
                        roles=roles,
                        seed=args.seed,
                        n=n_arg,
                        full=bool(args.full),
                    )
                else:  # math_rebaseline
                    result = tower.eval_math_rebaseline(
                        full=bool(args.full),
                        scoring=args.scoring,
                        roles=roles,
                        seed=args.seed,
                        n=n_arg,
                        production_sampling=True,
                    )
                verifier_counts = _verifier_result_counts(result)
                degenerate = _verifier_result_blocker(
                    result,
                    expected_n=n_arg,
                )
                if degenerate:
                    blockers.append(degenerate)
                    status = "eval_degenerate"
                    rc = 75
                else:
                    status = "complete"
            except _RunInterrupted as exc:
                blockers.append(f"verifier-mode eval interrupted by {exc}")
                status = "interrupted"
                rc = 130
            except Exception as exc:  # noqa: BLE001 - report artifact captures failures
                blockers.append(f"verifier-mode eval failed: {exc}")
                status = "eval_failed"
                rc = 75

    # EV-11c: below-floor reliability or fake/placeholder calibration in any arm
    # demotes decision_grade even on an otherwise clean run, with reasons recorded.
    decision_grade_reasons = (
        _decision_grade_quality_reasons(result) if result is not None else []
    )
    decision_grade = bool(
        args.apply
        and args.confirm_clean_window
        and not args.allow_autopilot_active
        and not blockers
        and result is not None
        and not decision_grade_reasons
    )
    report = {
        "schema_version": VERIFIER_REPORT_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "mode": mode,
        "status": status,
        "decision_grade": decision_grade,
        "decision_grade_reasons": decision_grade_reasons,
        "applied": bool(args.apply),
        "confirm_clean_window": bool(args.confirm_clean_window),
        "allow_autopilot_active": bool(args.allow_autopilot_active),
        "allow_serial": bool(args.allow_serial),
        "suite": args.suite,
        "split": args.split,
        "roles": roles,
        "scoring": args.scoring,
        "full": bool(args.full),
        "n": n_arg,
        "seed": args.seed,
        "api_url": args.api_url.rstrip("/"),
        "min_eval_concurrency": int(min_eval_concurrency),
        "resolved_eval_concurrency": resolved_eval_concurrency,
        "live_stack_contract": live_stack_contract,
        "verifier": args.verifier,
        "verifier_gate": gate,
        "pin_command": pin_command,
        "blockers": blockers,
        "preflight": {"autopilot_active": autopilot_active},
        "verifier_counts": verifier_counts,
        "result": result,
        "decision_grade_notes": [
            "requires --apply --confirm-clean-window",
            "requires AutoPilot inactive unless --allow-autopilot-active",
            "verifier-model pass (EV-5/7/8) is MODEL-DOWNLOAD gated",
            f"requires every arm reliability >= {DECISION_GRADE_RELIABILITY_FLOOR} "
            "and real confidence provenance (see decision_grade_reasons)",
        ],
    }
    return report, rc


def _write_verifier_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Eval-Batch Serving Verifier-Mode Window",
        "",
        f"- mode: `{report['mode']}`",
        f"- status: `{report['status']}`",
        f"- decision_grade: `{report['decision_grade']}`",
        f"- applied: `{report['applied']}`",
        f"- suite/split: `{report['suite']} / {report['split']}`",
        f"- roles: `{', '.join(report['roles'])}`",
        f"- scoring: `{report['scoring']}`  full: `{report['full']}`  n: `{report['n']}`  seed: `{report['seed']}`",
        f"- eval_concurrency: resolved=`{report.get('resolved_eval_concurrency')}` min=`{report.get('min_eval_concurrency')}`",
        f"- autopilot_active: `{report['preflight'].get('autopilot_active')}`",
    ]
    gate = report.get("verifier_gate")
    if isinstance(gate, dict):
        lines.append(
            f"- verifier: `{gate.get('verifier')}` status: `{gate.get('status')}`"
            + (f" ({gate.get('required_download')})" if gate.get("required_download") else "")
        )
    lines.extend(["", "## Pin Command", "", f"```bash\n{report['pin_command']}\n```"])
    if report.get("blockers"):
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- {blocker}" for blocker in report["blockers"])
    if report.get("decision_grade_reasons"):
        lines.extend(["", "## Decision-Grade Demotions", ""])
        lines.extend(f"- {reason}" for reason in report["decision_grade_reasons"])
    result = report.get("result")
    if isinstance(result, dict):
        lines.extend(
            ["", "## Result", "", f"- dataset_sha256: `{result.get('dataset_sha256')}`"]
        )
        for role, payload in (result.get("per_role") or {}).items():
            lines.append(f"- `{role}`: `{json.dumps(payload, sort_keys=True)}`")
    _atomic_write_text(path, "\n".join(lines) + "\n")


def write_verifier_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "summary.json"
    md_path = output_dir / "summary.md"
    report.setdefault("schema_version", VERIFIER_REPORT_SCHEMA_VERSION)
    _atomic_write_json(json_path, report)
    _write_verifier_markdown(md_path, report)
    return json_path, md_path


# ── error-requeue (EV-11c) ───────────────────────────────────────────────────
# --retry-errors-from <dir> reads a prior run's per-arm question_results.<arm>.jsonl
# sidecars, reruns ONLY the error rows for the requested role(s), and emits a MERGED
# summary (prior scored rows + retried rows) so a burned arm becomes a ~subset
# requeue instead of a full multi-hour rerun. Same --apply/--confirm-clean-window
# gating as verifier-mode; decision_grade applies to the MERGED pool.

RETRY_REPORT_SCHEMA_VERSION = "eval_batch_serving_evaltower.retry.v1"
RESUME_REPORT_SCHEMA_VERSION = "eval_batch_serving_evaltower.resume.v1"
_ARM_LABEL_PREFIXES = ("ev11-", "cal-", "retry-", "resume-")


def _role_from_arm_label(label: str) -> str:
    for prefix in _ARM_LABEL_PREFIXES:
        if label.startswith(prefix):
            return label[len(prefix):]
    return label


def _row_identity(row: dict[str, Any]) -> str:
    return str(row.get("question_id") or row.get("qid") or "").strip()


def load_arm_question_rows(directory: Path) -> dict[str, dict[str, Any]]:
    """Read a prior run's ``question_results.<arm>.jsonl`` sidecars.

    Returns ``{arm_label: {role, suite, scoring, complete, rows, path}}`` where
    ``rows`` is the ordered list of compact per-question result dicts. Malformed
    JSON lines are skipped (the writer is append-only + fsync'd, but a crash can
    leave a torn final line).
    """
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(Path(directory).glob("question_results.*.jsonl")):
        rows: list[dict[str, Any]] = []
        label: str | None = None
        complete = False
        suite: str | None = None
        scoring: str | None = None
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue
                rtype = row.get("row_type")
                if rtype == "batch_start":
                    label = row.get("label") or label
                elif rtype == "batch_complete":
                    complete = True
                elif rtype == "question_result":
                    label = row.get("label") or label
                    result = row.get("result")
                    if isinstance(result, dict):
                        rows.append(result)
                        suite = suite or result.get("suite")
                        scoring = scoring or result.get("scoring_method")
        if label is None:
            # question_results.<label>.jsonl → <label>
            label = path.name[len("question_results."):-len(".jsonl")]
        out[label] = {
            "role": _role_from_arm_label(label),
            "suite": suite,
            "scoring": scoring,
            "complete": complete,
            "rows": rows,
            "path": str(path),
        }
    return out


def _error_identities(rows: Sequence[dict[str, Any]]) -> list[str]:
    seen: dict[str, None] = {}
    for row in rows:
        if row.get("error"):
            ident = _row_identity(row)
            if ident:
                seen.setdefault(ident, None)
    return list(seen)


def _row_confidence_source(row: dict[str, Any]) -> str:
    # _compact_question_result only persists confidence/confidence_source when the
    # source is NOT the binary proxy, so an absent source means binary proxy.
    return str(row.get("confidence_source") or "binary_correctness_proxy")


def merge_prior_and_retried(
    prior_rows: Sequence[dict[str, Any]],
    retried_rows: Sequence[dict[str, Any]],
    *,
    role: str,
) -> dict[str, Any]:
    """Reconcile a prior arm's rows with the retried error rows into one pool.

    Prior NON-error rows are kept verbatim; prior error rows are REPLACED by their
    retried outcome (by question identity). Calibration is recomputed over the
    merged pool ONLY when every scored row carries real (geomean) confidence — else
    None + provenance (fail-closed), never a placeholder.
    """
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for row in prior_rows:
        ident = _row_identity(row)
        if not ident:
            continue
        if ident not in merged:
            order.append(ident)
        merged[ident] = row
    retried_idents: set[str] = set()
    for row in retried_rows:
        ident = _row_identity(row)
        if not ident:
            continue
        if ident not in merged:
            order.append(ident)
        merged[ident] = row
        retried_idents.add(ident)

    pool = [merged[i] for i in order]
    scored = [r for r in pool if not r.get("error")]
    errored = [r for r in pool if r.get("error")]
    correct = sum(1 for r in scored if r.get("correct"))
    source_counts: dict[str, int] = {}
    for r in scored:
        src = _row_confidence_source(r)
        source_counts[src] = source_counts.get(src, 0) + 1
    cal_real = bool(source_counts) and set(source_counts) <= {
        "completion_probabilities_geomean"
    }
    ece: float | None = None
    auroc: float | None = None
    if cal_real and scored:
        confidences = [float(r.get("confidence", 0.0)) for r in scored]
        labels = [float(bool(r.get("correct"))) for r in scored]
        cal = _compute_calibration_metrics(confidences, labels)
        ece = cal.get("ece")
        auroc = cal.get("auroc")
    retry_errors_remaining = sum(
        1 for r in errored if _row_identity(r) in retried_idents
    )
    return {
        "role": role,
        "n_questions": len(pool),
        "n_scored": len(scored),
        "correct": correct,
        "accuracy": (correct / len(scored)) if scored else None,
        "reliability": (len(scored) / len(pool)) if pool else 0.0,
        "ece": ece,
        "auroc": auroc,
        "confidence_is_real": cal_real,
        "confidence_source_counts": dict(sorted(source_counts.items())),
        "retried_n": len(retried_idents),
        "retry_errors_remaining": retry_errors_remaining,
        "prior_scored_n": len(prior_rows) - len(_error_identities(prior_rows)),
        "merged": True,
    }


def build_retry_report(
    args: argparse.Namespace, *, output_dir: Path
) -> tuple[dict[str, Any], int]:
    """Plan (default) or run a targeted error requeue from a prior run's sidecars.

    Plan-only unless ``--apply --confirm-clean-window`` (AutoPilot inactive unless
    overridden) — identical live-execution gating to verifier-mode. Reads the prior
    per-arm files, reruns error rows per requested role, and writes a merged summary.
    """
    source_dir = Path(args.retry_errors_from)
    roles_filter = [p.strip() for p in (args.roles or "").split(",") if p.strip()]
    preflight = activation_window.build_preflight(_activation_args(args))
    autopilot_active = bool(preflight.get("autopilot_active"))

    blockers: list[str] = []
    status = "plan_only"
    rc = 0
    resolved_eval_concurrency: int | None = None
    live_stack_contract: dict[str, Any] | None = None
    min_eval_concurrency = _effective_min_eval_concurrency(args)
    merged_per_role: dict[str, Any] = {}
    retry_plan: dict[str, Any] = {}

    if not source_dir.exists():
        blockers.append(f"--retry-errors-from source dir not found: {source_dir}")
        arms = {}
    else:
        arms = load_arm_question_rows(source_dir)
        if not arms:
            blockers.append(
                f"no question_results.<arm>.jsonl sidecars under {source_dir} "
                "(prior run predates per-arm persistence, or wrong dir)"
            )

    # Build the plan: which role(s) have how many error rows to requeue.
    for label, arm in arms.items():
        role = arm["role"]
        if roles_filter and role not in roles_filter:
            continue
        error_ids = _error_identities(arm["rows"])
        retry_plan[role] = {
            "arm_label": label,
            "suite": arm.get("suite"),
            "scoring": arm.get("scoring"),
            "prior_rows": len(arm["rows"]),
            "error_rows": len(error_ids),
            "complete": arm.get("complete"),
        }
    if arms and not retry_plan:
        blockers.append(
            "no arms matched the requested --roles for retry "
            f"(available: {sorted({a['role'] for a in arms.values()})})"
        )

    if not args.apply:
        status = "plan_only"
    else:
        resolved_eval_concurrency = _resolved_eval_concurrency(roles_filter or None)
        live_stack_contract = _optimized_live_stack_status()
        if _missing_concurrency_guard(args):
            blockers.append(
                "--apply requires explicit --min-eval-concurrency N or --allow-serial; "
                "refusing to silently serialize an eval-fanout run"
            )
        if not args.confirm_clean_window:
            blockers.append("retry-mode execution requires --confirm-clean-window")
        if autopilot_active and not args.allow_autopilot_active:
            blockers.append(
                "AutoPilot appears active; pass --allow-autopilot-active to override"
            )
        if not live_stack_contract.get("ok", False):
            warning_count = len(live_stack_contract.get("warnings") or [])
            blockers.append(
                f"live stack launch contract has {warning_count} warning(s); "
                "refusing to measure a drifted/non-optimized v7 stack"
            )
        if (
            min_eval_concurrency > 1
            and resolved_eval_concurrency < min_eval_concurrency
        ):
            blockers.append(
                f"resolved EvalTower concurrency {resolved_eval_concurrency} is below "
                f"--min-eval-concurrency {min_eval_concurrency}"
            )
        if blockers:
            status = "blocked"
            rc = _bool_blocker_rc(blockers)
        else:
            try:
                tower = EvalTower(
                    url=args.api_url.rstrip("/"),
                    timeout=args.evaltower_timeout_s,
                )
                tower.set_question_artifact_dir(output_dir)
                any_retried = False
                for role, plan in retry_plan.items():
                    error_ids = _error_identities(arms[plan["arm_label"]]["rows"])
                    if not error_ids:
                        merged_per_role[role] = merge_prior_and_retried(
                            arms[plan["arm_label"]]["rows"], [], role=role
                        )
                        continue
                    any_retried = True
                    subset = tower.eval_question_subset(
                        suite=plan.get("suite") or "math",
                        question_ids=error_ids,
                        roles=[role],
                        scoring=plan.get("scoring"),
                        seed=args.seed,
                        production_sampling=True,
                    )
                    retried_rows = (
                        (subset.get("per_role") or {}).get(role, {}).get("rows") or []
                    )
                    merged_per_role[role] = merge_prior_and_retried(
                        arms[plan["arm_label"]]["rows"], retried_rows, role=role
                    )
                status = "complete" if any_retried else "nothing_to_retry"
            except _RunInterrupted as exc:
                blockers.append(f"retry-mode eval interrupted by {exc}")
                status = "interrupted"
                rc = 130
            except Exception as exc:  # noqa: BLE001 - report artifact captures failures
                blockers.append(f"retry-mode eval failed: {exc}")
                status = "eval_failed"
                rc = 75

    merged_result = {"per_role": merged_per_role} if merged_per_role else None
    decision_grade_reasons = (
        _decision_grade_quality_reasons(merged_result) if merged_result else []
    )
    decision_grade = bool(
        args.apply
        and args.confirm_clean_window
        and not args.allow_autopilot_active
        and not blockers
        and merged_result is not None
        and not decision_grade_reasons
    )
    retried_n = sum(int(v.get("retried_n", 0)) for v in merged_per_role.values())
    report = {
        "schema_version": RETRY_REPORT_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "mode": "retry_errors",
        "status": status,
        "decision_grade": decision_grade,
        "decision_grade_reasons": decision_grade_reasons,
        "applied": bool(args.apply),
        "merged": True,
        "retry_source_run": str(source_dir),
        "retried_n": retried_n,
        "roles": roles_filter,
        "seed": args.seed,
        "api_url": args.api_url.rstrip("/"),
        "min_eval_concurrency": int(min_eval_concurrency),
        "resolved_eval_concurrency": resolved_eval_concurrency,
        "live_stack_contract": live_stack_contract,
        "retry_plan": retry_plan,
        "blockers": blockers,
        "preflight": {"autopilot_active": autopilot_active},
        "per_role": merged_per_role,
        "decision_grade_notes": [
            "requires --apply --confirm-clean-window",
            "requires AutoPilot inactive unless --allow-autopilot-active",
            "decision_grade applies to the MERGED (prior scored + retried) pool",
            f"requires every merged arm reliability >= {DECISION_GRADE_RELIABILITY_FLOOR} "
            "and real confidence provenance",
        ],
    }
    return report, rc


def write_retry_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "summary.json"
    md_path = output_dir / "summary.md"
    report.setdefault("schema_version", RETRY_REPORT_SCHEMA_VERSION)
    _atomic_write_json(json_path, report)
    lines = [
        "# Eval-Batch Serving Error-Requeue (Merged)",
        "",
        f"- status: `{report['status']}`",
        f"- decision_grade: `{report['decision_grade']}`",
        f"- retry_source_run: `{report['retry_source_run']}`",
        f"- retried_n: `{report['retried_n']}`  merged: `{report['merged']}`",
    ]
    if report.get("blockers"):
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- {b}" for b in report["blockers"])
    if report.get("decision_grade_reasons"):
        lines.extend(["", "## Decision-Grade Demotions", ""])
        lines.extend(f"- {r}" for r in report["decision_grade_reasons"])
    lines.extend(["", "## Merged Per-Role", ""])
    for role, payload in (report.get("per_role") or {}).items():
        lines.append(f"- `{role}`: `{json.dumps(payload, sort_keys=True)}`")
    _atomic_write_text(md_path, "\n".join(lines) + "\n")
    return json_path, md_path


# --resume-incomplete-from <dir> reads a prior INCOMPLETE run's per-arm
# question_results.<arm>.jsonl sidecars + its summary.json, reconstructs the SAME
# dataset draw (suite/split/seed/full derived from the prior summary; refuses on a
# dataset_sha256 mismatch), skips every ordinal that already has ANY question_result
# row (any verdict — reruning error rows is --retry-errors-from's job), runs ONLY the
# missing remainder, and emits a MERGED summary (prior rows + resumed rows) with
# resume provenance. Same --apply/--confirm-clean-window gating; decision_grade
# applies to the MERGED pool.


def _read_prior_summary(directory: Path) -> dict[str, Any]:
    """Read a prior run's ``summary.json`` for resume provenance (best-effort)."""
    path = Path(directory) / "summary.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _prior_dataset_sha256(prior_summary: dict[str, Any]) -> str | None:
    """dataset_sha256 lives top-level (retry/resume summaries) or under result
    (verifier/calibration summaries)."""
    top = prior_summary.get("dataset_sha256")
    if top:
        return str(top)
    result = prior_summary.get("result")
    if isinstance(result, dict) and result.get("dataset_sha256"):
        return str(result["dataset_sha256"])
    return None


def build_resume_report(
    args: argparse.Namespace, *, output_dir: Path
) -> tuple[dict[str, Any], int]:
    """Plan (default) or run a resume-the-remainder pass from a prior incomplete run.

    Plan-only unless ``--apply --confirm-clean-window`` (AutoPilot inactive unless
    overridden) — identical live-execution gating to verifier/retry mode. Derives the
    dataset provenance (suite/split/seed/scoring/full/n + dataset_sha256) from the
    prior run's summary.json and refuses if the reconstructed dataset drifts.
    """
    source_dir = Path(args.resume_incomplete_from)
    roles_filter = [p.strip() for p in (args.roles or "").split(",") if p.strip()]
    preflight = activation_window.build_preflight(_activation_args(args))
    autopilot_active = bool(preflight.get("autopilot_active"))

    blockers: list[str] = []
    status = "plan_only"
    rc = 0
    resolved_eval_concurrency: int | None = None
    live_stack_contract: dict[str, Any] | None = None
    min_eval_concurrency = _effective_min_eval_concurrency(args)
    merged_per_role: dict[str, Any] = {}
    resume_plan: dict[str, Any] = {}

    prior_summary: dict[str, Any] = {}
    if not source_dir.exists():
        blockers.append(f"--resume-incomplete-from source dir not found: {source_dir}")
        arms: dict[str, Any] = {}
    else:
        arms = load_arm_question_rows(source_dir)
        if not arms:
            blockers.append(
                f"no question_results.<arm>.jsonl sidecars under {source_dir} "
                "(prior run predates per-arm persistence, or wrong dir)"
            )
        prior_summary = _read_prior_summary(source_dir)
        if not prior_summary:
            blockers.append(
                f"no readable summary.json under {source_dir} — resume needs prior "
                "provenance (suite/split/seed/dataset_sha256)"
            )

    prior_suite = prior_summary.get("suite") or args.suite
    prior_split = prior_summary.get("split") if "split" in prior_summary else args.split
    prior_seed = prior_summary.get("seed", args.seed)
    prior_scoring = prior_summary.get("scoring")
    prior_full = bool(prior_summary.get("full"))
    prior_n = prior_summary.get("n")
    prior_sha = _prior_dataset_sha256(prior_summary)
    prior_total = prior_summary.get("n_questions") or (
        (prior_summary.get("result") or {}).get("n_questions")
        if isinstance(prior_summary.get("result"), dict)
        else None
    )
    if prior_summary and not prior_suite:
        blockers.append("prior summary.json has no suite; cannot reconstruct the dataset to resume")
    if prior_summary and not prior_sha:
        blockers.append(
            "prior summary.json has no dataset_sha256; refusing to resume without a "
            "reproducibility stamp to validate against"
        )

    # Build the plan: per arm, how many rows are already done vs still missing.
    for label, arm in arms.items():
        role = arm["role"]
        if roles_filter and role not in roles_filter:
            continue
        completed_ids = sorted({_row_identity(r) for r in arm["rows"] if _row_identity(r)})
        remaining_estimate = (
            max(0, int(prior_total) - len(completed_ids)) if prior_total is not None else None
        )
        resume_plan[role] = {
            "arm_label": label,
            "suite": arm.get("suite") or prior_suite,
            "scoring": arm.get("scoring") or prior_scoring,
            "prior_rows": len(arm["rows"]),
            "completed_ids": len(completed_ids),
            "remaining_estimate": remaining_estimate,
            "complete": arm.get("complete"),
        }
    if arms and not resume_plan:
        blockers.append(
            "no arms matched the requested --roles for resume "
            f"(available: {sorted({a['role'] for a in arms.values()})})"
        )

    if not args.apply:
        status = "plan_only"
    else:
        resolved_eval_concurrency = _resolved_eval_concurrency(roles_filter or None)
        live_stack_contract = _optimized_live_stack_status()
        if _missing_concurrency_guard(args):
            blockers.append(
                "--apply requires explicit --min-eval-concurrency N or --allow-serial; "
                "refusing to silently serialize an eval-fanout run"
            )
        if not args.confirm_clean_window:
            blockers.append("resume-mode execution requires --confirm-clean-window")
        if autopilot_active and not args.allow_autopilot_active:
            blockers.append(
                "AutoPilot appears active; pass --allow-autopilot-active to override"
            )
        if not live_stack_contract.get("ok", False):
            warning_count = len(live_stack_contract.get("warnings") or [])
            blockers.append(
                f"live stack launch contract has {warning_count} warning(s); "
                "refusing to measure a drifted/non-optimized v7 stack"
            )
        if (
            min_eval_concurrency > 1
            and resolved_eval_concurrency < min_eval_concurrency
        ):
            blockers.append(
                f"resolved EvalTower concurrency {resolved_eval_concurrency} is below "
                f"--min-eval-concurrency {min_eval_concurrency}"
            )
        if blockers:
            status = "blocked"
            rc = _bool_blocker_rc(blockers)
        else:
            try:
                tower = EvalTower(
                    url=args.api_url.rstrip("/"),
                    timeout=args.evaltower_timeout_s,
                )
                tower.set_question_artifact_dir(output_dir)
                any_resumed = False
                for role, plan in resume_plan.items():
                    arm_rows = arms[plan["arm_label"]]["rows"]
                    completed_ids = [_row_identity(r) for r in arm_rows if _row_identity(r)]
                    subset = tower.eval_resume_incomplete(
                        suite=prior_suite,
                        split=prior_split,
                        roles=[role],
                        seed=int(prior_seed),
                        scoring=plan.get("scoring"),
                        n=prior_n,
                        full=prior_full,
                        completed_ids=completed_ids,
                        expected_dataset_sha256=prior_sha,
                    )
                    resumed_rows = (
                        (subset.get("per_role") or {}).get(role, {}).get("rows") or []
                    )
                    if subset.get("resumed_n"):
                        any_resumed = True
                    merged = merge_prior_and_retried(arm_rows, resumed_rows, role=role)
                    merged["resumed_n"] = int(subset.get("resumed_n", len(resumed_rows)))
                    merged["resume_completed_n"] = int(subset.get("resume_completed_n", 0))
                    merged_per_role[role] = merged
                status = "complete" if any_resumed else "nothing_to_resume"
            except _RunInterrupted as exc:
                blockers.append(f"resume-mode eval interrupted by {exc}")
                status = "interrupted"
                rc = 130
            except ValueError as exc:
                # dataset drift / empty draw => refuse, do not measure.
                blockers.append(f"resume refused: {exc}")
                status = "dataset_mismatch"
                rc = 75
            except Exception as exc:  # noqa: BLE001 - report artifact captures failures
                blockers.append(f"resume-mode eval failed: {exc}")
                status = "eval_failed"
                rc = 75

    merged_result = {"per_role": merged_per_role} if merged_per_role else None
    decision_grade_reasons = (
        _decision_grade_quality_reasons(merged_result) if merged_result else []
    )
    decision_grade = bool(
        args.apply
        and args.confirm_clean_window
        and not args.allow_autopilot_active
        and not blockers
        and merged_result is not None
        and not decision_grade_reasons
    )
    resumed_n = sum(int(v.get("resumed_n", 0)) for v in merged_per_role.values())
    resume_completed_n = sum(int(v.get("resume_completed_n", 0)) for v in merged_per_role.values())
    report = {
        "schema_version": RESUME_REPORT_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "mode": "resume_incomplete",
        "status": status,
        "decision_grade": decision_grade,
        "decision_grade_reasons": decision_grade_reasons,
        "applied": bool(args.apply),
        "merged": True,
        "resumed": True,
        "resume_source_run": str(source_dir),
        "resumed_n": resumed_n,
        "resume_completed_n": resume_completed_n,
        "suite": prior_suite,
        "split": prior_split,
        "seed": prior_seed,
        "scoring": prior_scoring,
        "full": prior_full,
        "dataset_sha256": prior_sha,
        "roles": roles_filter,
        "api_url": args.api_url.rstrip("/"),
        "min_eval_concurrency": int(min_eval_concurrency),
        "resolved_eval_concurrency": resolved_eval_concurrency,
        "live_stack_contract": live_stack_contract,
        "resume_plan": resume_plan,
        "blockers": blockers,
        "preflight": {"autopilot_active": autopilot_active},
        "per_role": merged_per_role,
        "decision_grade_notes": [
            "requires --apply --confirm-clean-window",
            "requires AutoPilot inactive unless --allow-autopilot-active",
            "resume runs only ordinals with NO prior verdict; error rows are "
            "--retry-errors-from's job",
            "decision_grade applies to the MERGED (prior + resumed) pool",
            f"requires every merged arm reliability >= {DECISION_GRADE_RELIABILITY_FLOOR} "
            "and real confidence provenance",
        ],
    }
    return report, rc


def write_resume_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "summary.json"
    md_path = output_dir / "summary.md"
    report.setdefault("schema_version", RESUME_REPORT_SCHEMA_VERSION)
    _atomic_write_json(json_path, report)
    lines = [
        "# Eval-Batch Serving Resume-Incomplete (Merged)",
        "",
        f"- status: `{report['status']}`",
        f"- decision_grade: `{report['decision_grade']}`",
        f"- resume_source_run: `{report['resume_source_run']}`",
        f"- resumed_n: `{report['resumed_n']}`  resume_completed_n: "
        f"`{report['resume_completed_n']}`  merged: `{report['merged']}`",
        f"- suite/split: `{report['suite']} / {report['split']}`  seed: `{report['seed']}`",
        f"- dataset_sha256: `{report['dataset_sha256']}`",
    ]
    if report.get("blockers"):
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- {b}" for b in report["blockers"])
    if report.get("decision_grade_reasons"):
        lines.extend(["", "## Decision-Grade Demotions", ""])
        lines.extend(f"- {r}" for r in report["decision_grade_reasons"])
    lines.extend(["", "## Resume Plan", ""])
    for role, payload in (report.get("resume_plan") or {}).items():
        lines.append(f"- `{role}`: `{json.dumps(payload, sort_keys=True)}`")
    lines.extend(["", "## Merged Per-Role", ""])
    for role, payload in (report.get("per_role") or {}).items():
        lines.append(f"- `{role}`: `{json.dumps(payload, sort_keys=True)}`")
    _atomic_write_text(md_path, "\n".join(lines) + "\n")
    return json_path, md_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default=os.environ.get("ORCHESTRATOR_API_URL", DEFAULT_API_URL))
    parser.add_argument(
        "--eval-batch-url",
        default=os.environ.get("ORCHESTRATOR_EVAL_BATCH_FRONTDOOR_URL", DEFAULT_EVAL_BATCH_URL),
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-clean-window", action="store_true")
    parser.add_argument("--allow-autopilot-active", action="store_true")
    parser.add_argument("--skip-current-arm", action="store_true")
    parser.add_argument(
        "--skip-batch-arm",
        action="store_true",
        help=(
            "Measure ONLY the current EvalTower arm (R3 eval-lane pricing "
            "re-baseline): no eval-batch activation, no 18070 launch. Added "
            "2026-07-23 — under the restored big+quarters lineup the "
            "batch-shaped NODE0 lane thread-overlaps the live half instances."
        ),
    )
    parser.add_argument("--keep-enabled", action="store_true")
    parser.add_argument("--tap-events", default=None)
    parser.add_argument("--tier", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    # ── verifier-mode (EV-4 / EV-11 / EV-5/7/8) additive flags ───────────────
    # Default --mode tier keeps the existing tier-based A/B path byte-identical.
    parser.add_argument(
        "--mode",
        choices=("tier", "calibration", "math_rebaseline"),
        default="tier",
        help="tier = existing eval-batch A/B (default); calibration = EV-4 "
        "per-role calibration baseline; math_rebaseline = EV-11 GSM8K+MATH-500.",
    )
    parser.add_argument(
        "--suite",
        default=None,
        help="Verifier-mode suite (e.g. scoring_verifiers for EV-4 HE-R+).",
    )
    parser.add_argument(
        "--split",
        default=None,
        help="Verifier-mode split/subset selector (e.g. HE-R+, gsm8k, math500).",
    )
    parser.add_argument(
        "--roles",
        default=None,
        help="Comma-separated roles to force per arm (default: worker_general).",
    )
    parser.add_argument(
        "--scoring",
        default="math_verify",
        help="Scoring method for math_rebaseline (default: math_verify).",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Use the whole split (EV-4) / full 1,819-question math set (EV-11); "
        "ignores --n.",
    )
    parser.add_argument(
        "--verifier",
        default=None,
        help="EV-5/7/8 cross-family verifier model selector (PRM/Ouro/SAE). The "
        "MODE exists but the verifier-model pass is MODEL-DOWNLOAD gated.",
    )
    parser.add_argument(
        "--retry-errors-from",
        type=Path,
        default=None,
        help="EV-11c error requeue: read a prior run's per-arm "
        "question_results.<arm>.jsonl sidecars, rerun ONLY the error rows for the "
        "requested --roles, and emit a MERGED summary (prior scored + retried). "
        "Same --apply/--confirm-clean-window gating; overrides --mode.",
    )
    parser.add_argument(
        "--resume-incomplete-from",
        type=Path,
        default=None,
        help="Resume an INCOMPLETE prior run: read its per-arm "
        "question_results.<arm>.jsonl sidecars + summary.json, reconstruct the SAME "
        "dataset (refusing on a dataset_sha256 mismatch), run ONLY the ordinals with "
        "no prior verdict (error rows are --retry-errors-from's job), and emit a "
        "MERGED summary (prior + resumed). Same --apply/--confirm-clean-window "
        "gating; overrides --mode. Mutually exclusive with --retry-errors-from.",
    )
    parser.add_argument(
        "--min-eval-concurrency",
        type=int,
        default=None,
        help=(
            "Fail before live EvalTower execution unless resolved eval fanout is at least N. "
            "Required for --apply unless --allow-serial is explicit."
        ),
    )
    parser.add_argument(
        "--allow-serial",
        action="store_true",
        help="Explicitly permit --apply when EvalTower fanout resolves to serial execution.",
    )
    parser.add_argument("--attest-samples", type=int, default=12)
    parser.add_argument("--http-timeout-s", type=float, default=5.0)
    parser.add_argument("--command-timeout-s", type=float, default=900.0)
    # Per-question eval request budget. Default deferred (None) to the standard
    # env-aware eval default (`_default_eval_timeout` -> honors
    # AUTOPILOT_EVAL_REQUEST_TIMEOUT_S) so an operator who raises that env for a
    # rebaseline actually gets the longer budget. Previously this hardcoded 120.0,
    # which SILENTLY overrode the env on every EvalTower(...) construction below
    # (the runner always passes timeout=args.evaltower_timeout_s), capping every
    # heavy-suite question at 120s regardless of the env — the EV-BASELINE-E7
    # 119-120s timeouts. An explicit --evaltower-timeout-s still wins.
    parser.add_argument("--evaltower-timeout-s", type=float, default=None)
    parser.add_argument(
        "--start-mode",
        choices=("only", "include-warm"),
        default="only",
        help="How to start eval_batch_frontdoor during the temporary activation.",
    )
    args = parser.parse_args(argv)
    # Resolve the deferred eval budget to the env-aware standard default so a
    # raised AUTOPILOT_EVAL_REQUEST_TIMEOUT_S reaches EvalTower(timeout=...) —
    # and thus the per-question timeout_s/deadline that reaches the backend.
    if args.evaltower_timeout_s is None:
        args.evaltower_timeout_s = float(_default_eval_timeout())
    if args.skip_current_arm and getattr(args, "skip_batch_arm", False):
        parser.error("--skip-current-arm and --skip-batch-arm together leave nothing to measure")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = args.output_dir or default_output_dir()
    if args.retry_errors_from is not None and args.resume_incomplete_from is not None:
        raise SystemExit(
            "--retry-errors-from and --resume-incomplete-from are mutually exclusive "
            "(rerun errors vs run the missing remainder)"
        )
    if args.retry_errors_from is not None:
        report, rc = build_retry_report(args, output_dir=output_dir)
        json_path, md_path = write_retry_report(report, output_dir)
    elif args.resume_incomplete_from is not None:
        report, rc = build_resume_report(args, output_dir=output_dir)
        json_path, md_path = write_resume_report(report, output_dir)
    elif args.mode != "tier":
        report, rc = build_verifier_report(args, output_dir=output_dir)
        json_path, md_path = write_verifier_report(report, output_dir)
    else:
        report, rc = build_report(args, output_dir=output_dir)
        json_path, md_path = write_report(report, output_dir)
    if not args.summary_only:
        print(json.dumps(report, indent=2, sort_keys=True))
        print(f"\nwrote {json_path}")
        print(f"wrote {md_path}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
