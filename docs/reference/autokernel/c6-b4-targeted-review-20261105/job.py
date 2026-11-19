#!/usr/bin/env python3
"""Paired exact-case C6 diagnostic. Invoked only by rowflow under a GPU grant."""
from __future__ import annotations
import hashlib, json, os, pathlib, re, signal, subprocess, sys, time
import residency
from compare_capture import compare, load
from bind import image
from grant_evidence import validate as validate_grant

D = pathlib.Path(__file__).resolve().parent
BOUND = json.loads((D / 'BOUND.json').read_text())
SPEC = json.loads((D / 'spec.json').read_text())
PINS = {key: BOUND[key] for key in ('baseline','corrected')}
IMAGES = {key:(pathlib.Path(pin['binary']),pathlib.Path(pin['library_dir']),pin) for key,pin in PINS.items()}
CASES = SPEC['cases']
CAPTURES = ('candidate_weight.bin', 'candidate_activation.bin', 'sibling_weight.bin', 'sibling_activation.bin', 'candidate_output.bin', 'sibling_output.bin')
ROUTE = re.compile(r'GGML_CUDA_MUL_MAT_ROUTE route=(\S+) .*type=q4_K .*src0_ne=\[256,16,(\d+),(\d+)\] .*src1_ne=\[256,([45]),(\d+),(\d+)\] .*ne11=\4')
PROP = re.compile(r'AK_PROP_V2 metric=fp64_error_ratio/host-double-gguf-wire/v1 residual=([^ ]+) tolerance=([^ ]+) passed=([01]) suite_seed=(\d+)')

