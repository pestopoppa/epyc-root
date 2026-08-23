#!/usr/bin/env python3
"""RTG-49 FM-1: per-subagent timing collector (fanout_timing.v1).

Reads Claude Code and Codex transcripts OFFLINE (zero network, zero inference,
zero writes to the corpus) and emits a durable JSONL record of per-workflow
fan-out metrics. This turns the F-15 assertion ("did a main actually fan out,
or work serially?") into a number for every session already on disk.

Metric definitions follow OrchBench Appendix D-I real-side definitions as
scoped in handoffs/active/fleet-fanout-measurement.md FM-1:

  declared_agents        subagent transcripts found for the workflow (a main
                         that issued a Task/SendMessage leaves one file/rollout
                         per subagent — the declaration IS the file).
  started_agents         subagents with at least one timestamped record.
  completed_agents       subagents with a finish: last record present and
                         timestamped (Claude), or a terminal record
                         (task_complete | turn_aborted — Codex).
  workflow_span_s        max finish - min start over ALL records of the
                         workflow (main session records included).
  parallel_utilization   SUM(subagent active time) /
                         (max overlapping subagents * workflow span).
  workflow_depth         max chain length over REAL parent->child edges
                         (main = 1). NEVER keyword matching.
  max_overlapping_subagents  sweep-line max over [start, finish] intervals.

EDGE EXTRACTION — real fields only, no inference:

  Claude: the parent->child edge is the record-level `parentUuid` link when it
  resolves to a DIFFERENT agent's uuid (a Task/SendMessage-style edge: the
  child's first records reference the spawning agent's message uuid; measured
  291 such cross-file edges in a 6-session sample). Default parent is the
  session (the `sessionId` on every subagent record is the real main->child
  edge). `agent-*.meta.json` `spawnDepth` (workflow layout) is used when
  present. `parentUuid` that resolves within the same file (message-chain
  self-links) is ignored.
  Codex: `payload.source.subagent.thread_spawn.parent_thread_id` resolves to
  the parent rollout's `payload.id`; `thread_spawn.depth` corroborates.

QUEUE JOIN: queue_task_ids is matched by task-id tokens found in workflow
metadata (session file content / rollout meta + first records). No match => []
is emitted — a join is never fabricated.

DETERMINISM: re-running the same command on the same corpus produces
byte-identical output. `collected_at` is therefore the latest event timestamp
observed in the corpus (a corpus property), NOT the wall clock; `collector_sha256`
is the sha256 of this source file. Subagents and workflows are emitted sorted
by id; JSON keys sorted. Writes are atomic (tmp + rename).

D9-ack: operator tasking 2026-08-23 (RTG-49 FM-1).
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "fanout_timing.v1"

# Mirrors scripts/coordination/tmux_adapter.py:_ROLLOUT_TERMINAL (line 1313) —
# the adapter's 400/400 corpus verification of this resting tail applies here.
CODEX_TERMINAL = frozenset({"task_complete", "turn_aborted"})

_EPOCH_SENTINEL = "1970-01-01T00:00:00Z"
_TASK_ID_COORD_RE = re.compile(r"^(.*)--[^-]+-L\d+$")
_DEFAULT_QUEUE = Path("/workspace/coordination/session-bus/queue.jsonl")

_QUEUE_OP_TYPES = frozenset({"queue-operation", "ai-title", "mode", "user", "assistant", "system"})
_CLAUDE_SUBAGENT_GLOB = ("agent-*.jsonl", "workflows/*/agent-*.jsonl")
_CLAUDE_META_GLOB = ("workflows/*/agent-*.meta.json",)


# --------------------------------------------------------------------------- helpers


def _parse_ts(raw):
    """RFC3339 -> epoch seconds float, or None. Accepts 'Z' and offsets."""
    if not isinstance(raw, str) or not raw:
        return None
    text = raw.strip()
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None


def _r3(value):
    return round(value, 3)


def _r6(value):
    return round(value, 6)


def _fmt_rfc3339(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _collector_sha256():
    return hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()


def _atomic_write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


class _MalformedBucket:
    def __init__(self):
        self.count = 0
        self.torn = False

    def parse(self, path):
        """Parse a JSONL file, counting malformed lines. Sets `torn` when the
        file's LAST non-empty line is not parseable (a truncated tail)."""
        records = []
        self.torn = False
        last_line = None
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip():
                    continue
                last_line = line
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    self.count += 1
        if last_line is not None:
            try:
                json.loads(last_line)
            except json.JSONDecodeError:
                self.torn = True
        return records


