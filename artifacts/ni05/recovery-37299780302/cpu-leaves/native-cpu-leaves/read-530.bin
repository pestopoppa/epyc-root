"""INF-78 OAB-8: orchestrator-run read-only scouts before the planner turn.

Offline and inference-free: every model call goes to a scripted fake transport (or an
httpx.MockTransport), and /slots occupancy comes from a fake resolver. Acceptance
(handoff autokernel-orchestrator-actor-backend.md, OAB-8):
  * scouts run CONCURRENTLY (a barrier only opens when they overlap);
  * the concurrency cap respects the server's free slots minus a reserve (>= 1);
  * scouts are read-only: no write surface, reads confined to the task scope;
  * the planner's context carries the labelled, sized summaries;
  * a failed / timed-out scout degrades to "no summary", the planner still runs;
  * no scouts when the flag is off (the unscoped default is unchanged);
  * every scout has returned (finished or cancelled) before the stage — and /chat — returns.

Run: taskset -c 72-79 .venv/bin/python -m pytest tests/unit/test_oab8_scouts.py -q
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import threading
import time
import uuid
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import ValidationError

from src.api.models import ChatRequest, ChatResponse
from src.api.routes.chat_pipeline import scout_stage as S
from src.repl_environment import task_root as TR

SCRATCH_BASE = Path("/mnt/raid0/llm/tmp")

KERNEL_C = """#include "quants.h"

// the hot dot product
static inline float helper(int x) { return x * 0.5f; }

