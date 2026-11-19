import hashlib,json,os,pathlib,subprocess,sys,tempfile
D=pathlib.Path('/mnt/raid0/llm/tmp/speculative-decoding-mtp/cafe4-mtp-rollback-v3'); S=pathlib.Path('/mnt/raid0/llm/tmp/speculative-decoding-mtp/cafe4-mtp-rollback-source')
PATCH='351a431702613a5cad8d165c6959dbcde12a928963b8833bfa4668abb743e4dd'
def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
CANDIDATE='d0b766c3a3dfe86fad1a678d387520fb9b88d456a710a0e8ea776bc1352fc7f2'
BRIDGE='9688a97c3ad30e5aa008650d29a7b4d463109220b7dc48a136f9324aa2cf3919'
def source():
 assert digest(D/"candidate.cpp")==CANDIDATE and digest(D/"mtp_draft_bridge.hpp")==BRIDGE
 assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()=='ffc1bac82eeca6f9099e1ccd9ba49703c460a115'
 assert hashlib.sha256(subprocess.check_output(['git','-C',str(S),'diff','--binary','--abbrev=10','HEAD'])).hexdigest()==PATCH
 assert not subprocess.check_output(['git','-C',str(S),'ls-files','--others','--exclude-standard'])
def validate(d):
 source(); assert d["source_commit"]=="ffc1bac82eeca6f9099e1ccd9ba49703c460a115" and d["patch_sha256"]==PATCH and d["candidate_sha256"]==CANDIDATE and d["bridge_sha256"]==BRIDGE; r=pathlib.Path(d['run']).resolve(strict=True); assert r.parent==(D/'runs').resolve()
 for p,h in d['files'].items():
  q=pathlib.Path(p).resolve(strict=True); assert q.is_relative_to(r) and digest(q)==h
 p=r/('candidate.o' if d['mode']=='smoke' else 'build/bin/cafe4-mtp-rollback')
 assert b'CAFE4_MTP_ROLLBACK' in subprocess.check_output(['strings',str(p)])
 assert b'CAFE4_MTP_LOAD_ENABLED' in subprocess.check_output(['strings',str(p)])
 if d['mode']=='build':
  l=(r/'linkage.log').read_text(); assert 'not found' not in l and str(r/'build/bin') in l and 'llama-common' in l
 else: assert d['mode']=='smoke'
def write(mode,run,out):
 source(); r=pathlib.Path(run); files=[r/'candidate.o'] if mode=='smoke' else [r/'build/bin/cafe4-mtp-rollback',r/'build/CMakeCache.txt',r/'configure.log',r/'build.log',r/'linkage.log',*list((r/'build/bin').glob('libllama*.so*')),*list((r/'build/bin').glob('libggml*.so*'))]
 assert files and all(x.exists() for x in files)
 d={'schema':'epyc.cafe4.mtp.build.v1','mode':mode,'run':str(r.resolve()),'source_commit':'ffc1bac82eeca6f9099e1ccd9ba49703c460a115','patch_sha256':PATCH,'candidate_sha256':digest(D/'candidate.cpp'),'bridge_sha256':digest(D/'mtp_draft_bridge.hpp'),'files':{str(x.resolve()):digest(x) for x in files},'scope':'build only; target-bound real-MTP rollback and fault comparison source, no native result'}
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
