"""Validate only successor-owned copies of the full KPF-17 oracle build."""
import hashlib
import json
import os
from pathlib import Path
import re

D=Path(__file__).resolve().parent
COPY=D/'build-custody'
COPY_MANIFEST=COPY/'copy-manifest.json'
SOURCE='8952a0f693fb923918157eb25117641b74766230'
PATCH='b7eb4cabacadb7378bd1bcc8af4532f71ce39c751b5d0f11ce4abe96b010eac6'
TEST='b2f7085c3b772b58d6e9eb5ec33f217f22e9e1987bb8f51f040094eb586ef2ab'
HEADER='90787c4a526d2dedd3d3d11bf944ea81eeb1c2efd77e5e6862e8e69a57b26249'
HELPER='57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33'
HEX=re.compile(r'^[0-9a-f]{64}$')

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def need(condition,message):
    if not condition:raise ValueError(message)

def owned(path, root):
    path=Path(path).resolve(strict=True)
    need(path.is_relative_to(root.resolve(strict=True)), 'path outside successor custody: '+str(path))
    return path

def build_identity():
    copy=json.loads(COPY_MANIFEST.read_text())
    receipt_path=owned(copy['receipt_path'],COPY);receipt=json.loads(receipt_path.read_text())
    need(copy.get('schema')=='kpf17.oracle-build-copy.v1','unexpected copied-build manifest schema')
    need(copy.get('row_id')=='kvfork17-oracle-build-20261104','wrong prerequisite build row')
    need(digest(receipt_path)==copy.get('receipt_sha256')==copy.get('source_receipt_sha256'),'copied build receipt digest mismatch')
    ended=owned(copy['ended_path'],COPY);complete=owned(copy['completion_path'],COPY)
    need(digest(ended)==copy.get('ended_sha256'),'copied build end marker changed')
    need(digest(complete)==copy.get('completion_sha256'),'copied build completion marker changed')
    ended_text=ended.read_text();complete_text=complete.read_text()
    need('rc=0 ' in ended_text and 'reason=complete' in ended_text and 'job_id=kvfork17-oracle-build-20261104' in ended_text,'build did not end rc=0 complete')
    need('id=kvfork17-oracle-build-20261104' in complete_text,'build completion marker row mismatch')
    runtime_manifest=owned(copy['runtime_manifest_path'],COPY)
    need(digest(runtime_manifest)==copy.get('runtime_manifest_sha256'),'copied runtime manifest changed')
    required={'schema':'kpf17.oracle-build.v1','status':'BUILT','source_commit':SOURCE,
              'patch_sha256':PATCH,'patched_test_sha256':TEST,'oracle_header_sha256':HEADER}
    for key,value in required.items():need(receipt.get(key)==value,'build receipt mismatch: '+key)
    files=receipt.get('files');compilers=receipt.get('compiler_sha256')
    need(isinstance(files,dict) and isinstance(compilers,dict),'receipt artifact/compiler map missing')
    need(set(compilers)=={'/usr/bin/cc','/usr/bin/c++'},'compiler custody incomplete')
    for name,expected in compilers.items():need(isinstance(expected,str) and HEX.fullmatch(expected),'invalid compiler digest: '+name)
    copied=copy.get('artifacts',{})
    need(set(copied)==set(files),'copied build artifact coverage mismatch')
    for original,expected in files.items():
        row=copied[original];path=owned(row['path'],COPY)
        need(row.get('sha256')==expected and digest(path)==expected,'copied artifact mismatch: '+original)
    inputs=copy.get('runtime_inputs',{})
    need(len(inputs)==6,'runtime build-input coverage incomplete')
    for original,row in inputs.items():
        path=owned(row['path'],COPY);expected=row['sha256']
        need(HEX.fullmatch(expected) and digest(path)==expected,'copied build input mismatch: '+original)
    helper_src='/mnt/raid0/llm/tmp/kvfork/kpf17-oracle-build-20261104/verify_ggml_linkage.sh'
    helper_row=copied.get(helper_src)
    need(helper_row is not None and helper_row['sha256']==HELPER,'linkage helper custody missing')
    runtime_bin=owned(copy['runtime_bin'],D/'runtime')
    binary=(runtime_bin/'test-save-load-state').resolve(strict=True)
    need(binary.parent==runtime_bin and digest(binary)==copy.get('binary_sha256'),'successor-owned executable mismatch')
    source_binary='/mnt/raid0/llm/tmp/kvfork/kpf17-oracle-build-20261104/build/bin/test-save-load-state'
    need(files.get(source_binary)==digest(binary),'executable not bound to full build receipt')
    libs={}
    for name in ('libggml.so','libggml-base.so','libggml-cpu.so','libllama.so','libllama-common.so'):
        path=(runtime_bin/name).resolve(strict=True)
        need(path.parent==runtime_bin,'DSO escaped successor runtime: '+name)
        original=next((p for p,h in files.items() if Path(p).name==path.name and h==digest(path)),None)
        need(original is not None,'DSO not bound to full build receipt: '+name)
        libs[str(path)]=digest(path)
    return {'receipt_sha256':digest(receipt_path),'copy_manifest_sha256':digest(COPY_MANIFEST),
            'runtime_manifest_sha256':digest(runtime_manifest),'ended_sha256':digest(ended),
            'completion_sha256':digest(complete),'binary':str(binary),'binary_sha256':digest(binary),
            'libraries':libs,'linkage_helper':str(Path(helper_row['path'])),'runtime_bin':str(runtime_bin),
            'source_commit':SOURCE,'patch_sha256':PATCH,'test_sha256':TEST,'oracle_header_sha256':HEADER}

def model_identity(path):
    model=json.loads(Path(path).read_text())
    if model.get('sha256')!='0ad885ffd4bb022fc4f0d33a3308fa108ef8613159d3b3a67e23abca056b7a6c':
        raise ValueError('model does not have the preverified hash')
    target=Path(model['path']);stat=target.stat()
    actual={key:getattr(stat,'st_'+key) for key in ('dev','ino','size','mtime_ns','ctime_ns')}
    if model.get('stat')!=actual:raise ValueError('model metadata changed; weight hash is never computed in grant')
    return model

def validate_maps(lines,expected):
    seen={}
    for line in lines:
        parts=line.split(None,5)
        if len(parts)<6 or not re.search(r'/lib(?:ggml|llama)(?:[-.]|\.so)',parts[5]):continue
        if parts[5].endswith(' (deleted)'):raise ValueError('deleted mapped library')
        path=Path(parts[5]).resolve(strict=True);name=str(path)
        if name not in expected or digest(path)!=expected[name]:raise ValueError('unattested mapped library: '+name)
        stat=path.stat();major,minor=(int(x,16) for x in parts[3].split(':'))
        if (major,minor,int(parts[4]))!=(os.major(stat.st_dev),os.minor(stat.st_dev),stat.st_ino):raise ValueError('mapped library inode changed')
        seen[name]=expected[name]
    required=('libggml.so','libggml-base.so','libggml-cpu.so','libllama.so','libllama-common.so')
    if not all(any(Path(path).name.startswith(prefix) for path in seen) for prefix in required):raise ValueError('required mapped DSO absent')
    return seen
