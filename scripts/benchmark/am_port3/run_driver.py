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


def run(driver, config_path, converted=None):
    config = json.loads(Path(config_path).read_text())
    if config.get('source_commit') != PIN:
        raise ValueError('native driver requires approved experimental source pin')
    if config.get('mode') == 'reload':
        if converted is None:
            raise ValueError('reload requires a completed conversion manifest')
        verify_reload(config, converted)
    elif config.get('mode') != 'capture':
        raise ValueError('driver mode must be capture or reload')
    subprocess.run([str(Path(driver).resolve()), str(Path(config_path).resolve())], check=True)
    if config['mode'] == 'capture':
        seal_provenance(config['out'])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--driver', required=True)
    p.add_argument('--config', required=True)
    p.add_argument('--converted')
    args = p.parse_args()
    run(args.driver, args.config, args.converted)
