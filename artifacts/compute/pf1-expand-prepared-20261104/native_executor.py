#!/usr/bin/env python3
"""PF1 native executor: canonical wrapper, raw output and in-window witnesses.

This module is NOT an admission or booking interface. Call only from an
admitted owner-controlled launcher after all frozen-manifest and host gates.
"""
import hashlib, importlib.util, json, math, os, re, signal, subprocess, threading, time
from pathlib import Path
import controller
import affinity_witness
import maps_witness

ROOT=Path('/mnt/raid0/llm/worktrees/research-pin-brf-exp04-e7f6262b4')
WRAPPER=ROOT/'scripts/benchmark/bench_canonical.sh'
MONITOR=ROOT/'scripts/benchmark/cpu_prefill_v8_regression_runner.py'
SRC=Path('/mnt/raid0/llm/tmp/pf1-loadthreads-build-20261104/source')
HEAD='729599d69871181d67af715a4c2f9162d5153a2e'
BUILD_ROOT=Path('/mnt/raid0/llm/tmp/pf1-loadthreads-build-20261104/loadthreads-build')
CPU=BUILD_ROOT/'build-cpu/bin'
GPU=BUILD_ROOT/'build-gpu/bin'
BUILD_RECEIPT=BUILD_ROOT/'BUILD-RECEIPT.json'
MODEL=Path('/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf')

def validate_kfd_witness(witness):
    fallback=witness.get('lsof_fallback')
    if witness.get('unreadable_processes') and (not fallback or fallback.get('returncode') not in (0,1)):
        raise ValueError('KFD ownership could not be resolved')

def cpu_monitor(warrant):
    # The old executable runner is retired; import only its existing generic
    # process-group monitor and validator, never its stale binary/arm paths.
    import sys
    expected=warrant.get('monitor_sha256')
    if not expected or hashlib.sha256(MONITOR.read_bytes()).hexdigest()!=expected:
        raise ValueError('monitor/cache helper differs from frozen manifest')
    spec=importlib.util.spec_from_file_location('pf1_legacy_monitor',MONITOR)
    m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    if hashlib.sha256(MONITOR.read_bytes()).hexdigest()!=expected:
        raise ValueError('monitor/cache helper changed while loading')
    original=m.kfd_ownership; m.pf1_kfd_witnesses=[]
    def complete_kfd(*args,**kwargs):
        witness=original(*args,**kwargs); m.pf1_kfd_witnesses.append(witness)
        validate_kfd_witness(witness)
        return witness
    m.kfd_ownership=complete_kfd
    return m

def effective_load_threads():
    return max(1,len(os.sched_getaffinity(0)))

def command(cell,log_dir):
    arm=cell['arm']; binary=(CPU if arm=='A0' else GPU)/'llama-bench'
    args=['bash',str(WRAPPER),'-m',str(MODEL),'-p',str(cell['L']),'-n','0','-r',str(cell['n']),
          '--binary',str(binary),'--source-root',str(SRC),'--library-path',str(binary.parent),'--log-dir',str(log_dir)]
    if arm!='A0': args += ['--allow-skew']  # approved 2026-11-03 GPU placement covariate rule; A0 remains strict
    # The admitted launcher pins this process to the row's actual CPU grant.
    # A first-progress smoke therefore uses only its four allocated CPUs; full cells
    # naturally see the full 0-95 host grant.
    threads=effective_load_threads()
    args += ['--','-o','json','-oe','md','-mmp','0','--load-threads',str(threads)]
    if arm=='A0': args += ['-dev','none','-ngl','0','--no-op-offload','1']
    elif arm=='A1' or arm=='A1-disabled': args += ['-ngl','0','-ub',str(cell['ub'])]
    elif arm=='A2': args += ['-ngl','99','-ncmoe','48','-ub',str(cell['ub'])]
    else: raise ValueError('unknown arm')
    return args

def parse_bench(text,cell):
    build_lines=re.findall(r'^\s*build:\s*([0-9a-f]+)\s*\((\d+)\)\s*$',text,re.MULTILINE)
    if not any(HEAD.startswith(commit) and int(number)>0 for commit,number in build_lines):
        raise ValueError('missing result-emitted C6 build line')
    decoder=json.JSONDecoder()
    for m in re.finditer(r'\[\s*\{',text):
        try: data,_=decoder.raw_decode(text[m.start():])
        except ValueError: continue
        if not isinstance(data,list) or len(data)!=1 or not isinstance(data[0],dict): continue
        row=data[0]
        if row.get('n_prompt')!=cell['L'] or row.get('n_gen')!=0: continue
        if not isinstance(row.get('build_number'),int) or row.get('build_number')<=0 or not HEAD.startswith(str(row.get('build_commit','!'))): raise ValueError('benchmark build identity mismatch')
        ts=row.get('samples_ts'); ns=row.get('samples_ns')
        if not isinstance(ts,list) or not isinstance(ns,list) or len(ts)!=cell['n'] or len(ns)!=cell['n']: raise ValueError('truncated benchmark samples')
        if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<=0 for x in ts+ns): raise ValueError('invalid benchmark sample')
        return ts
    raise ValueError('missing exact llama-bench JSON row')

