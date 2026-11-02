import json,pathlib,shutil,hashlib
old=pathlib.Path('/mnt/raid0/llm/tmp/kvfork17a-cpu-successor'); d=pathlib.Path('/mnt/raid0/llm/tmp/kvfork/kpf17a-cpu-paired'); repo=pathlib.Path('scripts/coordination/kvfork/kpf17a_cpu_paired')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p in (old/'input').iterdir(): shutil.copy2(p,d/'input'/p.name)
for n in ['baseline.tar','champion.tar']: shutil.copy2(old/'sources'/n,d/'sources'/n)
for n in ['filler_run15.sh','filler_lib.sh']: shutil.copy2(old/n,d/n)
# Preserve prior receipts separately, not reused as results or paired evidence.
(d/'prior-receipts').mkdir(exist_ok=True)
for p in (old/'out').glob('original-???.json'): shutil.copy2(p,d/'prior-receipts'/p.name)
shutil.copy2(old/'identity.json',d/'prior-receipts'/'identity.json')
s=(old/'job.py').read_text(); a=s.index('# Imported cases remain producer records'); b=s.index('# Independent original baseline first;',a); s=s[:a]+s[b:]
a=s.index('        # Prove original cases retain their outputs under the extended harness.'); b=s.index('        files={',a)
s=s[:a]+'''        # Re-run the unchanged original under this same grant, with the same
        # thread count, to avoid cross-thread reduction-order comparisons.
        if harness=='shared' and case<86:
            for arm,B in zip(('baseline','champion'),builds):
                dump=A/(arm+'-original-paired'); dump.mkdir()
                env=dict(os.environ,LD_LIBRARY_PATH=str(B/'bin'),FA_CASE=str(case),FA_DUMP_DIR=str(dump))
                env.pop('GGML_BACKEND_PATH',None); env.pop('GGML_CUDA_FA_MASK_SKIP',None)
                run(['taskset','-c',os.environ['FILLER_CPUS'],str(B/'harness-original'),'CPU','exact',threads],A/(arm+'-original-paired.txt'),env)
                _,raw=validate(A/(arm+'-original-paired.txt'),dump,case,False)
                assert raw==(A/arm/f'out_{case:02d}.bin').read_bytes(), f'original output changed in paired {arm} case {case}'
''' + s[b:]
(d/'job.py').write_text(s); (repo/'job.py').write_text(s)
launch=(old/'launch.sh').read_text().replace(str(old),str(d)).replace('kvfork17a-cpu-successor','kvfork17a-cpu-paired'); (d/'launch.sh').write_text(launch); (repo/'launch.sh').write_text(launch)
C=json.loads((old/'identity.json').read_text()); C['scope']='CPU exactness successor: original and extended preservation compared under identical grant and thread count; earlier receipts retained separately'
C['inputs']={str(p.relative_to(d)):sha(p) for p in [*(d/'input').iterdir(),*(d/'sources').glob('*.tar'),d/'job.py',d/'filler_run15.sh',d/'filler_lib.sh',*(d/'prior-receipts').iterdir()]}
(d/'identity.json').write_text(json.dumps(C,indent=2)+'\n')
spec=json.loads((old/'spec.json').read_text()); spec.update(id='kvfork17a-cpu-paired',launcher=str(d/'launch.sh'),scratch_root=str(d),result_path=str(d/'out/results.jsonl'),supersedes='kvfork17a-cpu-successor',notes='Fresh paired original versus shared harness under same grant/thread count; historical receipts retained separately, not imported as paired evidence.')
(d/'spec.json').write_text(json.dumps(spec,indent=2)+'\n'); (repo/'spec.json').write_text(json.dumps(spec,indent=2)+'\n')
