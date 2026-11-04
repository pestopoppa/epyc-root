#!/usr/bin/env python3
"""Strict publisher smoke and full completion predicate."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from job import sha, verify
D = Path(__file__).resolve().parent
x = json.loads((D / 'RESULT.json').read_text())
assert not (D / 'INCOMPLETE.json').exists()
assert x['schema'] == 'p5.candidate-pii-controls.v1' and x['status'] == 'COMPLETE'
assert x['pytest_exit'] == 0
assert x['junit_counts'] == {'tests': 7, 'failures': 0, 'errors': 0, 'skipped': 0}
assert x['testcases'] == 7
assert x['sources_verified_pre_post'] is True and x['test_repositories_removed'] is True
assert not (D / 'pytest-tmp').exists()
assert not list((D / 'control-tmp').rglob('.git'))
assert x['sources'] == verify()['sources']
for name, key in [('pins.json', 'pins_sha256'), ('launch.sh', 'launcher_sha256'),
                  ('SOURCE.sha256', 'source_manifest_sha256'), ('junit.xml', 'junit_sha256')]:
    assert sha(D / name) == x[key]
r = ET.parse(D / 'junit.xml').getroot()
cases = r.findall('.//testcase')
assert len(cases) == 7
assert all(c.find(k) is None for c in cases for k in ('failure', 'error', 'skipped'))
assert len({c.attrib['name'] for c in cases}) == 7
