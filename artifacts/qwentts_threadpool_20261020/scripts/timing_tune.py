#!/usr/bin/env python3
"""Speech-kernel timing matrix: production vs experimental, qwen-tts and whisper-cli.

MUST be run inside an exclusive CPU bench claim (region-lock run ... -- python3 -I timing.py ...). The region's
physical cpus are passed with --cpus A-B (24 cpus). Every PID started (runs, spinners, neighbour) is appended to
pids_started.txt, spinners/neighbours are killed in a finally block and verified dead.

legs (b = first cpu of the region):
  quiet_1T            1 thread pinned to b
  quiet_8T_free       8 threads, affinity = whole region (24 cpus)
  quiet_8T_pinned     8 threads pinned to b..b+7
  cont_8T_1spin       8T pinned b..b+7, one busy-loop spinner on b
  cont_8T_8spin       8T pinned b..b+7, a spinner on each of the 8 cpus
  cont_1T_1spin       1T pinned to b, one spinner on b
  nb_8T               8T speech pinned b..b+7 + llama-bench -t 8 pinned to the SAME 8 cpus (real neighbour)
  nb_1T               1T speech pinned to b + llama-bench -t 1 pinned to b
"""
import argparse, json, os, re, signal, subprocess, sys, time, pathlib, datetime, threading

T = pathlib.Path('/mnt/raid0/llm/tmp/qwentts_threadpool_20261020')
PIDS = T / 'pids_started.txt'
M = '/mnt/raid0/llm/models/Qwen3-TTS-qwentts'
REF = '/mnt/raid0/llm/data/asr-eval/librispeech-test-clean-strat300/wav/3729-6852-0044.wav'
SHIM = '/mnt/raid0/llm/tmp/cs45/nprocs_shim.so'
TXT = 'Would you like me to book that table for Friday evening?'
PROD_Q = '/mnt/raid0/llm/qwentts.cpp/build'
EXP_Q = os.environ.get('EXP_Q', '/mnt/raid0/llm/worktrees/qwentts-threadpool-20261020/build')
PROD_W = '/mnt/raid0/llm/whisper.cpp/build/bin'
EXP_W = os.environ.get('EXP_W', '/mnt/raid0/llm/worktrees/whisper-threadpool-20261020/build/bin')
WMODEL = '/mnt/raid0/llm/models/whisper-ggml/ggml-large-v3-turbo.bin'
WCLIP = '/mnt/raid0/llm/tmp/cs45/run1/rec16/rec-u-0025.wav'
NBBIN = '/mnt/raid0/llm/kernels/production/cpu'
NBMODEL = '/mnt/raid0/llm/models/Qwen3-1.7B-Q8_0.gguf'

# variant -> (kind, env)
QVAR = {
    'prod':      ('shim', {}),
    'exp_ctl':   ('flag', {'QT_THREADPOOL': '0', 'GGML_CPU_BARRIER': 'spin'}),
    'exp_pool':  ('flag', {'GGML_CPU_BARRIER': 'spin'}),
    'exp_yield': ('flag', {'GGML_CPU_BARRIER': 'yield'}),
    'exp_futex': ('flag', {'GGML_CPU_BARRIER': 'futex'}),
    'exp_futexfix': ('flag', {'GGML_CPU_BARRIER': 'futex', 'GGML_CPU_BARRIER_ADAPT': '0'}),
}
WVAR = {
    'prod':      ('prod', {}),
    'exp_ctl':   ('exp', {'WHISPER_THREADPOOL': '0', 'GGML_CPU_BARRIER': 'spin'}),
    'exp_pool':  ('exp', {'GGML_CPU_BARRIER': 'spin'}),
    'exp_yield': ('exp', {'GGML_CPU_BARRIER': 'yield'}),
    'exp_futex': ('exp', {'GGML_CPU_BARRIER': 'futex'}),
}

ap = argparse.ArgumentParser()
ap.add_argument('--cpus', required=True, help='region phys cpus, e.g. 24-47')
ap.add_argument('--deadline', required=True, help='ISO UTC time after which no new run starts')
ap.add_argument('--out', required=True)
ap.add_argument('--suite', required=True, choices=['qts', 'whisper'])
ap.add_argument('--variants', default='prod,exp_ctl,exp_pool,exp_yield,exp_futex')
ap.add_argument('--legs', default='quiet_1T,quiet_8T_free,quiet_8T_pinned,cont_1T_1spin,cont_8T_1spin,cont_8T_8spin,nb_1T,nb_8T')
ap.add_argument('--reps', type=int, default=5)
ap.add_argument('--heavy-reps', type=int, default=3, help='reps for cont_8T_8spin')
ap.add_argument('--timeout', type=int, default=900)
ap.add_argument('--aa', action='store_true', help='also repeat the prod quiet legs as a second block (A/A)')
args = ap.parse_args()

