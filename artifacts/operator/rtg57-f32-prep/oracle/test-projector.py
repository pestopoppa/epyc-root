import importlib.util,pathlib,shutil,tempfile
D=pathlib.Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('p',D/'projector.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
with tempfile.TemporaryDirectory(dir=D) as t:
 out=pathlib.Path(t)/'out';shutil.copytree(D/'out',out)
 v=m.project(out/'native-receipt.json');assert v['grade'][:2]==('Judged','Located') and v['reps']==1 and not v['protocol_id']
 with (out/'positive.log').open('a') as f:f.write('tamper\n')
 try:m.project(out/'native-receipt.json')
 except ValueError:pass
 else:raise AssertionError('tampered original evidence accepted')
print('original receipt projection and evidence-tamper refusal PASS; no new measurement')
