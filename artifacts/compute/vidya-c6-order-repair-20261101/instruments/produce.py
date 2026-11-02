#!/usr/bin/env python3
"""C6 offline store build producer. No model/test/GPU execution and no CAS."""
from __future__ import annotations
import argparse,ctypes,fcntl,hashlib,json,os,re,shutil,signal,subprocess,sys,time
from pathlib import Path

HERE=Path(__file__).resolve().parent
CHAMPION='c72ec82f5417bb2937310326120f149b665e8400'
CHAMPION_REF='ak/champion/llama-cpp-ffc1bac82eec'
TARGETS=('llama-server', 'llama-bench', 'llama-quantize', 'test-backend-ops', 'test-qwen4exp-fused-rope', 'test-rope', 'test-mmap-evict', 'bench-grammar-sampler', 'test-sampling-greedy-fast', 'test-kv-host-mirror', 'test-server-reorder', 'test-server-chunk-store', 'test-dsa-sparse-attn-oracle', 'test-dsv41-engram-gate', 'test-spec-rng-poskey', 'test-kld-ear', 'test-server-prefill-order', 'test-chunk-kv', 'test-chunk-kv-recompute', 'test-chunk-kv-g3', 'test-chat-parse-truncation', 'test-gdn-state-guard', 'test-fa-rowexact', 'test-moe-fused-upgate', 'test-chat', 'test-rowexact-backend-toggle', 'test-memory-can-shift', 'test-dca', 'test-llama-archs')
STOP=False

