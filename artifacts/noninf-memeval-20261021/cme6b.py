import json,statistics as st
o=json.load(open('cme6_result.json'))
for run,S in o['systems'].items():
    print(run)
    for t,v in S.items():
        n=v['n_instances'];g=v['paired_gain_by_instance']
        print(' %-26s mean_gain/inst=%.4f (headline %.4f) idx0_gain=%.4f first_quarter_mean=%.4f last_quarter_mean=%.4f  instsd=%.4f  SE_mean_roll=%.4f SE_mean_incl_base=%.4f'%(t,v['cum_gain_recomputed']/n,v['cum_gain_headline'],g[0],sum(g[:n//4])/(n//4),sum(g[-(n//4):])/(n//4),v['pooled_instance_sd'],v['se_rollouts_only']/n,v['se_incl_single_stateless_draw_proxy']/n))
