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
import select
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import combinations, product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(Path(__file__).resolve().parent),
                str(ROOT / 'scripts/benchmark/jetlong_cpu'),
                str(ROOT / 'scripts/benchmark/m4_cpu_ownership')]

import affinity_guard
import kernel_promotion_evidence as evidence
import kernel_promotion_hot_stack as planner
import kernel_promotion_isolated_api as isolated_api
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
MATRIX_CONFIG = 'orchestration/contention_matrix.yaml'
PRIVATE_MATRIX_SCHEMA = 'epyc.kernel_promotion_contention_observation.v1'
PRIVATE_MATRIX_REPORT = 'epyc.kernel_promotion_private_matrix_diagnostic.v1'
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


def rowflow_ancestors(chain, row_id, engine, engine_sha):
    # At arm time the keeper copies the engine here. The launcher execs that
    # copy and unsets FILLER_ENGINE_SNAPSHOT before starting the inner process.
    snapshot = FLAGS / 'dryrun' / row_id / 'engine' / engine.name
    engines = {os.fsencode(path): path for path in (engine, snapshot)}
    inner_args = [b'--inner', b'--id', os.fsencode(row_id), b'--class']
    inner = [(index, engines[cmd[1]]) for index, (_, _, cmd) in enumerate(chain)
             if cmd[:1] == [b'/bin/bash'] and cmd[2:6] == inner_args and cmd[1] in engines]
    require(len(inner) == 1, 'missing unique Rowflow inner launcher ancestor')
    index, running_engine = inner[0]
    planner.check_pin(canonical_file(running_engine), engine_sha)

    tag = f'filler-{row_id}'.encode()
    providers = [index for index, (_, _, cmd) in enumerate(chain)
                 if cmd[1:4] == [b'-m', b'src.runtime.region_lock_cli', b'run'] and tag in cmd]
    require(providers == [index + 1], 'missing unique CPU lock provider parenting the Rowflow inner launcher')
    return chain[index + 1][:2], chain[index][:2]


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
        engine = canonical_file(Path(self.row['engine']['path']))
        engine_sha = self.row['engine']['sha256']
        planner.check_pin(engine, engine_sha)
        self.env = rowflow_environment(self.gpu, engine, os.environ)
        self.provider, self.inner = rowflow_ancestors(ancestor_chain(), self.row_id, engine, engine_sha)
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


def rebase_plan_storage(plan, source, destination):
    """Translate only the private log, state and slot paths emitted by the planner."""
    endpoints = []
    for endpoint in plan['endpoints']:
        port = str(endpoint['port'])
        argv = endpoint['argv'].copy()
        state, log = Path('state') / port, Path('logs') / f'{port}.log'
        require(endpoint['state_dir'] == str(source / state) and endpoint['log'] == str(source / log),
                'captured endpoint storage paths differ from its prepared directory')
        slot = planner.value_index(argv, '--slot-save-path', required=False)
        if slot is not None:
            require(argv[slot] == str(source / state / 'slots'), 'captured slot path differs from its prepared directory')
            argv[slot] = str(destination / state / 'slots')
        endpoints.append(endpoint | {'argv': argv, 'state_dir': str(destination / state), 'log': str(destination / log)})
    return plan | {'endpoints': endpoints}


def private_matrix_endpoints(plan):
    endpoints = []
    for port, role, instance, cores in ((8180, 'frontdoor', 2, range(48, 96)),
                                         (8086, 'worker_vision', 0, range(48))):
        matches = [endpoint for endpoint in plan['endpoints'] if endpoint['canonical_port'] == port]
        require(len(matches) == 1, f'private matrix requires exactly one canonical instance on {port}')
        endpoint = matches[0]
        require(endpoint['roles'][0] == role and endpoint['numa_instance'] == instance
                and endpoint['backend'] == 'cpu' and endpoint['device'] == 'none' and endpoint['test'] == 'chat'
                and endpoint['physical_cpus'] == list(cores), f'private matrix instance geometry differs on {port}')
        endpoints.append(endpoint)
    require(endpoints[0]['port'] != endpoints[1]['port'], 'private matrix isolated ports must be distinct')
    return endpoints


def check_private_witness(witness, endpoint, identity):
    pid, birth = identity
    require((witness['pid'], witness['birth']) == identity and witness['backend'] == {'kfd_client': False}
            and str(pid) in witness['threads'], 'private matrix CPU process witness differs from startup')
    mode, allowed_nodes = expected_numa(endpoint['argv'])
    allowed_cpus = set(endpoint['logical_cpus'])
    for tid, thread in witness['threads'].items():
        observed_mode, _, nodes = thread['numa_policy'].partition(':')
        cpus = thread['cpus']
        require(tid.isdecimal() and int(tid) > 0 and isinstance(cpus, list) and cpus
                and all(type(cpu) is int for cpu in cpus) and set(cpus) <= allowed_cpus
                and observed_mode == mode and id_list(nodes) == allowed_nodes,
                'private matrix thread affinity or NUMA witness differs from the plan')