void ggml_vec_dot_q4_K_q8_K(int n, float * s, const void * vx, const void * vy) {
    const block_q4_K * x = vx;
    float sumf = 0;
    for (int i = 0; i < n; ++i) {
        sumf += helper(x[i].d);
    }
    *s = sumf;
}
"""


@pytest.fixture(autouse=True)
def _no_leaked_scope(monkeypatch):
    monkeypatch.delenv(TR.ENV_VAR, raising=False)
    TR.clear_request_scope()
    yield
    TR.clear_request_scope()


@pytest.fixture()
def lane():
    base = SCRATCH_BASE / f"test_oab8_{uuid.uuid4().hex[:10]}"
    root, outside = base / "lane", base / "outside"
    (root / "ggml" / "src").mkdir(parents=True)
    outside.mkdir(parents=True)
    (root / "ggml" / "src" / "quants.c").write_text(KERNEL_C)
    (root / "ggml" / "src" / "quants.h").write_text(
        "void ggml_vec_dot_q4_K_q8_K(int n, float * s, const void * vx, const void * vy);\n")
    (root / "ggml" / "src" / "ops.cpp").write_text(
        "void ggml_compute_forward_mul_mat(void) {\n    // matmul driver\n}\n")
    (outside / "secret.txt").write_text("SECRET\n")
    scope = TR.TaskScope(root=str(root.resolve()), edit_mode=TR.EDIT_MODE_NONE)
    yield SimpleNamespace(base=base, root=root, outside=outside, scope=scope)
    shutil.rmtree(base, ignore_errors=True)


def _tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        h.update(str(p.relative_to(root)).encode())
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


class FakeResolver:
    """`ContextLimitResolver.pool_occupancy` stand-in: `busy` of `total` slots processing."""

    def __init__(self, total: int | None = 4, busy: int = 0):
        self.total, self.busy, self.calls = total, busy, 0

    def pool_occupancy(self, url):
        self.calls += 1
        if self.total is None:
            return None
        from src.backends.context_limits import PoolOccupancy, SlotState

        slots = tuple(SlotState(slot_id=i, n_ctx=196608, is_processing=i < self.busy,
                                n_prompt_tokens=100 if i < self.busy else 0, n_remain=None)
                      for i in range(self.total))
        return PoolOccupancy(url=url, slots=slots)


class ScriptedTransport:
    """Per-scout scripted replies keyed by the target's label (from the first user message).

    Tracks live concurrency; optional barrier makes the FIRST call of each scout wait until
    `barrier.parties` scouts are inside `complete` at the same time."""

    name = "fake"

    def __init__(self, scripts: dict[str, list], *, barrier: threading.Barrier | None = None,
                 delay_s: float = 0.0):
        self.scripts = {k: list(v) for k, v in scripts.items()}
        self.barrier = barrier
        self.delay_s = delay_s
        self.lock = threading.Lock()
        self.active = 0
        self.peak = 0
        self.calls: list[tuple[str, list[dict]]] = []
        self.seen_first: set[str] = set()

    def _label(self, messages):
        first_user = messages[1]["content"]
        for key in self.scripts:
            if key in first_user:
                return key
        raise AssertionError(f"no script for {first_user[:80]!r}")

    def complete(self, messages, *, max_tokens, should_stop, timeout_s):
        label = self._label(messages)
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
            first = label not in self.seen_first
            self.seen_first.add(label)
            self.calls.append((label, [dict(m) for m in messages]))
        try:
            if first and self.barrier is not None:
                self.barrier.wait()
            if self.delay_s:
                time.sleep(self.delay_s)
            step = self.scripts[label].pop(0)
            if isinstance(step, Exception):
                raise step
            if callable(step):
                return step(should_stop)
            return S.CompletionResult(step, prompt_tokens=1000, completion_tokens=50)
        finally:
            with self.lock:
                self.active -= 1


def _spec(targets, **extra):
    spec = {"enabled": True, "targets": targets, "max": 4, "max_turns": 4,
            "summary_tokens": 400, "budget_s": 20.0, "reserve_slots": 1}
    spec.update(extra)
    return spec


def _summary(tag: str) -> str:
    return f"SUMMARY\n{tag}: the loop at ggml/src/quants.c:9 dominates; lead: unroll x4."


# ── pure helpers ─────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("raw, ident", [
    ("ggml_vec_dot_q4_K_q8_K", "ggml_vec_dot_q4_K_q8_K"),
    ("ggml_vec_dot_q4_K_q8_K.cold", "ggml_vec_dot_q4_K_q8_K"),
    ("foo.isra.0", "foo"),
    ("void ns::detail::gemm<float, 4>(int, int) [clone .constprop.1]", "gemm"),
    ("memcpy@plt", "memcpy"),
])
def test_normalize_symbol(raw, ident):
    assert S.normalize_symbol(raw) == ident


def test_parse_reply_commands_and_summary():
    summary, cmds = S.parse_reply("<think>hmm</think>\nREAD ggml/src/quants.c 1 40\n"
                                  "GREP block_q4_K ggml/src\nGREP a b c ggml\nREAD x 1 2")
    assert summary is None
    assert cmds == [("READ", ["ggml/src/quants.c", "1", "40"]),
                    ("GREP", ["block_q4_K", "ggml/src"]), ("GREP", ["a b c", "ggml"])]
    summary, cmds = S.parse_reply("READ a 1 2\n**SUMMARY**\nfindings at a.c:3")
    assert summary == "findings at a.c:3" and cmds == []


# ── read-only enforcement ─────────────────────────────────────────────────────────────────


def test_reader_is_confined_to_the_scope_and_has_no_write_surface(lane):
    reader = S.ScopedReader(lane.scope)
    text, ok = reader.read(str(lane.outside / "secret.txt"), 1, 5)
    assert not ok and "TASK SCOPE" in text and "SECRET" not in text
    text, ok = reader.read("../outside/secret.txt", 1, 5)
    assert not ok and "SECRET" not in text
    text, ok = reader.grep("SECRET", str(lane.base))
    assert not ok and "SECRET\n" not in text
    text, ok = reader.read("ggml/src/quants.c", 6, 8)
    assert ok and "6: void ggml_vec_dot_q4_K_q8_K" in text
    assert not any(n for n in dir(reader) if n.startswith(("write", "edit", "patch", "run")))
    with pytest.raises(ValueError):
        S.ScopedReader(None)


def test_seed_locates_the_definition_not_the_declaration(lane):
    reader = S.ScopedReader(lane.scope)
    _, located = reader.seed(S.ScoutTarget(symbol="ggml_vec_dot_q4_K_q8_K.cold"))
    assert located == "ggml/src/quants.c:6"
    _, located = reader.seed(S.ScoutTarget(file="ggml/src/ops.cpp"))
    assert located == "ggml/src/ops.cpp"


def test_seed_prefers_the_host_arch_and_skips_nested_worktrees(lane):
    import os as _os

    src = lane.root / "ggml" / "src" / "arch"
    for arch in ("arm", "x86"):
        (src / arch).mkdir(parents=True)
        (src / arch / "q.c").write_text(f"// {arch}\nvoid kern(int n) {{\n}}\n")
    nested = lane.root / "aaa_worktrees" / "old"
    nested.mkdir(parents=True)
    (nested / ".git").write_text("gitdir: /elsewhere\n")
    (nested / "k.c").write_text("void kern(int n) {\n}\n")
    text, located = S.ScopedReader(lane.scope).seed(S.ScoutTarget(symbol="kern"))
    host = _os.uname().machine
    if host == "x86_64":
        assert located == "ggml/src/arch/x86/q.c:2"
        assert "Other definitions of this symbol in the tree: ggml/src/arch/arm/q.c:2" in text
    assert "aaa_worktrees" not in text and "aaa_worktrees" not in (located or "")


def test_a_scout_cannot_write_and_cannot_read_outside(lane):
    before = _tree_digest(lane.root)
    target = {"symbol": "ggml_vec_dot_q4_K_q8_K", "label": "T-dot"}
    transport = ScriptedTransport({"T-dot": [
        f"READ {lane.outside / 'secret.txt'} 1 3\nWRITE ggml/src/quants.c pwned",
        "rm -rf ggml\nrun_shell('touch x')",
        _summary("dot"),
    ]})
    stage = asyncio.run(S.run_scouts(_spec([target]), scope=lane.scope, role="frontdoor",
                                     url="http://x:1", transport=transport,
                                     resolver=FakeResolver()))
    assert _tree_digest(lane.root) == before, "the tree is byte-identical after the scout"
    row = stage.report["scouts"][0]
    assert row["status"] == "ok" and row["denied_reads"] == 1
    fed_back = "\n".join(m["content"] for _, msgs in transport.calls for m in msgs)
    assert "SECRET" not in fed_back.replace("secret.txt", "")
    assert "Unrecognised reply" in fed_back


def test_grep_is_a_literal_search_and_cannot_backtrack(lane):
    """Review F1: a model-authored pattern is never compiled as a regex (a backtracking
    regex holds the GIL and freezes the event loop)."""
    (lane.root / "ggml" / "src" / "slow.c").write_text(
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa bbbbbbbbbbbbbbbbbbbbbbbb\n"
        "int x = a.b(c) + [q]*;\n")
    reader = S.ScopedReader(lane.scope)
    started = time.monotonic()
    text, ok = reader.grep(r"(\w+\s?)*\(", "ggml/src")
    assert time.monotonic() - started < 0.5
    assert ok and text.startswith("GREP: no match")      # not a regex: no literal hit
    text, ok = reader.grep("a.b(c)", "ggml/src")          # metacharacters match literally
    assert ok and "slow.c:2:" in text
    text, ok = reader.grep("a.c", "ggml/src")             # '.' is not a wildcard
    assert ok and text.startswith("GREP: no match")
    text, ok = reader.grep("[q]*", "ggml/src")            # an invalid-looking regex is text
    assert ok and "slow.c:2:" in text


def test_tree_walks_stop_when_the_scout_is_stopped(lane):
    reader = S.ScopedReader(lane.scope, should_stop=lambda: True)
    text, ok = reader.grep("ggml", ".")
    assert ok and "GREP stopped" in text and "quants.c" not in text
    assert reader.definitions("ggml_vec_dot_q4_K_q8_K") == []
    calls = []

    def stop_after_one():
        calls.append(1)
        return len(calls) > 1

    reader = S.ScopedReader(lane.scope, should_stop=stop_after_one)
    assert len(list(reader._walk(lane.root))) == 1, "checked between files"


def test_read_past_eof_or_on_an_empty_file_does_not_kill_the_scout(lane):
    """Review F6: READ past EOF (or on an empty file) answered, never an IndexError."""
    (lane.root / "two.c").write_text("int a;\nint b;\n")
    (lane.root / "empty.c").write_text("")
    reader = S.ScopedReader(lane.scope)
    text, ok = reader.read("two.c", 50, 60)
    assert ok and text == "== two.c: only 2 lines"
    text, ok = reader.read("empty.c", 1, 10)
    assert ok and text == "== empty.c: only 0 lines"
    text, ok = reader.read("two.c", 2, 60)                # a straddling read still clips
    assert ok and text.endswith("2: int b;")
    text, located = reader.seed(S.ScoutTarget(file="empty.c"))
    assert located == "empty.c" and "only 0 lines" in text
    text, located = reader.seed(S.ScoutTarget(file="two.c"))
    assert located == "two.c" and "1: int a;" in text
    # and end to end: a scout whose model reads past EOF still finishes
    transport = ScriptedTransport({"T-e": ["READ two.c 50 60\nREAD empty.c 1 5", _summary("e")]})
    stage = asyncio.run(S.run_scouts(_spec([{"file": "empty.c", "label": "T-e"}]),
                                     scope=lane.scope, role="frontdoor", url="http://x",
                                     transport=transport, resolver=FakeResolver()))
    assert stage.report["scouts"][0]["status"] == "ok"
    fed_back = "\n".join(m["content"] for _, msgs in transport.calls for m in msgs)
    assert "== two.c: only 2 lines" in fed_back


def test_the_slots_read_runs_off_the_event_loop(lane):
    """Review F3: resolve_cap's synchronous /slots read happens in a worker thread."""
    seen = {}

    class ThreadRecordingResolver(FakeResolver):
        def pool_occupancy(self, url):
            seen["thread"] = threading.get_ident()
            return super().pool_occupancy(url)

    async def go():
        seen["loop_thread"] = threading.get_ident()
        return await S.run_scouts(_spec([{"symbol": "helper", "label": "T-1"}]),
                                  scope=lane.scope, role="frontdoor", url="http://x",
                                  transport=ScriptedTransport({"T-1": [_summary("t")]}),
                                  resolver=ThreadRecordingResolver())

    stage = asyncio.run(go())
    assert stage.report["completed"] == 1
    assert seen["thread"] != seen["loop_thread"]


