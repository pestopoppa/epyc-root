#!/usr/bin/env python3
"""HS-19a "Linked" acceptance for the OpenCode subagents profile: prepare, then verify offline.

Stage 1 of the harness-subagent ladder (operator-approved 2026-09-27). OpenCode, running
the opt-in SUBAGENTS profile (harness/opencode-plugin/config/opencode.subagents.jsonc.template),
spawns exactly ONE sub-agent through its `task` tool. The orchestrator owns model selection
for both sessions; the harness never pins a model. With the orchestrator's `v1_subagent_link`
flag on, every child /v1 call is recorded with its parent link.

Only the `run.sh` that `prepare` writes sends inference. This script never does.
`plan` and `prepare` do no network work. `verify` reads files only (plus one local
`node` run of the config lint).

  plan       (default) print the checklist and run the local preflight checks.
  prepare    create a scratch git repo, the subagents OpenCode config, the prompt,
             and a run.sh that the owning session starts in its quiet window.
  verify     check the evidence run.sh left behind and write verdict.json.
  parent-id  (used by run.sh) print the parent session id from `opencode run` events.
  child-ids  (used by run.sh) print the child session ids named by the parent's task parts.

Checks (verdict.json):
  S1  exactly one `task` tool part in the parent, completed; exactly one child session,
      whose export names the parent as parentID; no compaction or subtask parts in either
      session; the child made no task call of its own.
  S2  tap calls in the run window keyed to the parent (request_keys.x_session_id) >= 1 and
      to the child >= 1, all with this x_user_id and x_tool_mode="client"; zero calls keyed
      to any other session. Unkeyed calls are advisory unless --strict-window (as P0.4 A4).
  S3  the link: every child call has parent_session_id == parent, a parent_session_id_source
      of "body" or "header:*", subagent_depth == 1 and no *_mismatch flag; parent calls carry
      no link keys. x_agent_name, where present, equals the session's agent in the export.
  S4  normal selection, no pin: the child has >= 1 tap call served by a role the
      orchestrator selected (whether it matches the parent's roles is recorded, not gated);
      no tap call carries an x_force_* key; every assistant message in both exports is
      epyc-orchestrator/orchestrator (and so is the task part's child model); the rendered
      config passes the subagents lint.
  S5  A5 token parity PER SESSION (P0.4 logic): step-finish sums equal the tap's
      server_terminal counts for that session's calls.
  S6  the orchestrator's progress JSONL has a session_created row with
      data.kind == "harness_subagent_link" linking child -> parent in the run window.
      Advisory when the log directory is missing; required with --strict-session-log.
      When the row is absent, verify polls the log for up to --session-log-wait-s
      (default 10) before failing: the API's uvicorn workers append to one shared
      dated file, so there is no per-worker file to read, and a row a worker has not
      yet written is invisible to any reader. (Before the orchestrator's log_durable
      fix the row could sit in a worker's batch buffer until the next API reload.)
  T1  the parent's final answer names the fixture codename (the delegated lookup worked).
  T2  the scratch repo is unmodified (the lookup was read-only).

`verify` is also the SC86 write-side hook, exactly as in P0.4: it writes the run sidecar
(opencode_shell_run.json, the name the vidya ingest discovers) and attempts.jsonl, then calls
scripts/vidya/adapters/opencode_shell_run_capture.write_belief_measurements through
hs4_p04_acceptance.capture_beliefs. One task, one trial; the attempt passes when T1 and S1
pass. input_tokens is the sum over both sessions: the tap's server_terminal counts when the
tap measured every call of BOTH sessions, else the sessions' own counts (labelled).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hs4_p04_acceptance as p04  # noqa: E402

ROOT = p04.ROOT
PLUGIN_DIR = p04.PLUGIN_DIR
TEMPLATE = PLUGIN_DIR / "config" / "opencode.subagents.jsonc.template"
ENV_FILE = p04.ENV_FILE
LINT = PLUGIN_DIR / "scripts" / "lint-config.ts"
PINNED_VERSION = p04.PINNED_VERSION
DEFAULT_TAP_EVENTS = p04.DEFAULT_TAP_EVENTS
DEFAULT_PROGRESS_LOG_DIR = Path("/mnt/raid0/llm/epyc-orchestrator/logs/progress")

PROVIDER_ID = "epyc-orchestrator"
MODEL_ID = "orchestrator"
SUBAGENT_TYPE = "general"
SESSION_LOG_KIND = "harness_subagent_link"
LINK_KEYS = ("parent_session_id", "parent_session_id_source", "subagent_depth",
             "subagent_depth_basis", "parent_session_id_mismatch")
DEPTH_BASES = {"observed", "parent_unseen"}

CODENAME = "amber-heron-47"
FIXTURE_FILES = {
    "README.md": "# hs19a fixture\n\nA tiny repository for the HS-19a sub-agent link test.\n",
    "app/__init__.py": "",
    "app/main.py": (
        '"""Entry point. The release constants live elsewhere."""\n\n'
        "from app.util import greet\n\n\n"
        "def main():\n"
        '    print(greet("world"))\n'
    ),
    "app/util.py": 'def greet(name):\n    return f"hello {name}"\n',
    "config/release.toml": (
        "# Release metadata\n"
        "[release]\n"
        "version = \"0.3.1\"\n"
        f"RELEASE_CODENAME = \"{CODENAME}\"\n"
    ),
    "docs/notes.md": "Release notes are kept in the config directory.\n",
}

TASK_PROMPT = (
    "Use the task tool exactly once, with subagent_type \"general\", to delegate this "
    "read-only lookup to a subagent: find the file in this repository that sets "
    "RELEASE_CODENAME and report its value. Do not search for it yourself and do not "
    "modify any file. When the subagent has answered, reply with exactly one line: "
    "CODENAME=<value>"
)

RUN_SH = """#!/bin/bash
# HS-19a "Linked" acceptance run. SENDS INFERENCE. Start it only inside the owning
# session's quiet window, after `hs19a_acceptance.py plan` passes.
set -euo pipefail
EVID={evidence}
REPO={repo}
export EPYC_ROOT={root}
export EPYC_USER_ID="${{EPYC_USER_ID:?set EPYC_USER_ID before running}}"
# SC86 serving identity, read from the live stack by the operator of this run.
: "${{EPYC_HARNESS_CARD_VERSION:?set EPYC_HARNESS_CARD_VERSION}}"
: "${{EPYC_MODEL_ROLE:?set EPYC_MODEL_ROLE (the role that served the run)}}"
: "${{EPYC_BUILD_INFO:?set EPYC_BUILD_INFO (llama-server --version of that role)}}"
: "${{EPYC_ENABLE_THINKING:?set EPYC_ENABLE_THINKING to true or false}}"
cat >&2 <<'PRECONDITION'
########################################################################################
# PRECONDITION (not checked by this script): the orchestrator API must be RUNNING with
# the HS-19a link flag ON, and must have been restarted after that code landed:
#     ORCHESTRATOR_FEATURE_V1_SUBAGENT_LINK=1
#     (or the runtime-flags overlay:  v1_subagent_link: true)
# With it off, S3 and S6 fail by construction: no parent_session_id reaches the tap.
########################################################################################
PRECONDITION
# shellcheck disable=SC1091
source {env_file}
export OPENCODE_CONFIG="$EVID/opencode.jsonc"
node {lint} --profile subagents "$OPENCODE_CONFIG" {env_file}
opencode --version > "$EVID/opencode-version.txt"
date +%s.%N > "$EVID/window-start.txt"
# No --auto: permission asks are auto-rejected. The prompt goes on STDIN, never as a
# positional (a positional with spaces is re-quoted: audit addendum 2026-09-24, pitfall 1).
# stdout/stderr go to FILES, never pipes (pitfall 2).
RUN_RC=0
(cd "$REPO" && opencode run --format json --title hs19a-acceptance) \\
  < "$EVID/prompt.txt" > "$EVID/events.jsonl" 2> "$EVID/opencode-stderr.log" || RUN_RC=$?
