import subprocess, sys, os, json
W="/mnt/raid0/llm/worktrees/merge-reconcile-0205"
def run(a):
    return subprocess.run(a,cwd=W,capture_output=True)
def show(rev,path):
    r=run(["git","show",f"{rev}:{path}"])
    if r.returncode!=0: return None
    return r.stdout.decode("utf-8","replace")
def files(rev):
    r=run(["git","ls-tree","-r","--name-only",rev])
    return set(r.stdout.decode().splitlines())
base="3dd1ec1b"; ours="921113ed"; theirs="705b8f85"
allf=files(ours)|files(theirs)
def norm(t):
    if t is None: return None
    return [l.rstrip("\r") for l in t.split("\n") if l.strip()!=""]
out=[]
for p in sorted(allf):
    fp=os.path.join(W,p)
    if not os.path.exists(fp):
        wt=None
    else:
        try: wt=open(fp,encoding="utf-8",errors="replace").read()
        except Exception: continue
    o=show(ours,p); t=show(theirs,p); b=show(base,p)
    no,nt,nb,nw=norm(o),norm(t),norm(b),norm(wt)
    ws=set(nw or [])
    miss_o=[l for l in (no or []) if l not in ws]
    miss_t=[l for l in (nt or []) if l not in ws]
    if miss_o or miss_t:
        out.append({"path":p,"miss_ours":len(miss_o),"miss_theirs":len(miss_t),
                    "wt_exists":wt is not None,"in_base":b is not None,
                    "samples_o":miss_o[:400],"samples_t":miss_t[:400]})
json.dump(out,open("/workspace/tmp/coord-coldstart/scan.json","w"))
tot_o=sum(x["miss_ours"] for x in out); tot_t=sum(x["miss_theirs"] for x in out)
print("files:",len(out),"miss_from_ours:",tot_o,"miss_from_theirs:",tot_t)
for x in sorted(out,key=lambda z:-(z["miss_ours"]+z["miss_theirs"]))[:60]:
    print(f'{x["miss_ours"]:6d} {x["miss_theirs"]:6d}  wt={int(x["wt_exists"])} {x["path"]}')
