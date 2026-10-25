import shutil, subprocess
from pathlib import Path
B=Path("/mnt/raid0/llm/tmp/ws58-canary-20261025"); S=Path("/mnt/raid0/llm/state/vidya"); d=B/"state"/"A3-views-newindex"
d.mkdir(parents=True, exist_ok=True)
for f in ("ledger.jsonl","ledger.jsonl.sync.json"): shutil.copy2(S/f, d/f)
for x in ("loop-memo","loop-known-good"):
    if (d/x).exists(): shutil.rmtree(d/x)
    shutil.copytree(S/x, d/x)
head=subprocess.run(["git","-C","/mnt/raid0/llm/views/epyc-root-main","rev-parse","HEAD"],capture_output=True,text=True).stdout.strip()
idx=subprocess.run(["git","-C","/mnt/raid0/llm/views/epyc-root-main","show",f"{head}:research/intake_index.yaml"],capture_output=True,check=True).stdout
(B/"index"/f"intake_index.views-{head[:9]}.yaml").write_bytes(idx); print(head)
