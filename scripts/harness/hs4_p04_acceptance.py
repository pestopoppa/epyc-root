#!/usr/bin/env python3
"""HS-4 P0.4 live acceptance for the OpenCode shell: prepare, then verify offline.

Only the `run.sh` that `prepare` writes sends inference. This script never
does. `plan` and `prepare` do no network work. `verify` reads files only.

  plan     (default) print the checklist and run the local preflight checks.
  prepare  create a scratch git repo, the OpenCode config, and a run.sh that
           the owning session starts in its P0.4 quiet window.
  verify   check the evidence that run.sh left behind and write verdict.json.

Acceptance (docs/design/hs4-shell-and-orchestrator-features-20260916.md §4, P0.1 + P0.4):
  A1  OpenCode completes a read -> edit -> bash loop in the scratch repo, and
      the fixture test passes afterwards.
  A2  the orchestrator saw the x_* keys at the body's top level: tap events in
      the run window carry request_keys with this session's x_session_id,
      x_user_id and x_tool_mode="client".
  A3  no compaction and no subtask parts in the exported session.
  A4  every attributable tap call in the window carries the keys (title and
      side calls are disabled by the template, so none should lack them).
      Calls with no request_keys cannot be attributed to this run; they are
      counted and reported, and fail A4 only with --strict-window.
  A5  token parity: the exported session's prompt and completion totals equal
      the tap's server_terminal totals for this session's calls. The tap is
      the orchestrator's own measurement; the session is what the client
      recorded from /v1 `usage`. A client that lost or zeroed usage fails here.

`verify` is also the SC86 write-side hook (HS-4 P0.5): it writes
opencode_shell_run.json and attempts.jsonl, then calls
scripts/vidya/adapters/opencode_shell_run_capture.write_belief_measurements.
counts.input_tokens comes from the tap's server_terminal prompt_tokens when the
tap measured every call of the session (authoritative), else from the session;
the source is recorded in attempts.jsonl and verdict.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = ROOT / "harness" / "opencode-plugin"
TEMPLATE = PLUGIN_DIR / "config" / "opencode.jsonc.template"
ENV_FILE = PLUGIN_DIR / "config" / "opencode.env"
_PIN = json.loads((PLUGIN_DIR / "package.json").read_text())["opencode"]
PINNED_VERSION = _PIN["pluginApi"]
AUDITED_TIP = _PIN["auditedTip"]
DEFAULT_TAP_EVENTS = Path("/mnt/raid0/llm/tmp/inference_tap_events.jsonl")
EDIT_TOOLS = {"edit", "write", "apply_patch"}

# Orchestrator commits the live run depends on. The API must have been
# restarted after these landed (CLAUDE.md "Process Management").
ORCHESTRATOR_COMMITS = {
    "P0.1/P0.2 client tool mode + typed keys": "ed554da2",
    "P0.1/P0.2 review fixes": "b44ab3a8",
    "P0-MCP session_id on MCP tools": "54b6439d",
}

FIXTURE_FILES = {
    "calc.py": (
        '"""Tiny fixture for the HS-4 P0.4 OpenCode acceptance loop."""\n\n\n'
        "def add(a, b):\n"
        "    return a - b\n"
    ),
    "test_calc.sh": (
        "#!/bin/bash\n"
        "set -euo pipefail\n"
        'cd "$(dirname "$0")"\n'
        "python3 -B -c 'from calc import add; assert add(2, 3) == 5, add(2, 3)'\n"
        "echo PASS\n"
    ),
}

TASK_PROMPT = (
    "Read calc.py. The add function is wrong: fix it with a minimal edit. "
    "Then run `bash test_calc.sh` and report its output."
)

RUN_SH = """#!/bin/bash
# HS-4 P0.4 live acceptance run. SENDS INFERENCE. Start it only inside the
# owning session's P0.4 quiet window, after `hs4_p04_acceptance.py plan` passes.
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
# shellcheck disable=SC1091
source {env_file}
export OPENCODE_CONFIG="$EVID/opencode.jsonc"
node {lint} "$OPENCODE_CONFIG" {env_file}
opencode --version > "$EVID/opencode-version.txt"
date +%s.%N > "$EVID/window-start.txt"
# No --auto: permission asks are auto-rejected. edit and bash are allowed by
# OpenCode's defaults inside the project directory.
RUN_RC=0
(cd "$REPO" && opencode run --format json --title hs4-p04-acceptance {prompt}) \\
  > "$EVID/events.jsonl" 2> "$EVID/opencode-stderr.log" || RUN_RC=$?
