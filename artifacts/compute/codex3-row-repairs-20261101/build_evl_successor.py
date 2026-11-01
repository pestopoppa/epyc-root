from pathlib import Path
import hashlib,shutil,json,re,os
old=Path('/mnt/raid0/llm/tmp/codex3-evl34-r11-budget-v7-ab-20261030'); new=Path('/mnt/raid0/llm/tmp/codex3-row-repairs-20261101/evl-successor');new.mkdir(exist_ok=False)
entries=[]
for line in (old/'CAMPAIGN-SOURCES.sha256').read_text().splitlines():
 sha,name=line.split('  ',1);src=Path(name);rel=src.relative_to(old);dst=new/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);entries.append(rel)
shutil.copy2(old/'launch_campaign.sh',new/'launch_campaign.sh')
# The only semantic source edit is digest-preserving custody remap; all old output paths are successor-private.
closure=(Path('/mnt/raid0/llm/tmp/codex3-row-repairs-20261101/source_closure.py')).read_bytes();(new/'source_closure.py').write_bytes(closure)
for rel in entries+[Path('launch_campaign.sh')]:
 p=new/rel
 if p.suffix not in ('.py','.sh'):continue
 s=p.read_text();s=s.replace(str(old),str(new)).replace('/mnt/micron/codex3-evl34-r11-budget-v7-ab-20261030','/mnt/micron/codex3-evl34-r11-budget-v8-custody-20261101')
 if rel.name=='launch_campaign.sh':
  s=s.replace('export EVL34_EXTRA_HEADROOM_BYTES\n','export EVL34_EXTRA_HEADROOM_BYTES\nEVL34_REQUIREMENTS_FREEZE=/mnt/micron/codex3-lanes/root/artifacts/compute/codex3-row-repairs-20261101/requirements-freeze.txt\nexport EVL34_REQUIREMENTS_FREEZE\n')
  s=s.replace('EVL34_EXTRA_HEADROOM_BYTES,EVL34_PREFLIGHT_LOG /usr/bin/chroot','EVL34_EXTRA_HEADROOM_BYTES,EVL34_PREFLIGHT_LOG,EVL34_REQUIREMENTS_FREEZE /usr/bin/chroot').replace('/usr/bin/env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3','/usr/bin/env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 EVL34_REQUIREMENTS_FREEZE="$EVL34_REQUIREMENTS_FREEZE" /usr/bin/python3')
  # This packet is deliberately not schedulable until canonical LOOP49 engine is available.
  s=s.replace('codex3-evl34-r11-budget-v7-ab-20261030','codex3-evl34-r11-budget-v8-custody-20261101')
 p.write_text(s)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
cat=new/'CAMPAIGN-SOURCES.sha256';cat.write_text(''.join(f'{sha(new/r)}  {new/r}\n' for r in entries));launch=new/'launch_campaign.sh';s=launch.read_text();s=re.sub(r'EXPECTED_CATALOG_SHA256=[0-9a-f]{64}',f'EXPECTED_CATALOG_SHA256={sha(cat)}',s);launch.write_text(s)
(new/'PACKET.sha256').write_text(f'{sha(cat)}  {cat}\n{sha(launch)}  {launch}\n')
(new/'CUSTODY-PREPARATION.json').write_text(json.dumps({'schema':'evl34-custody-successor/v1','state':'UNQUALIFIED_NOT_READY','original_run':'codex3-evl34-r11-budget-v7-ab-20261030','source_manifest_sha256':sha(cat),'launcher_sha256':sha(launch),'requirements_freeze_git_path':'artifacts/compute/codex3-row-repairs-20261101/requirements-freeze.txt','requirements_freeze_sha256':'f133fc7fe76c72e24d294dfa1bee242d70375841959782ce78b80841cd0f9111','model_or_inference_ran':False,'canonical_engine_required':True,'loop49_qualification_required':True},indent=2)+'\n')
print('catalog',sha(cat),'launcher',sha(launch),'members',len(entries))
