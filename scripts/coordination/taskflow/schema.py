#!/usr/bin/env python3
"""taskflow/schema.py — build an `epyc.task.v1` record from a `.box-index.json` record (DESIGN.md §2.2, Stage 1).

The task record is what a worker sees and what the verifier checks. It is deterministic (no LLM) and carries:

  goal         the box's own block, VERBATIM from the handoff (first line + continuation lines). The identity is
               `text_sha` (box_index.text_sha of the first line); `file:line` is a hint only.
  done_when    the `· done when:` field, else an inline "done when …" clause, else None (verifier -> reviewer only)
  test_cmds    runnable commands the box names for its done-condition (backticked `pytest|python3|bash|make …`)
  inputs       paths the box names that exist in `repo` (excerpted into the prompt), plus box_index `inputs`
  forbidden    globs the worker must never touch (FORBIDDEN + any `holds.yaml` `files` targets)
  repo         the git tree the paths resolve in (epyc-root | epyc-orchestrator | epyc-inference-research | …)
  tier/budget  model tier hint and hard caps (turns, tokens, wall seconds)
  brief        task-brief layer P3 (docs/design/task-brief-layer.md §7): the deterministic `brief.compile_brief`
               merged in -- where, approach, acceptance, non_goals, inputs_ext, brief_state, stale (the stale-list),
               brief_accepted, brief_author, acceptance_matches_done_when, blast_radius, brief_path

    python3 scripts/coordination/taskflow/schema.py <box-key> [...]     # print task records as JSON
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

SCHEMA = "epyc.task.v1"
REPO_ROOT = Path(__file__).resolve().parents[3]
REPOS = {  # name -> working path; the first repo in which a named path exists wins (root on a tie / no path)
    "epyc-root": Path(os.environ.get("TASKFLOW_ROOT_REPO", "/workspace")),  # lanes come from the shared clone's origin/main
    "epyc-orchestrator": Path("/mnt/raid0/llm/epyc-orchestrator"),
    "epyc-inference-research": Path("/mnt/raid0/llm/epyc-inference-research"),
    "epyc-web": Path("/mnt/raid0/llm/epyc-web"),
}
# Never touched by a taskflow worker unless the box itself names the path as an input (DESIGN §2.5).
FORBIDDEN = (
    "handoffs/**", "agents/shared/**", "CLAUDE.md", "**/CLAUDE.md", ".claude/**", "coordination/session-bus/**",
    "scripts/coordination/rowflow/**", "scripts/coordination/keeper*", "scripts/coordination/taskflow/**",
    "scripts/hooks/**", "artifacts/**", "docs/reports/**", "kernels/**", "progress/**", "MEASUREMENT.md",
    "measurement/**", ".git/**",
)
DEFAULT_BUDGET = {"turns": 30, "tokens": 120000, "wall_s": 600,  # r7: one 839 s task ate a third of a booking;  # r1: 14 steps all went to exploration
                  "excerpt_chars": 9000}
TIER_BY_CLASS = {"non-inference": "terra", "inference": "terra"}
EXTERNAL_REF_DIR = PurePosixPath(".taskflow-refs/external")


def external_readonly_inputs(task: dict) -> list[dict[str, str]]:
    """Validate controller-supplied file pins on a task packet."""
    entries = task.get("external_readonly_inputs", [])
    if not isinstance(entries, list):
        raise ValueError("external_readonly_inputs must be a list")
    paths: set[PurePosixPath] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "lane_path", "sha256"}:
            raise ValueError("external input needs path, lane_path and sha256")
        if not all(isinstance(value, str) and "\0" not in value for value in entry.values()):
            raise ValueError("external input fields must be strings")
        source = Path(entry["path"])
        target = PurePosixPath(entry["lane_path"])
        if not source.is_absolute() or ".." in source.parts:
            raise ValueError(f"external input source must be an absolute path: {source}")
        if (".." in target.parts or "\\" in entry["lane_path"] or str(target) != entry["lane_path"]
                or target == EXTERNAL_REF_DIR or not target.is_relative_to(EXTERNAL_REF_DIR)):
            raise ValueError(f"invalid external input lane path: {entry['lane_path']}")
        if not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
            raise ValueError(f"invalid external input digest: {target}")
        if any(target.is_relative_to(other) or other.is_relative_to(target) for other in paths):
            raise ValueError(f"external input lane path collides: {target}")
        paths.add(target)
    return entries


# Per-task wall budget from the measured serving rate (r8b canary FIX-HARNESS 2026-11-22, fix 1): the 600 s default was
# sized for the GPU; on a CPU quarter prefill ran 77-284 tok/s over 30-80k-token tasks and 6+ of 16 runs died on time.
# wall_s = margin * (expected_prompt_tokens / prefill_tok_s + expected_output_tokens / decode_tok_s) + overhead_s,
# clamped to [floor_s, cap_s]. Every key is configurable (job CONFIG `wall_budget`, `dispatch.py run --wall-budget`).
WALL_BUDGET_DEFAULTS = {"expected_prompt_tokens": 80000, "expected_output_tokens": 6000, "margin": 1.25,
                        "overhead_s": 120, "floor_s": 600, "cap_s": 3600}


def wall_budget_s(cfg: dict | None) -> int | None:
    """None when no measured rate is given (keep the task's own wall_s)."""
    c = dict(WALL_BUDGET_DEFAULTS, **(cfg or {}))
    pre, dec = c.get("prefill_tok_s"), c.get("decode_tok_s")
    if not pre or not dec:
        return None
    w = float(c["margin"]) * (float(c["expected_prompt_tokens"]) / float(pre)
                              + float(c["expected_output_tokens"]) / float(dec)) + float(c["overhead_s"])
    w = max(float(c["floor_s"] or 0), w)
    if c.get("cap_s"):
        w = min(float(c["cap_s"]), w)
    return int(round(w))


# Per-request output cap (r8g fix 5, r8f LOOP-62 think): two 4096-token capped thinking outputs burned ~1160 s of a 1739 s
# wall at 10.7 tok/s decode and left no room to write the test. The proxy cap is now min(configured cap, what one request
# may spend of the wall at the MEASURED decode rate); `max_request_wall_frac` < 0.5 guarantees two capped requests can
# never consume the whole wall. Every key is configurable per arm in the job CONFIG (`arms[].request_cap`):
#   agent_cap_tokens          nothink agent-turn cap (default 2048)
#   think_cap_tokens          thinking agent-turn cap (default 6144)
#   max_request_wall_frac     share of the task wall one request may spend decoding (default 0.25; null disables)
#   decode_tok_s              measured decode rate (default: arm wall_budget.decode_tok_s)
#   floor_tokens              never cap below this (default 1024)
REQUEST_CAP_DEFAULTS = {"agent_cap_tokens": 2048, "think_cap_tokens": 6144, "max_request_wall_frac": 0.25, "floor_tokens": 1024}


def request_token_cap(arm: dict | None, thinking: bool | None = None, wall_s: float | None = None) -> int:
    """max_tokens cap for one agent-turn request of `arm` (a job-CONFIG arm dict). See REQUEST_CAP_DEFAULTS."""
    arm = arm or {}
    think = bool(arm.get("thinking") if thinking is None else thinking)
    c = dict(REQUEST_CAP_DEFAULTS, **(arm.get("request_cap") or {}))
    cap = int(c["think_cap_tokens"] if think else c["agent_cap_tokens"])
    frac = c.get("max_request_wall_frac")
    wb = arm.get("wall_budget") or {}
    dec = c.get("decode_tok_s") or wb.get("decode_tok_s")
    wall = wall_s if wall_s is not None else wall_budget_s(wb or None)
    if frac and dec and wall:
        cap = min(cap, int(float(frac) * float(wall) * float(dec)))
    return max(int(c["floor_tokens"]), cap)


def apply_wall_budget(task: dict, cfg: dict | None) -> dict:
    """Return the task with budget.wall_s derived from `cfg` (unchanged when cfg carries no rate)."""
    w = wall_budget_s(cfg)
    if w is None:
        return task
    return dict(task, budget=dict(task.get("budget") or DEFAULT_BUDGET, wall_s=w))

_PATH = re.compile(r"`([A-Za-z0-9_.][\w./-]*(?:\.[A-Za-z0-9]{1,6}|/))(?::\d+(?:-\d+)?)?`")
_BARE_PATH = re.compile(r"(?<![\w/.])((?:src|scripts|tests|docs|orchestration|research|dashboard|benchmarks)/[\w./-]+\.[A-Za-z0-9]{1,6})")
_CMD = re.compile(r"`((?:pytest|python3?|bash|make)\s[^`]+)`")
_INLINE_DW = re.compile(r"\bdone\s+when\b[:\s]+(.+?)(?:\.\s|;|\[no-belief|\[belief|$)", re.I | re.S)


def own_block(lines: list[str], i: int) -> str:
    """Box at 0-based line i plus its continuation lines (deeper-indented or blank-then-deeper), verbatim."""
    first = lines[i]
    ind = len(first) - len(first.lstrip())
    out = [first]
    for ln in lines[i + 1:]:
        if not ln.strip():
            break
        if len(ln) - len(ln.lstrip()) <= ind:
            break
        out.append(ln)
    return "\n".join(out)


def text_sha(first_line: str) -> str:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "handoffs"))
    try:
        import box_index
        return box_index.text_sha(first_line)
    except Exception:  # noqa: BLE001 - fixture roots without box_index
        return hashlib.sha256(" ".join(first_line.split()).encode()).hexdigest()[:16]
    finally:
        sys.path.pop(0)


