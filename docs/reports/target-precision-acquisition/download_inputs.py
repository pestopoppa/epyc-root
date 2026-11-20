#!/usr/bin/env python3
"""Acquire pinned candidate GGUFs to durable task-specific storage.

This is model preflight only: no run, admission, equivalence, or causal claim.
Source identity across different converters remains unverified. Uses no user
credentials, rechecks shared-host floors throughout, and records real failures.
"""
import hashlib, json, os, signal, sys, time, urllib.request
from pathlib import Path

SCRATCH=Path('/mnt/raid0/llm/tmp/df2/target-precision-inputs')
RESULT=Path('/mnt/raid0/llm/tmp/df2/target-precision-acquisition/result.json')
GIB=1024**3
SOURCES=(
 ('Qwen3.8-27B-BF16-00001-of-00002.gguf','https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/resolve/4ca720788d1e01f1bff70c033e0d0028fd02e502/BF16/Qwen3.8-27B-BF16-00001-of-00002.gguf',49986159616,'b9966e82b7a4d87028b5eae061d578ee826305ebf8baea5bfc6e09bad0ba191f'),
 ('Qwen3.8-27B-BF16-00002-of-00002.gguf','https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/resolve/4ca720788d1e01f1bff70c033e0d0028fd02e502/BF16/Qwen3.8-27B-BF16-00002-of-00002.gguf',4671576000,'92e3943c4f9bd6292a7bef82369f65fed9bfed088b9df0fb2fa2ce17c9edfa02'),
 ('Qwen3.8-27B-Q4_K_M.gguf','https://huggingface.co/ggml-org/Qwen3.8-27B-GGUF/resolve/cc54a8a3955ee1a099011952d0ef2eab24a7eab3/Qwen3.8-27B-Q4_K_M.gguf',18973870528,'c600de0300ae8a0eb3a6c0b8b5561b8b96f16bd2c863c2a66c42de29d391a747'),
)

def mem_available():
    with open('/proc/meminfo') as f:
        for line in f:
            if line.startswith('MemAvailable:'): return int(line.split()[1])*1024
    raise RuntimeError('missing MemAvailable')

def available(path):
    v=os.statvfs(path); return v.f_bavail*v.f_frsize

def guard(remaining):
    if available('/mnt/raid0') < 150*GIB+remaining: raise RuntimeError('remaining transfer would breach 150 GiB disk floor')
    if mem_available() < 250*GIB: raise RuntimeError('host MemAvailable below 250 GiB')

def download_inputs():
    # Only pinned filenames belong to this acquisition; never overwrite foreign data.
    allowed={n+s for n,_,_,_ in SOURCES for s in ('', '.part')}
    SCRATCH.mkdir(mode=0o700,parents=True,exist_ok=True)
    if any(p.name not in allowed or p.is_symlink() or not p.is_file() for p in SCRATCH.iterdir()):
        raise RuntimeError('foreign destination contents; refuse reuse')
    completed=[]; partial=None; started=time.time_ns(); retained=[]
    try:
        for index,(name,url,size,expected) in enumerate(SOURCES):
            partial=SCRATCH/(name+'.part'); path=SCRATCH/name
            if path.exists():
                with path.open('rb') as f: actual=hashlib.file_digest(f,'sha256').hexdigest()
                if path.stat().st_size!=size or actual!=expected:
                    raise RuntimeError('retained completed file fails pinned identity')
                if partial.exists(): raise RuntimeError('ambiguous completed and partial files')
                completed.append({'path':str(path),'size':size,'sha256':expected,'source':url})
                partial=None
                continue
            h=hashlib.sha256(); written=0
            if partial.exists():
                if partial.stat().st_size>size: raise RuntimeError('partial exceeds pinned size')
                with partial.open('rb') as f:
                    while b:=f.read(8*1024*1024): h.update(b); written+=len(b)
            remaining=sum(x[2] for x in SOURCES[index+1:]) + size-written
            guard(remaining)
            if written<size:
                headers={'User-Agent':'epyc-precision-preflight/2'}
                if written: headers['Range']=f'bytes={written}-'
                req=urllib.request.Request(url,headers=headers)
                with urllib.request.urlopen(req,timeout=120) as response:
                    length=int(response.headers.get('Content-Length','-1'))
                    if written:
                        expected_range=f'bytes {written}-{size-1}/{size}'
                        if response.status!=206 or response.headers.get('Content-Range')!=expected_range or length!=size-written:
                            raise RuntimeError('remote resume range or length mismatch')
                    elif response.status!=200 or length!=size:
                        raise RuntimeError('remote length or status mismatch')
                    with partial.open('ab' if written else 'xb') as out:
                        while True:
                            b=response.read(8*1024*1024)
                            if not b: break
                            if written+len(b)>size: raise RuntimeError('remote exceeded expected size')
                            out.write(b); h.update(b); written+=len(b)
                            guard(sum(x[2] for x in SOURCES[index+1:]) + size-written)
                        out.flush(); os.fsync(out.fileno())
            if written!=size: raise RuntimeError('incomplete transfer; partial retained')
            if h.hexdigest()!=expected:
                partial.unlink(); partial=None
                raise RuntimeError('pinned digest mismatch; corrupt partial removed')
            os.replace(partial,path); partial=None
            completed.append({'path':str(path),'size':written,'sha256':expected,'source':url})
        return {'status':'COMPLETE','started_ns':started,'finished_ns':time.time_ns(),'files':completed,
                'limitations':['durable task inputs; do not consume unless all digests and files remain valid',
                               'different converter Q4/base model revision equivalence not established',
                               'preflight inputs only; no inference or quality claim']}
    except BaseException as exc:
        for name,_,_,_ in SOURCES:
            p=SCRATCH/(name+'.part')
            if p.exists(): retained.append({'path':str(p),'size':p.stat().st_size,'verified':False})
        return {'status':'FAILED','started_ns':started,'finished_ns':time.time_ns(),'error_type':type(exc).__name__,
                'reason':str(exc) if isinstance(exc,RuntimeError) else 'transfer or I/O failure',
                'files':completed,'partials':retained,
                'limitations':['incomplete inputs; retained partials are unverified; no inference or equivalence claim']}

def main():
    def interrupted(signum, frame):
        raise RuntimeError('transfer interrupted by signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted); signal.signal(signal.SIGINT,interrupted)
    try: result=download_inputs()
    except BaseException as exc:
        result={'status':'FAILED','finished_ns':time.time_ns(),'error_type':type(exc).__name__,
                'reason':str(exc) if isinstance(exc,RuntimeError) else 'preflight failure','files':[]}
    RESULT.parent.mkdir(parents=True,exist_ok=True); temp=RESULT.with_suffix('.tmp')
    with temp.open('w') as f: json.dump(result,f,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(temp,RESULT)
    return 0 if result['status']=='COMPLETE' else 1
if __name__=='__main__': sys.exit(main())