def check_private_workloads(read, name, identities):
    workloads = read(name)
    require(workloads['verified'] == identities and workloads['identity_errors'] == {} and workloads['foreign'] == []
            and all(str(row['pid']) in identities for row in workloads['observed']),
            'private matrix workload custody differs from its captured processes')


def private_matrix_startup(read, endpoints, image):
    identities = {}
    inventory = canonical_file(Path(image['root']) / image['inventory'])
    planner.check_pin(inventory, image['inventory_sha256'])
    pin = image_pin(image, 'cpu')
    library_dir = Path(image['binary']).parent
    libraries = {str(library_dir / name): checksum for name, checksum in pin['libraries'].items()}
    verified = {}
    check_private_workloads(read, 'preload-workloads.json', verified)
    for endpoint in endpoints:
        port = str(endpoint['port'])
        check_private_workloads(read, f'preload-{port}-workloads.json', verified)
        startup = read(f'{port}.startup.json')
        pid, birth = startup['pid'], startup['birth']
        require(type(pid) is int and type(birth) is int and pid > 0 and birth > 0 and str(pid) not in verified,
                'private matrix startup lacks a unique captured identity')
        binary = startup['image']['binary']
        mapped = startup['image']['libraries']
        require(binary['sha256'] == pin['binary_sha256'] and evidence.valid_stat(binary['stat'])
                and {path: record['sha256'] for path, record in mapped.items()} == libraries
                and all(evidence.valid_stat(record['stat']) for record in mapped.values()),
                'private matrix executable or library witness differs from the candidate')
        models = {model['path']: model['stat'][:2] for model in endpoint['models']}
        mappings = startup['model_mappings']
        require(mappings.keys() <= models.keys() and all(models[path] == inode for path, inode in mappings.items())
                and ('--no-mmap' in endpoint['argv'] or mappings == models),
                'private matrix model witness differs from the prepared models')
        identity = pid, birth
        check_private_witness(startup['witness'], endpoint, identity)
        identities[port] = identity
        verified[str(pid)] = birth
    check_private_workloads(read, 'post-requests-workloads.json', verified)
    return identities


def private_matrix_phase(read, name, endpoints, identities):
    # Replay the fixed request and the four native decode legs of the v1 acquisition schema.
    request = {'prompt': 'Write a 100-word essay analyzing the philosophical implications of autonomous '
                         'decision-making in artificial intelligence systems.',
               'n_predict': 100, 'temperature': 0, 'cache_prompt': False}
    require(read(f'{name}/request.json') == request, 'private matrix request differs from the fixed acquisition request')
    check_private_workloads(read, f'{name}/workloads.json', {str(pid): birth for pid, birth in identities.values()})
    requests = read(f'{name}/requests.json')
    legs = requests['legs']
    by_port = {str(endpoint['port']): endpoint for endpoint in endpoints}
    require(legs.keys() == by_port.keys(), 'private matrix phase endpoint set differs from the acquisition scope')
    durations = {}
    for port, endpoint in by_port.items():
        leg = legs[port]
        stamps = [leg[key] for key in ('sent', 'headers', 'finished')]
        require(leg['status'] == 200 and 'failure' not in leg
                and all(type(stamp) in (int, float) and math.isfinite(stamp) and stamp > 0 for stamp in stamps)
                and stamps[0] < stamps[1] <= stamps[2], 'private matrix phase lacks a complete HTTP leg')
        timings = read(f'{name}/{port}.response.json')['timings']
        ms = timings['predicted_ms']
        require(type(timings['predicted_n']) is int and timings['predicted_n'] == request['n_predict']
                and type(ms) in (int, float) and math.isfinite(ms) and ms > 0,
                'private matrix phase lacks a complete native fixed-token response')
        durations[endpoint['roles'][0]] = ms / 1000
    start, end = max(leg['sent'] for leg in legs.values()), min(leg['headers'] for leg in legs.values())
    scans = requests['overlap_scans']
    require(isinstance(scans, list) and scans, 'private matrix phase lacks a complete request-time scan')
    for scan in scans:
        require(start <= scan['start'] < scan['end'] <= end and scan['witnesses'].keys() == by_port.keys(),
                'private matrix custody scan falls outside the shared request interval')
        for port, endpoint in by_port.items():
            check_private_witness(scan['witnesses'][port], endpoint, identities[port])
    return durations


