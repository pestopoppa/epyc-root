#!/usr/bin/env python3
"""taskflow/dispatch.py — select -> build task -> worker in a disposable worktree -> verify -> (tick) (DESIGN.md §2.4-2.6).

    dispatch.py plan  --keys K1,K2 ... | --top N  [--out tasks.json]        # select + schema, no model, no writes
    dispatch.py run   --tasks tasks.json --endpoint http://127.0.0.1:P/v1 --out DIR [--apply] [--reviewer]

`run` per task: `git worktree add` a detached disposable worktree of the task's repo at origin/main, branch
`taskflow/<run>/<n>` -> harness spawn -> the DISPATCHER commits the worker's changes on that lane (the worker never
commits) -> verify.verify -> ledger line. With --apply, a `verified` task is ticked via churn/wrapup.py under the owning
handoff's slug (box resolved by TEXT; evidence = the verifier's); index rows are never touched. Without --apply nothing
leaves the lane (the canary default). The lane worktree is removed after the diff and ledger are saved; the local
branch is kept for review.

Tier (operator directive 3): box `tier:` wins; else class -> tier (TIER_BY_KIND); escalation only after a verified
failure (`escalate()`). Ledger: one JSON line per task {key, tier, model, family, tokens (input/cached/uncached/output),
wall_s, verdict, reason, failure_class}.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import shutil
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))
from taskflow import schema, verify  # noqa: E402
from taskflow.harness import local_llm  # noqa: E402

ROOT = _HERE.parents[2]
TIERS = ("luna", "terra", "sol")
# cheapest capable tier per kind of work (operator 2026-11-20: clerical/filing/docs low, code mid, design/debug top)
TIER_BY_KIND = {"clerical": "luna", "docs": "luna", "file": "luna", "code": "terra", "design": "sol", "debug": "sol"}
_KIND_RX = [("file", r"\bfile (?:the )?(?:result|row|verdict)|run-end"),
            ("debug", r"\b(?:debug|root[- ]cause|bisect|diagnos|reproduce)"),
            ("design", r"\b(?:design|architecture|decide between|spec out)\b"),
            ("docs", r"\b(?:document|docs?/|README|write[- ]up|record (?:the|a)|note in)\b"),
            ("code", r"\b(?:fix|implement|add (?:a )?test|wire|refactor|\.py\b|test_)")]


def kind_of(task: dict) -> str:
    t = task["goal"]
    for k, rx in _KIND_RX:
        if re.search(rx, t, re.I):
            return k
    return "code"


def pick_tier(task: dict) -> str:
    t = str(task.get("tier") or "").lower()
    if t in TIERS:
        return t
    alias = {"haiku": "luna", "sonnet": "terra", "opus": "sol"}
    return alias.get(t) or TIER_BY_KIND[kind_of(task)]


def escalate(tier: str) -> str | None:
    i = TIERS.index(tier)
    return TIERS[i + 1] if i + 1 < len(TIERS) else None


# ----------------------------------------------------------------------------------------------------------- plan
def plan(keys: list[str] | None, top: int) -> list[dict]:
    sys.path.insert(0, str(ROOT / "scripts" / "handoffs"))
    import box_index
    from taskflow import select as S
    doc = box_index.load(ROOT)
    cands, _ = S.candidates(doc)
    byk = dict(cands)
    chosen = [(k, byk.get(k)) for k in keys] if keys else cands
    out = []
    for k, rec in chosen:
        if rec is None:
            print(f"skip {k}: not dispatchable now (select.py skips it)", file=sys.stderr)
            continue
        t = schema.build(dict(rec, key=k))
        why = schema.unsupported(t)
        if why:
            if keys:
                print(f"skip {k}: {why}", file=sys.stderr)
            continue
        t["kind"] = kind_of(t)
        t["tier"] = pick_tier(t)
        out.append(t)
        if not keys and len(out) >= top:
            break
    return out


# ------------------------------------------------------------------------------------------------------------ run
def _git(repo: Path, *a: str, check=True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=check)


# ------------------------------------------------------------------------------------------- worktree lifecycle
# docs/design/taskflow-dispatcher.md -> "Worktree lifecycle". One worker per worktree; created fresh from origin/main
# at a short path; the worker never commits, pushes or switches branches (POLICY + shell deny list); the DISPATCHER
# commits the worker's tree on the lane branch and only `--apply` (wrapup.py) pushes. Disposal = `git worktree remove`
# (never --force, never prune); a dirty lane is committed as WIP on its own branch first so nothing is lost.
KEEP_FAILED_H = float(os.environ.get("TASKFLOW_KEEP_FAILED_H", "24"))   # failed / aborted lanes kept for forensics
MAX_LANES = int(os.environ.get("TASKFLOW_MAX_LANES", "16"))             # live lanes under the lane root
MIN_FREE_GIB = float(os.environ.get("TASKFLOW_MIN_FREE_GIB", "50"))     # free space required to create a lane


class LaneRefused(RuntimeError):
    pass


def lane_root() -> Path:
    return Path(os.environ.get("TASKFLOW_LANE_ROOT", "/mnt/raid0/llm/tf"))


def _meta(lane: Path) -> Path:
    return lane.parent / f"{lane.name}.lane.json"


def make_lane(task: dict, base_dir: Path, branch: str) -> tuple[Path, Path, str]:
    repo = schema.REPOS[task["repo"]]
    # r3: the 35B miscopied long digit-heavy lane paths (".../canary-r3-2026120/.../t00/lane" for t02) ->
    # short lane roots: /mnt/raid0/llm/tf/<4 hex>
    root = lane_root()
    root.mkdir(parents=True, exist_ok=True)
    lane = root / hashlib.sha1(str(base_dir).encode()).hexdigest()[:4]
    if lane.exists():
        raise LaneRefused(f"{lane} exists: one worker per worktree")
    live = [m for m in root.glob("*.lane.json")]
    if len(live) >= MAX_LANES:
        raise LaneRefused(f"{len(live)} live lanes >= cap {MAX_LANES}; run `dispatch.py sweep`")
    free = shutil.disk_usage(root).free / 2**30
    if free < MIN_FREE_GIB:
        raise LaneRefused(f"{free:.0f} GiB free < {MIN_FREE_GIB} GiB")
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "lane.path").write_text(str(lane))
    base = _git(repo, "rev-parse", "origin/main").stdout.strip()
    _git(repo, "worktree", "add", "-q", "-b", branch, str(lane), base)
    _meta(lane).write_text(json.dumps({"lane": str(lane), "repo": str(repo), "branch": branch, "base": base,
                                       "created": time.time(), "state": "live", "task": task.get("key")}))
    for r in task.get("refs") or []:
        dst = lane / REFS / (r["repo"] + (f"@{r['rev']}" if r.get("rev") else "")) / r["path"]
        data = (schema.git_show(schema.REPOS[r["repo"]], r["rev"], r["path"]) if r.get("rev")
                else (schema.REPOS[r["repo"]] / r["path"]).read_bytes())
        if data is None:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        dst.chmod(0o444)
    return repo, lane, base


REFS = ".taskflow-refs"


def commit_lane(lane: Path, task: dict) -> bool:
    st = _git(lane, "status", "--porcelain", "-uall").stdout
    paths = [p for p in (ln[3:].split(" -> ")[-1] for ln in st.splitlines() if ln.strip())
             if not p.startswith(REFS + "/")]
    if not paths:
        return False
    _git(lane, "add", "--", *paths)
    _git(lane, "-c", "user.name=taskflow", "-c", "user.email=taskflow@localhost", "commit", "-q", "--no-verify",
         "-m", f"taskflow: {task.get('id') or task['text_sha']} (worker draft)")
    return True


def _clear_refs(lane: Path) -> None:
    refs = lane / REFS
    if refs.exists():                   # our own read-only copies; the worktree is otherwise clean after commit
        for f in sorted(refs.rglob("*"), reverse=True):
            if f.is_file():
                f.chmod(0o644)
                f.unlink()
            else:
                f.rmdir()
        refs.rmdir()


def _sweep_log(msg: str) -> None:
    root = lane_root()
    root.mkdir(parents=True, exist_ok=True)
    with (root / "sweep.log").open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n")


def delete_branch_if_safe(repo: Path, branch: str | None, base: str | None = None, pinned: bool = False) -> str:
    """Delete a taskflow lane branch when it is ours (taskflow/*), not pinned and not pushed anywhere. The tip sha is
    logged to <lane root>/sweep.log so `git branch <b> <sha>` recovers it while the reflog/objects live."""
    if not branch or not branch.startswith("taskflow/"):
        return "skip:not-taskflow"
    if pinned:
        return "skip:pinned"
    tip = _git(repo, "rev-parse", "--verify", "-q", f"refs/heads/{branch}", check=False).stdout.strip()
    if not tip:
        return "skip:absent"
    if _git(repo, "branch", "-r", "--contains", tip, check=False).stdout.strip() and tip != base:
        return "skip:pushed"
    if _git(repo, "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}", check=False).returncode == 0:
        return "skip:has-upstream"
    if _git(repo, "branch", "-D", branch, check=False).returncode != 0:
        return "fail"
    _sweep_log(f"deleted branch {branch} tip {tip} repo {repo}")
    return "deleted"


def drop_lane(repo: Path, lane: Path) -> bool:
    """Remove a lane: commit any leftover worker change as WIP on the lane branch, then plain `worktree remove`.
    A lane branch with no commit over its base is deleted at once (nothing to recover)."""
    meta = json.loads(_meta(lane).read_text()) if _meta(lane).exists() else {}
    if not lane.exists():
        _meta(lane).unlink(missing_ok=True)
        return True
    _clear_refs(lane)
    if _git(lane, "status", "--porcelain", "-uall", check=False).stdout.strip():
        st = _git(lane, "status", "--porcelain", "-uall", check=False).stdout
        left = [ln[3:].split(" -> ")[-1] for ln in st.splitlines() if ln.strip()]
        _git(lane, "add", "--", *left, check=False)
        _git(lane, "-c", "user.name=taskflow", "-c", "user.email=taskflow@localhost", "commit", "-q", "--no-verify",
             "-m", "taskflow: WIP left in lane at disposal", check=False)
    ok = _git(repo, "worktree", "remove", str(lane), check=False).returncode == 0
    if ok:
        _meta(lane).unlink(missing_ok=True)
        b, base = meta.get("branch"), meta.get("base")
        if b and base and _git(repo, "rev-parse", "-q", "--verify", f"refs/heads/{b}", check=False).stdout.strip() == base:
            delete_branch_if_safe(repo, b, base)
    return ok


def keep_lane(lane: Path, reason: str, hours: float | None = None) -> None:
    """Failed / aborted lane: keep for forensics, the sweep removes it after KEEP_FAILED_H."""
    m = _meta(lane)
    d = json.loads(m.read_text()) if m.exists() else {"lane": str(lane), "created": time.time()}
    d.update(state="kept", reason=reason, keep_until=time.time() + 3600 * (KEEP_FAILED_H if hours is None else hours))
    m.write_text(json.dumps(d))


def sweep_lanes(now: float | None = None) -> dict:
    """Orphan / expiry sweep over the lane root: kept lanes past keep_until, and live lanes (or lane dirs with no
    metadata) older than KEEP_FAILED_H -- i.e. left by a dead dispatcher. Removal is drop_lane (no --force/prune)."""
    now = now or time.time()
    out = {"removed": [], "kept": [], "failed": []}
    root = lane_root()
    if not root.exists():
        return out
    seen = set()
    for m in root.glob("*.lane.json"):
        d = json.loads(m.read_text())
        lane = Path(d["lane"])
        seen.add(lane.name)
        due = d.get("keep_until") if d.get("state") == "kept" else d.get("created", now) + 3600 * KEEP_FAILED_H
        if now < due:
            out["kept"].append(str(lane))
            continue
        repo = Path(d.get("repo") or ".")
        if drop_lane(repo, lane):
            out["removed"].append(str(lane))
            if d.get("state") == "kept":      # forensics window over: the WIP branch goes too (tip sha logged)
                out.setdefault("branches", []).append(
                    f"{d.get('branch')}:{delete_branch_if_safe(repo, d.get('branch'), d.get('base'), bool(d.get('pin')))}")
        else:
            out["failed"].append(str(lane))
    for lane in root.iterdir():
        if lane.is_dir() and lane.name not in seen and now - lane.stat().st_mtime > 3600 * KEEP_FAILED_H:
            common = _git(lane, "rev-parse", "--path-format=absolute", "--git-common-dir", check=False).stdout.strip()
            repo = Path(common).parent if common else None
            (out["removed"] if repo and drop_lane(repo, lane) else out["failed"]).append(str(lane))
    return out


def reviewer_for(endpoint: str, model: str):
    """Reviewer hook: ONE chat call, JSON verdict against the verbatim box text. Never edits."""
    def review(task: dict, diff: str) -> dict:
        msg = (local_llm.POLICY + "\n# REVIEW\nYou review a worker's diff for the box below. Answer ONLY JSON "
               '{"verdict":"done|not_done|drift","reason":"<=150 chars"}. done = the diff fully does what the box '
               "asks AND meets its DONE WHEN; not_done = partial, wrong, or the DONE WHEN is not met; drift = changes "
               "things the box did not ask for. Check the DONE WHEN clause item by item.\n\n## BOX\n"
               + task["goal"] + "\n\n## DONE WHEN\n" + str(task.get("done_when") or "(see box)")
               + "\n\n## DIFF\n" + diff[:12000])
        body = {"model": model, "messages": [{"role": "user", "content": msg}], "max_tokens": 200, "temperature": 0,
                "cache_prompt": True, "response_format": {"type": "json_object"},
                "chat_template_kwargs": {"enable_thinking": False}}
        req = urllib.request.Request(endpoint.rstrip("/") + "/chat/completions", json.dumps(body).encode(),
                                     {"content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            resp = json.loads(r.read())
        txt = resp["choices"][0]["message"]["content"]
        try:
            v = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])
        except ValueError:
            v = {"verdict": "unparseable", "reason": txt[:150]}
        v["usage"] = resp.get("usage")
        return v
    return review


def failure_class(w: dict, v: dict) -> str | None:
    """model-limitation | harness | task | None (verified)."""
    if v.get("verdict") == "verified":
        return None
    if w.get("errors") and not w["usage"]["steps"]:
        return "harness"
    te = len(w.get("tool_errors") or [])
    if te and te * 2 >= max(1, len(w.get("tools") or [])):
        return "harness"        # r1 canary: denied shell / JS-sandbox errors were mislabelled model-limitation
    if w.get("result") and w["result"].get("claimed_done") is False:
        return "task"           # the worker reported blocked/unclear: the box, not the model
    if v.get("reason") in ("forbidden-path", "outside-pathspec", "tests-fail", "reviewer-not_done", "reviewer-drift",
                           "done-when-fail"):
        return "model-limitation"
    if v.get("reason") == "no-change":
        return "model-limitation" if w["usage"]["steps"] else "harness"
    return "harness" if w.get("timed_out") and not w["usage"]["steps"] else "model-limitation"


def apply_tick(task: dict, lane: Path, v: dict, w: dict) -> str:
    rec = {"slug": task["owner_slug"], "state": "ready", "box": task.get("id") or task["text_sha"],
           "task_text": task["goal"].split("\n")[0], "ticks": [task["goal"].split("\n")[0]],
           "progress_md": f"taskflow verified {task['key']}: {(w.get('result') or {}).get('summary', '')}",
           "paths": v["evidence"]["paths"], "belief": "no-belief: taskflow-verified-code-change",
           "evidence": v["evidence"], "message": f"taskflow: {task['key']} (verified, {v['reason']})",
           "trailers": ["Taskflow-Model: " + w["model"]]}
    p = lane / ".taskflow-wrapup.json"
    p.write_text(json.dumps(rec))
    r = subprocess.run([sys.executable, str(ROOT / "scripts/coordination/churn/wrapup.py"), "--json", str(p),
                        "--lane", str(lane)], capture_output=True, text=True)
    p.unlink(missing_ok=True)
    return (r.stdout.strip().splitlines() or ["?"])[-1]


def run(tasks: list[dict], endpoint: str, out: Path, apply: bool, use_reviewer: bool, family: str = "local") -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ledger = out / "ledger.jsonl"
    rows = []
    for n, task in enumerate(tasks):
        tdir = out / f"t{n:02d}"
        tdir.mkdir(exist_ok=True)
        t0 = time.time()
        row = {"n": n, "key": task["key"], "handoff": task["handoff"], "repo": task["repo"], "kind": task.get("kind"),
               "tier": task.get("tier"), "family": family}
        try:
            repo, lane, base = make_lane(task, tdir, f"taskflow/{run_id}/{n:02d}-{hashlib.sha1(str(tdir).encode()).hexdigest()[:6]}")  # r4: same-second collision
        except (subprocess.CalledProcessError, LaneRefused) as e:
            row.update(verdict="error", reason="lane", failure_class="harness",
                       detail=(getattr(e, "stderr", None) or str(e))[-300:])
            rows.append(row); ledger.open("a").write(json.dumps(row) + "\n")
            continue
        try:
            w = local_llm.spawn(task, lane, tdir / "worker", endpoint, family=family)
            committed = commit_lane(lane, task)
            reviewer = reviewer_for(endpoint, w["model"]) if use_reviewer else None
            v = verify.verify(task, lane, base, {"verdict": (w.get("result") or {}).get("summary", "")}, reviewer)
            if committed:
                (tdir / "diff.patch").write_text(_git(lane, "diff", f"{base}..HEAD").stdout)
            u = w["usage"]
            row.update(model=w["model"], rc=w["rc"], timed_out=w["timed_out"], steps=u["steps"],
                       tokens={"prompt": u["input"] + u["cache_read"], "cached": u["cache_read"],
                               "uncached": u["input"], "output": u["output"]},  # opencode `input` excludes cache reads
                       review_tokens=(v.get("review") or {}).get("usage"), claimed=w.get("result"),
                       verdict=v["verdict"], reason=v["reason"], checks=v["checks"],
                       failure_class=failure_class(w, v), worker_wall_s=w["wall_s"], tools=w["tools"][:40], edits=w.get("edits"), nudged=w.get("nudged"),
                       tool_errors=(w.get("tool_errors") or [])[:5],
                       errors=w["errors"][:3])
            if apply and v["verdict"] == "verified":
                row["applied"] = apply_tick(task, lane, v, w)
        except Exception as e:  # noqa: BLE001 - one task never stops the batch
            row.update(verdict="error", reason=type(e).__name__, failure_class="harness", detail=str(e)[:300])
        finally:
            failed_with_work = row.get("verdict") in ("rejected", "error", "unchecked") and row.get("reason") != "no-change"
            if failed_with_work:
                keep_lane(lane, f"{row.get('verdict')}:{row.get('reason')}")
                row["lane_kept"] = str(lane)
            else:
                drop_lane(repo, lane)
        row["wall_s"] = round(time.time() - t0, 1)
        rows.append(row)
        with ledger.open("a") as f:
            f.write(json.dumps(row) + "\n")
    try:                                   # automatic orphan / expiry sweep at the end of every dispatch run
        sw = sweep_lanes()
        if sw.get("removed") or sw.get("failed"):
            with ledger.open("a") as f:
                f.write(json.dumps({"sweep": sw, "at": time.time()}) + "\n")
    except Exception as e:  # noqa: BLE001 - the sweep never fails a batch
        _sweep_log(f"sweep error {type(e).__name__}: {e}")
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--keys", default="")
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--out")
    r = sub.add_parser("run")
    r.add_argument("--tasks", required=True)
    r.add_argument("--endpoint", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--apply", action="store_true")
    r.add_argument("--reviewer", action="store_true")
    sub.add_parser("sweep")
    a = ap.parse_args(argv)
    if a.cmd == "sweep":
        print(json.dumps(sweep_lanes(), indent=1))
        return 0
    if a.cmd == "plan":
        tasks = plan([k for k in a.keys.split(",") if k] or None, a.top)
        s = json.dumps(tasks, indent=1)
        Path(a.out).write_text(s) if a.out else print(s)
        return 0
    rows = run(json.loads(Path(a.tasks).read_text()), a.endpoint, Path(a.out), a.apply, a.reviewer)
    print(json.dumps({"attempted": len(rows), "verified": sum(r.get("verdict") == "verified" for r in rows)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
