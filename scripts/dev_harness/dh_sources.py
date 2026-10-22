#!/usr/bin/env python3
"""Read-only readers for dev-harness transcripts (UTM-LB2 / DHM-7 shared layer).

Sources, in preference order (operator ruling 2026-10-22: read the EXISTING backup, build none):

  vault     /mnt/raid0/llm/cloud-llm-vault/{epyc,host,twyne}/{claude,codex}  (nightly 02:00Z, immutable)
  tarball   /mnt/raid0/llm/claude-backups/ai-sessions-*.tar.gz              (streamed, never extracted)
  live      ~/.claude/projects files newer than the last vault sync (``--include-live``);
            opencode.db, which neither the vault nor the tarballs hold (UTM-LB1 gap), opened
            ``immutable=1`` so SQLite can neither write nor take a lock.

Every reader yields ``Unit`` objects: one per transcript file / opencode session, carrying
normalized ``records`` (dicts). Records hold content (``text``, ``arguments``) IN MEMORY ONLY;
the projector drops it (hashes only) and the AgentRun converter writes it to the private root.

Nothing here opens a file for writing. The opencode reader queries an explicit table allowlist
(session, message, part, session_message) and never touches account/credential/share tables.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import tarfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

VAULT_ROOT = Path("/mnt/raid0/llm/cloud-llm-vault")
BACKUP_LOG = Path("/mnt/raid0/llm/claude-backups/backup.log")
LIVE_CLAUDE = Path(os.path.expanduser("~/.claude/projects"))
LIVE_OPENCODE_DB = Path(os.path.expanduser("~/.local/share/opencode/opencode.db"))

INTERRUPT_PLAIN = "[Request interrupted by user]"
INTERRUPT_TOOL = "[Request interrupted by user for tool use]"
_USER_REJECT_RE = re.compile(r"doesn't want to proceed with this tool use|rejected by (the )?user|"
                             r"user rejected|declined by (the )?user|rejected permission", re.I)
_HOOK_BLOCK_RE = re.compile(r"hook error|PreToolUse:|hook blocked|^BLOCKED:", re.I | re.M)
_COMMIT_RE = re.compile(r"^\[[^\]\n]*? ([0-9a-f]{7,40})\] ", re.M)
_CODEX_EXIT_RE = re.compile(r"(?:Process exited with code\s+|\"exit_code\":\s*|Exit code:?\s*)(-?\d+)")


@dataclass
class Unit:
    harness: str                 # claude_code | codex | opencode
    unit_key: str                # file-safe key: session id (+ .agent-<id> for subagents)
    conversation_id: str | None  # native session id; never fabricated
    collection_method: str       # vault_file | tarball_member | live_file | sqlite_row
    source_path: str
    agent_name: str | None = None
    agent_instance_id: str | None = None
    parent_conversation_id: str | None = None
    parent_tool_call_id: str | None = None
    edge_kind: str | None = None          # spawn | fork | None (root)
    edge_fidelity: str | None = None      # observed | inferred
    versions: set = field(default_factory=set)
    type_sig: set = field(default_factory=set)
    records: list = field(default_factory=list)
    parse_errors: int = 0

    def source_schema_key(self) -> str:
        """Composite per-session schema key: harness | producer versions | record-type signature."""
        import hashlib
        sig = hashlib.sha256("\n".join(sorted(self.type_sig)).encode()).hexdigest()[:12]
        vers = ",".join(sorted(v for v in self.versions if v)) or "unknown"
        return f"{self.harness}|v={vers}|types={sig}"


def last_vault_sync(log_path: Path = BACKUP_LOG) -> datetime | None:
    """Timestamp of the last ``VAULT`` line in the backup job's log (read-only)."""
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        m = re.match(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ) VAULT ", line)
        if m:
            return datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return None


# ─── content helpers ─────────────────────────────────────────────────────────