def validate_private_matrix(plan, plan_path, result_path, result_sha):
    import yaml

    scratch = planner.SCRATCH.resolve(strict=True)
    require(plan['schema'] == planner.PLAN_SCHEMA and plan['status'] == 'prepared_only'
            and plan['contention_matrix_status'] in {'ok', 'stale'}, 'private matrix needs a pinned prepared plan')
    require(result_path.name == 'RESULT.json' and result_path.parent.name == 'out'
            and result_path.is_relative_to(scratch), 'private matrix result must be a native packet out/RESULT.json under scratch')
    result_bytes = canonical_file(result_path).read_bytes()
    require(planner.is_hash(result_sha) and hashlib.sha256(result_bytes).hexdigest() == result_sha,
            'private matrix result SHA-256 differs from the requested pin')
    result = json.loads(result_bytes, object_pairs_hook=planner.unique_keys)
    require(result['schema'] == PRIVATE_MATRIX_SCHEMA and result['status'] == 'captured'
            and result['authority'] == 'observation_only' and result['cleanup_proved'] is True,
            'private matrix needs a captured, cleanup-proved native observation')
    attempt_id = result['attempt_id']
    require(planner.is_hash(attempt_id, 32), 'invalid private matrix attempt identity')
    capture = result_path.parent / attempt_id
    require(str(capture) == result['capture_dir'] and capture.resolve(strict=True) == capture
            and (capture.stat().st_mode & 0o077) == 0, 'private matrix capture must be the canonical private attempt')
    files = result['files']
    require(not any((capture / name).exists() for name in ('MANIFEST.json', 'COMPLETE'))
            and files == evidence.inventory(capture), 'private matrix file inventory differs from the acquisition manifest')

    def bound_bytes(name):
        require(name in files, f'private matrix capture is missing {name}')
        data = canonical_file(capture / name).read_bytes()
        require(hashlib.sha256(data).hexdigest() == files[name], f'private matrix artifact changed: {name}')
        return data

    def read(name):
        return json.loads(bound_bytes(f'observation/{name}'), object_pairs_hook=planner.unique_keys)

    summary = json.loads(bound_bytes('result.json'), object_pairs_hook=planner.unique_keys)
    require(not {'capture_dir', 'files'} & summary.keys()
            and result == (summary | {'capture_dir': str(capture), 'files': files}),
            'private matrix outer result differs from its captured result.json')
    packet = result_path.parent.parent
    prepared_dir = packet / 'prepared'
    prepared_file = canonical_file(prepared_dir / 'plan.json')
    prepared = bound_bytes('observation/prepared-plan.json')
    plan_sha = hashlib.sha256(prepared).hexdigest()
    require((prepared_dir.stat().st_mode & 0o077) == 0 and prepared_file.read_bytes() == prepared
            and canonical_file(prepared_dir / 'plan.sha256').read_text().strip() == plan_sha
            and result['plan_sha256'] == plan_sha, 'private matrix acquisition prepared plan pin differs')
    captured_plan = json.loads(prepared, object_pairs_hook=planner.unique_keys)
    source_status = captured_plan['contention_matrix_status']
    require(source_status in {'ok', 'stale'} and result['source_matrix_status_at_prepare'] == source_status
            and rebase_plan_storage(captured_plan, prepared_dir, plan_path.parent)
            == (plan | {'contention_matrix_status': source_status}),
            'private matrix prepared topology, endpoints, images, models or config differ from the live plan')
    matrix_bytes = bound_bytes('observation/source-matrix.yaml')
    matrix_sha = plan['spec']['config_sha256'][MATRIX_CONFIG]
    topology = plan['topology_hash']
    live_matrix = canonical_file(planner.ORCHESTRATOR.resolve(strict=True) / MATRIX_CONFIG)
    try:
        source_matrix = yaml.safe_load(matrix_bytes)
    except yaml.YAMLError as exc:
        raise ValueError('private matrix source matrix is invalid') from exc
    require(hashlib.sha256(matrix_bytes).hexdigest() == result['source_matrix_sha256'] == matrix_sha
            and live_matrix.read_bytes() == matrix_bytes
            and isinstance(source_matrix, dict) and source_matrix.get('topology_hash') == result['topology_hash'] == topology,
            'private matrix source bytes or topology differ from the pinned live matrix')
    endpoints = private_matrix_endpoints(captured_plan)
    roles = [endpoint['roles'][0] for endpoint in endpoints]
    instances = [{'role': endpoint['roles'][0], 'port': endpoint['port'], 'canonical_port': endpoint['canonical_port'],
                  'instance_idx': endpoint['numa_instance']} for endpoint in endpoints]
    require(result['roles'] == roles and result['instances'] == instances and type(result['samples']) is int
            and result['samples'] == 1 and result['scope'] == 'isolated_cpu_instance_pair',
            'private matrix result differs from the selected instance pair')
    ports = {str(endpoint['canonical_port']): endpoint['port'] for endpoint in endpoints}
    resources = plan['spec']['resources'] | {'gpu_devices': []}
    inputs = read('inputs.json')
    producer = 'sources/scripts/benchmark/kernel_promotion_contention_acquire.py'
    manifest = canonical_file(packet / 'SOURCE.sha256').read_text().splitlines()
    producer_pins = [line.split(maxsplit=1)[0] for line in manifest if line.split(maxsplit=1)[-1:] == [producer]]
    require(producer_pins == [inputs['producer_sha256']], 'private matrix producer differs from the packet source pin')
    planner.check_pin(canonical_file(packet / producer), inputs['producer_sha256'])
    require(inputs['plan_sha256'] == plan_sha
            and inputs['linkage_sha256'] == planner.digest(LINKAGE)
            and inputs['scope'] == {'ports': ports, 'resources': resources},
            'private matrix input, producer, linkage or claim scope differs')
    admission = read('admission.json')
    require(admission['row']['schema'] == 'epyc.row.v3' and admission['row']['id'] == result['unit_id']
            and sorted(admission['row']['ports']) == sorted(ports.values())
            and all(admission['rowflow_env'].get(key) == value for key, value in FENCE_ENV.items())
            and not grant_scope(parse_grant(admission['grant']), resources), 'private matrix lacks its CPU grant and fence')
    bound_bytes('observation/host.json')
    bound_bytes('observation/cpu-linkage.log')
    identities = private_matrix_startup(read, endpoints, plan['images']['cpu'])
    registry = bound_bytes('observation/owned-pids.txt').decode().splitlines()
    require(registry == [f'{pid} {birth}' for pid, birth in identities.values()], 'private matrix PID registry differs')
    for port in identities:
        bound_bytes(f'observation/{port}.server.log')
    solo = {}
    for endpoint in endpoints:
        solo.update(private_matrix_phase(read, f'solo-{endpoint["roles"][0]}', [endpoint], identities))
    parallel = private_matrix_phase(read, 'parallel', endpoints, identities)
    seq_s, parallel_s = sum(solo.values()), max(parallel.values())
    require(result['decode_s'] == {'solo': solo, 'parallel': parallel}
            and result['seq_aggregate_tps'] == 200 / seq_s and result['parallel_aggregate_tps'] == 200 / parallel_s
            and result['ratio'] == seq_s / parallel_s, 'private matrix native decode summary does not reproduce')
    cleanup = read('cleanup.json')
    require(cleanup['spawn_unproved'] is False and cleanup_proved(cleanup)
            and cleanup['servers'].keys() == {str(pid) for pid, _ in identities.values()},
            'private matrix cleanup does not cover both captured processes')
    for port, (pid, birth) in identities.items():
        clean = cleanup['servers'][str(pid)]
        require((clean['pid'], clean['birth'], clean['port']) == (pid, birth, int(port))
                and all(clean[key] is True for key in ('pidfd_exited', 'port_closed', 'kfd_absent')),
                'private matrix cleanup identity or closure proof differs')
    return {'schema': PRIVATE_MATRIX_REPORT, 'authority': 'observation_only', 'status': 'validated_capture',
            'acquisition_result_sha256': result_sha, 'source_matrix_status_at_prepare': source_status,
            'acquisition_plan_sha256': plan_sha, 'acquisition_unit_id': result['unit_id'],
            'acquisition_attempt_id': attempt_id, 'contention_matrix_sha256': matrix_sha, 'topology_hash': topology,
            'endpoints': [{key: endpoint[key] for key in ('canonical_port', 'port', 'roles', 'physical_cpus', 'device')}
                          for endpoint in endpoints]}


