"""Verify one target's mapped C5 ELF inodes; no inference or performance claim."""
from pathlib import Path
import os
import hashlib
import json
import re

BUILD = Path('/mnt/raid0/llm/kernels/builds/cpu-20261024-c72ec82f5-c5/bin')
REQUIRED = frozenset(('llama-server', 'libllama-server-impl.so',
    'libllama.so.0.0.10419', 'libllama-common.so.0.0.10419',
    'libmtmd.so.0.0.10419', 'libggml.so.0.16.0',
    'libggml-base.so.0.16.0', 'libggml-cpu.so.0.16.0'))
PREFIXES = ('libllama', 'libggml', 'libmtmd')
BOOT = Path('/proc/sys/kernel/random/boot_id')

def identity(pid, proc=Path('/proc')):
    if type(pid) is not int or pid <= 0: raise ValueError('invalid PID')
    raw=(proc/str(pid)/'stat').read_text(); first, sep, rest=raw.rpartition(') ')
    if not sep or first.split(' (',1)[0] != str(pid): raise ValueError('invalid process stat')
    return {'pid':pid, 'start_ticks':int(rest.split()[19]), 'boot_id':BOOT.read_text().strip()}

def parse_maps(text, build=BUILD, *, stat=os.stat):
    if not isinstance(text,str) or not text: raise ValueError('empty process maps')
    build=Path(build).resolve(strict=True); seen={}; executable=set()
    for line in text.splitlines():
        fields=line.split(maxsplit=5)
        if len(fields)<5: raise ValueError('malformed maps entry')
        area,perms,offset,dev,inode=fields[:5]
        if not re.fullmatch(r'[0-9a-f]+-[0-9a-f]+',area) or not re.fullmatch(r'[r-][w-][x-][ps]',perms) or not re.fullmatch(r'[0-9a-f]+',offset) or not re.fullmatch(r'[0-9a-f]+:[0-9a-f]+',dev) or not inode.isdecimal(): raise ValueError('malformed mapping identity')
        if len(fields)<6: continue
        name=fields[5]; basename=Path(name).name
        candidate=basename in REQUIRED or basename.startswith(PREFIXES) or basename.endswith(' (deleted)') and (basename.removesuffix(' (deleted)') in REQUIRED or basename.removesuffix(' (deleted)').startswith(PREFIXES))
        if not candidate: continue
        if name.endswith(' (deleted)') or not name.startswith('/'): raise ValueError('deleted/nonabsolute project mapping')
        resolved=Path(name).resolve(strict=True)
        if resolved.parent != build or resolved.name not in REQUIRED: raise ValueError('unexpected project mapping')
        st=stat(resolved,follow_symlinks=False); major,minor=(int(x,16) for x in dev.split(':'))
        if (os.major(st.st_dev),os.minor(st.st_dev),st.st_ino)!=(major,minor,int(inode)): raise ValueError('mapping inode/device mismatch')
        recorded=(str(resolved),major,minor,int(inode))
        if resolved.name in seen and seen[resolved.name]!=recorded: raise ValueError('conflicting project mappings')
        seen[resolved.name]=recorded
        if 'x' in perms: executable.add(resolved.name)
    if set(seen)!=REQUIRED or executable!=REQUIRED: raise ValueError('project executable mapping set incomplete')
    return {'status':'matching-c5-mapped-inodes','files':{k:{'path':v[0],'dev_major':v[1],'dev_minor':v[2],'inode':v[3]} for k,v in sorted(seen.items())},'coverage':'point-in-time-only','measurement_admission':'none'}

