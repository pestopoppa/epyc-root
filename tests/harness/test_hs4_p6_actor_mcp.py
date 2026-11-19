"""Actor-shaped requests exercised through the actual isolated FastMCP server."""
import asyncio
import os
from pathlib import Path
import sys

import pytest

fastmcp = pytest.importorskip('fastmcp')
CHECKOUT = Path(os.environ.get('HS4_P6_ORCHESTRATOR_ROOT', '/mnt/raid0/llm/epyc-orchestrator'))
if not (CHECKOUT / 'src/repl_environment/exploration_core.py').is_file():
    pytest.skip('pinned exploration core required', allow_module_level=True)
sys.path.insert(0, str(CHECKOUT))
from src.repl_environment import exploration_core as core
from scripts.harness import hs4_p6_actor_mcp as actor


@pytest.fixture
def seat(tmp_path):
    root = tmp_path / 'worktree'
    root.mkdir()
    (root / 'sample.py').write_text('def hello():\n    return 42\n')
    server = fastmcp.FastMCP('actor-candidate')
    actor.register_actor_tools(server, root, core=core)
    return server, root


def call(seat, name, **arguments):
    async def run():
        async with fastmcp.Client(seat[0]) as client:
            return await client.call_tool(name, arguments, raise_on_error=False)
    return asyncio.run(run())


def test_actor_catalog_requires_no_per_call_root(seat):
    async def run():
        async with fastmcp.Client(seat[0]) as client:
            tools = {t.name: t.inputSchema for t in await client.list_tools()}
            assert set(tools) == {'read_range', 'grep', 'outline', 'code_search'}
            assert tools['grep']['required'] == ['pattern']
            assert tools['grep']['properties']['path']['default'] == '.'
            assert tools['grep']['properties']['context']['default'] == 0
            assert tools['code_search']['properties']['k']['default'] == 6
            for schema in tools.values():
                assert 'root' not in schema['properties']
                assert schema['additionalProperties'] is False
    asyncio.run(run())
    assert call(seat, 'grep', pattern='hello', root='/').is_error


@pytest.mark.parametrize('name,kwargs', [
    ('read_range', {'path': 'sample.py'}), ('outline', {'path': 'sample.py'}),
    ('grep', {'pattern': 'hello'}), ('code_search', {'query': 'hello'}),
])
def test_actor_requests_and_optional_stamps_return_text(seat, name, kwargs):
    plain = call(seat, name, **kwargs)
    stamped = call(seat, name, session_id='actor_stamp', **kwargs)
    assert not plain.is_error and not stamped.is_error
    assert plain.content[0].text == stamped.content[0].text
    assert isinstance(plain.content[0].text, str)


def test_read_and_outline_delegate_to_shared_core(seat):
    root = str(seat[1])
    assert call(seat, 'read_range', path='sample.py').content[0].text == core.read_range(root, 'sample.py')
    assert call(seat, 'outline', path='sample.py').content[0].text == core.outline_file(root, 'sample.py')


def test_directory_grep_handles_nested_files_context_and_case(seat):
    root = seat[1]
    (root / 'nested').mkdir()
    (root / 'nested/hit.txt').write_text('before\nneedle\nafter\nNEEDLE\n')
    out = call(seat, 'grep', pattern='needle', context=1)
    assert not out.is_error
    text = out.content[0].text
    assert 'nested/hit.txt:2: needle' in text
    assert 'nested/hit.txt:1- before' in text
    assert 'nested/hit.txt:3- after' in text
    assert 'nested/hit.txt:4:' not in text
    assert '[1 match(es)]' in text


@pytest.mark.parametrize('name,kwargs', [
    ('read_range', {}), ('outline', {}), ('grep', {'pattern': 'secret'}),
])
@pytest.mark.parametrize('path', ['../secret.py', 'link.py'])
def test_actor_path_escape_refused(seat, name, kwargs, path):
    (seat[1].parent / 'secret.py').write_text('secret = 1')
    (seat[1] / 'link.py').symlink_to(seat[1].parent / 'secret.py')
    assert call(seat, name, path=path, **kwargs).is_error