def find_box(lines: list[str], rec: dict) -> int:
    """Resolve the box by TEXT (text_sha), using the line as a hint only. -1 when it no longer exists."""
    hint = int(rec.get("line") or 0) - 1
    want = rec.get("text_sha")
    order = ([hint] if 0 <= hint < len(lines) else []) + [j for j in range(len(lines)) if j != hint]
    for j in order:
        if re.match(r"\s*[-*] \[ \] ", lines[j]) and (not want or text_sha(lines[j]) == want):
            return j
    return -1


_SKILL = re.compile(r"`?([a-z0-9][a-z0-9-]+)`?\s+skill\b", re.I)


def named_paths(text: str) -> list[str]:
    seen: list[str] = []
    for m in _SKILL.finditer(text):           # "the kernel-promotion skill" -> .claude/skills/kernel-promotion/
        seen.append(f".claude/skills/{m.group(1).lower()}/")
    for m in list(_PATH.finditer(text)) + list(_BARE_PATH.finditer(text)):
        p = m.group(1).rstrip(".")
        if p not in seen and not p.startswith("/"):
            seen.append(p)
    return seen


_REV_PATH = re.compile(r"`([0-9a-f]{7,40}):([\w./-]+\.\w+)`|`([\w./-]+\.\w+)@([0-9a-f]{7,40})`")


