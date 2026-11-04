#!/usr/bin/env python3
"""Refuse mismatched build options; write a build-only provenance record."""
import hashlib, json, os, pathlib, sys, tempfile

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
    elif argv[1] == 'write':
        run, out = pathlib.Path(argv[2]), pathlib.Path(argv[3])
        files = [run/'configure.log', run/'build.log', run/'linkage.log', run/'build/CMakeCache.txt', run/'build/bin/llama-server']
        for name in ('libllama.so', 'libllama-common.so', 'libllama-server-impl.so', 'libggml-hip.so'):
            files.append(run/'build/bin'/name)
        files = [p.resolve(strict=True) for p in files]
        record = {'schema':'epyc.kpf174d.build.v1','status':'built','source_commit':'6ec877068936588b6d63dbba5842bbd540b92031','parent_source':'84d0a31603d495377dee24e1159bbbf02f1e2f21','source_tar_sha256':'eb58f5b820ccfce7a7a97e8260bb14e2476caf861efa7509239fdf749151cb95','run_dir':str(run),'linkage_pass':True,'knobs':['LLAMA_KPF_LAYOUT_TRACE','LLAMA_KPF_ITEM4_TRACE','--slot-fork-min-tokens'],'binary_sha256':digest(run/'build/bin/llama-server'),'libraries':{name:digest(run/'build/bin'/name) for name in ('libllama.so','libllama-common.so','libllama-server-impl.so','libggml-hip.so')},'files':{str(p):digest(p) for p in files},'compilers':compiler_receipt(),'scope':'prospective diagnostic build only; no historical image equivalence or inference verdict'}
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
