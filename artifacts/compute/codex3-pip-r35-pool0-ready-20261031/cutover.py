from pathlib import Path
import os,json,hashlib,datetime,sys,runpy
D=Path('/mnt/raid0/llm/tmp/codex3-pip-pool0-merged-r35-20261031-0650');F=Path('/mnt/raid0/llm/tmp/compute-flags');R=F/'ready';old='codex3-pip02-paddle-relocatable-r33-pool0-20261031';new='codex3-pip02-paddle-relocatable-r35-pool0-20261031';src=R/(old+'.json');armed=R/'armed'/(old+'.json');grant=F/'grants'/(old+'.grant');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();expected='ad2b352c68b0659a4618d5209189c044b968757dfdfb9475705bf154dbb595f5'
assert src.is_file() and sha(src)==expected and not armed.exists() and not grant.exists();assert not (R/(new+'.json')).exists();assert sha(D/'launch-p0.sh')=='19359800db1b0a88f21a23947836b91efc0a5ed080f02163aeab417cb236fab8';assert sha(D/'source.sha256')=='85ef3757d55b5b9127e24cb4250fae265819317140789425311c299e066c28d6'
archive=R/'withdrawn'/'codex3-r33-r35-pool0-cutover-20261031';archive.mkdir(exist_ok=False);dest=archive/(old+'.json');os.rename(src,dest);assert sha(dest)==expected
if armed.exists() or grant.exists():raise RuntimeError('old R33 acquired ownership during cutover: new READY not published')
sys.path.insert(0,'/mnt/micron/codex3-pip-pool0-merged-r35-20261031');import pool
pool.POOL_LOCKED=True;os.environ['FILLER_ID']=new
assert pool.old_r27_retired();conflicts={n:pool.active_group(n) for n in (5,17,29,41,53,65,77,89,101,113,125,137,149)};assert not any(conflicts.values()),conflicts
receipt={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'old_id':old,'archived_ready':str(dest),'old_sha256':expected,'new_id':new,'armed_absent_after':not armed.exists(),'native_grant_absent_after':not grant.exists(),'reason':'qualified merged successor, no native R33 exposure','old_controls_retained':True};(D/'SUPERSESSION.json').write_text(json.dumps(receipt,indent=2)+'\n')
runpy.run_path(str(D/'publish.py'),run_name='__main__')
