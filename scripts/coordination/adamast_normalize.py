#!/usr/bin/env python3
"""adamast_normalize.py - FM-2 Stage 1 enabler: transcripts -> AdaMAST canonical traces, plus a frozen stratified sample.

Canonical record (exactly four keys, AdaMAST `normalize` schema):
    {"problem_id": str, "task": str, "raw_trajectory": str, "metadata": dict}

OUTCOME-BLIND by construction: every key in OUTCOME_KEYS (outcome, final_gate_status, ...) is stripped recursively from
every record before rendering, and no outcome field is ever emitted. AdaMAST's own `outcome_blind_trace()` is a second
fence; this one means the judge input never contains the field even before that.

Subcommands (pure local file reads and writes; no network, no model calls):
  sample     --claude-root R [--codex-root R] --per-stratum N --seed S --manifest M.json
             strata = (harness, month, main|subagent); the manifest freezes every picked file's path/bytes/sha256 and is
             itself sha256-sealed (`manifest_sha256` over the canonical JSON of everything else).
  normalize  --manifest M.json --out-dir D     one D/<problem_id>.jsonl per trace (resumable: existing files skipped),
             plus D/index.jsonl. `--check` re-verifies each file's sha256 against the manifest first (fail on drift).
  smoke      --claude-root R --n 10            normalize N files, print a summary, write nothing.

Reuses delegation_accounting._epoch / _hash_file / _codex_class (same Claude/Codex classification as the accounting).
"""
import argparse
import hashlib
import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import delegation_accounting as da  # noqa: E402

SCHEMA = "adamast_normalize.v1"
MANIFEST_SCHEMA = "adamast_sample_manifest.v1"
CANON_KEYS = ("problem_id", "task", "raw_trajectory", "metadata")
OUTCOME_KEYS = frozenset({"outcome", "final_gate_status", "gate_status", "verdict", "result_status", "success",
                          "passed", "exit_status"})
BLOCK_CHARS = 4000            # per content block (tool output / text) in the rendered trajectory
TRAJ_CHARS = 400_000          # whole trajectory cap; truncation is recorded in metadata
TASK_CHARS = 8000
CLAUDE_KEEP_TYPES = ("user", "assistant")
CODEX_SESSION_META_KEYS = ("id", "source", "thread_source", "originator", "cli_version", "model_provider", "cwd",
                           "forked_from_id", "agent_role", "agent_nickname")


def strip_outcome(obj):
    """Recursively drop every OUTCOME_KEYS key (case-insensitive). Never mutates the input."""
    if isinstance(obj, dict):
        return {k: strip_outcome(v) for k, v in obj.items() if str(k).lower() not in OUTCOME_KEYS}
    if isinstance(obj, list):
        return [strip_outcome(v) for v in obj]
    return obj


def _clip(text, n=BLOCK_CHARS):
    if not isinstance(text, str):
        text = json.dumps(text, ensure_ascii=False, sort_keys=True)
    return text if len(text) <= n else text[:n] + f"...[truncated {len(text) - n} chars]"


def _blocks_text(content):
    """Message content (str | list of blocks) -> rendered text lines."""
    if isinstance(content, str):
        return [_clip(content)]
    out = []
    for b in content or []:
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if t == "text":
            out.append(_clip(b.get("text", "")))
        elif t == "thinking":
            continue                                    # reasoning is not part of the observable trajectory
        elif t == "tool_use":
            out.append("[tool_use %s] %s" % (b.get("name"), _clip(b.get("input", {}))))
        elif t == "tool_result":
            c = b.get("content")
            if isinstance(c, list):
                c = "".join(x.get("text", "") for x in c if isinstance(x, dict))
            out.append("[tool_result] " + _clip(c if c is not None else ""))
    return out


def _month(ts):
    ep = da._epoch(ts) if ts else None
    return datetime.fromtimestamp(ep, timezone.utc).strftime("%Y-%m") if ep is not None else None


