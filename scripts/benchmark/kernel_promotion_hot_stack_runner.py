#!/usr/bin/env python3
"""Run an admitted, isolated hot-stack functional smoke and seal its observations."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(Path(__file__).resolve().parent),
                str(ROOT / 'scripts/benchmark/jetlong_cpu'),
                str(ROOT / 'scripts/benchmark/m4_cpu_ownership')]

import affinity_guard
import kernel_promotion_evidence as evidence
import kernel_promotion_hot_stack as planner
import owned

FLAGS = planner.SCRATCH / 'compute-flags'
KFD = Path('/sys/class/kfd/kfd')
PROC = Path('/proc')
LINKAGE = Path('/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh')
ONLINE_NODES = Path('/sys/devices/system/node/online')
SAFE_ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C'}
SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
MAX_RESPONSE = 8 * 1024 * 1024
CLEANUP_RESERVE_S = 45
RAM_MARGIN_GIB = 100  # Rowflow's published RAM margin.
GIB = 1024**3
SCHEMA = 'epyc.kernel_promotion_hot_stack_observation.v1'
FENCE_ENV = {'ROCR_VISIBLE_DEVICES': '', 'HIP_VISIBLE_DEVICES': '-1', 'GPU_DEVICE_ORDINAL': '-1',
             'CUDA_VISIBLE_DEVICES': '-1', 'GGML_VK_VISIBLE_DEVICES': '-1', 'HSA_ENABLE_SDMA': '0'}
require = planner.require


def canonical_file(path):
    require(path.is_absolute() and path.resolve(strict=True) == path and path.is_file(),
            f'expected a canonical regular file: {path}')
    return path


def id_list(value):
    require(isinstance(value, str) and re.fullmatch(r'\d{1,3}(?:-\d{1,3})?(?:,\d{1,3}(?:-\d{1,3})?)*', value),
            f'invalid CPU or node list: {value!r}')
    result = set()
    for span in value.split(','):
        low, _, high = span.partition('-')
        members = set(range(int(low), int(high or low) + 1))
        require(members and members.isdisjoint(result), f'invalid or duplicate range: {value!r}')
        result.update(members)
    return result


def parse_grant(text):
    pairs = [token.partition('=') for token in text.split()]
    require(all(key and sep and val for key, sep, val in pairs) and len({p[0] for p in pairs}) == len(pairs),
            'malformed active Rowflow grant')
    return {key: value for key, _, value in pairs}


def grant_scope(fields, resources):
    cpus = id_list(resources['physical_cpus'])
    require(cpus == set(range(96)), 'hot-stack runtime currently requires a full-host CPU plan')
    devices = resources['gpu_devices']
    require(devices in ([], ['ROCm0']), 'hot-stack runtime supports the single host MI210')
    regions = set(fields['regions'].split(','))
    gpu = 'mi210_0' in regions
    regions.discard('mi210_0')
    cpu_tokens = [f'{int(token[1]) * 24}-{int(token[1]) * 24 + 23}'
                  if token in {'q0', 'q1', 'q2', 'q3'} else token for token in sorted(regions)]
    cpu_regions = id_list(','.join(cpu_tokens))
    holds = set(fields['holds'].split(','))
    require(cpu_regions <= set(range(192)) and {cpu % 96 for cpu in cpu_regions} == cpus
            and ('lock' not in fields or id_list(fields['lock']) == cpus)
            and {'q0', 'q1', 'q2', 'q3'} <= holds,
            'Rowflow grant differs from the full-host CPU plan')
    require(gpu == bool(devices) and (not gpu or 'gpu-quiet' in holds),
            'Rowflow grant differs from the plan GPU token')
    return gpu


def ancestor_chain():
    pid = os.getppid()
    chain = []
    while pid > 1:
        proc = PROC / str(pid)
        stat = (proc / 'stat').read_text().rsplit(') ', 1)[1].split()
        cmd = (proc / 'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
        chain.append((pid, int(stat[19]), cmd))
        pid = int(stat[1])
    return chain


def live_flocks(pid, paths):
    """Find exact lock-owning open descriptions in one ancestor's fdinfo."""
    stat_keys = {}
    for path in paths:
        stat = canonical_file(path).stat()
        stat_keys[(os.major(stat.st_dev), os.minor(stat.st_dev), stat.st_ino)] = str(path)
    global_rows = (PROC / 'locks').read_text().splitlines()
    found = {}
    for item in (PROC / str(pid) / 'fdinfo').iterdir():
        try:
            lines = item.read_text().splitlines()
        except FileNotFoundError:  # The provider may close an unrelated descriptor.
            continue
        for line in lines:
            fields = line.split()
            if fields[:1] != ['lock:'] or fields[2:5] != ['FLOCK', 'ADVISORY', 'WRITE']:
                continue
            major, minor, inode = fields[6].split(':')
            path = stat_keys.get((int(major, 16), int(minor, 16), int(inode)))
            if path:
                matching = [row for row in global_rows if row.split()[1:] == fields[2:]]
                if len(matching) == 1:
                    found[path] = {'fd': int(item.name), 'fdinfo': line, 'proc_locks': matching[0]}
    require(set(found) == set(stat_keys.values()), f'live ancestor {pid} lacks the declared exclusive flocks')
    return found


