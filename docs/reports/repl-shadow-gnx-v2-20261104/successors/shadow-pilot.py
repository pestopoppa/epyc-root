#!/usr/bin/env python3
"""Private three-query runtime wiring pilot. Not a retrieval-quality evaluation."""
import datetime, hashlib, json, os, pathlib, re, subprocess, sys, time, urllib.request, uuid
P=pathlib.Path('/mnt/raid0/llm/tmp/agentic-serving-harness-fixes/shadow-pilot')
SRC=pathlib.Path('/mnt/raid0/llm/tmp/agentic-serving-harness-fixes/b4k-successor-orch')
BIN='/mnt/raid0/llm/kernels/production/cpu/llama-server'
MODELS={'bge-large':'/mnt/raid0/llm/models/bge-large-en-v1.5-f16.gguf','granite-97m-r2':'/mnt/raid0/llm/models/granite-embedding-97m-multilingual-r2-f16.gguf','frontdoor':'/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf'}
PORTS={'bge-large':19081,'granite-97m-r2':19082,'frontdoor':19083}
sys.path[:0]=[str(P),str(SRC),str(SRC/'scripts/benchmark')]
from bridge import ShadowBridge
from scripts.vidya.producers.repl_shadow_validate import validate_shadow_stream
from src.repl_environment.context_bundle import ContextBundle, Section
from repl_emb_arms import LlamaServerAdapter
from repl_emb_eval import eval_specs


def digest(b): return hashlib.sha256(b).hexdigest()
def post(port,path,payload,timeout=300):
    req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.load(r)