def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def command(argv,**kwargs):
    return subprocess.check_output(argv,text=True,env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'},**kwargs).strip()

def source_guard(source,sha):
    if not re.fullmatch('[0-9a-f]{40}',sha):raise ValueError('source SHA must be an immutable full commit ID')
    if sha!=json.loads((HERE/'TARGET-CLOSURE.json').read_text())['head']:
        raise ValueError('source differs from exact reviewed target audit; refresh audit before build')
    def git(*args):return command(['git','-C',str(source),*args])
    if git('rev-parse','HEAD')!=sha:raise ValueError('source HEAD differs from final source SHA')
    if not git('branch','--show-current').startswith('experimental/'):
        raise ValueError('source must be the owned experimental C6 branch')
    if git('status','--porcelain','--untracked-files=all'):raise ValueError('source is not clean')
    if git('rev-parse',CHAMPION_REF)!=CHAMPION:raise ValueError('champion moved; review before building')
    subprocess.run(['git','-C',str(source),'merge-base','--is-ancestor',CHAMPION,sha],check=True)
    if git('diff','--name-only',CHAMPION,sha,'--','tools/ui','scripts/ui-assets.cmake'):
        raise ValueError('C6 UI source differs from C5; pinned UI recipe needs owner review')
    return git('rev-parse','HEAD^{tree}')

def native_identity():
    got={'gcc':command(['/usr/bin/gcc','-dumpfullversion']),
         'cmake':command(['/usr/bin/cmake','--version']).splitlines()[0],
         'rocm':Path('/opt/rocm/.info/version').read_text().strip(),
         'clang':command(['/opt/rocm/lib/llvm/bin/clang++','--version']).splitlines()[0],
         'libc':command(['/usr/bin/getconf','GNU_LIBC_VERSION'])}
    if got['gcc']!='15.2.0' or got['cmake']!='cmake version 3.31.6' or got['rocm']!='6.2.0-66' or \
       '26466ce804ac523b398608f17388eb6d605a3f09' not in got['clang'] or got['libc']!='glibc 2.42':
        raise ValueError('not the original native producer: GCC15.2/CMake3.31.6/ROCm6.2/glibc2.42 required')
    got['uid']=os.getuid();got['gid']=os.getgid()
    if got['uid']!=1000:raise ValueError('producer must run as owner UID1000')
    return got

def mapped_definitions(profile,source,output):
    result={}
    for name,item in profile['definitions'].items():
        if name=='CMAKE_GENERATOR':continue
        value=item['value'].replace(profile['source_root'],str(source)).replace(profile['root'],str(output))
        result[name]={'type':item['type'],'value':value}
    return result

def configure_argv(profile,source,output):
    definitions=mapped_definitions(profile,source,output)
    return ['/usr/bin/cmake','-S',str(source),'-B',str(output),'-G',profile['definitions']['CMAKE_GENERATOR']['value'],
            *[f'-D{name}:{item["type"]}={item["value"]}' for name,item in sorted(definitions.items())]]

def verify_aliases(binaries):
    for alias in binaries.glob('libggml*.so'):
        soname=binaries/(alias.name+'.0');versioned=binaries/(alias.name+'.0.16.0')
        if not alias.is_symlink() or alias.readlink()!=Path(soname.name) or not soname.is_symlink() or soname.readlink()!=Path(versioned.name) or not versioned.is_file() or versioned.is_symlink():
            raise ValueError('noncanonical ggml alias chain: '+str(alias))
    return True

def verify_c5(profile):
    root=Path(profile['root'])
    for name,expected in profile['original_files'].items():
        if digest(root/name)!=expected:raise ValueError(f'C5 baseline artifact changed: {root/name}')
    count=0
    for line in (root/'SHA256SUMS').read_text().splitlines():
        expected,relative=line.split(None,1);relative=relative.strip().lstrip('*')
        path=root/relative
        if not path.exists():path=root/'bin'/relative
        if digest(path)!=expected:raise ValueError(f'C5 manifest mismatch: {path}')
        count+=1
    verify_aliases(root/'bin')
    return count

def stage_ui(profile,output):
    # Existing ui-assets.cmake accepts fresh BUILD/tools/ui/dist without source writes.
    dest=output/'tools/ui/dist';dest.mkdir(parents=True,exist_ok=True)
    for relative,expected in profile['ui_assets'].items():
        src=HERE/'ui'/('gpu' if 'gpu-' in profile['root'] else 'cpu')/relative
        if digest(src)!=expected:raise ValueError('sealed UI input changed')
        target=dest/relative;target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and digest(target)!=expected:raise ValueError('staged UI asset differs')
        # copyfile deliberately stages fresh mtimes; bytes are exactly the sealed C5 assets.
        shutil.copyfile(src,target)
    stamp=output/'tools/ui/.ui-stamp'
    if stamp.exists():raise ValueError('foreign/download UI stamp is not the pinned prebuilt recipe')

class OwnedStep:
    """Sample/stop only this producer's descendants, using captured pidfds/birth IDs."""
    def __init__(self,log,limit_bytes,source_check,stopfile,output):
        if ctypes.CDLL(None,use_errno=True).prctl(36,1,0,0,0):raise OSError('subreaper unavailable')
        self.log=log;self.limit=limit_bytes;self.source_check=source_check;self.stopfile=stopfile;self.output=output
        self.pids={};self.peak=0;self.samples=0;self.witness=[];self.leader=None
    def snapshot(self):
        pending=[os.getpid()];seen=set();rss=0
        while pending:
            pid=pending.pop()
            if pid in seen:continue
            seen.add(pid);p=Path('/proc')/str(pid)
            try:
                fields=(p/'stat').read_text().rsplit(') ',1)[1].split();uid=p.stat().st_uid;birth=int(fields[19])
                if uid!=os.getuid():raise RuntimeError('foreign UID in owned descendants')
                rss+=int((p/'statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
                for task in (p/'task').iterdir():
                    try:pending += [int(v) for v in (task/'children').read_text().split()]
                    except FileNotFoundError:pass
                if pid!=os.getpid() and pid not in self.pids:
                    fd=os.pidfd_open(pid)
                    self.pids[pid]=(fd,birth)
                    after=(p/'stat').read_text().rsplit(') ',1)[1].split()
                    if int(after[19])!=birth:raise RuntimeError('PID identity changed')
                    argv=(p/'cmdline').read_bytes().split(b'\0');argv=[v.decode(errors='replace') for v in argv if v]
                    self.pids[pid]=(fd,birth)
                    if argv and Path(argv[0]).name in {'clang++','clang-18','cc1plus','cc1','as','gcc','g++','gcc-15','g++-15','cc','c++','collect2','ld','ld.lld'}:
                        self.witness.append({'pid':pid,'birth':birth,'argv':argv,'cwd':str((p/'cwd').readlink())})
            except (FileNotFoundError,ProcessLookupError):continue
        self.peak=max(self.peak,rss);self.samples+=1
        return rss,seen-{os.getpid()}
    def alive(self):
        _,seen=self.snapshot();result=[]
        for pid in seen:
            try:
                fields=(Path('/proc')/str(pid)/'stat').read_text().rsplit(') ',1)[1].split()
                if fields[0]!='Z':result.append(pid)
                elif pid!=self.leader:
                    try:os.waitpid(pid,os.WNOHANG)
                    except ChildProcessError:pass
            except FileNotFoundError:pass
        return result
    def drain(self):
        for sig,seconds in [(signal.SIGTERM,3),(signal.SIGKILL,7)]:
            end=time.monotonic()+seconds
            while True:
                live=self.alive()
                if not live:return True
                for pid in live:
                    if pid not in self.pids:raise RuntimeError('uncaptured owned PID')
                    try:signal.pidfd_send_signal(self.pids[pid][0],sig)
                    except ProcessLookupError:pass
                if time.monotonic()>=end:break
                time.sleep(.05)
        return not self.alive()
    def run(self,argv,cwd,env,seconds,cutoff=False):
        started=time.monotonic();reason=None;next_guard=started
        with self.log.open('ab') as log:
            log.write((json.dumps({'argv':argv,'cwd':str(cwd),'started':time.time()})+'\n').encode());log.flush()
            child=subprocess.Popen(argv,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            self.leader=child.pid
            try:
                while True:
                    rss,_=self.snapshot();now=time.monotonic()
                    if rss>self.limit-(1<<30):reason='sampled_ram_cap'
                    if STOP or self.stopfile and self.stopfile.exists():reason='stop_requested'
                    if now-started>=seconds:reason='forced_cutoff' if cutoff else 'window_cutoff'
                    if now>=next_guard:
                        self.source_check();next_guard=now+2
                        if shutil.disk_usage(cwd).free<150*1024**3:reason='disk_floor'
                    if reason or child.poll() is not None:break
                    time.sleep(.05 if cutoff else .1)
            except BaseException as exc:
                reason='boundary_refused: '+str(exc)
            finally:
                interrupted_pids=set(self.alive()) if reason else set()
                known_before_drain=set(self.pids)
                drained=self.drain();child.wait(timeout=10)
                interrupted_pids.update(set(self.pids)-known_before_drain)
                self.identities=[{'pid':pid,'birth':birth} for pid,(_,birth) in self.pids.items()]
                for fd,_ in self.pids.values():os.close(fd)
                self.pids={}
            row={'argv':argv,'rc':child.returncode,'reason':reason,'elapsed_s':time.monotonic()-started,
                 'sampled_peak_tree_rss_bytes':self.peak,'samples':self.samples,'children_drained':drained,
                 'compiler_witness':self.witness,'interrupted_compilers':[v for v in self.witness if v['pid'] in interrupted_pids],
                 'owned_pid_births':self.identities}
            if not drained:raise RuntimeError('owned children survived; no completion claim')
            return row

def discard_interrupted_outputs(row,output):
    removed=[]
    for item in row['interrupted_compilers']:
        argv=item['argv'];names=[]
        for i,arg in enumerate(argv[:-1]):
            if arg in ('-o','-MF'):names.append(argv[i+1])
        for name in names:
            path=Path(name)
            if not path.is_absolute():path=Path(item['cwd'])/path
            path=path.resolve()
            if not path.is_relative_to(output.resolve()):
                raise ValueError('compiler output outside owned build: '+str(path))
            if path.is_file():path.unlink();removed.append(str(path))
    return sorted(set(removed))

def audit_cache(profile,source,output):
    actual={}
    for line in (output/'CMakeCache.txt').read_text().splitlines():
        if line and not line.startswith(('#','//')) and '=' in line:
            left,value=line.split('=',1);actual[left.split(':',1)[0]]=value
    errors=[]
    for name,item in mapped_definitions(profile,source,output).items():
        if actual.get(name)!=item['value']:errors.append({'key':name,'expected':item['value'],'actual':actual.get(name)})
    if errors:raise ValueError('configured recipe mismatch: '+json.dumps(errors))
    return actual

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--source-sha',required=True)
    ap.add_argument('--kind',choices=['cpu','gpu'],required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--mode',choices=['plan','configure','smoke','cutoff','build','seal'],default='plan')
    ap.add_argument('--allocation',choices=['r6','calendar'],default='r6');ap.add_argument('--jobs',type=int,default=2)
    ap.add_argument('--seconds',type=int,default=850);ap.add_argument('--memory-gib',type=int,default=8);ap.add_argument('--resume',action='store_true')
    args=ap.parse_args();source=args.source.resolve();output=args.output.resolve()
    if args.jobs<1 or args.seconds<1 or args.memory_gib<2:raise ValueError('positive jobs/deadline and >=2GiB required')
    if args.allocation=='r6' and (args.jobs>2 or args.seconds>850 or args.memory_gib>8 or len(os.sched_getaffinity(0))!=2):
        raise ValueError('R6 requires2 admitted CPUs, jobs<=2, <=850s and <=8GiB')
    if args.allocation=='calendar':
        if not all(os.environ.get(k) for k in ['FILLER_ID','FILLER_CPUS','FILLER_DEADLINE']):raise ValueError('canonical calendar allocation required')
        if args.jobs>min(8,len(os.sched_getaffinity(0))) or args.memory_gib>32:raise ValueError('calendar build caps exceeded')
        args.seconds=min(args.seconds,int(float(os.environ['FILLER_DEADLINE'])-time.time()-20))
        if args.seconds<1:raise ValueError('no remaining calendar budget')
    tree=source_guard(source,args.source_sha);native=native_identity();profiles=json.loads((HERE/'C5-RECIPES.json').read_text());profile=profiles[args.kind]
    baseline_files=verify_c5(profile)
    if output==Path(profile['root']).resolve() or output.name.startswith(('cpu-20260921','gpu-20260921')):raise ValueError('frozen baseline output forbidden')
    allowed=(Path('/mnt/raid0/llm/kernels/builds').resolve(),(HERE/'probes').resolve())
    if not any(output.is_relative_to(root) for root in allowed) or args.source_sha[:9] not in output.name or not output.name.startswith(args.kind+'-'):
        raise ValueError('output must be an owned C6 store/probe named by kind and immutable source')
    identity={'schema':'c6.offline_store_build.v1','source':str(source),'source_sha':args.source_sha,'source_tree':tree,
              'champion_expected':CHAMPION,'kind':args.kind,'output':str(output),'targets':list(TARGETS),
              'native':native,'configure_argv':configure_argv(profile,source,output),'C5_files_verified':baseline_files}
    if args.mode=='plan':print(json.dumps(identity,indent=2));return 0
    if shutil.disk_usage(output.parent if output.parent.exists() else HERE).free < (150+16)*1024**3:raise ValueError('150GiB floor plus16GiB output reservation unavailable')
    output.mkdir(parents=True,exist_ok=True)
    with (output/'.c6-build.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        pin=output/'BUILD-IDENTITY.json'
        if pin.exists():
            if not args.resume or json.loads(pin.read_text())!=identity:raise ValueError('resume requires identical source/recipe/native identity')
        else:pin.write_text(json.dumps(identity,indent=2)+'\n')
        active=output/'STEP-ACTIVE.json'
        if active.exists():raise ValueError('previous step did not drain/receipt; inspect owned outputs before resume')
        env={**os.environ,'PATH':'/usr/bin:/bin','LD_LIBRARY_PATH':'','OMP_NUM_THREADS':'1',
             'HIP_VISIBLE_DEVICES':'','ROCR_VISIBLE_DEVICES':'','CUDA_VISIBLE_DEVICES':'',
             'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(output/'tmp')}
        for k in ['CC','CXX','HIPCC','CFLAGS','CXXFLAGS','HIPFLAGS','CPATH','CPLUS_INCLUDE_PATH','C_INCLUDE_PATH','LIBRARY_PATH','LD_PRELOAD','CMAKE_PREFIX_PATH','LLAMA_ZOS2','LLAMA_NO_MMAP_PREFETCH','LLAMA_MMAP_EVICT_LAST_USE','LLAMA_ARG_PREFILL_ORDER','GGML_BACKEND_PATH']:env.pop(k,None)
        if args.mode in ['smoke','cutoff']:env['CCACHE_DISABLE']='1'
        (output/'tmp').mkdir(exist_ok=True);started=time.monotonic();steps=[]
        stopfile=Path(os.environ['FILLER_STOPFILE']) if os.environ.get('FILLER_STOPFILE') else None
        def check_source():
            source_guard(source,args.source_sha)
            if args.allocation=='r6':
                sys.path.insert(0,'/mnt/raid0/llm/tmp/refactor-01a16fc3/r24-same-code-tripwire-20261030')
                import smoke_admission
                smoke_admission.check(os.sched_getaffinity(0))
        def run(argv,*,cutoff=False):
            remaining=args.seconds-(time.monotonic()-started)
            if remaining<=15:raise TimeoutError('batch budget exhausted before next step')
            active.write_text(json.dumps({'argv':argv,'source_sha':args.source_sha,'started':time.time()})+'\n')
            owner=OwnedStep(output/'BUILD.log',args.memory_gib*1024**3,check_source,stopfile,output)
            row=owner.run(argv,output,env,min(.7 if cutoff else remaining-10,remaining-10),cutoff=cutoff);steps.append(row)
            if row['reason'] or row['rc']:row['discarded_interrupted_outputs']=discard_interrupted_outputs(row,output)
            (output/'LAST-DRAINED-STEP.json').write_text(json.dumps(row,indent=2)+'\n');active.unlink()
            return row
        result={'source_sha':args.source_sha,'kind':args.kind,'mode':args.mode,'status':'STARTED','steps':steps}
        result_path=output/(args.mode+'-result.json');result_path.write_text(json.dumps(result,indent=2)+'\n')
        try:
            if not (output/'CMakeCache.txt').exists():
                stage_ui(profile,output);row=run(identity['configure_argv'])
                if row['reason'] or row['rc']:result['status']='PARTIAL' if row['reason'] else 'FAILED';return 75 if row['reason'] else row['rc']
            audit_cache(profile,source,output)
            if args.mode=='configure':result['status']='COMPLETE_CONFIGURE';return 0
            if args.mode in ['smoke','cutoff']:
                rel='ggml/src/CMakeFiles/ggml-base.dir/gguf.cpp.o' if args.kind=='cpu' else 'ggml/src/ggml-hip/CMakeFiles/ggml-hip.dir/__/ggml-cuda/acc.cu.o'
                makefile=str(Path(rel).parent/'build.make') if args.kind=='cpu' else 'ggml/src/ggml-hip/CMakeFiles/ggml-hip.dir/build.make'
                if (output/rel).exists():raise ValueError('smoke/cutoff needs a fresh probe object; preserve existing output and choose another probe')
                row=run(['/usr/bin/gmake','-f',makefile,rel,'-j1'],cutoff=args.mode=='cutoff')
                if args.mode=='cutoff':
                    result['status']='PARTIAL';result['cutoff_qualified']=row['reason']=='forced_cutoff' and bool(row['compiler_witness']) and row['children_drained'];return 75
                if row['reason'] or row['rc']:result['status']='PARTIAL' if row['reason'] else 'FAILED';return 75 if row['reason'] else row['rc']
                obj=output/rel
                if not obj.is_file() or obj.stat().st_size<64:raise ValueError('real compile object missing')
                result['object']={'path':str(obj),'size':obj.stat().st_size,'sha256':digest(obj)}
                if args.kind=='gpu' and '.hip_fatbin' not in command(['/usr/bin/readelf','-S',str(obj)]):raise ValueError('HIP object lacks device container')
                result['status']='COMPLETE_SMOKE';return 0
            if args.mode=='build':
                row=run(['/usr/bin/cmake','--build',str(output),'--target',*TARGETS,'--parallel',str(args.jobs)])
                if row['reason'] or row['rc']:result['status']='PARTIAL' if row['reason'] else 'FAILED';return 75 if row['reason'] else row['rc']
            binaries=output/'bin'
            for target in TARGETS:
                if not (binaries/target).is_file() or (binaries/target).stat().st_size<64:raise ValueError('missing required build target: '+target)
            verify_aliases(binaries)
            lines=[f'{digest(p)}  bin/{p.name}' for p in sorted(binaries.iterdir()) if p.is_file() and not p.is_symlink()]
            (output/'SHA256SUMS').write_text('\n'.join(lines)+'\n')
            result['status']='COMPLETE_BUILD_ONLY';result['sha256sums']=digest(output/'SHA256SUMS');result['GPU_execution']=False;return 0
        except BaseException as exc:
            result['status']='REFUSED';result['error']=str(exc);raise
        finally:
            result['elapsed_s']=time.monotonic()-started;result_path.write_text(json.dumps(result,indent=2)+'\n');check_source()

def interrupted(_sig,_frame):
    global STOP
    STOP=True

if __name__=='__main__':
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:sys.exit(main())
    except Exception as exc:print(f'C6_BUILD_REFUSED: {exc}',file=sys.stderr);sys.exit(2)
