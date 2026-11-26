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

import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
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
# r7d canary: 10 of 21 shell denials were `cat` (POLICY rule 6 promised it; READ_ONLY omitted it) plus `sed -n`,
# `pwd`, `git show` and `cmd | head`. tool_output (200 lines / 8 KiB) bounds every output, so `cat` is safe now.
READ_ONLY = ["ls*", "cat *", "head *", "tail *", "wc *", "grep *", "rg *", "sed -n *", "pwd", "find *",
             "git diff*", "git status*", "git log*", "git show *", "git branch*"]
# Pipe/redirect tails the model composes onto an allowed command (r7d: `cat f | head -100`, `cmd 2>&1`).
PIPE_TAILS = [" 2>&1", " | head *", " | tail *", " | wc *", " | grep *", " 2>&1 | head *", " 2>&1 | tail *",
              " 2>&1 | grep *"]
# r8c canary (fix 6): INTAKE-VALIDATE-86 composed `grep … | sed 's/…//' | sort -u`, `| awk '{print $2}'`, `| cut -d- -f2-`
# and every one was denied. These stream filters are allowed as pipe stages (both as a stage pattern and as a tail on
# every allowed command); their file-writing / command-running forms stay on BASH_DENY, which still wins.
PIPE_FILTERS = ["sed *", "sort", "sort *", "awk *", "cut *"]
PIPE_TAILS += [f" | {f}" for f in PIPE_FILTERS] + [f" 2>&1 | {f}" for f in PIPE_FILTERS]
# Task-brief layer P3 (§7): retrieval tools for locating code and for self-briefing (read-only, zero cloud tokens).
RETRIEVAL = ["gitnexus query *", "gitnexus context *", "gitnexus impact *",
             "/workspace/repos/epyc-orchestrator/.venv/bin/python /workspace/repos/epyc-orchestrator/scripts/kb_rag/cli.py query *"]
KB_SEARCH = RETRIEVAL[-1][:-2]
BASH_DENY = ["sed *-i*", "sed *--in-place*", "find *-delete*", "find *-exec*", "* > *", "* >> *", "* | sh*", "* | bash*",
             "sudo*", "git push*", "git reset*", "git checkout*", "git stash*", "git restore*",
             "git commit*", "curl*", "wget*", "systemctl*", "reboot*", "shutdown*",
             # r8c fix 6: the writing / executing forms of the pipe filters (sed -i / w FILE, awk system / getline /
             # redirect, sort -o)
             "* | sed *-i*", "* | sed *--in-place*", "sed */w *", "* | sed */w *",
             "awk *system*", "* | awk *system*", "awk *getline*", "* | awk *getline*", "awk *>*", "* | awk *>*",
             "sort *-o*", "* | sort *-o*", "sort *--output*", "* | sort *--output*"]

POLICY = """\
# taskflow worker contract (identical for every task)
You are a code worker on ONE handoff box in a disposable git worktree (your cwd). Rules:
1. Do exactly what the box asks, nothing more. Smallest correct change. Keep the repo's style.
2. Locate fast: at most 6 grep/glob/read calls, then EDIT. Read narrow line ranges, never whole large files.
3. Edit with the edit tool (exact old/new strings). Create a file with write only when the box needs a new file.
4. Every turn must call a tool until you finish. Never describe a plan without calling a tool in the same turn.
5. Never touch FORBIDDEN files. Never edit handoffs/, progress/, agents/, CLAUDE.md, .claude/.
6. The shell runs only the ALLOWED COMMANDS plus read-only helpers (ls, cat, head, tail, wc, grep, sed -n, find, pwd,
   git diff/status/log/show). You may append `2>&1` and pipe into head, tail, wc, grep, sed, sort, awk or cut. No `>` files, no && chains, no cd.
   When an ALLOWED COMMAND runs through orch-py.sh, you can also use `orch-py.sh -c "<python>"` or pass it a .py file
   inside your cwd (relative path). Use `taskflow-scratch rm <relative path>` or
   `taskflow-scratch mv <relative src> <relative dst>` to clean up untracked scratch files you created.
10. ALWAYS use paths relative to your cwd (e.g. src/x.py). Never type an absolute path.
    Read-only reference files from other repos are under .taskflow-refs/ (read them, never edit them).
7. Do not commit, push, stash, reset or checkout. Do not kill processes. No network.
8. Stop as soon as the box's done-when is met.
9. Finish with ONE final line, exactly:  TASKFLOW-RESULT {"claimed_done": true|false, "summary": "<=200 chars", "paths": ["changed/file", ...]}
   claimed_done=false with a reason when the box is blocked, unclear, too large for one change, or needs a decision.
"""


