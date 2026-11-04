import hashlib
import json
import sys
import importlib.util
import subprocess
from datetime import datetime, timezone
from argparse import Namespace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts/vidya'))
from adapters import lsa_moe_pilot as adapter
from claim_tuple import ProjectionError, grade


def sealed(path, record):
    path.write_text(json.dumps(record))
    envelope = path.with_name('producer-record.lsa-pilot.json')
    envelope.unlink(missing_ok=True)
    return adapter.seal_native(path)


def fixture(tmp_path, status='complete'):
    events, artifacts = [], []
    for doc, split, token in [('fit-doc', 'fit', 'b'*64), ('held-doc', 'heldout', 'c'*64)]:
        for layer in range(3, 40, 4):
            artifact = tmp_path/f'{doc}-{layer}.bin'; artifact.write_bytes(b'fixture')
            artifact_spec = {'path':artifact.name,'sha256':hashlib.sha256(b'fixture').hexdigest(), 'bytes':7}
            artifacts.append(artifact_spec)
            events.append({'event':'layer_captured', 'elapsed_seconds':1, 'document':doc, 'split':split,
                           'layer':layer, 'token_sha256':token, 'artifact':artifact_spec})
        events.append({'event':'document_captured', 'elapsed_seconds':2, 'seconds':1.0,
                       'document':doc, 'split':split})
    for layer in range(3, 40, 4):
        events.append({'event':'projection_step', 'elapsed_seconds':3, 'queries':2,
                       'document':'fit-doc', 'split':'fit', 'layer':layer, 'query_positions':[1,2]})
    events.append({'event':'training_complete', 'elapsed_seconds':4, 'seconds':1.5, 'steps':10, 'queries':20})
    event_path = tmp_path/'events.jsonl'
    event_path.write_text(''.join(json.dumps(e)+'\n' for e in events))
    identity = {'model':'fixture', **{k:'a'*64 for k in ('weights_sha256','config_sha256','tokenizer_sha256','corpus_sha256','source_sha256','producer_sha256','capture_module_sha256')}}
    limits = {'model_id':'fixture', 'checkpoint_sha256':'a'*64, 'tokenizer_sha256':'a'*64,
              'corpus_sha256':'a'*64, 'source_manifest_sha256':'a'*64,
              **{k:10 for k in ('max_docs','max_tokens','max_seconds','max_queries','max_artifact_bytes','max_score_cells')},
              'threads':1, 'tau':0.2, 'learning_rate':0.001, 'seed':1, 'sinks':1, 'window':2}
    runtime = {**{k:'fixture' for k in ('python','platform','torch','transformers','hf_modeling_path','hf_rope_utils_path')},
               'hf_modeling_sha256':'d'*64, 'hf_rope_utils_sha256':'e'*64, 'cpu_affinity':[0], 'torch_threads':1, 'torch_interop_threads':1}
    model = {'class':'fixture', 'devices':['cpu'], 'parameter_dtypes':['torch.float32'], 'cpu_affinity':[0], 'torch_threads':1, 'torch_interop_threads':1}
    record = {'schema':'lsa-moe-pilot-native-v1', 'status':status, 'events':'events.jsonl',
      'events_sha256':hashlib.sha256(event_path.read_bytes()).hexdigest(), 'started_unix':1,
      'elapsed_seconds':4, 'limits':limits, 'counts':{'eligible_documents':2,
      'completed_documents':2, 'captured_layers':20, 'projection_steps':10, 'queries':20},
      'artifacts':artifacts, 'identity':identity, 'runtime':runtime, 'actual_model':model,
      'fit_documents':['fit-doc'], 'heldout_documents':['held-doc'],
      'document_token_sha256':{'fit-doc':'b'*64, 'held-doc':'c'*64}}
    if status != 'complete': record['error'] = 'fixture failure'
    path = sealed(tmp_path/'producer-record.json', record)
    return path, record