date +%s.%N > "$EVID/window-end.txt"
echo "$RUN_RC" > "$EVID/opencode-exit.txt"
PARENT=$(python3 {script} parent-id --events "$EVID/events.jsonl" || true)
echo "$PARENT" > "$EVID/parent-session-id.txt"
: > "$EVID/child-session-ids.txt"
if [ -n "$PARENT" ]; then
  (cd "$REPO" && opencode export "$PARENT") > "$EVID/parent-session.json"
  python3 {script} child-ids --session "$EVID/parent-session.json" > "$EVID/child-session-ids.txt"
  while IFS= read -r CID; do
    [ -n "$CID" ] || continue
    (cd "$REPO" && opencode export "$CID") > "$EVID/child-$CID.json"
  done < "$EVID/child-session-ids.txt"
fi
python3 {script} verify --evidence "$EVID" --user-id "$EPYC_USER_ID" \\
  --harness-card-version "$EPYC_HARNESS_CARD_VERSION" --model-role "$EPYC_MODEL_ROLE" \\
  --build-info "$EPYC_BUILD_INFO" --enable-thinking "$EPYC_ENABLE_THINKING" \\
  --endpoint "$EPYC_ORCHESTRATOR_BASE_URL"
"""

_check = p04._check


# ---------------------------------------------------------------- plan


def lint_config(path: Path) -> dict[str, Any]:
    node = shutil.which("node")
    if not node:
        return _check(False, "S4-config-lint-subagents", "node is not on PATH")
    proc = subprocess.run(
        [node, str(LINT), "--profile", "subagents", str(path), str(ENV_FILE)],
        capture_output=True, text=True, timeout=60,
    )
    return _check(proc.returncode == 0, "S4-config-lint-subagents",
                  (proc.stdout + proc.stderr).strip())


def preflight(opencode_bin: str | None = None) -> list[dict[str, Any]]:
    """Local checks only: no network, no inference, no process inspection."""
    checks = [c for c in p04.preflight(opencode_bin)
              if c["check"] in {"opencode-installed", "opencode-version-pinned", "env-file",
                                "node-installed"}]
    checks.append(_check(TEMPLATE.is_file(), "subagents-config-template", str(TEMPLATE)))
    if TEMPLATE.is_file():
        lint = lint_config(TEMPLATE)
        checks.append({**lint, "check": "config-lint-subagents"})
    return checks


PLAN_TEXT = """HS-19a "Linked" acceptance checklist
===================================
Manual gates (the owning session confirms each; this script cannot):
  [ ] Quiet window claimed; no benchmark or AutoKernel run shares the host.
  [ ] The acceptance role is served with a tool-capable --jinja template.
  [ ] The orchestrator API runs the HS-19a link code (v1_subagent_link) and was
      restarted after it landed (compare the uvicorn start time with the commit date).
  [ ] The link flag is ON: ORCHESTRATOR_FEATURE_V1_SUBAGENT_LINK=1
      (or the runtime-flags overlay v1_subagent_link: true). Default is OFF.
  [ ] Feature flag v1_client_session_guard is on (the default).
  [ ] EPYC_USER_ID is exported.
  [ ] SC86 serving identity exported: EPYC_HARNESS_CARD_VERSION, EPYC_MODEL_ROLE,
      EPYC_BUILD_INFO, EPYC_ENABLE_THINKING.
  [ ] No x_force_model / x_force_role anywhere: the orchestrator selects the model.
