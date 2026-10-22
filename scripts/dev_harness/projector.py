#!/usr/bin/env python3
"""Private dev-harness transcript projector (UTM-LB2).

Reads Claude Code JSONL, Codex rollouts and opencode V1/V2 from the EXISTING conversation backup
(cloud-llm-vault; ai-sessions tarballs streamed; live stores only for what the last nightly sync
has not captured — see dh_sources.py) and writes content-free events to the private root:

  <private-root>/projections/<run-id>/
      events/<harness>/<unit_key>.jsonl   dev-harness-event.v1   (one row per transcript event)
      sessions.jsonl                      dev-harness-session.v1 (one row per transcript unit)
      commits.jsonl                       dev-harness-commit-join.v1 (session -> commit sha)
      run.json                            dev-harness-projection-run.v1 (inputs, counts, stamps)

Content never leaves memory: each text becomes keyed-HMAC-SHA256 hashes of 64-token blocks
(key at <private-root>/keys/block_hmac.key) plus char/token counts. Outputs are private
(F3-LB1, dh_privacy): never commit them; publish only aggregates via dh_privacy.publish_aggregate.

Event field conventions
  * detail_json carries OTel GenAI names (semantic-conventions-genai @ SEMCONV['commit'],
    Development stability): gen_ai.operation.name, gen_ai.tool.name, gen_ai.tool.call.id,
    gen_ai.conversation.id (native id only, never fabricated), gen_ai.agent.name,
    gen_ai.request.model, gen_ai.response.id, gen_ai.response.finish_reasons,
    gen_ai.usage.{input_tokens, output_tokens, cache_read.input_tokens,
    cache_creation.input_tokens, reasoning.output_tokens}. input_tokens is INCLUSIVE of cache
    per OTel; each harness's raw tuple and convention are kept under dh.usage_raw /
    dh.usage_convention.
  * Usage dedupe: Claude by message id (streaming lines repeat usage); Codex from
    token_usage_record per response id (token_count snapshots are cumulative and never summed);
    opencode from the message row (step-finish parts not summed).
  * Beacon provenance: collection_method (vault_file|tarball_member|live_file|sqlite_row) and
    fidelity (observed|inferred) on every event; lineage edge_kind spawn|fork on sessions.

Cheap by construction: stdlib only, streaming per file, run it under ``nice -n 19``.

    nice -n 19 python3 scripts/dev_harness/projector.py --claude 8 --codex 8 --opencode 4
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dh_privacy  # noqa: E402
import dh_sources as src  # noqa: E402

EVENT_SCHEMA = "dev-harness-event.v1"
SESSION_SCHEMA = "dev-harness-session.v1"
COMMIT_SCHEMA = "dev-harness-commit-join.v1"
RUN_SCHEMA = "dev-harness-projection-run.v1"
HASH_SCHEME = "hmac-sha256-trunc16/64-token-blocks/v1"
BLOCK_TOKENS = 64
SEMCONV = {
    "repo": "open-telemetry/semantic-conventions-genai",
    "commit": "9ffc7e00",
    "schema_url": "gen-ai-dev/1.42.0-dev",
    "stability": "development",
    "note": "pending fragment renames cache_creation -> cache_write; re-check before relying on names",
}
_TOKEN_RE = re.compile(r"\w+|[^\w\s]")
REPOS = {
    "epyc-root": "/workspace",
    "epyc-orchestrator": "/workspace/repos/epyc-orchestrator",
    "epyc-inference-research": "/workspace/repos/epyc-inference-research",
}


def block_hashes(text: str, key: bytes) -> tuple[int, list[str]]:
    toks = _TOKEN_RE.findall(text or "")
    out = []
    for i in range(0, len(toks), BLOCK_TOKENS):
        block = " ".join(toks[i:i + BLOCK_TOKENS]).encode("utf-8")
        out.append(hmac.new(key, block, hashlib.sha256).hexdigest()[:16])
    return len(toks), out


def project_record(unit: src.Unit, r: dict, key: bytes) -> dict:
    d: dict = {}
    if r.get("operation"):
        d["gen_ai.operation.name"] = r["operation"]
    if unit.conversation_id:
        d["gen_ai.conversation.id"] = unit.conversation_id
    if unit.agent_name:
        d["gen_ai.agent.name"] = unit.agent_name
    for k_src, k_otel in (("tool_name", "gen_ai.tool.name"), ("tool_call_id", "gen_ai.tool.call.id"),
                          ("model", "gen_ai.request.model"), ("response_id", "gen_ai.response.id")):
        if r.get(k_src):
            d[k_otel] = r[k_src]
    if r.get("finish_reason"):
        d["gen_ai.response.finish_reasons"] = [r["finish_reason"]]
    u = r.get("usage")
    if u:
        d["gen_ai.usage.input_tokens"] = u["input_inclusive"]
        d["gen_ai.usage.output_tokens"] = u["output"]
        d["gen_ai.usage.cache_read.input_tokens"] = u["cache_read"]
        d["gen_ai.usage.cache_creation.input_tokens"] = u["cache_creation"]
        if u.get("reasoning") is not None:
            d["gen_ai.usage.reasoning.output_tokens"] = u["reasoning"]
        d["dh.usage_raw"] = u["raw"]
        d["dh.usage_convention"] = u["convention"]
        d["dh.usage_dedupe"] = r.get("usage_dedupe")
    for k in ("role", "interrupt", "denial", "is_error", "is_meta", "human", "subtype", "subagent_type",
              "value", "v2_type"):
        if r.get(k) not in (None, False, ""):
            d[f"dh.{k}"] = r[k]
    n_tok, hashes = block_hashes(r.get("text") or "", key)
    ev = {
        "schema": EVENT_SCHEMA,
        "harness": unit.harness,
        "unit_key": unit.unit_key,
        "conversation_id": unit.conversation_id,
        "agent_instance_id": unit.agent_instance_id,
        "collection_method": unit.collection_method,
        "fidelity": r.get("fidelity", "observed"),
        "source_path": unit.source_path,
        "source_line": r.get("source_line"),
        "ts": r.get("ts"),
        "event_kind": r["kind"],
        "detail_json": d,
        "content": {"n_chars": len(r.get("text") or ""), "n_tokens": n_tok, "block_hashes": hashes,
                    "hash_scheme": HASH_SCHEME},
    }
    if r.get("commit_shas"):
        ev["commit_shas"] = r["commit_shas"]
    return ev


def summarize_unit(unit: src.Unit, events: list[dict]) -> dict:
    kinds = Counter(e["event_kind"] for e in events)
    interrupts = Counter(r.get("interrupt") for r in unit.records if r.get("interrupt"))
    denials = Counter(r.get("denial") for r in unit.records if r.get("denial"))
    usage = Counter()
    for r in unit.records:
        if r.get("usage"):
            for k in ("input_inclusive", "output", "cache_read", "cache_creation"):
                usage[k] += r["usage"][k] or 0
            usage["reasoning"] += r["usage"].get("reasoning") or 0
            usage["n_usage_records"] += 1
    shas = sorted({s for r in unit.records for s in (r.get("commit_shas") or [])})
    tss = sorted(e["ts"] for e in events if e.get("ts"))
    return {
        "schema": SESSION_SCHEMA,
        "harness": unit.harness,
        "unit_key": unit.unit_key,
        "conversation_id": unit.conversation_id,
        "agent_name": unit.agent_name,
        "agent_instance_id": unit.agent_instance_id,
        "parent_conversation_id": unit.parent_conversation_id,
        "parent_tool_call_id": unit.parent_tool_call_id,
        "edge_kind": unit.edge_kind,
        "edge_fidelity": unit.edge_fidelity,
        "collection_method": unit.collection_method,
        "source_path": unit.source_path,
        "source_schema_key": unit.source_schema_key(),
        "semconv": SEMCONV["commit"],
        "first_ts": tss[0] if tss else None,
        "last_ts": tss[-1] if tss else None,
        "n_events": len(events),
        "event_kinds": dict(kinds),
        "human_turns": sum(1 for r in unit.records if r.get("human")),
        "tool_calls": kinds.get("tool_call", 0),
        "tool_errors": sum(1 for r in unit.records if r["kind"] == "tool_result" and r.get("is_error")),
        "interrupts": dict(interrupts),
        "denials": dict(denials),
        "usage": dict(usage),
        "commit_shas": shas,
        "parse_errors": unit.parse_errors,
    }


def resolve_commits(shas: Iterable[str]) -> dict[str, str]:
    """sha -> repo name for shas that exist in a local repo (read-only cat-file batch)."""
    shas = sorted(set(shas))
    found: dict[str, str] = {}
    if not shas:
        return found
    for name, path in REPOS.items():
        todo = [s for s in shas if s not in found]
        if not todo or not Path(path).exists():
            continue
        proc = subprocess.run(["git", "-C", path, "cat-file", "--batch-check"], input="\n".join(todo) + "\n",
                              capture_output=True, text=True, timeout=120, check=False)
        for sha, line in zip(todo, proc.stdout.splitlines()):
            if line.split(" ")[1:2] == ["commit"]:
                found[sha] = name
    return found


def code_commit() -> str | None:
    try:
        return subprocess.run(["git", "-C", str(Path(__file__).resolve().parent), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=30, check=True).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None


def gather_units(a: argparse.Namespace) -> Iterator[src.Unit]:
    vault = Path(a.vault)
    if a.claude is not None:
        yield from src.select_vault_units("claude_code", a.claude, vault=vault, tenant=a.tenant,
                                          max_bytes=int(a.max_file_mb * (1 << 20)))
    if a.codex is not None:
        yield from src.select_vault_units("codex", a.codex, vault=vault, tenant=a.tenant,
                                          max_bytes=int(a.max_file_mb * (1 << 20)))
    if a.include_live:
        for main in src.live_claude_newer_than_vault(vault_claude=vault / a.tenant / "claude"):
            yield src.claude_file_unit(main, "live_file")
            for s in sorted((main.parent / main.stem / "subagents").glob("agent-*.jsonl")):
                yield src.claude_file_unit(s, "live_file")
    for tb in a.tarball or []:
        yield from src.iter_tarball_units(Path(tb), limit=a.tarball_limit)
    if a.opencode is not None:
        db = Path(a.opencode_db)
        if db.exists():
            yield from src.select_opencode_units(db, a.opencode)


def run(a: argparse.Namespace) -> dict:
    t0 = time.time()
    root = Path(a.private_root)
    run_id = a.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = dh_privacy.private_dir(root / "projections" / run_id)
    key = dh_privacy.hmac_key(root)
    sessions, all_shas = [], {}
    n_events = 0
    by_harness = Counter()
    for unit in gather_units(a):
        events = [project_record(unit, r, key) for r in unit.records]
        hdir = dh_privacy.private_dir(out / "events" / unit.harness)
        dh_privacy.private_write(hdir / f"{unit.unit_key}.jsonl",
                                 "".join(json.dumps(e, sort_keys=True) + "\n" for e in events))
        s = summarize_unit(unit, events)
        sessions.append(s)
        n_events += len(events)
        by_harness[unit.harness] += 1
        for sha in s["commit_shas"]:
            all_shas.setdefault(sha, []).append(s)
    resolved = resolve_commits(all_shas) if a.resolve_commits else {}
    joins = []
    for sha, ss in sorted(all_shas.items()):
        for s in ss:
            joins.append({"schema": COMMIT_SCHEMA, "sha": sha, "repo": resolved.get(sha),
                          "harness": s["harness"], "conversation_id": s["conversation_id"],
                          "unit_key": s["unit_key"], "last_ts": s["last_ts"]})
    dh_privacy.private_write(out / "sessions.jsonl", "".join(json.dumps(s, sort_keys=True) + "\n" for s in sessions))
    dh_privacy.private_write(out / "commits.jsonl", "".join(json.dumps(j, sort_keys=True) + "\n" for j in joins))
    manifest = {
        "schema": RUN_SCHEMA, "run_id": run_id, "code_commit": code_commit(), "semconv": SEMCONV,
        "hash_scheme": HASH_SCHEME, "last_vault_sync": (src.last_vault_sync() or datetime.min).isoformat(),
        "inputs": {"vault": a.vault, "tenant": a.tenant, "claude": a.claude, "codex": a.codex,
                   "opencode": a.opencode, "max_file_mb": a.max_file_mb, "opencode_db": a.opencode_db if a.opencode is not None else None,
                   "tarball": a.tarball, "include_live": a.include_live},
        "units": dict(by_harness), "events": n_events, "commit_joins": len(joins),
        "commits_resolved": len(resolved), "elapsed_s": round(time.time() - t0, 2),
    }
    dh_privacy.private_write(out / "run.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    manifest["out_dir"] = str(out)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--private-root", default=str(dh_privacy.PRIVATE_ROOT))
    p.add_argument("--run-id")
    p.add_argument("--vault", default=str(src.VAULT_ROOT))
    p.add_argument("--tenant", default="epyc", help="vault tenant dir: epyc | host | twyne")
    p.add_argument("--claude", type=int, help="N most recent Claude Code sessions from the vault (0 = all)")
    p.add_argument("--codex", type=int, help="N most recent Codex rollouts from the vault (0 = all)")
    p.add_argument("--max-file-mb", type=float, default=8.0,
                   help="skip vault transcripts larger than this (sample cheapness; 0 = no cap for full runs)")
    p.add_argument("--opencode", type=int, help="N most recent opencode sessions (0 = all)")
    p.add_argument("--opencode-db", default=str(src.LIVE_OPENCODE_DB),
                   help="opencode sqlite (opened immutable=1); a decompressed backup snapshot also works")
    p.add_argument("--tarball", action="append", help="ai-sessions tarball to stream (repeatable)")
    p.add_argument("--tarball-limit", type=int)
    p.add_argument("--include-live", action="store_true",
                   help="also read live ~/.claude/projects files newer than the last vault sync")
    p.add_argument("--no-resolve-commits", dest="resolve_commits", action="store_false")
    return p


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    if os.environ.get("DEV_HARNESS_ALLOW_NOT_NICE") != "1" and os.nice(0) < 10:
        os.nice(19 - os.nice(0))
    m = run(a)
    print(json.dumps(m, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
