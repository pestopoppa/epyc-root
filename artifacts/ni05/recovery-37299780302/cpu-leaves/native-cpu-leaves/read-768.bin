"""Unit tests for scripts/benchmark/seeding_tui.py."""

from __future__ import annotations

import importlib.util
import logging
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from rich.layout import Layout
from rich.panel import Panel


_ROOT = Path(__file__).resolve().parents[2] / "scripts" / "benchmark"
sys.path.insert(0, str(_ROOT))
_SPEC = importlib.util.spec_from_file_location("seeding_tui_test", _ROOT / "seeding_tui.py")
_MOD = importlib.util.module_from_spec(_SPEC)
sys.modules["seeding_tui_test"] = _MOD
_SPEC.loader.exec_module(_MOD)


class _Conv:
    def convert(self, text: str) -> str:
        if text in {"bad", r"\beta"}:
            raise RuntimeError("bad token")
        return f"U({text})"


def test_sanitize_display_removes_invisible_unicode():
    raw = "a\u200bb\u2060c\ufeffd"
    assert _MOD._sanitize_display(raw) == "abcd"


def test_latex_to_unicode_returns_original_when_converter_absent(monkeypatch):
    monkeypatch.setattr(_MOD, "_get_latex_converter", lambda: None)
    line = r"hello $x^2$ and \alpha"
    assert _MOD._latex_to_unicode(line) == line


def test_get_latex_converter_import_success_cache_and_importerror(monkeypatch):
    sentinel = object()

    class _Flat:
        @staticmethod
        def converter():
            return sentinel

    monkeypatch.setitem(sys.modules, "flatlatex", _Flat())
    _MOD._flatlatex_converter = None
    assert _MOD._get_latex_converter() is sentinel
    assert _MOD._get_latex_converter() is sentinel

    _MOD._flatlatex_converter = None
    monkeypatch.delitem(sys.modules, "flatlatex", raising=False)
    import builtins
    orig_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "flatlatex":
            raise ImportError("missing")
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    assert _MOD._get_latex_converter() is None


def test_latex_conversion_and_inline_error_fallback(monkeypatch):
    monkeypatch.setattr(_MOD, "_get_latex_converter", lambda: _Conv())
    line = r"pre $x$ and \[bad\] and \alpha"
    out = _MOD._latex_to_unicode(line)
    assert "U(x)" in out
    assert r"\[bad\]" in out
    assert r"U(\alpha)" in out


def test_latex_to_unicode_handles_empty_match_group(monkeypatch):
    monkeypatch.setattr(_MOD, "_get_latex_converter", lambda: _Conv())
    monkeypatch.setattr(_MOD, "_LATEX_INLINE_RE", _MOD.re.compile(r"()|()|()|()"))
    assert _MOD._latex_to_unicode("abc") == "abc"


def test_convert_bare_latex_handles_success_and_token_failure(monkeypatch):
    monkeypatch.setattr(_MOD, "_get_latex_converter", lambda: _Conv())
    line = r"\left \alpha and \beta with x_{1}"
    out = _MOD._convert_bare_latex(line)
    assert r"U(\alpha)" in out
    assert r"\beta" in out
    assert "U(x_{1})" in out


def test_convert_bare_latex_short_circuits_for_none_converter_and_no_command(monkeypatch):
    monkeypatch.setattr(_MOD, "_get_latex_converter", lambda: None)
    assert _MOD._convert_bare_latex("plain text") == "plain text"
    monkeypatch.setattr(_MOD, "_get_latex_converter", lambda: _Conv())
    assert _MOD._convert_bare_latex("plain text") == "plain text"


def test_deque_handler_emit_success_and_failure_paths():
    handler = _MOD.DequeHandler(maxlen=2)
    handler.setFormatter(logging.Formatter("%(message)s"))
    rec = logging.LogRecord("test", logging.INFO, __file__, 10, "hello", (), None)

    handler.emit(rec)
    assert list(handler.records) == ["hello"]

    handler.handleError = Mock()
    handler.format = Mock(side_effect=ValueError("format failure"))
    handler.emit(rec)
    handler.handleError.assert_called_once_with(rec)


