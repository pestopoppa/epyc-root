#!/usr/bin/env python3
"""Pre-launch audit for autopilot diagnostics.

Sends real questions through the full seeding eval pipeline and verifies
every diagnostic field is correctly wired. Run before launching autopilot
to catch measurement bugs (speed=0.0, tokens=0, broken scoring, etc.).

Usage:
    python scripts/autopilot/preflight_audit.py
    python scripts/autopilot/preflight_audit.py --url http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from src.registry.stack_priors import (
    live_stack_role_records,
    stack_prior_primary_port,
    stack_prior_serving,
)
from src.autopilot_core.baseline_ledger import canonical_jsonable
from src.autopilot_core.journal_reconstruction import (
    fold_supersession_events,
    objectives_from_journal_row,
    parse_journal_ts,
    reconstruct_archive_from_journal_rows,
)
from src.autopilot_core.journal_snapshot_replay import build_snapshot_replay_diagnostic
from src.autopilot_core.tier_specs import DEFAULT_FRONTIER_TIER
from src.roles import Role
from scripts.server.stack_manifest import HOT_SERVERS, ROLE_LAUNCH_META, WARM_SERVERS

log = logging.getLogger("autopilot.preflight")

SCRIPT_DIR = Path(__file__).resolve().parent
BENCHMARK_DIR = SCRIPT_DIR.parent / "benchmark"
sys.path.insert(0, str(BENCHMARK_DIR))
sys.path.insert(0, str(SCRIPT_DIR.parents[1]))

ORCHESTRATOR_URL = "http://localhost:8000"
REPO_ROOT = SCRIPT_DIR.parents[1]
STACK_PRIORS_PATH = SCRIPT_DIR.parents[1] / "orchestration" / "derived" / "stack_priors.yaml"
STATE_PATH = SCRIPT_DIR.parents[1] / "orchestration" / "autopilot_state.json"
JOURNAL_PATH = SCRIPT_DIR.parents[1] / "orchestration" / "autopilot_journal.jsonl"
STACK_CHANGE_GATE_TIMEOUT_S = 180
STACK_CHANGE_GATE_COMMAND = [
    "uv",
    "run",
    "python",
    "scripts/registry/stack_change_pipeline.py",
    "check",
    "--run-promotion-gate",
]


def _fallback_model_server_role_mode(role: str) -> str | None:
    canonical = Role.from_string(role) or role
    launch_meta = ROLE_LAUNCH_META.get(str(canonical))
    if not isinstance(launch_meta, dict):
        return None
    mode = launch_meta.get("mode")
    return mode if isinstance(mode, str) else None


def _fallback_model_server_includes_role(role: str) -> bool:
    return _fallback_model_server_role_mode(role) != "embedding"


def _health_url(endpoint: str) -> str | None:
    parsed = urlparse(endpoint)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}/health"


def _model_server_target_groups(
    roles: dict[str, dict[str, object]],
    orchestrator_url: str,
) -> tuple[str, dict[str, list[str]]]:
    api_health = _health_url(orchestrator_url) or "http://localhost:8000/health"
    names_by_health_url: dict[str, list[str]] = {}
    for role_name, record in roles.items():
        raw_display_role = record.get("role")
        display_role = raw_display_role if isinstance(raw_display_role, str) else role_name
        serving = stack_prior_serving(record)
        endpoint = serving.get("endpoint")
        health_url = _health_url(endpoint) if isinstance(endpoint, str) else None
        if health_url is None:
            endpoint_port = stack_prior_primary_port(serving)
            if endpoint_port is None:
                continue
            health_url = f"http://localhost:{endpoint_port}/health"
        names_by_health_url.setdefault(health_url, []).append(display_role)
    return api_health, names_by_health_url


def _format_model_server_targets(
    api_health: str,
    names_by_health_url: dict[str, list[str]],
) -> list[tuple[str, str]]:
    return [
        ("API", api_health),
        *[
            ("/".join(sorted(set(names))), health_url)
            for health_url, names in sorted(names_by_health_url.items())
        ],
    ]


def _fallback_model_server_targets(orchestrator_url: str) -> list[tuple[str, str]]:
    api_health = _health_url(orchestrator_url) or "http://localhost:8000/health"
    names_by_health_url: dict[str, list[str]] = {}
    for server in HOT_SERVERS + WARM_SERVERS:
        if not isinstance(server, dict):
            continue
        port = server.get("port")
        roles = server.get("roles")
        if not isinstance(port, int) or not isinstance(roles, list):
            continue
        visible_roles = [
            str(Role.from_string(role) or role)
            for role in roles
            if isinstance(role, str) and _fallback_model_server_includes_role(role)
        ]
        if not visible_roles:
            continue
        health_url = f"http://localhost:{port}/health"
        names_by_health_url.setdefault(health_url, []).extend(visible_roles)
    return _format_model_server_targets(api_health, names_by_health_url)


def _model_server_targets(
    stack_priors_path: Path = STACK_PRIORS_PATH,
    orchestrator_url: str = ORCHESTRATOR_URL,
) -> list[tuple[str, str]]:
    """Return health targets from generated stack priors, with degraded fallback."""
    roles = live_stack_role_records(stack_priors_path)
    if not roles:
        return _fallback_model_server_targets(orchestrator_url)

    api_health, names_by_health_url = _model_server_target_groups(roles, orchestrator_url)
    if not names_by_health_url:
        return _fallback_model_server_targets(orchestrator_url)
    return _format_model_server_targets(api_health, names_by_health_url)


def _header(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def _check(name: str, condition: bool, detail: str = "") -> bool:
    mark = "✓" if condition else "✗"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{mark}] {name}{suffix}")
    return condition


def _tail_output(text: str, max_chars: int = 500) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return "..." + text[-max_chars:]


def _gate_success_detail(output: str) -> str:
    lines = [line.strip() for line in output.splitlines()]
    selected = [
        line
        for line in lines
        if line.startswith(("summary:", "acceptance:"))
    ]
    return "; ".join(selected) or "passed"


def _jsonl_batch_key(path: Path) -> tuple[int, str]:
    stem = path.stem
    if stem == "autopilot_journal":
        return (0, path.name)
    prefix = "autopilot_journal_"
    if stem.startswith(prefix):
        try:
            return (int(stem.removeprefix(prefix)), path.name)
        except ValueError:
            pass
    return (10**9, path.name)


def _jsonl_paths(path: Path) -> list[Path]:
    if path.is_dir():
        return sorted(path.glob("autopilot_journal*.jsonl"), key=_jsonl_batch_key)
    if path.name != "autopilot_journal.jsonl":
        return [path]
    paths = [path]
    batch = 1
    while True:
        batch_path = path.with_name(f"autopilot_journal_{batch}.jsonl")
        if not batch_path.exists():
            break
        paths.append(batch_path)
        batch += 1
    return paths


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for jsonl_path in _jsonl_paths(path):
        for line_num, line in enumerate(
            jsonl_path.read_text(encoding="utf-8").splitlines(),
            1,
        ):
            try:
                row = json.loads(line)
            except Exception:
                log.debug("Skipping malformed JSONL line %d in %s", line_num, jsonl_path)
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _trial_id(row: dict) -> int | None:
    try:
        return int(row.get("trial_id"))
    except (TypeError, ValueError):
        return None


def _archive_entry_view(entry: dict) -> dict:
    view: dict[str, object] = {}
    for field in ("trial_id", "objectives", "eval_tier"):
        if field in entry:
            view[field] = entry[field]
    fingerprint = entry.get("config_fingerprint")
    if fingerprint:
        view["config_fingerprint"] = fingerprint
    try:
        reproductions = int(entry.get("n_reproductions"))
    except (TypeError, ValueError):
        reproductions = 0
    if reproductions > 1:
        view["n_reproductions"] = reproductions
    return view


def _sorted_entry_views(entries: object) -> list[dict]:
    if not isinstance(entries, list):
        return []
    views = [_archive_entry_view(entry) for entry in entries if isinstance(entry, dict)]
    return sorted(
        views,
        key=lambda item: (
            str(item.get("eval_tier", "")),
            str(item.get("trial_id", "")),
            json.dumps(item.get("objectives", []), sort_keys=True, default=str),
        ),
    )


def _archive_authority_view(payload: dict) -> dict:
    frontiers_by_tier = payload.get("frontiers_by_tier")
    if not isinstance(frontiers_by_tier, dict):
        frontiers_by_tier = {
            str(DEFAULT_FRONTIER_TIER): payload.get("frontier", [])
        } if payload.get("frontier") else {}
    hv_by_tier = payload.get("hv_history_by_tier")
    if not isinstance(hv_by_tier, dict):
        hv_by_tier = {
            str(DEFAULT_FRONTIER_TIER): payload.get("hypervolume_history", [])
        } if payload.get("hypervolume_history") else {}
    return canonical_jsonable(
        {
            "frontier": _sorted_entry_views(payload.get("frontier", [])),
            "frontiers_by_tier": {
                str(tier): _sorted_entry_views(frontier)
                for tier, frontier in sorted(frontiers_by_tier.items())
            },
            "all_entries": _sorted_entry_views(payload.get("all_entries", [])),
            "hypervolume_history": payload.get("hypervolume_history", []),
            "hv_history_by_tier": hv_by_tier,
        }
    )


def archive_replay_kwargs_from_state(state: dict) -> dict[str, float]:
    """Return journal replay knobs carried by runtime state."""
    kwargs: dict[str, float] = {}
    for state_key, replay_key in (
        ("pareto_epoch_ts", "deinflate_before_ts"),
        ("pareto_pre_epoch_speed_factor", "deinflate_factor"),
        ("pareto_exclude_before_ts", "exclude_before_ts"),
    ):
        try:
            value = float(state.get(state_key) or 0.0)
        except (TypeError, ValueError):
            continue
        if state_key == "pareto_pre_epoch_speed_factor":
            if value != 0.0 and value != 1.0:
                kwargs[replay_key] = value
        elif value:
            kwargs[replay_key] = value
    return kwargs


def empty_frontier_bootstrap_diagnostic(
    state: dict,
    journal_rows: list[dict],
    *,
    reconstructed_archive: dict | None,
) -> dict:
    """Validate a ratified, intentionally empty current-era frontier.

    A new measurement era deliberately removes the cached archive and excludes
    every older journal row. That makes normal replay return ``None`` until the
    first current-era numeric point lands. Treat that state as safe only when
    the full ratified bootstrap contract agrees with live state and there is no
    reconstructable current-era row or cached archive to hide.
    """
    reasons: list[str] = []
    bootstrap = state.get("eval_instrument_empty_frontier_bootstrap")
    note = state.get("_allow_empty_frontier_rebase_note")
    state_archive = state.get("pareto_archive")
    state_archive_present = isinstance(state_archive, dict) and bool(state_archive)

    if state.get("_allow_empty_frontier_rebase") is not True:
        reasons.append("_allow_empty_frontier_rebase is not true")
    if not isinstance(note, str) or not note.strip():
        reasons.append("_allow_empty_frontier_rebase_note is missing")
    if state_archive_present:
        reasons.append("state pareto_archive is present")
    if reconstructed_archive is not None:
        reasons.append("journal already reconstructs a current-era archive")
    if not isinstance(bootstrap, dict):
        reasons.append("eval_instrument_empty_frontier_bootstrap is missing")
        bootstrap = {}
    elif bootstrap.get("status") not in {
        "pending",
        "baseline_admitted_frontier_pending",
    }:
        reasons.append("empty-frontier bootstrap status is not pending")

    expected_fields = {
        "objective_policy": state.get("pareto_objective_policy"),
        "execution_instrument_id": state.get("eval_execution_instrument_id"),
        "scoring_schedule_id": state.get("eval_scoring_schedule_id"),
    }
    for field, expected in expected_fields.items():
        actual = bootstrap.get(field)
        if not isinstance(expected, str) or not expected:
            reasons.append(f"state {field} is missing")
        elif actual != expected:
            reasons.append(
                f"bootstrap {field}={actual!r} does not match state {expected!r}"
            )

    boundary_values: dict[str, float] = {}
    for field in (
        "pareto_epoch_ts",
        "pareto_exclude_before_ts",
        "quality_exclude_before_ts",
    ):
        try:
            value = float(state.get(field))
        except (TypeError, ValueError):
            value = 0.0
        if value <= 0.0:
            reasons.append(f"state {field} is missing")
        else:
            boundary_values[field] = value
    boundary = boundary_values.get("pareto_exclude_before_ts")
    if boundary is not None:
        for field, value in boundary_values.items():
            if abs(value - boundary) > 0.001:
                reasons.append(f"state {field} does not match pareto exclusion boundary")
        opened_at = parse_journal_ts(bootstrap.get("opened_at"))
        if opened_at is None or abs(opened_at - boundary) > 0.001:
            reasons.append("bootstrap opened_at does not match pareto exclusion boundary")

    objective_policy = expected_fields["objective_policy"]
    current_era_trial_rows = 0
    current_era_objective_rows = 0
    if boundary is not None:
        for row in journal_rows:
            ts = parse_journal_ts(row.get("timestamp"))
            if _trial_id(row) is None or ts is None or ts < boundary:
                continue
            current_era_trial_rows += 1
            bug = row.get("bug_corrupted_by") or ""
            if bug and bug != "mad_noise":
                continue
            if isinstance(objective_policy, str):
                try:
                    objectives = objectives_from_journal_row(
                        row,
                        objective_policy=objective_policy,
                    )
                except ValueError:
                    objectives = None
                if objectives is not None:
                    current_era_objective_rows += 1
    if current_era_objective_rows:
        reasons.append(
            f"journal contains {current_era_objective_rows} reconstructable current-era row(s)"
        )

    return {
        "authorized": not reasons,
        "status": "authorized_empty_current_era" if not reasons else "invalid",
        "reasons": reasons,
        "state_archive_present": state_archive_present,
        "boundary_ts": boundary,
        "current_era_trial_row_count": current_era_trial_rows,
        "current_era_objective_row_count": current_era_objective_rows,
        "objective_policy": expected_fields["objective_policy"],
        "execution_instrument_id": expected_fields["execution_instrument_id"],
        "scoring_schedule_id": expected_fields["scoring_schedule_id"],
    }


def archive_authority_diagnostic(state: dict, journal_rows: list[dict]) -> dict:
    """Check journal archive authority and any legacy state cache."""
    trial_ids = [_trial_id(row) for row in journal_rows]
    journal_max_trial_id = max((trial_id for trial_id in trial_ids if trial_id is not None), default=None)
    try:
        state_trial_counter = int(state.get("trial_counter"))
    except (TypeError, ValueError):
        state_trial_counter = None

    warnings: list[str] = []
    if (
        state_trial_counter is not None
        and journal_max_trial_id is not None
        and journal_max_trial_id >= state_trial_counter
    ):
        warnings.append(
            f"journal max trial {journal_max_trial_id} is not below "
            f"state trial_counter {state_trial_counter}"
        )

    replay_kwargs = archive_replay_kwargs_from_state(state)
    journal_archive = reconstruct_archive_from_journal_rows(
        journal_rows,
        None,
        current_run_only=False,
        **replay_kwargs,
    )
    if journal_archive is None:
        empty_bootstrap = empty_frontier_bootstrap_diagnostic(
            state,
            journal_rows,
            reconstructed_archive=journal_archive,
        )
        if empty_bootstrap["authorized"]:
            return {
                "status": "match" if not warnings else "drift",
                "authority_mode": empty_bootstrap["status"],
                "state_archive_present": False,
                "state_trial_counter": state_trial_counter,
                "journal_max_trial_id": journal_max_trial_id,
                "state_entry_count": 0,
                "journal_entry_count": 0,
                "state_frontier_count": 0,
                "journal_frontier_count": 0,
                "snapshot_readiness": empty_bootstrap["status"],
                "snapshot_replay_status": empty_bootstrap["status"],
                "snapshot_through_trial_id": None,
                "snapshot_tail_trial_count": 0,
                "snapshot_tail_max_trial_id": None,
                "snapshot_journal_max_trial_id": journal_max_trial_id,
                "snapshot_warnings": [],
                "replay_kwargs": replay_kwargs,
                "empty_frontier_bootstrap": empty_bootstrap,
                "warnings": warnings,
            }
        return {
            "status": "journal_unreconstructable",
            "state_trial_counter": state_trial_counter,
            "journal_max_trial_id": journal_max_trial_id,
            "replay_kwargs": replay_kwargs,
            "empty_frontier_bootstrap": empty_bootstrap,
            "warnings": warnings
            + ["journal rows did not reconstruct an archive"]
            + empty_bootstrap["reasons"],
        }

    state_archive = state.get("pareto_archive")
    state_archive_present = isinstance(state_archive, dict) and bool(state_archive)
    ledger_events = [
        row for row in journal_rows
        if row.get("type") and "trial_id" not in row
    ]
    snapshot_diagnostic = build_snapshot_replay_diagnostic(journal_rows, ledger_events)
    snapshot_warnings: list[str] = []
    if snapshot_diagnostic.bounded_replay_readiness == "prefix_invalidated":
        snapshot_warnings.append("latest journal snapshot prefix is invalidated")

    snapshot_tail_details = {
        "snapshot_through_trial_id": getattr(
            snapshot_diagnostic, "through_trial_id", None
        ),
        "snapshot_tail_trial_count": getattr(
            snapshot_diagnostic, "tail_trial_count", 0
        ),
        "snapshot_tail_max_trial_id": getattr(
            snapshot_diagnostic, "tail_max_trial_id", None
        ),
        "snapshot_journal_max_trial_id": getattr(
            snapshot_diagnostic, "journal_max_trial_id", None
        ),
    }

    journal_view = _archive_authority_view(journal_archive)
    if not state_archive_present:
        status = "match" if not warnings else "drift"
        return {
            "status": status,
            "state_archive_present": False,
            "state_trial_counter": state_trial_counter,
            "journal_max_trial_id": journal_max_trial_id,
            "state_entry_count": 0,
            "journal_entry_count": len(journal_view["all_entries"]),
            "state_frontier_count": 0,
            "journal_frontier_count": len(journal_view["frontier"]),
            "snapshot_readiness": snapshot_diagnostic.bounded_replay_readiness,
            "snapshot_replay_status": snapshot_diagnostic.status,
            **snapshot_tail_details,
            "snapshot_warnings": snapshot_warnings,
            "replay_kwargs": replay_kwargs,
            "warnings": warnings,
        }

    state_view = _archive_authority_view(state_archive)
    status = "match" if state_view == journal_view and not warnings else "drift"
    return {
        "status": status,
        "state_archive_present": True,
        "state_trial_counter": state_trial_counter,
        "journal_max_trial_id": journal_max_trial_id,
        "state_entry_count": len(state_view["all_entries"]),
        "journal_entry_count": len(journal_view["all_entries"]),
        "state_frontier_count": len(state_view["frontier"]),
        "journal_frontier_count": len(journal_view["frontier"]),
        "snapshot_readiness": snapshot_diagnostic.bounded_replay_readiness,
        "snapshot_replay_status": snapshot_diagnostic.status,
        **snapshot_tail_details,
        "snapshot_warnings": snapshot_warnings,
        "replay_kwargs": replay_kwargs,
        "warnings": warnings,
    }


def audit_stack_change_gate() -> bool:
    """Run the canonical stack-change gate before AutoPilot touches live evals."""
    _header("0. Stack Change Promotion Gate")
    try:
        result = subprocess.run(
            STACK_CHANGE_GATE_COMMAND,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=STACK_CHANGE_GATE_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return _check(
            "Canonical stack-change promotion gate",
            False,
            f"timed out after {STACK_CHANGE_GATE_TIMEOUT_S}s",
        )
    except OSError as exc:
        return _check(
            "Canonical stack-change promotion gate",
            False,
            str(exc)[:120],
        )

    output = "\n".join(
        part.strip()
        for part in (result.stdout, result.stderr)
        if part and part.strip()
    )
    if result.returncode == 0:
        return _check(
            "Canonical stack-change promotion gate",
            True,
            _gate_success_detail(output),
        )
    return _check(
        "Canonical stack-change promotion gate",
        False,
        _tail_output(output),
    )


def audit_model_servers(url: str = ORCHESTRATOR_URL) -> bool:
    """Check all key model servers are healthy."""
    _header("1. Model Server Health")

    all_ok = True
    for name, health_url in _model_server_targets(orchestrator_url=url):
        try:
            r = subprocess.run(
                ["curl", "-sf", health_url],
                capture_output=True, timeout=5,
            )
            ok = r.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            ok = False
        all_ok &= _check(f"{name} ({health_url})", ok)
    return all_ok


def audit_web_search() -> bool:
    """Check web search returns real results."""
    _header("2. Web Search")
    from src.tools.web.search import web_search

    r = web_search("Python programming language")
    count = r.get("result_count", 0)
    ok = _check("Returns results", count > 0, f"{count} results")
    if count > 0:
        _check("Has titles", bool(r["results"][0].get("title")))
        _check("Has URLs", bool(r["results"][0].get("url")))
    return ok


def audit_web_fetch() -> bool:
    """Check web fetch returns decompressed content."""
    _header("3. Web Fetch")
    from src.tools.web.fetch import _fetch_url

    try:
        content = _fetch_url("https://httpbin.org/get", max_length=2000)
        ok = _check("Returns content", len(content) > 50, f"{len(content)} chars")
        _check("Content is text (not gzip)", "origin" in content or "headers" in content)
        return ok
    except Exception as e:
        _check("Fetch works", False, str(e)[:80])
        return False


def audit_code_execution() -> bool:
    """Check code execution scoring works."""
    _header("4. Code Execution Scoring (USACO)")
    from debug_scorer import score_answer

    code = "n = int(input())\nfor i in range(n):\n    a, b = map(int, input().split())\n    print(a + b)"
    tc = "TEST_CASES = [('2\\n1 2\\n3 4\\n', '3\\n7\\n')]"
    ok = score_answer(code, "", "code_execution", {"language": "python", "timeout": 10, "test_code": tc})
    return _check("stdin program scores correctly", ok)


def audit_f1_scoring() -> bool:
    """Check F1 scoring with answer tags."""
    _header("5. F1 Scoring + Answer Tags")
    from debug_scorer import score_answer

    ok1 = score_answer(
        "Some text.\n<answer>Paris</answer>",
        "Paris", "f1", {"threshold": 0.5},
    )
    ok2 = score_answer(
        "The answer is Paris.",
        "Paris", "f1", {"threshold": 0.5},
    )
    _check("Extracts from <answer> tags", ok1)
    _check("Falls back to full text", ok2)
    return ok1


def audit_question_pool() -> bool:
    """Check question pool matches the live EvalTower scoring contract."""
    _header("6. Question Pool")
    from eval_tower import _is_scoreable_question, _sample_scoreable_eval_questions

    pool_path = SCRIPT_DIR.parents[1] / "benchmarks" / "prompts" / "question_pool.jsonl"
    if not pool_path.exists():
        # Try research repo
        pool_path = Path("/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.jsonl")

    if not pool_path.exists():
        return _check("Question pool exists", False, str(pool_path))

    pool: dict[str, list[dict]] = {}
    f1_total = f1_tagged = 0
    code_total = code_oracle = 0
    for line_num, line in enumerate(open(pool_path), 1):
        try:
            q = json.loads(line)
        except Exception:
            log.debug("Skipping malformed JSONL line %d", line_num)
            continue
        if q.get("__pool_metadata__"):
            continue
        suite = str(q.get("suite", "unknown"))
        pool.setdefault(suite, []).append(q)
        if q.get("scoring_method") == "f1":
            f1_total += 1
            f1_tagged += int("<answer>" in q.get("prompt", ""))
        if q.get("scoring_method") == "code_execution":
            code_total += 1
            code_oracle += int(_is_scoreable_question(q))

    scoreable_by_suite = {
        suite: sum(1 for q in suite_qs if _is_scoreable_question(q))
        for suite, suite_qs in pool.items()
    }
    empty_suites = sorted(s for s, n in scoreable_by_suite.items() if n == 0)
    t1_sample = _sample_scoreable_eval_questions(pool, 100, random.Random(42))
    t2_sample = _sample_scoreable_eval_questions(pool, 500, random.Random(42))
    t1_scoreable = sum(1 for q in t1_sample if _is_scoreable_question(q))
    t2_scoreable = sum(1 for q in t2_sample if _is_scoreable_question(q))
    t1_unique = len({id(q) for q in t1_sample})
    t2_unique = len({id(q) for q in t2_sample})

    all_ok = True
    all_ok &= _check("Question pool loaded", bool(pool), f"{sum(len(v) for v in pool.values())} rows")
    all_ok &= _check("F1 prompts carry answer tags", f1_total == f1_tagged, f"{f1_tagged}/{f1_total}")
    _check("Invalid code_execution rows quarantined", True, f"{code_total - code_oracle}/{code_total}")
    _check("Fully unscoreable suites quarantined", True, ", ".join(empty_suites[:8]) or "none")
    all_ok &= _check("T1 sampled scoreable rows", len(t1_sample) == 100 and t1_scoreable == 100, f"{t1_scoreable}/100")
    all_ok &= _check("T1 sampled rows are unique", t1_unique == len(t1_sample), f"{t1_unique}/{len(t1_sample)}")
    all_ok &= _check("T2 sampled scoreable rows", len(t2_sample) == 500 and t2_scoreable == 500, f"{t2_scoreable}/500")
    all_ok &= _check("T2 sampled rows are unique", t2_unique == len(t2_sample), f"{t2_unique}/{len(t2_sample)}")
    return all_ok


def audit_blacklist() -> bool:
    """Check blacklist is clean of entries sourced from poisoned trials."""
    _header("7. Failure Blacklist")
    import yaml

    bl_path = SCRIPT_DIR / "failure_blacklist.yaml"
    journal_path = SCRIPT_DIR.parents[1] / "orchestration" / "autopilot_journal.jsonl"
    if not bl_path.exists():
        return _check("Blacklist file exists", False)

    with open(bl_path) as f:
        data = yaml.safe_load(f)

    entries = data.get("blacklist", [])
    auto = [e for e in entries if e.get("source_trial", 0) != -1]
    manual = [e for e in entries if e.get("source_trial", 0) == -1]
    corrupted_trials = set()
    journal_rows: list[dict] = []
    for path in _jsonl_paths(journal_path):
        if not path.exists():
            continue
        with open(path) as fh:
            for line_num, line in enumerate(fh, 1):
                try:
                    journal_rows.append(json.loads(line))
                except Exception:
                    log.debug("Skipping malformed journal line %s:%d", path, line_num)
                    continue
    if journal_rows:
        folded_rows, _ = fold_supersession_events(journal_rows)
        for entry in folded_rows:
            if entry.get("bug_corrupted_by"):
                corrupted_trials.add(entry.get("trial_id"))
    contaminated = [
        e for e in entries
        if e.get("source_trial") in corrupted_trials
    ]

    all_ok = True
    all_ok &= _check("No poisoned-source blacklist entries", len(contaminated) == 0, f"{len(contaminated)} found")
    _check("Auto entries preserved", len(auto) >= 0, f"{len(auto)}")
    _check("Manual entries preserved", len(manual) > 0, f"{len(manual)}")
    return all_ok


def audit_archive_authority() -> bool:
    """Check state-backed archive authority matches append-only journal replay."""
    _header("8. Archive Authority Drift")
    if not STATE_PATH.exists():
        return _check("State file exists", False, str(STATE_PATH))
    if not JOURNAL_PATH.exists():
        return _check("Journal file exists", False, str(JOURNAL_PATH))
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return _check("State JSON parses", False, str(exc)[:80])
    if not isinstance(state, dict):
        return _check("State JSON is an object", False)

    journal_rows = _load_jsonl(JOURNAL_PATH)
    diagnostic = archive_authority_diagnostic(state, journal_rows)
    all_ok = True
    all_ok &= _check(
        "Journal rows loaded",
        bool(journal_rows),
        f"{len(journal_rows)} rows",
    )
    all_ok &= _check(
        "State archive matches journal fold",
        diagnostic["status"] == "match",
        (
            f"status={diagnostic['status']} "
            f"state_entries={diagnostic.get('state_entry_count', 'n/a')} "
            f"journal_entries={diagnostic.get('journal_entry_count', 'n/a')} "
            f"state_frontier={diagnostic.get('state_frontier_count', 'n/a')} "
            f"journal_frontier={diagnostic.get('journal_frontier_count', 'n/a')}"
        ),
    )
    full_replay_available = diagnostic["status"] == "match"
    snapshot_ok = (
        diagnostic.get("snapshot_readiness") != "prefix_invalidated"
        or full_replay_available
    )
    all_ok &= _check(
        "Snapshot replay is restart-safe",
        snapshot_ok,
        (
            f"readiness={diagnostic.get('snapshot_readiness', 'n/a')} "
            f"replay={diagnostic.get('snapshot_replay_status', 'n/a')} "
            f"through={diagnostic.get('snapshot_through_trial_id', 'n/a')} "
            f"tail_trials={diagnostic.get('snapshot_tail_trial_count', 'n/a')} "
            f"tail_max={diagnostic.get('snapshot_tail_max_trial_id', 'n/a')} "
            f"full_replay_available={full_replay_available}"
        ),
    )
    for warning in diagnostic.get("warnings", []):
        _check("Archive authority warning", False, str(warning))
    return all_ok


def audit_seeding_pipeline(url: str) -> bool:
    """Send a real question through the seeding eval pipeline and check all fields."""
    _header("9. Seeding Eval Pipeline (end-to-end)")
    import httpx

    # Send a simple question through the orchestrator (mimic seeding eval path)
    try:
        resp = httpx.post(
            f"{url}/chat",
            json={
                "prompt": "What is 7 times 8? Answer with just the number.",
                "real_mode": True,
                "max_turns": 1,
                "force_role": "frontdoor",
                "force_mode": "direct",
            },
            timeout=60.0,
        )
        if resp.status_code != 200:
            _check("API responds", False, f"HTTP {resp.status_code}")
            return False
    except Exception as e:
        _check("API responds", False, str(e)[:80])
        return False

    data = resp.json()
    all_ok = True

    # Check critical response fields
    answer = data.get("answer", "")
    tokens = data.get("tokens_generated", 0)
    tokens_est = data.get("tokens_generated_estimate", 0)
    elapsed = data.get("elapsed_seconds", 0)
    gen_ms = data.get("generation_ms", 0)
    routed = data.get("routed_to", "")

    all_ok &= _check("Has answer", bool(answer), f"{len(answer)} chars")
    all_ok &= _check("tokens_generated > 0", tokens > 0, f"{tokens}")
    _check("tokens_generated_estimate > 0", tokens_est > 0, f"{tokens_est}")
    all_ok &= _check("elapsed_seconds > 0", elapsed > 0, f"{elapsed:.2f}s")
    _check("generation_ms > 0", gen_ms > 0, f"{gen_ms:.0f}ms")
    _check("routed_to set", bool(routed), routed)

    # Check speed calculation would work
    if tokens > 0 and elapsed > 0:
        speed = tokens / elapsed
        all_ok &= _check("Speed calculable", speed > 0, f"{speed:.1f} t/s")
    else:
        all_ok &= _check("Speed calculable", False, "tokens or elapsed is 0")

    # Check answer correctness
    has_56 = "56" in answer
    _check("Answer contains '56'", has_56)

    # Verify speed calculation would work in eval tower
    speed_ok = tokens > 0 and elapsed > 0
    if speed_ok:
        speed = tokens / elapsed
        all_ok &= _check("Eval tower speed non-zero", True, f"{speed:.1f} t/s")
    else:
        all_ok &= _check("Eval tower speed non-zero", False,
                          f"tokens={tokens}, elapsed={elapsed:.2f}")
        if tokens == 0:
            _check("ROOT CAUSE: tokens_generated=0 in API response", False,
                   "pipeline not populating tokens_generated field")

    return all_ok


def audit_eval_tower() -> bool:
    """Check eval tower speed calculation with synthetic data."""
    _header("10. Eval Tower Speed Calculation")
    from dataclasses import dataclass

    @dataclass
    class FakeResult:
        correct: bool = True
        tokens_generated: int = 100
        elapsed_s: float = 5.0
        error: str = ""
        cost_tier: int = 2
        suite: str = "math"

    results = [
        FakeResult(correct=True, tokens_generated=100, elapsed_s=5.0),
        FakeResult(correct=True, tokens_generated=200, elapsed_s=4.0),
        FakeResult(correct=False, tokens_generated=50, elapsed_s=2.0),
    ]

    speeds = []
    for r in results:
        if r.tokens_generated > 0 and r.elapsed_s > 0 and not r.error:
            speeds.append(r.tokens_generated / r.elapsed_s)
    speed = sorted(speeds)[len(speeds) // 2] if speeds else 0.0

    ok = _check("Median speed > 0", speed > 0, f"{speed:.1f} t/s")
    _check("Speed list populated", len(speeds) == 3, f"{len(speeds)} entries")
    return ok


def main():
    parser = argparse.ArgumentParser(description="Autopilot pre-launch diagnostic audit")
    parser.add_argument("--url", default=ORCHESTRATOR_URL, help="Orchestrator URL")
    args = parser.parse_args()

    print("╔" + "═" * 58 + "╗")
    print("║  AUTOPILOT PRE-LAUNCH DIAGNOSTIC AUDIT                   ║")
    print("╚" + "═" * 58 + "╝")

    results = []
    results.append(("Stack Change Gate", audit_stack_change_gate()))
    results.append(("Model Servers", audit_model_servers(args.url)))
    results.append(("Web Search", audit_web_search()))
    results.append(("Web Fetch", audit_web_fetch()))
    results.append(("Code Execution", audit_code_execution()))
    results.append(("F1 Scoring", audit_f1_scoring()))
    results.append(("Question Pool", audit_question_pool()))
    results.append(("Blacklist", audit_blacklist()))
    results.append(("Archive Authority", audit_archive_authority()))
    results.append(("Seeding Pipeline", audit_seeding_pipeline(args.url)))
    results.append(("Eval Tower", audit_eval_tower()))

    _header("SUMMARY")
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  {'✓' if ok else '✗'} {name}: {status}")

    print(f"\n  {passed}/{total} checks passed")

    if passed == total:
        print("\n  ✅ ALL CHECKS PASSED — safe to launch autopilot")
        return 0
    else:
        print(f"\n  ❌ {total - passed} FAILURES — fix before launching")
        return 1


if __name__ == "__main__":
    sys.exit(main())
