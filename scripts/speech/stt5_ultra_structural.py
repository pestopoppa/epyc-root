#!/usr/bin/env python3
"""Read-only structural comparator. No inferential pass/fail is produced.

Unequal shapes are reported as UNALIGNED, without trimming or numeric comparison.
Input seals bind every consumed file. Historical bindings and the fixed engineering
cohort are checked separately; this tool creates no new measurement warrant.
"""
import argparse, hashlib, json, os, pathlib, re, signal, sys, time
import numpy as np

REQUIRED = {'torch': {'torch/frontend.npy','torch/attention_mask.npy','torch/encoder.npy','torch/joint_logits.npy','torch/result.json'}, 'f32': {'f32/pcm.f32','f32/shapes.txt','f32/mel.f32','f32/encoder.f32','f32/joint_logits.f32','f32/steps.tsv'}, 'q8': {'q8/pcm.f32','q8/shapes.txt','q8/mel.f32','q8/encoder.f32','q8/joint_logits.f32','q8/steps.tsv'}}

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def validate(case, arm):
    case = pathlib.Path(case)
    if case.is_symlink(): raise ValueError('symlink case')
    def read(name):
        p=case/name
        if p.is_symlink() or not p.is_file(): raise ValueError('missing or symlink '+name)
        return json.loads(p.read_bytes())
    exp=read(arm+'.exposure.json'); result=read(arm+'.result.json'); seal=read(arm+'.seal.json')
    if seal.get('exposure_sha256')!=digest(case/(arm+'.exposure.json')) or seal.get('result_sha256')!=digest(case/(arm+'.result.json')): raise ValueError('seal mismatch')
    if exp.get('arm')!=arm or type(result.get('rc')) is not int or result.get('rc')!=0 or result.get('interrupted') is not False: raise ValueError('invalid arm result')
    files=result.get('files');
    if not isinstance(files,dict) or not (REQUIRED[arm] | {arm+'-run.stdout',arm+'-run.stderr'}).issubset(files): raise ValueError('missing inventory entries')
    for name, expected in files.items():
        rel=pathlib.PurePosixPath(name)
        if rel.is_absolute() or '..' in rel.parts or not re.fullmatch(r'[0-9a-f]{64}', str(expected)): raise ValueError('invalid inventory entry')
        path=case.joinpath(*rel.parts)
        if any((case.joinpath(*rel.parts[:i])).is_symlink() for i in range(1,len(rel.parts)+1)): raise ValueError('symlink')
        if not path.is_file() or digest(path)!=expected: raise ValueError('inventory mismatch '+name)
    actual = {str(p.relative_to(case)) for p in (case/arm).rglob('*') if p.is_file()}
    actual |= {name for name in (arm+'-run.stdout', arm+'-run.stderr') if (case/name).exists()}
    if actual != set(files): raise ValueError('output inventory changed '+arm)
    return exp

def stats(name,a,b):
    if not np.isfinite(a).all() or not np.isfinite(b).all(): return {'name':name,'state':'NONFINITE','reference_shape':list(a.shape),'native_shape':list(b.shape)}
    if a.shape!=b.shape: return {'name':name,'state':'UNALIGNED','reference_shape':list(a.shape),'native_shape':list(b.shape)}
    if not a.size: return {'name':name,'state':'EMPTY','reference_shape':list(a.shape)}
    d=np.abs(a.astype(np.float64)-b.astype(np.float64))
    return {'name':name,'state':'COMPARABLE','shape':list(a.shape),'max_abs':float(d.max()),'mean_abs':float(d.mean()),'rmse':float(np.sqrt(np.mean(d*d)))}

def preflight(root, cases):
    """Audit sealed inventories before publishing; never load tensors or emit comparisons."""
    errors=[]
    for case in cases:
        if not re.fullmatch('[0-9a-f]{64}',case):
            raise ValueError('invalid case identity')
        for arm in ('torch','f32','q8'):
            try:
                validate(pathlib.Path(root)/case,arm)
            except (ValueError, OSError) as error:
                errors.append({'case':case,'arm':arm,'error':str(error)})
    return {'schema':'ultra.inventory-preflight.v1','ready':not errors,
            'cases':len(cases),'arms_checked':len(cases)*3,'errors':errors,
            'verdict':'NOT_EVALUATED','inference_run':False}

