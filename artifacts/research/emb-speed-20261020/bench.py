import os, sys, json, time, gc, re, subprocess, glob, statistics as st
import numpy as np, torch
W="/mnt/raid0/llm/tmp/emb-speed-20261020"; HUB=W+"/hf/hub/"
SMOKE=os.environ.get("SMOKE")=="1"
OUT=W+("/smoke.jsonl" if SMOKE else ("/results_retime.jsonl" if os.environ.get("RETIME") else "/results.jsonl"))
EG=HUB+"models--google--embeddinggemma-2/snapshots/914f7f89142e33e77833254d9c9b90c3cef7303b"
BG=HUB+"models--BAAI--bge-large-en-v1.5/snapshots/d4aa6901d3a41ba39fb536a557fa166f842b0e09"
PC=HUB+"models--minishlab--potion-code-16M-v2/snapshots/e9d2a44ca6a05ac6685f3b23709ea57eb7352d5b"
PB=HUB+"models--minishlab--potion-base-8M/snapshots/bf8b056651a2c21b8d2565580b8569da283cab23"
EG_DP="title: none | text: "; EG_QP="task: search result | query: "; BG_QP="Represent this sentence for searching relevant passages: "
CPUS=sorted(os.sched_getaffinity(0))
chunks=[json.loads(l)["text"] for l in open(W+"/corpus.jsonl")]; queries=json.load(open(W+"/queries.json"))
if SMOKE: chunks=chunks[:64]; queries=queries[:10]
def rss(): return int(re.search(r"VmRSS:\s+(\d+)",open("/proc/self/status").read()).group(1))//1024
def ctx():
    d={"t":time.time()}
    try:
        o=subprocess.run(["rocm-smi","--showuse"],capture_output=True,text=True,timeout=20).stdout
        m=re.search(r"GPU use \(%\):\s*(\d+)",o); d["gpu_use_pct"]=int(m.group(1)) if m else None
    except Exception as e: d["gpu_use_pct"]=None
    try: d["kfd_procs"]=len(os.listdir("/sys/class/kfd/kfd/proc"))
    except Exception: d["kfd_procs"]=None
    d["load1"]=float(open("/proc/loadavg").read().split()[0])
    fs=[]
    for c in CPUS[::4]:
        try: fs.append(int(open(f"/sys/devices/system/cpu/cpu{c}/cpufreq/scaling_cur_freq").read())/1000)
        except Exception: pass
    d["mhz_mean"]=round(sum(fs)/len(fs),0) if fs else None
    return d
fo=open(OUT,"a")
def row(**r):
    fo.write(json.dumps(r)+"\n"); fo.flush()
from sentence_transformers import SentenceTransformer
from model2vec import StaticModel
class M:  # uniform wrapper
    def __init__(s,name,kind,path,dtype=None,dp="",qp=""):
        s.name,s.kind,s.dp,s.qp=name,kind,dp,qp
        gc.collect(); r0=rss(); t=time.perf_counter()
        if kind=="st":
            kw={"model_kwargs":{"torch_dtype":dtype or torch.float32}}
            s.m=SentenceTransformer(path,device="cpu",**kw); s.m.max_seq_length=512 if s.m.max_seq_length is None else s.m.max_seq_length
            s.tok=s.m.tokenizer
            ps=[p for p in s.m.parameters()]; s.dtype=str(ps[0].dtype); s.nparams=sum(p.numel() for p in ps)
        else:
            s.dtype="float32/static"; s.nparams=None; s.m=StaticModel.from_pretrained(path); s.tok=None
        s.load_s=time.perf_counter()-t; s.rss_load=rss()-r0
    def enc(s,texts,bs,prompt=None,norm=True):
        p=(prompt if prompt is not None else s.dp)
        if s.kind=="st":
            return s.m.encode(texts,batch_size=bs,prompt=p or None,convert_to_numpy=True,normalize_embeddings=norm,show_progress_bar=False)
        v=s.m.encode([p+x for x in texts],batch_size=bs,show_progress_bar=False)
        v=np.asarray(v,dtype=np.float32)
        return v/np.maximum(np.linalg.norm(v,axis=1,keepdims=True),1e-12) if norm else v
    def ntok(s,texts,prompt=""):
        if s.kind=="st": return sum(len(x) for x in s.tok([prompt+t for t in texts],add_special_tokens=True)["input_ids"])
        return sum(len(x.ids) for x in s.m.tokenizer.encode_batch([prompt+t for t in texts]))
