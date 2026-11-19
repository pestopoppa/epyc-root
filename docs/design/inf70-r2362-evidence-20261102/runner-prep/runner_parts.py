#!/usr/bin/env python3
"""Safety primitives for the private R23-62 runner; not an inference entry point."""
import hashlib, mmap, os, signal, struct, subprocess
from pathlib import Path

KNOBS={'GGML_SOLO_YIELD_ROWCOL':'0','GGML_SCALE_SPLIT':'0','GGML_TINY_SOLO_CLAMP':'1','GGML_GET_ROWS_SOLO':'0'}

def create_knob_page(path):
    path=Path(path); payload=('\n'.join(k+'='+v for k,v in KNOBS.items())+'\n').encode()
    if len(payload)>=1024: raise ValueError('knob payload too long')
    fd=os.open(path,os.O_RDWR|os.O_CREAT|os.O_EXCL,0o600)
    try:
        os.ftruncate(fd,4096)
        with mmap.mmap(fd,4096) as page:
            page[1536:1536+len(payload)]=payload
            page.flush()
            page[0:8]=struct.pack('<Q',1)
            page.flush()
    finally: os.close(fd)

def verify_knob_page(path):
    b=Path(path).read_bytes()
    if len(b)!=4096 or struct.unpack('<Q',b[:8])[0]!=1: raise ValueError('invalid knob page')
    data=b[1536:2560].split(b'\0',1)[0].decode()
    expected='\n'.join(k+'='+v for k,v in KNOBS.items())+'\n'
    if data!=expected: raise ValueError('knob payload mismatch')

def verify_runtime(pid, bindir, knob_file=None):
    proc=Path('/proc')/str(pid); status=(proc/'status').read_text()
    thp=[line.split(':',1)[1].strip() for line in status.splitlines() if line.startswith('THP_enabled:')]
    if thp!=['1']: raise RuntimeError('THP OFF state not verified')
    maps=(proc/'maps').read_text(); root=Path(bindir).resolve()
    cpu=[line.split()[-1] for line in maps.splitlines() if '/libggml-cpu.so' in line]
    if not cpu or any(not Path(p).resolve().is_relative_to(root) for p in cpu): raise RuntimeError('CPU linkage not verified')
    if knob_file is not None and str(Path(knob_file).resolve()) not in maps: raise RuntimeError('knob page is not mapped')
    return {'thp_enabled':1,'cpu_objects':sorted(set(cpu)),'knob_mapped':knob_file is not None}

def stop_owned(process,seconds=10):
    if process.poll() is None:
        process.terminate()
        try: process.wait(timeout=seconds)
        except subprocess.TimeoutExpired: process.kill();process.wait(timeout=seconds)
    if process.poll() is None: raise RuntimeError('owned child still alive')
    return process.returncode

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def seal_local_dso(bindir):
    """Pin all local shared libraries, including dynamically loaded ggml backends."""
    root=Path(bindir).resolve(); out={}
    for p in root.glob('*.so*'):
        target=p.resolve(strict=True)
        if not target.is_relative_to(root): raise ValueError('library escapes build directory')
        if target.is_file(): out[str(target)]=sha256(target)
    if not any('/libggml-cpu.so' in k for k in out): raise ValueError('missing CPU backend')
    if not any('/libggml-base.so' in k for k in out): raise ValueError('missing ggml base')
    return out

def check_live_dso(pid, bindir, sealed):
    root=Path(bindir).resolve(); maps=(Path('/proc')/str(pid)/'maps').read_text(); seen={}
    for line in maps.splitlines():
        fields=line.split()
        if len(fields)<6 or not fields[-1].startswith('/'): continue
        p=Path(fields[-1])
        if '.so' not in p.name: continue
        target=p.resolve(strict=True)
        if target.is_relative_to(root):
            if str(target) not in sealed or sha256(target)!=sealed[str(target)]: raise ValueError('unexpected or changed build DSO')
            seen[str(target)]=sealed[str(target)]
        elif p.name.startswith(('libggml','libllama')):
            raise ValueError('foreign inference DSO: '+str(p))
    if not any('/libggml-cpu.so' in k for k in seen): raise ValueError('CPU backend not mapped')
    if not any('/libggml-base.so' in k for k in seen): raise ValueError('ggml base not mapped')
    return seen
