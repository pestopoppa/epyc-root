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
from adapters._llama_bench_protocol import refusal_code  # noqa: E402

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


def _files_except(exclude_suffix: str, *patterns: str) -> Units:
    """Like ``_files``, but a directory walk skips names ending in ``exclude_suffix``.

    For two sources that share one directory and must never read each other's sidecars (the
    offline recall and speed instruments). An explicitly named file is always its own unit, so the
    wrong source meets it and refuses it by name instead of never seeing it.
    """
    inner = _files(*patterns)

    def units(path: Path) -> list[Path]:
        found = inner(path)
        return found if path.is_file() else [p for p in found if not p.name.endswith(exclude_suffix)]
    return units


def _pb_hol_units(path: Path) -> list[Path]:
    return importlib.import_module("adapters.pb_hol").units(path)


def _run_dirs(marker: str) -> Units:
    """A directory holding ``marker`` is one run; otherwise its children that hold it are."""
    def units(path: Path) -> list[Path]:
        if not path.is_dir():
            return []
        if (path / marker).is_file():
            return [path]
        return sorted(p for p in path.iterdir() if p.is_dir() and (p / marker).is_file())
    return units


def _run_dirs_any(*markers: str, sidecar: str | None = None) -> Units:
    """Like ``_run_dirs``, but a directory is a run when it holds ANY of ``markers`` (one source, two layouts).

    ``sidecar`` names a producer-written file that is its own unit when passed as ``--path`` (it names its run dir)."""
    def held(p: Path) -> bool:
        return any((p / m).is_file() for m in markers)

    def units(path: Path) -> list[Path]:
        if sidecar and path.is_file() and path.name.endswith(sidecar):
            return [path]
        if not path.is_dir():
            return []
        if held(path):
            return [path]
        return sorted(p for p in path.iterdir() if p.is_dir() and held(p))
    return units


def _np_ctx_kvu_units(path: Path) -> list[Path]:
    """A directory holding ``summary.jsonl`` or ``requests.jsonl`` is one unit, else its children that do are; a
    named ``requests.jsonl`` file is its own unit."""
    if path.is_file():
        return [path] if path.name == "requests.jsonl" else []
    if not path.is_dir():
        return []
    held = lambda p: (p / "summary.jsonl").is_file() or (p / "requests.jsonl").is_file()  # noqa: E731
    if held(path):
        return [path]
    return sorted(p for p in path.iterdir() if p.is_dir() and held(p))


