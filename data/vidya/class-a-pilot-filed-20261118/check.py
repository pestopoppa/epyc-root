from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys

BASE = Path(__file__).parent
ROOT = Path.cwd()
CANONICAL = Path('/mnt/raid0/llm/state/vidya/ledger.jsonl')
sys.path.insert(0, str(ROOT / 'scripts/vidya'))
from adapters import committed_conclusion as ccm
import claim_tuple as ct
from ledger import Ledger
from prepare import GEMMA, Q27, Q35, Q38UD, ROOT, REF, STUDY
from cc_extract import ac0

NOW = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
NEXT = NOW
BATCH = BASE / 'gold-register.jsonl'
REG = ROOT / ccm.REGISTER_REL

def dump(name, data):
    (BASE / name).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')

def run(name, *args, **kw):
    r = subprocess.run(args, capture_output=True, text=True, **kw)
    (BASE / (name + '.stderr')).write_text(r.stderr)
    (BASE / (name + '.json')).write_text(r.stdout)
    if not r.stdout:
        raise RuntimeError((name, r.returncode, r.stderr[-500:]))
    return r.returncode, json.loads(r.stdout)

def cli(name, *args, **kw):
    rc, report = run(name, sys.executable, str(ROOT/'scripts/vidya/cli.py'), '--json', *args, **kw)
    assert rc == 0, (name, rc, report)
    return report

def write_row(path, row):
    ccm.check_row(row, repo=ROOT)
    ccm.append_row(path, row)

def expected_raises(expect, fn):
    try:
        fn()
    except ct.ProjectionError as e:
        assert expect in str(e), e
        return str(e)
    raise AssertionError(f'did not refuse {expect}')

def content(frame):
    frame = deepcopy(frame)
    frame.pop('frame_id')
    frame['pubinfo'].pop('created_at')
    return frame

def read_claims(path):
    source_ids = defaultdict(set)
    claims_by_source = defaultdict(set)
    for x in Ledger(path).read_all():
        f = x.frame
        t = f['frame_type']
        a = f['assertion']
        for path_leaf in ('inf70-ingest-ds41scope', 'sub-gpu-runner-20260916'):
            if t.endswith('source_observed/v1') and path_leaf in (a.get('locator') or ''):
                source_ids[path_leaf].add(a['source_id'])
        if t.endswith('claim_proposed/v1'):
            claims_by_source[a['source_id']].add(a['claim_id'])
    return {k: sorted(set().union(*(claims_by_source[i] for i in ids))) for k, ids in source_ids.items()}

