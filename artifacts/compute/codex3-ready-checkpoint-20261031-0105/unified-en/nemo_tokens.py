"""Validate native token IDs against raw transcript; preserve unknowns, separate language tags."""
import json,pathlib,re
V=json.loads((pathlib.Path(__file__).resolve().parent/'vocab.json').read_text());pieces=V['pieces'];types=V['types'];unk=V['unk_id']
if len(pieces)!=len(types) or pieces[unk]!='<unk>':raise ValueError('vocab drift')
def decode(ids):
 b=bytearray()
 for ident in ids:
  p=pieces[ident]
  if re.fullmatch(r'<0x[0-9A-Fa-f]{2}>',p):b.append(int(p[3:5],16))
  else:b.extend(p.replace('▁',' ').encode())
 return re.sub(r' +',' ',b.decode('utf-8')).strip(' ')
def parse(stdout,native_txt):
 lines=stdout.splitlines();start=[i for i,x in enumerate(lines) if re.fullmatch(r'CS8_NEMO_TOKENS \d+',x)]
 if len(start)!=1:raise ValueError('missing or duplicate token witness')
 completed=[re.fullmatch(r'CS8_NEMO_COMPLETED raw_count=(\d+)',x) for x in lines];completed=[x for x in completed if x]
 if len(completed)!=1:raise ValueError('missing or duplicate completion witness')
 i=start[0];n=int(lines[i].split()[-1]);i+=1;ids=[]
 if int(completed[0].group(1))!=n:raise ValueError('completion count mismatch')
 for index in range(n):
  while i<len(lines) and not lines[i].startswith('CS8_NEMO_TOKEN '):
   if lines[i]=='CS8_NEMO_TOKENS_END':raise ValueError('early token witness end')
   i+=1
  if i>=len(lines) or not (m:=re.fullmatch(r'CS8_NEMO_TOKEN (\d+) (\d+)',lines[i])) or int(m.group(1))!=index:raise ValueError('bad token witness')
  ident=int(m.group(2))
  if ident>=len(pieces):raise ValueError('token outside vocab')
  ids.append(ident);i+=1
 if i>=len(lines) or lines[i]!='CS8_NEMO_TOKENS_END':
  while i<len(lines) and not lines[i].startswith('CS8_NEMO_'):i+=1
  if i>=len(lines) or lines[i]!='CS8_NEMO_TOKENS_END':raise ValueError('missing witness end')
 raw=decode(ids)
 if raw!=native_txt.strip():raise ValueError('native transcript/token mismatch')
 unknown=[j for j,x in enumerate(ids) if x==unk or types[x]==2 or pieces[x]=='<unk>']
 controls=[j for j,x in enumerate(ids) if j not in unknown and (types[x]==3 or re.fullmatch(r'<[a-z]{2,3}-[A-Za-z]{2,4}>',pieces[x]))]
 keep=[x for j,x in enumerate(ids) if j not in controls]
 return {'token_ids':ids,'unk_positions':unknown,'unk_count':len(unknown),'control_positions':controls,'language_tags':[pieces[ids[j]] for j in controls if re.fullmatch(r'<[a-z]{2,3}-[A-Za-z]{2,4}>',pieces[ids[j]])],'hypothesis_with_unk':decode(keep)}
