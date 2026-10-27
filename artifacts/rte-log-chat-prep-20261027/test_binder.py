import json, os, subprocess, sys, tempfile
from pathlib import Path
D=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as t:
 p=Path(t); tree=p/'source'; names=('src/backends/prompt_layout.py','src/backends/serving_calls.py','src/backends/dispatch_log.py','src/api/routes/openai_compat.py','src/prompt_builders/builder.py','scripts/analysis/prompt_layout_live_check.py','scripts/analysis/prompt_layout_reader.py')
 for n in names:
  f=tree/n; f.parent.mkdir(parents=True,exist_ok=True); f.write_text(n)
 model=p/'model'; model.write_text('fixture'); evidence=p/'budget'; evidence.write_text('fixture only')
 x={'api_workers':[os.getpid()],'backend_pid':os.getpid(),'resident_processes':[os.getpid()],'model_paths':[str(model)],'future_kv_state_gib':1,'reservation_gib':2,'budget_evidence':str(evidence),'source_commit':'fixture','source_tree':str(tree),'backend_port':8070}
 input=p/'input.json'; output=p/'binding.json'; input.write_text(json.dumps(x))
 run=lambda: subprocess.run([sys.executable,str(D/'bind.py'),'--input',str(input),'--output',str(output)],capture_output=True,text=True)
 assert run().returncode==0
 b=json.loads(output.read_text()); assert b['births'][str(os.getpid())] and len(b['source_files'])==7 and b['models'][0]['size']==7
 output.unlink(); x['resident_processes']=[]; input.write_text(json.dumps(x)); assert run().returncode!=0 and not output.exists()
 x['resident_processes']=[os.getpid()]; x['budget_evidence']=str(p/'missing'); input.write_text(json.dumps(x)); assert run().returncode!=0 and not output.exists()
 x['budget_evidence']=str(evidence)
 for value in (True,float('nan'),float('inf')):
  x['reservation_gib']=value; input.write_text(json.dumps(x)); assert run().returncode!=0 and not output.exists()
print('binder fixture PASS (synthetic only)')
