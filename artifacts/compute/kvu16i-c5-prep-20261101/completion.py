#!/usr/bin/env python3
"""Reject partial, wrong-mode and missing native completion records."""
import json
import sys
from pathlib import Path

def complete(mode,path):
    try: data=json.loads(Path(path).read_text())
    except (OSError,ValueError):return False
    if not isinstance(data,dict) or data.get('schema')!='kvu16i.c5.complete.v1' or data.get('mode')!=mode:return False
    if mode=='qualification':return data.get('verdict')=='CONTROL_COMPLETE'
    if mode=='full':return data.get('verdict') in ('HOLDS','FAILS')
    return False
if __name__=='__main__':sys.exit(0 if len(sys.argv)==3 and complete(sys.argv[1],sys.argv[2]) else 1)
