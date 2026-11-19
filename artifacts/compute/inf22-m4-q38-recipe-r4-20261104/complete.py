#!/usr/bin/env python3
import json,sys
from pathlib import Path
p=Path('/mnt/raid0/llm/tmp/inf22-m4-q38-recipe-r4-20261104/captures/run-r1/capture/RESULT.json')
try:
 r=json.loads(p.read_bytes())
 assert r['schema']=='epyc.m4.q38.recipe-comparison.result.v1' and r['status']=='COMPLETE_DIAGNOSTIC'
 assert r['plan_sha256']=='98efaa341a003b0a9fb12f7071a8e14cd7bd80b0f453ab46e975e986e77917a4'
 assert r['decision'] is None and r['gate_authorized'] is False and len(r['records'])==12
except (OSError,ValueError,KeyError,TypeError,AssertionError): sys.exit(1)
