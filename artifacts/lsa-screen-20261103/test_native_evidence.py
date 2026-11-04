import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts' / 'vidya'))
import claim_tuple
from adapters import research_screen
from native_evidence import emit


def test_failure_capture_and_projection(tmp_path):
    item = {'id': 'synthetic', 'split': 'dev', 'nominal': 8192}
    manifest = {'rows': [item], 'arms': ['dense'], 'model': 'synthetic-fixture.gguf', 'model_sha256': 'a' * 64}
    manifest_path = tmp_path / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest))
    record = {'schema': 'lsa-screen-raw-v1', 'item': item, 'arm': 'dense',
              'status': 'failure', 'reason': 'synthetic failure',
              'time_utc': datetime.now(timezone.utc).isoformat(),
              'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
              'binding': {'effective_config': {'synthetic': True}, 'source_commit': 'fixture'},
              'output': None}
    output = tmp_path / 'result.json'
    output.write_text(json.dumps(record))
    receipt = emit(record, manifest_path, output)
    native = research_screen.native_rows(receipt)[0]
    claim = research_screen.project(native)
    assert claim.metric == 'lsa_item_passed' and claim.value == 0 and claim.extra['counts']['failure'] == 1
    assert claim.extra['window']['kind'] == 'diagnostic'
    assert claim.protocol_id == '' and claim_tuple.grade(claim)[:2] == ('Judged', 'Located')
    assert json.loads(Path(claim.extra['raw_outputs']['path']).read_text())['original'] == record
    import subprocess
    import loop_beliefs
    class Sync:
        def status(self, *args, **kwargs):
            return {'fresh': True, 'lag_entries': 0, 'index_max_id': 1, 'synced_max_id': 1,
                    'last_sync': datetime.now(timezone.utc).isoformat()}
    asof = datetime.now(timezone.utc).isoformat()
    root = Path(__file__).resolve().parents[2]
    ledger = tmp_path / 'ledger.jsonl'
    result = subprocess.run([sys.executable, str(root / 'scripts/vidya/cli.py'), '--ledger', str(ledger),
                             '--json', 'ingest', 'research-screen', '--path', str(receipt), '--as-of', asof],
                            check=True, text=True, capture_output=True)
    report = json.loads(result.stdout)
    assert report['rows_projected'] == 1 and not report['refused']
    cfg = tmp_path / 'alarm.yaml'
    cfg.write_text('backend: file\nfile:\n  path: ' + str(tmp_path / 'alarm.jsonl') + '\n')
    answer = loop_beliefs.prepare('test.lsa_diagnostic', {'model_file': 'synthetic-fixture.gguf', 'model_sha256': 'a' * 64, 'backend': 'cpu'}, ledger=ledger,
              index_path=tmp_path / 'index.yaml', as_of=asof, sync_module=Sync(),
              known_good=tmp_path / 'known.json', alarm_state=tmp_path / 'alarm-state.json',
              alarm_config=cfg, read_log=tmp_path / 'reads.jsonl')
    visible = [x for x in answer.get('evidence', {}).get('claims', [])
               if x.get('source_kind') == 'lsa-screen-item']
    assert answer['status'] == 'ready' and len(visible) == 1 and visible[0]['value'] == 0
    output.write_text('{}')
    with pytest.raises(Exception):
        research_screen.native_rows(receipt)
