"""Create-only exposure journal for the EVL44 prospective paired run."""
import hashlib,json,os
from pathlib import Path
from pair_contract import ARMS,model_input,exact

def encoded(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def create(path,record):
 data=encoded(record)
 if len(data)>8*1024*1024:raise ValueError('record exceeds bound')
 with path.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 fd=os.open(path.parent,os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def run(root,campaign,row,arm,invoke):
 if arm not in ARMS or not isinstance(campaign,str) or len(campaign)!=64 or any(c not in '0123456789abcdef' for c in campaign):raise ValueError('identity')
 identity={'campaign_sha256':campaign,'id':row['id'],'arm':arm,'prompt_sha256':hashlib.sha256(row['prompt'].encode()).hexdigest()}
 key=hashlib.sha256(encoded({'campaign_sha256':campaign,'id':row['id'],'arm':arm})).hexdigest();root=Path(root);root.mkdir(parents=True,exist_ok=True);start=root/(key+'.start');end=root/(key+'.end')
 if end.exists():
  data=json.loads(end.read_bytes())
  if data.get('identity')!=identity or data.get('start_sha256')!=hashlib.sha256(start.read_bytes()).hexdigest():raise RuntimeError('journal identity mismatch')
  return data
 if start.exists():raise RuntimeError('unknown in-flight exposure; automatic replay forbidden')
 create(start,{'identity':identity,'exposure':'unknown'})
 # Runtime receives only the prompt; reference answer remains outside model boundary.
 native=invoke(model_input(row))
 if not isinstance(native,dict) or not isinstance(native.get('answer'),str) or type(native.get('delegations')) is not int or native['delegations']<0:raise ValueError('incomplete native evidence')
 record={'identity':identity,'start_sha256':hashlib.sha256(start.read_bytes()).hexdigest(),'status':'complete','native':native,'correct':exact(native['answer'],row['gold'])}
 create(end,record);return record
