#!/usr/bin/env python3
"""Model-free authority parser checks; no region lock, model load or owner file write."""
import json
import pathlib
import tempfile
import time

import owner_pregrant as pregrant


def main():
    root = pathlib.Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='df2-pregrant-parser-', dir=root) as temp:
        directory = pathlib.Path(temp).resolve()
        pregrant.FLAGS = directory
        binary = root / 'frontend-instrument-corrected/cpu/bin/llama-server'
        record = {'kind': 'ws58.pregrant.native_test.v1', 'issuer': 'ws58',
                  'id': 'codex-ni-df2-12-1-MODEL-FREE-TEST', 'purpose': 'test', 'role': 'cpu',
                  'regions': '0-95', 'host_cpus': '0-95', 'manifest_sha256': pregrant.PROMPT_SHA,
                  'binary_sha256': pregrant.sha(binary), 'max_rss_gib': 120,
                  'model_sha256': pregrant.MODEL['cpu'][1], 'start_epoch': time.time() - 1,
                  'end_epoch': time.time() + 300}
        path = directory / 'authority.json'
        path.write_text(json.dumps(record))
        pregrant.validated_authority(path, 'test', 'cpu', binary)
        record['model_sha256'] = '0' * 64
        path.write_text(json.dumps(record))
        try:
            pregrant.validated_authority(path, 'test', 'cpu', binary)
        except RuntimeError:
            pass
        else:
            raise RuntimeError('wrong model SHA reached owner resource claim')
        image = json.loads((root / 'corrected-proof/frontdoor_mtp/IMAGE-PREFLIGHT.json').read_text())
        pregrant.validate_image_record(image, binary)
        path_key = next(iter(image['artifacts']))
        image['artifacts'][path_key]['sha256'] = '0' * 64
        try:
            pregrant.validate_image_record(image, binary)
        except RuntimeError as exc:
            assert 'artifact changed' in str(exc)
        else:
            raise RuntimeError('stale image artifact reached native dispatch')
        print('exact authority/image accepted; wrong model and stale artifact refused; MODEL_FREE only')


if __name__ == '__main__':
    main()
