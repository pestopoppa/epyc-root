#!/usr/bin/env python3
"""Measurement package B: does the 27B call OpenCode's `task` tool? MODEL vs SETUP.

Operator-approved 2026-09-27. HS-19a's live run showed FRONTDOOR (Qwen3.6-35B-A3B) delegating
through `task`; DS41-C20c showed the 27B on :8083, offered `task` in the opencode seat, never
delegating (n=1). This probe separates the served MODEL from the SETUP around it.

Design: the HS-19a harness (subagents profile, one logical model `epyc-orchestrator/orchestrator`,
same plugin, same OpenCode pin). The PARENT agent carries an evaluation pin in its agent
`options` (x_force_role, the one legitimate use); OpenCode merges agent options into the request
body (session/llm/request.ts:91), so only the parent's calls carry it. The CHILD (the sub-agent
`task` spawns) has no pin: the orchestrator selects its model. Because every arm uses the same
logical model id, OpenCode sends byte-identical system prompt, tool list and `task` description in
every arm; only the server behind the orchestrator changes.

Arms (the parent's pin):
  fd           no pin -> frontdoor (Qwen3.6-35B-A3B), registry enable_thinking=false
  27b-nothink  x_force_role=coder_escalation  -> :8083 Qwen3.8-27B, enable_thinking=false
  27b-think    x_force_role=architect_general -> :8083 Qwen3.8-27B, enable_thinking=true (medium)
Variants (the prompt/agent shape):
  hs19a  HS-19a's fixture and imperative prompt ("Use the task tool exactly once ..."), agent build
  ds41   DS41-C20c's seat shape: a primary `planner` agent, the seat's instructions (fan-out
         guidance, discretionary), a hidden `scout` sub-agent with the seat's description, and
         a two-question prompt that never names the task tool.

Only the run.sh that `prepare` writes sends inference. This script never does.

  plan        print the probe checklist and the local preflight
  prepare     one run dir: fixture repo, pinned config, pin-stripped lint copy, prompt, run.sh
  prepare-all every run of the pre-registered ABA schedule under one root + SCHEDULE.txt
  check-config (run.sh, before any inference) the pin is exactly where probe.json declares it
  verify      read the evidence, record the pin and the child's lack of one, classify the outcome
  summarize   per-cell counts over every verdict under a root + the pre-registered decision rule

Validity (verdict "valid"; a run that is not valid is re-run, never counted):
  C0 config pin: exactly the declared x_force_role on agent.<primary>.options (none for fd), no
     other override key anywhere, no sub-agent carries an x_* option or a model;
  C1 the pin-stripped copy equals the config minus the pin and passes the subagents lint;
  C2 parent calls: pinned arms are served on the pinned port (8083) with the declared pin (tap
     request_keys when the API records overrides, orchestrator 83b18f03; else the served port is
     the basis, named in the detail); fd parent calls carry no override and are not on 8083;
  C3 child calls carry no override key and are not served on the pinned port (vacuous, and said
     so, when the parent never delegated);
  C4 every assistant message in every export is the one logical model;
  C5 OpenCode is the pinned version.
Outcome (the dependent variable, never a validity gate):
  delegated         >= 1 completed task part with a linked child export
  delegated_failed  task part(s), none completed
  unparsed_attempt  no task part, but tool-call markup or subagent_type in the parent's text:
                    the model tried and the :8083 chat template / tool-call parser lost it
  self_served       no task part, other tools used
  no_tool           answered (or refused) without any tool
  run_error         no parent export
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hs19a_acceptance as h  # noqa: E402

p04 = h.p04
ROOT = h.ROOT
TEMPLATE = h.TEMPLATE
ENV_FILE = h.ENV_FILE
LINT = h.LINT
PINNED_VERSION = h.PINNED_VERSION
DEFAULT_TAP_EVENTS = h.DEFAULT_TAP_EVENTS
PROVIDER_ID, MODEL_ID = h.PROVIDER_ID, h.MODEL_ID

SCHEMA = "task-delegation-probe/v1"
FORCE_FIELD = "x_force_role"
OVERRIDE_KEYS = ("x_force_role", "x_force_model", "x_orchestrator_role")
PINNED_PORT = 8083
RUN_TIMEOUT_S = 900
SEEDS = (101, 202, 303)

# The parent's pin per arm. enable_thinking is the registry's chat_template_kwargs for that role
# (src/registry chat_template_kwargs_for_role, read 2026-09-27): frontdoor false,
# coder_escalation false, architect_general true (+ reasoning_effort medium).
ARMS: dict[str, dict[str, Any]] = {
    "fd": {"force_role": None, "model_role": "frontdoor", "enable_thinking": False,
           "served": "frontdoor Qwen3.6-35B-A3B (CPU), unpinned"},
    "27b-nothink": {"force_role": "coder_escalation", "model_role": "coder_escalation",
                    "enable_thinking": False,
                    "served": ":8083 Qwen3.8-27B-Q8_0 (MI210) via its coder_escalation alias"},
    "27b-think": {"force_role": "architect_general", "model_role": "architect_general",
                  "enable_thinking": True,
                  "served": ":8083 Qwen3.8-27B-Q8_0 (MI210) as architect_general"},
}

CODENAME = h.CODENAME
MAX_RETRIES = "13"
DS41_EXTRA_FILES = {"app/limits.py": '"""Client limits."""\n\nMAX_RETRIES = 13\nTIMEOUT_S = 30\n'}

DS41_PROMPT = (
    "Answer two independent questions about this repository. (1) Which file sets "
    "RELEASE_CODENAME, and what is its value? (2) Which file sets MAX_RETRIES, and what is its "
    "value? Do not modify any file. End your reply with exactly these two lines:\n"
    "CODENAME=<value>\nMAX_RETRIES=<value>"
)

# /mnt/raid0/llm/tmp/ak-seat-ab/actor-opencode-planner.instructions.md (the DS41-C20c bounded
# seat), adapted: the MCP-tool items (autokernel-tools_*, profiles) are dropped because this
# fixture has no MCP server; "autokernel-scout" -> "scout"; the reply is two lines, not JSON.
# The "Parallel investigation" block is otherwise verbatim.
DS41_INSTRUCTIONS = """You are the PLANNER for this repository worktree. You investigate the code and answer the questions you are given; you cannot edit files.

