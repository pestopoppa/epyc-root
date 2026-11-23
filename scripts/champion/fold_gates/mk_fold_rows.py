#!/usr/bin/env python3
"""TEMPLATE: clone the previous fold's gate rows into the next fold's rows (as used for C18 -> C19, 2026-11-23).
Edit the SHA/TREE/WT/ROWS constants for the new fold, then: phase 'clone' (once), edit, phase 'seal'.
spec.json is never sealed. No evidence reuse.

Template rules (C19 lessons, scripts/champion/fold_gates/fold_row_guard.py):
  * every cloned row gets fold_row_guard.py: launch.sh runs the job through `fold_row_guard.py run` (moves a stale
    out/RESULT.json to out/stale-<ts>/, records out/RUN.json with the grant's FILLER_ID, rc and the RESULT sha256) and
    completes through `fold_row_guard.py check` (requires that RUN.json, rc 0 and the bound RESULT);
  * a "library differs between arms" proof must come from fold_row_guard.libs_differ(repo, REF, CAND, ref_bin, cand_bin),
    which derives the libraries from the candidate's own commits; never a fixed list (C19 CPU r1: libllama.so was
    byte-identical because C19 touched no src/ file, and the fixed-list proof filed FUTILITY with nothing measured)."""
import importlib.util as _ilu
import hashlib, json, os, re, shutil, sys

T = '/mnt/raid0/llm/tmp'
C17_SHA, C17_TREE = '1b83c69671a3fc0193fdf5baf929e27240478e40', '1edb2ce34632094e1e30c40ae387fffd99dc9316'
C18_SHA, C18_TREE = '74c18e2d811424402f6987c91961d9f4978e3bb1', 'a75e4aa079df474ca0dc1bf793ed03025b628400'
C19_SHA, C19_TREE = 'a6a32c1354965a315c57f4887582763336fbdda1', 'd86995def21003b8abc51a2919b5cdb18e999e06'
S19 = C19_SHA[:9]
WT19 = '/mnt/raid0/llm/llama-worktrees/c19-20261123'
G19, P19 = f'gpu-20261123-{S19}-c19', f'cpu-20261123-{S19}-c19'
ROWS = {  # src row dir -> new row id
    'c18-fold-gpu-20261122': 'c19-fold-gpu-20261123',
    'c18-fold-a3b-gpu-20261122': 'c19-fold-a3b-gpu-20261123',
    'c18-fold-cpu-20261122-r2': 'c19-fold-cpu-20261123',
    'akx31-qdec-cpu-c18-20261122': 'c19-fold-qdec-cpu-20261123',
}
TEXT = ('.py', '.sh', '.json')
GUARD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fold_row_guard.py')
_spec = _ilu.spec_from_file_location('fold_row_guard', GUARD); fold_row_guard = _ilu.module_from_spec(_spec); _spec.loader.exec_module(fold_row_guard)
LLAMA_REPO = '/mnt/raid0/llm/llama.cpp'
NEW_KNOBS = [('libggml-hip.so', 'GGML_HIP_GDN_FUSED_COLS'), ('libggml-hip.so', 'GGML_HIP_MMVF_CDNA_MAX_NE11'),
             ('libggml-hip.so', 'GGML_CUDA_AK_H15'), ('libggml-hip.so', 'GGML_HIP_Q8IP_NOPACK_GETROWS'),
             ('libllama-common.so', 'LLAMA_DTREE_DEVICE_ACCEPT')]


