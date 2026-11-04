#!/usr/bin/env python3
"""Bounded one-server diagnostic capture; no scientific verdict is generated."""
import argparse, datetime, hashlib, json, os, pathlib, signal, subprocess, sys, threading, time, urllib.request
from residency_evidence import analyze_residency
from build_receipt_v4 import bind_v4_receipt
from analyze_timed_run import analyze as analyze_timed_run


def gpu_sample():
    record = {"observation_start": time.time(), "monotonic_start": time.monotonic()}
    try:
        proc = subprocess.run(["rocm-smi", "--showmeminfo", "vram", "--showproductname", "--json"], capture_output=True, text=True, timeout=5)
        record.update(rocm_smi_rc=proc.returncode, rocm_smi=proc.stdout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        record["rocm_smi_error"] = repr(exc)
    record["time"] = time.time()
    record["observation_end"] = time.time()
    record["monotonic_end"] = time.monotonic()
    return record



def digest(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_samples(path):
    try:
        return [json.loads(line) for line in path.read_text().splitlines()], None
    except (OSError, ValueError) as exc:
        return [], repr(exc)


def resolve_build_binding(config):
    """Bind configured server/backend to a complete content-checked V4 result.

    This checks artifact identity only: grant ownership and live GPU residency
    are independent requirements. No model weights are hashed here.
    """
    record = json.loads(pathlib.Path(config['build_result']).read_text())
    bound = bind_v4_receipt(record, config['build_root'])
    server = pathlib.Path(config['server']).resolve(strict=True)
    backend = pathlib.Path(config['backend']).resolve(strict=True)
    artifacts = bound['artifacts']
    if str(server) != artifacts['server']['path']:
        raise ValueError('server is not the bound build artifact')
    if str(backend) != artifacts['hip']['path']:
        raise ValueError('backend is not the bound HIP artifact')
    if config['backend_sha256'] != artifacts['hip']['sha256']:
        raise ValueError('configured backend digest differs from build receipt')
    build = server.parent.parent
    return bound, server, backend, build


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('config', type=pathlib.Path)
    a = ap.parse_args()
    c = json.loads(a.config.read_text())
    out = pathlib.Path(c['output']); out.mkdir(parents=True, exist_ok=False)
    bound, server, backend, build = resolve_build_binding(c)
    (out / 'build-binding.json').write_text(json.dumps(bound, indent=2) + '\n')
    preflight = pathlib.Path(c['model_preflight']).resolve()
    if digest(preflight) != c['model_preflight_sha256']: raise ValueError('model preflight digest mismatch')
    model_info = json.loads(preflight.read_text())['model']
    model = pathlib.Path(c['model']).resolve()
    st = model.stat()
    actual = dict(dev=st.st_dev, ino=st.st_ino, size=st.st_size, mtime_ns=st.st_mtime_ns, ctime_ns=st.st_ctime_ns)
    if str(model) != model_info['path'] or actual != model_info['stat'] or c['model_sha256'] != model_info['sha256']: raise ValueError('model preflight stat or hash identity mismatch')
    layer_manifest = pathlib.Path(c['layer_manifest']).resolve(strict=True)
    if digest(layer_manifest) != c['layer_manifest_sha256']: raise ValueError('layer manifest digest mismatch')
    layers = json.loads(layer_manifest.read_text())
    if layers['provenance']['path'] != str(model) or layers['provenance']['size_bytes'] != st.st_size: raise ValueError('layer manifest model mismatch')
    layer_ids = layers['verify_attention_layer_ids']
    if (not isinstance(layer_ids, list) or not layer_ids or
        any(type(x) is not int or x < 0 for x in layer_ids) or len(set(layer_ids)) != len(layer_ids)):
        raise ValueError('invalid expected attention layers')
    # Fixed marker must be specified after source review; it must occur in a built backend.
    if c['trace_marker'].encode() not in backend.read_bytes(): raise ValueError('trace marker missing')
    if not c['trace_marker']: raise ValueError('empty trace marker')
    if not c['requests']: raise ValueError('empty request list')
    if not 1 <= c['timeout_seconds'] <= 1800: raise ValueError('invalid timeout')
    if not c['url'].startswith('http://127.0.0.1:'): raise ValueError('loopback URL required')
    env = os.environ.copy(); env['LD_LIBRARY_PATH'] = str(backend.parent); env['GGML_G3_FATTN_TRACE'] = '1'
    with (out / 'linkage.txt').open('w') as linkage:
        subprocess.run(['/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh', str(server), str(build)], env=env, stdout=linkage, stderr=subprocess.STDOUT, check=True)
    argv = [str(server), *c['server_args']]
    (out / 'manifest.json').write_text(json.dumps({'config': c, 'argv': argv, 'model_sha256': c['model_sha256'], 'backend_sha256': digest(backend), 'server_sha256': digest(server), 'trace_mode': 'graph replay disabled; diagnostic only'}, indent=2) + '\n')
    stop = pathlib.Path(os.environ['FILLER_STOPFILE'])
    grant_deadline = int(os.environ['FILLER_DEADLINE'])
    if stop.exists() or time.time() >= grant_deadline: raise RuntimeError('grant stopped or expired')
    c['timeout_seconds'] = min(c['timeout_seconds'], max(0, int(grant_deadline - time.time())))
    if c['timeout_seconds'] < 1: raise RuntimeError('grant expired')
    done = threading.Event()
    baseline = gpu_sample()
    (out / 'residency-baseline.json').write_text(json.dumps(baseline) + '\n')
    request_windows = []
    with (out / 'server.log').open('wb') as log:
        # Keep TERM/INT pending until the new process group is captured and its
        # leader registered with the filler. The child restores the old signal
        # mask before exec. The filler can then reap the captured PID even if
        # this Python process is forcibly killed.
        masked = {signal.SIGTERM, signal.SIGINT}
        oldmask = signal.pthread_sigmask(signal.SIG_BLOCK, masked)
        oldhandlers = {sig: signal.getsignal(sig) for sig in masked}
        def interrupted(signum, frame):
            raise InterruptedError('signal ' + str(signum))
        for sig in masked: signal.signal(sig, interrupted)
        proc = None
        try:
            proc = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, env=env,
                                    start_new_session=True,
                                    preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, oldmask))
            with open(os.environ['FILLER_PIDFILE'], 'a', encoding='ascii') as registry:
                registry.write(str(proc.pid) + '\n'); registry.flush(); os.fsync(registry.fileno())
        except BaseException:
            if proc is not None:
                try: os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                proc.wait(timeout=10)
            for sig, handler in oldhandlers.items(): signal.signal(sig, handler)
            signal.pthread_sigmask(signal.SIG_SETMASK, oldmask)
            raise
        def sample():
            with (out / 'residency.jsonl').open('w') as f:
                while not done.is_set():
                    record = gpu_sample()
                    record.update(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), pid=proc.pid, alive=proc.poll() is None)
                    try: record['maps'] = pathlib.Path(f'/proc/{proc.pid}/maps').read_text()
                    except OSError: record['maps'] = None
                    record['kfd_pid_present'] = pathlib.Path(f'/sys/class/kfd/kfd/proc/{proc.pid}').exists()
                    record['observation_end'] = time.time()
                    record['monotonic_end'] = time.monotonic()
                    f.write(json.dumps(record) + '\n'); f.flush(); done.wait(1)
        sampler = threading.Thread(target=sample, daemon=True); sampler.start()
        result = {'status': 'partial', 'requests': []}; deadline = time.monotonic() + c['timeout_seconds']
        try:
            signal.pthread_sigmask(signal.SIG_SETMASK, oldmask)
            for payload in c['requests']:
                while True:
                    if stop.exists(): raise InterruptedError('STOP')
                    if proc.poll() is not None: raise RuntimeError('server exited')
                    if time.monotonic() >= deadline: raise TimeoutError('deadline')
                    try:
                        with urllib.request.urlopen(c['url'].rsplit('/', 1)[0] + '/health', timeout=2) as response:
                            if response.status == 200: break
                    except (OSError, ValueError): time.sleep(.5)
                if stop.exists(): raise InterruptedError('STOP')
                req = urllib.request.Request(c['url'], data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'})
                # A watcher must stop the server even while a request blocks.
                def watch():
                    while not done.wait(.2):
                        if stop.exists() or time.monotonic() >= deadline:
                            try: os.killpg(proc.pid, signal.SIGTERM)
                            except ProcessLookupError: pass
                            return
                watcher = threading.Thread(target=watch, daemon=True); watcher.start()
                request_start = time.time()
                try:
                    with urllib.request.urlopen(req, timeout=max(1, deadline-time.monotonic())) as response:
                        result['requests'].append(json.load(response))
                finally:
                    request_windows.append([request_start, time.time()])
                if stop.exists(): raise InterruptedError('STOP')
            result['status'] = 'complete'
        except Exception as e: result['error'] = repr(e)
        finally:
            for sig in masked: signal.signal(sig, signal.SIG_IGN)
            if stop.exists(): result['status'] = 'partial'; result['error'] = 'STOP'
            try: os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError: pass
            try: proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL); proc.wait(timeout=10)
            done.set(); sampler.join(timeout=8)
            try:
                os.killpg(proc.pid, 0)
                os.killpg(proc.pid, signal.SIGKILL)
                for _ in range(50):
                    try: os.killpg(proc.pid, 0)
                    except ProcessLookupError: break
                    time.sleep(.1)
                else: raise RuntimeError('process group did not drain')
                drained = True
            except ProcessLookupError: drained = True
            except RuntimeError: drained = False
            samples, sample_error = read_samples(out / 'residency.jsonl')
            residency = []
            for start, end in request_windows:
                try:
                    residency.append(analyze_residency(baseline=baseline, samples=samples,
                        card=c['rocm_card'], pid=proc.pid, backend=backend,
                        expected_sha256=c['backend_sha256'], start=start, end=end))
                except (OSError, ValueError, KeyError) as exc:
                    residency.append({'status': 'UNKNOWN', 'reasons': [repr(exc)]})
            if not request_windows:
                residency.append({'status': 'UNKNOWN', 'reasons': ['no request observation window']})
            if sample_error:
                residency.append({'status': 'UNKNOWN', 'reasons': ['unreadable residency capture: ' + sample_error]})
            result['residency'] = residency
            result['residency_scope'] = 'HTTP request window only; trace overlap and device isolation remain unproven'
            result['request_windows'] = request_windows
            result.update(server_exit=proc.returncode, process_group_drained=drained)
            # The observations are diagnostic-only and fail closed when capture,
            # correlation or clock samples are incomplete. They do not authorize
            # admission and device-wide VRAM is not per-process attribution.
            log.flush()
            try:
                result['timed_analysis'] = analyze_timed_run(
                    trace=(out / 'server.log').read_text(errors='replace'), expected_layer_ids=layer_ids,
                    baseline=baseline, samples=samples, card=c['rocm_card'], pid=proc.pid,
                    backend=backend, backend_sha256=c['backend_sha256'],
                    complete=result['status'] == 'complete' and not sample_error, drained=drained)
            except (OSError, ValueError, KeyError) as exc:
                result['timed_analysis'] = {'status': 'UNKNOWN', 'reasons': [repr(exc)]}
            if not drained: result['status'] = 'partial'
            (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            for sig, handler in oldhandlers.items(): signal.signal(sig, handler)
    return 0 if result['status'] == 'complete' else 75

if __name__ == '__main__': sys.exit(main())