def matrix_instance_matches(instance, endpoint):
    threads = planner.value_index(endpoint['argv'], '-t', required=False)
    return (isinstance(instance, dict) and threads is not None
            and instance.get('role') == endpoint['roles'][0]
            and instance.get('port') == endpoint['canonical_port']
            and instance.get('instance_idx') == endpoint['numa_instance']
            and str(instance.get('threads')) == endpoint['argv'][threads]
            and id_list(instance.get('cpu_list')) == set(endpoint['logical_cpus']))


def select_concurrency_pair(endpoints, matrix):
    """Return the first explicitly allowed pair of disjoint canonical instances."""
    unknown = {tuple(sorted(row['roles'])) for row in matrix.get('unknown_pairs', [])}
    for left, right in combinations(sorted(endpoints, key=lambda endpoint: endpoint['canonical_port']), 2):
        if (left['port'] == right['port'] or set(left['physical_cpus']) & set(right['physical_cpus'])
                or left['device'] == right['device'] != 'none'):
            continue
        roles = tuple(sorted((left['roles'][0], right['roles'][0])))
        if roles[0] == roles[1] or roles in unknown:
            continue
        matches = []
        for row in matrix.get('pairs', []):
            if tuple(sorted(row['roles'])) != roles:
                continue
            first, second = row.get('instance_a'), row.get('instance_b')
            if (matrix_instance_matches(first, left) and matrix_instance_matches(second, right)
                    or matrix_instance_matches(second, left) and matrix_instance_matches(first, right)):
                matches.append(row)
        if len(matches) == 1 and matches[0]['verdict'] == 'allow':
            return (left, right), matches[0]
    raise ValueError('no distinct, disjoint endpoint pair explicitly allowed by the pinned contention matrix')


