"""Build/review a source-pinned patch without modifying the application tree.

Tests install an import finder over these in-memory candidate sources. This
is not an application deployment mechanism.
"""

from __future__ import annotations

import ast
import difflib
import importlib.abc
import importlib.util
import subprocess
import sys
from pathlib import Path

BASE = "c1df9962c919562ce02bebb5608451093fe6bf6c"
REPO = Path("/mnt/raid0/llm/epyc-orchestrator")
HERE = Path(__file__).resolve().parent
NEW_FILES = {"src/trace/approval_live.py", "tests/unit/test_live_escalation_records.py"}


def original(path):
    return subprocess.check_output(
        ["git", "-C", str(REPO), "show", f"{BASE}:{path}"], text=True
    )


def once(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new)


def sources():
    result = {"src/trace/approval_live.py": (HERE / "approval_live.py").read_text()}
    path = "src/api/routes/chat_pipeline/stages.py"
    source = original(path)
    source = once(
        source,
        "    force: bool = False,",
        "    request_id: str | None = None,\n    force: bool = False,",
    )
    source = once(
        source,
        "                escalated = primitives.llm_call(\n                    prompt,\n                    role=candidate_name,",
        """                from src.trace.approval_live import call_escalation

                escalated = call_escalation(
                    primitives, prompt,
                    from_role=initial_name, to_role=candidate_name,
                    request_id=request_id,
                    reason="forced_consultant" if force else str(quality_issue),
                    alternatives=[str(role) for role in unique_candidates],""",
    )
    result[path] = source
    result[path] = once(
        result[path],
        "        allow_escalation=not bool(request.force_role),",
        "        allow_escalation=not bool(request.force_role),\n        request_id=request.request_id or routing.task_id,",
    )
    path = "src/api/routes/chat_pipeline/direct_stage.py"
    result[path] = once(
        original(path),
        "        allow_escalation=not bool(request.force_role),",
        "        allow_escalation=not bool(request.force_role),\n        request_id=request.request_id or routing.task_id,",
    )
    path = "src/api/routes/v1_escalation.py"
    result[path] = once(
        original(path),
        "                    allow_escalation=True,",
        "                    allow_escalation=True,\n                    request_id=task_id,",
    )
    path = "src/graph/observability.py"
    result[path] = once(
        original(path),
        "    pl = ctx.deps.progress_logger\n    if pl is None:\n        return\n    try:\n        pl.log_escalation(",
        """    from src.trace.approval_live import record_live_escalation

    record_live_escalation(
        request_id=ctx.state.task_id, prompt=getattr(ctx.state, "prompt", None),
        from_role=from_role, to_role=to_role, reason=reason,
        primitives=getattr(ctx.deps, "primitives", None),
    )
    pl = ctx.deps.progress_logger
    if pl is None:
        return
    try:
        pl.log_escalation(""",
    )
    for path in (
        "src/api/routes/chat.py",
        "src/api/routes/chat_pipeline/stream_adapter.py",
    ):
        source = original(path)
        lines = source.splitlines(keepends=True)
        sites = []
        for node in ast.walk(ast.parse(source)):
            if (
                not isinstance(node, ast.If)
                or ast.unparse(node.test) != "state.progress_logger"
            ):
                continue
            calls = [
                n
                for n in ast.walk(node)
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and n.func.attr == "log_escalation"
            ]
            if len(calls) != 1:
                continue
            reason = next(k.value for k in calls[0].keywords if k.arg == "reason")
            indent = " " * node.col_offset
            addition = [
                "from src.trace.approval_live import record_live_escalation",
                "record_live_escalation(",
                "    request_id=request.request_id or task_id, prompt=request.prompt,",
                "    from_role=str(role_history[-2]), to_role=str(current_role),",
                f"    reason={ast.unparse(reason)}, primitives=primitives,",
                ")",
            ]
            sites.append(
                (node.lineno - 1, "".join(indent + line + "\n" for line in addition))
            )
        assert len(sites) == 2, path
        for line, addition in sorted(sites, reverse=True):
            lines.insert(line, addition)
        result[path] = "".join(lines)
    result["tests/unit/test_live_escalation_records.py"] = (
        HERE / "test_approval_live.py"
    ).read_text()
    return result


class CandidateImporter(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, baseline=False):
        self.code = {
            p[:-3].replace("/", "."): (
                p,
                original(p) if baseline and p not in NEW_FILES else s,
            )
            for p, s in sources().items()
        }

    def find_spec(self, fullname, path=None, target=None):
        if fullname in self.code:
            return importlib.util.spec_from_loader(fullname, self)

    def exec_module(self, module):
        path, source = self.code[module.__name__]
        module.__file__ = str(REPO / path)
        exec(compile(source, module.__file__, "exec"), module.__dict__)  # noqa: S102 — reviewed local candidate


def install(baseline=False):
    sys.path.insert(0, str(REPO))
    sys.meta_path.insert(0, CandidateImporter(baseline=baseline))


if __name__ == "__main__":
    changes = sources()
    for path, source in changes.items():
        compile(source, path, "exec")
    patch = "".join(
        "".join(
            difflib.unified_diff(
                ([] if path in NEW_FILES else original(path).splitlines(keepends=True)),
                source.splitlines(keepends=True),
                fromfile="/dev/null" if path in NEW_FILES else "a/" + path,
                tofile="b/" + path,
            )
        )
        for path, source in changes.items()
    )
    (HERE / "implementation.patch").write_text(patch)
    print(f"{len(changes)} candidate files compiled; patch generated against {BASE}")
