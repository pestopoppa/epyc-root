set pagination off
set confirm off
set debuginfod enabled off
start
python
import gdb, json, os, hashlib
pins=json.load(open(os.environ['KPF_PINS']))
out=[]
pid=gdb.selected_inferior().pid
stat=open('/proc/%d/stat'%pid).read().rsplit(')',1)[1].split()
open(os.environ['KPF_PID'], 'w').write(json.dumps({'pid':pid,'ppid':int(stat[1]),'birth':stat[19]}))
class Observe(gdb.Breakpoint):
 def stop(self):
  inf=gdb.selected_inferior(); pid=inf.pid
  ub=int(gdb.parse_and_eval('$rdx'))
  mem=inf.read_memory
  n=int.from_bytes(bytes(mem(ub+0x10,4)),'little')
  ptr=int.from_bytes(bytes(mem(ub+0x40,8)),'little')
  if n<1 or n>32 or not ptr: raise RuntimeError('invalid ubatch')
  ids=[int.from_bytes(bytes(mem(ptr+i*4,4)),'little',signed=True) for i in range(n)]
  mapped={}
  for line in open('/proc/%d/maps'%pid):
   fields=line.rstrip().split(None,5)
   if len(fields)<6 or ('libggml' not in fields[5] and 'libllama' not in fields[5]): continue
   path=fields[5]
   if not path.startswith('/') or path.endswith(' (deleted)'): raise RuntimeError('invalid map')
   path=os.path.realpath(path); digest=hashlib.sha256(open(path,'rb').read()).hexdigest()
   if pins.get(path)!=digest: raise RuntimeError('mapping mismatch '+path)
   mapped[path]=digest
  if len(mapped)!=5: raise RuntimeError('expected five DSOs')
  exe=os.readlink('/proc/%d/exe'%pid)
  out.append({'ids':ids,'mapped':mapped,'exe':exe,'exe_sha256':hashlib.sha256(open(exe,'rb').read()).hexdigest()})
  return False
b=Observe('llama_kv_cache::find_slot(llama_ubatch const&, bool) const',type=gdb.BP_HARDWARE_BREAKPOINT)
end
continue
python
json.dump({'events':out,'exit_code':int(gdb.parse_and_eval('$_exitcode'))},open(os.environ['KPF_CAPTURE'],'w'))
end