def overlapping_samples(left, right):
    """Locate overlapping complete scans inside the common request window."""
    if any(report[field] is None for report in (left, right) for field in ('request_sent_s', 'response_headers_s')):
        return None
    sent = max(left['request_sent_s'], right['request_sent_s'])
    headers = min(left['response_headers_s'], right['response_headers_s'])
    for (li, ls), (ri, rs) in product(enumerate(left['samples']), enumerate(right['samples'])):
        start = max(ls['start_s'], rs['start_s'])
        end = min(ls['end_s'], rs['end_s'])
        if sent <= min(ls['start_s'], rs['start_s']) and start < end and max(ls['end_s'], rs['end_s']) <= headers:
            return {'sample_indices': [li, ri], 'start_s': start, 'end_s': end,
                    'request_start_s': sent, 'request_end_s': headers}
    return None


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


def chat_comparability(body, response):
    """Classify the evidence available from one captured chat response."""
    choices = response.get('choices')
    choice = (choices[0] if isinstance(choices, list) and len(choices) == 1
              and isinstance(choices[0], dict) else {})
    index = choice.get('index')
    message = choice.get('message')
    finish = choice.get('finish_reason')
    usage = response.get('usage')
    count = usage.get('completion_tokens') if isinstance(usage, dict) else None
    limit = body['max_tokens']
    if type(count) is not int or not 0 < count <= limit:
        count = None
    timings = response.get('timings')
    timing_count = timings.get('predicted_n') if isinstance(timings, dict) else None
    completion = (count is not None and type(index) is int and index == 0 and 'error' not in response
                  and ('timings' not in response or type(timing_count) is int and timing_count == count)
                  and (finish == 'stop' or finish == 'length' and count == limit))
    _, content, ids = evidence.parity_values(body, response, count)
    has_content = (isinstance(message, dict) and message.get('role') == 'assistant'
                   and content is not None and bool(content.strip()))
    return {'status': 'comparable' if completion and has_content and ids is not None else 'diagnostic_incomplete',
            'completion': 'complete' if completion else 'incomplete',
            'completion_tokens': count,
            'content': 'complete' if has_content else 'incomplete',
            'token_ids': 'complete' if ids is not None else 'incomplete'}


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
    def __init__(self, plan, plan_path, directory, admission, startup_timeout, request_timeout, *, plan_sha256=None):
        self.plan = plan
        self.plan_path = plan_path
        self.plan_sha256 = plan_sha256
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

    def select_pair(self):
        import yaml

        config = canonical_file(planner.ORCHESTRATOR.resolve(strict=True) / MATRIX_CONFIG).read_bytes()
        checksum = self.plan['spec']['config_sha256'][MATRIX_CONFIG]
        require(hashlib.sha256(config).hexdigest() == checksum, 'contention matrix changed after plan regeneration')
        matrix = yaml.safe_load(config)
        require(self.plan['contention_matrix_status'] == 'ok' and matrix['topology_hash'] == self.plan['topology_hash'],
                'paired concurrency requires a fresh, topology-matched contention matrix')
        endpoints, row = select_concurrency_pair(self.plan['endpoints'], matrix)
        return {'endpoints': [{key: endpoint[key] for key in ('canonical_port', 'port', 'roles', 'physical_cpus', 'device')}
                              for endpoint in endpoints],
                'contention_matrix_sha256': checksum, 'topology_hash': matrix['topology_hash'], 'matrix_pair': row}

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
        witness = {'pid': server.pid, 'birth': server.birth,
                   'threads': placement(server.pid, server.birth, server.endpoint, server.binary),
                   'backend': backend_residency(server.pid, server.endpoint['backend'], self.gpu_id)}
        self.verify_identity(server)
        return witness

    def request_http(self, server, method, path, body, timeout, request_sent=None, response_started=None,
                     send_barrier=None):
        require(timeout > 0, 'HTTP request has no remaining time')
        deadline = time.monotonic() + timeout
        with_http = http.client.HTTPConnection('127.0.0.1', server.port, timeout=min(timeout, 5))
        try:
            self.verify_identity(server)
            with_http.connect()
            self.verify_identity(server)
            if send_barrier is not None:
                send_barrier.wait(timeout=max(0, deadline - time.monotonic()))
                remaining = deadline - time.monotonic()
                require(remaining > 0, 'paired request has no time remaining after dispatch barrier')
                with_http.sock.settimeout(min(remaining, 5))
            with_http.request(method, path, body=body, headers={'Content-Type': 'application/json'})
            if request_sent is not None:
                request_sent()
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
            if request_sent is None:
                self.verify_identity(server)
            return response.status, bytes(raw)
        finally:
            with_http.close()

    def smoke(self, server, directory, *, send_barrier=None, clock_origin=None, sent=None, peer_sent=None):
        kind = server.endpoint['test']
        require(kind in {'chat', 'embedding'}, 'unknown endpoint smoke kind')
        body = chat_body() if kind == 'chat' else embedding_body()
        path = '/v1/chat/completions' if kind == 'chat' else '/v1/embeddings'
        planner.write_new(directory / 'request.json', body)
        timeout = self.timeout(self.request_timeout)
        sent = threading.Event() if sent is None else sent
        done = threading.Event()
        outcome = {}
        started = time.monotonic() if clock_origin is None else clock_origin

        def request():
            try:
                def request_sent():
                    outcome['request_sent'] = time.monotonic()
                    sent.set()

                def response_started():
                    outcome['response_started'] = time.monotonic()

                outcome['response'] = self.request_http(server, 'POST', path, json.dumps(body).encode(),
                                                        timeout, request_sent, response_started, send_barrier)
                self.verify_identity(server)
            except Exception as exc:
                outcome['failure'] = exc
                if send_barrier is not None:
                    send_barrier.abort()
            finally:
                outcome['finished'] = time.monotonic()
                done.set()

        worker = threading.Thread(target=request)
        worker.start()
        samples = []
        try:
            while not done.is_set() and 'response_started' not in outcome:
                self.check()
                if (not sent.wait(0.05) or (peer_sent is not None and not peer_sent.wait(0.05))
                        or done.is_set() or 'response_started' in outcome):
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
            sent_at = outcome.get('request_sent')
            headers_at = outcome.get('response_started')
            planner.write_new(directory / 'during-request.json',
                              {'elapsed_s': elapsed, 'request_window_s': request_window,
                               'request_sent_s': None if sent_at is None else sent_at - started,
                               'response_headers_s': None if headers_at is None else headers_at - started,
                               'samples': during})
            if 'response' in outcome:
                status, raw = outcome['response']
                (directory / 'response.raw.json').write_bytes(raw)
                planner.write_new(directory / 'http.json', {'endpoint': server.endpoint['endpoint'] + path, 'status': status})
        if 'failure' in outcome:
            raise outcome['failure']
        require(during, 'no complete affinity, NUMA, and backend scan inside request')
        require(status == 200, f'endpoint returned HTTP {status}')
        result = json.loads(raw, object_pairs_hook=planner.unique_keys)
        if kind == 'chat':
            planner.write_new(directory / 'response-comparability.json',
                              chat_comparability(body, result if isinstance(result, dict) else {}))
        response_check(kind, body, result)

    def paired_smoke(self, selected):
        directory = self.output / 'paired-concurrency'
        directory.mkdir(mode=0o700)
        planner.write_new(directory / 'pair.json', selected)
        servers = {server.port: server for server in self.servers}
        ports = [endpoint['port'] for endpoint in selected['endpoints']]
        for port in ports:
            (directory / str(port)).mkdir(mode=0o700)
        send_barrier = threading.Barrier(2)
        clock_origin = time.monotonic()
        sent = {port: threading.Event() for port in ports}
        failures = {}
        observations = {}

        def smoke_port(port, peer):
            try:
                self.smoke(servers[port], directory / str(port), send_barrier=send_barrier,
                           clock_origin=clock_origin, sent=sent[port], peer_sent=sent[peer])
            except Exception:
                send_barrier.abort()
                raise

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {port: pool.submit(smoke_port, port, peer) for port, peer in zip(ports, reversed(ports), strict=True)}
            for port, future in futures.items():
                try:
                    future.result()
                except Exception as exc:
                    failures[str(port)] = f'{type(exc).__name__}: {exc}'
                capture = directory / str(port) / 'during-request.json'
                if capture.is_file():
                    observations[port] = planner.read_json(capture)
        overlap = overlapping_samples(*(observations[port] for port in ports)) if len(observations) == 2 else None
        passed = not failures and overlap is not None
        planner.write_new(directory / 'result.json',
                          {'status': 'pass' if passed else 'failed', 'ports': ports, 'failures': failures, 'overlap': overlap})
        require(passed, 'paired concurrency requires two successful requests and overlapping complete witness scans')

    def observe_api_worker(self, proc, channel, server, deadline, capture):
        requests = capture['requests']
        active = None
        next_scan = 0
        while True:
            self.check()
            remaining = deadline - time.monotonic()
            require(remaining > 0, 'isolated API worker exceeded its request deadline')
            running = proc.poll() is None
            if select.select([channel], [], [], min(remaining, 0.02) if running else 0)[0]:
                event, request_id, stamp = json.loads(channel.recv(1024))
                fields = ('connect', 'dispatch', 'sent', 'headers')
                require(event in fields and type(request_id) is int and request_id > 0
                        and type(stamp) is int and capture['start_ns'] <= stamp <= time.monotonic_ns(),
                        'invalid isolated API trace event')
                row = requests.setdefault(str(request_id), {'samples': []})
                position = fields.index(event)
                previous = fields[position - 1] if position else None
                require(event not in row and (previous is None or row.get(previous, math.inf) <= stamp),
                        'out-of-order isolated API trace event')
                row[event] = stamp
                if event in {'connect', 'dispatch'}:
                    try:
                        self.verify_identity(server)
                    except Exception as exc:
                        capture.setdefault('witness_failure', f'{type(exc).__name__}: {exc}')
                        channel.send(b'deny')
                    else:
                        channel.send(b'allow')
                elif event == 'sent':
                    require(active is None, 'overlapping generation requests in isolated API smoke')
                    active = row
                    next_scan = 0
                else:
                    require(active is row, 'isolated API headers do not match the generation request')
                    row['samples'] = [sample for sample in row['samples'] if sample['end_ns'] <= stamp]
                    active = None
            elif not running:
                return
            if active is not None and 'witness_failure' not in capture and time.monotonic() >= next_scan:
                start = time.monotonic_ns()
                try:
                    witness = self.sample(server)
                except Exception as exc:
                    capture['witness_failure'] = f'{type(exc).__name__}: {exc}'
                else:
                    end = time.monotonic_ns()
                    active['samples'].append({'start_ns': start, 'end_ns': end, 'witness': witness})
                    next_scan = time.monotonic() + 0.1

    def isolated_api_smoke(self, role, port):
        directory = self.output / 'isolated-api'
        directory.mkdir(mode=0o700)
        capture = {'start_ns': time.monotonic_ns(), 'requests': {}}
        result = {'status': 'failed', 'role': role, 'requested_port': port}
        try:
            self.check()
            url, selected_port = isolated_api.select_endpoint(self.plan['endpoint_manifest'], role, port, set())
            matches = [server for server in self.servers if server.port == selected_port
                       and server.endpoint['test'] == 'chat' and server.endpoint['endpoint'] == url
                       and server.endpoint['roles'][0] == role]
            require(len(matches) == 1 and matches[0].image is not None, 'forced role has no ready owned chat server')
            server = matches[0]
            result.update(base_url=url, port=selected_port, pid=server.pid, birth=server.birth)
            self.verify_identity(server)
            require(planner.is_hash(self.plan_sha256), 'isolated API requires the admitted plan digest')
            consumer = canonical_file(Path(isolated_api.__file__).resolve())
            result['consumer_sha256'] = planner.digest(consumer)
            output = directory / 'consumer'
            budget = self.timeout(self.request_timeout)
            require(budget >= 1, 'isolated API has no complete second left in the grant')
            deadline = time.monotonic() + budget
            channel, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
            with channel, child, (directory / 'consumer.log').open('xb') as log:
                command = [sys.executable, '-I', '-B', str(consumer), '--plan', str(self.output / 'plan.json'),
                           '--plan-sha256', self.plan_sha256, '--output-dir', str(output), '--role', role,
                           '--port', str(selected_port), '--timeout', str(int(budget)),
                           '--witness-fd', str(child.fileno())]
                proc = subprocess.Popen(command, env=os.environ | self.admission.env, stdout=log,
                                        stderr=subprocess.STDOUT, pass_fds=(child.fileno(),))
                result.update(worker_pid=proc.pid, worker_cleanup_proved=False)
                try:
                    child.close()
                    result['worker_birth'] = owned.birth(proc.pid)
                    result['worker_cgroup'] = (PROC / str(proc.pid) / 'cgroup').read_text().strip()
                    require(result['worker_cgroup'] == self.admission.cgroup,
                            'isolated API worker escaped the Rowflow cleanup cgroup')
                    self.observe_api_worker(proc, channel, server, deadline, capture)
                finally:
                    try:
                        if proc.poll() is None:
                            proc.terminate()
                        result['worker_returncode'] = proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        try:
                            proc.kill()
                            result['worker_returncode'] = proc.wait(timeout=3)
                        except BaseException:
                            self.spawn_unproved = True
                            raise
                    except BaseException:
                        self.spawn_unproved = True
                        raise
                    result['worker_cleanup_proved'] = True
            api_result = planner.read_json(output / 'result.json')
            require(result['worker_returncode'] == 0 and api_result['status'] == 'passed',
                    api_result.get('error', 'isolated API consumer failed'))
            require(api_result['plan_sha256'] == self.plan_sha256 and api_result['role'] == role
                    and api_result['base_url'] == url, 'isolated API result changed its endpoint binding')
            require('witness_failure' not in capture, capture.get('witness_failure', ''))
            generation = [str(index) for index, call in enumerate(api_result['outbound'], 1)
                          if call['method'] == 'POST' and call['path'] in isolated_api.GENERATION_PATHS]
            require(len(generation) == 1, 'isolated API did not record exactly one generation')
            row = capture['requests'].get(generation[0], {})
            require('headers' in row and row['samples'],
                    'no complete affinity, NUMA, and backend scan inside isolated API generation request')
            require(all('dispatch' in capture['requests'].get(str(index), {})
                        for index in range(1, len(api_result['outbound']) + 1)),
                    'isolated API outbound call is missing its dispatch identity witness')
            self.verify_identity(server)
            result.update(status='pass', generation_request=generation[0])
        except Exception as exc:
            result['error'] = f'{type(exc).__name__}: {exc}'
            raise
        finally:
            for row in capture['requests'].values():
                if 'headers' not in row:
                    row['samples'] = []
            planner.write_new(directory / 'during-request.json', capture)
            planner.write_new(directory / 'result.json', result)

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


