#!/usr/bin/env python3
"""RTG-49 FM-1/FM-5/FM-6: per-subagent timing + outcome collector (fanout_timing.v2).

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

FM-5 — PER-SUBAGENT OUTCOME ACCOUNTING (schema v2)
--------------------------------------------------
Every subagent carries an `outcome` bucket, an `outcome_basis` naming the
signal that decided it, and a `tokens` block. The ladder is evaluated in this
order and the FIRST match wins:

  aborted    the run did not end normally. Claude: the parent's
             `<task-notification>` for this agentId carries a `<status>` other
             than `completed` (observed: killed / failed / stopped), or the
             transcript tail is torn. Codex: the terminal record is
             `turn_aborted`.
  blocked    the run ended on an EXTERNAL blocker it could not clear. Claude:
             the last record is `isApiErrorMessage: true` (observed form: "You
             have hit your session limit"). Codex: terminal payload `error` /
             `stream_error`. This is a LOWER BOUND — neither transcript format
             carries a general "I was blocked" marker, so a subagent that wrote
             a blocked report in prose is NOT counted here (it lands in
             produced-and-discarded / orphan). Prose is never read as a signal.
  no-output  no final report text at all (Claude: no assistant text block;
             Codex: no `agent_message` and no `task_complete.last_agent_message`).
  produced-and-used       output exists AND either (a) a path the subagent
             itself MUTATED was touched by a git commit at or after it finished,
             or (b) one of its reconnection targets (see FM-6) was mentioned by
             the PARENT transcript after it finished. (a) is deliberately
             restricted to written paths: a path the subagent merely CITED,
             committed later by somebody else, is not evidence its work was used.
  produced-and-discarded  output exists, the parent side is observable, and
             neither (a) nor (b) fired.
  unknown    output exists but the used/discarded split is NOT observable: the
             parent transcript is missing from the corpus, or the parent
             mention index hit its byte cap before the subagent's window. NEVER
             folded into another bucket — an unknown folded into a bucket is
             precisely the failure this handoff exists to prevent.

SELF-MATCH GUARD: a parent transcript quotes the child's own report verbatim
(Claude via `<task-notification><result>`, Codex by replaying the child's
`last_agent_message`). Those regions can never count as parent REUSE, or every
subagent would grade itself "used". Claude notification records are dropped from
the index outright; on both backends a candidate hit is rejected when the
child's report signature (first 80 chars) sits within +/-4000 chars of it.

TOKENS: Claude sums `message.usage` over the subagent's own assistant records;
Codex takes the LAST `token_count.info.total_token_usage` of the rollout
(cumulative by construction). Two totals are carried, because both backends
re-charge the resent prefix on every turn and a long agent therefore inflates:

  total  every token processed  (input + output + cache_creation + cache_read)
  new    the non-cached part    (input + output + cache_creation)

`report` publishes the FM-5 share on BOTH. Main/parent tokens are NOT in the
denominator: the target metric is the share of FAN-OUT tokens (subagent tokens)
spent on work that was never used.

FM-6 — RECONNECTION REQUIREMENT (schema v2)
-------------------------------------------
A subagent counts toward the measured fan-out width only if its OUTPUT links to
a backlog row or an artifact path. Linkage is structural, never prose:

  output_paths   path-shaped tokens in the final report that resolve to a path
                 KNOWN TO GIT in one of the configured roots (a path nobody has
                 ever committed is not an artifact path).
  output_tasks   queue.jsonl task ids appearing in the final report.
  written_paths  paths the subagent itself mutated (Claude: Edit/Write/
                 NotebookEdit/MultiEdit `file_path`. Codex: `apply_patch`
                 targets inside `exec_command`. Codex shell redirects and
                 heredocs are NOT parsed, so codex written_paths is a lower
                 bound and the orphan rate on that backend is an UPPER bound).

`orphan = not (output_paths or output_tasks or written_paths)`.
`measured_fanout_width` is the max-overlap sweep restricted to NON-orphan
subagents; `max_overlapping_subagents` (the v1 field) keeps the orphan-blind
value so the two can be compared. `declared_agents` is likewise unchanged.

SCHEMA COMPATIBILITY: v2 is a strict SUPERSET of v1 — every v1 field keeps its
v1 meaning and value. `merge` and `report` read both v1 and v2 rows; a v1 row
simply carries no outcome fields, and `report` counts those subagents under
`schema_v1_no_outcome` rather than inventing a bucket for them.

D9-ack: operator tasking 2026-08-23 (RTG-49 FM-1), 2026-09-07 (FM-5/FM-6).
"""

import argparse
import bisect
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "fanout_timing.v2"
SCHEMA_V1 = "fanout_timing.v1"
READABLE_SCHEMAS = frozenset({SCHEMA_V1, SCHEMA})

#: FM-5 buckets, in ladder order. `unknown` is a real bucket, never a fold.
OUTCOME_BUCKETS = (
    "produced-and-used",
    "produced-and-discarded",
    "no-output",
    "blocked",
    "aborted",
    "unknown",
)

# Mirrors scripts/coordination/tmux_adapter.py:_ROLLOUT_TERMINAL (line 1313) —
# the adapter's 400/400 corpus verification of this resting tail applies here.
CODEX_TERMINAL = frozenset({"task_complete", "turn_aborted"})

_EPOCH_SENTINEL = "1970-01-01T00:00:00Z"
_TASK_ID_COORD_RE = re.compile(r"^(.*)--[^-]+-L\d+$")
_DEFAULT_QUEUE = Path("/workspace/coordination/session-bus/queue.jsonl")