def _glob_dirs(marker: str, *patterns: str) -> Units:
    """A directory holding ``marker`` is one unit; otherwise every directory matched by ``patterns`` that holds it is."""
    def units(path: Path) -> list[Path]:
        if not path.is_dir():
            return []
        if (path / marker).is_file():
            return [path]
        found: set[Path] = set()
        for pattern in patterns:
            found.update(p.parent for p in path.glob(pattern) if p.is_file())
        return sorted(found)
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
    #: optional safe public locator for a source whose native custody is private.
    report_path: str = ""

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
    Source("ufh12-gs-coverage", "ufh12_gs_coverage", _files("*.belief_measurements.jsonl"), task="VB-UFH12-GS", note="prospective proxy-query and stored-token record coverage; explicit --path only"),
    Source("rtg57-vkq-comparison", "rtg57_vkq_comparison", _files("native-receipt.json"), task="VB-RTG57-VKQ-WIRE", note="prospective scoped T48/T96 timing; no adoption"),
    Source("rtg57-vkq-oracle", "rtg57_vkq_oracle", _files("native-receipt.json"), task="VB-RTG57-VKQ-WIRE", note="one model-free C5 numerical shape; no serving or adoption warrant"),
    Source("df2-row-exact-akx", "df2_row_exact", _files("belief-native.json", "*/belief-native.json"), task="VB-DF2-ROW-EXACT-WRITE", note="producer-time DF2 output and diagnostic observations; explicit --path only"),
    Source("hg5-request-event", "hg5_request_event", _files("*.json"),
           task="VB-HG5-TAP-READ",
           note="owned sealed completed post-answer request events only; nullable metrics decline; no default/runtime/correctness"),
    Source("graph-profiler-measurement", "graph_profile_measurement", _files("*.json"),
           natives="native_rows_file", task="SC55-READ",
           note="explicit SC55 closed capture envelope; no historical backfill or default corpus"),
    Source("dtap-timeout-report", "dtap_timeout_report", _files("receipt.json"),
           project="project_dtap_timeout_report", task="VB-DTAP-TIMEOUT-REPORT-WIRE",
           report_path="public_locator",
           note="explicit private original timeout-component integrity receipt; no default/body export"),
    Source("pii-staged-gate", "pii_staged_gate", _files("receipt.json"),
           task="VB-PII-STAGED-WIRE",
           note="explicit private original PII sub-gate receipt only; no default or public body export"),
    Source("qwen4exp-quality-measurement", "qwen4exp_quality", _files("*.quality.json", "**/*.quality.json"),
           note="prospective immutable SC54 llama-perplexity PPL/PPL-anchor/KLD receipts only; historical B7/C9 records are never backfilled",
           task="SC54-WRITE / SC54-READ"),
    Source("evidence-durability", "evidence_durability", _files("*.json"),
           default=Path("/workspace/repos/epyc-inference-research/logs/evidence_durability_scan.json.d"),
           note="prospective immutable citation durability receipts; qualified caveats yield no boolean",
           task="VB-NI-DURABILITY"),
    Source("ci-fixture-conformance", "ci_conformance", _files("receipt.json", "**/receipt.json"),
           project="project_ci_conformance", task="VB-CI-CONFORMANCE",
           note="prospective selected fixture execution receipts; diagnostics emit zero rows; no default"),
    Source("distillation-pool", "distillation_pool", _files("*.json"),
           task="VB-M26-DISTILL-POOL-WRITE",
           note="prospective selected-memory integrity receipts only; synthetic/mock receipts decline; no historical reconstruction"),
    Source("odl-unlimited-ocr-run", "odl_model_gated",
           _files("vidya_measurement_record.json", "*/vidya_measurement_record.json",
                  "**/vidya_measurement_record.json"),
           project="project_unlimited_ocr_run", task="SC42 / VB-ODL-P2",
           note="prospective run-time Unlimited-OCR records only; old demo JSON is identityless and is never upgraded"),
    Source("managed-tooling-check", "managed_tooling_check",
           _files("receipt.json", "*/receipt.json", "**/receipt.json"),
           project="project_managed_tooling_check", task="VB-MANAGED-TOOLING-WIRE",
           note="prospective named managed-interpreter pytest import checks; diagnostic/null captures decline; no default"),
    Source("contextbench-discovery-score", "contextbench_score", _run_dirs("receipt.json"),
           report_path="public_locator",
           note="prospective private ContextBench score integrity receipts; metric components are descriptive and unprojected; no default",
           task="VB-CONTEXTBENCH-SCORE-WIRE"),
    Source("strategy-projection-report", "strategy_projection_report",
           _run_dirs("receipt.json"), project="project_strategy_projection_report",
           report_path="public_locator",
           note="prospective private original StrategyStore report boolean only; declared input identities are hash-only and counts are descriptive",
           task="VB-AP-STRATEGY-PROJECTION-REPORT-WIRE"),
    Source("session-intercall-gap", "session_intercall_gap", _files("session-gap-pairs.jsonl"),
           note="prospective timestamp-pair integrity observations; exact enqueue and staging proxies stay separate",
           task="VB-GAP-DIST / HSF-3"),
    Source("orchestrator-serving-call", "serving_call", _files("serving_calls.jsonl*"),
           default=ORCHESTRATOR / "logs" / "serving_calls",
           note="native self-hashed per-call serving timings; absent-timing rows emit no claims; "
                "judge joins retain one row per attempt; no window aggregates",
           task="VB-SERVE-TIMING-1"),
    Source("exl3-measurement", "exl3", _files("*.measurement.json"),
           natives="measurement_rows", project="project_measurement",
           note="prospective self-hashed EXL3 measurement receipts", task="VB-EXL3-CPU-GFX90A"),
    Source("exl3-verifier", "exl3", _files("*.verifier.json"),
           natives="verifier_rows", project="project_verifier",
           note="prospective exact-proposition EXL3 verifier receipts", task="VB-EXL3-CPU-GFX90A"),
    Source("research-screen", "research_screen", _files("*.research-screen.json", "**/*.research-screen.json"),
           note="producer-sealed shared screen receipts: selector_replay or typed_decision_shadow",
           task="VB-RI-SCREEN-1 / VB-DGM-1 / VB-TDP-EXT"),
    Source("s4-omega-ab", "s4_omega_ab", _files("*.manifest.json", "**/*.manifest.json"),
           note="prospective S4 Omega frontdoor:repl per-question native observations; checks run/recovery custody and suite/prompt/request joins; no synthetic rows, paired delta, protocol or promotion claim",
           task="VB-S4-OMEGA-WIRE"),
    Source("kv-quant-27b-v10-measurement", "kv_quant_27b_v10",
           _files("belief_measurements.jsonl", "*/belief_measurements.jsonl",
                  "*/*/belief_measurements.jsonl"),
           default=Path("/workspace/repos/epyc-inference-research/data/gpu-mi210/kv-quant-27b-v10-sweep"),
           note="v10 MI210 KV-quant sweep sidecars; pre-hook/failed runs yield no claims",
           task="VB-KVQ-V10"),
    Source("kv-quant-27b-v10-retrofit", "kv_quant_27b_v10",
           _glob_dirs("identities.json", "*/identities.json", "*/*/identities.json"),
           natives="retrofit_rows", project="project_retrofit",
           default=Path("/workspace/repos/epyc-inference-research/data/gpu-mi210/kv-quant-27b-v10-sweep"),
           note="2026-09-22 pre-hook v10 MI210 KV-quant sweep run dirs (`identities.json` + `runs/<cell>/result.json`); "
                "ok cells only (runs a/b are all-error and decline), re-hashed identities, N=1, empty protocol, retrofit",
           task="VB-KVQ-V10-RETRO"),
    Source("autokernel-served-shape", "autokernel_served_shape",
           _glob_dirs("manifest.json", "store/served_shape/manifest.json", "*/store/served_shape/manifest.json", "*/manifest.json"),
           selector=lambda mod, native: (mod.project_verifier if native["kind"] == "verifier"
                                         else mod.project_measurement),
           default=Path("/mnt/raid0/llm/autokernel/campaigns/ak-ds41-1017-cpu-decode-20261021/store/served_shape"),
           note="AutoKernel served-shape oracle calibration (anchor-build NMSE per shape x quant, widths 1-5) + "
                "manifest caps re-derived; one measurement and one verifier tuple per (shape, type); retrofit",
           task="VB-AK-SERVED-SHAPE"),
    Source("speech-cpu-measurement", "speech_cpu_measurement",
           _files("speech_cpu_capture.jsonl", "*/speech_cpu_capture.jsonl"),
           note="prospective CPU STT/TTS capture rows (speech_cpu_bench.py / live_llm_contention_capture.py "
                "with SPEECH_CPU_CAPTURE_DIR); 2026-09-24 raw/ rows are never backfilled; capped/aborted "
                "requests are counted, never projected; no default",
           task="VB-SPEECH-CPU-1 / VB-SPEECH-CPU-1a"),
    Source("speech-listen-rating", "speech_listen_rating", _files("*-listen-*.json"),
           natives="native_rows", default=Path(__file__).resolve().parents[2] / "artifacts/stt-cs8",
           note="human speech listen/rating aggregates (schema epyc.<item>_listen.v<N>); observation, "
                "empty protocol_id, single labelled rater; records that do not re-derive are refused",
           task="VB-SPEECH-LISTEN-1"),
    Source("ds41-1017-validation", "ds41_1017_validation",
           _files("belief_measurements.jsonl", "*/belief_measurements.jsonl"),
           note="INF-77 DS41-W5/W6 1017 MXFP4-experts validation rows; each binds the 9 shard sha256s "
                "and the drafter digest (or its null reason) at write time; no backfill",
           task="VB-DS41-1017-WIRE"),
    Source("toc-ab", "toc_ab",
           _files("toc_ab.beliefs.jsonl", "*/toc_ab.beliefs.jsonl"),
           note="tool-output-compression A/B arms from the trajectory-artifact finalize boundary; "
                "runs with no sidecar decline",
           task="VB-TOC-AB-WRITE"),
    Source("skillbank-ab", "skillbank_ab",
           _files("skillbank_ab.beliefs.jsonl", "*/skillbank_ab.beliefs.jsonl"),
           note="M-23 per role x model-pin cells, negative cells kept, no pooled row",
           task="VB-SKILLBANK-AB-WRITE"),
    Source("harness-improvement", "harness_improvement",
           _files("harness_improvement.beliefs.jsonl", "*/harness_improvement.beliefs.jsonl"),
           note="HIL feature A/B rows carrying the HIL-2 item 14 arm pins",
           task="VB-HIL-WRITE / VB-HIL-WRITE-FIELDS"),
    Source("ak-history", "ak_history",
           _files("ak_history.beliefs.jsonl", "*/ak_history.beliefs.jsonl"),
           note="AK-HR-3 prospective per-trial fields; closed stores (AK-HR-1/2) stay retrospective "
                "and emit zero tuples",
           task="VB-AK-HISTORY"),
    Source("injection-fixture", "injection_fixture",
           _files("injection_fixture.beliefs.jsonl", "*/injection_fixture.beliefs.jsonl"),
           note="CT-18 injection fixture arms; the only claim is static-attack ASR on fixture set X "
                "(fixture hash, arm, thinking, served pin), never robustness",
           task="VB-IBENCH-WRITE"),
    Source("chunk-kv", "chunk_kv",
           _files("chunk_kv.beliefs.jsonl", "*/chunk_kv.beliefs.jsonl"),
           note="KPF-60/KPF-64 prefill rate, inject latency, drift curve, realised vs ideal prefix "
                "hit, and RTE-LOG-1 reader reports; each row carries served pin + window claim",
           task="VB-KVCHUNK-WRITE"),
    Source("conversation-stack-measurement", "conversation_stack_measurement",
           _files("conversation_stack.beliefs.jsonl", "*/conversation_stack.beliefs.jsonl"),
           note="INF-79 conversation-stack harness rows (generic, STT arm/fitting/lexicon, VAD, "
                "end-of-turn, time-to-final, interruption, degraded co-residency); literature "
                "reference rows are never projected; OBSERVATION until CS-2 Annex S; no default",
           task="VB-SPEECH-CONV-1 / 1B-1E"),
    Source("speech-ggml-optest", "speech_ggml_optest",
           _files("speech_ggml_optest.beliefs.jsonl", "*/speech_ggml_optest.beliefs.jsonl"),
           note="CS-43.1 / CH-18.d test-backend-ops records (measurement class, the same ladder as "
                "the test-backend-ops property source); upstream statements stay literature; no default",
           task="VB-SPEECH-KOPT-1"),
    Source("hil15a-auc", "hil15a_auc",
           _files("auc_table.beliefs.jsonl", "*/auc_table.beliefs.jsonl"),
           note="HIL-15a flag-on dependency AUC table: per feature set and per delta (CI), edge grade "
                "observed; mock manifests refused; pre-hook tables emit nothing",
           task="VB-HIL15A-WRITE"),
    Source("hil17-attribution-ladder", "hil17_attribution",
           _files("hil17_attribution.beliefs.jsonl", "*/hil17_attribution.beliefs.jsonl"),
           note="HIL-17 attribution-ladder per-rung accuracy/token table and aggregated nDCG@5 arms, "
                "OBSERVATION only; mock, unlabelled and undigested reports refused",
           task="VB-HIL17-WRITE"),
    Source("hil-lb1-loop-score", "hil_lb1_loop_score",
           _files("hil_lb1_loop_score.beliefs.jsonl", "*/hil_lb1_loop_score.beliefs.jsonl"),
           note="HIL-LB1 loop-detector scores on the Who&When Pro labelled loop set (injected "
                "behaviour, not natural frequency), OBSERVATION only; unlabelled firing counts "
                "are not projected",
           task="VB-HILLB1-WRITE"),
    Source("repl-preview", "repl_preview",
           _files("repl_preview.beliefs.jsonl", "*/repl_preview.beliefs.jsonl"),
           note="D-RI-PREVIEW-1 per role x rendering correct-rate with class counts; mock and partial "
                "results refused",
           task="VB-DRIPREVIEW-WRITE"),
    Source("kv-prefix-fork", "kv_prefix_fork",
           _files("belief_measurements.jsonl", "*/belief_measurements.jsonl",
                  "*/*/belief_measurements.jsonl"),
           note="KPF-18 runner `epyc.kpf.run.v1` records (kpf18_gate.py Run.finish); pre-hook runs yield no claims",
           task="VB-KVU-PF"),
    Source("pb-hol", "pb_hol", _pb_hol_units,
           note="PB-HOL-1 slot-order head-of-line run dirs (`summary.json` + `pb_hol_1.jsonl`, research "
                "`scripts/benchmark/pb_hol_1`); one claim per arm comparison with samples; retrofit",
           task="P1-L"),
    Source("embedder-placement-gate", "embedder_placement_gate",
           _files("*.belief_measurements.jsonl"),
           default=ORCHESTRATOR / "data/embedder_placement",
           note="UFH-12 placement gate sidecars (`<record>.belief_measurements.jsonl`); the "
                "2026-09-26 Phase-0 records have none and yield no claims",
           task="VB-UFH12-PLACEMENT"),
    Source("ufh12-irt-paired", "ufh12_irt_paired", _files("*.belief_measurements.jsonl"), task="VB-UFH12-IRT-PAIRED-WRITE", note="prospective paired held-out IRT correlations; explicit --path only"),
    Source("repl-retrieval-eval", "repl_retrieval_eval",
           _files_except(".speed.belief_measurements.jsonl", "*.belief_measurements.jsonl",
                         "*/*.belief_measurements.jsonl"),
           default=ORCHESTRATOR / "data/repl_retrieval_eval",
           note="UFH-12 offline retrieval eval sidecars (`<run_id>.belief_measurements.jsonl`, instrument "
                "offline_recall, written by `RetrievalRun.finalize()`); speed sidecars in the same "
                "directory are not read here, and an explicit one is refused by name",
           task="VB-UFH12-RETR"),
    Source("repl-embedder-speed", "repl_retrieval_eval",
           _files("*.speed.belief_measurements.jsonl", "*/*.speed.belief_measurements.jsonl"),
           natives="speed_native_rows", project="project_speed",
           default=ORCHESTRATOR / "data/repl_retrieval_eval",
           note="UFH-12 embedder speed-block sidecars (`<run_id>.speed.belief_measurements.jsonl`, "
                "instrument offline_speed, written by `SpeedRun.finalize()`); every row carries its "
                "timing context and its A/A noise floor",
           task="VB-UFH12-EMBSPEED"),
    Source("gfx90a-static-register", "gfx90a_static_register",
           _files("audit_*.json", "audit_*.json.gz", "*isa_audit*.json", "*isa_audit*.json.gz"),
           note="gfx90a static register/ISA audits (research `gfx90a_isa_audit.py audit --json`, "
                "schema epyc.gfx90a.isa_audit.v1); pre-hook audits (no `category`, e.g. research "
                "data/gfx90a-isa-audit-20260926) yield no claims; no default, pass --path",
           task="SC84 / SC84a (VB-VGPR-STATIC)"),
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
    Source("hs-prof1-profile-arms", "hs_prof1_profile_arms",
           _files("hs_prof1_profile_arms.beliefs.jsonl", "*/hs_prof1_profile_arms.beliefs.jsonl"),
           note="HS-PROF-1 BEAM profile-arm table (research `hs_prof1_profile_arms.py table "
                "--belief-measurements`): per ability x arm judge-scored means plus paired "
                "deltas; judge identity is part of every claim; pre-hook tables decline",
           task="VB-HSPROF1-WRITE"),
    Source("rus2-probe", "rus2_probe",
           _files("rus2_probe.beliefs.jsonl", "*/rus2_probe.beliefs.jsonl"),
           note="RUS-2 trace-length probe cells, OBSERVATION only (temperature and finish_reason "
                "absent at source)",
           task="VB-RUS2-PROBE-WIRE"),
    Source("gpu-leak-probe", "gpu_leak_probe",
           _files("gpu_leak_probe.beliefs.jsonl", "*/gpu_leak_probe.beliefs.jsonl"),
           note="GPU-LEAK-1/1d own-PID VRAM slope per arm (slopes re-derived from the recorded series), "
                "OBSERVATION only; producer verdict carried verbatim",
           task="VB-GPU-LEAK-WRITE"),
    Source("v11-oracle-rerun", "v11_oracle_rerun",
           _files("v11_oracle_rerun.beliefs.jsonl", "*/v11_oracle_rerun.beliefs.jsonl"),
           note="V11-086 FP32-oracle rerun pass fraction per arm (value = passed/total of the same row), scorer "
                "clause verdicts verbatim, OBSERVATION only",
           task="VB-V11-ORACLE-WRITE"),
    Source("repl-embedder-parity", "repl_embedder_parity",
           _files("repl_embedder_parity.beliefs.jsonl", "*/repl_embedder_parity.beliefs.jsonl"),
           note="EmbeddingGemma-2 vector-parity gate (REPL-EMB-2.5/2.6): per gated lane cos_min / cos_mean / "
                "non-finite count re-derived from the recorded per-item cosines, gate verdict re-derived, "
                "OBSERVATION only; vector parity, no recall or speed claim; 2026-10-20 results stay retrospective",
           task="VB-UFH12-PARITY"),
    Source("akx-lb32", "akx_lb32",
           _files("akx_lb32.beliefs.jsonl", "*/akx_lb32.beliefs.jsonl"),
           note="AKX-ALL-LB3.2 Q38FN attribution run: FA node-wall share F(N) of the 64k step per (threads, N) and the "
                "predeclared verdict/seed class, re-derived from the row's own F / max F / max S; VERDICT.json and the "
                "frozen PREDECLARATION are attested; INVALID never projects; OBSERVATION only",
           task="VB-AKX-LB32-WRITE"),
    Source("ds41-w5d", "ds41_w5d",
           _files("ds41_w5d.beliefs.jsonl", "*/ds41_w5d.beliefs.jsonl"),
           note="DS41-W5d 1017 llama-bench baseline + MUL_MAT_ID pp512 ratio, re-derived from the recorded "
                "values; VOID/INCOMPLETE halves project nothing",
           task="VB-DS41-W5D-WRITE"),
    Source("q38-serving-gate", "q38_serving_gate",
           _files("q38_serving_gate.beliefs.jsonl", "*/q38_serving_gate.beliefs.jsonl"),
           note="Q38-T10.1 serving-gate phase run: net-paired R/G/exact p, token-identical fraction, concordance "
                "re-derived from the recorded per-prompt payload; A/A 80/80 and guards are preconditions; "
                "truncated prompts listed and excluded; OBSERVATION only",
           task="VB-Q38-T10-1-GATE-WIRE"),
    Source("clbench-cache-hit", "clbench_cache_hit",
           _files("clbench_cache_hit.beliefs.jsonl", "*/clbench_cache_hit.beliefs.jsonl"),
           note="CL-Bench prefix-cache hit report: prompt_prefix and cme5 hit ratios plus the three missed_split "
                "buckets, re-derived from the recorded counts; pre-08ace05fd reports project nothing",
           task="VB-CLBENCH-CACHE-WIRE"),
    Source("cme7t-response", "cme7t_response", _run_dirs("RUN_RECORD.json"),
           note="CME-7T sealed native response/hand records; closed artifact seal and native journal accounting "
                "are re-verified; hand profits are diagnostic observations only, no efficacy/adoption claim",
           task="VB-CME7T-RESPONSE-WIRE"),
    Source("spec-rng-1-2", "spec_rng_1_2", _run_dirs("VERDICT.json"),
           note="SPEC-RNG.1.2 poskey depth-invariance launcher dirs (`VERDICT.json` + `out/records.jsonl` + "
                "`out/verdict.json`); chi-square/acceptance re-derived from the request rows, INDICATIVE "
                "correctness only, no throughput value; retrofit",
           task="VB-SPEC-RNG-1-2-WIRE"),
    Source("np-ctx-kvu-measurement", "np_ctx_kvu", _np_ctx_kvu_units,
           note="np x ctx x KV-mode capture rows (`epyc.vidya.np_ctx_kvu_capture.v1`): CELL shape = launch dir with "
                "`summary.jsonl` + `<launch>/<cell>/waves_capture.jsonl` (medians re-derived from the wave rows), "
                "REQUEST shape = `requests.jsonl`; HTTP errors stay in the denominator; pre-hook rows refuse; "
                "`cells.jsonl` decision rows are not read",
           task="VB-KVU-CPU"),
    Source("ufh14-lb7-stall", "ufh14_lb7_stall", _run_dirs("VERDICT.json"),
           note="UFH14-LB7 cache-idle-slots stall attribution launcher dirs (`VERDICT.json` + `out/*.attrib.json`); "
                "per-session turn-2+ summaries and the verdict re-derived from the attrib rows, harness-local "
                "PREDECLARATION.md sha256 in extra (protocol_id empty); INCOMPLETE / INSTRUMENT_FAIL decline; retrofit",
           task="VB-LB7-STALL-WIRE"),
    Source("pb-qcost", "pb_qcost", _run_dirs_any("pb_qcost_1.jsonl", "out/run/pb_qcost_1.jsonl",
                                                 sidecar="belief_measurements.jsonl"),
           note="PB-QCOST-1 prefill-cost run dirs (original `summary.json` layout and the confirm launcher "
                "`VERDICT.json` layout) or their research-emitted `belief_measurements.jsonl` (cross-verified row for "
                "row against the reader's own refit); grade and single-q caveat in applicability; OBSERVATION only",
           task="VB-PBQ-1"),
    Source("ch19-t3-screen", "ch19_t3_screen", _run_dirs("records.jsonl"),
           note="CH-19.2 T3 fused MoE up+gate speed-screen dirs (`records.jsonl` + `provenance.json` + `summary.txt`); "
                "per-test ON/OFF ratio and per-arm medians re-derived from the rows, same-window A/A-like noise floor "
                "carried or absent; INVALID results stay valueless rows; llama-bench protocol assessed; OBSERVATION; "
                "retrofit",
           task="VB-CH19-T3-SCREEN-WIRE"),
    Source("ev19-gold-selfcheck", "ev19_gold_selfcheck",
           _files("ev19_gold_selfcheck.beliefs.jsonl", "*/ev19_gold_selfcheck.beliefs.jsonl"),
           note="EV-19 scorer/pool gold self-check per suite; scorer validity, never a model; "
                "sampled runs never gating",
           task="VB-EV19-GOLD-SELFCHECK-WIRE"),
    Source("oolong", "oolong", _files("oolong.beliefs.jsonl", "*/oolong.beliefs.jsonl"),
           note="Oolong per (arm, family, context length) cells, context-clustered; labels_given "
                "records excluded", task="VB-OOLONG-WIRE"),
    Source("yarn-gate-agg", "yarn_gate_agg",
           _files("yarn_gate_agg.beliefs.jsonl", "*/yarn_gate_agg.beliefs.jsonl"),
           note="YaRN gate cells and noninferiority verdicts carrying judge pin, real prompt_n bin "
                "and zone; fixture rows invisible", task="VB-YARN-AGG-1"),
    Source("nemotron-bolt-fold", "nemotron_bolt_fold",
           _files("nemotron_bolt_fold.beliefs.jsonl", "*/nemotron_bolt_fold.beliefs.jsonl"),
           note="Nemotron 3.5 Bolt pending-fold records (build 59c1b915f on champion dd3d9721c): INDICATIVE MI210 speed "
                "(no floor, never gating), coherence + VRAM/KFD residency, Qwen3.6 greedy byte identity, "
                "test-backend-ops pass/total; every value re-derived from the row's recorded counts",
           task="VB-NEMOTRON-BOLT-FOLD-WIRE"),
    Source("tulving", "tulving_episodic", _files("belief_measurements.jsonl",
                                                 "*/belief_measurements.jsonl"), task="SC67"),
    Source("chat-template-ab", "chat_template_ab",
           _files("belief_measurements.jsonl", "*/belief_measurements.jsonl"), task="SC46"),
    Source("occ1", "occ1_optical_compression",
           _files("belief_measurements.jsonl", "*/belief_measurements.jsonl"),
           note="OCC-1 run dirs (`run_occ1.py report` sidecars); VOID/pre-hook runs decline",
           task="SC85"),
    Source("ak-width-dimension", "autokernel_width_dimension",
           _files("width_dimension.json", "*/width_dimension.json"),
           note="AKX-ALL-27 HIP width-invariance dimension records (`width_dimension.json` beside "
                "DECISION.json and parent/ + keep/ cells.jsonl); the comparison is re-derived from "
                "both cell tables and refused if it differs; CPU half is `ak-width-cells-cpu`",
           task="VB-AKX-ALL-26-CELLS-WIRE / VB-AKRSG-INGEST"),
    Source("ak-width-cells-cpu", "autokernel_width_cells_cpu",
           _files("cells.jsonl.gz", "*/cells.jsonl.gz"),
           default=Path("/mnt/raid0/llm/epyc-inference-research/artifacts/akx_all_26_cpu_20261020"),
           note="AKX-ALL-26 CPU width-invariance cell table (`cells.jsonl.gz`, schema "
                "`akx-all-26.cell.v1`, beside group_headers.jsonl, summary.json, ADDENDUM.sha256); "
                "every verdict, A/A flag, control pattern and summary count is re-derived from the "
                "rep digests and refused if it differs; two count tuples per (route, nth)",
           task="VB-AKX-ALL-26-CELLS-WIRE"),
    Source("gpu-cpu-noise", "gpu_cpu_noise", _run_dirs("RUN_RECORD.json"),
           default=Path("/mnt/raid0/llm/tmp/gpu-cpu-noise-20261021/runs"),
           note="U4-NOISE-1 session dirs (RUN_RECORD.json, schedule.json, reps.jsonl, END.json, "
                "ANALYSIS.json); prereg + schedule + every rep row re-hashed and every deterministic "
                "bias / variance-ratio / sigma_add re-derived from the rows; aborted, dry and "
                "unanalysed sessions decline; bootstrap CIs and verdicts carried verbatim",
           task="VB-GPU-CPU-NOISE-WIRE"),
    Source("moe-routing", "moe_routing",
           _files("moe_routing.beliefs.jsonl", "*/moe_routing.beliefs.jsonl"),
           note="INF-72 RT-1 routing-trace analyses (skew / residency h(k) / placement replay / locality), scope re-derived "
                "from the row's recorded input_traces (model file, arch, corpus sha256, phase, chunk size, calibration, n); "
                "unstamped analyses, unverified shards and guard-less traces project nothing; stride-hazard refused; "
                "diagnostic OBSERVATION, no throughput claim",
           task="VB-MOE-ROUTING-WIRE"),
    Source("launch-affinity", "launch_affinity",
           lambda p: importlib.import_module("adapters.launch_affinity").units(p),
           note="per-pid per-moment task-mask readings: epyc.launch_affinity.reading.v1 JSONL "
                "(orch launch_affinity.py --record, serving_gate affinity_readings.jsonl; strict "
                "self-hash + re-derived escapes) and the pre-hook diag/probe task dumps "
                "(retrofit, no binary sha256); a reading with no readable task declines",
           task="VB-LAUNCH-AFFINITY-WIRE"),
    Source("fused-decode-div", "fused_decode_div",
           lambda p: importlib.import_module("adapters.fused_decode_div").units(p),
           note="FD-DIV-1a epyc.fd_div_1a.smoke_receipt.v1 (one claim per decided smoke, byte identity "
                "test vs ref re-derived; the v10 fused-ON abort rides as S1's defect control) and "
                "FD-DIV-1b epyc.fd_div_1b.result.v1 (one claim per fixture cell, class re-derived); "
                "skipped smokes and void controls decline; decode ms/token is observation only",
           task="VB-FUSED-DECODE-DIV-WIRE"),
    Source("m4-cpu-recipe-speed", "m4_cpu_speed", _files("**/process-captures/*.json"),
           note="prospective M4 process captures only, source-sealed and partial-safe",
           task="VB-M4-FOLD-SPEED-WRITE"),
    Source("champion-fold-gate", "champion_fold_gate",
           lambda p: importlib.import_module("adapters.champion_fold_gate").units(p),
           note="fold_gate.v4 epyc.champion_fold_gate.v1 records: one strict verifier projection per library plus "
                "each EXPLAINED-UI policy exception; gate verdict, code-identity flags, propositions and store "
                "SHA256SUMS attestations are re-derived; text-only legacy output and pre-hook folds decline",
           task="VB-FOLDGATE-WRITE"),
    Source("hsf5p-microbench", "hsf5p_microbench",
           lambda p: importlib.import_module("adapters.hsf5p_microbench").units(p),
           default=Path("/mnt/raid0/llm/tmp/f8-launchers-20261024/hsf-5p"),
           note="HSF-5.P host KV mirror acceptance microbench (hsf5p.beliefs.jsonl beside VERDICT.json, "
                "epyc.hsf5p.microbench.row.v1): copy medians re-derived from bench12.jsonl, G1-G4 from arms.jsonl "
                "and the server logs, every input re-hashed; an INCONCLUSIVE run writes no rows",
           task="VB-HSF5P-WRITE"),
    Source("calendar-overrun", "calendar_overrun",
           lambda p: importlib.import_module("adapters.calendar_overrun").units(p),
           note="compute-calendar grants/<id>.ended with appended key=value lines (estimated_wall_s, actual_wall_s|started, job_id, owner, step, regions, co_residents, np, ctx); ratio actual/estimated re-derived, hard-end rc 124/125/143 marked censored; legacy .ended with no estimate declines",
           task="VB-CAL-OVERRUN-WIRE"),
    Source("floor-registry", "floor_registry",
           lambda p: importlib.import_module("adapters.floor_registry").units(p),
           note="serving_floors: section of the research MASTER model_registry.yaml (one BASELINE per entry: "
                "v1 reuses autokernel_serving_floor, v2 value=floor_pct reps=n unit=process; sealed "
                "record_sha256 re-derived, mismatch refuses; claim_class=indicative refused as "
                "decision-gating)",
           task="VB-FLOOR-REGISTRY-WIRE"),
    Source("weight-handoff", "weight_handoff", _files("*.weight-handoff.json", "**/*.weight-handoff.json"),
           task="VB-NEW13-WIRE",
           note="prospective captured llama-weight-handoff receipts only; per-arm KLD, R with paired-bootstrap CI and Gate 0 re-derived from kld.jsonl; NEW-13 v0 receipt never backfilled"),
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
    Source("verify-before-stop-measurement", "verify_before_stop",
           _files("mf_vbs1_verify_before_stop_result.json"),
           default=ORCHESTRATOR / "data" / "analysis" / "mf_vbs1_verify_before_stop_result.json",
           note="only report-v2 producer/input-bound native output is projected; legacy identity-free JSON is refused",
           task="VB-MFVBS-1"),
    Source("eval-suite-discriminability", "eval_suite_discriminability",
           _files("report.json", "**/report.json"),
           default=ORCHESTRATOR / "orchestration" / "reports" / "eval_suite_discriminability",
           note="only report-v2 producer/input-bound OBSERVATION is projected; legacy identity-free JSON is refused",
           task="VB-EVALDISC-1"),
    Source("ufh13-thesis-measurement", "ufh13_thesis",
           _files("belief_measurements.jsonl", "*/belief_measurements.jsonl"),
           note="UFH-13 scored-run sidecars only; no default path, pilot manifest refused",
           task="VB-THESIS-2"),
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


