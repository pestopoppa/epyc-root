"""Synthetic checks for the unapplied document-in-bundle candidate."""
import importlib.util
import sys
from pathlib import Path

import pytest
from src.models.document import Section
from src.repl_environment.context_bundle import ContextBundle, ContextPullBudgetExceeded

p = Path(__file__).with_name('repl_document.bundle-candidate.py')
spec = importlib.util.spec_from_file_location('bundle_document_candidate', p)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
TEXT = '# First\napricot text\n\n## Second\npear text\n'


def make(bundle_sections, budget=None):
    sections = [Section('s1', 'First', 1, 'apricot text'), Section('s2', 'Second', 2, 'pear text')]
    dc = mod.DocumentContext(sections, [], 1, [], '/doc')
    repl = mod.DocumentREPLEnvironment('Question\n\n' + TEXT, dc,
                                       document_search_enabled=True, document_search_embedder=None)
    bundle = ContextBundle.from_payload({'sections': bundle_sections}, pull_budget_bytes=budget)
    repl.attach_context_bundle(bundle)
    return repl, bundle


def test_pointers_use_exact_bundle_section_and_count_actual_utf8_pull():
    repl, bundle = make([{'name': 'other', 'text': 'not the document'}, {'name': 'doc', 'text': TEXT}])
    hits = repl._search_sections('pear')
    assert hits and bundle.accounting()['totals']['pull_calls'] == 0
    hit = hits[0]
    assert hit['source'] == 'context_bundle' and hit['bundle_section'] == 'doc' and hit['read'] == 'context.get'
    value = bundle.get(hit['bundle_section'], offset=hit['start'], max_chars=hit['end']-hit['start'])
    assert value == TEXT[hit['start']:hit['end']] and 'pear' in value
    totals = bundle.accounting()['totals']
    assert totals['pull_calls'] == 1 and totals['bytes_pulled'] == len(value.encode())


def test_budget_applies_to_follow_read():
    repl, bundle = make([{'name': 'doc', 'text': TEXT}], budget=1)
    hit = repl._search_sections('pear')[0]
    with pytest.raises(ContextPullBudgetExceeded):
        bundle.get(hit['bundle_section'], offset=hit['start'], max_chars=hit['end']-hit['start'])
    assert bundle.accounting()['totals']['bytes_pulled'] == 0


@pytest.mark.parametrize('items', [[{'name':'other', 'text':'wrong'}],
                                   [{'name':'doc1', 'text':TEXT}, {'name':'doc2', 'text':TEXT}]])
def test_missing_or_ambiguous_exact_document_refuses_without_pulls(items):
    repl, bundle = make(items)
    with pytest.raises(ValueError, match='exactly one exact document'):
        repl._search_sections('pear')
    assert bundle.accounting()['totals']['pull_calls'] == 0


def test_multichunk_unicode_pointers_round_trip_through_view_and_account_bytes():
    from src.repl_environment.context_bundle import repl_view

    content = ('αβγ filler\n' * 100) + 'uniquequince 漢字\n'
    sections = [Section('s', 'Unicode', 1, content)]
    text = '# Unicode\n' + content + '\n'
    dc = mod.DocumentContext(sections, [], 1, [], '/doc')
    repl = mod.DocumentREPLEnvironment('Question\n\n' + text, dc,
                                       document_search_enabled=True, document_search_embedder=None)
    bundle = ContextBundle.from_payload({'sections': [{'name': 'doc', 'text': text}]})
    repl.attach_context_bundle(bundle)
    hits = repl._search_sections('uniquequince')
    assert hits and any('uniquequince' in text[h['start']:h['end']] for h in hits)
    view = repl_view(bundle)
    total = 0
    for hit in hits:
        value = view.get(hit['bundle_section'], offset=hit['start'], max_chars=hit['end'] - hit['start'])
        assert value == text[hit['start']:hit['end']]
        assert hit['line'] == text.count('\n', 0, hit['start']) + 1
        total += len(value.encode('utf-8'))
    assert bundle.accounting()['totals']['bytes_pulled'] == total
    assert total > sum(h['end'] - h['start'] for h in hits)


def test_bundle_document_section_accessor_cannot_bypass_pull_budget():
    repl, bundle = make([{'name': 'doc', 'text': TEXT}], budget=1)
    with pytest.raises(ValueError, match=r'use context.get'):
        repl._section(1)
    assert bundle.accounting()['totals']['bytes_pulled'] == 0
    hit = repl._search_sections('pear')[0]
    with pytest.raises(ContextPullBudgetExceeded):
        bundle.get(hit['bundle_section'], offset=hit['start'], max_chars=hit['end']-hit['start'])


def test_legacy_section_accessor_remains_available_with_opt_in_disabled():
    repl, bundle = make([{'name': 'doc', 'text': TEXT}])
    repl._document_search_enabled = False
    assert 'apricot text' in repl._section(1)
    assert bundle.accounting()['totals']['pull_calls'] == 0


def test_state_advertises_accounted_reads_only_for_bundle_opt_in():
    repl, _ = make([{'name': 'doc', 'text': TEXT}])
    state = repl.get_state()
    assert 'context.get(bundle_section' in state
    assert 'context: bundle view' in state
    assert 'section(n): Get section' not in state
    repl._document_search_enabled = False
    state = repl.get_state()
    assert 'section(n): Get section' in state
    assert 'context: str' in state
    assert 'context.get(bundle_section' not in state