def test_separate_scopes_and_shared_grader(tmp_path):
    path, _ = fixture(tmp_path)
    rows = adapter.native_rows(path)
    assert [r['value'] for r in rows] == [2.0, 1.5]
    for row in rows:
        claim = adapter.project(row)
        assert grade(claim)[:2] == ('Judged', 'Located')
        assert 'no quality' in claim.claim


def test_failure_is_preserved(tmp_path):
    path, _ = fixture(tmp_path, 'invalid')
    assert adapter.project(adapter.native_rows(path)[0]).extra['native_record']['error'] == 'fixture failure'


@pytest.mark.parametrize('mutation', ['identity', 'config_sha', 'runtime', 'device', 'threads', 'limits', 'splits', 'duplicate_layer', 'duplicate_step', 'duplicate_document'])
def test_refuse_incomplete_identity_or_duplicate_events(tmp_path, mutation):
    _, record = fixture(tmp_path)
    if mutation == 'identity': record['identity'] = {'foo':1}
    elif mutation == 'config_sha': record['identity']['config_sha256'] = 'missing'
    elif mutation == 'runtime': record['runtime'] = {'foo':1}
    elif mutation == 'device': record['actual_model']['devices'] = ['cuda:0']
    elif mutation == 'threads': record['actual_model']['torch_threads'] = 2
    elif mutation == 'limits': record['limits']['tau'] = 0
    elif mutation == 'splits': record['heldout_documents'] = ['fit-doc']
    else:
        event_path = tmp_path/'events.jsonl'
        events = [json.loads(x) for x in event_path.read_text().splitlines()]
        kind = {'duplicate_layer':'layer_captured', 'duplicate_step':'projection_step', 'duplicate_document':'document_captured'}[mutation]
        indexes = [i for i,e in enumerate(events) if e['event'] == kind]
        events[indexes[1]] = dict(events[indexes[0]])
        event_path.write_text(''.join(json.dumps(e)+'\n' for e in events))
        record['events_sha256'] = hashlib.sha256(event_path.read_bytes()).hexdigest()
    with pytest.raises(ProjectionError): sealed(tmp_path/'producer-record.json', record)


def test_actual_pilot_terminal_failure_hook(tmp_path):
    research = ROOT.parent / 'research-lsa' / 'scripts/lsa_moe'
    sys.path.insert(0, str(research))
    spec = importlib.util.spec_from_file_location('pilot_hook_test', research/'pilot.py')
    pilot = importlib.util.module_from_spec(spec); spec.loader.exec_module(pilot)
    checkpoint = tmp_path/'checkpoint'; checkpoint.mkdir(); (checkpoint/'dummy').write_text('fixture')
    tokenizer = tmp_path/'tokenizer'; tokenizer.write_text('fixture')
    corpus = tmp_path/'corpus.json'; corpus.write_text('{"fit": [], "heldout": []}')
    helper = Path(adapter.__file__).resolve()
    manifest = tmp_path/'sources.json'; manifest.write_text(json.dumps({'files':[{'path':str(helper), 'sha256':pilot.sha(helper)}]}))
    args = Namespace(output=str(tmp_path/'out'), checkpoint=str(checkpoint), checkpoint_sha256=pilot.sha(checkpoint),
      tokenizer=str(tokenizer), tokenizer_sha256=pilot.sha(tokenizer), corpus=str(corpus), corpus_sha256=pilot.sha(corpus),
      source_manifest=str(manifest), source_manifest_sha256=pilot.sha(manifest), max_seconds=10, max_docs=2,
      evidence_helper=str(helper), evidence_helper_sha256=pilot.sha(helper))
    with pytest.raises(ValueError, match='invalid document count'): pilot.run(args)
    envelope = tmp_path/'out/producer-record.lsa-pilot.json'
    assert adapter.native_rows(envelope) == []
    raw = json.loads((tmp_path/'out/producer-record.json').read_text())
    assert raw['status'] == 'invalid' and 'invalid document count' in raw['error']