def compare(case,arm):
    case=pathlib.Path(case); ref=validate(case,'torch'); native=validate(case,arm)
    for key in ('clip_id','catalog_sha256','wav_sha256','pcm_s16_sha256','plan_sha256','input_manifest_sha256','processor_config_sha256','generation_config_sha256','ultra_model_sha256','native_library_sha256'):
        if not ref.get(key) or ref.get(key)!=native.get(key): raise ValueError('cross-arm binding mismatch '+key)
    t=case/'torch'; n=case/arm
    reference = json.loads((t/'result.json').read_text())
    if (reference['audio_file_sha256'] != ref['wav_sha256']
            or reference['model_sha256'] != ref['ultra_model_sha256']
            or reference['processor_config_sha256'] != ref['processor_config_sha256']
            or reference['generation_config_sha256'] != ref['generation_config_sha256']):
        raise ValueError('reference metadata binding mismatch')
    if digest(n/'pcm.f32') != reference['pcm_sha256'] or (n/'pcm.f32').stat().st_size != reference['samples']*4:
        raise ValueError('decoded PCM mismatch')
    def raw(name,width):
        arr=np.fromfile(n/name,dtype='<f4')
        if not arr.size or arr.size%width: raise ValueError('invalid native length '+name)
        return arr.reshape(-1,width)
    frontend=np.load(t/'frontend.npy',allow_pickle=False)[0]; mask=np.load(t/'attention_mask.npy',allow_pickle=False)[0]; mel=raw('mel.f32',128)
    if len(mask)!=len(frontend) or int(mask.sum())!=len(mel) or not np.array_equal(mask,np.arange(len(mask))<len(mel)): raise ValueError('frontend mask mismatch')
    encoder=np.load(t/'encoder.npy',allow_pickle=False)[0]; native_encoder=raw('encoder.f32',1024)
    logits=np.load(t/'joint_logits.npy',allow_pickle=False).reshape(-1,8198); native_logits=raw('joint_logits.f32',8198)
    lines=(n/'steps.tsv').read_text().splitlines(); steps=[list(map(int,line.split())) for line in lines if line and line[0].isdigit()]
    if not steps or any(len(row)!=5 or row[0]!=i or not 0<=row[2]<8198 or row[4]<0 for i,row in enumerate(steps)): raise ValueError('malformed steps')
    result=json.loads((t/'result.json').read_text()); ids=result['token_ids_including_blanks'][0][1:]; dur=result['durations'][0][1:]
    if len(ids)!=len(logits) or len(dur)!=len(ids) or len(steps)!=len(native_logits): raise ValueError('step count mismatch')
    ni=[x[2] for x in steps]; nd=[x[4] for x in steps]
    return {'schema':'ultra.structural-compare.v1','arm':arm,'clip_id':ref['clip_id'],'comparisons':[stats('frontend',frontend[:len(mel)],mel),stats('encoder',encoder,native_encoder),stats('joint_logits',logits,native_logits)],'tokens_equal':ids==ni,'durations_equal':dur==nd,'reference_steps':len(ids),'native_steps':len(ni),'verdict':'NOT_EVALUATED','limitation':'structural diagnostics only; unequal shapes not aligned; no original verdict altered'}


def write_new(path, value):
    with path.open('x') as out:
        json.dump(value, out, sort_keys=True, allow_nan=False)
        out.write('\n'); out.flush(); os.fsync(out.fileno())