NUDGE = "Continue now: call a tool in this turn (grep, read or edit). Do not describe a plan.\n"


TOOL_MAX_LINES, TOOL_MAX_BYTES = 200, 8192
POLICY_DIR = Path(os.environ.get("TASKFLOW_POLICY_DIR", "/mnt/raid0/llm/tmp/taskflow-policy"))


def policy_file() -> Path:
    """H3: ONE content-addressed POLICY path for every task, so the instructions block (which names its path) is
    byte-identical across tasks and the server's prefix cache spans the whole batch."""
    h = hashlib.sha256(POLICY.encode()).hexdigest()[:12]
    p = POLICY_DIR / f"POLICY-{h}.md"
    if not p.exists():
        POLICY_DIR.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(POLICY, encoding="utf-8")
        os.replace(tmp, p)
    return p


MAX_TOKENS_CAP = 4096


def cap_max_tokens(body: dict, cap: int = MAX_TOKENS_CAP) -> bool:
    """Proxy guard: every request gets an output cap (r3 runaway: 31,896 tokens from an uncapped side request)."""
    cur = body.get("max_completion_tokens") or body.get("max_tokens")
    if cur is None or int(cur) > cap or int(cur) < 0:
        body.pop("max_completion_tokens", None)
        body["max_tokens"] = cap
        return True
    return False


# r8g fix 2 (r8f MM-5 nothink): opencode 2 ships built-in `opencode_worktree_{create,list,remove}` tools. They assert the
# `edit` permission on the DIRECTORY, so the name-keyed deny entries in the agent permission never applied: the worker
# called opencode_worktree_remove(force) on its own lane, the diff was gone, and `git status` failed rc=128. The worker
# tool set is cut at the proxy (the model never sees the tools) and, as defence in depth, the edit permission denies the
# lane directory itself (write_config).
WORKER_DENIED_TOOLS = ("opencode_worktree_remove", "opencode_worktree_create", "opencode_worktree_list")


SHELL_DENIAL_HINT = (" Allowed shell forms: the ALLOWED COMMANDS, read-only helpers (ls cat head tail wc grep sed -n find git diff/status/log), "
                     "`bash <row>/orch-py.sh -m pytest <test>`, `bash <row>/orch-py.sh -c \"<python>\"`, `bash <row>/orch-py.sh <relative .py>`. "
                     "Scratch cleanup: `taskflow-scratch rm <relative path>` or `taskflow-scratch mv <relative src> <relative dst>`. "
                     "Bare `python3`, `cd`, `&&` and `>` are not allowed; use orch-py.sh -c for Python probes.")


def _annotate_text(c: str, hint: str) -> str | None:
    """The hinted text, or None when `c` is not a denial or already carries the hint. r8h (TF-R8G-REFUSAL-HINT): opencode
    sends the denial as JSON, `{"error":{"type":"permission.rejected","message":"Permission denied: shell"},"content":[]}`,
    so the r8g `startswith("Permission denied")` match never fired (16/16 bare denials). The hint goes into
    error.message so the content stays valid JSON."""
    if "Permission denied" not in c:
        return None
    try:
        d = json.loads(c)
    except ValueError:
        d = None
    if isinstance(d, dict) and isinstance(d.get("error"), dict) and "Permission denied" in str(d["error"].get("message", "")):
        msg = str(d["error"]["message"])
        if hint in msg:   # idempotency on the DECODED message: inside JSON the hint is escaped, so `hint in c` misses it
            return None
        d["error"]["message"] = msg.rstrip() + hint
        return json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    if hint in c:
        return None
    return c.rstrip() + hint