def available_ram():
    return int(re.search(r'^MemAvailable:\s+(\d+) kB$', (PROC / 'meminfo').read_text(), re.M)[1]) * 1024


def rowflow_environment(gpu, engine, environ):
    env = {key: environ[key] for key in ('FILLER_ID', 'FILLER_STOPFILE', 'FILLER_DEADLINE', 'FILLER_GPU_FENCE')}
    require(env['FILLER_GPU_FENCE'] == str(int(not gpu)), 'GPU fence state differs from the booked device')
    if gpu:
        require(not any(key in environ for key in FENCE_ENV), 'HIP grant has ambient device visibility overrides')
        return env
    require(all(environ.get(key) == value for key, value in FENCE_ENV.items()), 'CPU grant lacks Rowflow GPU visibility fence')
    preload = re.split(r'[ :]+', environ.get('LD_PRELOAD', '').strip())[0]
    fence = canonical_file(Path(preload))
    require(fence.parent == engine.parent / 'state' and re.fullmatch(r'gpu_fence-[0-9a-f]{12}\.so', fence.name),
            'CPU grant lacks the canonical Rowflow GPU preload fence')
    return env | FENCE_ENV | {'LD_PRELOAD': str(fence)}


class Admission:
    def __init__(self, plan):
        require(not any(os.environ.get(key) == '1' for key in ('FILLER_SMOKE', 'FILLER_DRYRUN', 'FILLER_DIRECT')),
                'a live keeper grant is required')
        self.row_id = os.environ['FILLER_ID']
        require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', self.row_id), 'invalid Rowflow ID')
        self.row_path = FLAGS / 'ready' / f'{self.row_id}.json'
        self.grant_path = FLAGS / 'grants' / f'{self.row_id}.grant'
        self.row_sha = planner.digest(canonical_file(self.row_path))
        self.grant_text = canonical_file(self.grant_path).read_text()
        self.fields = parse_grant(self.grant_text)
        self.row = planner.read_json(self.row_path)
        resources = plan['spec']['resources']
        self.gpu = grant_scope(self.fields, resources)
        self.ports = sorted(plan['spec']['ports'].values())
        require(self.row['schema'] == 'epyc.row.v3' and self.row['id'] == self.row_id
                and sorted(self.row['ports']) == self.ports
                and sorted(map(int, os.environ['FILLER_PORTS'].split(','))) == self.ports
                and ('mi210_0' in self.row['regions'].split(',')) == self.gpu,
                'published row or live port assignment differs from the plan')
        require(type(self.row['gib']) is int and type(resources['ram_gib']) is int
                and 0 < resources['ram_gib'] <= self.row['gib'],
                'the published RAM budget does not cover the plan')
        self.stopfile = Path(os.environ['FILLER_STOPFILE'])
        require(self.stopfile.is_absolute() and str(self.stopfile) == self.row['stop_file'],
                'published stop flag changed')
        self.start = datetime.fromisoformat(self.fields['start']).timestamp()
        self.end = datetime.fromisoformat(self.fields['end']).timestamp()
        require(int(os.environ['FILLER_END']) == self.end and os.environ.get('FILLER_NEEDGPU') == str(int(self.gpu)),
                'live Rowflow environment differs from the grant')
        self.deadline = min(self.end - CLEANUP_RESERVE_S, int(os.environ['FILLER_DEADLINE']))
        chain = ancestor_chain()
        tag = f'filler-{self.row_id}'.encode()
        providers = [(pid, birth) for pid, birth, cmd in chain
                     if cmd[1:4] == [b'-m', b'src.runtime.region_lock_cli', b'run'] and tag in cmd]
        engine = canonical_file(Path(self.row['engine']['path']))
        planner.check_pin(engine, self.row['engine']['sha256'])
        self.env = rowflow_environment(self.gpu, engine, os.environ)
        inner = [(pid, birth) for pid, birth, cmd in chain
                 if cmd[1:6] == [os.fsencode(engine), b'--inner', b'--id', os.fsencode(self.row_id), b'--class']]
        require(len(providers) == 1 and len(inner) == 1, 'missing unique Rowflow inner launcher or CPU lock ancestor')
        self.provider, self.inner = providers[0], inner[0]
        self.cgroup = (PROC / 'self/cgroup').read_text().strip()
        require(re.fullmatch(rf'0::/rowflow/{re.escape(self.row_id)}@\d+', self.cgroup)
                and all((PROC / str(pid) / 'cgroup').read_text().strip() == self.cgroup
                        for pid, _ in (self.provider, self.inner)), 'missing shared Rowflow cleanup cgroup')
        self.check()
        self.mem_before = available_ram()
        require(self.mem_before >= (resources['ram_gib'] + RAM_MARGIN_GIB) * GIB,
                'MemAvailable is below the plan budget plus the Rowflow safety margin')

    def check(self):
        require(self.start <= time.time() < self.deadline and not self.stopfile.exists(), 'grant stopped or out of time')
        require(not any(self.grant_path.with_suffix(suffix).exists() for suffix in ('.ended', '.complete'))
                and canonical_file(self.grant_path).read_text() == self.grant_text
                and planner.digest(canonical_file(self.row_path)) == self.row_sha,
                'active Rowflow row or grant changed')
        require(all(owned.birth(pid) == birth for pid, birth in (self.provider, self.inner)),
                'grant ancestor identity changed')
        flocks = live_flocks(self.provider[0], [planner.SCRATCH / f'cpu_region.GLOBAL.q{node}.lock' for node in range(4)])
        if self.gpu:
            flocks.update(live_flocks(self.inner[0], [planner.SCRATCH / 'gpu_device.mi210_0.lock']))
        return flocks

    def witness(self):
        return {'row': self.row, 'row_sha256': self.row_sha, 'grant': self.grant_text,
                'provider': self.provider, 'inner': self.inner, 'cgroup': self.cgroup,
                'flocks': self.check(), 'mem_available_bytes': self.mem_before, 'rowflow_env': self.env}


