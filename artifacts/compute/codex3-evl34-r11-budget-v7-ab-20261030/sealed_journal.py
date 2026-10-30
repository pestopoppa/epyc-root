"""Predeclared population admission around create-only exposure journal.

No native execution occurs here; caller must separately prove all route gates.
"""
import hashlib,json
from pathlib import Path
from paired_journal import run,create,encoded
from prompt_projection import project
BASE=Path(__file__).parent
DECL='f6ef91a8f85c040736e1c0ba779bfec6f993131a8b2326fedc952f4362414ae5'
MANIFEST='495762cf977bf0123a3bfc124e06cab61abb7347a9399ee72a6ea71036c1a761'
def read_checked(path,expected):
 data=path.read_bytes()
 if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('sealed input drift')
 return json.loads(data)
def invoke_cell(root,row,arm,cohort,invoke):
 dec=read_checked(BASE/'PREDECLARATION-FROZEN.json',DECL)
 manifest=read_checked(BASE/'FROZEN-PROMPT-MANIFEST.json',MANIFEST)
 if manifest['declaration_sha256']!=DECL:raise ValueError('declaration mismatch')
 if cohort=='pilot': items=manifest['pilot'];declared=dec['pilot']
 elif cohort=='control':items=[manifest['control']];declared=[dec['independent_smoke_control']]
 else:raise ValueError('unknown cohort')
 match=[x for x in items if x['id']==row.get('id')]
 if len(match)!=1 or not any(x['id']==row['id'] and x['row_sha256']==match[0]['row_sha256'] for x in declared):raise ValueError('unselected cell')
 raw=json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
 if hashlib.sha256(raw).hexdigest()!=match[0]['row_sha256']:raise ValueError('source row drift')
 prompt=project(row)
 if hashlib.sha256(prompt.encode()).hexdigest()!=match[0]['prompt_sha256']:raise ValueError('prompt drift')
 if not isinstance(row.get('answer'),str):raise ValueError('missing source answer')
 def checked(payload):
  native=invoke(payload)
  key=hashlib.sha256(encoded({'campaign_sha256':DECL,'id':row['id'],'arm':arm})).hexdigest()
  create(Path(root)/(key+'.native'),{'campaign_sha256':DECL,'id':row['id'],'arm':arm,'native':native})
  if not isinstance(native,dict) or native.get('status')!='complete' or native.get('flat_server_bound_attested') is not True:
   raise ValueError('native result lacks completed route and flat-server bound')
  if not isinstance(native.get('answer'),str) or native['answer'].lstrip().startswith('[ERROR:'):
   raise ValueError('native answer is missing or infrastructure error')
  if native.get('max_depth') not in (0,1) or type(native.get('max_depth')) is not int:
   raise ValueError('native depth unknown or out of scope')
  return native
 return run(root,DECL,{'id':row['id'],'prompt':prompt,'gold':row['answer']},arm,checked)
