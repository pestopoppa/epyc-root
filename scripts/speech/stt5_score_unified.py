#!/usr/bin/env python3
"""Read-only Unified EN validation rescore; categorical failures stay failures."""
import collections
import hashlib
import time
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

from stt5_score_baseline import RESEARCH_COMMIT, ledger_digest, sha, write

SETTINGS = ('c1r0', 'c1r1', 'c2r2', 'c2r4', 'c7r7', 'c13r13')


def read_setting(ledger, records, pins, source, setting, parse_tokens):
    rows, failures, units = [], [], []
    for record in records:
        clip = record['clip_id']
        key = hashlib.sha256(clip.encode()).hexdigest()
        chunk = json.loads((ledger / 'chunks' / (key + '.chunks.json')).read_text())
        if (chunk['status'], chunk['id'], chunk['original_pcm_sha256'], chunk['original_wav_sha256'], chunk['n_samples']) != (
                'ok', clip, record['pcm_sha256'], record['wav_sha256'], record['frames']):
            raise ValueError('chunk identity')
        texts, evidence, failed, position = [], [], False, 0
        for index, part in enumerate(chunk['chunks']):
            if part['index'] != index or part['start_sample'] != position or part['end_sample'] <= position:
                raise ValueError('chunk coverage')
            position = part['end_sample']
            unit = hashlib.sha256(f'{setting}|auto|{clip}|{index}'.encode()).hexdigest()
            units.append(unit)
            binding = dict(clip_id=clip, chunk_index=index, chunk_pcm_sha256=part['pcm_sha256'],
                           chunk_wav_sha256=part['wav_sha256'], input_sha256=pins['validation_sha256'],
                           plan_sha256=pins['plan_sha256'], source_sha256=source,
                           model_sha256=pins['models'][setting], binary_sha256=pins['runner_binary_sha256'][setting],
                           library_set_sha256=pins['runner_library_set_sha256'][setting], mode='auto')
            exposure = json.loads((ledger / (unit + '.exposure.json')).read_text())
            result = json.loads((ledger / (unit + '.result.json')).read_text())
            if exposure['binding'] != binding or result['binding'] != binding or result.get('reaped') is not True or type(result.get('rc')) is not int:
                raise ValueError('native binding/reaping')
            for suffix in ('stdout', 'stderr', 'txt'):
                path = ledger / (unit + '.' + suffix)
                expected = result[suffix + '_sha256']
                if (expected is None and path.exists()) or (expected is not None and (not path.exists() or sha(path) != expected)):
                    raise ValueError('native output drift')
            path = ledger / (unit + '.txt')
            text = path.read_text() if path.exists() else ''
            tokens = None
            if result['rc'] == 0 and not result.get('timedout', False):
                try:
                    tokens = parse_tokens((ledger / (unit + '.stdout')).read_text(), text)
                except ValueError:
                    if text.strip():
                        raise
            hypothesis = tokens['hypothesis_with_unk'] if tokens is not None else ''
            bad = result['rc'] != 0 or result.get('timedout', False) or not hypothesis.strip()
            if bad:
                failures.append(dict(unit=unit, clip_id=clip, setting=setting, rc=result['rc'],
                                     timedout=result.get('timedout', False), empty=not hypothesis.strip()))
            failed |= bad
            texts.append(hypothesis)
            evidence.append(tokens)
        if not texts or position != record['frames']:
            raise ValueError('incomplete chunks')
        rows.append(dict(utterance_id=clip, pcm_sha256=record['pcm_sha256'], reference_raw=record['reference_raw'],
                         hypothesis_chunks=[''] * len(texts) if failed else texts,
                         chunk_indices=list(range(len(texts))), duration_s=record['frames'] / 16000,
                         language='en', set_id='fleurs-validation', reference_track='standard', content_stratum='clean_read',
                         decode_status='error' if failed else 'ok', token_evidence=evidence,
                         unk_count_unknown=any(t is None for t in evidence)))
    return rows, failures, units


def score_rows(rows, norm):
    from scripts.speech.stt_bakeoff import stt_norm
    from scripts.speech.stt_bakeoff.scorer import score_utterance, bootstrap_pooled_wer
    from scripts.kernel_rnd.autokernel.adapters import whisper_stt
    contract = stt_norm.contract_check(norm)
    if norm == 'stt_norm/v1' and contract.outcome != 'PASS':
        raise ValueError('normalizer contract')
    props = stt_norm.check_properties([(r['reference_raw'], 'en') for r in rows] +
                                     [(h, 'en') for r in rows for h in r['hypothesis_chunks']], norm)
    if props.check.outcome != 'PASS':
        raise ValueError('normalizer properties')
    scored = [score_utterance(r, normaliser_id=norm, segmentation_mode='vad_30s', repetition_envelope=None) for r in rows]
    if any(r['class'] == 'VOID' for r in scored):
        raise ValueError('scorer VOID')
    taxonomy = {c: sum(r['class'] == c for r in scored) for c in whisper_stt.FAILURE_CLASSES}
    if not scored or sum(taxonomy.values()) != len(scored):
        raise ValueError('incomplete or foreign taxonomy')
    check = whisper_stt.check_failure_taxonomy(taxonomy, n_utterances=len(scored))
    # FAIL is a valid negative correctness result, not malformed evidence.
    if check.outcome not in ('PASS', 'FAIL'):
        raise ValueError('invalid taxonomy outcome')
    errors, refs = [r['errors'] for r in scored], [r['reference_tokens'] for r in scored]
    cell = dict(n=len(rows), errors=sum(errors), reference_tokens=sum(refs),
                wer_percent=whisper_stt.pooled_corpus_wer(errors, refs),
                ci95=bootstrap_pooled_wer(errors, refs, resamples=4000, seed=146064415),
                taxonomy_outcome=check.outcome, classes=dict(collections.Counter(r['class'] for r in scored)),
                unk_count_observed=sum(t['unk_count'] for r in rows for t in r['token_evidence'] if t is not None),
                unk_count_complete=not any(r['unk_count_unknown'] for r in rows),
                normalizer_contract=contract.outcome, normalizer_properties=props.check.outcome,
                normalizer_route='COULD_NOT_CHECK' if any(r['class'] in ('unknown_marker', 'numeral_uncovered') for r in scored) else 'CHECKED',
                repetition_check='COULD_NOT_CHECK')
    return cell, scored