_QUEUE_OP_TYPES = frozenset({"queue-operation", "ai-title", "mode", "user", "assistant", "system"})
_CLAUDE_SUBAGENT_GLOB = ("agent-*.jsonl", "workflows/*/agent-*.jsonl")
_CLAUDE_META_GLOB = ("workflows/*/agent-*.meta.json",)

# --- FM-5 / FM-6 constants -------------------------------------------------

#: Claude structured file-mutating tools. A Bash `>` redirect is NOT parsed —
#: written_paths is deliberately a lower bound rather than a guess.
CLAUDE_MUTATING_TOOLS = frozenset({"Edit", "Write", "NotebookEdit", "MultiEdit"})

#: Codex terminal payloads that mean "did not end normally" / "external blocker".
CODEX_ABORTED = frozenset({"turn_aborted"})
CODEX_BLOCKED = frozenset({"error", "stream_error"})

#: The only Claude task-notification status that means a normal end.
CLAUDE_OK_STATUS = "completed"

#: Path-shaped token. Must contain a separator; resolution against the git path
#: index (below) is what turns a candidate into an artifact path.
_PATH_CANDIDATE_RE = re.compile(r"[A-Za-z0-9_.@+-]+(?:/[A-Za-z0-9_.@+-]+)+")
_NOTIFICATION_RE = re.compile(r"<task-notification>(.*?)</task-notification>", re.S)
_NOTIF_TASK_RE = re.compile(r"<task-id>\s*([^<\s]+)\s*</task-id>")
_NOTIF_STATUS_RE = re.compile(r"<status>\s*([^<]*?)\s*</status>")
_NOTIF_RESULT_RE = re.compile(r"<result>(.*?)</result>", re.S)
#: `*** Add File: p` / `*** Update File: p` / `*** Delete File: p` in apply_patch.
_APPLY_PATCH_RE = re.compile(r"\*\*\* (?:Add|Update|Delete) File:\s*([^\s\"\\]+)")

_WORKSPACE = Path("/workspace")
#: First segments that mark a filesystem CONTAINER rather than a repo. Only a
#: path under one of these is eligible for suffix resolution (Reconnector.resolve).
_CONTAINER_ROOTS = frozenset({"mnt", "home", "workspace", "var", "opt", "srv", "repos"})
_DEFAULT_GIT_ROOTS = (
    "/workspace",
    "/workspace/repos/epyc-orchestrator",
    "/workspace/repos/epyc-inference-research",
)

#: Bytes of parent transcript retained for the reuse index. Beyond this the
#: index is TRUNCATED and affected subagents grade `unknown`, never `discarded`.
PARENT_INDEX_CAP = 512 * 1024 * 1024
#: Half-window around a candidate hit searched for the child's own report
#: signature (the self-match guard).
SELF_MATCH_WINDOW = 4000
#: Length of the child report prefix used as that signature.
SELF_MATCH_SIG_LEN = 80


def _empty_token_block():
    """`total` counts every token PROCESSED (the re-sent/cached prefix included,
    which both backends re-charge every turn); `new` excludes the cache-read
    prefix and is the fairer denominator for a long-running agent. FM-5 shares
    are reported on both — see outcome_report()."""
    return {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0,
            "new": 0, "total": 0}


def _normalize_repo_path(raw):
    """Strip absolute/relative decoration so a cited path can be looked up in
    the git path index. Returns '' when nothing usable remains."""
    text = raw.strip().strip("`'\"(),;:")
    if not text:
        return ""
    for prefix in ("/workspace/", "workspace/", "/mnt/raid0/llm/epyc-root/"):
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    while text.startswith("./"):
        text = text[2:]
    # Sentence punctuation: a report routinely ends a sentence with the path.
    text = text.rstrip(".,;:)")
    return text.strip("/")


class GitPathIndex:
    """path -> latest commit epoch, over every commit reachable from --all.

    A path is keyed BOTH repo-relative and workspace-relative, because a
    subagent cites `scripts/x.py` in the orchestrator repo and `repos/
    epyc-orchestrator/scripts/x.py` from the root repo interchangeably.
    """

    def __init__(self, mapping=None):
        self._paths = dict(mapping or {})
        self.roots = []

    def __contains__(self, path):
        return path in self._paths

    def __len__(self):
        return len(self._paths)

    def landed_after(self, paths, epoch):
        """True when any path was touched by a commit at/after `epoch`."""
        if epoch is None:
            return False
        for path in paths:
            at = self._paths.get(path)
            if at is not None and at >= epoch:
                return True
        return False

    @classmethod
    def from_roots(cls, roots):
        index = cls()
        for root in roots:
            root_path = Path(root)
            if not root_path.exists():
                continue
            try:
                out = subprocess.run(
                    ["git", "-C", str(root_path), "log", "--all", "--name-only",
                     "--pretty=format:%x01%ct"],
                    capture_output=True, text=True, errors="replace", check=False,
                )
            except OSError:
                continue
            if out.returncode != 0:
                continue
            try:
                rel_root = str(root_path.resolve().relative_to(_WORKSPACE.resolve()))
            except ValueError:
                rel_root = ""
            if rel_root == ".":
                rel_root = ""
            index.roots.append(str(root_path))
            epoch = None
            for line in out.stdout.split("\n"):
                if line.startswith("\x01"):
                    try:
                        epoch = float(line[1:])
                    except ValueError:
                        epoch = None
                    continue
                if not line or epoch is None:
                    continue
                for key in ({line, f"{rel_root}/{line}"} if rel_root else {line}):
                    prev = index._paths.get(key)
                    if prev is None or epoch > prev:
                        index._paths[key] = epoch
        return index


