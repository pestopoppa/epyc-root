#!/usr/bin/env python3
"""Only a validated PASS may cause the launcher to mark the row complete."""
import json
from pathlib import Path
import sys
import custody
import native_files
D=Path(__file__).resolve().parent
try:
    result=json.loads((D/'out/RESULT.json').read_text());binding=json.loads((D/'binding.json').read_text())
    if result.get('schema')!='kpf17.oracle-test.v1' or result.get('sealed') is not True or result.get('smoke') is not False:
        raise ValueError('invalid native result schema/seal')
    if result.get('status') != 'PASS' or result.get('process_verified_dead') is not True:
        raise ValueError('result is not complete')
    if result.get('build')!=binding.get('build') or result.get('model')!=binding.get('model'):
        raise ValueError('result custody mismatch')
    native_files.validate(result.get('files'), D/'out', custody.digest)
except (OSError,ValueError,KeyError,TypeError):sys.exit(1)
