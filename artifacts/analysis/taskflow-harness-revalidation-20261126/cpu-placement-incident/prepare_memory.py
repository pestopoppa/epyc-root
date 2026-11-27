import ctypes,json,mmap,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
GIB=1024**3
if len(sys.argv)>1:
 node=int(sys.argv[1]); size=20*GIB
 area=mmap.mmap(-1,size,flags=mmap.MAP_PRIVATE|mmap.MAP_ANONYMOUS)
 address=ctypes.addressof(ctypes.c_char.from_buffer(area))
 ctypes.memset(address,0,size)
 lines=Path('/proc/self/numa_maps').read_text().splitlines()
 import re
 maps=[line for line in lines if int(line.split()[0],16)==address]
 assert len(maps)==1,maps
 counts={int(n):int(v)*4096 for n,v in re.findall(r'\bN(\d+)=(\d+)',maps[0])}
 assert counts.get(node,0)>=size*.99 and sum(counts.values())>=size*.99,counts
 print(json.dumps({'pid':os.getpid(),'node':node,'bytes':size,'counts':counts,'mapping':maps[0]}),flush=True)
 assert sys.stdin.readline().strip()=='release'
 area.close();raise SystemExit(0)
avail=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
assert avail>160*GIB,avail
assert not Path('/proc/1016704').exists() and not Path('/proc/2323088').exists()
started=time.time(); workers=[]; records=[]
try:
 for node in range(4):
  proc=subprocess.Popen(['numactl',f'--membind={node}',f'--physcpubind={node*24}',sys.executable,'-B',str(Path(__file__).resolve()),str(node)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  workers.append(proc)
 for proc in workers:
  line=proc.stdout.readline()
  if not line:raise RuntimeError(f'owned allocation failed pid={proc.pid}: {proc.stderr.read()}')
  records.append(json.loads(line));print(line.strip(),flush=True)
 for proc in workers:proc.stdin.write('release\n');proc.stdin.flush()
 for proc in workers:assert proc.wait(timeout=30)==0
 result={'started_at':started,'ended_at':time.time(),'mem_available_before':avail,'bounded_bytes':80*GIB,'workers':records,'all_workers_reaped':all(p.poll() is not None for p in workers),'purpose':'strict per-node bounded cache reclaim then release; no global cache flush or kernel policy change'}
 (ROOT/'MEMORY-PREP.json').write_text(json.dumps(result,indent=2)+'\n');print('RELEASED all owned memory allocations',flush=True)
finally:
 for proc in workers:
  if proc.poll() is None:proc.kill();proc.wait()
