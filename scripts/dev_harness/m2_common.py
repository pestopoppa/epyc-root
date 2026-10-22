#!/usr/bin/env python3
"""Shared reading layer for the M2 mining analyses (DHM-2/3/4/7.2).

Reads one AgentRun conversion (agentrun.py output, PRIVATE) unit by unit: index.jsonl rows of a
unit are contiguous, so a unit's segments are merged back into one ordered message list without
holding the whole index in memory. Each tool call is flattened into a ``Call`` carrying the shell
command(s) and written paths it implies, paired with its tool result.

stdlib only. Nothing here writes; callers write through dh_privacy.
"""
from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

_VAULT_TENANT_RE = re.compile(r"/cloud-llm-vault/([A-Za-z0-9_-]+)/")
_CODEX_CMD_RE = re.compile(r"exec_command\(\s*\{\s*cmd\s*:\s*(\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`)")
_PATCH_FILE_RE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$|^\*\*\* Move to: (.+)$", re.M)

SHELL_TOOLS = {"bash", "shell", "exec_command", "local_shell", "shell_command", "container.exec",
               "monitor", "exec"}
WRITE_TOOLS = {"write", "edit", "multiedit", "notebookedit", "apply_patch", "patch"}


def infer_source(row: dict) -> str:
    """The row's `source` tag (epyc|host|twyne); older runs lack it, so fall back to the vault tenant."""
    s = row.get("source")
    if s:
        return s
    m = _VAULT_TENANT_RE.search(row.get("source_path") or "")
    if m:
        return m.group(1)
    sp = row.get("source_path") or ""
    if "host-" in sp:
        return "host"
    if "opencode" in sp:
        return "epyc"
    return "unknown"


@dataclass
class Call:
    idx: int                 # message index of the assistant turn in the unit
    ts: str | None
    function: str
    tool_call_id: str | None
    args: dict
    commands: list[str] = field(default_factory=list)   # shell command strings run by this call
    cwd: str | None = None
    write_paths: list[str] = field(default_factory=list)
    background: bool = False
    result: dict | None = None                          # the paired tool message

    @property
    def outcome(self) -> str:
        r = self.result
        if r is None:
            return "no_result"
        err = r.get("error") or {}
        et = err.get("type") or ""
        if et == "denial:hook_block":
            return "blocked_hook"
        if et == "denial:user_reject":
            return "blocked_user"
        if err:
            return "errored"
        return "slipped_through"


@dataclass
class Unit:
    harness: str
    source: str
    unit_key: str
    rows: list[dict]                     # index rows (segment metadata), in segment order
    messages: list[dict]                 # merged, ordered
    seg_of: list[int]                    # segment index of each message
    calls: list[Call]

    @property
    def is_main(self) -> bool:
        r = self.rows[0]   # opencode's primary agent is "build"; a spawned/forked child has a parent
        return not r.get("parent_conversation_id") and r.get("edge_kind") not in ("spawn", "fork")

    @property
    def first_ts(self) -> str | None:
        tss = [r.get("first_ts") for r in self.rows if r.get("first_ts")]
        return min(tss) if tss else None

    @property
    def source_path(self) -> str:
        return self.rows[0].get("source_path") or ""


def _js_string(lit: str) -> str:
    if lit[0] == '"':
        try:
            return json.loads(lit)
        except ValueError:
            return lit[1:-1]
    body = lit[1:-1]
    return body.replace("\\" + lit[0], lit[0]).replace("\\n", "\n").replace("\\\\", "\\")


def _cmd_of(v) -> str | None:
    if isinstance(v, str):
        return v
    if isinstance(v, list) and all(isinstance(x, str) for x in v):
        if len(v) >= 3 and v[0].endswith(("bash", "sh", "zsh")) and v[1] in ("-lc", "-c"):
            return v[2]
        return shlex.join(v)
    return None


