#!/usr/bin/env python3
"""row_scaffold.py — scaffold or lint an epyc.row.v3 row dir (row-owner-loop skill, step 1).

  row_scaffold.py --lint <rowdir> [--box-file handoffs/active/x.md]
  row_scaffold.py new <row-id> --handoff <file.md> --box <ID> --lane cpu|gpu --regions <list>
                  --threads N [--units N --unit-s S] --model "<model: ...>" [--root /mnt/raid0/llm/tmp]
                  (no --units/--unit-s: estimate_s defaults to estimate-from-history, family p75 x 1.25,
                  scripts/coordination/rowflow/estimate_history.py; refused when the family has < 3 runs)
                  [--research-repo <repo>] [--research-ref origin/main]  (gpu lane: copies the canonical gpu_common.py +
                  gpuproof_row.py from research origin/main via fetch + `git show` into the row, sha-pinned in job.py + seal)

Lint checks (each prints `LINT <CODE>: …`; exit 1 on any):
  BOX-*       the handoff box (spec.handoff_task file:ID, or --box-file) has a bold **ID**, `model:`,
              a stop rule, and `est N s`
  EST-ARITH   spec carries the estimate arithmetic (estimate_justification/notes with a `x`/`*` product)
  PRED-PATH   smoke_predicate, check_complete.py and --complete-cmd reference only paths in the row dir
  CPU-GPUTHR  a CPU-lane row uses cpus 88-95 / 184-191 (MI210 host threads)
  WIDTH       claimed physical cores exceed ceil(literal threads / 24) quarters (launch.sh / spec)
  SEAL        SOURCE.sha256 missing, or a listed file's hash no longer matches
  ID          launch.sh --id differs from spec id
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys

GPU_HOST = set(range(88, 96)) | set(range(184, 192))
PATH_RE = re.compile(r"/mnt/raid0/llm/tmp/[A-Za-z0-9._/-]+")
ALLOWED_OUTSIDE = ("/mnt/raid0/llm/tmp/compute-flags/",)


def cpus(spec: str) -> set[int]:
    out: set[int] = set()
    for part in (spec or "").split(","):
        part = part.strip()
        m = re.fullmatch(r"(\d+)-(\d+)", part)
        q = re.fullmatch(r"q([0-3])", part)
        if q:
            out |= set(range(24 * int(q[1]), 24 * int(q[1]) + 24))
        elif m:
            out |= set(range(int(m[1]), int(m[2]) + 1))
        elif part.isdigit():
            out.add(int(part))
    return out


def foreign_paths(text: str, rowdir: str) -> list[str]:
    rowdir = rowdir.rstrip("/") + "/"
    bad = []
    for p in PATH_RE.findall(text or ""):
        if p.rstrip("/") + "/" == rowdir or p.startswith(rowdir) or p.startswith(ALLOWED_OUTSIDE):
            continue
        bad.append(p)
    return sorted(set(bad))


def find_box(text: str, box_id: str) -> str | None:
    lines = text.splitlines()
    cands = [i for i, ln in enumerate(lines) if re.match(r"\s*[-*] \[[ xX]\]", ln) and box_id in ln]
    bold = [i for i in cands if re.search(r"\*\*" + re.escape(box_id) + r"\b", lines[i])]
    for i in (bold or cands)[:1]:
        ln = lines[i]
        if True:
            j = i + 1
            while j < len(lines) and lines[j].startswith(("  ", "\t")) and not re.match(r"\s*[-*] \[", lines[j]):
                j += 1
            return "\n".join(lines[i:j])
    return None


def lint_box(box: str | None, box_id: str) -> list[str]:
    if box is None:
        return [f"BOX-MISSING: no checkbox for {box_id}"]
    errs = []
    if not re.search(r"\*\*[A-Z0-9][A-Za-z0-9._-]*(\*\*|\s)", box.splitlines()[0]):
        errs.append("BOX-ID: first line has no bold **ID**")
    if "model:" not in box:
        errs.append("BOX-MODEL: no `model:`")
    if not re.search(r"(?i)\bstop[- ](rule|on)|stop-on|\bSTOP\b", box):
        errs.append("BOX-STOP: no stop rule")
    if not re.search(r"\best\.?\s*~?\s*\d+\s*s\b", box):
        errs.append("BOX-EST: no `est N s`")
    return errs


def lint_seal(rowdir: str) -> list[str]:
    p = os.path.join(rowdir, "SOURCE.sha256")
    if not os.path.exists(p):
        return ["SEAL: SOURCE.sha256 missing"]
    errs = []
    for ln in open(p):
        parts = ln.split()
        if len(parts) != 2:
            continue
        h, name = parts
        f = os.path.join(rowdir, name.lstrip("*"))
        if not os.path.exists(f):
            errs.append(f"SEAL: {name} listed but missing")
        elif hashlib.sha256(open(f, "rb").read()).hexdigest() != h:
            errs.append(f"SEAL: {name} changed since sealed (reseal after review)")
    return errs


def literal_threads(launch: str, spec: dict) -> int | None:
    vals = [int(x) for x in re.findall(r"(?:-t|--threads|--gpu-threads-n)\s+(\d+)\b", launch)]
    if spec.get("declared_threads"):
        vals.append(int(spec["declared_threads"]))
    return max(vals) if vals else None


def lint(rowdir: str, box_file: str | None = None, repo: str = "/workspace") -> list[str]:
    rowdir = os.path.abspath(rowdir)
    errs: list[str] = []
    sp = os.path.join(rowdir, "spec.json")
    if not os.path.exists(sp):
        return ["SPEC: spec.json missing"]
    spec = json.load(open(sp))
    launch = open(os.path.join(rowdir, "launch.sh")).read() if os.path.exists(os.path.join(rowdir, "launch.sh")) else ""
    # ID
    m = re.search(r"--id\s+([A-Za-z0-9._-]+)", launch)
    if m and m[1] != spec.get("id"):
        errs.append(f"ID: launch.sh --id {m[1]} != spec id {spec.get('id')}")
    # EST arithmetic
    just = " ".join(str(spec.get(k, "")) for k in ("estimate_justification", "notes"))
    if not spec.get("estimate_s") or not re.search(r"\d[\w .~]{0,20}?\s(x|×|\*)\s*~?\d|\d\s*(x|×|\*)\s*~?\d", just):
        errs.append("EST-ARITH: estimate_s without `units x rate` arithmetic in estimate_justification/notes")
    # predicate / completion provenance
    texts = {"smoke_predicate": spec.get("smoke_predicate", "")}
    cc = os.path.join(rowdir, "check_complete.py")
    if os.path.exists(cc):
        texts["check_complete.py"] = open(cc).read()
    cm = re.search(r"--complete-cmd\s+\"([^\"]+)\"", launch)
    if cm:
        texts["--complete-cmd"] = cm[1].replace("$D", rowdir)
    for name, t in texts.items():
        for p in foreign_paths(t, rowdir):
            errs.append(f"PRED-PATH: {name} references {p} outside the row dir")
    # CPU lane must not touch MI210 host threads
    lane = spec.get("lane", "")
    claimed = cpus(spec.get("claim_cpus") or "") | cpus(re.sub(r"mi210_\d+,?", "", spec.get("regions", "")))
    if lane == "cpu" and claimed & GPU_HOST:
        errs.append(f"CPU-GPUTHR: cpu lane claims {sorted(claimed & GPU_HOST)[:4]}… (88-95/184-191 are MI210 host threads)")
    # width
    thr = literal_threads(launch, spec)
    phys = {c for c in claimed if c < 96}
    if thr and lane == "cpu" and phys:
        quarters = {c // 24 for c in phys}
        need = math.ceil(thr / 24)
        if len(quarters) > need and not spec.get("width_justification"):
            errs.append(f"WIDTH: {len(quarters)} quarters claimed for {thr} literal threads (need {need})")
    errs += lint_seal(rowdir)
    # box
    ht = spec.get("handoff_task", "")
    if ":" in ht:
        fname, box_id = ht.split(":", 1)
        path = box_file or os.path.join(repo, "handoffs/active", fname)
        if os.path.exists(path):
            errs += lint_box(find_box(open(path).read(), box_id), box_id)
        else:
            errs.append(f"BOX-MISSING: {path} not found")
    else:
        errs.append("BOX-MISSING: spec.handoff_task is not file.md:ID")
    return errs


LAUNCH_T = """#!/bin/bash
# {id} ({owner}, {handoff}:{box}). Threads literal: {threads}.
set -euo pipefail
D={dir}
C={regions}
cd "$D"
ulimit -c 0
/usr/bin/sha256sum --check --status SOURCE.sha256
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id {id} \\
  --class {lane} --claim-cpus "$C" --role bench --min-window {minw} \\
  --cmd "/usr/bin/python3 -I -B $D/job.py" \\
  --complete-cmd "/usr/bin/python3 -I -B $D/check_complete.py" \\
  --stop "$D/STOP" --workdir "$D"
