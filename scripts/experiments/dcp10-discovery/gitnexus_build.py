"""Prospectively seal and build private DCP-10 indexes under allocator admission.

No build is run by importing this module or preparing its request. The caller
must provide allocator STOP/deadline enforcement via remaining(cap).
"""
from __future__ import annotations

import os
import shutil
import signal
import stat
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import gitnexus_native as native

SCHEMA = 'epyc.dcp10.gitnexus-build-request.v2'
WORKER = Path(__file__).with_name('gitnexus_build_worker.mjs').resolve()
TIMEOUT = 1800


# Shared scratch is allowed for request bookkeeping only. Docker bind sources
# use the stricter native.check_custody policy with no shared-ancestor exception.
SHARED_TMP = Path('/mnt/raid0/llm/tmp')


def check_build_path(path):
    if path.resolve(strict=True) != path:
        raise native.IsolationError('noncanonical build path')
    for component in (path, *path.parents):
        info = component.lstat()
        if component == SHARED_TMP:
            if info.st_uid != os.geteuid() or not stat.S_ISDIR(info.st_mode):
                raise native.IsolationError('unexpected shared scratch owner/type')
            continue
        if (info.st_uid not in (0, os.geteuid()) or info.st_mode & 0o022
                or (stat.S_ISREG(info.st_mode) and info.st_nlink != 1)):
            raise native.IsolationError(f'untrusted build path: {component}')


@contextmanager
def pinned_mounts(paths):
    """Use daemon-resolvable names under trusted ancestry, never proc-fd mounts.

    Descriptors detect replacement; they are not Docker mount sources. Both the
    daemon and caller must resolve the same ordinary paths. The custody check
    excludes peer-writable ancestors throughout the container's lifetime.
    """
    descriptors = {}

    def verify_names():
        for path, fd in descriptors.items():
            native.check_custody(path)
            named, pinned = path.stat(), os.fstat(fd)
            if (named.st_dev, named.st_ino) != (pinned.st_dev, pinned.st_ino):
                raise native.IsolationError('mount path changed while pinned')

    try:
        for path in paths:
            native.check_custody(path)
            fd = os.open(path, os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC)
            # Avoid losing a descriptor if the same source serves two targets.
            if path in descriptors:
                os.close(fd)
                continue
            descriptors[path] = fd
        verify_names()
        try:
            yield {path: path for path in descriptors}
        finally:
            verify_names()
    finally:
        for fd in descriptors.values():
            os.close(fd)


def inventory(root):
    """Bind all installed transitive modules/native parsers, including internal links."""
    entries = {}
    for path in sorted(root.rglob('*')):
        name = path.relative_to(root).as_posix()
        if path.is_symlink():
            if not path.resolve(strict=True).is_relative_to(root):
                raise ValueError('package link escapes the mounted source')
            entries[name] = {'link': os.readlink(path)}
        elif path.is_file():
            entries[name] = {'sha256': native.common.hash_file(path)}
        elif not path.is_dir():
            raise ValueError('package contains a special file')
    if not entries:
        raise ValueError('empty installed source')
    return entries


def producer_identity():
    return {**native.producer_identity(), Path(__file__).name: native.common.hash_file(Path(__file__)),
            WORKER.name: native.common.hash_file(WORKER)}


def write_new(path, value):
    with path.open('x') as stream:
        stream.write(native.pilot.encode(value) + '\n')
    return native.common.hash_file(path)


def task_binding(task):
    root = native.WORK / 'bases' / task['language']
    binding = {'root': str(root), 'base_commit': task['base_commit'],
               'base_tree': native.pilot.git(root, 'rev-parse', 'HEAD^{tree}'),
               'query_sha256': native.sha256(task['query'].encode()).hexdigest()}
    native.graph.bind_task(native.WORK, task, binding)
    return binding


