#!/usr/bin/env python3
"""Set an exact inherited CPU mask before exec; prototype, not native entry."""
import os
import sys
from admission import parse_cpus

def main():
    if len(sys.argv) < 4 or sys.argv[2] != '--':
        raise SystemExit('expected CPU-LIST -- COMMAND [ARGS]')
    cpus = parse_cpus(sys.argv[1])
    if not cpus.issubset(os.sched_getaffinity(0)):
        raise SystemExit('allocation exceeds inherited affinity')
    os.sched_setaffinity(0, cpus)
    if os.sched_getaffinity(0) != cpus:
        raise SystemExit('kernel did not apply exact allocation')
    os.execvpe(sys.argv[3], sys.argv[3:], os.environ)

if __name__ == '__main__':
    main()
