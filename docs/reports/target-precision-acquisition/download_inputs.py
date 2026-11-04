#!/usr/bin/env python3
"""Acquire pinned candidate GGUFs to volatile task-specific tmpfs.

This is model preflight only: no run, admission, equivalence, or causal claim.
Source identity across different converters remains unverified. Uses no user
credentials, rechecks shared-host floors throughout, and records real failures.
"""
import hashlib, json, os, signal, sys, time, urllib.request
from pathlib import Path

SCRATCH=Path('/dev/shm/mtp-target-precision-20261104')
RESULT=Path('/mnt/raid0/llm/tmp/speculative-decoding-mtp/precision-metadata/acquisition-result.json')
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
    if available('/mnt/raid0') < 150*GIB: raise RuntimeError('disk floor below 150 GiB')
    if mem_available() < 250*GIB: raise RuntimeError('host MemAvailable below 250 GiB')
    if available('/dev/shm') < remaining+4*GIB: raise RuntimeError('tmpfs headroom insufficient')

def download_inputs():
    if SCRATCH.exists(): raise RuntimeError('destination already exists; refuse reuse')
    guard(sum(x[2] for x in SOURCES)); SCRATCH.mkdir(mode=0o700)
    completed=[]; partial=None; started=time.time_ns()
    try:
        for index,(name,url,size,expected) in enumerate(SOURCES):
            remaining=sum(x[2] for x in SOURCES[index:]); guard(remaining)
            partial=SCRATCH/(name+'.part'); path=SCRATCH/name; h=hashlib.sha256(); written=0
            req=urllib.request.Request(url,headers={'User-Agent':'epyc-precision-preflight/1'})
            with urllib.request.urlopen(req,timeout=120) as response, open(partial,'xb') as out:
                if response.status!=200 or int(response.headers.get('Content-Length','-1'))!=size: raise RuntimeError('remote length or status mismatch')
                while True:
                    b=response.read(8*1024*1024)
                    if not b: break
                    out.write(b); h.update(b); written+=len(b)
                    if written>size: raise RuntimeError('remote exceeded expected size')
                    # Checks protect unrelated workloads; no shared process is killed.
                    guard(sum(x[2] for x in SOURCES[index+1:]) + size-written)
                out.flush(); os.fsync(out.fileno())
            if written!=size or h.hexdigest()!=expected: raise RuntimeError('byte count or digest mismatch')
            os.replace(partial,path); partial=None
            completed.append({'path':str(path),'size':written,'sha256':expected,'source':url})
        return {'status':'COMPLETE','started_ns':started,'finished_ns':time.time_ns(),'files':completed,
                'limitations':['tmpfs inputs are volatile across reboot; do not consume unless all digests and files remain valid',
                               'different converter Q4/base model revision equivalence not established',
                               'preflight inputs only; no inference or quality claim']}
    except BaseException as exc:
        if partial is not None:
            try: partial.unlink()
            except FileNotFoundError: pass
        return {'status':'FAILED','started_ns':started,'finished_ns':time.time_ns(),'error_type':type(exc).__name__,
                'reason':str(exc) if isinstance(exc,RuntimeError) else 'transfer or I/O failure',
                'files':completed,'limitations':['incomplete volatile inputs; no inference or equivalence claim']}

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
