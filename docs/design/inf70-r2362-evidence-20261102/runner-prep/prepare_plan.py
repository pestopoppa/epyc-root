#!/usr/bin/env python3
"""Dry-run only: derive a two-build R23-62 diagnostic plan from the codified recipe."""
import hashlib, json, os, subprocess, sys
from pathlib import Path
repo=Path('/workspace/repos/epyc-inference-research')
recipe=repo/'scripts/lib/qwen38_flash_next_recipe.py'
binaries={'old':Path('/mnt/raid0/llm/tmp/inf70/agents/champion3/bin-c3'), 'instrument':Path('/mnt/raid0/llm/tmp/inf70/agents/retest1/bin-r1')}
knob='/mnt/raid0/llm/tmp/codex-r2362-audit-20261102/run/knob.page'
plans={}
for arm, bindir in binaries.items():
 cmd=[sys.executable,str(recipe),'emit-serve-command','--bindir',str(bindir),'--plain']
 p=json.loads(subprocess.check_output(cmd,cwd=repo))
 assert p['env']['GGML_NOHUGEPAGE_PROCESS']=='1'
 p['env'].pop('GGML_NOHUGEPAGE_PROCESS')
 if arm=='instrument':
  p['env']['GGML_KNOB_FILE']=knob
  p['required_knob_payload']={'GGML_SOLO_YIELD_ROWCOL':'0','GGML_SCALE_SPLIT':'0','GGML_TINY_SOLO_CLAMP':'1','GGML_GET_ROWS_SOLO':'0'}
 p['server_sha256']=hashlib.sha256((bindir/'llama-server').read_bytes()).hexdigest()
 plans[arm]=p
assert plans['old']['env'].get('GGML_NOHUGEPAGE_PROCESS') is None
assert plans['instrument']['env'].get('GGML_NOHUGEPAGE_PROCESS') is None
print(json.dumps({'mode':'PREPARATION_ONLY_NOT_EXECUTABLE','recipe_sha256':hashlib.sha256(recipe.read_bytes()).hexdigest(),'pairs':[['old','instrument'] if i%2==0 else ['instrument','old'] for i in range(12)],'plans':plans,'missing':['materiality boundary and fixed stopping rule','independent complete DSO manifest and live linkage','model-shard digests','private knob-page initialisation and mapped/readback verification','positive THP controls for both arms','parity and contention screens','resource claim and host-health preflight','integrated runner and tests']},indent=2))