Steps:
  1. python3 scripts/harness/hs19a_acceptance.py prepare --out <dir>
  2. bash <dir>/evidence/run.sh           (SENDS INFERENCE)
  3. read <dir>/evidence/verdict.json; attach it to the handoff.
Preflight (local only):
"""


def cmd_plan(args: argparse.Namespace) -> int:
    print(PLAN_TEXT, end="")
    checks = preflight(args.opencode_bin)
    for c in checks:
        print(f"  {'PASS' if c['ok'] else 'FAIL'}  {c['check']}: {c['detail']}")
    return 0 if all(c["ok"] for c in checks) else 1


# ---------------------------------------------------------------- prepare


def cmd_prepare(args: argparse.Namespace) -> int:
    out = Path(args.out).resolve()
    repo, evidence = out / "repo", out / "evidence"
    if out.exists() and any(out.iterdir()):
        print(f"refusing: {out} exists and is not empty", file=sys.stderr)
        return 2
    repo.mkdir(parents=True)
    evidence.mkdir()
    for name, text in FIXTURE_FILES.items():
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    git = ["git", "-C", str(repo)]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", *FIXTURE_FILES], check=True)
    subprocess.run(
        [*git, "-c", "user.name=hs19a", "-c", "user.email=hs19a@localhost",
         "commit", "-q", "-m", "fixture"],
        check=True,
    )
    (evidence / "opencode.jsonc").write_text(TEMPLATE.read_text())
    (evidence / "prompt.txt").write_text(TASK_PROMPT + "\n")
    run_sh = evidence / "run.sh"
    run_sh.write_text(
        RUN_SH.format(
            evidence=p04._sh(evidence),
            repo=p04._sh(repo),
            root=p04._sh(ROOT),
            env_file=p04._sh(ENV_FILE),
            lint=p04._sh(LINT),
            script=p04._sh(Path(__file__).resolve()),
        )
    )
    run_sh.chmod(0o755)
    (evidence / "prepared.json").write_text(
        json.dumps(
            {
                "prepared_at": time.time(),
                "pinned_opencode": PINNED_VERSION,
                "profile": "subagents",
                "template": str(TEMPLATE),
                "orchestrator_flag": "v1_subagent_link (ORCHESTRATOR_FEATURE_V1_SUBAGENT_LINK=1)",
                "prompt": TASK_PROMPT,
                "expected_codename": CODENAME,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"prepared {out}\nnext (SENDS INFERENCE): bash {run_sh}")
    return 0


# ---------------------------------------------------------------- session helpers


def _parts(session: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for m in session.get("messages", []) for p in m.get("parts", [])]


def task_parts(session: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for p in _parts(session) if p.get("type") == "tool" and p.get("tool") == "task"]


def child_session_ids(session: dict[str, Any]) -> list[str]:
    """Child ids from the parent's task parts: state.metadata.sessionId (tool/task.ts:185-194)."""
    out: list[str] = []
    for part in task_parts(session):
        sid = ((part.get("state") or {}).get("metadata") or {}).get("sessionId")
        if isinstance(sid, str) and sid and sid not in out:
            out.append(sid)
    return out


