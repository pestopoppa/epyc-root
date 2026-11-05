#!/usr/bin/env python3
"""Exercise completion with synthetic artifacts and outer-only environment; no GPU."""
import hashlib,json,os,pathlib,runpy,shutil,sys,tempfile,types,unittest
D=pathlib.Path(__file__).resolve().parent
sha=lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
class CompletionOuter(unittest.TestCase):
 def run_case(self,change=None):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);shutil.copy(D/'complete.py',root/'complete.py');shutil.copy(D/'grant_evidence.py',root/'grant_evidence.py')
   (root/'BOUND.json').write_text('{}'); (root/'lib').mkdir(); hip=root/'lib/libggml-hip.so.0';hip.write_bytes(b'hip');h=sha(hip)
   job=types.ModuleType('job');job.SPEC={'id':'c6-b4-targeted-comparison-20261105'};job.BOUND={'n5_capture_path':'unused'};job.sha=sha;job.check_inputs=lambda:None;job.compare_pair=lambda *a:{'ok':True}
   job.CASES=[{'name':f'case{i}','tolerance_seed71':.01} for i in range(3)];job.CAPTURES=('candidate_weight.bin',)
   job.PINS={arm:{'binary_sha256':'binary','hip_library_sha256':h,'library_dir':str(root/'lib')} for arm in ('baseline','corrected')}
   rows=[]; run=root/'runs/run-1'
   for i,case in enumerate(job.CASES):
    for arm in (('baseline','corrected') if i<2 else ('corrected',)):
     out=run/'seed-071'/case['name']/arm;out.mkdir(parents=True)
     for f in ('stdout.log','stderr.log','candidate_weight.bin'):(out/f).write_text(f)
     rows.append({'case':case['name'],'arm':arm,'seed':71,'seed_index':7047 if i==2 else i,'binary_sha256':'binary','expected_mmvq_route_observed':True,'property':{'tolerance':.01,'passed':True},'native_rc':0,'stdout_sha256':sha(out/'stdout.log'),'stderr_sha256':sha(out/'stderr.log'),'capture_sha256':{'candidate_weight.bin':sha(out/'candidate_weight.bin')},'capture_metadata':{'valid':True},'residency':{'own_pid_kfd_reads':2,'own_pid_peak_vram_bytes':1},'hip_maps':{str(hip):h}})
   comparison={'input_bytes_equal':True};comp=types.ModuleType('compare_capture');comp.compare=lambda *a:comparison;comp.load=lambda *a:{'valid':True}
   raw='regions=mi210_0,184-191 start=2026-11-05T00:00Z end=2026-11-05T00:15Z holds=mi210_0\n'
   grant={'FILLER_ID':job.SPEC['id'],'FILLER_CPUS':'184-191','FILLER_NEEDGPU':'1','FILLER_DEADLINE':'1793837700','grant_text':raw,'grant_sha256':hashlib.sha256(raw.encode()).hexdigest()}
   if change:change(grant)
   result={'schema':'epyc.c6.corrected-comparison.v1','binding_sha256':sha(root/'BOUND.json'),'invocation_id':'outer-test','status':'COMPLETE_DIAGNOSTIC_ONLY','run_mode':'grant','cleanup':True,'completed_pairs':2,'records':rows,'pairs':[{'ok':True}]*2,'performance_claim':None,'promotion_claim':None,'full_gate_pass':None,'grant':grant,'run':str(run),'n5':rows[-1],'n5_comparison':comparison}
   (root/'RESULT.json').write_text(json.dumps(result))
   oldmods={k:sys.modules.get(k) for k in ('job','compare_capture','grant_evidence')};oldenv=dict(os.environ);oldpath=list(sys.path)
   try:
    sys.modules['job']=job;sys.modules['compare_capture']=comp;sys.modules.pop('grant_evidence',None);sys.path.insert(0,str(root))
    for key in ('FILLER_ID','FILLER_CPUS','FILLER_NEEDGPU','FILLER_DEADLINE','FILLER_DRYRUN'):os.environ.pop(key,None)
    os.environ['C6_INVOCATION_ID']='outer-test'
    try:runpy.run_path(str(root/'complete.py'),run_name='__main__');return 0
    except SystemExit as e:return e.code
   finally:
    os.environ.clear();os.environ.update(oldenv);sys.path[:]=oldpath
    for k,v in oldmods.items():
     if v is None:sys.modules.pop(k,None)
     else:sys.modules[k]=v
 def test_outer_without_inner_variables_accepts_valid_evidence(self): self.assertEqual(self.run_case(),0)
 def test_wrong_row_rejected(self): self.assertNotEqual(self.run_case(lambda g:g.update(FILLER_ID='another-row')),0)
 def test_tampered_grant_rejected(self): self.assertNotEqual(self.run_case(lambda g:g.update(grant_text=g['grant_text'].replace('mi210_0','cpu'))),0)
if __name__=='__main__':unittest.main()
