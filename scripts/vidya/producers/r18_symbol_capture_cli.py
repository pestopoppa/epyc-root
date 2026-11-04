#!/usr/bin/env python3
import sys
from pathlib import Path
import r18_symbol_capture as c
out=Path(sys.argv[1])
try:
    c.complete(out, int(sys.argv[2]), Path(__file__).with_name('r18_symbol_sets.py'))
except BaseException as exc:
    if (out/'begin.json').exists() and not (out/'terminal.json').exists():
        c.terminal(out, 'failed', {'error': repr(exc)})
    raise
