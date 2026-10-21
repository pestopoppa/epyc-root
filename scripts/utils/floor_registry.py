#!/usr/bin/env python3
"""floor_registry.py -- launcher-side entry point of the serving-floor registry.

The implementation lives in the RESEARCH repo (`scripts/kernel_rnd/autokernel/loop/floor_registry.py`)
because the AutoKernel campaign imports it (`run.py --floor-registry`) and research must not import
from root. It is stdlib-only with no relative imports, so this shim loads it BY FILE PATH and runs
its CLI unchanged. Gates and launchers that live in root (or in /tmp scratch dirs, e.g.
`gate_1017.py`) call:

    scripts/utils/floor_registry.py check-launch --build kernels/builds/<name> --floor <any floor json of the recipe> \
        --numerics-epoch <label> --require-grade decision --owner <session>
        exit 0  = reuse (floor path printed; --write-floor OUT.json extracts it)
        exit 10 = calibrate (you now hold the condition's claim; run the A/A once, then `register`)
        exit 11 = claimed by another launcher (wait for its floor; do not calibrate)
        exit 3  = refused (stale anchor / corrupt entry / bad input)

Override the research checkout with EPYC_RESEARCH_REPO. Contract and era rules: see the module
docstring (`floor_registry.py --help`).
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

REL = Path("scripts/kernel_rnd/autokernel/loop/floor_registry.py")


def _locate() -> Path:
    here = Path(__file__).resolve()
    roots = [Path(os.environ["EPYC_RESEARCH_REPO"])] if os.environ.get("EPYC_RESEARCH_REPO") else []
    roots += [Path("/workspace/repos/epyc-inference-research"),
              Path("/mnt/raid0/llm/epyc-inference-research"), here.parents[2] / "repos" / "epyc-inference-research"]
    for root in roots:
        if (root / REL).is_file():
            return root / REL
    raise SystemExit(f"floor_registry: research implementation {REL} not found "
                     f"(set EPYC_RESEARCH_REPO); searched {[str(r) for r in roots]}")


def main() -> int:
    spec = importlib.util.spec_from_file_location("floor_registry_impl", _locate())
    module = importlib.util.module_from_spec(spec)
    sys.modules["floor_registry_impl"] = module  # dataclasses need the module registered
    spec.loader.exec_module(module)
    return module.main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