def regenerate(plan, directory, ledger):
    require(plan['schema'] == planner.PLAN_SCHEMA and plan['status'] == 'prepared_only', 'expected a prepared plan')
    original = os.environ.copy()
    try:
        os.environ.clear()
        os.environ.update(SAFE_ENV | {'ARTIFACT_FINGERPRINT_LEDGER': str(ledger)})
        actual = planner.prepare_plan(plan['spec'], directory)
    finally:
        os.environ.clear()
        os.environ.update(original)
    require(actual['contention_matrix_status'] == 'ok', 'live contention matrix must be fresh')
    require(actual == plan, 'prepared plan differs from the regenerated pinned plan')
    return actual


def chat_body():
    return {'messages': [{'role': 'user', 'content': 'Describe three uses of a notebook in one short paragraph.'}],
            'max_tokens': 64, 'temperature': 0, 'seed': 1, 'stream': False}


def embedding_body():
    passage = 'A laboratory notebook records the date, method, observations, measurements, and changes to each experiment. '
    return {'input': [f'Record {index}: {passage * 7}' for index in range(12)]}


def response_check(kind, request, result):
    if kind == 'chat':
        message = result['choices'][0]['message']
        require(message['role'] == 'assistant'
                and any(isinstance(message.get(key), str) and message[key].strip()
                        for key in ('content', 'reasoning_content')), 'chat returned no usable assistant text')
        return
    embeddings = result['data']
    count = len(request['input'])
    require(len(embeddings) == count and {item['index'] for item in embeddings} == set(range(count)),
            'embedding response indices differ from request')
    sizes = {len(item['embedding']) for item in embeddings}
    require(len(sizes) == 1 and 0 not in sizes
            and all(all(type(value) in (float, int) and math.isfinite(value) for value in item['embedding'])
                    and any(item['embedding']) for item in embeddings), 'embedding returned malformed or zero vectors')


