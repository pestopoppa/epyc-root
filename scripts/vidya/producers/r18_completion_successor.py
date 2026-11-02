#!/usr/bin/env python3
"""Report completion only for an eligible, producer-authored terminal finding."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / 'r18_inputs'))
import replay_evidence as evidence
p = Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/r18a-verified-anchor-20261031/belief-successor-20261102/scratch/full')
try:
    result = json.loads((p/'full-result.json').read_text())
    native = json.loads((p/'symbol-identity.json').read_text())
    before = json.loads((p/'comparison-inputs-before.json').read_text())
    after = json.loads((p/'comparison-inputs-after.json').read_text())
    terminal = json.loads((p/'belief-symbol-finding/terminal.json').read_text())
    rc = result['exit_code']
    assert result['partial'] is False and rc in (0, 1) and before == after
    assert terminal['state'] == 'complete' and terminal['detail']['returncode'] == rc
    assert result['comparison'] == {'rc': rc, 'path': str(p/'symbol-identity.json'), 'sha256': evidence.sha(p/'symbol-identity.json')}
    passed = evidence.validate_comparison(native, rc, after, p/'buildcpu', p/'buildgpu')
    assert result['reason'] == ('independent_cpu_hip_symbol_identity_pass' if passed else 'independent_cpu_hip_symbol_identity_valid_negative')
except (OSError, ValueError, KeyError, TypeError, AssertionError):
    raise SystemExit(1)