def test_a_stuck_scout_thread_is_abandoned_after_a_bounded_wait(lane, monkeypatch):
    """Review F7: the post-stop wait is bounded; a thread that ignores the stop flag is
    logged and abandoned instead of holding the request open."""
    monkeypatch.setattr(S, "CONNECT_TIMEOUT_S", 0.0)
    monkeypatch.setattr(S, "ABANDON_WAIT_S", 0.2)
    release = threading.Event()

    def stuck(should_stop):
        release.wait(30)                   # ignores should_stop, like a blocked socket read
        return S.CompletionResult("late", None, None, "cancelled", cancelled=True)

    transport = ScriptedTransport({"T-1": [stuck]})

    async def go():
        started = time.monotonic()
        stage = await S.run_scouts(_spec([{"symbol": "helper", "label": "T-1"}], budget_s=0.2),
                                   scope=lane.scope, role="frontdoor", url="http://x",
                                   transport=transport, resolver=FakeResolver())
        elapsed = time.monotonic() - started
        release.set()                      # let the executor shut down cleanly
        return stage, elapsed

    stage, elapsed = asyncio.run(go())
    # budget 0.2 + first wait slack 5.0 + abandon 0.2; never the stuck call's 30 s
    assert elapsed < 10
    row = stage.report["scouts"][0]
    assert row["status"] == "timeout" and "abandoned" in (row["error"] or "")


