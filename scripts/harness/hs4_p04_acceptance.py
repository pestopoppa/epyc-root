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
import os
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
python3 {script} check-catalog --evidence "$EVID" \\
  --model-role "$EPYC_MODEL_ROLE" --build-info "$EPYC_BUILD_INFO"
opencode --version > "$EVID/opencode-version.txt"
date +%s.%N > "$EVID/window-start.txt"
# No --auto: permission asks are auto-rejected. edit and bash are allowed by
# OpenCode's defaults inside the project directory. Keep the prompt out of argv:
# OpenCode re-quotes positional messages containing spaces (audit pitfall 1).
RUN_RC=0
(cd "$REPO" && opencode run --format json --title hs4-p04-acceptance) \\
  < "$EVID/prompt.txt" \\
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


def load_mcp_launch_spec(path: Path) -> dict[str, Any]:
    """Validate a row-owned launch declaration without importing/starting its server.

    The file map pins declared inputs, not the complete runtime dependency closure
    or a running process. Live catalog and serving custody are still row duties.
    """
    spec = json.loads(path.read_bytes())
    if not isinstance(spec, dict) or set(spec) != {'command', 'cwd', 'files'}:
        raise ValueError('MCP launch spec requires exactly command, cwd and files')
    command, cwd, files = spec['command'], spec['cwd'], spec['files']
    if not isinstance(command, list) or not command or any(
            not isinstance(v, str) or not v or '\x00' in v
            or any(marker in v for marker in ('{env:', '{file:')) for v in command):
        raise ValueError('MCP command must be a nonempty literal argv list')
    if not isinstance(cwd, str) or any(marker in cwd for marker in ('{env:', '{file:')) \
            or not Path(cwd).is_absolute() \
            or not Path(cwd).is_dir():
        raise ValueError('MCP cwd must be an existing absolute directory')
    executable = Path(command[0])
    if not executable.is_absolute() or not executable.is_file() \
            or not os.access(executable, os.X_OK):
        raise ValueError('MCP executable must be an existing absolute executable file')
    if not isinstance(files, dict) or not files or command[0] not in files:
        raise ValueError('MCP files must pin the executable and declared source inputs')
    for name, digest in files.items():
        if not isinstance(name, str) or not Path(name).is_absolute() \
                or not isinstance(digest, str) or len(digest) != 64 \
                or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('MCP file pins require absolute paths and SHA-256 digests')
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'MCP launch input drift: {name}')
    return spec


def render_mcp_launch(config: str, spec: dict[str, Any]) -> str:
    """Replace only the existing orchestrator MCP command and cwd."""
    defaults = {
        'command': '["{env:EPYC_ORCHESTRATOR_MCP_PYTHON}", "-m", "src.mcp_server"]',
        'cwd': '"{env:EPYC_ORCHESTRATOR_REPO}"',
    }
    for key, value in defaults.items():
        needle = f'"{key}": {value}'
        if config.count(needle) != 1:
            raise ValueError(f'expected exactly one default MCP {key}')
        config = config.replace(needle, f'"{key}": {json.dumps(spec[key])}')
    return config


