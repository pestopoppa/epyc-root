"""Prospective KPF-50 no-redraw marker primitive; not integrated with the runner."""
import json, os, re, stat
from pathlib import Path

ORDER = ('full-a', 'mask-a', 'mask-b', 'full-b')

def begin(directory, window, run_id, validate_prior=None):
    """Durably record exposure before the caller is allowed to issue a request.

    Every existing start is terminal for this identity, even after a crash. The
    caller must retain this directory for the lifetime of the whole lineage.
    """
    if window not in ORDER or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', run_id):
        raise ValueError('invalid window or run identity')
    root = Path(directory)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    dfd = os.open(root, flags)
    try:
        for other in ORDER:
            try:
                st = os.stat(other + '.start.json', dir_fd=dfd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(st.st_mode):
                raise ValueError('non-regular exposure marker')
            if other == window:
                raise FileExistsError('window already exposed or begun')
        for prior in ORDER[:ORDER.index(window)]:
            try:
                st = os.stat(prior + '.complete.json', dir_fd=dfd, follow_symlinks=False)
            except FileNotFoundError as exc:
                raise ValueError('prior window incomplete') from exc
            if not stat.S_ISREG(st.st_mode):
                raise ValueError('non-regular completion marker')
            if validate_prior is None or validate_prior(dfd, prior, run_id) is not True:
                raise ValueError('prior completion not independently validated')
        name = window + '.start.json'
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600, dir_fd=dfd)
        try:
            payload = (json.dumps({'schema':'kpf50.window-start.v1','window':window,'run_id':run_id}, sort_keys=True)+'\n').encode()
            view = memoryview(payload)
            while view:
                n = os.write(fd, view)
                if n <= 0: raise OSError('short marker write')
                view = view[n:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(dfd)
    finally:
        os.close(dfd)
