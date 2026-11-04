#!/usr/bin/env python3
"""Refuse role/recipe declarations inconsistent with compiled serving truth.

This is an exclusion check only: a match does not prove a best recipe, floor,
or eligibility for a different benchmark context and cannot authorize a run.
"""
import argparse
import hashlib
import json
from pathlib import Path
import yaml

ROLES = ('architect_critic', 'coder_escalation', 'ingest_long_context')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def draft_arg(recipe):
    argv = recipe['extra_server_args']
    aliases = ('-md', '--model-draft')
    seen = [(i, value) for i, value in enumerate(argv) if value in aliases]
    if len(seen) != 1 or seen[0][0] + 1 >= len(argv):
        return None
    return argv[seen[0][0] + 1]

def check(priors, plan):
    findings = []
    for entry in plan['models']:
        role = entry['role']
        if role not in ROLES:
            raise ValueError('unexpected role: '+str(role))
        serving = priors['roles'][role]['serving']
        server = serving['server_role']
        req = serving['launch']['requirements']
        if server != 'architect_critic' or serving['ports'] != [8083]:
            raise ValueError('serving alias changed: '+role)
        spec = priors['roles'][server]['serving']['launch']['runtime']['flags']['spec']
        if not spec['enabled'] or spec['type'] != 'draft-dflash':
            raise ValueError('compiled serving draft changed: '+role)
        expected_draft = req['draft_model_path']
        if entry['model_path'] != req['model_path']:
            findings.append({'role': role, 'issue': 'model differs from compiled serving model'})
        for arm in ('baseline','candidate'):
            actual = draft_arg(entry[arm]['recipe'])
            if actual != expected_draft:
                findings.append({'role': role, 'arm': arm,
                                 'issue': 'draft differs from compiled shared server',
                                 'expected': expected_draft, 'actual': actual})
    if {e['role'] for e in plan['models']} != set(ROLES):
        raise ValueError('scope does not match three served roles')
    return findings

def main():
    p=argparse.ArgumentParser();p.add_argument('--priors',required=True);p.add_argument('--plan',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    priors=yaml.safe_load(Path(a.priors).read_text());plan=json.loads(Path(a.plan).read_text())
    findings=check(priors,plan)
    out={'schema':'m4.serving-binding-exclusions.v1','priors_sha256':sha(a.priors),'plan_sha256':sha(a.plan),'findings':findings,
         'scope':'compiled current shared serving recipe only; no claim of best speed, no floor, no context extrapolation',
         'eligibility':'REFUSE' if findings else 'UNRESOLVED'}
    Path(a.output).write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out))
    return 2 if findings else 3  # No success exit: best recipe and floor remain unbound.
if __name__=='__main__': raise SystemExit(main())
