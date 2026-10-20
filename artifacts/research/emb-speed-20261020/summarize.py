import json, statistics as st, sys, collections
W="/mnt/raid0/llm/tmp/emb-speed-20261020"
R=[json.loads(l) for l in open(W+"/results.jsonl")]
def med(x): return st.median(x)
def contam(r):
    c0,c1=r.get("ctx0"),r.get("ctx1")
    if not c0: return False
    return any((c or {}).get("gpu_use_pct") or (c or {}).get("kfd_procs") for c in (c0,c1))
out=[]
P=out.append
P("# Embedder speed pilot (timing screen only; NO retrieval-quality claim)\n")
P("Claim: region-lock q1+q2 = CPUs 24-71 (48 physical cores, NUMA nodes 1-2; SMT siblings excluded). OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active. CPU: AMD EPYC 9655.\n")
P("## Load, RSS, params, tokens\n\n| model | dtype | params(M) | load s | RSS delta MB | tokens/chunk |\n|---|---|---|---|---|---|")
tk={r["model"]:r["tokens_per_chunk"] for r in R if r["phase"]=="tokens"}
for r in R:
    if r["phase"]=="load": P(f"| {r['model']} | {r['dtype']} | {(r['nparams'] or 0)/1e6:.0f} | {r['load_s']:.2f} | {r['rss_delta_mb']} | {tk.get(r["model"],0):.0f} |")
P("\n(EG2 checkpoint loaded through sentence-transformers includes non-text towers; params/RSS are for the whole loaded module, only text path is run. Static-model RSS is file-backed/mmap and also small.)\n")
g=collections.defaultdict(list)
for r in R:
    if r["phase"]=="grid": g[(r["model"],r["batch"],r["threads"])].append(r)
P("## Encode throughput (documents) median of 3 timed reps, chunks/s (tokens/s); spread = (max-min)/median\n\n| model | batch | threads | n chunks | chunks/s | tokens/s | spread % | contaminated? |\n|---|---|---|---|---|---|---|---|")
for k in sorted(g,key=lambda x:(str(x[0]),str(x[2]),x[1])):
    rs=g[k]; c=[r["chunks_per_s"] for r in rs]; t=[r["tokens_per_s"] for r in rs]
    P(f"| {k[0]} | {k[1]} | {k[2]} | {rs[0]['n_chunks']} | {med(c):.1f} | {med(t):.0f} | {100*(max(c)-min(c))/med(c):.1f} | {'POSSIBLY CONTAMINATED' if any(contam(r) for r in rs) else 'no'} |")
P("\nSubsets: threads=1 -> 16 chunks, batch=1 -> 64 chunks, otherwise 256 chunks (fixed prefix of the 4,096-chunk corpus); model2vec rows use all 4,096 and are single-threaded.\n")
bb=[r for r in R if r["phase"]=="grid" and r["model"]=="bge_b"]
if bb:
    a=med([r["chunks_per_s"] for r in R if r["phase"]=="grid" and r["model"]=="bge" and r["batch"]==32 and r["threads"]==16])
    b=med([r["chunks_per_s"] for r in bb])
    P(f"## A/A noise floor (BGE vs BGE again, batch32 x16 threads, interleaved): {a:.2f} vs {b:.2f} chunks/s => {100*abs(a-b)/a:.1f}% (unit: percent of chunks/s). Rep-to-rep spreads in the table above are the other floor estimate. Differences below the larger of these are not distinguishable.\n")
P("## Single-query latency (200 queries x 3 reps, batch 1), ms\n\n| model | threads | p50 | p95 | max (median over reps) | contaminated? |\n|---|---|---|---|---|---|")
q=collections.defaultdict(list)
for r in R:
    if r["phase"]=="query": q[(r["model"],r["threads"])].append(r)
for k in sorted(q,key=lambda x:(x[1],x[0])):
    rs=q[k]; P(f"| {k[0]} | {k[1]} | {med([r['p50_ms'] for r in rs]):.2f} | {med([r['p95_ms'] for r in rs]):.2f} | {med([r['max_ms'] for r in rs]):.1f} | {'POSSIBLY CONTAMINATED' if any(contam(r) for r in rs) else 'no'} |")
P("\n## Index build, 4,096 chunks at best (batch>1, threads) config per model\n\n| model | batch | threads | wall s (reps) | chunks/s |\n|---|---|---|---|---|")
ib=collections.defaultdict(list)
for r in R:
    if r["phase"]=="index_build": ib[r["model"]].append(r)
for m,rs in ib.items():
    P(f"| {m} | {rs[0]['batch']} | {rs[0]['threads']} | {', '.join(f'{r['wall_s']:.1f}' for r in rs)} | {med([r['chunks_per_s'] for r in rs]):.1f} |")
for r in R:
    if r["phase"] in("sanity","sanity_bf16_vs_fp32","sanity_mrl256"): P(f"\n- sanity: {({k:v for k,v in r.items() if k not in('ctx',)})}")
open(W+"/summary_tables.md","w").write("\n".join(out)); print("\n".join(out))
