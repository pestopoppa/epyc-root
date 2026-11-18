#!/usr/bin/env python3
"""Acquire configured-primary contention pairs through owned, isolated listeners."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import uuid

SOURCE = Path(__file__).resolve().parent
sys.path.insert(0, str(SOURCE))

import kernel_promotion_contention_acquire as acquisition

runner = acquisition.runner
planner = runner.planner
require = planner.require
SCHEMA = 'epyc.kernel_promotion_matrix_capture.v1'
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


def canonical_modules(packet, spec):
    root = packet / 'orchestrator'
    require(root == root.resolve(strict=True) and spec['orchestrator_commit'] == ORCHESTRATOR_PIN
            and planner.git(root, 'rev-parse', 'HEAD') == ORCHESTRATOR_PIN
            and not planner.git(root, 'branch', '--show-current')
            and not planner.git(root, 'status', '--porcelain', '--untracked-files=all'),
            'canonical modules require the clean detached orchestrator checkout')
    planner.ORCHESTRATOR = root
    planner.check_stack_inputs(spec)
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


def read_prepared(packet, phase):
    path = runner.canonical_file(packet / phase / 'prepared/plan.json')
    require(path.parent.stat().st_mode & 0o077 == 0, 'prepared plan must be private')
    digest = (path.parent / 'plan.sha256').read_text().strip()
    planner.check_pin(path, digest)
    plan = planner.read_json(path)
    require(plan['schema'] == SCHEMA and plan['phase'] == phase and plan['spec']['candidate']['source_commit'] == C13,
            'prepared plan phase or C13 identity changed')
    matrix, config, contention = canonical_modules(packet, plan['spec'])
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
            source_matrix={'repo_commit': ORCHESTRATOR_PIN, 'path': runner.MATRIX_CONFIG,
                           'sha256': plan['spec']['config_sha256'][runner.MATRIX_CONFIG],
                           'measured_at': plan['source_matrix_measured_at'],
                           'status_at_prepare': plan['source_matrix_status_at_prepare']},
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
    return {str(path.relative_to(directory)): planner.digest(runner.canonical_file(path))
            for path in sorted(directory.rglob('*')) if path.is_file() or path.is_symlink()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--phase', choices=tuple(RAM), required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare', action='store_true')
    action.add_argument('--validate-plan', action='store_true')
    action.add_argument('--acquire', action='store_true')
    action.add_argument('--dry-run-result', type=Path)
    args = parser.parse_args()
    packet = args.packet.resolve(strict=True)
    phase = args.phase
    row_id = f'v9-8-contention-matrix-{phase}-20261118'
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
