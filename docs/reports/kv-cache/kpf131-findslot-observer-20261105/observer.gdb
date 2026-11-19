set pagination off
set confirm off
set debuginfod enabled off
set disable-randomization off
start < $OBSERVER_OUT/input
python
import gdb, os, json, hashlib, sys
from pathlib import Path
sys.path.insert(0,os.environ['OBSERVER_DIR'])
from map_identity import verify_snapshot
out=Path(os.environ['OBSERVER_OUT']); pins=json.loads((Path(os.environ['OBSERVER_DIR'])/'pins.json').read_text())
pid=gdb.selected_inferior().pid
def birth(): return int(Path('/proc/%d/stat'%pid).read_text().rsplit(')',1)[1].split()[19])
(out/'identity.json').write_text(json.dumps({'pid':pid,'birth':birth()}))
def snap():
 b=birth(); ex=Path('/proc/%d/exe'%pid); st=ex.stat(); f=Path(os.environ['OBSERVER_FIX']).stat()
 if (st.st_dev,st.st_ino)!=(f.st_dev,f.st_ino): raise RuntimeError('executable inode mismatch')
 h=hashlib.sha256(ex.read_bytes()).hexdigest()
 maps=verify_snapshot(Path('/proc/%d/maps'%pid).read_text().splitlines(),pins)
 if set(maps)!=set(pins) or birth()!=b: raise RuntimeError('mapping/birth mismatch')
 return {'pid':pid,'birth':b,'exe_sha256':h,'exe_device':st.st_dev,'exe_inode':st.st_ino,'maps':{p:{'identity':list(v),'sha256':pins[p]} for p,v in maps.items()}}
result={'before':snap(),'hits':0}
class Probe(gdb.Breakpoint):
 def stop(self):
  result['hits']+=1
  return False
p=Probe('llama_kv_cache::find_slot(llama_ubatch const&, bool) const',type=gdb.BP_HARDWARE_BREAKPOINT)
p.silent=True
end
catch syscall exit_group
continue
python
result['after']=snap()
end
continue
python
result['exit_code']=int(gdb.parse_and_eval('$_exitcode'))
(out/'native.json').write_text(json.dumps(result,sort_keys=True)+'\n')
end