class Reconnector:
    """FM-6 linkage oracle: turns a subagent's OUTPUT text into reconnection
    targets. Structural only — a path counts when git knows it, a task id counts
    when queue.jsonl carries it. Nothing is inferred from prose."""

    def __init__(self, git_index=None, queue_tokens=None):
        self.git_index = git_index if git_index is not None else GitPathIndex()
        self.queue_tokens = queue_tokens or {}

    def resolve(self, path):
        """Map a container-rooted path onto its repo path.

        Lane sessions work in `/mnt/raid0/llm/worktrees/<...>/<lane>/` and the
        worktree nesting depth is NOT fixed, so the prefix cannot be stripped by
        a fixed rule. Instead the suffixes are tried in order and the git index
        decides — a suffix that nobody ever committed resolves to nothing.
        Only container roots are eligible, so a scratch path under `tmp/` is not
        silently promoted into a repo path."""
        if not path or path in self.git_index:
            return path
        if path.split("/", 1)[0] not in _CONTAINER_ROOTS:
            return path
        parts = path.split("/")
        for i in range(1, len(parts) - 1):
            candidate = "/".join(parts[i:])
            if candidate in self.git_index:
                return candidate
        return path

    def paths(self, text):
        if not text:
            return []
        found = set()
        for match in _PATH_CANDIDATE_RE.finditer(text):
            norm = self.resolve(_normalize_repo_path(match.group(0)))
            if norm and norm in self.git_index:
                found.add(norm)
        return sorted(found)

    def tasks(self, text):
        if not text:
            return []
        return _match_queue_ids(text, self.queue_tokens)


class ParentIndex:
    """Post-finish mention index over a PARENT transcript.

    Records are appended in file order with their epoch; a lookup answers
    "was any of these needles mentioned at or after epoch T", excluding hits
    that sit inside the child's own quoted report (the self-match guard).
    """

    def __init__(self, cap=PARENT_INDEX_CAP):
        self.epochs = []
        self.offsets = []
        self._parts = []
        self._size = 0
        self._cap = cap
        self.truncated = False
        self._full = None

    def add(self, epoch, text):
        if epoch is None or not text:
            return
        if self._size >= self._cap:
            self.truncated = True
            return
        self._parts.append((epoch, text))
        self._size += len(text)

    def finalize(self):
        """Sort by epoch. A parent's OWN records arrive in file order but a
        session's subagent transcripts are appended afterwards, so the raw
        append order is NOT chronological — and 'mentioned after T' is a
        chronological question."""
        self._parts.sort(key=lambda item: item[0])
        offset = 0
        chunks = []
        for epoch, text in self._parts:
            self.epochs.append(epoch)
            self.offsets.append(offset)
            chunks.append(text)
            offset += len(text)
        self._full = "".join(chunks)
        self._parts = []
        return self

    def covers(self, epoch):
        """False when the byte cap stopped the index before `epoch` — the
        caller must then grade `unknown`, not `discarded`."""
        if not self.truncated:
            return True
        return bool(self.epochs) and epoch is not None and epoch <= self.epochs[-1]

    def mentions_after(self, needles, epoch, self_signature=None):
        if self._full is None or not needles or epoch is None:
            return False
        idx = bisect.bisect_left(self.epochs, epoch)
        if idx >= len(self.offsets):
            return False
        start = self.offsets[idx]
        sig = (self_signature or "").strip()[:SELF_MATCH_SIG_LEN]
        for needle in needles:
            pos = self._full.find(needle, start)
            while pos >= 0:
                if not sig:
                    return True
                lo = max(start, pos - SELF_MATCH_WINDOW)
                hi = pos + SELF_MATCH_WINDOW
                if sig not in self._full[lo:hi]:
                    return True
                pos = self._full.find(needle, pos + 1)
        return False