def annotate_denials(body: dict, hint: str = SHELL_DENIAL_HINT) -> int:
    """Proxy guard (r8g fix 4, r8h): opencode's refusal names no alternative. Append the allowed forms to every denial
    tool result in the request history (plain text, opencode's JSON error shape, or text content parts). Deterministic and
    idempotent, so the rewritten history is byte-identical on the next request (prefix cache). Returns messages touched."""
    n = 0
    for m in body.get("messages") or []:
        if m.get("role") != "tool":
            continue
        c = m.get("content")
        hit = False
        if isinstance(c, str):
            new = _annotate_text(c, hint)
            if new is not None:
                m["content"], hit = new, True
        elif isinstance(c, list):
            for part in c:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    new = _annotate_text(part["text"], hint)
                    if new is not None:
                        part["text"], hit = new, True
        n += hit
    return n


def strip_worker_tools(body: dict, denied=WORKER_DENIED_TOOLS) -> list[str]:
    """Proxy guard: drop worktree-mutating opencode tools from a request's `tools`. Returns the removed names."""
    tools = body.get("tools")
    if not isinstance(tools, list):
        return []
    gone = [t.get("function", {}).get("name") for t in tools
            if (t.get("function", {}).get("name") or "").startswith(tuple(denied))]
    if gone:
        body["tools"] = [t for t in tools if t.get("function", {}).get("name") not in gone]
        if not body["tools"]:
            body.pop("tools", None)
            body.pop("tool_choice", None)
    return gone


class DegenerationGuard:
    """Proxy-side abort for degenerate decoding (canary r3/r4: capped runaways decoding repetitive garbage at
    ~46 tok/s with ~0 MTP acceptance carried 44% of np1 drafted tokens).

    feed(text_delta, timings) per streamed chunk -> reason str when the request should be aborted, else None.
      mtp:    with per-chunk timings (request `timings_per_token: true`), rolling acceptance over the last
              >= MTP_WINDOW predicted tokens stays below MTP_MIN
      repeat: over the last REPEAT_WINDOW chars, the share of word NGRAM-grams that are repeats >= REPEAT_MAX
    """
    MTP_WINDOW, MTP_MIN = 512, 0.2
    REPEAT_WINDOW, NGRAM, REPEAT_MAX, MIN_CHARS = 4000, 6, 0.6, 2000

    def __init__(self):
        self.text = ""
        self.marks: list[tuple[int, int, int]] = []    # (predicted_n, draft_n, draft_accepted)

    def feed(self, delta: str = "", timings: dict | None = None) -> str | None:
        if delta:
            self.text = (self.text + delta)[-self.REPEAT_WINDOW * 2:]
        if timings and timings.get("draft_n") is not None:
            self.marks.append((int(timings.get("predicted_n") or 0), int(timings.get("draft_n") or 0),
                               int(timings.get("draft_n_accepted") or 0)))
            p1, d1, a1 = self.marks[-1]
            for p0, d0, a0 in reversed(self.marks[:-1]):
                if p1 - p0 >= self.MTP_WINDOW:
                    if d1 - d0 > 0 and (a1 - a0) / (d1 - d0) < self.MTP_MIN:
                        return f"mtp-acceptance {(a1 - a0) / (d1 - d0):.2f} over {p1 - p0} tokens"
                    break
        if len(self.text) >= self.MIN_CHARS:
            w = self.text[-self.REPEAT_WINDOW:].split()
            grams = [tuple(w[i:i + self.NGRAM]) for i in range(max(0, len(w) - self.NGRAM + 1))]
            if len(grams) >= 50:
                rep = 1 - len(set(grams)) / len(grams)
                if rep >= self.REPEAT_MAX:
                    return f"repeat-ratio {rep:.2f}"
        return None


