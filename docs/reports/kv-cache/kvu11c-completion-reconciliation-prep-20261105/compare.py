#!/usr/bin/env python3
"""Offline same-attempt comparator. Never imports job or invokes any launcher."""
import ast, hashlib, json
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/kvfork/kvu11c-gpu-mechanics-smoke-r2-20261105')
expected={'job.py':'df1edf33ebd95897311f2cb28653f0bc379184371f2575e388f437158ca90279','out/RESULT.json':'7a8254c6b44c9eb04b51bb7ed7bcdeaaf8345f4d1164b3feb9365aae86655e91'}
for name,seal in expected.items():
    if hashlib.sha256((D/name).read_bytes()).hexdigest()!=seal: raise SystemExit('source/result drift: '+name)
tree=ast.parse((D/'job.py').read_text())
ns={'r':json.loads((D/'out/RESULT.json').read_text()), 'signal':type('Signals',(),{'SIGTERM':15}),'all':all,'any':any}
for node in tree.body:
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in {'TEXT','VOICE','MODEL_SHA256','MODEL_RECEIPT_BODY_SHA256','MODEL_STAT_SNAPSHOT','TALKER','CODEC'}:
        # Only constant strings, dicts and str(Path) model-key expressions occur here.
        if node.targets[0].id in {'TALKER','CODEC'}: ns[node.targets[0].id]=ast.literal_eval(node.value.args[0])
        else: exec(compile(ast.Module(body=[node],type_ignores=[]),'<sealed constants>','exec'),{'str':str},ns)
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='complete')
rows=[]
for n in fn.body:
    if isinstance(n,ast.Assert):
        value=bool(eval(compile(ast.Expression(n.test),'<sealed completion assertion>','eval'),ns))
        rows.append({'line':n.lineno,'predicate':ast.unparse(n.test),'pass':value})
print(json.dumps({'scope':'retained native-result assertion comparison only; not grant PASS; no replay','assertions':rows,'historical_outer_environment':'not captured; cannot reconstruct STOP/deadline','source_defect':'complete() calls check_run_limits requiring FILLER_STOPFILE, while runner exports it only inside --inner; outer is_complete suppresses stderr','FILLER_ID':'not read by job.py'},indent=2))
