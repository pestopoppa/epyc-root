#!/usr/bin/env python3
"""qwentts correctness leg: greedy fixed-seed synthesis of the 10 fixed texts.
usage: corr_qwentts.py <label> <bindir> <threads> <cpus> <mode> [KEY=VAL ...]
  mode shim  : threads set through the CS-45 nprocs shim (production has no thread flag)
  mode flag  : threads set with --threads (experimental)
Writes corr/<label>/<id>.{wav,log,dump/} and corr/<label>/results.jsonl (one row per text).
Every PID started is appended to pids_started.txt.
"""
import hashlib, json, os, subprocess, sys, time, pathlib, shutil

T = pathlib.Path('/mnt/raid0/llm/tmp/qwentts_threadpool_20261020')
M = '/mnt/raid0/llm/models/Qwen3-TTS-qwentts'
SHIM = '/mnt/raid0/llm/tmp/cs45/nprocs_shim.so'
MAXNEW = os.environ.get('CORR_MAXNEW', '40')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def pcm_sha(p):
    d = open(p, 'rb').read()
    i = d.find(b'data')
    return hashlib.sha256(d[i + 8:]).hexdigest()


def main():
    label, bindir, th, cpus, mode = sys.argv[1:6]
    extra = dict(a.split('=', 1) for a in sys.argv[6:])
    out = T / 'corr' / label
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    texts = json.load(open(T / 'texts/texts10.json'))
    res = open(out / 'results.jsonl', 'w')
    for r in texts:
        env = {k: v for k, v in os.environ.items() if k not in ('LD_PRELOAD',)}
        env.update(HIP_VISIBLE_DEVICES='-1', GGML_BACKEND='CPU', LD_LIBRARY_PATH=f'{bindir}:/opt/rocm/lib')
        argv = ['nice', '-n', '10', 'taskset', '-c', cpus, f'{bindir}/qwen-tts', '--model', f'{M}/qwen-talker-0.6b-base-Q8_0.gguf',
                '--codec', f'{M}/qwen-tokenizer-12hz-Q8_0.gguf', '--lang', 'English', '--seed', '1234', '--greedy',
                '--max-new', MAXNEW, '--ref-wav', r['ref'], '--dump', str(out / (r['id'] + '.dump')), '-o', str(out / (r['id'] + '.wav'))]
        if mode == 'shim':
            env.update(LD_PRELOAD=SHIM, SHIM_NPROCS=str(2 * int(th)))
        else:
            argv += ['--threads', th]
        env.update(extra)
        (out / (r['id'] + '.dump')).mkdir()
        t0 = time.time()
        with open(out / (r['id'] + '.log'), 'w') as lf:
            p = subprocess.Popen(argv, env=env, stdin=subprocess.PIPE, stdout=lf, stderr=subprocess.STDOUT)
            with open(T / 'pids_started.txt', 'a') as pf:
                pf.write(f'{p.pid} corr {label} {r["id"]}\n')
            p.communicate((r['text'] + '\n').encode())
        dt = time.time() - t0
        dump = out / (r['id'] + '.dump')
        codes = dump / 'codes-full.f32'
        cands = sorted(dump.glob('codes-full*'))
        row = dict(label=label, id=r['id'], rc=p.returncode, secs=round(dt, 1), threads=int(th), cpus=cpus, mode=mode, env=extra,
                   wav_sha=sha(out / (r['id'] + '.wav')) if (out / (r['id'] + '.wav')).exists() else None,
                   pcm_sha=pcm_sha(out / (r['id'] + '.wav')) if (out / (r['id'] + '.wav')).exists() else None,
                   codes_files=[c.name for c in cands], codes_sha=[sha(c) for c in cands],
                   dump_sha={f.name: sha(f) for f in sorted(dump.iterdir())})
        res.write(json.dumps(row) + '\n')
        res.flush()
        print(label, r['id'], row['rc'], row['secs'], row['pcm_sha'][:12] if row['pcm_sha'] else None, flush=True)


main()
