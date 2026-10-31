import score_candidates as s
cs={x:{'label':lab,'gold':{'eot_gold_s':1.0}} for x,lab in [('positive','complete'),('negative','incomplete'),('background','backchannel')]}
ev=[{'candidate_id':'a','clip_id':'positive','status':'ok','answer':'finished','pause_audio_s':1.1,'pause_to_decision_s':.1,'result_sha256':'actual-fixture'}, {'candidate_id':'b','clip_id':'negative','status':'bad','answer':None}, {'candidate_id':'c','clip_id':'background','status':'ok','answer':'wait','pause_audio_s':1.,'pause_to_decision_s':.1,'result_sha256':'actual-fixture'}]
r=s.evaluate(cs,ev,[{'candidate_id':x['candidate_id'],'clip_id':x['clip_id']} for x in ev]);assert r['metrics']['eot_recall']['value']==1 and r['metrics']['eot_fpr']['value']==1 and r['metrics']['int_fpr']['value']==0
assert r['matched_latency_baseline']=='UNRESOLVED' and r['verdict']=='UNCOMPUTED'
