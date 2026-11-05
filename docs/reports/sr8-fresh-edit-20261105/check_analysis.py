from analysis import analyze_sr8
schedule=[{'rep':i,'task':f't{i}'} for i in range(1,6)]
rows=[]
for b in schedule:
 for arm in ('plain','current_dflash2','prompt_lookup'):
  r=dict(rep=b['rep'],task=b['task'],arm=arm,status='ok',temperature=0,fresh_server=True,gpu_residency=True,edit_validity='PASS',decode_tps=3 if arm=='prompt_lookup' else 2)
  if arm=='current_dflash2': r.update(draft_rounds=2,accepted=3,drafted=4)
  if arm=='prompt_lookup': r.update(draft_rounds=0,accepted=0,drafted=0)
  rows.append(r)
a=analyze_sr8(rows,schedule)
assert a['candidate_threshold_met'] and a['arms']['prompt_lookup']['zero_proposal_requests']==5
assert a['arms']['prompt_lookup']['mean_accepted_draft_tokens'] is None
for bad in (rows[:-1], rows+[rows[0]]):
 try: analyze_sr8(bad,schedule)
 except ValueError: pass
 else: raise AssertionError('invalid cohort accepted')
print('SR8_ANALYSIS_CONTROLS_PASS')
