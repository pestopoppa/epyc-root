"""The surviving card resolves the champion; a loop's seeded row cannot define it."""
from __future__ import annotations
from pathlib import Path
import subprocess

from dashboard import loop_status


def _tree(path, branch):
    subprocess.run(['git', 'init', '-q', '-b', branch, str(path)], check=True)
    subprocess.run(['git', '-C', str(path), '-c', 'user.name=t', '-c', 'user.email=t@t',
                    'commit', '-qm', 'original synthetic champion', '--allow-empty'], check=True)
    return subprocess.run(['git', '-C', str(path), 'rev-parse', 'HEAD'], check=True,
                          capture_output=True, text=True).stdout.strip()


def test_a_champion_ahead_of_production_is_never_called_equal_to_it(tmp_path, monkeypatch):
    tree = tmp_path / 'champion'
    anchor = _tree(tree, 'ak/champion/test')
    subprocess.run(['git', '-C', str(tree), '-c', 'user.name=t', '-c', 'user.email=t@t',
                    'commit', '-qm', 'admitted work', '--allow-empty'], check=True)
    monkeypatch.setenv(loop_status.CHAMPION_TREE_ENV, str(tree))
    view = loop_status.champion_snapshot(root=tmp_path,
        production={'resolved': True, 'commit': anchor, 'branch': 'production-consolidated-v10'})
    assert view['champion']['branch_tip'] != anchor
    assert view['measured'] is False
    assert view['effect_fraction'] is None


def test_a_champion_identical_to_production_says_so(tmp_path, monkeypatch):
    tree = tmp_path / 'champion'
    anchor = _tree(tree, 'ak/champion/test')
    monkeypatch.setenv(loop_status.CHAMPION_TREE_ENV, str(tree))
    view = loop_status.champion_snapshot(root=tmp_path,
        production={'resolved': True, 'commit': anchor, 'branch': 'production-consolidated-v10'})
    assert view['champion']['branch_tip'] == view['production']['commit']
    assert view['effect_fraction'] is None  # identity is never a measured speedup


def test_no_instrument_pin_reports_none_rather_than_inventing_one(tmp_path, monkeypatch):
    monkeypatch.setenv(loop_status.CHAMPION_TREE_ENV, str(tmp_path / 'absent'))
    view = loop_status.champion_snapshot(root=tmp_path)
    assert view['champion']['branch_tip'] is None
    assert view['champion']['tip_error']
    assert view['measured'] is False


def test_the_champion_is_not_derived_from_this_campaigns_banked_rows(tmp_path, monkeypatch):
    tree = tmp_path / 'champion'
    actual = _tree(tree, 'ak/champion/test')
    monkeypatch.setenv(loop_status.CHAMPION_TREE_ENV, str(tree))
    view = loop_status.champion_snapshot(root=tmp_path, champion_head='0' * 40)
    assert view['champion']['branch_tip'] == actual
    assert view['champion']['loop_champion_head'] == '0' * 40
    assert view['measured'] is False and view['capabilities']['known'] is False