def listeners(port):
    hits = {}
    for table in (PROC / 'net/tcp', PROC / 'net/tcp6'):
        for line in table.read_text().splitlines()[1:]:
            fields = line.split()
            host, local_port = fields[1].split(':')
            if fields[3] == '0A' and int(local_port, 16) == port:
                hits[f'socket:[{fields[9]}]'] = (table.name, host)
    return hits


def listener_owned(pid, port):
    live = listeners(port)
    if not live:
        return False
    links = set()
    for fd in (PROC / str(pid) / 'fd').iterdir():
        try:
            links.add(os.readlink(fd))
        except FileNotFoundError:
            continue
    require(len(live) == 1 and list(live.values()) == [('tcp', '0100007F')] and live.keys() <= links,
            f'isolated port {port} belongs to a different process or address')
    return True


def observed_numa(tid_dir, binary, expected_policy):
    # A file-backed executable VMA supplies a stable address with no deliberate
    # ggml placement override. Linux resolves its default policy for this TID.
    with (tid_dir / 'numa_maps').open() as stream:
        for line in stream:
            fields = line.split()
            if f'file={binary}' not in fields:
                continue
            mode, _, nodes = fields[1].partition(':')
            expected_mode, expected_nodes = expected_policy
            require(mode == expected_mode and id_list(nodes) == expected_nodes,
                    f'{tid_dir.name} NUMA policy differs from its launch binding: {fields[1]}')
            return fields[1]
    raise ValueError(f'{tid_dir.name} has no executable NUMA policy witness')


def expected_numa(argv):
    require(argv[:1] == ['numactl'] and argv[2:5] == ['--', 'taskset', '-c'], 'unknown NUMA launch prefix')
    kind, _, nodes = argv[1].partition('=')
    modes = {'--interleave': 'interleave', '--membind': 'bind'}
    require(kind in modes, 'unsupported NUMA launch policy')
    return modes[kind], id_list(ONLINE_NODES.read_text().strip() if nodes == 'all' else nodes)


def placement(pid, birth, endpoint, binary):
    root = PROC / str(pid) / 'task'
    cpus = set(endpoint['logical_cpus'])
    masks = affinity_guard.verify_threads(pid, birth, cpus, proc_root=PROC)
    policy = expected_numa(endpoint['argv'])
    result = {tid: {'cpus': mask, 'numa_policy': observed_numa(root / str(tid), binary, policy)}
              for tid, mask in masks.items()}
    require(affinity_guard.verify_threads(pid, birth, cpus, proc_root=PROC) == masks,
            'threads or affinity changed during NUMA inspection')
    return result


def backend_residency(pid, backend, gpu_id):
    clients = KFD / 'proc'
    require(clients.is_dir(), 'cannot inspect KFD clients')
    process = clients / str(pid)
    if backend == 'cpu':
        require(not process.exists(), 'CPU endpoint unexpectedly opened KFD')
        return {'kfd_client': False}
    pasid = int((process / 'pasid').read_text())
    vram = int((process / f'vram_{gpu_id}').read_text())
    require(pasid > 0 and vram > 0, 'HIP endpoint lacks a live KFD client and nonzero device VRAM')
    return {'kfd_client': True, 'gpu_id': gpu_id, 'pasid': pasid, 'vram_bytes': vram}


