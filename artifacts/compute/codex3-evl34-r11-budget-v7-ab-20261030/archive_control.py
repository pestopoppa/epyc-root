#!/usr/bin/env python3
"""Archive drained native smoke in RAM, verify every member, then admit actual RAID bytes."""
import hashlib,json,os,pathlib,shutil,stat,sys,tarfile,time
P=pathlib.Path; FLOOR=150*1024**3; RECEIPT_RESERVE=16*1024**2; CHUNK=1024*1024
class Pause(RuntimeError):pass
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def snapshot(root):
 result={}
 for p in sorted(root.rglob('*')):
  key=str(p.relative_to(root));s=p.lstat();r={'mode':stat.S_IMODE(s.st_mode),'size':s.st_size,'mtime_ns':s.st_mtime_ns,'inode':s.st_ino,'dev':s.st_dev}
  if p.is_symlink():r.update(type='symlink',target=os.readlink(p))
  elif p.is_dir():r.update(type='directory')
  elif p.is_file():r.update(type='file',sha256=sha(p))
  else:raise RuntimeError('unsupported output type '+str(p))
  a=p.lstat()
  if (s.st_ino,s.st_size,s.st_mtime_ns)!=(a.st_ino,a.st_size,a.st_mtime_ns):raise RuntimeError('output changed '+str(p))
  result[key]=r
 return result
def verify_archive(archive,inventory):
 with tarfile.open(archive,'r:gz') as t:
  members=t.getmembers(); m={x.name.removeprefix('control/'):x for x in members if x.name!='control'}
  if len(m)!=len(members)-1 or set(m)!=set(inventory):raise RuntimeError('archive member mismatch')
  for name,src in inventory.items():
   z=m[name]
   if z.mode!=src['mode']:raise RuntimeError('archive mode mismatch '+name)
   if src['type']=='directory':
    if not z.isdir():raise RuntimeError('archive directory mismatch '+name)
   elif src['type']=='symlink':
    if not z.issym() or z.linkname!=src['target']:raise RuntimeError('archive link mismatch '+name)
   else:
    if not (z.isfile() or z.islnk()):raise RuntimeError('archive file type mismatch '+name)
    with t.extractfile(z) as f: actual=hashlib.file_digest(f,'sha256').hexdigest()
    if actual!=src['sha256']:raise RuntimeError('archive bytes mismatch '+name)
def copy_admitted(src,dst,*,free=lambda p:shutil.disk_usage(p).free):
 size=src.stat().st_size;parent=dst.parent
 if dst.exists():
  existing=dst.stat().st_size
  if existing>size:raise RuntimeError('partial archive longer than source')
  with src.open('rb') as a,dst.open('rb') as b:
   remaining=existing
   while remaining:
    n=min(CHUNK,remaining)
    if a.read(n)!=b.read(n):raise RuntimeError('partial archive prefix mismatch')
    remaining-=n
 else: existing=0
 if free(parent)<FLOOR+RECEIPT_RESERVE+(size-existing):raise Pause('actual archive does not fit above RAID floor and receipt reserve')
 with src.open('rb') as f,dst.open('ab' if dst.exists() else 'xb') as o:
  f.seek(existing);left=size-existing
  while left:
   if free(parent)<FLOOR+RECEIPT_RESERVE+left:raise Pause('RAID space changed during archival copy')
   chunk=f.read(min(CHUNK,left))
   if not chunk:raise RuntimeError('short archive')
   o.write(chunk);left-=len(chunk)
  o.flush();os.fsync(o.fileno())
 if sha(src)!=sha(dst):raise RuntimeError('durable archive checksum mismatch')

def qualify(root):
 supervisor=json.loads((root/'campaign-supervisor.json').read_text())
 if not supervisor.get('drained'):raise RuntimeError('control descendant drain missing')
 attempts=list(root.glob('campaign-control-*'))
 if len(attempts)>1:raise RuntimeError('multiple control attempts')
 attempt=attempts[0] if attempts else None
 result_path=attempt/'result.json' if attempt else None
 result=json.loads(result_path.read_text()) if result_path and result_path.is_file() else None
 witness_path=attempt/'gpu-witness.jsonl' if attempt else None
 witness=[json.loads(x) for x in witness_path.read_text().splitlines()] if witness_path and witness_path.is_file() else []
 fast=[x for x in witness if x.get('kind')=='fast-kfd-residency' and x.get('hip_mapped') is True and x.get('gpu_own_pid_vram_bytes',0)>0]
 wire=(result or {}).get('wire_capture') or {};statuses=(result or {}).get('statuses') or {}
 qualified=(supervisor.get('rc')==0 and supervisor.get('reason') is None and result is not None and result.get('failure') is None and result.get('partial') is False and result.get('server_drained') is True and len(statuses)==2 and all(x=='complete' for x in statuses.values()) and wire.get('first_tools')==['delegate','wait'] and wire.get('tool_choice') in (None,'auto') and len(fast)>=2)
 return supervisor,attempt,result,len(fast),qualified

