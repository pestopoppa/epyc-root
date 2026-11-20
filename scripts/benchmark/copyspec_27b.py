#!/usr/bin/env python3
"""Prospective COPYSPEC GPU requests; only execute under the rowflow launcher."""
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request

ARMS = ('P', 'NM8', 'NO', 'P2')
STOP = False


def digest(p):
    return hashlib.file_digest(open(p, 'rb'), 'sha256').hexdigest()


def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(value, sort_keys=True))
    tmp.replace(p)


def counters(response, arm):
    tm = response['timings']
    dn, an = tm.get('draft_n', 0), tm.get('draft_n_accepted', 0)
    if type(dn) is not int or type(an) is not int or not 0 <= an <= dn:
        raise ValueError('malformed draft counters')
    if ('draft_n' in tm) != ('draft_n_accepted' in tm):
        raise ValueError('partial draft counters')
    if arm in ('P', 'NM8', 'P2') and dn == 0:
        raise ValueError('DFlash arm did not draft')
    n, ms = tm['predicted_n'], tm['predicted_ms']
    if type(n) is not int or n <= 0 or not isinstance(ms, (int, float)) or ms <= 0:
        raise ValueError('invalid timing')
    return dict(predicted_n=n, predicted_ms=ms, draft_n=dn, accepted_n=an,
                acceptance=an / dn if dn else None, tps=n * 1000 / ms)


def summarize(records, count):
    keys = {(r['arm'], r['id']) for r in records}
    if len(keys) != len(records) or len(keys) != len(ARMS) * count:
        raise ValueError('missing or duplicate request')
    result = {}
    for arm in ARMS:
        rs = [r for r in records if r['arm'] == arm]
        if len(rs) != count:
            raise ValueError('arm incomplete')
        ms = sum(r['predicted_ms'] for r in rs)
        dn = sum(r['draft_n'] for r in rs)
        an = sum(r['accepted_n'] for r in rs)
        result[arm] = dict(tps=sum(r['predicted_n'] for r in rs) * 1000 / ms,
                           draft_n=dn, accepted_n=an, acceptance=an / dn if dn else None)
    base = {r['id']: r['content_sha256'] for r in records if r['arm'] == 'P'}
    for arm in ARMS:
        result[arm]['identity_vs_P'] = sum(r['content_sha256'] == base[r['id']] for r in records if r['arm'] == arm)
        result[arm]['ratio_vs_P'] = result[arm]['tps'] / result['P']['tps']
    return result


def owns_port(pid, port):
    sockets = set()
    for fd in Path(f'/proc/{pid}/fd').iterdir():
        try:
            sockets.add(os.readlink(fd))
        except OSError:
            pass
    for line in Path(f'/proc/{pid}/net/tcp').read_text().splitlines()[1:]:
        fields = line.split()
        if fields[3] == '0A' and int(fields[1].split(':')[1], 16) == port:
            if f'socket:[{fields[9]}]' in sockets:
                return True
    return False