def rev_paths(text: str) -> list[tuple[str, str]]:
    out = []
    for m in _REV_PATH.finditer(text):
        out.append((m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3)))
    return out


def git_show(root: Path, rev: str, path: str) -> bytes | None:
    try:
        r = subprocess.run(["git", "-C", str(root), "show", f"{rev}:{path}"], capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def resolve_basename(root: Path, name: str) -> str | None:
    """A bare file name the box cites -> its tracked path when exactly one tracked file has that name."""
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files", f"*/{name}", name], capture_output=True,
                             text=True, timeout=20).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return None
    return out[0] if len(out) == 1 else None


def pick_repo(paths: list[str], text: str) -> str:
    hits = {name: sum((root / p).exists() for p in paths) for name, root in REPOS.items() if root.exists()}
    for name in ("epyc-orchestrator", "epyc-inference-research", "epyc-web"):
        if re.search(rf"\b{name.split('-', 1)[1].split('-')[0]}\b `", text) and hits.get(name):
            return name
    best = max(hits.items(), key=lambda kv: (kv[1], kv[0] == "epyc-root"), default=("epyc-root", 0))
    return best[0] if best[1] else "epyc-root"


def done_when_text(goal: str, rec: dict) -> str | None:
    if rec.get("done_when"):
        return str(rec["done_when"])
    m = _INLINE_DW.search(goal)
    return " ".join(m.group(1).split()) if m else None


# Repos a taskflow worker can change. Kernel / llama.cpp-tree work is never dispatched here (r3 CLOSE-6).
SUPPORTED_REPOS = ("epyc-root", "epyc-orchestrator", "epyc-inference-research")
_KERNEL = re.compile(r"\b(?:ggml|llama\.cpp|llama-server|GGML_[A-Z_]+|CUDA|HIP|ROCm|iqk|kernel tree|champion|"
                     r"fold(?:ed|ing)? into|tg128|llama-bench|top-k renorm|SYNC-\d+|INF-?\d+)\b", re.I)


