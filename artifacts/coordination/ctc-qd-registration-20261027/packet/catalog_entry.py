#!/usr/bin/env python3
"""Build one explicit checker-native catalog entry; prints JSON, changes no files."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import registration_sweep as sweep

def reference(path):
    path = Path(path)
    sweep.require(path.is_absolute(), 'native record path must be absolute')
    raw = sweep.read_regular(path)
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--candidate', required=True); p.add_argument('--id', required=True)
    p.add_argument('--recipe'); p.add_argument('--session'); p.add_argument('--anchor', action='append', default=[])
    p.add_argument('--server'); p.add_argument('--resolutions'); p.add_argument('--non-model')
    p.add_argument('--native-validation')
    a = p.parse_args()
    col, rows, _ = sweep.rows(a.candidate)
    sweep.require(set(rows) == {a.id}, 'one exact candidate required')
    cells = rows[a.id]
    meta = {'row_sha256': sweep.digest(cells)}
    if a.non_model:
        sweep.require(not (a.recipe or a.session or a.anchor or a.server or a.resolutions or a.native_validation), 'non-model conflicts with model metadata')
        meta['non_model'] = a.non_model
    else:
        sweep.require(bool(a.recipe and a.session and a.anchor and a.native_validation), 'recipe, session, native anchors and validation receipt required')
        ref = reference(a.recipe); recipe = sweep.record(ref)
        argv = recipe['argv']
        raw_argv = hashlib.sha256('\0'.join(argv).encode()).hexdigest()
        shape = (recipe['model']['sha256'], recipe['drafter']['sha256'] if recipe.get('drafter') is not None else None,
                 recipe['executable']['sha256'], tuple(sorted((x['role'], x['sha256']) for x in recipe['dsos'])),
                 'sha256:nul-joined-utf8-argv/v1', raw_argv)
        load = sweep.digest([shape, recipe['launch_env'], recipe['relevant_environment'], recipe['absent_environment']])
        meta.update(recipe=ref, session={'id': a.session, 'load_sha256': load, 'anchors': [reference(x) for x in a.anchor]})
        if a.server: meta['server'] = reference(a.server)
        if a.resolutions: meta['resolutions'], _ = sweep.load_json(a.resolutions)
        meta['native_validation'] = reference(a.native_validation)
        import registration_gate
        registration_gate.native_binding(meta)
    sweep.project(meta, cells, col)
    print(json.dumps(meta, sort_keys=True))

if __name__ == '__main__':
    try: main()
    except (sweep.Invalid, sweep.vf.Malformed, KeyError, TypeError, OSError, ValueError) as e:
        print('refuse: ' + str(e), file=sys.stderr); sys.exit(2)
