#!/usr/bin/env python3
"""Independent read-only replay of the filed W3 half-A r2 and W2 CPU r3 native records."""
import base64, hashlib, json, pathlib, re

ARTIFACT = pathlib.Path(__file__).resolve().parent
W3ROOT = ARTIFACT / 'evidence/w3'
W2ROOT = ARTIFACT / 'evidence/w2'
W3OUT = W3ROOT / 'out'
W2OUT = W2ROOT / 'out'
RECORDS = {
  'W3': (W3OUT/'inf75-w3-canonical-halfa-r2-20261029-b65edc5165c0e66d.json',
         'b060676693a6b907f810f7e8313508af5fb87f6c04f4fcbc4c923734f7d80ef0'),
  'W2': (W2OUT/'inf75-w2-current-cpu-census-r3-20261029-88fa1714c1c81d32.json',
         '2d1348d607991453d038d4307fb63544c6123fe06e67f160965638ac44634eab'),
}

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''): h.update(block)
    return h.hexdigest()

def read(path): return json.loads(pathlib.Path(path).read_text())
def verify_source_pins(root, names):
    entries={}
    for line in (root/'SOURCES.sha256').read_text().splitlines():
        digest, source = line.split('  ', 1); entries[source]=digest
    for name in names:
        p=root/name
        matches=[digest for source,digest in entries.items() if source.endswith('/'+name)]
        require(len(matches)==1 and sha(p)==matches[0], f'source pin mismatch: {p}')
def require(ok, why):
    if not ok: raise AssertionError(why)
