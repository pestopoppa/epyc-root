#!/usr/bin/env python3
"""Qualification-only synthetic bindings; retained implementation is unchanged."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys

D = Path(__file__).resolve().parent
fixture = Path(sys.argv[1])
anchor = sys.argv[2]
spec = importlib.util.spec_from_file_location('retained_anchor', D/'retained/anchor_preflight.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
# Only test bindings differ. No production model/admission path is traversed.
module.ROOT = fixture
module.PACKET = fixture/'packet'
module.ANCHOR = anchor
module.EXTERNAL = {str(fixture/'admission'/name)
                   for name in ('seals.json', 'check_models.py', 'models.stat.json')}
sys.argv = [str(D/'retained/anchor_preflight.py')]
try:
    with contextlib.redirect_stdout(io.StringIO()) as output:
        module.main()
    print(json.dumps({'kind':'accepted','payload':json.loads(output.getvalue())},sort_keys=True))
except Exception as exc:
    print(json.dumps({'kind':'refused','type':type(exc).__name__,
                      'message':str(exc) if not isinstance(exc,OSError) else None,
                      'errno':exc.errno if isinstance(exc,OSError) else None},sort_keys=True))
    raise SystemExit(2)
