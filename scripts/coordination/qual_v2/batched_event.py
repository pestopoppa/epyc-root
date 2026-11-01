#!/usr/bin/env python3
"""Qualification branch for the normal job entry; native binary, not a simulator."""
import hashlib, json, os, pathlib, signal, subprocess, time, uuid
from batched_qual import expected_argv, first_ok, live_ok, native_row_ok, sha


def put(path, obj):
    path = pathlib.Path(path); tmp = path.with_name('.' + path.name + uuid.uuid4().hex)
    with tmp.open('x') as f:
        json.dump(obj, f, sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.link(tmp, path); tmp.unlink()


def main():
    m = json.loads(pathlib.Path(os.environ['WS58_MANIFEST_PATH']).read_text())
    b = m['llm']['batched']; phase = os.environ['FILLER_QUAL_PHASE']
    if phase not in ('normal','cutoff'): raise RuntimeError('bad phase')
    output = pathlib.Path(os.environ['FILLER_RESULTS_DIR']) / ('batched-' + phase + '-' + uuid.uuid4().hex)
    output.mkdir(parents=True)
    for key in ('binary','model','hip_library'):
        if sha(b[key]['path']) != b[key]['sha256']: raise RuntimeError('pin mismatch: ' + key)
    log = output / 'native.jsonl'; err = output / 'native.stderr'; proc = None
    env = dict(os.environ, LD_LIBRARY_PATH=str(pathlib.Path(b['binary']['path']).parent) + ':/opt/rocm/lib', OMP_NUM_THREADS='1')
    with log.open('xb') as stdout, err.open('xb') as stderr:
        proc = subprocess.Popen(expected_argv(b), stdout=stdout, stderr=stderr, env=env)
        try:
            birth = int(pathlib.Path(f'/proc/{proc.pid}/stat').read_text().rsplit(') ',1)[1].split()[19])
            deadline = min(float(os.environ['FILLER_DEADLINE']), time.time()+240)
            line = b''
            while time.time() < deadline and proc.poll() is None:
                with log.open('rb') as f: line = f.readline()
                if line.endswith(b'\n'):
                    try: row=json.loads(line)
                    except ValueError: time.sleep(.05); continue
                    first={'ok':True,'scope':'TARGET_NATIVE_BATCHED_BENCH',
                           'manifest_sha256':m['request_manifest_sha256'], 'production_recipe_sha256':m['production_recipe']['sha256'],
                           'work_unit':m['rate_basis'].get('work_unit'), 'measured_tok_s':row['speed_tg'], 'argv':expected_argv(b),
                           'binary_sha256':b['binary']['sha256'],'model_sha256':b['model']['sha256'],
                           'source_commit':b['source_commit'],'native_pid':proc.pid,'native_birth_ticks':birth,
                           'native_pgid':os.getpgid(proc.pid),'native_uid':os.getuid(),
                           'observed_cpus':sorted(os.sched_getaffinity(proc.pid)),
                           'native_jsonl':str(log),'native_line_sha256':hashlib.sha256(line).hexdigest(),'native_row':row}
                    if not first_ok(m,first) or not native_row_ok(first,output) or not live_ok(m,first):
                        raise RuntimeError('first row/live native validation failed')
                    break
                time.sleep(.05)
            else: raise RuntimeError('no flushed native row while child live')
            proof={'id':m['id'],'phase':phase,'nonce':os.environ['WS58_QUAL_NONCE'],'first_request':first,
                   'observed_cpus':sorted(os.sched_getaffinity(0)),'disk':{'job_floor_gib':150}}
            if phase == 'cutoff':
                put(os.environ['WS58_QUAL_CUTOFF_EVENT'],{'id':m['id'],'nonce':proof['nonce'],'phase':phase,
                    'native_first_event':True,'native_pid':proc.pid,'native_birth_ticks':birth,'first_request':first})
                stop=pathlib.Path(os.environ['FILLER_STOPFILE'])
                while not stop.exists() and time.time()<deadline and proc.poll() is None: time.sleep(.02)
                if not stop.exists() or proc.poll() is not None: raise RuntimeError('STOP did not reach live native child')
                proc.terminate()
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=5)
                proof.update(partial=True,stop_observed=True,deadline_reached=False,unknown_disposition='UNKNOWN')
                put(os.environ['WS58_QUAL_PROOF'],proof)
                return 75
            if proc.wait(timeout=max(1,deadline-time.time())) != 0: raise RuntimeError('native exit nonzero')
            rows=[json.loads(x) for x in log.read_text().splitlines() if x.startswith('{')]
            if len(rows)!=2 or any(not first_ok(m, dict(first, native_row=r)) for r in rows):
                raise RuntimeError('native second cell missing')
            result=output/'RESULT.json';put(result,{'complete':True,'native_jsonl':str(log),'rows':rows})
            proof['result_writer']={'ok':True,'result_path':str(result),'sha256':sha(result)}
            put(os.environ['WS58_QUAL_PROOF'],proof);return 0
        finally:
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
if __name__=='__main__': raise SystemExit(main())
