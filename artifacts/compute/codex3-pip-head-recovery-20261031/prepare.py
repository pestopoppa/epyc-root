import json,hashlib,datetime,os,importlib.util
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent;H=Path('/mnt/micron/codex3-pip-relocatable-r25-20261030');BASE=Path('/mnt/raid0/llm/tmp/pip02-pipeline-prep-20261029');V=Path('/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
audit=P/'ORIGIN-AUDIT.json';orig=json.loads(audit.read_bytes());assert all(r['verified'] and not r['original_finish_present'] for r in orig['rows']);inputs={}
for row in orig['rows']:inputs.update(row['image_layout_page_and_regions_sha256'])
paths=[D/'assemble.py',D/'prepare.py',P/'audit.py',audit,Path('/mnt/raid0/llm/tmp/codex3-pip-pool2-r30-v2-20261031/HEAD-0-34-AUDIT.json'),V/'venv-files.json',V/'PADDLE-FRESH-SOURCES.sha256',H/'venv-files-r9.json',H/'venv-dirs-r9.json',BASE/'venv_witness.py',BASE/'opencv-overlay-v1-hashes.json',BASE/'opencv-headless-v1-hashes.json',Path('/mnt/raid0/llm/tmp/inf51-streamingllm-full-20261029/bounded_writer.py'),Path('/home/daniele/.local/share/uv/python/cpython-3.12-linux-x86_64-gnu/bin/python3.12')]
for p in paths:inputs[str(p)]=sha(p)
assert inputs[str(V/'venv-files.json')]=='e2b651b64c3449973ee83084bb94f21d59142bbb3dcc1ba771b643d82c03784d';assert inputs[str(H/'venv-files-r9.json')]=='254e35f1edf3fcc3a880825e6f05874a9174c71f78d67ff6eb4c0d536afb4588';assert inputs[str(H/'venv-dirs-r9.json')]=='7d4ce147150cdb7b32e9548c4857ddb68f8c995e75dd6136a346cc657063ff1e';assert inputs[str(paths[-1])]=='0a97d28d3635c7dfd143de6d00b09c0cb382249c020b28ee33fb4002db1efb9c'
for f in ('opencv-overlay-v1-hashes.json','opencv-headless-v1-hashes.json'):
 for name,digest in json.loads((BASE/f).read_bytes()).items():
  if name in inputs:assert inputs[name]==digest
  inputs[name]=digest
for name,digest in inputs.items():assert sha(name)==digest,name
for row in orig['rows']:
 starts=[Path(f['path']) for f in json.loads(Path('/mnt/raid0/llm/tmp/codex3-pip-pool2-r30-v2-20261031/HEAD-0-34-AUDIT.json').read_bytes())['rows'][0 if row['index']==0 else 1]['files'] if f['path'].endswith('.start')]
 assert len(starts)==1 and not starts[0].with_name(starts[0].name[:-len('.start')]+'.finish.json').exists()
start={'schema':'pip02-offline-assembly-recovery-start/v1','id':'pip02-head-offline-assembly-20261031-r1','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'indices':[0,34],'scope':'prospective deterministic native assembly of authenticated saved layouts and cached responses; no network or new model requests','script_path':str(D/'assemble.py'),'script_sha256':sha(D/'assemble.py'),'writer_path':'/mnt/raid0/llm/tmp/inf51-streamingllm-full-20261029/bounded_writer.py','source_venv_policy':'original file hashes plus r9 inventory; only additional files may be pycache, which this process does not read','original_missing_finish_preserved':True,'inputs_sha256':inputs}
spec=importlib.util.spec_from_file_location('native_writer',start['writer_path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);w=m.Writer(D/'output',8*1024*1024)
try:w.create('RECOVERY-START.json',(json.dumps(start,sort_keys=True,separators=(',',':'))+'\n').encode())
finally:w.close()
print('prospective start created before assembly, hashes',len(inputs))
