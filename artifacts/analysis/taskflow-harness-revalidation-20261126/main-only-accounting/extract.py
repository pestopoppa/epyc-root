#!/usr/bin/env python3
"""Deterministically account for six direct-main cases and one paid direct repair.

Reads saved JSON/JSONL and committed reviews only. Never imports a worker,
executes candidate code, launches a model, or changes a source artifact.
"""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess

SCHEMA_ID = 'epyc.a3b.main-only-execution-accounting.v1'
CASES = ('PAW-5', 'DS41-W-66', 'NARIQ-LIBTRELLIS-MAP-1', 'PFXC-A3', 'TU-GR-1', 'MM-5')
TOKEN_FIELDS = ('input_tokens', 'cached_input_tokens', 'uncached_input_tokens',
                'cache_write_input_tokens', 'output_tokens', 'reasoning_output_tokens')
COMMITTED = {
    'original_four_results': 'quality-launch/main-only-results.json',
    'original_four_scope': 'quality-launch/direct-command-scope-review.json',
    'paw_migration': 'quality-launch/acceptance-migration.json',
    'pfxc_migration': 'pfxc-oracle-v4/acceptance-migration.json',
    'legacy_first_scope': 'legacy-main-first-pass/independent-review.json',
    'repair_scope': 'legacy-main-repair/source-and-scope-review.json',
    'repair_accounting': 'legacy-main-repair/DIRECT-REPAIR-ACCOUNTING.json',
}
SCHEMA = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': SCHEMA_ID,
    'type': 'object', 'required': ['schema', 'scope', 'turns', 'cases', 'totals', 'provenance'],
    'properties': {
        'schema': {'const': SCHEMA_ID}, 'scope': {'type': 'object'},
        'turns': {'type': 'array', 'minItems': 7, 'maxItems': 7},
        'cases': {'type': 'array', 'minItems': 6, 'maxItems': 6},
        'totals': {'type': 'object'}, 'provenance': {'type': 'object'},
        'excluded_paid_guidance': {'type': 'object'},
    },
    '$comment': 'Reasoning tokens are a subset of output tokens. Wall sums are CLI execution durations including tools, never parallel batch elapsed or isolated inference service time.',
}


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def token_text(value):
    return 'unavailable' if value is None else f'{value:,}'


class Reader:
    def __init__(self):
        self.files = {}

    def bytes(self, path):
        path = path.resolve()
        data = path.read_bytes()
        record = {'sha256': sha(data), 'bytes': len(data)}
        if str(path) in self.files and self.files[str(path)] != record:
            raise ValueError('source changed during extraction: ' + str(path))
        self.files[str(path)] = record
        return data

    def json(self, path):
        return json.loads(self.bytes(path))

    def verify_unchanged(self):
        for path, record in self.files.items():
            if sha(Path(path).read_bytes()) != record['sha256']:
                raise ValueError('source changed during extraction: ' + path)


def types(value, prefix='', result=None):
    result = defaultdict(set) if result is None else result
    result[prefix or '$'].add(type(value).__name__)
    if isinstance(value, dict):
        for key, item in value.items():
            types(item, prefix + '.' + key if prefix else key, result)
    elif isinstance(value, list):
        for item in value:
            types(item, prefix + '[]', result)
    return {key: sorted(values) for key, values in sorted(result.items())}


def usage_from_event(raw):
    for key, value in raw.items():
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
            raise ValueError(f'invalid usage {key}: {value!r}')
    usage = {key: raw.get(key) for key in TOKEN_FIELDS}
    if usage['input_tokens'] is None or usage['cached_input_tokens'] is None:
        raise ValueError('input/cache usage unavailable for this enrolled snapshot')
    usage['uncached_input_tokens'] = usage['input_tokens'] - usage['cached_input_tokens']
    if usage['uncached_input_tokens'] < 0:
        raise ValueError('cache exceeds input')
    if usage['reasoning_output_tokens'] is not None and usage['reasoning_output_tokens'] > usage['output_tokens']:
        raise ValueError('reasoning exceeds output')
    return usage


def total(turns):
    result = {field: (sum(t['usage'][field] for t in turns)
                      if all(t['usage'][field] is not None for t in turns) else None)
              for field in TOKEN_FIELDS}
    result['turns'] = len(turns)
    result['cli_execution_wall_s_sum'] = format(sum((Decimal(t['cli_execution_wall_s']) for t in turns), Decimal(0)), '.6f')
    return result