def image_pin(image, backend):
    root = Path(image['root'])
    binary = Path(image['binary'])
    inventory = {path: checksum for checksum, path in
                 (line.split(maxsplit=1) for line in (root / image['inventory']).read_text().splitlines())}
    names = planner.LIBRARIES + (('libggml-hip.so',) if backend == 'hip' else ())
    files = {str((binary.parent / name).resolve(strict=True).relative_to(root)) for name in names}
    return {'binary_sha256': image['binary_sha256'],
            'libraries': {Path(name).name: inventory.get(name, inventory.get('*' + name)) for name in files}}


def verify_models(endpoint):
    argv = endpoint['argv']
    model_paths = [Path(argv[index]).resolve(strict=True) for flag in planner.MODEL_FLAGS
                   if (index := planner.value_index(argv, flag, required=flag == '-m')) is not None]
    for resolved, model in zip(model_paths, endpoint['models'], strict=True):
        path = canonical_file(Path(model['path']))
        require(resolved == path and evidence.stat_identity(path.stat()) == model['stat'], f'prepared model changed: {path}')


@dataclass
class Server:
    proc: subprocess.Popen
    fd: int
    birth: int
    endpoint: dict
    binary: Path
    image: dict | None = None

    @property
    def pid(self):
        return self.proc.pid

    @property
    def port(self):
        return self.endpoint['port']