Tool discipline -- your context is one ~98k-token slot and every byte a tool returns stays in it:
1. Locate before you read: grep or glob with a NARROW pattern, then read only the lines you need.
2. Never read more than ~200 lines at once and never read a whole file. If you use the built-in read tool, always pass offset and limit.
3. bash is for short, bounded commands only (e.g. `git log --oneline -n 20`, `git diff --stat`); bound every command's output.
4. Do not re-read what you have already read; keep notes in your reasoning.
5. Stop investigating as soon as you can answer. Print the requested answer lines as the LAST thing in your reply, with nothing after them.

Parallel investigation -- keep your own context small:
- When questions are independent (e.g. one per candidate hotspot or file), delegate them with the `task` tool, subagent_type "scout", issuing up to 2 task calls in the SAME message so they run concurrently. The server has 2 slots: never more than 2 subagents at once.
- Give each scout one precise question and ask for a summary of at most ~15 lines with file:line references.
- Work from the summaries; do not repeat a scout's reads yourself.

If you are a scout subagent: ignore the role and fan-out text above; answer only your one question, read-only, in a summary of at most ~15 lines with file:line references -- no file dumps.
"""
# Verbatim from the seat config (actor-opencode-planner.json, agent autokernel-scout).
SCOUT_DESCRIPTION = ("Read-only investigator for ONE independent question about the lane's code "
                     "or profiles; returns a <=15-line summary.")

VARIANTS: dict[str, dict[str, Any]] = {
    "hs19a": {"primary": "build", "subagents": ["general"],
              "files": dict(h.FIXTURE_FILES), "prompt": h.TASK_PROMPT, "instructions": None,
              "answers": {"CODENAME": CODENAME}},
    "ds41": {"primary": "planner", "subagents": ["scout"],
             "files": {**h.FIXTURE_FILES, **DS41_EXTRA_FILES}, "prompt": DS41_PROMPT,
             "instructions": DS41_INSTRUCTIONS,
             "answers": {"CODENAME": CODENAME, "MAX_RETRIES": MAX_RETRIES}},
}

_check = p04._check
_UNPARSED = re.compile(r"<tool_call>|<function=|\"name\"\s*:\s*\"task\"|subagent_type")


# ---------------------------------------------------------------- JSONC


def strip_jsonc(text: str) -> str:
    """Drop // and /* */ comments and trailing commas, never inside a string."""
    out: list[str] = []
    i, n = 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif c == ",":
            j = _skip_blank(text, i + 1)
            if j < n and text[j] in "}]":
                i += 1  # trailing comma
            else:
                out.append(c)
                i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _skip_blank(text: str, j: int) -> int:
    """Index of the next character that is neither whitespace nor inside a comment."""
    n = len(text)
    while j < n:
        if text[j] in " \t\r\n":
            j += 1
        elif text.startswith("//", j):
            k = text.find("\n", j)
            j = n if k < 0 else k
        elif text.startswith("/*", j):
            k = text.find("*/", j + 2)
            j = n if k < 0 else k + 2
        else:
            break
    return j


def load_jsonc(path: Path) -> dict[str, Any]:
    return json.loads(strip_jsonc(path.read_text()))


# ---------------------------------------------------------------- config


def build_config(variant: str, arm: str, seed: int, instructions_path: Path | None) -> dict[str, Any]:
    """The run's OpenCode config: the HS-19a subagents template plus this variant's agents.

    Every agent gets the run's `seed` in its options (a plain body field the orchestrator forwards;
    without it every call decodes with the backend's fixed seed 42, so replicates would repeat one
    draw). Only the PRIMARY agent gets the pin.
    """
    v, a = VARIANTS[variant], ARMS[arm]
    cfg = load_jsonc(TEMPLATE)
    agents = cfg.setdefault("agent", {})
    if variant == "hs19a":
        agents.setdefault("general", {})["options"] = {"seed": seed}
        agents["build"] = {"options": {"seed": seed}}
    else:
        agents["general"] = {"disable": True}
        agents["explore"] = {"disable": True}
        agents["planner"] = {
            "description": "planner seat (step-capped)", "mode": "primary", "steps": 60,
            "permission": {"edit": "deny", "task": {"*": "deny", "scout": "allow"}},
            "options": {"seed": seed},
        }
        agents["scout"] = {
            "description": SCOUT_DESCRIPTION, "mode": "subagent", "hidden": True, "steps": 20,
            "permission": {"edit": "deny", "task": "deny"}, "options": {"seed": seed},
        }
        cfg["permission"]["task"] = {"*": "deny", "scout": "allow"}
        cfg["instructions"] = [str(instructions_path)]
    if a["force_role"]:
        agents[v["primary"]]["options"][FORCE_FIELD] = a["force_role"]
    return cfg


def strip_pin(cfg: dict[str, Any], primary: str) -> dict[str, Any]:
    out = copy.deepcopy(cfg)
    ((out.get("agent") or {}).get(primary) or {}).get("options", {}).pop(FORCE_FIELD, None)
    return out