def main(config_path):
    cfg = json.loads(Path(config_path).read_text())
    for path, digest in cfg['input_pins'].items():
        if sha(path) != digest:
            raise ValueError('prepared input drift: ' + path)
    research = Path(cfg['research'])
    if subprocess.check_output(['git', '-C', str(research), 'rev-parse', 'HEAD'], text=True).strip() != RESEARCH_COMMIT:
        raise ValueError('scorer commit drift')
    subprocess.run(['git', '-C', str(research), 'diff', '--exit-code', 'HEAD', '--', 'scripts'], check=True, stdout=subprocess.DEVNULL)
    sys.path.insert(0, str(research))
    smoke = os.environ.get('FILLER_SMOKE') == '1'
    output = Path(cfg['smoke_output'] if smoke else cfg['output'])
    output.mkdir(exist_ok=True)
    if smoke:
        # Real pinned scorer, synthetic noncohort decode-error control only.
        rows = [dict(utterance_id='synthetic', pcm_sha256=hashlib.sha256(b'\x00\x00' * 16000).hexdigest(), reference_raw='hello world',
                     hypothesis_chunks=[''], chunk_indices=[0], duration_s=1, language='en', set_id='fixture',
                     reference_track='standard', content_stratum='clean_read', decode_status='error',
                     token_evidence=[None], unk_count_unknown=True)]
        cell, _ = score_rows(rows, 'stt_norm/v1')
        if cell['errors'] != 2 or cell['classes'].get('decode_error') != 1 or cell['taxonomy_outcome'] != 'FAIL':
            raise ValueError('synthetic deletion control')
        write(output / 'summary.json', dict(smoke=True, epoch=time.time(), cell=cell))
        return
    native = Path(cfg['native'])
    ledger = native / 'validation-results'
    if list(ledger_digest(ledger)) != cfg['ledger_pin']:
        raise ValueError('ledger drift')
    spec = importlib.util.spec_from_file_location('native_token_parser', native / 'nemo_tokens.py')
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    pins = json.loads((native / 'INPUT-PINS.json').read_text())
    records = [r for r in json.loads(Path(cfg['manifest']).read_text())['records'] if r['language'] == 'en_us']
    if len(records) != 394 or len({r['clip_id'] for r in records}) != 394:
        raise ValueError('cohort denominator')
    report = dict(schema='stt5-unified-validation-score/v1', selection_only=True, settings_selection='UNKNOWN',
                  correctness_verdict='INCONCLUSIVE', inference_run=False, seed=146064415, resamples=4000,
                  config_sha256=sha(config_path), scorer_commit=RESEARCH_COMMIT, ledger_pin=cfg['ledger_pin'],
                  cells={}, failures=[], unknown=0, timing_comparable=False)
    units = []
    for setting in SETTINGS:
        rows, failures, ids = read_setting(ledger, records, pins, cfg['source_catalog_sha256'], setting, parser.parse)
        units += ids
        report['failures'] += failures
        for norm in ('stt_norm/v1', 'stt_norm/v2'):
            cell, scored = score_rows(rows, norm)
            report['cells'][f'{setting}|auto|{norm}|en'] = cell
            write(output / f'per-utterance-{setting}-{norm.rsplit("/", 1)[-1]}.json', scored)
            write(output / 'summary.json', report)
            print('scored', setting, norm, cell['n'], flush=True)
    expected = {p.name.removesuffix('.exposure.json') for p in ledger.glob('*.exposure.json')}
    actual = {p.name.removesuffix('.result.json') for p in ledger.glob('*.result.json')}
    if set(units) != expected or set(units) != actual or len(units) != 2370 or len(report['failures']) != 11:
        raise ValueError('terminal accounting mismatch')
    if list(ledger_digest(ledger)) != cfg['ledger_pin']:
        raise ValueError('ledger changed during scoring')
    report['complete'] = True
    write(output / 'summary.json', report)
    write(output / 'COMPLETE.json', dict(result_sha256=sha(output / 'summary.json'), cells=12))


if __name__ == '__main__':
    main(sys.argv[1])
