import os, sys, json, numpy as np, time
os.environ["RETIME"]="1"
sys.path.insert(0,"/mnt/raid0/llm/tmp/emb-speed-20261020")
import bench as B
# headline configs from first pass (best cfg) ; ABA, 3 reps, 256 chunks; queries 200 x 3 at threads 4 and 16
ms={}
ms["bge"]=B.M("bge","st",B.BG,qp=B.BG_QP)
ms["eg2_fp32"]=B.M("eg2_fp32","st",B.EG,dp=B.EG_DP,qp=B.EG_QP)
ms["eg2_bf16"]=B.M("eg2_bf16","st",B.EG,dtype=B.torch.bfloat16,dp=B.EG_DP,qp=B.EG_QP)
cfgs=json.loads(sys.argv[1])  # {"bge":[bs,th],...}
sub=B.chunks[:256]
for k,(bs,th) in cfgs.items():
    B.setthreads(th); ms[k].enc(sub,bs)
for rep in range(3):
    for k in (list(cfgs) if rep%2==0 else list(cfgs)[::-1]):
        bs,th=cfgs[k]; B.setthreads(th); m=ms[k]
        _,dt,c0,c1=B.timed(lambda: m.enc(sub,bs)); toks=m.ntok(sub,m.dp)
        B.row(phase="retime_grid",model=k,batch=bs,threads=th,n_chunks=256,rep=rep,wall_s=dt,chunks_per_s=256/dt,tokens_per_s=toks/dt,ctx0=c0,ctx1=c1,t_start=c0["t"],t_end=c1["t"])
for th in (4,16):
    B.setthreads(th)
    for rep in range(3):
        for k in (["bge","eg2_fp32","eg2_bf16"] if rep%2==0 else ["eg2_bf16","eg2_fp32","bge"]):
            m=ms[k]; c0=B.ctx(); lat=[]
            for q in B.queries:
                t=time.perf_counter(); m.enc([q],1,prompt=m.qp); lat.append((time.perf_counter()-t)*1000)
            c1=B.ctx(); a=np.array(lat)
            B.row(phase="retime_query",model=k,threads=th,rep=rep,n=len(a),p50_ms=float(np.percentile(a,50)),p95_ms=float(np.percentile(a,95)),max_ms=float(a.max()),ctx0=c0,ctx1=c1,t_start=c0["t"],t_end=c1["t"])
