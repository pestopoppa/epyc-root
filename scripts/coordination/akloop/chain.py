#!/usr/bin/env python3
"""chain.py -- AutoKernel parallel-loop P2: row-chain scaffolder + successor emitter (NEVER publishes).

One CANDIDATE RECORD (base sha, patch sha, hypothesis id, predicted effect) becomes a chain of five epyc.row.v3
row dirs, each scaffolded by row_scaffold.py and linted by row_scaffold.lint + publish_row.lint (a dry run):

    build  ->  oracle-kld  ->  op-perf  ->  ab-timing  ->  fold-check

(the order of research stage_bodies.STAGES; op-perf is a SCREEN, never a polar PASS: RSL-R3).

Every spec carries `lineage=<candidate id>`, `supersedes` (the prior attempt of the same stage, or null), a
`gate` list naming the previous stage's box (also rendered as the box's `· gate:` field, which index_state.py
resolves), the P1 gate ids its verdict is decided by (`gate_ids`, gate_eval.py), and an estimate from
estimate_history.py over the AK rows of the same stage class (p75 wall x 1.25).

Region shapes (keeper packing rules, inference-backlog-scheduling skill):
    build       cpu lane, ONE quarter (any-of q0,q1,q2) (never q3: 88-95 are the MI210 host threads a GPU timing row holds)
    oracle-kld  gpu lane, mi210_0 + host threads 184-191, not a timing row (quiet-only on the timing cores)
    op-perf     gpu timing row like ab-timing (GPU path): shape gpu-q3, admission block-timing-quiet
    ab-timing   gpu timing row: shape gpu-q3 (mi210_0, 88-95 held, 184-191), admission block-timing-quiet
    fold-check  gpu timing row like ab-timing, resumable (per-step checkpoints)
    serving-screen  OPTIONAL, only for a candidate of kind "serving-knob" (a served-recipe delta, no source change): the
                served path's lane (gpu: mi210_0 + 184-191; cpu: whole host). SCREEN ONLY (AK-SURFACE-SERVING-1): polar FAIL
                or FUTILITY_SCREEN_ONLY_NO_KEEP, never a polar PASS; never a fold input. Its chain is that one stage.
PATH STAGES (oracle-kld, op-perf, ab-timing, serving-screen) follow the candidate's `serving_path` ("model|device", default 27b-q8_0|mi210,
research stage_bodies.DEFAULT_PATH). A `|cpu` path (q38fn-ud-iq4xs-cpu|cpu, a3b-q8_0-cpu|cpu) runs them on the CPU
lane as a WHOLE-HOST QUIET row (oracle-kld too, so the path's own CPU KLD clauses can run), never the gpu-q3 shape: Q38FN is one NUMA_FULL instance and A3B two concurrent
NUMA-half instances, both spanning all 96 physical cores (research cpu_timing_runner reads the instance list from the
registry + stack_numa). Shape copied from the published ak-{q38fn,a3b}-cpu-aa-floor / ak-opperf-cal-q38fn-cpu rows:
regions q0,q1,q2,q3, claim_cpus "any-of q0,q1,q2", shape host, declared_threads 96, requires_quiet_host, role bench.
`resumable` is true where a window end can continue from a checkpoint (incremental build, chunked KLD, per-step
fold check) and false for the A/B timing window, which must be one quiet grant.

Stage driver (AKPL-P3): each job.py runs research `autokernel.loop.stage_bodies` for its stage, pinned to a research
commit (`git archive`, never the clone's tree), with the RESULT paths of its upstream stage rows; it always leaves a
finished polar RESULT (or FUTILITY_HARNESS_*). A candidate record's `stages` narrows the chain (a rebase-and-recheck
chain: build + oracle-kld [+ ab-timing when the measured path moved] + fold-check).

Successor emitter: when a cap or rule changes, `successor()` copies a scaffolded row dir to `<id>-r<N+1>`, sets
`supersedes=<prior id>`, cites the prior row's evidence (filed verdict / RESULT path) in `successor_of`, and changes
ONLY the named clause(s); everything else is byte-identical apart from the id/path rewrite and the reseal.

    chain.py scaffold --candidate cand.json --handoff churn-pipeline.md [--root DIR] [--date YYYYMMDD]
                      [--research-commit SHA] [--research-tree DIR --test-mode]   (offline rows never publish)
    chain.py from-ledger --ledger ledger.json --tag AK-GAP-1-IDSORT --llama /mnt/raid0/llm/llama.cpp [...]
    chain.py successor --rowdir DIR --set estimate_s=4200 --reason "cap raised" [--evidence PATH]
    chain.py lint --rowdir DIR [--box-file boxes.md]

Exit: 0 all rows lint clean, 1 a lint problem, 2 bad input. Output: one JSON report on stdout.
"""
from __future__ import annotations

import argparse
import contextlib
import dataclasses
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Callable

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SKILL_SCRIPTS = os.path.join(REPO, ".claude", "skills", "row-owner-loop", "scripts")
ROWFLOW = os.path.join(REPO, "scripts", "coordination", "rowflow")
for _p in (SKILL_SCRIPTS, ROWFLOW):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import row_scaffold as RS  # noqa: E402
import estimate_history as EH  # noqa: E402