def session_agent(session: dict[str, Any]) -> str | None:
    agent = (session.get("info") or {}).get("agent")
    if isinstance(agent, str) and agent:
        return agent
    for m in session.get("messages", []):
        info = m.get("info") or {}
        if info.get("role") == "assistant" and isinstance(info.get("agent"), str):
            return info["agent"]
    return None


def final_text(session: dict[str, Any]) -> str:
    for m in reversed(session.get("messages", [])):
        if (m.get("info") or {}).get("role") != "assistant":
            continue
        texts = [p.get("text", "") for p in m.get("parts", []) if p.get("type") == "text"]
        if any(t.strip() for t in texts):
            return "\n".join(texts)
    return ""


# ---------------------------------------------------------------- checks


def check_sessions(parent: dict[str, Any], parent_id: str, children: dict[str, dict[str, Any]],
                   child_ids: list[str]) -> list[dict[str, Any]]:
    tasks = task_parts(parent)
    done = [p for p in tasks if (p.get("state") or {}).get("status") == "completed"]
    child = children.get(child_ids[0]) if len(child_ids) == 1 else None
    child_info = (child or {}).get("info") or {}
    bad_parent = sorted(p.get("type") for p in _parts(parent)
                        if p.get("type") in {"compaction", "subtask"})
    bad_child = sorted(p.get("type") for p in _parts(child or {})
                       if p.get("type") in {"compaction", "subtask"})
    child_tasks = len(task_parts(child or {}))
    ok = (
        len(tasks) == 1 and len(done) == 1 and len(child_ids) == 1 and child is not None
        and child_info.get("id") == child_ids[0] and child_info.get("parentID") == parent_id
        and not bad_parent and not bad_child and child_tasks == 0
    )
    return [_check(
        ok, "S1-one-linked-child",
        f"parent task parts: {len(tasks)} ({len(done)} completed); child ids: {child_ids or 'none'}; "
        f"child export: {'present' if child is not None else 'missing'}, parentID "
        f"{child_info.get('parentID')!r}; compaction/subtask parts parent {bad_parent or 'none'}, "
        f"child {bad_child or 'none'}; child task calls: {child_tasks}",
    )]


def tap_calls(events: list[dict[str, Any]], start: float, end: float) -> dict[str, dict[str, Any]]:
    """One entry per request_id in the window: its request_keys (last seen) and roles."""
    calls: dict[str, dict[str, Any]] = {}
    for e in events:
        if not start <= float(e.get("ts_epoch") or 0) <= end:
            continue
        rid = str(e.get("request_id") or "")
        if not rid:
            continue
        call = calls.setdefault(rid, {"keys": None, "roles": set(), "force": set()})
        keys = e.get("request_keys")
        if isinstance(keys, dict):
            call["keys"] = keys
            call["force"].update(k for k in keys if k.startswith("x_force_"))
        if isinstance(e.get("role"), str) and e["role"]:
            call["roles"].add(e["role"])
    return calls


