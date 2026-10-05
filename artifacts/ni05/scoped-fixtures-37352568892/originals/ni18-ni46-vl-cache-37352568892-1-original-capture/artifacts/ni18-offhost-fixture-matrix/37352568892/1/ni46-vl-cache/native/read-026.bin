#!/usr/bin/env python3
"""Plan A9 pairwise expansion for failed independent holdout strata.

The pairwise ranker has signal on random group-disjoint splits but mixed
independent holdout evidence. This planner selects prompt-free source rows that
can add non-overlapping cross-action pairwise evidence for the weak strata
without training a model or changing runtime routing.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
from itertools import combinations
import json
from pathlib import Path
import sys
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.graph_router.action_space import load_live_canonical_actions  # noqa: E402
from scripts.graph_router.build_offline_reward_feature_manifest import (  # noqa: E402
    PRIVATE_FIELDS,
    _source_family_onehot,
)
from scripts.graph_router.build_offline_reward_oracle_rows import (  # noqa: E402
    _binary_reward,
    _load_records,
    _role_results,
)
from scripts.graph_router.build_offline_reward_pairwise_contract import (  # noqa: E402
    _group_key,
)
from scripts.graph_router.plan_offline_reward_verifier_expansion import (  # noqa: E402
    CANDIDATE_SCHEMA_VERSION,
    _canonical_action,
    _candidate_id,
    _existing_keys,
    _iter_input_files,
    _parse_csv,
)
from scripts.benchmark.seeding_types import DEFAULT_SUITES  # noqa: E402


SUMMARY_SCHEMA_VERSION = "offline_reward_pairwise_holdout_expansion_plan.v1"
COLLECTION_MANIFEST_SCHEMA_VERSION = "offline_reward_pairwise_collection_window.v1"
COLLECTION_TIMESTAMP_PLACEHOLDER = "<YYYYMMDDTHHMMSSZ>"
DEFAULT_COLLECTION_WORKDIR = Path(__file__).resolve().parents[2]
DEFAULT_COLLECTION_MAX_TOKENS = 1024
DEFAULT_RESULTS_ROOT = Path("/mnt/raid0/llm/epyc-inference-research/benchmarks/results")
REFERENCE_BACKED_PROMPTS_ROOT = Path("/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts")
DEFAULT_REPORT_DIR = (
    PROJECT_ROOT
    / "orchestration/reports/offline_reward_oracle_token_coverage_final_labels_20260621"
)
DEFAULT_EXISTING_MANIFEST = (
    DEFAULT_REPORT_DIR / "offline_reward_feature_manifest_with_seeding_eval_expansion.jsonl"
)
DEFAULT_EXISTING_PAIRWISE = (
    DEFAULT_REPORT_DIR / "offline_reward_pairwise_preference_contract_score_ordered.jsonl"
)
DEFAULT_TARGET_SOURCE_FAMILIES = "seeding_eval"
DEFAULT_TARGET_SUITES = "thinking"
DEFAULT_PRIORITY_STRATA = {
    ("source_family", "orchestrator_live_seed"): (0, "independent_holdout_source_family_blocker"),
    ("source_family", "seeding_eval"): (0, "independent_holdout_source_family_blocker"),
    ("suite", "general"): (1, "independent_holdout_suite_blocker"),
}
REFERENCE_BACKED_COLLECTION_SOURCES = {
    # The live IFEval adapter and current debug YAML are programmatic and emit
    # expected="", but the legacy v1 prompt bundle preserves text references
    # that the A9 reference-token-coverage oracle can score.
    "instruction_precision": REFERENCE_BACKED_PROMPTS_ROOT / "v1",
}


class PairwiseHoldoutExpansionError(ValueError):
    """Raised when a pairwise holdout expansion plan cannot be built."""


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            value = json.loads(stripped)
            if not isinstance(value, dict):
                raise PairwiseHoldoutExpansionError(f"{path}:{line_number}: expected object")
            rows.append(value)
    return rows


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _record_group_key(
    *,
    source_path: Path,
    offset: int,
    question_id: str,
    prompt_sha256: str,
    expected_sha256: str,
) -> str:
    return "|".join(
        [
            str(source_path),
            str(offset),
            question_id,
            prompt_sha256,
            expected_sha256,
        ]
    )


def _existing_manifest_groups(
    path: Path | None,
    *,
    canonical_actions: set[str],
) -> tuple[dict[str, set[str]], Counter, Counter]:
    if path is None or not path.exists():
        return {}, Counter(), Counter()
    groups: dict[str, set[str]] = defaultdict(set)
    source_family_counts: Counter = Counter()
    suite_counts: Counter = Counter()
    for row in _load_jsonl(path):
        group_key = _group_key(row)
        role_key = str(row.get("role_key") or "")
        canonical = _canonical_action(role_key, canonical_actions) if role_key else None
        if canonical:
            groups[group_key].add(canonical)
        context = row.get("feature_context")
        source_family = None
        if isinstance(context, dict):
            source_family = context.get("source_family")
        if isinstance(source_family, str) and source_family:
            source_family_counts[source_family] += 1
        suite = str(row.get("suite") or "")
        if suite:
            suite_counts[suite] += 1
    return groups, source_family_counts, suite_counts


def _existing_pairwise_groups(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    groups: set[str] = set()
    for row in _load_jsonl(path):
        group_key = str(row.get("group_key") or "")
        if group_key:
            groups.add(group_key)
    return groups


def _canonical_action_pair(actions: Iterable[str]) -> str:
    values = sorted(str(action) for action in actions)
    if len(values) != 2:
        raise PairwiseHoldoutExpansionError("action pair must contain exactly two actions")
    return f"{values[0]}>{values[1]}"


def _load_collection_targets(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    targets = payload.get("collection_targets")
    if not isinstance(targets, list):
        raise PairwiseHoldoutExpansionError(f"{path}: missing collection_targets list")
    out: list[dict[str, Any]] = []
    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            raise PairwiseHoldoutExpansionError(f"{path}: collection_targets[{index}] must be object")
        field = str(target.get("stratum_field") or "")
        value = str(target.get("stratum_value") or "")
        action_pair = str(target.get("action_pair") or "")
        if field not in {"source_family", "suite"}:
            raise PairwiseHoldoutExpansionError(
                f"{path}: collection_targets[{index}] has unsupported stratum_field {field!r}"
            )
        if not value:
            raise PairwiseHoldoutExpansionError(
                f"{path}: collection_targets[{index}] missing stratum_value"
            )
        parts = [part for part in action_pair.split(">") if part]
        if len(parts) != 2:
            raise PairwiseHoldoutExpansionError(
                f"{path}: collection_targets[{index}] invalid action_pair {action_pair!r}"
            )
        out.append(
            {
                "stratum_field": field,
                "stratum_value": value,
                "action_pair": _canonical_action_pair(parts),
                "needs_direction": target.get("needs_direction") or [],
                "prefer_hi": target.get("prefer_hi"),
                "prefer_lo": target.get("prefer_lo"),
                "current_rows": target.get("current_rows"),
                "current_direction_balance": target.get("current_direction_balance"),
                "suggested_min_rows": target.get("suggested_min_rows"),
            }
        )
    return out


def _preferred_actions_for_target(target: dict[str, Any]) -> list[str]:
    action_a, action_b = str(target["action_pair"]).split(">")
    needs = [str(value) for value in target.get("needs_direction") or []]
    explicit: set[str] = set()
    for action in (action_a, action_b):
        if any(f"prefer {action}" in need for need in needs):
            explicit.add(action)
    if explicit:
        return sorted(explicit)
    if any("balance both directions" in need for need in needs):
        try:
            prefer_hi = int(target.get("prefer_hi") or 0)
            prefer_lo = int(target.get("prefer_lo") or 0)
        except (TypeError, ValueError):
            return [action_a, action_b]
        if prefer_lo < prefer_hi:
            return [action_a]
        if prefer_hi < prefer_lo:
            return [action_b]
        return [action_a, action_b]
    if any("prefer other-side" in need for need in needs):
        try:
            prefer_hi = int(target.get("prefer_hi") or 0)
            prefer_lo = int(target.get("prefer_lo") or 0)
        except (TypeError, ValueError):
            return [action_a, action_b]
        return [action_a if prefer_hi <= prefer_lo else action_b]
    return []


def _target_requirement_key(target: dict[str, Any]) -> str:
    return (
        f"{target['stratum_field']}:{target['stratum_value']}:"
        f"{target['action_pair']}"
    )


def _collection_target_lookup(
    collection_targets: list[dict[str, Any]],
) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    lookup: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for target in collection_targets:
        lookup[
            (
                str(target["stratum_field"]),
                str(target["stratum_value"]),
                str(target["action_pair"]),
            )
        ].append(target)
    return lookup


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _binary_reward_contrast_targets(
    candidates: list[dict[str, Any]],
    collection_targets_by_key: dict[tuple[str, str, str], list[dict[str, Any]]],
    *,
    source_family: str,
    suite: str,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    if not collection_targets_by_key:
        return matches

    for left, right in combinations(candidates, 2):
        left_action = str(left.get("canonical_action") or "")
        right_action = str(right.get("canonical_action") or "")
        if not left_action or not right_action or left_action == right_action:
            continue
        left_value = _float_or_none(left.get("binary_reward"))
        right_value = _float_or_none(right.get("binary_reward"))
        if left_value is None or right_value is None or left_value == right_value:
            continue
        preferred_action = left_action if left_value > right_value else right_action
        rejected_action = right_action if left_value > right_value else left_action
        pair = _canonical_action_pair([left_action, right_action])

        for field, value in (("source_family", source_family), ("suite", suite)):
            for target in collection_targets_by_key.get((field, value, pair), []):
                preferred_actions = _preferred_actions_for_target(target)
                if preferred_actions and preferred_action not in preferred_actions:
                    continue
                matches.append(
                    {
                        "target": _target_requirement_key(target),
                        "stratum_field": field,
                        "stratum_value": value,
                        "action_pair": pair,
                        "preferred_action": preferred_action,
                        "rejected_action": rejected_action,
                        "contrast_metric": "source_binary_reward",
                    }
                )
    return matches


def _collection_requirements(
    collection_targets: list[dict[str, Any]],
    contrast_collection_target_counts: Counter,
    *,
    presence_collection_target_counts: Counter | None = None,
    unavailable_targets: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    presence_collection_target_counts = presence_collection_target_counts or Counter()
    unavailable_targets = unavailable_targets or {}
    requirements: list[dict[str, Any]] = []
    for target in collection_targets:
        key = _target_requirement_key(target)
        suggested_min = target.get("suggested_min_rows")
        current_rows = target.get("current_rows")
        try:
            suggested_min_int = int(suggested_min)
        except (TypeError, ValueError):
            suggested_min_int = 20
        matched = int(contrast_collection_target_counts.get(key, 0))
        presence_matched = int(presence_collection_target_counts.get(key, 0))
        unavailable_reason = unavailable_targets.get(key)
        remaining = 0 if unavailable_reason else max(0, suggested_min_int - matched)
        priority, priority_reason = DEFAULT_PRIORITY_STRATA.get(
            (str(target["stratum_field"]), str(target["stratum_value"])),
            (2, "direction_balance_cleanup"),
        )
        status = "matched_contrast_candidates" if remaining == 0 else "needs_new_source_records"
        if unavailable_reason:
            status = "unavailable_with_current_oracle"
        requirements.append(
            {
                "target": key,
                "status": status,
                "stratum_field": target["stratum_field"],
                "stratum_value": target["stratum_value"],
                "action_pair": target["action_pair"],
                "actions_to_evaluate_on_same_source_record": str(target["action_pair"]).split(">"),
                "target_preferred_actions": _preferred_actions_for_target(target),
                "needs_direction": target.get("needs_direction") or [],
                "current_rows": current_rows,
                "current_direction_balance": target.get("current_direction_balance"),
                "matched_candidate_groups": matched,
                "presence_candidate_groups": presence_matched,
                "matched_candidate_group_metric": "source_binary_reward_directional_contrast",
                "suggested_min_rows": suggested_min,
                "suggested_min_new_source_records": remaining,
                "collection_priority": priority,
                "collection_priority_reason": priority_reason,
                "source_record_shape": (
                    "one prompt/reference evaluated by every action in action_pair "
                    "with role_results, rewards, suite, prompt, and expected fields"
                ),
                "runtime_gate_change_allowed": False,
                **(
                    {"collection_unavailable_reason": unavailable_reason}
                    if unavailable_reason
                    else {}
                ),
            }
        )
    return requirements


def _slug(value: str) -> str:
    out = []
    for char in value.lower():
        if char.isalnum():
            out.append(char)
        else:
            out.append("_")
    compact = "_".join(part for part in "".join(out).split("_") if part)
    return compact or "target"


def _collection_sample_size_for_suite_arg(
    requested_records: int,
    *,
    suite_argument: str,
) -> tuple[int, int]:
    """Return CLI sample-size and estimated records for a collection target.

    seed_specialist_routing.py interprets --sample-size as questions per suite.
    Source-family targets use --suites all, so passing the requested target
    rows directly would multiply the clean-window run across every default
    suite. Keep the target record budget approximately stable instead.
    """
    requested = max(1, requested_records)
    if suite_argument != "all":
        return requested, requested
    suite_count = max(1, len(DEFAULT_SUITES))
    cli_sample_size = max(1, (requested + suite_count - 1) // suite_count)
    return cli_sample_size, cli_sample_size * suite_count


def _reference_backed_prompt_count(suite: str, source_dir: Path) -> int | None:
    try:
        import yaml
    except ImportError:
        return None

    path = source_dir / f"{suite}.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None

    questions = data.get("questions")
    if isinstance(questions, list):
        return sum(
            1 for item in questions
            if isinstance(item, dict) and item.get("prompt")
        )
    prompts = data.get("prompts")
    if isinstance(prompts, dict):
        return sum(
            1 for item in prompts.values()
            if isinstance(item, dict) and item.get("prompt")
        )
    return None


def _ordered_unique(items: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = str(item)
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _merge_reference_backed_requirements(
    requirements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    suite_index: dict[str, dict[str, Any]] = {}
    for requirement in requirements:
        stratum_field = str(requirement.get("stratum_field") or "")
        stratum_value = str(requirement.get("stratum_value") or "")
        if (
            stratum_field != "suite"
            or stratum_value not in REFERENCE_BACKED_COLLECTION_SOURCES
        ):
            merged.append(requirement)
            continue

        existing = suite_index.get(stratum_value)
        if existing is None:
            existing = dict(requirement)
            existing["merged_collection_targets"] = [str(requirement.get("target") or "")]
            existing["merged_action_pairs"] = [str(requirement.get("action_pair") or "")]
            suite_index[stratum_value] = existing
            merged.append(existing)
            continue

        existing["merged_collection_targets"].append(str(requirement.get("target") or ""))
        existing["merged_action_pairs"].append(str(requirement.get("action_pair") or ""))
        existing["actions_to_evaluate_on_same_source_record"] = _ordered_unique(
            [
                *existing.get("actions_to_evaluate_on_same_source_record", []),
                *requirement.get("actions_to_evaluate_on_same_source_record", []),
            ]
        )
        existing["target_preferred_actions"] = _ordered_unique(
            [
                *existing.get("target_preferred_actions", []),
                *requirement.get("target_preferred_actions", []),
            ]
        )
        existing["suggested_min_new_source_records"] = max(
            int(existing.get("suggested_min_new_source_records") or 0),
            int(requirement.get("suggested_min_new_source_records") or 0),
        )
        existing["target"] = "+".join(existing["merged_collection_targets"])
        existing["action_pair"] = "+".join(existing["merged_action_pairs"])
    return merged


def _collection_batches(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    batches: list[dict[str, Any]] = []
    ordered_requirements = sorted(
        _merge_reference_backed_requirements(requirements),
        key=lambda requirement: (
            int(requirement.get("collection_priority") or 0),
            -int(requirement.get("suggested_min_new_source_records") or 0),
            str(requirement.get("target") or ""),
        ),
    )
    for requirement in ordered_requirements:
        if int(requirement.get("suggested_min_new_source_records") or 0) <= 0:
            continue
        actions = list(requirement["actions_to_evaluate_on_same_source_record"])
        roles = " ".join(actions)
        requested_records = int(requirement.get("suggested_min_new_source_records") or 20)
        target = str(requirement["target"])
        target_slug = _slug(target)
        stratum_field = str(requirement["stratum_field"])
        stratum_value = str(requirement["stratum_value"])
        suite = stratum_value if stratum_field == "suite" else "all"
        source_override = (
            REFERENCE_BACKED_COLLECTION_SOURCES.get(suite)
            if stratum_field == "suite"
            else None
        )
        sample_size, estimated_records = _collection_sample_size_for_suite_arg(
            requested_records,
            suite_argument=suite,
        )
        reference_source_prompt_count = None
        if source_override is not None:
            reference_source_prompt_count = _reference_backed_prompt_count(
                suite,
                source_override,
            )
            if reference_source_prompt_count is not None:
                sample_size = min(sample_size, max(1, reference_source_prompt_count))
                estimated_records = min(estimated_records, reference_source_prompt_count)
        if stratum_field == "source_family" and stratum_value == "orchestrator_live_seed":
            output = (
                "/mnt/raid0/llm/epyc-inference-research/benchmarks/results/"
                f"orchestrator/seeding_live_a9_{target_slug}_"
                f"{COLLECTION_TIMESTAMP_PLACEHOLDER}.json"
            )
            expected_source_family = "orchestrator_live_seed"
        else:
            output = (
                "/mnt/raid0/llm/epyc-inference-research/benchmarks/results/"
                f"eval/seeding_a9_{target_slug}_{COLLECTION_TIMESTAMP_PLACEHOLDER}.json"
            )
            expected_source_family = "seeding_eval"
        source_args = ""
        if source_override is not None:
            source_args = (
                f"--question-source yaml --debug-prompts-dir {source_override} "
            )
        command = (
            "uv run python scripts/benchmark/seed_specialist_routing.py "
            f"--suites {suite} --roles {roles} --modes direct "
            f"--sample-size {sample_size} {source_args}"
            f"--max-tokens {DEFAULT_COLLECTION_MAX_TOKENS} "
            f"--strict-modes --dry-run --output {output}"
        )
        batches.append(
            {
                "target": target,
                "targets": list(requirement.get("merged_collection_targets") or [target]),
                "expected_source_family": expected_source_family,
                "suite_argument": suite,
                "roles_argument": actions,
                "modes_argument": ["direct"],
                "sample_size": sample_size,
                "max_tokens": DEFAULT_COLLECTION_MAX_TOKENS,
                "strict_modes": True,
                "question_source": "yaml" if source_override is not None else "auto",
                **(
                    {"debug_prompts_dir": str(source_override)}
                    if source_override is not None
                    else {}
                ),
                "requested_new_source_records": requested_records,
                "estimated_new_source_records": estimated_records,
                **(
                    {"reference_source_prompt_count": reference_source_prompt_count}
                    if reference_source_prompt_count is not None
                    else {}
                ),
                "sample_size_semantics": (
                    "seed_specialist_routing.py interprets --sample-size as "
                    "questions per suite; source-family targets with --suites "
                    "all are downscaled to approximate the requested total."
                ),
                "collection_priority": int(requirement.get("collection_priority") or 0),
                "collection_priority_reason": str(
                    requirement.get("collection_priority_reason") or "unknown"
                ),
                "durable_source_path": output,
                "checkpoint_note": (
                    "seed_specialist_routing.py also writes a seeding_*.jsonl "
                    "checkpoint under benchmarks/results/eval; use the JSON path "
                    "above when the target explicitly requires orchestrator_live_seed"
                ),
                "dry_run_semantics": (
                    "--dry-run still performs scoring/evaluation; it only prevents "
                    "reward injection into runtime memory."
                ),
                "command": command,
                "can_run_during_active_autopilot": False,
                "reason": (
                    "Consumes live model slots and should be run in a coordinated "
                    "measurement window so A9 evidence is not mixed with W6/T2 accrual."
                ),
            }
        )
    return batches


def _validate_collection_timestamp(timestamp: str) -> None:
    if timestamp == COLLECTION_TIMESTAMP_PLACEHOLDER:
        return
    if (
        len(timestamp) == 16
        and timestamp[8] == "T"
        and timestamp.endswith("Z")
        and timestamp[:8].isdigit()
        and timestamp[9:15].isdigit()
    ):
        return
    raise PairwiseHoldoutExpansionError(
        "collection timestamp must be <YYYYMMDDTHHMMSSZ> or UTC form YYYYMMDDTHHMMSSZ"
    )


def _materialize_batch(batch: dict[str, Any], *, timestamp: str) -> dict[str, Any]:
    _validate_collection_timestamp(timestamp)
    durable_source_path = str(batch["durable_source_path"])
    command = str(batch["command"])
    materialized_path = durable_source_path.replace(COLLECTION_TIMESTAMP_PLACEHOLDER, timestamp)
    materialized_command = command.replace(COLLECTION_TIMESTAMP_PLACEHOLDER, timestamp)
    out = dict(batch)
    out["collection_timestamp"] = timestamp
    out["command_workdir"] = str(DEFAULT_COLLECTION_WORKDIR)
    out["durable_source_path_template"] = durable_source_path
    out["command_template"] = command
    out["durable_source_path"] = materialized_path
    out["command"] = materialized_command
    return out


def build_collection_manifest(
    summary: dict[str, Any],
    *,
    timestamp: str = COLLECTION_TIMESTAMP_PLACEHOLDER,
) -> dict[str, Any]:
    _validate_collection_timestamp(timestamp)
    batches = [
        _materialize_batch(batch, timestamp=timestamp)
        for batch in summary.get("collection_batches", [])
    ]
    return {
        "schema_version": COLLECTION_MANIFEST_SCHEMA_VERSION,
        "source_plan_schema_version": summary.get("schema_version"),
        "source_plan_decision": summary.get("decision"),
        "collection_timestamp": timestamp,
        "command_workdir": str(DEFAULT_COLLECTION_WORKDIR),
        "requires_active_autopilot_absent": True,
        "autopilot_guard": {
            "process_pattern": "scripts/autopilot/autopilot.py start",
            "refusal_exit_code": 75,
            "reason": (
                "A9 source acquisition consumes live model slots and must not mix "
                "with active W6/T2 AutoPilot accrual."
            ),
        },
        "batch_count": len(batches),
        "batches": batches,
        "post_collection_pipeline": (
            summary.get("collection_guidance", {}).get("post_collection_pipeline", [])
        ),
    }


def write_collection_script(path: Path, manifest: dict[str, Any]) -> None:
    timestamp = str(manifest["collection_timestamp"])
    if timestamp == COLLECTION_TIMESTAMP_PLACEHOLDER:
        timestamp_line = 'RUN_TS="${A9_COLLECTION_TIMESTAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"'
    else:
        timestamp_line = f'RUN_TS="{timestamp}"'
    lines = [
        "#!/bin/bash",
        "set -euo pipefail",
        "",
        timestamp_line,
        'if [[ ! "$RUN_TS" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]; then',
        '  echo "invalid A9 collection timestamp: $RUN_TS" >&2',
        "  exit 64",
        "fi",
        "if pgrep -af 'scripts/autopilot/autopilot.py start' >/dev/null; then",
        "  echo 'refusing A9 collection while AutoPilot is active' >&2",
        "  exit 75",
        "fi",
        f"cd {DEFAULT_COLLECTION_WORKDIR}",
        "",
    ]
    for index, batch in enumerate(manifest["batches"], start=1):
        target = str(batch["target"])
        output_path = str(batch["durable_source_path_template"]).replace(
            COLLECTION_TIMESTAMP_PLACEHOLDER,
            "${RUN_TS}",
        )
        command = str(batch["command_template"]).replace(
            COLLECTION_TIMESTAMP_PLACEHOLDER,
            "${RUN_TS}",
        )
        lines.extend(
            [
                f"echo 'A9 collection batch {index}/{manifest['batch_count']}: {target}'",
                f'mkdir -p "$(dirname "{output_path}")"',
                command,
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    path.chmod(0o755)


def _post_collection_commands() -> list[str]:
    report_dir = str(DEFAULT_REPORT_DIR)
    return [
        (
            "uv run python scripts/graph_router/plan_offline_reward_pairwise_holdout_expansion.py "
            f"--input /mnt/raid0/llm/epyc-inference-research/benchmarks/results "
            f"--existing-manifest {report_dir}/offline_reward_feature_manifest_with_pairwise_audit_target_expansions.jsonl "
            f"--existing-pairwise-jsonl {report_dir}/offline_reward_pairwise_preference_contract_score_ordered_audit_target_expanded.jsonl "
            f"--collection-targets-json {report_dir}/offline_reward_pairwise_expanded_gap_direction_audit.json "
            f"--candidates-jsonl {report_dir}/offline_reward_pairwise_expanded_gap_candidates.jsonl "
            f"--summary-json {report_dir}/offline_reward_pairwise_expanded_gap_plan_summary.json "
            f"--summary-md {report_dir}/offline_reward_pairwise_expanded_gap_plan_summary.md "
            "--target-source-families '' --target-suites ''"
        ),
        (
            "uv run python scripts/graph_router/build_offline_reward_oracle_rows.py "
            "--input <new_collection_json_or_jsonl> "
            f"--candidate-manifest-jsonl {report_dir}/offline_reward_pairwise_expanded_gap_candidates.jsonl "
            f"--output-jsonl {report_dir}/offline_reward_pairwise_expanded_gap_oracle_rows.jsonl "
            f"--summary-json {report_dir}/offline_reward_pairwise_expanded_gap_rows_summary.json"
        ),
        (
            "uv run python scripts/graph_router/score_offline_reward_oracle_token_coverage.py "
            f"--input-jsonl {report_dir}/offline_reward_pairwise_expanded_gap_oracle_rows.jsonl "
            f"--output-jsonl {report_dir}/offline_reward_pairwise_expanded_gap_scored_rows.jsonl "
            f"--summary-json {report_dir}/offline_reward_pairwise_expanded_gap_score_summary.json "
            f"--summary-md {report_dir}/offline_reward_pairwise_expanded_gap_score_summary.md"
        ),
        (
            "uv run python scripts/graph_router/export_offline_reward_expansion_labels.py "
            f"--manifest-json {report_dir}/adoption_manifest.json "
            f"--scored-rows-jsonl {report_dir}/offline_reward_pairwise_expanded_gap_scored_rows.jsonl "
            f"--candidates-jsonl {report_dir}/offline_reward_pairwise_expanded_gap_candidates.jsonl "
            f"--labels-jsonl {report_dir}/offline_reward_pairwise_expanded_gap_labels.jsonl "
            f"--summary-json {report_dir}/offline_reward_pairwise_expanded_gap_labels_summary.json "
            f"--summary-md {report_dir}/offline_reward_pairwise_expanded_gap_labels_summary.md"
        ),
        (
            "uv run python scripts/graph_router/build_offline_reward_feature_manifest.py "
            f"--labels-jsonl {report_dir}/offline_reward_pairwise_expanded_gap_labels.jsonl "
            f"--manifest-jsonl {report_dir}/offline_reward_feature_manifest_pairwise_expanded_gap.jsonl "
            f"--summary-json {report_dir}/offline_reward_feature_manifest_pairwise_expanded_gap_summary.json "
            f"--summary-md {report_dir}/offline_reward_feature_manifest_pairwise_expanded_gap_summary.md"
        ),
        (
            "uv run python scripts/graph_router/build_offline_reward_pairwise_contract.py "
            f"--manifest-jsonl {report_dir}/offline_reward_feature_manifest_pairwise_expanded_gap.jsonl "
            f"--output-jsonl {report_dir}/offline_reward_pairwise_preference_contract_candidate_only_expanded_gap.jsonl "
            f"--summary-json {report_dir}/offline_reward_pairwise_preference_contract_candidate_only_expanded_gap_summary.json "
            f"--summary-md {report_dir}/offline_reward_pairwise_preference_contract_candidate_only_expanded_gap_summary.md "
            "--artifact-scope candidate_only"
        ),
        (
            "uv run python scripts/graph_router/evaluate_offline_reward_pairwise_ranker.py "
            f"--pairwise-jsonl {report_dir}/offline_reward_pairwise_preference_contract_candidate_only_expanded_gap.jsonl "
            f"--summary-json {report_dir}/offline_reward_pairwise_ranker_candidate_only_expanded_gap_summary.json "
            f"--summary-md {report_dir}/offline_reward_pairwise_ranker_candidate_only_expanded_gap_summary.md"
        ),
    ]


def _pair_keys(actions: set[str]) -> set[str]:
    return {_canonical_action_pair(pair) for pair in combinations(sorted(actions), 2)}


def _candidate_from_role(
    *,
    path: Path,
    offset: int,
    record: dict[str, Any],
    role_key: str,
    role_result: dict[str, Any],
    canonical_action: str,
    source_family: str,
    prompt: str,
    reference: str,
) -> dict[str, Any]:
    rewards = record.get("rewards") if isinstance(record.get("rewards"), dict) else {}
    reward_value = rewards.get(role_key)
    record_index = offset + 1
    response = str(role_result.get("answer") or role_result.get("response") or "")
    candidate = {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "candidate_id": _candidate_id(path, record_index, role_key),
        "source_path": str(path),
        "source_record_index": record_index,
        "source_record_offset": offset,
        "source_record_index_base": "one_based",
        "question_id": str(record.get("question_id") or record.get("qid") or ""),
        "suite": str(record.get("suite") or "unknown"),
        "role_key": role_key,
        "canonical_action": canonical_action,
        "source_family": source_family,
        "source_passed": role_result.get("passed"),
        "source_error_present": bool(role_result.get("error")),
        "source_elapsed_seconds": role_result.get("elapsed_seconds"),
        "binary_reward": _binary_reward(role_result, reward_value),
        "prompt_sha256": _hash_text(prompt),
        "reference_sha256": _hash_text(reference),
        "expected_sha256": _hash_text(reference),
        "response_sha256": _hash_text(response),
        "prompt_chars": len(prompt),
        "reference_chars": len(reference),
        "response_chars": len(response),
        "scoring_next_step": "build_offline_reward_oracle_rows -> score_offline_reward_oracle_token_coverage",
    }
    if reward_value is not None:
        try:
            candidate["q_reward"] = float(reward_value)
        except (TypeError, ValueError):
            pass
    return candidate


def _scan_candidate_groups(
    paths: Iterable[Path],
    *,
    canonical_actions: set[str],
    target_actions: set[str],
    target_source_families: set[str],
    target_suites: set[str],
    target_match_mode: str,
    existing_keys: set[tuple[str, int, str]],
) -> tuple[dict[str, list[dict[str, Any]]], Counter]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    stats: Counter = Counter()
    for path in _iter_input_files(paths):
        stats["files_scanned"] += 1
        source_family, _ = _source_family_onehot(path)
        if (
            target_match_mode == "all"
            and target_source_families
            and source_family not in target_source_families
        ):
            stats["skipped_non_target_source_family_file"] += 1
            continue
        try:
            records = list(_load_records(path))
        except Exception:
            stats["skipped_unreadable_file"] += 1
            continue
        for offset, record in enumerate(records):
            if not isinstance(record, dict):
                stats["skipped_non_object_record"] += 1
                continue
            suite = str(record.get("suite") or "unknown")
            if target_match_mode == "all":
                source_family_match = (
                    not target_source_families or source_family in target_source_families
                )
                suite_match = not target_suites or suite in target_suites
                target_match = source_family_match and suite_match
            else:
                source_family_match = (
                    bool(target_source_families) and source_family in target_source_families
                )
                suite_match = bool(target_suites) and suite in target_suites
                target_match = source_family_match or suite_match
            if not target_match:
                stats["skipped_non_target_suite_record"] += 1
                continue
            prompt = str(record.get("prompt") or "")
            reference = str(record.get("expected") or record.get("reference") or "")
            if not prompt:
                stats["skipped_missing_prompt"] += 1
                continue
            if not reference:
                stats["skipped_missing_reference"] += 1
                stats[f"skipped_missing_reference_suite:{suite}"] += 1
                stats[f"skipped_missing_reference_source_family:{source_family}"] += 1
                continue
            stats[f"reference_available_suite:{suite}"] += 1
            stats[f"reference_available_source_family:{source_family}"] += 1
            role_results = _role_results(record)
            if not role_results:
                stats["skipped_missing_role_results"] += 1
                continue
            group_key = _record_group_key(
                source_path=path,
                offset=offset,
                question_id=str(record.get("question_id") or record.get("qid") or ""),
                prompt_sha256=_hash_text(prompt),
                expected_sha256=_hash_text(reference),
            )
            for role_key, role_result in role_results.items():
                raw_role = str(role_key)
                if (str(path), offset, raw_role) in existing_keys:
                    stats["skipped_existing_row"] += 1
                    continue
                if not isinstance(role_result, dict):
                    stats["skipped_bad_role_result"] += 1
                    continue
                response = str(role_result.get("answer") or role_result.get("response") or "")
                if not response:
                    stats["skipped_missing_response"] += 1
                    continue
                canonical = _canonical_action(raw_role, canonical_actions)
                if canonical is None:
                    stats["skipped_unmapped_role"] += 1
                    continue
                if target_actions and canonical not in target_actions:
                    stats["skipped_non_target_action"] += 1
                    continue
                groups[group_key].append(
                    _candidate_from_role(
                        path=path,
                        offset=offset,
                        record=record,
                        role_key=raw_role,
                        role_result=role_result,
                        canonical_action=canonical,
                        source_family=source_family,
                        prompt=prompt,
                        reference=reference,
                    )
                )
                stats["candidate_rows"] += 1
    return groups, stats


def _assert_prompt_free(rows: Iterable[dict[str, Any]]) -> None:
    for row_number, row in enumerate(rows, start=1):
        present = sorted(PRIVATE_FIELDS & set(row))
        if present:
            raise PairwiseHoldoutExpansionError(
                f"candidate row {row_number}: private fields present: {', '.join(present)}"
            )


def build_plan(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    canonical_actions = set(load_live_canonical_actions())
    target_actions = set(_parse_csv(args.target_actions))
    unknown_actions = sorted(target_actions - canonical_actions)
    if unknown_actions:
        raise PairwiseHoldoutExpansionError(
            f"unknown target action(s): {', '.join(unknown_actions)}"
        )
    target_source_families = set(_parse_csv(args.target_source_families))
    target_suites = set(_parse_csv(args.target_suites))
    collection_targets = _load_collection_targets(args.collection_targets_json)
    collection_target_pairs: dict[tuple[str, str], set[str]] = defaultdict(set)
    collection_targets_by_key = _collection_target_lookup(collection_targets)
    for target in collection_targets:
        key = (str(target["stratum_field"]), str(target["stratum_value"]))
        collection_target_pairs[key].add(str(target["action_pair"]))
        if target["stratum_field"] == "source_family":
            target_source_families.add(str(target["stratum_value"]))
        elif target["stratum_field"] == "suite":
            target_suites.add(str(target["stratum_value"]))
    if args.target_match_mode not in {"any", "all"}:
        raise PairwiseHoldoutExpansionError("target_match_mode must be 'any' or 'all'")
    input_paths = args.input or [DEFAULT_RESULTS_ROOT]
    existing_keys = _existing_keys(args.existing_manifest)
    manifest_groups, manifest_source_family_counts, manifest_suite_counts = (
        _existing_manifest_groups(args.existing_manifest, canonical_actions=canonical_actions)
    )
    pairwise_groups = _existing_pairwise_groups(args.existing_pairwise_jsonl)
    candidate_groups, stats = _scan_candidate_groups(
        input_paths,
        canonical_actions=canonical_actions,
        target_actions=target_actions,
        target_source_families=target_source_families,
        target_suites=target_suites,
        target_match_mode=args.target_match_mode,
        existing_keys=existing_keys,
    )

    selected_groups: list[dict[str, Any]] = []
    selected_candidates: list[dict[str, Any]] = []
    skipped_pairwise_overlap = 0
    skipped_no_cross_action = 0
    skipped_no_collection_target_pair = 0
    for group_key in sorted(candidate_groups):
        candidates = sorted(
            candidate_groups[group_key],
            key=lambda row: (str(row["canonical_action"]), str(row["role_key"])),
        )
        if args.require_non_overlapping_pairwise_groups and group_key in pairwise_groups:
            skipped_pairwise_overlap += 1
            continue
        candidate_actions = {str(row["canonical_action"]) for row in candidates}
        existing_actions = manifest_groups.get(group_key, set())
        potential_actions = set(existing_actions) | candidate_actions
        if len(potential_actions) < 2:
            skipped_no_cross_action += 1
            continue
        group_pair_keys = _pair_keys(potential_actions)
        source_family = str(candidates[0]["source_family"])
        suite = str(candidates[0]["suite"])
        matched_collection_targets: list[dict[str, Any]] = []
        if collection_targets:
            for field, value in (("source_family", source_family), ("suite", suite)):
                matched_pairs = sorted(group_pair_keys & collection_target_pairs.get((field, value), set()))
                for pair in matched_pairs:
                    matched_collection_targets.append(
                        {
                            "stratum_field": field,
                            "stratum_value": value,
                            "action_pair": pair,
                        }
                    )
            if not matched_collection_targets:
                skipped_no_collection_target_pair += 1
                continue
        binary_reward_contrast_targets = _binary_reward_contrast_targets(
            candidates,
            collection_targets_by_key,
            source_family=source_family,
            suite=suite,
        )
        selected_groups.append(
            {
                "group_key": group_key,
                "candidate_rows": len(candidates),
                "candidate_actions": sorted(candidate_actions),
                "existing_manifest_actions": sorted(existing_actions),
                "potential_actions": sorted(potential_actions),
                "potential_action_pairs": sorted(group_pair_keys),
                "matched_collection_targets": matched_collection_targets,
                "binary_reward_contrast_collection_targets": binary_reward_contrast_targets,
                "source_family": source_family,
                "suite": suite,
                "source_path": str(candidates[0]["source_path"]),
                "source_record_offset": int(candidates[0]["source_record_offset"]),
            }
        )
        selected_candidates.extend(candidates)
        if args.max_groups is not None and len(selected_groups) >= args.max_groups:
            break
        if args.max_candidate_rows is not None and len(selected_candidates) >= args.max_candidate_rows:
            selected_candidates = selected_candidates[: args.max_candidate_rows]
            break

    _assert_prompt_free(selected_candidates)
    source_family_counts = Counter(str(row["source_family"]) for row in selected_candidates)
    suite_counts = Counter(str(row["suite"]) for row in selected_candidates)
    action_counts = Counter(str(row["canonical_action"]) for row in selected_candidates)
    group_source_family_counts = Counter(str(row["source_family"]) for row in selected_groups)
    group_suite_counts = Counter(str(row["suite"]) for row in selected_groups)
    presence_collection_target_counts = Counter(
        f"{target['stratum_field']}:{target['stratum_value']}:{target['action_pair']}"
        for group in selected_groups
        for target in group["matched_collection_targets"]
    )
    contrast_collection_target_counts = Counter(
        str(target["target"])
        for group in selected_groups
        for target in group["binary_reward_contrast_collection_targets"]
    )
    expected_collection_target_keys = sorted(
        f"{target['stratum_field']}:{target['stratum_value']}:{target['action_pair']}"
        for target in collection_targets
    )
    unmatched_collection_targets = [
        key for key in expected_collection_target_keys if key not in contrast_collection_target_counts
    ]
    unavailable_collection_targets: dict[str, str] = {}
    for target in collection_targets:
        if target["stratum_field"] != "suite":
            continue
        suite = str(target["stratum_value"])
        key = _target_requirement_key(target)
        if presence_collection_target_counts.get(key, 0):
            continue
        missing_reference_count = int(stats.get(f"skipped_missing_reference_suite:{suite}") or 0)
        reference_available_count = int(stats.get(f"reference_available_suite:{suite}") or 0)
        if (
            missing_reference_count > 0
            and reference_available_count == 0
            and suite not in REFERENCE_BACKED_COLLECTION_SOURCES
        ):
            unavailable_collection_targets[key] = (
                "source records for this suite have no reference/expected text; "
                "reference_token_coverage cannot score them"
            )
    source_record_requirements = _collection_requirements(
        collection_targets,
        contrast_collection_target_counts,
        presence_collection_target_counts=presence_collection_target_counts,
        unavailable_targets=unavailable_collection_targets,
    )
    collection_batches = _collection_batches(source_record_requirements)
    contrast_candidate_groups = sum(
        1 for group in selected_groups
        if group["binary_reward_contrast_collection_targets"]
    )

    status = (
        "expansion_plan_ready"
        if (
            selected_candidates
            and (
                (
                    not collection_targets
                    and len(selected_groups) >= args.min_cross_action_candidate_groups
                )
                or (
                    collection_targets
                    and contrast_candidate_groups >= args.min_cross_action_candidate_groups
                )
            )
        )
        else "insufficient_non_overlapping_cross_action_candidates"
    )
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "candidate_schema_version": CANDIDATE_SCHEMA_VERSION,
        "inputs": [str(path) for path in input_paths],
        "existing_manifest": str(args.existing_manifest) if args.existing_manifest else None,
        "existing_pairwise_jsonl": (
            str(args.existing_pairwise_jsonl) if args.existing_pairwise_jsonl else None
        ),
        "target_source_families": sorted(target_source_families),
        "target_suites": sorted(target_suites),
        "target_match_mode": args.target_match_mode,
        "target_actions": sorted(target_actions),
        "collection_targets_json": (
            str(args.collection_targets_json) if args.collection_targets_json else None
        ),
        "collection_target_count": len(collection_targets),
        "matched_collection_target_counts": dict(sorted(contrast_collection_target_counts.items())),
        "candidate_presence_collection_target_counts": dict(
            sorted(presence_collection_target_counts.items())
        ),
        "collection_target_match_metric": "source_binary_reward_directional_contrast",
        "unmatched_collection_targets": unmatched_collection_targets,
        "unavailable_collection_targets": dict(sorted(unavailable_collection_targets.items())),
        "source_record_requirements": source_record_requirements,
        "collection_batches": collection_batches,
        "candidate_rows": len(selected_candidates),
        "candidate_groups": len(selected_groups),
        "candidate_contrast_groups": contrast_candidate_groups,
        "candidate_action_counts": dict(sorted(action_counts.items())),
        "candidate_source_family_counts": dict(sorted(source_family_counts.items())),
        "candidate_suite_counts": dict(sorted(suite_counts.items())),
        "candidate_group_source_family_counts": dict(sorted(group_source_family_counts.items())),
        "candidate_group_suite_counts": dict(sorted(group_suite_counts.items())),
        "existing_manifest_source_family_counts": dict(sorted(manifest_source_family_counts.items())),
        "existing_manifest_suite_counts": dict(sorted(manifest_suite_counts.items())),
        "existing_pairwise_group_count": len(pairwise_groups),
        "skipped_pairwise_overlap_groups": skipped_pairwise_overlap,
        "skipped_no_cross_action_groups": skipped_no_cross_action,
        "skipped_no_collection_target_pair_groups": skipped_no_collection_target_pair,
        "min_cross_action_candidate_groups": args.min_cross_action_candidate_groups,
        "decision": {
            "status": status,
            "runtime_gate_change_allowed": False,
            "recommended_next": (
                "score_selected_candidates_and_rebuild_pairwise_contract"
                if status == "expansion_plan_ready"
                else "add_more_source_records_for_failed_pairwise_holdout_strata"
            ),
        },
        "privacy": {
            "private_fields_excluded": sorted(PRIVATE_FIELDS),
            "text_represented_by_sha256_and_lengths": True,
            "commits_prompt_reference_response_text": False,
        },
        "collection_guidance": {
            "workspace": str(DEFAULT_COLLECTION_WORKDIR),
            "seeding_eval_command_template": (
                "uv run python scripts/benchmark/seed_specialist_routing.py "
                "--suites <suite> --roles <actions_to_evaluate_on_same_source_record> "
                "--modes direct --sample-size <n> "
                f"--max-tokens {DEFAULT_COLLECTION_MAX_TOKENS} --strict-modes --dry-run "
                "--output <benchmarks/results/eval/seeding_a9_*.json>"
            ),
            "reference_backed_suite_sources": {
                suite: str(path)
                for suite, path in sorted(REFERENCE_BACKED_COLLECTION_SOURCES.items())
            },
            "orchestrator_live_seed_note": (
                "add records under benchmarks/results/orchestrator/seeding_live*.json "
                "or an equivalent orchestrator source path so source_family resolves "
                "to orchestrator_live_seed"
            ),
            "post_collection_pipeline": _post_collection_commands(),
        },
        "stats": {key: int(value) for key, value in sorted(stats.items())},
        "selected_groups": selected_groups[:100],
    }
    return selected_candidates, summary


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Offline Reward Pairwise Holdout Expansion Plan",
        "",
        f"- Decision: `{summary['decision']['status']}`",
        f"- Candidate rows: `{summary['candidate_rows']}`",
        f"- Candidate groups: `{summary['candidate_groups']}`",
        f"- Target source families: `{summary['target_source_families']}`",
        f"- Target suites: `{summary['target_suites']}`",
        f"- Target match mode: `{summary['target_match_mode']}`",
        f"- Target actions: `{summary['target_actions']}`",
        f"- Collection targets: `{summary['collection_target_count']}`",
        f"- Collection target match metric: `{summary['collection_target_match_metric']}`",
        f"- Matched collection targets: `{summary['matched_collection_target_counts']}`",
        f"- Candidate-presence collection targets: `{summary['candidate_presence_collection_target_counts']}`",
        f"- Unmatched collection targets: `{summary['unmatched_collection_targets']}`",
        f"- Unavailable collection targets: `{summary['unavailable_collection_targets']}`",
        f"- Candidate contrast groups: `{summary['candidate_contrast_groups']}`",
        f"- Candidate action counts: `{summary['candidate_action_counts']}`",
        f"- Candidate source-family counts: `{summary['candidate_source_family_counts']}`",
        f"- Candidate suite counts: `{summary['candidate_suite_counts']}`",
        f"- Existing pairwise groups: `{summary['existing_pairwise_group_count']}`",
        f"- Skipped pairwise-overlap groups: `{summary['skipped_pairwise_overlap_groups']}`",
        f"- Skipped no-cross-action groups: `{summary['skipped_no_cross_action_groups']}`",
        f"- Skipped no-collection-target-pair groups: `{summary['skipped_no_collection_target_pair_groups']}`",
        f"- Runtime gate change allowed: `{summary['decision']['runtime_gate_change_allowed']}`",
        f"- Recommended next: `{summary['decision']['recommended_next']}`",
        "",
        "## Source Record Requirements",
        "",
    ]
    for requirement in summary["source_record_requirements"][:20]:
        line = (
            f"- `{requirement['target']}`: `{requirement['status']}`, "
            f"priority `{requirement['collection_priority']}` "
            f"(`{requirement['collection_priority_reason']}`), "
            f"evaluate `{requirement['actions_to_evaluate_on_same_source_record']}` "
            f"on the same source records; preferred winners "
            f"`{requirement['target_preferred_actions']}`; suggest "
            f"`{requirement['suggested_min_new_source_records']}` new records"
        )
        reason = requirement.get("collection_unavailable_reason")
        if reason:
            line += f"; unavailable reason `{reason}`"
        lines.append(line)
    if not summary["source_record_requirements"]:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Selected Groups",
            "",
        ]
    )
    for group in summary["selected_groups"][:20]:
        lines.append(
            f"- `{group['source_family']}/{group['suite']}` "
            f"`{group['source_path']}#{group['source_record_offset']}` "
            f"candidates `{group['candidate_actions']}` existing "
            f"`{group['existing_manifest_actions']}` targets "
            f"`{group['matched_collection_targets']}`"
        )
    if not summary["selected_groups"]:
        lines.append("- none")
    lines.extend(
        [
            "",
            "This artifact is prompt-free. It selects source/role keys for the",
            "existing offline scoring path and does not authorize a runtime gate.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan pairwise expansion candidates for failed A9 holdout strata.",
    )
    parser.add_argument("--input", action="append", type=Path, default=None)
    parser.add_argument("--existing-manifest", type=Path, default=DEFAULT_EXISTING_MANIFEST)
    parser.add_argument("--existing-pairwise-jsonl", type=Path, default=DEFAULT_EXISTING_PAIRWISE)
    parser.add_argument("--candidates-jsonl", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--summary-md", type=Path)
    parser.add_argument(
        "--collection-manifest-json",
        type=Path,
        help="Optional guarded acquisition manifest for missing source-record batches.",
    )
    parser.add_argument(
        "--collection-script",
        type=Path,
        help="Optional executable shell script for the guarded acquisition manifest.",
    )
    parser.add_argument(
        "--collection-timestamp",
        default=COLLECTION_TIMESTAMP_PLACEHOLDER,
        help=(
            "UTC timestamp to materialize collection outputs, or the default "
            f"{COLLECTION_TIMESTAMP_PLACEHOLDER} placeholder for runtime date stamping."
        ),
    )
    parser.add_argument("--target-source-families", default=DEFAULT_TARGET_SOURCE_FAMILIES)
    parser.add_argument("--target-suites", default=DEFAULT_TARGET_SUITES)
    parser.add_argument(
        "--collection-targets-json",
        type=Path,
        help="Optional preference-direction audit JSON; restrict selected groups to its collection_targets.",
    )
    parser.add_argument(
        "--target-match-mode",
        choices=("any", "all"),
        default="any",
        help="Use 'any' for the union of weak strata, or 'all' for their intersection.",
    )
    parser.add_argument(
        "--target-actions",
        default="architect_general,coder_escalation,frontdoor",
    )
    parser.add_argument("--min-cross-action-candidate-groups", type=int, default=20)
    parser.add_argument("--max-groups", type=int)
    parser.add_argument("--max-candidate-rows", type=int)
    parser.add_argument(
        "--allow-existing-pairwise-groups",
        action="store_false",
        dest="require_non_overlapping_pairwise_groups",
        help="Allow candidate groups that already appear in the existing pairwise contract.",
    )
    parser.set_defaults(require_non_overlapping_pairwise_groups=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        candidates, summary = build_plan(args)
    except (PairwiseHoldoutExpansionError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    write_jsonl(args.candidates_jsonl, candidates)
    write_json(args.summary_json, summary)
    if args.summary_md:
        write_markdown(args.summary_md, summary)
    if args.collection_manifest_json or args.collection_script:
        try:
            manifest = build_collection_manifest(
                summary,
                timestamp=str(args.collection_timestamp),
            )
        except PairwiseHoldoutExpansionError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.collection_manifest_json:
            write_json(args.collection_manifest_json, manifest)
        if args.collection_script:
            write_collection_script(args.collection_script, manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
