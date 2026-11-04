#!/usr/bin/env python3
import json, pathlib, sys
D=pathlib.Path(__file__).resolve().parent
mode=sys.argv[1]
p=D/('qualification/QUALIFICATION.json' if mode=='control' else 'run/COMPLETE.json')
try:
 d=json.loads(p.read_text());valid=d.get('state')=='complete' and (d.get('mode')=='control' if mode=='control' else d.get('verdict') in ('UNIFIED_BETTER','SPLIT_BETTER','NO_DIFFERENCE','MIXED'))
except (OSError,ValueError,TypeError):valid=False
sys.exit(0 if valid else 1)
