#!/usr/bin/python3
"""Private C5 HYBRID vs F32 timing; an owner must review before use."""
import ctypes, datetime, hashlib, importlib.util, json, math, os, pathlib, signal, statistics, subprocess, sys, time
D = pathlib.Path(__file__).resolve().parent
SMOKE = os.environ.get('RTG57_SMOKE') == '1'
B = pathlib.Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/buildcpu/bin')
MODEL = pathlib.Path('/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf')
RESEARCH = D/'research'
sys.path.insert(0, str(RESEARCH/'scripts/lib'))
import canonical_recipe as canonical
import qwen38_flash_next_recipe as recipe
class WindowPartial(Exception):
    pass

active = None
birth = None
spec = importlib.util.spec_from_file_location('t1_drain', D/'deps/dryrun_check.py')
t1_drain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t1_drain)
libc = ctypes.CDLL(None, use_errno=True)
if libc.prctl(36, 1, 0, 0, 0) != 0:
    raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER failed')

def starttime(pid):
    return pathlib.Path(f'/proc/{pid}/stat').read_text().rpartition(') ')[2].split()[19]

def cleanup():
    global active
    if active is None:
        return
    residual = t1_drain.drain_entry(active, int(birth))
    active = None
    if residual:
        raise RuntimeError('benchmark exited with descendants; drained, result invalid')

def interrupt(signum, _frame):
    cleanup()
    raise SystemExit(128 + signum)
for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
    signal.signal(sig, interrupt)

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def grade(cells):
    results = {}
    for key in cells[0]:
        effects = [(cells[b][key]-cells[a][key])/cells[a][key] for a,b in ((0,1),(3,2),(4,5))]
        m = statistics.median(effects)
        results[str(key)] = {'effects':effects,'median':m}
    verdict = 'COSTS' if any(x['median'] <= -.01 and all(v < 0 for v in x['effects']) for x in results.values()) else ('NO_COST' if all(x['median'] > -.01 for x in results.values()) else 'INCONCLUSIVE')
    return verdict, results

