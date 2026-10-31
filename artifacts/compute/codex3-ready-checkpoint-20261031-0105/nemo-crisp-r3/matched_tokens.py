"""Recover complete native nonblank IDs and strip only checkpoint locale-control IDs."""
import json,pathlib,re
V=json.loads((pathlib.Path(__file__).resolve().parent/'vocab.json').read_text());pieces=V['pieces'];types=V['types'];unk=V['unk_id']
if len(pieces)!=len(types) or pieces[unk]!='<unk>':raise ValueError('vocab drift')
def native(ids):
 s=''.join(pieces[x].replace('▁',' ') for x in ids)
 return s[1:] if s.startswith(' ') else s
def strip_lang_tags(s):
 out='';i=0
 while i<len(s):
  m=re.match(r'<[a-z]{2,3}-[A-Z]{2}>',s[i:])
  if m:
   i+=len(m.group())
   if out.endswith(' ') and i<len(s) and s[i]==' ':i+=1
  else:out+=s[i];i+=1
 return out.rstrip(' ')
def parse(stdout,native_txt):
 lines=stdout.splitlines();start=[i for i,x in enumerate(lines) if re.fullmatch(r'CS8_MATCHED_NEMO_TOKENS \d+',x)]
 if len(start)!=1:raise ValueError('missing or duplicate token witness')
 i=start[0];n=int(lines[i].split()[-1]);i+=1;ids=[]
 for index in range(n):
  if i>=len(lines) or not (m:=re.fullmatch(r'CS8_MATCHED_NEMO_TOKEN (\d+) (\d+)',lines[i])) or int(m.group(1))!=index:raise ValueError('token witness mismatch')
  ident=int(m.group(2));
  if ident>=len(pieces):raise ValueError('token outside vocabulary')
  ids.append(ident);i+=1
 if i>=len(lines) or lines[i]!='CS8_MATCHED_NEMO_TOKENS_END':raise ValueError('missing token witness end')
 raw=native(ids)
 if raw.strip()!=native_txt.strip():raise ValueError('native transcript/token mismatch')
 return {'token_ids':ids,'unk_positions':[i for i,x in enumerate(ids) if x==unk or pieces[x]=='<unk>'],'unk_count':sum(x==unk or pieces[x]=='<unk>' for x in ids),'language_tags':[{'position':i,'tag':pieces[x]} for i,x in enumerate(ids) if re.fullmatch(r'<[a-z]{2,3}-[A-Z]{2}>',pieces[x])],'hypothesis_with_unk':strip_lang_tags(raw)}
