from __future__ import annotations

import sys


def test_seed_loader_accepts_init_flag(monkeypatch) -> None:
    from orchestration.repl_memory import seed_loader

    calls: list[dict[str, bool]] = []
    monkeypatch.setattr(seed_loader, "seed_memory", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(sys, "argv", ["seed_loader.py", "--init"])

    seed_loader.main()

    assert calls == [{"force": False, "init": True}]


def test_seed_loader_force_still_clears(monkeypatch) -> None:
    from orchestration.repl_memory import seed_loader

    calls: list[dict[str, bool]] = []
    monkeypatch.setattr(seed_loader, "seed_memory", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(sys, "argv", ["seed_loader.py", "--force"])

    seed_loader.main()

    assert calls == [{"force": True, "init": False}]