SCHEMA = "epyc.akloop.chain.v1"
CANDIDATE_SCHEMA = "epyc.akloop.candidate.v1"
MIN_ESTIMATE_S = 300            # publish_row.MIN_ESTIMATE_S: a shorter job runs in the owner's turn, not as a row
GPU_TIMING_REGIONS = "mi210_0,88-95,184-191"
GPU_PLAIN_REGIONS = "mi210_0,184-191"
#: Any ONE of q0..q2 (never q3: 88-95 are the MI210 host cores a timing row holds). AKPL-P3: a fixed "q1" pinned
#: every candidate's build to one quarter, so two candidates could never build at once.
BUILD_REGIONS = "any-of q0,q1,q2"
#: Research stage_bodies.DEFAULT_PATH: a candidate without `serving_path` is the 27B on the MI210 (the legacy chain).
DEFAULT_SERVING_PATH = "27b-q8_0|mi210"
#: Stages whose device is the candidate PATH's (research stage_bodies.PATH_STAGES).
PATH_STAGE_NAMES = ("oracle-kld", "op-perf", "ab-timing", "serving-screen")
#: Stages that are SCREENS: they can fail a candidate (polar FAIL) or file FUTILITY_SCREEN_ONLY_NO_KEEP, never PASS a gate.
SCREEN_STAGE_NAMES = ("op-perf", "serving-screen")
#: Candidate kind whose chain is the single screen stage (no source change, so no build / fold-check).
SERVING_KNOB_KIND = "serving-knob"
#: Whole-host CPU quiet booking (a CPU path's served topology spans all 96 physical cores). `regions` is the published
#: precedent spelling; the polar scaffolder refuses a cpu-lane row touching 88-95, so scaffold_stage books q0,q1,q2 into
#: the scaffolder and writes this over the spec (see CPU_WHOLE_HOST_SPEC).
CPU_WHOLE_HOST_REGIONS = "q0,q1,q2,q3"
SUCCESSOR_CLAUSES = ("estimate_s", "max_window_s", "min_window_s", "decision_rule", "regions", "resumable",
                     "timing", "admission_class", "gate_ids", "busy_fraction", "first_progress_s")


@dataclass(frozen=True)
class Stage:
    name: str
    lane: str
    regions: str
    threads: int
    resumable: bool
    history: str                    # regex over AK row ids of the same stage class (estimate population)
    gate_ids: tuple[str, ...]       # P1 gate_eval gate ids that decide this stage
    question: str
    rule: str
    stop: str
    fallback_s: int                 # used only when the stage class has < MIN_SAMPLES runs (stated in the spec)
    timing: str | None = None
    admission_class: str | None = None
    shape: str | None = None
    extra: dict = field(default_factory=dict)


STAGES: tuple[Stage, ...] = (
    Stage("build", "cpu", BUILD_REGIONS, 24, True, r"^(ak|akx|c\d+)-.*-build(-|$)",
          ("declared.polar", "declared.futility_harness"),
          "Does the candidate patch build cleanly on its base (CPU + HIP trees), with its test target?",
          "PASS if both trees build and the feature test binary exists; FUTILITY_HARNESS_BUILD_ENV on a toolchain/"
          "disk fault; FAIL otherwise. polar PASS|FAIL.",
          "on-answer: first build result. on-futility: toolchain fault. rc 75 only on STOP / FILLER_DEADLINE.", 300),
    Stage("oracle-kld", "gpu", GPU_PLAIN_REGIONS, 8, True, r"^(ak|akx|c\d+)-.*-(kld|oracle|gate)(-|$)",
          ("graph_kld.gpu.q38_27b", "graph_kld.gpu.q38fn", "ppl_contract.q38_27b"),
          "Is the candidate numerically safe: oracle identity + 27B-anchored graph KLD (graph_kld_policy.json)?",
          "FAIL if 27B mean KLD > 0.003 or |dPPL| > 0.5% or Q38FN same-top < 93%; FUTILITY_HARNESS_* if the oracle "
          "harness or residency proof fails; PASS otherwise. polar PASS|FAIL.",
          "on-answer: all 16 chunks scored. on-futility: residency proof fails twice.", 1800),
    Stage("op-perf", "gpu", GPU_TIMING_REGIONS, 8, False, r"^(ak|akx|c\d+)-.*-op-?perf(-|$)",
          ("declared.polar", "declared.futility_harness"),
          "Does the candidate regress any served-shape op (paired test-backend-ops perf over the path's served grid, "
          "per-cell A/A floors)? SCREEN ONLY (RSL-R3): it can fail a candidate, never keep one.",
          "FAIL (FAIL_OP_PERF_*) if a cell regresses beyond its A/A floor; a clean screen is FUTILITY_SCREEN_ONLY_NO_KEEP "
          "and never a polar PASS; FUTILITY_HARNESS_* if the path is ungated or the runner refuses. polar FAIL only.",
          "on-answer: every served-grid cell measured. on-futility: runner refusal or an ungated path.",
          3600, timing="bench", admission_class="block-timing-quiet", shape="gpu-q3"),
    Stage("ab-timing", "gpu", GPU_TIMING_REGIONS, 8, False, r"^(ak|akx|c\d+)-.*-(timing|e2e|ab|step\d*)(-|$)",
          ("speed.row_geomean_floor", "speed.bench_floor.tg128"),
          "Is the candidate faster than its base on the served shapes (quiet A/B, interleaved pairs)?",
          "PASS if geomean >= rule.geomean_min and the effect clears the bench floor; FUTILITY_CANDIDATE_NO_GAIN "
          "inside the floor; FUTILITY_HARNESS_CONTENTION if the quiet guard trips. polar PASS|FAIL.",
          "on-answer: pre-registered pairs done. on-futility: CI excludes the predicted effect after half the pairs.",
          1800, timing="ak-keep-gate", admission_class="block-timing-quiet", shape="gpu-q3"),
    Stage("fold-check", "gpu", GPU_TIMING_REGIONS, 8, True, r"^c\d+-fold-",
          ("speed.row_geomean_floor", "graph_kld.gpu.q38_27b"),
          "Does the next C-fold composite carrying this feature (one commit + its test) keep speed and numerics?",
          "PASS if per-step geomean >= 0.995 and the 27B KLD gate holds on the composite; FAIL otherwise; "
          "FUTILITY_HARNESS_* on an invalid run. polar PASS|FAIL.",
          "on-answer: every fold step measured. on-futility: an invalid run twice.",
          3600, timing="bench", shape="gpu-q3"),
)
#: Optional stage (never in STAGES, never a fold input): see chain_stages. GPU path: plain mi210 regions like oracle-kld
#: (not a timing row; nothing here is timed). CPU path: stage_for turns it into the whole-host quiet row.
SERVING_SCREEN = Stage(
    "serving-screen", "gpu", GPU_PLAIN_REGIONS, 8, False, r"^(ak|akx|c\d+)-.*-serving-screen(-|$)",
    ("declared.polar", "declared.futility_harness"),
    "Does a serving-knob arm beat its control on the served best case (steady state) without breaking the worst case "
    "(burst: fits memory, ITL p95 within +20%, correct output)? SCREEN ONLY: it can reject an arm, never keep one.",
    "FAIL (polar) if the arm is rejected on a worst-case guard rail; a clean screen is FUTILITY_SCREEN_ONLY_NO_KEEP and "
    "never a polar PASS; FUTILITY_HARNESS_* on invalid measurements. polar FAIL only.",
    "on-answer: both cases screened once (research serving_knob_measure.screen_stage). on-futility: invalid measurements.",
    300)