def cmd_prepare(args: argparse.Namespace) -> int:
    config = render_config(TEMPLATE.read_text(), args.enable_mcp)
    launch_path = getattr(args, 'mcp_launch_spec', None)
    if launch_path is not None:
        if not args.enable_mcp or not args.catalog_manifest:
            raise ValueError('--mcp-launch-spec requires --enable-mcp and catalog binding')
        config = render_mcp_launch(config, load_mcp_launch_spec(Path(launch_path)))
    binding = prepare_catalog_binding(args, config)
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
    (evidence / "opencode.jsonc").write_text(config)
    binding_digest = None
    if binding is not None:
        raw = json.dumps(binding, sort_keys=True, indent=2) + "\n"
        (evidence / "catalog-binding.json").write_text(raw)
        binding_digest = hashlib.sha256(raw.encode()).hexdigest()
    run_sh = evidence / "run.sh"
    run_sh.write_text(
        RUN_SH.format(
            evidence=_sh(evidence),
            repo=_sh(repo),
            root=_sh(ROOT),
            env_file=_sh(ENV_FILE),
            lint=_sh(PLUGIN_DIR / "scripts" / "lint-config.ts"),
            script=_sh(Path(__file__).resolve()),
        )
    )
    run_sh.chmod(0o755)
    (evidence / "prompt.txt").write_text(TASK_PROMPT, encoding="utf-8")
    (evidence / "prepared.json").write_text(
        json.dumps(
            {
                "prepared_at": time.time(),
                "pinned_opencode": PINNED_VERSION,
                "mcp_enabled": args.enable_mcp,
                "orchestrator_commits": ORCHESTRATOR_COMMITS,
                "prompt": TASK_PROMPT,
                "catalog_binding_sha256": binding_digest,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"prepared {out}\nnext (SENDS INFERENCE): bash {run_sh}")
    return 0


def _sh(value: object) -> str:
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


def prepare_catalog_binding(args: argparse.Namespace, config: str) -> dict[str, Any] | None:
    """Bind a declared catalog snapshot before execution, never on historical runs.

    Model/server are the exact --model-role/--build-info declarations. Snapshot
    bytes must hash to the manifest catalog identity; this is not proof that a
    live tools/list actually served them. That custody remains a row requirement.
    """
    fields = (args.catalog_manifest, args.catalog_arm, args.catalog_trial, args.catalog_snapshot)
    if all(value is None for value in fields):
        return None
    if any(value is None for value in fields):
        raise ValueError('all four --catalog-* options are required together')
    manifest_path = Path(args.catalog_manifest).resolve()
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    identity, catalogs = manifest['identity'], manifest['catalogs']
    if not all(isinstance(identity.get(k), str) and identity[k].strip()
               for k in ('model', 'server', 'plugin', 'base_catalog')):
        raise ValueError('missing shared catalog identity')
    if not all(isinstance(catalogs.get(k), str) and catalogs[k].strip()
               for k in ('baseline', 'candidate')) or catalogs['baseline'] == catalogs['candidate']:
        raise ValueError('distinct arm catalogs required')
    if identity['base_catalog'] != catalogs['baseline'] or identity['plugin'] != plugin_sha256():
        raise ValueError('baseline catalog or current plugin identity mismatch')
    tasks = [t for t in manifest['tasks'] if t['id'] == 'calc-add-fix']
    if len(tasks) != 1 or tasks[0].get('previously_passing') is not True \
            or tasks[0].get('fixture') != task_suite_fingerprint():
        raise ValueError('manifest must freeze the previously passing calc-add-fix fixture')
    snapshot = Path(args.catalog_snapshot).resolve()
    catalog = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    if catalog != catalogs[args.catalog_arm]:
        raise ValueError('catalog snapshot digest mismatch')
    binding = {
        'schema': 'hs4-p6-binding/v1',
        'comparison': {'task': 'calc-add-fix', 'arm': args.catalog_arm,
                       'trial': args.catalog_trial, 'fixture': task_suite_fingerprint(),
                       'identity': identity, 'catalog': catalog},
        'manifest_path': str(manifest_path),
        'manifest_sha256': hashlib.sha256(manifest_raw).hexdigest(),
        'catalog_snapshot_path': str(snapshot),
        'config_sha256': hashlib.sha256(config.encode()).hexdigest(),
        'prompt_sha256': hashlib.sha256(TASK_PROMPT.encode()).hexdigest(),
        'producer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'identity_basis': 'prospective declarations; live catalog/model/build custody required separately',
    }
    launch_path = getattr(args, 'mcp_launch_spec', None)
    if launch_path is not None:
        path = Path(launch_path).resolve()
        launch_raw = path.read_bytes()
        spec = load_mcp_launch_spec(path)
        if config != render_mcp_launch(render_config(TEMPLATE.read_text(), True), spec):
            raise ValueError('MCP launch configuration drift during preparation')
        # The original manifest chooses each arm's launch input prospectively.
        if manifest.get('mcp_launch_specs', {}).get(args.catalog_arm) \
                != hashlib.sha256(launch_raw).hexdigest():
            raise ValueError('manifest MCP launch spec digest mismatch')
        binding['mcp_launch'] = {
            'path': str(path), 'sha256': hashlib.sha256(launch_raw).hexdigest(),
            'spec': spec,
        }
    return binding


def load_catalog_binding(evid: Path, model_role: str, build_info: str) -> dict[str, Any] | None:
    path = evid / 'catalog-binding.json'
    prepared_path = evid / 'prepared.json'
    prepared = json.loads(prepared_path.read_text()) if prepared_path.is_file() else {}
    expected = prepared.get('catalog_binding_sha256')
    if expected is None:
        if path.exists():
            raise ValueError('refusing retrospective catalog binding')
        return None
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('catalog binding drift')
    binding = json.loads(raw)
    comparison = binding['comparison']
    pins = ((evid / 'opencode.jsonc', binding['config_sha256']),
            (evid / 'prompt.txt', binding['prompt_sha256']),
            (Path(binding['manifest_path']), binding['manifest_sha256']),
            (Path(binding['catalog_snapshot_path']), comparison['catalog']),
            (Path(__file__), binding['producer_sha256']))
    if any(hashlib.sha256(path.read_bytes()).hexdigest() != digest for path, digest in pins):
        raise ValueError('catalog input drift')
    if 'mcp_launch' in binding:
        launch = binding['mcp_launch']
        path = Path(launch['path'])
        if hashlib.sha256(path.read_bytes()).hexdigest() != launch['sha256'] \
                or load_mcp_launch_spec(path) != launch['spec']:
            raise ValueError('MCP launch declaration drift')
    identity = comparison['identity']
    if identity['plugin'] != plugin_sha256() or comparison['fixture'] != task_suite_fingerprint():
        raise ValueError('catalog producer/fixture drift')
    if identity['model'] != model_role or identity['server'] != build_info:
        raise ValueError('catalog serving declaration mismatch')
    return binding


def cmd_check_catalog(args: argparse.Namespace) -> int:
    try:
        evid = Path(args.evidence)
        binding = load_catalog_binding(evid, args.model_role, args.build_info)
        if binding and any((evid / name).exists() for name in
                           ('window-start.txt', 'events.jsonl', 'catalog-record.json')):
            raise ValueError('refusing to rerun an exposed catalog trial')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'catalog binding refused: {exc}', file=sys.stderr)
        return 2
    return 0


def catalog_usage_complete(session: dict[str, Any]) -> bool:
    """P6 cost requires explicit nonnegative step usage, including cache usage."""
    steps = [p for msg in session.get('messages', []) for p in msg.get('parts', [])
             if p.get('type') == 'step-finish']
    if not steps:
        return False
    for step in steps:
        tokens = step.get('tokens')
        if not isinstance(tokens, dict) or not isinstance(tokens.get('cache'), dict):
            return False
        counts = [tokens.get(k) for k in ('input', 'output', 'reasoning')]
        counts += [tokens['cache'].get(k) for k in ('read', 'write')]
        if any(type(n) is not int or n < 0 for n in counts):
            return False
    return True


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
    try:
        binding = load_catalog_binding(evid, args.model_role, args.build_info)
        if binding and (evid / 'catalog-record.json').exists():
            raise ValueError('catalog trial already finalized')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'catalog binding refused: {exc}', file=sys.stderr)
        return 2
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
    capture = capture_beliefs(
        args, evid, session, session_id, start, end, fixture_ok, tokens,
        arm_role=binding['comparison']['arm'].upper() if binding else 'BASELINE',
        record_extra={'catalog_comparison': binding['comparison']} if binding else None,
    )
    checks.append(_check(capture["status"] in {"written", "skipped"}, "sc86-belief-capture",
                         f"{capture['status']}: {capture.get('path') or capture.get('reason')}"))
    if binding:
        checks.append(_check(
            catalog_usage_complete(session) and exit_file.is_file() and version.is_file(),
            'catalog-native-records-complete',
            'P6 requires explicit step usage, exit status and shell version records',
        ))
        behavioral = {'A1-read-edit-bash-loop', 'A1-fixture-test-passes', 'A3-no-compaction-or-subtask'}
        uncertain = any(not c['ok'] for c in checks if c['check'] not in behavioral)
        result = {
            **binding['comparison'],
            'outcome': 'infra_error' if uncertain else 'pass' if all(c['ok'] for c in checks) else 'fail',
            'tokens': None if uncertain else tokens['input_tokens'] + tokens['session_completion_tokens'],
            'token_basis': 'prompt plus completion, A5 parity required',
            'session_id': session_id, 'window': [start, end],
            'binding_sha256': json.loads((evid / 'prepared.json').read_text())['catalog_binding_sha256'],
            'identity_basis': binding['identity_basis'],
        }
        with (evid / 'catalog-record.json').open('x') as fh:
            fh.write(json.dumps(result, sort_keys=True, indent=2) + '\n')
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
                    tokens: dict[str, Any] | None = None, *,
                    task: str = "calc-add-fix",
                    run_id: str | None = None,
                    suite: dict[str, str] | None = None,
                    producer: str = "scripts/harness/hs4_p04_acceptance.py",
                    record_extra: dict[str, Any] | None = None,
                    arm_role: str = "BASELINE") -> dict[str, Any]:
    """SC86 hook: write the run sidecar and call the belief writer (P0.5).

    One task, one trial. The attempt passes when the fixture test passes.
    The keyword arguments let a sibling acceptance runner (HS-19a) reuse this
    hook unchanged; their defaults are the P0.4 values.
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
        "task": task, "trial": 0, "session_id": session_id,
        "passed": passed, "input_tokens": prompt_tokens, "cached_prompt_tokens": cached_tokens,
        "input_tokens_source": tokens["input_tokens_source"],
        "cached_prompt_tokens_source": tokens["cached_prompt_tokens_source"],
        **(record_extra or {}),
    }, sort_keys=True) + "\n")
    run = {
        "schema": cap.RUN_SCHEMA,
        "run_id": run_id or f"hs4-p04-{session_id}",
        "started_at": _utc(start),
        "finished_at": _utc(end),
        "arm_role": arm_role,
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
        "task_suite": suite or {"name": "hs4-p04-calc-fixture",
                                "fingerprint": task_suite_fingerprint()},
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
            evid, producer=producer, run=run, emitted_at=args.emitted_at)
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
    p.add_argument('--catalog-manifest', help='prospective frozen P6 comparison manifest')
    p.add_argument('--catalog-arm', choices=['baseline', 'candidate'])
    p.add_argument('--catalog-trial', type=int, choices=[1, 2])
    p.add_argument('--catalog-snapshot', help='catalog bytes whose SHA-256 is the arm identity')
    p.add_argument('--mcp-launch-spec', help='prospective row-owned MCP argv/cwd/file pins JSON')
    p = sub.add_parser('check-catalog')
    p.add_argument('--evidence', required=True)
    p.add_argument('--model-role', required=True)
    p.add_argument('--build-info', required=True)
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
    return {"plan": cmd_plan, "prepare": cmd_prepare, "verify": cmd_verify,
            'check-catalog': cmd_check_catalog}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