def prepare(build=BUILD, custody_path=None):
    """Hash manifest-bound binaries once before publication; bind digests to inodes."""
    build=Path(build).resolve(strict=True); manifest_bytes=(build.parent/'SHA256SUMS').read_bytes()
    if custody_path is None: raise ValueError('existing preparation receipt required')
    custody=json.loads(Path(custody_path).read_text())
    if custody.get('schema')!='ch26.c5-build-preparation.v1' or custody.get('native_manifest_checked') is not True or custody.get('source_commit')!='c72ec82f5417bb2937310326120f149b665e8400' or hashlib.sha256(manifest_bytes).hexdigest()!=custody.get('store_manifest_sha256'): raise ValueError('prepared source manifest identity mismatch')
    manifest=manifest_bytes.decode('ascii')
    entries={}
    for line in manifest.splitlines():
        parts=line.split('  ',1)
        if len(parts)!=2 or not re.fullmatch(r'[0-9a-f]{64}',parts[0]) or not parts[1].startswith('./'):
            raise ValueError('invalid build manifest')
        name=parts[1][2:]
        if '/' in name or name in entries: raise ValueError('unsafe manifest entry')
        entries[name]=parts[0]
    if not REQUIRED <= entries.keys(): raise ValueError('incomplete build manifest')
    files={}
    for name in sorted(REQUIRED):
        path=build/name; fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        try:
            before=os.fstat(fd); h=hashlib.sha256()
            while True:
                block=os.read(fd,1024*1024)
                if not block: break
                h.update(block)
            after=os.fstat(fd); current=os.stat(path,follow_symlinks=False)
            key=lambda st:(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)
            if key(before)!=key(after) or key(after)!=key(current): raise ValueError('binary changed during hash')
            if h.hexdigest()!=entries[name]: raise ValueError('binary digest differs from manifest')
            files[name]={'path':str(path),'dev_major':os.major(before.st_dev),'dev_minor':os.minor(before.st_dev),'inode':before.st_ino,'size':before.st_size,'mtime_ns':before.st_mtime_ns,'ctime_ns':before.st_ctime_ns,'sha256':h.hexdigest()}
        finally: os.close(fd)
    return {'schema':'epyc.ch26.c5-mapped-preparation.v1','files':files}

def bind_prepared(mapped, prepared):
    if prepared.get('schema')!='epyc.ch26.c5-mapped-preparation.v1' or set(prepared.get('files',{}))!=REQUIRED: raise ValueError('invalid preverified mapping receipt')
    if not isinstance(mapped.get('files'),dict) or set(mapped['files'])!=REQUIRED: raise ValueError('incomplete mapped binary set')
    for name,identity in mapped['files'].items():
        record=prepared['files'][name]
        if any(record.get(k)!=identity[k] for k in ('path','dev_major','dev_minor','inode')) or not re.fullmatch(r'[0-9a-f]{64}',record.get('sha256','')): raise ValueError('mapped inode differs from hashed prepared binary')
        current=os.stat(identity['path'],follow_symlinks=False)
        if (os.major(current.st_dev), os.minor(current.st_dev), current.st_ino, current.st_size, current.st_mtime_ns, current.st_ctime_ns) != (record.get('dev_major'), record.get('dev_minor'), record.get('inode'), record.get('size'), record.get('mtime_ns'), record.get('ctime_ns')): raise ValueError('prepared binary changed after hash')
    return {**mapped,'prepared_sha256':{n:prepared['files'][n]['sha256'] for n in sorted(REQUIRED)}}

def capture(pid, prepared, build=BUILD, proc=Path('/proc')):
    before=identity(pid,proc)
    with (proc/str(pid)/'maps').open('r') as f: text=f.read(4*1024*1024+1)
    if len(text)>4*1024*1024: raise ValueError('process maps exceeds bound')
    receipt=bind_prepared(parse_maps(text,build),prepared)
    exe_path=proc/str(pid)/'exe'
    exe_name=os.readlink(exe_path)
    if not exe_name.startswith('/') or exe_name.endswith(' (deleted)'):
        raise ValueError('deleted or nonabsolute target executable')
    st=os.stat(exe_path)
    expected=receipt['files']['llama-server']
    if (os.major(st.st_dev),os.minor(st.st_dev),st.st_ino)!=(expected['dev_major'],expected['dev_minor'],expected['inode']):
        raise ValueError('target executable inode mismatch')
    receipt['executable']=dict(expected)
    if identity(pid,proc)!=before: raise ValueError('target identity changed during maps read')
    return {**receipt,'target':before}
