"""Synthetic source-level controls; not an online run."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

path = Path(__file__).with_name('shadow_bridge.py')
spec = importlib.util.spec_from_file_location('shadow_bridge_candidate', path)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class Bundle:
    def __init__(self):
        self.sections = {'doc': SimpleNamespace(name='doc', text='abcdefghij')}

    def _section(self, name):
        return self.sections[name]


def hit(start, end):
    return {'section': 'doc', 'start': start, 'end': end}


def test_default_off_does_not_register_or_call_arms(monkeypatch):
    monkeypatch.delenv('EPYC_REPL_SHADOW_CAPTURE', raising=False)
    b = Bundle()
    assert bridge.configure(b, shown_arm='shown', hidden_arms={'other': lambda *_: []}, sink=lambda _: None) is False
    bridge.search(b, 'query', 1, None, [hit(0, 5)])
    assert not hasattr(b, '_repl_shadow_bridge')


def test_shown_and_counterfactual_are_distinguished(monkeypatch):
    monkeypatch.setenv('EPYC_REPL_SHADOW_CAPTURE', '1')
    b, records, calls = Bundle(), [], []
    def hidden(*args):
        calls.append(args)
        return [hit(3, 8), hit(8, 10)]
    assert bridge.configure(b, shown_arm='shown', hidden_arms={'other': hidden}, sink=records.append)
    shown = [hit(0, 5)]
    bridge.search(b, 'query', 2, None, shown)
    bridge.opened(b, 'doc', 4, 6)
    assert calls == [('query', 2, None)] and shown == [hit(0, 5)]
    record = records[0]
    assert record['arms']['shown'][0]['next_open_overlap'] is True
    assert record['arms']['shown'][0]['interpretation'] == 'shown'
    assert [x['next_open_overlap'] for x in record['arms']['other']] == [True, False]
    assert all(x['interpretation'] == 'counterfactual_span_match' for x in record['arms']['other'])
    assert repr('query') not in repr(record) and 'abcdefghij' not in repr(record)


def test_superseded_search_preserves_unknown(monkeypatch):
    monkeypatch.setenv('EPYC_REPL_SHADOW_CAPTURE', '1')
    b, records = Bundle(), []
    bridge.configure(b, shown_arm='shown', hidden_arms={'other': lambda *_: [hit(1, 2)]}, sink=records.append)
    bridge.search(b, 'q1', 1, None, [hit(0, 1)])
    bridge.search(b, 'q2', 1, None, [hit(0, 1)])
    assert records[0]['opened_at'] is None
    assert records[0]['arms']['shown'][0]['next_open_overlap'] is None
    b._repl_shadow_bridge.close()
    assert records[1]['opened_at'] is None


def test_changed_content_does_not_match(monkeypatch):
    monkeypatch.setenv('EPYC_REPL_SHADOW_CAPTURE', '1')
    b, records = Bundle(), []
    bridge.configure(b, shown_arm='shown', hidden_arms={'other': lambda *_: [hit(0, 1)]}, sink=records.append)
    bridge.search(b, 'q', 1, None, [hit(0, 1)])
    b.sections['doc'].text = 'zyxwvutsrq'
    bridge.opened(b, 'doc', 0, 1)
    assert records[0]['arms']['shown'][0]['next_open_overlap'] is False
