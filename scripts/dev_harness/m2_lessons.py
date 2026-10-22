#!/usr/bin/env python3
"""DHM-3 — lesson registry and the interrupted-time-series (ITS) pilot.

Registry (committed, content-free): every feedback memory, every INCIDENT_LOG entry and every
bold-led CLAUDE.md rule, each with an id, a date (+ how the date was derived), the channel it is
delivered through, and the mechanical detector (a DHM-2 guard class) when the lesson has a
forbidden surface form. A lesson with no surface form is registered with ``detector: []`` and is
not measurable by this pilot — that is recorded, never papered over.

    /usr/bin/python3 scripts/dev_harness/m2_lessons.py build-registry   # rewrites lesson_registry.json

READS memory files, INCIDENT_LOG.md and CLAUDE.md; never writes them.

ITS pilot (run by mine_m2.py): for 5 lessons with forbidden surface forms, violations per 1000 tool
calls (companion: per 1000 operator turns) before / after the lesson date and after the hook date,
split prose-only vs hook-enforced, plus the delivered-context rate and an exposure-weighted
segmented regression over daily rates. Spec: docs/design/dev-harness-its-pilot-spec.md.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from m2_guards import HOOK_COVERAGE  # noqa: E402

REGISTRY_SCHEMA = "dev-harness-lesson-registry.v1"
REGISTRY_PATH = Path(__file__).resolve().parent / "lesson_registry.json"
MEMORY_DIR = Path(os.path.expanduser("~/.claude/projects/-workspace/memory"))
INCIDENT_LOG = ROOT / "docs/reference/agent-config/INCIDENT_LOG.md"
CLAUDE_MD = ROOT / "CLAUDE.md"

# Lessons whose rule names a forbidden surface form -> DHM-2 guard classes (hand-curated).
DETECTOR_MAP: dict[str, list[str]] = {
    # feedback memories
    "feedback_no_wholesale_git_add_shared_files": ["wholesale_git_add"],
    "feedback_pathspec_limited_commit_in_shared_tree": ["wholesale_git_add"],
    "feedback_never_chain_push_after_piped_tests": ["piped_gate_push"],
    "feedback_pipe_hazards": ["piped_gate_push"],
    "feedback_never_edit_running_shell_script": ["edit_running_script"],
    "feedback_llama_cli_repl_must_be_killed": ["llama_cli_unbounded"],
    "feedback_worktree_remove_force_destroys_orphan_work": ["git_worktree_prune_or_force"],
    "feedback_update_ref_with_stale_worktree_publishes_deletions": ["git_worktree_prune_or_force"],
    "feedback_gitnexus_bloat_protection": ["bare_gitnexus_analyze"],
    "feedback_speed_verify_via_llama_bench": ["run_benchmark_invocation"],
    "feedback_scratchpad_blocked_use_workspace_tmp": ["write_outside_allowlist"],
    "feedback_manual_confirm_before_deletion": ["glob_rm"],
    "feedback_shared_file_whole_file_operations": ["git_stash"],
    # incidents
    "INC-20260731-broad-process-pattern-kills": ["pattern_kill", "pgrep_pattern"],
    "INC-20260816-git-clean-shared-clone": ["git_clean"],
    "INC-20260823-filesystem-containment-gap": ["write_outside_allowlist", "write_tool_outside_allowlist"],
    "INC-20260917-daemon-stale-script-inode": ["edit_running_script"],
    "INC-20260929-piped-gate-push": ["piped_gate_push"],
    "INC-20261004-glob-rm-deleted-receipt-evidence": ["glob_rm"],
    "INC-20261004-cleanup-removed-load-bearing-worktree": ["git_worktree_prune_or_force"],
    "INC-20260806-pytest-api-escape": ["pytest_xdist_auto"],
}
# CLAUDE.md rules are matched by keyword in the rule text.
CLAUDE_MD_KEYWORDS: list[tuple[str, list[str]]] = [
    (r"pkill", ["pattern_kill", "pgrep_pattern"]),
    (r"gitnexus analyze", ["bare_gitnexus_analyze"]),
]

# The 5 pilot lessons: class -> registry ids it is measured against (earliest date = lesson date).
PILOT = {
    "pattern_kill": ["INC-20260731-broad-process-pattern-kills"],
    "llama_cli_unbounded": ["feedback_llama_cli_repl_must_be_killed"],
    "wholesale_git_add": ["feedback_no_wholesale_git_add_shared_files"],
    "piped_gate_push": ["INC-20260929-piped-gate-push", "feedback_never_chain_push_after_piped_tests"],
    "glob_rm": ["INC-20261004-glob-rm-deleted-receipt-evidence"],
}

# Never-lessoned control classes (no registry lesson maps to them): the secular trend for a DiD read.
CONTROL_CLASSES = ("git_reset_hard", "no_verify", "hooks_path_null")

_ISO = re.compile(r"\b(20\d\d-[01]\d-[0-3]\d)\b")
_INC = re.compile(r"^## (INC-(\d{4})(\d\d)(\d\d)-[\w-]+)\s*$", re.M)
_MEM_LABEL = re.compile(r"\[([^\]]+)\]\(([\w.-]+)\.md\)")


def _frontmatter(text: str) -> dict:
    fm: dict = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        for line in text[3:end].splitlines():
            m = re.match(r"\s*(\w+):\s*(.*)$", line)
            if m:
                fm[m.group(1)] = m.group(2).strip().strip('"')
    return fm


def _git_first_date(path: Path, needle: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "log", "--format=%cs", "-S", needle, "--", str(path)],
                             capture_output=True, text=True, timeout=30).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return None
    return out[-1] if out else None


def _enforcement(classes: list[str]) -> list[dict]:
    out = []
    for c in classes:
        cov = HOOK_COVERAGE.get(c)
        if cov:
            out.append({"class": c, "hook": cov[0], "harnesses": list(cov[1]), "since": cov[2]})
    return out


def build_registry(memory_dir: Path = MEMORY_DIR, incident_log: Path = INCIDENT_LOG,
                   claude_md: Path = CLAUDE_MD) -> dict:
    lessons: list[dict] = []
    labels = {}
    idx = memory_dir / "MEMORY.md"
    if idx.exists():
        for m in _MEM_LABEL.finditer(idx.read_text()):
            labels[m.group(2)] = m.group(1)
    for p in sorted(memory_dir.glob("*.md")):
        if p.name == "MEMORY.md" or not p.name.startswith("feedback"):
            continue
        text = p.read_text(errors="replace")
        fm = _frontmatter(text)
        if fm.get("type") not in (None, "feedback") and "type: feedback" not in text[:600]:
            continue
        dates = sorted(_ISO.findall(text))
        if dates:
            d, basis = dates[0], "earliest_iso_date_in_text"
        else:
            d, basis = datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).date().isoformat(), "file_mtime"
        det = DETECTOR_MAP.get(p.stem, [])
        lessons.append({"id": p.stem, "kind": "feedback_memory", "channel": "memory", "date": d,
                        "date_basis": basis, "title": labels.get(p.stem, fm.get("name", p.stem))[:120],
                        "indexed_in_memory_md": p.stem in labels, "detector": det,
                        "enforced_by": _enforcement(det)})
    inc_text = incident_log.read_text()
    for m in _INC.finditer(inc_text):
        iid = m.group(1)
        det = DETECTOR_MAP.get(iid, [])
        lessons.append({"id": iid, "kind": "incident_rule", "channel": "incident_log",
                        "date": f"{m.group(2)}-{m.group(3)}-{m.group(4)}", "date_basis": "incident_id",
                        "title": iid[13:].replace("-", " "), "detector": det, "enforced_by": _enforcement(det)})
    section = "preamble"
    n_in = Counter()
    for line in claude_md.read_text().splitlines():
        if line.startswith("#"):
            section = re.sub(r"[^a-z0-9]+", "-", line.lstrip("#").strip().lower()).strip("-")[:40]
            continue
        m = re.match(r"\s*- \*\*(.+?)\*\*", line)
        if not m:
            continue
        n_in[section] += 1
        rule = m.group(1)
        det: list[str] = []
        for kw, cls in CLAUDE_MD_KEYWORDS:
            if re.search(kw, line):
                det += [c for c in cls if c not in det]
        needle = line.strip()[:60]
        d = _git_first_date(claude_md, needle)
        lessons.append({"id": f"claude_md:{section}:{n_in[section]}", "kind": "claude_md_rule",
                        "channel": "claude_md", "date": d, "date_basis": "git_pickaxe_current_wording" if d else "unknown",
                        "title": re.sub(r"[`*]", "", rule)[:120], "detector": det, "enforced_by": _enforcement(det)})
    unknown = sorted(set(DETECTOR_MAP) - {l["id"] for l in lessons})
    return {"schema": REGISTRY_SCHEMA,
            "sources": {"memory_dir": str(memory_dir).replace(os.path.expanduser("~"), "~"),
                        "incident_log": str(incident_log.relative_to(ROOT)) if incident_log.is_relative_to(ROOT) else str(incident_log),
                        "claude_md": "CLAUDE.md"},
            "counts": {"lessons": len(lessons),
                       "by_kind": dict(Counter(l["kind"] for l in lessons)),
                       "with_detector": sum(1 for l in lessons if l["detector"]),
                       "hook_enforced": sum(1 for l in lessons if l["enforced_by"])},
            "detector_map_ids_not_found": unknown,
            "pilot": PILOT,
            "lessons": lessons}


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    return json.loads(Path(path).read_text())


# ── ITS pilot ────────────────────────────────────────────────────────────────

def _delivered(u, channel: str) -> bool:
    """Mechanical delivered-context test (fidelity=inferred): was the lesson's channel in context?"""
    sp = u.source_path
    if channel == "memory":
        # auto-memory of the /workspace project loads into Claude Code sessions of that project
        if u.harness == "claude_code" and "/claude/-workspace/" in sp:
            return True
    if channel == "claude_md":
        if u.harness == "claude_code" and u.source == "epyc":
            return True
    target = {"memory": "/memory/", "claude_md": "CLAUDE.md", "incident_log": "INCIDENT_LOG.md"}[channel]
    for c in u.calls:
        if c.function.lower() in ("read", "view") and target in json.dumps(c.args):
            return True
        if any(target in cmd and re.search(r"\b(cat|sed|head|less|grep)\b", cmd) for cmd in c.commands):
            return True
    return False