_XML_IN_ARGS = ("<parameter=", "<function=", "<tool_call>", "</parameter>", "</function>", "</tool_call>")
TOOL_ARG_CORRECTION = ("Your last tool call's arguments contained raw XML tags (<parameter=...>). Call the tool again "
                       "with plain JSON argument values only, one tool call per turn.")


def invalid_tool_args(arguments: str) -> str | None:
    """Client-side tool-argument check (r3/r4: Qwen XML tool-call markup leaked into argument values).
    The r6 proxy (tool_arg_filter=true, operator 2026-11-20 "can't hurt") rejects such a response, retries upstream
    once with TOOL_ARG_CORRECTION appended, and logs `bad_tool_args`; the strict server parser (AK) is the real fix."""
    for tag in _XML_IN_ARGS:
        if tag in (arguments or ""):
            return f"tool arguments contain {tag}"
    return None


LANES_ROOT = os.environ.get("TASKFLOW_LANES_ROOT", "/mnt/raid0/llm/tf")
# r5-r7d canary: the 35B types the lane's absolute path with a mangled prefix while keeping the hex lane id intact:
# `<mnt/raid0/llm/tf/e9f8`, `.mnt/...`, `mnt/raid0/tf/...`, `/mnt/raid0/84fd/...`, `/mnt/raid0/llm/t/65a8/...`.
_MANGLED_LANE = re.compile(r"(?<![\w/])[<.>]?/?mnt/raid0/(?:llm/)?(?:tf?/)?([0-9a-f]{4,8})(?=/|$|[\s\"'`])")


def repair_lane_paths(text: str, lane_exists=None) -> tuple[str, int]:
    """Rewrite mangled lane-prefix paths to LANES_ROOT/<id>. Only rewrites when the lane id names an existing lane
    (lane_exists(id) -> bool, default: a directory under LANES_ROOT), so unrelated /mnt/raid0 paths are untouched."""
    lane_exists = lane_exists or (lambda h: os.path.isdir(os.path.join(LANES_ROOT, h)))
    n = 0

    def sub(m):
        nonlocal n
        good = f"{LANES_ROOT}/{m.group(1)}"
        if m.group(0) == good or not lane_exists(m.group(1)):
            return m.group(0)
        n += 1
        return good
    return _MANGLED_LANE.sub(sub, text or ""), n


def rewrite_sse_tool_args(chunks: list[bytes], lane_exists=None) -> tuple[list[bytes], int]:
    """Proxy side of repair_lane_paths: reassemble each streamed tool call's arguments, repair them, and if anything
    changed re-emit the stream with the whole repaired argument string in that call's first delta (later argument
    deltas emptied). Unchanged streams are returned byte-identical."""
    raw = b"".join(chunks)
    lines = raw.split(b"\n")
    evs: list = []
    args: dict = {}
    for ln in lines:
        ev = None
        if ln.startswith(b"data: {"):
            try:
                ev = json.loads(ln[6:])
            except ValueError:
                ev = None
        evs.append(ev)
        for ch in (ev or {}).get("choices") or []:
            for tc in (ch.get("delta") or {}).get("tool_calls") or []:
                k = (ch.get("index", 0), tc.get("index", 0))
                args[k] = args.get(k, "") + str((tc.get("function") or {}).get("arguments") or "")
    fixed, total = {}, 0
    for k, a in args.items():
        a2, n = repair_lane_paths(a, lane_exists)
        if n:
            fixed[k], total = a2, total + n
    if not total:
        return chunks, 0
    seen, out = set(), []
    for ln, ev in zip(lines, evs):
        touched = False
        for ch in (ev or {}).get("choices") or []:
            for tc in (ch.get("delta") or {}).get("tool_calls") or []:
                k = (ch.get("index", 0), tc.get("index", 0))
                fn = tc.get("function")
                if k in fixed and isinstance(fn, dict) and "arguments" in fn:
                    fn["arguments"] = "" if k in seen else fixed[k]
                    seen.add(k)
                    touched = True
        out.append(b"data: " + json.dumps(ev).encode() if touched else ln)
    return [b"\n".join(out)], total


