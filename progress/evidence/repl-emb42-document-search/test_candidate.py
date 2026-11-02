import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

p = Path(__file__).with_name('repl_document.candidate.py')
spec = importlib.util.spec_from_file_location('repl_document_candidate', p)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
from src.models.document import Section
from src.repl_environment.context_search import DenseResult

class Dense:
    model_id = 'fake'
    def embed(self, texts, **kwargs):
        return DenseResult(np.tile(np.array([[1., 0.]], dtype=np.float32), (len(texts), 1)), self.model_id)

def make(**kwargs):
    sections = [Section('s1', 'First', 1, 'apricot text'), Section('s2', 'Second', 2, 'pear text')]
    dc = mod.DocumentContext(sections, [], 1, [], '/doc')
    text = '# First\napricot text\n\n## Second\npear text\n'
    return mod.DocumentREPLEnvironment('Question: # First\napricot text\n\n' + text, dc, **kwargs), text

def test_opt_in_returns_resolvable_pointers_and_hybrid():
    repl, text = make(document_search_enabled=True, document_search_embedder=Dense())
    hits = repl._search_sections('pear')
    assert hits and all(h['mode'] == 'hybrid' for h in hits)
    for hit in hits:
        assert repl._peek(n=hit['end']-hit['start'], offset=hit['start']) == repl.context[hit['start']:hit['end']]
        assert hit['start'] >= len(repl.context) - len(text)
        assert hit['line'] == repl.context.count('\n', 0, hit['start']) + 1
    assert 'pear' in repl._peek(n=hits[0]['end']-hits[0]['start'], offset=hits[0]['start'])

def test_bundle_refuses_before_search_or_read():
    repl, _ = make(document_search_enabled=True)
    repl._context_bundle = object()
    with pytest.raises(ValueError, match='context bundle'):
        repl._search_sections('pear')
    assert repl._document_search_index is None

def test_opt_out_preserves_existing_search_format():
    repl, _ = make()
    hits = repl._search_sections('pear')
    assert hits == [{'section': 2, 'title': 'Second', 'matches': 1, 'pages': '1-1'}]

def test_mismatched_document_refuses_and_lexical_mode():
    repl, _ = make(document_search_enabled=True, document_search_embedder=None)
    assert repl._search_sections('pear')[0]['mode'] == 'lexical'
    repl.context += ' changed'
    with pytest.raises(ValueError, match='context suffix'):
        repl._search_sections('pear')


def test_default_embedder_resolves_pool_per_search(monkeypatch):
    from src.repl_environment import context_search
    calls = []
    monkeypatch.setattr(context_search, "pool_dense_embedder", lambda: calls.append(1) or Dense())
    repl, _ = make(document_search_enabled=True)
    assert repl._search_sections("pear")[0]["mode"] == "hybrid"
    assert repl._search_sections("pear")[0]["mode"] == "hybrid"
    assert calls == [1, 1]
