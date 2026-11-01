#!/usr/bin/env python3
"""Fail-closed completeness predicate for the engine, never executes compute."""
import json, sys
from pathlib import Path

def complete(mode, path):
    try:
        data=json.loads(Path(path).read_text())
        if mode=='qualification':
            return data.get('kind')=='qualification_control' and data.get('http_status')==200 and data.get('target_exposed') is False and isinstance(data.get('draft_n'),int) and not isinstance(data.get('draft_n'),bool) and data['draft_n']>0
        if mode=='full':
            return data.get('state')=='complete_raw' and data.get('partial') is False and data.get('divergence_known') is True and all(isinstance(data.get(k),(int,float)) and not isinstance(data.get(k),bool) and 0<=data[k]<=1 for k in ('hybrid_acceptance','legacy_acceptance'))
    except (OSError, ValueError, TypeError):
        pass
    return False

if __name__=='__main__':
    sys.exit(0 if len(sys.argv)==3 and complete(sys.argv[1],sys.argv[2]) else 1)
