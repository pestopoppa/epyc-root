#!/usr/bin/env python3
"""FM-7: delegation accounting over Claude Code journals and Codex rollouts.

Exposed through `fanout_timing.py delegation-manifest` / `delegation-accounting`.
OFFLINE ONLY: zero network, zero inference, corpus read-only. It shares no state
with the FM-1/FM-5/FM-6 collector, so those outputs are unchanged by construction.

FROZEN INPUT. `build_manifest` records, for every transcript, its byte length and
the sha256 of exactly those bytes at the cutoff. `account` reads ONLY that byte
prefix and re-hashes it while reading; a mismatch is counted and the file is
excluded (transcripts are append-only, so a live file still verifies). Re-running
the accounting on the same manifest is byte-identical, even while sessions grow.

UNITS. A "request" is one model call: Claude assistant records are de-duplicated
by `message.id` (one call is journaled once per content block with the same
usage); Codex requests are `token_usage_record` rows keyed by `response_id`, with
a fallback to changes of `token_count.info.total_token_usage` for older rollouts.
Request input = input + cache_creation + cache_read (Codex: `input_tokens`, which
already includes `cached_input_tokens`).

DECISION NUMBER A (predeclared in handoffs/active/fleet-fanout-measurement.md FM-7):

  A = sum(chars/4 of main-thread FULL reads of files > 350 lines
          x requests remaining in that session)
      / sum(main-thread input + cache_creation + cache_read tokens)

  A full read is a Read tool call with neither `offset` nor `limit` (the shape the
  M1 hook would block). When the tool_use input is not in the journal the fallback
  is startLine == 1 and numLines == totalLines. "Requests remaining" is realised
  per request: every main-thread request carries the chars/4 of every qualifying
  read that preceded it, and both numerator and denominator are attributed to the
  window of that REQUEST's timestamp. Summed over a session this is exactly
  sum(read tokens x requests remaining).

  Rule: A >= 10% in BOTH windows (before / from 2026-10-15) fires M1; A < 3% in
  BOTH closes M1 as declined; anything else re-measures in 30 days.

  `A_compaction_bounded` stops the carry at each compact boundary. It is reported
  as a sensitivity only and never enters the rule. So is
  `A_proxy_large_tool_output_main`: the same carry over EVERY main-thread tool
  output over 350 lines (Bash stdout included), which catches whole-file reads
  done with `cat` that the Read-based A cannot see.

Codex logs carry no structured file-read event (reads are shell commands inside
`exec`), so A is NOT computable for Codex; `A_proxy_large_tool_output` applies
the same carry arithmetic to every main-thread tool output over 350 lines.

M2 TRIGGER. A cheap-tier dispatch (Claude haiku/sonnet, Codex luna/terra/reserve)
counts as re-dispatched at a higher tier when the SAME parent later dispatches a
higher-tier agent for the same task: normalised description / task_name equal,
or (Claude) prompt word-set Jaccard >= 0.8 on prompts of at least 200 chars.
Effort-only escalations (same tier, higher effort) are counted separately.
"""

import hashlib
import json
import os
import re
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "delegation_accounting.v1"
MANIFEST_SCHEMA = "delegation_manifest.v1"
WINDOW_SPLIT = "2026-10-15T00:00:00Z"
LARGE_FILE_LINES = 350          # "files over 350 lines": totalLines > 350
CHARS_PER_TOKEN = 4
A_FIRE = 0.10
A_DECLINE = 0.03
M2_RATE = 0.15
M2_DAYS = 30
PROMPT_JACCARD = 0.8
PROMPT_MIN_CHARS = 200
_CHUNK = 1 << 20

CLAUDE_TIERS = (("haiku", 1), ("sonnet", 2), ("opus", 3), ("fable", 4))
CODEX_TIERS = (("luna", 1), ("reserve", 1), ("terra", 2), ("sol", 3), ("astra", 4))
CHEAP_MAX_TIER = 2
EFFORT_RANK = {"minimal": 0, "low": 1, "lower": 1, "medium": 2, "high": 3,
               "higher": 3, "xhigh": 4, "max": 5}

_CODEX_MARKERS = ('"session_meta"', '"turn_context"', '"token_usage_record"', '"token_count"',
                  '"task_complete"', '"function_call_output"', '"custom_tool_call_output"',
                  '"spawn_agent"', '"compacted"', '"agent_message"')


# --------------------------------------------------------------------------- helpers


def _epoch(raw):
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


_SPLIT_EPOCH = _epoch(WINDOW_SPLIT)


def window_of(epoch, split_epoch=_SPLIT_EPOCH):
    if epoch is None:
        return None
    return "pre" if epoch < split_epoch else "post"


def tier_of(model, backend):
    if not isinstance(model, str) or not model:
        return None
    low = model.lower()
    for token, rank in (CLAUDE_TIERS if backend == "claude" else CODEX_TIERS):
        if token in low:
            return rank
    return None


def tier_name(rank, backend):
    for token, r in (CLAUDE_TIERS if backend == "claude" else CODEX_TIERS):
        if r == rank:
            return token
    return "unknown"


def _norm_task(text, backend):
    """Normalise a description / task_name so a re-dispatch of the same task
    under a different tier matches: lowercase, tier and retry tokens dropped."""
    if not isinstance(text, str):
        return ""
    low = text.lower()
    for token, _ in (CLAUDE_TIERS if backend == "claude" else CODEX_TIERS):
        low = low.replace(token, " ")
    low = re.sub(r"\b(retry|rerun|redo|again|v\d+|take\d*|attempt\d*)\b", " ", low)
    return " ".join(re.findall(r"[a-z]+", low))


