"""`cli.py ingest <source>` for the file-shaped belief-kernel adapters.

Same lesson as ``autokernel`` and ``inf70`` in ``cli.py``: an adapter that was written,
tested and verified could never persist a row, because ``ingest`` accepted only the names
in its ``choices``. **Wiring the name IS the write side.** This module is that wiring for
every adapter whose native input is a file or a run directory.

It is a DISPATCHER, not a grader. Each source names its adapter's own reader
(``native_rows``) and its registered projection (``project``); frames go out through
``claim_tuple.to_frames``, so ``claim_tuple.grade()`` decides every tuple. No source here
carries a ladder, a grade or a fallback value. (``autopilot-journal`` and
``sealed-manifest`` predate the shared carrier and emit through their own frame builders,
which also delegate grading; they are dispatched at frame level for that reason only.)

Every matched unit ends in exactly one of four outcomes, counted separately because a
single reassuring number hides the one that needs a fix:

* ``projected``  -- at least one row reached the ledger (or would have, in a dry run);
* ``declined``   -- the strict reader accepted nothing: pre-hook, absent, void or foreign.
  Absence is recorded, never filled (spec §4.7);
* ``refused``    -- the reader or projection raised ``ProjectionError``: a record that does
  not re-derive. Named with its reason, never skipped silently;
* units that do not exist are reported under ``missing``.
"""

from __future__ import annotations

import importlib
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from claim_tuple import ProjectionError, to_frames

Units = Callable[[Path], list[Path]]


def _files(*patterns: str) -> Units:
    """A file is its own unit; a directory contributes every file matching ``patterns``."""
    def units(path: Path) -> list[Path]:
        if path.is_file():
            return [path]
        found: set[Path] = set()
        for pattern in patterns:
            found.update(p for p in path.glob(pattern) if p.is_file())
        return sorted(found)
    return units


def _run_dirs(marker: str) -> Units:
    """A directory holding ``marker`` is one run; otherwise its children that hold it are."""
    def units(path: Path) -> list[Path]:
        if not path.is_dir():
            return []
        if (path / marker).is_file():
            return [path]
        return sorted(p for p in path.iterdir() if p.is_dir() and (p / marker).is_file())
    return units


@dataclass(frozen=True)
class Source:
    name: str
    module: str
    units: Units
    default: Path | None = None
    natives: str = "native_rows"
    project: str = "project"
    #: frame-level sources: ``frames(unit, as_of=...) -> list[frame]``; no native rows.
    frames: str = ""
    #: optional per-native projection selector (research sweeps carry three projections).
    selector: Callable[[Any, dict], Callable] | None = None
    note: str = ""
    task: str = ""
    extra: dict = field(default_factory=dict)

    def load(self):
        return importlib.import_module(f"adapters.{self.module}")


def _sweep_projection(mod, native: dict) -> Callable:
    schema = native["row"]["schema"]
    return {mod.G2_SCHEMA: mod.project_g2, mod.G3_SCHEMA: mod.project_g3}.get(
        schema, mod.project_g4)


ORCH_JOURNAL_DIR = Path("/workspace/repos/epyc-orchestrator/orchestration")
INF70_AGENT_RUNS = Path("/mnt/raid0/llm/tmp/inf70/agents")
ORCHESTRATOR = Path("/mnt/raid0/llm/epyc-orchestrator")