def _read_records(path, limit_lines=None):
    recs, bad = [], 0
    with open(path, "rb") as fh:
        for i, raw in enumerate(fh):
            if limit_lines is not None and i >= limit_lines:
                break
            raw = raw.strip()
            if not raw:
                continue
            try:
                recs.append(json.loads(raw.decode("utf-8", errors="replace")))
            except json.JSONDecodeError:
                bad += 1
    return recs, bad


def detect_harness(records):
    for r in records[:50]:
        if r.get("type") in ("session_meta", "turn_context", "response_item", "event_msg"):
            return "codex"
        if r.get("type") in ("user", "assistant", "system", "attachment", "mode", "permission-mode", "last-prompt"):
            return "claude"
    return None


def classify(path, records):
    """-> (harness, kind) with kind in main|subagent, same rules as delegation_accounting."""
    harness = detect_harness(records)
    if harness == "codex":
        meta = next((r.get("payload") or {} for r in records if r.get("type") == "session_meta"), {})
        return harness, ("subagent" if da._codex_class(meta) == "subagent" else "main")
    sub = "/subagents/" in str(path).replace("\\", "/") or any(
        r.get("isSidechain") or r.get("agentId") for r in records[:200] if isinstance(r, dict))
    return harness, ("subagent" if sub else "main")


def normalize_claude(path, records):
    messages, lines, task, bad_types = [], [], "", 0
    session_id = agent_id = None
    for r in records:
        t = r.get("type")
        session_id = session_id or r.get("sessionId")
        if r.get("agentId"):
            agent_id = agent_id or r.get("agentId")
        if t not in CLAUDE_KEEP_TYPES:
            continue
        m = r.get("message") if isinstance(r.get("message"), dict) else {}
        texts = _blocks_text(m.get("content"))
        if not texts:
            continue
        if not task and t == "user" and not r.get("isMeta"):
            cand = " ".join(x for x in texts if not x.startswith("[tool_result]")).strip()
            if cand and not cand.startswith(("<command-", "<local-command", "Caveat:")):   # slash-command wrappers
                task = cand[:TASK_CHARS]
        role = m.get("role") or t
        lines.append(json.dumps({"role": role, "content": "\n".join(texts)}, ensure_ascii=False))
        messages.append({"uuid": r.get("uuid"), "parentUuid": r.get("parentUuid"), "agentId": r.get("agentId"),
                         "isSidechain": bool(r.get("isSidechain")), "type": t, "timestamp": r.get("timestamp")})
    return task, lines, messages, {"session_id": session_id, "agent_id": agent_id}


def normalize_codex(path, records):
    meta = next((r.get("payload") or {} for r in records if r.get("type") == "session_meta"), {})
    lines, messages, task = [], [], ""
    for r in records:
        p = r.get("payload") if isinstance(r.get("payload"), dict) else {}
        ptype = p.get("type")
        if r.get("type") != "response_item":
            continue
        ts = r.get("timestamp")
        if ptype == "message":
            text = "\n".join(_clip(b.get("text", "")) for b in p.get("content") or [] if isinstance(b, dict) and
                             b.get("text"))
            if not text:
                continue
            if not task and p.get("role") == "user" and "<environment_context>" not in text[:60]:
                task = text[:TASK_CHARS]
            lines.append(json.dumps({"role": p.get("role"), "content": text}, ensure_ascii=False))
        elif ptype in ("function_call", "custom_tool_call"):
            lines.append(json.dumps({"role": "assistant", "content": "[tool_use %s] %s" % (
                p.get("name"), _clip(p.get("arguments") or p.get("input") or ""))}, ensure_ascii=False))
        elif ptype in ("function_call_output", "custom_tool_call_output"):
            out = p.get("output")
            if isinstance(out, list):
                out = "".join(b.get("text", "") for b in out if isinstance(b, dict))
            elif isinstance(out, dict):
                out = out.get("content") or json.dumps(out, sort_keys=True)
            lines.append(json.dumps({"role": "tool", "content": "[tool_result] " + _clip(out or "")},
                                    ensure_ascii=False))
        else:
            continue
        messages.append({"type": ptype, "timestamp": ts})
    spawn = {k: meta.get(k) for k in CODEX_SESSION_META_KEYS if k in meta}
    return task, lines, messages, {"session_id": meta.get("id"), "session_meta": spawn,
                                   "thread_spawn": ((meta.get("source") or {}).get("subagent") or {}).get(
                                       "thread_spawn") if isinstance(meta.get("source"), dict) else None}


