#!/usr/bin/env python3
"""Summarize only existing native receipts; never invent missing counts."""
import json,pathlib,sys
D=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path(__file__).resolve().parent/'run'
for p in sorted(D.glob('*.response.json')):
 x=json.loads(p.read_text());print(json.dumps({'arm':x.get('arm'),'draft_n':x.get('draft_n'),'draft_n_accepted':x.get('draft_n_accepted'),'acceptance':x.get('acceptance'),'native_tokens_present':x.get('tokens') is not None}))
for n in ('PARTIAL.json','TERMINAL.json'):
 p=D/n
 if p.exists():print(n,p.read_text().strip())