def _override_paths(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for k, v in value.items():
            here = f"{path}.{k}" if path else k
            if k in OVERRIDE_KEYS or k.startswith("x_force_"):
                found.append(here)
            found += _override_paths(v, here)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            found += _override_paths(v, f"{path}[{i}]")
    return found


def check_config_pin(cfg: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    """C0: the pin is exactly where probe.json declares it; the sub-agents carry none."""
    primary, role = probe["primary"], probe["force_role"]
    expected = [f"agent.{primary}.options.{FORCE_FIELD}"] if role else []
    found = _override_paths(cfg)
    problems = []
    if sorted(found) != expected:
        problems.append(f"override keys at {found or 'none'}, expected {expected or 'none'}")
    agents = cfg.get("agent") or {}
    if role and ((agents.get(primary) or {}).get("options") or {}).get(FORCE_FIELD) != role:
        problems.append(f"agent.{primary}.options.{FORCE_FIELD} is not {role!r}")
    for name in probe["subagents"]:
        a = agents.get(name) or {}
        if "model" in a:
            problems.append(f"sub-agent {name} carries a model")
        x = [k for k in (a.get("options") or {}) if k.startswith("x_")]
        if x:
            problems.append(f"sub-agent {name} carries x_* options {x}")
    for name, a in agents.items():
        if isinstance(a, dict) and "model" in a:
            problems.append(f"agent {name} carries a model (the pin is x_force_role, never a model)")
    return _check(not problems, "C0-config-pin-declared",
                  "; ".join(sorted(set(problems))) if problems else
                  (f"pin {FORCE_FIELD}={role!r} on agent {primary!r} only" if role else
                   "no pin anywhere (unpinned arm)") + f"; sub-agents {probe['subagents']} unpinned")


def lint_stripped(evid: Path, probe: dict[str, Any]) -> dict[str, Any]:
    """C1: the lint copy is the config minus the pin, and it passes the subagents lint."""
    cfg = load_jsonc(evid / "opencode.jsonc")
    lint_copy = load_jsonc(evid / "opencode.lint.jsonc")
    same = lint_copy == strip_pin(cfg, probe["primary"])
    lint = h.lint_config(evid / "opencode.lint.jsonc")
    return _check(same and lint["ok"], "C1-config-lint-pin-stripped",
                  ("lint copy == config minus the pin" if same else
                   "lint copy differs from the config minus the pin") + f"; lint: {lint['detail']}")


# ---------------------------------------------------------------- prepare


RUN_SH = """#!/bin/bash
# Task-delegation probe (measurement package B) run {run_id}: variant {variant}, arm {arm},
# seed {seed}. SENDS INFERENCE. Start it only in the window the main session cleared.
set -euo pipefail
EVID={evidence}
REPO={repo}
export EPYC_ROOT={root}
export EPYC_USER_ID="${{EPYC_USER_ID:?set EPYC_USER_ID before running}}"
: "${{EPYC_HARNESS_CARD_VERSION:?set EPYC_HARNESS_CARD_VERSION}}"
: "${{EPYC_BUILD_INFO:?set EPYC_BUILD_INFO (llama-server --version of the parent server)}}"
cat >&2 <<'PRECONDITION'
########################################################################################
# PRECONDITIONS (the main session confirms; this script cannot):
#  - GPU window on the MI210 / :8083 agreed with workspace-76 (no overlap with its GPU work);
#  - :8083 serves the production Qwen3.8-27B-Q8_0 (architect_general + coder_escalation alias);
#  - frontdoor serves Qwen3.6-35B-A3B (fd parents and EVERY child run there, on CPU): no CPU
#    measurement window may be open on the frontdoor's cores;
#  - orchestrator API running with ORCHESTRATOR_FEATURE_V1_SUBAGENT_LINK=1;
#  - recommended: orchestrator 83b18f03 merged and the API reloaded, so the tap records the pin
#    itself (otherwise C2/C3 fall back to the served port, and the verdict says so).
########################################################################################
PRECONDITION
# shellcheck disable=SC1091
source {env_file}
export OPENCODE_CONFIG="$EVID/opencode.jsonc"
node {lint} --profile subagents "$EVID/opencode.lint.jsonc" {env_file}
python3 {script} check-config --evidence "$EVID"
opencode --version > "$EVID/opencode-version.txt"
# Serving identity snapshots (GETs, no inference). A failed GET is recorded, never fatal.
curl -s -m 10 http://127.0.0.1:{pinned_port}/props > "$EVID/props-{pinned_port}.json" || true
curl -s -m 10 http://127.0.0.1:8070/props > "$EVID/props-8070.json" || true
curl -s -m 10 "$EPYC_ORCHESTRATOR_BASE_URL/models" > "$EVID/v1-models.json" || true
for AG in {agents}; do
  (cd "$REPO" && opencode debug agent "$AG") > "$EVID/agent-$AG.json" 2>> "$EVID/opencode-stderr.log" || true
done
date +%s.%N > "$EVID/window-start.txt"
# No --auto: permission asks are auto-rejected. The prompt goes on STDIN (audit pitfall 1);
# stdout/stderr go to FILES, never pipes (pitfall 2). timeout bounds a runaway run (rc 124).
RUN_RC=0
(cd "$REPO" && timeout --kill-after=30 {timeout_s} opencode run --format json --title {title}{agent_flag}) \\
  < "$EVID/prompt.txt" > "$EVID/events.jsonl" 2>> "$EVID/opencode-stderr.log" || RUN_RC=$?
date +%s.%N > "$EVID/window-end.txt"
echo "$RUN_RC" > "$EVID/opencode-exit.txt"
PARENT=$(python3 {hs19a} parent-id --events "$EVID/events.jsonl" || true)
echo "$PARENT" > "$EVID/parent-session-id.txt"
: > "$EVID/child-session-ids.txt"
if [ -n "$PARENT" ]; then
  (cd "$REPO" && opencode export "$PARENT") > "$EVID/parent-session.json"
  python3 {hs19a} child-ids --session "$EVID/parent-session.json" > "$EVID/child-session-ids.txt"
  while IFS= read -r CID; do
    [ -n "$CID" ] || continue
    (cd "$REPO" && opencode export "$CID") > "$EVID/child-$CID.json"
  done < "$EVID/child-session-ids.txt"
fi
python3 {script} verify --evidence "$EVID" --user-id "$EPYC_USER_ID" \\
  --harness-card-version "$EPYC_HARNESS_CARD_VERSION" --build-info "$EPYC_BUILD_INFO" \\
  --endpoint "$EPYC_ORCHESTRATOR_BASE_URL"
"""


def suite_fingerprint(variant: str) -> str:
    v = VARIANTS[variant]
    parts = [f"{k}\0{t}".encode() for k, t in sorted(v["files"].items())]
    parts += [v["prompt"].encode(), (v["instructions"] or "").encode()]
    return p04._sha256_bytes(parts)


def prepare_run(out: Path, variant: str, arm: str, seed: int, run_id: str,
                pinned_port: int = PINNED_PORT, timeout_s: int = RUN_TIMEOUT_S) -> Path:
    out = out.resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"refusing: {out} exists and is not empty")
    v, a = VARIANTS[variant], ARMS[arm]
    repo, evid = out / "repo", out / "evidence"
    repo.mkdir(parents=True)
    evid.mkdir()
    for name, text in v["files"].items():
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    git = ["git", "-C", str(repo)]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", *v["files"]], check=True)
    subprocess.run([*git, "-c", "user.name=probe", "-c", "user.email=probe@localhost",
                    "commit", "-q", "-m", "fixture"], check=True)
    instructions = None
    if v["instructions"]:
        instructions = evid / "instructions.md"
        instructions.write_text(v["instructions"])
    cfg = build_config(variant, arm, seed, instructions)
    header = (f"// task-delegation probe {run_id}: variant {variant}, arm {arm}, seed {seed}.\n"
              f"// Generated from {TEMPLATE.name}; the pin (if any) is on agent.{v['primary']} only.\n")
    (evid / "opencode.jsonc").write_text(header + json.dumps(cfg, indent=2) + "\n")
    (evid / "opencode.lint.jsonc").write_text(
        "// The run config minus the evaluation pin: what the subagents lint checks.\n"
        + json.dumps(strip_pin(cfg, v["primary"]), indent=2) + "\n")
    (evid / "prompt.txt").write_text(v["prompt"] + "\n")
    probe = {
        "schema": SCHEMA, "run_id": run_id, "variant": variant, "arm": arm, "seed": seed,
        "force_field": FORCE_FIELD, "force_role": a["force_role"], "model_role": a["model_role"],
        "enable_thinking": a["enable_thinking"], "served": a["served"],
        "primary": v["primary"], "subagents": v["subagents"], "answers": v["answers"],
        "pinned_port": pinned_port, "timeout_s": timeout_s, "prepared_at": time.time(),
        "pinned_opencode": PINNED_VERSION, "template": str(TEMPLATE),
        "suite_fingerprint": suite_fingerprint(variant), "prompt": v["prompt"],
    }
    (evid / "probe.json").write_text(json.dumps(probe, indent=2) + "\n")
    run_sh = evid / "run.sh"
    run_sh.write_text(RUN_SH.format(
        run_id=run_id, variant=variant, arm=arm, seed=seed,
        evidence=p04._sh(evid), repo=p04._sh(repo), root=p04._sh(ROOT),
        env_file=p04._sh(ENV_FILE), lint=p04._sh(LINT),
        script=p04._sh(Path(__file__).resolve()), hs19a=p04._sh(Path(h.__file__).resolve()),
        pinned_port=pinned_port, agents=" ".join([v["primary"], *v["subagents"]]),
        timeout_s=timeout_s, title=p04._sh(f"probe-{run_id}"),
        agent_flag="" if v["primary"] == "build" else f" --agent {v['primary']}",
    ))
    run_sh.chmod(0o755)
    return run_sh


def schedule(include_conditional: bool = True) -> list[tuple[str, str, str, int]]:
    """The pre-registered order: (run_id, variant, arm, seed).

    Block 1 (hs19a): three rounds, one seed per round shared by every arm (paired), arm order
    reversed in the middle round (A B C | C B A | A B C). Block 2 (ds41): A B | B A | A B.
    Block 3 (ds41, 27b-nothink) is CONDITIONAL: run it only if the decision rule asks for it.
    """
    rows: list[tuple[str, str, int]] = []
    for i, seed in enumerate(SEEDS):
        arms = ["fd", "27b-nothink", "27b-think"]
        rows += [("hs19a", a, seed) for a in (arms if i != 1 else arms[::-1])]
    for i, seed in enumerate(SEEDS):
        arms = ["fd", "27b-think"]
        rows += [("ds41", a, seed) for a in (arms if i != 1 else arms[::-1])]
    if include_conditional:
        rows += [("ds41", "27b-nothink", seed) for seed in SEEDS]
    return [(f"{n:02d}-{v}-{a}-s{s}", v, a, s) for n, (v, a, s) in enumerate(rows, 1)]


def cmd_prepare(args: argparse.Namespace) -> int:
    try:
        run_sh = prepare_run(Path(args.out), args.variant, args.arm, args.seed,
                             args.run_id or f"{args.variant}-{args.arm}-s{args.seed}",
                             args.pinned_port, args.timeout_s)
    except FileExistsError as exc:
        print(exc, file=sys.stderr)
        return 2
    print(f"prepared {run_sh.parent.parent}\nnext (SENDS INFERENCE): bash {run_sh}")
    return 0


def cmd_prepare_all(args: argparse.Namespace) -> int:
    root = Path(args.out_root).resolve()
    if root.exists() and any(root.iterdir()):
        print(f"refusing: {root} exists and is not empty", file=sys.stderr)
        return 2
    lines = ["# Task-delegation probe: pre-registered ABA schedule. Run strictly in order, one at a",
             "# time. Every line SENDS INFERENCE. Lines under CONDITIONAL run only if",
             f"# `python3 {Path(__file__).resolve()} summarize --root {root}` asks for them.", ""]
    header_done = False
    for run_id, variant, arm, seed in schedule():
        run_sh = prepare_run(root / run_id, variant, arm, seed, run_id, args.pinned_port,
                             args.timeout_s)
        if variant == "ds41" and arm == "27b-nothink" and not header_done:
            lines += ["", "# CONDITIONAL (block 3): only if summarize says run_conditional_block"]
            header_done = True
        lines.append(f"bash {run_sh}")
    (root / "SCHEDULE.txt").write_text("\n".join(lines) + "\n")
    print((root / "SCHEDULE.txt").read_text(), end="")
    return 0


def cmd_check_config(args: argparse.Namespace) -> int:
    evid = Path(args.evidence).resolve()
    probe = json.loads((evid / "probe.json").read_text())
    c = check_config_pin(load_jsonc(evid / "opencode.jsonc"), probe)
    print(f"{'PASS' if c['ok'] else 'FAIL'}  {c['check']}: {c['detail']}")
    return 0 if c["ok"] else 1


# ---------------------------------------------------------------- verify


def tap_calls(events: list[dict[str, Any]], start: float, end: float) -> dict[str, dict[str, Any]]:
    """Per request_id in the window: last request_keys, roles, ports, parsed client tool calls,
    and the server's completion tokens."""
    calls: dict[str, dict[str, Any]] = {}
    for e in events:
        if not start <= float(e.get("ts_epoch") or 0) <= end:
            continue
        rid = str(e.get("request_id") or "")
        if not rid:
            continue
        c = calls.setdefault(rid, {"keys": None, "roles": set(), "ports": set(),
                                   "tool_calls": set(), "completion_tokens": None,
                                   "prompt_tokens": None})
        if isinstance(e.get("request_keys"), dict):
            c["keys"] = e["request_keys"]
        if isinstance(e.get("role"), str) and e["role"]:
            c["roles"].add(e["role"])
        if isinstance(e.get("port"), int) and not isinstance(e.get("port"), bool):
            c["ports"].add(e["port"])
        for name in e.get("client_tool_calls") or []:
            if isinstance(name, str):
                c["tool_calls"].add(name)
        if e.get("event") == "timings":
            c["completion_tokens"] = e.get("tokens")
            c["prompt_tokens"] = e.get("prompt_tokens")
    return calls


def _keyed(calls: dict[str, dict[str, Any]], session_ids: set[str]) -> list[dict[str, Any]]:
    return [c for c in calls.values()
            if c["keys"] is not None and c["keys"].get("x_session_id") in session_ids]


def _overrides(call: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in (call["keys"] or {}).items()
            if k in OVERRIDE_KEYS or k.startswith("x_force_")}


def check_parent_pin(parent_calls: list[dict[str, Any]], probe: dict[str, Any],
                     require_tap_pin: bool) -> dict[str, Any]:
    """C2. Pinned arms: every parent call on the pinned port, carrying the declared pin when the
    tap records overrides. Unpinned arm: no override and never on the pinned port."""
    role, port = probe["force_role"], probe["pinned_port"]
    ports = sorted(set().union(*(c["ports"] for c in parent_calls))) if parent_calls else []
    roles = sorted(set().union(*(c["roles"] for c in parent_calls))) if parent_calls else []
    seen = [_overrides(c) for c in parent_calls]
    recorded = any(seen)
    problems = []
    if not parent_calls:
        problems.append("no tap call keyed to the parent")
    if role:
        off = [p for c in parent_calls for p in c["ports"] if p != port]
        if off or any(not c["ports"] for c in parent_calls):
            problems.append(f"parent served off the pinned port {port}: ports {ports}")
        if recorded:
            bad = [s for s in seen if s != {FORCE_FIELD: role}]
            if bad:
                problems.append(f"parent override keys {bad[:3]} != {{{FORCE_FIELD!r}: {role!r}}}")
        elif require_tap_pin:
            problems.append("the tap records no override key (API predates 83b18f03?) and "
                            "--require-tap-pin is set")
        basis = "tap request_keys" if recorded else "served port (tap records no override keys)"
        name = "C2-parent-pinned"
    else:
        if recorded:
            problems.append(f"unpinned arm, but parent calls carry {[s for s in seen if s][:3]}")
        if port in ports:
            problems.append(f"unpinned parent served on the pinned port {port}")
        if parent_calls and "frontdoor" not in roles:
            problems.append(f"unpinned parent not served by frontdoor: roles {roles}")
        basis = "no override key on any parent call; frontdoor served"
        name = "C2-parent-unpinned"
    return _check(not problems, name,
                  f"{len(parent_calls)} parent call(s); roles {roles or 'none'}; ports "
                  f"{ports or 'none'}; basis: {basis}"
                  + ("; " + "; ".join(problems) if problems else ""))


def check_child_unpinned(child_calls: list[dict[str, Any]], child_ids: list[str],
                         probe: dict[str, Any]) -> dict[str, Any]:
    """C3. The child is selected by the orchestrator: no override key, not on the pinned port."""
    if not child_ids:
        return _check(True, "C3-child-unpinned", "n/a: no child session (the parent did not delegate)")
    port = probe["pinned_port"]
    ports = sorted(set().union(*(c["ports"] for c in child_calls))) if child_calls else []
    roles = sorted(set().union(*(c["roles"] for c in child_calls))) if child_calls else []
    pinned = [_overrides(c) for c in child_calls if _overrides(c)]
    problems = []
    if not child_calls:
        problems.append("child session(s) exist but no tap call is keyed to them")
    if pinned:
        problems.append(f"child calls carry override keys {pinned[:3]}")
    if port in ports:
        problems.append(f"child served on the pinned port {port}")
    return _check(not problems, "C3-child-unpinned",
                  f"{len(child_calls)} child call(s) over {len(child_ids)} child session(s); roles "
                  f"{roles or 'none'}; ports {ports or 'none'}; override keys: none seen"
                  + ("; " + "; ".join(problems) if problems else ""))


def check_one_model(sessions: list[dict[str, Any]], parent: dict[str, Any]) -> dict[str, Any]:
    """C4: every assistant message and task child model is the one logical model."""
    return next(c for c in h.check_selection({}, "", None, sessions, parent)
                if c["check"] == "S4-one-logical-model") | {"check": "C4-one-logical-model"}


def parent_text(session: dict[str, Any]) -> str:
    return "\n".join(p.get("text", "") for m in session.get("messages", [])
                     if (m.get("info") or {}).get("role") == "assistant"
                     for p in m.get("parts", []) if p.get("type") in {"text", "reasoning"})


def classify(parent: dict[str, Any], children: dict[str, dict[str, Any]]) -> dict[str, Any]:
    parts = h._parts(parent)
    tasks = h.task_parts(parent)
    done = [p for p in tasks if (p.get("state") or {}).get("status") == "completed"]
    linked = [cid for cid in h.child_session_ids(parent)
              if ((children.get(cid) or {}).get("info") or {}).get("parentID")
              == (parent.get("info") or {}).get("id")]
    other = sorted({p.get("tool") for p in parts if p.get("type") == "tool" and p.get("tool") != "task"})
    markers = sorted(set(_UNPARSED.findall(parent_text(parent))))
    if not parent:
        outcome = "run_error"
    elif done and linked:
        outcome = "delegated"
    elif tasks:
        outcome = "delegated_failed"
    elif markers:
        outcome = "unparsed_attempt"
    elif other:
        outcome = "self_served"
    else:
        outcome = "no_tool"
    return {"outcome": outcome, "task_parts": len(tasks), "task_parts_completed": len(done),
            "linked_children": linked, "other_tools": other, "unparsed_markers": markers,
            "subagent_types": [((p.get("state") or {}).get("input") or {}).get("subagent_type")
                               for p in tasks],
            "reasoning_parts": sum(1 for p in parts if p.get("type") == "reasoning")}


def answers_correct(parent: dict[str, Any], answers: dict[str, str]) -> dict[str, Any]:
    text = h.final_text(parent)
    got = {k: bool(re.search(rf"{re.escape(k)}\s*=\s*[`'\"]?{re.escape(v)}(?![\w-])", text))
           for k, v in answers.items()}
    return _check(all(got.values()), "T1-answers-correct",
                  f"final answer {text.strip()[-200:]!r}; expected {answers}; matched {got}")


def cmd_verify(args: argparse.Namespace) -> int:
    evid = Path(args.evidence).resolve()
    probe = json.loads((evid / "probe.json").read_text())
    repo = Path(args.repo).resolve() if args.repo else evid.parent / "repo"
    parent_id = h._read(evid / "parent-session-id.txt")
    start = float(h._read(evid / "window-start.txt"))
    end = float(h._read(evid / "window-end.txt"))
    window_end = end + args.slack_s
    parent = h._load_json(evid / "parent-session.json")
    child_ids = [x for x in h._read(evid / "child-session-ids.txt").splitlines() if x.strip()]
    children = {cid: s for cid in child_ids if (s := h._load_json(evid / f"child-{cid}.json"))}

    checks = [check_config_pin(load_jsonc(evid / "opencode.jsonc"), probe),
              lint_stripped(evid, probe)]
    tap = Path(args.tap_events)
    observations: dict[str, Any] = {}
    per_session_tokens: dict[str, dict[str, Any]] = {}
    if tap.is_file():
        events = p04._jsonl(tap)
        calls = tap_calls(events, start, window_end)
        p_calls = _keyed(calls, {parent_id} if parent_id else set())
        c_calls = _keyed(calls, set(child_ids))
        checks.append(check_parent_pin(p_calls, probe, args.require_tap_pin))
        checks.append(check_child_unpinned(c_calls, child_ids, probe))
        keyed_ids = {parent_id, *child_ids}
        observations["tap"] = {
            "parent_calls": len(p_calls), "child_calls": len(c_calls),
            "foreign_keyed_calls_in_window": sum(
                1 for c in calls.values()
                if c["keys"] is not None and c["keys"].get("x_session_id") not in keyed_ids),
            "unkeyed_calls_in_window": sum(1 for c in calls.values() if c["keys"] is None),
            "parent_tool_calls_parsed": sorted(set().union(*(c["tool_calls"] for c in p_calls)))
            if p_calls else [],
            "parent_completion_tokens_per_call": [c["completion_tokens"] for c in p_calls],
            "parent_prompt_tokens_per_call": [c["prompt_tokens"] for c in p_calls],
            "parent_override_keys": [_overrides(c) for c in p_calls],
        }
        for label, sid, sess in [("parent", parent_id, parent),
                                 *[(f"child:{cid}", cid, s) for cid, s in children.items()]]:
            t = p04.tap_token_counts(events, sid or "", start, window_end)
            per_session_tokens[label] = p04.resolve_token_counts(sess, t)
            observations.setdefault("token_parity", {})[label] = p04.check_token_parity(sess, t)
    else:
        for name in ("C2-parent-pinned" if probe["force_role"] else "C2-parent-unpinned",
                     "C3-child-unpinned"):
            checks.append(_check(False, name, f"tap events file missing: {tap}"))
        per_session_tokens["parent"] = p04.resolve_token_counts(parent, None)
    checks.append(check_one_model([parent, *children.values()], parent))
    version = h._read(evid / "opencode-version.txt")
    checks.append(_check(version == PINNED_VERSION, "C5-opencode-version-pinned", version or "missing"))
    valid = all(c["ok"] for c in checks)

    outcome = classify(parent, children)
    answer = answers_correct(parent, probe["answers"])
    rc = h._read(evid / "opencode-exit.txt")
    errors = ([e for e in p04._jsonl(evid / "events.jsonl") if e.get("type") == "error"]
              if (evid / "events.jsonl").is_file() else [])
    observations.update({
        "answer": answer, "repo_unmodified": h.check_repo_unmodified(repo),
        "opencode_exit": rc, "timed_out": rc == "124", "error_events": len(errors),
        "agent_debug_files": sorted(p.name for p in evid.glob("agent-*.json")),
        "props_files": sorted(p.name for p in evid.glob("props-*.json")),
    })
    delegated = outcome["outcome"] == "delegated"
    tokens = h.combine_tokens(per_session_tokens)
    capture_args = SimpleNamespace(
        no_belief_capture=args.no_belief_capture or not valid,
        harness_card_version=args.harness_card_version, model_role=probe["model_role"],
        build_info=args.build_info, enable_thinking="true" if probe["enable_thinking"] else "false",
        endpoint=args.endpoint, emitted_at=args.emitted_at)
    capture = p04.capture_beliefs(
        capture_args, evid, parent, parent_id or "unknown", start, end,
        delegated and answer["ok"], tokens,
        task=f"task-delegation-probe-{probe['variant']}",
        run_id=f"task-probe-{probe['run_id']}-{parent_id or 'unknown'}",
        suite={"name": f"task-delegation-probe-{probe['variant']}",
               "fingerprint": probe["suite_fingerprint"]},
        producer="scripts/harness/task_delegation_probe.py",
        record_extra={"variant": probe["variant"], "arm": probe["arm"], "seed": probe["seed"],
                      "force_role": probe["force_role"], "outcome": outcome["outcome"],
                      "child_session_ids": child_ids,
                      "note": "passed = delegated with a linked child AND the answers correct; "
                              "the child is served by orchestrator selection (frontdoor)"},
    )
    if not valid and capture.get("status") == "skipped":
        capture = {"status": "skipped", "reason": "run is not valid (setup checks failed); re-run it"}
    verdict = {
        "schema": SCHEMA, "run_id": probe["run_id"], "variant": probe["variant"],
        "arm": probe["arm"], "seed": probe["seed"],
        "pin": {"field": FORCE_FIELD, "role": probe["force_role"], "agent": probe["primary"],
                "child_agents_unpinned": probe["subagents"]},
        "valid": valid, "outcome": outcome["outcome"], "delegated": delegated,
        "answer_correct": answer["ok"], "parent_session_id": parent_id,
        "child_session_ids": child_ids, "window": [start, end], "tap_events": str(tap),
        "checks": checks, "classification": outcome, "observations": observations,
        "token_counts": tokens, "belief_capture": capture,
        "note": "valid = the pin/unpin evidence holds; the outcome is the measured variable.",
    }
    (evid / "verdict.json").write_text(json.dumps(verdict, indent=2, default=str) + "\n")
    for c in checks:
        print(f"{'PASS' if c['ok'] else 'FAIL'}  {c['check']}: {c['detail']}")
    print(f"OUTCOME {outcome['outcome']} (answer {'correct' if answer['ok'] else 'wrong'}); "
          f"VALID {'yes' if valid else 'NO: re-run this run'}")
    return 0 if valid else 1


# ---------------------------------------------------------------- summarize / decision rule


def cell_state(verdicts: list[dict[str, Any]], n_required: int = 3) -> dict[str, Any]:
    valid = [v for v in verdicts if v.get("valid")]
    d = sum(1 for v in valid if v.get("delegated"))
    n = len(valid)
    if n < n_required:
        state = "incomplete"
    elif d == 0:
        state = "no"
    elif d * 3 >= 2 * n:
        state = "yes"
    else:
        state = "mixed"
    outcomes: dict[str, int] = {}
    for v in valid:
        outcomes[v["outcome"]] = outcomes.get(v["outcome"], 0) + 1
    return {"state": state, "valid": n, "delegated": d, "invalid": len(verdicts) - n,
            "outcomes": outcomes}


def decide(cells: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    """The pre-registered decision rule (docs: the probe's report). Returns verdict + reasons."""
    def st(v, a):
        return cells.get((v, a), {"state": "incomplete", "outcomes": {}})

    fd1, nt1, th1 = st("hs19a", "fd"), st("hs19a", "27b-nothink"), st("hs19a", "27b-think")
    fd2, th2, nt2 = st("ds41", "fd"), st("ds41", "27b-think"), st("ds41", "27b-nothink")
    need = [f"{v}/{a}" for (v, a), c in
            [(("hs19a", "fd"), fd1), (("hs19a", "27b-nothink"), nt1), (("hs19a", "27b-think"), th1)]
            if c["state"] == "incomplete"]
    if need:
        return {"verdict": "INCOMPLETE", "reason": f"cells without 3 valid runs: {need}",
                "run_conditional_block": False}
    if fd1["state"] != "yes":
        return {"verdict": "CONTROL_FAILED", "reason": "frontdoor did not reproduce HS-19a "
                "(< 2/3 delegated under the imperative prompt): the harness, not the model, is "
                "in question; no model claim", "run_conditional_block": False}
    if "mixed" in (nt1["state"], th1["state"]):
        return {"verdict": "INCONCLUSIVE", "reason": "a 27B cell under the imperative prompt is "
                "1/3: extend that cell and hs19a/fd by 3 runs each (seeds 404, 505, 606, same "
                "order), then re-summarize", "run_conditional_block": False}
    if nt1["state"] == "no":
        parser = nt1["outcomes"].get("unparsed_attempt", 0) * 3 >= 2 * nt1["valid"]
        return {"verdict": "MODEL",
                "qualifier": "served stack: tool-call format/parser on :8083" if parser else
                             "behavioural: the 27B does not call task when told to",
                "reason": "byte-identical OpenCode prompt and tools, thinking off in both arms: "
                          "frontdoor delegates, the 27B does not",
                "thinking_arm": th1["state"], "run_conditional_block": False}
    # nt1 == yes: the 27B delegates when instructed at matched thinking.
    if th1["state"] == "no":
        return {"verdict": "SETUP", "qualifier": "thinking mode",
                "reason": "the 27B delegates with enable_thinking=false and does not with it on "
                          "(C20c ran thinking on)", "run_conditional_block": False}
    base = {"reason_v1": "the 27B delegates when instructed (thinking on and off), so C20c's "
                         "non-delegation is not an inability of the model"}
    if "incomplete" in (fd2["state"], th2["state"]):
        return {**base, "verdict": "SETUP (V1)", "qualifier": "ds41 cells incomplete; the "
                "prompt-shape attribution is open", "run_conditional_block": False}
    if "mixed" in (fd2["state"], th2["state"]):
        return {**base, "verdict": "SETUP (V1); ds41 INCONCLUSIVE", "qualifier": "extend the mixed "
                "ds41 cell and its pair by 3 runs each", "run_conditional_block": False}
    if fd2["state"] == "yes" and th2["state"] == "no":
        if nt2["state"] == "incomplete":
            return {**base, "verdict": "PENDING_CONDITIONAL", "qualifier": "run block 3 "
                    "(ds41/27b-nothink) to split thinking from model propensity",
                    "run_conditional_block": True}
        if nt2["state"] == "yes":
            return {**base, "verdict": "SETUP", "qualifier": "thinking mode under discretionary "
                    "guidance", "run_conditional_block": False}
        return {**base, "verdict": "MODEL (propensity)", "qualifier": "the 27B can delegate when "
                "told, but under the seat's discretionary guidance it does not while frontdoor "
                "does", "run_conditional_block": False}
    if fd2["state"] == "no" and th2["state"] == "no":
        return {**base, "verdict": "SETUP", "qualifier": "prompt shape: neither model delegates "
                "under the seat's discretionary guidance", "run_conditional_block": False}
    if th2["state"] == "yes":
        return {**base, "verdict": "SETUP", "qualifier": "residual: the seat shape elicits "
                "delegation from the 27B here; C20c differs by what this probe does not "
                "replicate (40k-token context, open-ended task, MCP tools, direct :8083 route, "
                "variant high)", "run_conditional_block": False}
    return {**base, "verdict": "UNEXPECTED", "qualifier": f"ds41 fd={fd2['state']} "
            f"27b-think={th2['state']}: report as-is, no attribution", "run_conditional_block": False}


def cmd_summarize(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    verdicts = [json.loads(p.read_text()) for p in sorted(root.glob("*/evidence/verdict.json"))]
    by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for v in verdicts:
        by_cell.setdefault((v["variant"], v["arm"]), []).append(v)
    cells = {k: cell_state(vs) for k, vs in by_cell.items()}
    decision = decide(cells)
    summary = {"schema": f"{SCHEMA}-summary", "root": str(root), "runs": len(verdicts),
               "cells": {f"{v}/{a}": c for (v, a), c in sorted(cells.items())},
               "decision": decision}
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    for key, c in summary["cells"].items():
        print(f"{key:22s} {c['state']:10s} delegated {c['delegated']}/{c['valid']} valid "
              f"(+{c['invalid']} invalid) {c['outcomes']}")
    print("DECISION", json.dumps(decision))
    return 0


# ---------------------------------------------------------------- plan


PLAN_TEXT = """Task-delegation probe (measurement package B) checklist
=========================================================
Manual gates (the main session confirms each; this script cannot):
  [ ] GPU window agreed with workspace-76: the MI210 / :8083 carries no measurement of theirs.
  [ ] :8083 serves the production Qwen3.8-27B-Q8_0 (architect_general, alias coder_escalation).
  [ ] frontdoor serves Qwen3.6-35B-A3B; no CPU measurement window is open on its cores (fd
      parents and every child run there).
  [ ] Orchestrator API running with ORCHESTRATOR_FEATURE_V1_SUBAGENT_LINK=1.
  [ ] Recommended: orchestrator 83b18f03 merged + API reloaded (the tap then records the pin).
  [ ] EPYC_USER_ID, EPYC_HARNESS_CARD_VERSION, EPYC_BUILD_INFO exported.
Steps:
  1. python3 scripts/harness/task_delegation_probe.py prepare-all --out-root <dir>
  2. run SCHEDULE.txt's lines in order (each SENDS INFERENCE); a run whose verify prints
     "VALID NO" is re-run once from a fresh `prepare` (same variant/arm/seed)
  3. python3 scripts/harness/task_delegation_probe.py summarize --root <dir>
Preflight (local only):
"""


def cmd_plan(args: argparse.Namespace) -> int:
    print(PLAN_TEXT, end="")
    checks = h.preflight(args.opencode_bin)
    checks.append(_check(shutil.which("timeout") is not None, "timeout-installed",
                         shutil.which("timeout") or "missing"))
    checks.append(_check(shutil.which("curl") is not None, "curl-installed",
                         shutil.which("curl") or "missing"))
    for c in checks:
        print(f"  {'PASS' if c['ok'] else 'FAIL'}  {c['check']}: {c['detail']}")
    return 0 if all(c["ok"] for c in checks) else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("plan")
    p.add_argument("--opencode-bin")
    p = sub.add_parser("prepare")
    p.add_argument("--out", required=True)
    p.add_argument("--variant", choices=sorted(VARIANTS), required=True)
    p.add_argument("--arm", choices=sorted(ARMS), required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--run-id")
    p.add_argument("--pinned-port", type=int, default=PINNED_PORT)
    p.add_argument("--timeout-s", type=int, default=RUN_TIMEOUT_S)
    p = sub.add_parser("prepare-all")
    p.add_argument("--out-root", required=True)
    p.add_argument("--pinned-port", type=int, default=PINNED_PORT)
    p.add_argument("--timeout-s", type=int, default=RUN_TIMEOUT_S)
    p = sub.add_parser("check-config")
    p.add_argument("--evidence", required=True)
    p = sub.add_parser("verify")
    p.add_argument("--evidence", required=True)
    p.add_argument("--repo")
    p.add_argument("--user-id", required=True)
    p.add_argument("--tap-events", default=str(DEFAULT_TAP_EVENTS))
    p.add_argument("--slack-s", type=float, default=5.0)
    p.add_argument("--require-tap-pin", action="store_true",
                   help="C2 fails unless the tap itself records the parent's x_force_role "
                        "(needs orchestrator 83b18f03 deployed)")
    g = p.add_argument_group("SC86 belief capture (model_role / enable_thinking come from probe.json)")
    g.add_argument("--no-belief-capture", action="store_true")
    g.add_argument("--harness-card-version", default="")
    g.add_argument("--build-info", default="")
    g.add_argument("--endpoint", default="http://127.0.0.1:8000/v1")
    g.add_argument("--emitted-at", help=argparse.SUPPRESS)
    p = sub.add_parser("summarize")
    p.add_argument("--root", required=True)
    args = ap.parse_args(argv)
    if args.cmd is None:
        args = ap.parse_args(["plan", *(argv or [])])
    return {"plan": cmd_plan, "prepare": cmd_prepare, "prepare-all": cmd_prepare_all,
            "check-config": cmd_check_config, "verify": cmd_verify,
            "summarize": cmd_summarize}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
