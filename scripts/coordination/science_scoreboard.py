#!/usr/bin/env python3
"""D2: science credit from retained FILED verdicts; owner-debited failures.

READY-WAIT-DISK is shown separately and counts neither runnable READY nor science.
No target number exists until the owner writes science-quota.json explicitly.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import qualify_launcher as q

WORKERS=('ni','codex3','refactor')
def worker(owner: str) -> str:
    s=owner.lower()
    if 'codex-ni' in s or s=='ni':return 'ni'
    if 'refactor' in s:return 'refactor'
    if 'codex3' in s or s=='sol':return 'codex3'
    return 'unknown'
def parse_time(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(dt.timezone.utc)
def read_json(path: Path) -> dict | None:
    try:
        obj=json.loads(path.read_text())
        return obj if isinstance(obj,dict) else None
    except (OSError,ValueError):return None

def filing_time(obj: dict | None,path: Path) -> dt.datetime | None:
    try:
        return parse_time(obj['filed_at']) if obj and obj.get('filed_at') else dt.datetime.fromtimestamp(path.stat().st_mtime,dt.timezone.utc)
    except (OSError,ValueError,KeyError):return None

def legacy_failed(text: str,obj: dict | None, ended_first: str) -> bool:
    outcome=str(obj.get('outcome','')) if obj else text.splitlines()[0] if text.splitlines() else ''
    if not re.search(r'(^|\s)FAILED-RUN(?:[/: \t]|$)',outcome[:320]):return False
    if 'owner-retired' in outcome or 'stop-file-before-start' in outcome:return False
    match=re.match(r'rc=(\d+)\b',ended_first)
    if not match or int(match.group(1)) in (0,75):return False
    # A receipt describing a prior attempt under a reused id is ambiguous.
    if obj and obj.get('original_end') and str(obj['original_end']).splitlines()[0] != ended_first:
        return False
    claimed=re.search(r'\brc=(\d+)\b',str(obj.get('original_end','')) if obj and obj.get('original_end') else outcome)
    if claimed and claimed.group(1)!=match.group(1):return False
    return True

def targets(flags: Path) -> dict[str,int]:
    data=read_json(flags/'science-quota.json') or {}
    if data.get('kind')!='epyc.science-quota.v1' or data.get('owner_approved') is not True:return {}
    raw=data.get('daily_verdict_targets')
    if not isinstance(raw,dict):return {}
    return {k:v for k,v in raw.items() if k in WORKERS and type(v) is int and v>=0}

def collect(flags: Path, now: dt.datetime) -> dict:
    owners={}
    rows={w:{'cpu':0,'gpu':0,'host':0,'wait_disk':0,'verdicts':0,'failed':0} for w in WORKERS}
    try:
        for line in (flags/'FILLERS.md').read_text().splitlines():
            cells=[v.strip() for v in line.strip().strip('|').split('|')]
            if len(cells)==18:
                w=worker(cells[1])
                if w!='unknown':owners[cells[0]]=w
    except OSError:pass
    for parent in (flags/'ready',flags/'ready/armed',flags/'ready/refused'):
        for path in parent.glob('*.json'):
            m=read_json(path)
            if not m:continue
            w=worker(str(m.get('owner','')))
            if w=='unknown':continue
            rid=str(m.get('id') or path.stem);owners[rid]=w
            if (parent!=flags/'ready' or m.get('schema')!='epyc.ready.v2' or m.get('production') is not True or
                m.get('hold') is not None or (flags/'grants'/(rid+'.complete')).exists() or
                (flags/'grants'/(rid+'.ended')).exists()):continue
            try: wait=q.disk_wait(path)
            except (OSError,ValueError,KeyError,q.Refused):wait=False
            if wait:
                rows[w]['wait_disk']+=1;continue
            try:q.verify(path,flags,True)
            except (q.Refused,OSError,ValueError,KeyError,subprocess.TimeoutExpired):continue
            r=str(m.get('regions',''))
            b='host' if r=='0-95' or r.count('q')>=4 else 'gpu' if 'mi210' in r else 'cpu'
            rows[w][b]+=1
    for path in (flags/'filing-done').glob('*.FILED'):
        rid=path.stem
        try:text=path.read_text()
        except OSError:continue
        obj=read_json(path)
        if obj and obj.get('id') not in (None,rid):continue
        w=owners.get(rid) or worker(str(obj.get('owner','')) if obj else '')
        if w=='unknown':continue
        filed=filing_time(obj,path)
        if filed is None or not dt.timedelta()<=now-filed<=dt.timedelta(hours=24):continue
        ended=flags/'grants'/(rid+'.ended')
        try:first=ended.read_text().splitlines()[0]
        except (OSError,IndexError):continue
        klass=obj.get('outcome_class') if obj else None
        if klass=='FAILED-RUN' or (klass is None and legacy_failed(text,obj,first)):
            rows[w]['failed']+=1;continue
        if klass not in ('SCIENCE-VERDICT','PARTIAL-VERDICT','DIAGNOSTIC-RESULT'):continue
        verdict=obj.get('verdict')
        if not (isinstance(verdict,dict) and verdict.get('status')=='filed' and verdict.get('kind') in ('science','diagnostic') and
                isinstance(verdict.get('native_result_sha256'),str) and re.fullmatch('[0-9a-f]{64}',verdict['native_result_sha256'])):continue
        native=Path(str(obj.get('native_result_path','')))
        try:
            if not native.is_absolute() or q.sha(native)!=verdict['native_result_sha256']:continue
        except (q.Refused,OSError):continue
        if first.startswith('rc=0 ') or first.startswith('rc=75 '):rows[w]['verdicts']+=1
    for record in rows.values():record['net_science']=record['verdicts']-record['failed']
    return rows

def render(rows: dict, now: dt.datetime, quota: dict[str,int]) -> str:
    lines=[f'# Science scoreboard {now:%Y-%m-%dT%H:%M:%SZ}','',
           'Structured FILED verdicts with retained native SHA and rc0/75 earn credit. Exact legacy FAILED-RUN filings joined to native ended records debit the owner. WAIT-DISK is parked, separate from runnable READY and science. Targets remain unset until owner-approved science-quota.json exists.','',
           '| worker | runnable READY cpu/gpu/host | parked WAIT-DISK | verdicts 24h | FAILED 24h | net science | approved daily target |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for w in WORKERS:
        r=rows[w];ready=f"{r['cpu']} / {r['gpu']} / {r['host']}"
        lines.append(f"| {w} | {ready} | {r['wait_disk']} | {r['verdicts']} | {r['failed']} | {r['net_science']} | {quota.get(w,'unset')} |")
    return '\n'.join(lines)+'\n'
def main()->int:
    p=argparse.ArgumentParser();p.add_argument('--flags',type=Path,default=Path('/mnt/raid0/llm/tmp/compute-flags'))
    p.add_argument('--output',type=Path);a=p.parse_args()
    now=dt.datetime.now(dt.timezone.utc);text=render(collect(a.flags,now),now,targets(a.flags))
    if a.output:a.output.write_text(text)
    else:print(text,end='')
    return 0
if __name__=='__main__':raise SystemExit(main())