def test_taptailer_process_chunk_semantic_break_wrap_and_role_cycle():
    tailer = _MOD.TapTailer("/tmp/unused.tap", max_lines=100)

    tailer._process_chunk("=" * 20 + "\nROLE=architect\nhello")
    assert tailer.get_current_section() == ["=" * 20, "ROLE=architect", "hello"]
    assert tailer.get_role_chain() == ["architect"]

    tailer._process_chunk("WORLDFINAL(answer)")
    lines = tailer.get_current_section()
    assert lines[-2] == "helloWORLD"
    assert lines[-1].startswith("FINAL(")

    tailer._process_chunk("\nROLE=coder")
    assert tailer.get_role_chain() == ["architect", "coder"]

    tailer._process_chunk("\nROLE=architect")
    assert tailer.get_role_chain() == ["architect"]

    tailer._process_chunk(" " + ("x" * 80), wrap_width=20)
    assert any(len(x) <= 20 for x in tailer.get_current_section()[-5:])

    tailer.reset_role_chain()
    tailer.reset_section()
    assert tailer.get_role_chain() == []
    assert tailer.get_current_section() == []
    assert tailer.get_current_section(tail=1) == []


def test_taptailer_start_stop_and_semantic_break_empty():
    tailer = _MOD.TapTailer("/tmp/unused.tap", max_lines=10)
    tailer._semantic_break_last_line()  # empty-path early return

    fake_thread = SimpleNamespace(start=Mock(), join=Mock())
    with patch.object(_MOD.threading, "Thread", return_value=fake_thread) as thread_ctor:
        tailer.start()
    thread_ctor.assert_called_once()
    fake_thread.start.assert_called_once()

    tailer._thread = fake_thread
    tailer.stop()
    fake_thread.join.assert_called_once_with(timeout=2.0)


def test_taptailer_run_waits_for_file_then_returns_if_stopped(monkeypatch):
    class _Stop:
        def __init__(self, states):
            self._states = iter(states)
            self.wait_calls = []

        def is_set(self):
            return next(self._states)

        def wait(self, v):
            self.wait_calls.append(v)

    tailer = _MOD.TapTailer("/tmp/never.tap")
    stop = _Stop([False, True, True])
    tailer._stop = stop
    monkeypatch.setattr(_MOD.os.path, "exists", lambda _: False)
    tailer._run()
    assert stop.wait_calls == [0.5]


def test_taptailer_run_reads_and_polls_when_no_data(monkeypatch):
    class _Stop:
        def __init__(self, states):
            self._states = iter(states)
            self.wait_calls = []

        def is_set(self):
            return next(self._states)

        def wait(self, v):
            self.wait_calls.append(v)

    class _FH:
        def __init__(self):
            self._reads = [b"abc", b""]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def seek(self, *_args):
            return 0

        def tell(self):
            return 0

        def read(self, _n):
            return self._reads.pop(0)

    tailer = _MOD.TapTailer("/tmp/fake.tap", poll_interval=0.2)
    stop = _Stop([False, False, False, False, True])
    tailer._stop = stop
    monkeypatch.setattr(_MOD.os.path, "exists", lambda _: True)
    monkeypatch.setattr("builtins.open", lambda *_a, **_k: _FH())
    tailer._process_chunk = Mock()
    tailer._run()
    tailer._process_chunk.assert_called_once()
    assert stop.wait_calls == [0.2]


def test_style_helpers_cover_stream_and_repl_markers(monkeypatch):
    monkeypatch.setattr(_MOD, "_latex_to_unicode", lambda s: s.replace("$x$", "x"))

    stream = _MOD._style_stream_lines(
        [
            "=" * 20,
            "PROMPT: hidden",
            "RESPONSE:",
            "```python",
            "x = 1",
            "```",
            "FINAL(done)",
            "regular $x$",
        ]
    )
    plain = stream.plain
    assert "PROMPT: hidden" in plain
    assert "FINAL(done)" in plain
    assert "regular x" in plain

    repl = _MOD._style_repl_lines(
        [
            "[turn 1] $ python",
            "def f():",
            "    return 1",
            "Traceback (most recent call last)",
            "[turn 2] FINAL(answer)",
        ]
    )
    rplain = repl.plain
    assert "[turn 1] $ python" in rplain
    assert "Traceback" in rplain
    assert "FINAL(answer)" in rplain


def test_style_helpers_cover_additional_stream_and_repl_paths():
    stream = _MOD._style_stream_lines(
        [
            "TIMINGS: x",
            "[1] ROLE=frontdoor",
        ]
    )
    assert "TIMINGS: x" in stream.plain
    assert "ROLE=frontdoor" in stream.plain

    repl = _MOD._style_repl_lines(
        [
            "[turn 3] ERROR boom",
            "[turn 4] (no output)",
            "[turn 5] note",
            "CODE block starts",
            "    indented line",
            "plain text",
        ]
    )
    plain = repl.plain
    assert "ERROR boom" in plain
    assert "(no output)" in plain
    assert "CODE block starts" in plain
    assert "plain text" in plain