def classify_outcome(sub, parent_index, git_index):
    """FM-5 ladder. Returns (bucket, basis). First match wins; see the module
    docstring. `sub` is the collector's per-subagent dict."""
    if sub.get("abort_signal"):
        return "aborted", sub["abort_signal"]
    if sub.get("blocked_signal"):
        return "blocked", sub["blocked_signal"]
    if not sub.get("produced_output"):
        return "no-output", "no-final-report"
    # git-landed rests ONLY on paths the subagent itself MUTATED. A path it
    # merely cited in prose, later committed by somebody else, is not evidence
    # that this subagent's work was used.
    written = sorted(set(sub.get("written_paths", [])))
    if git_index is not None and git_index.landed_after(written, sub.get("finish_epoch")):
        return "produced-and-used", "git-landed"
    if parent_index is None:
        return "unknown", "parent-transcript-absent"
    needles = sorted(set(written) | set(sub.get("output_paths", []))
                     | set(sub.get("output_tasks", [])))
    if parent_index.mentions_after(needles, sub.get("finish_epoch"),
                                   sub.get("report_signature")):
        return "produced-and-used", "parent-reference"
    if not parent_index.covers(sub.get("finish_epoch")):
        return "unknown", "parent-index-truncated"
    return "produced-and-discarded", "no-reuse-observed"



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

    # --- FM-6: orphan-aware width. The v1 field keeps its orphan-BLIND value.
    non_orphan = [s for s in subagents if not s.get("orphan", False)]
    measured_width = _sweep_max_overlap(
        [(s["start_epoch"], s["finish_epoch"]) for s in non_orphan])

    # --- FM-5: per-bucket counts and token totals.
    outcome_counts = {b: 0 for b in OUTCOME_BUCKETS}
    outcome_tokens = {b: 0 for b in OUTCOME_BUCKETS}
    for s in subagents:
        bucket = s.get("outcome", "unknown")
        outcome_counts[bucket] = outcome_counts.get(bucket, 0) + 1
        outcome_tokens[bucket] = outcome_tokens.get(bucket, 0) + int(
            (s.get("tokens") or {}).get("total", 0))

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
        "measured_fanout_width": measured_width,
        "orphan_agents": sum(1 for s in subagents if s.get("orphan", False)),
        "linked_agents": len(non_orphan),
        "outcome_counts": outcome_counts,
        "outcome_tokens": outcome_tokens,
        "subagents": [{
            "id": s["id"],
            "parent": s["parent"],
            "depth": depth_of(s["id"]),
            "start_ts": s["start_ts"],
            "finish_ts": s["finish_ts"],
            "active_s": _r3(s["active_s"]),
            "outcome": s.get("outcome", "unknown"),
            "outcome_basis": s.get("outcome_basis", "not-classified"),
            "orphan": bool(s.get("orphan", False)),
            "tokens": s.get("tokens") or _empty_token_block(),
            "output_paths": sorted(s.get("output_paths", [])),
            "output_tasks": sorted(s.get("output_tasks", [])),
            "written_paths": sorted(s.get("written_paths", [])),
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


def _claude_text_blocks(record):
    """Every text-ish string a Claude record carries: `content`, the message
    content (string or block list), and structured tool_use inputs."""
    out = []
    content = record.get("content")
    if isinstance(content, str):
        out.append(content)
    message = record.get("message")
    if isinstance(message, dict):
        mc = message.get("content")
        if isinstance(mc, str):
            out.append(mc)
        elif isinstance(mc, list):
            for block in mc:
                if not isinstance(block, dict):
                    continue
                if isinstance(block.get("text"), str):
                    out.append(block["text"])
                if block.get("type") == "tool_result":
                    inner = block.get("content")
                    if isinstance(inner, str):
                        out.append(inner)
                    elif isinstance(inner, list):
                        out.extend(b.get("text", "") for b in inner if isinstance(b, dict))
    return out


def _claude_assistant_text(record):
    """The assistant text of one record, or '' — the subagent's report is the
    last such non-empty string in its transcript."""
    message = record.get("message")
    if not isinstance(message, dict) or message.get("role") != "assistant":
        return ""
    blocks = message.get("content")
    if isinstance(blocks, str):
        return blocks
    if not isinstance(blocks, list):
        return ""
    return "\n".join(b.get("text", "") for b in blocks
                     if isinstance(b, dict) and b.get("type") == "text"
                     and isinstance(b.get("text"), str))


def _claude_tool_text(record):
    """Tool-call text of one record: tool_use inputs and tool_result payloads.
    Deliberately EXCLUDES assistant prose — see _parse_claude_subagent."""
    parts = []
    message = record.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), list):
        for block in message["content"]:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                parts.append(json.dumps(block.get("input"), sort_keys=True, default=str))
            elif block.get("type") == "tool_result":
                inner = block.get("content")
                if isinstance(inner, str):
                    parts.append(inner)
                elif isinstance(inner, list):
                    parts.extend(b.get("text", "") for b in inner if isinstance(b, dict))
    return "\n".join(part for part in parts if part)


def _claude_written_paths(record):
    message = record.get("message")
    paths = set()
    if isinstance(message, dict) and isinstance(message.get("content"), list):
        for block in message["content"]:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            if block.get("name") not in CLAUDE_MUTATING_TOOLS:
                continue
            args = block.get("input")
            if not isinstance(args, dict):
                continue
            for key in ("file_path", "notebook_path", "path"):
                value = args.get(key)
                if isinstance(value, str) and value:
                    norm = _normalize_repo_path(value)
                    if norm:
                        paths.add(norm)
    result = record.get("toolUseResult")
    if isinstance(result, dict):
        value = result.get("filePath")
        if isinstance(value, str) and value:
            norm = _normalize_repo_path(value)
            if norm:
                paths.add(norm)
    return paths


def _parse_notifications(raw_line, epoch, notifications):
    """`<task-notification>` blocks carry the ONLY terminal status Claude
    records for a subagent. One block can name several task-ids (the
    'no completion record was found for N agents' form)."""
    for match in _NOTIFICATION_RE.finditer(raw_line):
        body = match.group(1)
        status_match = _NOTIF_STATUS_RE.search(body)
        status = status_match.group(1) if status_match else None
        for task_match in _NOTIF_TASK_RE.finditer(body):
            notifications.setdefault(task_match.group(1), []).append(
                (epoch if epoch is not None else 0.0, status))


def _parse_claude_session_file(path, bucket, parent_index=None):
    """Parse a MAIN session transcript. Also harvests the task-notification
    statuses and (when `parent_index` is given) the post-finish reuse index.

    Notification records are EXCLUDED from the reuse index: they quote the
    child's own report, so indexing them would grade every subagent 'used'."""
    records = []
    notifications = {}
    uuid_to_agent = {}
    timestamps = []
    meta_text = []
    bucket.torn = False
    last_line = None
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            last_line = line
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                bucket.count += 1
                continue
            records.append(r)
            ts = _parse_ts(r.get("timestamp"))
            uid = r.get("uuid")
            if isinstance(uid, str) and r.get("agentId"):
                uuid_to_agent[uid] = r["agentId"]
            if ts is not None:
                timestamps.append(ts)
            is_notification = "<task-notification>" in line
            if is_notification:
                _parse_notifications(line, ts, notifications)
            elif parent_index is not None:
                parent_index.add(ts, line)
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
    if last_line is not None:
        try:
            json.loads(last_line)
        except json.JSONDecodeError:
            bucket.torn = True
    return records, uuid_to_agent, timestamps, "\n".join(meta_text), notifications