STAGE_BY_NAME = {s.name: s for s in (*STAGES, SERVING_SCREEN)}

#: Spec fields of a CPU-path whole-host quiet row (copied from the published ak-q38fn-cpu-aa-floor-20261124 /
#: ak-a3b-cpu-aa-floor-20261124 / ak-opperf-cal-q38fn-cpu-20261124 specs; placement itself is the runner's, from the
#: registry path spec + stack_numa, never typed here).
CPU_WHOLE_HOST_SPEC = {
    "regions": CPU_WHOLE_HOST_REGIONS, "claim_cpus": "any-of q0,q1,q2", "shape": "host", "declared_threads": 96,
    "requires_quiet_host": True, "role": "bench", "resumable": False,
    "width_justification": ("whole host (q0-q3) because the served CPU path's instances span all 96 physical cores; the "
                            "quiet-host booking keeps co-tenants off the other regions."),
    "threads_evidence": ["whole host: the path's NUMA_FULL instance (Q38FN :8074) or its two concurrent NUMA-half "
                         "instances (A3B :8070), 96 physical cores, aggregate tok/s; placement from the registry path "
                         "spec + stack_numa inside the runner; smoke refuses unless the served topology totals 96 threads"],
    "gpu_fence_override": ("akloop/chain.py: CPU-path stage; no GPU code runs (CPU store, --device none, "
                           "HIP/ROCR visibility -1 off the gpu lane)"),
}
#: History population / fallback of a CPU-path stage: its own (GPU rows are not its samples); measured on the
#: 24-pair calibration rows (Q38FN floor 14700 s, A3B floor 10000 s, Q38FN op-perf cal 10800 s) scaled to a screen/A-B run.
#: oracle-kld on a CPU path has NO measured population yet (the CPU KLD clauses have not run as a row): its fallback is a
#: PROVISIONAL stated guess, re-booked from the row's smoke_measure.json (spec.estimate_basis.provisional). serving-screen
#: is a parse of already-measured rows, so it books the 300 s row minimum.
CPU_PATH_FALLBACK_S = {"ab-timing": 7200, "op-perf": 4800, "oracle-kld": 3600, "serving-screen": 300}
_PATH_RX = re.compile(r"^[a-z0-9][a-z0-9_.+-]*\|(mi210|cpu)$")


def serving_path(cand: dict[str, Any]) -> str:
    """The candidate's served path `model|device` (research stage_bodies resolves it against the registry). Absent ->
    the 27B on the MI210, so an old candidate scaffolds exactly as before."""
    p = str(cand.get("serving_path") or DEFAULT_SERVING_PATH)
    if not _PATH_RX.match(p):
        raise ValueError(f"serving_path must be '<model>|mi210' or '<model>|cpu', got {p!r}")
    return p


def path_lane(cand: dict[str, Any]) -> str:
    return "gpu" if serving_path(cand).endswith("|mi210") else "cpu"


def stage_for(cand: dict[str, Any], st: Stage) -> Stage:
    """`st` as this candidate's path runs it: a GPU path keeps today's stage; a CPU path's oracle-kld / op-perf /
    ab-timing / serving-screen is a cpu-lane whole-host quiet row (never the gpu-q3 timing shape, never an MI210 grant)."""
    if st.name not in PATH_STAGE_NAMES or path_lane(cand) == "gpu":
        return st
    return dataclasses.replace(st, lane="cpu", regions=CPU_WHOLE_HOST_REGIONS, threads=96, resumable=False,
                               history=r"(?!)", timing=None, admission_class=None, shape="host", fallback_s=CPU_PATH_FALLBACK_S[st.name],
                               extra=dict(CPU_WHOLE_HOST_SPEC))


def model_label(cand: dict[str, Any], stage: Stage) -> str:
    if stage.name == "build":
        return "n/a (build)"
    if stage.name in PATH_STAGE_NAMES and serving_path(cand) != DEFAULT_SERVING_PATH:
        return f"served path {serving_path(cand)}"
    return "Qwen3.8-27B Q8_0 + Q38FN"


# ---- candidate record ---------------------------------------------------------------------------

def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:40] or "cand"


def candidate(base_sha: str, patch_sha: str, hypothesis_id: str, predicted_effect: str, **extra) -> dict[str, Any]:
    for k, v in (("base_sha", base_sha), ("patch_sha", patch_sha)):
        if not re.fullmatch(r"[0-9a-f]{7,40}", str(v or "")):
            raise ValueError(f"{k} must be a git sha, got {v!r}")
    if not hypothesis_id:
        raise ValueError("hypothesis_id required")
    rec = {"schema": CANDIDATE_SCHEMA, "base_sha": base_sha, "patch_sha": patch_sha,
           "hypothesis_id": str(hypothesis_id), "predicted_effect": str(predicted_effect or "unstated")}
    rec.update({k: v for k, v in extra.items() if v is not None})
    rec.setdefault("id", f"cand-{_slug(hypothesis_id)}-{patch_sha[:9]}")
    return rec


