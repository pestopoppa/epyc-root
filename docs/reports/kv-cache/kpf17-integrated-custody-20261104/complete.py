#!/usr/bin/env python3
import json,sys
from pathlib import Path
try:
 d=json.loads(Path(sys.argv[1]).read_text());w=d['witness'];samples=w['samples'];checks=d['cleanup_checks']
 assert d['status']=='PASS' and not d['qualification_only'] and d['child_reaped'] and w['error'] is None
 assert [x['mode'] for x in w['entries']]==[0,8] and {(x['mode'],x['point']) for x in samples}=={(m,p) for m in (0,8) for p in ('decode_entry','restore_dst_1','restore_dst_2')}
 assert checks and all(x['dead'] for x in checks)
except (AssertionError,TypeError,KeyError,OSError,ValueError): sys.exit(1)
