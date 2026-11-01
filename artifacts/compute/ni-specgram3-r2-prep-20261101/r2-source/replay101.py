from pathlib import Path
import os
S=Path(__file__).resolve().parent
import sys
sys.path.insert(0,str(S/"wheel"))
import llguidance as L, json, collections, sys, time, statistics
from tokenizers import Tokenizer
M="/mnt/raid0/llm/models/"
TOK={"qwen35":M+"turboderp/Qwen3.8-27B-exl3-4.00bpw/tokenizer.json",
     "qwen35-q36":M+"dflash/Qwen3.6-27B-DFlash/tokenizer.json",
     "qwen3":"/mnt/raid0/llm/hf-models/Qwen3-4B-Instruct-2507/tokenizer.json"}
calls=[json.loads(l) for l in open(S/"corpus.jsonl")]
LIMIT=int(sys.argv[1]) if len(sys.argv)>1 else len(calls)
all_calls=calls[:] # derive schemas from full original corpus even in smoke
# ---- per-tool schema inference
by=collections.defaultdict(list)
for c in calls: by[c["tool"]].append(c["input"])
def jt(v):
    return {bool:"boolean",int:"integer",float:"number",str:"string",list:"array",dict:"object",type(None):"null"}[type(v)]
schemas={}
for tool,ins in by.items():
    keys=collections.defaultdict(list); types=collections.defaultdict(set); cnt=collections.Counter()
    for d in ins:
        ks=list(d.keys())
        for i,k in enumerate(ks): keys[k].append(i/max(1,len(ks))); types[k].add(jt(d[k])); cnt[k]+=1
    order=sorted(keys,key=lambda k:(sum(keys[k])/len(keys[k]),k))
    req=[k for k in order if cnt[k]/len(ins)>=0.9]
    schemas[tool]=dict(order=order,req=req,types={k:sorted(types[k]) for k in order})
def prop_schema(ts):
    if len(ts)==1: return {"type":ts[0]}
    return {}
def json_schema():
    alts=[]
    for tool,s in schemas.items():
        props={k:prop_schema(s["types"][k]) for k in s["order"]}
        alts.append({"type":"object","properties":{"name":{"const":tool},"arguments":{"type":"object","properties":props,"required":s["req"],"additionalProperties":False}},"required":["name","arguments"],"additionalProperties":False})
    return {"anyOf":alts}
def reorder(tool,inp):
    o=schemas[tool]["order"]; return {k:inp[k] for k in o if k in inp}
def lark_xml(tc,etc):
    tools=[];rules=[]
    for tool,s in schemas.items():
        rn="t_"+"".join(ch if ch.isalnum() else "_" for ch in tool)
        alts=[]
        for k in s["order"]:
            ts=s["types"][k]
            if ts==["integer"]: body='/-?[0-9]+/'
            elif ts==["boolean"]: body='("true"|"false")'
            else: body='free'
            alts.append(f'"{k}>\\n" {body}')
        rules.append(f'{rn}: "{tool}>\\n" {rn}_p* "</function>\\n" <[{etc}]>')
        rules.append(f'{rn}_p: "<parameter=" ({" | ".join(alts)}) "\\n</parameter>\\n"')
        tools.append(rn)
    return f'start: <[{tc}]> "\\n<function=" ({" | ".join(tools)})\nfree[stop="\\n</parameter>"]: /(?s:.*)/\n'+"\n".join(rules)+"\n"
def xml_text(tool,inp):
    s="<tool_call>\n<function="+tool+">\n"
    for k,v in inp.items():
        s+="<parameter="+k+">\n"+(v if isinstance(v,str) else json.dumps(v,ensure_ascii=False))+"\n</parameter>\n"
    return s+"</function>\n</tool_call>"
def json_text(tool,inp,compact):
    o={"name":tool,"arguments":reorder(tool,inp)}
    return json.dumps(o,ensure_ascii=False,separators=(",",":")) if compact else json.dumps(o,ensure_ascii=False)
# ---- byte tables
def byte_table(path):
    j=json.load(open(path)); v=j["model"]["vocab"]; added={a["id"]:a["content"] for a in j["added_tokens"]}
    bs=list(range(33,127))+list(range(161,173))+list(range(174,256)); cs=bs[:]; n=0
    for b in range(256):
        if b not in bs: bs.append(b); cs.append(256+n); n+=1
    dec={chr(c):b for b,c in zip(bs,cs)}
    tab={}
    for s,i in v.items(): tab[i]=bytes(dec[ch] for ch in s)
    for i,s in added.items(): tab[i]=s.encode()
    return tab
def tcids(path):
    j=json.load(open(path)); a={x["content"]:x["id"] for x in j["added_tokens"]}
    return a.get("<tool_call>"),a.get("</tool_call>")