class Runtime:
    def __init__(self, plan, plan_path, directory, admission, startup_timeout, request_timeout):
        self.plan = plan
        self.plan_path = plan_path
        self.output = directory
        self.admission = admission
        self.startup_timeout = startup_timeout
        self.request_timeout = request_timeout
        self.servers = []
        self.spawn_unproved = False
        self.interrupted = None
        self.gpu_id = None

    def check(self):
        require(self.interrupted is None, f'runner interrupted by signal {self.interrupted}')
        return self.admission.check()

    def timeout(self, configured):
        self.check()
        remaining = self.admission.deadline - time.time()
        require(remaining > 0, 'grant work interval ended')
        return min(configured, remaining)

    def preflight(self):
        self.check()
        if self.admission.gpu:
            ids = {int(path.read_text()) for path in (KFD / 'topology/nodes').glob('*/gpu_id')}
            require(len(ids - {0}) == 1, 'expected one KFD device for the MI210 grant')
            self.gpu_id = (ids - {0}).pop()
        self.verify_kfd_clients()
        require(not any(listeners(port) for port in self.admission.ports), 'an isolated port is already listening')
        for backend, image in self.plan['images'].items():
            command = [str(canonical_file(LINKAGE)), image['binary'], image['library_dir']]
            env = SAFE_ENV | self.admission.env | {'LD_LIBRARY_PATH': f"{image['library_dir']}:{planner.LLVM_LIBRARY_DIR}"}
            with (self.output / f'{backend}-linkage.log').open('xb') as log:
                subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                               timeout=self.timeout(30), check=True)
        for name in ('state', 'logs'):
            (self.plan_path.parent / name).mkdir(mode=0o700)

    def verify_kfd_clients(self):
        if self.admission.gpu:
            clients = {int(path.name) for path in (KFD / 'proc').iterdir() if path.name.isdecimal()}
            declared = {server.pid for server in self.servers if server.endpoint['backend'] == 'hip'}
            require(clients <= declared, f'competing KFD clients hold the device: {sorted(clients - declared)}')

    def verify_model_inputs(self):
        for endpoint in self.plan['endpoints']:
            verify_models(endpoint)

    def start(self, endpoint):
        self.check()
        self.verify_kfd_clients()
        require(available_ram() >= RAM_MARGIN_GIB * GIB, 'host MemAvailable fell below the Rowflow safety margin')
        verify_models(endpoint)
        port = endpoint['port']
        require(not listeners(port), f'isolated port {port} is already listening')
        state = Path(endpoint['state_dir'])
        state.mkdir(mode=0o700)
        (state / 'slots').mkdir(mode=0o700)
        binary = Path(self.plan['images'][endpoint['backend']]['binary'])
        with Path(endpoint['log']).open('xb') as log:
            try:
                env = endpoint['env'] | self.admission.env
                proc, fd, birth = owned.spawn(endpoint['argv'], env=env, stdout=log,
                                               stderr=subprocess.STDOUT, registry=self.output / 'owned-pids.txt')
            except BaseException:
                self.spawn_unproved = True
                raise
            server = Server(proc, fd, birth, endpoint, binary)
            self.servers.append(server)
        require((PROC / str(server.pid) / 'cgroup').read_text().strip() == self.admission.cgroup,
                f'port {port} escaped the Rowflow cleanup cgroup')
        return server

    def verify_identity(self, server):
        require(not owned.exited(server.fd) and owned.birth(server.pid) == server.birth
                and Path(f'{PROC}/{server.pid}/exe').resolve(strict=True) == server.binary
                and listener_owned(server.pid, server.port), f'isolated listener {server.port} lost its owned identity')
        if server.image is not None:
            evidence.verify_live_image(PROC / str(server.pid), server.image)

    def ready(self, server):
        deadline = time.monotonic() + self.timeout(self.startup_timeout)
        while time.monotonic() < deadline:
            self.check()
            require(not owned.exited(server.fd), f'port {server.port} exited during startup')
            if listener_owned(server.pid, server.port):
                self.verify_identity(server)
                try:
                    status, raw = self.request_http(server, 'GET', '/health', None,
                                                    min(2, deadline - time.monotonic()))
                except OSError:
                    pass  # TLS is disabled. An owned listener may still be starting.
                else:
                    if status == 200 and json.loads(raw).get('status') == 'ok':
                        break
            time.sleep(0.25)
        else:
            raise TimeoutError(f'isolated endpoint {server.port} never became healthy')
        proc = PROC / str(server.pid)
        endpoint = server.endpoint
        server.image = evidence.live_image(proc, server.binary,
                                           image_pin(self.plan['images'][endpoint['backend']], endpoint['backend']))
        models = {model['path']: model for model in endpoint['models']}
        maps = (proc / 'maps').read_text()
        mappings = evidence.model_mappings(maps, models.keys(), models, no_mmap='--no-mmap' in endpoint['argv'])
        witness = self.sample(server)
        return {'pid': server.pid, 'birth': server.birth, 'image': server.image,
                'model_mappings': mappings, 'witness': witness}

    def sample(self, server):
        self.verify_identity(server)
        self.verify_kfd_clients()
        verify_models(server.endpoint)
        witness = {'threads': placement(server.pid, server.birth, server.endpoint, server.binary),
                   'backend': backend_residency(server.pid, server.endpoint['backend'], self.gpu_id)}
        self.verify_identity(server)
        return witness

    def request_http(self, server, method, path, body, timeout, sent=None, response_started=None):
        require(timeout > 0, 'HTTP request has no remaining time')
        deadline = time.monotonic() + timeout
        with_http = http.client.HTTPConnection('127.0.0.1', server.port, timeout=min(timeout, 5))
        try:
            self.verify_identity(server)
            with_http.connect()
            self.verify_identity(server)
            with_http.request(method, path, body=body, headers={'Content-Type': 'application/json'})
            if sent is not None:
                sent.set()
            response = with_http.getresponse()
            if response_started is not None:
                response_started()
            raw = bytearray()
            while True:
                require(time.monotonic() < deadline and len(raw) <= MAX_RESPONSE, 'HTTP response exceeded deadline or size')
                chunk = response.read1(min(64 * 1024, MAX_RESPONSE + 1 - len(raw)))
                if not chunk:
                    break
                raw.extend(chunk)
            self.verify_identity(server)
            return response.status, bytes(raw)
        finally:
            with_http.close()

    def smoke(self, server, directory):
        kind = server.endpoint['test']
        require(kind in {'chat', 'embedding'}, 'unknown endpoint smoke kind')
        body = chat_body() if kind == 'chat' else embedding_body()
        path = '/v1/chat/completions' if kind == 'chat' else '/v1/embeddings'
        planner.write_new(directory / 'request.json', body)
        timeout = self.timeout(self.request_timeout)
        sent, done = threading.Event(), threading.Event()
        outcome = {}
        started = time.monotonic()

        def request():
            try:
                def response_started():
                    outcome['response_started'] = time.monotonic()

                outcome['response'] = self.request_http(server, 'POST', path, json.dumps(body).encode(),
                                                        timeout, sent, response_started)
            except Exception as exc:
                outcome['failure'] = exc
            finally:
                outcome['finished'] = time.monotonic()
                done.set()

        worker = threading.Thread(target=request)
        worker.start()
        samples = []
        try:
            while not done.is_set() and 'response_started' not in outcome:
                self.check()
                if not sent.wait(0.05) or done.is_set() or 'response_started' in outcome:
                    continue
                sample_start = time.monotonic()
                witness = self.sample(server)
                sample_end = time.monotonic()
                if sample_end <= outcome.get('response_started', math.inf):
                    samples.append({'start_s': sample_start - started, 'end_s': sample_end - started, 'witness': witness})
                done.wait(0.1)
        finally:
            worker.join()
            elapsed = outcome['finished'] - started
            request_window = outcome.get('response_started', outcome['finished']) - started
            during = [sample for sample in samples if sample['end_s'] <= request_window]
            planner.write_new(directory / 'during-request.json',
                              {'elapsed_s': elapsed, 'request_window_s': request_window, 'samples': during})
            if 'response' in outcome:
                status, raw = outcome['response']
                (directory / 'response.raw.json').write_bytes(raw)
                planner.write_new(directory / 'http.json', {'endpoint': server.endpoint['endpoint'] + path, 'status': status})
        if 'failure' in outcome:
            raise outcome['failure']
        require(during, 'no complete affinity, NUMA, and backend scan inside request')
        require(status == 200, f'endpoint returned HTTP {status}')
        response_check(kind, body, json.loads(raw, object_pairs_hook=planner.unique_keys))

    def cleanup(self):
        result = {}
        for sig in (signal.SIGTERM, signal.SIGKILL):
            for server in self.servers:
                if not owned.exited(server.fd):
                    try:
                        signal.pidfd_send_signal(server.fd, sig)
                    except ProcessLookupError:
                        continue
                    except OSError as exc:
                        result.setdefault(str(server.pid), {}).update(signal_failure=str(exc))
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and any(not owned.exited(server.fd) for server in self.servers):
                time.sleep(0.05)
        for server in self.servers:
            try:
                exited = owned.exited(server.fd)
                record = {'pid': server.pid, 'birth': server.birth, 'port': server.port, 'pidfd_exited': exited,
                          'reaped_rc': server.proc.wait(timeout=0) if exited else None,
                          'port_closed': not listeners(server.port), 'kfd_absent': not (KFD / 'proc' / str(server.pid)).exists()}
                result.setdefault(str(server.pid), {}).update(record)
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                result.setdefault(str(server.pid), {}).update(cleanup_failure=str(exc))
            finally:
                os.close(server.fd)
        return {'spawn_unproved': self.spawn_unproved, 'servers': result}


