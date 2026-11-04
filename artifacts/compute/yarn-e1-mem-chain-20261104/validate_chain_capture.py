#!/usr/bin/env python3
"""Model-free structure checks for YARN-E1-MEM-CHAIN native receipts."""
EXPECTED=('128k','240k','400k','500k')
def validate(report,calls,attribution,samples,expected=EXPECTED):
    issues=[]
    needle=report.get('needle') or {}
    for stage in expected:
        row=needle.get(stage)
        if not isinstance(row,dict) or row.get('aborted'):
            issues.append(f'{stage}: report missing or aborted')
        elif row.get('n') != 5:
            issues.append(f'{stage}: expected five needle records, got {row.get("n")}')
        sr=[x for x in calls if x.get('stage')==stage and x.get('kind')=='needle']
        if len(sr)!=5 or any(not x.get('http_ok') for x in sr):
            issues.append(f'{stage}: expected five successful native needle calls')
        local=[x for x in calls if x.get('stage')==stage and x.get('kind')=='local']
        if len(local)!=1 or any(not x.get('http_ok') for x in local):
            issues.append(f'{stage}: expected one successful local probe call')
        a=(attribution.get('stages') or {}).get(stage) or {}
        if a.get('own_kfd_peak_gib') is None:
            issues.append(f'{stage}: missing own-PID KFD sample in stage window')
    good=[x for x in samples if x.get('pid_vram_gib') is not None]
    if not good: issues.append('no own-PID KFD samples')
    return issues
