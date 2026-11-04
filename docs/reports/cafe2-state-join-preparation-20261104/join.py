#!/usr/bin/env python3
"""Prospective CAFE-2 state join; validates producer-authored snapshot digests.

Input is two source-authored JSON records plus raw snapshot files. No original
run lacking its own snapshot digest can be upgraded by this verifier.
"""
import argparse, hashlib, json, math, pathlib, re, sys
ORDER=[[1,5,9,2,6,3,7,4,8,1,5],[9,1,8,3,7,4,6,2,5,1,5],[5,2,8,1,7,3,9,4,6,1,5],[2,6,4,8,1,9,3,7,5,1,5],[8,4,7,2,9,5,3,1,6,1,5]]
HEX=re.compile(r'^[0-9a-f]{64}$')
class Unknown(Exception): pass
def need(condition, reason):
    if not condition: raise Unknown(reason)
def unique_object(pairs):
    out={}
    for key,value in pairs:
        need(key not in out,'duplicate JSON member')
        out[key]=value
    return out
def bad_constant(value):
    raise Unknown('nonfinite JSON constant '+value)
def read_json(path):
    need(path.stat().st_size <= 64*1024*1024,'JSON too large')
    with path.open() as f:return json.load(f,object_pairs_hook=unique_object,parse_constant=bad_constant)
