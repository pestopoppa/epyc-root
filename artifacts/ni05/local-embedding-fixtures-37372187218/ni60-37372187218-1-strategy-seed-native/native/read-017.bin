#!/usr/bin/env python3
"""Seed operator-curated handoff hints into AutoPilot StrategyStore."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
ORCH_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(ORCH_ROOT))

from orchestration.repl_memory.strategy_store import (  # noqa: E402
    DEFAULT_STRATEGY_PATH,
    StrategyStore,
)

DEFAULT_SEED_FILE = SCRIPT_DIR / "operator_seed_strategies.yaml"
DEFAULT_STATE_PATH = ORCH_ROOT / "orchestration" / "autopilot_state.json"
DEFAULT_CAMPAIGN = "operator-handoff-distillation"
AGENT_LOG_SH = ORCH_ROOT.parent / "epyc-root" / "scripts" / "utils" / "agent_log.sh"

VALID_SPECIES = {
    "all",
    "numeric_swarm",
    "prompt_forge",
    "routing",
    "seeder",
    "structural_lab",
}
VALID_ENTRY_TYPES = {"pattern", "convention"}
VALID_TRANCHES = {"green", "guardrail", "frozen"}
VALID_CONFIDENCE = {"low", "medium", "high"}
VALID_BIND_STATUS = {"live", "future", "context"}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")


@dataclass(frozen=True)
class SeedRow:
    slug: str
    tranche: str
    species: str
    entry_type: str
    title: str
    description: str
    insight: str
    evidence_trial_ids: list[int]
    source_handoff: str
    seeded_reason: str
    confidence: str
    bind_status: str
    bind_identifiers: list[str]

    @property
    def entry_id(self) -> str:
        return f"opseed-{self.tranche}-{self.slug}"

    def searchable_text(self) -> str:
        return (
            f"{self.title} {self.description} {self.insight} "
            f"{' '.join(self.bind_identifiers)}"
        ).lower()


def _load_trial_counter(path: Path) -> int:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        raise SystemExit(f"state file does not exist: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"state file is not valid JSON: {path}: {exc}") from exc
    for key in ("trial_counter", "trial_id"):
        try:
            value = int(data[key])
        except (KeyError, TypeError, ValueError):
            continue
        if value >= 0:
            return value
    raise SystemExit(f"state file lacks a non-negative trial counter: {path}")


def _coerce_row(raw: Any, idx: int) -> SeedRow:
    if not isinstance(raw, dict):
        raise ValueError(f"row {idx}: expected mapping")
    required = {
        "slug",
        "tranche",
        "species",
        "entry_type",
        "title",
        "description",
        "insight",
        "evidence_trial_ids",
        "source_handoff",
        "seeded_reason",
        "confidence",
    }
    missing = sorted(required - set(raw))
    if missing:
        raise ValueError(f"row {idx}: missing fields: {', '.join(missing)}")
    slug = str(raw["slug"]).strip()
    tranche = str(raw["tranche"]).strip()
    species = str(raw["species"]).strip()
    entry_type = str(raw["entry_type"]).strip()
    confidence = str(raw["confidence"]).strip()
    if not SLUG_RE.match(slug):
        raise ValueError(f"row {idx}: invalid slug {slug!r}")
    if tranche not in VALID_TRANCHES:
        raise ValueError(f"row {idx}: invalid tranche {tranche!r}")
    if species not in VALID_SPECIES:
        raise ValueError(f"row {idx}: invalid species {species!r}")
    if entry_type not in VALID_ENTRY_TYPES:
        raise ValueError(f"row {idx}: invalid entry_type {entry_type!r}")
    if confidence not in VALID_CONFIDENCE:
        raise ValueError(f"row {idx}: invalid confidence {confidence!r}")
    bind_status = str(raw.get("bind_status", "")).strip()
    if not bind_status:
        bind_status = "live" if species in {"numeric_swarm", "structural_lab"} else "context"
    if bind_status not in VALID_BIND_STATUS:
        raise ValueError(f"row {idx}: invalid bind_status {bind_status!r}")
    bind_raw = raw.get("bind_identifiers", [])
    if bind_raw is None:
        bind_raw = []
    if not isinstance(bind_raw, list):
        raise ValueError(f"row {idx}: bind_identifiers must be a list")
    bind_identifiers = sorted({str(item).strip() for item in bind_raw if str(item).strip()})
    if species in {"numeric_swarm", "structural_lab"} and not bind_identifiers:
        raise ValueError(
            f"row {idx}: {species} rows must list bind_identifiers"
        )
    evidence_raw = raw["evidence_trial_ids"]
    if evidence_raw is None:
        evidence_raw = []
    if not isinstance(evidence_raw, list):
        raise ValueError(f"row {idx}: evidence_trial_ids must be a list")
    evidence_trial_ids: list[int] = []
    for item in evidence_raw:
        try:
            evidence_trial_ids.append(int(item))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"row {idx}: invalid evidence trial id {item!r}"
            ) from exc
    text_fields = {
        field: str(raw[field]).strip()
        for field in (
            "title",
            "description",
            "insight",
            "source_handoff",
            "seeded_reason",
        )
    }
    empty = [field for field, value in text_fields.items() if not value]
    if empty:
        raise ValueError(f"row {idx}: empty fields: {', '.join(empty)}")
    return SeedRow(
        slug=slug,
        tranche=tranche,
        species=species,
        entry_type=entry_type,
        title=text_fields["title"],
        description=text_fields["description"],
        insight=text_fields["insight"],
        evidence_trial_ids=sorted(set(evidence_trial_ids)),
        source_handoff=text_fields["source_handoff"],
        seeded_reason=text_fields["seeded_reason"],
        confidence=confidence,
        bind_status=bind_status,
        bind_identifiers=bind_identifiers,
    )


def load_seed_rows(path: Path) -> list[SeedRow]:
    try:
        data = yaml.safe_load(path.read_text())
    except FileNotFoundError:
        raise SystemExit(f"seed file does not exist: {path}") from None
    if data is None:
        data = []
    if not isinstance(data, list):
        raise SystemExit(f"seed file must contain a top-level list: {path}")
    rows = [_coerce_row(item, idx) for idx, item in enumerate(data, start=1)]
    ids = [row.entry_id for row in rows]
    duplicates = sorted({entry_id for entry_id in ids if ids.count(entry_id) > 1})
    if duplicates:
        raise SystemExit(f"duplicate deterministic entry ids: {', '.join(duplicates)}")
    return rows


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _known_hot_swap_features() -> set[str]:
    module = _load_module(SCRIPT_DIR / "config_applicator.py", "_operator_seed_config")
    return {str(item) for item in module.HOT_SWAP_FEATURES}


def _known_numeric_surfaces() -> set[str]:
    module = _load_module(
        SCRIPT_DIR / "species" / "numeric_swarm.py",
        "_operator_seed_numeric_swarm",
    )
    return {str(item) for item in module.SURFACES}


def audit_identifiers(rows: list[SeedRow]) -> dict[str, Any]:
    """Check seed rows against live StructuralLab flags and NumericSwarm surfaces."""
    hot_swap_features = _known_hot_swap_features()
    numeric_surfaces = _known_numeric_surfaces()
    findings: list[dict[str, Any]] = []
    for row in rows:
        if row.species == "structural_lab":
            matched = sorted(set(row.bind_identifiers) & hot_swap_features)
            if row.bind_status == "live" and not matched:
                findings.append(
                    {
                        "slug": row.slug,
                        "species": row.species,
                        "status": "missing_live_hot_swap_feature",
                        "bind_identifiers": row.bind_identifiers,
                    }
                )
            elif row.bind_status != "live":
                findings.append(
                    {
                        "slug": row.slug,
                        "species": row.species,
                        "status": f"documented_{row.bind_status}_binding",
                        "bind_identifiers": row.bind_identifiers,
                    }
                )
        if row.species == "numeric_swarm":
            matched = sorted(set(row.bind_identifiers) & numeric_surfaces)
            if row.bind_status == "live" and not matched:
                findings.append(
                    {
                        "slug": row.slug,
                        "species": row.species,
                        "status": "missing_live_numeric_surface",
                        "bind_identifiers": row.bind_identifiers,
                        "known_numeric_surfaces": sorted(numeric_surfaces),
                    }
                )
            elif row.bind_status != "live":
                findings.append(
                    {
                        "slug": row.slug,
                        "species": row.species,
                        "status": f"documented_{row.bind_status}_binding",
                        "bind_identifiers": row.bind_identifiers,
                    }
                )
    blocking = [
        finding
        for finding in findings
        if finding["status"] in {
            "missing_live_hot_swap_feature",
            "missing_live_numeric_surface",
        }
    ]
    return {
        "ok": not blocking,
        "row_count": len(rows),
        "hot_swap_features": sorted(hot_swap_features),
        "numeric_surfaces": sorted(numeric_surfaces),
        "finding_count": len(findings),
        "blocking_count": len(blocking),
        "findings": findings,
    }


def _metadata(row: SeedRow, *, campaign: str, seeded_date: str) -> dict[str, Any]:
    return {
        "seeded_by": "operator",
        "seeded_date": seeded_date,
        "seed_campaign": campaign,
        "seeded_reason": row.seeded_reason,
        "source_handoff": row.source_handoff,
        "confidence": row.confidence,
        "tranche": row.tranche,
        "bind_status": row.bind_status,
        "bind_identifiers": row.bind_identifiers,
    }


def _existing_ids(store: StrategyStore, rows: list[SeedRow]) -> set[str]:
    if not rows:
        return set()
    placeholders = ",".join("?" for _ in rows)
    sql = f"SELECT id FROM strategies WHERE id IN ({placeholders})"
    return {
        item[0]
        for item in store._conn.execute(sql, [row.entry_id for row in rows]).fetchall()
    }


def _autopilot_running() -> bool:
    result = subprocess.run(
        ["pgrep", "-f", "scripts/autopilot/autopilot.py start"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _agent_log(func: str, *args: str) -> None:
    """Best-effort bridge to root agent logging for mutating operations."""
    if not AGENT_LOG_SH.exists():
        return
    quoted = " ".join(json.dumps(str(arg)) for arg in args)
    subprocess.run(
        [
            "bash",
            "-lc",
            f"source {json.dumps(str(AGENT_LOG_SH))}; {func} {quoted}",
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def seed_rows(
    *,
    rows: list[SeedRow],
    strategy_path: Path,
    source_trial_id: int,
    campaign: str,
    apply: bool,
) -> dict[str, Any]:
    if apply:
        _agent_log(
            "agent_task_start",
            "Seed operator StrategyStore hints",
            f"campaign={campaign}; rows={len(rows)}; source_trial_id={source_trial_id}",
        )
    store = StrategyStore(path=strategy_path)
    try:
        before_count = store.count()
        existing_ids = _existing_ids(store, rows)
        seeded_date = datetime.now(timezone.utc).date().isoformat()
        inserted: list[str] = []
        skipped_existing: list[str] = []
        if apply:
            for row in rows:
                if row.entry_id in existing_ids:
                    skipped_existing.append(row.entry_id)
                    continue
                store.store(
                    description=row.description,
                    insight=row.insight,
                    source_trial_id=source_trial_id,
                    species=row.species,
                    metadata=_metadata(
                        row,
                        campaign=campaign,
                        seeded_date=seeded_date,
                    ),
                    entry_type=row.entry_type,
                    evidence_trial_ids=row.evidence_trial_ids,
                    title=row.title,
                    generalized_content=row.insight,
                    entry_id=row.entry_id,
                )
                inserted.append(row.entry_id)
        after_count = store.count()
        tranche_counts = Counter(row.tranche for row in rows)
        species_counts = Counter(row.species for row in rows)
        report = {
            "apply": apply,
            "campaign": campaign,
            "source_trial_id": source_trial_id,
            "row_count": len(rows),
            "would_insert_count": len(rows) - len(existing_ids),
            "inserted_count": len(inserted),
            "skipped_existing_count": len(existing_ids) if not apply else len(skipped_existing),
            "before_count": before_count,
            "after_count": after_count,
            "tranche_counts": dict(sorted(tranche_counts.items())),
            "species_counts": dict(sorted(species_counts.items())),
            "existing_ids": sorted(existing_ids),
            "inserted_ids": inserted,
        }
        if apply:
            _agent_log(
                "agent_task_end",
                "Seed operator StrategyStore hints",
                "success",
            )
        return report
    except Exception:
        if apply:
            _agent_log(
                "agent_task_end",
                "Seed operator StrategyStore hints",
                "failure",
            )
        raise
    finally:
        store.close()


def purge_campaign(
    *,
    strategy_path: Path,
    campaign: str,
    allow_running_autopilot: bool,
) -> dict[str, Any]:
    if _autopilot_running() and not allow_running_autopilot:
        raise SystemExit(
            "AutoPilot appears to be running; stop it before purge or pass "
            "--allow-running-autopilot for a deliberate maintenance override."
        )
    _agent_log(
        "agent_task_start",
        "Purge operator StrategyStore hint campaign",
        f"campaign={campaign}; strategy_path={strategy_path}",
    )
    store = StrategyStore(path=strategy_path)
    try:
        report = store.purge_strategy_campaign(campaign)
        _agent_log(
            "agent_task_end",
            "Purge operator StrategyStore hint campaign",
            "success",
        )
        return report
    except Exception:
        _agent_log(
            "agent_task_end",
            "Purge operator StrategyStore hint campaign",
            "failure",
        )
        raise
    finally:
        store.close()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run, apply, or purge operator-curated StrategyStore hints."
    )
    parser.add_argument("--seed-file", type=Path, default=DEFAULT_SEED_FILE)
    parser.add_argument("--strategy-path", type=Path, default=DEFAULT_STRATEGY_PATH)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--campaign", default=DEFAULT_CAMPAIGN)
    parser.add_argument("--source-trial-id", type=int)
    parser.add_argument("--apply", action="store_true", help="Write rows to StrategyStore.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Explicit no-write mode; this is the default when --apply is absent.",
    )
    parser.add_argument(
        "--audit-identifiers",
        action="store_true",
        help=(
            "Check StructuralLab rows against HOT_SWAP_FEATURES and NumericSwarm "
            "rows against SURFACES without writing."
        ),
    )
    parser.add_argument(
        "--purge-campaign",
        metavar="NAME",
        help="Delete rows for a campaign and rebuild FTS5/FAISS mirrors.",
    )
    parser.add_argument(
        "--allow-running-autopilot",
        action="store_true",
        help="Allow purge while AutoPilot process is still running.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.apply and args.dry_run:
        parser.error("--dry-run cannot be combined with --apply")
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    strategy_path = args.strategy_path.expanduser().resolve()
    if args.purge_campaign:
        report = purge_campaign(
            strategy_path=strategy_path,
            campaign=args.purge_campaign,
            allow_running_autopilot=args.allow_running_autopilot,
        )
    else:
        rows = load_seed_rows(args.seed_file.expanduser().resolve())
        if args.audit_identifiers:
            report = audit_identifiers(rows)
        else:
            source_trial_id = (
                args.source_trial_id
                if args.source_trial_id is not None
                else _load_trial_counter(args.state_path.expanduser().resolve())
            )
            report = seed_rows(
                rows=rows,
                strategy_path=strategy_path,
                source_trial_id=source_trial_id,
                campaign=args.campaign,
                apply=bool(args.apply),
            )
    if args.json:
        print(json.dumps(report, sort_keys=True))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    if args.audit_identifiers and not report.get("ok", False):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
