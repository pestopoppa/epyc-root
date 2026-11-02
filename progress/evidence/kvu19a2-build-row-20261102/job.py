#!/usr/bin/env python3
"""Build a sealed KVU-19a-2 source pair; smoke performs configuration only."""
import hashlib,json,os,signal,stat,subprocess,sys,tempfile,time
from pathlib import Path
import source_guard
D=Path('/mnt/raid0/llm/tmp/kvu19a2-build-row-20261102')
SOURCE_RECEIPT_PIN='8700981959dc11332792c064647e3227f20de12b65603f0fed35446426afc141'
OUT=D/'output'
COMMIT='a0d0ae238e714aaab04e973ef4b5a4b7c9917744'
TREE='507ee1a6b1c5f09d56a337232f99eb82c1aeea55'
TILES={'base':'878a3640f685e68c6c3d3102c331c43054bfb0bce81f68c3224ad271b8d9d844','candidate':'3f79373e68603691630c7dc38703411456cdf5fa12348d07812323568cdb1e82'}
TILE='ggml/src/ggml-cuda/fattn-tile.cuh'
def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def check(src):
 for p in (D,src/'base',src/'candidate'):
  s=p.lstat()
  if not stat.S_ISDIR(s.st_mode) or s.st_uid!=os.geteuid() or s.st_mode & 0o022:raise ValueError('source ancestry ownership or permissions mismatch')
 for arm in TILES:
  if digest(src/arm/TILE)!=TILES[arm]:raise ValueError('tile identity mismatch')
 subprocess.run(['sha256sum','-c','--quiet',str(D/'toolchain.sha256')],check=True)
def source_metadata_digest(root):
 entries=[]
 def fail(error):raise error
 for parent,dirs,files in os.walk(root,followlinks=False,onerror=fail):
  for name in sorted(dirs+files):
   path=Path(parent)/name;st=path.lstat()
   if not (stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode)):raise ValueError('special source entry')
   entries.append((str(path.relative_to(root)),st.st_dev,st.st_ino,st.st_mode,st.st_uid,st.st_size,st.st_mtime_ns,st.st_ctime_ns))
 entries.sort()
 return hashlib.sha256(json.dumps(entries,separators=(',',':')).encode()).hexdigest()

def verify_cmake_source(build, source, arm):
 cache=build/'CMakeCache.txt'
 text=cache.read_text()
 expected=f'CMAKE_HOME_DIRECTORY:INTERNAL={source}'
 if text.splitlines().count(expected)!=1:raise ValueError('CMake canonicalized or changed the anchored source path')
 mutable=str(D/'source-sealed-20261102'/arm).encode()
 for path in build.rglob('*'):
  if path.is_file() and (path.name in ('Makefile','build.ninja') or path.suffix in ('.cmake','.make')):
   if mutable in path.read_bytes():raise ValueError('generated build metadata contains mutable source path')
 return cache

def publish(path,data):
 path=Path(path)
 if path.exists() or path.is_symlink():raise ValueError('result exists')
 fd,tmp=tempfile.mkstemp(prefix='.native-',dir=path.parent)
 try:
  with os.fdopen(fd,'w') as f:json.dump(data,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
  os.link(tmp,path)
 finally:os.unlink(tmp)
def main():
 if os.environ.get('FILLER_ID')!='handoff-kvu-kvu19a2-build-20261102':raise ValueError('wrong grant identity')
 dry=os.environ.get('FILLER_DRYRUN')=='1'
 if os.environ.get('FILLER_DRYRUN') not in ('0','1'):raise ValueError('invalid mode')
 result=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if dry else OUT/'RESULT.json'
 if dry:
  root=Path(os.environ['FILLER_DRYRUN_DIR']).resolve();parent=result.parent.resolve()
  if not parent.is_relative_to(root/'native-attempts'):raise ValueError('invalid native path')
 if result.exists() or result.is_symlink():raise ValueError('result exists')
 deadline=int(os.environ['FILLER_DEADLINE'])-30
 def ready():
  if time.time()>=deadline or Path(os.environ['FILLER_STOPFILE']).exists():raise RuntimeError('stop or deadline')
 ready();source_fd=source_guard.open_sealed_source(D,SOURCE_RECEIPT_PIN)
 try:
  return run_build(dry,result,deadline,ready,source_fd)
 finally:os.close(source_fd)
def run_build(dry,result,deadline,ready,source_fd):
 src=source_guard.proc_path(source_fd)
 check(src);metadata_before=source_metadata_digest(src)
 run=Path(tempfile.mkdtemp(prefix='smoke-' if dry else 'build-',dir=OUT));os.chmod(run,0o700)
 env={'PATH':'/opt/rocm/bin:/usr/bin:/bin','ROCM_PATH':'/opt/rocm','HIP_PATH':'/opt/rocm','CXX':'/usr/bin/g++','CC':'/usr/bin/gcc','HIPCXX':'/opt/rocm/llvm/bin/clang++'}
 threads=int(os.environ['FILLER_THREADS']); outputs={}
 for arm in ('base','candidate'):
  ready(); build=run/arm;build.mkdir()
  cmd=['/usr/bin/cmake','-S',str(src/arm),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DGGML_HIP=ON','-DAMDGPU_TARGETS=gfx90a','-DLLAMA_BUILD_TESTS=ON','-DLLAMA_BUILD_SERVER=OFF','-DLLAMA_BUILD_TOOLS=OFF']
  with (run/(arm+'-configure.log')).open('xb') as f:subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
  ready(); cache=verify_cmake_source(build,src/arm,arm)
  if 'GGML_HIP:BOOL=ON' not in cache.read_text():raise ValueError('HIP configuration absent')
  if not dry:
   with (run/(arm+'-build.log')).open('xb') as f:subprocess.run(['/usr/bin/cmake','--build',str(build),'--target','test-backend-ops','--parallel',str(threads)],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
   ready(); exe=build/'bin/test-backend-ops'; libs=list((build/'bin').glob('libggml-hip.so*'))
   if not exe.is_file() or not libs:raise ValueError('expected test binary and HIP library absent')
   outputs[arm]={'test_sha256':digest(exe),'hip_sha256':digest(libs[0]),'binary':str(exe),'hip_library':str(libs[0])}
  outputs.setdefault(arm,{})['cmake_cache_sha256']=digest(cache)
 check(src);ready();metadata_after=source_metadata_digest(src)
 if metadata_after!=metadata_before:raise ValueError('source metadata changed during build')
 publish(result,{'schema':'kvu19a2.build-pair.v1','mode':'qualification' if dry else 'full','status':'configured' if dry else 'built','source_commit':COMMIT,'source_tree':TREE,'tile_sha256':TILES,'sealed_source_receipt_sha256':SOURCE_RECEIPT_PIN,'source_files_sha256':json.loads((D/'sealed-source-receipt.json').read_text())['files_sha256'],'source_custody':'node-owned snapshot; same-UID mutation remains possible','source_metadata_sha256_before':metadata_before,'source_metadata_sha256_after':metadata_after,'source_pair_receipt_sha256':digest(D/'source-pair.json'),'toolchain_catalog_sha256':digest(D/'toolchain.sha256'),'outputs':outputs,'run_dir':str(run),'scope':'build only; no GPU test or nondeterminism result'})
 return 0
if __name__=='__main__':
 try:sys.exit(main())
 except Exception as e:print('build refused:',e,file=sys.stderr);sys.exit(75)