def check():
    existing = ccm.read_register(REG)
    batch = ccm.read_register(BATCH)
    confirmed = json.loads((BASE/'confirmation.json').read_text())
    conf = {r['gold_index']: r for r in confirmed}
    original = set(json.loads((STUDY/'labels_classA_true.json').read_text()))
    result0 = ac0(json.loads((STUDY/'class_a_items.json').read_text()), original)
    dump('ac0-replay.json', result0)
    assert {r['gold_index'] for r in confirmed} == original
    assert len(existing) == 30
    assert not ({r['cc_id'] for r in existing} & {r['cc_id'] for r in batch})
    assert len(batch) == len({r['cc_id'] for r in batch}) == 53
    decisions = ccm.declined(BATCH)
    assert decisions == [{'cc_id': conf[24]['cc_id'], 'reason': 'decision'}], decisions
    rows_by_cid = {r['cc_id']:r for r in batch}
    assert rows_by_cid[conf[34]['cc_id']]['also_anchored'][0]['path'] == conf[35]['path']
    assert 'corrected 2026-10-20' in rows_by_cid[conf[108]['cc_id']]['anchor']['quote']
    native = ccm.native_rows(BATCH, repo=ROOT)
    assert len(native) == sum(max(1, len(r['stated']['metrics'])) for r in batch if r['kind']=='result')
    tuples = [ccm.project(n) for n in native]
    for tup in tuples:
        q, t, why = ct.grade(tup)
        assert (q, t, tup.protocol_id, tup.reps) == ('Judged','Located','',None)
        assert 'run_id' not in tup.applicability
        assert any('no protocol citation' in w for w in why), why
    frames = [f for tup in tuples for f in ct.to_frames(tup, as_of=NOW, adapter_id=ccm.ADAPTER_ID)]
    again = [f for tup in tuples for f in ct.to_frames(tup, as_of='2026-11-18T00:00:00Z',
                                                      adapter_id=ccm.ADAPTER_ID)]
    assert [content(f) for f in frames] == [content(f) for f in again]
    assert len(frames) == len(set(f['frame_id'] for f in frames)) == 3 * len(tuples)
    assert all(ccm.cc_id(r['anchor']['path'].replace('/active/', '/completed/'),
                         r['anchor']['head_norm'], r.get('facet','')) == r['cc_id'] for r in batch)
    base = batch[0]
    bad = deepcopy(base)
    bad['anchor']['quote'] += '\nchanged'
    bad['anchor']['quote_sha256'] = ccm.quote_sha(bad['anchor']['quote'])
    refusals = [expected_raises('quote audit', lambda: ccm.check_row(bad, repo=ROOT))]
    for field in ('protocol_id', 'reps', 'run_id'):
        bad = deepcopy(base)
        bad['stated'][field] = 'forbidden'
        refusals.append(expected_raises(field, lambda: ccm.check_row(bad, repo=ROOT)))
    merged = BASE/'combined-register.jsonl'
    merged.write_bytes(REG.read_bytes() + BATCH.read_bytes())
    report = cli('dry-combined', '--ledger', str(BASE/'empty-unused.jsonl'), 'ingest',
                 'committed-conclusion','--path', str(merged),'--as-of',NOW,'--dry-run')
    assert not report['refused'] and report['rows_projected'] == len(ccm.native_rows(merged))
    verify_ledger = BASE/'verification-ledger.jsonl'
    verify_ledger.unlink(missing_ok=True)
    real_args = ('--ledger', str(verify_ledger), 'ingest','committed-conclusion',
                 '--path', str(BATCH), '--as-of', NOW, '--only-new')
    first = cli('pilot-ingest', *real_args)
    repeated = cli('pilot-replay', *real_args)
    assert first['frames_emitted'] == len(frames) and first['frames_skipped'] == 0 and not first['refused']
    assert repeated['frames_emitted'] == 0 and repeated['frames_skipped'] == len(frames) and not repeated['refused']
    stable = Ledger(verify_ledger)
    assert not stable.verify() and [x.frame for x in stable.read_all()] == frames

    state = BASE/'planning'
    state.mkdir(exist_ok=True)
    ledger = state/'ledger.jsonl'
    before_sha = hashlib.sha256(CANONICAL.read_bytes()).hexdigest()
    shutil.copy2(CANONICAL, ledger)
    assert hashlib.sha256(ledger.read_bytes()).hexdigest() == before_sha
    shutil.copy2(Path(str(CANONICAL) + '.sync.json'), Path(str(ledger) + '.sync.json'))
    native_claims = read_claims(ledger)
    assert {k:len(v) for k,v in native_claims.items()} == {'inf70-ingest-ds41scope':48,
                                                         'sub-gpu-runner-20260916':24}
    covered = BASE/'covered-controls.jsonl'
    covered.unlink(missing_ok=True)
    for leaf, line in [('inf70-ingest-ds41scope',1969), ('sub-gpu-runner-20260916',1257)]:
        source_row = ccm.build_row(path='handoffs/active/vidya-belief-substrate-program.md',
                                   ref=REF, line=line, scope={}, stated={}, scope_evidence='none',
                                   actor='h-vidya-belief-substrate/class_a_fill', at=NOW, retrofit=True,
                                   category='CANDIDATE', direction='higher_better', repo=ROOT)
        source_row['covered_by'] = native_claims[leaf][0]
        write_row(covered, source_row)
    cover = cli('covered-ingest', '--ledger', str(ledger), 'ingest', 'committed-conclusion',
                '--path', str(covered),'--as-of', NOW, '--dry-run')
    declines = ccm.declined(covered)
    assert not cover['refused'] and cover['frames_emitted'] == 0
    assert len(declines)==2 and all(r['reason']=='covered_by' for r in declines)
    dump('covered-native-joins.json', dict(source_claim_ids=native_claims, declines=declines))

    out = dict(
        reviewed_gold=54, picked_distinct_register_rows=len(batch), decision_declines=decisions,
        linked_duplicate_count=1, projected_distinct_gold_rows=sum(r['kind']=='result' for r in batch),
        projected_metric_claims=len(tuples), frames=len(frames), unscoped_register_rows=sum(not r['scope'] for r in batch),
        unscoped_projected_rows=sum(not r['scope'] and r['kind']=='result' for r in batch),
        total_combined_rows=len(existing)+len(batch), combined_frames=report['frames_emitted'],
        batch_sha256=hashlib.sha256(BATCH.read_bytes()).hexdigest(), before_sha=before_sha,
        quote_and_warrant_negative_controls=refusals, as_of=NOW)
    dump('ac1-ac5.json',out)
    (state/'index.yaml').write_text('[]\n')
    (state/'alarm.yaml').write_text(
        'schema_version: alarm_channel.config.v1\nenabled: false\nbackend: ntfy\n'
        'advisory_mirror: false\nntfy:\n  url: https://ntfy.sh/REPLACE-ME-canary-disabled\n'
        '  timeout_s: 1\nemail:\n  to: REPLACE-ME@example.invalid\nfile:\n'
        f"  path: {state/'alarm-spool.jsonl'}\n")
    for stage in ('before', 'after'):
        if stage == 'after':
            copied = cli('planning-ingest', '--ledger', str(ledger), 'ingest', 'committed-conclusion',
                         '--path', str(BATCH), '--as-of', NOW, '--only-new')
            assert copied['frames_emitted']==len(frames) and not copied['refused']
        targets = {'gemma-cpu': {'model_file':GEMMA, 'backend':'cpu', 'quant':'Q4_K_M', 'context_tokens':8192},
                   'q27-gpu': {'model_file':Q27, 'backend':'gpu', 'quant':'Q8_0'},
                   'q38-cpu': {'model_file':Q38UD, 'backend':'cpu', 'quant':'UD-IQ4_XS'},
                   'q35-gpu': {'model_file':Q35, 'backend':'gpu', 'quant':'Q8_0'}}
        if stage == 'before':
            targets = {'q27-gpu': targets['q27-gpu']}
        for label, target in targets.items():
            opts = [sys.executable, str(ROOT/'scripts/vidya/loop_beliefs.py'), 'prepare', '--consumer','cc-pilot',
                    '--target-json', json.dumps(target), '--as-of', NOW,'--ledger',str(ledger),
                    '--index',str(state/'index.yaml'),'--read-log',str(state/'reads.jsonl'),
                    '--known-good',str(state/'known-good.json'),'--alarm-config',str(state/'alarm.yaml'),
                    '--alarm-state',str(state/'alarm-state.json')]
            rc, reply = run(f'plan-{stage}-{label}', *opts)
            if rc and reply.get('refused_reason') == 'reader_checkout_stale':
                rc, reply = run(f'plan-{stage}-{label}', *opts,'--allow-stale-reader')
            assert rc==0 and reply['status']=='ready', (label,rc,reply.get('status'),reply.get('reason'))
    assert hashlib.sha256(CANONICAL.read_bytes()).hexdigest()==before_sha
    print(json.dumps(out, indent=2))

if __name__ == '__main__':
    check()