def read_turn(reader, run, case, case_ordinal, kind):
    plan = reader.json(run / 'plan.json')
    execution = reader.json(run / 'execution.json')
    measurement = reader.json(run / 'measurement.json')
    launch = reader.json(run / 'launch-start.json')
    events_raw = reader.bytes(run / 'events.jsonl')
    events = [json.loads(line) for line in events_raw.splitlines() if line.strip()]
    completed = [(i + 1, e) for i, e in enumerate(events) if e.get('type') == 'turn.completed']
    threads = [e for e in events if e.get('type') == 'thread.started']
    if len(completed) != 1 or len(threads) != 1 or any(e.get('type') in {'turn.failed', 'error'} for e in events):
        raise ValueError('expected one successful fresh metered turn: ' + str(run))
    line, event = completed[0]
    raw_usage = event['usage']
    usage = usage_from_event(raw_usage)
    for key, value in measurement['jsonl']['usage'].items():
        if key in usage and usage[key] != value:
            raise ValueError(f'raw/normalized usage mismatch: {case} {key}')
    if measurement['execution'] != execution or plan['model'] != 'gpt-6.1-sol' or plan['reasoning_effort'] != 'low':
        raise ValueError('execution/profile mismatch')
    if execution['rc'] != 0 or execution['cli_version'] != 'codex-cli 0.172.0':
        raise ValueError('unexpected CLI exit/version')
    reader.bytes(run / 'stderr.log')
    if sha(reader.bytes(run / 'prompt.md')) != plan['prompt_sha256']:
        raise ValueError('prompt hash mismatch')
    patch_sha = sha(reader.bytes(run / 'delta.patch'))
    if patch_sha != measurement['patch_sha256']:
        raise ValueError('candidate patch hash mismatch')
    original = reader.json(run / 'oracle-result.json')
    migration = measurement.get('acceptance_migration')
    oracle = original
    if migration:
        oracle = reader.json(run / migration['results_directory'] / 'oracle-result.json')
        if original['checked_candidate_files'] != oracle['checked_candidate_files']:
            raise ValueError('checker migration changed candidate')
    oracle_dir = run / migration['results_directory'] if migration else run
    for channel in ('stdout', 'stderr'):
        if sha(reader.bytes(oracle_dir / f'oracle.{channel}.log')) != oracle[f'{channel}_sha256']:
            raise ValueError('oracle log hash mismatch')
    if measurement.get('oracle') is not None and measurement['oracle'] != oracle:
        raise ValueError('normalized active oracle differs from receipt')
    commands = [e['item'] for e in events if e.get('type') == 'item.completed'
                and isinstance(e.get('item'), dict) and e['item'].get('type') == 'command_execution']
    return {
        'case': case, 'case_turn': case_ordinal, 'kind': kind, 'run': str(run),
        'model': plan['model'], 'effort': plan['reasoning_effort'],
        'cli_version': execution['cli_version'], 'plan_schema': plan.get('schema'),
        'thread_id': threads[0]['thread_id'], 'completed_turn_jsonl_line': line,
        'usage': usage, 'raw_usage': raw_usage,
        'usage_sha256': sha(encoded(raw_usage)), 'usage_schema': types(raw_usage),
        'usage_schema_sha256': sha(encoded(types(raw_usage))),
        'turn_completed_schema_sha256': sha(encoded(types(event))),
        'event_type_counts': dict(sorted(Counter(e.get('type') for e in events).items())),
        'completed_command_count': len(commands), 'events_sha256': sha(events_raw),
        'cli_execution_wall_s': format(Decimal(str(execution['wall_s'])), '.6f'),
        'launch_started_unix': launch['started_unix'], 'pure_model_service_duration_s': None,
        'initial_oracle_rc': original['rc'], 'selected_oracle_rc': oracle['rc'],
        'selected_oracle_sha256': oracle['oracle_sha256'],
        'original_oracle_sha256': original['oracle_sha256'], 'checker_migration': migration,
        'candidate_files': oracle['checked_candidate_files'], 'patch_sha256': patch_sha,
        'path_scope_pass': measurement['path_scope_pass'],
        'raw_human_review_flag': measurement.get('human_tool_and_answer_blinding_review'),
        'embedded_oracle_was_null': measurement.get('oracle') is None,
    }


