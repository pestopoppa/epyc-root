#!/usr/bin/env python3
"""row_scaffold.py — RETIRED 2026-11-24 (RCA ak-row-robustness-rca-20261124 F1: one row generator).

This is a thin shim over scripts/coordination/rowflow/mk_ak_row.py, the ONLY way a row dir comes into being. The
polar/akloop profile that used to live here moved there verbatim; every old invocation keeps working:

  row_scaffold.py --lint <rowdir> [--box-file x.md]   == mk_ak_row.py polar --lint <rowdir> [--box-file x.md]
  row_scaffold.py --seal <rowdir>                     == mk_ak_row.py polar --seal <rowdir>
  row_scaffold.py new <row-id> ...                    == mk_ak_row.py polar new <row-id> ...

New AK measurement rows: use mk_ak_row.py directly (native profile: harness helpers, production-argv smoke,
--served-ref). The names below are re-exported for importers (akloop/chain.py, the skill tests).
"""
from __future__ import annotations

import os
import sys

_ROWFLOW = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "..", "..", "..", "..", "scripts", "coordination", "rowflow"))
if _ROWFLOW not in sys.path:
    sys.path.insert(0, _ROWFLOW)
import mk_ak_row as MK  # noqa: E402

GPU_HOST = MK.GPU_HOST
PATH_RE = MK.PATH_RE
ALLOWED_OUTSIDE = MK.ALLOWED_OUTSIDE
LAUNCH_T, JOB_T, GPU_JOB_T, CHECK_T = MK.LAUNCH_T, MK.JOB_T, MK.GPU_JOB_T, MK.CHECK_T
RESEARCH_REPO, HARNESS_PATH, HARNESS_FILES = MK.RESEARCH_REPO, MK.HARNESS_PATH, MK.HARNESS_FILES
ESTIMATE_HISTORY_DIR = MK.ESTIMATE_HISTORY_DIR
cpus, foreign_paths, find_box, lint_box = MK.cpus, MK.foreign_paths, MK.find_box, MK.lint_box
lint_seal, literal_threads = MK.lint_seal, MK.literal_threads
history_suggestion, resolve_estimate = MK.history_suggestion, MK.resolve_estimate
lint, seal = MK.polar_lint, MK.polar_seal
fetch_harness = MK.fetch_harness


def _fetch(*a, **k):
    return fetch_harness(*a, **k)   # module-global lookup at call time: monkeypatching row_scaffold.fetch_harness works


def scaffold(a) -> int:
    return MK.polar_scaffold(a, _fetch)


def main(argv=None) -> int:
    return MK.polar_main(sys.argv[1:] if argv is None else list(argv), _fetch)


if __name__ == "__main__":
    sys.exit(main())
