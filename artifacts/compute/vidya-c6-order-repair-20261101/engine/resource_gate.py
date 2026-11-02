#!/usr/bin/env python3
"""In-claim resource proof without the retired row-bound T1 protocol."""
import argparse
from dryrun_check import cpus, limits_record, refuse

p = argparse.ArgumentParser()
p.add_argument('--id', required=True)
p.add_argument('--allowed-cpus', required=True)
p.add_argument('--ram-gib', type=float, required=True)
a = p.parse_args()
try:
    allowed = cpus(a.allowed_cpus)
    if a.ram_gib != 32 or len(allowed) < 1:
        refuse('unexpected RAM envelope or empty grant CPU set')
    limits_record(a.ram_gib, a.ram_gib, allowed, allowed)
    print(f'RESOURCE_PASS id={a.id} scope=normal-grant', flush=True)
except Exception as exc:
    print(f'RESOURCE_REFUSED: {exc}', flush=True)
    raise SystemExit(70)