def test_request_validation_scouts_need_task_root(lane):
    with pytest.raises(ValidationError, match="scouts require task_root"):
        ChatRequest(prompt="p", scouts={"enabled": True, "targets": [{"symbol": "f"}]})
    with pytest.raises(ValidationError, match="symbol or a file"):
        ChatRequest(prompt="p", task_root=str(lane.root), scouts={"enabled": True, "targets": [{}]})
    with pytest.raises(ValidationError):
        ChatRequest(prompt="p", task_root=str(lane.root),
                    scouts={"enabled": True, "targets": [{"symbol": "f"}], "reserve_slots": 0})
    # disabled scouts never need a root; enabled ones validate with one
    assert ChatRequest(prompt="p", scouts={"enabled": False}).scouts.enabled is False
    ok = ChatRequest(prompt="p", task_root=str(lane.root),
                     scouts={"enabled": True, "targets": [{"symbol": "f", "share": 0.3}]})
    assert ok.scouts.max == 4 and ok.scouts.reserve_slots == 1


# ── concurrency + cap ─────────────────────────────────────────────────────────────────────


def test_scouts_run_concurrently(lane):
    targets = [{"symbol": "ggml_vec_dot_q4_K_q8_K", "label": "T-a", "share": 0.4},
               {"file": "ggml/src/ops.cpp", "label": "T-b", "share": 0.2},
               {"symbol": "helper", "label": "T-c", "share": 0.1}]
    barrier = threading.Barrier(3, timeout=10)   # opens ONLY if all three overlap
    transport = ScriptedTransport({"T-a": [_summary("a")], "T-b": [_summary("b")],
                                   "T-c": [_summary("c")]}, barrier=barrier)
    stage = asyncio.run(S.run_scouts(_spec(targets), scope=lane.scope, role="architect_general",
                                     url="http://x:8083", transport=transport,
                                     resolver=FakeResolver(total=4, busy=0)))
    rep = stage.report
    assert rep["launched"] == 3 and rep["completed"] == 3 and rep["max_concurrency"] == 3
    assert rep["max_inflight_calls"] == 3, "three model calls were in flight at once"
    assert transport.peak == 3
    # the RAW timestamps: the provenance rows round to 3 decimals, which can tie
    latest_start = max(r.started_s for r in stage.results)
    earliest_end = min(r.ended_s for r in stage.results)
    assert latest_start < earliest_end, "all scout intervals overlap"
    assert rep["cap"]["cap"] == 3 and rep["cap"]["source"] == "live_slots"