"""
JOB_T = '''#!/usr/bin/python3
"""{id}
QUESTION  {model}
          TODO: the one question this row answers.
SOURCE    TODO: binary/tree + content proof (sha / symbol).
STEPS     TODO: units ({units} x ~{unit_s} s).
RULE      TODO: pre-registered, first match wins. RESULT.json carries ONE polar token per row:
          "polar": "PASS" | "FAIL" (beside the named answer in "verdict"); a futility outcome is split:
          FUTILITY_HARNESS_<WHY> (instrument/harness/input, candidate not judged -> inconclusive) vs
          FUTILITY_CANDIDATE_<WHY> (a measured negative about the candidate -> fail). gate_eval reads these.
          No finished RESULT -> no claim: the row files SUPERSEDED/WITHDRAWN, never inconclusive.
STOP      on-answer: TODO. on-futility: TODO. rc 75 only on STOP file / FILLER_DEADLINE.
"""
{gpu_block}raise SystemExit("TODO: implement job (write out/results.jsonl and out/RESULT.json with complete, verdict, polar)")
'''
RESEARCH_REPO = "/mnt/raid0/llm/epyc-inference-research"  # shared clone: fetch + `git show` only, never its tree/branch/index
HARNESS_PATH = "scripts/kernel_rnd/autokernel/harness"
HARNESS_FILES = ("gpu_common.py", "gpuproof_row.py")
GPU_JOB_T = '''
# GPU lane: the canonical row helpers were copied INTO this row dir by row_scaffold.py from research {gpu_ref} @ {gpu_commit}
# ({harness_path}); never hand-edit them. The sha256 pins below are checked at start, so an edited copy is a
# FUTILITY_HARNESS_MISSING_INPUT, not a silent change. Both files are also listed in SOURCE.sha256.
import hashlib, os, sys
ROW_DIR = os.path.dirname(os.path.abspath(__file__))
GPU_COMMON_SHA256 = "{gpu_common_sha}"
GPUPROOF_ROW_SHA256 = "{gpuproof_row_sha}"
for _n, _s in (("gpu_common.py", GPU_COMMON_SHA256), ("gpuproof_row.py", GPUPROOF_ROW_SHA256)):
    if hashlib.sha256(open(os.path.join(ROW_DIR, _n), "rb").read()).hexdigest() != _s:
        raise SystemExit(f"FUTILITY_HARNESS_MISSING_INPUT: {{_n}} sha256 differs from the scaffold pin")
sys.path.insert(0, ROW_DIR)
import gpu_common as G  # noqa: E402  (residency_from_proof gates < 2 s children on the in-process witness + LD_DEBUG proof)
'''


def fetch_harness(repo: str, ref: str = "origin/main") -> tuple[str, dict[str, bytes]] | str:
    """(commit, {name: bytes}) for HARNESS_FILES at `ref` of `repo`, via `git fetch` + `git show` only (never touches the
    working tree, branch or index). Returns an error string on failure."""
    import subprocess
    remote, _, branch = ref.partition("/")
    f = subprocess.run(["git", "-C", repo, "fetch", "-q", remote, branch], capture_output=True, text=True)
    if f.returncode != 0:
        return f"git fetch {remote} {branch} failed: {f.stderr.strip()[:200]}"
    c = subprocess.run(["git", "-C", repo, "rev-parse", "--verify", ref + "^{commit}"], capture_output=True, text=True)
    if c.returncode != 0:
        return f"{ref} not resolvable in {repo}"
    out = {}
    for n in HARNESS_FILES:
        r = subprocess.run(["git", "-C", repo, "show", f"{ref}:{HARNESS_PATH}/{n}"], capture_output=True)
        if r.returncode != 0:
            return f"{ref}:{HARNESS_PATH}/{n} missing"
        out[n] = r.stdout
    return c.stdout.strip(), out


CHECK_T = '''#!/usr/bin/python3
"""rc 0 iff THIS row's out/RESULT.json is complete with a terminal verdict AND one polar token; smoke never counts.
Polar token: "polar": "PASS"|"FAIL", or a split futility verdict FUTILITY_HARNESS_* / FUTILITY_CANDIDATE_*."""
import json, sys
try:
    r = json.load(open("{dir}/out/RESULT.json"))
except (OSError, ValueError):
    sys.exit(1)
v = str(r.get("verdict") or "")
polar = str(r.get("polar") or "").upper() in ("PASS", "FAIL") or v.startswith(("FUTILITY_HARNESS", "FUTILITY_CANDIDATE"))
sys.exit(0 if r.get("complete") is True and polar and v.startswith(("PASS", "KEEP", "DROP", "FAIL", "FUTILITY")) else 1)
'''


def seal(rowdir: str, names: list[str]) -> None:
    with open(os.path.join(rowdir, "SOURCE.sha256"), "w") as f:
        for n in names:
            f.write(f"{hashlib.sha256(open(os.path.join(rowdir, n), 'rb').read()).hexdigest()}  {n}\n")


ESTIMATE_HISTORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", "..", "scripts", "coordination", "rowflow")


def history_suggestion(row_id: str, units: int | None = None, flags: str | None = None):
    """estimate_history.suggest() for this row's family, or None (no / too little history)."""
    sys.path.insert(0, os.path.normpath(ESTIMATE_HISTORY_DIR))
    try:
        import estimate_history
    finally:
        sys.path.pop(0)
    kw = {"flags": flags} if flags else {}
    return estimate_history.suggest(row_id, units=units, **kw)


