#!/usr/bin/env python3
"""Validate explicit Research native exports; print a bound receipt, never start a server.

The owner must pin and inspect the Research checkout, secure these inputs and the
output, and separately inspect actual ORCH launch/residency custody. This does not
authenticate the owner or establish live server residency.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import registration_sweep as sweep


def ref(path):
    p=Path(path)
    sweep.require(p.is_absolute(), 'record path must be absolute')
    return {'path': str(p), 'sha256': hashlib.sha256(sweep.read_regular(p)).hexdigest()}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--research-root', required=True); p.add_argument('--recipe', required=True)
    p.add_argument('--anchor', required=True, action='append'); p.add_argument('--server')
    p.add_argument('--server-custody')
    a=p.parse_args()
    root=Path(a.research_root).resolve()
    commit=subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], check=True, text=True, capture_output=True).stdout.strip()
    sys.path.insert(0, str(root/'scripts/kernel_rnd'))
    from autokernel.loop.resolved_recipe import CanonicalResolvedRecipe
    from autokernel.loop.experiment_plan import ExperimentPlan
    recipe_ref=ref(a.recipe); recipe=CanonicalResolvedRecipe.from_dict(sweep.record(recipe_ref))
    recipe.validate_launch(recipe.template, recipe.build_dir, recipe.port)
    anchors=[ref(x) for x in a.anchor]
    for anchor in anchors: ExperimentPlan.from_dict(sweep.record(anchor))
    server_ref=ref(a.server) if a.server else None
    if server_ref:
        launch=sweep.record(server_ref)
        sweep.require(launch.get('schema') == sweep.LAUNCH, 'unsupported server record')
    else: sweep.require(not a.server_custody, 'server custody without server')
    src=root/'scripts/kernel_rnd/autokernel/loop/resolved_recipe.py'
    plan_src=root/'scripts/kernel_rnd/autokernel/loop/experiment_plan.py'
    print(json.dumps({'schema':'epyc.registration_native_validation.v1', 'recipe':recipe_ref,
                      'anchors':anchors, 'server':server_ref,
                      'server_custody':ref(a.server_custody) if a.server_custody else None,
                      'server_custody_status': 'provided' if a.server_custody else ('UNKNOWN' if server_ref else 'not_applicable'),
                      'validator_source':f'{commit}:{ref(src)["sha256"]}:{ref(plan_src)["sha256"]}'}, sort_keys=True))

if __name__ == '__main__':
    try: main()
    except (sweep.Invalid, OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as e:
        print('refuse: '+str(e), file=sys.stderr); sys.exit(2)