@pytest.mark.parametrize("total, busy, reserve, expected", [
    (4, 0, 1, 3),    # np4 idle: 4 free - 1 reserve
    (4, 1, 1, 2),    # another client holds a slot
    (4, 3, 1, 0),    # only the reserve is left -> no scouts
    (4, 0, 2, 2),
    (None, 0, 1, 0),  # /slots unknown -> never guess
])
def test_cap_respects_free_slots(total, busy, reserve, expected):
    cap = S.resolve_cap("http://x:8083", max_scouts=4, n_targets=4, reserve_slots=reserve,
                        resolver=FakeResolver(total=total, busy=busy))
    assert cap["cap"] == expected
    assert S.resolve_cap("http://x", max_scouts=4, n_targets=4, reserve_slots=0,
                         resolver=FakeResolver(total=4))["reserve"] == 1, "reserve is >= 1"


def test_launch_count_follows_the_cap_and_skips_the_rest(lane):
    targets = [{"symbol": "helper", "label": f"T-{i}"} for i in range(5)]
    transport = ScriptedTransport({f"T-{i}": [_summary(str(i))] for i in range(5)}, delay_s=0.05)
    stage = asyncio.run(S.run_scouts(_spec(targets, max=4), scope=lane.scope, role="frontdoor",
                                     url="http://x:8070", transport=transport,
                                     resolver=FakeResolver(total=4, busy=1)))
    rep = stage.report
    assert rep["cap"]["cap"] == 2 and rep["launched"] == 2 and transport.peak <= 2
    statuses = [r["status"] for r in rep["scouts"]]
    assert statuses == ["ok", "ok", "skipped", "skipped", "skipped"]
    assert rep["scouts"][4]["skip_reason"] == "beyond max"
    assert "no free slot" in rep["scouts"][2]["skip_reason"]


def test_no_free_slot_runs_nothing(lane):
    transport = ScriptedTransport({})
    stage = asyncio.run(S.run_scouts(_spec([{"symbol": "helper", "label": "T"}]),
                                     scope=lane.scope, role="frontdoor", url="http://x",
                                     transport=transport, resolver=FakeResolver(total=1)))
    assert stage.block == "" and stage.report["launched"] == 0 and not transport.calls


# ── degradation + cancellation ────────────────────────────────────────────────────────────


