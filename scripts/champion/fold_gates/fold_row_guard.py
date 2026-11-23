#!/usr/bin/env python3
"""fold_row_guard.py — run guard + completion check + touched-library proof for champion fold-gate rows (template).

Three defects this closes (C19 fold, 2026-11-23):
  * A complete-check that accepts ANY terminal out/RESULT.json can be satisfied by output a previous run left behind.
    `run` moves an existing non-smoke RESULT.json to out/stale-<UTC>/ before the job starts, runs the job, then writes
    out/RUN.json {run_id, rc, result_sha256}. `check` passes only when RUN.json names a run id, rc 0, and the sha256 of
    the RESULT.json that is there now, with a terminal verdict. A RESULT not written under a guarded run never completes.
  * A "library differs" proof keyed on a FIXED library list fails when the candidate's commits do not touch that library
    (c19-fold-cpu-20261123: libllama.so byte-identical because C19 changes no src/ file). `touched-libs` derives the
    library set from `git diff --name-only REF..CAND` and `libs-differ` proves at least one of THOSE differs.

Usage (launch.sh / spec):
  --cmd "python3 -I fold_row_guard.py run --dir $D -- /usr/bin/python3 -I -B $D/job.py"
  --complete-cmd "python3 -I fold_row_guard.py check --dir $D"
  in job.py proofs: fold_row_guard.libs_differ(repo, ref_sha, cand_sha, ref_bin, cand_bin) -> dict with 'ok'
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, time

TERMINAL = ('PASS', 'FAIL', 'FUTILITY', 'INCONCLUSIVE', 'ATTRIBUTED', 'MIXED', 'UNATTRIBUTED', 'CLEAN', 'DEFECT')
SMOKE_ENV = ('FILLER_SMOKE', 'FILLER_DRYRUN')

# source path prefix -> library (or binary) in the store's bin/. First match wins; order is most specific first.
LIB_MAP = [
    ('ggml/src/ggml-cpu/', 'libggml-cpu.so'),
    ('ggml/src/ggml-cuda/', 'libggml-hip.so'),
    ('ggml/src/ggml-hip/', 'libggml-hip.so'),
    ('ggml/src/', 'libggml-base.so'),
    ('ggml/include/', 'libggml-base.so'),
    ('src/', 'libllama.so'),
    ('include/', 'libllama.so'),
    ('common/', 'libllama-common.so'),
    ('tools/server/', 'llama-server'),
    ('tools/perplexity/', 'llama-perplexity'),
    ('tests/test-backend-ops.cpp', 'test-backend-ops'),
]


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def now():
    return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())


def is_smoke(env=None):
    env = os.environ if env is None else env
    return any(env.get(k) == '1' for k in SMOKE_ENV)


def run_id(env=None):
    env = os.environ if env is None else env
    return env.get('FILLER_ID') or env.get('FILLER_GRANT_ID') or ('pid-%d-%s' % (os.getpid(), now()))


def move_stale(out):
    """Move a pre-existing out/RESULT.json (and RUN.json) aside. Returns the stale dir or None."""
    res = os.path.join(out, 'RESULT.json')
    if not os.path.exists(res):
        return None
    dst = os.path.join(out, 'stale-' + now())
    os.makedirs(dst, exist_ok=True)
    for n in ('RESULT.json', 'RUN.json'):
        p = os.path.join(out, n)
        if os.path.exists(p):
            shutil.move(p, os.path.join(dst, n))
    return dst


def cmd_run(a):
    out = os.path.join(a.dir, 'out')
    os.makedirs(out, exist_ok=True)
    if is_smoke():
        os.execv(a.cmd[0], a.cmd)   # smoke writes its own TERMINAL-smoke file; RESULT/RUN are untouched
    rid = run_id()
    stale = move_stale(out)
    run_p = os.path.join(out, 'RUN.json')
    p = subprocess.Popen(a.cmd)
    try:
        rc = p.wait()
    finally:
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(30)
            except subprocess.TimeoutExpired:
                p.kill(); p.wait()
    res = os.path.join(out, 'RESULT.json')
    rec = {'run_id': rid, 'rc': rc, 'at': now(), 'stale_moved_to': stale,
           'result_sha256': sha256(res) if os.path.exists(res) else None}
    tmp = run_p + '.tmp'
    json.dump(rec, open(tmp, 'w'), indent=1)
    os.replace(tmp, run_p)
    return rc


def check(d):
    """(ok, why). ok iff RUN.json binds the current RESULT.json, rc 0, a run id and a terminal verdict."""
    out = os.path.join(d, 'out')
    try:
        run = json.load(open(os.path.join(out, 'RUN.json')))
        res_p = os.path.join(out, 'RESULT.json')
        res = json.load(open(res_p))
    except (OSError, ValueError) as e:
        return False, 'missing/unreadable RUN.json or RESULT.json: %s' % e
    if not run.get('run_id'):
        return False, 'RUN.json has no run_id'
    if run.get('rc') != 0:
        return False, 'run rc %r' % run.get('rc')
    if run.get('result_sha256') != sha256(res_p):
        return False, 'RESULT.json was not written by the guarded run (sha mismatch)'
    complete = res.get('complete') is True or res.get('status') == 'complete'
    v = str(res.get('verdict') or '')
    if not complete or not v.startswith(TERMINAL):
        return False, 'RESULT not complete/terminal: %r' % v
    return True, 'ok run_id=%s verdict=%s' % (run['run_id'], v)


def touched_libs(repo, ref_sha, cand_sha):
    names = subprocess.check_output(['git', '-C', repo, 'diff', '--name-only', ref_sha + '..' + cand_sha], text=True).split()
    libs = {}
    for n in names:
        for pre, lib in LIB_MAP:
            if n.startswith(pre):
                libs.setdefault(lib, []).append(n)
                break
    return libs


def libs_differ(repo, ref_sha, cand_sha, ref_bin, cand_bin):
    """Proof: at least one library the candidate's commits touch differs between the two stores' bin/ dirs."""
    libs = touched_libs(repo, ref_sha, cand_sha)
    rep = {}
    for lib in sorted(libs):
        a, b = os.path.join(ref_bin, lib), os.path.join(cand_bin, lib)
        if os.path.exists(a) and os.path.exists(b):
            ha, hb = sha256(os.path.realpath(a)), sha256(os.path.realpath(b))
            rep[lib] = {'differs': ha != hb, 'ref_sha256': ha, 'cand_sha256': hb, 'n_files': len(libs[lib])}
        else:
            rep[lib] = {'differs': None, 'missing': [x for x in (a, b) if not os.path.exists(x)], 'n_files': len(libs[lib])}
    ok = any(v.get('differs') for v in rep.values())
    return {'ok': ok, 'touched': rep, 'rule': 'at least one library touched by ' + ref_sha[:9] + '..' + cand_sha[:9] + ' differs'}


def install_guard(row_dir, guard_src=None):
    """Template step: copy this module into a fold row and route launch.sh through it.
    --cmd "<job>"            -> --cmd "/usr/bin/python3 -I $D/fold_row_guard.py run --dir $D -- <job>"
    --complete-cmd "<check>" -> --complete-cmd "/usr/bin/python3 -I $D/fold_row_guard.py check --dir $D"
    Returns the files to add to SOURCE.sha256 (the caller seals; spec.json is never sealed)."""
    import re
    guard_src = guard_src or os.path.abspath(__file__)
    shutil.copy(guard_src, os.path.join(row_dir, 'fold_row_guard.py'))
    lp = os.path.join(row_dir, 'launch.sh')
    s = open(lp).read()
    if 'fold_row_guard.py' not in s:
        s, n1 = re.subn(r'--cmd "([^"]+)"', lambda m: '--cmd "/usr/bin/python3 -I $D/fold_row_guard.py run --dir $D -- ' + m.group(1) + '"', s, count=1)
        s, n2 = re.subn(r'--complete-cmd "[^"]+"', '--complete-cmd "/usr/bin/python3 -I $D/fold_row_guard.py check --dir $D"', s, count=1)
        if n1 != 1 or n2 != 1:
            raise SystemExit('install_guard: launch.sh has no single --cmd / --complete-cmd to wrap: ' + lp)
        if not re.search(r'^D=', s, re.M):
            raise SystemExit('install_guard: launch.sh does not define D= (the row dir): ' + lp)
        open(lp, 'w').write(s)
    return ['fold_row_guard.py', 'launch.sh']


def main(argv=None):
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd_name', required=True)
    r = sp.add_parser('run'); r.add_argument('--dir', required=True); r.add_argument('cmd', nargs=argparse.REMAINDER)
    c = sp.add_parser('check'); c.add_argument('--dir', required=True)
    t = sp.add_parser('libs-differ')
    for k in ('repo', 'ref', 'cand', 'ref-bin', 'cand-bin'):
        t.add_argument('--' + k, required=True)
    a = ap.parse_args(argv)
    if a.cmd_name == 'run':
        a.cmd = [x for x in a.cmd if x != '--'] if a.cmd and a.cmd[0] == '--' else a.cmd
        if not a.cmd:
            ap.error('run needs a command after --')
        return cmd_run(a)
    if a.cmd_name == 'check':
        ok, why = check(a.dir)
        print(why)
        return 0 if ok else 1
    print(json.dumps(libs_differ(a.repo, a.ref, a.cand, a.ref_bin, a.cand_bin), indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
