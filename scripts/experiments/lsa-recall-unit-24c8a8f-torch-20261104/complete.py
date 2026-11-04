#!/usr/bin/env python3
import json
from pathlib import Path

here = Path(__file__).resolve().parent
result = json.loads((here / 'RESULT.json').read_text())
assert result['schema'] == 'lsa-recall-unit-binding-v1'
assert result['source_commit'] == '24c8a8f2aa7cb4800fe4637151aaa5e149a7af71'
assert result['kind'] == 'unit-suite' and result['status'] == 'pass' and result['rc'] == 0
