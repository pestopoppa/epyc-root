#!/usr/bin/env python3
"""Revalidate retained evidence; never execute GPU workloads."""
import json,os,pathlib,sys
import job
from compare_capture import compare,load
from grant_evidence import validate as validate_grant
D=pathlib.Path(__file__).resolve().parent
try:
 dry=os.environ.get('FILLER_DRYRUN')=='1'
 p=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if dry else D/'RESULT.json'
 r=json.loads(p.read_text());job.check_inputs()
 assert r['schema']=='epyc.c6.corrected-comparison.v1' and r['binding_sha256']==job.sha(D/'BOUND.json')
 assert r['invocation_id']==os.environ['C6_INVOCATION_ID']
 if dry: assert p.resolve()!=(D/'RESULT.json').resolve()
 if True:
  assert r['status']=='COMPLETE_DIAGNOSTIC_ONLY' and r['run_mode']==('dryrun' if dry else 'grant') and r['cleanup'] is True and r['completed_pairs']==2
  assert len(r['records'])==5 and len(r['pairs'])==2 and all(r[x] is None for x in ('performance_claim','promotion_claim','full_gate_pass'))
  validate_grant(r['grant'],job.SPEC['id'],dry)
  root=pathlib.Path(r['run']).resolve();assert root.is_relative_to((D/('smoke-runs' if dry else 'runs')).resolve())
  for ci,case in enumerate(job.CASES):
   rows=[x for x in r['records'] if x['case']==case['name']]
   assert {x['arm'] for x in rows}==({'baseline','corrected'} if ci<2 else {'corrected'}) and len(rows)==(2 if ci<2 else 1)
   byarm={x['arm']:x for x in rows}
   if ci<2: assert job.compare_pair(root,71,ci,byarm)==r['pairs'][ci]
   for arm,row in byarm.items():
    out=root/'seed-071'/case['name']/arm
    assert row['seed']==71 and row['binary_sha256']==job.PINS[arm]['binary_sha256'] and row['expected_mmvq_route_observed']
    assert row['property']['tolerance']==case['tolerance_seed71'] and row['native_rc'] in (0,1) and (row['native_rc']==0)==row['property']['passed']
    assert row['stdout_sha256']==job.sha(out/'stdout.log') and row['stderr_sha256']==job.sha(out/'stderr.log')
    assert row['capture_sha256']=={n:job.sha(out/n) for n in job.CAPTURES} and row['capture_metadata']==load(out)
    assert row['residency']['own_pid_kfd_reads']>=2 and row['residency']['own_pid_peak_vram_bytes']>0
    assert row['hip_maps'] and any(pathlib.Path(q).name.startswith('libggml-hip.so') and h==job.PINS[arm]['hip_library_sha256'] for q,h in row['hip_maps'].items())
    assert all(pathlib.Path(q).resolve().is_relative_to(pathlib.Path(job.PINS[arm]['library_dir']).resolve()) and job.sha(q)==h for q,h in row['hip_maps'].items())
  n5=r['records'][-1];assert n5==r['n5'] and n5['seed_index']==7047
  assert compare(job.BOUND['n5_capture_path'],root/'seed-071'/job.CASES[2]['name']/'corrected')==r['n5_comparison'] and r['n5_comparison']['input_bytes_equal']
except Exception as e:
 print('INCOMPLETE:',repr(e),file=sys.stderr);sys.exit(1)