lo, hi = [int(x) for x in args.cpus.split('-')]
B = lo
deadline = datetime.datetime.fromisoformat(args.deadline.replace('Z', '+00:00')).timestamp()
OUT = pathlib.Path(args.out)
OUT.mkdir(parents=True, exist_ok=True)
RES = open(OUT / f'results_{args.suite}.jsonl', 'a')  # tune copy: separate OUT dir
LOGS = OUT / 'logs'
LOGS.mkdir(exist_ok=True)
SPIN = []


def note_pid(pid, what):
    with open(PIDS, 'a') as f:
        f.write(f'{pid} timing {what}\n')


def cpurange(a, n):
    return f'{a}-{a + n - 1}' if n > 1 else str(a)


def start_spinners(cpus):
    for c in cpus:
        p = subprocess.Popen(['taskset', '-c', str(c), 'bash', '-c', 'while :; do :; done'])
        SPIN.append(p)
        note_pid(p.pid, f'spinner cpu{c}')


def stop_spinners():
    for p in SPIN:
        if p.poll() is None:
            p.terminate()
    time.sleep(0.5)
    for p in SPIN:
        if p.poll() is None:
            p.kill()
    for p in SPIN:
        try:
            p.wait(timeout=5)
        except Exception:
            pass
    dead = all(p.poll() is not None for p in SPIN)
    SPIN.clear()
    return dead


NB = {}


