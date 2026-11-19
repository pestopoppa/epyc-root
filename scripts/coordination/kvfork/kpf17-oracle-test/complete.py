#!/usr/bin/env python3
"""A sealed INVALID is a completed diagnostic, not a passing result."""
import json
from pathlib import Path
import sys
import custody
D=Path(__file__).resolve().parent
try:
    result=json.loads((D/'out/RESULT.json').read_text());binding=json.loads((D/'binding.json').read_text())
    assert result['schema']=='kpf17.oracle-test.v1' and result['sealed'] and not result['smoke']
    assert result['status'] in ('PASS','INVALID') and result['process_verified_dead']
    assert result['build']==binding['build'] and result['model']==binding['model']
    assert all(custody.digest(p)==h for p,h in result['files'].items())
except (OSError,ValueError,KeyError,TypeError,AssertionError):sys.exit(1)