def resolve_estimate(a) -> tuple:
    """(estimate_s, justification). A measured `--units x --unit-s` always wins; without it the
    default is estimate-from-history (family p75 x 1.25, or units x per-unit p75 x 1.25)."""
    if a.units and a.unit_s:
        est = math.ceil(a.units * a.unit_s * 1.25)
        return est, f"{a.units} units x {a.unit_s} s measured x 1.25 margin = {est} s"
    sug = history_suggestion(a.row_id, a.units, getattr(a, "flags", None))
    if not sug:
        return None, ("no measured estimate (--units N --unit-s S) and no estimate-from-history "
                      "for this row family (needs >= 3 completed runs)")
    return sug["estimate_s"], sug["estimate_justification"]


def scaffold(a) -> int:
    d = os.path.join(a.root, a.row_id)
    if os.path.exists(d):
        print(f"REFUSED: {d} exists")
        return 1
    if a.lane == "cpu" and cpus(a.regions) & GPU_HOST:
        print("REFUSED: cpu lane regions touch 88-95/184-191")
        return 1
    harness, got = {}, None
    if a.lane == "gpu":  # resolve the canonical harness BEFORE creating anything, so a refusal leaves no dir behind
        got = fetch_harness(a.research_repo, a.research_ref)
        if isinstance(got, str):
            print(f"REFUSED: canonical gpu_common.py: {got}")
            return 1
    est, just = resolve_estimate(a)
    if est is None:
        print(f"REFUSED: {just}")
        return 1
    os.makedirs(os.path.join(d, "out"))
    fmt = dict(id=a.row_id, owner=a.owner, handoff=a.handoff, box=a.box, threads=a.threads, dir=d,
               regions=a.regions, lane=a.lane, minw=math.ceil(est * 0.8), model=a.model, units=a.units or '?', unit_s=a.unit_s or '?', gpu_block="")
    if a.lane == "gpu":
        commit, harness = got
        for n, b in harness.items():
            with open(os.path.join(d, n), "wb") as f:
                f.write(b)
        sh = {n: hashlib.sha256(b).hexdigest() for n, b in harness.items()}
        fmt["gpu_block"] = GPU_JOB_T.format(gpu_ref=a.research_ref, gpu_commit=commit, harness_path=HARNESS_PATH,
                                            gpu_common_sha=sh["gpu_common.py"], gpuproof_row_sha=sh["gpuproof_row.py"])
    for name, t, mode in (("launch.sh", LAUNCH_T, 0o755), ("job.py", JOB_T, 0o755), ("check_complete.py", CHECK_T, 0o755)):
        with open(os.path.join(d, name), "w") as f:
            f.write(t.format(**fmt))
        os.chmod(os.path.join(d, name), mode)
    spec = {"owner": a.owner, "schema": "epyc.row.v3", "kind": "compute", "lane": a.lane, "id": a.row_id,
            "regions": a.regions, "claim_cpus": a.regions, "verdict_by": "agent",
            "launcher": f"{d}/launch.sh", "result_path": f"{d}/out/RESULT.json", "result_format": "json",
            "scratch_root": d, "workdir": d, "stop_file": f"{d}/STOP", "estimate_s": est,
            "min_window_s": math.ceil(est * 0.8), "declared_threads": a.threads,
            "estimate_justification": just,
            "handoff_task": f"{os.path.basename(a.handoff)}:{a.box}", "model": a.model,
            "smoke_predicate": f"/usr/bin/test -s {d}/out/TERMINAL-smoke.json",
            "decision_rule": "see job.py docstring (RULE)", "notes": f"scaffolded by row_scaffold.py for {a.owner}"}
    with open(os.path.join(d, "spec.json"), "w") as f:
        json.dump(spec, f, indent=1)
    seal(d, ["job.py", "check_complete.py", "launch.sh", "spec.json"] + sorted(harness))
    print(f"SCAFFOLDED {d} estimate_s={est}; fill job.py TODOs, reseal (row_scaffold.py --seal {d}), then --lint")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lint", metavar="ROWDIR")
    ap.add_argument("--box-file")
    ap.add_argument("--repo", default="/workspace")
    ap.add_argument("--seal", metavar="ROWDIR", help="rewrite SOURCE.sha256 over the files it already lists")
    sub = ap.add_subparsers(dest="cmd")
    n = sub.add_parser("new")
    n.add_argument("row_id")
    n.add_argument("--handoff", required=True)
    n.add_argument("--box", required=True)
    n.add_argument("--lane", choices=["cpu", "gpu"], required=True)
    n.add_argument("--regions", required=True)
    n.add_argument("--threads", type=int, required=True)
    n.add_argument("--units", type=int, help="units of work; with --unit-s a measured estimate")
    n.add_argument("--unit-s", type=float, help="measured seconds per unit; omit to default to estimate-from-history")
    n.add_argument("--flags", help="compute-flags root for estimate-from-history (default: the live one)")
    n.add_argument("--model", required=True)
    n.add_argument("--owner", default="autokernel")
    n.add_argument("--root", default="/mnt/raid0/llm/tmp")
    n.add_argument("--research-repo", default=RESEARCH_REPO, help="gpu lane: repo to fetch the canonical harness from (fetch + show only)")
    n.add_argument("--research-ref", default="origin/main", help="gpu lane: remote ref holding the canonical harness")
    a = ap.parse_args(argv)
    if a.cmd == "new":
        return scaffold(a)
    if a.seal:
        names = [ln.split()[1].lstrip("*") for ln in open(os.path.join(a.seal, "SOURCE.sha256")) if len(ln.split()) == 2]
        seal(a.seal, names)
        print(f"SEALED {len(names)} files")
        return 0
    if a.lint:
        errs = lint(a.lint, a.box_file, a.repo)
        for e in errs:
            print(f"LINT {e}")
        print("LINT OK" if not errs else f"LINT {len(errs)} problem(s)")
        return 1 if errs else 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
