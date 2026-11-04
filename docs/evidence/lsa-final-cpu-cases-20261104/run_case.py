#!/usr/bin/env python3
"""Run one owned graph-test PID; HIP requires in-window KFD/VRAM witness."""
import hashlib, json, os, pathlib, signal, subprocess, sys, time
D = pathlib.Path(__file__).resolve().parent
backend, case, binary, out = sys.argv[1:]
out = pathlib.Path(out)
out.mkdir(exist_ok=False)
env = os.environ.copy()
ready, release, timeline = (out / x for x in ('ready', 'release', 'timeline.txt'))
graph_ready, graph_release = (out / x for x in ('graph-ready', 'graph-release'))
env.update(LSA_GRAPH_WITNESS_READY=str(graph_ready), LSA_GRAPH_WITNESS_RELEASE=str(graph_release))
env.update(LSA_HIP_WITNESS_READY=str(ready), LSA_HIP_WITNESS_RELEASE=str(release), LSA_HIP_TIMELINE=str(timeline))
cmd = [binary, '--backend', backend, '--case', case, '--fixture', str(D/'cases.json')]
# Complete file and signal setup before owning a child process.
log = (out/'unit.log').open('x')
sample_log = (out/'residency-samples.jsonl').open('x', buffering=1)
interrupted = False
def on_signal(signum, frame):
    global interrupted
    interrupted = True
signal.signal(signal.SIGTERM, on_signal)
signal.signal(signal.SIGINT, on_signal)
start = time.monotonic(); samples=[]; maps={}; failure=None
child = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, text=True, start_new_session=True)
def capture_maps():
    for line in (pathlib.Path('/proc')/str(child.pid)/'maps').read_text().splitlines():
        name=line.split()[-1]; p=pathlib.Path(name)
        if name.startswith('/') and ('ggml' in name or 'libllama' in name or 'hip' in name or 'hsa' in name) and p.is_file():
            maps[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()
try:
    while child.poll() is None:
        now=time.monotonic()
        if interrupted or now-start > 60 or (os.environ.get('FILLER_DEADLINE') and time.time() >= int(os.environ['FILLER_DEADLINE'])):
            failure='timeout_or_stop'; break
        if graph_ready.exists() and not graph_release.exists():
            if graph_ready.read_text().strip() != str(child.pid):
                failure='graph_witness_pid_mismatch'; break
            capture_maps()
            graph_release.write_text('release\n')
        if backend == 'hip' and ready.exists() and not release.exists():
            if ready.read_text().strip() != str(child.pid):
                failure='witness_pid_mismatch'; break
            capture_maps()
            release.write_text('release\n')
        if backend == 'hip':
            proc=pathlib.Path('/sys/class/kfd/kfd/proc')/str(child.pid); v={}
            for p in proc.glob('vram_*'):
                try: v[p.name]=int(p.read_text().strip())
                except (ValueError,OSError): pass
            sample={'monotonic_ns':time.monotonic_ns(),'kfd_process':proc.exists(),'vram_bytes':sum(v.values()),'vram_files':v}
            samples.append(sample)
            sample_log.write(json.dumps(sample)+'\n')
        time.sleep(.002 if backend == 'hip' else .05)
finally:
    if child.poll() is None:
        os.killpg(child.pid,signal.SIGTERM)
        try: child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid,signal.SIGKILL); child.wait(timeout=3)
    sample_log.close()
    log.close()
    output=(out/'unit.log').read_text()
    (out/'residency-samples.json').write_text(json.dumps(samples,indent=2)+'\n')
    events={}
    if timeline.exists():
        try: events={k:int(v) for k,v in (line.split() for line in timeline.read_text().splitlines())}
        except ValueError: failure='malformed_timeline'
    overlap=sum(1 for s in samples if s['kfd_process'] and s['vram_bytes']>0 and events.get('first_launch',1) <= s['monotonic_ns'] <= events.get('last_finish',0))
    dead=not pathlib.Path('/proc',str(child.pid)).exists()
    approved=json.loads((D/('approved-'+backend+'.json')).read_text())
    pinned={str(pathlib.Path(x['path']).resolve()):x['sha256'] for x in approved['artifacts'] if x['role'] in ('ggml_dso','llama_dso')}
    loaded_ggml={p:d for p,d in maps.items() if 'ggml' in pathlib.Path(p).name or 'libllama' in pathlib.Path(p).name}
    if not graph_ready.exists() or not graph_release.exists(): failure=failure or 'missing_graph_witness'
    if not pinned or any(maps.get(p) != digest for p,digest in pinned.items()) or any(pinned.get(p) != digest for p,digest in loaded_ggml.items()): failure=failure or 'loaded_ggml_identity_mismatch'
    if backend=='hip' and (not ready.exists() or not release.exists() or overlap < 1 or not maps): failure=failure or 'missing_hip_residency'
    if not dead: failure=failure or 'owned_pid_still_alive'
    result={'case':case,'backend':backend,'pid':child.pid,'returncode':child.returncode,'pid_dead_verified':dead,'overlapping_residency_samples':overlap,'loaded_dsos_sha256':maps,'failure':failure,'argv':cmd}
    (out/'witness.json').write_text(json.dumps(result,indent=2)+'\n')
print(output, end='')
print(json.dumps(result),flush=True)
sys.exit(1 if failure or child.returncode != 0 else 0)
