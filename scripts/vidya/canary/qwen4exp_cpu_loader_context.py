"""Read a live prospective CPU loader seal through one isolated planning ledger."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

VIDYA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VIDYA))

from adapters import qwen4exp_cpu_loader as adapter
from ingest_sources import ingest
from ledger import Ledger
from loop_beliefs import prepare
from producers import qwen4exp_cpu_loader_contract as contract


def run(seal, output, native_exit_code):
    seal = seal.resolve(strict=True)
    record, plan, state, _ = adapter._validate(seal)
    status = state['status']
    contract.require(status in contract.TERMINAL, 'incomplete native diagnostic')
    contract.require(native_exit_code == int(status != 'loader_diagnostic_complete'),
                     'native disposition differs from native exit code')
    original = seal.read_bytes()
    output.mkdir()
    ledger = output / 'ledger.jsonl'
    as_of = datetime.now(timezone.utc).isoformat()
    report = ingest(Ledger(ledger), contract.SOURCE_KIND, [seal], as_of=as_of, only_new=True)
    contract.require(report['rows_projected'] == 1 and report['frames_emitted'] == 3
                     and not (report['refused'] or report['declined'] or report['missing']),
                     f'loader intake refused: {report}')
    ledger_raw = ledger.read_bytes()
    retry = ingest(Ledger(ledger), contract.SOURCE_KIND, [seal], as_of=as_of, only_new=True)
    contract.require(retry['frames_skipped'] == 3 and retry['frames_emitted'] == 0
                     and ledger.read_bytes() == ledger_raw, 'duplicate ingest changed scratch ledger')
    frames = [json.loads(line)['frame'] for line in ledger_raw.splitlines()]
    source, claim, support = (next(f['assertion'] for f in frames if f['frame_type'].endswith(kind + '/v1'))
                              for kind in ('source_observed', 'claim_proposed', 'evidence_supports_claim'))
    claim_id = claim['claim_id']
    contract.require(source['source_kind'] == contract.SOURCE_KIND
                     and support['protocol_id'] == '' and support['grade'] == {'Q': 'Judged', 'T': 'Located'}
                     and support['observation']['outcome_native'] == status,
                     'loader observation differs from shared grade or native disposition')

    validator_sha = state['validator_source_sha256']
    exact = contract.selector(plan, validator_sha)
    model = Path(plan['model_shards'][0]['path']).name
    cases = {
        'exact': exact,
        'foreign_source': {**exact, 'build_sha': '0' * 40},
        'foreign_run': {**exact, 'run_id': exact['run_id'] + '-foreign'},
        'ordinary_cpu': {'model_file': model, 'backend': 'cpu'},
        'ordinary_hip': {'model_file': model, 'backend': 'gpu'},
    }
    for label in ('binary', 'model', 'recipe'):
        drifted = deepcopy(plan)
        if label == 'binary':
            drifted['arms']['candidate']['binary_sha256'] = '0' * 64
        elif label == 'model':
            drifted['model_shards'][0]['sha256'] = '0' * 64
        else:
            drifted['recipes']['diagnostic']['args'] += ['--warmup']
        cases['foreign_' + label] = contract.selector(drifted, validator_sha)

    index = output / 'index.yaml'
    index.write_text('[]\n')
    alarms = output / 'alarms.yaml'
    alarms.write_text(f'backend: file\nfile:\n  path: {json.dumps(str(output / "alarms.jsonl"))}\n')
    reads = {}
    expected_head = None
    for label, target in cases.items():
        answer = prepare(
            'autokernel.planner', target, ledger=ledger, index_path=index, as_of=as_of,
            known_good=output / f'{label}.known-good.json', alarm_config=alarms,
            alarm_state=output / 'alarm-state.json', read_log=output / 'reads.jsonl',
            check_reader_checkout=True,
        )
        contract.require(answer['status'] == 'ready' and not answer.get('read_log_error'),
                         f'{label}: planning reader did not become ready: {answer}')
        ledger_state, evidence = answer['ledger_state'], answer['evidence']
        expected_head = expected_head or ledger_state['head_hash']
        contract.require(ledger_state['head_hash'] == expected_head and ledger_state['frame_count'] == 3
                         and ledger_state['fresh'] is True and ledger_state['ledger_path'] == str(ledger),
                         f'{label}: reader did not use the pinned scratch ledger')
        expected = [claim_id] if label == 'exact' else []
        contract.require(evidence['claim_ids'] == expected
                         and [item['claim_id'] for item in evidence['claims']] == expected
                         and evidence['not_evidence_claim_ids'] == [] and evidence['tried_index'] == []
                         and bool(evidence['section']) == bool(expected)
                         and (not expected or claim_id in evidence['section']),
                         f'{label}: unexpected planner visibility')
        reasons = [] if expected else ['inapplicable_target' if label == 'foreign_run' else 'no_applicable_claims']
        contract.require(evidence['reasons'] == reasons, f'{label}: planning refusal reason differs')
        reads[label] = {'selector': target, 'claim_ids': evidence['claim_ids'],
                        'section_sha256': evidence['section_sha256'], 'reasons': evidence['reasons']}
    contract.require(seal.read_bytes() == original and ledger.read_bytes() == ledger_raw,
                     'canary altered source or ledger')
    return {
        'schema': 'epyc.qwen4exp_cpu_loader_planning_context.v1', 'wiring_status': 'passed',
        'native_status': status, 'native_exit_code': native_exit_code, 'row_id': contract.ROW,
        'claim_id': claim_id, 'grade': support['grade'], 'seal_sha256': contract.sha(original),
        'capture_pins': state['captures'], 'ledger_sha256': contract.sha(ledger_raw), 'head_hash': expected_head,
        'ingest': report, 'retry': retry, 'reads': reads, 'reader_checkout': answer['reader_checkout'],
        'reader_sha256': {name: contract.sha((VIDYA / name).read_bytes()) for name in (
            'loop_beliefs.py', 'ingest_sources.py', 'claim_tuple.py', 'adapters/qwen4exp_cpu_loader.py',
            'producers/qwen4exp_cpu_loader_contract.py', 'canary/qwen4exp_cpu_loader_context.py',
        )},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('seal', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('native_exit_code', type=int)
    args = parser.parse_args()
    result = run(args.seal, args.output, args.native_exit_code)
    if 'FILLER_ID' in os.environ:
        contract.require(
            os.environ['FILLER_ID'] == contract.ROW
            and time.time() < int(os.environ['FILLER_DEADLINE'])
            and not Path(os.environ['FILLER_STOPFILE']).exists(),
            'row identity, STOP or deadline changed before planning receipt',
        )
    with (args.output / 'receipt.json').open('xb') as stream:
        stream.write(contract.canonical(result) + b'\n')


if __name__ == '__main__':
    main()
