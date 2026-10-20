import json,sys,collections
rows=[json.loads(l) for l in open(sys.argv[1])]
A=[r for r in rows if r['phase']=='A']
print(len(A),collections.Counter(r['suite'] for r in A))
by=collections.defaultdict(dict)
for r in A: by[r['id']][r['arm']]=r
def cls(s):
    if s in('coder','bigcodebench','debugbench','livecodebench'):return 'code'
    if s in('math','gpqa_diamond_cot','physics','mmlu_pro','thinking'):return 'reason'
    return 'prose'
res=collections.defaultdict(list);excl=[]
for i,d in by.items():
    a,b=d['dflash2'],d['nodraft'];s=a['suite']
    print(f"{i:22s}{s:14s}{cls(s):7s} n={a['predicted_n']}/{b['predicted_n']} df={a['decode_tps']} nd={b['decode_tps']} ratio={a['decode_tps']/b['decode_tps']:.3f} acc={a['draft_acc']}")
    if min(a['predicted_n'],b['predicted_n'])<50: excl.append(i);continue
    res[cls(s)].append((i,a,b))
print('EXCL',excl)
for c,l in res.items():
    # token-weighted: sum tokens / sum time per arm
    ta=sum(a['predicted_n'] for _,a,_ in l)/sum(a['predicted_n']/a['decode_tps'] for _,a,_ in l)
    tb=sum(b['predicted_n'] for _,_,b in l)/sum(b['predicted_n']/b['decode_tps'] for _,_,b in l)
    dn=sum(a['draft_n'] for _,a,_ in l);da=sum(a['draft_n_accepted'] for _,a,_ in l)
    print(c,len(l),f"df={ta:.2f} nd={tb:.2f} ratio={ta/tb:.3f} acc={da/dn:.3f}")

al=[x for l in res.values() for x in l]
print('ALL',len(al),sum(a['predicted_n'] for _,a,_ in al)/sum(a['predicted_n']/a['decode_tps'] for _,a,_ in al),sum(b['predicted_n'] for _,_,b in al)/sum(b['predicted_n']/b['decode_tps'] for _,_,b in al))