def unsupported(task: dict) -> str | None:
    """Why the harness must not take this task, or None."""
    if task["repo"] not in SUPPORTED_REPOS:
        return f"repo {task['repo']} not supported"
    try:
        external_readonly_inputs(task)
    except ValueError as exc:
        return str(exc)
    hits = _KERNEL.findall(task["goal"])
    if len(hits) >= 2 and not task["inputs"]:
        return "kernel/llama.cpp-tree work (" + ",".join(sorted(set(h.lower() for h in hits))[:4]) + ")"
    return None


BRIEF_KEYS = ("where", "approach", "acceptance", "non_goals", "inputs_ext", "brief_state", "stale", "brief_accepted",
              "brief_author", "brief_review", "acceptance_matches_done_when", "blast_radius", "brief_path",
              "verify_scope", "control_tests", "sanctioned_skips")   # r8h: reviewer context (TF-R8G-REVIEWER-CONTROL)


def merge_brief(task: dict, root: Path) -> dict:
    """Fill the BRIEF_KEYS of an epyc.task.v1 record from the box's sidecar (compile is deterministic, 0 tokens).
    A box without an ID, or a compile that cannot run, is `brief_state: none` (the worker self-briefs, §5)."""
    empty = {"where": [], "approach": None, "acceptance": None, "non_goals": [], "inputs_ext": [],
             "brief_state": "none", "stale": [], "brief_accepted": None, "brief_author": None, "brief_review": None,
             "acceptance_matches_done_when": False, "blast_radius": {}, "brief_path": None,
             "verify_scope": None, "control_tests": [], "sanctioned_skips": []}
    task.update(empty)
    bid = task.get("id")
    if not bid:
        return task
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    try:
        from taskflow import brief as B
        r = B.compile_brief(bid, Path(root))
        doc = {}
        p = Path(root) / r["brief"]
        if p.exists() and r["state"] != "none":
            try:
                doc = B.parse_text(p.read_text(encoding="utf-8"))
            except ValueError:
                doc = {}
    except Exception as e:  # noqa: BLE001 - a broken sidecar never stops the task build; it routes to self-brief
        task["stale"] = [f"compile unavailable: {type(e).__name__}: {e}"[:200]]
        return task
    finally:
        sys.path.pop(0)
    task.update(brief_state=r["state"], stale=list(r.get("stale_list") or []), brief_path=r["brief"],
                brief_accepted=r.get("accepted"), brief_author=r.get("author"), brief_review=r.get("review"),
                acceptance_matches_done_when=bool(r.get("acceptance_matches_done_when")),
                inputs_ext=list(r.get("inputs_ext") or []), blast_radius=dict(r.get("blast_radius") or {}))
    if doc:
        task.update(where=[str(w) for w in doc.get("where") or []], approach=(doc.get("approach") or "").strip() or None,
                    acceptance=(str(doc["acceptance"]).strip() if doc.get("acceptance") else None),
                    non_goals=[str(x) for x in doc.get("non_goals") or []],
                    verify_scope=(str(doc["verify_scope"]).strip() if doc.get("verify_scope") else None),
                    control_tests=[str(x) for x in doc.get("control_tests") or []],
                    sanctioned_skips=[str(x) for x in doc.get("sanctioned_skips") or []])
    return task