OUT=Path(os.environ["SPECGRAM3_REPLAY_OUT"]);OUT.mkdir(exist_ok=True)
res={}
(OUT/"VERSION.json").write_text(json.dumps({"module":L.__file__,"native_module":__import__("llguidance._lib",fromlist=["x"]).__file__,"version":"1.0.1","source":"pinned PyPI wheel; not locally source-built","corpus_calls":len(all_calls),"smoke_limit":LIMIT}))
consist_bad=0
SPEC={248058,248059}
DEBUG=False
def run(label,tokpath,gram,texts,tk,lt,tab):
    t0=time.time()
    base=L.LLMatcher(lt,gram); m=base
    if m.is_error(): print(label,"GRAMMAR ERROR",m.get_error()[:300]); return
    global consist_bad
    consist_bad=0
    strict_accepts=0;
    N=0;F=0;Fu=0;under=0;waste=0;untr=0;shares=[];runs=collections.Counter();rej=0;ok=0;ntr=collections.Counter();viol=0;ev=0;skip=0
    sampled_first=0
    for call_index,(tool,txt) in enumerate(texts):
        ids=tk.encode(txt).ids
        m=base.deep_copy(); i=0;n=len(ids);f=0;fu=0;r=[];good=True;trims=[]
        byte_off=[0]
        for t in ids: byte_off.append(byte_off[-1]+len(tab[t]))
        raw=txt.encode();events=[]
        while i<n:
            ff=m.compute_ff_tokens()
            if ff and ids[i:i+len(ff)]==ff:
                # untrimmed forced bytes
                fb=bytes(m.compute_ff_bytes()) if True else b""
                events.append({"position":i,"forced_tokens":ff,"forced_bytes_hex":fb.hex()})
                m.consume_tokens(ff); f+=len(ff); r.append(len(ff))
                # audit canonical trim on this forced span
                end=byte_off[i]+len(fb)+sum(len(tab[t]) for t in ff if t in SPEC)
                if byte_off[i+len(ff)]>end: consist_bad+=1
                try:
                    tail=tk.encode(raw[:end].decode()).ids
                    c=0
                    pre=ids[:i]
                    # tokens of forced-only text beyond prefix
                    ft=tail[i:] if tail[:i]==pre else None
                    if ft is not None:
                        cm=0
                        while cm<len(ft) and i+cm<n and ft[cm]==ids[i+cm]: cm+=1
                        k=len(ft)-cm
                        trims.append((k,len(ft),len(ff)))
                    else: trims.append(("prefixdiff",0,0))
                except UnicodeDecodeError: trims.append(("midutf8",0,0))
                i+=len(ff); continue
            if not m.consume_token(ids[i]):
                good=False
                if DEBUG and rej<2: print('REJ',label,tool,i,n,repr(raw[byte_off[max(0,i-3)]:byte_off[min(n,i+3)]]),m.get_error()[:200].replace(chr(10),' '))
                break
            i+=1
        strict_accepting=bool(good and m.is_accepting());strict_accepts+=int(strict_accepting)
        with (OUT/(label.replace("|","-")+".raw.jsonl")).open("a") as out:out.write(json.dumps({"call":call_index,"tool":tool,"text":txt,"tokens":ids,"fully_consumed":good,"strict_accepting":strict_accepting,"forced_events":events,"trims":trims})+"\n")
        if good and m.is_accepting() is not None:
            ok+=1;N+=n;F+=f;shares.append(f/n)
            for x in r: runs[x]+=1
            for k,ftl,fft in trims:
                ev+=1
                if isinstance(k,str): skip+=1; continue
                untr+=ftl; tt=ftl-fft
                if k>tt: under+=1
                else: waste+=tt-k
                ntr[k]+=1
                if k>4: viol+=1
        else: rej+=1
    d=dict(label=label,strict_accepting_calls=strict_accepts,legacy_acceptance_compatibility="original is_accepting() is not None; boolFalse also counted; strict state retained separately",calls_ok=ok,calls_rejected=rej,tokens=N,forced=F,forced_share=F/N if N else None,
           ceiling=1/(1-F/N) if N and F<N else None,runs={str(k):v for k,v in sorted(runs.items())},
           n_ff_events=sum(runs.values()),mean_run=(F/sum(runs.values())) if runs else None,
           need_trim_hist={str(k):v for k,v in sorted(ntr.items())},audit_events=ev,audit_skipped=skip,audit_k_gt4=viol,consistency_bad=consist_bad,undertrim_events=under,overtrim_tokens=waste,untrimmed_forced_tokens=untr,untrimmed_share=(untr/N if N else None),median_call_share=statistics.median(shares) if shares else None,lazy_share=((F-ok)/N if N else None),secs=round(time.time()-t0,1))
    print(json.dumps(d),flush=True); res[label]=d
calls=calls[:LIMIT]
fam={}
for name,path in TOK.items():
    if not Path(path).exists():
        (OUT/("UNAVAILABLE-"+name+".json")).write_text(json.dumps({"path":path,"auxiliary_tokenizer_equality_check":"unavailable; not substituted"}));continue
    fam[name]=(Tokenizer.from_file(path),L.LLTokenizer(open(path).read()),byte_table(path),tcids(path))
# equality check qwen35 vs q36 on corpus
xml_texts=[(c["tool"],xml_text(c["tool"],c["input"])) for c in calls]
if "qwen35-q36" in fam:
    a,b=fam["qwen35"][0],fam["qwen35-q36"][0]
    neq=sum(1 for _,t in xml_texts if a.encode(t).ids!=b.encode(t).ids)
    print("tokenizer qwen35 vs qwen36 encode mismatches on corpus:",neq,"of",len(xml_texts),flush=True)
else:print("qwen36 auxiliary tokenizer equality UNKNOWN: original canonical file unavailable",flush=True)
tk,lt,tab,(tc,etc)=fam["qwen35"]
g=L.LLMatcher.grammar_from_lark(lark_xml(tc,etc))
run("qwen35|xml|eager",None,g,xml_texts,tk,lt,tab)
# lazy: grammar starts after trigger token => drop the first token from forced
sch=json_schema()
for fl,tx,lab in ((True,False,"flexgrammar+flextext"),(False,True,"compactgrammar+compacttext"),(True,True,"flexgrammar+compacttext")):
    g=L.LLMatcher.grammar_from_json_schema(sch,defaults={"whitespace_flexible":fl})
    texts=[(c["tool"],json_text(c["tool"],c["input"],tx)) for c in calls]
    for fn in ("qwen35","qwen3"):
        tk,lt,tab,_=fam[fn]
        run(f"{fn}|json|{lab}",None,g,texts,tk,lt,tab)
json.dump(res,open(OUT/("results_%d.json"%LIMIT),"w"),indent=1)