def request_digest(body: dict) -> dict:
    """H5: what the metering proxy logs per request -- enough to locate a prefix break without storing prompts."""
    msgs = body.get("messages") or []
    sys_txt = "".join(str(m.get("content")) for m in msgs if m.get("role") == "system")
    raw = json.dumps(body, sort_keys=False)
    return {"n_messages": len(msgs), "roles": [m.get("role") for m in msgs][:60],
            "tools": [t.get("function", {}).get("name") for t in body.get("tools") or []],
            "system_sha": hashlib.sha256(sys_txt.encode()).hexdigest()[:16],
            "head2k_sha": hashlib.sha256(raw[:2048].encode()).hexdigest()[:16], "body_chars": len(raw),
            "is_title": not body.get("tools") and len(msgs) <= 2}


def model_for(tier: str | None, family: str = "local") -> str:
    m = TIER_MODELS[family]
    return m.get(tier or "terra", m["terra"])


BRIEF_RESULT = "TASKFLOW-BRIEF"


def allowed_commands(task: dict) -> list[str]:
    """Acceptance first (it IS the runnable done-when, §1.5), then the box's own test commands, deduplicated."""
    out = []
    from taskflow import verify as _V       # `cd <task repo> && X` -> `X`: the lane is that repo
    acc = _V.lane_cmd(task.get("acceptance"), task) if task.get("acceptance") else None
    for c in ([acc] if acc else []) + list(task.get("test_cmds") or []):
        c = " ".join(str(c).strip().strip("`").split())
        if c and c not in out:
            out.append(c)
    return out


def brief_sections(task: dict) -> list[str]:
    """## WHERE / ## APPROACH / ## NON-GOALS / ## STALE (task-brief layer P3). Empty when there is no brief."""
    out = []
    if task.get("where"):
        blast = task.get("blast_radius") or {}
        ranged = any("#L" in str(w) for w in task["where"])
        out.append("## WHERE\n" + ("Entries with `#L<a>-<b>` are line ranges: read ONLY those lines (read offset/limit), never the whole file.\n"
                                   if ranged else "") + "\n".join(
            f"- {w}" + (f"  (blast radius {blast[w.split('::')[-1].split('#L')[0]]}: change with care)"
                        if "::" in w and str(blast.get(w.split("::")[-1].split("#L")[0], "")).upper() in ("HIGH", "CRITICAL") else "")
            for w in task["where"]))
    if task.get("approach"):
        out.append("## APPROACH\n" + str(task["approach"]).strip())
    if task.get("non_goals"):
        out.append("## NON-GOALS (doing any of these is drift)\n" + "\n".join(f"- {g}" for g in task["non_goals"]))
    if task.get("brief_state") == "stale" and task.get("stale"):
        out.append("## STALE (the brief no longer matches the tree)\n" + "\n".join(f"- {x}" for x in task["stale"]))
    return out


def write_brief_section(task: dict) -> str:
    """Phase 1 of the two-phase run (§5): self-brief (none/orphaned) or refresh (stale) -- output is constrained."""
    why = {"stale": "the brief above is STALE: fix the listed items", "orphaned": "the old brief was written for "
           "different box text"}.get(task.get("brief_state"), "this box has no brief yet")
    return ("## WRITE BRIEF FIRST\n"
            f"Phase 1 of 2 ({why}). Do NOT edit any file in this phase. Locate the code with grep/read and, if allowed, "
            f"`gitnexus query|context <name>` or `{KB_SEARCH} \"<question>\"`. Then finish with ONE line, exactly:\n"
            f'{BRIEF_RESULT} {{"where": ["epyc-root:path/to/file.py::symbol", ...], "approach": "<=5 lines: the decision", '
            '"acceptance": "<the runnable form of DONE WHEN, e.g. pytest -q tests/x.py::test_y>", '
            '"non_goals": ["<what not to change>", ...]}\n'
            "where = repo-qualified paths that exist (optional ::symbol); acceptance must FAIL on the unchanged tree "
            "and pass once the box is done; use the DONE WHEN command verbatim when it is one.")