def capture(argv,timeout=8):
    try:
        p=subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,check=False)
        return {'argv':argv,'rc':p.returncode,'output':p.stdout,'at':time.time()}
    except (OSError,subprocess.TimeoutExpired) as e: return {'argv':argv,'error':repr(e),'at':time.time()}

def gpu_sample():
    # --showpidgpus takes a PID; --showpids supplies the KFD PID/VRAM mapping.
    return capture(['rocm-smi','--showpids','--showmeminfo','vram','--showclocks','--showpower','--showtemp','--showuse'],timeout=0.9)

def sample_gpu_until(stop, samples, sampler=gpu_sample, interval=0.8):
    """Sample independently of NUMA/proc scans; retain all timing failures."""
    while not stop.is_set():
        started=time.monotonic()
        try: sample=sampler()
        except Exception as exc: sample={'error':repr(exc)}
        sample['started_monotonic']=started
        sample['finished_monotonic']=time.monotonic()
        samples.append(sample)
        stop.wait(max(0,interval-(time.monotonic()-started)))

def validate_gpu_cadence(samples):
    if len(samples)<2: raise ValueError('insufficient in-window GPU samples')
    for sample in samples:
        start=sample.get('started_monotonic'); end=sample.get('finished_monotonic')
        if sample.get('rc')!=0 or not isinstance(start,(int,float)) or not isinstance(end,(int,float)) or not math.isfinite(start) or not math.isfinite(end) or end<start or end-start>1:
            raise ValueError('invalid or slow GPU sample')
    if any(not 0<b['started_monotonic']-a['started_monotonic']<=1 for a,b in zip(samples,samples[1:])):
        raise ValueError('GPU cadence below 1 Hz')

def attribute_kfd(snapshot):
    """Retain raw KFD owners and exclude only this sampled process group."""
    import copy
    clean=copy.deepcopy(snapshot)
    members=set(clean['target']['members'])
    owners=clean['contamination']['kfd_users']
    if not members or any(type(x.get('pid')) is not int for x in owners):
        raise ValueError('invalid KFD ownership witness')
    owned=[x for x in owners if x['pid'] in members]
    clean['contamination']['kfd_users']=[x for x in owners if x['pid'] not in members]
    return clean,owned

def gpu_residency(samples, owned, maps, pidgpu):
    """Require a mapped owned PID with a positive per-process VRAM row."""
    mapped={x['pid'] for x in maps if x.get('verdict')=='pass'}
    owned_pids={x['pid'] for group in owned for x in group}
    valid=mapped & owned_pids
    for sample in samples:
        for line in sample.get('output','').splitlines():
            match=re.match(r'^\s*(\d+)\s+\S+\s+\d+\s+(\d+)\s+\d+\s+\d+\s*$',line)
            pid=int(match.group(1)) if match else None
            mapped_device=any(x.get('rc')==0 and re.search(rf'PID\s+{pid}\s+is using\s+1\s+DRM device\(s\):\s*\n\s*0\s*(?:\n|$)',x.get('output','')) for x in pidgpu)
            if match and pid in valid and int(match.group(2))>0 and mapped_device:
                return {'pid':int(match.group(1)),'vram_bytes':int(match.group(2)),
                        'sample_started_monotonic':sample['started_monotonic'],'row':line}
    raise ValueError('owned benchmark PID with nonzero GPU VRAM not witnessed')

def total_vram(snapshot):
    values=re.findall(r'VRAM Total Used Memory \(B\):\s*(\d+)',snapshot.get('output',''))
    if len(values)!=1: raise ValueError('missing or ambiguous GPU VRAM total')
    return int(values[0])

