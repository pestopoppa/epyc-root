#!/usr/bin/env python3
import json
from pathlib import Path
p = Path(__file__).resolve().parent / 'RESULT.json'
try:
    d = json.loads(p.read_text())
    assert d['schema'] == 'epyc.kvu16h.native-lifecycle.v1'
    assert d['status'] == 'ok' and len(d['results']) == 2
    assert d['results'][0]['server_no_draft'] is True
    pids = [r['cleanup']['pid'] for r in d['results']]
    assert len(set(pids)) == 2
    for r in d['results']:
        assert r['status'] == 'ok' and r['cleanup']['dead'] is True and r['cleanup']['completed'] is True
except (OSError, ValueError, KeyError, AssertionError):
    raise SystemExit(1)