def metadata_pins(root, cases):
    return {str(path.relative_to(root)): digest(path)
            for case in cases for arm in ('torch','f32','q8')
            for path in (root/case/(arm+suffix) for suffix in ('.exposure.json','.result.json','.seal.json'))}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--preflight',action='store_true',help='audit original sealed inventories before publication; no comparisons or output files')
    ap.add_argument('config',type=pathlib.Path); args=ap.parse_args()
    cfg=json.loads(args.config.read_text()); config_sha=digest(args.config)
    smoke=os.environ.get('FILLER_SMOKE')=='1'
    root=pathlib.Path(cfg['smoke_root'] if smoke else cfg['root']).resolve()
    output=pathlib.Path(cfg['smoke_output'] if smoke else cfg['output']).resolve()
    if output.is_relative_to(root): raise ValueError('output overlaps input')
    for path,expected in cfg['pins'].items():
        if digest(pathlib.Path(path)) != expected: raise ValueError('source/input drift '+path)
    cases=cfg['smoke_cases'] if smoke else cfg['cases']
    pins=cfg['smoke_metadata'] if smoke else cfg['metadata']
    if metadata_pins(root,cases)!=pins: raise ValueError('original metadata drift')
    manifest=json.loads(pathlib.Path(cfg['manifest']).read_text())
    by_case={hashlib.sha256(row['clip_id'].encode()).hexdigest():row for row in manifest['records']}
    if not smoke and (len(by_case)!=25 or set(by_case)!=set(cases)):
        raise ValueError('original engineering cohort mismatch')
    if args.preflight:
        report=preflight(root,cases)
        report.update(config_sha256=config_sha,driver_sha256=digest(pathlib.Path(__file__)),smoke=smoke)
        print(json.dumps(report,sort_keys=True))
        return 0 if report['ready'] else 2
    output.mkdir(exist_ok=True)
    stopping=False
    def stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)
    stopfile=pathlib.Path(os.environ.get('FILLER_STOPFILE',str(output.parent/'STOP')))
    deadline=float(os.environ.get('FILLER_DEADLINE',time.time()+1230))-30
    results=[]
    for key in cases:
        if not re.fullmatch('[0-9a-f]{64}',key): raise ValueError('invalid case identity')
        for arm in ('f32','q8'):
            if stopping or stopfile.exists() or time.time()>=deadline: return 75
            path=output/(key+'-'+arm+'.json')
            # Always reopen originals, even on a resumed comparison-only run.
            value=compare(root/key,arm)
            exposure=validate(root/key,arm)
            expected=cfg['bindings'] if not smoke else cfg['smoke_bindings']
            if any(exposure.get(k)!=v for k,v in expected.items()) or exposure.get('native_model_sha256')!=cfg['native_models'][arm]: raise ValueError('historical binding drift')
            if not smoke:
                row=by_case[key]
                if exposure['clip_id']!=row['clip_id'] or exposure['wav_sha256']!=row['wav_sha256'] or exposure['input_manifest_sha256']!=digest(pathlib.Path(cfg['manifest'])):
                    raise ValueError('cohort exposure drift')
            value.update(config_sha256=config_sha,smoke=smoke)
            if path.exists():
                if json.loads(path.read_text())!=value: raise ValueError('previous diagnostic drift')
            else: write_new(path,value)
            results.append(value)
            print('STRUCTURAL',key,arm,flush=True)
    if metadata_pins(root,cases)!=pins: raise ValueError('metadata changed during comparison')
    states={}
    for result in results:
        for stage in result['comparisons']:
            label=stage['name']+':'+stage['state']; states[label]=states.get(label,0)+1
    summary={'schema':'ultra.structural-summary.v1','complete':True,'cases':len(cases),
             'pair_count':len(results),'states':states,'smoke':smoke,'epoch':time.time(),
             'tokens_equal_pairs':sum(r['tokens_equal'] for r in results),
             'durations_equal_pairs':sum(r['durations_equal'] for r in results),
             'config_sha256':config_sha,'verdict':'NOT_EVALUATED','inference_run':False,
             'limitation':'Retained engineering cases only; no quality, timing, accuracy or HIP gate. Shapes unaligned without trimming; original verdicts unchanged.'}
    summary_path=output/'summary.json'
    if not summary_path.exists(): write_new(summary_path,summary)
    if not (output/'COMPLETE.json').exists(): write_new(output/'COMPLETE.json',{'result_sha256':digest(summary_path),'pair_count':len(results)})
    return 0


if __name__=='__main__': sys.exit(main())