def normalize_file(path, root=None, records=None):
    """One transcript file -> the 4-field canonical dict (or None if it holds no renderable messages)."""
    path = Path(path)
    if records is None:
        records, bad = _read_records(path)
    else:
        bad = 0
    records = [strip_outcome(r) for r in records if isinstance(r, dict)]
    harness, kind = classify(path, records)
    if harness is None:
        return None
    if harness == "codex":
        task, lines, messages, extra = normalize_codex(path, records)
    else:
        task, lines, messages, extra = normalize_claude(path, records)
    if not lines:
        return None
    traj = "\n".join(lines)
    truncated = len(traj) > TRAJ_CHARS
    if truncated:
        traj = traj[:TRAJ_CHARS] + "\n[trajectory truncated]"
    rel = str(path.relative_to(root)) if root else path.name
    first_ts = next((m.get("timestamp") for m in messages if m.get("timestamp")), None)
    pid = hashlib.sha256(f"{harness}:{rel}".encode()).hexdigest()[:16]
    meta = {"harness": harness, "kind": kind, "is_subagent": kind == "subagent", "source_path": rel,
            "month": _month(first_ts), "first_timestamp": first_ts, "n_messages": len(messages),
            "bad_lines": bad, "truncated": truncated, "normalizer": SCHEMA, **extra}
    if harness == "claude":
        meta["messages"] = messages            # per-message agentId / isSidechain / parentUuid
    else:
        meta["messages"] = messages
    return {"problem_id": f"{harness}-{pid}", "task": task, "raw_trajectory": traj, "metadata": meta}


# --------------------------------------------------------------------------------------------- sampler


def _stratum_of(path, root):
    recs, _ = _read_records(path, limit_lines=400)
    harness, kind = classify(path, recs)
    ts = next((r.get("timestamp") for r in recs if r.get("timestamp")), None)
    if ts is None:
        ts = next((((r.get("payload") or {}).get("timestamp")) for r in recs if r.get("type") == "session_meta"), None)
    month = _month(ts) or datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m")
    return harness, month, kind


def _candidates(claude_root, codex_root):
    for backend, root, pat in (("claude", claude_root, "**/*.jsonl"), ("codex", codex_root, "**/rollout-*.jsonl")):
        if root:
            for p in sorted(Path(root).glob(pat)):
                yield backend, Path(root), p


def build_sample(claude_root, codex_root, per_stratum, seed):
    strata = {}
    for backend, root, p in _candidates(claude_root, codex_root):
        try:
            harness, month, kind = _stratum_of(p, root)
        except OSError:
            continue
        if harness is None:
            continue
        strata.setdefault((harness, month, kind), []).append((root, p))
    entries = []
    for key in sorted(strata):
        pool = strata[key]
        rng = random.Random(f"{seed}|{key[0]}|{key[1]}|{key[2]}")   # stratum-local: adding a stratum never reshuffles others
        for root, p in sorted(rng.sample(pool, min(per_stratum, len(pool))), key=lambda x: str(x[1])):
            digest, size = da._hash_file(p)
            entries.append({"stratum": "|".join(key), "harness": key[0], "month": key[1], "kind": key[2],
                            "root": str(root), "path": str(p.relative_to(root)), "bytes": size, "sha256": digest})
    body = {"schema": MANIFEST_SCHEMA, "seed": seed, "per_stratum": per_stratum,
            "claude_root": str(claude_root) if claude_root else None,
            "codex_root": str(codex_root) if codex_root else None,
            "strata": {"|".join(k): {"population": len(v), "picked": min(per_stratum, len(v))}
                       for k, v in sorted(strata.items())},
            "entries": entries}
    body["manifest_sha256"] = manifest_seal(body)
    return body