def analyze(name, path, expected_sha):
    require(sha(path)==expected_sha, f'{name} native record hash mismatch')
    rec=read(path)
    require(rec['schema']=='epyc.autokernel.workload_census.v1',f'{name} schema')
    require(rec['validity']['observed'] is True and rec['validity']['state']=='OBSERVED',f'{name} validity')
    ident=rec['identity']
    require(ident['backend']=='cpu' and ident['claim_cpus']=='0-47,96-143',f'{name} CPU/placement identity')
    require(ident['kernel']['commit']=='c72ec82f5417bb2937310326120f149b665e8400',f'{name} kernel commit')
    require(ident['kernel']['binary_sha256']=='bfab92dffa31ad24f65ca53ec082ef8f1751b54d56efdc0f106bef797a72ee2e',f'{name} ELF identity')
    binpath=pathlib.Path(ident['recipe']['binary'])
    current_binary_hash=sha(binpath) if binpath.is_file() else None
    if current_binary_hash is not None:
        require(current_binary_hash==ident['kernel']['binary_sha256'],f'{name} current ELF bytes disagree with native identity')
    elfmanifest=ARTIFACT/'evidence/shared/ELF.sha256'
    elf_rows={line.split('  ',1)[1]:line.split('  ',1)[0] for line in elfmanifest.read_text().splitlines()}
    require(elf_rows.get(str(binpath))==ident['kernel']['binary_sha256'],f'{name} ELF manifest does not bind server binary')
    source_root=W3ROOT if name=='W3' else W2ROOT
    source_names=['work.py','full_main.py','recipes.json','producer/autokernel/loop/census.py','producer/autokernel/loop/census_capture.py']
    if name=='W2': source_names.append('MODELS.json')
    verify_source_pins(source_root, source_names)
    rows=[]
    for shape in rec['graph']['per_shape']:
        phase=shape['shape']['phase']; ev=shape['native_shape_evidence']
        require(shape['state']=='OBSERVED' and shape['rc']==0 and ev['observed'],f'{name} {phase} state')
        require(all(v is True for v in ev['guards'].values()),f'{name} {phase} guard failure')
        graphs=shape['graphs']; node_sum=sum(g['declared_nodes'] for g in graphs)
        require(len(graphs)==shape['graphs_count'] if 'graphs_count' in shape else True,f'{name} graph count')
        require(node_sum==shape['nodes_total'],f'{name} {phase} declared-node sum')
        ids=sorted({g['decode_id'] for g in graphs})
        require(ids==list(range(ids[0],ids[0]+len(ids))),f'{name} {phase} decode-id contiguity')
        # Per-shape request and response logs are separately pinned by the native record.
        reqpath=(W3OUT if name=='W3' else W2OUT)/pathlib.Path(shape['request_log']).name
        foreignpath=(W3OUT if name=='W3' else W2OUT)/pathlib.Path(shape['foreign_load']).name
        require(sha(reqpath)==shape['request_log_sha256'],f'{name} {phase} request log hash')
        require(sha(foreignpath)==shape['foreign_load_sha256'],f'{name} {phase} foreign log hash')
        request_doc=read(reqpath)
        reqs=request_doc['requests']; responses=request_doc['responses']
        require(len(reqs)==len(responses)==len(shape['request_windows'])==1,f'{name} {phase} one actual API exchange')
        win=shape['request_windows'][0]
        require(win['success'] is True and win['start_mono_ns']<win['end_mono_ns'] and win['start_utc_ns']<win['end_utc_ns'],f'{name} {phase} request window')
        require(request_doc['request_windows']==shape['request_windows'],f'{name} {phase} request-window binding')
        counts=[]; contained=[]
        for line in foreignpath.read_text().splitlines():
            row=json.loads(line)
            if 'interval_start_mono_ns' not in row: continue
            a,b=row['interval_start_mono_ns'],row['interval_end_mono_ns']; u,v=row['interval_start_utc_ns'],row['interval_end_utc_ns']
            require(0<a<b and 0<u<=v,f'{name} {phase} invalid foreign interval')
            if win['start_mono_ns']<=a and b<=win['end_mono_ns'] and win['start_utc_ns']<=u and v<=win['end_utc_ns']:
                contained.append((a,b,u,v))
        distinct=set(contained)
        require(len(distinct)>=2,f'{name} {phase} fewer than two distinct both-clock contained foreign intervals')
        require(shape['foreign_interval_counts']==[len(distinct)],f'{name} {phase} producer foreign count disagrees with replay')
        # Each retained graph must be coupled to a single successful request's API batch.
        require(all(g['api_batch']['scope']=='api_batch, coupled to native tensor metadata by decode_id' for g in graphs),f'{name} {phase} API graph coupling')
        rows.append({'phase':phase,'shape':shape['shape'],'graphs':len(graphs),'nodes':node_sum,'decode_ids':[ids[0],ids[-1]],'api_batches':sorted(set(g['api_batch']['tokens'] for g in graphs)),'foreign_inside_request':len(distinct),'request_ok':win['success']})
    # Workload-specific native witnesses are checked against the recorded request, graph rows and response.
    if name=='W3':
        by={r['shape']['phase']:r for r in rec['graph']['per_shape']}
        pre=by['prefill']['native_shape_evidence']; dec=by['decode']['native_shape_evidence']; ver=by['verify']['native_shape_evidence']
        require(pre['configured_ubatch']==[2048] and pre['requested_prefill_tokens']==2048 and pre['native_prompt_tokens_by_slot']=={'0':4096},'W3 prefill requested/native prompt witness')
        prelog=read(by['prefill']['request_log']); preq=prelog['requests'][0]; pres=prelog['responses'][0]
        require(len(preq['prompt'])==4096 and preq['n_predict']==1 and pres['timings']['prompt_n']==4096 and pres['tokens_predicted']==1,'W3 actual 4096-token HTTP prefill request/response')
        require([b['tokens'] for witness in pre['split_prefill']['witnesses'] for b in witness['batches']]==[2044,4,2044,4],'W3 split prefill batch witnesses')
        require(all(b['tensor_width_matches'] for witness in pre['split_prefill']['witnesses'] for b in witness['batches']),'W3 split tensor width')
        require(dec['native_single_tensor_width_and_api_sequences'] and by['decode']['shape']['n_tokens']==1,'W3 decode shape')
        dlog=read(by['decode']['request_log']); require(isinstance(dlog['requests'][0]['prompt'],str) and dlog['responses'][0]['timings']['prompt_n']==19 and dlog['responses'][0]['tokens_predicted']==16,'W3 plain decode HTTP request/response')
        require(ver['native_verified_draft_widths']=={'0':[4]} and by['verify']['shape']['n_tokens']==4,'W3 verify draft width')
        vlog=read(by['verify']['request_log']); require(vlog['requests'][0]['speculative.n_max']==4 and vlog['responses'][0]['tokens_predicted']>=4,'W3 verify HTTP request/response')
        pin=read(W3ROOT/'source-pins.json')['models'][ident['model']['path']]['sha256']
        require(pin==ident['model']['sha256'],'W3 source pin/model identity')
    else:
        pre=next(x for x in rec['graph']['per_shape'] if x['shape']['phase']=='prefill')
        dec=next(x for x in rec['graph']['per_shape'] if x['shape']['phase']=='decode')
        wit=pre['native_shape_evidence']['native_microbatch_witnesses']
        prelog=read(pre['request_log']); preq=prelog['requests'][0]; pres=prelog['responses'][0]
        require(len(preq['prompt']['multimodal_data'])==1 and pres['timings']['prompt_n']==4232 and pres['tokens_predicted']==16,'W2 actual image HTTP request/response')
        dlog=read(dec['request_log']); require(dlog['responses'][0]['timings']['prompt_n']==1032 and dlog['responses'][0]['tokens_predicted']==16,'W2 decode HTTP request/response')
        require(len(wit)==8 and {x['native_tensor_width'] for x in wit}=={512},'W2 exact native 512 microbatch witnesses')
        require({x['api_batch_tokens'] for x in wit}=={1024,2048,1159},'W2 API batch widths')
        image=pre['native_shape_evidence']['image_encoder']
        require(image['observed'] and len(image['encodes'])==1 and image['encodes'][0]['native_tokens']==1024 and image['nodes_total']==853,'W2 image encoder attribution')
        require(set(image['op_backend']) and all(set(backends)=={'CPU'} for backends in image['op_backend'].values()),'W2 image CPU backends')
        # Native graph IDs cover the contiguous capture interval once image graph 4 is included.
        gids={g['gid'] for g in pre['graphs']+dec['graphs']}
        gids.add(image['encodes'][0]['graphs'][0])
        require(gids==set(range(min(gids),max(gids)+1)),f'W2 capture graph-id gap: {sorted(gids)}')
        image_bytes=base64.b64decode(preq['prompt']['multimodal_data'][0])
        require(sha(W2ROOT/'image.png')==hashlib.sha256(image_bytes).hexdigest(),'W2 actual image request differs from pinned image.png')
        model_pins=read(W2ROOT/'MODELS.json')
        require(model_pins[ident['model']['path']]['sha256']==ident['model']['sha256'],'W2 model source pin')
        require(model_pins[ident['projector']['canonical_path']]['sha256']==ident['projector']['sha256'],'W2 projector source pin')
    return {'native_record':str(path.relative_to(ARTIFACT)),'native_sha256':expected_sha,'workload_id':ident['recipe']['id'],'model':ident['model'],'projector':ident.get('projector'),'kernel':ident['kernel'],'shapes':rows}