def placement_proof(log_dir,arm):
    log_dir=Path(log_dir); raw=(log_dir/'placement.log').read_text(errors='replace')
    reason=(log_dir/'placement.log.reason').read_text(errors='replace').strip()
    rc=int((log_dir/'placement.log.rc').read_text().strip())
    header=re.search(r'NUMA placement check \(pid:(\d+),',raw)
    maximum=re.search(r'max=node(\d)@([\d.]+)%',raw)
    captured=re.search(r'^captured: pid=(\d+) comm=([^ ]+) rss_pages=(\d+).*expected_comm=([^ ]+) settled=(.*?) coverage_pct=(-?\d+)',reason,re.M)
    if not header or not maximum or not captured: raise ValueError('in-window placement proof missing')
    coverage=int(captured.group(6)); pid=int(captured.group(1)); logged_pid=int(header.group(1)); max_pct=float(maximum.group(2))
    if pid!=logged_pid or captured.group(2)!='llama-bench' or captured.group(4)!='llama-bench' or coverage<90:
        raise ValueError('placement PID/process/RSS coverage proof invalid')
    if arm=='A0' and (rc!=0 or max_pct>40): raise ValueError('A0 strict <=40% placement requirement failed')
    if arm!='A0' and rc not in (0,3): raise ValueError('GPU placement sample/checker invalid')
    shares={int(node):float(pct) for node,pct in re.findall(r'node (\d):\s+[\d.]+ MB\s+([\d.]+)%',raw)}
    if len(shares)!=4: raise ValueError('placement proof lacks all four NUMA node shares')
    return {'checker_rc':rc,'sample_pid':pid,'max_node':int(maximum.group(1)),'max_node_share_pct':max_pct,
            'shares_pct':shares,'coverage_pct':coverage,'settled':captured.group(5)=='yes',
            'provisional':captured.group(5).startswith('no('),'reason':reason,'rule':'A0 strict <=40%; GPU valid sample, skew recorded'}