def _parse_claude_subagent(path, bucket, uuid_to_agent, parent_index=None):
    """-> dict(subagent) or None. Records without agentId are skipped (e.g.
    journal.jsonl is already excluded by the agent-*.jsonl glob, but a foreign
    file must not crash the walk).

    v2 additions: token totals from the subagent's OWN assistant records, its
    final report text, the paths it mutated, and the two terminal signals
    (torn tail => aborted, isApiErrorMessage tail => blocked)."""
    records = bucket.parse(path)
    if not records:
        return None
    torn = bucket.torn
    agent_id = None
    parent = None
    start_ts = finish_ts = None
    start_epoch = finish_epoch = None
    last_has_ts = False
    meta_text = []
    tokens = _empty_token_block()
    report = ""
    written = set()
    last_record = None
    nested_notifications = {}
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
            last_record = r
        message = r.get("message")
        if isinstance(message, dict) and isinstance(message.get("usage"), dict):
            usage = message["usage"]
            tokens["input"] += int(usage.get("input_tokens") or 0)
            tokens["output"] += int(usage.get("output_tokens") or 0)
            tokens["cache_creation"] += int(usage.get("cache_creation_input_tokens") or 0)
            tokens["cache_read"] += int(usage.get("cache_read_input_tokens") or 0)
        text = _claude_assistant_text(r)
        if text.strip():
            report = text
        written |= _claude_written_paths(r)
        # A subagent can itself spawn subagents; its transcript then carries
        # THEIR notifications, and it is their parent for both purposes. Only
        # this agent's TOOL text joins the reuse index — indexing its own report
        # prose would let a subagent's report match itself and grade "used".
        for block in _claude_text_blocks(r):
            if "<task-notification>" in block:
                _parse_notifications(block, _parse_ts(r.get("timestamp")), nested_notifications)
        if parent_index is not None:
            tool_text = _claude_tool_text(r)
            if tool_text:
                parent_index.add(_parse_ts(r.get("timestamp")), tool_text)
    if agent_id is None:
        return None
    tokens["new"] = tokens["input"] + tokens["output"] + tokens["cache_creation"]
    tokens["total"] = tokens["new"] + tokens["cache_read"]
    api_error_tail = bool(last_record and last_record.get("isApiErrorMessage"))
    return {
        "id": agent_id,
        "parent": parent if parent is not None else "main",
        "start_ts": start_ts,
        "finish_ts": finish_ts,
        "start_epoch": start_epoch,
        "finish_epoch": finish_epoch,
        "active_s": (finish_epoch - start_epoch) if (start_epoch is not None and finish_epoch is not None) else 0.0,
        "completed": start_epoch is not None and last_has_ts and not torn,
        "declared_depth": 0,
        "meta_text": "\n".join(meta_text),
        "tokens": tokens,
        "report": report,
        "report_signature": report.strip()[:SELF_MATCH_SIG_LEN],
        "produced_output": bool(report.strip()) and not api_error_tail,
        "written_paths": sorted(written),
        "abort_signal": "torn-tail" if torn else None,
        "blocked_signal": "claude:api-error-tail" if api_error_tail else None,
        "nested_notifications": nested_notifications,
    }


def collect_claude(root, queue_path=None, stats=None, reconnector=None, git_index=None):
    root = Path(root)
    if stats is not None:
        stats.setdefault("subagent_files", 0)
        stats.setdefault("malformed_lines", 0)
        stats.setdefault("workflows", 0)
        stats.setdefault("subagents", 0)
        stats.setdefault("no_notification", 0)
    bucket = _MalformedBucket()
    queue_ids = _load_queue_ids(queue_path)
    queue_tokens = _queue_tokens(queue_ids)
    if reconnector is None:
        reconnector = Reconnector(git_index=git_index, queue_tokens=queue_tokens)
    rows = []
    session_files = sorted(root.glob("*.jsonl"))
    session_dirs = sorted(d for d in root.iterdir() if d.is_dir())
    sids = sorted({p.name[:-6] for p in session_files} | {d.name for d in session_dirs})

    for sid in sids:
        session_path = root / f"{sid}.jsonl"
        session_dir = root / sid
        parent_index = ParentIndex()
        session_present = session_path.is_file()
        if session_present:
            records, _session_map, timestamps, session_meta, notifications = (
                _parse_claude_session_file(session_path, bucket, parent_index))
        else:
            records, _session_map, timestamps, session_meta, notifications = [], {}, [], "", {}
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
            sub = _parse_claude_subagent(path, bucket, uuid_to_agent, parent_index)
            if sub is not None:
                notifications.update({k: notifications.get(k, []) + v
                                      for k, v in sub.pop("nested_notifications").items()})
                subagents.append(sub)
        parent_index.finalize()
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

        for sub in subagents:
            statuses = sorted(notifications.get(sub["id"], []), key=lambda x: x[0])
            if statuses:
                last_status = statuses[-1][1]
                if last_status is not None and last_status != CLAUDE_OK_STATUS:
                    sub["abort_signal"] = sub["abort_signal"] or f"notification:{last_status}"
            elif stats is not None:
                stats["no_notification"] += 1
            _finish_subagent(sub, reconnector,
                             parent_index if session_present else None,
                             reconnector.git_index)

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


def _finish_subagent(sub, reconnector, parent_index, git_index):
    """Shared FM-5/FM-6 tail: reconnection targets from the OUTPUT, orphan flag,
    then the outcome ladder. Backend-agnostic on purpose."""
    report = sub.get("report") or ""
    sub["output_paths"] = reconnector.paths(report)
    sub["output_tasks"] = reconnector.tasks(report)
    # A lane subagent writes through its worktree path; resolve it the same way
    # so `git-landed` can see the commit.
    sub["written_paths"] = sorted({reconnector.resolve(w)
                                   for w in sub.get("written_paths", [])})
    sub["orphan"] = not (sub["output_paths"] or sub["output_tasks"] or sub.get("written_paths"))
    bucket, basis = classify_outcome(sub, parent_index, git_index)
    sub["outcome"] = bucket
    sub["outcome_basis"] = basis
    return sub


