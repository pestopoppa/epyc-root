"""Species 3 — StructuralLab: Feature flags, routing model lifecycle, checkpointing.

Manages the routing intelligence lifecycle:
  checkpoint → train → A/B test → enable → monitor → reset → reseed
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("autopilot.structural_lab")

ORCH_ROOT = Path(__file__).resolve().parents[3]
CHECKPOINT_DIR = ORCH_ROOT / "orchestration" / "autopilot_checkpoints"
MEMORY_DIR = ORCH_ROOT / "orchestration" / "repl_memory" / "sessions"
SKILLS_DIR = ORCH_ROOT / "orchestration" / "repl_memory"
PROMPTS_DIR = ORCH_ROOT / "orchestration" / "prompts"
CLASSIFIER_CONFIG = ORCH_ROOT / "orchestration" / "classifier_config.yaml"
AP22_MEMORY = ORCH_ROOT / "orchestration" / "autopilot_short_term_memory.md"
STRATEGY_STORE_DIR = SKILLS_DIR / "strategies"
STRATEGY_STORE_CHECKPOINT = "strategy_store"

AUTOPILOT_STATE = ORCH_ROOT / "orchestration" / "autopilot_state.json"
EPISODIC_DB = MEMORY_DIR / "episodic.db"

# Files to checkpoint — autopilot_state.json is CRITICAL (contains Pareto frontier
# with trial configs, HV history, all entries). Without it, frontier is lost on restart.
CHECKPOINT_FILES = {
    "autopilot_state.json": AUTOPILOT_STATE,
    "episodic.db": MEMORY_DIR / "episodic.db",
    "embeddings.faiss": MEMORY_DIR / "embeddings.faiss",
    "id_map.npy": MEMORY_DIR / "id_map.npy",
    "skills.db": SKILLS_DIR / "skills.db",
    "skill_embeddings.faiss": SKILLS_DIR / "skill_embeddings.faiss",
    "routing_classifier_weights.npz": SKILLS_DIR / "routing_classifier_weights.npz",
    "graph_router_weights.npz": ORCH_ROOT / "scripts" / "graph_router" / "graph_router_weights.npz",
}


@dataclass
class CheckpointMeta:
    timestamp: str
    trial_id: int = -1
    hypervolume: float = 0.0
    feature_flags: dict[str, bool] = field(default_factory=dict)
    config_snapshot: dict[str, Any] = field(default_factory=dict)
    memory_count: int = 0
    is_production_best: bool = False
    notes: str = ""


class StructuralLab:
    """Species 3: Feature flag experiments + routing intelligence lifecycle."""

    def __init__(self, orchestrator_url: str = "http://localhost:8000"):
        self.url = orchestrator_url

    # ── checkpointing ────────────────────────────────────────────

    def checkpoint_state(
        self,
        trial_id: int = -1,
        hypervolume: float = 0.0,
        feature_flags: dict[str, bool] | None = None,
        config_snapshot: dict[str, Any] | None = None,
        notes: str = "",
        mark_production_best: bool = False,
    ) -> Path:
        """Snapshot all routing intelligence files to timestamped directory."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        cp_dir = CHECKPOINT_DIR / ts
        cp_dir.mkdir(parents=True, exist_ok=True)

        # Copy files
        copied = []
        for name, src in CHECKPOINT_FILES.items():
            if src.exists():
                dst = cp_dir / name
                shutil.copy2(src, dst)
                copied.append(name)
                log.info("Checkpointed %s", name)

        # Copy prompts
        prompts_cp = cp_dir / "prompts"
        if PROMPTS_DIR.exists():
            shutil.copytree(PROMPTS_DIR, prompts_cp, dirs_exist_ok=True)
            copied.append("prompts/")

        # Copy classifier config
        if CLASSIFIER_CONFIG.exists():
            shutil.copy2(CLASSIFIER_CONFIG, cp_dir / "classifier_config.yaml")
            copied.append("classifier_config.yaml")

        # AP-22 + StrategyStore are planner memory. A checkpoint/restore must
        # snapshot them with the frontier/config files or a rewind leaves stale
        # hypotheses active after restoring older routing state.
        if AP22_MEMORY.exists():
            shutil.copy2(AP22_MEMORY, cp_dir / AP22_MEMORY.name)
            copied.append(AP22_MEMORY.name)

        if STRATEGY_STORE_DIR.exists():
            shutil.copytree(
                STRATEGY_STORE_DIR,
                cp_dir / STRATEGY_STORE_CHECKPOINT,
                dirs_exist_ok=True,
            )
            copied.append(f"{STRATEGY_STORE_CHECKPOINT}/")

        # Memory count
        memory_count = self._get_memory_count()

        # Write metadata
        meta = CheckpointMeta(
            timestamp=ts,
            trial_id=trial_id,
            hypervolume=hypervolume,
            feature_flags=feature_flags or {},
            config_snapshot=config_snapshot or {},
            memory_count=memory_count,
            is_production_best=mark_production_best,
            notes=notes,
        )
        (cp_dir / "checkpoint_meta.json").write_text(
            json.dumps(meta.__dict__, indent=2, default=str)
        )

        # If production best, update symlink
        if mark_production_best:
            best_link = CHECKPOINT_DIR / "production_best"
            if best_link.is_symlink() or best_link.exists():
                best_link.unlink()
            best_link.symlink_to(cp_dir)
            log.info("Marked as production best: %s", ts)

        log.info("Checkpoint %s: %d files copied, %d memories", ts, len(copied), memory_count)
        return cp_dir

    def restore_checkpoint(
        self, checkpoint_path: Path | None = None, *, restore_prompts: bool = True
    ) -> dict[str, Any]:
        """Restore routing intelligence from a checkpoint.

        If no path given, restores from production_best. ``restore_prompts=False`` skips
        the checkpoint's prompt-directory copy (a mutation candidate's rollback restores
        only its own file, and must not overwrite unrelated prompt edits).
        """
        if checkpoint_path is None:
            checkpoint_path = CHECKPOINT_DIR / "production_best"
            if not checkpoint_path.exists():
                return {"status": "error", "error": "No production_best checkpoint"}

        if checkpoint_path.is_symlink():
            checkpoint_path = checkpoint_path.resolve()

        if not checkpoint_path.exists():
            return {"status": "error", "error": f"Checkpoint not found: {checkpoint_path}"}

        restored = []
        for name, dst in CHECKPOINT_FILES.items():
            src = checkpoint_path / name
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                restored.append(name)

        # Restore prompts
        prompts_cp = checkpoint_path / "prompts"
        if restore_prompts and prompts_cp.exists():
            shutil.copytree(prompts_cp, PROMPTS_DIR, dirs_exist_ok=True)
            restored.append("prompts/")

        # Restore classifier config
        cc = checkpoint_path / "classifier_config.yaml"
        if cc.exists():
            shutil.copy2(cc, CLASSIFIER_CONFIG)
            restored.append("classifier_config.yaml")

        # Restore or clear planner memory explicitly. Older checkpoints did not
        # carry these artifacts; clearing is safer than keeping post-checkpoint
        # hypotheses attached to pre-checkpoint routing state.
        ap22_src = checkpoint_path / AP22_MEMORY.name
        if ap22_src.exists():
            AP22_MEMORY.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ap22_src, AP22_MEMORY)
            restored.append(AP22_MEMORY.name)
        elif AP22_MEMORY.exists():
            AP22_MEMORY.unlink()
            restored.append(f"{AP22_MEMORY.name}:cleared")

        strategy_src = checkpoint_path / STRATEGY_STORE_CHECKPOINT
        if STRATEGY_STORE_DIR.exists():
            if STRATEGY_STORE_DIR.is_dir():
                shutil.rmtree(STRATEGY_STORE_DIR)
            else:
                STRATEGY_STORE_DIR.unlink()
        if strategy_src.exists():
            shutil.copytree(strategy_src, STRATEGY_STORE_DIR)
            restored.append(f"{STRATEGY_STORE_CHECKPOINT}/")
        else:
            restored.append(f"{STRATEGY_STORE_CHECKPOINT}/:cleared")

        log.info("Restored %d files from %s", len(restored), checkpoint_path.name)
        return {"status": "ok", "restored": restored, "from": str(checkpoint_path)}

    def list_checkpoints(self) -> list[dict[str, Any]]:
        """List available checkpoints with metadata."""
        if not CHECKPOINT_DIR.exists():
            return []
        result = []
        for d in sorted(CHECKPOINT_DIR.iterdir()):
            if not d.is_dir() or d.is_symlink():
                continue
            meta_file = d / "checkpoint_meta.json"
            if meta_file.exists():
                meta = json.loads(meta_file.read_text())
            else:
                meta = {"timestamp": d.name}
            meta["path"] = str(d)
            result.append(meta)
        return result

    # ── routing model training ───────────────────────────────────

    def train_routing_models(self, min_memories: int = 500) -> dict[str, Any]:
        """Train MLP routing classifier + GAT GraphRouter from episodic memories."""
        memory_count = self._get_memory_count()
        if memory_count < min_memories:
            return {
                "status": "skipped",
                "reason": f"Insufficient memories: {memory_count} < {min_memories}",
            }

        results: dict[str, Any] = {"memory_count": memory_count}

        # Extract training data (applies label normalization, uses reembedded.npz if available)
        try:
            extract_script = ORCH_ROOT / "scripts" / "graph_router" / "extract_training_data.py"
            if extract_script.exists():
                proc = subprocess.run(
                    [sys.executable, str(extract_script)],
                    capture_output=True, text=True, timeout=120,
                    cwd=str(ORCH_ROOT),
                )
                results["extraction"] = {
                    "status": "ok" if proc.returncode == 0 else "error",
                    "stdout": proc.stdout[-500:],
                    "stderr": proc.stderr[-500:],
                }
            else:
                results["extraction"] = {"status": "script_not_found"}
        except Exception as e:
            results["extraction"] = {"status": "error", "error": str(e)}

        # Train MLP classifier (depends on extracted data above)
        try:
            classifier_script = ORCH_ROOT / "scripts" / "graph_router" / "train_routing_classifier.py"
            if classifier_script.exists():
                proc = subprocess.run(
                    [sys.executable, str(classifier_script)],
                    capture_output=True, text=True, timeout=120,
                    cwd=str(ORCH_ROOT),
                )
                results["classifier"] = {
                    "status": "ok" if proc.returncode == 0 else "error",
                    "stdout": proc.stdout[-500:],
                    "stderr": proc.stderr[-500:],
                }
            else:
                results["classifier"] = {"status": "script_not_found"}
        except Exception as e:
            results["classifier"] = {"status": "error", "error": str(e)}

        # Train GAT GraphRouter
        try:
            gat_script = ORCH_ROOT / "scripts" / "graph_router" / "train_graph_router.py"
            if gat_script.exists():
                proc = subprocess.run(
                    [sys.executable, str(gat_script)],
                    capture_output=True, text=True, timeout=300,
                    cwd=str(ORCH_ROOT),
                )
                results["graph_router"] = {
                    "status": "ok" if proc.returncode == 0 else "error",
                    "stdout": proc.stdout[-500:],
                    "stderr": proc.stderr[-500:],
                }
            else:
                results["graph_router"] = {"status": "script_not_found"}
        except Exception as e:
            results["graph_router"] = {"status": "error", "error": str(e)}

        return results

    # ── skillbank distillation ───────────────────────────────────

    def distill_skillbank(
        self,
        teacher: str = "claude",
        categories: list[str] | None = None,
        max_trajectories: int = 200,
        min_q_value: float = 0.7,
        skill_db_path: "Path | None" = None,
    ) -> dict[str, Any]:
        """Run the SkillBank distillation pipeline over high-Q episodic memories.

        REPAIRED 2026-07-28. Since it was written this constructed
        ``DistillationPipeline(teacher_model=..., categories=...)`` — kwargs the
        class has never accepted — and sync-called its async ``run()``, so every
        autopilot ``distill_skillbank`` action returned ``{"status": "error"}``
        and the surface never once distilled. Now mirrors the working reference
        flow in ``scripts/skillbank/seed_skills.py``: teacher resolution,
        high-Q trajectory extraction from the episodic store, and
        ``asyncio.run`` (the autopilot loop is synchronous). ``categories`` is
        accepted for action-schema compatibility but the pipeline groups by
        trajectory OUTCOME (success/failure/escalation), not by these labels.

        Requires inference: the teacher LLM writes the skills. ``teacher`` is
        one of claude | codex | local | mock (mock = wiring test, stores
        nothing unless preloaded with responses).
        """
        try:
            import asyncio

            import numpy as np

            from orchestration.repl_memory.distillation.pipeline import DistillationPipeline
            from orchestration.repl_memory.distillation.teachers import (
                ClaudeTeacher,
                CodexTeacher,
                LocalLlamaTeacher,
                MockTeacher,
            )
            from orchestration.repl_memory.embedder import TaskEmbedder
            from orchestration.repl_memory.episodic_store import EpisodicStore
            from orchestration.repl_memory.skill_bank import SkillBank
        except ImportError as e:
            log.warning("DistillationPipeline not available: %s", e)
            return {"status": "not_available"}
        try:
            def _local_teacher():
                # LocalLlamaTeacher's class default (port 8083, qwen3-235b) is a
                # dead endpoint from an old lineup. Default to the always-resident
                # frontdoor and let env retarget it when the stack reshapes.
                return LocalLlamaTeacher(
                    base_url=os.environ.get(
                        "AUTOPILOT_DISTILL_LOCAL_URL", "http://127.0.0.1:8080"
                    ),
                    model_id=os.environ.get(
                        "AUTOPILOT_DISTILL_LOCAL_MODEL", "qwen3.6-35b-a3b-frontdoor"
                    ),
                )

            teachers = {
                "claude": ClaudeTeacher,
                "codex": CodexTeacher,
                "local": _local_teacher,
                "mock": MockTeacher,
            }
            if teacher not in teachers:
                return {
                    "status": "error",
                    "error": f"unknown teacher {teacher!r}; use one of {sorted(teachers)}",
                }
            teacher_obj = teachers[teacher]()
            if categories:
                log.info(
                    "distill_skillbank: categories=%s noted; pipeline groups by outcome",
                    categories,
                )

            store = EpisodicStore()
            # Zero-vector query = "any k, ranked by Q" (all IP scores are 0.0,
            # so ordering falls to the Q filter) — same idiom as seed_skills.py.
            memories = store.retrieve_by_similarity(
                np.zeros(1024, dtype=np.float32),
                k=max_trajectories,
                min_q_value=min_q_value,
            )
            trajectories = []
            for mem in memories:
                ctx_d = mem.context if isinstance(mem.context, dict) else {}
                trajectories.append(
                    {
                        "task_id": mem.id,
                        "task_type": ctx_d.get("task_type", "general"),
                        # contract key first, legacy key second (seed_skills.py
                        # still reads only the legacy one and silently falls
                        # back to the routing label for contract rows)
                        "objective": ctx_d.get("objective")
                        or ctx_d.get("task_description")
                        or mem.action,
                        "routing_decision": mem.action,
                        "outcome": mem.outcome or "unknown",
                        "escalations": [],
                        "cost_metrics": {},
                    }
                )
            if not trajectories:
                return {
                    "status": "ok",
                    "report": {"total_trajectories": 0, "skills_stored": 0},
                    "note": f"no memories with Q >= {min_q_value}; nothing to distill",
                }

            # Pair faiss_path with db_path: SkillBank defaults faiss_path to the
            # LIVE sessions dir, so a custom db_path alone would split the pair
            # (db in one place, vectors written into production).
            sb = SkillBank(
                db_path=skill_db_path,
                faiss_path=Path(skill_db_path).parent if skill_db_path else None,
            )
            try:
                pipeline = DistillationPipeline(
                    teacher=teacher_obj,
                    skill_bank=sb,
                    embedder=TaskEmbedder(),  # write path refuses fallback vectors
                )
                report = asyncio.run(pipeline.run(trajectories))
            finally:
                sb.close()
            return {
                "status": "ok",
                "report": {
                    "teacher": teacher_obj.model_id,
                    "total_trajectories": report.total_trajectories,
                    "skills_proposed": report.skills_proposed,
                    "skills_stored": report.skills_stored,
                    "skills_merged": report.skills_merged,
                    "skills_rejected": report.skills_rejected,
                    "duration_seconds": round(report.duration_seconds, 1),
                    "errors": report.errors[:5],
                },
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── memory reset ─────────────────────────────────────────────

    def reset_and_reseed(
        self,
        keep_seen: bool = True,
        keep_skills: bool = True,
        checkpoint_first: bool = True,
        trial_id: int = -1,
    ) -> dict[str, Any]:
        """Checkpoint → reset → ready for reseeding.

        NEVER resets without checkpointing first (unless checkpoint_first=False
        and caller has already checkpointed).
        """
        result: dict[str, Any] = {}

        if checkpoint_first:
            cp = self.checkpoint_state(
                trial_id=trial_id,
                notes="Pre-reset checkpoint",
            )
            result["checkpoint"] = str(cp)

        # Run reset script
        reset_script = ORCH_ROOT / "scripts" / "session" / "reset_episodic_memory.sh"
        if not reset_script.exists():
            return {"status": "error", "error": "Reset script not found"}

        cmd = ["bash", str(reset_script)]
        if keep_seen:
            cmd.append("--keep-seen")
        if keep_skills:
            cmd.append("--keep-skills")

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
                cwd=str(ORCH_ROOT),
            )
            result["reset"] = {
                "status": "ok" if proc.returncode == 0 else "error",
                "stdout": proc.stdout[-500:],
                "stderr": proc.stderr[-500:],
            }
        except Exception as e:
            result["reset"] = {"status": "error", "error": str(e)}

        return result

    # ── feature flag experiments ─────────────────────────────────

    def propose_flag_experiment(
        self,
        flags: dict[str, bool],
    ) -> dict[str, Any]:
        """Propose a feature flag experiment.

        Validates flag dependencies against the MERGED candidate config (live
        flags + proposed overrides), not the partial patch. Validating only
        ``Features(**flags)`` defaults every unspecified flag to False, so a
        single-flag enable of a dependent feature always fails its dependency
        check — e.g. ``{"specialist_routing": True}`` reports "requires memrl"
        even when memrl is live-ON. That made the documented two-step
        (enable dependency in one trial, dependent flag in the next) impossible.
        Merging mirrors what apply_flag_experiment / POST /config actually do.

        Status contract:
          valid   — merged config passes all dependency checks.
          invalid — KNOWN live state + a stable dependency violation. Blacklistable.
          error   — could not validate reliably (exception, OR live flag state
                    unavailable so the merge is untrustworthy). NOT blacklistable.
        """
        import sys
        # DRIFT-1: insert the repo ROOT (not <root>/src) so src/ is never ahead of
        # scripts/autopilot on sys.path. Inserting <root>/src at position 0 let a
        # bare `import safety_gate` (used throughout the autopilot) bind src/*.py
        # instead of scripts/autopilot/safety_gate.py. Import src modules via the
        # `src.` package prefix from the repo root instead.
        if str(ORCH_ROOT) not in sys.path:
            sys.path.insert(0, str(ORCH_ROOT))

        try:
            from src.features import Features, _REGISTRY_BY_NAME

            # Validate all flags exist in the declarative registry (always
            # trustworthy — registry-based, independent of live state).
            unknown = set(flags.keys()) - set(_REGISTRY_BY_NAME.keys())
            if unknown:
                return {
                    "status": "invalid",
                    "errors": [f"Unknown flags not in registry: {sorted(unknown)}"],
                    "proposed_flags": flags,
                }

            current = self.current_flags()  # {} if orchestrator unreachable
            merged = {
                k: v
                for k, v in {**current, **flags}.items()
                if k in _REGISTRY_BY_NAME
            }
            errors = Features(**merged).validate()
            if errors:
                if not current:
                    # No live state — the merge is just the partial patch and
                    # its dependency failures are not trustworthy. Surface as a
                    # transient error so the caller does NOT auto-blacklist a
                    # flag that might be perfectly valid against real config.
                    return {
                        "status": "error",
                        "error": (
                            "; ".join(errors)
                            + " (live flag state unavailable; not validated "
                            "against merged config)"
                        ),
                        "proposed_flags": flags,
                    }
                return {
                    "status": "invalid",
                    "errors": errors,
                    "proposed_flags": flags,
                    "merged_flags": merged,
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

        return {"status": "valid", "flags": flags}

    def apply_flag_experiment(self, flags: dict[str, bool]) -> dict[str, Any]:
        """Apply feature flags via POST /config."""
        import httpx
        try:
            resp = httpx.post(f"{self.url}/config", json=flags, timeout=10)
            resp.raise_for_status()
            result = resp.json()
            result["attestation"] = self.attest_flags(flags)
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def attest_flags(
        self,
        expected: dict[str, bool] | None = None,
        *,
        polls: int = 120,
        timeout_s: float = 15.0,
    ) -> dict[str, Any]:
        """Poll /config/attest and summarize cross-worker flag consistency."""
        import httpx
        import time

        deadline = time.time() + timeout_s
        seen: dict[str, dict[str, Any]] = {}
        attempts = 0
        last_error = ""
        while attempts < polls and time.time() < deadline:
            attempts += 1
            try:
                resp = httpx.get(
                    f"{self.url}/config/attest",
                    headers={"Connection": "close"},
                    timeout=2,
                )
                resp.raise_for_status()
                data = resp.json()
                pid = str(data.get("pid") or f"unknown-{attempts}")
                seen[pid] = data
            except Exception as exc:
                last_error = str(exc)
            time.sleep(0.05)

        diffs: list[dict[str, Any]] = []
        expected = expected or {}
        for pid, data in seen.items():
            flags = data.get("flags", {}) or {}
            for name, value in expected.items():
                if flags.get(name) != bool(value):
                    diffs.append({
                        "pid": pid,
                        "flag": name,
                        "expected": bool(value),
                        "actual": flags.get(name),
                    })

        heterogeneous: dict[str, dict[str, Any]] = {}
        if seen:
            all_names = sorted({
                name
                for data in seen.values()
                for name in (data.get("flags", {}) or {}).keys()
            })
            for name in all_names:
                values = {
                    pid: (data.get("flags", {}) or {}).get(name)
                    for pid, data in seen.items()
                }
                if len(set(values.values())) > 1:
                    heterogeneous[name] = values

        status = "ok" if seen and not diffs and not heterogeneous else "mismatch"
        if not seen:
            status = "error"
        return {
            "status": status,
            "workers_seen": len(seen),
            "attempts": attempts,
            "expected": expected,
            "diffs": diffs,
            "heterogeneous": heterogeneous,
            "last_error": last_error,
        }

    def current_flags(self) -> dict[str, bool]:
        """Read the live feature-flag state from the orchestrator.

        POST /config with an empty body applies no overrides and returns the
        full current feature summary (see src/api/routes/config.py). This is the
        only way to GET live flags — there is no dedicated GET endpoint. Returns
        an empty dict if the orchestrator is unreachable so callers can degrade
        to "unknown" rather than crash the planner prompt assembly.
        """
        import httpx
        try:
            resp = httpx.get(f"{self.url}/config/attest", timeout=10)
            resp.raise_for_status()
            return dict(resp.json().get("flags", {}))
        except Exception:
            try:
                resp = httpx.post(f"{self.url}/config", json={}, timeout=10)
                resp.raise_for_status()
                return dict(resp.json().get("features", {}))
            except Exception:
                return {}

    def flag_schema(self) -> list[dict[str, Any]]:
        """Return the declarative feature registry for the planner prompt.

        Each entry: {name, dependencies, default_prod, description}. Sourced from
        src/features.py _FEATURE_REGISTRY (the single source of truth the flag
        validator also reads), so the planner sees the same dependency rules that
        propose_flag_experiment() enforces — e.g. graph_router -> specialist_routing.
        """
        import sys
        # DRIFT-1: insert repo ROOT and import via the `src.` package prefix so
        # src/ never shadows scripts/autopilot on sys.path (see propose_flag_experiment).
        if str(ORCH_ROOT) not in sys.path:
            sys.path.insert(0, str(ORCH_ROOT))
        try:
            from src.features import _FEATURE_REGISTRY  # type: ignore
        except Exception:
            return []
        return [
            {
                "name": s.name,
                "dependencies": list(s.dependencies),
                "default_prod": s.default_prod,
                "description": s.description,
            }
            for s in _FEATURE_REGISTRY
        ]

    # ── helpers ──────────────────────────────────────────────────

    def _get_memory_count(self) -> int:
        try:
            if not EPISODIC_DB.exists():
                return 0
            with sqlite3.connect(EPISODIC_DB) as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE action_type = ?",
                    ("routing",),
                ).fetchone()
            return int(row[0]) if row else 0
        except Exception:
            return 0

    def prune_block(self, content: str, block_id: str) -> str | None:
        """AP-17: Remove a heading-delimited block from markdown content.

        block_id is a heading like "## Section Name". Removes from the heading
        through the next heading at the same or higher level (or end of file).
        Returns pruned content, or None if block not found.
        """
        lines = content.split("\n")
        block_level = block_id.count("#")
        block_title = block_id.lstrip("# ").strip()

        start_idx = None
        end_idx = None

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#"):
                level = len(stripped) - len(stripped.lstrip("#"))
                title = stripped.lstrip("# ").strip()
                if start_idx is None and title == block_title and level == block_level:
                    start_idx = i
                elif start_idx is not None and level <= block_level:
                    end_idx = i
                    break

        if start_idx is None:
            return None

        if end_idx is None:
            end_idx = len(lines)

        pruned_lines = lines[:start_idx] + lines[end_idx:]
        return "\n".join(pruned_lines)

    def summary(self) -> dict[str, Any]:
        return {
            "memory_count": self._get_memory_count(),
            "checkpoints": len(self.list_checkpoints()),
            "has_production_best": (CHECKPOINT_DIR / "production_best").exists(),
        }

    # ── NIB2-41: MDL distillation + staleness mutation primitives ─────

    def mdl_compress_strategies(
        self,
        *,
        strategy_store: Any = None,
        journal: Any = None,
        excluded_trial_ids: set[int] | None = None,
        window_trials: int | None = None,
        min_cluster_size: int = 3,
        jaccard_threshold: float = 0.60,
        compression_threshold: float = 0.20,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Cluster near-duplicate strategies and promote clusters whose MDL
        compresses by >= ``compression_threshold`` into conventions.

        Based on `research/deep-dives/token-savior-extractable-patterns.md` §3.
        MDL proxied by ``zlib.compress(text.encode())`` length.
        """
        import zlib
        from orchestration.repl_memory.commitment_contract import (
            derive_commitment_contract,
        )

        if strategy_store is None:
            import sys as _sys
            _sys.path.insert(0, str(ORCH_ROOT / "orchestration" / "repl_memory"))
            from strategy_store import StrategyStore  # type: ignore
            strategy_store = StrategyStore()
            _owns_store = True
        else:
            _owns_store = False

        try:
            if hasattr(strategy_store, "strategy_rows_for_compression"):
                rows = strategy_store.strategy_rows_for_compression(
                    window_trials=window_trials,
                    journal=journal,
                    excluded_trial_ids=excluded_trial_ids,
                )
            else:
                if journal is not None or excluded_trial_ids is not None:
                    raise RuntimeError(
                        "journal-aware strategy compression requires "
                        "StrategyStore.strategy_rows_for_compression()"
                    )
                rows = strategy_store._conn.execute(
                    "SELECT id, insight, source_trial_id, evidence_trial_ids, metadata_json "
                    "FROM strategies ORDER BY source_trial_id DESC"
                ).fetchall()
                if window_trials is not None:
                    rows = rows[:window_trials]

            if not rows:
                return {"status": "ok", "clusters_examined": 0, "conventions_promoted": 0,
                        "total_compression_saved_bytes": 0}

            # Tokenize once.
            def tokens(text: str) -> set[str]:
                return {t for t in text.lower().split() if len(t) >= 3}

            entries = []
            for row in rows:
                try:
                    metadata = json.loads(row["metadata_json"] or "{}")
                except (KeyError, TypeError, json.JSONDecodeError):
                    metadata = {}
                entries.append({
                    "id": row["id"],
                    "insight": row["insight"],
                    "source_trial_id": row["source_trial_id"],
                    "trial": row["source_trial_id"],
                    "evidence_trial_ids": strategy_store._evidence_trial_ids_for_row(row),
                    "evidence": strategy_store._evidence_trial_ids_for_row(row),
                    "metadata": metadata if isinstance(metadata, dict) else {},
                    "toks": tokens(row["insight"]),
                })

            # Agglomerative Jaccard clustering (simple O(n^2), fine for <10k entries).
            clusters: list[list[int]] = []
            assigned: set[int] = set()
            for i, e_i in enumerate(entries):
                if i in assigned:
                    continue
                cluster = [i]
                assigned.add(i)
                for j in range(i + 1, len(entries)):
                    if j in assigned:
                        continue
                    if not e_i["toks"] or not entries[j]["toks"]:
                        continue
                    jac = len(e_i["toks"] & entries[j]["toks"]) / max(
                        len(e_i["toks"] | entries[j]["toks"]), 1
                    )
                    if jac >= jaccard_threshold:
                        cluster.append(j)
                        assigned.add(j)
                if len(cluster) >= min_cluster_size:
                    clusters.append(cluster)

            conventions_promoted = 0
            bytes_saved = 0
            for cluster in clusters:
                insights = [entries[idx]["insight"] for idx in cluster]
                ids = [entries[idx]["id"] for idx in cluster]
                trials = [entries[idx]["trial"] for idx in cluster]
                evidence_trial_ids = sorted({
                    int(trial_id)
                    for idx in cluster
                    for trial_id in entries[idx]["evidence"]
                    if trial_id is not None
                })

                # Text is presentation only. Planner applicability/binding is
                # derived from the intersection of every supporting member.
                rep = min(insights, key=lambda text: (len(text), text))
                contract = derive_commitment_contract(
                    [entries[idx] for idx in cluster], claim_fields=("insight",)
                )
                rep_bytes = len(zlib.compress(rep.encode()))

                mdl_before = sum(len(zlib.compress(ins.encode())) for ins in insights)
                # Delta = insight with rep tokens removed (coarse but fast).
                rep_toks = set(rep.lower().split())
                deltas = [
                    " ".join(t for t in ins.split() if t.lower() not in rep_toks)
                    for ins in insights
                ]
                delta_bytes = sum(len(zlib.compress(d.encode())) if d else 0 for d in deltas)
                mdl_after = rep_bytes + delta_bytes

                if mdl_before == 0:
                    continue
                ratio = (mdl_before - mdl_after) / mdl_before
                if ratio < compression_threshold:
                    continue

                if not dry_run:
                    strategy_store.add_convention(
                        representative=rep,
                        member_ids=ids,
                        compression_ratio=ratio,
                        span_trials=(min(trials), max(trials)),
                        evidence_trial_ids=evidence_trial_ids,
                        metadata=contract,
                    )
                conventions_promoted += 1
                bytes_saved += (mdl_before - mdl_after)

            return {
                "status": "ok",
                "clusters_examined": len(clusters),
                "conventions_promoted": conventions_promoted,
                "total_compression_saved_bytes": bytes_saved,
                "dry_run": dry_run,
            }
        finally:
            if _owns_store:
                strategy_store.close()

    def staleness_invalidate_strategies(
        self,
        *,
        strategy_store: Any = None,
        journal: Any = None,
        excluded_trial_ids: set[int] | None = None,
        scan_targets: list[str] | None = None,
        quarantine_threshold: float = 0.40,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Content-hash scan: when a referenced file's hash changes, bump the
        Bayesian validity counter on every strategy whose metadata cites it.

        Cascade: quarantined strategies invalidate the routing-classifier
        checkpoint if its metadata trail references the quarantined id.
        """
        from ._content_hash import hash_file

        if scan_targets is None:
            scan_targets = [
                str(PROMPTS_DIR),
                str(CLASSIFIER_CONFIG),
                str(ORCH_ROOT / "orchestration" / "model_registry.yaml"),
            ]

        if strategy_store is None:
            import sys as _sys
            _sys.path.insert(0, str(ORCH_ROOT / "orchestration" / "repl_memory"))
            from strategy_store import StrategyStore  # type: ignore
            strategy_store = StrategyStore()
            _owns_store = True
        else:
            _owns_store = False

        try:
            from pathlib import Path as _P
            # Collect current hashes for every scan target (file or dir).
            current: dict[str, str] = {}
            for target in scan_targets:
                tp = _P(target)
                if tp.is_dir():
                    for f in tp.rglob("*"):
                        if f.is_file():
                            h = hash_file(f)
                            if h is not None:
                                current[str(f)] = h
                elif tp.is_file():
                    h = hash_file(tp)
                    if h is not None:
                        current[str(tp)] = h

            changed: list[str] = []
            for path, h_now in current.items():
                h_prev = strategy_store.get_content_hash(path)
                if h_prev is not None and h_prev != h_now:
                    changed.append(path)
                if not dry_run:
                    strategy_store.upsert_content_hash(path, h_now)

            # For each strategy referencing a changed path, bump validity failure.
            import json as _json
            if hasattr(strategy_store, "strategy_rows_for_staleness_scan"):
                rows = strategy_store.strategy_rows_for_staleness_scan(
                    journal=journal,
                    excluded_trial_ids=excluded_trial_ids,
                )
            else:
                if journal is not None or excluded_trial_ids is not None:
                    raise RuntimeError(
                        "journal-aware strategy staleness invalidation requires "
                        "StrategyStore.strategy_rows_for_staleness_scan()"
                    )
                rows = strategy_store._conn.execute(
                    "SELECT id, metadata_json FROM strategies"
                ).fetchall()

            strategies_checked = len(rows)
            quarantined_count = 0
            suspected_count = 0
            touched_ids: list[str] = []

            if changed:
                changed_set = set(changed)
                for r in rows:
                    meta = _json.loads(r["metadata_json"] or "{}")
                    refs = meta.get("refs", []) or meta.get("content_refs", [])
                    if not any(ref in changed_set for ref in refs):
                        continue
                    if dry_run:
                        touched_ids.append(r["id"])
                        continue
                    validity, quarantined = strategy_store.update_validity(
                        r["id"], failure=True, quarantine_threshold=quarantine_threshold,
                    )
                    touched_ids.append(r["id"])
                    if quarantined:
                        quarantined_count += 1
                    elif validity < 0.60:
                        suspected_count += 1

            # Cascade: if any routing_classifier_weights.npz metadata references
            # the quarantined ids, flag the checkpoint for retrain.
            cascade_invalidated = 0
            if not dry_run and quarantined_count:
                quarantined_ids = strategy_store.quarantined_ids()
                classifier_meta = ORCH_ROOT / "orchestration" / "repl_memory" / "routing_classifier_meta.json"
                if classifier_meta.exists():
                    try:
                        meta = _json.loads(classifier_meta.read_text())
                        referenced = set(meta.get("training_strategy_ids", []))
                        if referenced & quarantined_ids:
                            meta["stale"] = True
                            meta["stale_at"] = datetime.now(timezone.utc).isoformat()
                            classifier_meta.write_text(_json.dumps(meta, indent=2))
                            cascade_invalidated = 1
                    except Exception as e:  # corrupt json shouldn't crash sweep
                        log.warning("classifier meta cascade check failed: %s", e)

            return {
                "status": "ok",
                "targets_scanned": len(current),
                "hashes_changed": len(changed),
                "strategies_checked": strategies_checked,
                "strategies_touched": len(touched_ids),
                "quarantined": quarantined_count,
                "suspected": suspected_count,
                "cascade_invalidated": cascade_invalidated,
                "dry_run": dry_run,
            }
        finally:
            if _owns_store:
                strategy_store.close()
