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

2026-11-04 fix (four legitimate decision packages blocked): CLAUDE.md's decision-package contract REQUIRES the
recommended option first, labelled "(Recommended)", and the tool takes up to 4 questions. So:
  1'. up to 4 DISTINCT questions pass; duplicates or >4 are denied;
  2'. one "(Recommended)" option per question passes; a question with several marked options is denied
      (a mark that does not discriminate is not a recommendation);
  3'. the imperative test is case-sensitive for bare NOW (shouted), and is skipped when the operator asked for the
      question itself ("decision tool", "options", "ask me", ...) or when every question is an operator-only decision
      (ratification, signature, ack, approval, authorisation, human-only path);
  4 is unchanged and applies to every question: a thread that owns live compute never blocks.
2026-11-20 fix (AK audit C1; refused 3x on 11-18T23:36Z after the operator wrote "Use the decision tool!"):
  5. an operator turn that EXPLICITLY requests the tool ("decision tool", "decision package", "AskUserQuestion",
     "ask me") allows the call outright, ahead of rules 1-4; the operator asked for exactly this call;
  6. operator text delivered mid-turn arrives wrapped in a <system-reminder> ("The user sent the following message:
     ..."); the old reader skipped every text starting with "<", so it fell back to an OLDER turn (often one with
     NOW in it). The reader now unwraps that form and strips other tags instead of skipping the whole turn;
  7. every refusal names the operator text it matched (first 160 chars), so a misfire is visible in the record.
Everything else passes. Malformed input passes (the hook never blocks on its own bug). Flags dir: ROWFLOW_FLAGS.
"""
import glob
import json
import os
import re
import sys

IMPERATIVE = re.compile(r"\bNOW\b|\b(?i:JUST RUN|RUN IT|DO SOMETHING|LAUNCH (IT|THE)|GO AHEAD|STOP ASKING)\b")
RECOMMENDED = re.compile(r"\b(recommended|default)\b", re.I)
ASKS_FOR_QUESTION = re.compile(r"decision (tool|package)|AskUserQuestion|\boptions?\b|trade-?offs?|\bask me\b|which (one|option)", re.I)
OPERATOR_ONLY = re.compile(r"ratif|signature|\bsign[- ]?off\b|\bsign\b|\back(nowledge\w*)?\b|approv|authori[sz]|human[- ]only|operator[- ]only", re.I)
EXPLICIT_REQUEST = re.compile(r"decision[- ](tool|package)|AskUserQuestion|\bask me\b", re.I)
RELAYED = re.compile(r"user sent (?:the following|a new) message[^:\n]*:\s*(.*)", re.I | re.S)
# S4: a negation up to three words before "ask me" ("do not ever ask me", "never again ask me"), or
# "again" after it ("don't ask me again"), is the opposite of a request.
NEGATED_ASK = re.compile(r"(?:n't|\bnot|\bnever|\bno need to|\bstop)\b(?:\W+\w+){0,3}?\W+ask(?:ing)? me\b|\bask me again\b", re.I)
# S2: background-task notifications are harness text (their summary repeats the MODEL's own Bash
# description), never an operator turn.
NOTIFICATION = re.compile(r"\[SYSTEM NOTIFICATION - NOT USER INPUT\]|<task-notification>", re.I)
TAG_BLOCK = re.compile(r"<(system-reminder|command-[a-z-]+|local-command-[a-z-]+)[^>]*>(.*?)</\1>", re.S)
MAX_QUESTIONS = 4
FLAGS = os.environ.get("ROWFLOW_FLAGS", "/mnt/raid0/llm/tmp/compute-flags")


def _unnegated(text):
    """Text with negated 'ask me' phrases removed, so they never count as a request."""
    return NEGATED_ASK.sub(" ", text)


def operator_text(text):
    """The operator-authored part of a user-turn string, '' when it holds none.

    Relayed mid-turn messages live inside a <system-reminder>; unwrap those, drop every other tag block."""
    relayed = []

    def repl(m):
        r = RELAYED.search(m.group(2))
        if r and r.group(1).strip():
            relayed.append(r.group(1).strip())
        return " "
    rest = TAG_BLOCK.sub(repl, text)
    if NOTIFICATION.search(rest) or NOTIFICATION.search(text) and not relayed:
        return relayed[-1] if relayed and not NOTIFICATION.search(relayed[-1]) else ""
    rest = re.sub(r"<[^>\n]{1,80}>", " ", rest).strip()
    return relayed[-1] if relayed else rest


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
                text = operator_text(text)    # tool results / bare reminders yield '' and are not operator turns
                if text.strip():
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
    qs = [x for x in qs if isinstance(x, dict)]
    text = last_user_text(hook_input.get("transcript_path", "")) if last_text is None else last_text
    text = text or ""
    if EXPLICIT_REQUEST.search(_unnegated(text)):
        return None                                   # rule 5: the operator asked for this call
    v = _verdict(qs, hook_input, flags, text)
    if v:
        snippet = " ".join(text.split())[:160]
        v += f" [operator text matched: {snippet!r}]" if snippet else " [operator text matched: none found]"
    return v


def _verdict(qs, hook_input, flags, text):
    if len(qs) > MAX_QUESTIONS:
        return f"BLOCKED: {len(qs)} items in one question (max {MAX_QUESTIONS}); fix: ask only the decisions only the operator can make, act on the rest first"
    keys = [(str(x.get("question", "")).strip().lower(), str(x.get("header", "")).strip().lower()) for x in qs]
    if len(set(keys)) != len(keys):
        return "BLOCKED: duplicate items in one question; fix: ask each distinct operator decision once"
    for x in qs:
        marked = 0
        for o in x.get("options") or []:
            label = " ".join(str(o.get(k, "")) for k in ("label", "description")) if isinstance(o, dict) else str(o)
            marked += bool(RECOMMENDED.search(label))
        if marked > 1:
            return "BLOCKED: several options marked Recommended/default in one question; fix: recommend ONE option (first), or act if they are all acceptable"
    operator_only = bool(qs) and all(OPERATOR_ONLY.search(f"{x.get('header', '')} {x.get('question', '')}") for x in qs)
    m = IMPERATIVE.search(text)
    asks = ASKS_FOR_QUESTION.search(_unnegated(text))
    if m and not operator_only and not asks:
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
