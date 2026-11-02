#!/usr/bin/env python3
"""Durable terminal record around the independently guarded native build."""
import json, os, runpy, signal, sys, time, traceback
from pathlib import Path
D = Path(__file__).resolve().parent
B = Path(sys.argv[sys.argv.index('--scratch') + 1]).resolve() if '--scratch' in sys.argv else D / 'scratch' / 'full'
if not B.is_relative_to((D / 'scratch').resolve()):
    raise SystemExit('private scratch required')
B.mkdir(parents=True, exist_ok=True)
def interrupted(signum, frame):
    raise SystemExit(75)
for sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(sig, interrupted)
rc = 70
error = None
try:
    sys.argv[0] = str(D / 'full_build.py')
    runpy.run_path(sys.argv[0], run_name='__main__')
    rc = 0
except SystemExit as exc:
    rc = exc.code if isinstance(exc.code, int) else 70
except BaseException as exc:
    error = ''.join(traceback.format_exception(exc))
    print(error, file=sys.stderr)
finally:
    result = B / 'full-result.json'
    if result.exists():
        try:
            data = json.loads(result.read_text())
        except (OSError, ValueError):
            data = None
    else:
        data = None
    if not isinstance(data, dict):
        data = {'partial': True, 'exit_code': rc, 'reason': 'unhandled_exit', 'error': error}
        tmp = result.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(data, indent=2) + '\n')
        os.replace(tmp, result)
    with (B / 'terminal-events.jsonl').open('a') as f:
        f.write(json.dumps({'schema':'r18a.native-unit.v1', 'kind':'terminal', 'time':time.time(), 'exit_code':rc, 'partial':data.get('partial', True), 'disposition':'UNKNOWN' if data.get('partial',True) else 'SEE_FULL_RESULT', 'result_path':str(result)}) + '\n')
        f.flush(); os.fsync(f.fileno())
sys.exit(rc)