def _rate_ci(k: int, n: int, per: int = 1000) -> dict:
    if n <= 0:
        return {"k": k, "n": n, "rate": 0, "lo": 0, "hi": 0}
    r = k / n
    if k == 0:
        lo, hi = 0.0, 3.0 / n                       # rule of three (95% upper)
    else:
        se = 1.96 / math.sqrt(k)
        lo, hi = r * math.exp(-se), r * math.exp(se)  # log-normal Poisson interval
    return {"k": k, "n": n, "rate": round(per * r, 4), "lo": round(per * lo, 4), "hi": round(per * hi, 4)}


class ITSPilot:
    def __init__(self, registry: dict) -> None:
        by_id = {l["id"]: l for l in registry["lessons"]}
        self.meta: dict[str, dict] = {}
        for cls, ids in registry.get("pilot", PILOT).items():
            ls = [by_id[i] for i in ids if i in by_id and by_id[i].get("date")]
            if not ls:
                continue
            first = min(ls, key=lambda l: l["date"])
            cov = HOOK_COVERAGE.get(cls)
            chans = sorted({l["channel"] for l in registry["lessons"] if cls in (l.get("detector") or [])})
            self.meta[cls] = {"lesson_id": first["id"], "lesson_date": first["date"], "channel": first["channel"],
                              "channels": chans,
                              "hook_date": cov[2] if cov else None,
                              "hook_harnesses": list(cov[1]) if cov else []}
        # (cls, harness, day) -> Counter(tool_calls, human_turns, violations, delivered_calls, units)
        self.daily: dict = defaultdict(Counter)
        self.excluded = Counter()

    def observe(self, u, hits: list[dict]) -> None:
        day = (u.first_ts or "")[:10]
        if not day:
            return
        human = sum(1 for m in u.messages if m.get("role") == "user" and (m.get("metadata") or {}).get("human"))
        for cls, meta in self.meta.items():
            if day == meta["lesson_date"]:
                self.excluded[cls] += 1      # campaign-grouped self-exclusion: the lesson's origin day
                continue
            k = sum(1 for h in hits if h["class"] == cls)
            c = self.daily[(cls, u.harness, day)]
            c["control_violations"] += sum(1 for h in hits if h["class"] in CONTROL_CLASSES)
            c["units"] += 1
            c["tool_calls"] += len(u.calls)
            c["human_turns"] += human
            c["violations"] += k
            got = [ch for ch in meta["channels"] if _delivered(u, ch)]
            if got:
                c["delivered_calls"] += len(u.calls)
            for ch in got:
                c["delivered_calls:" + ch] += len(u.calls)

    @staticmethod
    def _segfit(days: list[str], rates: list[float], weights: list[float], t0: str, t1: str | None) -> dict:
        try:
            import numpy as np
        except ImportError:
            return {"fit_ok": 0, "numpy_unavailable": 1}
        if len(days) < 6:
            return {"fit_ok": 0, "too_few_days": 1, "n_days": len(days)}
        d0 = date.fromisoformat(days[0])
        t = np.array([(date.fromisoformat(d) - d0).days for d in days], dtype=float)
        tl = (date.fromisoformat(t0) - d0).days
        cols = [np.ones_like(t), t, (t >= tl).astype(float), np.where(t >= tl, t - tl, 0.0)]
        names = ["intercept", "trend", "level_change_lesson", "slope_change_lesson"]
        if t1 and t1 > t0:
            th = (date.fromisoformat(t1) - d0).days
            cols += [(t >= th).astype(float), np.where(t >= th, t - th, 0.0)]
            names += ["level_change_hook", "slope_change_hook"]
        X = np.stack(cols, axis=1)
        y = np.array(rates)
        w = np.sqrt(np.array(weights))
        keep = [i for i in range(X.shape[1]) if np.ptp(X[:, i]) > 0 or i == 0]
        X = X[:, keep]
        names = [names[i] for i in keep]
        beta, *_ = np.linalg.lstsq(X * w[:, None], y * w, rcond=None)
        return {"fit_ok": 1, "n_days": len(days), **{n: round(float(b), 5) for n, b in zip(names, beta)}}

    def aggregate(self) -> dict:
        out: dict = {}
        for cls, meta in self.meta.items():
            rows = {k: v for k, v in self.daily.items() if k[0] == cls}
            seg = defaultdict(Counter)
            per_h = defaultdict(lambda: defaultdict(Counter))
            for (_, h, day), c in rows.items():
                if day < meta["lesson_date"]:
                    s = "pre_lesson"
                elif meta["hook_date"] and day >= meta["hook_date"]:
                    s = "post_hook" if h in meta["hook_harnesses"] else "post_hook_harness_uncovered"
                else:
                    s = "post_lesson_prose_only"
                seg[s] += c
                per_h[h][s] += c
            res: dict = {"lesson_date_ordinal": date.fromisoformat(meta["lesson_date"]).toordinal(),
                         "hook_date_ordinal": date.fromisoformat(meta["hook_date"]).toordinal() if meta["hook_date"] else 0,
                         "self_excluded_units": self.excluded[cls], "segments": {}, "by_harness": {}}
            for s, c in seg.items():
                res["segments"][s] = {"per_1k_tool_calls": _rate_ci(c["violations"], c["tool_calls"]),
                                      "control_per_1k_tool_calls": _rate_ci(c["control_violations"], c["tool_calls"]),
                                      "per_1k_human_turns": _rate_ci(c["violations"], c["human_turns"]),
                                      "delivered_context_rate": round(c["delivered_calls"] / c["tool_calls"], 4)
                                      if c["tool_calls"] else 0, "units": c["units"],
                                      "delivered_context_rate_by_channel": {
                                          ch: round(c["delivered_calls:" + ch] / c["tool_calls"], 4) if c["tool_calls"] else 0
                                          for ch in meta["channels"]}}
            for h, segs in per_h.items():
                res["by_harness"][h] = {s: _rate_ci(c["violations"], c["tool_calls"]) for s, c in segs.items()}
            daily = defaultdict(Counter)
            for (_, h, day), c in rows.items():
                daily[day] += c
            days = sorted(d for d in daily if daily[d]["tool_calls"] > 0)
            res["segmented_regression"] = self._segfit(
                days, [1000 * daily[d]["violations"] / daily[d]["tool_calls"] for d in days],
                [daily[d]["tool_calls"] for d in days], meta["lesson_date"], meta["hook_date"])
            out[cls] = res
        return out

    def meta_rules(self) -> list[str]:
        return [f"{cls}: lesson {m['lesson_id']} ({'+'.join(m['channels'])}) dated {m['lesson_date']}; "
                f"hook {m['hook_date'] or 'none (prose-only)'}" for cls, m in self.meta.items()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build-registry")
    b.add_argument("--memory-dir", default=str(MEMORY_DIR))
    b.add_argument("--out", default=str(REGISTRY_PATH))
    a = ap.parse_args(argv)
    reg = build_registry(Path(a.memory_dir))
    Path(a.out).write_text(json.dumps(reg, indent=1, sort_keys=True) + "\n")
    print(json.dumps(reg["counts"], sort_keys=True), "missing:", reg["detector_map_ids_not_found"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
