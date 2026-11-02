import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_unscoped_fact_ingests_but_is_not_presented(tmp_path):
    out = tmp_path / 'canary'
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/vidya/repl_trace_facts_negative_canary.py'),
                             '--out', str(out)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    receipt = json.loads((out / 'receipt.json').read_text())
    assert receipt['rows_projected'] == 1
    assert receipt['negative_control'] == 'passed'
    assert receipt['wired'] is False
    assert receipt['evidence_status'] == 'omitted'
    assert receipt['evidence_reasons'] == ['no_applicable_claims']
    assert receipt['visible_claims'] == 0
