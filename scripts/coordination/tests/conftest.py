"""Suite-wide spawn isolation (INC-20260806-test-spawned-codex): no coordination test may reach the operator's real tmux
server or the real codex/claude/opencode binaries. Every test runs with a private tmux socket (-L) and record-only stub
binaries first on PATH; handoff_sessions.refuse_real_spawn_under_test() is the in-code backstop."""
import os
import shutil
import tempfile

import pytest


@pytest.fixture(autouse=True)
def _no_real_tmux_or_engines(monkeypatch):
    d = tempfile.mkdtemp(prefix="hs-stubs-")
    for b in ("tmux", "codex", "claude", "opencode"):
        p = os.path.join(d, b)
        with open(p, "w") as f:
            f.write("#!/bin/sh\necho \"%s $*\" >> \"%s/invoked\"\nexit 1\n" % (b, d))
        os.chmod(p, 0o755)
    monkeypatch.setenv("PATH", d + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.setenv("HS_TMUX_SOCKET", "hs-test-%d" % os.getpid())
    monkeypatch.setenv("TMUX_TMPDIR", d)
    yield
    shutil.rmtree(d, ignore_errors=True)