if __name__=='__main__':
    output={name:analyze(name,*pair) for name,pair in RECORDS.items()}
    # The generic owner wrapper marks a whole-census rc as first_request_ok but leaves
    # the smoke-loop counter at its initialized zero; native records carry three (W3)
    # and two (W2) independent successful HTTP windows.
    w3run=W3ROOT/'run'
    w3result=read(w3run/'result.json'); w3work=read(w3run/'WORK-RESULT.json'); w3last=read(W3ROOT/'LAST-RESULT.json')
    require(w3result['rc']==0 and w3result['first_request_ok'] and w3result['requests_completed']==0,'W3 wrapper anomaly not reproduced')
    require(w3work['requests_completed']==0 and w3last['requests_completed']==0,'W3 wrapper count anomaly inconsistent')
    require(w3result['native_summary'].endswith('/SUMMARY.json'),'W3 native summary pointer')
    output['W3_requests_completed_resolution']={'verdict':'wrapper-field anomaly; does not mean zero HTTP requests','actual_successful_native_http_windows':sum(len(x['shapes']) for x in [output['W3']]),'writer_cause':'work.py full-census branch only promotes summary OBSERVED into canonical_W3_observed and sets first_request_ok=(rc==0), result_writer_ok=true; it never advances smoke-only requests_completed initialized to 0; smoke branch increments after each completed request','source':'evidence/w3/work.py','producer_path':'evidence/w3/work.py'}
    w2run=W2ROOT/'run'
    w2result=read(w2run/'result.json'); w2work=read(w2run/'WORK-RESULT.json'); w2last=read(W2ROOT/'LAST-RESULT.json')
    require(w2result['rc']==0 and w2result['first_request_ok'] and w2result['requests_completed']==0,'W2 wrapper anomaly not reproduced')
    require(w2work['requests_completed']==0 and w2last['requests_completed']==0,'W2 wrapper count anomaly inconsistent')
    output['W2_requests_completed_resolution']={'verdict':'same full-census wrapper-field anomaly; does not mean zero HTTP requests','actual_successful_native_http_windows':sum(len(x['shapes']) for x in [output['W2']]),'writer_cause':'work.py full-census branch only promotes summary OBSERVED into current_W2_CPU_observed and sets first_request_ok=(rc==0), result_writer_ok=true; it never advances smoke-only requests_completed initialized to 0; smoke branch increments after each completed request','source':'evidence/w2/work.py','producer_path':'evidence/w2/work.py'}
    out=pathlib.Path(__file__).resolve().parent/'REPLAY.json'
    out.write_text(json.dumps(output,indent=2,sort_keys=True)+'\n')
    print(out)
    print(json.dumps({k:(v if k.endswith('_resolution') else {'native_sha256':v['native_sha256'],'shapes':v['shapes']}) for k,v in output.items()},indent=2,sort_keys=True))
