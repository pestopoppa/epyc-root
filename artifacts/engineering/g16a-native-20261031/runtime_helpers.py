import pathlib,os,signal,datetime,re,hashlib
PREP_MUTEX='/mnt/raid0/llm/tmp/compute-flags/prep-locks/32-33.lock'
def mutexes(mode,directory):
 return ([PREP_MUTEX] if mode!='full' else [])+[str(directory/'writer.lock')]
def proc_rows(root=pathlib.Path('/proc')):
 rows={}
 for d in root.iterdir():
  if not d.name.isdigit():continue
  try:
   text=(d/'stat').read_text();v=text[text.rfind(')')+2:].split()
   rows[int(d.name)]={'ppid':int(v[1]),'rss':int(v[21])*os.sysconf('SC_PAGE_SIZE'),'birth':int(v[19]),'state':v[0]}
  except (OSError,ValueError,IndexError):pass
 return rows

def capture(owned,rows):
 live={p:b for p,b in owned.items() if p in rows and rows[p]['birth']==b}
 while True:
  new={p:r['birth'] for p,r in rows.items() if r['ppid'] in live and p not in live}
  if not new:break
  live.update(new);owned.update(new)
 return live

def signal_matching(pid,birth,sig,read_rows=proc_rows,send=os.kill):
 rows=read_rows()
 if pid in rows and rows[pid]['birth']==birth and rows[pid]['state']!='Z':
  try:send(pid,sig);return True
  except ProcessLookupError:pass
 return False

def classify_admission(grants,rows,now):
 active=[];busy=set()
 for name,text,ended in grants:
  if ended:continue
  end=re.search(r'end=(\S+)',text)
  if end:
   try:
    if datetime.datetime.fromisoformat(end.group(1).replace('Z','+00:00'))<=now:continue
   except ValueError:return None,{'refusal':'invalid grant deadline','grant':name}
  active.append(name);m=re.search(r'regions=(\S+)',text)
  if not m:return None,{'refusal':'missing grant regions','grant':name}
  for token in m.group(1).split(','):
   if re.fullmatch(r'\d+-\d+',token):
    a,b=map(int,token.split('-'));busy.update(range(a,b+1))
   elif token.isdigit():busy.add(int(token))
 allowed=('block-correctness','correctness','diagnostic','block-diagnostic')
 # Standing prep pauses beside any timing/unknown overlapping grant.
 for a in (32,56,80,8):
  if a not in busy and a+1 not in busy:return (a,a+1),{'active_classes':{n:rows.get(n) for n in active},'smt':False}
 if all(rows.get(n) in allowed for n in active):return (128,129),{'active_classes':{n:rows.get(n) for n in active},'smt':True}
 return None,{'refusal':'timing/unknown class when all quarters granted','active_classes':{n:rows.get(n) for n in active}}

def current_admission():
 flags=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags');fill=flags/'FILLERS.md';text=fill.read_text();rows={}
 for line in text.splitlines():
  cells=[c.strip() for c in line.split('|')]
  if len(cells)>9:rows[cells[1]]=cells[9]
 grants=[(p.stem,p.read_text(),p.with_suffix('.ended').exists()) for p in (flags/'grants').glob('*.grant')]
 now=datetime.datetime.now(datetime.timezone.utc);pair,evidence=classify_admission(grants,rows,now)
 evidence.update(timestamp=now.isoformat(),fillers_sha256=hashlib.sha256(text.encode()).hexdigest())
 return pair,evidence