def _jaccard(a, b):
    sa, sb = set(a.lower().split()), set(b.lower().split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _r6(x):
    return round(float(x), 6)


def _dist(values):
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return {"n": 0}
    p90 = vals[min(len(vals) - 1, int(round(0.9 * (len(vals) - 1))))]
    return {"n": len(vals), "mean": _r6(statistics.fmean(vals)), "median": _r6(statistics.median(vals)),
            "p90": _r6(p90), "min": _r6(vals[0]), "max": _r6(vals[-1]), "sum": _r6(sum(vals))}


def _usage_block():
    return {"input": 0, "cache_creation": 0, "cache_read": 0, "output": 0}


def _add_usage(block, req):
    for k in ("input", "cache_creation", "cache_read", "output"):
        block[k] += req[k]
    return block


def _req_input(req):
    return req["input"] + req["cache_creation"] + req["cache_read"]


def _most_common(values):
    c = Counter(v for v in values if v)
    return c.most_common(1)[0][0] if c else None


# --------------------------------------------------------------------------- manifest


def _hash_file(path, nbytes=None):
    h = hashlib.sha256()
    done = 0
    with open(path, "rb") as fh:
        while nbytes is None or done < nbytes:
            want = _CHUNK if nbytes is None else min(_CHUNK, nbytes - done)
            chunk = fh.read(want)
            if not chunk:
                break
            h.update(chunk)
            done += len(chunk)
    return h.hexdigest(), done


def build_manifest(claude_root=None, codex_root=None, since=None, cutoff=None):
    """Frozen input list. Claude: every **/*.jsonl under the root. Codex: every
    rollout-*.jsonl whose mtime is at/after `since` (a long-lived main that
    started earlier but wrote inside the window is included)."""
    since_epoch = _epoch(since) if since else None
    entries, unreadable = [], []

    def _add(backend, root, path):
        try:
            size = path.stat().st_size
            digest, done = _hash_file(path, size)
        except OSError as exc:
            unreadable.append({"backend": backend, "path": str(path), "error": type(exc).__name__})
            return
        entries.append({"backend": backend, "root": str(root),
                        "path": str(path.relative_to(root)), "bytes": done, "sha256": digest})

    if claude_root:
        root = Path(claude_root)
        for path in sorted(root.glob("**/*.jsonl")):
            _add("claude", root, path)
    if codex_root:
        root = Path(codex_root)
        for path in sorted(root.glob("**/rollout-*.jsonl")):
            try:
                mtime = path.stat().st_mtime
            except OSError as exc:
                unreadable.append({"backend": "codex", "path": str(path), "error": type(exc).__name__})
                continue
            if since_epoch is not None and mtime < since_epoch:
                continue
            _add("codex", root, path)
    return {
        "schema": MANIFEST_SCHEMA,
        "cutoff": cutoff or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "since": since,
        "claude_root": str(claude_root) if claude_root else None,
        "codex_root": str(codex_root) if codex_root else None,
        "entries": entries,
        "unreadable": unreadable,
        "totals": {"files": len(entries), "bytes": sum(e["bytes"] for e in entries)},
    }


class _Prefix:
    """Read exactly `nbytes` of a file, hashing as it goes. Yields lines."""

    def __init__(self, path, nbytes):
        self.path, self.nbytes = path, nbytes
        self.digest = None
        self.bad_lines = 0

    def lines(self):
        h = hashlib.sha256()
        done = 0
        tail = b""
        with open(self.path, "rb") as fh:
            while done < self.nbytes:
                chunk = fh.read(min(_CHUNK, self.nbytes - done))
                if not chunk:
                    break
                h.update(chunk)
                done += len(chunk)
                buf = tail + chunk
                parts = buf.split(b"\n")
                tail = parts.pop()
                for part in parts:
                    if part.strip():
                        yield part.decode("utf-8", errors="replace")
        if tail.strip():
            yield tail.decode("utf-8", errors="replace")
        self.digest = h.hexdigest() if done == self.nbytes else None

    def records(self, keep=None):
        for line in self.lines():
            if keep is not None and not keep(line):
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                self.bad_lines += 1


# --------------------------------------------------------------------------- Claude


def _claude_keep(line):
    return not line.startswith('{"type":"api-request')


def parse_claude_thread(records, main=False):
    """One transcript -> requests, reads, dispatches, compactions, final report.

    `main=True` drops sidechain / agentId records (a main file may embed them)."""
    reqs = {}          # msg_id -> request dict (insertion-ordered)
    events = []        # ("req", id) | ("read", read) | ("compact", None) in journal order
    tool_inputs = {}   # tool_use_id -> (name, input)
    dispatches = []
    final_text, final_req = "", None
    first_ts = last_ts = None
    last_epoch = None
    for r in records:
        if main and (r.get("isSidechain") or r.get("agentId")):
            continue
        ts = r.get("timestamp")
        ep = _epoch(ts)
        if ep is not None:
            last_epoch = ep
            first_ts = first_ts or ts
            last_ts = ts
        rtype = r.get("type")
        if rtype == "system" and r.get("subtype") == "compact_boundary":
            events.append(("compact", None))
            continue
        message = r.get("message") if isinstance(r.get("message"), dict) else {}
        if rtype == "assistant":
            mid = message.get("id") or r.get("requestId") or r.get("uuid")
            usage = message.get("usage") if isinstance(message.get("usage"), dict) else None
            if mid not in reqs and usage is not None:
                reqs[mid] = {"id": mid, "epoch": last_epoch, "ts": ts,
                             "model": message.get("model"), "effort": r.get("effort"),
                             "requested_model": r.get("requestedModel"),
                             "input": 0, "cache_creation": 0, "cache_read": 0, "output": 0}
                events.append(("req", mid))
            if usage is not None and mid in reqs:
                req = reqs[mid]
                req["input"] = int(usage.get("input_tokens") or 0)
                req["cache_creation"] = int(usage.get("cache_creation_input_tokens") or 0)
                req["cache_read"] = int(usage.get("cache_read_input_tokens") or 0)
                req["output"] = int(usage.get("output_tokens") or 0)
            for block in message.get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    inp = block.get("input") if isinstance(block.get("input"), dict) else {}
                    tool_inputs[block.get("id")] = (block.get("name"), inp)
                    if block.get("name") in ("Agent", "Task"):
                        dispatches.append({
                            "tool_use_id": block.get("id"), "ts": ts, "epoch": last_epoch,
                            "description": inp.get("description") or "",
                            "prompt": inp.get("prompt") or "",
                            "subagent_type": inp.get("subagent_type"),
                            "model": inp.get("model"), "effort": inp.get("effort"),
                        })
                elif block.get("type") == "text" and (block.get("text") or "").strip():
                    final_text, final_req = block["text"], mid
            continue
        tur = r.get("toolUseResult")
        if rtype == "user" and isinstance(tur, dict) and isinstance(tur.get("stdout"), str):
            text = tur["stdout"] + (tur.get("stderr") or "")
            events.append(("out", {"epoch": last_epoch, "ts": ts, "chars": len(text),
                                   "lines": text.count("\n") + 1}))
            continue
        if rtype == "user" and isinstance(tur, dict) and isinstance(tur.get("file"), dict):
            fobj = tur["file"]
            content = fobj.get("content")
            if not isinstance(content, str) or "numLines" not in fobj:
                continue
            tool_use_id = None
            for block in message.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    tool_use_id = block.get("tool_use_id")
                    break
            name, inp = tool_inputs.get(tool_use_id, (None, None))
            if name is not None and name != "Read":
                continue
            total = fobj.get("totalLines")
            start = fobj.get("startLine")
            nlines = fobj.get("numLines")
            if inp is not None:
                full = inp.get("offset") in (None, "") and inp.get("limit") in (None, "")
                basis = "input"
            else:
                full = start == 1 and nlines == total
                basis = "result-shape"
            read = {"path": fobj.get("filePath"), "ts": ts, "epoch": last_epoch,
                    "startLine": start, "numLines": nlines, "totalLines": total,
                    "chars": len(content), "full": bool(full), "full_basis": basis}
            events.append(("read", read))
    final_output = reqs[final_req]["output"] if final_req in reqs else None
    return {"requests": list(reqs.values()), "events": events, "dispatches": dispatches,
            "final_report_chars": len(final_text), "final_report_output_tokens": final_output,
            "first_ts": first_ts, "last_ts": last_ts}


def _qualifies(read):
    return read["full"] and isinstance(read.get("totalLines"), int) and read["totalLines"] > LARGE_FILE_LINES


def carry_accounting(events, reqs_by_id, qualifies, size_of, since_epoch=None,
                     split_epoch=_SPLIT_EPOCH):
    """Per-window numerator/denominator of A for one main thread.
    -> {window: {"num", "num_compact", "den", "requests", "qualifying_reads"}}"""
    out = {}
    carried = carried_c = 0.0
    for kind, item in events:
        if kind == "compact":
            carried_c = 0.0
        elif kind == "read":
            if qualifies(item):
                tok = size_of(item) / CHARS_PER_TOKEN
                carried += tok
                carried_c += tok
                w = window_of(item.get("epoch"), split_epoch)
                if w and not (since_epoch and (item.get("epoch") or 0) < since_epoch):
                    out.setdefault(w, _win())["qualifying_reads"] += 1
        elif kind == "req":
            req = reqs_by_id[item]
            if since_epoch is not None and (req["epoch"] is None or req["epoch"] < since_epoch):
                continue
            w = window_of(req["epoch"], split_epoch)
            if w is None:
                continue
            slot = out.setdefault(w, _win())
            slot["num"] += carried
            slot["num_compact"] += carried_c
            slot["den"] += _req_input(req)
            slot["requests"] += 1
    return out


def _win():
    return {"num": 0.0, "num_compact": 0.0, "den": 0, "requests": 0, "qualifying_reads": 0}


def _thread_tokens(requests):
    block = _usage_block()
    for req in requests:
        _add_usage(block, req)
    block["total_input"] = block["input"] + block["cache_creation"] + block["cache_read"]
    return block


def _first_request(requests):
    if not requests:
        return None
    req = requests[0]
    return {"input": req["input"], "cache_creation": req["cache_creation"],
            "cache_read": req["cache_read"], "total_input": _req_input(req)}


def _read_summary(reads):
    return {"reads": len(reads), "full_reads": sum(1 for r in reads if r["full"]),
            "chars": sum(r["chars"] for r in reads),
            "large_full_reads": sum(1 for r in reads if _qualifies(r)),
            "large_full_read_chars": sum(r["chars"] for r in reads if _qualifies(r))}


def account_claude_session(sid, main_records, subagent_items, since_epoch=None):
    """-> (main_row, [subagent_rows], [dispatch_groups])"""
    rows = []
    groups = []
    main = parse_claude_thread(main_records, main=True)
    reqs_by_id = {r["id"]: r for r in main["requests"]}
    reads = [item for kind, item in main["events"] if kind == "read"]
    windows = carry_accounting(main["events"], reqs_by_id, _qualifies, lambda r: r["chars"],
                               since_epoch=since_epoch)
    # Sensitivity only (never in the rule): the Codex-comparable proxy, i.e. every
    # main-thread tool output over 350 lines (Bash stdout or any Read window).
    proxy_events = []
    for kind, item in main["events"]:
        if kind == "out":
            proxy_events.append(("read", item))
        elif kind == "read":
            proxy_events.append(("read", {"epoch": item["epoch"], "chars": item["chars"],
                                          "lines": item.get("numLines") or 0}))
        else:
            proxy_events.append((kind, item))
    proxy = carry_accounting(proxy_events, reqs_by_id, lambda o: o["lines"] > LARGE_FILE_LINES,
                             lambda o: o["chars"], since_epoch=since_epoch)
    main_model = _most_common(r["model"] for r in main["requests"])
    main_row = {
        "schema": SCHEMA, "backend": "claude", "kind": "main", "session": sid, "id": sid,
        "model": main_model, "tier": tier_of(main_model, "claude"),
        "effort": _most_common(r["effort"] for r in main["requests"]),
        "requests": len(main["requests"]), "tokens": _thread_tokens(main["requests"]),
        "first_ts": main["first_ts"], "last_ts": main["last_ts"],
        "compactions": sum(1 for k, _ in main["events"] if k == "compact"),
        "dispatches": len(main["dispatches"]),
        "read_summary": _read_summary(reads),
        "reads": [{k: r[k] for k in ("path", "ts", "startLine", "numLines", "totalLines", "chars", "full")}
                  for r in reads],
        "a_windows": {w: {"num": _r6(v["num"]), "num_compact": _r6(v["num_compact"]), "den": v["den"],
                          "requests": v["requests"], "qualifying_reads": v["qualifying_reads"]}
                      for w, v in sorted(windows.items())},
        "a_proxy_windows": {w: {"num": _r6(v["num"]), "num_compact": _r6(v["num_compact"]), "den": v["den"],
                                "requests": v["requests"], "qualifying_outputs": v["qualifying_reads"]}
                            for w, v in sorted(proxy.items())},
    }
    rows.append(main_row)

    by_tool_use = {}
    thread_tier = {"main": main_row["tier"]}
    sub_dispatches = {}
    for agent_id, meta, records in subagent_items:
        th = parse_claude_thread(records)
        model = _most_common(r["model"] for r in th["requests"])
        reads_s = [item for kind, item in th["events"] if kind == "read"]
        start_epoch = th["requests"][0]["epoch"] if th["requests"] else _epoch(th["first_ts"])
        row = {
            "schema": SCHEMA, "backend": "claude", "kind": "subagent", "session": sid, "id": agent_id,
            "parent": meta.get("parentAgentId") or "main",
            "agent_type": meta.get("agentType"), "description": meta.get("description"),
            "requested_model": meta.get("model"), "model": model, "tier": tier_of(model, "claude"),
            "effort": _most_common(r["effort"] for r in th["requests"]),
            "spawn_depth": meta.get("spawnDepth"), "tool_use_id": meta.get("toolUseId"),
            "requests": len(th["requests"]), "tokens": _thread_tokens(th["requests"]),
            "first_request": _first_request(th["requests"]),
            "final_report_chars": th["final_report_chars"],
            "final_report_output_tokens": th["final_report_output_tokens"],
            "first_ts": th["first_ts"], "last_ts": th["last_ts"],
            "window": window_of(start_epoch),
            "dispatches": len(th["dispatches"]),
            "read_summary": _read_summary(reads_s),
        }
        rows.append(row)
        if meta.get("toolUseId"):
            by_tool_use[meta["toolUseId"]] = row
        thread_tier[agent_id] = row["tier"]
        if th["dispatches"]:
            sub_dispatches[agent_id] = th["dispatches"]

    for parent, dlist in [("main", main["dispatches"])] + sorted(sub_dispatches.items()):
        group = []
        for d in dlist:
            child = by_tool_use.get(d["tool_use_id"])
            if child is not None and child["tier"] is not None:
                tier, basis = child["tier"], "child-model"
            elif tier_of(d["model"], "claude") is not None:
                tier, basis = tier_of(d["model"], "claude"), "requested-model"
            else:
                tier, basis = thread_tier.get(parent), "inherited"
            group.append({"epoch": d["epoch"], "key": _norm_task(d["description"], "claude"),
                          "prompt": d["prompt"], "tier": tier, "tier_basis": basis,
                          "effort": (child or {}).get("effort") or d["effort"]})
        groups.append(group)
    return main_row, rows[1:], groups


def _claude_sessions(entries):
    """Group manifest entries into sessions: <sid>.jsonl + <sid>/subagents/**/agent-*.jsonl."""
    sessions = {}
    other = []
    for e in entries:
        parts = Path(e["path"]).parts
        if len(parts) == 1 and parts[0].endswith(".jsonl"):
            sessions.setdefault(parts[0][:-6], {"main": None, "subs": []})["main"] = e
        elif len(parts) >= 3 and parts[1] == "subagents" and Path(parts[-1]).name.startswith("agent-"):
            sessions.setdefault(parts[0], {"main": None, "subs": []})["subs"].append(e)
        else:
            other.append(e)
    return sessions, other


# --------------------------------------------------------------------------- Codex


def _codex_keep(line):
    head = line[:240]
    return (any(m in head for m in _CODEX_MARKERS) or '"role":"assistant"' in head
            or '"name":"spawn_agent"' in line)


def parse_codex_rollout(records):
    meta = {}
    reqs = {}
    events = []
    model = effort = None
    dispatches = []
    final_text = ""
    last_total = None
    have_records = False
    first_ts = last_ts = None
    last_epoch = None
    tc_reqs = []
    for r in records:
        ts = r.get("timestamp")
        ep = _epoch(ts)
        if ep is not None:
            last_epoch = ep
            first_ts = first_ts or ts
            last_ts = ts
        rtype = r.get("type")
        p = r.get("payload") if isinstance(r.get("payload"), dict) else {}
        ptype = p.get("type")
        if rtype == "session_meta" and not meta:
            meta = p
        elif rtype == "turn_context":
            model = p.get("model") or model
            effort = p.get("effort") or (p.get("collaboration_mode") or {}).get("settings", {}).get("reasoning_effort") or effort
        elif rtype == "token_usage_record":
            have_records = True
            rid = p.get("response_id") or f"r{len(reqs)}"
            u = p.get("usage") or {}
            if rid not in reqs:
                events.append(("req", rid))
            reqs[rid] = _codex_req(rid, u, last_epoch, ts, model, effort)
        elif ptype == "token_count":
            info = p.get("info") or {}
            total = json.dumps(info.get("total_token_usage"), sort_keys=True)
            if info.get("last_token_usage") and total != last_total:
                last_total = total
                rid = f"tc{len(tc_reqs)}"
                tc_reqs.append(rid)
                reqs.setdefault(rid, _codex_req(rid, info["last_token_usage"], last_epoch, ts, model, effort))
                events.append(("tcreq", rid))
        elif ptype in ("function_call_output", "custom_tool_call_output"):
            out = p.get("output")
            if isinstance(out, list):
                out = "".join(b.get("text", "") for b in out if isinstance(b, dict))
            elif isinstance(out, dict):
                out = out.get("content") or json.dumps(out)
            if isinstance(out, str):
                events.append(("read", {"epoch": last_epoch, "ts": ts, "chars": len(out),
                                        "lines": out.count("\n") + 1}))
        elif ptype in ("function_call", "custom_tool_call") and p.get("name") == "spawn_agent":
            try:
                args = json.loads(p.get("arguments") or "{}")
            except (json.JSONDecodeError, TypeError):
                args = {}
            dispatches.append({"epoch": last_epoch, "ts": ts, "task_name": args.get("task_name") or "",
                               "model": args.get("model"), "effort": args.get("reasoning_effort")})
        elif ptype == "compacted" or rtype == "compacted":
            events.append(("compact", None))
        elif ptype == "task_complete":
            msg = p.get("last_agent_message")
            if isinstance(msg, str) and msg.strip():
                final_text = msg
        elif ptype == "agent_message" and rtype == "event_msg":
            msg = p.get("message")
            if isinstance(msg, str) and msg.strip():
                final_text = msg
        elif ptype == "message" and p.get("role") == "assistant":
            text = "".join(b.get("text", "") for b in p.get("content") or [] if isinstance(b, dict))
            if text.strip():
                final_text = text
    if have_records:
        events = [e for e in events if e[0] != "tcreq"]
        for rid in tc_reqs:
            reqs.pop(rid, None)
    else:
        events = [("req", e[1]) if e[0] == "tcreq" else e for e in events]
    ordered = [reqs[e[1]] for e in events if e[0] == "req"]
    return {"meta": meta, "requests": ordered, "events": events, "dispatches": dispatches,
            "final_report_chars": len(final_text),
            "final_report_output_tokens": ordered[-1]["output"] if ordered else None,
            "first_ts": first_ts, "last_ts": last_ts, "request_source":
                "token_usage_record" if have_records else "token_count"}


def _codex_req(rid, u, epoch, ts, model, effort):
    total_in = int(u.get("input_tokens") or 0)
    cached = int(u.get("cached_input_tokens") or 0)
    write = int(u.get("cache_write_input_tokens") or 0)
    return {"id": rid, "epoch": epoch, "ts": ts, "model": model, "effort": effort,
            "input": max(0, total_in - cached - write), "cache_creation": write,
            "cache_read": cached, "output": int(u.get("output_tokens") or 0)}


def _codex_class(meta):
    source = meta.get("source")
    if isinstance(source, dict) and isinstance(source.get("subagent"), dict):
        return "subagent"
    if meta.get("thread_source") == "subagent":
        return "subagent"
    if source == "exec" or meta.get("originator") == "codex_exec":
        return "exec"
    return "main"


def account_codex_rollout(rel_path, records, since_epoch=None):
    th = parse_codex_rollout(records)
    meta = th["meta"]
    klass = _codex_class(meta)
    spawn = {}
    if isinstance(meta.get("source"), dict):
        spawn = (meta["source"].get("subagent") or {}).get("thread_spawn") or {}
    model = _most_common(r["model"] for r in th["requests"])
    start_epoch = th["requests"][0]["epoch"] if th["requests"] else _epoch(th["first_ts"])
    large = lambda o: o["lines"] > LARGE_FILE_LINES
    row = {
        "schema": SCHEMA, "backend": "codex", "kind": klass, "id": meta.get("id") or rel_path,
        "file": rel_path, "session": meta.get("session_id"),
        "parent": meta.get("parent_thread_id") or spawn.get("parent_thread_id"),
        "agent_path": spawn.get("agent_path"), "spawn_depth": spawn.get("depth"),
        "originator": meta.get("originator"),
        "model": model, "tier": tier_of(model, "codex"),
        "effort": _most_common(r["effort"] for r in th["requests"]),
        "requests": len(th["requests"]), "request_source": th["request_source"],
        "tokens": _thread_tokens(th["requests"]),
        "first_request": _first_request(th["requests"]),
        "final_report_chars": th["final_report_chars"],
        "final_report_output_tokens": th["final_report_output_tokens"],
        "first_ts": th["first_ts"], "last_ts": th["last_ts"], "window": window_of(start_epoch),
        "dispatches": len(th["dispatches"]),
        "large_tool_outputs": sum(1 for k, o in th["events"] if k == "read" and large(o)),
    }
    if klass != "subagent":
        reqs_by_id = {r["id"]: r for r in th["requests"]}
        windows = carry_accounting(th["events"], reqs_by_id, large, lambda o: o["chars"],
                                   since_epoch=since_epoch)
        row["a_proxy_windows"] = {w: {"num": _r6(v["num"]), "num_compact": _r6(v["num_compact"]),
                                      "den": v["den"], "requests": v["requests"],
                                      "qualifying_outputs": v["qualifying_reads"]}
                                  for w, v in sorted(windows.items())}
    return row, th["dispatches"]


# --------------------------------------------------------------------------- re-dispatch


def redispatch_events(groups):
    """groups: list (per parent) of ordered dispatch dicts with epoch, key,
    prompt (optional), tier, effort. -> list of per-cheap-dispatch outcomes."""
    out = []
    for group in groups:
        ordered = sorted(group, key=lambda d: (d["epoch"] or 0))
        for i, d in enumerate(ordered):
            if d["tier"] is None or d["tier"] > CHEAP_MAX_TIER:
                continue
            higher = effort_up = False
            match_basis = None
            for later in ordered[i + 1:]:
                same = bool(d["key"]) and d["key"] == later["key"]
                basis = "description" if same else None
                if not same and len(d.get("prompt") or "") >= PROMPT_MIN_CHARS \
                        and len(later.get("prompt") or "") >= PROMPT_MIN_CHARS \
                        and _jaccard(d["prompt"], later["prompt"]) >= PROMPT_JACCARD:
                    same, basis = True, "prompt-jaccard"
                if not same:
                    continue
                if later["tier"] is not None and later["tier"] > d["tier"]:
                    higher, match_basis = True, basis
                    break
                if later["tier"] == d["tier"] and \
                        EFFORT_RANK.get(str(later.get("effort")), -1) > EFFORT_RANK.get(str(d.get("effort")), 99):
                    effort_up = True
            out.append({"epoch": d["epoch"], "tier": d["tier"], "higher_tier_redispatch": higher,
                        "match_basis": match_basis, "effort_only_redispatch": effort_up and not higher})
    return out


def _redispatch_summary(events, cutoff_epoch):
    def _rate(evs):
        n = len(evs)
        k = sum(1 for e in evs if e["higher_tier_redispatch"])
        eo = sum(1 for e in evs if e["effort_only_redispatch"])
        return {"cheap_dispatches": n, "higher_tier_redispatches": k,
                "rate": _r6(k / n) if n else None,
                "effort_only_redispatches": eo,
                "by_basis": dict(Counter(e["match_basis"] for e in evs if e["match_basis"]))}
    last30 = [e for e in events if e["epoch"] is not None and cutoff_epoch is not None
              and e["epoch"] >= cutoff_epoch - M2_DAYS * 86400]
    summary = {
        "all": _rate(events),
        "pre": _rate([e for e in events if window_of(e["epoch"]) == "pre"]),
        "post": _rate([e for e in events if window_of(e["epoch"]) == "post"]),
        "last_30_days": _rate(last30),
    }
    r = summary["last_30_days"]["rate"]
    summary["m2_trigger"] = ("fires" if r is not None and r >= M2_RATE else
                             "does-not-fire" if r is not None else "no-cheap-dispatches")
    return summary


# --------------------------------------------------------------------------- rollups


def decide(a_pre, a_post):
    if a_pre is None or a_post is None:
        return "re-measure"
    if a_pre >= A_FIRE and a_post >= A_FIRE:
        return "M1 fires"
    if a_pre < A_DECLINE and a_post < A_DECLINE:
        return "M1 declined"
    return "re-measure"


def _a_rollup(rows, key):
    out = {}
    for w in ("pre", "post"):
        num = numc = 0.0
        den = reqs = q = 0
        sessions = 0
        for row in rows:
            v = (row.get(key) or {}).get(w)
            if not v:
                continue
            sessions += 1
            num += v["num"]
            numc += v["num_compact"]
            den += v["den"]
            reqs += v["requests"]
            q += v.get("qualifying_reads", v.get("qualifying_outputs", 0))
        out[w] = {"A": _r6(num / den) if den else None,
                  "A_compaction_bounded": _r6(numc / den) if den else None,
                  "numerator_tokens": _r6(num), "denominator_tokens": den,
                  "main_requests": reqs, "qualifying_items": q, "sessions": sessions}
    return out


def _tier_rollup(rows, backend):
    tiers = {}
    for row in rows:
        name = tier_name(row.get("tier"), backend)
        t = tiers.setdefault(name, {"agents": 0, "tokens": _usage_block(), "requests": 0,
                                    "_overhead": [], "_overhead_share": [], "_report_chars": [],
                                    "_report_out": [], "_effort": Counter()})
        t["agents"] += 1
        t["requests"] += row["requests"]
        _add_usage(t["tokens"], row["tokens"])
        fr = row.get("first_request")
        if fr:
            t["_overhead"].append(fr["total_input"])
            if row["tokens"]["total_input"]:
                t["_overhead_share"].append(fr["total_input"] / row["tokens"]["total_input"])
        if row.get("final_report_output_tokens") is not None:
            t["_report_out"].append(row["final_report_output_tokens"])
        t["_report_chars"].append(row.get("final_report_chars") or 0)
        t["_effort"][str(row.get("effort"))] += 1
    out = {}
    for name, t in sorted(tiers.items()):
        tok = t["tokens"]
        tok["total_input"] = tok["input"] + tok["cache_creation"] + tok["cache_read"]
        tok["total"] = tok["total_input"] + tok["output"]
        out[name] = {"agents": t["agents"], "requests": t["requests"], "tokens": tok,
                     "first_request_input": _dist(t["_overhead"]),
                     "first_request_share_of_agent_input": _dist(t["_overhead_share"]),
                     "final_report_output_tokens": _dist(t["_report_out"]),
                     "final_report_chars": _dist(t["_report_chars"]),
                     "effort_mix": dict(sorted(t["_effort"].items()))}
    return out


def _main_tier_rollup(rows, backend):
    out = {}
    for row in rows:
        name = tier_name(row.get("tier"), backend)
        t = out.setdefault(name, {"threads": 0, "requests": 0, "tokens": _usage_block()})
        t["threads"] += 1
        t["requests"] += row["requests"]
        _add_usage(t["tokens"], row["tokens"])
    for t in out.values():
        tok = t["tokens"]
        tok["total_input"] = tok["input"] + tok["cache_creation"] + tok["cache_read"]
        tok["total"] = tok["total_input"] + tok["output"]
    return dict(sorted(out.items()))


def _spend_share(main_tiers, sub_tiers):
    main_total = sum(t["tokens"]["total"] for t in main_tiers.values())
    sub_total = sum(t["tokens"]["total"] for t in sub_tiers.values())
    grand = main_total + sub_total
    return {"main_total_tokens": main_total, "subagent_total_tokens": sub_total,
            "subagent_share": _r6(sub_total / grand) if grand else None,
            "by_subagent_tier_share": {k: _r6(v["tokens"]["total"] / grand) if grand else None
                                       for k, v in sub_tiers.items()}}


# --------------------------------------------------------------------------- driver


def account(manifest, since=None):
    """-> (rows, report). Reads only the manifest's frozen byte prefixes."""
    since_epoch = _epoch(since or manifest.get("since"))
    cutoff_epoch = _epoch(manifest.get("cutoff"))
    integrity = {"files": 0, "verified": 0, "mismatch": [], "missing": [], "unparsable_lines": 0,
                 "files_with_unparsable_lines": 0, "empty_threads": 0}
    rows = []
    claude_groups, codex_dispatch = [], {}

    def _open(entry):
        integrity["files"] += 1
        path = Path(entry["root"]) / entry["path"]
        if not path.is_file() or path.stat().st_size < entry["bytes"]:
            integrity["missing"].append(entry["path"])
            return None
        return _Prefix(path, entry["bytes"])

    def _finish(pref, entry):
        if pref.bad_lines:
            integrity["unparsable_lines"] += pref.bad_lines
            integrity["files_with_unparsable_lines"] += 1
        if pref.digest != entry["sha256"]:
            integrity["mismatch"].append(entry["path"])
            return False
        integrity["verified"] += 1
        return True

    claude_entries = [e for e in manifest["entries"] if e["backend"] == "claude"]
    sessions, other = _claude_sessions(claude_entries)
    integrity["claude_unclassified_files"] = [e["path"] for e in other]
    for sid in sorted(sessions):
        group = sessions[sid]
        main_records, ok = [], True
        if group["main"] is not None:
            pref = _open(group["main"])
            if pref is not None:
                main_records = list(pref.records(_claude_keep))
                ok = _finish(pref, group["main"])
            else:
                ok = False
        if not ok:
            main_records = []
        subs = []
        for e in sorted(group["subs"], key=lambda x: x["path"]):
            pref = _open(e)
            if pref is None:
                continue
            recs = list(pref.records(_claude_keep))
            if not _finish(pref, e):
                continue
            agent_id = Path(e["path"]).name[len("agent-"):-len(".jsonl")]
            meta_path = Path(e["root"]) / e["path"][:-len(".jsonl")]
            meta = {}
            try:
                meta = json.loads(Path(str(meta_path) + ".meta.json").read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                meta = {}
            subs.append((agent_id, meta, recs))
        main_row, sub_rows, groups = account_claude_session(sid, main_records, subs, since_epoch)
        main_row["main_file_present"] = group["main"] is not None and ok
        rows.append(main_row)
        rows.extend(sub_rows)
        claude_groups.extend(groups)

    codex_rows = []
    for e in sorted((x for x in manifest["entries"] if x["backend"] == "codex"), key=lambda x: x["path"]):
        pref = _open(e)
        if pref is None:
            continue
        recs = list(pref.records(_codex_keep))
        if not _finish(pref, e):
            continue
        if not recs:
            integrity["empty_threads"] += 1
            continue
        row, dispatches = account_codex_rollout(e["path"], recs, since_epoch)
        codex_rows.append(row)
        if dispatches:
            codex_dispatch[row["id"]] = (row, dispatches)
    rows.extend(codex_rows)

    # Codex dispatch tiers: requested model on spawn_agent, else the child's model.
    child_by_parent_task = {}
    for row in codex_rows:
        if row["kind"] == "subagent" and row["parent"] and row["agent_path"]:
            child_by_parent_task[(row["parent"], row["agent_path"].rstrip("/").split("/")[-1])] = row
    codex_groups = []
    for pid, (prow, dlist) in sorted(codex_dispatch.items()):
        group = []
        for d in dlist:
            child = child_by_parent_task.get((pid, d["task_name"]))
            tier = tier_of(d["model"], "codex")
            basis = "requested-model"
            if tier is None and child is not None:
                tier, basis = child["tier"], "child-model"
            if tier is None:
                tier, basis = prow["tier"], "inherited"
            group.append({"epoch": d["epoch"], "key": _norm_task(d["task_name"], "codex"),
                          "prompt": "", "tier": tier, "tier_basis": basis, "effort": d["effort"]})
        codex_groups.append(group)

    rows.sort(key=lambda r: (r["backend"], r.get("session") or "", r["kind"], r["id"]))
    report = build_report(rows, manifest, integrity, claude_groups, codex_groups, cutoff_epoch)
    return rows, report


def build_report(rows, manifest, integrity, claude_groups, codex_groups, cutoff_epoch):
    cl_main = [r for r in rows if r["backend"] == "claude" and r["kind"] == "main"]
    cl_sub = [r for r in rows if r["backend"] == "claude" and r["kind"] == "subagent"]
    cx_main = [r for r in rows if r["backend"] == "codex" and r["kind"] == "main"]
    cx_exec = [r for r in rows if r["backend"] == "codex" and r["kind"] == "exec"]
    cx_sub = [r for r in rows if r["backend"] == "codex" and r["kind"] == "subagent"]
    a = _a_rollup(cl_main, "a_windows")
    verdict = decide(a["pre"]["A"], a["post"]["A"])
    cl_main_tiers = _main_tier_rollup(cl_main, "claude")
    cl_sub_tiers = _tier_rollup(cl_sub, "claude")
    cx_main_tiers = _main_tier_rollup(cx_main + cx_exec, "codex")
    cx_sub_tiers = _tier_rollup(cx_sub, "codex")
    return {
        "schema": SCHEMA,
        "manifest": {"cutoff": manifest.get("cutoff"), "since": manifest.get("since"),
                     "files": len(manifest["entries"]),
                     "bytes": sum(e["bytes"] for e in manifest["entries"]),
                     "unreadable_at_manifest": len(manifest.get("unreadable") or [])},
        "integrity": {**integrity, "mismatch": sorted(integrity["mismatch"]),
                      "missing": sorted(integrity["missing"])},
        "decision_rule": {"split": WINDOW_SPLIT, "large_file_lines_gt": LARGE_FILE_LINES,
                          "fire_at_or_above": A_FIRE, "decline_below": A_DECLINE,
                          "chars_per_token": CHARS_PER_TOKEN},
        "claude": {
            "denominator": {"main_sessions": len(cl_main), "subagents": len(cl_sub),
                            "main_sessions_without_main_file": sum(1 for r in cl_main if not r.get("main_file_present"))},
            "A": a,
            "verdict": verdict,
            "main_by_tier": cl_main_tiers,
            "subagents_by_tier": cl_sub_tiers,
            "spend_share": _spend_share(cl_main_tiers, cl_sub_tiers),
            "fixed_overhead_all_subagents": _dist([r["first_request"]["total_input"] for r in cl_sub
                                                   if r.get("first_request")]),
            "A_proxy_large_tool_output_main": _a_rollup(cl_main, "a_proxy_windows"),
            "redispatch": _redispatch_summary(redispatch_events(claude_groups), cutoff_epoch),
        },
        "codex": {
            "denominator": {"main_rollouts": len(cx_main), "exec_rollouts": len(cx_exec),
                            "subagent_rollouts": len(cx_sub)},
            "A": None,
            "A_not_computable": "Codex rollouts record no structured file-read event "
                                "(no path/startLine/totalLines; reads are shell text inside exec)",
            "A_proxy_large_tool_output_main": _a_rollup(cx_main, "a_proxy_windows"),
            "A_proxy_large_tool_output_exec": _a_rollup(cx_exec, "a_proxy_windows"),
            "main_and_exec_by_tier": cx_main_tiers,
            "subagents_by_tier": cx_sub_tiers,
            "spend_share": _spend_share(cx_main_tiers, cx_sub_tiers),
            "fixed_overhead_all_subagents": _dist([r["first_request"]["total_input"] for r in cx_sub
                                                   if r.get("first_request")]),
            "redispatch": _redispatch_summary(redispatch_events(codex_groups), cutoff_epoch),
            "request_source": dict(Counter(r["request_source"] for r in rows if r["backend"] == "codex")),
        },
    }


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")
    os.replace(tmp, path)


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
