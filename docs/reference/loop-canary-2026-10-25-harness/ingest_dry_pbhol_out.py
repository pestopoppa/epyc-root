import subprocess, json, hashlib
B="/mnt/raid0/llm/tmp/ws58-canary-20261025"; T="/mnt/raid0/llm/tmp/"
cp=B+"/state/ingest/ledger.jsonl"
for t,p in [("M4.2-out",T+"f8-launchers-20261023/m4-srpf-pbhol/out"),("M4.2a-out",T+"f8-launchers-20261024/m4-srpf-pbhol-2a/out"),("M4.2b-out",T+"f8-launchers-20261024/m4-2b-champion-control/out")]:
    r=subprocess.run(["/usr/bin/python3","/mnt/raid0/llm/views/epyc-root-main/scripts/vidya/cli.py","--ledger",cp,"--json","ingest","pb-hol","--path",p,"--dry-run","--as-of","2026-10-25T00:00:00Z"],capture_output=True,text=True)
    open(f"{B}/ingest/{t}.out","w").write(r.stdout+r.stderr)
    j=json.loads(r.stdout); print(t,{k:(len(v) if isinstance(v,list) else v) for k,v in j.items() if k in("units_matched","units_projected","declined","refused","rows_projected","frames_emitted")},[x["reason"][:200] for x in j["refused"]][:2],j["declined"][:3])
for f in (cp,"/mnt/raid0/llm/state/vidya/ledger.jsonl"): print(hashlib.sha256(open(f,"rb").read()).hexdigest())