def sh(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def must(s, a, b, n=1):
    assert s.count(a) == n, (a[:90], s.count(a))
    return s.replace(a, b)


def relabel(s, old_row, new_row):
    pairs = [
        (old_row, '@@NEWROW@@'),
        ('/mnt/raid0/llm/worktrees/llama-c18-fold-20261122', '@@WT19@@'),
        ('llama.cpp-experimental-c18-20261122', '@@BR19@@'), ('llama.cpp-experimental-c18-20261121', '@@BR19@@'),
        (C18_SHA, '@@C19SHA@@'), (C18_TREE, '@@C19TREE@@'), (C17_SHA, '@@REFSHA@@'), (C17_TREE, '@@REFTREE@@'),
        ('gpu-20261122-74c18e2d8-c18', '@@G19@@'), ('cpu-20261122-74c18e2d8-c18', '@@P19@@'),
        ('gpu-20261121-1b83c6967-c17', '@@G18@@'), ('cpu-20261121-1b83c6967-c17', '@@P18@@'),
        ('libllama.so.0.0.10682', '@@LL19@@'), ('libllama.so.0.0.10674', '@@LL18@@'),
        ('74c18e2d8', '@@S19@@'), ('1b83c6967', '@@S18@@'),
        ('c18-fold-build-20261122', '@@BUILD19@@'),
        ('c18', '@@c19@@'), ('C18', '@@C19@@'), ('c17', 'c18'), ('C17', 'C18'),
    ]
    for a, b in pairs:
        s = s.replace(a, b)
    fin = {'@@NEWROW@@': new_row, '@@WT19@@': WT19, '@@BR19@@': 'llama.cpp-experimental-c19-20261123',
           '@@C19SHA@@': C19_SHA, '@@C19TREE@@': C19_TREE, '@@REFSHA@@': C18_SHA, '@@REFTREE@@': C18_TREE,
           '@@G19@@': G19, '@@P19@@': P19, '@@G18@@': 'gpu-20261122-74c18e2d8-c18', '@@P18@@': 'cpu-20261122-74c18e2d8-c18',
           '@@LL19@@': LL19, '@@LL18@@': 'libllama.so.0.0.10682', '@@S19@@': S19, '@@S18@@': '74c18e2d8',
           '@@BUILD19@@': 'c19-fold-build-20261123', '@@c19@@': 'c19', '@@C19@@': 'C19'}
    for a, b in fin.items():
        s = s.replace(a, b)
    return s


def clone(old, new):
    src, dst = f'{T}/{old}', f'{T}/{new}'
    assert not os.path.exists(dst), dst + ' exists'
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('out', 'out-smoke', '__pycache__', 'inc', 'STOP', 'verdict.json',
                                                            'build-*', 'src-*', 'smoke-cfg-*', 'cargo-home-empty'))
    for root, _, files in os.walk(dst):
        for f in files:
            p = os.path.join(root, f)
            if p.endswith(TEXT):
                s = open(p).read()
                s2 = relabel(s, old, new)
                if s2 != s:
                    open(p, 'w').write(s2)
    return dst


def fix_gpu(dst):
    p = dst + '/job.py'
    s = open(p).read()
    s = must(s, "('libllama-common.so', 'LLAMA_DTREE_POLICY'),):",
             "('libllama-common.so', 'LLAMA_DTREE_POLICY'),"
             + ''.join(f"\n                      ('{l}', '{k}')," for l, k in NEW_KNOBS) + "):")
    open(p, 'w').write(s)


def fix_a3b(dst):
    p = dst + '/job.py'
    s = open(p).read()
    s = must(s, "('libllama.so', 'LLAMA_DEVICE_ACCEPT')):",
             "('libllama.so', 'LLAMA_DEVICE_ACCEPT'),\n                        ('libggml-hip.so', 'GGML_HIP_MMVF_CDNA_MAX_NE11'), ('libggml-hip.so', 'GGML_HIP_GDN_FUSED_COLS')):")
    open(p, 'w').write(s)


def fix_cpu(dst):
    # CH-33 probe headers: inc/c18 = C18's own (old inc/c18), inc/c19 = the C19 tree's
    src = f'{T}/c18-fold-cpu-20261122-r2/inc/c18'
    shutil.copytree(src, dst + '/inc/c18')
    os.makedirs(dst + '/inc/c19/include')
    shutil.copy(WT19 + '/include/llama.h', dst + '/inc/c19/llama.h')
    for f in os.listdir(src + '/include'):
        shutil.copy(WT19 + '/ggml/include/' + f, dst + '/inc/c19/include/' + f)
    p = dst + '/job.py'
    s = open(p).read()
    # the C19-only CPU-visible knob string: LLAMA_DTREE_DEVICE_ACCEPT in libllama-common (26654c22f); RS_REPLAY is in both arms now
    s = must(s, '"c19_only_rs_replay_in_libllama": b"LLAMA_RS_REPLAY" in b}',
             '"c19_only_rs_replay_in_libllama": b"LLAMA_DTREE_DEVICE_ACCEPT" in (a["bdir"] / "bin/libllama-common.so").read_bytes()}')
    # derived "library differs" proof (template rule): the libraries the candidate's commits touch, not libllama.so
    s = must(s, '    r["libllama_differs"] = r[REF]["libllama_sha256"] != r[CAND]["libllama_sha256"]\n',
             '    r["libllama_differs"] = r[REF]["libllama_sha256"] != r[CAND]["libllama_sha256"]\n'
             '    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n'
             '    import fold_row_guard\n'
             '    r["libs_differ"] = fold_row_guard.libs_differ("%s", ARMS[REF]["sha"], ARMS[CAND]["sha"], str(ARMS[REF]["bdir"] / "bin"), str(ARMS[CAND]["bdir"] / "bin"))\n' % LLAMA_REPO)
    s = must(s, 'r["ok"] = bool(r["libllama_differs"] and', 'r["ok"] = bool(r["libs_differ"]["ok"] and')
    open(p, 'w').write(s)