def main():
    phase='smoke' if os.environ.get('FILLER_DRYRUN')=='1' else 'run'
    out=P/'out'/phase/uuid.uuid4().hex; out.mkdir(parents=True,exist_ok=True)
    result=out/'results.jsonl'
    if result.exists(): raise RuntimeError('output exists; unique phase directory required')
    if phase=='smoke':
        env=dict(os.environ,LD_LIBRARY_PATH=str(pathlib.Path(BIN).resolve().parent))
        with (out/'bge.log').open('wb') as log:
            proc=subprocess.Popen([BIN,'-m',MODELS['bge-large'],'--host','127.0.0.1','--port',str(PORTS['bge-large']),'-t','4','-c','4096','-np','1','--no-mmap','--embedding'],stdout=log,stderr=subprocess.STDOUT,env=env)
            try:
                if os.environ.get('FILLER_PIDFILE'):
                    with open(os.environ['FILLER_PIDFILE'],'a') as f:f.write(str(proc.pid)+'\n')
                deadline=time.time()+300
                while time.time()<deadline:
                    if proc.poll() is not None:raise RuntimeError('smoke embedder exited')
                    try:
                        with urllib.request.urlopen(f'http://127.0.0.1:{PORTS["bge-large"]}/health',timeout=2) as r:
                            if r.status==200:break
                    except Exception:time.sleep(2)
                else:raise RuntimeError('smoke embedder health deadline')
                spec=eval_specs('llama-server-production-v10','not-used')['bge-large']
                embedder=LlamaServerAdapter(spec,f'http://127.0.0.1:{PORTS["bge-large"]}')
                bundle=ContextBundle([Section('doc','The retrieval index stores searchable source chunks.')],search_enabled=True)
                bundle.set_embedder(embedder);hits=bundle.search('searchable source',k=1)
                if not hits or bundle._search_log[-1]['mode']!='hybrid': raise RuntimeError('smoke native hybrid search failed')
                with result.open('w') as f:f.write(json.dumps({'phase':'smoke','arm':'bge-large','native_ranked_hits':len(hits),'mode':'hybrid'})+'\n')
            finally:
                if proc.poll() is None:proc.terminate()
                try:proc.wait(timeout=30)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=30)
        return 0
    if subprocess.check_output(['git','-C',str(SRC),'rev-parse','HEAD'],text=True).strip() != '77ba24efe7f27783a3a98be5474bace26c753f12': raise RuntimeError('source pin mismatch')
    prepared=json.loads((P/'prepared-inputs.json').read_text())
    for arm, path in MODELS.items():
        st=pathlib.Path(path).stat(); pin=prepared[arm]
        if (st.st_size,st.st_ino,st.st_mtime_ns)!=(pin['size'],pin['inode'],pin['mtime_ns']):raise RuntimeError('prepared input changed: '+arm)
    if digest(pathlib.Path(BIN).resolve().read_bytes()) != prepared['kernel']['sha256']:raise RuntimeError('kernel digest mismatch')
    (out/'prepared-inputs.json').write_text(json.dumps(prepared,indent=2))
    env=dict(os.environ,LD_LIBRARY_PATH=str(pathlib.Path(BIN).resolve().parent))
    link=subprocess.run(['/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh',BIN,env['LD_LIBRARY_PATH']],env=env,text=True,capture_output=True)
    (out/'linkage.txt').write_text(link.stdout+link.stderr)
    if link.returncode: raise RuntimeError('linkage check failed')
    owned=[]; files=[]; bridge=None
    try:
        import socket
        for port in PORTS.values():
            with socket.socket() as sock:
                sock.settimeout(1)
                if sock.connect_ex(('127.0.0.1',port))==0:raise RuntimeError('port already in use')
        for arm,model in MODELS.items():
            argv=[BIN,'-m',model,'--host','127.0.0.1','--port',str(PORTS[arm]),'-t','3' if arm!='frontdoor' else '16','-c','4096','-np','1','--no-mmap']
            if arm!='frontdoor': argv+=['--embedding']
            log=(out/(arm+'.log')).open('wb');files.append(log)
            proc=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,env=env); owned.append(proc)
            pidfile=os.environ.get('FILLER_PIDFILE')
            if pidfile:
                with open(pidfile,'a') as f:f.write(str(proc.pid)+'\n')
            (out/(arm+'-launch.json')).write_text(json.dumps({'argv':argv,'pid':proc.pid,'ld_library_path':env['LD_LIBRARY_PATH'],'phase':'run','binary_realpath':str(pathlib.Path(BIN).resolve()),'model':model},indent=2))
        for arm,proc in zip(MODELS,owned):
            deadline=min(time.time()+600,float(os.environ.get('FILLER_DEADLINE',time.time()+1800))-120)
            while time.time()<deadline:
                if proc.poll() is not None: raise RuntimeError(f'{arm} exited {proc.returncode}')
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{PORTS[arm]}/health',timeout=2) as r:
                        if r.status==200:
                            listeners=subprocess.check_output(['ss','-ltnp','sport',':'+str(PORTS[arm])],text=True)
                            if 'pid='+str(proc.pid)+',' not in listeners: raise RuntimeError('listener ownership mismatch')
                            break
                except Exception: time.sleep(2)
            else: raise RuntimeError(f'{arm} health deadline')
        specs=eval_specs('llama-server-production-v10','not-used')
        selected=['bge-large','granite-97m-r2']; adapters={a:LlamaServerAdapter(specs[a],f'http://127.0.0.1:{PORTS[a]}') for a in selected}
        content={'search':(SRC/'src/repl_environment/context_search.py').read_text()[:3000],'bundle':(SRC/'src/repl_environment/context_bundle.py').read_text()[:3000], 'trajectory':(SRC/'src/graph/trajectory_artifact.py').read_text()[:3000]}
        sections=[Section(k,v) for k,v in content.items()]
        bundles={a:ContextBundle(sections,search_enabled=True) for a in selected}
        for a in selected: bundles[a].set_embedder(adapters[a])
        ids={a:specs[a].index_identity()['digest'] for a in selected}
        bridge=ShadowBridge(out,run_id='online_shadow_'+uuid.uuid4().hex[:12],session=uuid.uuid4().hex[:16],source_sha256=digest((SRC/'src/repl_environment/context_search.py').read_bytes()),arm_identities=ids,arm_modes={a:'hybrid' for a in selected},sections=content)
        queries=['How is text divided into searchable chunks?', 'How does context expose retrieval pointers?', 'Where are trajectory events and outputs recorded?']
        with result.open('w') as f:
            for number,query in enumerate(queries):
                if os.path.exists(os.environ.get('FILLER_STOPFILE',str(P/'STOP'))) or time.time()>float(os.environ.get('FILLER_DEADLINE',time.time()+600))-120: break
                def search(arm,q):
                    hits=bundles[arm].search(q,k=3)
                    mode=bundles[arm]._search_log[-1]['mode']
                    return hits,mode
                hits=bridge.search(query,shown_arm='bge-large',run_arm=search)
                prompt='Select exactly one relevant pointer by number, or 0 if none. Output one digit only.\nQuestion: '+query+'\n'+'\n'.join(f'{i+1}: {h["section"]} offsets {h["start"]}-{h["end"]}' for i,h in enumerate(hits))+'\nAnswer:'
                response=post(PORTS['frontdoor'],'/completion',{'prompt':prompt,'n_predict':16,'temperature':0,'seed':42},timeout=420)
                answer=str(response.get('content','')).strip(); match=re.fullmatch(r'[0-3]',answer)
                idx=int(answer)-1 if match else -1; opened=False
                if 0<=idx<len(hits):
                    hit=hits[idx]; text=bundles['bge-large'].get(hit['section'],offset=hit['start'],max_chars=hit['end']-hit['start'])
                    if text!=content[hit['section']][hit['start']:hit['end']]:raise ValueError('opened content mismatch')
                    opened=bridge.opened(hit['section'],hit['start'],hit['end'],current_text=content[hit['section']])
                row={'phase':'run','query_number':number,'shown_arm':'bge-large','model_output':answer,'shown_pointers':hits,'actual_open':opened,'index_identity':ids,'frontdoor_timings':response.get('timings'),'model_scope':'runtime launch evidence only'}
                f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())
        bridge.close(); path=bridge.sink.path;bridge=None
        events=validate_shadow_stream(path); (out/'stream-validation.json').write_text(json.dumps({'path':str(path),'events':len(events),'validated':True}))
        return 0
    finally:
        if bridge:
            try:bridge.close()
            except Exception:pass
        for p in owned:
            if p.poll() is None:p.terminate()
        for p in owned:
            try:p.wait(timeout=30)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=30)
        for f in files:f.close()
        (out/'drain.json').write_text(json.dumps({'owned_processes_dead':all(p.poll() is not None for p in owned)}))

if __name__=='__main__':raise SystemExit(main())