def execute(runtime, *, paired_concurrency=False, api_role=None, api_port=None):
    output = runtime.output
    failure = None
    api_status = 'not_run'
    try:
        selected = runtime.select_pair() if paired_concurrency else None
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
        if selected is not None:
            runtime.paired_smoke(selected)
        if api_role is not None:
            api_status = 'failed'
            runtime.isolated_api_smoke(api_role, api_port)
            api_status = 'pass'
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
    result = {'schema': SCHEMA, 'functional_smoke': verdict, 'failure': failure,
              'artifact_failures': artifact_failures, 'cleanup_proved': cleanup_proved(cleanup),
              'paired_concurrency_requested': paired_concurrency}
    if api_role is not None:
        result['isolated_api'] = {'role': api_role, 'requested_port': api_port, 'status': api_status}
    planner.write_new(output / 'result.json', result)
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
    parser.add_argument('--paired-concurrency', action='store_true',
                        help='also test one explicitly allowed disjoint endpoint pair')
    parser.add_argument('--api-role', help='also run the isolated forced-role /chat smoke for this role')
    parser.add_argument('--api-port', type=int, help='isolated port for the forced role when it has multiple instances')
    parser.add_argument('--private-matrix-result', type=Path,
                        help='validate a native acquisition offline and export a private diagnostic record')
    parser.add_argument('--private-matrix-result-sha256', help='pinned SHA-256 of the native acquisition RESULT.json')
    args = parser.parse_args(argv)
    if args.api_port is not None and args.api_role is None:
        parser.error('--api-port requires --api-role')
    if (args.private_matrix_result is None) != (args.private_matrix_result_sha256 is None):
        parser.error('--private-matrix-result and --private-matrix-result-sha256 must be supplied together')
    if args.private_matrix_result is not None and (args.paired_concurrency or args.api_role is not None):
        parser.error('private matrix validation runs offline and cannot be combined with live diagnostics')
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
        if args.private_matrix_result is not None:
            require(not output.is_relative_to(args.private_matrix_result.parent.parent),
                    'private matrix output must be outside the acquisition packet')
            record = validate_private_matrix(plan, plan_path, args.private_matrix_result, args.private_matrix_result_sha256)
            output.mkdir(mode=0o700)
            planner.write_new(output / 'private-matrix-diagnostic.json', record | {'plan_sha256': args.plan_sha256})
            return 0
        admission = Admission(plan)
        output.mkdir(mode=0o700)
        plan = regenerate(plan, plan_path.parent, output / 'artifact-ledger.json')
        (output / 'plan.json').write_bytes(plan_bytes)
        planner.write_new(output / 'admission.json', admission.witness())
        inputs = {'plan_sha256': args.plan_sha256, 'runner_sha256': planner.digest(Path(__file__)),
                  'linkage_sha256': planner.digest(LINKAGE), 'paired_concurrency_requested': args.paired_concurrency}
        if args.api_role is not None:
            inputs.update(api_role=args.api_role, api_port=args.api_port)
        planner.write_new(output / 'inputs.json', inputs)
        runtime = Runtime(plan, plan_path, output, admission, args.startup_timeout, args.request_timeout,
                          plan_sha256=args.plan_sha256)
        previous = {sig: signal.signal(sig, lambda signum, _: setattr(runtime, 'interrupted', signum)) for sig in SIGNALS}
        try:
            return execute(runtime, paired_concurrency=args.paired_concurrency, api_role=args.api_role, api_port=args.api_port)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
    except (OSError, ValueError, TypeError, KeyError, IndexError, RuntimeError, ImportError, subprocess.SubprocessError) as exc:
        print(f'hot stack smoke refused: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