def _text_of(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                for key in ("text", "content", "output", "thinking"):
                    v = item.get(key)
                    if isinstance(v, str):
                        parts.append(v)
                        break
                    if isinstance(v, list):
                        parts.append(_text_of(v))
                        break
        return "\n".join(p for p in parts if p)
    if isinstance(content, dict):
        return _text_of([content])
    return str(content)


def _denial(text: str) -> str | None:
    if _USER_REJECT_RE.search(text or ""):
        return "user_reject"
    if _HOOK_BLOCK_RE.search(text or ""):
        return "hook_block"
    return None


def commit_shas(text: str) -> list[str]:
    return sorted(set(_COMMIT_RE.findall(text or "")))


def _rec(unit: Unit, line: int | str, ts: str | None, kind: str, **kw: Any) -> dict:
    r = {"source_line": line, "ts": ts, "kind": kind, "fidelity": "observed"}
    r.update(kw)
    unit.records.append(r)
    return r


# ─── Claude Code ─────────────────────────────────────────────────────────────

def _claude_usage(u: dict) -> dict:
    inp = int(u.get("input_tokens") or 0)
    cr = int(u.get("cache_read_input_tokens") or 0)
    cc = int(u.get("cache_creation_input_tokens") or 0)
    return {"input_inclusive": inp + cr + cc, "output": int(u.get("output_tokens") or 0),
            "cache_read": cr, "cache_creation": cc, "reasoning": None,
            "convention": "anthropic_input_excludes_cache(+read+creation)",
            "raw": {k: u.get(k) for k in ("input_tokens", "cache_read_input_tokens",
                                          "cache_creation_input_tokens", "output_tokens")}}


def parse_claude_lines(lines: Iterable[str], unit: Unit) -> Unit:
    usage_by_msg: dict[str, tuple] = {}
    for lineno, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        try:
            d = json.loads(raw)
        except json.JSONDecodeError:
            unit.parse_errors += 1
            continue
        if not isinstance(d, dict):
            unit.parse_errors += 1
            continue
        t = d.get("type")
        unit.type_sig.add(f"{t}:{d.get('subtype') or ''}")
        if d.get("version"):
            unit.versions.add(f"claude-code/{d['version']}")
        if unit.conversation_id is None and d.get("sessionId"):
            unit.conversation_id = d["sessionId"]
        if unit.agent_instance_id is None and d.get("agentId"):
            unit.agent_instance_id = d["agentId"]
        ts = d.get("timestamp")
        msg = d.get("message") if isinstance(d.get("message"), dict) else {}
        if t == "user":
            content = msg.get("content")
            items = content if isinstance(content, list) else [content]
            for item in items:
                if isinstance(item, dict) and item.get("type") == "tool_result":
                    text = _text_of(item.get("content"))
                    den = _denial(text) if item.get("is_error") else None
                    # is_error is observed; the denial CLASS is a text-pattern inference
                    _rec(unit, lineno, ts, "tool_result", role="tool", operation="execute_tool",
                         tool_call_id=item.get("tool_use_id"), is_error=bool(item.get("is_error")),
                         denial=den, text=text, commit_shas=commit_shas(text),
                         fidelity="inferred" if den else "observed")
                    continue
                text = _text_of(item)
                if not text:
                    continue
                interrupt = None
                if INTERRUPT_TOOL in text:
                    interrupt = "tool_use"
                elif INTERRUPT_PLAIN in text:
                    interrupt = "plain"
                is_meta = bool(d.get("isMeta")) or text.startswith(("<local-command", "<command-", "Caveat:"))
                kind = "interrupt" if interrupt else "chat"
                _rec(unit, lineno, ts, kind, role="user", operation="chat", interrupt=interrupt,
                     is_meta=is_meta, human=not is_meta and not interrupt and not d.get("isSidechain"),
                     text=text)
        elif t == "assistant":
            mid = msg.get("id")
            model = msg.get("model")
            for item in msg.get("content") or []:
                if not isinstance(item, dict):
                    continue
                it = item.get("type")
                if it == "text":
                    _rec(unit, lineno, ts, "chat", role="assistant", operation="chat", model=model,
                         response_id=mid, text=item.get("text") or "")
                elif it in ("thinking", "redacted_thinking"):
                    _rec(unit, lineno, ts, "reasoning", role="assistant", operation="chat", model=model,
                         response_id=mid, text=item.get("thinking") or "")
                elif it == "tool_use":
                    name = item.get("name")
                    args = item.get("input") if isinstance(item.get("input"), dict) else {"input": item.get("input")}
                    op = "invoke_agent" if name in ("Task", "Agent") else "execute_tool"
                    _rec(unit, lineno, ts, "tool_call", role="assistant", operation=op, model=model,
                         response_id=mid, tool_name=name, tool_call_id=item.get("id"), arguments=args,
                         subagent_type=args.get("subagent_type") if op == "invoke_agent" else None,
                         text=json.dumps(args, sort_keys=True))
            if mid and isinstance(msg.get("usage"), dict):
                # Streaming writes one line per content block, each repeating the message's usage:
                # keep ONE usage per message id (the last line seen = final output count).
                usage_by_msg[mid] = (lineno, ts, msg["usage"], model, msg.get("stop_reason"))
        elif t == "system":
            sub = d.get("subtype")
            if sub == "compact_boundary":
                _rec(unit, lineno, ts, "compaction", role="system", operation="compaction",
                     text=_text_of(d.get("content")))
            else:
                _rec(unit, lineno, ts, "meta", role="system", operation=None, subtype=sub,
                     text=_text_of(d.get("content")))
        elif t in ("permission-mode", "mode"):
            _rec(unit, lineno, ts, "meta", role=None, operation=None, subtype=t,
                 value=d.get("permissionMode") or d.get("mode"), text="")
    for mid, (lineno, ts, u, model, stop) in usage_by_msg.items():
        _rec(unit, lineno, ts, "usage", role="assistant", operation="chat", response_id=mid, model=model,
             finish_reason=stop, usage=_claude_usage(u), usage_dedupe="last_line_per_message_id", text="")
    return unit


def _claude_meta(meta_path: Path, unit: Unit) -> None:
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        unit.edge_kind, unit.edge_fidelity = "spawn", "inferred"
        return
    apply_claude_meta(meta, unit)


def apply_claude_meta(meta: dict, unit: Unit) -> None:
    unit.agent_name = meta.get("agentType") or unit.agent_name
    unit.parent_tool_call_id = meta.get("toolUseId")
    unit.edge_kind = "fork" if meta.get("agentType") == "fork" else "spawn"
    unit.edge_fidelity = "observed"


def claude_file_unit(path: Path, method: str) -> Unit:
    is_sub = path.parent.name == "subagents"
    key = path.stem
    if is_sub:
        key = f"{path.parent.parent.name}.{path.stem}"
    unit = Unit("claude_code", key, None, method, str(path), agent_name=None if is_sub else "main")
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        parse_claude_lines(fh, unit)
    if is_sub:
        unit.parent_conversation_id = unit.conversation_id
        meta = path.with_suffix(".meta.json")
        if meta.exists():
            _claude_meta(meta, unit)
        else:
            unit.edge_kind, unit.edge_fidelity = "spawn", "inferred"
    return unit


def discover_claude(root: Path) -> list[tuple[Path, list[Path]]]:
    """[(main transcript, [its subagent transcripts])] under a projects-shaped root."""
    out = []
    if not root.is_dir():
        return out
    for proj in sorted(root.iterdir()):
        if not proj.is_dir():
            continue
        for main in sorted(proj.glob("*.jsonl")):
            subs = sorted((proj / main.stem / "subagents").glob("agent-*.jsonl"))
            out.append((main, subs))
    return out


# ─── Codex ───────────────────────────────────────────────────────────────────

def _codex_usage(u: dict) -> dict:
    return {"input_inclusive": int(u.get("input_tokens") or 0), "output": int(u.get("output_tokens") or 0),
            "cache_read": int(u.get("cached_input_tokens") or 0),
            "cache_creation": int(u.get("cache_write_input_tokens") or 0),
            "reasoning": int(u.get("reasoning_output_tokens") or 0),
            "convention": "openai_input_includes_cached",
            "raw": dict(u)}


def parse_codex_lines(lines: Iterable[str], unit: Unit) -> Unit:
    seen_resp: set[str] = set()
    model = None
    token_count_events = 0
    for lineno, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        try:
            d = json.loads(raw)
        except json.JSONDecodeError:
            unit.parse_errors += 1
            continue
        if not isinstance(d, dict):
            unit.parse_errors += 1
            continue
        t = d.get("type")
        p = d.get("payload") if isinstance(d.get("payload"), dict) else {}
        pt = p.get("type")
        unit.type_sig.add(f"{t}:{pt or ''}")
        ts = d.get("timestamp")
        if t == "session_meta":
            unit.conversation_id = p.get("session_id") or p.get("id")
            unit.agent_instance_id = p.get("id")
            if p.get("cli_version"):
                unit.versions.add(f"codex/{p['cli_version']}")
            src = p.get("source")
            spawn = src.get("subagent", {}).get("thread_spawn") if isinstance(src, dict) and isinstance(src.get("subagent"), dict) else None
            parent = p.get("parent_thread_id") or (spawn or {}).get("parent_thread_id")
            unit.agent_name = p.get("agent_nickname") or p.get("agent_path") or ("main" if not parent else None)
            if parent:
                unit.parent_conversation_id = parent
                unit.edge_kind = "spawn" if spawn else ("fork" if p.get("forked_from_id") else "spawn")
                unit.edge_fidelity = "observed" if (spawn or p.get("forked_from_id")) else "inferred"
            elif p.get("forked_from_id"):
                unit.parent_conversation_id = p["forked_from_id"]
                unit.edge_kind, unit.edge_fidelity = "fork", "observed"
        elif t == "turn_context":
            model = p.get("model") or model
        elif t == "token_usage_record":
            rid = p.get("response_id")
            if rid and rid in seen_resp:
                continue
            if rid:
                seen_resp.add(rid)
            u = p.get("usage") if isinstance(p.get("usage"), dict) else {}
            _rec(unit, lineno, ts, "usage", role="assistant", operation="chat", response_id=rid, model=model,
                 usage=_codex_usage(u), usage_dedupe="token_usage_record_per_response_id", text="")
        elif t == "compacted":
            _rec(unit, lineno, ts, "compaction", role="system", operation="compaction", text="")
        elif t == "response_item":
            if pt == "message":
                text = _text_of(p.get("content"))
                role = p.get("role")
                is_meta = role != "assistant" and text.lstrip().startswith(("<environment_context", "# AGENTS.md",
                                                                             "<user_instructions", "<permissions"))
                _rec(unit, lineno, ts, "chat", role="user" if role in ("user", "developer") else "assistant",
                     operation="chat", model=model, is_meta=is_meta or role == "developer",
                     human=role == "user" and not is_meta and unit.parent_conversation_id is None, text=text)
            elif pt == "agent_message":
                _rec(unit, lineno, ts, "chat", role="assistant", operation="invoke_agent", model=model,
                     text=_text_of(p.get("content")))
            elif pt == "reasoning":
                _rec(unit, lineno, ts, "reasoning", role="assistant", operation="chat", model=model,
                     text=_text_of(p.get("summary")))
            elif pt in ("function_call", "custom_tool_call", "local_shell_call"):
                args_raw = p.get("arguments") if pt == "function_call" else p.get("input") or p.get("action")
                try:
                    args = json.loads(args_raw) if isinstance(args_raw, str) and pt == "function_call" else args_raw
                except json.JSONDecodeError:
                    args = args_raw
                if not isinstance(args, dict):
                    args = {"input": args}
                name = p.get("name") or pt
                _rec(unit, lineno, ts, "tool_call", role="assistant",
                     operation="invoke_agent" if name in ("spawn_agent", "spawn_subagent") else "execute_tool",
                     model=model, tool_name=name, tool_call_id=p.get("call_id"), arguments=args,
                     text=json.dumps(args, sort_keys=True, default=str))
            elif pt in ("function_call_output", "custom_tool_call_output", "local_shell_call_output"):
                text = _text_of(p.get("output"))
                m = _CODEX_EXIT_RE.search(text)
                is_error = bool(m and m.group(1) != "0") or text.lstrip().startswith(("Script failed", "aborted"))
                den = _denial(text)
                _rec(unit, lineno, ts, "tool_result", role="tool", operation="execute_tool",
                     tool_call_id=p.get("call_id"), is_error=is_error or den is not None, denial=den,
                     text=text, commit_shas=commit_shas(text), fidelity="inferred")
        elif t == "event_msg":
            if pt == "token_count":
                token_count_events += 1   # cumulative snapshots: counted, NEVER summed
            elif pt == "turn_aborted":
                _rec(unit, lineno, ts, "interrupt", role="user", operation=None,
                     interrupt=f"turn_aborted:{p.get('reason') or 'unknown'}", text="")
    unit.type_sig.add(f"token_count_events:{'yes' if token_count_events else 'no'}")
    return unit


def codex_file_unit(path: Path, method: str) -> Unit:
    unit = Unit("codex", path.stem, None, method, str(path))
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        parse_codex_lines(fh, unit)
    unit.unit_key = unit.agent_instance_id or path.stem
    return unit


def discover_codex(root: Path) -> list[Path]:
    return sorted(root.glob("**/rollout-*.jsonl")) if root.is_dir() else []


# ─── opencode (V1 message/part tables, V2 session_message) ──────────────────

OPENCODE_TABLES = ("session", "message", "part", "session_message")


def open_opencode(db: Path) -> sqlite3.Connection:
    """Open read-only AND immutable: no write, no lock, no -wal/-shm creation."""
    return sqlite3.connect(f"file:{db}?immutable=1", uri=True)


def _ms_iso(ms: Any) -> str | None:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OSError):
        return None