def test_a_failed_scout_degrades_to_no_summary(lane):
    targets = [{"symbol": "ggml_vec_dot_q4_K_q8_K", "label": "T-ok"},
               {"symbol": "helper", "label": "T-boom"},
               {"file": "ggml/src/ops.cpp", "label": "T-mute"}]
    transport = ScriptedTransport({
        "T-ok": [_summary("ok")],
        "T-boom": [httpx.ConnectError("refused")],
        "T-mute": ["READ ggml/src/ops.cpp 1 3", "still thinking", ""],   # never summarises
    })
    stage = asyncio.run(S.run_scouts(_spec(targets, max_turns=3), scope=lane.scope,
                                     role="frontdoor", url="http://x", transport=transport,
                                     resolver=FakeResolver()))
    by = {r["target"]["label"]: r for r in stage.report["scouts"]}
    assert by["T-ok"]["status"] == "ok" and by["T-ok"]["evidence_refs"] >= 1
    assert by["T-boom"]["status"] == "error" and "ConnectError" in by["T-boom"]["error"]
    assert by["T-mute"]["status"] == "no_summary" and by["T-mute"]["turns"] == 3
    assert "ok: the loop at ggml/src/quants.c:9" in stage.block
    assert "[status error; no summary" in stage.block
    assert stage.report["completed"] == 1 and stage.report["failed"] == 2


def _blocking(exited: list):
    def step(should_stop):
        try:
            while not should_stop():
                time.sleep(0.01)
            return S.CompletionResult("partial", None, None, "cancelled", cancelled=True)
        finally:
            exited.append(threading.get_ident())
    return step


def test_budget_timeout_cancels_every_scout_before_the_stage_returns(lane):
    exited: list = []
    targets = [{"symbol": "helper", "label": "T-1"}, {"symbol": "helper", "label": "T-2"}]
    transport = ScriptedTransport({"T-1": [_blocking(exited)], "T-2": [_blocking(exited)]})
    started = time.monotonic()
    stage = asyncio.run(S.run_scouts(_spec(targets, budget_s=0.3), scope=lane.scope,
                                     role="frontdoor", url="http://x", transport=transport,
                                     resolver=FakeResolver()))
    assert time.monotonic() - started < 5
    assert len(exited) == 2 and transport.active == 0, "no scout is still inside a call"
    assert {r["status"] for r in stage.report["scouts"]} == {"timeout"}
    assert stage.report["scouts"][0]["tokens_exact"] is False
    assert all(r["ended_s"] is not None for r in stage.report["scouts"])


def test_client_disconnect_cancels_the_scouts(lane):
    exited: list = []
    cancel = threading.Event()
    transport = ScriptedTransport({"T-1": [_blocking(exited)]})

    async def go():
        task = asyncio.ensure_future(S.run_scouts(
            _spec([{"symbol": "helper", "label": "T-1"}]), scope=lane.scope, role="frontdoor",
            url="http://x", transport=transport, resolver=FakeResolver(), cancel_event=cancel))
        await asyncio.sleep(0.1)
        cancel.set()
        return await task

    stage = asyncio.run(go())
    assert exited and stage.report["scouts"][0]["status"] == "cancelled"