SOURCES: dict[str, Source] = {s.name: s for s in (
    Source("research-screen", "research_screen", _files("*.research-screen.json", "**/*.research-screen.json"),
           note="producer-sealed shared screen receipts: selector_replay or typed_decision_shadow",
           task="VB-RI-SCREEN-1 / VB-DGM-1 / VB-TDP-EXT"),
    Source("kv-quant-27b-v10-measurement", "kv_quant_27b_v10",
           _files("belief_measurements.jsonl", "*/belief_measurements.jsonl",
                  "*/*/belief_measurements.jsonl"),
           default=Path("/workspace/repos/epyc-inference-research/data/gpu-mi210/kv-quant-27b-v10-sweep"),
           note="v10 MI210 KV-quant sweep sidecars; pre-hook/failed runs yield no claims",
           task="VB-KVQ-V10"),
    Source("kb-rag-qlen", "kb_rag_query_length",
           _files("*query_length*.json", "**/*query_length*.json"),
           note="persisted `query_length_report.py --out` snapshots", task="VB-KBRAG-QLEN-R"),
    Source("typed-decisions-measurement", "typed_decisions_measurement",
           _files("*.json", "**/*.json"),
           default=Path(tempfile.gettempdir()) / "typed_decisions",
           note="TD-2/TD-3 `measure.py` receipts (`<study>-<utc-stamp>.json`); the default "
                "location is the producer's tmp dir, so `--path` a durable copy before citing "
                "these numbers. A foreign document is refused by name; a receipt missing a "
                "declared metric is refused, never silently under-produced",
           task="VB-TDP-1"),
    Source("inf70-arms", "inf70_serving_arm",
           _files("*.belief_measurements.jsonl", "*/runs/*.belief_measurements.jsonl"),
           default=INF70_AGENT_RUNS,
           note="per-arm sidecars under agents/*/runs", task="SC75 / VB-INF70-ARMS"),
    Source("contention-gate", "contention_gate", _files("*.jsonl"),
           default=Path("/mnt/raid0/llm/bus-runtime/contention_gate_capture.jsonl"),
           task="SC19"),
    Source("contention-matrix", "contention_matrix", _run_dirs("j4b_nway_results.json"),
           default=Path("/mnt/raid0/llm/epyc-orchestrator/data/contention_matrix"),
           task="SC21"),
    Source("beam", "beam_memory", _files("belief_measurements.jsonl",
                                         "*/belief_measurements.jsonl"), task="SC68"),
    Source("tulving", "tulving_episodic", _files("belief_measurements.jsonl",
                                                 "*/belief_measurements.jsonl"), task="SC67"),
    Source("chat-template-ab", "chat_template_ab",
           _files("belief_measurements.jsonl", "*/belief_measurements.jsonl"), task="SC46"),
    Source("occ1", "occ1_optical_compression",
           _files("belief_measurements.jsonl", "*/belief_measurements.jsonl"),
           note="OCC-1 run dirs (`run_occ1.py report` sidecars); VOID/pre-hook runs decline",
           task="SC85"),
    Source("tale-budget", "tale_budget",
           _files("*.beliefs.jsonl", "**/*.beliefs.jsonl"),
           note="PRB-T4 `prb_t4_tale_gpu.py --out` dirs (`<results>.beliefs.jsonl` beside each "
                "eval_tale_budget.py results file); pre-hook results decline",
           task="VB-PRB-T4"),
    Source("review-f1", "review_f1",
           _files("_summary.semantic.*.beliefs.jsonl", "**/_summary.semantic.*.beliefs.jsonl"),
           note="EV-13b `ev13b_run.py --out` dirs (one sidecar per judge beside "
                "`_summary.semantic.<judge>.json`); pre-hook summaries decline",
           task="VB-REVIEW-F1"),
    Source("opencode-shell", "opencode_shell_run", _run_dirs("opencode_shell_run.json"),
           note="HS-4 OpenCode-shell run dirs (driver-written `opencode_shell_run.json` plus the "
                "SC86 `opencode_shell_run.beliefs.jsonl`); a run dir without the belief sidecar "
                "is pre-hook and declines",
           task="SC86"),
    Source("ak-actor-seat", "autokernel_actor_seat",
           _files("actor-calls.jsonl", "**/actor-calls.jsonl", "result-*.json",
                  "**/result-*.json"),
           note="AutoKernel actor-seat records: `actor-replies/actor-calls.jsonl` lines "
                "(epyc.autokernel.actor_call.v1) and seat A/B `result-<arm>.json` "
                "(epyc.autokernel.seat_ab_arm.v1); pre-hook lines/results and censored "
                "(timeout/signal) sessions decline; every tuple is an OBSERVATION (n=1, no "
                "codified protocol)",
           task="VB-AK-SEAT"),
    Source("memento-lora", "memento_lora",
           _files("stage*_belief_measurements.json", "**/stage*_belief_measurements.json"),
           task="SC20"),
    Source("pareval", "pareval", _files("*records*.jsonl", "**/*records*.jsonl"), task="SC45"),
    Source("eval-tower-band", "eval_tower_band", _files("*.band.json", "**/*.band.json"),
           task="SC37"),
    Source("fanout-outcome", "fanout_outcome", _files("*.v2.jsonl"),
           default=Path(__file__).resolve().parents[2] / "data" / "fanout_timing"
           / "merged.v2.jsonl", task="SC62"),
    Source("mhs-guard-verdicts", "mhs_guard", _run_dirs("autopilot_rejected_mutations.jsonl"),
           default=ORCH_JOURNAL_DIR,
           note="AP-53 ledger + journal, closed post-hook day windows; declines until "
                "VIDYA_MHS_GUARD_HOOK_SINCE / mhs_guard.HOOK_SINCE is set "
                "(producer sub/gate-frontier-20260916, pending merge)", task="VB-MHS-OPS"),
    Source("mhs-guard-ops", "mhs_guard", _run_dirs("autopilot_journal.jsonl"),
           default=ORCH_JOURNAL_DIR, natives="ops_native_rows", project="project_ops",
           note="journal `eval_leakage_guard` events: preflight failures, closed alarm "
                "intervals", task="VB-MHS-OPS"),
    Source("research-sweep-g1", "research_sweeps", _run_dirs("run_manifest.json"),
           project="project_g1", task="SC49"),
    Source("research-sweep-g234", "research_sweeps", _files("*.jsonl"),
           natives="native_rows_file", selector=_sweep_projection, task="SC49/SC50"),
    Source("autopilot-journal", "autopilot_journal", lambda p: [p] if p.exists() else [],
           default=Path("/workspace"), frames="emit",
           note="PATH is an epyc-root checkout (shards under repos/epyc-orchestrator) "
                "or one autopilot_journal*.jsonl shard"),
    Source("autopilot-reproposal-rate", "autopilot_reproposal_rate",
           _files("autopilot_reproposal_rates*.jsonl"),
           default=ORCHESTRATOR / "orchestration" / "autopilot_reproposal_rates.jsonl",
           note="per-window rows from AutoPilot's record_closed_windows hook; the "
                "*.retrospective.jsonl backfill is accepted and projects zero rows",
           task="VB-AP53-RATE"),
    Source("reviewer-fa", "reviewer_false_accept",
           _files("*false_accept_runs*.jsonl", "**/*false_accept_runs*.jsonl"),
           default=ORCHESTRATOR / "data" / "reviewer_eval" / "false_accept_runs.jsonl",
           note="scripts/review/score_false_accept.py scoring-run lines", task="SC83"),
    Source("sealed-manifest", "sealed_manifest", _files("artifacts/**/manifest.json"),
           default=Path("/workspace/repos/epyc-inference-research"),
           frames="frames_for_manifest"),
)}

