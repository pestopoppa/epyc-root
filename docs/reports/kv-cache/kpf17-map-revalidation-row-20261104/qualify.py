#!/usr/bin/env python3
"""Exercise the sealed KPF-17 custody.validate_maps on private mapped-DSO fixtures."""
import hashlib, importlib.util, json, os, tempfile, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED_CUSTODY_SHA256 = 'ab6d10e509d7483963a39b0da2caccab4ac8b85ee33a9e0b117107601d8d8702'
EXPECTED_BINDING_SHA256 = '5b56f806a39f24a2f68dafe147b5b56295a2975fea3914bca2a388e571b16b82'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20), b''): h.update(block)
    return h.hexdigest()

def load_sealed_custody():
    seal=json.loads((ROOT/'input_seal.json').read_text())
    binding=json.loads((ROOT/'binding.json').read_text())
    source=ROOT/'custody.py'
    if seal.get('custody_source_sha256')!=EXPECTED_CUSTODY_SHA256 or sha(source)!=EXPECTED_CUSTODY_SHA256:
        raise ValueError('sealed custody source digest mismatch')
    if seal.get('source_binding_sha256')!=EXPECTED_BINDING_SHA256 or sha(ROOT/'binding.json')!=EXPECTED_BINDING_SHA256:
        raise ValueError('source binding digest mismatch')
    if binding.get('runner_files',{}).get('custody.py')!=seal['binding_expected_custody_sha256'] or binding['runner_files']['custody.py']!=EXPECTED_CUSTODY_SHA256:
        raise ValueError('source binding does not pin copied custody.py')
    spec=importlib.util.spec_from_file_location('kpf17_alt17_sealed_custody',source)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module,seal

def maps_for(paths):
    lines=[]; expected={}
    for i,p in enumerate(paths):
        p=Path(p).resolve(strict=True); st=p.stat()
        addr=0x100000+i*0x1000
        lines.append(f'{addr:x}-{addr+0x1000:x} r-xp 00000000 {os.major(st.st_dev):x}:{os.minor(st.st_dev):x} {st.st_ino} {p}')
        expected[str(p)]=sha(p)
    return lines,expected

def run():
    custody,seal=load_sealed_custody()
    # All fixture files live below this task scratch; never link or edit the source packet's artifacts.
    with tempfile.TemporaryDirectory(prefix='alt17-fixture-',dir=ROOT) as td:
        fixture=Path(td)
        names=('libggml.so','libggml-base.so','libggml-cpu.so','libllama.so','libllama-common.so')
        paths=[]
        for name in names:
            p=fixture/name; p.write_bytes((b'private approved fixture '+name.encode()+b'\0')*128); paths.append(p)
        lines,expected=maps_for(paths)
        baseline=custody.validate_maps(lines,expected)
        if len(baseline)!=5: raise ValueError('sealed validator did not accept complete baseline fixture')

        # Deterministic mutation window: baseline validate_maps completes, then the same-UID writer
        # overwrites one private mapped path, then the sealed validator is called again on the same map.
        checked=threading.Event(); mutated=threading.Event(); outcome={}
        target=paths[0]
        def revalidate():
            checked.set()
            if not mutated.wait(5): outcome['error']='mutation barrier timeout'; return
            try:
                custody.validate_maps(lines,expected)
                outcome['result']='ACCEPTED'
            except ValueError as exc:
                outcome['result']='REFUSED'; outcome['reason']=str(exc)
        def writer():
            if not checked.wait(5): outcome['error']='validation barrier timeout'; return
            target.write_bytes(b'private mutated fixture\0'*128)
            mutated.set()
        a=threading.Thread(target=revalidate); b=threading.Thread(target=writer)
        a.start(); b.start(); a.join(6); b.join(6)
        if a.is_alive() or b.is_alive(): raise RuntimeError('barrier worker did not terminate')
        if outcome.get('error'): raise RuntimeError(outcome['error'])
        if outcome.get('result')!='REFUSED' or 'unattested mapped library' not in outcome.get('reason',''):
            raise RuntimeError('sealed validate_maps did not refuse post-baseline in-place mutation: '+repr(outcome))
        result={'schema':'kpf17.alt17-custody-race.v1','status':'PASS','sealed':True,
                'case_count':1,'unit_key':'case_count',
                'input_seal_sha256':sha(ROOT/'input_seal.json'),
                'custody_source_sha256':seal['custody_source_sha256'],
                'tested_function':'custody.validate_maps','baseline':'ACCEPTED_COMPLETE_FIVE_DSO_FIXTURE',
                'case':{'id':'same-uid-in-place-overwrite-between-map-captures','barrier':'PASS',
                        'revalidation':'REFUSED','reason':outcome['reason'],'fixture_scope':'private temporary directory'},
                'limitations':'This only proves custody.validate_maps detects this mutation when called again after the write. It does not cover mutation after the final revalidation, build_identity, the native loader, or the full KPF-17 custody chain.'}
        ROOT.joinpath('out').mkdir(parents=True,exist_ok=True)
        smoke_path=os.environ.get('FILLER_DRYRUN_RESULT_PATH') if os.environ.get('FILLER_SMOKE')=='1' else None
        destination=Path(smoke_path) if smoke_path else ROOT/'out'/'RESULT.json'
        destination.parent.mkdir(parents=True,exist_ok=True)
        tmp=destination.with_name(destination.name+'.tmp'); tmp.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n'); os.replace(tmp,destination)
    print(json.dumps({'progress':'ALT17-QUALIFICATION-COMPLETE','case_count':1,'function':'custody.validate_maps'},sort_keys=True),flush=True)

if __name__=='__main__': run()
