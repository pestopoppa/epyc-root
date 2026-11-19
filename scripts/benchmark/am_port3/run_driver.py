#!/usr/bin/env python3
"""Row-only native driver invocation, with fitted state/carrier content checks.

This does not grant compute. Invoke only from an admitted row launcher. The row
must prove its own linked patched build/model/input identities before calling.
"""
import argparse
import json
from pathlib import Path
import subprocess

from apply_integration import PIN
from convert import seal_provenance, verify_reload
from compact_check import check as check_compact, inputs
from fit import digest


def run(driver, config_path, converted=None, original=None):
    config = json.loads(Path(config_path).read_text())
    if config.get('source_commit') != PIN:
        raise ValueError('native driver requires approved experimental source pin')
    if config.get('mode') == 'reload':
        if converted is None:
            raise ValueError('reload requires a completed conversion manifest')
        verify_reload(config, converted)
        if config.get('capture_reload'):
            if original is None:
                raise ValueError('compact capture requires original native capture')
            inputs(original, converted)
    elif config.get('mode') != 'capture':
        raise ValueError('driver mode must be capture or reload')
    subprocess.run([str(Path(driver).resolve()), str(Path(config_path).resolve())], check=True)
    if config['mode'] == 'capture':
        seal_provenance(config['out'])
    elif config.get('capture_reload'):
        root = Path(config['out'])
        result = json.loads((root / 'RESULT.json').read_text())
        if (result.get('schema') != 'epyc.am.native-driver.v1' or result.get('mode') != 'reload'
                or result.get('captured_reload') is not True
                or result.get('decoded_tokens') != config['decode_steps']):
            raise ValueError('completed compact reload result required')
        p = json.loads((root / 'COMPACT.raw.json').read_text())
        p.update(complete_sha256=digest(root / 'native' / 'COMPLETE.json'),
                 conversion_sha256=digest(Path(converted) / 'CONVERT.json'))
        with (root / 'COMPACT.json').open('x') as f:
            f.write(json.dumps(p, indent=2) + '\n')
        checked = check_compact(original, converted, root)
        with (root / 'CHECK.json').open('x') as f:
            f.write(json.dumps(checked, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--driver', required=True)
    p.add_argument('--config', required=True)
    p.add_argument('--converted')
    p.add_argument('--original')
    args = p.parse_args()
    run(args.driver, args.config, args.converted, args.original)
