"""Read or write within /testbed without following symlink path components."""
import base64
import os
import sys


def execute(root, mode, path, encoded=''):
    parts = path.split('/')
    if mode not in ('read', 'write') or not parts or any(p in ('', '.', '..') for p in parts):
        raise ValueError('invalid testbed path')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(root, flags)
    try:
        for part in parts[:-1]:
            if mode == 'write':
                try:
                    os.mkdir(part, mode=0o755, dir_fd=fd)
                except FileExistsError:
                    pass
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        if mode == 'read':
            file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
            with os.fdopen(file_fd, 'rb') as f:
                return f.read()
        data = base64.b64decode(encoded, validate=True)
        file_fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o644, dir_fd=fd)
        with os.fdopen(file_fd, 'wb') as f:
            f.write(data)
        return b''
    finally:
        os.close(fd)


if __name__ == '__main__':
    sys.stdout.buffer.write(execute('/testbed', *sys.argv[1:]))
