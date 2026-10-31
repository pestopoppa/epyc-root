#!/usr/bin/env python3
"""Strict read-only R13 full microbench completion predicate; no keep grade."""
import hashlib
import json
import re
from pathlib import Path

HERE=Path(__file__).resolve().parent
ID='refactor-c6-35186-q4-two-cohort-cpu-r2-20261031'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def refuse(s): raise SystemExit('REFUSED '+s)
pointer=HERE/'LATEST-RUN'
if not pointer.is_file(): refuse('no run pointer')
out=Path(pointer.read_text().strip())
if out.parent!=HERE/'runs' or not out.is_dir(): refuse('run pointer outside owned runs')
prepath=out/'PRE-RUN.json'; resultpath=out/'RESULT.json'; seal=out/'SHA256SUMS.txt'
if not prepath.is_file() or not resultpath.is_file() or not seal.is_file(): refuse('incomplete run artifacts')
pre=json.loads(prepath.read_text()); result=json.loads(resultpath.read_text())
if pre.get('mode')!='--full' or pre.get('filler_id')!=ID or not pre.get('grant_sha256') or not pre.get('grant_text'):
    refuse('missing full calendar pre-run warrant')
outer_log=Path('/mnt/raid0/llm/tmp/compute-flags/ready/refactor-c6-35186-q4-two-cohort-cpu-r2-20261031.launcher.out')
if not outer_log.is_file(): refuse('outer launcher log absent')
outer_text=outer_log.read_text(errors='replace')
end_match=re.search(r'\bend=([^\s]+)',pre['grant_text'])
if (not end_match or 'end='+end_match.group(1) not in outer_text or
        'RESOURCE_PASS id='+ID not in outer_text or 'job rc=0' not in outer_text):
    refuse('outer launcher log lacks matching grant/resource/native exit proof')
if not isinstance(pre.get('affinity'),list) or len(pre['affinity'])<2 or not str(pre.get('env',{}).get('AUTOKERNEL_CPU_N_THREADS','')).isdigit():
    refuse('affinity/thread identity absent')
images=pre.get('images',{})
if (images.get('candidate',{}).get('source')!='729599d69871181d67af715a4c2f9162d5153a2e' or
        images.get('control',{}).get('source')!='3dbca8f4f407e21f11a2d04dcb6529ef40af9e62'):
    refuse('image identity mismatch')
if pre.get('instruments',{}).get('q4_wrapper_sha256')!=sha(HERE/'launch-q4.sh') or pre['instruments'].get('ds41_wrapper_sha256')!=sha(HERE/'ds41/launch_ds41.py'):
    refuse('instrument changed after pre-run')
if result.get('schema')!='c6.35186.q4_two_cohort_component_result.v1' or result.get('status')!='COMPLETE_MICROBENCH_ONLY' or result.get('no_keep_or_serving_grade') is not True or result.get('pre_run_sha256')!=sha(prepath):
    refuse('result schema/identity')
items=result.get('results')
if not isinstance(items,list) or len(items)!=4: refuse('four cohort/image results required')
expected=[('27b','candidate',9),('27b','control',9),('ds41','candidate',2),('ds41','control',2)]
for item,(cohort,image,count) in zip(items,expected):
    if item.get('cohort')!=cohort or item.get('image')!=image: refuse('cohort order/identity')
    sub=out/(cohort+'-'+image)
    rp=sub/('result-summary.json' if cohort=='27b' else 'RESULT.json')
    sp=sub/'SHA256SUMS.txt'
    if not rp.is_file() or not sp.is_file() or item.get('result_sha256')!=sha(rp) or item.get('component_seal_sha256')!=sha(sp):
        refuse('component result/seal mismatch')
    data=json.loads(rp.read_text())
    actual=data.get('case_count') if cohort=='27b' else len(data.get('results',[]))
    if actual!=count: refuse('case count mismatch')
    for line in sp.read_text().splitlines():
        digest,rel=line.split(None,1)
        p=sub/rel.strip()
        if not p.is_file() or sha(p)!=digest: refuse('component raw changed')
for line in seal.read_text().splitlines():
    digest,rel=line.split(None,1);p=out/rel.strip()
    if not p.is_file() or sha(p)!=digest: refuse('top-level raw changed')
print(json.dumps({'status':'COMPLETE_MICROBENCH_ONLY','run':str(out),'pre_run_sha256':sha(prepath),
                  'result_sha256':sha(resultpath),'case_counts':[9,9,2,2],
                  'purpose':'diagnostic component timing, no keep/serving grade'},sort_keys=True))