def extract(base, repo, revision):
    reader = Reader()
    revision = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', revision + '^{commit}'], text=True).strip()
    prefix = 'artifacts/analysis/taskflow-harness-revalidation-20261126/'
    committed, blobs, payloads = {}, {}, {}
    for key, suffix in COMMITTED.items():
        path = prefix + suffix
        raw = subprocess.check_output(['git', '-C', str(repo), 'show', revision + ':' + path])
        committed[key] = json.loads(raw)
        blobs[key] = {'repo': str(repo), 'commit': revision, 'path': path, 'sha256': sha(raw),
                      'git_blob': subprocess.check_output(['git', '-C', str(repo), 'rev-parse', revision + ':' + path], text=True).strip()}
        payloads['provenance/committed/' + key + '.json'] = raw
    turns = []
    for cid in CASES:
        cohort = base / 'main-comparison' if cid in CASES[:4] else base / 'coverage/legacy-comparison'
        turns.append(read_turn(reader, cohort / 'runs' / cid / 'direct-1', cid, 1, 'initial-direct'))
    repair = read_turn(reader, base / 'coverage/legacy-direct-repair/runs/TU-GR-1/direct-repair-1', 'TU-GR-1', 2, 'direct-repair')
    turns.append(repair)
    if len({t['thread_id'] for t in turns}) != 7:
        raise ValueError('duplicate paid turn/thread')
    original_reviews = {x['case']: x for x in committed['original_four_scope']['cases']}
    if committed['original_four_scope']['no_observed_answer_contamination'] is not True:
        raise ValueError('original scope review does not support answer blinding')
    original_results = {x['case']: x for x in committed['original_four_results']}
    legacy_reviews = {x['case']: x for x in committed['legacy_first_scope']['cases']}
    for t in turns:
        cid = t['case']
        if cid in CASES[:4]:
            review = original_reviews[cid]
            if original_results[cid]['patch_sha256'] != t['patch_sha256'] or original_results[cid]['oracle']['rc'] != 0:
                raise ValueError('committed first-four result does not bind candidate')
            t['review_source'] = 'original_four_scope'
            t['review_outcome'] = 'scope-pass; owner-accepted checker-passing artifact'
        elif t['kind'] == 'direct-repair':
            review = committed['repair_scope']
            if review['semantic_verdict'] != 'accept' or review['oracle_rc'] != 0:
                raise ValueError('repair not accepted')
            t['review_source'] = 'repair_scope'; t['review_outcome'] = 'accept'
        else:
            review = legacy_reviews[cid]
            if review['reviewed_candidate_patch_sha256'] != t['patch_sha256']:
                raise ValueError('legacy review candidate mismatch')
            t['review_source'] = 'legacy_first_scope'; t['review_outcome'] = review['candidate_verdict']
        if review['events_sha256'] != t['events_sha256']:
            raise ValueError('committed review does not bind actual events')
        reviewed_commands = review.get('commands_reviewed', review.get('reviewed_commands'))
        if reviewed_commands is None and isinstance(review.get('commands'), list):
            reviewed_commands = len(review['commands'])
        if reviewed_commands != t['completed_command_count']:
            raise ValueError('committed command review count differs from actual events')
    finalized = reader.json(Path(repair['run']) / 'DIRECT-REPAIR-ACCOUNTING.json')
    if finalized != committed['repair_accounting']:
        raise ValueError('committed/finalized repair accounting differs')
    for key, value in finalized['first_pass']['usage'].items():
        if turns[4]['usage'].get(key) != value:
            raise ValueError('embedded first-pass costs differ; never count this embedded copy twice')
    # Preserve a later shared-checker replay without changing original first-pass records.
    pfxc = committed['pfxc_migration']
    replay = pfxc['saved_assessments']['main_direct']
    if (replay['receipt']['original']['rc'] != 0 or replay['receipt']['revised']['rc'] != 0
            or replay['candidate_sha256'] not in {x['sha256'] for x in turns[3]['candidate_files'].values()}):
        raise ValueError('PFXC same-byte revised-checker replay does not bind direct artifact')
    turns[3]['later_shared_checker_replay'] = {
        'version': pfxc['version'], 'original': replay['receipt']['original'],
        'revised': replay['receipt']['revised'], 'candidate_sha256': replay['candidate_sha256'],
        'source': 'pfxc_migration', 'extra_paid_model_turns': 0,
    }
    guidance_run = base / 'main-comparison/runs/NARIQ-LIBTRELLIS-MAP-1/guidance-1'
    # Different arm; deliberately not discovered by globbing or included in totals.
    gm = reader.json(guidance_run / 'measurement.json')
    ge = reader.json(guidance_run / 'execution.json')
    gp = reader.json(guidance_run / 'plan.json')
    graw = reader.bytes(guidance_run / 'events.jsonl')
    gev = [json.loads(l) for l in graw.splitlines() if l.strip()]
    gu = [e['usage'] for e in gev if e.get('type') == 'turn.completed']
    if len(gu) != 1 or gm['changed_by_strong_turn'] != [] or gp['arm'] != 'guidance':
        raise ValueError('excluded guidance arm/status changed')
    excluded = {'case':'NARIQ-LIBTRELLIS-MAP-1','arm':'guidance','ordinal':1,'run':str(guidance_run),
                'usage':usage_from_event(gu[0]),'cli_execution_wall_s':format(Decimal(str(ge['wall_s'])),'.6f'),
                'events_sha256':sha(graw),'candidate_changed':False,
                'included_in_main_only_totals':False,'reason':'paid A3B review/guidance, not direct-main completion'}
    cases = []
    for cid in CASES:
        rows = [t for t in turns if t['case'] == cid]
        accepted = next((t['case_turn'] for t in rows if t['selected_oracle_rc'] == 0), None)
        cases.append({'case':cid,'accepted_after_paid_turns':accepted,'first_turn_oracle_rc':rows[0]['selected_oracle_rc'],
                      'last_turn_oracle_rc':rows[-1]['selected_oracle_rc'],'execution':total(rows),
                      'turn_ids':[t['thread_id'] for t in rows],
                      'final_candidate_files':rows[-1]['candidate_files']})
    totals = {'initial_six_turns':total(turns[:6]),'additional_direct_repair':total([repair]),'all_seven_turns':total(turns)}
    assert sum(c['accepted_after_paid_turns'] == 1 for c in cases) == 5
    assert sum(c['accepted_after_paid_turns'] == 2 for c in cases) == 1
    reader.verify_unchanged()
    result = {
        'schema':SCHEMA_ID,'schema_sha256':sha(encoded(SCHEMA)),
        'scope':{'cases':6,'initial_paid_turns':6,'additional_paid_repair_turns':1,
                 'accepted_after_one_turn':5,'accepted_after_two_turns':1,
                 'model':'gpt-6.1-sol','reasoning_effort':'low','cli_version':'codex-cli 0.172.0',
                 'duration_definition':'sum saved CLI execution wall_s, including tool/runtime time; not pure model-service time and not parallel batch elapsed',
                 'reasoning_definition':'reported reasoning_output_tokens are included in output_tokens; never add them again',
                 'excluded_costs':'manager/setup/review, checker repairs and experiment coordination are not isolated by these CLI vectors; they are neither zero nor included. Native A3B execution and paid A3B guidance are separate.',
                 'parallel_batch_elapsed_s':None,'pure_model_service_duration_s':None,
                 'raw_review_flags':'preserved pending flags can predate the committed source/scope reviews; authoritative review provenance is linked separately'},
        'turns':turns,'cases':cases,'totals':totals,'excluded_paid_guidance':excluded,
        'checker_qualifications':{
            'PAW-5':'same-byte formatting migration from original rc1 to paw5.markdown-fields.v3 rc0; no second paid model turn',
            'DS41-W-66':'same oracle SHA; isolated test dependency/context replay retained in committed scope audit',
            'NARIQ-LIBTRELLIS-MAP-1':'selected pinned source checker rc0; source/web-read audit retained',
            'PFXC-A3':'original direct checker rc0 and later pfxc.exact-events.v4 shared-checker replay rc0 on identical candidate; no second paid turn'},
        'provenance':{'extractor_sha256':sha(Path(__file__).read_bytes()),'committed_reviews':blobs,
                      'source_files':dict(sorted(reader.files.items()))},
        'validation':{'raw_usage_cross_checked_with_measurements':7,'unique_paid_thread_ids':7,
                      'repair_first_pass_embedded_usage_not_double_counted':True,'all_original_files_read_only':True,
                      'native_or_model_reexecution':False,'output_schema_sha256':sha(encoded(SCHEMA))},
    }
    payloads['ACCOUNTING.json'] = encoded(result)
    payloads['SCHEMA.json'] = encoded(SCHEMA)
    columns = ('case','case_turn','kind',*TOKEN_FIELDS,'cli_execution_wall_s','selected_oracle_rc','thread_id')
    lines = ['\t'.join(columns)]
    for t in turns:
        lines.append('\t'.join(str(t['usage'].get(k) if k in TOKEN_FIELDS else t.get(k)) for k in columns))
    payloads['TURNS.tsv'] = ('\n'.join(lines)+'\n').encode()
    lines = ['case\taccepted_after_paid_turns\t'+'\t'.join(TOKEN_FIELDS)+'\tcli_execution_wall_s_sum']
    for c in cases:
        lines.append('\t'.join([c['case'],str(c['accepted_after_paid_turns'])]+[str(c['execution'][k]) for k in TOKEN_FIELDS]+[c['execution']['cli_execution_wall_s_sum']]))
    payloads['CASES.tsv'] = ('\n'.join(lines)+'\n').encode()
    report = [
        '# Six-case direct-main execution accounting', '',
        'Five cases passed after one paid direct turn; TU-GR-1 passed after a second paid repair turn. This selected cohort contains seven fresh gpt-6.1-sol/low CLI turns. The failed first TU attempt remains fully counted.', '',
        '| Case | Paid turns to acceptance | Input | Cached | Uncached | Output | Reasoning subset | CLI seconds summed |',
        '|---|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for c in cases:
        v=c['execution'];report.append('| '+c['case']+' | '+str(c['accepted_after_paid_turns'])+' | '+' | '.join(token_text(v[k]) for k in ('input_tokens','cached_input_tokens','uncached_input_tokens','output_tokens','reasoning_output_tokens'))+' | '+v['cli_execution_wall_s_sum']+' |')
    report += ['', '| Execution scope | Input | Cached | Uncached | Output | Reasoning subset | CLI seconds summed |',
               '|---|---:|---:|---:|---:|---:|---:|']
    for label,key in [('Initial six turns','initial_six_turns'),('Additional TU repair','additional_direct_repair'),('All seven turns','all_seven_turns')]:
        v=totals[key];report.append('| '+label+' | '+' | '.join(token_text(v[k]) for k in ('input_tokens','cached_input_tokens','uncached_input_tokens','output_tokens','reasoning_output_tokens'))+' | '+v['cli_execution_wall_s_sum']+' |')
    excluded_text = ('The separately recorded NARIQ paid guidance-1 review ('
                     +token_text(excluded['usage']['input_tokens'])+' input / '
                     +token_text(excluded['usage']['cached_input_tokens'])+' cached / '
                     +token_text(excluded['usage']['uncached_input_tokens'])+' uncached / '
                     +token_text(excluded['usage']['output_tokens'])+' output, including '
                     +token_text(excluded['usage']['reasoning_output_tokens'])+' reasoning; '
                     +excluded['cli_execution_wall_s']+' CLI seconds) is explicitly excluded from every main-only total; its candidate was unchanged.')
    report += ['', 'Reported reasoning is already included in output. Total cache-write input is '+token_text(totals['all_seven_turns']['cache_write_input_tokens'])+' in the raw usage records; an absent field would remain unavailable. The duration sum includes CLI tool/runtime work and is not parallel batch elapsed or isolated model inference time.',
               '', 'Checker history remains visible: PAW moves from original rc1 to formatting-checker v3 rc0 on identical bytes. PFXC retains original rc0 and a later exact-events v4 rc0 replay of the same direct artifact. W66 retains its isolated dependency/context check; NARIQ retains its selected source checker and source/web audit. These regrades add no measured direct-main execution turn to these receipts; their broader work cost remains outside these vectors. Raw measurement review flags are unchanged; committed source/scope reviews bind the actual event and candidate hashes.',
               '', 'These are main-only execution vectors. Manager work, setup, review, checker repair and experiment coordination are neither priced as free nor included. Native A3B execution remains separate. '+excluded_text,
               '', 'ACCOUNTING.json binds raw usage, schemas, candidate/receipt hashes and committed reviews at '+revision+'. TURNS.tsv preserves all seven turn vectors; CASES.tsv groups them by logical task. Extraction performs no model/candidate reexecution and changes no original files.',
               '', 'Next: main integrates these execution-only vectors with separately measured A3B, guidance and coordination evidence.']
    payloads['REPORT.md'] = ('\n'.join(report)+'\n').encode()
    payloads['OUTPUT-HASHES.json'] = encoded({'schema':SCHEMA_ID,'extractor_sha256':sha(Path(__file__).read_bytes()),
                                            'sha256':{name:sha(data) for name,data in sorted(payloads.items())}})
    return result, payloads


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--repo',type=Path,default=Path('/mnt/raid0/llm/tmp/ws58-a3b-finish-20261126'))
    parser.add_argument('--revision',default='47139dc8f')
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--check',action='store_true',help='read-only exact regeneration comparison')
    args=parser.parse_args()
    result,payloads=extract(args.base.resolve(),args.repo.resolve(),args.revision)
    for name,data in payloads.items():
        target=args.output/name
        if args.check:
            if not target.is_file() or target.read_bytes()!=data:
                raise SystemExit('deterministic output differs: '+str(target))
        else:
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    print(json.dumps({'mode':'check' if args.check else 'write','outputs':len(payloads),
                      'totals':result['totals'],'accepted_after_one_turn':5,'accepted_after_two_turns':1},indent=2))