def sha(path):
    with pathlib.Path(path).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def check_inputs():
    if sha(BOUND['build_receipt']) != BOUND['build_receipt_sha256'] or sha(D/'PRIOR-CANDIDATE-RESULT.json') != BOUND['prior_n4_sha256']:
        raise RuntimeError('receipt or prior result drift')
    build = json.loads(pathlib.Path(BOUND['build_receipt']).read_text())
    source = pathlib.Path(BOUND['build_receipt']).parent
    if build['source_manifest_sha256'] != BOUND['build_source_manifest_sha256'] or sha(source/'BUILD-INPUTS.sha256') != BOUND['build_source_manifest_sha256'] or sha(source/'b4-quantized-min.patch') != BOUND['build_patch_sha256']:
        raise RuntimeError('corrected source custody drift')
    subprocess.run(['sha256sum','--strict','--quiet','-c','BUILD-INPUTS.sha256'],cwd=source,check=True)
    for name,(binary,libdir,pin) in IMAGES.items():
        files,links=image(libdir)
        if files != pin['files'] or links != pin['symlinks'] or sha(binary) != pin['binary_sha256']:
            raise RuntimeError(name+': image drift')
        if b'C6_PROPERTY_CAPTURE_DIR' not in binary.read_bytes() or b'C6_SEED_INDEX' not in binary.read_bytes():
            raise RuntimeError(name+': capture instrumentation missing')
    prior=pathlib.Path(BOUND['n5_capture_path'])
    if {p.name:sha(p) for p in prior.iterdir() if p.is_file() and not p.is_symlink()} != BOUND['n5_capture_sha256']:
        raise RuntimeError('n5 prior capture drift')

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
        'C6_PROPERTY_CAPTURE_DIR': str(out), 'GGML_FA_VKQ_F32': '1',
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
    capture_meta = load(out)
    seed_markers = re.findall(r'^C6_SEED_INDEX (\d+)$', stderr, re.M)
    props = list(PROP.finditer(stdout))
    if len(seed_markers) != 1 or len(props) != 1 or int(props[0].group(4)) != seed:
        raise RuntimeError(f'{label}/{case["name"]}: seed/case accounting mismatch')
    routes = [(m.group(1), (int(m.group(2)), int(m.group(3)), int(m.group(5)), int(m.group(6))),int(m.group(4))) for m in ROUTE.finditer(stderr)]
    want = [(3,2,6,4),(2,3,2,3),(1,1,1,1)][caseidx]
    selected_routes = [r for r in routes if r[1] == want and r[2] == (5 if caseidx == 2 else 4)]
    if not selected_routes:
        raise RuntimeError(f'{label}/{case["name"]}: exact q4_K route signature absent; saw={routes!r}')
    clean = re.sub(r'\x1b\[[0-9;]*m', '', stdout)
    selected = re.findall(r'^\s*MUL_MAT\((.*?)\):\s+AK_PROP_V2 ',clean,re.M)
    totals = re.findall(r'^\s*(\d+)/(\d+) tests passed\s*$',clean,re.M)
    if len(selected) != 1 or not re.fullmatch(case['params_regex'],selected[0]) or len(totals) != 1 or totals[0][1] != '1':
        raise RuntimeError('selected case or native test accounting mismatch')
    verdicts = re.findall(r'^\s*Backend ROCm0: (OK|FAIL)\s*$', clean, re.M)
    if len(verdicts) != 1 or not re.search(r'^\d+/\d+ backends passed\s*$', clean, re.M):
        raise RuntimeError(f'{label}/{case["name"]}: missing native terminal summary')
    residual, tolerance, passed, _ = props[0].groups()
    prop_passed = passed == '1'
    import math
    if not math.isfinite(float(residual)) or not math.isfinite(float(tolerance)) or (float(residual) <= float(tolerance)) != prop_passed:
        raise RuntimeError('invalid residual or property')
    if totals[0][0] != ('1' if prop_passed else '0') or rc not in (0,1) or (rc == 0) != prop_passed or verdicts[0] != ('OK' if rc == 0 else 'FAIL'):
        raise RuntimeError(f'{label}/{case["name"]}: rc/property/backend terminal verdict disagree')
    record = {
        'seed': seed, 'case': case['name'], 'arm': label, 'native_rc': rc,
        'property': {'residual': float(residual), 'tolerance': float(tolerance), 'passed': passed == '1'},
        'capture_metadata':capture_meta, 'seed_index': int(seed_markers[0]), 'route_shapes': [{'route':r,'dims':list(d),'n':n} for r,d,n in selected_routes], 'expected_mmvq_route_observed': any(r == CASES[caseidx]['expected_route'] for r,d,n in selected_routes),
        'stdout_sha256': sha(stdout_path), 'stderr_sha256': sha(stderr_path),
        'capture_sha256': {n: sha(out/n) for n in CAPTURES}, 'hip_maps': hip_maps,
        'residency': proof, 'binary_sha256': sha(binary), 'library_dir': str(libdir),
    }
    (out / 'record.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    return record

def compare_pair(runroot, seed, caseidx, records):
    case = CASES[caseidx]
    a = runroot / f'seed-{seed:03d}' / case['name'] / 'baseline'
    b = runroot / f'seed-{seed:03d}' / case['name'] / 'corrected'
    for suffix in ('weight.bin', 'activation.bin'):
        if sha(a / ('candidate_' + suffix)) != sha(b / ('candidate_' + suffix)):
            raise RuntimeError(f'seed {seed} {case["name"]}: paired GPU inputs differ across images')
    for root in (a,b):
        for suffix in ('weight.bin','activation.bin'):
            if sha(root / ('candidate_' + suffix)) != sha(root / ('sibling_' + suffix)):
                raise RuntimeError(f'{root}: GPU and oracle input captures differ')
    prior=json.loads((D/'PRIOR-CANDIDATE-RESULT.json').read_text())['records'][caseidx]
    for label, root in [('baseline',a),('corrected',b)]:
        for tensor in ('weight','activation'):
            if sha(root/('candidate_'+tensor+'.bin')) != prior['capture']['candidate_'+tensor]['sha256']:
                raise RuntimeError('captured inputs do not match retained diagnostic; no causal claim')
        if records[label]['property']['tolerance'] != case['tolerance_seed71']:
            raise RuntimeError('original tolerance changed')
        if not records[label]['expected_mmvq_route_observed']:
            raise RuntimeError('MMVQ route absent; no branch attribution')
    x, y = records['baseline'], records['corrected']
    if seed == 71:
        for arm in ('baseline', 'corrected'):
            metric = records[arm]['property']
            if arm == 'baseline' and (abs(metric['residual']-case['residual_seed71']) > 1e-12 or abs(metric['tolerance']-case['tolerance_seed71']) > 1e-12):
                raise RuntimeError(f'seed 71 exact replay mismatch for {case["name"]}: got {metric}')
    if x['seed_index'] != y['seed_index'] or x['seed_index'] != prior['ordinal']:
        raise RuntimeError(f'seed {seed} {case["name"]}: generic/candidate case ordinals differ')
    return {
        'seed': seed, 'case': case['name'],
        'inputs_byte_identical_across_images': True,
        'route_identical': x['route_shapes'] == y['route_shapes'],
        'expected_mmvq_route_observed': x['expected_mmvq_route_observed'] and y['expected_mmvq_route_observed'],
        'baseline': x['property'], 'corrected': y['property'],
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
    expected_id=SPEC['id']
    grant_dir=pathlib.Path(os.environ.get('FILLER_GRANTS_DIR','/mnt/raid0/llm/tmp/compute-flags/grants'))
    grant_text=(grant_dir/(expected_id+'.grant')).read_text()
    grant={k:os.environ.get(k,'') for k in ('FILLER_ID','FILLER_CPUS','FILLER_NEEDGPU','FILLER_DEADLINE')}
    grant.update(grant_text=grant_text,grant_sha256=hashlib.sha256(grant_text.encode()).hexdigest())
    validate_grant(grant,expected_id,dry)
    runroot=D/('smoke-runs' if dry else 'runs')/('run-'+str(time.time_ns()));runroot.mkdir(parents=True)
    rows=[];pairs=[]
    for ci,case in enumerate(CASES[:2]):
        records={}
        for arm in (('baseline','corrected') if ci==0 else ('corrected','baseline')):
            records[arm]=run_case(runroot,71,ci,arm);rows.append(records[arm])
        pairs.append(compare_pair(runroot,71,ci,records))
        (runroot/'PROGRESS.json').write_text(json.dumps({'completed_pairs':len(pairs)}))
    n5=run_case(runroot,71,2,'corrected'); rows.append(n5)
    if n5['seed_index'] != 7047 or n5['property']['tolerance'] != CASES[2]['tolerance_seed71'] or not n5['expected_mmvq_route_observed']:
        raise RuntimeError('n5 ordinal/tolerance/MMQ route mismatch')
    n5dir=runroot/'seed-071'/CASES[2]['name']/'corrected'
    comparison=compare(BOUND['n5_capture_path'],n5dir)
    if not comparison['input_bytes_equal']: raise RuntimeError('n5 input drift')
    check_inputs()
    result={'n5':n5,'n5_comparison':comparison,'completed_pairs':len(pairs),'schema':'epyc.c6.corrected-comparison.v1','status':'COMPLETE_DIAGNOSTIC_ONLY','records':rows,'pairs':pairs,'pins':PINS,'binding_sha256':sha(D/'BOUND.json'),'cleanup':True,'invocation_id':invocation_id,'grant':grant,'run':str(runroot),'run_mode':'dryrun' if dry else 'grant','scope':'two paired n4 cases and n5 preservation; images may differ in other libraries; no sole-source causality','performance_claim':None,'promotion_claim':None,'full_gate_pass':None}
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