def test_task_cancellation_waits_for_the_threads(lane):
    exited: list = []
    transport = ScriptedTransport({"T-1": [_blocking(exited)]})

    async def go():
        task = asyncio.ensure_future(S.run_scouts(
            _spec([{"symbol": "helper", "label": "T-1"}]), scope=lane.scope, role="frontdoor",
            url="http://x", transport=transport, resolver=FakeResolver()))
        await asyncio.sleep(0.1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return list(exited)

    assert len(asyncio.run(go())) == 1, "the scout thread returned before the cancel propagated"


# ── the streamed transport (httpx.MockTransport, no network) ──────────────────────────────


def _sse(*objs, done=True) -> bytes:
    lines = [f"data: {json.dumps(o)}\n\n" for o in objs]
    if done:
        lines.append("data: [DONE]\n\n")
    return "".join(lines).encode()


def test_transport_parses_the_stream_and_usage():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        body = _sse({"choices": [{"delta": {"content": "SUMMARY\n"}}]},
                    {"choices": [{"delta": {"content": "x at a.c:1"}, "finish_reason": "stop"}]},
                    {"choices": [], "usage": {"prompt_tokens": 321, "completion_tokens": 9}})
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    t = S.ChatCompletionsTransport("http://x:8083/", client=client)
    out = t.complete([{"role": "user", "content": "hi"}], max_tokens=64,
                     should_stop=lambda: False, timeout_s=5)
    assert out.text == "SUMMARY\nx at a.c:1" and out.finish_reason == "stop"
    assert (out.prompt_tokens, out.completion_tokens) == (321, 9)
    assert seen["path"] == "/v1/chat/completions" and seen["body"]["stream"] is True
    assert seen["body"]["chat_template_kwargs"] == {"enable_thinking": False}


def test_transport_stops_reading_when_told():
    def handler(request):
        return httpx.Response(200, content=_sse(*({"choices": [{"delta": {"content": "tok "}}]}
                                                  for _ in range(50)), done=False))

    calls = {"n": 0}

    def should_stop():
        calls["n"] += 1
        return calls["n"] > 3

    t = S.ChatCompletionsTransport("http://x", client=httpx.Client(transport=httpx.MockTransport(handler)))
    out = t.complete([], max_tokens=8, should_stop=should_stop, timeout_s=5)
    assert out.cancelled and out.text.count("tok") < 50


# ── /chat integration: planner context, default-off parity, provenance ───────────────────


def _pipeline_patches(mock_primitives, routing, executed, captured):
    def fake_repl(request, *_a, **_k):
        captured["prompt"] = request.prompt
        return executed

    return (
        patch("src.api.routes.chat._route_request", return_value=routing),
        patch("src.api.routes.chat._preprocess", return_value=None),
        patch("src.api.routes.chat._init_primitives", return_value=mock_primitives),
        patch("src.api.routes.chat._plan_review_gate", return_value=None),
        patch("src.api.routes.chat._execute_vision", new=AsyncMock(return_value=None)),
        patch("src.api.routes.chat._execute_proactive", new=AsyncMock(return_value=None)),
        patch("src.api.routes.chat._try_cheap_first", new=AsyncMock(return_value=None)),
        patch("src.api.routes.chat._execute_repl", new=AsyncMock(side_effect=fake_repl)),
    )


@pytest.fixture()
def pipeline():
    from src.api.routes.chat_utils import RoutingResult
    from src.api.state import AppState

    state = MagicMock(spec=AppState)
    for attr in ("progress_logger", "hybrid_router", "tool_registry", "script_registry", "registry"):
        setattr(state, attr, None)
    primitives = MagicMock()
    primitives.request_context = MagicMock(return_value=nullcontext())
    primitives.server_urls = {"frontdoor": "full:http://127.0.0.1:8070,http://127.0.0.1:8080",
                              "architect_general": "http://127.0.0.1:8083"}
    routing = RoutingResult(task_id="t-oab8", task_ir={"task_type": "chat", "objective": "x"},
                            use_mock=False, routing_decision=["frontdoor"],
                            routing_strategy="rules", skill_ids=[])
    executed = ChatResponse(answer='{"abstain": "x"}', turns=3, elapsed_seconds=0.1,
                            mock_mode=False, real_mode=True, routed_to="frontdoor", mode="repl")
    return SimpleNamespace(state=state, primitives=primitives, routing=routing, executed=executed)


def _run_handle_chat(pipeline, req, captured, transport=None, resolver=None):
    from src.api.routes.chat import _handle_chat
    from src.backends import context_limits as CL

    patches = _pipeline_patches(pipeline.primitives, pipeline.routing, pipeline.executed, captured)
    CL.set_context_limit_resolver(resolver or FakeResolver())
    TR.begin_request_scope(req.task_root, req.edit_mode, req.read_roots)
    try:
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], \
                patches[6], patches[7], \
                patch.object(S, "ChatCompletionsTransport",
                             side_effect=lambda url, **kw: (captured.setdefault("url", url),
                                                            transport)[1]):
            return asyncio.run(_handle_chat(req, pipeline.state))
    finally:
        CL.set_context_limit_resolver(None)
        TR.clear_request_scope()