# --------------------------------------------------------------------------- Codex


def _codex_meta(path):
    """Cheap first-line pass: id / session / subagent classification / parent
    edge, without reading the (sometimes multi-GB) body."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            first = fh.readline()
    except OSError:
        return None
    if not first.strip():
        return None
    try:
        record = json.loads(first)
    except json.JSONDecodeError:
        return None
    payload = record.get("payload") or {}
    source = payload.get("source")
    is_subagent = (
        payload.get("thread_source") == "subagent"
        or (isinstance(source, dict) and isinstance(source.get("subagent"), dict))
    )
    spawn = {}
    if isinstance(source, dict) and isinstance(source.get("subagent"), dict):
        spawn = source["subagent"].get("thread_spawn") or {}
    return {
        "file": path,
        "id": payload.get("id"),
        "session_id": payload.get("session_id"),
        "parent_thread_id": spawn.get("parent_thread_id") or payload.get("parent_thread_id"),
        "spawn_depth": spawn.get("depth"),
        "is_subagent": is_subagent,
    }


def _parse_codex_rollout(path, bucket, parent_index=None, index_cutoff=None):
    """Full parse of one rollout.

    v2 additions: cumulative token usage (last `token_count`), the final agent
    message (the OUTPUT), apply_patch targets (written paths), and the terminal
    signal. When `parent_index` is given, lines at/after `index_cutoff` join the
    reuse index for this rollout's children."""
    records = []
    bucket.torn = False
    last_line = None
    tokens = _empty_token_block()
    report = ""
    written = set()
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            last_line = line
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                bucket.count += 1
                continue
            records.append(r)
            payload = r.get("payload") if isinstance(r.get("payload"), dict) else {}
            ptype = payload.get("type")
            if ptype == "token_count":
                usage = (payload.get("info") or {}).get("total_token_usage") or {}
                cached = int(usage.get("cached_input_tokens") or 0)
                fresh_in = max(0, int(usage.get("input_tokens") or 0) - cached)
                out_tok = int(usage.get("output_tokens") or 0)
                tokens = {
                    "input": fresh_in,
                    "output": out_tok,
                    "cache_creation": 0,
                    "cache_read": cached,
                    "new": fresh_in + out_tok,
                    "total": int(usage.get("total_tokens") or 0),
                }
            elif ptype == "agent_message":
                message = payload.get("message")
                if isinstance(message, str) and message.strip():
                    report = message
            elif ptype == "task_complete":
                message = payload.get("last_agent_message")
                if isinstance(message, str) and message.strip():
                    report = message
            elif ptype == "function_call":
                args = payload.get("arguments")
                if isinstance(args, str):
                    for match in _APPLY_PATCH_RE.finditer(args):
                        norm = _normalize_repo_path(match.group(1))
                        if norm:
                            written.add(norm)
            if parent_index is not None:
                ts = _parse_ts(r.get("timestamp"))
                if ts is not None and (index_cutoff is None or ts >= index_cutoff):
                    parent_index.add(ts, line)
    if last_line is not None:
        try:
            json.loads(last_line)
        except json.JSONDecodeError:
            bucket.torn = True
    if not records:
        return None
    torn = bucket.torn
    meta = _codex_meta(path) or {}
    first = records[0]
    start_ts = first.get("timestamp")
    start_epoch = _parse_ts(start_ts)
    last = records[-1]
    finish_ts = last.get("timestamp")
    finish_epoch = _parse_ts(finish_ts)
    last_payload = last.get("payload") if isinstance(last.get("payload"), dict) else {}
    terminal = last_payload.get("type")
    completed = terminal in CODEX_TERMINAL and start_epoch is not None
    if not tokens["total"]:
        tokens["total"] = tokens["new"] + tokens["cache_read"]
    abort = None
    if torn:
        abort = "torn-tail"
    elif terminal in CODEX_ABORTED:
        abort = f"codex:{terminal}"
    row = {
        "file": path,
        "id": meta.get("id"),
        "session_id": meta.get("session_id"),
        "parent_thread_id": meta.get("parent_thread_id"),
        "spawn_depth": meta.get("spawn_depth"),
        "is_subagent": bool(meta.get("is_subagent")),
        "start_ts": start_ts,
        "finish_ts": finish_ts,
        "start_epoch": start_epoch,
        "finish_epoch": finish_epoch,
        "active_s": (finish_epoch - start_epoch) if (start_epoch is not None and finish_epoch is not None) else 0.0,
        "completed": completed,
        "meta_text": json.dumps(first.get("payload") or {}, ensure_ascii=True)[:20000],
        "tokens": tokens,
        "report": report,
        "report_signature": report.strip()[:SELF_MATCH_SIG_LEN],
        "produced_output": bool(report.strip()),
        "written_paths": sorted(written),
        "abort_signal": abort,
        "blocked_signal": f"codex:{terminal}" if terminal in CODEX_BLOCKED else None,
    }
    return row