def _load_queue_ids(queue_path):
    if queue_path is None or not Path(queue_path).is_file():
        return []
    ids = []
    try:
        with open(queue_path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                tid = r.get("task_id")
                if isinstance(tid, str) and tid:
                    ids.append(tid)
    except OSError:
        return []
    return sorted(set(ids))


def _queue_tokens(task_ids):
    """Match tokens per queue task id: the full id and the id without its
    trailing -L<line> coordinate (e.g. 'x--010-L512' -> 'x--010')."""
    tokens = {}
    for tid in task_ids:
        cands = {tid}
        m = _TASK_ID_COORD_RE.match(tid)
        if m:
            cands.add(m.group(1))
        tokens[tid] = cands
    return tokens


def _match_queue_ids(text, tokens):
    if not tokens:
        return []
    found = []
    for tid, cands in tokens.items():
        if any(c in text for c in cands):
            found.append(tid)
    return sorted(found)


def _sweep_max_overlap(intervals):
    """intervals: iterable of (start_epoch, finish_epoch). Max concurrent."""
    events = []
    for start, finish in intervals:
        if start is None or finish is None or finish < start:
            continue
        events.append((start, 1))
        events.append((finish, -1))
    if not events:
        return 0
    events.sort()
    active = best = 0
    for _ts, delta in events:
        active += delta
        if active > best:
            best = active
    return best


def _active_sum(intervals):
    return sum((finish - start) for start, finish in intervals
               if start is not None and finish is not None and finish >= start)


# --------------------------------------------------------------------------- shared metric math


def _workflow_row(source, workflow_id, declared, subagents, span_start, span_end,
                  queue_task_ids, latest_ts):
    """subagents: list of dicts {id,parent,depth,start_ts,finish_ts,active_s,
    start_epoch,finish_epoch,completed}."""
    started = sum(1 for s in subagents if s["start_epoch"] is not None)
    completed = sum(1 for s in subagents if s["completed"])
    span_s = _r3((span_end - span_start)) if (span_start is not None and span_end is not None) else 0.0
    intervals = [(s["start_epoch"], s["finish_epoch"]) for s in subagents]
    max_overlap = _sweep_max_overlap(intervals)
    active = _active_sum(intervals)
    if max_overlap > 0 and span_s > 0:
        parallel_utilization = _r6(active / (max_overlap * span_s))
    else:
        parallel_utilization = 0.0

    memo = {}

    def depth_of(agent_id):
        if agent_id in memo:
            return memo[agent_id]
        if agent_id == "main":
            memo[agent_id] = 1
            return 1
        parent = next((s["parent"] for s in subagents if s["id"] == agent_id), "main")
        if parent == agent_id:
            memo[agent_id] = 2
            return 2
        child = depth_of(parent) + 1
        declared_depth = next((s["declared_depth"] for s in subagents if s["id"] == agent_id), 0)
        memo[agent_id] = max(child, declared_depth)
        return memo[agent_id]

    depth_values = [depth_of(s["id"]) for s in subagents] or [1]
    workflow_depth = max(1, *depth_values)

    return {
        "schema": SCHEMA,
        "source": source,
        "workflow_id": workflow_id,
        "declared_agents": declared,
        "started_agents": started,
        "completed_agents": completed,
        "workflow_span_s": span_s,
        "parallel_utilization": parallel_utilization,
        "workflow_depth": workflow_depth,
        "max_overlapping_subagents": max_overlap,
        "subagents": [{
            "id": s["id"],
            "parent": s["parent"],
            "depth": depth_of(s["id"]),
            "start_ts": s["start_ts"],
            "finish_ts": s["finish_ts"],
            "active_s": _r3(s["active_s"]),
        } for s in sorted(subagents, key=lambda x: x["id"])],
        "queue_task_ids": queue_task_ids,
        "collected_at": _fmt_rfc3339(latest_ts) if latest_ts is not None else _EPOCH_SENTINEL,
        "collector_sha256": _collector_sha256(),
    }


# --------------------------------------------------------------------------- Claude


def _scan_uuid_agents(path):
    """uuid -> agentId across a whole transcript file. The parentUuid edge
    resolver needs subagent uuids too, so this pre-pass covers every file.
    Malformed lines are not double-counted: the parse pass counts them."""
    mapping = {}
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            uid = r.get("uuid")
            aid = r.get("agentId")
            if isinstance(uid, str) and isinstance(aid, str):
                mapping[uid] = aid
    return mapping


def _parse_claude_session_file(path, bucket):
    records = bucket.parse(path)
    uuid_to_agent = {}
    timestamps = []
    meta_text = []
    for r in records:
        uid = r.get("uuid")
        if isinstance(uid, str) and r.get("agentId"):
            uuid_to_agent[uid] = r["agentId"]
        ts = _parse_ts(r.get("timestamp"))
        if ts is not None:
            timestamps.append(ts)
        if r.get("type") in _QUEUE_OP_TYPES:
            content = r.get("content")
            if not isinstance(content, str):
                message = r.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                if isinstance(content, list):
                    content = json.dumps(content)
            if isinstance(content, str):
                meta_text.append(content)
    return records, uuid_to_agent, timestamps, "\n".join(meta_text)


def _parse_claude_subagent(path, bucket, uuid_to_agent):
    """-> dict(subagent) or None. Records without agentId are skipped (e.g.
    journal.jsonl is already excluded by the agent-*.jsonl glob, but a foreign
    file must not crash the walk)."""
    records = bucket.parse(path)
    if not records:
        return None
    agent_id = None
    parent = None
    start_ts = finish_ts = None
    start_epoch = finish_epoch = None
    last_has_ts = False
    meta_text = []
    for r in records:
        aid = r.get("agentId")
        if isinstance(aid, str):
            if agent_id is None:
                agent_id = aid
            ts = _parse_ts(r.get("timestamp"))
            if ts is not None:
                if start_epoch is None:
                    start_epoch, start_ts = ts, r.get("timestamp")
                finish_epoch, finish_ts = ts, r.get("timestamp")
                last_has_ts = True
            else:
                last_has_ts = False
            pu = r.get("parentUuid")
            if parent is None and isinstance(pu, str) and uuid_to_agent.get(pu) not in (None, aid):
                parent = uuid_to_agent[pu]
            if len(meta_text) < 3:
                message = r.get("message")
                if isinstance(message, dict):
                    message = message.get("content")
                if isinstance(message, list):
                    message = json.dumps(message)
                if isinstance(message, str):
                    meta_text.append(message)
    if agent_id is None:
        return None
    return {
        "id": agent_id,
        "parent": parent if parent is not None else "main",
        "start_ts": start_ts,
        "finish_ts": finish_ts,
        "start_epoch": start_epoch,
        "finish_epoch": finish_epoch,
        "active_s": (finish_epoch - start_epoch) if (start_epoch is not None and finish_epoch is not None) else 0.0,
        "completed": start_epoch is not None and last_has_ts and not bucket.torn,
        "declared_depth": 0,
        "meta_text": "\n".join(meta_text),
    }


def collect_claude(root, queue_path=None, stats=None):
    root = Path(root)
    if stats is not None:
        stats.setdefault("subagent_files", 0)
        stats.setdefault("malformed_lines", 0)
        stats.setdefault("workflows", 0)
        stats.setdefault("subagents", 0)
    bucket = _MalformedBucket()
    queue_tokens = _queue_tokens(_load_queue_ids(queue_path))
    rows = []
    session_files = sorted(root.glob("*.jsonl"))
    session_dirs = sorted(d for d in root.iterdir() if d.is_dir())
    sids = sorted({p.name[:-6] for p in session_files} | {d.name for d in session_dirs})

    for sid in sids:
        session_path = root / f"{sid}.jsonl"
        session_dir = root / sid
        records, _session_map, timestamps, session_meta = (
            _parse_claude_session_file(session_path, bucket)
            if session_path.is_file()
            else ([], {}, [], "")
        )
        subagent_paths = []
        for pattern in _CLAUDE_SUBAGENT_GLOB:
            subagent_paths.extend((session_dir / "subagents").glob(pattern))
        # uuid -> agentId over the WHOLE session (session file + every subagent
        # file): a subagent's parentUuid can resolve to another subagent's uuid.
        uuid_to_agent = dict(_session_map)
        for path in subagent_paths:
            uuid_to_agent.update(_scan_uuid_agents(path))
        subagents = []
        for path in sorted(subagent_paths):
            sub = _parse_claude_subagent(path, bucket, uuid_to_agent)
            if sub is not None:
                subagents.append(sub)
        # spawnDepth from the workflow layout meta files corroborates depth.
        for pattern in _CLAUDE_META_GLOB:
            for meta_path in (session_dir / "subagents").glob(pattern):
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                spawn = meta.get("spawnDepth")
                agent_id = meta_path.name[len("agent-"):-len(".meta.json")]
                if isinstance(spawn, int) and spawn >= 0:
                    for sub in subagents:
                        if sub["id"] == agent_id:
                            sub["declared_depth"] = max(sub["declared_depth"], spawn + 1)

        span_epochs = timestamps + [ts for s in subagents
                                    for ts in (s["start_epoch"], s["finish_epoch"]) if ts is not None]
        span_start = min(span_epochs) if span_epochs else None
        span_end = max(span_epochs) if span_epochs else None
        latest = span_end

        meta_text = session_meta
        for sub in subagents:
            meta_text += "\n" + sub["meta_text"]
        queue_hits = _match_queue_ids(meta_text, queue_tokens)

        rows.append(_workflow_row(
            "claude", sid, len(subagents), subagents, span_start, span_end,
            queue_hits, latest,
        ))
        if stats is not None:
            stats["subagent_files"] += len(subagent_paths)
    if stats is not None:
        stats["malformed_lines"] += bucket.count
        stats["workflows"] += len(rows)
        stats["subagents"] += sum(r["declared_agents"] for r in rows)
    return rows


# --------------------------------------------------------------------------- Codex


def _parse_codex_rollout(path, bucket):
    records = bucket.parse(path)
    if not records:
        return None
    first = records[0]
    payload = first.get("payload") or {}
    source = payload.get("source")
    # Classification follows thread_source (the same signal tmux_adapter uses);
    # the source.subagent dict is the metadata carrier. Either one marks a
    # subagent; a main rollout declares neither.
    is_subagent = (
        payload.get("thread_source") == "subagent"
        or isinstance(source, dict) and isinstance(source.get("subagent"), dict)
    )
    spawn = {}
    if isinstance(source, dict) and isinstance(source.get("subagent"), dict):
        spawn = source["subagent"].get("thread_spawn") or {}
    start_ts = first.get("timestamp")
    start_epoch = _parse_ts(start_ts)
    last = records[-1]
    finish_ts = last.get("timestamp")
    finish_epoch = _parse_ts(finish_ts)
    completed = isinstance(last.get("payload"), dict) and last["payload"].get("type") in CODEX_TERMINAL
    meta_text = json.dumps(payload, ensure_ascii=True)[:20000]
    return {
        "file": path,
        "id": payload.get("id"),
        "session_id": payload.get("session_id"),
        "parent_thread_id": spawn.get("parent_thread_id") or payload.get("parent_thread_id"),
        "spawn_depth": spawn.get("depth"),
        "is_subagent": is_subagent,
        "start_ts": start_ts,
        "finish_ts": finish_ts,
        "start_epoch": start_epoch,
        "finish_epoch": finish_epoch,
        "active_s": (finish_epoch - start_epoch) if (start_epoch is not None and finish_epoch is not None) else 0.0,
        "completed": completed and start_epoch is not None,
        "meta_text": meta_text,
    }


def collect_codex(root, queue_path=None, stats=None):
    root = Path(root)
    if stats is not None:
        stats.setdefault("rollout_files", 0)
        stats.setdefault("malformed_lines", 0)
        stats.setdefault("workflows", 0)
        stats.setdefault("subagents", 0)
    bucket = _MalformedBucket()
    queue_tokens = _queue_tokens(_load_queue_ids(queue_path))
    rollouts = []
    for path in sorted(root.glob("**/rollout-*.jsonl")):
        ro = _parse_codex_rollout(path, bucket)
        if ro is not None:
            rollouts.append(ro)

    by_id = {ro["id"]: ro for ro in rollouts if ro["id"]}
    workflows = {}
    for ro in rollouts:
        wid = ro["session_id"] or ro["id"]
        workflows.setdefault(wid, []).append(ro)

    rows = []
    for wid in sorted(workflows):
        files = workflows[wid]
        mains = [f for f in files if not f["is_subagent"]]
        subs = [f for f in files if f["is_subagent"]]
        for sub in subs:
            parent_thread = by_id.get(sub["parent_thread_id"])
            if parent_thread is not None:
                parent_id = parent_thread["id"]
                if parent_thread["is_subagent"]:
                    sub["parent"] = parent_id
                else:
                    sub["parent"] = "main"
            else:
                sub["parent"] = "main"
            sub["declared_depth"] = sub["spawn_depth"] + 1 if isinstance(sub["spawn_depth"], int) else 0

        subagent_rows = [{
            "id": f["id"] or f["file"].name,
            "parent": f.get("parent", "main"),
            "start_ts": f["start_ts"],
            "finish_ts": f["finish_ts"],
            "start_epoch": f["start_epoch"],
            "finish_epoch": f["finish_epoch"],
            "active_s": f["active_s"],
            "completed": f["completed"],
            "declared_depth": f["declared_depth"],
        } for f in subs]

        span_epochs = [ts for f in files for ts in (f["start_epoch"], f["finish_epoch"]) if ts is not None]
        span_start = min(span_epochs) if span_epochs else None
        span_end = max(span_epochs) if span_epochs else None
        latest = span_end

        meta_text = "\n".join(f["meta_text"] for f in files)
        queue_hits = _match_queue_ids(meta_text, queue_tokens)

        rows.append(_workflow_row(
            "codex", str(wid), len(subs), subagent_rows, span_start, span_end,
            queue_hits, latest,
        ))
        if stats is not None:
            stats["rollout_files"] += len(files)
    if stats is not None:
        stats["malformed_lines"] += bucket.count
        stats["workflows"] += len(rows)
        stats["subagents"] += sum(r["declared_agents"] for r in rows)
    return rows


# --------------------------------------------------------------------------- merge / CLI


def merge(claude_path, codex_path, output):
    rows = []
    for path, source in ((claude_path, "claude"), (codex_path, "codex")):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                if r.get("schema") != SCHEMA or r.get("source") != source:
                    raise ValueError(f"{path}: row schema/source mismatch")
                rows.append(r)
    rows.sort(key=lambda r: (r["source"], r["workflow_id"]))
    _atomic_write_jsonl(output, rows)
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="fanout_timing.py",
        description="RTG-49 FM-1 per-subagent timing collector (fanout_timing.v1). "
                    "Offline only: zero network, zero inference, corpus read-only.",
    )
    parser.add_argument("--queue", type=Path, default=_DEFAULT_QUEUE,
                        help="queue.jsonl path for task-id joins (default: canonical /workspace path)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_claude = sub.add_parser("collect-claude", help="collect from a Claude projects dir")
    p_claude.add_argument("--root", required=True, help="e.g. ~/.claude/projects/-workspace")
    p_claude.add_argument("--output", required=True)

    p_codex = sub.add_parser("collect-codex", help="collect from a Codex sessions dir")
    p_codex.add_argument("--root", required=True, help="e.g. ~/.codex/sessions")
    p_codex.add_argument("--output", required=True)

    p_merge = sub.add_parser("merge", help="merge claude+codex records into one file")
    p_merge.add_argument("--claude", required=True)
    p_merge.add_argument("--codex", required=True)
    p_merge.add_argument("--output", required=True)

    args = parser.parse_args(argv)
    stats = {"workflows": 0, "subagents": 0, "subagent_files": 0, "rollout_files": 0, "malformed_lines": 0}

    if args.cmd == "collect-claude":
        rows = collect_claude(args.root, queue_path=args.queue, stats=stats)
        _atomic_write_jsonl(args.output, rows)
        print(f"claude: {len(rows)} workflows, {stats['subagents']} subagents, "
              f"{stats['subagent_files']} subagent files, {stats['malformed_lines']} malformed lines "
              f"-> {args.output}", file=sys.stderr)
    elif args.cmd == "collect-codex":
        rows = collect_codex(args.root, queue_path=args.queue, stats=stats)
        _atomic_write_jsonl(args.output, rows)
        print(f"codex: {len(rows)} workflows, {stats['subagents']} subagents, "
              f"{stats['rollout_files']} rollout files, {stats['malformed_lines']} malformed lines "
              f"-> {args.output}", file=sys.stderr)
    elif args.cmd == "merge":
        rows = merge(args.claude, args.codex, args.output)
        print(f"merge: {len(rows)} rows -> {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