def candidate_from_ledger(ledger: dict[str, Any], tag: str, git: Callable[..., str] | None = None) -> dict[str, Any]:
    """A candidate record for one P4 ledger feature: patch = its keep sha, base = the keep's first parent."""
    feat = next((f for f in ledger.get("features", []) if f.get("tag") == tag), None)
    if feat is None:
        raise ValueError(f"tag {tag} not in ledger")
    keep = feat.get("keep_sha") or (feat.get("commits") or [{}])[-1].get("sha")
    base = git("rev-parse", f"{keep}^") if git else feat.get("base_sha")
    effect = re.search(r"([+-]?\d+(?:\.\d+)?%|\d\.\d{3}\s*\[[^\]]+\])", feat.get("hypothesis", ""))
    return candidate(str(base).strip(), keep, tag, effect.group(1) if effect else "unstated",
                     hypothesis=feat.get("hypothesis"), fold=ledger.get("current_fold"),
                     next_c=ledger.get("next_c"), test_files=feat.get("test_files"),
                     gate_results=feat.get("gate_results"), in_fold=feat.get("in_fold"))


# ---- estimates ----------------------------------------------------------------------------------

def stage_estimate(stage: Stage, recs: list[dict[str, Any]] | None = None, flags: str = EH.FLAGS) -> tuple[int, str]:
    """(estimate_s, justification) from estimate_history over the AK rows of this stage class."""
    recs = EH.samples(flags) if recs is None else recs
    fam = f"akchain-{stage.name}" + ("-cpu" if stage.lane == "cpu" and stage.name in PATH_STAGE_NAMES else "")
    rx = re.compile(stage.history)
    pool = [dict(r, family=fam) for r in recs if rx.search(str(r.get("row", "")))]
    sug = EH.suggest(fam, recs=pool)
    if sug:
        est, just = int(sug["estimate_s"]), sug["estimate_justification"]
    else:
        n = sum(1 for r in pool if r.get("usable"))
        est = stage.fallback_s
        just = (f"history {fam}: {n} usable runs < {EH.MIN_SAMPLES}; stage fallback 1 run x {stage.fallback_s} s "
                f"(no margin; re-estimate after 3 runs)")
    if est < MIN_ESTIMATE_S:
        just += f"; raised to the {MIN_ESTIMATE_S} s row minimum (1 x {MIN_ESTIMATE_S} s)"
        est = MIN_ESTIMATE_S
    return est, just


# ---- scaffolding --------------------------------------------------------------------------------

def _rebase_tag(cand: dict[str, Any]) -> str:
    """A rebase-and-recheck chain re-tests the SAME hypothesis on a new base: its rows carry the rebased patch."""
    return f"-rb{str(cand['patch_sha'])[:7]}" if cand.get("rebase_of") else ""


def row_id(cand: dict[str, Any], stage: Stage, date: str) -> str:
    return f"akc-{_slug(cand['hypothesis_id'])}{_rebase_tag(cand)}-{stage.name}-{date}"


def box_id(cand: dict[str, Any], stage: Stage) -> str:
    return f"AKC-{_slug(cand['hypothesis_id']).upper()}{_rebase_tag(cand).upper()}-{stage.name.upper()}"


def render_box(cand: dict[str, Any], stage: Stage, est: int, gate: list[str], owner: str) -> str:
    text = (f"AK chain {stage.name} for candidate `{cand['id']}` ({cand['hypothesis_id']}; patch {cand['patch_sha'][:9]} "
            f"on base {cand['base_sha'][:9]}; predicted {cand['predicted_effect']}). model: "
            f"{model_label(cand, stage)}. STOP {stage.stop} est {est} s.")
    lines = [f"- [ ] **{box_id(cand, stage)}** [inference] {text}",
             f"      · done when: row `{row_id(cand, stage, '<date>')}` filed by gate_eval on "
             f"{', '.join(stage.gate_ids)} "
             f"({'screen only: polar FAIL or FUTILITY_SCREEN_ONLY_NO_KEEP, never a PASS' if stage.name in SCREEN_STAGE_NAMES else 'polar PASS/FAIL'}).",
             f"      · gate: {', '.join(gate) if gate else 'none'}",
             f"      · owner: {owner}"]
    return "\n".join(lines)


CAND_FIELDS = ("id", "base_sha", "patch_sha", "hypothesis_id", "predicted_effect", "paths", "rebase_of",
               "skip_stages", "champion_ref", "op", "geomean_min", "pairs", "timing_model", "anchor_build",
               "llama_repo", "serving_path", "shape_class", "journal_key", "stages",
               "kind", "mechanism_id", "server", "delta", "delta_digest", "base_recipe_hash", "registry_base_digest", "argv",
               "argv_delta", "screening_only", "steady_results", "arm_map", "burst_results", "floor_result", "test_outcomes", "test_refs", "test_parents", "test_fixture_repo",
               "test_lineage_log")


