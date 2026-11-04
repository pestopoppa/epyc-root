#!/usr/bin/env python3
"""Fail-closed completeness predicate for the engine, never executes compute."""
import json, sys
from mode_guard import native_acceptance
from pathlib import Path

def complete(mode, path):
    try:
        data=json.loads(Path(path).read_text())
        if mode=='qualification':
            return data.get('kind')=='qualification_control' and data.get('http_status')==200 and data.get('target_exposed') is False and native_acceptance(data.get('draft_n'),data.get('draft_n_accepted')) is not None and type(data.get('token_count')) is int and data['token_count']>0 and all(isinstance(data.get(k),str) and len(data[k])==64 and all(c in '0123456789abcdef' for c in data[k]) for k in ('plan_sha256','full_model_catalog_sha256','source_sha256','grant_sha256'))
        if mode=='full':
            return data.get('state')=='complete_raw' and data.get('partial') is False and data.get('divergence_known') is True and all(data.get(k)==200 for k in ('hybrid_http_status','legacy_http_status')) and all(isinstance(data.get(k),(int,float)) and not isinstance(data.get(k),bool) and 0<=data[k]<=1 for k in ('hybrid_acceptance','legacy_acceptance'))
    except (OSError, ValueError, TypeError):
        pass
    return False

if __name__=='__main__':
    sys.exit(0 if len(sys.argv)==3 and complete(sys.argv[1],sys.argv[2]) else 1)
