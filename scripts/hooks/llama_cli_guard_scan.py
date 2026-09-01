#!/usr/bin/env python3
"""Decide whether a shell command INVOKES llama-cli without a time bound.

Reads a command on stdin, prints one verdict:

    unbounded-invocation   llama-cli is invoked and nothing bounds its runtime
    bounded-invocation     llama-cli is invoked under `timeout`
    acked                  an EPYC_LLAMA_CLI_ACK=... assignment precedes it
    none                   llama-cli is not invoked (mentioned, listed, grepped, ...)

WHY THIS EXISTS (2026-09-01, self-inflicted): llama-cli does not exit when its
generation finishes. It re-enters its prompt loop, and because `read_input()`
discards the EOF signal that `console::readline()` returns, a closed or redirected
stdin makes every subsequent read return instantly -- an unbounded busy loop
printing "> ". One left running for 11h15m wrote 322 GB (taking the array from
480 G free to 191 G) and held a CPU region lock the whole time. The footgun was
already documented on 2026-08-28 and was hit anyway, which is why enforcement
lives here and not in a memory. The binary-level fix exists as a patch
(llama-cli-eof-fix-20260901) but cannot be applied to the FROZEN production
kernel, so unpatched binaries stay on this host indefinitely.

SCOPED TO INVOCATIONS, NOT TEXT -- quoted strings and heredocs are stripped
first, so documenting the rule, grepping for the name, or listing the binary all
pass. A guard that forbids its own documentation is a failure this repo has
already paid for once (C21).
"""
import os
import re
import shlex
import sys

ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
ACK_VAR = "EPYC_LLAMA_CLI_ACK"

# Wrappers that precede the real command; their options are skipped so the
# command underneath is still found.
WRAPPERS = {
    "taskset", "numactl", "nice", "ionice", "env", "stdbuf", "setsid",
    "nohup", "chrt", "time",
}
# Options of the wrappers above that consume a following value.
VALUE_OPTS = {
    "-c", "-C", "-n", "-N", "-m", "-p", "-i", "-o", "-e",
    "--cpunodebind", "--membind", "--physcpubind", "--interleave",
}


def strip_literals(cmd: str) -> str:
    """Remove heredoc bodies and quoted strings so only executable text remains."""
    for m in re.finditer(r"<<-?\s*'?\"?([A-Za-z_][A-Za-z0-9_]*)'?\"?", cmd):
        tag = m.group(1)
        end = re.search(rf"^\s*{re.escape(tag)}\s*$", cmd[m.end():], re.M)
        if end:
            cmd = cmd[: m.end()] + cmd[m.end() + end.end():]
    cmd = re.sub(r"'[^']*'", " '' ", cmd)
    cmd = re.sub(r'"[^"]*"', ' "" ', cmd)
    return cmd


def segments(cmd: str):
    """Split into command segments on shell separators."""
    return [s for s in re.split(r"(?:\|\||&&|[;\n|&])", cmd) if s.strip()]


def scan_segment(seg: str):
    try:
        toks = shlex.split(seg, comments=True)
    except ValueError:
        toks = seg.split()
    i = 0
    saw_timeout = False
    saw_ack = False
    while i < len(toks):
        tok = toks[i]
        if not tok:  # quote-stripping leaves empty tokens behind
            i += 1
            continue
        if ASSIGN.match(tok):
            if tok.startswith(ACK_VAR + "="):
                saw_ack = True
            i += 1
            continue
        if tok == "--":
            i += 1
            continue
        base = os.path.basename(tok)
        if base == "timeout":
            saw_timeout = True
            i += 1
            while i < len(toks) and toks[i].startswith("-"):
                i += 1
            if i < len(toks):  # the duration
                i += 1
            continue
        if base in WRAPPERS:
            i += 1
            while i < len(toks) and toks[i].startswith("-"):
                opt = toks[i]
                i += 1
                if opt in VALUE_OPTS and i < len(toks):
                    i += 1
            continue
        if base == "llama-cli":
            if saw_ack:
                return "acked"
            return "bounded-invocation" if saw_timeout else "unbounded-invocation"
        # Some other command heads this segment. llama-cli after it is an
        # argument (ls/grep/cat/...), UNLESS a `--` hands off to a real command
        # (region-lock run ... -- taskset ... llama-cli).
        rest = toks[i:]
        if "--" in rest:
            i += rest.index("--") + 1
            continue
        return "none"
    return "none"


def main() -> int:
    cmd = sys.stdin.read()
    if "llama-cli" not in cmd:
        print("none")
        return 0
    cleaned = strip_literals(cmd)
    verdicts = [scan_segment(s) for s in segments(cleaned)]
    for want in ("unbounded-invocation", "acked", "bounded-invocation"):
        if want in verdicts:
            print(want)
            return 0
    print("none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
