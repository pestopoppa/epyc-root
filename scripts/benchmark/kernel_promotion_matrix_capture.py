#!/usr/bin/env python3
"""Acquire configured-primary contention pairs or admit a complete split matrix offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import uuid

SOURCE = Path(__file__).resolve().parent
sys.path.insert(0, str(SOURCE))

import kernel_promotion_contention_acquire as acquisition

runner = acquisition.runner
planner = runner.planner
require = planner.require
SCHEMA = 'epyc.kernel_promotion_matrix_capture.v1'
SPLIT_SCHEMA = 'epyc.kernel_promotion_split_matrix_admission.v1'
ORCHESTRATOR_PIN = '12afe2858f9dbd4691447926d6cf1864de64348c'
C13 = 'bda43aa17c11b671e0e203e7eb7bf4f1303bc273'
PORTS = {
    'architect_critic': (8083, 19574),
    'architect_general': (8074, 19573),
    'frontdoor': (8070, 19572),
    'worker_vision': (8086, 19575),
}
RAM = {'cpu': 384, 'hip': 448, 'full': 448}
SCOPE = {'cpu': 'configured_primary_cpu_pairs',
         'hip': 'configured_primary_hip_critic_pairs',
         'full': 'all_configured_primary_pairs'}
STARTUP_TIMEOUT = 780
SPLIT_GGUF = re.compile(r'(.*)-(\d{5})-of-(\d{5})\.gguf')
MATRIX_SCRIPT = 'scripts/server/contention_matrix.py'
FRESHNESS_SCRIPT = 'scripts/validate/check_contention_matrix_fresh.py'
HEALTH_RULE_FILES = (
    Path('/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/server_np_sweep.py'),
    Path('/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/server_numa_np_sweep.py'),
)


def canonical_checkout(packet, spec):
    root = packet / 'orchestrator'
    require(root == root.resolve(strict=True) and spec['orchestrator_commit'] == ORCHESTRATOR_PIN
            and planner.git(root, 'rev-parse', 'HEAD') == ORCHESTRATOR_PIN
            and not planner.git(root, 'branch', '--show-current')
            and not planner.git(root, 'status', '--porcelain', '--untracked-files=all'),
            'canonical modules require the clean detached orchestrator checkout')
    planner.ORCHESTRATOR = root
    planner.check_stack_inputs(spec)
    return root


def canonical_modules(packet, spec):
    root = canonical_checkout(packet, spec)
    sys.path[:0] = [str(root / 'scripts/server'), str(root)]
    import contention_matrix
    import stack_numa
    from src.scheduling import contention

    for module in (contention_matrix, stack_numa, contention):
        require(Path(module.__file__).resolve().is_relative_to(root),
                f'module {module.__name__} did not load from the pinned checkout')
    return contention_matrix, stack_numa.NUMA_CONFIG, contention


def pair_sets(matrix, config, phase):
    required = matrix._enumerate_full_pairs(config)
    roles = sorted({role for pair in required for role in pair})
    require(roles == sorted(PORTS) and len(required) == 6,
            'configured role pair universe differs from the prepared scope')
    cpu = [pair for pair in required if 'architect_critic' not in pair]
    hip = [pair for pair in required if 'architect_critic' in pair]
    return required, {'cpu': cpu, 'hip': hip, 'full': required}[phase]


def endpoint_records(matrix, config, endpoints, pairs):
    roles = {role for pair in pairs for role in pair}
    require(len(endpoints) == len(roles), 'phase requires exactly its configured-primary endpoints')
    instances = {}
    for endpoint in endpoints:
        role = endpoint['roles'][0]
        require(role in roles and role not in instances, f'host plan has duplicate or unexpected role {role}')
        idx, canonical_port, regions = matrix._role_footprints(config, role)[0]
        declared = matrix._instance_record(role, idx, canonical_port, regions, config)
        require((endpoint['canonical_port'], endpoint['port']) == PORTS[role]
                and endpoint['canonical_port'] == canonical_port
                and endpoint['numa_instance'] == idx == 0
                and runner.id_list(declared['cpu_list']) == set(endpoint['logical_cpus'])
                and int(endpoint['argv'][planner.value_index(endpoint['argv'], '-t')]) == declared['threads']
                and endpoint['argv'][planner.value_index(endpoint['argv'], '--host')] == '127.0.0.1'
                and int(endpoint['argv'][planner.value_index(endpoint['argv'], '--port')]) == endpoint['port'],
                f'{role} does not match the configured primary and isolated loopback port')
        expected = 'hip' if role == 'architect_critic' else 'cpu'
        require(endpoint['backend'] == expected and endpoint['device'] == ('ROCm0' if expected == 'hip' else 'none'),
                f'{role} execution backend differs from the pinned scope')
        instances[role] = declared
    return instances


def extra_inputs(endpoint):
    argv = endpoint['argv']
    inputs = {}
    for model in endpoint['models']:
        path = Path(model['path'])
        split = SPLIT_GGUF.fullmatch(path.name)
        if split:
            stem, number, total = split.groups()
            require(int(number) == 1 and 1 < int(total) <= 32, f'invalid first model shard: {path}')
            for index in range(2, int(total) + 1):
                sibling = runner.canonical_file(path.with_name(f'{stem}-{index:05d}-of-{total}.gguf'))
                inputs[str(sibling)] = {'stat': runner.evidence.stat_identity(sibling.stat())}
    index = planner.value_index(argv, '--chat-template-file', required=False)
    if index is not None:
        template = runner.canonical_file(Path(argv[index]))
        inputs[str(template)] = {'stat': runner.evidence.stat_identity(template.stat()), 'sha256': planner.digest(template)}
    return inputs


def verify_inputs(endpoint, pins):
    runner.verify_models(endpoint)
    require(extra_inputs(endpoint) == pins, f'model shard or template identity changed on :{endpoint["port"]}')


def integrity_paths(root):
    return [root / MATRIX_SCRIPT, root / FRESHNESS_SCRIPT, runner.LINKAGE, *HEALTH_RULE_FILES]


def verify_image_inventory(image):
    root = Path(image['root'])
    planner.check_pin(runner.canonical_file(root / image['inventory']), image['inventory_sha256'])
    planner.check_pin(runner.canonical_file(root / 'BUILD-IDENTITY.json'), image['identity_sha256'])


def prepare(packet, phase):
    spec = planner.read_json(packet / 'spec.json')
    matrix, config, contention = canonical_modules(packet, spec)
    from scripts.server import orchestrator_stack as launch, stack_manifest as manifest, stack_numa as numa

    all_pairs, pairs = pair_sets(matrix, config, phase)
    roles = {role for pair in pairs for role in pair}
    servers = [row for row in manifest.HOT_SERVERS + manifest.WARM_SERVERS
               if row['port'] in {PORTS[role][0] for role in roles}]
    ports = {str(PORTS[role][0]): PORTS[role][1] for role in sorted(roles)}
    spec.update(ports=ports, endpoint_tests={port: 'chat' for port in ports},
                resources={'physical_cpus': '0-95',
                           'gpu_devices': [] if phase == 'cpu' else ['ROCm0'],
                           'ram_gib': RAM[phase]})
    canonical_ports = set(manifest.PORT_MAP.values()) | {service.port for service in manifest.AUX_SERVICES.values()}
    canonical_ports.update(row['port'] for row in manifest.HOT_SERVERS + manifest.WARM_SERVERS)
    planner.validate_endpoints(spec, servers, canonical_ports)
    candidate = spec['candidate']
    require(candidate['source_commit'] == C13, 'matrix preparation requires the pinned champion C13 commit')
    production = planner.production_runtime_dirs()
    backends = ('cpu',) if phase == 'cpu' else ('cpu', 'hip')
    images = {backend: planner.verify_stage(candidate[backend], candidate, backend, production) for backend in backends}
    phase_dir = packet / phase
    prepared = phase_dir / 'prepared'
    prepared.mkdir(mode=0o700, parents=True)
    registry = launch.RegistryLoader()
    endpoints = []
    for server in servers:
        endpoint = planner.build_endpoint(spec, prepared, server, manifest, launch, numa, registry, images)
        models = []
        for flag in planner.MODEL_FLAGS:
            index = planner.value_index(endpoint['argv'], flag, required=flag == '-m')
            if index is not None:
                path = runner.canonical_file(Path(endpoint['argv'][index]).resolve(strict=True))
                models.append({'path': str(path), 'stat': runner.evidence.stat_identity(path.stat())})
        endpoint['models'] = models
        endpoints.append(endpoint)
    planner.validate_claim(spec['resources'], endpoints, numa, manifest._HOST_PHYSICAL_CORES)
    records = endpoint_records(matrix, config, endpoints, pairs)
    source_path = planner.ORCHESTRATOR / runner.MATRIX_CONFIG
    source_matrix = contention.load_contention_matrix(source_path)
    topology = contention.topology_fingerprint({role: config[role] for role in sorted(PORTS)})
    require(source_matrix.topology_hash == topology == contention.topology_fingerprint_for_matrix(config, source_matrix),
            'source matrix and configured-primary topology differ')
    files = {str(path): planner.digest(path) for path in integrity_paths(planner.ORCHESTRATOR)}
    plan = {
        'schema': SCHEMA, 'phase': phase, 'spec': spec, 'images': images, 'endpoints': endpoints,
        'required_pairs': all_pairs, 'phase_pairs': pairs, 'instances': records, 'topology_hash': topology,
        'source_matrix_measured_at': source_matrix.measured_at,
        'source_matrix_status_at_prepare': contention.matrix_status(source_path, current_topology_hash=topology).value,
        'extra_inputs': {str(endpoint['port']): extra_inputs(endpoint) for endpoint in endpoints},
        'files': files,
    }
    path = prepared / 'plan.json'
    planner.write_new(path, plan)
    (prepared / 'plan.sha256').write_text(planner.digest(path) + '\n')
    return path


def read_prepared(packet, phase, *, trusted_sha=None, modules=None):
    path = runner.canonical_file(packet / phase / 'prepared/plan.json')
    require(path.parent.stat().st_mode & 0o077 == 0, 'prepared plan must be private')
    digest = runner.canonical_file(path.parent / 'plan.sha256').read_text().strip()
    data = path.read_bytes()
    require(planner.is_hash(digest) and hashlib.sha256(data).hexdigest() == digest
            and (trusted_sha is None or digest == trusted_sha), f'invalid or changed prepared plan pin: {path}')
    plan = json.loads(data, object_pairs_hook=planner.unique_keys)
    require(plan['schema'] == SCHEMA and plan['phase'] == phase and plan['spec']['candidate']['source_commit'] == C13,
            'prepared plan phase or C13 identity changed')
    if modules is None:
        matrix, config, contention = canonical_modules(packet, plan['spec'])
    else:
        # Both detached checkouts have the same pinned commit. Verify this checkout,
        # then replay with the canonical modules already imported from the first.
        canonical_checkout(packet, plan['spec'])
        matrix, config, contention = modules
    all_pairs, pairs = pair_sets(matrix, config, phase)
    require(plan['required_pairs'] == [list(pair) for pair in all_pairs]
            and plan['phase_pairs'] == [list(pair) for pair in pairs]
            and plan['instances'] == endpoint_records(matrix, config, plan['endpoints'], pairs)
            and plan['topology_hash'] == contention.topology_fingerprint({role: config[role] for role in PORTS}),
            'prepared pair set, primary geometry or topology changed')
    require(set(plan['files']) == {str(path) for path in integrity_paths(planner.ORCHESTRATOR)},
            'prepared validator or provenance dependencies are missing')
    for filename, expected in plan['files'].items():
        planner.check_pin(Path(filename), expected)
    require(acquisition.REQUEST == {
        'prompt': matrix.PROMPT, 'n_predict': matrix.N_PREDICT,
        'temperature': 0, 'cache_prompt': False,
    } and acquisition.N_PREDICT == matrix.N_PREDICT
        and matrix.TIMEOUT_PER_REQUEST_S == 180, 'fixed request differs from the canonical bench protocol')
    for endpoint in plan['endpoints']:
        verify_inputs(endpoint, plan['extra_inputs'][str(endpoint['port'])])
    backends = {'cpu'} if phase == 'cpu' else {'cpu', 'hip'}
    require(plan['spec']['resources'] == {'physical_cpus': '0-95',
                                         'gpu_devices': [] if phase == 'cpu' else ['ROCm0'],
                                         'ram_gib': RAM[phase]}
            and set(plan['images']) == backends, 'prepared resource or build scope changed')
    for backend, image in plan['images'].items():
        expected = plan['spec']['candidate'][backend]
        require(all(image[key] == value for key, value in expected.items()), 'prepared image provenance changed')
        verify_image_inventory(image)
    return path, digest, plan, matrix, config, contention


class MatrixRuntime(runner.Runtime):
    def verify_kfd_clients(self):
        # Even the CPU-only phase is an exclusive interference measurement.
        clients = {int(path.name) for path in (runner.KFD / 'proc').iterdir() if path.name.isdecimal()}
        allowed = {server.pid for server in self.servers if server.endpoint['backend'] == 'hip'
                   and runner.owned.birth(server.pid) == server.birth}
        require(clients <= allowed, f'foreign KFD workloads: {sorted(clients - allowed)}')

    def sample(self, server):
        verify_inputs(server.endpoint, self.plan['extra_inputs'][str(server.port)])
        return super().sample(server)

    def ready(self, server):
        image = self.plan['images'][server.endpoint['backend']]
        verify_image_inventory(image)
        result = super().ready(server)
        verify_image_inventory(image)
        return result


def result_pair(matrix, instances, roles, solo, parallel):
    values = acquisition.ratio(*(solo[role] for role in roles), *(parallel[role] for role in roles))
    solo_a, solo_b = (matrix.BenchResult(instances[role]['port'], role, matrix.N_PREDICT / solo[role], solo[role])
                      for role in roles)
    par_a, par_b = (matrix.BenchResult(instances[role]['port'], role, matrix.N_PREDICT / parallel[role], parallel[role])
                    for role in roles)
    return matrix.PairBench(roles, instances[roles[0]], instances[roles[1]], solo_a, solo_b, par_a, par_b, **values)


def validate_full(path, plan, matrix, config, contention):
    import yaml

    candidate = contention.load_contention_matrix(path)
    checked_topology = contention.topology_fingerprint_for_matrix(config, candidate)
    expected = {tuple(pair) for pair in plan['required_pairs']}
    require(set(candidate.pairs) == expected and not candidate.unknown_pairs
            and candidate.topology_hash == checked_topology == plan['topology_hash']
            and contention.matrix_status(path, current_topology_hash=checked_topology) == contention.MatrixStatus.OK,
            'scratch matrix failed full coverage, topology or freshness check')
    rows = yaml.safe_load(path.read_text())['pairs']
    require(len(rows) == len(expected) and {tuple(row['roles']) for row in rows} == expected,
            'scratch matrix contains duplicate or unexpected raw pair entries')
    for row in rows:
        first, second = row['roles']
        require(row['instance_a'] == plan['instances'][first] and row['instance_b'] == plan['instances'][second],
                f'scratch matrix changed configured-primary evidence: {first}, {second}')
    proc = subprocess.run([sys.executable, '-I', '-B', str(planner.ORCHESTRATOR / FRESHNESS_SCRIPT),
                           '--matrix-path', str(path)], capture_output=True, text=True, timeout=30)
    require(proc.returncode == 0, f'canonical freshness gate refused scratch matrix: {proc.stdout}{proc.stderr}')
    return {'check_output': proc.stdout.strip(), 'sha256': planner.digest(path),
            'host_health': matrix.read_matrix_host_health(path)}


def acquisition_interval(result, now=None):
    """Validate original conservative UTC bounds; never manufacture capture time."""
    try:
        start = datetime.fromisoformat(result['acquisition_started_at'])
        end = datetime.fromisoformat(result['acquisition_finished_at'])
        require(start.tzinfo is not None and end.tzinfo is not None, 'capture times require timezone')
        start, end = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
        require(start <= end <= (now or datetime.now(timezone.utc)), 'capture time is reversed or future')
        return start, end
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError('capture times missing or malformed') from exc


def stamp_acquisition_start(emitted, result):
    acquisition_interval(result)
    emitted, count = re.subn(r'^measured_at: .*$',
                             'measured_at: ' + json.dumps(result['acquisition_started_at']),
                             emitted, flags=re.MULTILINE)
    require(count == 1, 'canonical emitter must provide exactly one measurement time')
    return emitted


def source_identity(plan):
    return {'repo_commit': ORCHESTRATOR_PIN, 'path': runner.MATRIX_CONFIG,
            'sha256': plan['spec']['config_sha256'][runner.MATRIX_CONFIG],
            'measured_at': plan['source_matrix_measured_at'],
            'status_at_prepare': plan['source_matrix_status_at_prepare']}


def capture(packet, phase, row_id, directory):
    result = {'schema': SCHEMA, 'unit_id': row_id, 'attempt_id': directory.name, 'status': 'failed',
              'phase': phase, 'phase_scope': SCOPE[phase], 'authority': 'isolated_observation', 'completed_pairs': [],
              'complete_matrix': False}
    runtime = None
    handlers = {}
    records = []
    try:
        acquisition.require_live_grant(row_id, os.environ)
        # A conservative wall-clock bound for every following measured cell.
        result['acquisition_started_at'] = datetime.now(timezone.utc).isoformat()
        path, digest, plan, matrix, config, contention = read_prepared(packet, phase)
        result.update(
            prepared_plan={'path': str(path), 'sha256': digest},
            source_matrix=source_identity(plan),
            topology_hash=plan['topology_hash'], required_pairs=plan['required_pairs'],
            phase_pairs=plan['phase_pairs'], orchestrator_commit=ORCHESTRATOR_PIN, candidate_commit=C13,
        )
        admission = runner.Admission(plan)
        planner.write_new(directory / 'admission.json', admission.witness())
        runtime = MatrixRuntime(plan, path, directory, admission, STARTUP_TIMEOUT, matrix.TIMEOUT_PER_REQUEST_S,
                                plan_sha256=digest)
        handlers = {sig: signal.signal(sig, lambda number, _: setattr(runtime, 'interrupted', number))
                    for sig in runner.SIGNALS}
        acquisition.check_workloads(runtime, directory / 'preload-workloads.json')
        runtime.preflight()
        runtime.verify_model_inputs()
        before = matrix._host_health_probe(expected_ports=set())
        planner.write_new(directory / 'host-before.json', {'identity': runner.evidence.host_snapshot(), 'health': before})
        live = {}
        for endpoint in plan['endpoints']:
            acquisition.check_workloads(runtime, directory / f'preload-{endpoint["port"]}-workloads.json')
            server = runtime.start(endpoint)
            live[endpoint['roles'][0]] = server
            planner.write_new(directory / f'{server.port}.startup.json', runtime.ready(server))
        for first, second in plan['phase_pairs']:
            cell = directory / f'{first}--{second}'
            cell.mkdir(mode=0o700)
            solo = acquisition.capture_phase(runtime, cell / 'solo-a', [live[first]])
            solo.update(acquisition.capture_phase(runtime, cell / 'solo-b', [live[second]]))
            parallel = acquisition.capture_phase(runtime, cell / 'parallel', [live[first], live[second]])
            acquisition.check_workloads(runtime, cell / 'post-workloads.json')
            record = result_pair(matrix, plan['instances'], (first, second), solo, parallel)
            planner.write_new(cell / 'cell.json', record.to_yaml_dict() | {'solo_s': solo, 'parallel_s': parallel,
                              'isolated_ports': {role: live[role].port for role in (first, second)}})
            records.append(record)
            result['completed_pairs'].append([first, second])
        runtime.check()
        acquisition.check_workloads(runtime, directory / 'post-requests-workloads.json')
        health = matrix._host_health_probe(expected_ports={server.port for server in live.values()},
                                           extra_blockers=before['decision_grade_blockers'])
        acquisition.check_workloads(runtime, directory / 'post-health-workloads.json')
        runtime.verify_kfd_clients()
        runtime.check()
        planner.check_stack_inputs(plan['spec'])
        planner.write_new(directory / 'host-after.json', health)
        result.update(status='captured', host_health=health, samples_per_cell=1)
    except Exception as exc:
        result.update(status='failed', failure=f'{type(exc).__name__}: {exc}')
    finally:
        try:
            acquisition.finish_cleanup(runtime, directory, result)
        finally:
            for sig, handler in handlers.items():
                signal.signal(sig, handler)

    if 'acquisition_started_at' in result:
        result['acquisition_finished_at'] = datetime.now(timezone.utc).isoformat()
        try:
            acquisition_interval(result)
        except ValueError as exc:
            result.update(status='failed', failure=f'{type(exc).__name__}: {exc}')

    if result['status'] == 'captured' and phase == 'full':
        output = directory / 'contention_matrix.yaml'
        try:
            source = planner.ORCHESTRATOR / runner.MATRIX_CONFIG
            provenance = {'git_commit': C13}
            for backend, image in plan['images'].items():
                field = 'llama_server_path' if backend == 'cpu' else 'hip_llama_server_path'
                provenance[field] = image['binary']
                provenance[f'{backend}_binary_sha256'] = image['binary_sha256']
            emitted = matrix._emit_yaml(records, topology_hash=plan['topology_hash'],
                                        binary=provenance, host=health['hostname'], host_health=health,
                                        preserve_sections=matrix._carry_forward_sections(source))
            emitted = stamp_acquisition_start(emitted, result)
            with output.open('x') as stream:
                stream.write(emitted)
            result['matrix'] = validate_full(output, plan, matrix, config, contention)
            result['complete_matrix'] = True
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            result.update(status='failed', failure=f'{type(exc).__name__}: {exc}')
    planner.write_new(directory / 'result.json', result)
    return result


def attempt_inventory(directory):
    require(directory.is_dir() and not directory.is_symlink(), f'invalid native evidence directory: {directory}')
    files = {}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink() or not path.is_dir():
            files[str(path.relative_to(directory))] = planner.digest(runner.canonical_file(path))
    return files


def pinned_bytes(path, expected):
    data = runner.canonical_file(path).read_bytes()
    require(planner.is_hash(expected) and hashlib.sha256(data).hexdigest() == expected,
            f'invalid or changed SHA-256 pin: {path}')
    return data


def packet_sources(packet, path, plan_sha, source_sha):
    manifest = pinned_bytes(packet / 'SOURCE.sha256', source_sha)
    entries = {}
    for line in manifest.decode().splitlines():
        checksum, filename = line.split(maxsplit=1)
        require(filename not in entries and planner.is_hash(checksum), 'invalid packet source manifest')
        entries[filename] = checksum
    expected = [f'sources/scripts/benchmark/{name}.py' for name in (
        'kernel_promotion_matrix_capture', 'kernel_promotion_contention_acquire',
        'kernel_promotion_hot_stack_runner', 'kernel_promotion_hot_stack', 'kernel_promotion_evidence',
    )]
    require(entries.get(str(path.relative_to(packet))) == plan_sha and all(name in entries for name in expected),
            'packet source manifest lacks the prepared plan or acquisition source pins')
    for name in expected:
        planner.check_pin(runner.canonical_file(packet / name), entries[name])
    return {'manifest_sha256': source_sha,
            'tool_sha256': {name: entries[name] for name in expected}}


def validate_split_grant(admission, plan, result, interval):
    row, env = admission['row'], admission['rowflow_env']
    unit_id = result['unit_id']
    phase = plan['phase']
    gpu = phase == 'hip'
    resources = plan['spec']['resources']
    fields = runner.parse_grant(admission['grant'])
    grant_start, grant_end = (datetime.fromisoformat(fields[key]) for key in ('start', 'end'))
    require(grant_start.tzinfo is not None and grant_end.tzinfo is not None
            and grant_start <= interval[0] <= interval[1] <= grant_end,
            f'{phase} acquisition lies outside its recorded grant')
    require(runner.grant_scope(fields, resources) == gpu
            and row['schema'] == 'epyc.row.v3' and row['id'] == env['FILLER_ID'] == unit_id
            and sorted(row['ports']) == sorted(plan['spec']['ports'].values())
            and ('mi210_0' in row['regions'].split(',')) == gpu
            and type(row['gib']) is int and row['gib'] >= resources['ram_gib']
            and admission['mem_available_bytes'] >= (resources['ram_gib'] + runner.RAM_MARGIN_GIB) * runner.GIB
            and planner.is_hash(admission['row_sha256'])
            and row['stop_file'] == env['FILLER_STOPFILE']
            and re.fullmatch(rf'0::/rowflow/{re.escape(unit_id)}@\d+', admission['cgroup']),
            f'{phase} scope differs from its recorded Rowflow admission')
    locks = {str(planner.SCRATCH / f'cpu_region.GLOBAL.q{node}.lock') for node in range(4)}
    if gpu:
        locks.add(str(planner.SCRATCH / 'gpu_device.mi210_0.lock'))
    require(admission['flocks'].keys() == locks and env['FILLER_GPU_FENCE'] == str(int(not gpu)),
            f'{phase} admission lacks its exclusive locks or expected GPU fence')
    if gpu:
        require(not (env.keys() & (*runner.FENCE_ENV, 'LD_PRELOAD')), 'HIP admission carries CPU fence settings')
    else:
        fence = Path(env['LD_PRELOAD'])
        require(all(env.get(key) == value for key, value in runner.FENCE_ENV.items())
                and fence.parent == Path(row['engine']['path']).parent / 'state'
                and re.fullmatch(r'gpu_fence-[0-9a-f]{12}\.so', fence.name),
                'CPU admission lacks the recorded Rowflow GPU fence')


def validate_split_health(health, matrix, phase, expected_processes):
    require(health['status'] == 'clean' and health['decision_grade'] is True
            and health['decision_grade_blockers'] == [] and health['attestation_error'] == ''
            and health['attestation_status'] == 'collected' and health['rule_source'] == matrix._HOST_HEALTH_RULE_SOURCE
            and type(health['uptime_seconds']) in (int, float) and math.isfinite(health['uptime_seconds'])
            and health['uptime_seconds'] > 0 and health['hostname'] and health['kernel']
            and health['llama_processes_foreign'] == []
            and health['llama_processes_lineup'] == health['llama_processes_at_attestation'] == expected_processes
            and set(health['warnings']) == set(health['structural_for_harness']),
            f'{phase} host-health refusal: {health}')


def validate_native_witness(witness, endpoint, identity, numa_online, hip_backend=None):
    pid, birth = identity
    threads = witness['threads']
    require((witness['pid'], witness['birth']) == identity
            and runner.evidence.valid_affinity({tid: row['cpus'] for tid, row in threads.items()},
                                               pid, set(endpoint['logical_cpus'])),
            f'port {endpoint["port"]} placement differs from its captured identity')
    argv = endpoint['argv'].copy()
    if argv[1] == '--interleave=all':
        argv[1] = '--interleave=' + numa_online
    mode, nodes = runner.expected_numa(argv)
    for thread in threads.values():
        policy, _, observed = thread['numa_policy'].partition(':')
        require(policy == mode and runner.id_list(observed) == nodes,
                f'port {endpoint["port"]} NUMA policy differs from its prepared binding')
    backend = witness['backend']
    if endpoint['backend'] == 'cpu':
        require(backend == {'kfd_client': False} and backend['kfd_client'] is False,
                f'CPU port {endpoint["port"]} lacks the KFD absence witness')
    else:
        require(backend['kfd_client'] is True
                and all(type(backend[key]) is int and backend[key] > 0 for key in ('gpu_id', 'pasid', 'vram_bytes'))
                and (hip_backend is None or all(backend[key] == hip_backend[key] for key in ('gpu_id', 'pasid'))),
                f'HIP port {endpoint["port"]} lacks its captured KFD client or nonzero device VRAM')


def validate_split_startup(startup, endpoint, image):
    port = endpoint['port']
    binary = startup['image']['binary']
    libraries = startup['image']['libraries']
    pin = runner.image_pin(image, endpoint['backend'])
    expected = {str(Path(image['library_dir']) / name): checksum for name, checksum in pin['libraries'].items()}
    require(binary['sha256'] == pin['binary_sha256'] and runner.evidence.valid_stat(binary['stat'])
            and {path: row['sha256'] for path, row in libraries.items()} == expected
            and all(runner.evidence.valid_stat(row['stat']) for row in libraries.values()),
            f'port {port} loaded executable or library differs from its pinned image')
    models = {model['path']: model['stat'] for model in endpoint['models']}
    mappings = startup['model_mappings']
    required_models = set(models)
    index = planner.value_index(endpoint['argv'], '--mmproj', required=False)
    if index is not None:
        source = endpoint['argv'][index]
        path = str(Path(source).resolve(strict=True))
        require(startup['mmproj'] == {'path': path, 'stat': models[path], 'argv_path': source, 'mapped': path in mappings},
                f'port {port} projector witness differs from its prepared input')
        required_models.remove(path)
    require(mappings.keys() <= models.keys() and all(models[path][:2] == inode for path, inode in mappings.items())
            and ('--no-mmap' in endpoint['argv'] or required_models <= mappings.keys()),
            f'port {port} model mapping differs from its prepared inputs')


def replay_native_legs(read, raw, name, roles, endpoints, startups, identities, numa_online):
    require(read(f'{name}/request.json') == acquisition.REQUEST, f'{name} request differs from the fixed protocol')
    runner.check_private_workloads(read, f'{name}/workloads.json', identities)
    requests = read(f'{name}/requests.json')
    legs, scans = requests['legs'], requests['overlap_scans']
    by_port = {str(endpoints[role]['port']): role for role in roles}
    require(legs.keys() == by_port.keys() and isinstance(scans, list) and scans,
            f'{name} lacks the expected native legs and request-time custody scan')
    durations = {}
    for port, role in by_port.items():
        leg = legs[port]
        sent, headers, finished = (leg[key] for key in ('sent', 'headers', 'finished'))
        require(all(type(value) in (int, float) and math.isfinite(value) for value in (sent, headers, finished))
                and 0 < sent < headers <= finished and 'failure' not in leg,
                f'{name} port {port} has an invalid native request interval')
        body = raw(f'{name}/{port}.response.json')
        require(len(body) <= runner.MAX_RESPONSE, f'{name} port {port} response exceeds the native size limit')
        durations[role] = acquisition.leg_timing(leg['status'], body)
    require(acquisition.complete_scans(legs, scans) == scans, f'{name} custody scan fell outside the shared request interval')
    for scan in scans:
        require(scan['witnesses'].keys() == by_port.keys(), f'{name} custody scan differs from the native leg scope')
        for port, role in by_port.items():
            startup = startups[role]
            validate_native_witness(scan['witnesses'][port], endpoints[role], (startup['pid'], startup['birth']),
                                    numa_online, startup['witness']['backend'])
    return durations


def replay_split_phase(plan, matrix, read, raw, logs, numa_online):
    endpoints = {endpoint['roles'][0]: endpoint for endpoint in plan['endpoints']}
    for backend, image in plan['images'].items():
        linkage = raw(f'{backend}-linkage.log').decode().splitlines()
        require(linkage[:2] == [f'binary : {image["binary"]}', f'expect : libraries under {image["library_dir"]}']
                and f'PASS: all linked ggml libraries resolve inside {image["library_dir"]}' in linkage
                and any(re.match(r'\s+OK\s+libggml-base\.so', line) for line in linkage)
                and not any(re.match(r'\s*(?:FAIL:|BAD\s)', line) for line in linkage),
                f'{backend} native linkage evidence differs from the prepared candidate')
    identities, startups = {}, {}
    runner.check_private_workloads(read, 'preload-workloads.json', identities)
    for role, endpoint in endpoints.items():
        port = endpoint['port']
        runner.check_private_workloads(read, f'preload-{port}-workloads.json', identities)
        startup = read(f'{port}.startup.json')
        pid, birth = startup['pid'], startup['birth']
        require(type(pid) is int and pid > 0 and type(birth) is int and birth > 0 and str(pid) not in identities,
                f'port {port} lacks a unique captured PID and birth')
        validate_split_startup(startup, endpoint, plan['images'][endpoint['backend']])
        validate_native_witness(startup['witness'], endpoint, (pid, birth), numa_online)
        require(logs(f'{port}.log'), f'port {port} lacks its native server log')
        identities[str(pid)], startups[role] = birth, startup
    require(raw('owned-pids.txt').decode().splitlines() == [f'{pid} {birth}' for pid, birth in identities.items()],
            'native PID registry differs from the exact startup identities')

    records = []
    for first, second in plan['phase_pairs']:
        name = f'{first}--{second}'
        roles = first, second
        solo = replay_native_legs(read, raw, f'{name}/solo-a', (first,), endpoints, startups, identities, numa_online)
        solo.update(replay_native_legs(read, raw, f'{name}/solo-b', (second,), endpoints, startups, identities, numa_online))
        parallel = replay_native_legs(read, raw, f'{name}/parallel', roles, endpoints, startups, identities, numa_online)
        record = result_pair(matrix, plan['instances'], roles, solo, parallel)
        require(read(f'{name}/cell.json') == record.to_yaml_dict() | {
            'solo_s': solo, 'parallel_s': parallel, 'isolated_ports': {role: endpoints[role]['port'] for role in roles},
        }, f'{name} cell differs from its native raw decode timings')
        runner.check_private_workloads(read, f'{name}/post-workloads.json', identities)
        records.append(record)

    for name in ('post-requests-workloads.json', 'post-health-workloads.json'):
        runner.check_private_workloads(read, name, identities)
    cleanup = read('cleanup.json')
    require(cleanup['spawn_unproved'] is False and runner.cleanup_proved(cleanup)
            and identities.keys() == cleanup['servers'].keys(), 'cleanup does not cover the exact captured PID set')
    for role, endpoint in endpoints.items():
        pid, birth = startups[role]['pid'], startups[role]['birth']
        record = cleanup['servers'][str(pid)]
        require((record['pid'], record['birth'], record['port']) == (pid, birth, endpoint['port'])
                and all(record[key] is True for key in ('pidfd_exited', 'port_closed', 'kfd_absent')),
                f'port {endpoint["port"]} lacks exact cleanup identity or closure proof')
    return records


@dataclass
class SplitPhase:
    plan_path: Path
    plan: dict
    interval: tuple[datetime, datetime]
    records: list
    custody: dict


def read_split_phase(result_path, result_sha, plan_sha, source_sha, phase, modules=None):
    packet = result_path.parents[2]
    scratch = planner.SCRATCH.resolve(strict=True)
    require(result_path == packet / phase / 'out/RESULT.json' and packet.is_relative_to(scratch) and packet != scratch,
            f'{phase} result must be the canonical packet {phase}/out/RESULT.json under host scratch')
    result = json.loads(pinned_bytes(result_path, result_sha), object_pairs_hook=planner.unique_keys)
    path, digest, plan, matrix, config, contention = read_prepared(packet, phase, trusted_sha=plan_sha, modules=modules)
    require(result['attempt_id'] == Path(result['capture_dir']).name and planner.is_hash(result['attempt_id'], 32),
            f'{phase} attempt identity is invalid')
    directory = result_path.parent / result['attempt_id']
    log_dir = path.parent / 'logs'
    require(str(directory) == result['capture_dir'] and directory.resolve(strict=True) == directory
            and directory.is_dir() and directory.stat().st_mode & 0o077 == 0,
            f'{phase} native attempt must be its canonical private directory')
    require(log_dir.resolve(strict=True) == log_dir and log_dir.is_dir() and log_dir.stat().st_mode & 0o077 == 0,
            f'{phase} server logs must be in the original private prepared plan directory')
    files, log_files = result['attempt_files_sha256'], result['server_logs_sha256']['files']
    require(files == attempt_inventory(directory) and result['server_logs_sha256']['path'] == str(log_dir)
            and log_files == attempt_inventory(log_dir), f'{phase} native attempt or server log inventory changed')

    def artifact(parent, inventory, name):
        require(name in inventory, f'{phase} missing native artifact {name}')
        return pinned_bytes(parent / name, inventory[name])

    def raw(name):
        return artifact(directory, files, name)

    def read(name):
        return json.loads(raw(name), object_pairs_hook=planner.unique_keys)

    summary = read('result.json')
    envelope = {'capture_dir', 'attempt_files_sha256', 'server_logs_sha256'}
    require(not (envelope & summary.keys()) and summary == {key: value for key, value in result.items() if key not in envelope},
            f'{phase} outer result differs from its inventory-bound native summary')
    require(summary['schema'] == SCHEMA and summary['status'] == 'captured' and summary['authority'] == 'isolated_observation'
            and summary['unit_id'] == matrix_row_id(phase) and summary['cleanup_proved'] is True
            and summary['complete_matrix'] is False and type(summary['samples_per_cell']) is int
            and summary['samples_per_cell'] == 1 and summary['phase'] == phase and summary['phase_scope'] == SCOPE[phase]
            and summary['required_pairs'] == plan['required_pairs']
            and summary['phase_pairs'] == summary['completed_pairs'] == plan['phase_pairs'],
            f'{phase} result lacks a complete, cleanup-proved three-pair native capture')
    source = source_identity(plan)
    source_path = runner.canonical_file(packet / 'orchestrator' / source['path'])
    pinned_bytes(source_path, source['sha256'])
    source_matrix = contention.load_contention_matrix(source_path)
    require(summary['prepared_plan'] == {'path': str(path), 'sha256': digest}
            and summary['orchestrator_commit'] == ORCHESTRATOR_PIN and summary['candidate_commit'] == C13
            and summary['source_matrix'] == source and summary['topology_hash'] == plan['topology_hash']
            and source['status_at_prepare'] in {'ok', 'stale'} and source_matrix.measured_at == source['measured_at']
            and source_matrix.topology_hash == plan['topology_hash']
            == contention.topology_fingerprint_for_matrix(config, source_matrix),
            f'{phase} native plan, source matrix or topology differs from its pins')
    sources = packet_sources(packet, path, digest, source_sha)
    interval = acquisition_interval(summary)
    validate_split_grant(read('admission.json'), plan, summary, interval)
    before, after = read('host-before.json'), read('host-after.json')
    require(after == summary['host_health'], f'{phase} host after probe differs from its native summary')
    validate_split_health(before['health'], matrix, f'{phase} before', 0)
    validate_split_health(after, matrix, f'{phase} after', len(plan['endpoints']))
    require(all(before['health'][key] == after[key] for key in ('hostname', 'kernel')),
            f'{phase} host identity differs between the recorded health probes')
    runner.id_list(before['identity']['numa_online'])
    records = replay_split_phase(plan, matrix, read, raw, lambda name: artifact(log_dir, log_files, name),
                                 before['identity']['numa_online'])
    custody = {key: summary[key] for key in ('attempt_id', 'unit_id', 'acquisition_started_at', 'acquisition_finished_at')}
    custody.update(result_path=str(result_path), result_sha256=result_sha, prepared_plan=summary['prepared_plan'],
                   packet_sources=sources, source_matrix=source, phase_pairs=summary['completed_pairs'],
                   host_before=before, host_after=after)
    return SplitPhase(path, plan, interval, records, custody), (matrix, config, contention)


def shared_split_plan(cpu, hip):
    cpu_plan, hip_plan = cpu.plan, hip.plan
    scoped = {'ports', 'resources', 'endpoint_tests'}
    require({key: value for key, value in cpu_plan['spec'].items() if key not in scoped}
            == {key: value for key, value in hip_plan['spec'].items() if key not in scoped}
            and cpu_plan['images']['cpu'] == hip_plan['images']['cpu']
            and cpu.custody['source_matrix']['sha256'] == hip.custody['source_matrix']['sha256']
            and cpu_plan['topology_hash'] == hip_plan['topology_hash'],
            'split captures disagree on source, topology, config or CPU build image')
    cpu_endpoints = runner.rebase_plan_storage(cpu_plan, cpu.plan_path.parent, hip.plan_path.parent)['endpoints']
    hip_endpoints = {endpoint['port']: endpoint for endpoint in hip_plan['endpoints']}
    for endpoint in cpu_endpoints:
        port = endpoint['port']
        require(endpoint == hip_endpoints[port] and cpu_plan['extra_inputs'][str(port)] == hip_plan['extra_inputs'][str(port)]
                and cpu_plan['instances'][endpoint['roles'][0]] == hip_plan['instances'][endpoint['roles'][0]],
                f'split captures disagree on prepared CPU recipe, models, shards, templates or geometry for port {port}')
    for relative in (MATRIX_SCRIPT, FRESHNESS_SCRIPT):
        paths = [str(phase.plan_path.parents[2] / 'orchestrator' / relative) for phase in (cpu, hip)]
        require(cpu_plan['files'][paths[0]] == hip_plan['files'][paths[1]], f'split validator source differs: {relative}')
    for path in (runner.LINKAGE, *HEALTH_RULE_FILES):
        require(cpu_plan['files'][str(path)] == hip_plan['files'][str(path)], f'split witness source differs: {path}')
    cpu_pairs, hip_pairs = ({tuple(pair) for pair in phase.plan['phase_pairs']} for phase in (cpu, hip))
    expected = {tuple(pair) for pair in hip_plan['required_pairs']}
    require(len(cpu_plan['phase_pairs']) == len(hip_plan['phase_pairs']) == len(cpu_pairs) == len(hip_pairs) == 3
            and cpu_pairs.isdisjoint(hip_pairs) and (cpu_pairs | hip_pairs) == expected
            and cpu_plan['required_pairs'] == hip_plan['required_pairs'], 'split scopes do not cover six distinct pairs')
    return hip_plan


def merge_split(cpu_pin, hip_pin, output):
    cpu, modules = read_split_phase(*cpu_pin, 'cpu')
    hip, _ = read_split_phase(*hip_pin, 'hip', modules=modules)
    matrix, config, contention = modules
    plan = shared_split_plan(cpu, hip)
    first, last = sorted((cpu, hip), key=lambda phase: phase.interval[0])
    require(first.interval[1] <= last.interval[0], 'exclusive split acquisition intervals overlap')
    for key in ('hostname', 'kernel'):
        require(cpu.custody['host_after'][key] == hip.custody['host_after'][key], 'split health probes refer to different hosts')
    for key in ('numa_online', 'numa_cpus', 'cpu_online', 'cpu_model'):
        require(cpu.custody['host_before']['identity'][key] == hip.custody['host_before']['identity'][key],
                f'split captures disagree on host geometry: {key}')

    scratch = planner.SCRATCH.resolve(strict=True)
    require(output.is_absolute() and output.is_relative_to(scratch) and output != scratch
            and output.parent.resolve(strict=True) == output.parent
            and all(not output.is_relative_to(phase.plan_path.parents[2]) for phase in (cpu, hip)),
            'split admission output must be a new directory under host scratch outside both native packets')
    candidate = plan['spec']['candidate']
    provenance = {'git_commit': C13}
    production = planner.production_runtime_dirs()
    for backend, image in plan['images'].items():
        require(image == planner.verify_stage(candidate[backend], candidate, backend, production),
                f'{backend} stage bytes differ from the prepared image')
        field = 'llama_server_path' if backend == 'cpu' else 'hip_llama_server_path'
        provenance[field] = image['binary']
        provenance[f'{backend}_binary_sha256'] = image['binary_sha256']
    times = {'acquisition_started_at': first.custody['acquisition_started_at'],
             'acquisition_finished_at': last.custody['acquisition_finished_at']}
    health = last.custody['host_after'].copy()
    probes = [probe for phase in (first, last) for probe in (phase.custody['host_before']['health'], phase.custody['host_after'])]
    for key in ('warnings', 'structural_for_harness'):
        health[key] = list(dict.fromkeys(item for probe in probes for item in probe[key]))
    source = planner.ORCHESTRATOR / runner.MATRIX_CONFIG
    pinned_bytes(source, hip.custody['source_matrix']['sha256'])
    emitted = matrix._emit_yaml(cpu.records + hip.records, topology_hash=plan['topology_hash'], binary=provenance,
                                host=health['hostname'], host_health=health,
                                preserve_sections=matrix._carry_forward_sections(source))
    with tempfile.TemporaryDirectory(prefix='.split-matrix-', dir=output.parent) as temp:
        directory = Path(temp)
        path = directory / 'contention_matrix.yaml'
        path.write_text(stamp_acquisition_start(emitted, times))
        # The pinned canonical freshness gate uses mtime. Give it the native
        # lower bound so packaging or running the merger cannot renew the cells.
        os.utime(path, (first.interval[0].timestamp(), first.interval[0].timestamp()))
        validated = validate_full(path, plan, matrix, config, contention)
        require(validated['host_health']['decision_grade'] is True, 'canonical YAML lost the admitted host-health stamp')
        report = {'schema': SPLIT_SCHEMA, 'status': 'admitted', 'authority': 'isolated_observation',
                  'candidate_commit': C13, 'orchestrator_commit': ORCHESTRATOR_PIN,
                  'topology_hash': plan['topology_hash'], 'required_pairs': plan['required_pairs'],
                  'measured_at': times['acquisition_started_at'], 'phases': {'cpu': cpu.custody, 'hip': hip.custody},
                  'matrix': validated | {'path': path.name}}
        report_path = directory / 'admission.json'
        planner.write_new(report_path, report)
        output.mkdir(mode=0o700)
        try:
            os.link(report_path, output / report_path.name)
            os.link(path, output / path.name)
        except OSError:
            (output / report_path.name).unlink(missing_ok=True)
            output.rmdir()
            raise
    return report


def matrix_row_id(phase):
    return f'v9-8-contention-matrix-{phase}-20261118'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=Path)
    parser.add_argument('--phase', choices=tuple(RAM))
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare', action='store_true')
    action.add_argument('--validate-plan', action='store_true')
    action.add_argument('--acquire', action='store_true')
    action.add_argument('--dry-run-result', type=Path)
    action.add_argument('--merge-split', action='store_true', help='admit complete native CPU and HIP results offline')
    for phase in ('cpu', 'hip'):
        parser.add_argument(f'--{phase}-result', type=Path)
        parser.add_argument(f'--{phase}-result-sha256')
        parser.add_argument(f'--{phase}-plan-sha256')
        parser.add_argument(f'--{phase}-source-sha256', help='publisher-bound SHA-256 of the original SOURCE.sha256')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args(argv)
    pins = [(getattr(args, f'{phase}_result'), getattr(args, f'{phase}_result_sha256'),
             getattr(args, f'{phase}_plan_sha256'), getattr(args, f'{phase}_source_sha256')) for phase in ('cpu', 'hip')]
    if args.merge_split:
        if args.packet or args.phase or not args.output_dir or not all(all(pin) for pin in pins):
            parser.error('--merge-split requires two result paths, their result, plan and source SHA-256 pins, and --output-dir')
        try:
            merge_split(*pins, args.output_dir)
        except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, ImportError,
                subprocess.SubprocessError) as exc:
            print(f'split matrix admission refused: {exc}', file=sys.stderr)
            return 2
        print(args.output_dir / 'admission.json')
        return 0
    if not args.packet or not args.phase or args.output_dir or any(any(pin) for pin in pins):
        parser.error('native modes require --packet and --phase. Split inputs require --merge-split')
    packet = args.packet.resolve(strict=True)
    phase = args.phase
    row_id = matrix_row_id(phase)
    if args.prepare:
        print(prepare(packet, phase))
        return 0
    if args.validate_plan:
        _, digest, plan, *_ = read_prepared(packet, phase)
        print(f'{phase}: {len(plan["phase_pairs"])} configured-primary pairs from six required, plan SHA {digest}')
        return 0
    if args.dry_run_result:
        require(os.environ.get('FILLER_DRYRUN') == '1', 'dry-run results require keeper dry-run mode')
        planner.write_new(args.dry_run_result, {'unit_id': row_id, 'status': 'plumbing_only'})
        return 0
    acquisition.require_live_grant(row_id, os.environ)
    out = packet / phase / 'out'
    directory = out / uuid.uuid4().hex
    directory.mkdir(mode=0o700)
    result = capture(packet, phase, row_id, directory)
    result['capture_dir'] = str(directory)
    logs = out.parent / 'prepared/logs'
    try:
        result['attempt_files_sha256'] = attempt_inventory(directory)
        result['server_logs_sha256'] = {'path': str(logs), 'files': attempt_inventory(logs)}
    except (OSError, ValueError) as exc:
        result.update(status='failed', complete_matrix=False, inventory_failure=f'{type(exc).__name__}: {exc}')
    planner.write_new(out / 'RESULT.json', result)
    return 0 if result['status'] == 'captured' else 78


if __name__ == '__main__':
    sys.exit(main())