def _opencode_usage(tok: dict) -> dict:
    cache = tok.get("cache") if isinstance(tok.get("cache"), dict) else {}
    inp, cr, cw = int(tok.get("input") or 0), int(cache.get("read") or 0), int(cache.get("write") or 0)
    return {"input_inclusive": inp + cr + cw, "output": int(tok.get("output") or 0), "cache_read": cr,
            "cache_creation": cw, "reasoning": int(tok.get("reasoning") or 0),
            "convention": "opencode_input_excludes_cache(+read+write)", "raw": tok}


def opencode_sessions(conn: sqlite3.Connection, limit: int | None = None,
                      session_ids: list[str] | None = None) -> list[tuple]:
    q = ("SELECT id, parent_id, version, agent, model, time_created FROM session")
    args: list = []
    if session_ids:
        q += f" WHERE id IN ({','.join('?' * len(session_ids))})"
        args = list(session_ids)
    q += " ORDER BY time_created DESC"
    if limit:
        q += f" LIMIT {int(limit)}"
    return conn.execute(q, args).fetchall()


def opencode_unit(conn: sqlite3.Connection, srow: tuple, db_path: str) -> Unit:
    sid, parent, version, agent, model, _created = srow
    unit = Unit("opencode", sid, sid, "sqlite_row", f"{db_path}#session={sid}", agent_name=agent or "main",
                agent_instance_id=sid)
    if version:
        unit.versions.add(f"opencode/{version}")
    if parent:
        unit.parent_conversation_id = parent
        unit.edge_kind, unit.edge_fidelity = "spawn", "inferred"
    msgs = conn.execute("SELECT id, time_created, data FROM message WHERE session_id=? ORDER BY time_created, id",
                        (sid,)).fetchall()
    unit.type_sig.add("v1:message" if msgs else "v1:none")
    for mid, tc, data in msgs:
        try:
            m = json.loads(data)
        except json.JSONDecodeError:
            unit.parse_errors += 1
            continue
        role = m.get("role")
        ts = _ms_iso(tc)
        mm = m.get("model")
        mmodel = m.get("modelID") or (mm.get("modelID") if isinstance(mm, dict) else None)
        err = m.get("error") if isinstance(m.get("error"), dict) else None
        if err and err.get("name") == "MessageAbortedError":
            _rec(unit, f"message:{mid}", ts, "interrupt", role="user", operation=None,
                 interrupt="message_aborted", text="")
        parts = conn.execute("SELECT id, time_created, data FROM part WHERE message_id=? ORDER BY time_created, id",
                             (mid,)).fetchall()
        for pid, ptc, pdata in parts:
            try:
                p = json.loads(pdata)
            except json.JSONDecodeError:
                unit.parse_errors += 1
                continue
            pt = p.get("type")
            unit.type_sig.add(f"part:{pt}")
            pts = _ms_iso(ptc)
            line = f"part:{pid}"
            if pt == "text":
                _rec(unit, line, pts, "chat", role="user" if role == "user" else "assistant", operation="chat",
                     model=mmodel, response_id=mid, human=role == "user" and not parent and not p.get("synthetic"),
                     is_meta=bool(p.get("synthetic")), text=p.get("text") or "")
            elif pt == "reasoning":
                _rec(unit, line, pts, "reasoning", role="assistant", operation="chat", model=mmodel,
                     response_id=mid, text=p.get("text") or "")
            elif pt == "tool":
                st = p.get("state") if isinstance(p.get("state"), dict) else {}
                args = st.get("input") if isinstance(st.get("input"), dict) else {"input": st.get("input")}
                name = p.get("tool")
                _rec(unit, line, pts, "tool_call", role="assistant",
                     operation="invoke_agent" if name == "task" else "execute_tool", model=mmodel,
                     response_id=mid, tool_name=name, tool_call_id=p.get("callID"), arguments=args,
                     text=json.dumps(args, sort_keys=True, default=str))
                status = st.get("status")
                if status in ("completed", "error"):
                    text = _text_of(st.get("output")) if status == "completed" else _text_of(st.get("error"))
                    aborted = status == "error" and "aborted" in text.lower()
                    if aborted:
                        _rec(unit, line, pts, "interrupt", role="user", operation=None,
                             interrupt="tool_aborted", text="")
                    _rec(unit, line, pts, "tool_result", role="tool", operation="execute_tool",
                         tool_call_id=p.get("callID"), is_error=status == "error",
                         denial=_denial(text) if status == "error" else None, text=text,
                         commit_shas=commit_shas(text))
            elif pt == "compaction":
                _rec(unit, line, pts, "compaction", role="system", operation="compaction", text="")
        if role == "assistant" and isinstance(m.get("tokens"), dict):
            fin = m.get("finish")
            _rec(unit, f"message:{mid}", ts, "usage", role="assistant", operation="chat", response_id=mid,
                 model=mmodel, finish_reason=fin, usage=_opencode_usage(m["tokens"]),
                 usage_dedupe="message_row_tokens(step-finish parts not summed)", fidelity="inferred", text="")
    try:
        v2 = conn.execute("SELECT id, type, seq, time_created, data FROM session_message WHERE session_id=? "
                          "ORDER BY seq", (sid,)).fetchall()
    except sqlite3.OperationalError:
        v2 = []
    if v2:
        unit.type_sig.add("v2:session_message")
    for rid, typ, seq, tc, data in v2:
        try:
            p = json.loads(data)
        except json.JSONDecodeError:
            unit.parse_errors += 1
            continue
        unit.type_sig.add(f"v2:{typ}")
        role = p.get("role") if isinstance(p, dict) else None
        _rec(unit, f"session_message:{seq}", _ms_iso(tc), "chat", role=role or "assistant", operation="chat",
             text=_text_of(p.get("content") if isinstance(p, dict) else p), fidelity="inferred", v2_type=typ)
    return unit


