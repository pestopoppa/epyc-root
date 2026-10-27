#!/usr/bin/env python3
"""Read-only native C72 mini-graph diagnostic; only paths/CPU differ from packet."""
import json, os, pathlib, shutil, subprocess, time
root=pathlib.Path('/mnt/raid0/llm/tmp/codex-ni-20261027-gnx-split-phase')
packet=root/'stage2-packet'; test=root/'stage2-fixture-v2'; test.mkdir(exist_ok=False)
(test/'registry').mkdir(); (test/'results').mkdir()
old=pathlib.Path('/mnt/raid0/llm/tmp/codex-ni-20261027-c5-graph-call-edge-repair')
entries=json.loads((old/'catalog/registry.json').read_text())
selected=[x for x in entries if x['name']=='edge-repair-c72-mini']; assert len(selected)==1
(test/'registry/registry.json').write_text(json.dumps(selected))
source=(packet/'readonly-query.cjs').read_text().replace(str(root/'stage1-state/registry'),str(test/'registry'))
(test/'readonly-query.cjs').write_text(source)
shutil.copyfile(packet/'targets.tsv',test/'targets.tsv')
shutil.copyfile(packet/'graph-result.py',test/'graph-result.py')
sent=(packet/'sentinels.py').read_text()
sent=sent.replace("P=ROOT/'stage2-packet'; TREE=ROOT/'source-view'; OUT=ROOT/'stage2-results'",f"P=pathlib.Path({str(test)!r}); TREE=pathlib.Path({str(old/'c72-mini')!r}); OUT=P/'results'")
sent=sent.replace("CATALOG=ROOT/'stage1-state/registry/registry.json'",f"CATALOG=pathlib.Path({str(test/'registry/registry.json')!r})")
sent=sent.replace('{72,73}','{0,1}')
assert "P=ROOT/'stage2-packet'" not in sent and '{72,73}' not in sent
(test/'sentinels.py').write_text(sent)
env=dict(os.environ, FILLER_END=str(int(time.time())+600), FILLER_DEADLINE=str(int(time.time())+510))
p=subprocess.run(['/usr/bin/python3','-I','-B',str(test/'sentinels.py')],env=env)
if p.returncode: raise SystemExit(p.returncode)
print('C72_MINI_NATIVE_READONLY_FIXTURE_PASS')
