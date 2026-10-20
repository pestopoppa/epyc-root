#!/usr/bin/env python3
"""whisper correctness leg: whisper-cli on the 10 fixed CS-45 clips, CPU only, deterministic flags.
usage: corr_whisper.py <label> <bindir> <threads> <cpus> [KEY=VAL ...]
Writes corr_w/<label>/<clip>.json (+ .log) and results.jsonl with sha256 of the canonical (text, token ids, token p,
offsets) tuple and of the raw JSON. Every PID is appended to pids_started.txt.
"""
import hashlib, json, os, subprocess, sys, time, pathlib, shutil

T = pathlib.Path('/mnt/raid0/llm/tmp/qwentts_threadpool_20261020')
MODEL = '/mnt/raid0/llm/models/whisper-ggml/ggml-large-v3-turbo.bin'


def main():
    label, bindir, th, cpus = sys.argv[1:5]
    extra = dict(a.split('=', 1) for a in sys.argv[5:])
    out = T / 'corr_w' / label
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    clips = json.load(open(T / 'texts/clips10.json'))
    res = open(out / 'results.jsonl', 'w')
    for c in clips:
        name = pathlib.Path(c).stem
        env = {k: v for k, v in os.environ.items() if k not in ('LD_PRELOAD', 'LD_LIBRARY_PATH')}
        env.update(HIP_VISIBLE_DEVICES='-1', LD_LIBRARY_PATH=f'{bindir}:/opt/rocm/lib')
        env.update(extra)
        argv = ['nice', '-n', '10', 'taskset', '-c', cpus, f'{bindir}/whisper-cli', '-m', MODEL, '-f', c, '-t', th, '-ng', '-l', 'en',
                '-ojf', '-of', str(out / name), '-np', '-nf']
        t0 = time.time()
        with open(out / (name + '.log'), 'w') as lf:
            p = subprocess.Popen(argv, env=env, stdout=lf, stderr=subprocess.STDOUT)
            with open(T / 'pids_started.txt', 'a') as pf:
                pf.write(f'{p.pid} corr_w {label} {name}\n')
            p.wait()
        dt = time.time() - t0
        jp = out / (name + '.json')
        canon = None
        raw = None
        text = None
        if jp.exists():
            raw = hashlib.sha256(open(jp, 'rb').read()).hexdigest()
            j = json.load(open(jp))
            segs = []
            for s in j.get('transcription', []):
                segs.append([s.get('text'), s.get('offsets'), [[t.get('id'), t.get('text'), t.get('p'), t.get('offsets')] for t in s.get('tokens', [])]])
            canon = hashlib.sha256(json.dumps(segs, sort_keys=True).encode()).hexdigest()
            text = ' '.join(s[0].strip() for s in segs)
            ntok = sum(len(s[2]) for s in segs)
        # timing line from the log (encode/decode ms)
        row = dict(label=label, clip=name, rc=p.returncode, secs=round(dt, 2), threads=int(th), cpus=cpus, env=extra,
                   canon_sha=canon, raw_json_sha=raw, n_tokens=ntok if canon else None, text=text)
        res.write(json.dumps(row) + '\n')
        res.flush()
        print(label, name, row['rc'], row['secs'], (canon or '')[:12], flush=True)


main()