def start_neighbour(cpus, threads, reps=400):
    """llama-bench tg32 on `cpus`; stderr progress lines are timestamped on arrival."""
    env = {k: v for k, v in os.environ.items() if k not in ('LD_PRELOAD', 'LD_LIBRARY_PATH')}
    env.update(LD_LIBRARY_PATH=NBBIN, HIP_VISIBLE_DEVICES='-1')
    argv = ['taskset', '-c', cpus, f'{NBBIN}/llama-bench', '-m', NBMODEL, '-p', '0', '-n', '32', '-t', str(threads), '-r', str(reps),
            '--progress', '-o', 'jsonl', '-ngl', '0']
    p = subprocess.Popen(argv, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    note_pid(p.pid, f'neighbour llama-bench {cpus} t{threads}')
    stamps = []

    def rd():
        for line in p.stderr:
            m = re.search(r'generation run (\d+)/(\d+)', line)
            if m or 'warmup' in line:
                stamps.append((time.time(), line.strip()))
    th = threading.Thread(target=rd, daemon=True)
    th.start()
    NB.update(p=p, stamps=stamps, th=th)
    return p


def stop_neighbour():
    p = NB.get('p')
    if not p:
        return None
    if p.poll() is None:
        p.terminate()
        try:
            p.wait(timeout=10)
        except Exception:
            p.kill()
            p.wait(timeout=10)
    out = None
    try:
        out = p.stdout.read()
    except Exception:
        pass
    stamps = NB.get('stamps', [])
    NB.clear()
    return stamps, out, p.poll() is not None


def now():
    return time.time()


def run_cmd(argv, env, timeout, logname):
    t0 = now()
    with open(LOGS / logname, 'w') as lf:
        p = subprocess.Popen(argv, env=env, stdin=subprocess.PIPE, stdout=lf, stderr=subprocess.STDOUT, text=True)
        note_pid(p.pid, logname)
        try:
            p.communicate(TXT + '\n', timeout=timeout)
            to = False
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
            to = True
    return p.returncode, now() - t0, t0, to


def qts_run(var, threads, cpuset, logname):
    parts = var.split('@')
    base = parts[0]
    kind, vexec = QVAR[base]
    vexec = dict(vexec)
    if len(parts) > 1 and parts[1]:
        vexec['GGML_CPU_BARRIER_SPIN'] = parts[1]
    if len(parts) > 2 and parts[2]:
        vexec['GGML_CPU_BARRIER_SPIN_LO'] = parts[2]
    bindir = PROD_Q if var == 'prod' else EXP_Q
    env = {k: v for k, v in os.environ.items() if k not in ('LD_PRELOAD', 'LD_LIBRARY_PATH')}
    env.update(HIP_VISIBLE_DEVICES='-1', GGML_BACKEND='CPU', LD_LIBRARY_PATH=f'{bindir}:/opt/rocm/lib')
    argv = ['taskset', '-c', cpuset, f'{bindir}/qwen-tts', '--model', f'{M}/qwen-talker-0.6b-base-Q8_0.gguf', '--codec',
            f'{M}/qwen-tokenizer-12hz-Q8_0.gguf', '--lang', 'English', '--seed', '1234', '--greedy', '--max-new', '24', '--ref-wav', REF,
            '-o', str(OUT / 'out.wav')]
    if kind == 'shim':
        env.update(LD_PRELOAD=SHIM, SHIM_NPROCS=str(2 * threads))
    else:
        argv += ['--threads', str(threads)]
        env.update(vexec)
    rc, dt, t0, to = run_cmd(argv, env, args.timeout, logname)
    s = open(LOGS / logname).read()
    d = dict(rc=rc, wall_s=round(dt, 2), t0=t0, t1=t0 + dt, timeout=to)
    m = re.search(r'Total ([\d.]+) ms \((\d+) frames, ([\d.]+) ms/frame AR', s)
    if m:
        d.update(frames=int(m.group(2)), total_ms_frame=float(m.group(3)))
    m = re.search(r'TalkerDecode ([\d.]+) ms \((\d+) frames, ([\d.]+) ms/frame\)', s)
    if m:
        d['talker_ms_frame'] = float(m.group(3))
    m = re.search(r'CodePredictor ([\d.]+) ms \(([\d.]+) ms/frame\)', s)
    if m:
        d['predictor_ms_frame'] = float(m.group(2))
    m = re.search(r'CPU threads: (\d+)', s)
    d['log_threads'] = int(m.group(1)) if m else None
    d['pool_logged'] = 'CPU threadpool: persistent' in s
    return d


def whisper_run(var, threads, cpuset, logname):
    kindw, vexec = WVAR[var]
    bindir = PROD_W if var == 'prod' else EXP_W
    env = {k: v for k, v in os.environ.items() if k not in ('LD_PRELOAD', 'LD_LIBRARY_PATH')}
    env.update(HIP_VISIBLE_DEVICES='-1', LD_LIBRARY_PATH=f'{bindir}:/opt/rocm/lib')
    env.update(vexec)
    argv = ['taskset', '-c', cpuset, f'{bindir}/whisper-cli', '-m', WMODEL, '-f', WCLIP, '-t', str(threads), '-ng', '-l', 'en', '-nf', '-nt']
    rc, dt, t0, to = run_cmd(argv, env, args.timeout, logname)
    s = open(LOGS / logname).read()
    d = dict(rc=rc, wall_s=round(dt, 2), t0=t0, t1=t0 + dt, timeout=to)
    for key, rx in (('total_ms', r'total time =\s+([\d.]+) ms'), ('encode_ms', r'encode time =\s+([\d.]+) ms'),
                    ('decode_ms', r'decode time =\s+([\d.]+) ms'), ('batchd_ms', r'batchd time =\s+([\d.]+) ms'),
                    ('mel_ms', r'mel time =\s+([\d.]+) ms')):
        m = re.search(rx, s)
        if m:
            d[key] = float(m.group(1))
    return d


def leg_setup(leg):
    """returns (threads, speech_cpuset, spinner_cpus, nb(cpus,threads)|None)"""
    p8 = cpurange(B, 8)
    if leg == 'quiet_1T':
        return 1, str(B), [], None
    if leg == 'quiet_8T_free':
        return 8, f'{lo}-{hi}', [], None
    if leg == 'quiet_8T_pinned':
        return 8, p8, [], None
    if leg == 'cont_1T_1spin':
        return 1, str(B), [B], None
    if leg == 'cont_8T_1spin':
        return 8, p8, [B], None
    if leg == 'cont_8T_8spin':
        return 8, p8, list(range(B, B + 8)), None
    if leg == 'nb_1T':
        return 1, str(B), [], (str(B), 1)
    if leg == 'nb_8T':
        return 8, p8, [], (p8, 8)
    raise SystemExit('bad leg ' + leg)


def nb_window_stats(stamps, out, t0, t1):
    """per-rep t/s of the neighbour reps fully inside [t0,t1], from the arrival stamps of 'generation run k/N' lines."""
    try:
        row = json.loads(out.strip().splitlines()[-1])
        ts = row.get('samples_ts') or []
    except Exception:
        ts = []
    runs = [(t, l) for t, l in stamps if 'generation run' in l]
    warm = [t for t, l in stamps if 'warmup' in l]
    # run k completes when line k+1 (or the end) arrives; start of run 1 = arrival of 'generation run 1/N'
    inside = []
    for k in range(len(runs) - 1):
        a, b = runs[k][0], runs[k + 1][0]
        if a >= t0 and b <= t1 and k < len(ts):
            inside.append(ts[k])
    return inside


def do_leg(suite, var, leg, reps, block='main'):
    threads, cpuset, spin_cpus, nb = leg_setup(leg)
    runner = qts_run if suite == 'qts' else whisper_run
    for r in range(1, reps + 1):
        if now() > deadline:
            print('DEADLINE reached; stopping before', var, leg, r, flush=True)
            return False
        la = os.getloadavg()[0]
        try:
            if spin_cpus:
                start_spinners(spin_cpus)
            if nb:
                start_neighbour(nb[0], nb[1])
                time.sleep(6)  # warmup + first reps of the neighbour before speech starts
            d = runner(var, threads, cpuset, f'{suite}_{var}_{leg}_r{r}.log')
        finally:
            nbinfo = stop_neighbour() if nb else None
            spun_dead = stop_spinners() if spin_cpus else True
        row = dict(suite=suite, variant=var, leg=leg, block=block, rep=r, threads=threads, cpuset=cpuset, spinner_cpus=spin_cpus, load1_before=la,
                   region=args.cpus, spinners_dead=spun_dead, env_variant=(QVAR if suite == 'qts' else WVAR)[var.partition('@')[0]][1], **d)
        if nbinfo:
            stamps, out, dead = nbinfo
            row['nb_ts_inside_window'] = nb_window_stats(stamps, out, d['t0'], d['t1'])
            row['nb_dead'] = dead
        RES.write(json.dumps(row) + '\n')
        RES.flush()
        k = row.get('total_ms_frame') or row.get('total_ms')
        print(suite, var, leg, r, k, 'TIMEOUT' if d['timeout'] else '', flush=True)
    return True


def nb_alone(reps=1):
    """neighbour alone on the same cpus (baseline for the neighbour throughput loss)."""
    for leg in ('nb_1T', 'nb_8T'):
        threads, cpuset, spin_cpus, nb = leg_setup(leg)
        start_neighbour(nb[0], nb[1], reps=20)
        p = NB['p']
        try:
            p.wait(timeout=600)
        except Exception:
            pass
        stamps, out, dead = stop_neighbour()
        try:
            row = json.loads(out.strip().splitlines()[-1])
            RES.write(json.dumps(dict(suite=args.suite, variant='nb_alone', leg=leg, samples_ts=row.get('samples_ts'), avg_ts=row.get('avg_ts'),
                                      threads=nb[1], cpuset=nb[0], nb_dead=dead)) + '\n')
            RES.flush()
            print('nb_alone', leg, row.get('avg_ts'), flush=True)
        except Exception as e:
            print('nb_alone parse fail', e, flush=True)


def main():
    RES.write(json.dumps(dict(config_echo=vars(args), host_load1=os.getloadavg()[0], start=time.time(),
                              binaries={k: v for k, v in dict(prod_q=PROD_Q, exp_q=EXP_Q, prod_w=PROD_W, exp_w=EXP_W).items()})) + '\n')
    try:
        variants = args.variants.split(',')
        legs = args.legs.split(',')
        suite = args.suite
        order = [l for l in legs if l not in ('cont_8T_8spin', 'nb_1T', 'nb_8T')]
        for l in order:
            for v in variants:
                if not do_leg(suite, v, l, args.reps):
                    return
        if args.aa:
            for l in [x for x in order if x.startswith('quiet')]:
                if not do_leg(suite, 'prod', l, args.reps, block='AA'):
                    return
        if any(l.startswith('nb_') for l in legs):
            nb_alone()
            for l in [x for x in legs if x.startswith('nb_')]:
                for v in variants:
                    if not do_leg(suite, v, l, args.reps):
                        return
        if 'cont_8T_8spin' in legs:
            for v in variants:
                if not do_leg(suite, v, 'cont_8T_8spin', args.heavy_reps):
                    return
    finally:
        stop_neighbour()
        stop_spinners()
        RES.write(json.dumps(dict(end=time.time())) + '\n')
        RES.flush()


main()
