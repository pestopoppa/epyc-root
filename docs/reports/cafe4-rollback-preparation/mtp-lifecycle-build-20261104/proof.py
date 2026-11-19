import hashlib,json,os,pathlib,subprocess,sys,tempfile
D=pathlib.Path('/mnt/raid0/llm/tmp/speculative-decoding-mtp/cafe4-mtp-build-r2'); S=pathlib.Path('/mnt/raid0/llm/tmp/speculative-decoding-mtp/cafe4-mtp-build-source')
PATCH='757556450bfdce0b1c0321de12c21ad5ea26edfe2a2dcb80ca0bba2ea7c95dec'
def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
def source():
 assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()=='ffc1bac82eeca6f9099e1ccd9ba49703c460a115'
 assert hashlib.sha256(subprocess.check_output(['git','-C',str(S),'diff','--binary','--abbrev=10','HEAD'])).hexdigest()==PATCH
 assert not subprocess.check_output(['git','-C',str(S),'ls-files','--others','--exclude-standard'])
def validate(d):
 source(); r=pathlib.Path(d['run']).resolve(strict=True); assert r.parent==(D/'runs').resolve()
 for p,h in d['files'].items():
  q=pathlib.Path(p).resolve(strict=True); assert q.is_relative_to(r) and digest(q)==h
 p=r/('candidate.o' if d['mode']=='smoke' else 'build/bin/cafe4-mtp-lifecycle')
 assert b'MTP_LIFECYCLE' in subprocess.check_output(['strings',str(p)])
 if d['mode']=='build':
  l=(r/'linkage.log').read_text(); assert 'not found' not in l and str(r/'build/bin') in l and 'llama-common' in l
 else: assert d['mode']=='smoke'
def write(mode,run,out):
 source(); r=pathlib.Path(run); files=[r/'candidate.o'] if mode=='smoke' else [r/'build/bin/cafe4-mtp-lifecycle',r/'build/CMakeCache.txt',r/'configure.log',r/'build.log',r/'linkage.log',*list((r/'build/bin').glob('libllama*.so*')),*list((r/'build/bin').glob('libggml*.so*'))]
 assert files and all(x.exists() for x in files)
 d={'schema':'epyc.cafe4.mtp.build.v1','mode':mode,'run':str(r.resolve()),'source_commit':'ffc1bac82eeca6f9099e1ccd9ba49703c460a115','patch_sha256':PATCH,'candidate_sha256':digest(D/'candidate.cpp'),'bridge_sha256':digest(D/'mtp_draft_bridge.hpp'),'files':{str(x.resolve()):digest(x) for x in files},'scope':'build only; not native MTP, rollback, or fault evidence'}
 validate(d); p=pathlib.Path(out); p.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(dir=p.parent,prefix='.proof-')
 with os.fdopen(fd,'w') as f: json.dump(d,f,sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno())
 os.replace(tmp,p)
if sys.argv[1]=='predicate':
 try:
  p=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']); assert p.stat().st_mtime >= int(os.environ['FILLER_SMOKE_T0'])
  d=json.loads(p.read_text()); assert d['mode']=='smoke'; validate(d)
 except (AssertionError, OSError, KeyError, ValueError, json.JSONDecodeError): raise SystemExit(1)
 raise SystemExit(0)
if sys.argv[1]=='source': source()
elif sys.argv[1]=='write': write(*sys.argv[2:])
elif sys.argv[1]=='check':
 d=json.loads((D/'RESULT.json').read_text()); assert d['mode']=='build'; validate(d)