def main(root):
    global STOP
    def sig(*_):
        global STOP
        STOP = True
    signal.signal(signal.SIGTERM, sig)
    signal.signal(signal.SIGINT, sig)
    d = Path(root)
    cfg = json.loads((d / 'config.json').read_text())
    smoke = os.environ.get('FILLER_DRYRUN') == '1' or os.environ.get('FILLER_SMOKE') == '1'
    if not os.environ.get('FILLER_DEADLINE'):
        raise ValueError('rowflow grant required')
    deadline = float(os.environ['FILLER_DEADLINE'])
    out = d / ('smoke' if smoke else 'out')
    out.mkdir(exist_ok=True)
    seal = digest(d / 'config.json')
    for p, expected in cfg['files'].items():
        if digest(p) != expected:
            raise ValueError('input changed: ' + p)
    for p, expected in cfg['model_stats'].items():
        s = Path(p).stat()
        if {k: getattr(s, k) for k in expected} != expected:
            raise ValueError('prepared model changed')
    prompts = [json.loads(l) for l in (d / 'prompts.jsonl').read_text().splitlines()]
    if smoke:
        prompts = prompts[:1]
    port = cfg['port']
    bindir = cfg['bin']
    env = dict(PATH='/usr/bin:/bin', HOME=os.environ.get('HOME', '/tmp'),
               LD_LIBRARY_PATH=bindir + ':/opt/rocm/lib', ROCR_VISIBLE_DEVICES='0',
               HSA_OVERRIDE_CPU_AFFINITY_DEBUG='0', GGML_CUDA_AK_H15='0',
               FILLER_ID=os.environ.get('FILLER_ID', 'df2-copyspec-27b-gpu-20261120'))
    proof = subprocess.run(['bash', cfg['linkage'], bindir + '/llama-server'], env=env, capture_output=True, text=True)
    save(out / 'linkage.json', dict(rc=proof.returncode, text=proof.stdout + proof.stderr))
    if proof.returncode:
        raise ValueError('linkage refused')
    def http(path, body=None):
        req = urllib.request.Request(f'http://127.0.0.1:{port}' + path,
            data=None if body is None else json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=max(1, min(180, deadline - time.time() - 20))) as f:
            return json.load(f)
    def stopped():
        return STOP or Path(os.environ['FILLER_STOPFILE']).exists() or time.time() + 60 >= deadline
    for arm in (ARMS[:2] if smoke else ARMS):
        if stopped():
            return 75
        pending = []
        for q in prompts:
            checkpoint = out / arm / (q['id'] + '.json')
            if checkpoint.exists() and not smoke:
                if json.loads(checkpoint.read_text())['config_sha256'] != seal:
                    raise ValueError('checkpoint configuration drift')
            else:
                pending.append(q)
        if not pending:
            continue
        extra = ['--spec-type', 'ngram-mod' if arm == 'NO' else 'ngram-mod,draft-dflash' if arm == 'NM8' else 'draft-dflash']
        if arm != 'NO':
            extra += ['-md', cfg['draft'], '-ngld', '99', '--spec-draft-n-max', '8']
        if arm in ('NM8', 'NO'):
            extra += ['--spec-ngram-mod-n-match', '12', '--spec-ngram-mod-n-min', '4', '--spec-ngram-mod-n-max', '8']
        cpus = ','.join(map(str, sorted(os.sched_getaffinity(0))[:4])) if smoke else '184-191'
        argv = ['numactl', '--membind=3', '--', 'taskset', '-c', cpus, bindir + '/llama-server',
                '-m', cfg['model'], '-ngl', '99', '--device', 'ROCm0', '-np', '1', '-c', '32768',
                '-t', '4' if smoke else '8', '-tb', '4' if smoke else '8', '-b', '2048', '-ub', '2048',
                '-ctk', 'f16', '-ctv', 'f16', '-fa', 'on', '--host', '127.0.0.1', '--port', str(port)] + extra
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('127.0.0.1', port))
        armout = out / arm
        armout.mkdir(exist_ok=True)
        save(armout / 'argv.json', dict(argv=argv, env=env, config_sha256=seal))
        with (armout / 'server.log').open('ab') as log:
            proc = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT)
            if os.environ.get('FILLER_PIDFILE'):
                with open(os.environ['FILLER_PIDFILE'], 'a') as pf:
                    pf.write(str(proc.pid) + '\n')
            try:
                ready = False
                for _ in range(180):
                    if proc.poll() is not None or stopped():
                        break
                    try:
                        ready = http('/health').get('status') == 'ok'
                        if ready:
                            break
                    except (OSError, ValueError):
                        pass
                    time.sleep(1)
                if not ready:
                    if stopped():
                        return 75
                    raise ValueError('server not ready')
                if not owns_port(proc.pid, port):
                    raise ValueError('HTTP port is not owned by child')
                maps = Path(f'/proc/{proc.pid}/maps').read_text()
                libs = {Path(l.split()[-1]).resolve() for l in maps.splitlines() if 'libggml' in l or 'libllama' in l}
                if not libs or not any('libggml-hip' in p.name for p in libs) or any(p.parent != Path(bindir).resolve() for p in libs):
                    raise ValueError('foreign or missing HIP libraries')
                for q in pending:
                    if stopped():
                        return 75
                    samples = []
                    event = threading.Event()
                    def sample():
                        while not event.is_set():
                            def rd(p):
                                try:
                                    return int(p.read_text().strip())
                                except (OSError, ValueError):
                                    return -1
                            kd = Path(f'/sys/class/kfd/kfd/proc/{proc.pid}')
                            samples.append(dict(t=time.time(), pid=proc.pid, kfd=kd.exists(),
                                own_vram=sum(max(0, rd(p)) for p in kd.glob('vram_*')),
                                vram=rd(Path(cfg['device']) / 'mem_info_vram_used'),
                                busy=rd(Path(cfg['device']) / 'gpu_busy_percent')))
                            event.wait(.25)
                    thread = threading.Thread(target=sample, daemon=True)
                    thread.start()
                    try:
                        response = http('/v1/chat/completions', dict(messages=[dict(role='user', content=q['prompt'])],
                            max_tokens=128 if smoke else 450 if q['suite'] == 'prose' else 400,
                            temperature=0, top_k=1, seed=1, cache_prompt=False,
                            chat_template_kwargs=dict(enable_thinking=False)))
                    finally:
                        event.set()
                        thread.join(5)
                    metrics = counters(response, arm)
                    if sum(s['kfd'] and s['own_vram'] > 0 and s['vram'] > 0 and s['busy'] >= 0 for s in samples) < 2:
                        raise ValueError('missing during-request GPU proof')
                    content = response['choices'][0]['message'].get('content') or ''
                    record = dict(arm=arm, id=q['id'], suite=q['suite'], config_sha256=seal,
                        content_sha256=hashlib.sha256(content.encode()).hexdigest(), response=response,
                        samples=samples, server_pid=proc.pid, **metrics)
                    save(armout / (q['id'] + '.json'), record)
                    with (out / 'results.jsonl').open('a') as f:
                        f.write(json.dumps(record) + '\n')
                        f.flush()
                        os.fsync(f.fileno())
                    if smoke:
                        break  # one real request from each smoke arm
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(30)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(30)
                assert proc.poll() is not None
    if smoke:
        return 75
    records = [json.loads((out / a / (q['id'] + '.json')).read_text()) for a in ARMS for q in prompts]
    save(out / 'RESULT.json', dict(verdict='COMPLETE_DESCRIPTIVE', arms=summarize(records, len(prompts)),
        config_sha256=seal, prompt_count=len(prompts),
        limits='One sweep; no efficacy or deployment verdict. Rendered-token repetition fraction unmeasured.'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
