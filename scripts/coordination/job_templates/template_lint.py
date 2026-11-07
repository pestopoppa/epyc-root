#!/usr/bin/python3
"""Publish-time WARN-only lint: does a row's job dir vendor a lane template (write_fence.py / smoke_admission.py /
smoke_root_exec.py) that does not import the shared job_templates/job_fence.py, or a one-process gitnexus-impact
job.py instead of job_templates/gitnexus_impact.py? Never refuses.

Delete lens: a hand-harvested SHA list protected only against the copies harvested on 2026-11-06; the name-based
rule catches those and every copy never harvested.

  template_lint.py <launcher-or-job-dir>      # prints one WARN per finding, exit 0 always
Used by rowflow2.publish (rowflow/publish_row.py is frozen; operator 2026-11-06).
"""
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


def lint_dir(path):
    """WARN strings for the job dir of `path` (a launcher file or a directory)."""
    p = Path(path)
    root = p if p.is_dir() else p.parent
    if not root.is_dir():
        return []
    warns, seen = [], 0
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith((".", "out", "smoke-", "gitnexus-home", "__pycache__"))]
        for n in files:
            seen += 1
            if seen > MAX_FILES:
                return warns
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
                tw = thread_warn(f, t)
                if tw:
                    warns.append(tw)
                if not n.endswith(".py"):
                    continue
                if ("gitnexus" in t and ("analyze" in t or "gitnexus-writer" in t) and '"impact"' in t
                        and "gitnexus_impact" not in t):
                    warns.append(f"template-lint: {f} is a vendored gitnexus-impact job (analyze+scan in one process); "
                                 "use compute-flags/bin/job_templates/gitnexus_impact.py --phase analyze|scan")
    return warns


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    for a in argv:
        for w in lint_dir(a):
            print("WARN " + w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
