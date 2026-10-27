"""Model-free lifecycle fixture; identity checks are replaced only inside the test copy."""
import hashlib, os, pathlib, socket, subprocess, tempfile, textwrap, time
B=pathlib.Path('/mnt/raid0/llm/tmp/codex-ni-20261027-ufh14-lb51-template')
base=pathlib.Path(tempfile.mkdtemp(prefix='lifecycle-',dir=os.environ['TMPDIR']))
source=(B/'server_job.py').read_text()
for mode in ('success','server_failure','audit_failure','missing_verdict','stop'):
 d=base/mode; d.mkdir(); k=d/'kernel'; k.mkdir(); model=d/'model'; model.write_bytes(b'fixture')
 (d/'verdict_check.py').write_text((B/'verdict_check.py').read_text())
 (d/'SOURCE.SHA256SUMS').write_text('fixture manifest\n')
 (d/'verify_ggml_linkage.sh').write_text('#!/bin/bash\nexit 0\n')
 s=socket.socket();s.bind(('127.0.0.1',0));port=s.getsockname()[1];s.close()
 fake=("#!/usr/bin/python3\nimport http.server\nclass H(http.server.BaseHTTPRequestHandler):\n def do_GET(self):\n  self.send_response(200);self.end_headers()\n def log_message(self,*args): pass\nhttp.server.HTTPServer(('127.0.0.1',%d),H).serve_forever()\n"%port)
 (k/'llama-server').write_text('#!/bin/sh\nexit 3\n' if mode=='server_failure' else fake); (k/'llama-server').chmod(0o755)
 audit=("import json,sys\nopen(sys.argv[3],'w').write(json.dumps({'verdict':{'P1':True,'P2':True,'P3':True}}))\n")
 if mode=='audit_failure': audit='raise SystemExit(1)\n'
 if mode=='missing_verdict': audit="import sys\nopen(sys.argv[3],'w').write('{}')\n"
 if mode=='stop': audit=f"from pathlib import Path\nimport time\nPath({str(d/'STOP')!r}).touch()\ntime.sleep(30)\n"
 (d/'live_audit.py').write_text(audit)
 script=source.replace("B=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-ufh14-lb51-template')",f'B=Path({str(d)!r})').replace("K=Path('/mnt/raid0/llm/kernels/production/cpu').resolve(strict=True)",f'K=Path({str(k)!r})').replace("MODEL=Path('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf')",f'MODEL=Path({str(model)!r})').replace('a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348',hashlib.sha256(b'fixture').hexdigest()).replace('18994',str(port)).replace('list(range(24,48))','[48,49]')
 # Mocked server has Python's mappings, so retain the lifecycle while explicitly
 # excluding native ELF/model identity gates, independently source-reviewed.
 start=script.index("  maps=Path(f'/proc/{p.pid}/maps')")
 end=script.index("  with (B/'audit.log')",start)
 script=script[:start]+f"  mapped=set(); sealed={{str((K/'llama-server').resolve()):'mock'}}\n"+script[end:]
 testjob=d/'testjob.py';testjob.write_text(script)
 env={**os.environ,'FILLER_DEADLINE':str(int(time.time())+45),'FILLER_STOPFILE':str(d/'STOP')}
 with (d/'run.log').open('wb') as log:
  r=subprocess.run(['/usr/bin/python3','-B',str(B/'resource-watch.py'),'/usr/bin/python3','-B',str(testjob)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=50)
 assert (r.returncode==0)==(mode=='success'),(mode,r.returncode,(d/'run.log').read_text())
 assert (d/'CANDIDATE.json').exists()==(mode=='success'),mode
 if (d/'server-identity.json').exists():
  import json
  pid=json.loads((d/'server-identity.json').read_text())['pid']
  assert not pathlib.Path(f'/proc/{pid}').exists(),(mode,pid)
 print(mode,'PASS rc',r.returncode)
print('FAKE_LIFECYCLE_PASS',base)
