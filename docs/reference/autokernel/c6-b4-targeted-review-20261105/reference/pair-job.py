#!/usr/bin/env python3
"""Paired exact-case C6 diagnostic. Invoked only by rowflow under a GPU grant."""
from __future__ import annotations
import hashlib, json, os, pathlib, re, signal, subprocess, sys, time
import residency

D = pathlib.Path(__file__).resolve().parent
PINS = json.loads((D / 'PINS.json').read_text())
SPEC = json.loads((D / 'spec.json').read_text())
ROOT = pathlib.Path('/mnt/raid0/llm/kernels/builds/gpu-20261030-729599d69-c6')
IMAGES = {
    'generic': (pathlib.Path(PINS['generic']['binary']), pathlib.Path(PINS['generic']['library_dir']), PINS['generic']),
    'candidate': (pathlib.Path(PINS['candidate']['binary']), pathlib.Path(PINS['candidate']['library_dir']), PINS['candidate']),
}
CASES = SPEC['cases']
CAPTURES = ('candidate_weight.bin', 'candidate_activation.bin', 'sibling_weight.bin', 'sibling_activation.bin', 'candidate_output.bin', 'sibling_output.bin')
ROUTE = re.compile(r'GGML_CUDA_MUL_MAT_ROUTE route=(\S+) .*type=q4_K .*src0_ne=\[256,16,(\d+),(\d+)\] .*src1_ne=\[256,4,(\d+),(\d+)\] .*ne11=4')
PROP = re.compile(r'AK_PROP_V2 metric=fp64_error_ratio/host-double-gguf-wire/v1 residual=([^ ]+) tolerance=([^ ]+) passed=([01]) suite_seed=(\d+)')

def sha(path):
    with pathlib.Path(path).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def check_inputs():
    source = pathlib.Path('/mnt/raid0/llm/tmp/autokernel-cross-workload-keep-gate/c6-n4-generic-bypass-20261104/src')
    build = json.loads((D/'GENERIC-BUILD-RESULT.json').read_text())
    manifest = D/'GENERIC-source-manifest.json'
    if sha(manifest) != build['source_manifest_sha256'] or sha(D/'generic-bypass.patch') != build['patch_sha256']:
        raise RuntimeError('generic source manifest or patch drift')
    if build['source_base'] != '729599d69871181d67af715a4c2f9162d5153a2e' or build['candidate_hip_sha256'] != PINS['generic']['hip_library_sha256']:
        raise RuntimeError('generic build provenance mismatch')
    if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip() != build['source_base']:
        raise RuntimeError('generic source base mismatch')
    for name, digest in json.loads(manifest.read_text()).items():
        path = source / name
        if not path.resolve().is_relative_to(source.resolve()) or sha(path) != digest:
            raise RuntimeError('generic source manifest mismatch: '+name)
    for name, (binary, libdir, pin) in IMAGES.items():
        if not binary.is_file() or sha(binary) != pin['binary_sha256']:
            raise RuntimeError(f'{name}: binary missing or digest drift')
        hip = libdir / 'libggml-hip.so.0.16.0'
        if not hip.is_file() or sha(hip) != pin['hip_library_sha256']:
            raise RuntimeError(f'{name}: HIP library missing or digest drift')
        for libname, digest in pin['ggml_libraries_sha256'].items():
            if sha(libdir / libname) != digest:
                raise RuntimeError(f'{name}: ggml DSO digest drift: {libname}')
        if b'C6_PROPERTY_CAPTURE_DIR' not in binary.read_bytes() or b'C6_SEED_INDEX' not in binary.read_bytes():
            raise RuntimeError(f'{name}: exact-seed/capture instrumentation missing')
    for label, (_, libdir, pin) in IMAGES.items():
        for name, digest in pin['files'].items():
            if sha(libdir/name) != digest: raise RuntimeError('image content drift')
        for name, target in pin['symlinks'].items():
            p=libdir/name
            if not p.is_symlink() or os.readlink(p)!=target or not p.resolve().is_relative_to(libdir): raise RuntimeError('image alias drift')