def test_update_progress_resets_sections_and_role_chain():
    tui = _MOD.SeedingTUI(session_id="s")
    tui._tailer = SimpleNamespace(
        reset_role_chain=Mock(),
        reset_section=Mock(),
    )
    tui._repl_tailer = SimpleNamespace(reset_section=Mock())

    tui.update_progress(1, 10, "suite", "q1", action="a1", question="q")
    tui._tailer.reset_role_chain.assert_called_once()
    tui._tailer.reset_section.assert_called_once()
    tui._repl_tailer.reset_section.assert_called_once()

    tui.update_progress(2, 10, "suite", "q1", action="a1", question="q")
    assert tui._tailer.reset_role_chain.call_count == 1
    assert tui._tailer.reset_section.call_count == 1

    tui.update_progress(3, 10, "suite", "q1", action="a2", question="q")
    assert tui._tailer.reset_role_chain.call_count == 2
    assert tui._tailer.reset_section.call_count == 1


def test_make_layout_renders_expected_panels_and_filters_prompt():
    tui = _MOD.SeedingTUI(session_id="sess")
    tui._progress.current_index = 2
    tui._progress.total_questions = 5
    tui._progress.current_suite = "suiteA"
    tui._progress.current_qid = "q42"
    tui._progress.current_action = "act"
    tui._progress.current_question = "line1\nline2"
    tui._progress.start_time = time.monotonic() - 10
    tui._deque_handler.records.append("log line")

    tui._tailer = SimpleNamespace(
        get_current_section=lambda: [
            "=" * 20,
            "PROMPT:",
            "secret prompt line",
            "-" * 20,
            "RESPONSE:",
            "hello world",
            "FINAL(done)",
        ],
        get_role_chain=lambda: ["architect", "coder"],
    )
    tui._repl_tailer = SimpleNamespace(
        get_current_section=lambda: ["[turn 1] $ python", "print(1)"]
    )

    layout = tui._make_layout()
    assert isinstance(layout, Layout)

    header = layout["header"].renderable
    assert "suiteA/q42" in header.plain
    assert "sess" in header.plain

    stream_panel = layout["stream"].renderable
    assert isinstance(stream_panel, Panel)
    assert stream_panel.title.startswith("Inference (")
    assert "architect" in stream_panel.title
    assert "coder" in stream_panel.title
    stream_text = stream_panel.renderable.plain
    assert "PROMPT: [...]" in stream_text
    assert "secret prompt line" not in stream_text
    assert "FINAL(done)" in stream_text

    question_panel = layout["question"].renderable
    assert isinstance(question_panel, Panel)
    assert question_panel.title == "suiteA/q42"


def test_make_layout_wrap_scroll_hidden_code_and_empty_repl(monkeypatch):
    tui = _MOD.SeedingTUI(session_id="sess")
    tui._console = SimpleNamespace(width=50, height=16)
    tui._progress.current_suite = "suiteB"
    tui._progress.current_qid = "q99"
    tui._progress.current_question = "p1\np2\np3\np4"
    tui._progress.start_time = 0.0
    monkeypatch.setattr(_MOD.time, "monotonic", lambda: 8.0)
    tui._deque_handler.records.append("X" * 200)

    long_stream = ["```hidden"] + [f"line-{i}" for i in range(20)] + ["PROMPT:", "hidden", "-" * 20, "RESPONSE:", "ok"]
    tui._tailer = SimpleNamespace(
        get_current_section=lambda: long_stream,
        get_role_chain=lambda: [],
    )
    tui._repl_tailer = SimpleNamespace(get_current_section=lambda: [])

    layout = tui._make_layout()
    assert isinstance(layout["log"].renderable, Panel)
    assert isinstance(layout["question"].renderable, Panel)
    assert "(no REPL activity)" in layout["repl"].renderable.renderable.plain


def test_make_layout_question_blank_paragraph_branch():
    tui = _MOD.SeedingTUI(session_id="sess")
    tui._console = SimpleNamespace(width=80, height=20)
    tui._progress.current_question = "line1\n\nline2"
    tui._tailer = SimpleNamespace(get_current_section=lambda: [], get_role_chain=lambda: [])
    tui._repl_tailer = SimpleNamespace(get_current_section=lambda: [])

    layout = tui._make_layout()
    q_plain = layout["question"].renderable.renderable.plain
    assert "line1" in q_plain
    assert "line2" in q_plain


