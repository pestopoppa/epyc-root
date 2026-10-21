import gzip,json,math,statistics as st
R='/mnt/raid0/llm/tmp/dive-clbench-repo/repo/final_results/runs/'
RMAX={'exploitable_poker':9.49,'database_exploration':1.0,'blind_spectrum_monitoring':1.0,'cohort_studies':0.162,'codebase_adaptation':1.0,'sales_prediction':1.0}
out={}
for run in ['icl-gpt-5.4','icl-claude-sonnet-4.6']:
    gs=[];var=[];per={}
    for t,rm in RMAX.items():
        d=json.load(gzip.open(R+run+'/tasks/%s.json.gz'%t))
        base=[o['reward'] for o in d['baseline_trace']['instance_outcomes']]
        runs=[[o['reward'] for o in r['trace']['instance_outcomes']] for r in d['run_traces']]
        bm=sum(base)/len(base); head=rm-bm
        gk=[(sum(r)/len(r)-bm)/head for r in runs]   # per-rollout normalized gain
        g=sum(gk)/len(gk); gs.append(g); var.append(st.variance(gk)/len(gk)); per[t]=dict(sl_mean=round(bm,4),headroom=round(head,4),norm_gain=round(g,4),rollout_sd=round(st.stdev(gk),4))
    m=sum(gs)/6; ci=1.96*math.sqrt(sum(var))/6
    out[run]=dict(per_task=per,norm_gain_pct=round(100*m,2),ci95_pct_from_rollout_var=round(100*ci,2))
    print(run,out[run]['norm_gain_pct'],'+-',out[run]['ci95_pct_from_rollout_var']); [print('  ',k,v) for k,v in per.items()]
json.dump(out,open('cme6_table1_compare.json','w'),indent=1)