def task_suffix(task: dict, excerpts: dict[str, str]) -> str:
    """The per-task user message (everything after the byte-identical stable prefix = opencode system prompt + tool
    schemas + POLICY). Ordered most-stable-first so even within a task the head caches."""
    b = task["budget"]
    out = [f"## BOX ({task['handoff']}, id {task.get('id') or task['text_sha']})", task["goal"].strip(), ""]
    out.append(f"## DONE WHEN\n{task.get('done_when') or '(not stated: do what the box text asks; the reviewer judges it)'}")
    out.extend(brief_sections(task))
    if task.get("phase") == "brief":
        out.append(write_brief_section(task))
    allowed = allowed_commands(task)
    out.append("## ALLOWED COMMANDS\n" + ("\n".join(allowed) if allowed else "(no test command for this box)")
               + "\nRead-only helpers: gitnexus query|context|impact <name>"
               + ("; kb-search (see WRITE BRIEF FIRST)." if task.get("phase") == "brief" else ".")
               + "\nUntracked scratch files: `taskflow-scratch rm <relative path>` or `taskflow-scratch mv <relative src> <relative dst>`.")
    if task.get("refs"):
        out.append("## REFERENCE FILES (read-only copies from other repos)\n" + "\n".join(
            f".taskflow-refs/{r['repo']}" + (f"@{r['rev']}" if r.get("rev") else "") + f"/{r['path']}"
            for r in task["refs"]))
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


# r8b canary (FIX-HARNESS 2026-11-22, fix 3): workers could not run their own acceptance. They prefixed it with
# `cd <lane> && `, appended `; echo "EXIT: $?"`, or re-ran the same test runner with another selection. Each allowed
# command also gets those shapes; the runner prefix (`bash .../orch-py.sh -m pytest`, `python3 -m pytest`) is allowed
# with any arguments. The deny list still wins (redirects, sh pipes, git writes).
_RUNNER_PREFIX = re.compile(r"^((?:bash\s+)?\S*orch-py\.sh\s+-m\s+pytest|python3?\s+-m\s+pytest|pytest)\b")
EXIT_TAILS = ["; echo *", " ; echo *", " 2>&1; echo *"]


def acceptance_patterns(task: dict, lane: Path | str | None = None) -> list[str]:
    """Shell allow patterns for the task's acceptance / test commands (exact, with args, runner prefix, cd-lane)."""
    out: list[str] = []
    for c in allowed_commands(task):
        bases = [c]
        m = _RUNNER_PREFIX.match(c)
        if m:
            bases.append(m.group(1))
            if m.group(1).startswith("bash "):
                bases.append(m.group(1)[5:].lstrip())
        for b in bases:
            pats = [b, b + " *"]
            if lane:
                pats += [f"cd {lane} && {p}" for p in (b, b + " *")]
            for p in pats:
                if p not in out:
                    out.append(p)
    if lane and out:
        out.append(f"cd {lane}")
    return out


# r8e canary (FIX-HARNESS 2026-11-23, fix 1): TU-GR-1 / LOOP-62 nothink spent ~15 of 30 steps on denied one-line
# probes (`orch-py.sh -c ...`) and wrote scratch files to get around it. Inside the lane the row's own orch-py.sh may
# run `-c <code>` and a lane-relative .py file. An absolute, `..` or `~` script path stays denied (deny list wins).
_ORCH = re.compile(r"^(?:bash\s+)?(\S*orch-py\.sh)\b")
SCRATCH_DENY = ["*orch-py.sh /*", "*orch-py.sh ..*", "*orch-py.sh ~*", "*orch-py.sh *../*"]