def _split(calls: dict[str, dict[str, Any]], parent_id: str, child_id: str | None):
    keyed = {rid: c for rid, c in calls.items() if c["keys"] is not None}
    parent = [c for c in keyed.values() if c["keys"].get("x_session_id") == parent_id]
    child = [c for c in keyed.values()
             if child_id is not None and c["keys"].get("x_session_id") == child_id]
    foreign = len(keyed) - len(parent) - len(child)
    unkeyed = len(calls) - len(keyed)
    return parent, child, foreign, unkeyed


def check_tap(calls: dict[str, dict[str, Any]], parent_id: str, child_id: str | None,
              user_id: str, strict_window: bool) -> list[dict[str, Any]]:
    parent, child, foreign, unkeyed = _split(calls, parent_id, child_id)
    wrong = [c for c in parent + child
             if c["keys"].get("x_user_id") != user_id or c["keys"].get("x_tool_mode") != "client"]
    ok = (bool(parent) and bool(child) and not wrong and foreign == 0
          and (unkeyed == 0 or not strict_window))
    return [_check(
        ok, "S2-tap-keyed-parent-and-child",
        f"{len(parent)} call(s) keyed to parent {parent_id}, {len(child)} to child {child_id}; "
        f"{len(wrong)} with a wrong x_user_id or x_tool_mode; {foreign} keyed to another session; "
        f"{unkeyed} without request_keys"
        + ("" if strict_window else " (unkeyed calls are advisory without --strict-window)"),
    )]


def check_link(calls: dict[str, dict[str, Any]], parent_id: str, child_id: str | None,
               parent_agent: str | None, child_agent: str | None) -> list[dict[str, Any]]:
    parent, child, _, _ = _split(calls, parent_id, child_id)
    problems: list[str] = []
    bases: set[str] = set()
    named = 0
    for c in child:
        k = c["keys"]
        if k.get("parent_session_id") != parent_id:
            problems.append(f"child call parent_session_id={k.get('parent_session_id')!r}")
        src = k.get("parent_session_id_source")
        if not (isinstance(src, str) and (src == "body" or src.startswith("header:"))):
            problems.append(f"child call parent_session_id_source={src!r}")
        depth = k.get("subagent_depth")
        if isinstance(depth, bool) or depth != 1:
            problems.append(f"child call subagent_depth={depth!r}")
        basis = k.get("subagent_depth_basis")
        if basis not in DEPTH_BASES:
            problems.append(f"child call subagent_depth_basis={basis!r}")
        else:
            bases.add(basis)
        for flag in ("session_id_mismatch", "parent_session_id_mismatch"):
            if k.get(flag):
                problems.append(f"child call {flag}")
        if "x_agent_name" in k:
            named += 1
            if k["x_agent_name"] != child_agent:
                problems.append(f"child x_agent_name={k['x_agent_name']!r} != export agent {child_agent!r}")
    for c in parent:
        k = c["keys"]
        present = [key for key in LINK_KEYS if key in k]
        if present:
            problems.append(f"parent call carries link keys {present}")
        if k.get("session_id_mismatch"):
            problems.append("parent call session_id_mismatch")
        if "x_agent_name" in k and k["x_agent_name"] != parent_agent:
            problems.append(f"parent x_agent_name={k['x_agent_name']!r} != export agent {parent_agent!r}")
    ok = bool(child) and not problems
    return [_check(
        ok, "S3-parent-link-recorded",
        f"{len(child)} child call(s) checked, {named} carrying x_agent_name (export agent "
        f"{child_agent!r}); depth basis {sorted(bases) or 'none'}; "
        + ("; ".join(sorted(set(problems))) if problems else "no problems"),
    )]