# ─── tarball streaming ───────────────────────────────────────────────────────

def iter_tarball_units(path: Path, limit: int | None = None) -> Iterator[Unit]:
    """Stream an ai-sessions tarball (never extracted to disk) and yield transcript units.

    Member prefixes: projects/ and .claude/projects/ = Claude Code; sessions/ and .codex/sessions/ = Codex.
    Subagent edge kind comes from a sibling .meta.json only when it precedes the transcript in the
    archive; otherwise the edge is recorded as spawn with fidelity=inferred.
    """
    metas: dict[str, dict] = {}
    n = 0
    with tarfile.open(path, mode="r|gz") as tf:
        for member in tf:
            if not member.isfile():
                continue
            name = member.name.lstrip("./")
            is_claude = name.startswith(("projects/", "claude/projects/")) or member.name.startswith(".claude/projects/")
            is_codex = name.startswith(("sessions/", "codex/sessions/")) or member.name.startswith(".codex/sessions/")
            if is_claude and name.endswith(".meta.json") and "/subagents/" in name:
                fh = tf.extractfile(member)
                if fh:
                    try:
                        metas[name[:-len(".meta.json")]] = json.loads(fh.read().decode("utf-8", "replace"))
                    except json.JSONDecodeError:
                        pass
                continue
            if not name.endswith(".jsonl"):
                continue
            fh = tf.extractfile(member)
            if fh is None:
                continue
            lines = fh.read().decode("utf-8", "replace").splitlines()
            src = f"{path}::{member.name}"
            p = Path(name)
            if is_claude:
                is_sub = p.parent.name == "subagents"
                key = f"{p.parent.parent.name}.{p.stem}" if is_sub else p.stem
                unit = Unit("claude_code", key, None, "tarball_member", src, agent_name=None if is_sub else "main")
                parse_claude_lines(lines, unit)
                if is_sub:
                    unit.parent_conversation_id = unit.conversation_id
                    meta = metas.get(name[:-len(".jsonl")])
                    if meta:
                        apply_claude_meta(meta, unit)
                    else:
                        unit.edge_kind, unit.edge_fidelity = "spawn", "inferred"
            elif is_codex and p.name.startswith("rollout-"):
                unit = Unit("codex", p.stem, None, "tarball_member", src)
                parse_codex_lines(lines, unit)
                unit.unit_key = unit.agent_instance_id or p.stem
            else:
                continue
            yield unit
            n += 1
            if limit and n >= limit:
                return