def scratch_patterns(task: dict, lane: Path | str | None = None) -> list[str]:
    """Allow patterns for the row's orch-py.sh with `-c` / a lane .py, derived from the task's own runner path."""
    out: list[str] = []
    for c in allowed_commands(task):
        m = _ORCH.match(c)
        if not m:
            continue
        orch = m.group(1)
        for pre in (f"bash {orch}", orch):
            for p in (f"{pre} -c *", f"{pre} *.py", f"{pre} *.py *"):
                for q in ([p] + ([f"cd {lane} && {p}"] if lane else [])):
                    if q not in out:
                        out.append(q)
    return out


# NOFOLD deleted tracked READMEs with raw rm, including from a shell workdir set to a subdirectory.
# The helper validates the actual argv against the current worktree before touching files.
CLEANUP_ALLOW = ["taskflow-scratch rm *", "taskflow-scratch mv *"]
CLEANUP_DENY = ["rm", "rm *", "mv", "mv *", "*/rm", "*/rm *", "*/mv", "*/mv *"]
CLEANUP_DENY += [f"taskflow-scratch *{c}*" for c in ";&|$`<>"]


def install_scratch_command(run_dir: Path, lane: Path) -> Path:
    """Provide the checked cleanup command in the worker's private PATH, bound to its lane."""
    bin_dir = (run_dir / "worker-bin").resolve()
    bin_dir.mkdir(parents=True, exist_ok=True)
    helper = Path(__file__).with_name("scratch_files.py").resolve()
    command = bin_dir / "taskflow-scratch"
    command.write_text(f'#!/bin/sh\nexec {shlex.join([sys.executable, "-I", str(helper), str(lane.resolve())])} "$@"\n',
                       encoding="utf-8")
    command.chmod(0o700)
    return bin_dir


