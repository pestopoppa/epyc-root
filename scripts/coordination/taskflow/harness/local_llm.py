#!/usr/bin/env python3
"""taskflow/harness/local_llm.py — worker adapter: OPENCODE driving a local OpenAI-compatible llama-server.

Operator directive 2026-11-20: Stage 1 workers run on the local Qwen3.6-35B-A3B through opencode (no custom agent loop).

Prompt-cache layout (operator directive 2): every request is   [opencode system prompt + tool schemas + POLICY digest]
                                                                (byte-identical across every task of a batch)
                                                              + [per-task suffix: box, done_when, excerpts]
The policy digest goes in the system prompt via top-level `instructions: [file]` (an agent `prompt` would REPLACE
opencode's terse system prompt -- reference_opencode_cli_footguns). The server runs -np 1 with cache_prompt (default
on) so the stable prefix is computed once per batch; the per-task split is read from each step's usage
(`cache.read` = cached prompt tokens).

Small-model contract: tools = read / edit / write / glob / grep + bash restricted to the task's allowlisted test
commands; no task/webfetch/todo tools; `steps` = turn cap; `limit.output` caps each step; thinking off
(chat_template_kwargs). opencode footguns honoured: prompt on STDIN, stdout captured to a FILE, rc=1 with a complete
reply is not a failure, `snapshot: false`, private XDG dirs so the shared opencode.db never grows, `--standalone`.

Tier map (operator directive 3): the adapter maps the task tier to a model; Stage 1 maps every tier to the local 35B.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

OPENCODE = os.environ.get("TASKFLOW_OPENCODE", "/usr/local/share/npm-global/bin/opencode")
PROVIDER = "taskflow-local"
AGENT = "taskflow-worker"
# tier -> model id per adapter family. Local: one model serves every tier in Stage 1.
TIER_MODELS = {
    "local": {"luna": "q35-a3b", "terra": "q35-a3b", "sol": "q35-a3b"},
    "codex": {"luna": "gpt-6.1-luna", "terra": "gpt-6.1-terra", "sol": "gpt-6.1-sol"},
    "claude": {"luna": "haiku", "terra": "sonnet", "sol": "opus"},
}
# Global deny-list carried over from /workspace/opencode.json (the per-run XDG config dir replaces the global config).
# r1 canary: a piped test command (`cmd | head`) was denied by "*": deny -> read-only helpers are allowed.
READ_ONLY = ["ls*", "cat *", "head *", "tail *", "wc *", "grep *", "rg *", "git diff*", "git status*", "git log*"]
BASH_DENY = ["sudo*", "rm -rf*", "git push*", "git reset*", "git checkout*", "git stash*", "git restore*",
             "git commit*", "curl*", "wget*", "systemctl*", "reboot*", "shutdown*"]

POLICY = """\
# taskflow worker contract (identical for every task)
You are a code worker on ONE handoff box in a disposable git worktree (your cwd). Rules:
1. Do exactly what the box asks, nothing more. Smallest correct change. Keep the repo's style.
2. Locate fast: at most 6 grep/glob/read calls, then EDIT. Read narrow line ranges, never whole large files.
3. Edit with the edit tool (exact old/new strings). Create a file with write only when the box needs a new file.
4. Every turn must call a tool until you finish. Never describe a plan without calling a tool in the same turn.
5. Never touch FORBIDDEN files. Never edit handoffs/, progress/, agents/, CLAUDE.md, .claude/.
6. The shell runs only the ALLOWED COMMANDS (plus ls, cat, head, tail, wc, grep, git diff, git status). No pipes needed.
7. Do not commit, push, stash, reset or checkout. Do not kill processes. No network.
8. Stop as soon as the box's done-when is met.
9. Finish with ONE final line, exactly:  TASKFLOW-RESULT {"claimed_done": true|false, "summary": "<=200 chars", "paths": ["changed/file", ...]}
   claimed_done=false with a reason when the box is blocked, unclear, too large for one change, or needs a decision.