def test_directory_grep_never_follows_links_or_special_files(seat):
    root = seat[1]
    (root.parent / 'secret.py').write_text('secret')
    (root / 'escape').symlink_to(root.parent, target_is_directory=True)
    (root / 'binary.py').write_bytes(b'secret\x00')
    os.mkfifo(root / 'pipe.py')
    text = call(seat, 'grep', pattern='secret').content[0].text
    assert 'no matches' in text and 'coverage incomplete' in text
    assert 'secret.py:' not in text and 'binary.py:' not in text


def test_grep_hit_and_scan_limits_report_partial_coverage(seat, monkeypatch):
    (seat[1] / 'many.txt').write_text(('needle ' * 200 + '\n') * 250)
    result = call(seat, 'grep', pattern='needle', path='many.txt', max_hits=999)
    text = result.content[0].text
    assert sum(': needle' in line for line in text.splitlines()) == 80
    assert 'truncated' in text
    assert all(len(line.split(': ', 1)[1]) <= 240 for line in text.splitlines() if ': needle' in line)
    monkeypatch.setattr(actor, 'MAX_TOTAL_BYTES', 1)
    assert 'truncated' in call(seat, 'grep', pattern='needle').content[0].text
    monkeypatch.setattr(actor, 'MAX_ENTRIES', 1)
    assert 'truncated' in call(seat, 'grep', pattern='needle').content[0].text


@pytest.mark.parametrize('pattern', ['', '['])
def test_invalid_pattern_is_error_even_for_empty_directory(seat, pattern):
    (seat[1] / 'empty').mkdir()
    assert call(seat, 'grep', pattern=pattern, path='empty').is_error


def test_search_labels_semantic_difference_and_preserves_actor_k_cap(seat):
    for i in range(15):
        (seat[1] / f'hit{i}.py').write_text('needle')
    text = call(seat, 'code_search', query='needle', k=999).content[0].text
    assert '[root-lexical]' in text
    assert sum('  lines ' in line for line in text.splitlines()) == 10
    assert 'paths + line ranges only' in text


@pytest.mark.parametrize('root', ['.', '/does-not-exist'])
def test_actor_launch_root_must_be_absolute_and_existing(root):
    with pytest.raises(ValueError):
        actor.register_actor_tools(fastmcp.FastMCP('bad'), root, core=core)


@pytest.fixture
def legacy_actor():
    research = Path(os.environ.get('HS4_P6_RESEARCH_ROOT', '/mnt/raid0/llm/epyc-inference-research'))
    source = research / 'scripts/kernel_rnd/autokernel/loop/actor_tools_mcp.py'
    if not source.is_file():
        pytest.skip('native actor source required for differential contracts')
    sys.path.insert(0, str(research / 'scripts/kernel_rnd'))
    from autokernel.loop import actor_tools_mcp
    return actor_tools_mcp


def test_native_actor_read_header_and_rows_match(seat, legacy_actor):
    (seat[1] / 'lines.py').write_text(''.join(f'line {i}\n' for i in range(30)))
    old = legacy_actor.read_range(str(seat[1]), 'lines.py', 10, 3)
    new = call(seat, 'read_range', path='lines.py', start_line=10, num_lines=3).content[0].text
    # Continuation prose differs, but line units/header/content retain their contract.
    assert new.splitlines()[:4] == old.splitlines()[:4]
    assert 'continue with start_line=13' in new


def test_native_actor_single_file_grep_hits_match(seat, legacy_actor):
    old = legacy_actor.grep(str(seat[1]), 'hello', path='sample.py', _rg=None)
    new = call(seat, 'grep', pattern='hello', path='sample.py').content[0].text
    assert new == old


def test_native_actor_python_outline_definition_locations_match(seat, legacy_actor):
    old = legacy_actor.outline(str(seat[1]), 'sample.py')
    new = call(seat, 'outline', path='sample.py').content[0].text
    assert [line for line in new.splitlines() if line.startswith('L')] == [
        line for line in old.splitlines() if line.startswith('L')]


