#!/usr/bin/env python3
"""Write original one-extra capture; do not invent a six-pass grading rule."""
import hashlib,json,pathlib,datetime,os
G=pathlib.Path(__file__).resolve().parent;O=G/os.environ.get('GPU_GATE_OUTPUT','out');S=pathlib.Path('/mnt/raid0/llm/tmp/codex-ni-zos23-concurrent-successor-20261031/out')
for line in (G/'RETAINED-SHA256SUMS').read_text().splitlines():
 h,p=line.split('  ',1);assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h,p
original=json.loads((S/'RESULT.json').read_text());assert original['threshold_band']=='UNDERPOWERED' and original['reason']=='one A3/B3 extension allowed'
records={}
for arm in ('A1','B1','A2','B2','A3','B3'):
 root=O if arm in ('A3','B3') else S
 assert (root/arm/'COMPLETE.json').exists()
 waves=[json.loads(x) for x in (root/arm/'waves.jsonl').read_text().splitlines()]
 rows=[r for w in waves if w['wave']>0 for r in w['responses']];assert len(rows)==(4 if arm in ('A3','B3') and os.environ.get('GPU_GATE_QUALIFY')=='1' else 24)
 assert all(len(r['tokens'])==(256 if arm in ('A3','B3') and os.environ.get('GPU_GATE_QUALIFY')=='1' else 1024) and r['timings']['predicted_per_second']>0 for r in rows)
 records[arm]={'waves_path':str(root/arm/'waves.jsonl'),'sha256':hashlib.sha256((root/arm/'waves.jsonl').read_bytes()).hexdigest(),'responses':rows}
r={'schema':'ni.gpu_zos23_one_extra_capture.v1','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'partial':False,'capture_complete':os.environ.get('GPU_GATE_QUALIFY')!='1','qualification_only':os.environ.get('GPU_GATE_QUALIFY')=='1','arms':records,'original_result':original,'original_rule':'Append A3 and B3 and recompute S and NF over all 6 passes with the same rule. If still underpowered, result is INCONCLUSIVE.','ship_authorized':False,'original_parent_complete':False,'verdict':'QUALIFICATION_ONLY' if os.environ.get('GPU_GATE_QUALIFY')=='1' else 'ATOMIC_DIAGNOSTIC_EXTENSION_CAPTURED','analysis_scope':'Native six-pass records retained. No new six-pass NF or alternation semantics introduced; original predeclared analysis remains authoritative.'}
t=O/'RESULT.json.tmp';t.write_text(json.dumps(r,indent=2)+'\n');t.replace(O/'RESULT.json');print(r['verdict'])
