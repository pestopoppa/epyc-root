"""Receipt-gated release of pinned sources. No recursive deletion or model execution.

Call only after acquisition/conversion have stopped; exclusive directory flock
coordinates cooperating callers. Retained receipts are evidence inputs, not a
replacement for the native tensor/tokenizer verifier that produces them.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat

import acquisition as acq

NAMESPACES = (Path('/mnt/raid0/llm/tmp/df2'), Path('/dev/shm/df2'))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def identity(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'single-link regular file required')
        sha, git = hashlib.sha256(), hashlib.sha1()
        git.update(f'blob {before.st_size}\0'.encode())
        while chunk := stream.read(acq.CHUNK):
            sha.update(chunk)
            git.update(chunk)
        after = os.fstat(stream.fileno())
        require(signature(before) == signature(after), 'file changed during verification')
    return dict(size=before.st_size, sha256=sha.hexdigest(), git_blob_sha1=git.hexdigest()), before


def signature(s):
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink


def release_sources(raw_plan, task_root, source, controls, acquisition_ref, conversion_ref, event):
    """Validate every input before the first unlink; retain a durable intent first.

    Refuse retries after any published intent, including partial release. Such a
    receipt requires explicit recovery; it must never be mistaken for completion.
    """
    task = acq.safe_directory(task_root)
    require(any(task != ns and ns in task.parents for ns in NAMESPACES), 'df2 task namespace required')
    source, controls = acq.safe_directory(source), acq.safe_directory(controls)
    require(source.parent == task and controls.parent == task and source != controls,
            'separate direct task-owned source/control directories required')
    event = Path(event).absolute()
    require(event.parent == controls and not event.exists() and not event.is_symlink(), 'fresh retained event required')
    plan = json.loads(raw_plan)
    sources = acq.source_list(plan)
    plan_sha = hashlib.sha256(raw_plan).hexdigest()

    def receipt(ref):
        require(set(ref) == {'path', 'sha256'}, 'content-bound receipt required')
        p = Path(ref['path']).absolute()
        require(p.parent == controls and p != event, 'receipt must remain in controls')
        ident, _ = identity(p)
        require(ident['size'] <= acq.EVENT_CAP and ident['sha256'] == ref['sha256'], 'receipt digest/size mismatch')
        fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            raw = stream.read(acq.EVENT_CAP+1)
        require(hashlib.sha256(raw).hexdigest() == ref['sha256'], 'receipt changed during read')
        result = json.loads(raw)
        require(result.get('status') == 'COMPLETE' and result.get('plan_sha256') == plan_sha,
                'complete plan-bound receipt required')
        return result

    directory = os.open(source, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fcntl.flock(directory, fcntl.LOCK_EX | fcntl.LOCK_NB)
        directory_stat = os.fstat(directory)
        acquired, converted = receipt(acquisition_ref), receipt(conversion_ref)
        require(acquired.get('worker_reaped') is True and acquired.get('worker_returncode') == 0,
                'reaped successful acquisition required')
        require(converted.get('schema') == 'epyc.target-precision.conversion.v1'
                and converted.get('acquisition') == acquisition_ref and converted.get('base') == plan['base']
                and converted.get('source_root') == str(source), 'conversion provenance mismatch')
        require(converted.get('tensor_correspondence') == 'verified'
                and converted.get('tokenizer_correspondence') == 'verified', 'full correspondence required')
        build = receipt(converted['build'])
        require(build.get('source_commit') == plan['converter_commit'], 'converter commit mismatch')
        for ref in (converted['tensor_report'], converted['tokenizer_report']):
            report = receipt(ref)
            require(report.get('verdict') == 'PASS' and report.get('output') == converted['output']
                    and report.get('acquisition') == acquisition_ref, 'correspondence report binding mismatch')
        output = converted['output']
        output_path = Path(output['path']).absolute()
        require(task in output_path.parents and source not in output_path.parents
                and controls not in output_path.parents, 'retained task output required')
        acq.safe_directory(output_path.parent)
        ident, _ = identity(output_path)
        require(output.get('quant') == 'BF16' and ident['sha256'] == output['sha256']
                and ident['size'] == output['size'], 'BF16 output mismatch')
        # Preserve tool and log bytes, not merely their labels in a receipt.
        for key in ('tool', 'log'):
            ref = build[key] if key == 'tool' else converted[key]
            p = Path(ref['path']).absolute()
            require(source not in p.parents and p != source, 'retained tool/log required')
            acq.safe_directory(p.parent)
            ident, _ = identity(p)
            require(ident['sha256'] == ref['sha256'], 'tool/log digest mismatch')
        require(set(os.listdir(directory)) == {s['path'] for s in sources}, 'source inventory mismatch')
        require(len(acquired.get('files', [])) == len(sources), 'acquisition inventory mismatch')
        checked = []
        for s, record in zip(sources, acquired['files']):
            ident, st = identity(source/s['path'])
            require(record.get('source') == s and record.get('path') == str(source/s['path'])
                    and record.get('size') == s['size'] == ident['size']
                    and record.get('sha256') == ident['sha256'], 'source receipt mismatch')
            key = 'sha256' if 'sha256' in s else 'git_blob_sha1'
            require(ident[key] == s[key], 'pinned source mismatch')
            checked.append((s['path'], st))
        result = dict(status='RELEASING', plan_sha256=plan_sha, acquisition=acquisition_ref,
                      conversion=conversion_ref, removed=[], verified_weights=False)
        # Exclusive durable journal precedes any destructive operation.
        with event.open('x') as journal:
            def save():
                journal.seek(0)
                journal.write(json.dumps(result, sort_keys=True)+'\n')
                journal.truncate()
                journal.flush()
                os.fsync(journal.fileno())
            save()
            parent_fd = os.open(controls, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
            try:
                for name, before in checked:
                    current_dir = os.stat(source, follow_symlinks=False)
                    require((current_dir.st_dev, current_dir.st_ino) ==
                            (directory_stat.st_dev, directory_stat.st_ino), 'source directory moved')
                    require(signature(os.stat(name, dir_fd=directory, follow_symlinks=False)) == signature(before),
                            'source changed before unlink')
                    os.unlink(name, dir_fd=directory)
                    os.fsync(directory)
                    result['removed'].append(name)
                    save()
                result['status'] = 'RELEASED'
            except Exception as exc:
                result.update(status='FAILED', error=str(exc))
                raise
            finally:
                save()
        return result
    finally:
        os.close(directory)
