#!/usr/bin/env python3
"""chain.py -- AutoKernel parallel-loop P2: row-chain scaffolder + successor emitter (NEVER publishes).

One CANDIDATE RECORD (base sha, patch sha, hypothesis id, predicted effect) becomes a chain of four epyc.row.v3
row dirs, each scaffolded by row_scaffold.py and linted by row_scaffold.lint + publish_row.lint (a dry run):

    build  ->  oracle-kld  ->  ab-timing  ->  fold-check

Every spec carries `lineage=<candidate id>`, `supersedes` (the prior attempt of the same stage, or null), a
`gate` list naming the previous stage's box (also rendered as the box's `· gate:` field, which index_state.py
resolves), the P1 gate ids its verdict is decided by (`gate_ids`, gate_eval.py), and an estimate from
estimate_history.py over the AK rows of the same stage class (p75 wall x 1.25).

Region shapes (keeper packing rules, inference-backlog-scheduling skill):
    build       cpu lane, ONE quarter, q0..q2 only (never q3: 88-95 are the MI210 host threads a GPU timing row holds)
    oracle-kld  gpu lane, mi210_0 + host threads 184-191, not a timing row (quiet-only on the timing cores)
    ab-timing   gpu timing row: shape gpu-q3 (mi210_0, 88-95 held, 184-191), admission block-timing-quiet
    fold-check  gpu timing row like ab-timing, resumable (per-step checkpoints)
`resumable` is true where a window end can continue from a checkpoint (incremental build, chunked KLD, per-step
fold check) and false for the A/B timing window, which must be one quiet grant.

Successor emitter: when a cap or rule changes, `successor()` copies a scaffolded row dir to `<id>-r<N+1>`, sets
`supersedes=<prior id>`, cites the prior row's evidence (filed verdict / RESULT path) in `successor_of`, and changes
ONLY the named clause(s); everything else is byte-identical apart from the id/path rewrite and the reseal.

    chain.py scaffold --candidate cand.json --handoff churn-pipeline.md [--root DIR] [--date YYYYMMDD]
    chain.py from-ledger --ledger ledger.json --tag AK-GAP-1-IDSORT --llama /mnt/raid0/llm/llama.cpp [...]
    chain.py successor --rowdir DIR --set estimate_s=4200 --reason "cap raised" [--evidence PATH]
    chain.py lint --rowdir DIR [--box-file boxes.md]

Exit: 0 all rows lint clean, 1 a lint problem, 2 bad input. Output: one JSON report on stdout.
"""
from __future__ import annotations

