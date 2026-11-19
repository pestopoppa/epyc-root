#!/usr/bin/env python3
"""Stage the pinned quantizer inputs BEFORE requesting a compute grant.

The private snapshot is independent of the shared staging tree. Its archive pin
was established by regenerating git archive from the pinned source commit here.
"""
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

from verify_source import file_digest, verify

COMMIT = '7cdd7c97bed538a85c3b75331b6cdb369e5b2adc'
ARCHIVE_SHA = 'cc9c5831b6622dd2fbc5aa85387c70b998af100276e1cd6c0dac3174bbfadff6'
MANIFEST_SHA = '0fa8259e744e4db07ca4e7efbf78e85806ddb50acde135981f05ba0ca31205b0'
ROOT = Path('/mnt/raid0/llm/tmp/inf75-quantizer-7cdd7c97-20261102')
STAGED = Path('/mnt/raid0/llm/tmp/autokernel-cross-workload-keep-gate/quantizer-source')
REPO = Path('/mnt/raid0/llm/tmp/inf70/retest1wt')


def prepare(root=ROOT, staged=STAGED, repo=REPO, smoke=False):
    runs = root / 'runs'
    runs.mkdir(parents=True, exist_ok=True)
    pointer = root / ('PREPARED-SMOKE.json' if smoke else 'PREPARED.json')
    if pointer.exists():
        raise ValueError('prepared run already exists; refuse to replace it')
    run = Path(tempfile.mkdtemp(prefix='build-', dir=runs))
    try:
        # Generate from the object database, never the mutable checkout.
        with (run / 'source.tar').open('wb') as stream:
            subprocess.run(['git', '-C', str(repo), 'archive', '--format=tar', COMMIT],
                           stdout=stream, check=True)
        if file_digest(run / 'source.tar') != ARCHIVE_SHA:
            raise ValueError('commit archive differs from trusted pin')
        shutil.copyfile(staged / 'tree-manifest.json', run / 'tree-manifest.json')
        (run / 'src').mkdir()
        with tarfile.open(run / 'source.tar') as archive:
            archive.extractall(run / 'src', filter='data')
        verify(run / 'src', run / 'tree-manifest.json', MANIFEST_SHA)
        (run / 'build').mkdir()
        (run / 'output').mkdir()
        provenance = dict(source_commit=COMMIT, archive_sha256=ARCHIVE_SHA,
                          manifest_sha256=MANIFEST_SHA, method='git archive from pinned commit',
                          source_dir=str(run / 'src'), run_dir=str(run),
                          source_device=(run/'src').stat().st_dev,
                          source_inode=(run/'src').stat().st_ino,
                          protection='root-owned tree; all write bits removed after verification')
        (run / 'source-provenance.json').write_text(json.dumps(provenance, sort_keys=True) + '\n')
        run.chmod(0o755)
        # Keep build writable by the worker; protect all source and custody
        # metadata from ordinary same-UID writers. Root remains trusted.
        subprocess.run(['sudo', '-n', 'chown', '-R', 'root:root', str(run/'src')], check=True)
        subprocess.run(['sudo', '-n', 'chmod', '-R', 'a-w', str(run/'src')], check=True)
        for path in (run/'source.tar', run/'tree-manifest.json', run/'source-provenance.json', run):
            subprocess.run(['sudo', '-n', 'chown', 'root:root', str(path)], check=True)
            subprocess.run(['sudo', '-n', 'chmod', 'a-w', str(path)], check=True)
        with pointer.open('x') as stream:
            json.dump(provenance, stream, sort_keys=True)
            stream.write('\n')
        return run
    except BaseException:
        subprocess.run(['sudo', '-n', 'rm', '-rf', '--', str(run)], check=False)
        raise


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke', action='store_true')
    print(prepare(smoke=parser.parse_args().smoke))
