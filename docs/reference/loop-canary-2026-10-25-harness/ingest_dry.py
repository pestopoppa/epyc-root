import shutil, hashlib, subprocess, os, json
B="/mnt/raid0/llm/tmp/ws58-canary-20261025"
S="/mnt/raid0/llm/state/vidya"
def sha(p): return hashlib.sha256(open(p,"rb").read()).hexdigest()
for f in ("ledger.jsonl","ledger.jsonl.sync.json"):
    shutil.copy2(f"{S}/{f}", f"{B}/state/ingest/{f}")
cp=f"{B}/state/ingest/ledger.jsonl"
ev={"canon_before":sha(f"{S}/ledger.jsonl"),"copy_before":sha(cp)}
T="/mnt/raid0/llm/tmp/"
ticks=[
("M4.2","pb-hol",T+"f8-launchers-20261023/m4-srpf-pbhol"),
("M4.2a","pb-hol",T+"f8-launchers-20261024/m4-srpf-pbhol-2a"),
("M4.2b","pb-hol",T+"f8-launchers-20261024/m4-2b-champion-control"),
("KPF-17.4c","kv-prefix-fork",T+"f8-launchers-20261024/kpf17-4c-bisect"),
("KPF-18.0b","kv-prefix-fork",T+"overnight-20261020/kpf18-run"),
("KPF-18.0d-item3","kv-prefix-fork",T+"overnight-20261020/kpf18-run-w1c"),
("KPF-18-S1.R4","kv-prefix-fork",T+"f8-launchers-20261024/kpf18-s1-r4"),
("AKX-ALL-26b","ak-width-cells-cpu","/mnt/raid0/llm/epyc-inference-research/artifacts/akx_all_26_cpu_20261020"),
("PB-QCOST-1-confirm","pb-qcost",T+"f8-launchers-20261023/pb-qcost-1-confirm"),
("PB-QCOST-1-confirm-R","pb-qcost",T+"f8-launchers-20261024/pb-qcost-1-confirm-r"),
]
for t,a,p in ticks:
    r=subprocess.run(["/usr/bin/python3","/mnt/raid0/llm/views/epyc-root-main/scripts/vidya/cli.py","--ledger",cp,"--json","ingest",a,"--path",p,"--dry-run","--as-of","2026-10-25T00:00:00Z"],capture_output=True,text=True)
    open(f"{B}/ingest/{t}.out","w").write(f"adapter={a} path={p} rc={r.returncode}\n--stdout--\n{r.stdout}\n--stderr--\n{r.stderr}\n")
    try:
        j=json.loads(r.stdout); print(t,a,"rc",r.returncode,{k:(len(v) if isinstance(v,list) else v) for k,v in j.items() if k in("units_matched","units_projected","declined","refused","missing","rows_projected","frames_emitted")}, [x["reason"][:150] for x in j.get("refused",[])][:2])
    except Exception: print(t,a,"rc",r.returncode,r.stderr[-300:])
ev.update(canon_after=sha(f"{S}/ledger.jsonl"),copy_after=sha(cp))
print(ev)