def _only_new_frames(ledger, frames: list[dict], *, as_of: str) -> list[dict]:
    """Filter complete bundles using the fold's surviving evidence, never grades.

    The ledger remains single-writer (§11.0). Partial bundles are refused rather
    than interpreted as unobserved claims. A historical bundle with no surviving
    evidence is also refused: automatic retries cannot revive withdrawn evidence.
    """
    from fold import FT_CLAIM, FT_SOURCE, FT_SUPPORT, FT_OPPOSE, FoldError, fold
    from ledger import LedgerIntegrityError

    repairs: list[str] = []
    try:
        records = ledger.read_all(repair_report=repairs)
    except LedgerIntegrityError as exc:
        raise ValueError(f"--only-new refuses an invalid ledger: {exc}") from exc
    if repairs:
        raise ValueError("--only-new refuses a torn ledger tail: " + "; ".join(repairs))
    if records:
        problems = ledger.verify()
        if problems:
            raise ValueError("--only-new refuses an invalid ledger: " + "; ".join(problems))
    existing = [record.frame for record in records]
    try:
        result = fold(existing, as_of=as_of)
    except FoldError as exc:
        raise ValueError(f"--only-new refuses an invalid ledger fold: {exc}") from exc
    live = {cid for cid, belief in result.beliefs.items()
            if belief.pro_paths or belief.con_paths}
    sources = {f["assertion"].get("source_id") for f in existing
               if f.get("frame_type") == FT_SOURCE}
    claims = {f["assertion"].get("claim_id") for f in existing
              if f.get("frame_type") == FT_CLAIM}
    evidence = {f["assertion"].get("claim_id") for f in existing
                if f.get("frame_type") in (FT_SUPPORT, FT_OPPOSE)}
    incoming = {f["assertion"]["claim_id"]: f["assertion"].get("source_id")
                for f in frames if f["frame_type"] == FT_CLAIM}
    projected_sources = {f["assertion"].get("source_id") for f in frames
                         if f["frame_type"] == FT_SOURCE}
    projected_evidence = {f["assertion"].get("claim_id") for f in frames
                          if f["frame_type"] in (FT_SUPPORT, FT_OPPOSE)}
    if projected_evidence - incoming.keys():
        raise ValueError("--only-new refuses projected evidence without a claim")
    for cid, sid in incoming.items():
        if sid not in projected_sources or cid not in projected_evidence:
            raise ValueError(f"--only-new refuses partial projected bundle for {cid}")
        present = (sid in sources, cid in claims, cid in evidence)
        if any(present) and not all(present):
            raise ValueError(f"--only-new refuses partial ledger state for {cid}")
        if all(present) and result.alias_map.get(cid, cid) not in live:
            raise ValueError(f"--only-new refuses historical claim {cid} with no live evidence; "
                             "reconcile explicitly before ingesting again")

    keep_claims = {cid for cid in incoming
                   if result.alias_map.get(cid, cid) not in live}
    keep_sources = {incoming[cid] for cid in keep_claims}
    emitted: dict[tuple[str, str], dict] = {}
    kept = []
    for frame in frames:
        ftype, assertion = frame["frame_type"], frame["assertion"]
        if ftype == FT_SOURCE:
            ident = assertion.get("source_id")
            keep = ident in keep_sources
        elif ftype in (FT_CLAIM, FT_SUPPORT, FT_OPPOSE):
            ident = assertion.get("claim_id")
            keep = ident in keep_claims
        else:
            raise ValueError(f"--only-new cannot filter frame type {ftype!r}")
        key = (ftype, ident)
        if keep:
            # Repeated paths may project the same bundle twice. Divergent native
            # records under one identity are not duplicates and must not merge.
            payload = {k: v for k, v in frame.items() if k != "frame_id"}
            payload["pubinfo"] = {k: v for k, v in frame.get("pubinfo", {}).items()
                                  if k != "created_at"}
            if key in emitted and emitted[key] != payload:
                raise ValueError(f"--only-new refuses conflicting projected frames for {ident}")
            if key not in emitted:
                emitted[key] = payload
                kept.append(frame)
    return kept