def grant_boundary(min_seconds=45):
    stop = pathlib.Path(os.environ.get('FILLER_STOPFILE', D / 'STOP'))
    deadline = float(os.environ.get('FILLER_DEADLINE', '0'))
    if stop.exists() or deadline <= time.time() + min_seconds:
        raise InterruptedError('STOP/deadline boundary reached')

def run_case(runroot, seed, caseidx, arm):
    grant_boundary()
    label = arm
    binary, libdir, pin = IMAGES[label]
    case = CASES[caseidx]
    out = runroot / f'seed-{seed:03d}' / case['name'] / label
    out.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    for key in ('LD_LIBRARY_PATH', 'GGML_BACKEND_PATH', 'HIP_VISIBLE_DEVICES', 'ROCR_VISIBLE_DEVICES', 'CUDA_VISIBLE_DEVICES', 'C6_PROPERTY_CAPTURE_DIR', 'GGML_CUDA_LOG_MMVQ_ROUTE'):
        env.pop(key, None)
    env.update({
        'LD_LIBRARY_PATH': str(libdir) + ':/opt/rocm/lib',
        'GGML_BACKEND_PATH': str(libdir),
        'C6_PROPERTY_CAPTURE_DIR': str(out),
        'GGML_CUDA_LOG_MMVQ_ROUTE': '2',
        'HIP_VISIBLE_DEVICES': '0', 'ROCR_VISIBLE_DEVICES': '0', 'CUDA_VISIBLE_DEVICES': '0',
        'HSA_OVERRIDE_CPU_AFFINITY_DEBUG': '0',
    })
    cmd = [str(binary), 'test', '-b', 'ROCm0', '-o', 'MUL_MAT', '-p', case['params_regex'], '-j', '1', '--suite-seed', str(seed), '--autokernel-properties']
    stdout_path, stderr_path = out / 'stdout.log', out / 'stderr.log'
    with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
        if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
            raise RuntimeError('pidfd lifecycle control unavailable')
        proc = subprocess.Popen(cmd, env=env, stdout=stdout, stderr=stderr)
        try:
            pidfd = os.pidfd_open(proc.pid)
        except BaseException:
            proc.terminate()
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait(timeout=5)
            raise
        sampler = residency.Sampler(.02)
        try:
            sampler.watch_pid(proc.pid); sampler.__enter__()
        except BaseException:
            if proc.poll() is None:
                signal.pidfd_send_signal(pidfd, signal.SIGTERM)
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    signal.pidfd_send_signal(pidfd, signal.SIGKILL); proc.wait(timeout=5)
            os.close(pidfd)
            raise
        mapped_files = {}
        try:
            while proc.poll() is None:
                try:
                    for line in pathlib.Path(f'/proc/{proc.pid}/maps').read_text().splitlines():
                        bits = line.split()
                        if len(bits) >= 6 and '/libggml' in bits[-1]:
                            mapped = pathlib.Path(bits[-1]).resolve()
                            mapped_files[str(mapped)] = {'dev':bits[3], 'inode':int(bits[4])}
                except (FileNotFoundError, ProcessLookupError, PermissionError):
                    pass
                grant_boundary(30)
                time.sleep(.02)
            rc = proc.wait()
        except BaseException:
            if proc.poll() is None:
                signal.pidfd_send_signal(pidfd, signal.SIGTERM)
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    signal.pidfd_send_signal(pidfd, signal.SIGKILL)
                    proc.wait(timeout=5)
            if pathlib.Path(f'/proc/{proc.pid}').exists():
                raise RuntimeError(f'owned child pid {proc.pid} failed to drain')
            raise
        finally:
            sampler.__exit__()
            os.close(pidfd)
    proof = sampler.proof
    expected_dir = libdir.resolve()
    hip_maps = {}
    for p, identity in mapped_files.items():
        mapped = pathlib.Path(p)
        st = mapped.stat()
        major, minor = (int(v,16) for v in identity['dev'].split(':'))
        if st.st_ino != identity['inode'] or os.major(st.st_dev) != major or os.minor(st.st_dev) != minor:
            raise RuntimeError(f'{label}: mapped library identity changed while child ran: {p}')
        if not mapped.is_relative_to(expected_dir):
            raise RuntimeError(f'{label}: ggml DSO loaded outside its own image tree: {p}')
        digest = sha(mapped)
        expected_digest = pin['ggml_libraries_sha256'].get(mapped.name)
        if expected_digest is None or digest != expected_digest:
            raise RuntimeError(f'{label}: mapped ggml DSO is unpinned or changed: {p}')
        hip_maps[p] = digest
    if not hip_maps or not any(pathlib.Path(p).name.startswith('libggml-hip.so') and digest == pin['hip_library_sha256'] for p,digest in hip_maps.items()):
        raise RuntimeError(f'{label}/{case["name"]}: own-PID mapped HIP DSO is not pinned image library')
    if proc.poll() is None or pathlib.Path(f'/proc/{proc.pid}').exists():
        raise RuntimeError(f'{label}/{case["name"]}: child did not drain')
    if proof.get('own_pid_kfd_reads', 0) < 2 or proof.get('own_pid_peak_vram_bytes', 0) <= 0:
        raise RuntimeError(f'{label}/{case["name"]}: positive own-PID KFD VRAM proof absent')
    if not all((out / n).is_file() for n in CAPTURES):
        raise RuntimeError(f'{label}/{case["name"]}: incomplete raw capture')
    stderr = stderr_path.read_text(errors='replace')
    stdout = stdout_path.read_text(errors='replace')
    seed_markers = re.findall(r'^C6_SEED_INDEX (\d+)$', stderr, re.M)
    props = list(PROP.finditer(stdout))
    if len(seed_markers) != 1 or len(props) != 1 or int(props[0].group(4)) != seed:
        raise RuntimeError(f'{label}/{case["name"]}: seed/case accounting mismatch')
    routes = [(m.group(1), (int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)))) for m in ROUTE.finditer(stderr)]
    want = (3,2,6,4) if caseidx == 0 else (2,3,2,3)
    selected_routes = [r for r in routes if r[1] == want]
    if not selected_routes:
        raise RuntimeError(f'{label}/{case["name"]}: exact q4_K route signature absent; saw={routes!r}')
    clean = re.sub(r'\x1b\[[0-9;]*m', '', stdout)
    verdicts = re.findall(r'^\s*Backend ROCm0: (OK|FAIL)\s*$', clean, re.M)
    if len(verdicts) != 1 or not re.search(r'^\d+/\d+ backends passed\s*$', clean, re.M):
        raise RuntimeError(f'{label}/{case["name"]}: missing native terminal summary')
    residual, tolerance, passed, _ = props[0].groups()
    prop_passed = passed == '1'
    if rc not in (0,1) or (rc == 0) != prop_passed or verdicts[0] != ('OK' if rc == 0 else 'FAIL'):
        raise RuntimeError(f'{label}/{case["name"]}: rc/property/backend terminal verdict disagree')
    record = {
        'seed': seed, 'case': case['name'], 'arm': label, 'native_rc': rc,
        'property': {'residual': float(residual), 'tolerance': float(tolerance), 'passed': passed == '1'},
        'seed_index': int(seed_markers[0]), 'route_shapes': [{'route':r,'dims':list(d)} for r,d in selected_routes], 'expected_mmvq_route_observed': any(r == 'MMVQ' for r,d in selected_routes),
        'stdout_sha256': sha(stdout_path), 'stderr_sha256': sha(stderr_path),
        'capture_sha256': {n: sha(out/n) for n in CAPTURES}, 'hip_maps': hip_maps,
        'residency': proof, 'binary_sha256': sha(binary), 'library_dir': str(libdir),
    }
    (out / 'record.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    return record

def compare_pair(runroot, seed, caseidx, records):
    case = CASES[caseidx]
    a = runroot / f'seed-{seed:03d}' / case['name'] / 'generic'
    b = runroot / f'seed-{seed:03d}' / case['name'] / 'candidate'
    for suffix in ('weight.bin', 'activation.bin'):
        if sha(a / ('candidate_' + suffix)) != sha(b / ('candidate_' + suffix)):
            raise RuntimeError(f'seed {seed} {case["name"]}: paired GPU inputs differ across images')
    for root in (a,b):
        for suffix in ('weight.bin','activation.bin'):
            if sha(root / ('candidate_' + suffix)) != sha(root / ('sibling_' + suffix)):
                raise RuntimeError(f'{root}: GPU and oracle input captures differ')
    prior=json.loads((D/'PRIOR-CANDIDATE-RESULT.json').read_text())['records'][caseidx]
    for label, root in [('generic',a),('candidate',b)]:
        for tensor in ('weight','activation'):
            if sha(root/('candidate_'+tensor+'.bin')) != prior['capture']['candidate_'+tensor]['sha256']:
                raise RuntimeError('captured inputs do not match retained diagnostic; no causal claim')
        if records[label]['property']['tolerance'] != case['tolerance_seed71']:
            raise RuntimeError('original tolerance changed')
        if not records[label]['expected_mmvq_route_observed']:
            raise RuntimeError('MMVQ route absent; no branch attribution')
    x, y = records['generic'], records['candidate']
    if seed == 71:
        for arm in ('generic', 'candidate'):
            metric = records[arm]['property']
            if arm == 'candidate' and (abs(metric['residual']-case['residual_seed71']) > 1e-12 or abs(metric['tolerance']-case['tolerance_seed71']) > 1e-12):
                raise RuntimeError(f'seed 71 exact replay mismatch for {case["name"]}: got {metric}')
    if x['seed_index'] != y['seed_index']:
        raise RuntimeError(f'seed {seed} {case["name"]}: generic/candidate case ordinals differ')
    return {
        'seed': seed, 'case': case['name'],
        'inputs_byte_identical_across_images': True,
        'route_identical': x['route_shapes'] == y['route_shapes'],
        'expected_mmvq_route_observed': x['expected_mmvq_route_observed'] and y['expected_mmvq_route_observed'],
        'generic': x['property'], 'candidate': y['property'],
        'candidate_minus_original_residual': y['property']['residual'] - x['property']['residual'],
        'pass_status_differs': x['property']['passed'] != y['property']['passed'],
    }

def main():
    if not os.environ.get('FILLER_DEADLINE') or not os.environ.get('FILLER_STOPFILE'): raise RuntimeError('missing grant')
    invocation_id = os.environ['C6_INVOCATION_ID']
    if not re.fullmatch(r'[0-9a-f-]{36}', invocation_id): raise RuntimeError('invalid invocation id')
    dry = os.environ.get('FILLER_DRYRUN') == '1'
    result_path = pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if dry else D/'RESULT.json'
    if result_path.exists() or (dry and result_path.resolve() == (D/'RESULT.json').resolve()): raise RuntimeError('result path already exists or smoke targets full result')
    check_inputs()
    runroot=D/'runs'/('run-'+str(time.time_ns()));runroot.mkdir(parents=True)
    rows=[];pairs=[]
    for ci,case in enumerate(CASES):
        records={}
        for arm in (('generic','candidate') if ci==0 else ('candidate','generic')):
            records[arm]=run_case(runroot,71,ci,arm);rows.append(records[arm])
        pairs.append(compare_pair(runroot,71,ci,records))
        (runroot/'PROGRESS.json').write_text(json.dumps({'completed_pairs':len(pairs)}))
    result={'completed_pairs':len(pairs),'schema':'epyc.c6.generic-isolation.v1','status':'COMPLETE_DIAGNOSTIC_ONLY','records':rows,'pairs':pairs,'pins':PINS,'cleanup':True,'invocation_id':invocation_id,'run':str(runroot),'run_mode':'dryrun' if dry else 'grant','scope':'two retained-input seed-71 cases; images differ in additional libraries; no sole-source causality','performance_claim':None,'promotion_claim':None,'full_gate_pass':None}
    # Rowflow isolates each smoke attempt; publish only this invocation's validated pairs.
    result_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = result_path.with_name(result_path.name + '.' + invocation_id + '.tmp')
    with temporary.open('x') as f:
        f.write(json.dumps(result,indent=2)+'\n'); f.flush(); os.fsync(f.fileno())
    try: os.link(temporary, result_path)  # atomic and refuses overwriting any prior result
    finally: temporary.unlink()
    return 0
if __name__=='__main__':
    try:sys.exit(main())
    except InterruptedError as e:print('INVALID_DIAGNOSTIC_STOP:',e,file=sys.stderr);sys.exit(75)
    except Exception as e:print('INVALID_DIAGNOSTIC:',e,file=sys.stderr);sys.exit(2)
