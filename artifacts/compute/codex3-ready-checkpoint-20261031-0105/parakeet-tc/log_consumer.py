#!/usr/bin/env python3
"""Summarize retained launcher and qualification logs for result filing."""
import json,pathlib
D=pathlib.Path(__file__).resolve().parent
for p in sorted(D.glob('*.log')):
 print(json.dumps({'path':str(p),'bytes':p.stat().st_size,'text':p.read_text(errors='replace')}))
p=D/'ws58-launcher.out'
if p.exists():print(json.dumps({'path':str(p),'bytes':p.stat().st_size,'text':p.read_text(errors='replace')}))