def write_config(run_dir: Path, base_url: str, model_id: str, task: dict, ctx: int = 65536,
                 out_tokens: int = 4096, lane: Path | str | None = None) -> Path:
    """Per-run opencode config (XDG_CONFIG_HOME/opencode/opencode.json) + the POLICY instructions file.
    Everything that reaches the prompt is task-independent; only bash allow patterns vary (not prompt text)."""
    cfg_dir = run_dir / "xdg-config" / "opencode"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    pol = policy_file()
    bash = {"*": "deny"}
    for ro in READ_ONLY:
        bash[ro] = "allow"
    for ro in RETRIEVAL:
        bash[ro] = "allow"
    for ro in PIPE_FILTERS:
        bash[ro] = "allow"
    acc_pats = acceptance_patterns(task, lane) + scratch_patterns(task, lane)
    for c in acc_pats:
        bash[c] = "allow"
    for base in [k for k, v in bash.items() if v == "allow"]:
        for tail in PIPE_TAILS:
            bash[base + tail] = "allow"
    for base in acc_pats:
        for tail in EXIT_TAILS:
            bash[base + tail] = "allow"
    for c in CLEANUP_ALLOW:
        bash[c] = "allow"
    for d in BASH_DENY + SCRATCH_DENY + CLEANUP_DENY:
        bash.pop(d, None)  # A task-supplied command may already have inserted this pattern.
        bash[d] = "deny"
    edit_perm: str | dict = "allow"
    if lane:                    # r8g fix 2: the built-in worktree_remove asserts `edit` on the lane directory itself
        lp = str(lane).rstrip("/")
        rp = os.path.realpath(lp)
        edit_perm = {"*": "allow", **{v: "deny" for q in dict.fromkeys([lp, rp]) for v in (q, q + "/", q + "/.")}}
    cfg = {
        "$schema": "https://opencode.ai/config.json",
        "snapshot": False,
        "autoupdate": False,
        "share": "disabled",
        "instructions": [str(pol)],
        # H1 (prefix-cache brief 2026-11-20): r2 single tool bursts reached 20-23k tokens and drove compaction
        "tool_output": {"max_lines": TOOL_MAX_LINES, "max_bytes": TOOL_MAX_BYTES},
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
        # H2: no title side-request (r1: ~6% of computed tokens, evicts the np1 slot); r3: an uncapped side request
        # (summary/small-model path) decoded 31,896 tokens in 714 s -> summary off too, and the proxy caps max_tokens.
        "agent": {"title": {"disable": True}, "summary": {"disable": True}, AGENT: {
            "description": "taskflow single-box worker", "mode": "primary",
            "steps": int(task["budget"]["turns"]),
            "permission": {"read": "allow", "edit": edit_perm, "glob": "allow", "grep": "allow", "list": "allow",
                           "bash": bash, "shell": bash, "question": "deny",
                           # r1 canary: the JS `execute` sandbox ate 13 of 14 steps on syntax errors; image tool is noise
                           "execute": "deny", "experimental_image_generate": "deny", "opencode_*": "deny", "opencode_worktree_remove": "deny", "opencode_worktree_create": "deny",
                           "opencode_worktree_list": "deny", "opencode.*": "deny", "webfetch": "deny", "websearch": "deny", "task": "deny",
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
    brief = None
    for ln in reversed(final.splitlines()):
        if BRIEF_RESULT in ln:
            raw = ln.split(BRIEF_RESULT, 1)[1].strip()
            try:
                brief = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
            except ValueError:
                brief = {"unparseable": raw[:300]}
            break
    return {"usage": usage, "result": result, "brief": brief, "text_tail": final[-1500:], "errors": errors, "tools": tools,
            "tool_errors": tool_errors, "edits": edits}


def spawn(task: dict, cwd: Path, run_dir: Path, base_url: str, family: str = "local",
          timeout_s: int | None = None) -> dict:
    """Run one worker to completion (or the wall cap). Returns {rc, wall_s, usage, result, model, tier, ...}."""
    run_dir.mkdir(parents=True, exist_ok=True)
    model_id = model_for(task.get("tier"), family)
    write_config(run_dir, base_url, model_id, task, ctx=int(task["budget"].get("ctx", 65536)), lane=cwd)  # = server per-slot ctx
    bin_dir = install_scratch_command(run_dir, cwd)
    prompt = task_suffix(task, excerpts_for(task, cwd))
    (run_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    env = dict(os.environ,
               XDG_CONFIG_HOME=str(run_dir / "xdg-config"), XDG_DATA_HOME=str(run_dir / "xdg-data"),
               XDG_STATE_HOME=str(run_dir / "xdg-state"), XDG_CACHE_HOME=str(run_dir.parent / "xdg-cache"),
               PATH=os.pathsep.join((str(bin_dir), os.environ.get("PATH", os.defpath))),
               OPENCODE_DISABLE_AUTOUPDATE="1", PWD=str(cwd),
               # r6: the epyc-root lane's project plugin (.opencode/plugins/filesystem-containment.ts) blocked worker
               # writes, and Claude-Code compat would pull the lane's CLAUDE.md/.claude skills -> isolate the worker
               OPENCODE_DISABLE_PROJECT_CONFIG="1", OPENCODE_CONFIG_PROJECT_DISABLE="1", OPENCODE_DISABLE_CLAUDE_CODE="1",
                # r2: opencode resolves paths from $PWD, not the process cwd
               OPENCODE_DISABLE_LSP_DOWNLOAD="1", NO_COLOR="1")
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
            "result": ev["result"], "brief": ev.get("brief"), "errors": ev["errors"], "tools": ev["tools"], "nudged": nudged,
            "tool_errors": ev["tool_errors"], "edits": ev["edits"], "text_tail": ev["text_tail"]}
