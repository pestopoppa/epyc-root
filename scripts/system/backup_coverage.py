#!/usr/bin/env python3
"""Read-only coverage check of the EXISTING conversation backup (UTM-LB1) + reaper precondition (NIB2-LB1).

The host already runs a nightly root cron job (operator ruling 2026-10-22: build NO parallel backup):
  02:00Z  cloud-llm-vault sync   /mnt/raid0/llm/cloud-llm-vault/{epyc,host,twyne}/{claude,codex}  (immutable)
  ~02:15Z ai-sessions tarball     /mnt/raid0/llm/claude-backups/ai-sessions-*.tar.gz  (keep 14)
          micron snapshot          /mnt/micron/backups (vault only, keep 60; host mount, not visible here)
and logs to claude-backups/backup.log + LAST_STATUS.

This tool copies nothing, writes nothing outside --out, changes no retention and never opens a store
for writing. It answers, per dev-harness store: is it held by the vault or a tarball, and since when.

    python3 scripts/system/backup_coverage.py report [--tarball-listing FILE] [--json]
    python3 scripts/system/backup_coverage.py precondition --store opencode_db [--rows-before ISO]

``--tarball-listing`` takes the output of ``tar tvzf <newest ai-sessions tarball>`` (listing a
7.8 GB tarball costs ~3 min of one core; do it under nice, once, and pass the file). Without it,
tarball membership is reported as ``unknown`` rather than guessed.

PRECONDITION (NIB2-LB1). Before any reaper deletes rows/files of a store, ``precondition`` must exit 0:
the store is ``covered`` and its newest backup evidence is not older than --rows-before (the
newest row/file the reaper would delete). Exit 3 = not covered (the reaper must not delete; the
operator decides — see the decision package in unified-trace-memory-service.md UTM-LB1), exit 4 =
covered but the newest backup predates the rows. This tool never authorises an extract or a copy.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
VAULT = Path("/mnt/raid0/llm/cloud-llm-vault")
BACKUPS = Path("/mnt/raid0/llm/claude-backups")
ORCH = Path("/workspace/repos/epyc-orchestrator")
KEEP_TARBALLS = 14
STALE_H = 36

# store -> (live globs, vault globs, tarball member regex, extra backup-file globs)
STORES: dict[str, dict] = {
    "claude_transcripts": {
        "live": [str(HOME / ".claude/projects/*/*.jsonl"), str(HOME / ".claude/projects/*/*/subagents/*.jsonl")],
        "vault": [str(VAULT / "*/claude/*/*.jsonl"), str(VAULT / "*/claude/*/*/subagents/*.jsonl")],
        "tar": r"(^|/)(\.claude/)?projects/[^/]+/([^/]+\.jsonl|[^/]+/subagents/agent-[^/]+\.jsonl)$",
    },
    "claude_history": {
        "live": [str(HOME / ".claude/history.jsonl")],
        "vault": [str(VAULT / "*/claude/history.jsonl"), str(VAULT / "*/history.jsonl")],
        "tar": r"(^|/)history\.jsonl$",
    },
    "claude_memory": {
        "live": [str(HOME / ".claude/projects/*/memory/*.md")],
        "vault": [str(VAULT / "*/claude/*/memory/*.md")],
        "tar": r"(^|/)projects/[^/]+/memory/[^/]+\.md$",
    },
    "codex_rollouts": {
        "live": [str(HOME / ".codex/sessions/*/*/*/rollout-*.jsonl")],
        "vault": [str(VAULT / "*/codex/*/*/*/rollout-*.jsonl")],
        "tar": r"(^|/)(\.codex/)?sessions/\d{4}/\d\d/\d\d/rollout-[^/]+\.jsonl$",
    },
    "codex_state_sqlite": {
        "live": [str(HOME / ".codex/state_*.sqlite"), str(HOME / ".codex/thread_history_*.sqlite")],
        "vault": [str(VAULT / "*/codex/*.sqlite")],
        "tar": r"(^|/)(state|thread_history)_\d+\.sqlite$",
    },
    "opencode_db": {
        "live": [str(HOME / ".local/share/opencode/opencode.db")],
        "vault": [str(VAULT / "*/opencode*")],
        "tar": r"(^|/)opencode[^/]*\.db$",
        "files": [str(BACKUPS / "opencode-*.db.zst")],
    },
    "agent_audit_and_orch_logs": {
        "live": ["/workspace/logs/agent_audit*.log", str(ORCH / "logs/*.log")],
        "vault": [str(VAULT / "*/logs/agent_audit*.log")],
        "tar": r"(^|/)agent_audit[^/]*\.log$",
    },
    "serving_calls": {
        "live": [str(ORCH / "logs/serving_calls/serving_calls.jsonl")],
        "vault": [str(VAULT / "*/serving_calls*")],
        "tar": r"(^|/)serving_calls\.jsonl$",
    },
    "planner_archive": {
        "live": [str(ORCH / "logs/planner_archive.jsonl")],
        "vault": [str(VAULT / "*/planner_archive*")],
        "tar": r"(^|/)planner_archive\.jsonl$",
    },
}


def _iso(ts: float | None) -> str | None:
    return None if ts is None else datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")


def _files(globs: list[str]) -> list[Path]:
    out: set[Path] = set()
    for g in globs:
        out.update(Path(p) for p in glob.glob(g))
    return sorted(p for p in out if p.is_file())


def _content_start(paths: list[Path], max_files: int = 20000) -> str | None:
    """Earliest record timestamp found in the first lines of the files (content date, not mtime)."""
    best = None
    pat = re.compile(r'"timestamp"\s*:\s*"(\d{4}-\d\d-\d\dT[^"]+)"')
    for p in paths[:max_files]:
        m = re.search(r"rollout-(\d{4}-\d\d-\d\dT\d\d-\d\d-\d\d)", p.name)
        if m:
            cand = m.group(1)[:10]
        else:
            cand = None
            try:
                with p.open("r", encoding="utf-8", errors="replace") as fh:
                    for _ in range(30):
                        line = fh.readline()
                        if not line:
                            break
                        mm = pat.search(line)
                        if mm:
                            cand = mm.group(1)[:10]
                            break
            except OSError:
                continue
        if cand and (best is None or cand < best):
            best = cand
    return best


def job_status(backups: Path = BACKUPS) -> dict:
    log = backups / "backup.log"
    st: dict = {"backup_log": str(log), "last_status": None, "last_status_age_h": None, "last_vault_line": None,
                "last_micron_line": None, "tarballs": [], "tarballs_expected": KEEP_TARBALLS}
    try:
        st["last_status"] = (backups / "LAST_STATUS").read_text().strip()
        m = re.match(r"(\S+Z)", st["last_status"])
        if m:
            age = datetime.now(timezone.utc) - datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            st["last_status_age_h"] = round(age.total_seconds() / 3600, 1)
    except OSError:
        pass
    try:
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        lines = []
    for line in reversed(lines):
        if st["last_vault_line"] is None and " VAULT " in line:
            st["last_vault_line"] = line
        if st["last_micron_line"] is None and " MICRON " in line:
            st["last_micron_line"] = line
    st["log_rsync_errors"] = sum(1 for line in lines if line.startswith("rsync error"))
    days = sorted({line[:10] for line in lines if re.match(r"\d{4}-\d\d-\d\dT.* BACKUP ", line)})
    st["backup_days_logged"] = len(days)
    st["backup_day_gaps"] = _gaps(days)
    tbs = sorted(backups.glob("ai-sessions-*.tar.gz"))
    st["tarballs"] = [{"name": t.name, "bytes": t.stat().st_size, "mtime": _iso(t.stat().st_mtime)} for t in tbs]
    st["live"] = (st["last_status_age_h"] is not None and st["last_status_age_h"] <= STALE_H
                  and "OK" in (st["last_status"] or ""))
    return st


def _gaps(days: list[str]) -> list[str]:
    from datetime import date, timedelta
    gaps = []
    ds = [date.fromisoformat(d) for d in days]
    for a, b in zip(ds, ds[1:]):
        if (b - a).days > 1:
            gaps.append(f"{a + timedelta(days=1)}..{b - timedelta(days=1)} ({(b - a).days - 1} d)")
    return gaps


def store_report(name: str, spec: dict, tar_members: list[str] | None) -> dict:
    live = _files(spec["live"])
    vault = _files(spec["vault"])
    extra = _files(spec.get("files", []))
    r: dict = {"store": name, "live_files": len(live), "live_newest": _iso(max((p.stat().st_mtime for p in live), default=None)),
               "vault_files": len(vault), "vault_newest": _iso(max((p.stat().st_mtime for p in vault), default=None)),
               "vault_content_from": _content_start(vault) if vault and name in ("claude_transcripts", "codex_rollouts") else None,
               "backup_files": [p.name for p in extra],
               "backup_files_newest": _iso(max((p.stat().st_mtime for p in extra), default=None))}
    if tar_members is None:
        r["tarball_members"] = "unknown (no --tarball-listing)"
        in_tar = False
    else:
        rx = re.compile(spec["tar"])
        n = sum(1 for m in tar_members if rx.search(m))
        r["tarball_members"] = n
        in_tar = n > 0
    if vault or in_tar:
        r["covered"] = "covered"
    elif extra:
        r["covered"] = "partial"          # a backup file exists but no nightly cadence is proven here
    else:
        r["covered"] = "not_covered"
    r["evidence"] = ", ".join(x for x in (
        f"vault {len(vault)} files" if vault else "",
        f"tarball {r['tarball_members']} members" if in_tar else "",
        f"backup files {', '.join(r['backup_files'])}" if extra else "") if x) or "none"
    return r


def _tar_members(listing: str | None) -> list[str] | None:
    if not listing:
        return None
    members = []
    for line in Path(listing).read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if parts:
            members.append(parts[-1])
    return members


def cmd_report(a) -> int:
    tar = _tar_members(a.tarball_listing)
    rep = {"schema": "backup-coverage.v1", "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "job": job_status(), "tarball_listing": a.tarball_listing,
           "stores": [store_report(n, s, tar) for n, s in STORES.items()]}
    if a.json:
        print(json.dumps(rep, indent=2))
    else:
        j = rep["job"]
        print(f"job live={j['live']}  {j['last_status']}  age={j['last_status_age_h']}h  "
              f"tarballs={len(j['tarballs'])}/{j['tarballs_expected']}  gaps={j['backup_day_gaps']}")
        for s in rep["stores"]:
            print(f"  {s['store']:<28} {s['covered']:<12} {s['evidence']}"
                  + (f"  (content from {s['vault_content_from']})" if s.get("vault_content_from") else ""))
    return 0


def cmd_precondition(a) -> int:
    if a.store not in STORES:
        print(f"unknown store {a.store}; known: {sorted(STORES)}", file=sys.stderr)
        return 2
    r = store_report(a.store, STORES[a.store], _tar_members(a.tarball_listing))
    j = job_status()
    if r["covered"] != "covered" or not j["live"]:
        print(f"PRECONDITION FAILED: {a.store} is {r['covered']} (job live={j['live']}); evidence: {r['evidence']}. "
              "Do not delete: the operator decides (NIB2-LB1).", file=sys.stderr)
        return 3
    newest = max(filter(None, [r["vault_newest"], r["backup_files_newest"],
                               (j["tarballs"][-1]["mtime"] if j["tarballs"] and r["tarball_members"] not in (0,) else None)]),
                 default=None)
    if a.rows_before and (newest is None or newest < a.rows_before):
        print(f"PRECONDITION FAILED: newest backup evidence {newest} predates rows up to {a.rows_before}.", file=sys.stderr)
        return 4
    print(f"precondition ok: {a.store} covered ({r['evidence']}); newest backup evidence {newest}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("report")
    pr.add_argument("--tarball-listing")
    pr.add_argument("--json", action="store_true")
    pr.set_defaults(func=cmd_report)
    pc = sub.add_parser("precondition")
    pc.add_argument("--store", required=True)
    pc.add_argument("--rows-before", help="ISO time of the newest row/file the reaper would delete")
    pc.add_argument("--tarball-listing")
    pc.set_defaults(func=cmd_precondition)
    a = p.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
