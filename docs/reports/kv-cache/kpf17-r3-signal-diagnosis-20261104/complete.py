#!/usr/bin/env python3
"""Only a validated PASS may cause the launcher to mark the row complete."""
import json
from pathlib import Path
import sys
import custody
D=Path(__file__).resolve().parent
try:
    result=json.loads((D/'out/RESULT.json').read_text());binding=json.loads((D/'binding.json').read_text())
    if result.get('schema')!='kpf17.oracle-test.v1' or result.get('sealed') is not True or result.get('smoke') is not False:
        raise ValueError('invalid native result schema/seal')
    if result.get('status') != 'PASS' or result.get('process_verified_dead') is not True:
        raise ValueError('result is not complete')
    if result.get('build')!=binding.get('build') or result.get('model')!=binding.get('model'):
        raise ValueError('result custody mismatch')
    for name,h in result.get('files',{}).items():
        if custody.digest(name)!=h:
            raise ValueError('result file changed: '+name)
except (OSError,ValueError,KeyError,TypeError):sys.exit(1)