def _job_text(cand: dict[str, Any], stage: Stage, rid: str, d: str, *, prior_results: dict[str, str],
              research_commit: str | None, research_tree: str | None, test_mode: bool,
              research_repo: str = RS.RESEARCH_REPO) -> str:
    """Stage job.py: runs `autokernel.loop.stage_bodies` (research repo, AKPL-P3) for this stage and leaves ONE
    polar RESULT.json. The research code comes from `git archive <pinned commit>` of the research clone (read-only:
    never its tree, branch or index), or from `research_tree` for an offline test-mode row (lint refuses to publish
    those). Any harness failure still writes a finished FUTILITY_HARNESS_* RESULT, so no run ends without a claim."""
    return f'''#!/usr/bin/python3
"""{rid}
QUESTION  {stage.question}
          candidate {cand['id']}: hypothesis {cand['hypothesis_id']}, patch {cand['patch_sha']}, base {cand['base_sha']},
          predicted effect {cand['predicted_effect']}.
SOURCE    llama.cpp-experimental worktree at {cand['patch_sha']} (content proof: git rev-parse HEAD == patch sha);
          stage driver autokernel.loop.stage_bodies @ research {research_commit or research_tree}.
STEPS     stage {stage.name}; gate ids {", ".join(stage.gate_ids)}.
RULE      {stage.rule}
STOP      {stage.stop}
"""
import io, json, os, subprocess, sys, tarfile
D = {d!r}
OUT = os.path.join(D, "out", "RESULT.json")
STAGE, LANE, ROW = {stage.name!r}, {stage.lane!r}, {rid!r}
RESEARCH_REPO, RESEARCH_COMMIT, RESEARCH_TREE = {research_repo!r}, {research_commit!r}, {research_tree!r}
PRIOR_RESULTS = {json.dumps(prior_results, sort_keys=True)}
TEST_MODE = {bool(test_mode)!r}
os.makedirs(os.path.dirname(OUT), exist_ok=True)


def harness(token, why):
    json.dump({{"complete": True, "verdict": f"{{token}} ({{why}})", "stage": STAGE, "row": ROW,
               "candidate": {cand['id']!r}}}, open(OUT, "w"))
    sys.exit(0)


if LANE != "gpu":
    os.environ["HIP_VISIBLE_DEVICES"] = "-1"
    os.environ["ROCR_VISIBLE_DEVICES"] = "-1"
if RESEARCH_TREE:
    kr = os.path.join(RESEARCH_TREE, "scripts", "kernel_rnd")
else:
    root = os.path.join(D, "research")
    kr = os.path.join(root, "scripts", "kernel_rnd")
    if not os.path.exists(os.path.join(kr, "autokernel", "loop", "stage_bodies.py")):
        a = subprocess.run(["git", "-C", RESEARCH_REPO, "archive", RESEARCH_COMMIT, "scripts/kernel_rnd/autokernel"],
                           capture_output=True)
        if a.returncode != 0:
            harness("FUTILITY_HARNESS_MISSING_INPUT", f"git archive {{RESEARCH_COMMIT}} failed")
        tarfile.open(fileobj=io.BytesIO(a.stdout)).extractall(root)
cand = json.load(open(os.path.join(D, "candidate.json")))
cand["stage_results"] = PRIOR_RESULTS
cp = os.path.join(D, "out", "candidate.run.json")
json.dump(cand, open(cp, "w"), indent=1)
argv = [sys.executable, "-s", "-B", "-m", "autokernel.loop.stage_bodies", "--stage", STAGE, "--candidate", cp,
        "--out", OUT, "--lane", LANE, "--row", ROW] + (["--test-mode"] if TEST_MODE else [])
rc = subprocess.run(argv, cwd=kr).returncode
if not os.path.exists(OUT):
    harness("FUTILITY_HARNESS_STAGE_DRIVER_CRASH", f"stage driver rc={{rc}} wrote no RESULT")
sys.exit(0)
'''


def scaffold_stage(cand: dict[str, Any], stage: Stage, *, root: str, date: str, handoff: str, owner: str,
                   gate: list[str], supersedes: str | None, recs: list[dict[str, Any]] | None,
                   research_repo: str = RS.RESEARCH_REPO, quiet: bool = True,
                   prior_results: dict[str, str] | None = None, research_commit: str | None = None,
                   research_tree: str | None = None, test_mode: bool = False) -> dict[str, Any]:
    rid = row_id(cand, stage, date)
    est, just = stage_estimate(stage, recs)
    whole_host = bool(stage.extra.get("requires_quiet_host"))
    # the polar scaffolder refuses a cpu-lane row touching 88-95: a whole-host row is scaffolded on q0,q1,q2 and its spec
    # is then written with the published whole-host shape (stage.extra, CPU_WHOLE_HOST_SPEC)
    a = SimpleNamespace(row_id=rid, handoff=handoff, box=box_id(cand, stage), lane=stage.lane,
                        regions="q0,q1,q2" if whole_host else stage.regions,
                        threads=stage.threads, units=1, unit_s=est / 1.25, flags=None, owner=owner, root=root,
                        model=model_label(cand, stage),
                        research_repo=research_repo, research_ref="origin/main",
                        # akloop stages pre-register their own stop rule (Stage.stop) and rewrite job.py: AK-EVAL-FUT opt-out
                        custom_futility=f"akloop stage {stage.name}: {stage.stop}")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = RS.scaffold(a)
    if rc != 0:
        raise RuntimeError(f"row_scaffold refused {rid}: {buf.getvalue().strip()}")
    d = os.path.join(root, rid)
    with open(os.path.join(d, "job.py"), "w") as f:
        f.write(_job_text(cand, stage, rid, d, prior_results=prior_results or {}, research_commit=research_commit,
                          research_tree=research_tree, test_mode=test_mode, research_repo=research_repo))
    with open(os.path.join(d, "candidate.json"), "w") as f:
        json.dump({**{k: cand[k] for k in CAND_FIELDS if k in cand}, "serving_path": serving_path(cand)}, f, indent=1,
                  sort_keys=True)
    if whole_host:   # precedent launchers (ak-q38fn-cpu-aa-floor): no C= / --claim-cpus, the grant's cpus are the claim
        lp = os.path.join(d, "launch.sh")
        lt = re.sub(r"^C=.*\n", "", open(lp).read(), flags=re.M).replace(' --claim-cpus "$C"', "")
        with open(lp, "w") as f:
            f.write(lt)
    if stage.lane == "gpu":   # GPU rows: filler_run15.sh --claim-cpus takes a digit/comma/dash cpu list, never the mi210_0 region token
        lp = os.path.join(d, "launch.sh")
        claim = ",".join(t for t in stage.regions.split(",") if re.fullmatch(r"\d+(-\d+)?", t)) or "184-191"
        lt = re.sub(r"^C=.*$", lambda m: f"C=${{WS58_CPUS:-{claim}}}", open(lp).read(), flags=re.M)
        with open(lp, "w") as f:
            f.write(lt)

    sp = os.path.join(d, "spec.json")
    spec = json.load(open(sp))
    spec.update({"estimate_s": est, "estimate_justification": just, "min_window_s": spec["min_window_s"],
                 "lineage": cand["id"], "supersedes": supersedes, "gate": list(gate), "gate_ids": list(stage.gate_ids),
                 "resumable": stage.resumable, "family": f"akchain-{stage.name}", "verdict_by": "gate_eval",
                 "decision_rule": f"gate_eval {', '.join(stage.gate_ids)}; job.py RULE",
                 "candidate": {k: cand[k] for k in ("id", "base_sha", "patch_sha", "hypothesis_id", "predicted_effect")},
                 "stage": stage.name, "serving_path": serving_path(cand), "stage_driver": {"research_commit": research_commit,
                                                       "research_tree": research_tree, "test_mode": bool(test_mode)},
                 **({"rebase_of": cand["rebase_of"]} if cand.get("rebase_of") else {}),
                 "notes": (f"akloop/chain.py stage {stage.name} of {cand['id']}; gate: {', '.join(gate) or 'none'}; "
                           f"estimate {just}")})
    if stage.regions.startswith("any-of"):
        spec["shape"] = "quarter"
        spec["width_justification"] = (f"{stage.regions} is the allow-set, not the width: rowflow.contract_of books "
                                       f"ONE quarter (shape quarter, options q0|q1|q2)")
    for k in ("timing", "admission_class", "shape"):
        v = getattr(stage, k)
        if v:
            spec[k] = v
    if whole_host:
        spec.update(json.loads(json.dumps(stage.extra)))
        spec["baseline_ref"] = BASELINE_REF[stage.name](cand)
    spec["estimate_basis"] = {"provisional": True, "rebook_from": os.path.join(d, "out", "smoke_measure.json"),
                              "reason": (f"chain stage {stage.name}: estimate from the stage table/history ({just}); "
                                         f"re-book from this row's smoke_measure.json after the smoke")}
    if stage.resumable and not spec.get("max_window_s"):
        spec["max_window_s"] = max(int(spec["min_window_s"]) + 300, int(math.ceil(est * 1.2)) + 300)
    with open(sp, "w") as f:
        json.dump(spec, f, indent=1)
    RS.seal(d, ["job.py", "check_complete.py", "launch.sh", "candidate.json"]
            + sorted(n for n in RS.HARNESS_FILES if os.path.exists(os.path.join(d, n))))
    return {"stage": stage.name, "id": rid, "rowdir": d, "box": box_id(cand, stage), "estimate_s": est,
            "regions": spec["regions"], "lane": stage.lane, "serving_path": serving_path(cand), "resumable": stage.resumable, "gate": list(gate),
            "gate_ids": list(stage.gate_ids), "supersedes": supersedes}