def collect_codex(root, queue_path=None, stats=None, reconnector=None, git_index=None):
    """Three passes so every file is read at most twice and the reuse index is
    built only for rollouts that actually PARENT a subagent:

      A  first lines only        -> who is a subagent, and who its parent is
      B  full parse of subagents -> timing, tokens, output, written paths
      C  full parse of the rest  -> timing, plus a reuse index for real parents
      D  re-read of subagent rollouts that are themselves parents (nesting)
    """
    root = Path(root)
    if stats is not None:
        stats.setdefault("rollout_files", 0)
        stats.setdefault("malformed_lines", 0)
        stats.setdefault("workflows", 0)
        stats.setdefault("subagents", 0)
        stats.setdefault("parent_rollouts_indexed", 0)
    bucket = _MalformedBucket()
    queue_ids = _load_queue_ids(queue_path)
    queue_tokens = _queue_tokens(queue_ids)
    if reconnector is None:
        reconnector = Reconnector(git_index=git_index, queue_tokens=queue_tokens)

    paths = sorted(root.glob("**/rollout-*.jsonl"))
    metas = {}
    for path in paths:
        meta = _codex_meta(path)
        if meta is not None:
            metas[path] = meta
    parent_ids = {m["parent_thread_id"] for m in metas.values()
                  if m["is_subagent"] and m["parent_thread_id"]}

    rollouts = []
    by_path = {}
    # Pass B: subagents first, so parent cutoffs are known before Pass C.
    for path in paths:
        meta = metas.get(path)
        if meta is None or not meta["is_subagent"]:
            continue
        ro = _parse_codex_rollout(path, bucket)
        if ro is not None:
            rollouts.append(ro)
            by_path[path] = ro

    cutoffs = {}
    for ro in rollouts:
        pid = ro["parent_thread_id"]
        if not pid or ro["finish_epoch"] is None:
            continue
        prev = cutoffs.get(pid)
        if prev is None or ro["finish_epoch"] < prev:
            cutoffs[pid] = ro["finish_epoch"]

    indexes = {}
    # Pass C: everything else; index only genuine parents.
    for path in paths:
        meta = metas.get(path)
        if meta is None or meta["is_subagent"]:
            continue
        index = None
        if meta["id"] in parent_ids:
            index = ParentIndex()
        ro = _parse_codex_rollout(path, bucket, index, cutoffs.get(meta["id"]))
        if ro is not None:
            rollouts.append(ro)
            by_path[path] = ro
        if index is not None:
            indexes[meta["id"]] = index.finalize()
            if stats is not None:
                stats["parent_rollouts_indexed"] += 1

    # Pass D: nested spawners (a subagent that is itself somebody's parent).
    for path, meta in metas.items():
        if not meta["is_subagent"] or meta["id"] not in parent_ids:
            continue
        index = ParentIndex()
        _parse_codex_rollout(path, _MalformedBucket(), index, cutoffs.get(meta["id"]))
        indexes[meta["id"]] = index.finalize()
        if stats is not None:
            stats["parent_rollouts_indexed"] += 1

    by_id = {ro["id"]: ro for ro in rollouts if ro["id"]}
    workflows = {}
    for ro in rollouts:
        wid = ro["session_id"] or ro["id"]
        workflows.setdefault(wid, []).append(ro)

    rows = []
    for wid in sorted(workflows):
        files = workflows[wid]
        subs = [f for f in files if f["is_subagent"]]
        for sub in subs:
            parent_thread = by_id.get(sub["parent_thread_id"])
            if parent_thread is not None:
                parent_id = parent_thread["id"]
                sub["parent"] = parent_id if parent_thread["is_subagent"] else "main"
            else:
                sub["parent"] = "main"
            sub["declared_depth"] = sub["spawn_depth"] + 1 if isinstance(sub["spawn_depth"], int) else 0
            _finish_subagent(sub, reconnector, indexes.get(sub["parent_thread_id"]),
                             reconnector.git_index)

        subagent_rows = [dict(f, id=f["id"] or f["file"].name) for f in subs]

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
    """v1 rows stay READABLE: any schema in READABLE_SCHEMAS merges. The source
    column is still enforced, so a file cannot be merged against itself."""
    rows = []
    for path, source in ((claude_path, "claude"), (codex_path, "codex")):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                if r.get("schema") not in READABLE_SCHEMAS or r.get("source") != source:
                    raise ValueError(f"{path}: row schema/source mismatch")
                rows.append(r)
    rows.sort(key=lambda r: (r["source"], r["workflow_id"]))
    _atomic_write_jsonl(output, rows)
    return rows