import argparse
import contextlib
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
    Stage("build", "cpu", "q1", 24, True, r"^(ak|akx|c\d+)-.*-build(-|$)",
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
STAGE_BY_NAME = {s.name: s for s in STAGES}


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
    fam = f"akchain-{stage.name}"
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

def row_id(cand: dict[str, Any], stage: Stage, date: str) -> str:
    return f"akc-{_slug(cand['hypothesis_id'])}-{stage.name}-{date}"


def box_id(cand: dict[str, Any], stage: Stage) -> str:
    return f"AKC-{_slug(cand['hypothesis_id']).upper()}-{stage.name.upper()}"


def render_box(cand: dict[str, Any], stage: Stage, est: int, gate: list[str], owner: str) -> str:
    text = (f"AK chain {stage.name} for candidate `{cand['id']}` ({cand['hypothesis_id']}; patch {cand['patch_sha'][:9]} "
            f"on base {cand['base_sha'][:9]}; predicted {cand['predicted_effect']}). model: "
            f"{'Qwen3.8-27B Q8_0 + Q38FN' if stage.lane == 'gpu' else 'n/a (build)'}. STOP {stage.stop} est {est} s.")
    lines = [f"- [ ] **{box_id(cand, stage)}** [inference] {text}",
             f"      · done when: row `{row_id(cand, stage, '<date>')}` filed by gate_eval on "
             f"{', '.join(stage.gate_ids)} (polar PASS/FAIL).",
             f"      · gate: {', '.join(gate) if gate else 'none'}",
             f"      · owner: {owner}"]
    return "\n".join(lines)


def _job_text(cand: dict[str, Any], stage: Stage, rid: str, d: str) -> str:
    """Stage job.py with the docstring filled; the body refuses as FUTILITY_HARNESS until the stage driver lands."""
    return f'''#!/usr/bin/python3
"""{rid}
QUESTION  {stage.question}
          candidate {cand['id']}: hypothesis {cand['hypothesis_id']}, patch {cand['patch_sha']}, base {cand['base_sha']},
          predicted effect {cand['predicted_effect']}.
SOURCE    llama.cpp-experimental worktree at {cand['patch_sha']} (content proof: git rev-parse HEAD == patch sha).
STEPS     stage {stage.name}; gate ids {", ".join(stage.gate_ids)}.
RULE      {stage.rule}
STOP      {stage.stop}
"""
import json, os, sys
OUT = os.path.join("{d}", "out", "RESULT.json")
# Stage driver: generated by akloop/chain.py. Until the per-stage driver is wired (AKPL-P2 live run), the job
# writes a finished harness-futility RESULT so a smoke can never be read as a candidate result.
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump({{"complete": True, "verdict": "FUTILITY_HARNESS_STAGE_DRIVER_MISSING", "stage": "{stage.name}",
           "candidate": "{cand['id']}"}}, open(OUT, "w"))
sys.exit(0)
'''


def scaffold_stage(cand: dict[str, Any], stage: Stage, *, root: str, date: str, handoff: str, owner: str,
                   gate: list[str], supersedes: str | None, recs: list[dict[str, Any]] | None,
                   research_repo: str = RS.RESEARCH_REPO, quiet: bool = True) -> dict[str, Any]:
    rid = row_id(cand, stage, date)
    est, just = stage_estimate(stage, recs)
    a = SimpleNamespace(row_id=rid, handoff=handoff, box=box_id(cand, stage), lane=stage.lane, regions=stage.regions,
                        threads=stage.threads, units=1, unit_s=est / 1.25, flags=None, owner=owner, root=root,
                        model=("Qwen3.8-27B Q8_0 + Q38FN" if stage.lane == "gpu" else "n/a (build)"),
                        research_repo=research_repo, research_ref="origin/main")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = RS.scaffold(a)
    if rc != 0:
        raise RuntimeError(f"row_scaffold refused {rid}: {buf.getvalue().strip()}")
    d = os.path.join(root, rid)
    with open(os.path.join(d, "job.py"), "w") as f:
        f.write(_job_text(cand, stage, rid, d))
    sp = os.path.join(d, "spec.json")
    spec = json.load(open(sp))
    spec.update({"estimate_s": est, "estimate_justification": just, "min_window_s": spec["min_window_s"],
                 "lineage": cand["id"], "supersedes": supersedes, "gate": list(gate), "gate_ids": list(stage.gate_ids),
                 "resumable": stage.resumable, "family": f"akchain-{stage.name}", "verdict_by": "gate_eval",
                 "decision_rule": f"gate_eval {', '.join(stage.gate_ids)}; job.py RULE",
                 "candidate": {k: cand[k] for k in ("id", "base_sha", "patch_sha", "hypothesis_id", "predicted_effect")},
                 "notes": (f"akloop/chain.py stage {stage.name} of {cand['id']}; gate: {', '.join(gate) or 'none'}; "
                           f"estimate {just}")})
    for k in ("timing", "admission_class", "shape"):
        v = getattr(stage, k)
        if v:
            spec[k] = v
    if stage.resumable and not spec.get("max_window_s"):
        spec["max_window_s"] = max(int(spec["min_window_s"]) + 300, int(math.ceil(est * 1.2)) + 300)
    with open(sp, "w") as f:
        json.dump(spec, f, indent=1)
    RS.seal(d, ["job.py", "check_complete.py", "launch.sh", "spec.json"]
            + sorted(n for n in RS.HARNESS_FILES if os.path.exists(os.path.join(d, n))))
    return {"stage": stage.name, "id": rid, "rowdir": d, "box": box_id(cand, stage), "estimate_s": est,
            "regions": stage.regions, "lane": stage.lane, "resumable": stage.resumable, "gate": list(gate),
            "gate_ids": list(stage.gate_ids), "supersedes": supersedes}


def lint_row(rowdir: str, box_file: str | None) -> list[str]:
    """row_scaffold.lint + publish_row.lint on a COPY of the spec (lint rewrites in place; nothing is published)."""
    errs = list(RS.lint(rowdir, box_file))
    spec = json.load(open(os.path.join(rowdir, "spec.json")))
    try:
        import publish_row as PR
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            PR.lint(dict(spec))
    except Exception as e:  # noqa: BLE001 - rf.Refused and any lint crash are lint failures
        errs.append(f"PUBLISH-LINT: {type(e).__name__}: {e}")
    if spec.get("lane") == "cpu" and RS.cpus(spec.get("regions", "")) & set(range(72, 96)):
        errs.append("CHAIN-Q3: a cpu-lane chain row books q3 (GPU timing rows hold 88-95)")
    if spec.get("timing") and "88-95" not in str(spec.get("regions")):
        errs.append("CHAIN-TIMING: a GPU timing row must hold 88-95")
    for k in ("lineage", "gate_ids"):
        if not spec.get(k):
            errs.append(f"CHAIN-FIELD: spec.{k} missing")
    if "supersedes" not in spec or "gate" not in spec:
        errs.append("CHAIN-FIELD: spec.supersedes / spec.gate missing")
    return errs


def scaffold_chain(cand: dict[str, Any], *, root: str, date: str, handoff: str, owner: str = "pipeline-mgmt",
                   prior: dict[str, str] | None = None, recs: list[dict[str, Any]] | None = None,
                   research_repo: str = RS.RESEARCH_REPO) -> dict[str, Any]:
    """Scaffold + dry-run lint the four stage rows. Never publishes. `prior` maps stage -> prior row id."""
    prior = prior or {}
    recs = EH.samples() if recs is None else recs
    os.makedirs(root, exist_ok=True)
    rows, boxes, prev = [], [], None
    for st in STAGES:
        gate = [prev["box"]] if prev else []
        r = scaffold_stage(cand, st, root=root, date=date, handoff=handoff, owner=owner, gate=gate,
                           supersedes=prior.get(st.name), recs=recs, research_repo=research_repo)
        boxes.append(render_box(cand, st, r["estimate_s"], gate, owner))
        rows.append(r)
        prev = r
    box_file = os.path.join(root, f"{cand['id']}.boxes.md")
    with open(box_file, "w") as f:
        f.write(f"# Draft boxes for {cand['id']} (akloop/chain.py; NOT in any handoff)\n\n" + "\n".join(boxes) + "\n")
    for r in rows:
        r["lint"] = lint_row(r["rowdir"], box_file)
    return {"schema": SCHEMA, "candidate": cand, "rows": rows, "box_file": box_file, "published": False,
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
    names = [ln.split()[1].lstrip("*") for ln in open(os.path.join(nd, "SOURCE.sha256")) if len(ln.split()) == 2]
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
                                 prior=dict(p.split("=", 1) for p in a.prior), research_repo=a.research_repo)
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