def mount_binding(task, base, host_root):
    """Validate an independent Git worktree of the exact original base.

    Host placement is a transport detail. The worker, metadata and receipt keep
    the original logical path. Reuse the cohort's clean-tree/read-scope checks
    against a conventional <private-root>/bases/<language> host layout.
    """
    root = Path(host_root)
    native.check_custody(root)
    native.graph.bind_task(root.parent.parent, task, {**base, 'root': str(root)})
    return str(root)


def mount_layout(tasks, bindings, mount_bases):
    if not isinstance(mount_bases, dict) or set(mount_bases) != set(tasks):
        raise ValueError('mount layout must bind exactly the original tasks')
    return {key: mount_binding(task, bindings[key], mount_bases[key])
            for key, task in tasks.items()}


def prepare(assets, mount_bases=None):
    """Seal original identities plus explicitly validated host worktree paths."""
    check_build_path(assets)
    if assets.stat().st_mode & 0o077 or list(assets.iterdir()):
        raise ValueError('build assets must be empty and private')
    native.seal_file(native.NODE, native.NODE_SHA)
    tasks = native.original_tasks()
    bindings = {key: task_binding(task) for key, task in tasks.items()}
    if mount_bases is None:
        mount_bases = {key: base['root'] for key, base in bindings.items()}
    request = {'schema': SCHEMA, 'producer_sha256': producer_identity(),
               'gitnexus_source': native.writer_identity(), 'runtime': native.runtime_identity(),
               'source_inventory': inventory(native.graph.SOURCE_ROOT), 'tasks': bindings,
               'mount_bases': mount_layout(tasks, bindings, mount_bases)}
    return write_new(assets / 'build-request.json', request)


def launch_config(docker, name, output, base, timeout, pins=None, mount_base=None):
    mounts = [(native.graph.SOURCE_ROOT, str(native.graph.SOURCE_ROOT)),
              (mount_base if mount_base is not None else Path(base['root']), base['root']),
              (native.NODE.parent, '/dcp10/runtime'), (WORKER.parent, '/dcp10/producer')]
    pins = pins or {}
    mounts = [(pins.get(path, path), target) for path, target in mounts]
    command = native.launch_config(docker, name, mounts, timeout)
    command[-2:] = ['/dcp10/runtime/node', '/dcp10/producer/gitnexus_build_worker.mjs']
    command = [item.replace(",bind-recursive=readonly", ",bind-recursive=readonly,bind-propagation=rprivate")
               for item in command]
    for old, new in (('--cpus=1', '--cpus=4'), ('--memory=2g', '--memory=8g'),
                     ('--memory-swap=2g', '--memory-swap=8g'), ('--pids-limit=64', '--pids-limit=256')):
        command[command.index(old)] = new
    if any(char in str(output) for char in ',\n\r"'):
        raise native.IsolationError('unsupported build output path')
    command[-6:-6] = ['--mount', f'type=bind,src={pins.get(output, output)},dst=/dcp10/output',
                      '--tmpfs', '/tmp:rw,nosuid,nodev,size=1g',
                      '--tmpfs', '/dcp10/empty-home:rw,nosuid,nodev,size=64m']
    return command