def execute(cell,warrant,cell_dir,deadline,stopfile,active=None):
    controller.check_warrant(warrant)
    cell_dir=Path(cell_dir); cell_dir.mkdir(parents=True,exist_ok=False)
    if os.environ.get('FILLER_PREFLIGHT')=='1': raise ValueError('preflight must never run inference')
    if time.time()>=deadline or Path(stopfile).exists() or (active is not None and not active()): raise ValueError('grant/deadline/STOP')
    argv=command(cell,cell_dir/'canonical'); env=os.environ.copy()
    # filler_run15 already owns the grant's CPU region and GPU quiet claim;
    # bench_canonical must not acquire a conflicting nested region lock.
    if os.environ.get('FILLER_NEEDGPU')!='1' or not os.environ.get('FILLER_CPUS'):
        raise ValueError('native executor requires the admitted rowflow CPU+GPU claim')
    env['CANONICAL_SKIP_REGION_LOCK']='1'
    for key in tuple(env):
        if key.startswith('GGML_'): env.pop(key)
    if cell['arm']=='A1-disabled': env['GGML_OP_OFFLOAD_MIN_BATCH']='2147483647'
    env['LD_LIBRARY_PATH']=str((CPU if cell['arm']=='A0' else GPU))+':/usr/lib/llvm-20/lib'
    identity={'cell':cell,'manifest_sha256':warrant['manifest_sha256'],'argv':argv,'env':{k:env.get(k) for k in ('LD_LIBRARY_PATH','GGML_OP_OFFLOAD_MIN_BATCH','GGML_IQK','OMP_PROC_BIND','OMP_PLACES','OMP_WAIT_POLICY','OMP_DYNAMIC')},'created_at':time.time()}
    identity['self_sha256']=controller.digest(identity); controller.write(cell_dir/'before-load.json',identity)
    before=gpu_sample(); controller.write(cell_dir/'gpu-before.json',before)
    mon=cpu_monitor(warrant); samples=[]; owned_kfd=[]; gpu=[]; numa=[]; affinity=[]; maps=[]; pidgpu=[]; error=None
    with (cell_dir/'raw.log').open('wb') as raw:
        proc=subprocess.Popen(argv,stdout=raw,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        gpu_stop=threading.Event()
        gpu_thread=threading.Thread(target=sample_gpu_until,args=(gpu_stop,gpu),daemon=True)
        gpu_thread.start()
        try:
            while proc.poll() is None:
                if time.time()>=deadline or Path(stopfile).exists() or (active is not None and not active()): raise TimeoutError('grant/deadline/STOP')
                try:
                    snap=mon.monitor_snapshot(proc.pid,proc.pid)
                    snap,owned=attribute_kfd(snap); samples.append(snap); owned_kfd.append(owned)
                    for pid in snap['target']['members']:
                        try:
                            if Path(f'/proc/{pid}/exe').resolve(strict=True)==Path(argv[argv.index('--binary')+1]).resolve(strict=True):
                                affinity.append(affinity_witness.snapshot(pid,argv[argv.index('--binary')+1]))
                                if cell['arm'] in ('A1','A2'):
                                    pidgpu.append(capture(['rocm-smi','--showpidgpus',str(pid)],timeout=3))
                                try:
                                    role='cpu' if cell['arm']=='A0' else 'gpu'
                                    maps.append(maps_witness.snapshot(pid,argv[argv.index('--binary')+1],warrant['binary_inventory'][role]['libraries'],role=='gpu'))
                                except (OSError,ValueError,KeyError) as exc:
                                    maps.append({'error':repr(exc),'pid':pid})
                        except FileNotFoundError: pass
                        numa.append(capture(['numastat','-p',str(pid)],timeout=3))
                except Exception as e: samples.append({'error':repr(e),'at':time.monotonic()})
                time.sleep(1)
        except BaseException as e:
            error=repr(e)
            if proc.poll() is None:
                os.killpg(proc.pid,signal.SIGTERM)
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired: os.killpg(proc.pid,signal.SIGKILL); proc.wait()
        finally:
            proc.wait()
            gpu_stop.set(); gpu_thread.join(timeout=2)
            if gpu_thread.is_alive(): error='GPU sampler did not stop'
    after=gpu_sample()
    try: kfd_after=mon.kfd_ownership()
    except Exception as exc: kfd_after={'error':repr(exc)}
    for name,value in [('contention.json',samples),('owned-kfd.json',owned_kfd),('kfd-raw.json',mon.pf1_kfd_witnesses),('kfd-after.json',kfd_after),('gpu-during.json',gpu),('gpu-after.json',after),('pidgpu.json',pidgpu),('numastat.json',numa),('affinity.json',affinity),('maps.json',maps)]: controller.write(cell_dir/name,value)
    result={'status':'failed','error':error,'returncode':proc.returncode,'raw_output':str(cell_dir/'raw.log')}
    if error or proc.returncode: return result
    try:
        raw_text=(cell_dir/'raw.log').read_text(errors='replace')
        result['samples_ts']=parse_bench(raw_text,cell)
        result['build_line']=next((f'build: {commit} ({number})' for commit,number in re.findall(r'^\s*build:\s*([0-9a-f]+)\s*\((\d+)\)\s*$',raw_text,re.MULTILINE) if HEAD.startswith(commit)),None)
        result['placement']=placement_proof(cell_dir/'canonical',cell['arm'])
        if any('error' in x for x in samples) or before.get('rc')!=0 or after.get('rc')!=0: raise ValueError('monitor failure')
        validate_gpu_cadence(gpu)
        if not affinity: raise ValueError('no in-window benchmark thread affinity witness')
        if not any(x.get('verdict')=='pass' for x in maps): raise ValueError('no mapped-library witness')
        mapped_pids={x['pid'] for x in maps if x.get('verdict')=='pass'}
        if not any(x.get('rc')==0 and x.get('argv')==['numastat','-p',str(pid)] for x in numa for pid in mapped_pids): raise ValueError('no in-window benchmark NUMA witness')
        if len(samples)<2: raise ValueError('insufficient contention observations')
        if 'error' in kfd_after or kfd_after.get('users'): raise ValueError('KFD still owned after cleanup')
        if total_vram(after)>total_vram(before)+1048576: raise ValueError('VRAM did not settle after cleanup')
        for snap in samples:
            if any(snap['contamination'].values()) or snap['target']['ownership_changed']:
                raise ValueError('foreign process contamination or unstable ownership')
        residency=gpu_residency(gpu,owned_kfd,maps,pidgpu) if cell['arm'] in ('A1','A2') else None
        if cell['arm']=='A0' and cell['L']==2048:
            validation=mon.validate_monitor_samples(samples); controller.write(cell_dir/'contention-verdict.json',validation)
        if re.search(r'(?i)\b(out of memory|op.offload fallback|failed to offload)\b',(cell_dir/'raw.log').read_text(errors='replace')):
            raise ValueError('OOM or offload fallback warning')
        result['status']='ok'
        result['evidence']={'raw_output':str(cell_dir/'raw.log'),'argv':argv,'env':identity['env'],
                            'numastat':str(cell_dir/'numastat.json'),'proc_stat':str(cell_dir/'contention.json'),
                            'kfd':str(cell_dir/'kfd-raw.json'),'vram':str(cell_dir/'gpu-during.json'),
                            'build_line':result['build_line'],'nonzero_vram_during':residency,'placement':result['placement'],
                            'load_threads':effective_load_threads(),'mmap':0,
                            'maps':str(cell_dir/'maps.json'),'protocol_id':'',
                            'classification':'observation; P-GPU-1 fresh-server requirement not established'}
        return result
    except Exception as e: result['error']=repr(e); return result