BASELINE_REF = {
    "ab-timing": lambda c: (f"arm A = base build {str(c['base_sha'])[:9]}, arm B = patch {str(c['patch_sha'])[:9]} "
                            f"(same store, same env, interleaved pairs)"),
    "op-perf": lambda c: (f"arm A = base build {str(c['base_sha'])[:9]}, arm B = patch {str(c['patch_sha'])[:9]} "
                          f"(same store, same env, interleaved pairs over the served-shape grid)"),
    "oracle-kld": lambda c: (f"anchor = base build {str(c['base_sha'])[:9]}, candidate = patch {str(c['patch_sha'])[:9]} "
                             f"(same GGUF, same chunks, the path's own KLD clauses)"),
    "serving-screen": lambda c: (f"control arm vs the knob arms of one served recipe ({c.get('server', '?')}), "
                                 f"delta {str(c.get('delta_digest', ''))[:12] or 'unstated'}; no source change"),
}


def _is_whole_host(spec: dict[str, Any]) -> bool:
    return (spec.get("lane") == "cpu" and spec.get("shape") == "host" and spec.get("requires_quiet_host") is True
            and int(spec.get("declared_threads") or 0) >= 96
            and len(str(spec.get("width_justification") or "").strip()) >= 20)


def lint_row(rowdir: str, box_file: str | None) -> list[str]:
    """row_scaffold.lint + publish_row.lint on a COPY of the spec (lint rewrites in place; nothing is published)."""
    errs = list(RS.lint(rowdir, box_file))
    spec = json.load(open(os.path.join(rowdir, "spec.json")))
    whole_host = _is_whole_host(spec)
    if whole_host:   # q3's cores are inside the served topology: the published whole-host shape, not the gpu-q3 shape
        errs = [e for e in errs if not e.startswith("CPU-GPUTHR")]
    try:
        import publish_row as PR
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            PR.lint(dict(spec))
    except Exception as e:  # noqa: BLE001 - rf.Refused and any lint crash are lint failures
        errs.append(f"PUBLISH-LINT: {type(e).__name__}: {e}")
    if spec.get("lane") == "cpu" and not whole_host and RS.cpus(spec.get("regions", "")) & set(range(72, 96)):
        errs.append("CHAIN-Q3: a cpu-lane chain row books q3 (GPU timing rows hold 88-95)")
    if spec.get("timing") and "88-95" not in str(spec.get("regions")):
        errs.append("CHAIN-TIMING: a GPU timing row must hold 88-95")
    if spec.get("stage") in PATH_STAGE_NAMES and spec.get("serving_path"):
        want = "gpu" if str(spec["serving_path"]).endswith("|mi210") else "cpu"
        if spec.get("lane") != want:
            errs.append(f"CHAIN-PATHLANE: {spec['stage']} of path {spec['serving_path']} must run on the {want} lane, "
                        f"not {spec.get('lane')}")
        if want == "cpu" and not whole_host:
            errs.append("CHAIN-CPUPATH: a cpu-path stage must be a whole-host quiet row (shape host, requires_quiet_host, "
                        "declared_threads 96)")
    for k in ("lineage", "gate_ids"):
        if not spec.get(k):
            errs.append(f"CHAIN-FIELD: spec.{k} missing")
    if "supersedes" not in spec or "gate" not in spec:
        errs.append("CHAIN-FIELD: spec.supersedes / spec.gate missing")
    drv = spec.get("stage_driver") or {}
    if drv.get("test_mode"):
        errs.append("CHAIN-TESTMODE: an offline test-mode row (stub stage bodies) is never publishable")
    if drv and not drv.get("test_mode") and (drv.get("research_tree") or not drv.get("research_commit")):
        errs.append("CHAIN-DRIVER: the stage driver must be a pinned research commit (git archive), not a tree")
    return errs


