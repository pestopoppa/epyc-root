#!/usr/bin/env python3
"""BUILDVERIFY-1: content-based build identity check (digest OBJECTS, never the linked .so).

  buildverify.py manifest <build_dir> [-o out.json]   sha256 of every *.o under build_dir
  buildverify.py compare A.json B.json                exit 0 iff identical object sets+digests
  buildverify.py symbol <lib.so> <STRING> [...]       exit 0 iff every STRING is present in the binary
  buildverify.py --selftest

The compiler is byte-reproducible on this host; the linker is not (one commit, four libggml-hip.so
digests), so object digests are the identity and a .so digest is never compared. A build path,
directory name or mtime does not identify a binary; use `symbol` to prove a fix-specific knob/string
is compiled in before reasoning from a null.
"""
import hashlib, json, os, sys, tempfile

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def manifest(root):
    objs = {}
    for d, _, fs in os.walk(root):
        for n in fs:
            if n.endswith('.o'):
                p = os.path.join(d, n)
                objs[os.path.relpath(p, root)] = sha(p)
    if not objs:
        raise SystemExit(f'no .o files under {root}: refusing an empty manifest (vacuous identity)')
    agg = hashlib.sha256(''.join(f'{k}={v}\n' for k, v in sorted(objs.items())).encode()).hexdigest()
    return {'n_objects': len(objs), 'aggregate': agg, 'objects': objs}

def compare(a, b):
    ao, bo = a['objects'], b['objects']
    only_a, only_b = sorted(set(ao) - set(bo)), sorted(set(bo) - set(ao))
    diff = sorted(k for k in set(ao) & set(bo) if ao[k] != bo[k])
    for tag, xs in (('only-in-A', only_a), ('only-in-B', only_b), ('differs', diff)):
        for x in xs:
            print(f'{tag}: {x}')
    ok = not (only_a or only_b or diff)
    print(f"{'IDENTICAL' if ok else 'DIFFERENT'}: A={a['n_objects']} B={b['n_objects']} objects")
    return ok

def symbol(lib, strs):
    data = open(lib, 'rb').read()
    ok = True
    for s in strs:
        hit = s.encode() in data
        print(f"{'PRESENT' if hit else 'ABSENT '}: {s}")
        ok &= hit
    return ok

def selftest():
    with tempfile.TemporaryDirectory() as t:
        for sub in ('a', 'b', 'c'):
            os.makedirs(f'{t}/{sub}')
        for sub, body in (('a', b'x'), ('b', b'x'), ('c', b'y')):
            open(f'{t}/{sub}/m.o', 'wb').write(body)
        ma, mb, mc = (manifest(f'{t}/{s}') for s in 'abc')
        assert compare(ma, mb) and not compare(ma, mc)
        open(f'{t}/l.so', 'wb').write(b'..GGML_KNOB..')
        assert symbol(f'{t}/l.so', ['GGML_KNOB']) and not symbol(f'{t}/l.so', ['NOPE'])
        os.makedirs(f'{t}/e')
        try:
            manifest(f'{t}/e'); raise AssertionError('empty manifest accepted')
        except SystemExit:
            pass
    print('selftest OK')
    return True

def main(a):
    if a[:1] == ['--selftest']:
        return 0 if selftest() else 1
    if a[:1] == ['manifest'] and len(a) >= 2:
        m = manifest(a[1])
        out = a[a.index('-o') + 1] if '-o' in a else None
        (open(out, 'w') if out else sys.stdout).write(json.dumps(m, indent=1) + '\n')
        return 0
    if a[:1] == ['compare'] and len(a) == 3:
        return 0 if compare(json.load(open(a[1])), json.load(open(a[2]))) else 1
    if a[:1] == ['symbol'] and len(a) >= 3:
        return 0 if symbol(a[1], a[2:]) else 1
    print(__doc__); return 2

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