def sha_file(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def clean_path(root, name):
    need(isinstance(name,str) and name and '\x00' not in name,'missing snapshot path')
    p=(root/name).resolve(strict=True)
    need(p.is_relative_to(root) and p.is_file(),'snapshot outside attempt root or not regular')
    return p
def validate_arm(arm,kind,root):
    need(isinstance(arm,dict) and arm.get('schema')=='cafe2.state-join.arm.v1' and arm.get('arm')==kind,'wrong source schema/arm')
    need(arm.get('status')=='COMPLETE' and arm.get('child_reaped') is True and arm.get('cutoff') is None,'partial or unclosed arm')
    for k in ('source_sha256','binary_sha256','model_sha256','state_sha256'):
        need(isinstance(arm.get(k),str) and HEX.fullmatch(arm[k]) is not None,'missing digest '+k)
    need(type(arm.get('state_bytes')) is int and 0<arm['state_bytes']<=2**31,'invalid snapshot size')
    snapshot=clean_path(root,arm.get('state_file'))
    need(snapshot.stat().st_size==arm['state_bytes'] and sha_file(snapshot)==arm['state_sha256'],'snapshot mismatch')
    need(type(arm.get('effective_threads')) is int and arm['effective_threads']>0,'threads missing')
    need(type(arm.get('effective_batch_threads')) is int and arm['effective_batch_threads']>0,'batch threads missing')
    need(isinstance(arm.get('libraries'),dict) and arm['libraries'] and all(isinstance(k,str) and isinstance(v,str) and HEX.fullmatch(v) for k,v in arm['libraries'].items()),'library identity missing')
    p=arm.get('plan');need(isinstance(p,dict),'missing original plan')
    for k in ('prompt_tokens','draft_tokens'):
        need(isinstance(p.get(k),list) and p[k] and all(type(x) is int and x>=0 for x in p[k]),'bad plan '+k)
    need(len(p['draft_tokens'])==8 and type(p.get('boundary')) is int and p['boundary']>=0 and p.get('arm')==kind,'bad boundary/chain/arm')
    cells=arm.get('cells');need(isinstance(cells,list) and len(cells)==55,'full 55-cell coverage required')
    for k,c in enumerate(cells):
        rep,idx=divmod(k,11);need(isinstance(c,dict) and type(c.get('window')) is int and c['window']==k and type(c.get('rep')) is int and type(c.get('cell')) is int and type(c.get('rows')) is int and (c['rep'],c['cell'],c['rows'])==(rep,idx,ORDER[rep][idx]) and type(c.get('position_start')) is int and c['position_start']==len(p['prompt_tokens']) and c.get('state_equal') is True and c.get('state_sha256')==arm['state_sha256'],'wrong cell/order/position/state')
        if kind=='timing_no_callback':
            ns=c.get('ns');need(type(ns) in (int,float) and math.isfinite(ns) and ns>=1000,'bad elapsed cell')
            need(c.get('callback_enabled') is False,'timing callback not disabled')
        else:
            need(c.get('coverage_complete') is True and type(c.get('decode_rc')) is int and c['decode_rc']==0 and c.get('expected_layers')==40 and c.get('experts')==256 and c.get('topk')==8 and c.get('target_tokens')==[p['boundary']]+p['draft_tokens'][:c['rows']-1],'bad census closure/target')
            layers=c.get('layers');need(isinstance(layers,list) and len(layers)==40,'missing layer coverage')
            seen=set()
            for layer in layers:
                need(isinstance(layer,dict) and type(layer.get('id')) is int and 0<=layer['id']<40 and layer['id'] not in seen,'duplicate/invalid layer');seen.add(layer['id'])
                need(all(type(layer.get(x)) is int for x in ('window','rep','cell','position_start','rows','experts','topk')) and layer.get('window')==k and layer.get('rep')==rep and layer.get('cell')==idx and layer.get('position_start')==c['position_start'] and layer.get('rows')==c['rows'] and layer.get('tensor')==f"ffn_moe_topk-{layer['id']}" and isinstance(layer.get('shape'),list) and all(type(x) is int for x in layer['shape']) and layer.get('shape')==[8,c['rows'],1,1] and layer.get('experts')==256 and layer.get('topk')==8,'bad layer identity/shape')
                stride=layer.get('strides_bytes');need(isinstance(stride,list) and len(stride)==4 and all(type(x) is int and x>0 for x in stride) and stride[0]==4 and 32<=stride[1]<=1024,'bad tensor stride')
                rows=layer.get('expert_ids_by_token');need(isinstance(rows,list) and len(rows)==c['rows'],'bad expert rows')
                for row in rows:need(isinstance(row,list) and len(row)==8 and all(type(x) is int and 0<=x<256 for x in row) and len(set(row))==8,'bad expert IDs')
                unique={x for row in rows for x in row};need(type(layer.get('union_count')) is int and layer['union_count']==len(unique) and layer.get('union_ids')==sorted(unique),'union mismatch')
            need(seen==set(range(40)),'missing layer')
    return arm
def join(expert,timing,root):
    a=validate_arm(expert,'expert_census',root);b=validate_arm(timing,'timing_no_callback',root)
    for k in ('source_sha256','binary_sha256','model_sha256','state_sha256','state_bytes','effective_threads','effective_batch_threads','libraries'):
        need(a[k]==b[k],'cross-arm mismatch '+k)
    for k in ('prompt_tokens','draft_tokens','boundary'):
        need(a['plan'][k]==b['plan'][k],'cross-arm plan mismatch '+k)
    return {'status':'MATCHED_PRODUCER_SNAPSHOT_DECLARATIONS','scope':'snapshot bytes and source-authored 55-cell declarations match; no authenticity, runtime mapping, timing floor, cost verdict or belief warrant','state_sha256':a['state_sha256'],'cells':55,'threads':a['effective_threads'],'batch_threads':a['effective_batch_threads']}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--expert',required=True);ap.add_argument('--timing',required=True);args=ap.parse_args()
    try:
        root=pathlib.Path(args.root).resolve(strict=True);need(root.is_dir(),'root not directory')
        a=read_json(clean_path(root,args.expert))
        b=read_json(clean_path(root,args.timing))
        print(json.dumps(join(a,b,root),sort_keys=True));return 0
    except (Unknown,OSError,ValueError,TypeError,KeyError,RecursionError) as exc:
        print(json.dumps({'status':'UNKNOWN','reason':str(exc)}));return 2
if __name__=='__main__':sys.exit(main())
