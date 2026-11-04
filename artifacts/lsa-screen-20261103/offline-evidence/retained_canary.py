"""Read retained original receipts without rewriting or re-sealing any source."""
import json, sys, subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts/vidya'))
from adapters import research_screen
import loop_beliefs

HERE = Path(__file__).resolve().parent
class Sync:
    def status(self, *args, **kwargs):
        return {'fresh': True, 'lag_entries': 0, 'index_max_id': 1, 'synced_max_id': 1,
                'last_sync': datetime.now(timezone.utc).isoformat()}

def main():
    failures = []
    (HERE / 'retained-ledger.jsonl').unlink(missing_ok=True)
    for receipt in sorted((ROOT / 'artifacts/lsa-screen-20261103').glob('*/**/*.research-screen.json')):
        try:
            claim = research_screen.project(research_screen.native_rows(receipt)[0])
            if claim.source_kind != 'lsa-screen-item':
                continue
            asof = datetime.now(timezone.utc).isoformat()
            ledger = HERE / 'retained-ledger.jsonl'
            proc = subprocess.run([sys.executable, str(ROOT / 'scripts/vidya/cli.py'), '--ledger', str(ledger), '--json', 'ingest', 'research-screen', '--path', str(receipt), '--as-of', asof], check=True, text=True, capture_output=True)
            report = json.loads(proc.stdout)
            assert report['rows_projected'] == 1 and not report['refused'], report
            cfg = HERE / 'alarm.yaml'
            cfg.write_text('backend: file\nfile:\n  path: ' + str(HERE / 'alarm.jsonl') + '\n')
            profile = json.loads(receipt.read_text())['profile']
            target = {'model_file': profile['model_file'], 'model_sha256': profile['model_sha256'], 'backend': 'cpu'}
            answer = loop_beliefs.prepare('test.lsa_retained', target, ledger=ledger, index_path=HERE / 'index.yaml', as_of=asof, sync_module=Sync(), known_good=HERE / 'known.json', alarm_state=HERE / 'alarm-state.json', alarm_config=cfg, read_log=HERE / 'reads.jsonl')
            visible = [x for x in answer.get('evidence', {}).get('claims', []) if x.get('source_kind') == 'lsa-screen-item' and x.get('value') == claim.value]
            assert answer['status'] == 'ready' and visible, (answer['status'], visible)
            (HERE / 'retained-canary.json').write_text(json.dumps({'receipt': str(receipt), 'status': answer['status'], 'rows_projected': report['rows_projected'], 'refused': report['refused'], 'value': claim.value, 'claims_visible': len(visible), 'source_files_modified': False, 'previous_refusals': failures}, indent=2) + '\n')
            return
        except Exception as exc:
            failures.append({'receipt': str(receipt), 'error': repr(exc)})
    (HERE / 'retained-canary-failures.json').write_text(json.dumps(failures, indent=2) + '\n')
    raise SystemExit('No retained receipt passed: ' + str(len(failures)))

if __name__ == '__main__': main()