def test_planner_context_carries_the_scout_summaries(lane, pipeline):
    transport = ScriptedTransport({"T-dot": [_summary("dot")], "T-ops": [_summary("ops")]})
    req = ChatRequest(prompt="PROPOSE ONE HYPOTHESIS", mock_mode=False, real_mode=True,
                      force_mode="repl", force_role="architect_general",
                      task_root=str(lane.root), quiescent_after=True,
                      scouts={"enabled": True, "targets": [
                          {"symbol": "ggml_vec_dot_q4_K_q8_K", "label": "T-dot", "share": 0.31},
                          {"file": "ggml/src/ops.cpp", "label": "T-ops"}]})
    captured: dict = {}
    resp = _run_handle_chat(pipeline, req, captured, transport)
    prompt = captured["prompt"]
    assert prompt.startswith("## Orchestrator scout findings (INF-78 OAB-8)")
    assert prompt.rstrip().endswith("PROPOSE ONE HYPOTHESIS"), "the original prompt follows"
    assert "dot: the loop at ggml/src/quants.c:9" in prompt and "ops: the loop" in prompt
    assert "share 31.0%" in prompt and "chars, ~" in prompt, "labelled, with sizes"
    assert captured["url"] == "http://127.0.0.1:8083", "scouts use force_role's server"
    assert req.prompt == "PROPOSE ONE HYPOTHESIS", "the caller's request is not mutated"
    sc = resp.scouts
    assert sc["schema"] == S.SCHEMA and sc["launched"] == 2 and sc["completed"] == 2
    assert sc["role"] == "architect_general" and sc["block_chars"] == len(prompt) - len(req.prompt) - 1
    assert all("summary" not in row for row in sc["scouts"]), "provenance, never full summaries"


def test_scout_role_override_and_frontdoor_primary_url(lane, pipeline):
    transport = ScriptedTransport({"T": [_summary("t")]})
    req = ChatRequest(prompt="P", mock_mode=False, real_mode=True, force_mode="repl",
                      task_root=str(lane.root),
                      scouts={"enabled": True, "role": "frontdoor",
                              "targets": [{"symbol": "helper", "label": "T"}]})
    captured: dict = {}
    _run_handle_chat(pipeline, req, captured, transport)
    assert captured["url"] == "http://127.0.0.1:8070"


def test_no_scouts_when_the_flag_is_off(lane, pipeline):
    for scouts in (None, {"enabled": False, "targets": [{"symbol": "helper"}]}):
        req = ChatRequest(prompt="PLAIN", mock_mode=False, real_mode=True, force_mode="repl",
                          task_root=str(lane.root), scouts=scouts)
        captured: dict = {}
        with patch.object(S, "run_scouts", side_effect=AssertionError("scouts ran")):
            resp = _run_handle_chat(pipeline, req, captured, transport=None)
        assert captured["prompt"] == "PLAIN"
        assert resp.scouts is None and "scouts" not in resp.model_dump()


def test_unscoped_default_request_is_unchanged(pipeline):
    req = ChatRequest(prompt="hello", mock_mode=False, real_mode=True, force_mode="repl")
    captured: dict = {}
    with patch.object(S, "run_scouts", side_effect=AssertionError("scouts ran")):
        resp = _run_handle_chat(pipeline, req, captured)
    assert captured["prompt"] == "hello" and resp.scouts is None


def test_a_crashing_stage_still_runs_the_planner(lane, pipeline):
    req = ChatRequest(prompt="P", mock_mode=False, real_mode=True, force_mode="repl",
                      task_root=str(lane.root),
                      scouts={"enabled": True, "targets": [{"symbol": "helper"}]})
    captured: dict = {}
    with patch.object(S, "run_scouts", new=AsyncMock(side_effect=RuntimeError("boom"))):
        resp = _run_handle_chat(pipeline, req, captured)
    assert captured["prompt"] == "P"
    assert resp.scouts["launched"] == 0 and "boom" in resp.scouts["error"]


def test_stream_endpoint_refuses_scouts(lane):
    from fastapi import HTTPException

    from src.api.routes.chat import chat_stream

    req = ChatRequest(prompt="P", task_root=str(lane.root),
                      scouts={"enabled": True, "targets": [{"symbol": "helper"}]})
    with pytest.raises(HTTPException) as err:
        asyncio.run(chat_stream(req, MagicMock()))
    assert err.value.status_code == 422


def test_task_scoped_requests_skip_proactive_delegation(lane):
    from src.api.routes.chat_pipeline.proactive_stage import _execute_proactive

    req = ChatRequest(prompt="Design and implement a distributed system " * 40,
                      mock_mode=False, real_mode=True, task_root=str(lane.root))
    with patch("src.api.routes.chat_pipeline.proactive_stage.features",
               return_value=SimpleNamespace(parallel_execution=True)):
        out = asyncio.run(_execute_proactive(req, MagicMock(), MagicMock(), MagicMock(), 0.0))
    assert out is None