@pytest.mark.parametrize('tool,arguments', [
    ('read_range', {'path': 'binary.py'}), ('outline', {'path': 'binary.py'}),
    ('grep', {'pattern': 'needle', 'path': 'binary.py'}),
])
def test_actor_binary_input_refused(seat, tool, arguments):
    (seat[1] / 'binary.py').write_bytes(b'needle\x00def secret():\n    pass\n')
    result = call(seat, tool, **arguments)
    assert result.is_error
    assert 'binary' in result.content[0].text


def test_c_family_outline_native_fixture_definitions_match(seat, legacy_actor):
    # Native fixture is loaded in place; no source/fixture copy enters the repository.
    from autokernel.loop.test_actor_tools_mcp import CPP_FIXTURE
    (seat[1] / 'fixture.cpp').write_text(CPP_FIXTURE)
    old = legacy_actor.outline(str(seat[1]), 'fixture.cpp')
    new = call(seat, 'outline', path='fixture.cpp')
    assert not new.is_error
    old_rows = [line for line in old.splitlines() if line.startswith('L')]
    new_rows = [line for line in new.content[0].text.splitlines() if line.startswith('L')]
    assert new_rows == old_rows
    assert any('process' in row for row in new_rows)
    assert any('mul_mat_qX_K' in row for row in new_rows)
    assert not any('prototype_only' in row or 'helper(' in row for row in new_rows)


@pytest.mark.parametrize('source', [
    'namespace n {\nstruct A {\nvoid f() {\n if (true) { other(); }\n}\n};\n}\n',
    '#define FOO(x) ((x)+1)\nextern "C" {\nint f(int n) { return n; }\n}\n',
    '/* fake() { */\nvoid prototype();\ntemplate <class T>\nT actual(T x)\n{ return x; }\n',
    'struct A {\nconst char * f() { return "}"; }\nvoid g() { /* { */ }\n};\n',
])
def test_c_family_differential_edge_cases(seat, legacy_actor, source):
    (seat[1] / 'edge.hpp').write_text(source)
    old = legacy_actor.outline(str(seat[1]), 'edge.hpp')
    new = call(seat, 'outline', path='edge.hpp').content[0].text
    assert [line for line in new.splitlines() if line.startswith('L')] == [
        line for line in old.splitlines() if line.startswith('L')]


def test_candidate_composition_does_not_mutate_base_core(seat):
    from scripts.harness.hs4_p6_shared_core import candidate_core
    original_reader, original_parser = core._read_text, core._outline_c_heuristic
    candidate = candidate_core(core)
    assert candidate_core(candidate) is candidate
    (seat[1] / 'binary.py').write_bytes(b'hello\x00')
    assert '\x00' in core._read_text(str(seat[1]), 'binary.py')[0]
    with pytest.raises(core.ExplorationError, match='binary'):
        candidate._read_text(str(seat[1]), 'binary.py')
    assert core._read_text is original_reader
    assert core._outline_c_heuristic is original_parser


def test_candidate_composition_reads_only_once(seat, monkeypatch):
    from scripts.harness.hs4_p6_shared_core import candidate_core
    original = core._read_text
    reads = []
    def counted(*args, **kwargs):
        reads.append(args)
        return original(*args, **kwargs)
    monkeypatch.setattr(core, '_read_text', counted)
    candidate = candidate_core(core)
    candidate.read_range(str(seat[1]), 'sample.py')
    assert len(reads) == 1
    candidate.outline_file(str(seat[1]), 'sample.py')
    assert len(reads) == 2


def test_missing_or_different_parser_checkout_is_refused(tmp_path, legacy_actor):
    from scripts.harness.hs4_p6_shared_core import load_actor_parser
    with pytest.raises(ValueError, match='native actor'):
        load_actor_parser(tmp_path)
    alternate = tmp_path / 'scripts/kernel_rnd/autokernel/loop'
    alternate.mkdir(parents=True)
    (alternate / 'actor_tools_mcp.py').write_text('# wrong checkout\n')
    with pytest.raises(RuntimeError, match='declared research'):
        load_actor_parser(tmp_path)