def flatten_call(idx: int, ts: str | None, tc: dict) -> Call:
    fn = tc.get("function") or ""
    args = tc.get("arguments") or {}
    if not isinstance(args, dict):
        args = {"input": str(args)}
    c = Call(idx=idx, ts=ts, function=fn, tool_call_id=tc.get("id"), args=args)
    low = fn.lower()
    if low in SHELL_TOOLS:
        c.cwd = args.get("workdir") or args.get("cwd")
        c.background = bool(args.get("run_in_background"))
        if low == "exec":   # Codex code-mode: JS that calls tools.exec_command({cmd: ...})
            src = args.get("input") or ""
            if isinstance(src, str):
                c.commands = [_js_string(m.group(1)) for m in _CODEX_CMD_RE.finditer(src)]
                c.write_paths += [a or b for a, b in _PATCH_FILE_RE.findall(src)]
        else:
            for k in ("command", "cmd", "script"):
                cmd = _cmd_of(args.get(k))
                if cmd:
                    c.commands.append(cmd)
                    break
    if low in WRITE_TOOLS:
        for k in ("file_path", "filePath", "notebook_path", "path"):
            if isinstance(args.get(k), str):
                c.write_paths.append(args[k])
        patch = args.get("input") or args.get("patch")
        if isinstance(patch, str):
            c.write_paths += [a or b for a, b in _PATCH_FILE_RE.findall(patch)]
    c.write_paths = [p.strip() for p in c.write_paths if p and p.strip()]
    return c


def build_unit(rows: list[dict]) -> Unit:
    msgs: list[dict] = []
    seg_of: list[int] = []
    for r in sorted(rows, key=lambda x: x.get("segment_index", 0)):
        try:
            ar = json.loads(Path(r["path"]).read_text())
        except (OSError, ValueError):
            continue
        for t in ar.get("transcripts") or []:
            for m in t.get("messages") or []:
                msgs.append(m)
                seg_of.append(r.get("segment_index", 0))
    calls: list[Call] = []
    by_id: dict[str, Call] = {}
    for i, m in enumerate(msgs):
        md = m.get("metadata") or {}
        if m.get("role") == "assistant":
            for tc in m.get("tool_calls") or []:
                c = flatten_call(i, md.get("ts"), tc)
                calls.append(c)
                if c.tool_call_id:
                    by_id[c.tool_call_id] = c
        elif m.get("role") == "tool":
            c = by_id.get(m.get("tool_call_id") or "")
            if c is not None and c.result is None:
                c.result = m
    r0 = rows[0]
    return Unit(harness=r0.get("harness") or "unknown", source=infer_source(r0),
                unit_key=r0.get("unit_key") or "", rows=rows, messages=msgs, seg_of=seg_of, calls=calls)


def iter_units(agentrun_dir: Path | str, limit: int | None = None) -> Iterator[Unit]:
    """Stream units from <agentrun_dir>/index.jsonl (rows of one unit are contiguous)."""
    cur_key = None
    cur: list[dict] = []
    n = 0
    with open(Path(agentrun_dir) / "index.jsonl") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            key = (r.get("harness"), r.get("source"), r.get("unit_key"))
            if cur and key != cur_key:
                yield build_unit(cur)
                n += 1
                if limit and n >= limit:
                    return
                cur = []
            cur_key = key
            cur.append(r)
    if cur:
        yield build_unit(cur)


def text_of(m: dict) -> str:
    c = m.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(p.get("text") or "" for p in c if isinstance(p, dict) and p.get("type") == "text")
    return ""


_SECRET_RE = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|[A-Za-z0-9+_-]{40,}={0,2})")


def excerpt(text: str, n: int) -> str:
    """One-line excerpt with long token-like runs (keys, base64 blobs) masked."""
    t = _SECRET_RE.sub("<redacted-token>", " ".join((text or "").split()))
    return t if len(t) <= n else t[:n - 1] + "…"