def ingest(ledger, name: str, paths: Iterable[Path] | None, *, as_of: str,
           limit: int | None = None, dry_run: bool = False, only_new: bool = False) -> dict:
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
    report_path = getattr(mod, src.report_path) if src.report_path else str
    report: dict[str, Any] = {
        "source": name, "adapter": f"adapters/{src.module}.py", "adapter_id": adapter_id,
        "paths": [report_path(r) for r in roots], "units_matched": 0, "units_projected": 0,
        "declined": [], "refused": [], "missing": [], "rows_projected": 0,
        "frames_emitted": 0, "dry_run": dry_run,
    }
    for root in roots:
        if not root.exists():
            report["missing"].append(report_path(root))
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
                report["refused"].append({"unit": report_path(unit), "reason": str(exc)})
                _code = refusal_code(str(exc))
                if _code:
                    by_code = report.setdefault("llama_bench_protocol_refused", {})
                    by_code[_code] = by_code.get(_code, 0) + 1
                continue
            if not got:
                report["declined"].append(report_path(unit))
                continue
            frames.extend(got)
            report["units_projected"] += 1
            report["rows_projected"] += rows

    if only_new:
        projected_count = len(frames)
        frames = _only_new_frames(ledger, frames, as_of=as_of)
        report["only_new"] = True
        report["frames_skipped"] = projected_count - len(frames)
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
    if report.get("only_new"):
        lines.append(f"only-new: skipped {report['frames_skipped']} frames")
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