def outcome_report(paths):
    """FM-5/FM-6 rollup over collected records. v1 rows carry no outcome fields:
    their subagents are counted under `schema_v1_no_outcome` and are EXCLUDED
    from the bucket denominators rather than folded into a bucket."""
    report = {
        "schema": SCHEMA,
        "workflows": 0,
        "workflows_v1": 0,
        "subagents": 0,
        "schema_v1_no_outcome": 0,
        "classified_subagents": 0,
        "outcome_counts": {b: 0 for b in OUTCOME_BUCKETS},
        "outcome_tokens": {b: 0 for b in OUTCOME_BUCKETS},
        "outcome_new_tokens": {b: 0 for b in OUTCOME_BUCKETS},
        "outcome_basis": {},
        "total_tokens": 0,
        "total_new_tokens": 0,
        "orphan_agents": 0,
        "linked_agents": 0,
        "declared_width_sum": 0,
        "measured_width_sum": 0,
        "by_source": {},
    }
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("schema") not in READABLE_SCHEMAS:
                    raise ValueError(f"{path}: unreadable schema {row.get('schema')!r}")
                src = report["by_source"].setdefault(row.get("source"), {
                    "workflows": 0, "subagents": 0, "classified_subagents": 0,
                    "orphan_agents": 0,
                    "outcome_counts": {b: 0 for b in OUTCOME_BUCKETS},
                    "outcome_tokens": {b: 0 for b in OUTCOME_BUCKETS},
                    "total_tokens": 0,
                })
                report["workflows"] += 1
                src["workflows"] += 1
                is_v1 = row.get("schema") == SCHEMA_V1
                if is_v1:
                    report["workflows_v1"] += 1
                report["declared_width_sum"] += row.get("max_overlapping_subagents", 0)
                report["measured_width_sum"] += row.get("measured_fanout_width", 0)
                for sub in row.get("subagents", []):
                    report["subagents"] += 1
                    src["subagents"] += 1
                    if is_v1 or "outcome" not in sub:
                        report["schema_v1_no_outcome"] += 1
                        continue
                    bucket = sub["outcome"]
                    tok = sub.get("tokens") or {}
                    total = int(tok.get("total", 0))
                    fresh = int(tok.get("new", 0))
                    report["classified_subagents"] += 1
                    src["classified_subagents"] += 1
                    report["outcome_counts"][bucket] = report["outcome_counts"].get(bucket, 0) + 1
                    report["outcome_tokens"][bucket] = report["outcome_tokens"].get(bucket, 0) + total
                    src["outcome_counts"][bucket] = src["outcome_counts"].get(bucket, 0) + 1
                    src["outcome_tokens"][bucket] = src["outcome_tokens"].get(bucket, 0) + total
                    report["outcome_new_tokens"][bucket] = report["outcome_new_tokens"].get(bucket, 0) + fresh
                    report["total_new_tokens"] += fresh
                    basis = sub.get("outcome_basis", "not-classified")
                    report["outcome_basis"][basis] = report["outcome_basis"].get(basis, 0) + 1
                    report["total_tokens"] += total
                    src["total_tokens"] += total
                    if sub.get("orphan"):
                        report["orphan_agents"] += 1
                        src["orphan_agents"] += 1
                    else:
                        report["linked_agents"] += 1
    classified = report["classified_subagents"]
    tokens = report["total_tokens"]
    unused = [b for b in OUTCOME_BUCKETS if b != "produced-and-used"]
    report["unused_token_share"] = (
        _r6(sum(report["outcome_tokens"][b] for b in unused if b != "unknown") / tokens)
        if tokens else 0.0)
    report["unknown_token_share"] = (
        _r6(report["outcome_tokens"]["unknown"] / tokens) if tokens else 0.0)
    report["used_token_share"] = (
        _r6(report["outcome_tokens"]["produced-and-used"] / tokens) if tokens else 0.0)
    fresh_total = report["total_new_tokens"]
    report["unused_new_token_share"] = (
        _r6(sum(report["outcome_new_tokens"][b] for b in unused if b != "unknown") / fresh_total)
        if fresh_total else 0.0)
    report["unknown_new_token_share"] = (
        _r6(report["outcome_new_tokens"]["unknown"] / fresh_total) if fresh_total else 0.0)
    report["orphan_rate"] = _r6(report["orphan_agents"] / classified) if classified else 0.0
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="fanout_timing.py",
        description="RTG-49 FM-1 per-subagent timing collector (fanout_timing.v1). "
                    "Offline only: zero network, zero inference, corpus read-only.",
    )
    parser.add_argument("--queue", type=Path, default=_DEFAULT_QUEUE,
                        help="queue.jsonl path for task-id joins (default: canonical /workspace path)")
    parser.add_argument("--git-root", action="append", default=None,
                        help="repo root whose committed paths define 'artifact path' "
                             "(repeatable; default: epyc-root + orchestrator + research)")
    parser.add_argument("--no-git", action="store_true",
                        help="disable the git path index entirely: NO path resolves, so every "
                             "subagent grades orphan. Diagnostic only.")
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

    p_report = sub.add_parser("report", help="FM-5/FM-6 rollup over collected records")
    p_report.add_argument("--input", required=True, action="append",
                          help="collected .jsonl (repeatable); v1 and v2 both readable")
    p_report.add_argument("--output", default=None, help="write the rollup JSON here too")

    args = parser.parse_args(argv)
    stats = {"workflows": 0, "subagents": 0, "subagent_files": 0, "rollout_files": 0,
             "malformed_lines": 0, "no_notification": 0, "parent_rollouts_indexed": 0}

    if args.cmd in ("collect-claude", "collect-codex"):
        git_index = (GitPathIndex() if args.no_git
                     else GitPathIndex.from_roots(args.git_root or _DEFAULT_GIT_ROOTS))
        print(f"git path index: {len(git_index)} keys over {len(git_index.roots)} roots",
              file=sys.stderr)

    if args.cmd == "collect-claude":
        rows = collect_claude(args.root, queue_path=args.queue, stats=stats, git_index=git_index)
        _atomic_write_jsonl(args.output, rows)
        print(f"claude: {len(rows)} workflows, {stats['subagents']} subagents, "
              f"{stats['subagent_files']} subagent files, {stats['malformed_lines']} malformed lines, "
              f"{stats['no_notification']} subagents with no task-notification "
              f"-> {args.output}", file=sys.stderr)
    elif args.cmd == "collect-codex":
        rows = collect_codex(args.root, queue_path=args.queue, stats=stats, git_index=git_index)
        _atomic_write_jsonl(args.output, rows)
        print(f"codex: {len(rows)} workflows, {stats['subagents']} subagents, "
              f"{stats['rollout_files']} rollout files, {stats['malformed_lines']} malformed lines, "
              f"{stats['parent_rollouts_indexed']} parent rollouts indexed "
              f"-> {args.output}", file=sys.stderr)
    elif args.cmd == "merge":
        rows = merge(args.claude, args.codex, args.output)
        print(f"merge: {len(rows)} rows -> {args.output}", file=sys.stderr)
    elif args.cmd == "report":
        report = outcome_report(args.input)
        text = json.dumps(report, indent=2, sort_keys=True)
        print(text)
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
