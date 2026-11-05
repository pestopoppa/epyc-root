import hashlib,json,os,pathlib,sys
D=pathlib.Path(__file__).resolve().parent
ROW='kpf131-typed-decoder-qual-20261105'
try:
 mode='smoke' if os.environ.get('FILLER_SMOKE')=='1' else 'full'
 path=pathlib.Path(os.environ.get('FILLER_DRYRUN_RESULT_PATH',str(D/'out'/'RESULT.json')))
 r=json.loads(path.read_text());cases=json.loads((D/'inputs.json').read_text())
 assert r['row_id']==ROW and r['invocation']==os.environ['KPF131_INVOCATION']
 assert r['status']=='SYNTHETIC_CONTROLS_PASS' and r['mode']==mode
 assert r['cleanup_verified'] is True and r['child_exit']==0
 assert r['native_binding']=='UNKNOWN' and r['historical_control']=='UNKNOWN'
 assert len(r['records'])==len(cases)==8
 for actual,case in zip(r['records'],cases):
  result=actual['result']
  assert actual['case']==case['case'] and actual['passed'] is True
  assert result['status']==case['expected_status']
  assert result['native_binding']=='UNKNOWN' and result['historical_control']=='UNKNOWN'
  if case['expected_structural'] is not None:assert result['structural_status']==case['expected_structural']
  if 'expected_reason' in case:assert result['reason']==case['expected_reason']
 root=pathlib.Path(r['output']).resolve()
 assert root.parent==(D/'out'/mode).resolve()
 assert json.loads((root/'RESULT.json').read_text())==r
 before=json.loads((root/'before.json').read_text());after=json.loads((root/'after.json').read_text())
 assert before['pid']==r['child_pid'] and before['birth']==r['child_birth']
 for snap in [before,after]:
  assert snap['file_backed_maps']==[l for l in snap['maps'].splitlines() if len(l.split(None,5))==6 and l.split(None,5)[5].startswith('/')]
 assert {k:v for k,v in before.items() if k!='maps'}=={k:v for k,v in after.items() if k!='maps'}
 for name,h in r['raw_sha256'].items():
  assert pathlib.Path(name).name==name and hashlib.sha256((root/name).read_bytes()).hexdigest()==h
 assert r['input_sha256']==hashlib.sha256((D/'inputs.json').read_bytes()).hexdigest()
 for manifest in ['SHA256SUMS','RUNTIME.sha256']:
  for line in (D/manifest).read_text().splitlines():
   h,name=line.split('  ',1);f=pathlib.Path(name)
   if not f.is_absolute():f=D/f
   assert hashlib.sha256(f.read_bytes()).hexdigest()==h
except (OSError,ValueError,KeyError,AssertionError,TypeError):sys.exit(1)
sys.exit(0)
