import json, os, subprocess, sys, tempfile
from pathlib import Path
base=Path('/mnt/raid0/llm/tmp/brf-exp09-resume-r5');os.environ['EXP09_WORKDIR']=str(base);sys.path.insert(0,str(base));import job
with tempfile.TemporaryDirectory() as tmp:
 job.RES=str(Path(tmp)/'results.jsonl')
 got,dups,bad=job.done_cells();assert len(got)==24 and not dups and not bad and all(arm=='control' for _,arm in got)
 duplicate=next(iter(got.values()));Path(job.RES).write_text(json.dumps(duplicate)+'\n')
 _,dups,bad=job.done_cells();assert dups==[(duplicate['item'],'control')] and not bad
 dry=Path(tmp)/'dry.jsonl';script=base/'smoke_predicate.py'
 dry.write_text(json.dumps({'kind':'cell','arm':'control','dryrun':False,'exec_id':'old'})+'\n')
 assert subprocess.run([sys.executable,str(script),str(dry)]).returncode!=0
 dry.write_text(json.dumps({'kind':'cell','arm':'verified_quote','dryrun':True,'exec_id':'new'})+'\n')
 assert subprocess.run([sys.executable,str(script),str(dry)]).returncode==0
print('R5 seed loading, duplicate rejection, and fresh-treatment smoke predicate: PASS')