"""


NUDGE = "Continue now: call a tool in this turn (grep, read or edit). Do not describe a plan.\n"


def model_for(tier: str | None, family: str = "local") -> str:
    m = TIER_MODELS[family]
    return m.get(tier or "terra", m["terra"])


def task_suffix(task: dict, excerpts: dict[str, str]) -> str:
    """The per-task user message. Ordered most-stable-first so even within a task the head caches."""
    b = task["budget"]
    out = [f"## BOX ({task['handoff']}, id {task.get('id') or task['text_sha']})", task["goal"].strip(), ""]
    out.append(f"## DONE WHEN\n{task.get('done_when') or '(not stated: do what the box text asks; the reviewer judges it)'}")
    allowed = task.get("test_cmds") or []
    out.append("## ALLOWED COMMANDS\n" + ("\n".join(allowed) if allowed else "(none: do not use bash)"))
    out.append("## FORBIDDEN\n" + ", ".join(task["forbidden"][:12]) + " …")
    out.append(f"## LIMITS\n{b['turns']} tool turns max. Be brief.")
    if excerpts:
        out.append("## FILE EXCERPTS (truncated; read more with the read tool)")
        for p, txt in excerpts.items():
            out.append(f"### {p}\n```\n{txt}\n```")
    return "\n".join(out) + "\n"


def excerpts_for(task: dict, cwd: Path) -> dict[str, str]:
    """Head of each input file, sharing one char budget (budget.excerpt_chars)."""
    left = int(task["budget"].get("excerpt_chars", 9000))
    out: dict[str, str] = {}
    for p in task.get("inputs") or []:
        f = cwd / p
        if left < 400 or not f.is_file():
            continue
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        cut = min(left, max(400, left // max(1, len(task["inputs"]))))
        lines = txt.splitlines()
        head = "\n".join(f"{i + 1}: {ln}" for i, ln in enumerate(lines))[:cut]
        out[p] = head + (f"\n… ({len(lines)} lines total)" if len(head) >= cut else "")
        left -= len(out[p])
    return out


def write_config(run_dir: Path, base_url: str, model_id: str, task: dict, ctx: int = 32768,
                 out_tokens: int = 4096) -> Path:
    """Per-run opencode config (XDG_CONFIG_HOME/opencode/opencode.json) + the POLICY instructions file.
    Everything that reaches the prompt is task-independent; only bash allow patterns vary (not prompt text)."""
    cfg_dir = run_dir / "xdg-config" / "opencode"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    pol = run_dir / "POLICY.md"
    if not pol.exists():
        pol.write_text(POLICY, encoding="utf-8")
    bash = {"*": "deny"}
    for ro in READ_ONLY:
        bash[ro] = "allow"
    for c in task.get("test_cmds") or []:
        bash[c] = "allow"
        bash[c + " *"] = "allow"
    for d in BASH_DENY:
        bash[d] = "deny"
    cfg = {
        "$schema": "https://opencode.ai/config.json",
        "snapshot": False,
        "autoupdate": False,
        "share": "disabled",
        "instructions": [str(pol)],
        "model": f"{PROVIDER}/{model_id}",
        "provider": {PROVIDER: {
            "npm": "@ai-sdk/openai-compatible",
            "name": "taskflow local llama-server",
            "options": {"baseURL": base_url, "apiKey": "local"},
            "models": {model_id: {
                "name": model_id, "tool_call": True,
                "limit": {"context": ctx, "output": out_tokens},
                "options": {"chat_template_kwargs": {"enable_thinking": False}, "cache_prompt": True},
            }},
        }},
        "agent": {AGENT: {
            "description": "taskflow single-box worker", "mode": "primary",
            "steps": int(task["budget"]["turns"]),
            "permission": {"read": "allow", "edit": "allow", "glob": "allow", "grep": "allow", "list": "allow",
                           "bash": bash, "shell": bash, "question": "deny",
                           # r1 canary: the JS `execute` sandbox ate 13 of 14 steps on syntax errors; image tool is noise
                           "execute": "deny", "experimental_image_generate": "deny", "opencode_*": "deny", "opencode_worktree_remove": "deny", "opencode_worktree_create": "deny", "webfetch": "deny", "websearch": "deny", "task": "deny",
                           "todowrite": "deny", "todoread": "deny", "skill": "deny",
                           "external_directory": "deny"},
        }},
    }
    p = cfg_dir / "opencode.json"
    p.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    return p


def parse_events(path: Path) -> dict:
    """Usage + final text from `opencode run --format json` output (one JSON event per line; tolerant)."""
    usage = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "reasoning": 0, "steps": 0}
    texts: list[str] = []
    errors: list[str] = []
    tools: list[str] = []
    tool_errors: list[str] = []
    edits = 0
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        lines = []
    for ln in lines:
        ln = ln.strip()
        if not ln.startswith("{"):
            continue
        try:
            ev = json.loads(ln)
        except ValueError:
            continue
        part = ev.get("part") if isinstance(ev.get("part"), dict) else ev
        typ = ev.get("type") or part.get("type")
        if typ in ("step_finish", "step-finish"):
            tok = part.get("tokens") or {}
            usage["steps"] += 1
            usage["input"] += int(tok.get("input") or 0)
            usage["output"] += int(tok.get("output") or 0)
            usage["reasoning"] += int(tok.get("reasoning") or 0)
            cache = tok.get("cache") or {}
            usage["cache_read"] += int(cache.get("read") or 0)
            usage["cache_write"] += int(cache.get("write") or 0)
        elif typ == "text" and part.get("text"):
            texts.append(str(part["text"]))
        elif typ in ("tool_use", "tool"):
            name = str(part.get("tool") or "?")
            tools.append(name)
            st = part.get("state") or {}
            out_txt = str(st.get("output") or st.get("error") or "")
            if st.get("status") == "error" or out_txt.startswith(("SyntaxError", "ReferenceError", "Permission denied")):
                tool_errors.append(f"{name}: {out_txt[:120]}")
            if name in ("edit", "write", "patch", "apply_patch"):
                edits += 1
        elif typ == "error":
            errors.append(json.dumps(ev.get("error") or ev)[:300])
    final = "\n".join(texts)
    result = None
    for ln in reversed(final.splitlines()):
        if "TASKFLOW-RESULT" in ln:
            raw = ln.split("TASKFLOW-RESULT", 1)[1].strip()
            try:
                result = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
            except ValueError:
                result = {"claimed_done": None, "summary": "unparseable TASKFLOW-RESULT", "raw": raw[:300]}
            break
    return {"usage": usage, "result": result, "text_tail": final[-1500:], "errors": errors, "tools": tools,
            "tool_errors": tool_errors, "edits": edits}


def spawn(task: dict, cwd: Path, run_dir: Path, base_url: str, family: str = "local",
          timeout_s: int | None = None) -> dict:
    """Run one worker to completion (or the wall cap). Returns {rc, wall_s, usage, result, model, tier, ...}."""
    run_dir.mkdir(parents=True, exist_ok=True)
    model_id = model_for(task.get("tier"), family)
    write_config(run_dir, base_url, model_id, task)
    prompt = task_suffix(task, excerpts_for(task, cwd))
    (run_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    env = dict(os.environ,
               XDG_CONFIG_HOME=str(run_dir / "xdg-config"), XDG_DATA_HOME=str(run_dir / "xdg-data"),
               XDG_STATE_HOME=str(run_dir / "xdg-state"), XDG_CACHE_HOME=str(run_dir.parent / "xdg-cache"),
               OPENCODE_DISABLE_AUTOUPDATE="1", OPENCODE_DISABLE_LSP_DOWNLOAD="1", NO_COLOR="1")
    env.pop("OPENCODE_CONFIG", None)
    argv = [OPENCODE, "run", "--standalone", "--format", "json", "--agent", AGENT,
            "--model", f"{PROVIDER}/{model_id}", "--auto"]
    out_p, err_p = run_dir / "events.jsonl", run_dir / "stderr.log"
    t0 = time.time()
    timeout_s = int(timeout_s or task["budget"]["wall_s"])
    with out_p.open("wb") as out, err_p.open("wb") as err:
        proc = subprocess.Popen(argv, cwd=str(cwd), env=env, stdin=subprocess.PIPE, stdout=out, stderr=err)
        (run_dir / "worker.pid").write_text(str(proc.pid))
        timed_out = False
        try:
            proc.communicate(prompt.encode("utf-8"), timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.terminate()
            try:
                proc.wait(15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(15)
    ev = parse_events(out_p)
    nudged = False
    if (not timed_out and ev["result"] is None and ev["usage"]["steps"] <= 2
            and not subprocess.run(["git", "-C", str(cwd), "status", "--porcelain"], capture_output=True, text=True).stdout.strip()):
        # r1 canary: the 35B narrated a plan without a tool call and opencode ended the run after 1 step.
        # One continuation in the SAME session (cached prefix), never a fresh thread.
        nudged = True
        with out_p.open("ab") as out, err_p.open("ab") as err:
            proc = subprocess.Popen(argv + ["--continue"], cwd=str(cwd), env=env, stdin=subprocess.PIPE, stdout=out, stderr=err)
            try:
                proc.communicate(NUDGE.encode(), timeout=max(60, timeout_s - int(time.time() - t0)))
            except subprocess.TimeoutExpired:
                timed_out = True
                proc.terminate()
                try:
                    proc.wait(15)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(15)
        ev = parse_events(out_p)
    u = ev["usage"]
    return {"rc": proc.returncode, "timed_out": timed_out, "wall_s": round(time.time() - t0, 1),
            "family": family, "tier": task.get("tier"), "model": model_id, "prompt_chars": len(prompt),
            "usage": u, "uncached_input": u["input"],  # opencode reports input net of cache reads
            "result": ev["result"], "errors": ev["errors"], "tools": ev["tools"], "nudged": nudged,
            "tool_errors": ev["tool_errors"], "edits": ev["edits"], "text_tail": ev["text_tail"]}
