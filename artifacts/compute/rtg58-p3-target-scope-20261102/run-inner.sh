#!/bin/bash
set -euo pipefail
job=/mnt/raid0/llm/tmp/kv-prefix-fork/rtg58-p3-target-scope-smoke-20261102
build_job=/mnt/raid0/llm/tmp/kv-prefix-fork/rtg58-p3-target-scope-cpu-20261102
build=/mnt/micron/rtg58-p3-target-scope-cpu-20261102
packet=/mnt/raid0/llm/tmp/kv-prefix-fork/rtg58-p3-phase-trial-20261102
belief=/mnt/raid0/llm/tmp/kv-prefix-fork/rtg58-p3-belief-20261102
trap 'rc=$?; printf "%s\n" "$rc" > "$job/EXIT_CODE"; touch "$job/FINISHED"' EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
[[ -f "$build_job/FINISHED" && $(cat "$build_job/EXIT_CODE") = 0 ]]
(cd "$build/bin"; sha256sum -c "$build_job/BINARIES.sha256")
LD_LIBRARY_PATH="$build/bin" bash /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$build/bin/llama-server" "$build/bin" > "$job/linkage.txt"
PYTHONPATH="$packet/runner:$belief/scripts/vidya" python3 - "$job" "$build" <<'PY'
import hashlib,json,os,pathlib,signal,socket,subprocess,sys,time,urllib.error,urllib.request
from kpf30_phase_capture import parse_log,write_phase_capture
from adapters.kv_prefix_fork import project
from claim_tuple import grade
job=pathlib.Path(sys.argv[1]); build=pathlib.Path(sys.argv[2]); binary=build/'bin/llama-server'; model='/mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf'
argv=['taskset','-c','80-81',str(binary),'-m',model,'-md',model,'--spec-type','draft-simple','--spec-draft-n-max','4','-ngld','0','--device-draft','none','--host','127.0.0.1','--port','19879','-c','512','-np','1','-b','128','-ub','128','-t','2','-tb','2','--no-mmap','--device','none','--kv-unified','-lv','4','--no-warmup']
req={'prompt':'The scientific method begins with','n_predict':24,'temperature':0,'cache_prompt':False}
request=job/'request.json'; request.write_text(json.dumps(req,sort_keys=True)); sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
for scope in (False,True):
    label='target-only' if scope else 'unscoped-control'; env=dict(os.environ,LD_LIBRARY_PATH=str(build/'bin'),LLAMA_KPF30_MIXED_BLOCKS='1'); env['LLAMA_KPF30_TARGET_ONLY']='1' if scope else '0'
    log=job/(label+'.log'); start=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()); actual_argv=None; proc=None
    with log.open('wb') as f:
      try:
        proc=subprocess.Popen(argv,env=env,stdout=f,stderr=subprocess.STDOUT)
        for _ in range(120):
          if proc.poll() is not None: raise RuntimeError(f'{label} server exited {proc.returncode}')
          try:
            with urllib.request.urlopen('http://127.0.0.1:19879/health',timeout=2) as response:
              if response.status==200: break
          except (OSError,urllib.error.URLError): pass
          time.sleep(.5)
        else: raise RuntimeError(f'{label} server not ready')
        actual_argv=[v for v in pathlib.Path('/proc',str(proc.pid),'cmdline').read_bytes().decode().split('\0') if v]
        http=urllib.request.Request('http://127.0.0.1:19879/completion',request.read_bytes(),{'Content-Type':'application/json'})
        with urllib.request.urlopen(http,timeout=180) as response:
          body=response.read(); assert response.status==200
        (job/(label+'-response.json')).write_bytes(body)
      finally:
        if proc is not None and proc.poll() is None:
          proc.terminate()
          try: proc.wait(timeout=30)
          except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=30)
    if not scope:
      try:
        with log.open() as f: parse_log(f)
      except ValueError as e:
        assert 'unbracketed mask row after observation start' in str(e),str(e)
        print('PASS: unscoped draft rows cause refusal')
      else: raise AssertionError('unscoped control failed to exercise draft rows')
    else:
      with log.open() as f: rows,prestart=parse_log(f)
      assert any(x['phase']=='verify' for x in rows), 'no actual verify rows'
      meta=dict(run_id='rtg58-p3-scope-smoke',window_id='rtg58-p3-scope-smoke',host=socket.gethostname(),binary_sha256=sha(binary),prompt_set_sha256=sha(request),start_utc=start,category='CANDIDATE',argv=actual_argv,fan_completed=True,process_reaped=proc.poll() is not None,server_returncode=proc.returncode)
      records=write_phase_capture(log,job/'phase-capture',meta)
      claims=[project({'row':x,'sidecar_path':str(job/'phase-capture/belief_measurements.jsonl')}) for x in records]
      assert any(c.extra['phase']=='verify' and c.attestation_verified for c in claims)
      print('PASS: target-only draft-simple verify rows:',sum(x['phase']=='verify' for x in rows),'prestart:',prestart,'grade:',grade(claims[0])[0])
PY