def bundle_source(root,dest):
 bundle=root/'frozen-source';bundle.mkdir(mode=0o700,exist_ok=True)
 selected=[p for p in dest.iterdir() if p.is_file() and (p.suffix in ('.py','.sh','.sha256') or p.name in ('CONTROL-PRIVATE.json','PILOT-PRIVATE.json','PREDECLARATION-FROZEN.json','FROZEN-PROMPT-MANIFEST.json','SOURCE-DECLARATION.json','LOCAL-SOURCE-INVENTORY.json','CONTROL-EXPOSURE-START.json'))]
 selected.append(P('/mnt/raid0/llm/tmp/codex3-evl34-deepdive-prep-20261030/qa_rl.parquet'))
 for src in selected:
  dst=bundle/src.name
  if dst.exists():
   if sha(dst)!=sha(src):raise RuntimeError('frozen source changed: '+src.name)
  else:
   shutil.copy2(src,dst)
   if sha(dst)!=sha(src):raise RuntimeError('source bundle mismatch: '+src.name)

 def_file=dest/'CAMPAIGN-SOURCES.sha256'
 for line in def_file.read_text().splitlines():
  expected,name=line.split('  ',1)
  if name.endswith('.gguf'):continue
  if sha(P(name))!=expected:raise RuntimeError('source changed: '+name)

def main():
 root=P('/dev/shm/codex3-evl34-deepdive-r8-control-20261030');dest=P(__file__).resolve().parent
 if dest!=P('/mnt/raid0/llm/tmp/codex3-evl34-r11-budget-v7-ab-20261030') or root.is_symlink():raise RuntimeError('wrong archive location')
 supervisor,attempt,result,witnesses,qualified=qualify(root)
 marker=dest/'CONTROL-EXPOSURE-START.json'
 if not marker.is_file():raise RuntimeError('control exposure marker missing')
 bundle_source(root,dest);before=snapshot(root);archive=root.parent/(root.name+'.tar.gz')
 if not archive.exists():
  with archive.open('xb') as f:
   with tarfile.open(fileobj=f,mode='w:gz',dereference=False) as tar:tar.add(root,arcname='control',recursive=True)
 verify_archive(archive,before)
 if snapshot(root)!=before:raise RuntimeError('control changed during archive')
 digest=sha(archive);size=archive.stat().st_size;partial=dest/'control-archive.tar.gz.partial';final=dest/'control-archive.tar.gz'
 try:
  if final.exists():
   if sha(final)!=digest:raise RuntimeError('existing final archive mismatch')
  else:copy_admitted(archive,partial)
 except Pause as e:
  print(json.dumps({'state':'archive-wait','reason':str(e),'ram_archive':str(archive),'sha256':digest,'bytes':size}));return 75
 if not final.exists():os.link(partial,final)
 receipt={'schema':'evl34-r7-control-archive/v1','ram_root':str(root),'ram_archive':str(archive),'archive':str(final),'sha256':digest,'bytes':size,'member_count':len(before),'members':before,'supervisor':supervisor,'native_result_sha256':sha(attempt/'result.json') if result is not None else None,'native_result':result,'qualified':qualified,'source_manifest_sha256':sha(dest/'CAMPAIGN-SOURCES.sha256'),'exposure_marker_sha256':sha(marker),'fast_gpu_samples':witnesses,'created_epoch':time.time()}
 encoded=(json.dumps(receipt,indent=2)+'\n').encode()
 if len(encoded)>8*1024**2:raise RuntimeError('receipt exceeds 8 MiB')
 rp=dest/'control-archive-receipt.json'
 if rp.exists():
  prior=json.loads(rp.read_text())
  if prior.get('sha256')!=digest or prior.get('members')!=before or prior.get('native_result_sha256')!=receipt['native_result_sha256']:raise RuntimeError('existing receipt mismatch')
 else:
  with rp.open('xb') as f:f.write(encoded);f.flush();os.fsync(f.fileno())
 print(json.dumps({'state':'archived','archive':str(final),'sha256':digest,'bytes':size,'members':len(before),'qualified':qualified}));return 0
if __name__=='__main__':sys.exit(main())
