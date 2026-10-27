"""Build draft current topology recipe without a model, server, socket or grant."""
from pathlib import Path
import hashlib,json,sys
D=Path(__file__).resolve().parent;B=D.parent
N=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-inf75-census-prep')
V=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-inf75-v3-runtime-unblock/v5')
R=B/'research-main';O=B/'orch-main'
modelroot=Path('/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF')
shards=[str(modelroot/'UD-IQ4_XS'/f'Qwen3.8-Flash-Next-UD-IQ4_XS-{i:05d}-of-00003.gguf') for i in range(1,4)]
head=str(modelroot/'MTP/mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf')
build='/mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/buildcpu';binary=build+'/bin/llama-server'
p=json.loads((V/'recipes.json').read_text())['workloads'][0]
p.update(id='inf75-c5-w5s-full-census',model=shards[0],ordered_shards=shards,head=head,physical_cpus='0-95',port=18678,timeout_s=1200,
 scope='current registered architect_general full host t96 np1 ub2048 ctx262144 MTP4; primary-target tensors and graphs only; separate draft head bound by identity but its tensor inventory and draft graphs excluded; P0d remains open')
p['foreign_load']=str(D/'foreign_load.py')
native=json.loads((D/'native-builder.json').read_text())
for pin in native['sources']:
    if hashlib.sha256(Path(pin['path']).read_bytes()).hexdigest()!=pin['sha256']:
        raise ValueError('native builder source drift')
p['builder_source_pins']=native['sources']
argv=native['argv'][:]
servers=[i for i,x in enumerate(argv) if x.endswith('/llama-server')]
if len(servers)!=1:raise ValueError('unresolved production server')
server_index=servers[0]
def get(flag):
    args=argv[server_index+1:]
    if args.count(flag)!=1:raise ValueError(f'missing or duplicate production flag {flag}')
    return args[args.index(flag)+1]
for flag,expected in {'-m':shards[0],'-md':head,'-np':'1','-c':'262144','-t':'96','-ub':'2048',
                      '-ctk':'f16','-ctv':'f16','--spec-type':'draft-mtp','--spec-draft-n-max':'4',
                      '--draft-p-min':'0.5','--ctx-checkpoints':'32','--cache-ram':'32768',
                      '--host':'127.0.0.1','--device':'none'}.items():
    if get(flag)!=expected:raise ValueError(f'current production {flag} differs: {get(flag)}')
if '--mlock' not in argv or '--no-mmap' not in argv or '--interleave=all' not in argv:
    raise ValueError('current production placement or memory flags differ')
argv[server_index]=binary
for flag,value in {'--port':'18678','--slot-save-path':str(D/'runtime-slots')}.items():argv[argv.index(flag)+1]=value
argv+=['--log-verbosity','4']
p['argv']=argv
p['env']={**native['environment'],'PATH':'/usr/bin:/bin','LANG':'C.UTF-8',
 'LD_LIBRARY_PATH':build+'/bin:/usr/lib/llvm-20/lib',
 'LD_PRELOAD':str(N/'source-turn-2/libcensus-native.so'),
 'GGML_SCHED_DEBUG':'2','LLAMA_TRACE':'1','EPYC_ROOT_REPO':str(B/'root-main')}
p['request_files']={phase:str(D/f'requests-{phase}.json') for phase in ('prefill','decode','verify')}
p['capture_inputs'].update({'model':shards[0],'model_shard_2':shards[1],'model_shard_3':shards[2],'drafter':head,
 'recipe':str(D/'recipes.json'),'binding':str(D/'OWNER-RECIPE-BOUND.json'),'producer':str(B/'private_census.py'),
 'driver':str(D/'driver.py'),'server_probe':str(D/'server_probe_full.py'),'server_evidence':str(B/'server_evidence_full.py'),
 'workload_contract':str(D/'runtime/autokernel/controller/workload_contract.py'),
 'capture_module':str(D/'runtime/autokernel/loop/census_capture.py'),
 'residency':str(D/'runtime/autokernel/loop/residency.py'),'owner_start':str(D/'owner-start.json'),
 'build_receipt_binding':str(D/'BUILD-RECEIPT-PATH'),
 'python_identity':str(D/'PYTHON.sha256'),
 'native_touch':str(D/'native-full-touch.py'),'source_manifest':str(D/'SOURCES.sha256'),
 'split_reader':str(B/'flash_next_census.py'),'split_inspector':str(B/'split_inspect.py'),'belief_writer':str(B/'census_belief.py'),
 'foreign_load':str(D/'foreign_load.py'),
 'registry':str(R/'orchestration/model_registry.yaml'),'topology':str(O/'orchestration/stack_topology.yaml'),
 'builder_snapshot':str(D/'native-builder.json'),'builder_source':str(O/'scripts/server/orchestrator_stack.py'),
 'model_digests':str(B/'model.sha256')})
p.pop('source_target',None);p.pop('source_export_sha256',None);p['capture_inputs'].pop('native_export',None)
p['capture_inputs'].pop('chat_template',None)
if '--chat-template-file' in argv:
    p['capture_inputs']['chat_template']=get('--chat-template-file')
p['large_refs']=['model_shard_2','model_shard_3','drafter']
p['capture_inputs'].update({f'builder_input_{i}':pin['path'] for i,pin in enumerate(native['sources'])})
p['diagnostic_deltas']={'kernel':'private C5 candidate and callback-free host tracer','port':'private 18678','startup_eviction':'40 GiB target per owned node 0-3; bounded full-byte touches','scope':'structural observations only'}
for phase in ('decode','verify'):
    req=json.loads((V/f'requests-{phase}.json').read_text());req[0]['n_predict']=48
    (D/f'requests-{phase}.json').write_text(json.dumps(req)+'\n')
req=json.loads((V/'requests-prefill.json').read_text())
sys.path.insert(0,str(B))
from split_inspect import inspect
vocab=inspect(shards[0])['metadata'].get('tokenizer.ggml.tokens',{}).get('array_length',0)
if not isinstance(vocab,int) or vocab<=1 or any(token!=1 for token in req[0]['prompt']):
    raise ValueError('prefill token fixture is not bounded by this GGUF vocabulary')
p['prefill_fixture']={'token_id':1,'tokens':len(req[0]['prompt']),'gguf_vocabulary_count':vocab,
                      'note':'request only; exact 2048 same-call native tensor remains required'}
(D/'requests-prefill.json').write_text(json.dumps(req)+'\n')
(D/'recipes.json').write_text(json.dumps({'kernel_commit':p['kernel_commit'],'workloads':[p]},indent=2)+'\n')