def research_head(repo: str = RS.RESEARCH_REPO, ref: str = "origin/main") -> str | None:
    """The research commit a live chain pins its stage driver to (fetch + rev-parse only; never the clone's tree)."""
    remote, _, branch = ref.partition("/")
    subprocess.run(["git", "-C", repo, "fetch", "-q", remote, branch], capture_output=True, text=True)
    r = subprocess.run(["git", "-C", repo, "rev-parse", "--verify", f"{ref}^{{commit}}"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def chain_stages(cand: dict[str, Any]) -> tuple[Stage, ...]:
    """The stages this candidate's chain runs: all five, or the record's `stages` (a rebase-and-recheck chain is
    build + oracle-kld [+ op-perf + ab-timing only when the measured path moved] + fold-check), each as the
    candidate's `serving_path` runs it (stage_for). A candidate of kind "serving-knob" changes the served recipe, not
    the source: its chain is the ONE optional `serving-screen` stage (a screen, never a fold input), and no other
    candidate may name that stage."""
    if cand.get("kind") == SERVING_KNOB_KIND:
        names = cand.get("stages") or ["serving-screen"]
        if list(names) != ["serving-screen"]:
            raise ValueError(f"a serving-knob candidate's chain is exactly ['serving-screen']; got {list(names)}")
        return (stage_for(cand, SERVING_SCREEN),)
    names = cand.get("stages") or [s.name for s in STAGES]
    bad = [n for n in names if n not in STAGE_BY_NAME or n == SERVING_SCREEN.name]
    if bad or names[-1] != "fold-check" or names[0] != "build":
        raise ValueError(f"chain stages must run build .. fold-check from {[s.name for s in STAGES]}; got {names}"
                         + (" (serving-screen is only for kind serving-knob)" if "serving-screen" in names else ""))
    return tuple(stage_for(cand, STAGE_BY_NAME[n]) for n in names)


def scaffold_chain(cand: dict[str, Any], *, root: str, date: str, handoff: str, owner: str = "pipeline-mgmt",
                   prior: dict[str, str] | None = None, recs: list[dict[str, Any]] | None = None,
                   research_repo: str = RS.RESEARCH_REPO, research_commit: str | None = None,
                   research_tree: str | None = None, test_mode: bool = False) -> dict[str, Any]:
    """Scaffold + dry-run lint the stage rows (build, oracle-kld, op-perf, ab-timing, fold-check). Never publishes. `prior` maps stage -> prior row id.

    Each job runs autokernel.loop.stage_bodies pinned to `research_commit` (default: research origin/main), with the
    RESULT paths of its upstream stage rows, so fold-check can prove the keep lands on the base it was built from."""
    prior = prior or {}
    recs = EH.samples() if recs is None else recs
    if research_tree is None and research_commit is None:
        research_commit = research_head(research_repo)
    os.makedirs(root, exist_ok=True)
    rows, boxes, prev = [], [], None
    results: dict[str, str] = {}
    for st in chain_stages(cand):
        gate = [prev["box"]] if prev else []
        r = scaffold_stage(cand, st, root=root, date=date, handoff=handoff, owner=owner, gate=gate,
                           supersedes=prior.get(st.name), recs=recs, research_repo=research_repo,
                           prior_results=dict(results), research_commit=research_commit,
                           research_tree=research_tree, test_mode=test_mode)
        results[st.name] = os.path.join(r["rowdir"], "out", "RESULT.json")
        boxes.append(render_box(cand, st, r["estimate_s"], gate, owner))
        rows.append(r)
        prev = r
    box_file = os.path.join(root, f"{cand['id']}.boxes.md")
    with open(box_file, "w") as f:
        f.write(f"# Draft boxes for {cand['id']} (akloop/chain.py; NOT in any handoff)\n\n" + "\n".join(boxes) + "\n")
    for r in rows:
        r["lint"] = lint_row(r["rowdir"], box_file)
    return {"schema": SCHEMA, "candidate": cand, "rows": rows, "box_file": box_file, "published": False,
            "research_commit": research_commit, "test_mode": bool(test_mode),
            "lint_clean": all(not r["lint"] for r in rows)}


# ---- successor emitter --------------------------------------------------------------------------

_REV = re.compile(r"^(?P<base>.+?)(?:-r(?P<n>\d+))?$")


def next_id(rid: str) -> str:
    m = _REV.match(rid)
    return f"{m.group('base')}-r{int(m.group('n') or 1) + 1}"


def _rewrite(text: str, rowdir: str, nd: str, old: str, new: str) -> str:
    """Row dir -> new dir and old id -> new id, without re-rewriting the new dir (it contains the old id)."""
    mark = "\x00ROWDIR\x00"
    return text.replace(rowdir, mark).replace(old, new).replace(mark, nd)


def successor(rowdir: str, changes: dict[str, Any], reason: str, evidence: list[str] | None = None,
              root: str | None = None) -> dict[str, Any]:
    """Emit `<id>-r<N+1>` superseding the row at `rowdir`, changing ONLY the named clauses."""
    bad = sorted(set(changes) - set(SUCCESSOR_CLAUSES))
    if bad:
        raise ValueError(f"successor changes only {SUCCESSOR_CLAUSES}; refused {bad}")
    if not changes:
        raise ValueError("a successor must change at least one clause")
    rowdir = os.path.abspath(rowdir)
    spec = json.load(open(os.path.join(rowdir, "spec.json")))
    old, new = spec["id"], next_id(spec["id"])
    nd = os.path.join(root or os.path.dirname(rowdir), new)
    if os.path.exists(nd):
        raise FileExistsError(nd)
    shutil.copytree(rowdir, nd, ignore=shutil.ignore_patterns("out", "STOP", "*.log", "verdict.json"))
    os.makedirs(os.path.join(nd, "out"))
    for name in ("launch.sh", "job.py", "check_complete.py"):
        p = os.path.join(nd, name)
        if os.path.exists(p):
            t = _rewrite(open(p).read(), rowdir, nd, old, new)
            if name == "launch.sh" and "min_window_s" in changes:
                t = re.sub(r"--min-window \d+", f"--min-window {int(changes['min_window_s'])}", t)
            if name == "launch.sh" and "regions" in changes:
                t = re.sub(r"^C=.*$", f"C={changes['regions']}", t, flags=re.M)
            with open(p, "w") as f:
                f.write(t)
    before = {k: spec.get(k) for k in changes}
    s2 = json.loads(_rewrite(json.dumps(spec), rowdir, nd, old, new))
    s2["id"] = new
    s2.update(changes)
    if "regions" in changes:
        s2["claim_cpus"] = changes["regions"]
    s2["supersedes"] = old
    ev = list(evidence or [])
    for cand_ev in (os.path.join(rowdir, "out", "RESULT.json"), os.path.join(rowdir, "verdict.json"),
                    os.path.join(EH.FLAGS, "filing-done", f"{old}.verdict.json")):
        if os.path.exists(cand_ev) and cand_ev not in ev:
            ev.append(cand_ev)
    s2["successor_of"] = {"row": old, "reason": reason, "changed": {k: {"from": before[k], "to": changes[k]}
                                                                    for k in changes}, "evidence": ev}
    s2["notes"] = (f"{spec.get('notes', '')} | successor of {old}: {reason}; changed "
                   f"{', '.join(sorted(changes))}; prior evidence {', '.join(ev) or 'none on disk'} (cite, do not re-run)")
    with open(os.path.join(nd, "spec.json"), "w") as f:
        json.dump(s2, f, indent=1)
    names = [ln.split()[1].lstrip("*") for ln in open(os.path.join(nd, "SOURCE.sha256")) if len(ln.split()) == 2
             and ln.split()[1].lstrip("*") != "spec.json"]
    RS.seal(nd, names)
    return {"id": new, "rowdir": nd, "supersedes": old, "changed": sorted(changes), "evidence": ev}


def spec_diff(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    """Keys whose values differ, after normalising the id/path rewrite (for tests and the CLI report)."""
    na = json.loads(json.dumps(a).replace(a["id"], "<ID>").replace(os.path.dirname(a["launcher"]), "<D>"))
    nb = json.loads(json.dumps(b).replace(b["id"], "<ID>").replace(os.path.dirname(b["launcher"]), "<D>"))
    return sorted(k for k in set(na) | set(nb) if na.get(k) != nb.get(k))


# ---- CLI ----------------------------------------------------------------------------------------

def _git(repo: str) -> Callable[..., str]:
    def run(*args: str) -> str:
        return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout.strip()
    return run


def _parse_set(items: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for it in items:
        k, _, v = it.partition("=")
        try:
            out[k] = json.loads(v)
        except ValueError:
            out[k] = v
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("scaffold", "from-ledger"):
        p = sub.add_parser(name)
        p.add_argument("--handoff", default="churn-pipeline.md")
        p.add_argument("--root", default="/mnt/raid0/llm/tmp")
        p.add_argument("--date", required=True)
        p.add_argument("--owner", default="pipeline-mgmt")
        p.add_argument("--research-repo", default=RS.RESEARCH_REPO)
        p.add_argument("--prior", action="append", default=[], help="stage=row-id: the prior attempt this supersedes")
        p.add_argument("--research-commit", help="pin the stage driver (default: research origin/main)")
        p.add_argument("--research-tree", help="OFFLINE ONLY: run the stage driver from this tree (lint refuses publish)")
        p.add_argument("--test-mode", action="store_true", help="OFFLINE ONLY: stub stage bodies (lint refuses publish)")
        if name == "scaffold":
            p.add_argument("--candidate", required=True)
        else:
            p.add_argument("--ledger", required=True)
            p.add_argument("--tag", required=True)
            p.add_argument("--llama", default="/mnt/raid0/llm/llama.cpp")
    s = sub.add_parser("successor")
    s.add_argument("--rowdir", required=True)
    s.add_argument("--set", action="append", default=[], required=True)
    s.add_argument("--reason", required=True)
    s.add_argument("--evidence", action="append", default=[])
    s.add_argument("--box-file")
    li = sub.add_parser("lint")
    li.add_argument("--rowdir", required=True)
    li.add_argument("--box-file")
    a = ap.parse_args(argv)
    try:
        if a.cmd in ("scaffold", "from-ledger"):
            cand = (json.load(open(a.candidate)) if a.cmd == "scaffold" else
                    candidate_from_ledger(json.load(open(a.ledger)), a.tag, _git(a.llama)))
            if a.cmd == "scaffold":
                cand = candidate(**{k: v for k, v in cand.items() if k != "schema"})
            rep = scaffold_chain(cand, root=a.root, date=a.date, handoff=a.handoff, owner=a.owner,
                                 prior=dict(p.split("=", 1) for p in a.prior), research_repo=a.research_repo,
                                 research_commit=a.research_commit, research_tree=a.research_tree,
                                 test_mode=a.test_mode)
            if a.test_mode:   # offline rows are expected to carry the CHAIN-TESTMODE refusal and nothing else
                return 0 if all(all(e.startswith("CHAIN-TESTMODE") for e in r["lint"]) for r in rep["rows"]) else 1
            print(json.dumps(rep, indent=1))
            return 0 if rep["lint_clean"] else 1
        if a.cmd == "successor":
            r = successor(a.rowdir, _parse_set(a.set), a.reason, a.evidence)
            r["lint"] = lint_row(r["rowdir"], a.box_file)
            print(json.dumps(r, indent=1))
            return 0 if not r["lint"] else 1
        errs = lint_row(a.rowdir, a.box_file)
        print(json.dumps({"rowdir": a.rowdir, "lint": errs}, indent=1))
        return 0 if not errs else 1
    except (ValueError, KeyError, FileExistsError, RuntimeError, subprocess.CalledProcessError) as e:
        print(json.dumps({"error": f"{type(e).__name__}: {e}"}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
