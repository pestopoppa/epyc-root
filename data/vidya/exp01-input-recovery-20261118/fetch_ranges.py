"""Fill disjoint verified ranges for the pinned EXP01 source in a resumable file."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen
import os
import sys
import time


SIZE = 36914690368
WORKERS = 16
BLOCK = 128 << 20


def fetch(src: Path, url: str) -> None:
    prefix = Path(str(src) + '.part')
    output = Path(str(src) + '.ranges')
    state = src.parent / 'range-recovery'
    state.mkdir(exist_ok=True)
    origin = state / 'prefix'
    if not origin.is_file():
        count = prefix.stat().st_size if prefix.is_file() else 0
        if not 0 <= count <= SIZE:
            raise ValueError('invalid contiguous prefix length')
        with origin.open('x') as stream:
            stream.write(f'{count}\n')
    count = int(origin.read_text())
    if prefix.is_file() and not output.exists():
        prefix.rename(output)
    if count and not output.is_file():
        raise ValueError('saved prefix bytes missing')
    with output.open('r+b' if output.exists() else 'x+b') as stream:
        fd = stream.fileno()
        os.ftruncate(fd, SIZE)

        def download(start):
            end = min(start + BLOCK, SIZE) - 1
            done = state / f'done-{start}-{end}'
            if done.is_file():
                return
            offset = start
            tries = 0
            while offset <= end:
                request = Request(f'{url}?exp01_range_start={offset}', headers={
                    'Accept-Encoding': 'identity', 'Range': f'bytes={offset}-{end}'})
                try:
                    with urlopen(request, timeout=45) as response:
                        if (response.status != 206
                                or response.headers.get('Content-Range') != f'bytes {offset}-{end}/{SIZE}'
                                or int(response.headers['Content-Length']) != end - offset + 1):
                            raise ValueError(f'invalid server range response at {offset}')
                        while offset <= end:
                            block = memoryview(response.read(min(end - offset + 1, 2 << 20)))
                            if not block:
                                raise OSError('truncated HTTP range')
                            while block:
                                wrote = os.pwrite(fd, block, offset)
                                if wrote <= 0:
                                    raise OSError('zero-byte write')
                                offset += wrote
                                block = block[wrote:]
                except OSError as exc:
                    tries += 1
                    if tries >= 5:
                        raise
                    print(f'retrying {offset}-{end}: {exc}', flush=True)
                    time.sleep(tries)
            complete = done.with_suffix('.tmp')
            complete.write_text(f'{start}-{end}\n')
            complete.replace(done)
            print(f'validated {start}-{end}', flush=True)

        if count < SIZE:
            with ThreadPoolExecutor(max_workers=WORKERS) as pool:
                for _ in pool.map(download, range(count, SIZE, BLOCK)):
                    pass
        os.fsync(fd)
    output.rename(src)


if __name__ == '__main__':
    fetch(Path(sys.argv[1]), sys.argv[2])
