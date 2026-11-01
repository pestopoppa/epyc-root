#!/usr/bin/env python3
"""One-cell dry-run boundary for a proposed E1-MEM v15 same-entry job.

Pure driver: it does not load a model, write an output, or authorize execution.
The caller supplies the actual cell executor and an exact completion predicate.
"""
import time
from pathlib import Path

STEPS = (('E1','A0','low'), ('W','A0','low'), ('E1','A1','low'),
         ('W','A1','low'), ('E1','A1','high'), ('W','A1','high'))

def drive(run_cell, complete, stop_path, deadline, *, dryrun=False, now=time.time, safety_s=300):
    """Return 0 only when all six cells completed; 75 means safely partial.

    In dry-run one new fully validated cell is the limit even if the keeper has
    not yet observed it and written its stop file. A failure or stop while a
    native cell is active is the executor's responsibility and must return its
    real status; the driver never marks that cell completed.
    """
    for step in STEPS:
        if complete(step):
            continue
        if Path(stop_path).exists() or now() >= deadline-safety_s:
            return 75
        rc = run_cell(*step)
        if rc:
            return rc
        if not complete(step):
            return 70
        if dryrun:
            return 75
        if Path(stop_path).exists() or now() >= deadline-safety_s:
            return 75
    return 0
