def test_all():
    import json,tempfile
    from pathlib import Path
    from unittest.mock import patch
    import census_belief as cb
    import private_census as census
    from autokernel.loop import census_capture as cc
    from autokernel.controller.workload_contract import WorkloadCensus
    from claim_tuple import grade,ProjectionError
    root=Path(tempfile.mkdtemp());intent=cb.begin_capture(root/'intent.json',workload_id='test')
    ts=json.loads(intent.read_text())['created_ns'];js=[]
    shapes=[{'phase':p,'n_tokens':n,'n_seq':1} for p,n in [('prefill',2048),('decode',1),('verify',5)]]
    refs=[{'path':f'/fake/{x}','sha256':'a'*64} for x in range(4)]
    pins=[{'path':'/fake/builder','sha256':'b'*64}]
    rows=[]
    for i,s in enumerate(shapes):
     p=root/f'{i}.jsonl';js.append(p)
     cc.append_event(p,{'kind':'start','attempt_id':str(i),'started_ns':ts+1,'shape':s,'inputs':{'belief_intent':{'sha256':cb._digest(intent)},'builder_input_0':{'origin_path':pins[0]['path'],'sha256':pins[0]['sha256']},**dict(zip(('model','model_shard_2','model_shard_3','drafter'),refs))}})
     cc.append_event(p,{'kind':'terminal','attempt_id':str(i),'spawned_ns':ts+2,'ended_ns':ts+300,'rc':0,'error':''})
     req=root/f'request{i}.json';req.write_text(json.dumps({'request_windows':[{'start_ns':ts+10,'end_ns':ts+200}]}))
     foreign=root/f'foreign{i}.jsonl';foreign.write_text(''.join(json.dumps(x)+'\n' for x in [{'window_start_ns':ts+20,'window_end_ns':ts+30},{'window_start_ns':ts+40,'window_end_ns':ts+50}]))
     guards={k:True for k in ('configured_parallelism','request_count','slot_occupancy_observed','terminal_responses',
      'prompt_counters_present','native_instrument_mapping','native_ggml_mapping','native_tensor_width_and_api_sequences')}
     extra={'prefill':('configured_ubatch','frozen_token_width','native_prompt_width'),
      'decode':('plain_decode_request','plain_decode_response'),
      'verify':('native_verify_width','native_draft_counters','request_verify_budget')}[s['phase']]
     guards.update({k:True for k in extra})
     rows.append({'shape':s,'state':'OBSERVED','nodes_total':1001,'op_backend':{'MUL_MAT':{},'MUL_MAT_ID':{}},
      'native_shape_evidence':{'guards':guards},
      'request_log':str(req),'request_log_sha256':cb._digest(req),'foreign_load':str(foreign),'foreign_load_sha256':cb._digest(foreign)})
    identity={'model':{'shards':refs[:3],'head':refs[3]},'recipe':{'builder_source_pins':pins}}
    weights=WorkloadCensus(refs[0]['path'],'qwen4exp',2560,{'Q8_0':1224})
    def probe(binary,model,shape,**kwargs):return rows[('prefill','decode','verify').index(shape.phase)]
    with patch.object(census,'read_flash_next_weights',return_value=weights):
     r=census.produce_census(workload_id='test',workload_signature='fixture',model=Path(refs[0]['path']),
      identity=identity,shapes=[census.Shape(**s) for s in shapes],binary=Path('/fake/server'),probe=probe)
    rp=root/'record.json';rp.write_text(json.dumps(r));side=cb.write_belief_measurements(root,record_path=rp,journals=js,intent_path=intent,emitted_at='2026-10-27T00:00:00Z')
    native=cb.native_rows(side);assert len(native)==3
    for row in native:
     t=cb.project(row);assert t.protocol_id=='';assert grade(t)[:2]==('Judged','Located')
    try:cb.write_belief_measurements(root,record_path=rp,journals=js,intent_path=intent)
    except ValueError:pass
    else:raise AssertionError('reuse accepted')
    # A native input change voids all rows; direct projection must also refuse.
    Path(rows[0]['foreign_load']).write_text('{}\n');assert cb.native_rows(side)==()
    try:cb.project(native[0])
    except ProjectionError:pass
    else:raise AssertionError('tampered direct projection accepted')
    print('PASS: prospective shape rows, shared Judged/Located grade, reuse/tamper refusals')
    # Controls operate only on this fixture, never on production evidence.
    Path(rows[0]['foreign_load']).write_text(''.join(json.dumps(x)+'\n' for x in [
     {'window_start_ns':ts+20,'window_end_ns':ts+30},{'window_start_ns':ts+40,'window_end_ns':ts+50}]))
    cb._check_record(rp,js,intent)
    def refuses(record):
     rp.write_text(json.dumps(record))
     try:cb._check_record(rp,js,intent)
     except (ValueError,KeyError,TypeError):return
     raise AssertionError('invalid record accepted')
    import copy
    bad=copy.deepcopy(r);bad['graph']['shape_envelope'].pop();refuses(bad)
    bad=copy.deepcopy(r);bad['identity']['model']['head']['sha256']='b'*64;refuses(bad)
    bad=copy.deepcopy(r);bad['graph']['per_shape'][1]['op_backend'].pop('MUL_MAT_ID');refuses(bad)
    bad=copy.deepcopy(r);bad['graph']['per_shape'][2]['shape']['n_tokens']=4;refuses(bad)
    bad=copy.deepcopy(r);bad['graph']['per_shape'][0]['native_shape_evidence']['guards'].pop('native_ggml_mapping');refuses(bad)
    print('PASS: partial phases, wrong artifact, missing op and wrong verify width refuse')


if __name__ == "__main__":
    test_all()
