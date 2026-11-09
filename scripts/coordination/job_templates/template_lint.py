#!/usr/bin/python3
"""Publish-time WARN-only lint: does a row's job dir vendor a lane template (write_fence.py / smoke_admission.py /
smoke_root_exec.py) that does not import the shared job_templates/job_fence.py, or a one-process gitnexus-impact
job.py instead of job_templates/gitnexus_impact.py? Never refuses.

Delete lens: a hand-harvested SHA list protected only against the copies harvested on 2026-11-06; the name-based
rule catches those and every copy never harvested.

  template_lint.py <launcher-or-job-dir>      # prints one WARN per finding, exit 0 always
NIB2-98: a row manifest declaring gib/ram_gib >= 100 whose job files never reference the shared RAM admission
(job_fence.py --need-ram-gib / `job_fence.py ram` / JOB_FENCE_NEED_RAM_GIB) gets a WARN.
Used by rowflow2.publish (rowflow/publish_row.py is frozen; operator 2026-11-06).
"""
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FENCE_NAMES = ("write_fence.py", "smoke_admission.py", "smoke_root_exec.py")
MAX_FILES = 400


THREAD_VARS = ("OMP_NUM_THREADS", "AUTOKERNEL_BACKEND_THREADS", "AUTOKERNEL_CPU_N_THREADS", "GGML_N_THREADS",
               "LLAMA_ARG_THREADS")
BIN_RE = re.compile(r"test-backend-ops|llama-(?:bench|cli|server|perplexity|batched-bench|speculative|cvector-generator"
                    r"|[a-z-]+)")
T_RE = re.compile(r"(?:^|[\s'\"\[,])(?:-t|--threads)(?:[\s='\",\]]|$)")


def thread_warn(path, text):
    """WARN when a job file invokes test-backend-ops / llama-* with no -t and no thread env var (ggml defaults to
    hardware_concurrency()=192 and ignores affinity). job_fence.py fence/smoke sets the env defaults itself."""
    if not BIN_RE.search(text) or "job_fence" in text or any(v in text for v in THREAD_VARS) or T_RE.search(text):
        return None
    return (f"template-lint: {path} runs test-backend-ops/llama-* without -t or a thread env var "
            f"({'/'.join(THREAD_VARS[:2])}/..); ggml defaults to 192 threads and ignores affinity. "
            "Run under job_templates/job_fence.py or pass -t <affinity CPUs>")


def manifest_warns(root):
    """WARN-only: a row manifest (top-level *.json with schema epyc.row.v3 or an id) with no numeric budget_gib / no
    raw declaration. No manifest found = nothing to say."""
    out = []
    try:
        names = sorted(n for n in os.listdir(root) if n.endswith(".json"))[:50]
    except OSError:
        return out
    for n in names:
        try:
            d = json.loads((Path(root) / n).read_text(errors="replace"))
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict) or not (d.get("schema") == "epyc.row.v3" or "id" in d):
            continue
        b = d.get("budget_gib")
        if isinstance(b, bool) or not isinstance(b, (int, float)):
            out.append("budget_gib missing: row declares no disk budget "
                       "(DEFAULT 1 GiB is enforced/alerted by row_disk_budget.py)")
        if not d.get("raw") and "raw_globs=" not in str(d.get("notes") or ""):
            out.append("raw declaration missing: no 'raw' list and no raw_globs= in notes, so nothing is reclaimed "
                       "at filing (keeper 1-day backstop only)")
        break
    return out


RAM_ADMIT_TOKENS = ("--need-ram-gib", "JOB_FENCE_NEED_RAM_GIB", "--need-gib", "ram_admit")
BIG_RAM_GIB = 100


def big_ram_gib(root):
    """The declared gib/ram_gib (>= BIG_RAM_GIB) of the first row manifest in root, else None."""
    try:
        names = sorted(n for n in os.listdir(root) if n.endswith(".json"))[:50]
    except OSError:
        return None
    for n in names:
        try:
            d = json.loads((Path(root) / n).read_text(errors="replace"))
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict) or not (d.get("schema") == "epyc.row.v3" or "id" in d):
            continue
        for k in ("ram_gib", "gib"):
            v = d.get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v >= BIG_RAM_GIB:
                return v
        return None
    return None


def ram_admission_warn(root, texts):
    """WARN-only: a big-RAM row (>= 100 GiB declared) whose job files never reference the load-time RAM admission."""
    gib = big_ram_gib(root)
    if gib is None or any(tok in t for t in texts for tok in RAM_ADMIT_TOKENS):
        return None
    return (f"template-lint: row declares {gib:g} GiB but no job file references the load-time RAM admission "
            "(job_templates/job_fence.py fence/smoke --need-ram-gib N, or `job_fence.py ram --need-gib N`); the grant-time "
            "check is not atomic with the load and uses a 64 GiB margin, the ratified rule is 100 GiB (NIB2-98)")


def lint_dir(path):
    """WARN strings for the job dir of `path` (a launcher file or a directory)."""
    p = Path(path)
    root = p if p.is_dir() else p.parent
    if not root.is_dir():
        return []
    warns, seen, texts = manifest_warns(root), 0, []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith((".", "out", "smoke-", "gitnexus-home", "__pycache__"))]
        for n in files:
            seen += 1
            if seen > MAX_FILES:
                break
            f = Path(dirpath) / n
            if n in FENCE_NAMES:
                try:
                    t = f.read_text(errors="replace")
                except OSError:
                    continue
                if "job_fence" not in t:
                    warns.append(f"template-lint: {f} is a vendored fence/smoke copy that does not import "
                                 "job_templates/job_fence.py; import compute-flags/bin/job_templates/job_fence.py")
            elif n.endswith((".py", ".sh")):
                try:
                    t = f.read_text(errors="replace")
                except OSError:
                    continue
                texts.append(t)
                tw = thread_warn(f, t)
                if tw:
                    warns.append(tw)
                if not n.endswith(".py"):
                    continue
                if ("gitnexus" in t and ("analyze" in t or "gitnexus-writer" in t) and '"impact"' in t
                        and "gitnexus_impact" not in t):
                    warns.append(f"template-lint: {f} is a vendored gitnexus-impact job (analyze+scan in one process); "
                                 "use compute-flags/bin/job_templates/gitnexus_impact.py --phase analyze|scan")
        else:
            continue
        break
    rw = ram_admission_warn(root, texts)
    if rw:
        warns.append(rw)
    return warns


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    for a in argv:
        for w in lint_dir(a):
            print("WARN " + w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
