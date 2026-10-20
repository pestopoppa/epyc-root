# prioritised continuation (coordinator reprioritisation 2026-10-20). Appends to results.jsonl.
import os, sys, json, time, numpy as np, statistics as st
sys.path.insert(0,"/mnt/raid0/llm/tmp/emb-speed-20261020")
import bench as B
from bench import row, ctx, timed
ms=B.build(); ms["bge_b"]=ms["bge"]
m_st=["bge","eg2_fp32","eg2_bf16"]
row(phase="run2_start",note="continuation after killing first run mid th=4; subsets: bs1->64, others->256 chunks (<=512 cap)",ctx=ctx(),cpus=B.CPUS)
for k,m in ms.items():
    if k!="bge_b": row(phase="load2",model=k,load_s=m.load_s,rss_delta_mb=m.rss_load,dtype=m.dtype,ctx=ctx())
def grid(th,bs,n=256,run=m_st,tag="grid"):
    sub=B.chunks[:n]; B.setthreads(th)
    for k in run: ms[k].enc(sub,bs)
    for rep in range(3):
        for k in (run if rep%2==0 else run[::-1]):
            m=ms[k]; _,dt,c0,c1=timed(lambda: m.enc(sub,bs)); toks=m.ntok(sub,m.dp)
            row(phase=tag,model=k,batch=bs,threads=th,n_chunks=n,rep=rep,wall_s=dt,chunks_per_s=n/dt,tokens_per_s=toks/dt,ctx0=c0,ctx1=c1,t_start=c0["t"],t_end=c1["t"])
def queries(th):
    B.setthreads(th); run=["bge","eg2_fp32","eg2_bf16"]
    for k in run: ms[k].enc(B.queries[:20],1,prompt=ms[k].qp)
    for rep in range(3):
        for k in (run if rep%2==0 else run[::-1]):
            m=ms[k]; c0=ctx(); lat=[]
            for q in B.queries:
                t=time.perf_counter(); m.enc([q],1,prompt=m.qp); lat.append((time.perf_counter()-t)*1000)
            c1=ctx(); a=np.array(lat)
            row(phase="query",model=k,threads=th,rep=rep,n=len(a),p50_ms=float(np.percentile(a,50)),p95_ms=float(np.percentile(a,95)),max_ms=float(a.max()),ctx0=c0,ctx1=c1,t_start=c0["t"],t_end=c1["t"])
# P1 headline
grid(16,32,run=["bge","eg2_fp32","eg2_bf16","bge_b"]); grid(16,8)
grid(48,32); grid(48,8)
queries(4); queries(16)
row(phase="interim_marker",ctx=ctx())
# P2 rest
grid(16,128); grid(4,32,n=128)
for bs in (8,32,128):
    for k in ["potion_code","potion_base"]:
        m=ms[k]; m.enc(B.chunks[:256],bs)
        for rep in range(3):
            _,dt,c0,c1=timed(lambda: m.enc(B.chunks,bs)); toks=m.ntok(B.chunks,"")
            row(phase="grid",model=k,batch=bs,threads="n/a(single)",n_chunks=len(B.chunks),rep=rep,wall_s=dt,chunks_per_s=len(B.chunks)/dt,tokens_per_s=toks/dt,ctx0=c0,ctx1=c1,t_start=c0["t"],t_end=c1["t"])
for k in ["potion_code","potion_base"]:
    for rep,th in ((0,"single"),):
        m=ms[k]; v,dt,c0,c1=timed(lambda: m.enc(B.chunks,128))
        row(phase="index_build",model=k,batch=128,threads="single",n_chunks=len(B.chunks),rep=0,wall_s=dt,chunks_per_s=len(B.chunks)/dt,ctx0=c0,ctx1=c1,t_start=c0["t"],t_end=c1["t"])
# index build at best cfg among new th>=16 legs
rows=[json.loads(l) for l in open(B.OUT)]; g={}
for r in rows:
    if r["phase"]=="grid" and r["model"] in m_st and r["threads"] in (16,48) and r["batch"]>1: g.setdefault((r["model"],r["batch"],r["threads"]),[]).append(r["chunks_per_s"])
cfg={}
for k in m_st:
    c=max([x for x in g if x[0]==k],key=lambda x: st.median(g[x])); cfg[k]=(c[1],c[2])
row(phase="best_cfg",cfg={k:list(v) for k,v in cfg.items()})
for rep in range(2):
    for k in (m_st if rep==0 else m_st[::-1]):
        bs,th=cfg[k]; B.setthreads(th); m=ms[k]
        if rep==0: m.enc(B.chunks[:64],bs)
        v,dt,c0,c1=timed(lambda: m.enc(B.chunks,bs))
        row(phase="index_build",model=k,batch=bs,threads=th,n_chunks=len(B.chunks),rep=rep,wall_s=dt,chunks_per_s=len(B.chunks)/dt,finite=bool(np.isfinite(v).all()),dim=int(v.shape[1]),ctx0=c0,ctx1=c1,t_start=c0["t"],t_end=c1["t"])
row(phase="run2_end",ctx=ctx())