def test_fixture_ingest_and_planning_context(tmp_path):
    import loop_beliefs
    path, _ = fixture(tmp_path)
    ledger = tmp_path/'ledger.jsonl'
    asof = datetime.now(timezone.utc).isoformat()
    proc = subprocess.run([sys.executable, str(ROOT/'scripts/vidya/cli.py'), '--ledger', str(ledger), '--json', 'ingest', 'lsa-moe-pilot', '--path', str(path), '--as-of', asof], text=True, capture_output=True, check=True)
    report = json.loads(proc.stdout)
    assert report['rows_projected'] == 2 and not report['refused']
    class Sync:
        def status(self, *args, **kwargs):
            return {'fresh':True, 'lag_entries':0, 'index_max_id':1, 'synced_max_id':1, 'last_sync':asof}
    cfg = tmp_path/'alarm.yaml'; cfg.write_text('backend: file\nfile:\n  path: '+str(tmp_path/'alarm.jsonl')+'\n')
    result = loop_beliefs.prepare('test.lsa_pilot', {'model_file':'fixture', 'model_sha256':'a'*64, 'backend':'cpu'}, ledger=ledger, index_path=tmp_path/'index.yaml', as_of=asof, sync_module=Sync(), known_good=tmp_path/'known.json', alarm_state=tmp_path/'alarm-state.json', alarm_config=cfg, read_log=tmp_path/'reads.jsonl')
    visible = [x for x in result.get('evidence', {}).get('claims', []) if x.get('source_kind') == 'lsa-moe-pilot']
    assert result['status'] == 'ready' and sorted(x['value'] for x in visible) == [1.5, 2.0]


@pytest.mark.parametrize('exit_code,case_status,wrapper_exit', [(0,'passed',0), (1,'failure',1), (77,'skipped',0)])
def test_prospective_unit_junit_exit_classification(tmp_path, exit_code, case_status, wrapper_exit):
    sys.path.insert(0, str(ROOT))
    from scripts.ci.native_conformance import junit_summary
    junit = tmp_path/'unit.xml'
    wrapper = Path(__file__).with_name('native_unit_junit.py')
    result = subprocess.run([sys.executable, str(wrapper), '--junit', str(junit), '--case', 'synthetic', '--', sys.executable, '-c', f'raise SystemExit({exit_code})'])
    assert result.returncode == wrapper_exit
    assert junit_summary(junit.read_bytes())['cases'][0]['status'] == case_status


@pytest.mark.parametrize('option', ['--tau', '--learning-rate'])
def test_pilot_rejects_nonfinite_hyperparameters(tmp_path, option):
    pilot = ROOT.parent/'research-lsa/scripts/lsa_moe/pilot.py'
    args = [sys.executable, str(pilot)]
    for key in ('checkpoint', 'checkpoint-sha256', 'tokenizer', 'tokenizer-sha256', 'corpus', 'corpus-sha256', 'source-manifest', 'source-manifest-sha256', 'model-id', 'output'):
        args += ['--'+key, str(tmp_path/'out') if key == 'output' else 'fixture']
    for key in ('max-docs', 'max-tokens', 'max-seconds', 'max-queries', 'max-artifact-bytes', 'max-score-cells', 'seed', 'threads'):
        args += ['--'+key, '1']
    args += ['--tau', '1', option, 'nan']
    result = subprocess.run(args, capture_output=True, text=True)
    assert result.returncode != 0 and not (tmp_path/'out').exists()


@pytest.mark.parametrize('mutation', ['record', 'events', 'artifact', 'partial', 'denominator'])
def test_refuse_tamper_or_partial(tmp_path, mutation):
    path, record = fixture(tmp_path)
    if mutation == 'record': (tmp_path/'producer-record.json').write_text('{}')
    elif mutation == 'events': (tmp_path/'events.jsonl').write_text('{}\n')
    elif mutation == 'artifact': (tmp_path/'fit-doc-3.bin').write_bytes(b'tamper')
    elif mutation in ('partial', 'denominator'):
        if mutation == 'partial': record['status'] = 'running'
        else: record['counts']['queries'] = 3
        with pytest.raises(ProjectionError): sealed(tmp_path/'producer-record.json', record)
        return
    with pytest.raises(ProjectionError): adapter.native_rows(path)
