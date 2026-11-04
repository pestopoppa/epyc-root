#!/usr/bin/env python3
"""PreToolUse(AskUserQuestion) hook: question discipline enforced by the harness (2026-11-03 session review item 9).

On 2026-11-03 the main thread blocked 52 minutes on a three-part question whose every option was marked "Recommended",
while two grants died unobserved and the host sat idle; a fifth question was asked while the operator typed "RUN IT NOW".
Prose rules did not fire; this hook denies the call (exit 2, one line, cause + fix) when, deterministically:

  1. the question bundles more than one item            -> ask ONE item, or act;
  2. an option is marked Recommended/default             -> you already know the answer: act on it, report after;
  3. the last operator message was an imperative          -> the imperative maps to a tool call this turn, not a question
     (NOW / JUST RUN / RUN IT / DO SOMETHING / LAUNCH ... in the transcript's last user turn);
  4. this session owns a live launch                      -> a thread that owns live compute never blocks
     (a `dryrun/<id>/DIRECT.json` or `grants/<id>.grant` whose record carries this hook's session_id; run_direct.sh
     records it when CLAUDE_SESSION_ID is in its environment).

Everything else passes. Malformed input passes (the hook never blocks on its own bug). Flags dir: ROWFLOW_FLAGS.
"""
import glob
import json
import os
import re
import sys

IMPERATIVE = re.compile(r"\b(NOW|JUST RUN|RUN IT|DO SOMETHING|LAUNCH (IT|THE)|GO AHEAD|STOP ASKING)\b", re.I)
RECOMMENDED = re.compile(r"\b(recommended|default)\b", re.I)
FLAGS = os.environ.get("ROWFLOW_FLAGS", "/mnt/raid0/llm/tmp/compute-flags")


def last_user_text(transcript_path):
    """Text of the last human turn in a Claude Code JSONL transcript, '' when unreadable."""
    last = ""
    try:
        with open(transcript_path, errors="replace") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("type") != "user":
                    continue
                msg = rec.get("message") or {}
                content = msg.get("content")
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = " ".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
                else:
                    continue
                if text.strip() and not text.lstrip().startswith("<"):   # tool results / system reminders are not operator turns
                    last = text
    except OSError:
        return ""
    return last


def live_launch(session_id, flags=FLAGS):
    """A DIRECT.json or .grant record this session wrote (session_id recorded), or None."""
    if not session_id:
        return None
    for p in glob.glob(os.path.join(flags, "dryrun", "*", "DIRECT.json")):
        try:
            rec = json.load(open(p))
        except (OSError, ValueError):
            continue
        if rec.get("session_id") == session_id and not rec.get("ended"):
            return rec.get("id") or os.path.basename(os.path.dirname(p))
    for p in glob.glob(os.path.join(flags, "grants", "*.grant")):
        try:
            if f"session={session_id}" in open(p).read():
                return os.path.basename(p)[:-6]
        except OSError:
            continue
    return None


def verdict(hook_input, flags=FLAGS, last_text=None):
    """None = allow; else the one-line denial (cause; fix)."""
    ti = hook_input.get("tool_input") or {}
    qs = ti.get("questions")
    if not isinstance(qs, list):
        return None
    if len(qs) > 1:
        return f"BLOCKED: {len(qs)} items in one question; fix: ask the ONE decision only the operator can make, or act on the rest first"
    for q in qs:
        for o in (q.get("options") or []) if isinstance(q, dict) else []:
            label = " ".join(str(o.get(k, "")) for k in ("label", "description")) if isinstance(o, dict) else str(o)
            if RECOMMENDED.search(label):
                return "BLOCKED: an option is marked Recommended/default; fix: you already know the answer - do it and report, do not ask"
    text = last_user_text(hook_input.get("transcript_path", "")) if last_text is None else last_text
    m = IMPERATIVE.search(text or "")
    if m:
        return f"BLOCKED: the operator's last message is an imperative ({m.group(0)!r}); fix: make the tool call it asks for in this turn"
    rid = live_launch(hook_input.get("session_id"), flags)
    if rid:
        return f"BLOCKED: this session owns a live launch ({rid}); fix: a thread that owns compute never blocks - watch it, report measured utilisation, ask later"
    return None


def main():
    try:
        hook_input = json.load(sys.stdin)
    except ValueError:
        return 0
    if hook_input.get("tool_name") not in (None, "AskUserQuestion"):
        return 0
    v = verdict(hook_input)
    if v:
        print(v, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
