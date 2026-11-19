#!/usr/bin/env python3
"""Refuse mismatched build options; write a build-only provenance record."""
import hashlib, json, os, pathlib, shlex, subprocess, sys, tempfile

from integrity import verify as verify_integrity

COMPILER_PATHS = ('/usr/bin/cc', '/usr/bin/c++', '/opt/rocm-6.2.0/lib/llvm/bin/clang++')

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''): h.update(b)
    return h.hexdigest()

def cache(path):
    result = {}
    for line in pathlib.Path(path).read_text().splitlines():
        if not line or line[0] in '#/' or '=' not in line or ':' not in line.split('=', 1)[0]: continue
        keytype, value = line.split('=', 1)
        key, kind = keytype.split(':', 1)
        if (key.startswith(('GGML_', 'LLAMA_')) and kind == 'BOOL') or key in {'CMAKE_BUILD_TYPE', 'CMAKE_C_COMPILER', 'CMAKE_CXX_COMPILER', 'CMAKE_HIP_COMPILER', 'AMDGPU_TARGETS', 'CMAKE_INSTALL_RPATH', 'CMAKE_BUILD_RPATH_USE_ORIGIN', 'CMAKE_BUILD_WITH_INSTALL_RPATH'}:
            result[key] = value
    return result

def compare_caches(reference, actual):
    missing = sorted(set(reference) - set(actual))
    extra = sorted(set(actual) - set(reference))
    changed = {k: [reference[k], actual[k]] for k in set(reference) & set(actual) if reference[k] != actual[k]}
    if missing or extra or changed:
        raise SystemExit('cache option mismatch: ' + json.dumps({'missing': missing, 'extra': extra, 'changed': changed}, sort_keys=True))

def compiler_receipt(paths=COMPILER_PATHS):
    # Keep the declared host paths as keys; completion reopens those exact paths
    # inside the same /proc/1/root namespace used by the build.
    return {name:digest(name) for name in paths}

def main(argv):
    if argv[1] == 'compare':
        compare_caches(cache(argv[2]), cache(argv[3]))
    elif argv[1] == 'smoke':
        run, out = pathlib.Path(argv[2]), pathlib.Path(argv[3])
        build = run / 'build'
        obj = build / 'src/CMakeFiles/llama.dir/llama-kv-cache.cpp.o'
        db = build / 'compile_commands.json'
        entries = [x for x in json.loads(db.read_text()) if pathlib.Path(x['file']).name == 'llama-kv-cache.cpp']
        if len(entries) != 1: raise SystemExit('expected exactly one cache object compile command')
        cmd = entries[0].get('arguments') or shlex.split(entries[0]['command'])
        if '-o' not in cmd or cmd[cmd.index('-o')+1] != 'src/CMakeFiles/llama.dir/llama-kv-cache.cpp.o':
            raise SystemExit('compile command targets unexpected object')
        if pathlib.Path(entries[0]['file']).resolve() != pathlib.Path('/mnt/raid0/llm/tmp/kvu/kpf174-custody-r3-20261104/source/src/llama-kv-cache.cpp'):
            raise SystemExit('compile command uses another source tree')
        if digest(entries[0]['file']) != 'd4619db202efa483c26403e62a0cbf82846b887d1dce44fab6e3ad54fecfa2d9':
            raise SystemExit('source mismatch')
        if 'LLAMA_KPF_LAYOUT_TRACE' not in subprocess.check_output(['strings', str(obj)], text=True):
            raise SystemExit('compiled object lacks layout knob')
        files = [obj, db, build/'CMakeCache.txt', run/'configure.log', run/'first-unit.log']
        record = {'schema':'epyc.kpf174d.first_unit.v1','status':'compiled','source_commit':'6ec877068936588b6d63dbba5842bbd540b92031','run_dir':str(run),'target':'src/CMakeFiles/llama.dir/llama-kv-cache.cpp.o','source_sha256':'d4619db202efa483c26403e62a0cbf82846b887d1dce44fab6e3ad54fecfa2d9','files':{str(p.resolve(strict=True)):digest(p) for p in files},'scope':'first object only; no binary, full build or inference verdict'}
        record['integrity'] = verify_integrity(actual_cache=run/'build/CMakeCache.txt')
        out.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix='.first-unit-', dir=out.parent)
        try:
            with os.fdopen(fd, 'w') as f: json.dump(record,f,sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno())
            os.replace(tmp,out)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
    elif argv[1] == 'write':
        run, out = pathlib.Path(argv[2]), pathlib.Path(argv[3])
        files = [run/'configure.log', run/'build.log', run/'linkage.log', run/'build/CMakeCache.txt', run/'build/bin/llama-server']
        for name in ('libllama.so', 'libllama-common.so', 'libllama-server-impl.so', 'libggml-hip.so', 'libggml.so', 'libggml-base.so', 'libggml-cpu.so'):
            files.append(run/'build/bin'/name)
        files = [p.resolve(strict=True) for p in files]
        record = {'schema':'epyc.kpf174d.build.v1','status':'built','source_commit':'6ec877068936588b6d63dbba5842bbd540b92031','parent_source':'84d0a31603d495377dee24e1159bbbf02f1e2f21','source_tar_sha256':'eb58f5b820ccfce7a7a97e8260bb14e2476caf861efa7509239fdf749151cb95','run_dir':str(run),'linkage_pass':True,'knobs':['LLAMA_KPF_LAYOUT_TRACE','LLAMA_KPF_ITEM4_TRACE','--slot-fork-min-tokens'],'binary_sha256':digest(run/'build/bin/llama-server'),'libraries':{name:digest(run/'build/bin'/name) for name in ('libllama.so','libllama-common.so','libllama-server-impl.so','libggml-hip.so','libggml.so','libggml-base.so','libggml-cpu.so')},'files':{str(p):digest(p) for p in files},'compilers':compiler_receipt(),'scope':'prospective diagnostic build only; no historical image equivalence or inference verdict'}
        record['linkage_verifier_sha256'] = digest('/mnt/raid0/llm/tmp/kvu/kpf174-custody-r3-20261104/v3/verify_ggml_linkage.sh')
        if record['linkage_verifier_sha256'] != '57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33': raise SystemExit('linkage verifier mismatch')
        record['integrity'] = verify_integrity(actual_cache=run/'build/CMakeCache.txt')
        out.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix='.proof-', dir=out.parent)
        try:
            with os.fdopen(fd, 'w') as f: json.dump(record, f, sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno())
            os.replace(tmp, out)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
    else:
        raise SystemExit('unknown command')

if __name__ == '__main__':
    main(sys.argv)