def build():
    ms={}
    ms["bge"]=M("bge","st",BG,qp=BG_QP)
    ms["eg2_fp32"]=M("eg2_fp32","st",EG,dp=EG_DP,qp=EG_QP)
    ms["eg2_bf16"]=M("eg2_bf16","st",EG,dtype=torch.bfloat16,dp=EG_DP,qp=EG_QP)
    ms["potion_code"]=M("potion_code","m2v",PC); ms["potion_base"]=M("potion_base","m2v",PB)
    return ms
def setthreads(t): torch.set_num_threads(t)
def timed(fn):
    c0=ctx(); t=time.perf_counter(); r=fn(); dt=time.perf_counter()-t; c1=ctx(); return r,dt,c0,c1
def main():
    man={"cpus":CPUS,"cpu_model":open("/proc/cpuinfo").read().split("model name\t: ")[1].split("\n")[0],
      "env":{k:v for k,v in os.environ.items() if k.startswith(("OMP","MKL","KMP","TORCH","HF_"))},
      "torch":torch.__version__,"torch_threads_default":torch.get_num_threads(),"start":ctx(),"smoke":SMOKE}
    import sentence_transformers, transformers, model2vec, importlib.metadata as im
    man["versions"]={"sentence_transformers":sentence_transformers.__version__,"transformers":transformers.__version__,"model2vec":im.version("model2vec"),"numpy":np.__version__}
    ms=build()
    for k,m in ms.items(): row(phase="load",model=k,load_s=m.load_s,rss_delta_mb=m.rss_load,dtype=m.dtype,nparams=m.nparams,rss_total_mb=rss(),ctx=ctx())
    # token counts
    tk={}
    for k,m in ms.items():
        n=m.ntok(chunks,m.dp); tk[k]={"tokens_total_chunks":n,"tokens_per_chunk":n/len(chunks)}
        row(phase="tokens",model=k,**tk[k])
    # sanity
    setthreads(16)
    sub=chunks[:200]; ref={}
    for k,m in ms.items():
        v=m.enc(sub,32); ref[k]=v
        row(phase="sanity",model=k,dim=int(v.shape[1]),finite=bool(np.isfinite(v).all()),norm_min=float(np.linalg.norm(v,axis=1).min()),norm_max=float(np.linalg.norm(v,axis=1).max()))
    c=(ref["eg2_fp32"]*ref["eg2_bf16"]).sum(1)/(np.linalg.norm(ref["eg2_fp32"],axis=1)*np.linalg.norm(ref["eg2_bf16"],axis=1))
    row(phase="sanity_bf16_vs_fp32",cos_mean=float(c.mean()),cos_min=float(c.min()),n=len(c))
    v=ref["eg2_fp32"][:,:256]; v=v/np.linalg.norm(v,axis=1,keepdims=True)
    row(phase="sanity_mrl256",dim=256,norm_min=float(np.linalg.norm(v,axis=1).min()),norm_max=float(np.linalg.norm(v,axis=1).max()),finite=bool(np.isfinite(v).all()))
    st_models=["bge","eg2_fp32","eg2_bf16"]; allm=list(ms)
    # ---- grid
    BS=[1,8,32,128]; TH=[1,4,16,48]
    if SMOKE: BS=[1,8]; TH=[1,4]
    best={}
    for th in TH:
        for bs in BS:
            if th==48 and bs<32: continue
            n=16 if th==1 else (64 if bs==1 else 256)
            if SMOKE: n=8
            sub=chunks[:n]
            run=[k for k in st_models]
            if th==16 and bs==32: run=["bge","eg2_fp32","eg2_bf16","bge_b"]
            setthreads(th)
            for k in run:  # warmup
                ms.get(k,ms["bge"]).enc(sub,bs)
            for rep in range(3):
                order=run if rep%2==0 else run[::-1]
                for k in order:
                    m=ms.get(k,ms["bge"])
                    _,dt,c0,c1=timed(lambda: m.enc(sub,bs))
                    toks=m.ntok(sub,m.dp)
                    row(phase="grid",model=k,batch=bs,threads=th,n_chunks=n,rep=rep,wall_s=dt,chunks_per_s=n/dt,tokens_per_s=toks/dt,ctx0=c0,ctx1=c1,t_start=c0["t"],t_end=c1["t"])
    # model2vec (single-threaded numpy), full corpus
    for bs in BS:
        for k in ["potion_code","potion_base"]:
            m=ms[k]; m.enc(chunks[:256],bs)
            for rep in range(3):
                _,dt,c0,c1=timed(lambda: m.enc(chunks,bs)); toks=m.ntok(chunks,"")
                row(phase="grid",model=k,batch=bs,threads="n/a(single)",n_chunks=len(chunks),rep=rep,wall_s=dt,chunks_per_s=len(chunks)/dt,tokens_per_s=toks/dt,ctx0=c0,ctx1=c1,t_start=c0["t"],t_end=c1["t"])
    # ---- queries
    for th in ([4,16] if not SMOKE else [4]):
        setthreads(th)
        run=["bge","eg2_fp32","eg2_bf16","potion_code","potion_base"]
        for k in run: ms[k].enc(queries[:20],1,prompt=ms[k].qp)
        for rep in range(3):
            for k in (run if rep%2==0 else run[::-1]):
                m=ms[k]; c0=ctx(); lat=[]
                for q in queries:
                    t=time.perf_counter(); m.enc([q],1,prompt=m.qp); lat.append((time.perf_counter()-t)*1000)
                c1=ctx(); a=np.array(lat)
                row(phase="query",model=k,threads=th,rep=rep,n=len(a),p50_ms=float(np.percentile(a,50)),p95_ms=float(np.percentile(a,95)),max_ms=float(a.max()),ctx0=c0,ctx1=c1,t_start=c0["t"],t_end=c1["t"])
    # ---- MRL256 timing (should equal 768 encode time) + index build
    def bestcfg(k):
        rows=[json.loads(l) for l in open(OUT)]; g={}
        for r in rows:
            if r["phase"]=="grid" and r["model"]==k and r["batch"]>1 and r["threads"]!="n/a(single)": g.setdefault((r["batch"],r["threads"]),[]).append(r["chunks_per_s"])
        return max(g,key=lambda x: statistics_med(g[x]))
    def statistics_med(x): return st.median(x)
    cfg={k:bestcfg(k) for k in st_models}
    row(phase="best_cfg",cfg={k:list(v) for k,v in cfg.items()})
    for rep in range(2):
        for k in (st_models if rep==0 else st_models[::-1]):
            bs,th=cfg[k]; setthreads(th); m=ms[k]
            if rep==0: m.enc(chunks[:64],bs)
            v,dt,c0,c1=timed(lambda: m.enc(chunks,bs))
            row(phase="index_build",model=k,batch=bs,threads=th,n_chunks=len(chunks),rep=rep,wall_s=dt,chunks_per_s=len(chunks)/dt,finite=bool(np.isfinite(v).all()),dim=int(v.shape[1]),ctx0=c0,ctx1=c1,t_start=c0["t"],t_end=c1["t"])
            if k=="eg2_fp32" and rep==0:
                t=time.perf_counter(); v2=v[:,:256]; v2=v2/np.linalg.norm(v2,axis=1,keepdims=True); row(phase="mrl256_postproc",wall_s=time.perf_counter()-t,note="encode time identical to 768 (slice+renorm only)")
    for k in ["potion_code","potion_base"]:
        m=ms[k]; v,dt,c0,c1=timed(lambda: m.enc(chunks,128))
        row(phase="index_build",model=k,batch=128,threads="single",n_chunks=len(chunks),rep=0,wall_s=dt,chunks_per_s=len(chunks)/dt,ctx0=c0,ctx1=c1,t_start=c0["t"],t_end=c1["t"])
    man["end"]=ctx(); man["tokens"]=tk; man["best_cfg"]={k:list(v) for k,v in cfg.items()}
    json.dump(man,open(W+("/smoke_manifest.json" if SMOKE else "/run_manifest.json"),"w"),indent=1)
if __name__=='__main__' and not os.environ.get('RETIME'): main()
