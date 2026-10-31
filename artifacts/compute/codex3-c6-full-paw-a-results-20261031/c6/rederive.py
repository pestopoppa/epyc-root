import json,hashlib,re,collections
from pathlib import Path
r=Path('/mnt/raid0/llm/tmp/refactor-c6-gpu-gak-full-prep-20261031/runs/20261031T051940Z-158757');j=json.loads((r/'native/native-records.json').read_text());bad=[]
for x in j['records']:
 for k,h in [('raw_log','raw_sha256'),('stderr_log','stderr_sha256')]:
  if x.get(k) and hashlib.sha256(Path(x[k]).read_bytes()).hexdigest()!=x[h]:bad.append([x['name'],k])
assert not bad and len(j['records'])==9 and j['records'][-1]['name']=='C5-MUL_MAT' and j['records'][-1]['native_rc']==1
s=re.sub(r'\x1b\[[0-9;]*m','',(r/'native/C5-MUL_MAT.log').read_text(errors='replace'));counts=collections.Counter();bytype=collections.Counter();fail=[]
for line in s.splitlines():
 if not (line.lstrip().startswith('MUL_MAT(') and '):' in line):continue
 typ=re.search(r'type_a=([^,]+)',line).group(1);status='FAIL' if re.search(r'\bFAIL\s*$',line) else 'OK' if re.search(r'\bOK\s*$',line) else 'not_supported' if 'not supported' in line.lower() else 'other';counts[status]+=1;bytype[(typ,status)]+=1
 if status=='FAIL':
  m=re.search(r'AK_PROP_V2 metric=([^ ]+) residual=([^ ]+) tolerance=([^ ]+) passed=0',line);assert m and float(m[2])>float(m[3]);fail.append({'case_sha256':hashlib.sha256(line.encode()).hexdigest(),'type_a':typ,'metric':m[1],'residual':float(m[2]),'tolerance':float(m[3])})
assert dict(counts)=={'OK':1080,'not_supported':326,'FAIL':65} and len(fail)==65
print(json.dumps({'status_counts':dict(counts),'by_type':{t:{k:v for (a,k),v in bytype.items() if a==t} for t in sorted({a for a,k in bytype})},'failures':fail,'native_stdout_sha256':j['records'][-1]['raw_sha256'],'native_stderr_sha256':j['records'][-1]['stderr_sha256'],'own_kfd_reads':j['records'][-1]['sampler']['own_pid_kfd_reads'],'own_peak_vram_bytes':j['records'][-1]['sampler']['own_pid_peak_vram_bytes'],'source':'C5 baseline only; C6 phases not run; full gate unknown'},indent=2))