def build_private_index(assets, request_sha, task_id, remaining):
    """One admitted build. No retries, fallback, source copying or shared writes."""
    remaining(TIMEOUT)
    check_build_path(assets / 'build-request.json')
    request = native.read_record(assets / 'build-request.json', request_sha, max_bytes=32 * 1024**2)
    tasks = native.original_tasks()
    if task_id not in tasks or set(request.get('tasks', {})) != set(tasks):
        raise ValueError('build task outside original cohort')

    def snapshot():
        writer = native.writer_identity()
        bindings = {key: task_binding(task) for key, task in tasks.items()}
        expected = {'schema': SCHEMA, 'producer_sha256': producer_identity(), 'gitnexus_source': writer,
                    'runtime': native.runtime_identity(), 'source_inventory': inventory(native.graph.SOURCE_ROOT),
                    'tasks': bindings,
                    'mount_bases': mount_layout(tasks, bindings, request.get('mount_bases'))}
        if request != expected:
            raise ValueError('prospective build source/base/request drift')
        for path in (native.graph.SOURCE_ROOT, native.NODE, WORKER):
            check_build_path(path)
        native.seal_file(native.NODE, native.NODE_SHA)
        return writer

    writer = snapshot()
    language = tasks[task_id]['language']
    output = assets / f'work-{language}'
    output.mkdir(mode=0o700)  # existing/failed attempts cannot be overwritten
    check_build_path(output)
    base = request['tasks'][task_id]
    command, result = run_isolated(output, base, remaining(TIMEOUT), snapshot,
                                   mount_base=Path(request['mount_bases'][task_id]))
    remaining(TIMEOUT)
    index = output / 'index'
    if {path.name for path in output.iterdir()} != {'index'}:
        raise ValueError('unexpected build output')
    if {path.name for path in index.iterdir()} != {'lbug', 'meta.json'}:
        raise ValueError('private build has uncheckpointed sidecars')
    for path in index.iterdir():
        check_build_path(path)
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError('nonregular build output')
    receipts = assets / 'index-builds'
    receipts.mkdir(exist_ok=True, mode=0o700)
    receipt = receipts / f'{language}.json'
    manifest_sha = write_new(receipt.with_suffix('.manifest.json'), {
        'schema': SCHEMA, 'request_sha256': request_sha, 'task_id': task_id,
        'command': command, 'stdout_sha256': native.sha256(result.stdout).hexdigest(),
        'stderr_sha256': native.sha256(result.stderr).hexdigest(), 'returncode': result.returncode,
        'base': base, 'mount_base': request['mount_bases'][task_id], 'producer_sha256': request['producer_sha256']})
    record = {'schema': native.INDEX_BUILD_SCHEMA, 'task_id': task_id, 'base': base,
              'gitnexus_source': writer, 'build_manifest_sha256': manifest_sha,
              'files': {path.name: native.common.hash_file(path) for path in index.iterdir()}}
    receipt_sha = write_new(receipt, record)
    native.index_identity(index, receipt, receipt_sha, task_id=task_id, base=base, writer=writer)
    indexes = assets / 'indexes'
    indexes.mkdir(exist_ok=True, mode=0o700)
    index.rename(indexes / language)
    output.rmdir()
    return receipt_sha


def run_isolated(output, base, timeout, verify, mount_base=None):
    """One bounded private writer invocation, shared by native smoke and cohort."""
    name = f'dcp10-gitnexus-build-{uuid4().hex}'
    docker = shutil.which('docker')
    if docker is None or os.geteuid() == 0:
        raise native.IsolationError('build requires Docker and a non-root caller')
    if type(timeout) not in (int, float) or not 0.001 <= timeout <= TIMEOUT:
        raise ValueError('invalid build time budget')
    env = {'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent', 'LANG': 'C.UTF-8',
           'DOCKER_HOST': 'unix:///var/run/docker.sock', 'DOCKER_CONFIG': '/run/dcp10-no-docker-config'}
    mount_base = mount_base if mount_base is not None else Path(base['root'])
    previous = signal.signal(signal.SIGTERM, native._stop_on_term)
    try:
        with pinned_mounts([native.graph.SOURCE_ROOT, mount_base, native.NODE.parent, WORKER.parent, output]) as pins:
            # Snapshot after custody/identity checks; descriptors stay open until
            # container cleanup and a second custody/identity check complete.
            verify()
            command = launch_config(docker, name, output, base, timeout, pins, mount_base=mount_base)
            try:
                result = native.read_bounded(command, env, native.pilot.encode(
                    {'source': str(native.graph.SOURCE_ROOT), 'base': base}).encode(), timeout + 5)
            finally:
                native.remove_container(docker, name, env)
        if result.returncode or result.stderr:
            raise native.QueryError(f'private build rc={result.returncode}; diagnostics={result.stderr[-2048:]!r}; no receipt admitted')
    finally:
        signal.signal(signal.SIGTERM, previous)
        verify()
    return command, result