def main():
    global active, birth
    out = pathlib.Path(os.environ.get('RTG57_OUT', str(D/'out')))
    out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()) or (D/'COMPLETE').exists():
        raise RuntimeError('existing output; use a new reviewed entry')
    if not SMOKE and os.environ.get('FILLER_CPUS') != '0-95':
        raise RuntimeError('full 0-95 grant required')
    if not SMOKE and time.time() + 5000 >= int(os.environ['FILLER_DEADLINE']):
        raise WindowPartial('insufficient time for atomic six-arm run')
    if (D/'STOP').exists():
        raise WindowPartial('STOP')
    if subprocess.run(['/mnt/raid0/llm/tmp/compute-flags/ram_admit.sh', '110'], check=False).returncode:
        raise RuntimeError('RAM admission failed')
    env = {k:v for k,v in os.environ.items() if not k.startswith(('GGML_', 'OMP_'))}
    env.update(canonical.CANONICAL_OMP_ENV)
    env.update(recipe.CANONICAL_OMP_ENV)
    env.update(recipe.CHAMPION_GGML_ENV)
    env['LD_LIBRARY_PATH'] = str(B)
    if recipe.THREADS != 48 or recipe.KV_CACHE_FLAGS != ['-ctk', 'f16', '-ctv', 'f16'] or env.get('GGML_FA_SPLIT_KV') != '0' or pathlib.Path(recipe.TRUNK_GGUF) != MODEL:
        raise RuntimeError('recipe is not the reviewed T48 F16-V shape')
    linkage = RESEARCH/'scripts/utils/verify_ggml_linkage.sh'
    with (out/'linkage.txt').open('w') as f:
        subprocess.run(['bash', str(linkage), str(B/'llama-bench'), str(B)], env=env, stdout=f, stderr=subprocess.STDOUT, check=True)
    lib = B/'libggml-cpu.so.0.16.0'
    strings = subprocess.check_output(['strings', str(lib)], text=True).splitlines()
    if 'GGML_FA_VKQ_F32' not in strings or 'GGML_FA_VKQ_F16' not in strings:
        raise RuntimeError('candidate knobs absent')
    shards = [pathlib.Path(path) for path, _, _ in recipe.TRUNK_SHARDS]
    hashes = {str(p):sha(p) for p in ([B/'llama-bench',lib] if SMOKE else shards + [B/'llama-bench',lib])}
    if SMOKE:
        hashes.update({path:expected_sha for path,_,expected_sha in recipe.TRUNK_SHARDS})
    for path, expected_bytes, expected_sha in recipe.TRUNK_SHARDS:
        if pathlib.Path(path).stat().st_size != expected_bytes or hashes[path] != expected_sha:
            raise RuntimeError('model shard does not match canonical recipe')
    (out/'identity.json').write_text(json.dumps({'source':'c72ec82f5417bb2937310326120f149b665e8400', 'source_ops_sha256':'f0d83af52edf9d41bd76a95dd9c07d7769c8f00369c4b09474f67f2114752e3d', 'recipe_sha256':recipe.recipe_sha256(), 'sha256':hashes, 'library_mtime_ns':lib.stat().st_mtime_ns, 'threads':2 if SMOKE else 96, 'cpus':','.join(map(str,sorted(os.sched_getaffinity(0)))) if SMOKE else '0-95'}, indent=2)+'\n')
    arms = ['HYBRID'] if SMOKE else ['HYBRID','F32','F32','HYBRID','HYBRID','F32']
    cells = []
    for i, arm in enumerate(arms, 1):
        if (D/'STOP').exists() or time.time() + (5 if SMOKE else 600) >= int(os.environ['FILLER_DEADLINE']):
            raise WindowPartial('STOP or insufficient time')
        # Existing canonical placement protocol uses per-arm interleaving eviction.
        if not SMOKE:
            subprocess.run(['/usr/bin/python3','-B','-I', str(RESEARCH/'scripts/utils/numa_evict.py'), '--target-gib','40'], check=True)
        this = dict(env)
        if arm == 'F32': this['GGML_FA_VKQ_F32'] = '1'
        cmd = list(recipe.SERVE_PREFIX) + [str(B/'llama-bench'),'-m',str(MODEL),'-t','96','-fa','1','-mmp','0'] + list(recipe.KV_CACHE_FLAGS) + ['-p','5','-n','64','-d','8192,32768','-r','10','-o','jsonl','--progress']
        if SMOKE:
            cpus = sorted(os.sched_getaffinity(0))
            if len(cpus) != 2:
                raise RuntimeError('CPU smoke requires exactly two admitted CPUs')
            cmd = ['taskset','-c',','.join(map(str,cpus)),str(B/'llama-bench'),'-m',str(MODEL),'-t','2','-fa','1','-mmp','1'] + list(recipe.KV_CACHE_FLAGS) + ['-p','1','-n','8','-d','0','-r','10','-o','jsonl','--progress']
        with (out/f'{i}-{arm}.jsonl').open('w') as stdout, (out/f'{i}-{arm}.err').open('w') as stderr:
            active = subprocess.Popen(cmd, env=this, stdout=stdout, stderr=stderr, start_new_session=True)
            birth = starttime(active.pid)
            ident = t1_drain.identity(active.pid)
            if ident is None or ident[:4] != (os.getuid(),active.pid,active.pid,int(birth)):
                cleanup()
                raise RuntimeError('owned benchmark session identity mismatch')
            try:
                until = time.monotonic() + 300
                while time.monotonic() < until:
                    if 'benchmark 1/' in (out/f'{i}-{arm}.err').read_text(errors='replace'):
                        break
                    if active.poll() is not None:
                        raise RuntimeError('benchmark died before warmup')
                    time.sleep(0.05 if SMOKE else 2)
                else:
                    raise RuntimeError('warmup timed out')
                if starttime(active.pid) != birth:
                    raise RuntimeError('benchmark process identity changed')
                if pathlib.Path(f'/proc/{active.pid}/exe').resolve() != (B/'llama-bench').resolve():
                    raise RuntimeError('unexpected actual executable')
                maps = pathlib.Path(f'/proc/{active.pid}/maps').read_text()
                if str(lib.resolve()) not in maps:
                    raise RuntimeError('candidate CPU library not mapped')
                (out/f'{i}-{arm}.maps').write_text(maps)
                with (out/f'{i}-{arm}.numa').open('w') as placement:
                    if not SMOKE:
                        subprocess.run(['bash', str(RESEARCH/'scripts/utils/numa_placement_check.sh'), str(active.pid)], stdout=placement, stderr=subprocess.STDOUT, check=True)
                if 'ADVISORY' in (out/f'{i}-{arm}.numa').read_text():
                    raise RuntimeError('NUMA sample too small')
                raw = pathlib.Path(f'/proc/{active.pid}/environ').read_bytes().split(b'\0')
                actual = dict(x.split(b'=',1) for x in raw if b'=' in x)
                expected = {k.encode():v.encode() for k,v in this.items() if k.startswith(('GGML_', 'OMP_'))}
                observed = {k:v for k,v in actual.items() if k.startswith((b'GGML_',b'OMP_'))}
                if observed != expected:
                    raise RuntimeError('actual process env mismatch')
                (out/f'{i}-{arm}.env.json').write_text(json.dumps({k.decode():v.decode(errors='replace') for k,v in actual.items() if k.startswith((b'GGML_',b'OMP_'))},sort_keys=True)+'\n')
                (out/f'{i}-{arm}.process.json').write_text(json.dumps({'pid':active.pid,'start_ticks':birth,'pgid':os.getpgid(active.pid),'cmd':cmd})+'\n')
                rc = active.wait()  # outer captured-descendant watcher owns deadline and partial handling
                if rc: raise RuntimeError(f'benchmark exited {rc}')
            finally:
                cleanup()
        rows = [json.loads(s) for s in (out/f'{i}-{arm}.jsonl').read_text().splitlines() if s.startswith('{')]
        if SMOKE:
            if not rows or not any((r.get('n_gen') or 0)>0 for r in rows):
                raise RuntimeError('smoke has no completed real decode row')
            (out/'SMOKE.json').write_text(json.dumps({'first_request_ok':True,'result_writer_ok':True,'cleanup_verified':True,'partial':False,'model_sha256_source':'canonical recipe TRUNK_SHARDS; no fresh full model hash in smoke','model_sha256':{path:expected for path,_,expected in recipe.TRUNK_SHARDS},'rows':rows},indent=2)+'\n')
            return
        if len(rows) != 4 or any(r.get('autokernel_hardened') is not False for r in rows):
            raise RuntimeError('invalid row count or hardened protocol')
        cell = {(1 if r['n_gen'] else r['n_prompt'],r['n_depth']):r['avg_ts'] for r in rows}
        if set(cell) != {(1,8192),(5,8192),(1,32768),(5,32768)} or any(not math.isfinite(v) or v <= 0 for v in cell.values()):
            raise RuntimeError('invalid metric cells')
        cells.append(cell)
    verdict, results = grade(cells)
    (out/'verdict.json').write_text(json.dumps({'verdict':verdict,'cells':results,'classification':'indicative; not correctness or owner acceptance'},indent=2)+'\n')
    evidence = {p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()}
    receipt = {'schema':'epyc.rtg57.vkq_comparison.native.v1',
               'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'source_commit':'c72ec82f5417bb2937310326120f149b665e8400',
               'recipe_sha256':recipe.recipe_sha256(), 'protocol_id':None,
               'predeclared_rule_sha256':sha(D/'PROTOCOL.md'),
               'source_manifest_sha256':sha(D/'SOURCES.sha256'),
               'producer_script_sha256':sha(pathlib.Path(__file__)),
               'n_process_pairs':3, 'arm_order':arms, 'cells':results,
               'effect_unit':'relative_throughput', 'effect_direction':'higher_better',
               'native_verdict':verdict, 'evidence_sha256':evidence,
               'claim_scope':'indicative T96 CPU timing; no correctness or deployment acceptance'}
    raw = json.dumps(receipt,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    receipt['content_sha256'] = hashlib.sha256(raw).hexdigest()
    (out/'native-receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    with (out/'projected-claims.json').open('w') as projected:
        subprocess.run(['/usr/bin/python3','-B','-I',str(D/'projector.py'),str(out/'native-receipt.json')], stdout=projected, check=True)
    (D/'COMPLETE').write_text('comparison complete; owner review required\n')

if __name__ == '__main__':
    try: main()
    except WindowPartial as exc:
        out=pathlib.Path(os.environ.get('RTG57_OUT',str(D/'out')));out.mkdir(parents=True,exist_ok=True)
        (out/'PARTIAL.json').write_text(json.dumps({'partial':True,'rc':75,'reason':str(exc)})+'\n')
        raise SystemExit(75)
    finally: cleanup()
