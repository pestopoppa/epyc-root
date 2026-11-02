"""CPU-only vocabulary capture. Never executes the candidate HIP tokenizer.

Outputs are CPU-reference counts, not proof of candidate server equivalence.
"""
import hashlib,json,os,pathlib,re,shutil,subprocess,sys,tempfile
import native_config as c, runtime_entry as y
from paired_runner import DOC_HEAD,STAGES,atomic
P=pathlib.Path;ROOT=P(__file__).resolve().parent
CPU=P('/mnt/raid0/llm/kernels/production/cpu')
PINS={
'llama-tokenize':'3893e741f796e21342fd0d5a599db9e9eb3050448532689339f2523f19776407',
'libllama.so.0':'5cdd003d3f441e1efe42e4c06e4434b0195f25ab6317d64aa7e7cf60deaba844',
'libllama-common.so.0':'dfd31d4bb51818e5507b9eeaa7766452cab914f02bdbd1e0f18b4c3e9294de09',
'libggml.so.0':'87074c95c8709c491e84b2c8b9c0b8fa911b1cd309fbd5536a4947063a96998e',
'libggml-base.so.0':'92cc3dfd7e1119b7bcc83c18f758099c47363073013a896ee76efcd6ad19145a',
'libggml-cpu.so.0':'3f4edd2fc0f1e78003735be59db987d43c4bc0e6a8f821bc419d7b6f492346c0'}
SYSTEM={'libstdc++.so.6','libgcc_s.so.1','libc.so.6','libm.so.6','libgomp.so.1','ld-linux-x86-64.so.2'}
class Refused(RuntimeError):pass
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def stage_cpu(source,dest):
 """Copy only the pinned CPU artifact closure into a fresh empty directory."""
 source=P(source);dest=P(dest)
 if source.resolve()!=CPU.resolve():raise Refused('only approved CPU store accepted')
 if any(dest.iterdir()):raise Refused('staging directory not empty')
 for name,expected in PINS.items():
  src=source/name
  if not src.resolve(strict=True).is_relative_to(source.resolve()) or sha(src)!=expected:raise Refused('CPU artifact mismatch '+name)
  shutil.copyfile(src,dest/name)
  if sha(dest/name)!=expected:raise Refused('staged artifact mismatch '+name)
  os.chmod(dest/name,0o500)
 for name in PINS:
  proc=subprocess.run(['/usr/bin/readelf','-d',str(dest/name)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,text=True,timeout=10)
  needed=set(re.findall(r'\(NEEDED\).*\[(.*?)\]',proc.stdout))
  if not needed or needed-(set(PINS)|SYSTEM):raise Refused('unexpected shared dependency: '+name)
 return dict(PINS)
def main(out):
 out=P(out)
 if not out.is_absolute():raise Refused('absolute output directory required')
 out.mkdir(mode=0o700,parents=False,exist_ok=False)
 atomic(out/'status.json',{'status':'partial_no_verdict','warrant':'cpu_reference_only'})
 inp=y.load_inputs()
 if inp['bad']:raise Refused('input mismatch')
 receipt=json.loads((ROOT/'model-receipt.json').read_text());fd=os.open(c.MODEL,os.O_RDONLY|os.O_CLOEXEC);s=os.fstat(fd);rs=receipt['fd_after']
 try:
  if receipt['status']!='PASS' or receipt['sha256']!='a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348' or (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)!=(rs['device'],rs['inode'],rs['size_bytes'],rs['mtime_ns'],rs['ctime_ns']):raise Refused('model receipt mismatch')
  with tempfile.TemporaryDirectory(prefix='cpu-tokenizer-',dir=out) as tmp:
   stage=P(tmp);pins=stage_cpu(CPU,stage)
   # Empty isolated cwd, no inherited loader, device, or backend variables.
   env={'PATH':'/usr/bin:/bin','LC_ALL':'C','LD_LIBRARY_PATH':str(stage)}
   atomic(out/'provenance.json',{'status':'started','executable':'pinned CPU store copy','pins':pins,'model_receipt_sha256':sha(ROOT/'model-receipt.json'),'manifest_sha256':y.MANIFEST_SHA,'flags':['--stdin','--ids','--no-bos','--no-escape'],'environment':env,'stderr_files':'<stage>.stderr','stdout_files':'<stage>.stdout','limitation':'CPU reference only; no candidate server equivalence established'})
   rows={}
   for name in STAGES:
    data=(DOC_HEAD.format(k=1)+inp['segments'][name]).encode()
    cmd=[str(stage/'llama-tokenize'),'-m',f'/proc/self/fd/{fd}','--stdin','--ids','--no-bos','--no-escape']
    # Both files exist before spawn; failure retains stderr and any partial stdout.
    with (out/(name+'.stdout')).open('xb') as stdout,(out/(name+'.stderr')).open('xb') as stderr:
     proc=subprocess.run(cmd,input=data,stdout=stdout,stderr=stderr,env=env,cwd=stage,pass_fds=(fd,),timeout=180)
    if proc.returncode:raise Refused('tokenizer failure; stderr retained')
    raw=(out/(name+'.stdout')).read_bytes();ids=json.loads(raw)
    if not isinstance(ids,list) or any(type(i) is not int for i in ids):raise Refused('bad token ids')
    rows[name]={'count':len(ids),'segment_sha256':hashlib.sha256(inp['segments'][name].encode()).hexdigest(),'input_sha256':hashlib.sha256(data).hexdigest(),'ids_sha256':hashlib.sha256(raw).hexdigest(),'stderr_sha256':sha(out/(name+'.stderr')),'returncode':proc.returncode}
   if os.fstat(fd)!=s:raise Refused('model changed')
   atomic(out/'status.json',{'status':'complete_cpu_reference','counts':rows,'pins':pins,'model_receipt_sha256':sha(ROOT/'model-receipt.json'),'manifest_sha256':y.MANIFEST_SHA,'flags':['--stdin','--ids','--no-bos','--no-escape'],'environment':env,'limitation':'CPU reference only; no candidate server equivalence established'})
 finally:os.close(fd)
if __name__=='__main__':
 if len(sys.argv)!=2:raise SystemExit('usage: candidate_counts.py ABSOLUTE_NEW_OUTPUT_DIRECTORY')
 main(sys.argv[1])
