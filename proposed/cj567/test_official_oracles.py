"""Original source controls using frozen official predicates; no model calls."""
import ast
import copy
import json
import os
from pathlib import Path
import socket
import urllib.request
import pytest
from ifbench_fixture import load_corpus, validate_corpus, NLTK_RESOURCES
from cj_edit_fixture import SOURCE_FUNCTION

@pytest.fixture(autouse=True)
def deny_oracle_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('network denied during official oracle controls')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket.socket, 'connect_ex', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(urllib.request, 'urlopen', denied)
    import nltk
    monkeypatch.setattr(nltk, 'download', denied)


def test_real_official_population_and_registry():
    rows = load_corpus(Path(os.environ['CJ567_OFFICIAL']) / 'data/IFBench_test.jsonl')
    validate_corpus(rows)
    from ifbench import instructions_registry
    counts = [item for row in rows for item in row['instruction_id_list']]
    assert len(rows) == 300 and len(counts) == 344 and len(set(counts)) == 58
    assert set(counts) <= set(instructions_registry.INSTRUCTION_DICT)


def test_official_strict_oracle_accepts_and_rejects_actual_pinned_item():
    import evaluation_lib as official
    rows = load_corpus(Path(os.environ['CJ567_OFFICIAL']) / 'data/IFBench_test.jsonl')
    row = rows[0]
    assert row['instruction_id_list'] == ['count:keywords_multiple']
    args = row['kwargs'][0]
    response = ' '.join(args['keyword'+str(i)] for i, count in enumerate([1, 2, 3, 5, 7], 1) for _ in range(count))
    def observe(answer):
        return official.test_instruction_following_strict(official.InputExample(**copy.deepcopy(row)), {row['prompt']: answer})
    assert observe(response).follow_all_instructions is True
    assert observe(response.replace(args['keyword1'], '')).follow_all_instructions is False


def test_all_four_seed_resources_ready_without_download():
    import nltk
    for resource in NLTK_RESOURCES:
        assert nltk.data.find(resource)
    assert nltk.sent_tokenize('One sentence. Another sentence.') == ['One sentence.', 'Another sentence.']
    assert nltk.pos_tag(['simple', 'test'])


def test_inverse_fixture_literal_matches_pinned_real_beam_source():
    path = Path(os.environ['CJ567_RESEARCH']) / 'scripts/benchmark/beam_scoring.py'
    raw = path.read_text()
    tree = ast.parse(raw)
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_mean']
    assert len(functions) == 1
    actual = ast.get_source_segment(raw, functions[0]) + '\n'
    assert actual == SOURCE_FUNCTION
