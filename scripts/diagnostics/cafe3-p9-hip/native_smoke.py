"""Bounded publisher-only inference; no P9 or performance verdict."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

import launch_context as context
import native_runner


def qualifying(sample, start, end, pid):
    return (sample['pid'] == pid and start <= sample['at'] <= end and
            sample['kfd_registered'] and sample['vram_bytes'] > 0 and
            sample['models_mapped'] and sample['libraries_mapped'])


def validate(record):
    samples = record['samples']
    context.require(record['child_reaped'] and record['tokens_predicted'] > 0 and
                    record['cutoff'] is None and len(samples) >= 2 and
                    len({s['at'] for s in samples}) >= 2 and
                    all(qualifying(s, record['request_start'], record['request_end'], record['pid'])
                        for s in samples), 'native smoke missing in-request residency/inference')


def request(url, payload=None, timeout=1):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def run(inventory, prepared, executable):
    context.require(os.environ.get('FILLER_DRYRUN') == '1' and
                    os.environ['FILLER_ID'] == inventory['row'], 'publisher smoke only')
    cpus = context.cpu_set(os.environ['FILLER_CPUS'])
    context.require(cpus <= os.sched_getaffinity(0), 'smoke CPU affinity')
    threads = min(int(os.environ['FILLER_THREADS']), len(cpus))
    context.require(threads > 0, 'smoke threads')
    receipt = context.bound_json(inventory['build'])
    expected = {str(Path(p).resolve()) for p in receipt['files']
                if Path(p).name.startswith(('libggml', 'libllama'))}
    models = {str(Path(m['path']).resolve()) for m in prepared['models'].values()}
    argv = [str(executable), '-m', prepared['models']['target']['path'],
            '--model-draft', prepared['models']['draft']['path'],
            '-t', str(threads), '-tb', str(threads), '-ngl', '999',
            '--gpu-layers-draft', '999', '-c', '4096', '-np', '1',
            '--host', '127.0.0.1', '--port', str(inventory['port']),
            '--spec-type', 'draft-dflash', '--spec-draft-n-max', '3', '-fa', 'off']
    deadline = min(time.time() + 240, int(os.environ['FILLER_DEADLINE']) - 5)
    stop = Path(os.environ['FILLER_STOPFILE'])
    work = Path(tempfile.mkdtemp(prefix='smoke-', dir=Path(__file__).parent))
    samples = []
    start = end = None
    future = None
    reply = None
    cutoff = None
    env = dict(os.environ, LD_LIBRARY_PATH=str(executable.parent),
               HIP_VISIBLE_DEVICES='0', ROCR_VISIBLE_DEVICES='0', OMP_NUM_THREADS=str(threads))
    url = 'http://127.0.0.1:' + str(inventory['port'])
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    with (work / 'server.log').open('x') as log:
        proc = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL)
        try:
            while proc.poll() is None:
                if stop.exists() or time.time() >= deadline:
                    cutoff = 'STOP/deadline'
                    break
                if future is None:
                    try:
                        request(url + '/health', timeout=.2)
                    except (OSError, urllib.error.URLError):
                        pass
                    else:
                        start = time.time()
                        future = pool.submit(request, url + '/completion',
                            dict(prompt='Count the integers from one to thirty two.', n_predict=32,
                                 temperature=0, seed=42, cache_prompt=False, ignore_eos=True),
                            max(.1, deadline - time.time()))
                else:
                    if future.done():
                        reply = future.result()
                        end = time.time()
                        break
                    try:
                        lines = Path(f'/proc/{proc.pid}/maps').read_text().splitlines()
                        paths = {str(Path(line.split()[-1]).resolve()) for line in lines
                                 if len(line.split()) >= 6 and line.split()[-1].startswith('/')}
                        libraries = {p for p in paths if Path(p).name.startswith(('libggml', 'libllama'))}
                        context.require(libraries <= expected, 'foreign smoke library')
                        sample = native_runner.residency(proc.pid)
                        sample.update(at=time.time(), libraries=sorted(libraries),
                                      libraries_mapped=libraries == expected, models_mapped=models <= paths)
                        if qualifying(sample, start, deadline, proc.pid):
                            samples.append(sample)
                    except FileNotFoundError:
                        pass
                try:
                    proc.wait(timeout=.05)
                except subprocess.TimeoutExpired:
                    pass
        finally:
            rc = native_runner.reap(proc)
            pool.shutdown(wait=True, cancel_futures=True)
    record = dict(pid=proc.pid, argv=argv, threads=threads, cpus=sorted(cpus),
                  request_start=start, request_end=end, samples=samples, cutoff=cutoff,
                  tokens_predicted=reply.get('tokens_predicted', 0) if reply else 0,
                  response=reply, child_reaped=proc.poll() is not None, rc=rc,
                  log=str(work / 'server.log'))
    (work / 'capture.json').write_text(json.dumps(record, indent=2) + '\n')
    validate(record)
    return record
