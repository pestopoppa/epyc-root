#!/usr/bin/env python3
"""Bounded public-fixture recipe check; never reads validation/test ledgers."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import stt5_crisp_runtime_probe as probe


def assess(waves, references):
    """A rate is descriptive only; missing work cannot become zero-cost audio."""
    complete = len(waves) == 6 and all(
        len(w['summary']['cases']) == 8 and w['summary']['verdict'] == 'PASS'
        and w['summary']['workers'] == 8 for w in waves)
    parity = []
    for wave in waves:
        if wave['duration_label'] != 'full':
            continue
        for result in wave['summary']['cases']:
            ref = references[result['case']]
            parity.append(dict(case=result['case'], wave=wave['index'],
                               matches=result.get('tokens', {}).get('token_ids') == ref))
    return dict(complete=complete, verdict='PASS' if complete and len(parity) == 16
                and all(p['matches'] for p in parity) else 'INCONCLUSIVE',
                repeat_agreement=parity,
                aggregate_wall_rtf=sum(w['wall_s'] for w in waves) /
                sum(w['audio_s'] * 8 for w in waves) if complete else None,
                slowest_wave_wall_rtf=max(w['wall_s'] / (w['audio_s'] * 8)
                                         for w in waves) if complete else None,
                rate_scope='descriptive public-fixture envelope only; not production rate evidence',
                independent_runner_parity=False, validation_exposed=False)


def main():
    config_path = Path(sys.argv[1])
    cfg = json.loads(config_path.read_text())
    for path, digest in cfg['pins'].items():
        if probe.sha(path) != digest:
            raise ValueError('prepared source/reference drift: ' + path)
    smoke = os.environ.get('FILLER_SMOKE') == '1'
    output = Path(cfg['smoke_output'] if smoke else cfg['output'])
    output.mkdir(exist_ok=True)
    references = {key: json.loads(Path(path).read_text())['tokens']['token_ids']
                  for key, path in cfg['references'].items()}
    waves = []
    # Every wave has its own no-redraw exposure ledger; interrupted waves remain
    # incomplete and are never re-invoked here. A stopped run needs owner filing.
    for index, entry in enumerate(cfg['waves']):
        if index and smoke:
            break
        if Path(os.environ.get('FILLER_STOPFILE', str(output.parent / 'STOP'))).exists() or time.time() >= float(os.environ.get('FILLER_DEADLINE', 'inf')) - 30:
            return 75
        marker = output / f'wave-{index}.json'
        if marker.exists():
            raise ValueError('calibration invocation already exposed; owner filing required')
        probe.write_new(marker, dict(index=index, started_epoch=time.time()))
        started = time.monotonic()
        sys.argv = ['probe', entry['config']]
        rc = probe.main()
        wave_cfg = json.loads(Path(entry['config']).read_text())
        native = Path(wave_cfg['smoke_output'] if smoke else wave_cfg['output']) / 'summary.json'
        if rc or not native.exists():
            probe.write_new(output / 'partial.json', dict(index=index, rc=rc,
                            reason='stopped or missing native summary; no redraw'))
            return 75
        waves.append(dict(index=index, duration_label=entry['duration_label'],
                          audio_s=entry['audio_s'], wall_s=time.monotonic() - started,
                          native_summary=str(native), native_sha256=probe.sha(native),
                          summary=json.loads(native.read_text())))
        if waves[-1]['summary']['verdict'] != 'PASS':
            break
    result = assess(waves, references)
    result.update(schema='stt5-crisp-public-calibration/v1', waves=waves,
                  smoke=smoke, config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest())
    probe.write_new(output / 'summary.json', result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
