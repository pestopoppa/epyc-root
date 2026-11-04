#!/usr/bin/env python3
import json
from pathlib import Path
import custody
D=Path(__file__).resolve().parent
b=json.loads((D/'binding.json').read_text())
assert custody.build_identity()==b['build'] and custody.model_identity(D/'model.json')==b['model']
assert custody.digest('/usr/bin/gdb')==b['gdb_sha256']
assert all(custody.digest(D/n)==h for n,h in b['runner_files'].items())
