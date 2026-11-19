#!/usr/bin/env python3
"""Offline, selection-only scoring of the retained STT5 baseline ledger.

Uses the unchanged P-STT-1 scorer at the plan's research commit. Missing exposed
results remain unknown; a full-deletion sensitivity column retains their tokens.
No inference, acceptance decision, source mutation, or unknown-unit redraw.
"""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

RESEARCH_COMMIT = '99301fa149af86a6f9743d2b0405c9234ba39586'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ledger_digest(root):
    files = sorted(p for p in root.iterdir() if p.suffix in ('.json', '.txt', '.stdout', '.stderr'))
    files += sorted((root / 'chunks').glob('*.chunks.json'))
    digest = hashlib.sha256()
    for path in files:
        digest.update((str(path.relative_to(root)) + ' ' + sha(path) + '\n').encode())
    return digest.hexdigest(), len(files)


def write(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    temp.replace(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('config', type=Path)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text())
    native, research, output = (Path(cfg[k]) for k in ('native', 'research', 'output'))
    output.mkdir(exist_ok=True)
    for name, digest in cfg['input_pins'].items():
        if sha(name) != digest:
            raise ValueError('input drift: ' + name)
    if subprocess.check_output(['git', '-C', str(research), 'rev-parse', 'HEAD'], text=True).strip() != RESEARCH_COMMIT:
        raise ValueError('scorer commit drift')
    subprocess.run(['git', '-C', str(research), 'diff', '--exit-code', 'HEAD', '--', 'scripts'], check=True, stdout=subprocess.DEVNULL)
    ledger = native / 'validation-results'
    digest, count = ledger_digest(ledger)
    if [digest, count] != cfg['ledger_pin']:
        raise ValueError('ledger drift')
    sys.path.insert(0, str(research))
    from scripts.speech.stt_bakeoff.scorer import score_utterance, bootstrap_pooled_wer, _validate_manifest, validate_arm
    from scripts.speech.stt_bakeoff import stt_norm
    from scripts.kernel_rnd.autokernel.adapters import whisper_stt

    pins = json.loads((native / 'INPUT-PINS.json').read_text())
    records = json.loads(Path(cfg['manifest']).read_text())['records']
    report = dict(schema='cs8-stt5-validation-score/v2', selection_only=True,
                  correctness_verdict='INCONCLUSIVE', reason='exposed unknowns; repetition envelope unavailable',
                  inference_run=False, source_commit=RESEARCH_COMMIT, config_sha256=sha(args.config),
                  scorer_sha256=sha(research / 'scripts/speech/stt_bakeoff/scorer.py'),
                  seed=146064415, resamples=4000, ledger_sha256=digest, ledger_files=count,
                  unknown_policy='retained; full-utterance deletion sensitivity, never observed decode_error',
                  timing_comparable=False, cells={}, unknowns=[], thread_width_exposures={})
    widths = collections.Counter()
    for model in ('turbo', 'large'):
        for mode in ('forced', 'auto'):
            rows, unknown_ids = [], set()
            for rec in records:
                clip = rec['clip_id']
                key = hashlib.sha256(clip.encode()).hexdigest()
                chunk = json.loads((ledger / 'chunks' / (key + '.chunks.json')).read_text())
                if (chunk['status'], chunk['id'], chunk['original_pcm_sha256'], chunk['original_wav_sha256']) != ('ok', clip, rec['pcm_sha256'], rec['wav_sha256']):
                    raise ValueError('chunk identity')
                texts, failed, position = [], False, 0
                for i, part in enumerate(chunk['chunks']):
                    if part['index'] != i or part['start_sample'] != position:
                        raise ValueError('chunk coverage')
                    position = part['end_sample']
                    unit = hashlib.sha256(f'{model}|{mode}|{clip}|{i}'.encode()).hexdigest()
                    ep, rp = ledger / (unit + '.exposure.json'), ledger / (unit + '.result.json')
                    exposure = json.loads(ep.read_text())  # absent exposure is a harness fault
                    binding = dict(clip_id=clip, chunk_index=i, chunk_pcm_sha256=part['pcm_sha256'],
                                   chunk_wav_sha256=part['wav_sha256'], input_sha256=pins['validation_sha256'],
                                   plan_sha256=pins['plan_sha256'], source_sha256=cfg['source_catalog_sha256'],
                                   model_sha256=pins['models'][model], binary_sha256=pins['whisper_binary_sha256'],
                                   library_set_sha256=pins['whisper_library_set_sha256'], mode=mode)
                    if exposure['binding'] != binding:
                        raise ValueError('exposure binding')
                    argv = exposure['command']
                    widths[str(argv[argv.index('-t') + 1])] += 1
                    if not rp.exists():
                        report['unknowns'].append(dict(unit=unit, language=rec['language'], model=model, mode=mode))
                        unknown_ids.add(clip)
                        texts.append('')
                        failed = True
                        continue
                    result = json.loads(rp.read_text())
                    if result['binding'] != binding or result.get('reaped') is not True or type(result.get('rc')) is not int:
                        raise ValueError('result binding/reaping')
                    for suffix in ('stdout', 'stderr', 'txt'):
                        path = ledger / (unit + '.' + suffix)
                        expected = result[suffix + '_sha256']
                        if (expected is None and path.exists()) or (expected is not None and (not path.exists() or sha(path) != expected)):
                            raise ValueError('output drift')
                    path = ledger / (unit + '.txt')
                    text = path.read_text() if path.exists() else ''
                    failed |= result['rc'] != 0 or not text.strip()
                    texts.append(text)
                if not texts or position != chunk['n_samples']:
                    raise ValueError('incomplete chunks')
                rows.append(dict(utterance_id=clip, pcm_sha256=rec['pcm_sha256'], reference_raw=rec['reference_raw'],
                                 hypothesis_chunks=[''] * len(texts) if failed else texts,
                                 chunk_indices=list(range(len(texts))), duration_s=rec['frames']/16000,
                                 language=rec['language'].split('_')[0], set_id='fleurs-validation',
                                 reference_track='standard', content_stratum='clean_read',
                                 decode_status='error' if failed else 'ok'))
            arm = dict(arm_id=model, arm_kind='offline_utterance_final', model_family='whisper',
                       runner_id='whisper.cpp-whisper-cli', runner_commit='b307379226d93d9c5ed790d7cea0626613c0ef4b',
                       ggml_version='0.18.0', quant='F16', backend='cpu', weights_sha256=pins['models'][model])
            manifest = dict(schema_version='stt_bakeoff.raw_manifest/v1', corpus_id='fleurs-validation',
                            stratum='selection', language_mode=mode, segmentation_mode='vad_30s', arm=arm, rows=rows)
            _validate_manifest(manifest)
            validate_arm(arm)
            # Unknown is outside the scorer's two-status vocabulary: do not export
            # a raw manifest that misrepresents unknown as an observed error.
            for norm in ('stt_norm/v1', 'stt_norm/v2'):
                contract = stt_norm.contract_check(norm)
                if norm == 'stt_norm/v1' and contract.outcome != 'PASS':
                    raise ValueError('normalizer contract')
                props = stt_norm.check_properties([(r['reference_raw'], r['language']) for r in rows] +
                                                  [(h, r['language']) for r in rows for h in r['hypothesis_chunks']], norm)
                if props.check.outcome != 'PASS':
                    raise ValueError('normalizer properties')
                scored = [score_utterance(r, normaliser_id=norm, segmentation_mode='vad_30s', repetition_envelope=None) for r in rows]
                for item in scored:
                    item['native_outcome'] = 'unknown' if item['utterance_id'] in unknown_ids else 'observed'
                write(output / f'per-utterance-{model}-{mode}-{norm.rsplit("/", 1)[-1]}.json', scored)
                for lang in ('en', 'it', 'de', 'fr'):
                    cases = [r for r in scored if r['language'] == lang]
                    if any(r['class'] == 'VOID' for r in cases):
                        raise ValueError('canonical scorer VOID')
                    errors, refs = [r['errors'] for r in cases], [r['reference_tokens'] for r in cases]
                    unknown_n = sum(r['native_outcome'] == 'unknown' for r in cases)
                    cell = dict(n=len(cases), reference_tokens=sum(refs), errors_full_deletion_sensitivity=sum(errors),
                                unknown_utterances=unknown_n, unknown_reference_tokens=sum(r['reference_tokens'] for r in cases if r['native_outcome'] == 'unknown'),
                                wer_percent_full_deletion_sensitivity=whisper_stt.pooled_corpus_wer(errors, refs),
                                ci95_full_deletion_sensitivity=bootstrap_pooled_wer(errors, refs, resamples=4000, seed=146064415),
                                repetition_check='COULD_NOT_CHECK', normalizer_contract=contract.outcome,
                                normalizer_properties=props.check.outcome,
                                observed_classes=dict(collections.Counter(r['class'] for r in cases if r['native_outcome'] == 'observed')))
                    report['cells'][f'{model}|{mode}|{norm}|{lang}'] = cell
                    report['thread_width_exposures'] = dict(widths)
                    write(output / 'validation-score.json', report)
                    print('scored', model, mode, norm, lang, 'n', len(cases), 'unknown', unknown_n, flush=True)
    if len(report['unknowns']) != 3 or dict(widths) != {'24': 2613, '32': 3140, '8': 39}:
        raise ValueError('unexpected ledger accounting')
    report['complete'] = True
    write(output / 'validation-score.json', report)
    write(output / 'COMPLETE.json', dict(cells=len(report['cells']), result_sha256=sha(output / 'validation-score.json')))


if __name__ == '__main__':
    main()
