"""Bind new prospective packet to unchanged tracked current orchestrator checkout."""
import hashlib,json,subprocess
from pathlib import Path
from source_closure import inventory
p=Path(__file__).parent;repo='/mnt/micron/codex3-lanes/orchestrator';sha=lambda x:hashlib.sha256(x).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',repo,*args],text=True).strip()
head=git('rev-parse','HEAD');assert head=='b0f8613d65f30986f147e5467b1c66892c887ce5';assert not git('status','--porcelain','--untracked-files=no')
inv=inventory();assert git('rev-parse','HEAD')==head and not git('status','--porcelain','--untracked-files=no')
raw=json.dumps(inv,sort_keys=True,indent=2).encode()+b'\n';(p/'LOCAL-SOURCE-INVENTORY.json').write_bytes(raw)
f=p/'PREDECLARATION-FROZEN.json';old=sha(f.read_bytes());dec=json.loads(f.read_bytes());dec['inventory_sha256']=sha(raw);dec['orchestrator_observed_commit']=head;dec['orchestrator_repl_executor_sha256']=sha(Path(repo+'/src/api/routes/chat_pipeline/repl_executor.py').read_bytes());dec['runtime_source_note']='Fresh prospective run pins current native source; it differs from immutable R11. Exact inventory and source manifest determine execution.';f.write_text(json.dumps(dec,sort_keys=True,indent=2,ensure_ascii=False)+'\n');new=sha(f.read_bytes())
m=p/'FROZEN-PROMPT-MANIFEST.json';oldm=sha(m.read_bytes());d=json.loads(m.read_bytes());d['declaration_sha256']=new;m.write_text(json.dumps(d,sort_keys=True,indent=2,ensure_ascii=False)+'\n');newm=sha(m.read_bytes());j=p/'sealed_journal.py';s=j.read_text();assert old in s and oldm in s;j.write_text(s.replace(old,new).replace(oldm,newm));print(json.dumps({'head':head,'source_inventory_files':len(inv),'inventory_sha256':sha(raw),'repl_executor_sha256':dec['orchestrator_repl_executor_sha256'],'declaration_sha256':new,'manifest_sha256':newm}))