def fix_qdec(dst):
    p = dst + '/cfg.json'
    c = json.load(open(p))
    c['iq3xxs_fix_sha'] = 'eab0af8f3f9d771e2ce424f08e5ae928a68a325d'   # C19's own cherry-pick of 17d092de0
    c['configure_template_sha256'] = sh(dst + '/' + c['configure_template'])   # relabelled template
    json.dump(c, open(p, 'w'), indent=1)
    p = dst + '/job.py'
    s = open(p).read()
    # C19 gate clause: IQ3_XXS CPU mul_mat must judge pass with 0 mismatches (the 17d092de0 fix is in C19); other types are reported
    s = must(s, "    return {'complete': True, 'verdict': v, 'failing_legs':",
             "    iq3 = [x for x in verdicts if x['type'] == 'IQ3_XXS' and x['leg'] == 'mul_mat:CPU']\n"
             "    c19_gate = 'PASS' if (iq3 and all(x['verdict'] == 'pass' and (x.get('mismatches') or 0) == 0 for x in iq3) and anc) else 'FAIL'\n"
             "    return {'complete': True, 'verdict': v, 'c19_iq3xxs_gate': c19_gate, 'iq3xxs_mul_mat_cpu': iq3, 'failing_legs':")
    open(p, 'w').write(s)


def seal(dst):
    if os.path.exists(dst + '/shas.json'):
        new = {}
        for k in json.load(open(dst + '/shas.json')):
            if 'libllama.so.0.0.' in k and not os.path.exists(k):
                lib = [f for f in os.listdir(os.path.dirname(k)) if f.startswith('libllama.so.0.0.')]
                assert len(lib) == 1, lib
                k = os.path.dirname(k) + '/' + lib[0]
            new[k] = sh(k)
        json.dump(new, open(dst + '/shas.json', 'w'), indent=1)
    lines = [ln for ln in open(dst + '/SOURCE.sha256').read().split('\n') if ln.strip()]
    files = [ln.split(None, 1)[1] for ln in lines]
    files = [f for f in files if f != 'spec.json']   # sealed without spec.json
    if os.path.exists(dst + '/fold_row_guard.py') and 'fold_row_guard.py' not in files:
        files.append('fold_row_guard.py')
    if os.path.isdir(dst + '/inc'):
        files = [f for f in files if not f.startswith('inc/')]
        for root, _, fs in os.walk(dst + '/inc'):
            files += sorted(os.path.relpath(os.path.join(root, f), dst) for f in fs)
    open(dst + '/SOURCE.sha256', 'w').write(''.join(f'{sh(os.path.join(dst, f))}  {f}\n' for f in files))


if __name__ == '__main__':
    lib = [f for f in os.listdir(f'/mnt/raid0/llm/kernels/builds/{G19}/bin') if f.startswith('libllama.so.0.0.')]
    assert len(lib) == 1, lib
    LL19 = lib[0]
    phase = sys.argv[1]
    for old, new in ROWS.items():
        dst = f'{T}/{new}'
        if phase == 'clone':
            clone(old, new)
            {'gpu': fix_gpu, 'a3b': fix_a3b, 'cpu': fix_cpu, 'qdec': fix_qdec}[new.split('-')[2]](dst)
            fold_row_guard.install_guard(dst, GUARD)
        else:
            seal(dst)
            # 2026-11-23 failure audit: lint the sealed row (SHA-CWD, SEALED-SPEC, STALE-OUT, SERVER-NO-TRAP, ...)
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'coordination', 'rowflow'))
            import ak_row_lint
            res = ak_row_lint.lint_dir(dst)
            for lvl, code, msg in res:
                print(f'{lvl} {code} {dst}: {msg}')
            if any(r[0] == 'FAIL' for r in res):
                sys.exit(f'seal: {dst} fails ak_row_lint; fix before publishing')
        print(phase, dst)
