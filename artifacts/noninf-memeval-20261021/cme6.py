import gzip,json,hashlib,statistics as st,math,sys
R='/mnt/raid0/llm/tmp/dive-clbench-repo/repo/final_results/runs/'
out={'repo_sha':'5f8c50eb1e84b2eda2ef4faff757dfc812a0ea26','manifest':{},'systems':{}}
tasks=['exploitable_poker','database_exploration','blind_spectrum_monitoring','cohort_studies','codebase_adaptation','sales_prediction']
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
for run in ['icl-gpt-5.4','icl-claude-sonnet-4.6']:
    out['manifest'][run]={f:sha(R+run+'/'+f) for f in ['manifest.json']+['tasks/%s.json.gz'%t for t in tasks]}
    mf=json.load(open(R+run+'/manifest.json'))
    head={t['task']:t['headline']['cumulative_gain'] for t in mf['tasks']}
    S={}
    for t in tasks:
        d=json.load(gzip.open(R+run+'/tasks/%s.json.gz'%t))
        base=[o['reward'] for o in d['baseline_trace']['instance_outcomes']]
        runs=[[o['reward'] for o in r['trace']['instance_outcomes']] for r in d['run_traces']]
        n=len(base); nulls=sum(x is None for x in base)+sum(x is None for r in runs for x in r)
        short=[len(r) for r in runs]
        allv=[x for x in base+[y for r in runs for y in r] if x is not None]
        # failed -> keep as recorded reward; None -> 0 (counted, flagged)
        f=lambda v:0.0 if v is None else v
        base=[f(x) for x in base]; runs=[[f(x) for x in r]+[0.0]*(n-len(r)) for r in runs]
        k=len(runs)
        gain_i=[sum(r[i] for r in runs)/k-base[i] for i in range(n)]
        cum=sum(gain_i)
        per_run_cum=[sum(r[i]-base[i] for i in range(n)) for r in runs]
        ceil=1.0 if max(allv)<=1.0+1e-9 else None
        head_norm=None
        if ceil is not None:
            den=sum(ceil-b for b in base)
            head_norm=cum/den if den>0 else None
        # per-instance rollout spread (proxy for single-run noise)
        sd_i=[st.stdev([r[i] for r in runs]) for i in range(n)]
        pooled=math.sqrt(sum(s*s for s in sd_i)/n)
        # SE of cumulative gain: rollouts-only vs including a single stateless draw w/ same per-instance variance
        se_roll=math.sqrt(sum(s*s for s in sd_i)/k)
        se_both=math.sqrt(sum(s*s*(1/k+1) for s in sd_i))
        S[t]=dict(n_instances=n,n_rollouts=k,len_runs=short,nulls=nulls,reward_min=min(allv),reward_max=max(allv),
          failed_instances_baseline=None,
          cum_gain_recomputed=round(cum,6),cum_gain_headline=head[t],match=abs(cum-head[t])<1e-4,
          per_run_cum_gain=[round(x,4) for x in per_run_cum],
          rollout_sd_of_cum_gain=round(st.stdev(per_run_cum),4),
          stateless_cum_reward=round(sum(base),4),stateful_cum_reward_mean=round(sum(sum(r) for r in runs)/k,4),
          headroom_norm_gain=None if head_norm is None else round(head_norm,4),
          frac_instances_paired_gain_pos=round(sum(g>0 for g in gain_i)/n,3),
          paired_gain_by_instance=[round(g,4) for g in gain_i],
          pooled_instance_sd=round(pooled,4),
          se_rollouts_only=round(se_roll,4),se_incl_single_stateless_draw_proxy=round(se_both,4),
          hidden_share_of_variance_proxy=round(1-se_roll**2/se_both**2,4) if se_both else None)
    out['systems'][run]=S
json.dump(out,open('cme6_result.json','w'),indent=1)
for run,S in out['systems'].items():
    print(run)
    for t,v in S.items():
        print(' %-26s n=%2d k=%d nulls=%d rew[%.2f,%.2f] cum=%.4f hdl=%.4f %s hn=%s pos=%.2f sdroll=%.3f SE %.3f->%.3f hidden=%s'%(t,v['n_instances'],v['n_rollouts'],v['nulls'],v['reward_min'],v['reward_max'],v['cum_gain_recomputed'],v['cum_gain_headline'],v['match'],v['headroom_norm_gain'],v['frac_instances_paired_gain_pos'],v['rollout_sd_of_cum_gain'],v['se_rollouts_only'],v['se_incl_single_stateless_draw_proxy'],v['hidden_share_of_variance_proxy']))
