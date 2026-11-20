import hashlib
import os
from pathlib import Path
import subprocess

import pytest
import port

HERE = Path(__file__).parent
REPO = os.environ.get('DTREE_SOURCE_REPO', '/mnt/raid0/llm/llama.cpp-experimental')


@pytest.fixture(scope='module')
def source():
    return subprocess.check_output(['git', '-C', REPO, 'show', port.COMMIT + ':' + port.PATH])


def test_source_binding_and_minimal_change(source):
    assert hashlib.sha256(source).hexdigest() == port.SOURCE_SHA256
    fixed = port.repair(source)
    assert fixed.replace(port.NEW.encode(), port.OLD.encode()) == source
    with pytest.raises(ValueError, match='digest'):
        port.repair(fixed)


@pytest.mark.parametrize('change', [b'X', b'\n\n', b'foreign source'])
def test_refuse_unknown_source(source, change):
    with pytest.raises(ValueError, match='digest'):
        port.repair(source[:-1] + change)


def executable(source, scratch):
    text = source.decode()
    start = text.index('    std::vector<llama_seq_id>   tree_seq_store;')
    end = text.index('    // AK-DTREE-1: no alternative sequence', start)
    resolve = text[start:end]
    start = text.index('            // add accepted tokens to the prompt')
    end = text.index('            SLT_DBG(slot, "add accepted tokens:', start)
    accept = text[start:end]
    harness = (HERE/'regression.cpp').read_text().replace('// INSERT_PINNED_RESOLVE', resolve)
    harness = harness.replace('// INSERT_PINNED_ACCEPT', accept)
    cpp, exe = scratch/'regression.cpp', scratch/'regression'
    cpp.write_text(harness)
    subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=undefined', '-fno-sanitize-recover=all',
                    str(cpp), '-o', str(exe)], check=True, capture_output=True, text=True)
    return subprocess.run([str(exe)], capture_output=True, text=True)


def test_actual_pinned_resolve_accept_regression(source, tmp_path):
    # The same harness must expose the original bug and pass only with the repair.
    old = executable(source, tmp_path)
    assert old.returncode == 1 and 'wrong prefix/next-position' in old.stderr
    fixed = executable(port.repair(source), tmp_path)
    assert fixed.returncode == 0, fixed.stderr
    assert fixed.stdout.strip() == '630 resolve/accept cases passed'


def test_cli_emits_patch_without_editing_input(source, tmp_path):
    original, patch = tmp_path/'source.cpp', tmp_path/'fix.patch'
    original.write_bytes(source)
    subprocess.run(['python3', str(HERE/'port.py'), str(original), str(patch)], check=True)
    assert original.read_bytes() == source
    assert '--- a/' + port.PATH in patch.read_text()
    second = subprocess.run(['python3', str(HERE/'port.py'), str(original), str(patch)], capture_output=True)
    assert second.returncode != 0
