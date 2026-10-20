import ast, hashlib, json, os, re, sys
SRC="/workspace/repos/epyc-orchestrator/src"; MD="/workspace/handoffs/active"
def files(root, ext):
    out=[]
    for d,_,fs in os.walk(root):
        for f in fs:
            if f.endswith(ext): out.append(os.path.join(d,f))
    return sorted(out)
def sha(b): return hashlib.sha256(b).hexdigest()
def chunks(text, target=800):
    out=[];cur=""
    for ln in text.splitlines(keepends=True):
        if len(cur)+len(ln)>target and len(cur)>=400:
            out.append(cur); cur=""
        cur+=ln[:target]
        if len(cur)>=target: out.append(cur); cur=""
    if len(cur)>=400: out.append(cur)
    return out
def stride(xs,n):
    if len(xs)<=n: return xs
    return [xs[int(i*len(xs)/n)] for i in range(n)]
man={"files":[]}; allc={}; queries={"py":[],"md":[]}
for kind,root,ext in (("py",SRC,".py"),("md",MD,".md")):
    cs=[]
    for p in files(root,ext):
        b=open(p,"rb").read(); t=b.decode("utf8","replace")
        man["files"].append({"path":p,"sha256":sha(b),"kind":kind})
        for i,c in enumerate(chunks(t)): cs.append({"src":p,"i":i,"kind":kind,"text":c})
        if kind=="py":
            try:
                for n in ast.walk(ast.parse(t)):
                    if isinstance(n,(ast.FunctionDef,ast.ClassDef,ast.AsyncFunctionDef,ast.Module)):
                        d=ast.get_docstring(n)
                        if d:
                            s=re.split(r"(?<=[.!?])\s|\n\n",d.strip())[0].strip()
                            if 20<=len(s)<=200: queries["py"].append(s)
            except Exception: pass
        else:
            for m in re.finditer(r"^#{1,4}\s+(.{15,150})$",t,re.M): queries["md"].append(m.group(1).strip())
    allc[kind]=cs
sel=stride(allc["py"],2048)+stride(allc["md"],2048)
man["n_available"]={k:len(v) for k,v in allc.items()}
def uniq(xs):
    seen=set();o=[]
    for x in xs:
        if x not in seen: seen.add(x);o.append(x)
    return o
q=stride(uniq(queries["py"]),100)+stride(uniq(queries["md"]),100)
q=uniq(q)
man["n_chunks"]=len(sel); man["n_queries"]=len(q)
man["mean_chars"]=sum(len(c["text"]) for c in sel)/len(sel)
with open("corpus.jsonl","w") as f:
    for c in sel: f.write(json.dumps(c)+"\n")
json.dump(q,open("queries.json","w"),indent=0)
man["corpus_sha256"]=sha(open("corpus.jsonl","rb").read()); man["queries_sha256"]=sha(open("queries.json","rb").read())
json.dump(man,open("corpus_manifest.json","w"),indent=1)
print({k:v for k,v in man.items() if k!="files"}, len(man["files"]))
