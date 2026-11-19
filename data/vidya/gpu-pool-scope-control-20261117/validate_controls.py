import json,os,sys,time,unittest
from pathlib import Path
p=Path(__file__).resolve().parent
os.environ.update(GPU_POOL_CONTROL_RESEARCH=str(p/'research'),TMPDIR=str(p/'validation-scratch'),EPYC_BUS_ROOT=str(p/'validation-scratch/bus'),ALARM_BACKEND='file')
Path(os.environ['TMPDIR']).mkdir(exist_ok=True)
sys.path.insert(0,str(p/'root/tests/vidya'))
from test_gpu_pool_scope_control import ScopeControls
with (p/'validation.log').open('w') as log:
 r=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ScopeControls))
receipt={'synthetic_control':True,'official_native_acceptance':False,'positive_planning_context':False,'reader_checkout_check':False,'tests_run':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped),'status':'passed' if r.wasSuccessful() and r.testsRun==6 and not r.skipped else 'failed','cpu_affinity':sorted(os.sched_getaffinity(0))}
(p/'validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
raise SystemExit(0 if receipt['status']=='passed' else 1)