def check_selection(calls: dict[str, dict[str, Any]], parent_id: str, child_id: str | None,
                    sessions: list[dict[str, Any]], parent: dict[str, Any]) -> list[dict[str, Any]]:
    p_calls, c_calls, _, _ = _split(calls, parent_id, child_id)
    p_roles = set().union(*(c["roles"] for c in p_calls)) if p_calls else set()
    c_roles = set().union(*(c["roles"] for c in c_calls)) if c_calls else set()
    # The child is a plain request to the one logical model, so ANY role the
    # orchestrator's selection picked is "normal selection"; a pin is caught by
    # S4-no-force-pin and S4-one-logical-model. Whether the child landed on the
    # parent's roles is recorded, not gated (a different prompt may route differently).
    roles_ok = bool(c_roles)
    forced = sorted(set().union(*(c["force"] for c in calls.values()))) if calls else []
    models = []
    for s in sessions:
        for m in s.get("messages", []):
            info = m.get("info") or {}
            if info.get("role") == "assistant":
                models.append((info.get("providerID"), info.get("modelID")))
    task_models = [((p.get("state") or {}).get("metadata") or {}).get("model") or {}
                   for p in task_parts(parent)]
    models += [(tm.get("providerID"), tm.get("modelID")) for tm in task_models]
    off = sorted({f"{p}/{m}" for p, m in models if (p, m) != (PROVIDER_ID, MODEL_ID)})
    return [
        _check(roles_ok, "S4-child-served-by-selection",
               f"parent roles {sorted(p_roles) or 'none'}; child roles {sorted(c_roles) or 'none'}; "
               f"child within parent's roles: {bool(c_roles) and c_roles <= p_roles}"),
        _check(not forced, "S4-no-force-pin",
               f"x_force_* keys on tap calls in window: {forced or 'none'}"),
        _check(bool(models) and not off, "S4-one-logical-model",
               f"{len(models)} assistant message(s)/task model(s) checked; not "
               f"{PROVIDER_ID}/{MODEL_ID}: {off or 'none'}"),
    ]


def check_token_parity(name: str, session: dict[str, Any], tap: dict[str, Any]) -> dict[str, Any]:
    c = p04.check_token_parity(session, tap)
    return {**c, "check": name}


def _progress_rows(log_dir: Path, start: float, end: float) -> list[dict[str, Any]]:
    day = datetime.fromtimestamp(start, timezone.utc).date()
    last = datetime.fromtimestamp(end, timezone.utc).date()
    rows: list[dict[str, Any]] = []
    while day <= last:
        path = log_dir / f"{day.isoformat()}.jsonl"
        if path.is_file():
            rows += p04._jsonl(path)
        day += timedelta(days=1)
    return rows


def _session_log_hits(log_dir: Path, parent_id: str, child_id: str | None, start: float,
                      end: float) -> list[dict[str, Any]]:
    hits = []
    for row in _progress_rows(log_dir, start, end):
        data = row.get("data") or {}
        if row.get("event_type") != "session_created" or data.get("kind") != SESSION_LOG_KIND:
            continue
        try:
            ts = datetime.fromisoformat(str(row.get("timestamp"))).timestamp()
        except ValueError:
            continue
        if not start <= ts <= end:
            continue
        if data.get("session_id") == child_id and data.get("parent_session_id") == parent_id:
            hits.append(data)
    return hits


def check_session_log(log_dir: Path, parent_id: str, child_id: str | None, start: float,
                      end: float, strict: bool, wait_s: float = 0.0, poll_s: float = 1.0,
                      *, clock=time.monotonic, sleep=time.sleep) -> dict[str, Any]:
    """S6. Polls a bounded ``wait_s`` for the row before failing (never when it is found)."""
    if not log_dir.is_dir():
        return _check(not strict, "S6-session-log-link",
                      f"progress log dir missing: {log_dir}"
                      + ("" if strict else " (advisory without --strict-session-log)"))
    deadline = clock() + max(0.0, wait_s)
    polls = 0
    hits = _session_log_hits(log_dir, parent_id, child_id, start, end)
    while not hits and child_id is not None and clock() < deadline:
        sleep(max(0.0, min(poll_s, deadline - clock())))
        polls += 1
        hits = _session_log_hits(log_dir, parent_id, child_id, start, end)
    return _check(bool(hits) and child_id is not None, "S6-session-log-link",
                  f"{len(hits)} session_created/{SESSION_LOG_KIND} row(s) linking {child_id} -> "
                  f"{parent_id} in {log_dir}"
                  + (f"; depth {hits[0].get('subagent_depth')!r}, name {hits[0].get('name')!r}"
                     if hits else "")
                  + (f" (after {polls} re-read(s) over <= {wait_s:g}s)" if polls else ""))


def check_answer(parent: dict[str, Any]) -> dict[str, Any]:
    text = final_text(parent)
    return _check(CODENAME in text, "T1-answer-correct",
                  f"final answer {text.strip()[-200:]!r}; expected codename {CODENAME}")


def check_repo_unmodified(repo: Path) -> dict[str, Any]:
    proc = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                          capture_output=True, text=True, timeout=60)
    dirty = proc.stdout.strip()
    return _check(proc.returncode == 0 and not dirty, "T2-repo-unmodified",
                  dirty[-300:] or (proc.stderr.strip() or "clean"))