def manifest_seal(body):
    core = {k: v for k, v in body.items() if k != "manifest_sha256"}
    return hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_manifest(manifest):
    problems = []
    if manifest_seal(manifest) != manifest.get("manifest_sha256"):
        problems.append("manifest seal mismatch")
    for e in manifest["entries"]:
        p = Path(e["root"]) / e["path"]
        try:
            d, n = da._hash_file(p, e["bytes"])   # prefix hash: live session files may have grown since the freeze
        except OSError as exc:
            problems.append(f"{e['path']}: {type(exc).__name__}")
            continue
        if d != e["sha256"]:
            problems.append(f"{e['path']}: prefix sha256 drift")
    return problems


def normalize_manifest(manifest, out_dir):
    out = Path(out_dir)
    (out / "traces").mkdir(parents=True, exist_ok=True)
    index, skipped = [], 0
    for e in manifest["entries"]:
        root, p = Path(e["root"]), Path(e["root"]) / e["path"]
        # read exactly the frozen prefix so the trace is a function of the manifest, not of the live file
        pre = da._Prefix(p, e["bytes"])
        recs = list(pre.records())
        rec = normalize_file(p, root=root, records=recs)
        if rec is None:
            skipped += 1
            continue
        rec["metadata"]["stratum"] = e["stratum"]
        rec["metadata"]["source_sha256"] = e["sha256"]
        dest = out / "traces" / f"{rec['problem_id']}.jsonl"
        if dest.exists():
            index.append({"problem_id": rec["problem_id"], "resumed": True})
            continue
        tmp = dest.with_suffix(".part")
        tmp.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, dest)
        index.append({"problem_id": rec["problem_id"], "stratum": e["stratum"], "chars": len(rec["raw_trajectory"])})
    (out / "index.jsonl").write_text("".join(json.dumps(i) + "\n" for i in index), encoding="utf-8")
    return {"written": len(index), "skipped_empty": skipped}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample")
    s.add_argument("--claude-root")
    s.add_argument("--codex-root")
    s.add_argument("--per-stratum", type=int, default=3)
    s.add_argument("--seed", default="fm2-adamast-20261110")
    s.add_argument("--manifest", required=True)
    n = sub.add_parser("normalize")
    n.add_argument("--manifest", required=True)
    n.add_argument("--out-dir", required=True)
    n.add_argument("--check", action="store_true")
    k = sub.add_parser("smoke")
    k.add_argument("--claude-root", required=True)
    k.add_argument("--n", type=int, default=10)
    k.add_argument("--seed", default="fm2-smoke")
    a = ap.parse_args(argv)
    if a.cmd == "sample":
        if not (a.claude_root or a.codex_root):
            ap.error("need --claude-root and/or --codex-root")
        m = build_sample(a.claude_root, a.codex_root, a.per_stratum, a.seed)
        Path(a.manifest).write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")
        print(f"manifest {a.manifest} entries={len(m['entries'])} strata={len(m['strata'])} sha256={m['manifest_sha256']}")
        return 0
    if a.cmd == "normalize":
        m = json.loads(Path(a.manifest).read_text())
        if a.check:
            bad = verify_manifest(m)
            if bad:
                print("DRIFT " + "; ".join(bad[:5]), file=sys.stderr)
                return 3
        print(json.dumps(normalize_manifest(m, a.out_dir)))
        return 0
    m = build_sample(a.claude_root, None, 2, a.seed)
    rows = []
    for e in m["entries"][:a.n]:
        root, p = Path(e["root"]), Path(e["root"]) / e["path"]
        rec = normalize_file(p, root=root, records=list(da._Prefix(p, e["bytes"]).records()))
        rows.append((e["stratum"], rec))
    for st, rec in rows:
        if rec is None:
            print(f"{st}: EMPTY")
            continue
        md = rec["metadata"]
        print(f"{st}: keys={sorted(rec)} msgs={md['n_messages']} traj_chars={len(rec['raw_trajectory'])} "
              f"sidechain_msgs={sum(1 for x in md['messages'] if x.get('isSidechain'))} task={rec['task'][:50]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