def build(rec: dict, root: Path | None = None, held_files: list[str] | None = None,
          budget: dict | None = None) -> dict:
    """epyc.task.v1 from a box-index record. Raises LookupError when the box text no longer resolves."""
    root = root or REPO_ROOT
    lines = (root / rec["file"]).read_text(encoding="utf-8").split("\n")
    i = find_box(lines, rec)
    if i < 0:
        raise LookupError(f"box {rec.get('key') or rec.get('id')} no longer resolves by text in {rec['file']}")
    goal = own_block(lines, i)
    paths = named_paths(goal)
    repo = pick_repo(paths, goal)
    rroot = REPOS[repo]
    inputs = [p for p in paths if (rroot / p).exists()]
    for p in [p for p in paths if "/" not in p and not (rroot / p).exists()]:
        hit = resolve_basename(rroot, p)          # r3 DHM-8: `m2_guards.py` lives at scripts/dev_harness/
        if hit:
            inputs.append(hit)
            paths.remove(p)
    for p in rec.get("inputs") or []:
        if p not in inputs and (rroot / p).exists():
            inputs.append(p)
    refs = []                                   # cross-repo inputs: copied read-only into the lane (.taskflow-refs/)
    for p in paths:
        if p in inputs or (rroot / p).exists():
            continue
        for name, other in REPOS.items():
            if name != repo and other.exists() and (other / p).is_file():
                refs.append({"repo": name, "path": p})
                break
    for p in [p for p in paths if "/" not in p and p not in inputs and not any(r["path"] == p for r in refs)]:
        for name, other in REPOS.items():         # bare name living in ANOTHER repo (r3 HS-OD-4 decision doc)
            if name != repo and other.exists():
                hit = resolve_basename(other, p)
                if hit:
                    refs.append({"repo": name, "path": hit})
                    break
    for rev, p in rev_paths(goal):                # `<sha>:<path>` / `<path>@<sha>` (r3 RESUME-7)
        for name, other in REPOS.items():
            if other.exists() and git_show(other, rev, p) is not None:
                refs.append({"repo": name, "path": p, "rev": rev})
                break
    dw = done_when_text(goal, rec)
    cmds = _CMD.findall(dw or "") or _CMD.findall(goal)
    task = {
        "schema": SCHEMA,
        "key": rec.get("key") or rec.get("id") or f"{rec['file']}#{rec.get('text_sha')}",
        "id": rec.get("id"),
        "text_sha": text_sha(lines[i]),
        "handoff": rec["file"],
        "line_hint": i + 1,
        "owner_slug": Path(rec["file"]).stem,
        "track": rec.get("track"),
        "class": rec.get("class") or "non-inference",
        "goal": goal,
        "done_when": dw,
        "test_cmds": [" ".join(c.split()) for c in cmds][:3],
        "inputs": inputs,
        "outputs": [p for p in paths if p not in inputs and p not in {r["path"] for r in refs}],
        "refs": refs,   # named but not yet existing = may be created
        "forbidden": list(FORBIDDEN) + list(held_files or []),
        "repo": repo,
        "tier": rec.get("tier"),   # the box `tier:` hint only; dispatch.pick_tier fills the default by kind
        "budget": dict(DEFAULT_BUDGET, **(budget or {})),
    }
    merge_brief(task, root)
    return follow_brief_repo(task)


def follow_brief_repo(task: dict) -> dict:
    """The lane follows the brief: when a supported repo other than the task's holds MORE `where` entries than the
    task's repo, run the task there; the other repos' existing files become read-only refs (r7 TU-GR-1: box text
    names no path -> epyc-root lane; brief `where` = 3 orchestrator code paths + 1 root design doc)."""
    import collections
    ents = [(str(w).split(":", 1)[0], str(w).split(":", 1)[1].split("::")[0]) for w in task.get("where") or []
            if ":" in str(w).split("::")[0]]
    cnt = collections.Counter(r for r, _ in ents)
    if not cnt:
        return task
    best, n = cnt.most_common(1)[0]
    if (best != task["repo"] and n > cnt.get(task["repo"], 0) and best in SUPPORTED_REPOS and REPOS.get(best)
            and Path(REPOS[best]).exists()):
        task["repo_from_box"] = task["repo"]
        task["repo"] = best
        have = {(r.get("repo"), r.get("path")) for r in task.get("refs") or []}
        for r, p in ents:
            if r != best and REPOS.get(r) and (Path(REPOS[r]) / p).is_file() and (r, p) not in have:
                task.setdefault("refs", []).append({"repo": r, "path": p})
    return task


def main(argv=None) -> int:
    keys = list(argv if argv is not None else sys.argv[1:])
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "handoffs"))
    import box_index
    doc = box_index.load(REPO_ROOT)
    out = []
    for k in keys:
        rec = (doc.get("boxes") or {}).get(k)
        if rec is None:
            print(f"unknown box key {k}", file=sys.stderr)
            return 2
        out.append(build(dict(rec, key=k)))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