def combine_tokens(per_session: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Sum the P0.4 per-session resolution over both sessions.

    The tap is authoritative only when it measured every call of EVERY session;
    otherwise every session's own count is used, and labelled so.
    """
    all_tap = all(t["input_tokens_source"] == "tap_server_terminal" for t in per_session.values())
    key = "input_tokens" if all_tap else "session_prompt_tokens"
    return {
        "input_tokens": sum(t[key] for t in per_session.values()),
        "input_tokens_source": "tap_server_terminal" if all_tap else "opencode_session",
        "cached_prompt_tokens": sum(t["cached_prompt_tokens"] for t in per_session.values()),
        "cached_prompt_tokens_source": "opencode_session",
        "per_session": per_session,
    }


def task_suite_fingerprint() -> str:
    parts = [f"{k}\0{v}".encode() for k, v in sorted(FIXTURE_FILES.items())]
    return p04._sha256_bytes(parts + [TASK_PROMPT.encode()])


def _read(path: Path) -> str:
    return path.read_text().strip() if path.is_file() else ""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text()) if path.is_file() else {}
    except json.JSONDecodeError:
        return {}


def cmd_verify(args: argparse.Namespace) -> int:
    evid = Path(args.evidence).resolve()
    repo = Path(args.repo).resolve() if args.repo else evid.parent / "repo"
    parent_id = _read(evid / "parent-session-id.txt")
    start = float(_read(evid / "window-start.txt"))
    end = float(_read(evid / "window-end.txt"))
    window_end = end + args.slack_s
    parent = _load_json(evid / "parent-session.json")
    child_ids = [x for x in _read(evid / "child-session-ids.txt").splitlines() if x.strip()]
    children = {cid: _load_json(evid / f"child-{cid}.json") for cid in child_ids}
    children = {cid: s for cid, s in children.items() if s}
    child_id = child_ids[0] if len(child_ids) == 1 else None
    child = children.get(child_id, {}) if child_id else {}

    checks = [_check(bool(parent_id) and bool(parent), "parent-session-exported",
                     f"parent {parent_id or '?'}: export {'present' if parent else 'missing'}")]
    checks += check_sessions(parent, parent_id, children, child_ids)

    tap = Path(args.tap_events)
    per_session_tokens: dict[str, dict[str, Any]] = {}
    if tap.is_file():
        events = p04._jsonl(tap)
        calls = tap_calls(events, start, window_end)
        checks += check_tap(calls, parent_id, child_id, args.user_id, args.strict_window)
        checks += check_link(calls, parent_id, child_id, session_agent(parent), session_agent(child))
        checks += check_selection(calls, parent_id, child_id, [parent, child], parent)
        for label, sid, sess in (("parent", parent_id, parent), ("child", child_id, child)):
            t = p04.tap_token_counts(events, sid or "", start, window_end)
            checks.append(check_token_parity(f"S5-{label}-tokens-match-tap", sess, t))
            per_session_tokens[label] = p04.resolve_token_counts(sess, t)
    else:
        for name in ("S2-tap-keyed-parent-and-child", "S3-parent-link-recorded",
                     "S4-child-served-by-selection", "S4-no-force-pin",
                     "S5-parent-tokens-match-tap", "S5-child-tokens-match-tap"):
            checks.append(_check(False, name, f"tap events file missing: {tap}"))
        checks += [c for c in check_selection({}, parent_id, child_id, [parent, child], parent)
                   if c["check"] == "S4-one-logical-model"]
        per_session_tokens = {"parent": p04.resolve_token_counts(parent, None),
                              "child": p04.resolve_token_counts(child, None)}
    checks.append(lint_config(evid / "opencode.jsonc"))
    checks.append(check_session_log(Path(args.progress_log_dir), parent_id, child_id, start,
                                    window_end, args.strict_session_log,
                                    wait_s=args.session_log_wait_s))
    checks.append(check_answer(parent))
    checks.append(check_repo_unmodified(repo))

    errors = ([e for e in p04._jsonl(evid / "events.jsonl") if e.get("type") == "error"]
              if (evid / "events.jsonl").is_file() else [])
    checks.append(_check(not errors, "run-no-error-events", f"{len(errors)} error event(s)"))
    rc = _read(evid / "opencode-exit.txt")
    if rc:
        checks.append(_check(rc == "0", "run-exit-zero", f"opencode run exited {rc}"))
    version = _read(evid / "opencode-version.txt")
    if version:
        checks.append(_check(version == PINNED_VERSION, "opencode-version-pinned", version))

    passed = (p04._by_name(checks, "T1-answer-correct")["ok"]
              and p04._by_name(checks, "S1-one-linked-child")["ok"])
    tokens = combine_tokens(per_session_tokens)
    capture = p04.capture_beliefs(
        args, evid, parent, parent_id or "unknown", start, end, passed, tokens,
        task="hs19a-linked-subagent-lookup",
        run_id=f"hs19a-{parent_id or 'unknown'}",
        suite={"name": "hs19a-linked-subagent-fixture", "fingerprint": task_suite_fingerprint()},
        producer="scripts/harness/hs19a_acceptance.py",
        record_extra={"child_session_id": child_id, "profile": "subagents",
                      "per_session_input_tokens": {
                          k: v["input_tokens"] for k, v in per_session_tokens.items()}},
    )
    checks.append(_check(capture["status"] in {"written", "skipped"}, "sc86-belief-capture",
                         f"{capture['status']}: {capture.get('path') or capture.get('reason')}"))
    verdict = {
        "schema": "hs19a-acceptance/v1",
        "pass": all(c["ok"] for c in checks),
        "profile": "subagents",
        "parent_session_id": parent_id,
        "child_session_ids": child_ids,
        "window": [start, end],
        "tap_events": str(tap),
        "progress_log_dir": str(args.progress_log_dir),
        "checks": checks,
        "token_counts": tokens,
        "belief_capture": capture,
        "note": "The pass/fail verdict is an acceptance check. The SC86 belief rows are "
                "Judged/Located observations until SC86b codifies a shell-run protocol.",
    }
    (evid / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")
    for c in checks:
        print(f"{'PASS' if c['ok'] else 'FAIL'}  {c['check']}: {c['detail']}")
    print("VERDICT", "PASS" if verdict["pass"] else "FAIL")
    return 0 if verdict["pass"] else 1


# ---------------------------------------------------------------- run.sh helpers


def cmd_parent_id(args: argparse.Namespace) -> int:
    """The first event's sessionID. `opencode run` stamps every event with the root session
    (cli/cmd/run.ts:678-690), and child parts are filtered out of the stream (:722)."""
    for row in p04._jsonl(Path(args.events)):
        sid = row.get("sessionID")
        if isinstance(sid, str) and sid:
            print(sid)
            return 0
    return 1


def cmd_child_ids(args: argparse.Namespace) -> int:
    for sid in child_session_ids(_load_json(Path(args.session))):
        print(sid)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("plan")
    p.add_argument("--opencode-bin")
    p = sub.add_parser("prepare")
    p.add_argument("--out", required=True)
    p = sub.add_parser("parent-id")
    p.add_argument("--events", required=True)
    p = sub.add_parser("child-ids")
    p.add_argument("--session", required=True)
    p = sub.add_parser("verify")
    p.add_argument("--evidence", required=True)
    p.add_argument("--repo")
    p.add_argument("--user-id", required=True)
    p.add_argument("--tap-events", default=str(DEFAULT_TAP_EVENTS))
    p.add_argument("--slack-s", type=float, default=5.0)
    p.add_argument("--strict-window", action="store_true")
    p.add_argument("--progress-log-dir", default=str(DEFAULT_PROGRESS_LOG_DIR))
    p.add_argument("--strict-session-log", action="store_true")
    p.add_argument("--session-log-wait-s", type=float, default=10.0,
                   help="S6: re-read the progress log for up to this many seconds when the "
                        "link row is not there yet (0 = one read)")
    g = p.add_argument_group("SC86 belief capture (the serving identity is recorded, never guessed)")
    g.add_argument("--no-belief-capture", action="store_true")
    g.add_argument("--harness-card-version", default="")
    g.add_argument("--model-role", default="")
    g.add_argument("--build-info", default="")
    g.add_argument("--enable-thinking", choices=["true", "false"])
    g.add_argument("--endpoint", default="http://127.0.0.1:8000/v1")
    g.add_argument("--emitted-at", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if args.cmd is None:
        args = ap.parse_args(["plan", *(argv or [])])
    return {"plan": cmd_plan, "prepare": cmd_prepare, "verify": cmd_verify,
            "parent-id": cmd_parent_id, "child-ids": cmd_child_ids}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