# ─── sample / corpus selection ───────────────────────────────────────────────

def live_claude_newer_than_vault(live_root: Path = LIVE_CLAUDE, vault_claude: Path = VAULT_ROOT / "epyc/claude",
                                 since: datetime | None = None) -> list[Path]:
    """Live main transcripts modified after the last vault sync whose vault copy is missing or shorter."""
    since = since or last_vault_sync()
    if since is None or not live_root.is_dir():
        return []
    cutoff = since.timestamp()
    out = []
    for main, _subs in discover_claude(live_root):
        st = main.stat()
        if st.st_mtime <= cutoff:
            continue
        vcopy = vault_claude / main.relative_to(live_root)
        if not vcopy.exists() or vcopy.stat().st_size < st.st_size:
            out.append(main)
    return out


def select_vault_units(harness: str, limit: int, vault: Path = VAULT_ROOT, tenant: str = "epyc",
                       min_bytes: int = 2048, max_bytes: int = 8 << 20) -> Iterator[Unit]:
    """Most-recent ``limit`` sessions of ``harness`` from the vault (subagents ride with their main)."""
    if harness == "claude_code":
        pairs = discover_claude(vault / tenant / "claude")
        pairs = [(m, s) for m, s in pairs if min_bytes <= m.stat().st_size and (not max_bytes or m.stat().st_size <= max_bytes)]
        pairs.sort(key=lambda ms: ms[0].stat().st_mtime, reverse=True)
        for main, subs in (pairs[:limit] if limit else pairs):
            yield claude_file_unit(main, "vault_file")
            for s in subs:
                yield claude_file_unit(s, "vault_file")
    elif harness == "codex":
        files = [f for f in discover_codex(vault / tenant / "codex")
                 if min_bytes <= f.stat().st_size and (not max_bytes or f.stat().st_size <= max_bytes)]
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        for f in (files[:limit] if limit else files):
            yield codex_file_unit(f, "vault_file")
    else:
        raise ValueError(harness)


def select_opencode_units(db: Path, limit: int, session_ids: list[str] | None = None) -> Iterator[Unit]:
    conn = open_opencode(db)
    try:
        for row in opencode_sessions(conn, limit=limit, session_ids=session_ids):
            yield opencode_unit(conn, row, str(db))
    finally:
        conn.close()