date +%s.%N > "$EVID/window-end.txt"
echo "$RUN_RC" > "$EVID/opencode-exit.txt"
SID=$(python3 -c 'import json,sys
for line in open(sys.argv[1]):
    line = line.strip()
    if line:
        print(json.loads(line)["sessionID"]); break' "$EVID/events.jsonl")
echo "$SID" > "$EVID/session-id.txt"
(cd "$REPO" && opencode export "$SID") > "$EVID/session.json"
python3 {script} verify --evidence "$EVID" --user-id "$EPYC_USER_ID" \\
  --harness-card-version "$EPYC_HARNESS_CARD_VERSION" --model-role "$EPYC_MODEL_ROLE" \\
  --build-info "$EPYC_BUILD_INFO" --enable-thinking "$EPYC_ENABLE_THINKING" \\
  --endpoint "$EPYC_ORCHESTRATOR_BASE_URL"
"""


def _check(ok: bool, name: str, detail: str) -> dict[str, Any]:
    return {"check": name, "ok": bool(ok), "detail": detail}


# ---------------------------------------------------------------- plan


def preflight(opencode_bin: str | None = None) -> list[dict[str, Any]]:
    """Local checks only: no network, no inference, no process inspection."""
    checks = []
    binary = opencode_bin or shutil.which("opencode")
    if not binary:
        checks.append(_check(False, "opencode-installed", "opencode is not on PATH"))
    else:
        out = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=30)
        version = out.stdout.strip()
        checks.append(
            _check(
                version == PINNED_VERSION,
                "opencode-version-pinned",
                f"{binary} reports {version or '?'}; the audited pin is {PINNED_VERSION}"
                + (
                    ""
                    if version == PINNED_VERSION
                    else f" (install it: npm install -g opencode-ai@{PINNED_VERSION})"
                ),
            )
        )
    checks.append(_check(TEMPLATE.is_file(), "config-template", str(TEMPLATE)))
    checks.append(_check(ENV_FILE.is_file(), "env-file", str(ENV_FILE)))
    node = shutil.which("node")
    checks.append(_check(node is not None, "node-installed", node or "node is not on PATH"))
    if node and TEMPLATE.is_file():
        lint = subprocess.run(
            [node, str(PLUGIN_DIR / "scripts" / "lint-config.ts"), str(TEMPLATE), str(ENV_FILE)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        checks.append(
            _check(lint.returncode == 0, "config-lint", (lint.stdout + lint.stderr).strip())
        )
    return checks


PLAN_TEXT = """HS-4 P0.4 live acceptance checklist
===================================
Manual gates (the owning session confirms each; this script cannot):
  [ ] P0.4 quiet window claimed; no benchmark or AutoKernel run shares the host.
  [ ] The acceptance role is served with a tool-capable --jinja template.
  [ ] The orchestrator API was restarted after these commits landed:
{commits}
      (compare the uvicorn start time with the commit dates; do not trust a reload claim).
  [ ] Feature flag v1_client_session_guard is on (the default).
  [ ] EPYC_USER_ID is exported.
  [ ] SC86 serving identity exported: EPYC_HARNESS_CARD_VERSION, EPYC_MODEL_ROLE,
      EPYC_BUILD_INFO, EPYC_ENABLE_THINKING. verify writes opencode_shell_run.json and
      calls the SC86 writer; rows stay Judged/Located until SC86b.
Steps:
  1. python3 scripts/harness/hs4_p04_acceptance.py prepare --out <dir>
  2. bash <dir>/evidence/run.sh           (SENDS INFERENCE)
  3. read <dir>/evidence/verdict.json; attach it to the handoff.
  4. On a pass: republish the Harness Card (HS-7) and freeze the OpenCode pin (HS-5b).
Preflight (local only):
"""


def cmd_plan(args: argparse.Namespace) -> int:
    commits = "\n".join(f"        {sha}  {what}" for what, sha in ORCHESTRATOR_COMMITS.items())
    print(PLAN_TEXT.format(commits=commits), end="")
    checks = preflight(args.opencode_bin)
    for c in checks:
        print(f"  {'PASS' if c['ok'] else 'FAIL'}  {c['check']}: {c['detail']}")
    return 0 if all(c["ok"] for c in checks) else 1


# ---------------------------------------------------------------- prepare


def render_config(template_text: str, enable_mcp: bool) -> str:
    if not enable_mcp:
        return template_text
    needle = '"enabled": false'
    if template_text.count(needle) != 1:
        raise ValueError(f"expected exactly one {needle!r} in the template")
    return template_text.replace(needle, '"enabled": true')


def cmd_prepare(args: argparse.Namespace) -> int:
    out = Path(args.out).resolve()
    repo, evidence = out / "repo", out / "evidence"
    if out.exists() and any(out.iterdir()):
        print(f"refusing: {out} exists and is not empty", file=sys.stderr)
        return 2
    repo.mkdir(parents=True)
    evidence.mkdir()
    for name, text in FIXTURE_FILES.items():
        (repo / name).write_text(text)
    git = ["git", "-C", str(repo)]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", *FIXTURE_FILES], check=True)
    subprocess.run(
        [*git, "-c", "user.name=hs4-p04", "-c", "user.email=hs4-p04@localhost",
         "commit", "-q", "-m", "fixture"],
        check=True,
    )
    (evidence / "opencode.jsonc").write_text(render_config(TEMPLATE.read_text(), args.enable_mcp))
    run_sh = evidence / "run.sh"
    run_sh.write_text(
        RUN_SH.format(
            evidence=_sh(evidence),
            repo=_sh(repo),
            root=_sh(ROOT),
            env_file=_sh(ENV_FILE),
            lint=_sh(PLUGIN_DIR / "scripts" / "lint-config.ts"),
            prompt=_sh(TASK_PROMPT),
            script=_sh(Path(__file__).resolve()),
        )
    )
    run_sh.chmod(0o755)
    (evidence / "prepared.json").write_text(
        json.dumps(
            {
                "prepared_at": time.time(),
                "pinned_opencode": PINNED_VERSION,
                "mcp_enabled": args.enable_mcp,
                "orchestrator_commits": ORCHESTRATOR_COMMITS,
                "prompt": TASK_PROMPT,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"prepared {out}\nnext (SENDS INFERENCE): bash {run_sh}")
    return 0


def _sh(value: object) -> str:
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


# ---------------------------------------------------------------- verify


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def check_session(session: dict[str, Any]) -> list[dict[str, Any]]:
    parts = [p for m in session.get("messages", []) for p in m.get("parts", [])]
    tools = [p for p in parts if p.get("type") == "tool"]
    done = [p.get("tool") for p in tools if p.get("state", {}).get("status") == "completed"]
    order = []
    for name in done:
        kind = "edit" if name in EDIT_TOOLS else name
        if kind in {"read", "edit", "bash"} and (not order or order[-1] != kind):
            order.append(kind)
    loop_ok = _is_subsequence(["read", "edit", "bash"], order)
    bad = sorted(p.get("type") for p in parts if p.get("type") in {"compaction", "subtask"})
    task_calls = [p for p in tools if p.get("tool") == "task"]
    return [
        _check(loop_ok, "A1-read-edit-bash-loop", f"completed tool order: {order or 'none'}"),
        _check(not bad and not task_calls, "A3-no-compaction-or-subtask",
               f"compaction/subtask parts: {bad or 'none'}; task calls: {len(task_calls)}"),
    ]


def _is_subsequence(needle: list[str], hay: list[str]) -> bool:
    it = iter(hay)
    return all(any(x == y for y in it) for x in needle)


def check_tap(
    events: list[dict[str, Any]],
    session_id: str,
    user_id: str,
    start: float,
    end: float,
    strict_window: bool,
) -> list[dict[str, Any]]:
    # The tap writes several events per model call (metadata, chunk, response,
    # end), each carrying the section metadata. One call = one request_id.
    calls: dict[str, dict[str, Any] | None] = {}
    for e in events:
        if not start <= float(e.get("ts_epoch") or 0) <= end:
            continue
        rid = str(e.get("request_id") or "")
        if not rid:
            continue
        keys = e.get("request_keys")
        if isinstance(keys, dict):
            calls[rid] = keys
        else:
            calls.setdefault(rid, None)
    keyed = [k for k in calls.values() if k is not None]
    ours = [k for k in keyed if k.get("x_session_id") == session_id]
    wrong = [
        k for k in ours
        if k.get("x_user_id") != user_id or k.get("x_tool_mode") != "client"
    ]
    foreign = len(keyed) - len(ours)
    unkeyed = len(calls) - len(keyed)
    return [
        _check(bool(ours) and not wrong, "A2-keys-at-top-level",
               f"{len(ours)} tap call(s) keyed to {session_id}; {len(wrong)} with a wrong "
               "x_user_id or x_tool_mode"),
        _check(foreign == 0 and (unkeyed == 0 or not strict_window), "A4-no-unkeyed-side-calls",
               f"in window: {unkeyed} call(s) without request_keys (not attributable), "
               f"{foreign} keyed to another session"
               + ("" if strict_window else "; unkeyed calls are advisory without --strict-window")),
    ]


def check_fixture(repo: Path) -> dict[str, Any]:
    proc = subprocess.run(["bash", str(repo / "test_calc.sh")], capture_output=True, text=True,
                          timeout=60)
    return _check(proc.returncode == 0, "A1-fixture-test-passes",
                  (proc.stdout + proc.stderr).strip()[-300:])


def cmd_verify(args: argparse.Namespace) -> int:
    evid = Path(args.evidence).resolve()
    repo = Path(args.repo).resolve() if args.repo else evid.parent / "repo"
    session_id = (evid / "session-id.txt").read_text().strip()
    start = float((evid / "window-start.txt").read_text().strip())
    end = float((evid / "window-end.txt").read_text().strip())
    session = json.loads((evid / "session.json").read_text())
    checks = check_session(session)
    checks.append(check_fixture(repo))
    tap = Path(args.tap_events)
    tap_tokens: dict[str, Any] | None = None
    if tap.is_file():
        tap_events = _jsonl(tap)
        checks += check_tap(tap_events, session_id, args.user_id, start, end + args.slack_s,
                            args.strict_window)
        tap_tokens = tap_token_counts(tap_events, session_id, start, end + args.slack_s)
        checks.append(check_token_parity(session, tap_tokens))
    else:
        checks.append(_check(False, "A2-keys-at-top-level", f"tap events file missing: {tap}"))
        checks.append(_check(False, "A5-session-tokens-match-tap",
                             f"tap events file missing: {tap}"))
    errors = [e for e in _jsonl(evid / "events.jsonl") if e.get("type") == "error"] \
        if (evid / "events.jsonl").is_file() else []
    checks.append(_check(not errors, "run-no-error-events", f"{len(errors)} error event(s)"))
    exit_file = evid / "opencode-exit.txt"
    if exit_file.is_file():
        rc = exit_file.read_text().strip()
        checks.append(_check(rc == "0", "run-exit-zero", f"opencode run exited {rc}"))
    version = (evid / "opencode-version.txt")
    if version.is_file():
        v = version.read_text().strip()
        checks.append(_check(v == PINNED_VERSION, "opencode-version-pinned", v))
    fixture_ok = _by_name(checks, "A1-fixture-test-passes")["ok"]
    tokens = resolve_token_counts(session, tap_tokens)
    capture = capture_beliefs(args, evid, session, session_id, start, end, fixture_ok, tokens)
    checks.append(_check(capture["status"] in {"written", "skipped"}, "sc86-belief-capture",
                         f"{capture['status']}: {capture.get('path') or capture.get('reason')}"))
    verdict = {
        "schema": "hs4-p04-acceptance/v1",
        "pass": all(c["ok"] for c in checks),
        "session_id": session_id,
        "window": [start, end],
        "tap_events": str(tap),
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


def _by_name(checks: list[dict[str, Any]], name: str) -> dict[str, Any]:
    return next(c for c in checks if c["check"] == name)


# ---------------------------------------------------------------- SC86 write side


def _utc(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_bytes(chunks: list[bytes]) -> str:
    h = hashlib.sha256()
    for c in chunks:
        h.update(hashlib.sha256(c).digest())
    return h.hexdigest()


def plugin_sha256() -> str:
    """Digest over the plugin source files (src/*.ts, sorted by name)."""
    files = sorted((PLUGIN_DIR / "src").glob("*.ts"))
    return _sha256_bytes([f.name.encode() + b"\0" + f.read_bytes() for f in files])


def task_suite_fingerprint() -> str:
    parts = [f"{k}\0{v}".encode() for k, v in sorted(FIXTURE_FILES.items())]
    return _sha256_bytes(parts + [TASK_PROMPT.encode()])


def step_token_counts(session: dict[str, Any]) -> tuple[int, int]:
    """(prompt tokens, cache-read tokens) summed over step-finish parts.

    At the pin, OpenCode's `tokens.input` excludes cache read and write
    (session/session.ts:361-370), so one call's prompt size is
    input + cache.read + cache.write. A message's own `tokens` holds only its
    last step (session/processor.ts:459), so the step-finish parts are summed.
    """
    prompt = cached = 0
    for m in session.get("messages", []):
        for part in m.get("parts", []):
            if part.get("type") != "step-finish":
                continue
            t = part.get("tokens") or {}
            cache = t.get("cache") or {}
            prompt += int(t.get("input", 0)) + int(cache.get("read", 0)) + int(cache.get("write", 0))
            cached += int(cache.get("read", 0))
    return prompt, cached


def step_completion_tokens(session: dict[str, Any]) -> int:
    """Completion tokens summed over step-finish parts.

    At the pin, OpenCode splits the server's completion_tokens into
    output (text) + reasoning (session/session.ts:373-374).
    """
    total = 0
    for m in session.get("messages", []):
        for part in m.get("parts", []):
            if part.get("type") == "step-finish":
                t = part.get("tokens") or {}
                total += int(t.get("output", 0)) + int(t.get("reasoning", 0))
    return total


def _step_count(session: dict[str, Any]) -> int:
    return sum(1 for m in session.get("messages", []) for part in m.get("parts", [])
               if part.get("type") == "step-finish")


def tap_token_counts(events: list[dict[str, Any]], session_id: str, start: float,
                     end: float) -> dict[str, Any]:
    """The orchestrator's own token counts for this session's calls.

    One `timings` event per model call (keyed by request_id), attributed by
    request_keys.x_session_id. prompt_tokens counts only when its source is
    server_terminal (the server's own number); a call without one is counted
    as unmeasured, never estimated. `tokens` is the server's completion count.
    """
    calls: dict[str, dict[str, Any]] = {}
    for e in events:
        if e.get("event") != "timings":
            continue
        if not start <= float(e.get("ts_epoch") or 0) <= end:
            continue
        keys = e.get("request_keys")
        if not isinstance(keys, dict) or keys.get("x_session_id") != session_id:
            continue
        rid = str(e.get("request_id") or "")
        if rid:
            calls[rid] = e
    measured = [
        e for e in calls.values()
        if e.get("prompt_tokens_source") == "server_terminal"
        and isinstance(e.get("prompt_tokens"), int) and not isinstance(e.get("prompt_tokens"), bool)
    ]
    return {
        "calls": len(calls),
        "measured_calls": len(measured),
        "prompt_tokens": sum(int(e["prompt_tokens"]) for e in measured),
        "completion_tokens": sum(int(e.get("tokens") or 0) for e in calls.values()),
    }


def check_token_parity(session: dict[str, Any], tap: dict[str, Any]) -> dict[str, Any]:
    """A5: what the client recorded equals what the orchestrator measured."""
    s_prompt, _ = step_token_counts(session)
    s_completion = step_completion_tokens(session)
    ok = (
        tap["calls"] >= 1
        and tap["measured_calls"] == tap["calls"]
        and s_prompt == tap["prompt_tokens"]
        and s_completion == tap["completion_tokens"]
    )
    return _check(ok, "A5-session-tokens-match-tap",
                  f"session prompt/completion {s_prompt}/{s_completion} over "
                  f"{_step_count(session)} step(s); tap server_terminal "
                  f"{tap['prompt_tokens']}/{tap['completion_tokens']} over {tap['calls']} "
                  f"call(s), {tap['calls'] - tap['measured_calls']} without a server prompt count")


def resolve_token_counts(session: dict[str, Any],
                         tap: dict[str, Any] | None) -> dict[str, Any]:
    """The prompt-token count the belief capture records, with its source.

    The tap's server_terminal sum is authoritative when it measured every call
    of the session; otherwise the session's own count is used and labelled so.
    Cache reuse is not in the tap, so cached_prompt_tokens stays the session's.
    """
    s_prompt, s_cached = step_token_counts(session)
    out: dict[str, Any] = {
        "session_prompt_tokens": s_prompt,
        "session_completion_tokens": step_completion_tokens(session),
        "cached_prompt_tokens": s_cached,
        "cached_prompt_tokens_source": "opencode_session",
        "tap": tap,
    }
    if tap and tap["calls"] >= 1 and tap["measured_calls"] == tap["calls"]:
        out["input_tokens"] = tap["prompt_tokens"]
        out["input_tokens_source"] = "tap_server_terminal"
    else:
        out["input_tokens"] = s_prompt
        out["input_tokens_source"] = "opencode_session"
    return out


def capture_beliefs(args, evid: Path, session: dict[str, Any], session_id: str,
                    start: float, end: float, passed: bool,
                    tokens: dict[str, Any] | None = None) -> dict[str, Any]:
    """SC86 hook: write the run sidecar and call the belief writer (P0.5).

    One task, one trial. The attempt passes when the fixture test passes.
    """
    if args.no_belief_capture:
        return {"status": "skipped", "reason": "--no-belief-capture"}
    missing = [flag for flag, value in (
        ("--harness-card-version", args.harness_card_version),
        ("--model-role", args.model_role),
        ("--build-info", args.build_info),
        ("--enable-thinking", args.enable_thinking),
    ) if value in (None, "")]
    if missing:
        return {"status": "refused", "reason": "serving identity not recorded: " + ", ".join(missing)}
    sys.path.insert(0, str(ROOT / "scripts" / "vidya" / "adapters"))
    import opencode_shell_run_capture as cap  # noqa: E402

    if tokens is None:
        tokens = resolve_token_counts(session, None)
    prompt_tokens = tokens["input_tokens"]
    cached_tokens = tokens["cached_prompt_tokens"]
    records = evid / "attempts.jsonl"
    records.write_text(json.dumps({
        "task": "calc-add-fix", "trial": 0, "session_id": session_id,
        "passed": passed, "input_tokens": prompt_tokens, "cached_prompt_tokens": cached_tokens,
        "input_tokens_source": tokens["input_tokens_source"],
        "cached_prompt_tokens_source": tokens["cached_prompt_tokens_source"],
    }, sort_keys=True) + "\n")
    run = {
        "schema": cap.RUN_SCHEMA,
        "run_id": f"hs4-p04-{session_id}",
        "started_at": _utc(start),
        "finished_at": _utc(end),
        "arm_role": "BASELINE",
        "harness": {"name": cap.HARNESS_NAME, "pin": AUDITED_TIP},
        "plugin": {"name": "@epyc/opencode-plugin", "sha256": plugin_sha256()},
        "config_sha256": cap.file_sha256(evid / "opencode.jsonc"),
        "harness_card_version": args.harness_card_version,
        "request_keys": {"x_memory": "off", "x_tool_mode": "client"},
        "serving": {
            "endpoint": args.endpoint,
            "model_role": args.model_role,
            "build_info": args.build_info,
            "enable_thinking": args.enable_thinking == "true",
        },
        "task_suite": {"name": "hs4-p04-calc-fixture", "fingerprint": task_suite_fingerprint()},
        "counts": {
            "tasks": 1, "trials_per_task": 1, "attempts": 1,
            "passed_attempts": int(passed),
            "input_tokens": prompt_tokens, "cached_prompt_tokens": cached_tokens,
        },
        "records_file": records.name,
    }
    (evid / cap.RUN_SIDECAR_NAME).write_text(json.dumps(run, indent=2, sort_keys=True) + "\n")
    try:
        out = cap.write_belief_measurements(
            evid, producer="scripts/harness/hs4_p04_acceptance.py", run=run,
            emitted_at=args.emitted_at)
    except cap.CaptureError as exc:
        return {"status": "refused", "reason": str(exc)}
    return {"status": "written", "path": str(out)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("plan")
    p.add_argument("--opencode-bin")
    p = sub.add_parser("prepare")
    p.add_argument("--out", required=True)
    p.add_argument("--enable-mcp", action="store_true",
                   help="enable the orchestrator MCP server so the session_id stamp is exercised")
    p = sub.add_parser("verify")
    p.add_argument("--evidence", required=True)
    p.add_argument("--repo")
    p.add_argument("--user-id", required=True)
    p.add_argument("--tap-events", default=str(DEFAULT_TAP_EVENTS))
    p.add_argument("--slack-s", type=float, default=5.0)
    p.add_argument("--strict-window", action="store_true")
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
    return {"plan": cmd_plan, "prepare": cmd_prepare, "verify": cmd_verify}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