#: Adapters that exist and are deliberately NOT dispatched here, with the reason.
UNWIRED: dict[str, str] = {
    "dflash2_experimental_runtime": (
        "authority is experimental_runtime_no_kernel_champion_no_promotion, and the reader "
        "executes the reviewed research producer by digest; wire it with DF2-5, not generically"),
    "autokernel_*": "dispatched by `ingest autokernel` (autokernel_corpus.py), except "
                    "autokernel_actor_seat, which is the file source `ak-actor-seat` above",
    "inf70_roofline_ledger": "dispatched by `ingest inf70`",
    "research_intake": "dispatched by `ingest intake` (literature class)",
}


def ingest(ledger, name: str, paths: Iterable[Path] | None, *, as_of: str,
           limit: int | None = None, dry_run: bool = False) -> dict:
    """Project every unit under ``paths`` through source ``name``; append unless dry-run."""
    src = SOURCES[name]
    roots = [Path(p) for p in paths] if paths else ([src.default] if src.default else [])
    if not roots:
        raise ValueError(f"source {name!r} has no default location; pass --path")
    mod = src.load()
    adapter_id = mod.ADAPTER_ID
    authority = getattr(mod, "AUTHORITY", None)
    if not authority:
        # No silent default: the frame's authority scope is the adapter's declaration.
        raise ValueError(f"adapter {src.module} declares no AUTHORITY")

    frames: list[dict] = []
    report: dict[str, Any] = {
        "source": name, "adapter": f"adapters/{src.module}.py", "adapter_id": adapter_id,
        "paths": [str(r) for r in roots], "units_matched": 0, "units_projected": 0,
        "declined": [], "refused": [], "missing": [], "rows_projected": 0,
        "frames_emitted": 0, "dry_run": dry_run,
    }
    for root in roots:
        if not root.exists():
            report["missing"].append(str(root))
            continue
        for unit in src.units(root):
            remaining = None if limit is None else limit - report["rows_projected"]
            if remaining is not None and remaining <= 0:
                break
            report["units_matched"] += 1
            try:
                if src.frames:
                    fn = getattr(mod, src.frames)
                    if src.frames == "emit":
                        got = list(fn(unit, as_of=as_of, limit=remaining))
                    else:
                        got = list(fn(unit, as_of=as_of))
                    rows = len({f["assertion"].get("claim_id") for f in got
                                if f["frame_type"].endswith("claim_proposed/v1")})
                else:
                    got, rows = [], 0
                    for native in getattr(mod, src.natives)(unit):
                        if remaining is not None and rows >= remaining:
                            break
                        project = (src.selector(mod, native) if src.selector
                                   else getattr(mod, src.project))
                        got.extend(to_frames(project(native), as_of=as_of,
                                             adapter_id=adapter_id, authority=authority))
                        rows += 1
            except ProjectionError as exc:
                report["refused"].append({"unit": str(unit), "reason": str(exc)})
                continue
            if not got:
                report["declined"].append(str(unit))
                continue
            frames.extend(got)
            report["units_projected"] += 1
            report["rows_projected"] += rows

    if not dry_run:
        for frame in frames:
            ledger.append(frame)
    report["frames_emitted"] = len(frames)
    return report


def human(report: dict) -> str:
    lines = [
        f"{report['source']} ({report['adapter']}): units matched={report['units_matched']}  "
        f"projected={report['units_projected']}  declined={len(report['declined'])}  "
        f"refused={len(report['refused'])}  rows={report['rows_projected']}  "
        f"frames={'(dry run) ' if report['dry_run'] else ''}{report['frames_emitted']}",
    ]
    if report["missing"]:
        lines.append(f"missing (no such path): {', '.join(report['missing'])}")
    if report["refused"]:
        lines.append("refused (strict reader: the record does not re-derive):")
        lines.extend(f"  {r['unit']}: {r['reason'][:110]}" for r in report["refused"][:10])
    if report["declined"]:
        lines.append("declined (accepted, projected nothing: pre-hook / absent / void):")
        lines.extend(f"  {u}" for u in report["declined"][:10])
    return "\n".join(lines)


__all__ = ["SOURCES", "UNWIRED", "Source", "ingest", "human"]
