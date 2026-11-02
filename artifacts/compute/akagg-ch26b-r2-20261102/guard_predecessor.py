#!/usr/bin/env python3
"""Refuse if the failed predecessor changed or might be active; never mutate its row."""
import hashlib, json, os
from pathlib import Path
FLAGS=Path('/mnt/raid0/llm/tmp/compute-flags')
OLD='akagg-ch26b-1017-c2-20261101'
EXPECTED_ROW='ab613e1e30e96a8253a8e7a3a5a4d1f846ea492335abb870dc4c13e7b4310622'
EXPECTED_LAUNCHER='9c0ec1aa39b5df4446c8c5d00bfb6a9614c1d208e5a15151bbcb0a1caa63b20c'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(flags=FLAGS):
 row=flags/'ready'/f'{OLD}.json'; failure=flags/'dryrun'/OLD/'FAIL-1.json'
 if not row.is_file() or not failure.is_file(): raise ValueError('predecessor row/failure absent')
 if sha(row)!=EXPECTED_ROW:raise ValueError('predecessor row changed')
 d=json.loads(row.read_text()); f=json.loads(failure.read_text());launch=Path(d['launcher']['path'])
 if sha(launch)!=EXPECTED_LAUNCHER or f['row_sha256']!=EXPECTED_ROW or f['launcher_sha256']!=EXPECTED_LAUNCHER:raise ValueError('predecessor failure is stale')
 for p in (flags/'grants'/f'{OLD}.grant',flags/'dryrun'/OLD/'RUNNING.json',flags/'dryrun'/OLD/'ARMED.json'):
  if p.exists():raise ValueError(f'predecessor may be active: {p}')
 return True
if __name__=='__main__':
 try:check()
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:raise SystemExit(f'REFUSED: {e}')