def cleanup_proved(result):
    return not result['spawn_unproved'] and all(
        record.get('pidfd_exited') and type(record.get('reaped_rc')) is int and record.get('port_closed') and record.get('kfd_absent')
        and 'cleanup_failure' not in record for record in result['servers'].values())


def seal(output, verdict):
    manifest = output / 'MANIFEST.json'
    files = evidence.inventory(output)
    planner.write_new(manifest, {'schema': SCHEMA, 'status': 'observation_only', 'functional_smoke': verdict, 'files': files})
    require(evidence.inventory(output) == files, 'result files changed while sealing')
    with (output / 'COMPLETE').open('x') as stream:
        stream.write(planner.digest(manifest) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(output, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def execute(runtime):
    output = runtime.output
    failure = None
    try:
        runtime.preflight()
        runtime.verify_model_inputs()
        for endpoint in runtime.plan['endpoints']:
            directory = output / str(endpoint['port'])
            directory.mkdir(mode=0o700)
            server = runtime.start(endpoint)
            planner.write_new(directory / 'startup.json', runtime.ready(server))
        for server in runtime.servers:
            # Prove the whole stack is ready before testing the first endpoint.
            runtime.verify_identity(server)
        for server in runtime.servers:
            runtime.smoke(server, output / str(server.port))
        runtime.check()
    except Exception as exc:
        failure = f'{type(exc).__name__}: {exc}'
    finally:
        cleanup = runtime.cleanup()
        planner.write_new(output / 'cleanup.json', cleanup)
    if failure is None:
        try:
            runtime.check()
        except (OSError, ValueError) as exc:
            failure = f'{type(exc).__name__}: {exc}'
    artifact_failures = []
    for server in runtime.servers:
        try:
            shutil.copyfile(canonical_file(Path(server.endpoint['log'])), output / str(server.port) / 'server.log')
        except (OSError, ValueError) as exc:
            artifact_failures.append(f'port {server.port}: {exc}')
    verdict = 'pass' if failure is None and not artifact_failures and cleanup_proved(cleanup) else 'failed'
    planner.write_new(output / 'result.json', {'schema': SCHEMA, 'functional_smoke': verdict, 'failure': failure,
                                               'artifact_failures': artifact_failures, 'cleanup_proved': cleanup_proved(cleanup)})
    if cleanup_proved(cleanup):
        seal(output, verdict)
    return 0 if verdict == 'pass' else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--startup-timeout', type=int, default=900)
    parser.add_argument('--request-timeout', type=int, default=60)
    args = parser.parse_args(argv)
    try:
        plan_path = canonical_file(args.plan)
        output = args.output_dir
        scratch = planner.SCRATCH.resolve(strict=True)
        require(plan_path.name == 'plan.json' and plan_path.parent.is_relative_to(scratch)
                and plan_path.parent != scratch and (plan_path.parent.stat().st_mode & 0o077) == 0,
                'expected a private prepared plan directory under host scratch')
        require(output.is_absolute() and output.is_relative_to(scratch) and output != scratch
                and output.parent.resolve(strict=True) == output.parent
                and not output.is_relative_to(plan_path.parent), 'output must be a new directory under host scratch outside the plan directory')
        require(1 <= args.startup_timeout <= 3600 and 1 <= args.request_timeout <= 120, 'invalid lifecycle timeout')
        plan_bytes = plan_path.read_bytes()
        require(planner.is_hash(args.plan_sha256) and hashlib.sha256(plan_bytes).hexdigest() == args.plan_sha256,
                'prepared plan SHA-256 differs from the requested pin')
        plan = json.loads(plan_bytes, object_pairs_hook=planner.unique_keys)
        admission = Admission(plan)
        output.mkdir(mode=0o700)
        plan = regenerate(plan, plan_path.parent, output / 'artifact-ledger.json')
        (output / 'plan.json').write_bytes(plan_bytes)
        planner.write_new(output / 'admission.json', admission.witness())
        planner.write_new(output / 'inputs.json', {'plan_sha256': args.plan_sha256, 'runner_sha256': planner.digest(Path(__file__)),
                                                   'linkage_sha256': planner.digest(LINKAGE)})
        runtime = Runtime(plan, plan_path, output, admission, args.startup_timeout, args.request_timeout)
        previous = {sig: signal.signal(sig, lambda signum, _: setattr(runtime, 'interrupted', signum)) for sig in SIGNALS}
        try:
            return execute(runtime)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
    except (OSError, ValueError, TypeError, KeyError, IndexError, RuntimeError, ImportError, subprocess.SubprocessError) as exc:
        print(f'hot stack smoke refused: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