def test_make_layout_uses_dimension_fallback_on_console_errors():
    class _BrokenConsole:
        @property
        def width(self):
            raise RuntimeError("no width")

        @property
        def height(self):
            raise RuntimeError("no height")

    tui = _MOD.SeedingTUI(session_id="sess")
    tui._console = _BrokenConsole()
    tui._tailer = SimpleNamespace(get_current_section=lambda: [], get_role_chain=lambda: [])
    tui._repl_tailer = SimpleNamespace(get_current_section=lambda: [])

    layout = tui._make_layout()
    assert isinstance(layout, Layout)
    assert isinstance(layout["log"].renderable, Panel)
    assert isinstance(layout["stream"].renderable, Panel)


def test_sentinel_repl_tap_and_cleanup(tmp_path, monkeypatch):
    sentinel = tmp_path / ".inference_tap_active"
    tap = tmp_path / "tap.log"
    repl = tmp_path / "repl.log"

    monkeypatch.setattr(_MOD, "_SENTINEL_PATH", str(sentinel))

    class _Console:
        def __init__(self):
            self.called = False

        def set_alt_screen(self, *_):
            self.called = True

    tui = _MOD.SeedingTUI(session_id="sess", tap_path=str(tap), repl_tap_path=str(repl))
    tui._console = _Console()

    tui._write_sentinel()
    assert sentinel.read_text() == str(tap)

    repl.write_text("old")
    tui._truncate_repl_tap()
    assert repl.read_text() == ""

    tap.write_text("x")
    tui._cleanup()
    assert not sentinel.exists()
    assert not tap.exists()
    assert not repl.exists()
    assert tui._console.called is True


def test_file_ops_swallow_os_errors(monkeypatch, tmp_path):
    sentinel = tmp_path / ".inference_tap_active"
    tap = tmp_path / "tap.log"
    repl = tmp_path / "repl.log"
    monkeypatch.setattr(_MOD, "_SENTINEL_PATH", str(sentinel))
    tui = _MOD.SeedingTUI(session_id="sess", tap_path=str(tap), repl_tap_path=str(repl))
    tui._console = SimpleNamespace(set_alt_screen=Mock(side_effect=RuntimeError("console fail")))

    with patch.object(_MOD.Path, "mkdir", side_effect=OSError("mkdir fail")):
        tui._write_sentinel()
        tui._truncate_repl_tap()

    with patch.object(_MOD.os, "unlink", side_effect=[FileNotFoundError(), OSError("busy"), FileNotFoundError()]):
        tui._cleanup()


def test_context_manager_enter_and_exit_restore_logging(monkeypatch):
    class _FakeLive:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.started = False
            self.stopped = False

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

    monkeypatch.setattr(_MOD, "Live", _FakeLive)
    monkeypatch.setattr(_MOD.atexit, "register", Mock())

    tui = _MOD.SeedingTUI(session_id="sess")
    tui._write_sentinel = Mock()
    tui._truncate_repl_tap = Mock()
    tui._cleanup = Mock()
    tui._tailer.start = Mock()
    tui._tailer.stop = Mock()
    tui._repl_tailer.start = Mock()
    tui._repl_tailer.stop = Mock()

    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    try:
        with tui as entered:
            assert entered is tui
            assert isinstance(tui._live, _FakeLive)
            assert tui._live.started is True
            assert root.handlers == [tui._deque_handler]
            assert root.level == logging.INFO

        tui._tailer.stop.assert_called_once()
        tui._repl_tailer.stop.assert_called_once()
        tui._cleanup.assert_called_once()
        assert root.handlers == saved_handlers
        assert root.level == saved_level
    finally:
        root.handlers.clear()
        for h in saved_handlers:
            root.addHandler(h)
        root.setLevel(saved_level)


def test_exit_swallow_live_stop_exception():
    tui = _MOD.SeedingTUI(session_id="sess")
    tui._live = SimpleNamespace(stop=Mock(side_effect=RuntimeError("stop fail")))
    tui._tailer.stop = Mock()
    tui._repl_tailer.stop = Mock()
    tui._cleanup = Mock()

    assert tui.__exit__(None, None, None) is False
    tui._tailer.stop.assert_called_once()
    tui._repl_tailer.stop.assert_called_once()
    tui._cleanup.assert_called_once()
