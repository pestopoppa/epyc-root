#!/usr/bin/env python3
"""Scan a Bash command for an INFERENCE LAUNCH that acquires no region claim.

REG-ENF-2 (handoffs/active/coordination-and-churn-pipeline.md, intake 2026-11-06,
2609.26682): tool-use authorization moves from prose to the tool boundary. The prose
rule is INVARIANTS.md #5 ("Claims are ACQUIRED, never observed") and #8 (compute windows
are granted per policy) plus OPERATING_CONSTRAINTS.md -> *Inference and Benchmarks*.

SCOPED TO INVOCATIONS, NOT TEXT: uses the shared `shell_scan.lex()` so a heredoc, a
quoted string, a grep pattern or a commit message that MENTIONS llama-bench passes.

A segment is an inference launch when its command word (after env assignments and
runner prefixes such as nohup/setsid/taskset/numactl/timeout/env/nice) is one of
LAUNCH_BINARIES, path-qualified or not, and it is not an informational call
(--help/-h/--version/--list-devices).

The command ACQUIRES a claim when, in the same command text (quoted data kept),
a `flock` invocation names a region lock file (cpu_region.*.lock,
gpu_device.*.lock, gpu_quiet.lock) — the kernel-held claim of invariant 5 — or
the launch runs under a sanctioned claiming wrapper (filler_run*.sh,
build_locked.sh is NOT one: it serializes builds, not inference). Observing that
some lock is held by someone is deliberately NOT accepted (invariant 5: observing
is TOCTOU and proves nothing about who holds it).

Verdicts: `unclaimed-launch`, `claimed-launch`, `clean`.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shell_scan import SEPARATORS, lex, lex_text  # noqa: E402

LAUNCH_BINARIES = (
    "llama-server", "llama-bench", "llama-cli", "llama-perplexity",
    "llama-batched-bench", "llama-speculative", "llama-speculative-simple",
    "llama-mtmd-cli", "llama-run", "llama-simple", "llama-parallel",
    "llama-lookup", "llama-imatrix", "llama-embedding", "llama-sweep-bench",
    "whisper-cli", "whisper-server", "whisper-bench",
)
_RUNNERS = {"nohup", "setsid", "env", "nice", "ionice", "time", "exec", "stdbuf",
            "taskset", "numactl", "timeout", "chrt", "sudo"}
_INFO = re.compile(r"(?:^|\s)(?:-h|--help|--version|--list-devices|--usage)(?:\s|$)")
_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_LOCKFILE = r"(?:cpu_region\.[^\s'\"]+\.lock|gpu_device\.[^\s'\"]+\.lock|gpu_quiet\.lock)"
_FLOCK_CLAIM = re.compile(r"(?:^|[\s/;&|(`])flock\b[^;&|\n]*?" + _LOCKFILE)
_C_BODY = re.compile(r"""(?:^|[\s/;&|(])(?:bash|sh|zsh|flock)\b(?:[^;&|\n'"]|'[^']*'|"[^"]*")*?\s-[A-Za-z]*c\s+(['"])(.*?)\1""", re.S)
_WRAPPER = re.compile(r"(?:^|[\s/])filler_run[0-9]*\.sh\b")


def _command_word(seg: str) -> tuple[str, str] | None:
    """(basename of the command word, rest) after env assignments and runner prefixes."""
    words = seg.split()
    i = 0
    while i < len(words):
        w = words[i]
        base = w.rsplit("/", 1)[-1]
        if _ASSIGN.match(w) or w.startswith("-"):
            i += 1
            continue
        if base == "flock":                       # flock [opts] LOCKFILE CMD...
            i += 1
            while i < len(words) and words[i].startswith("-"):
                i += 1 + (words[i] in {"-w", "--timeout", "-E", "--conflict-exit-code"})
            i += 1                                # the lock file
            continue
        if base in {"bash", "sh", "zsh"} and i + 1 < len(words) and words[i + 1].startswith("-") \
                and "c" in words[i + 1].lstrip("-"):
            i += 2                                # bash -c 'CMD' (quoted body kept by caller)
            continue
        if base in _RUNNERS:
            i += 1
            # taskset -c LIST / numactl --opts / timeout N: skip a following non-flag operand
            if base in {"taskset", "timeout", "chrt", "ionice", "nice"} and i < len(words) \
                    and not words[i].startswith("-") and re.match(r"^[0-9][0-9,\-ksmh.]*$", words[i]):
                i += 1
            continue
        if re.match(r"^[0-9][0-9,\-]*$", w):   # taskset -c 0-47 operand
            i += 1
            continue
        return base, " ".join(words[i + 1:])
    return None


def launch_segments(command: str) -> list[str]:
    out = []
    for seg in lex(command):
        cw = _command_word(seg)
        if cw and cw[0] in LAUNCH_BINARIES and not _INFO.search(" " + cw[1] + " "):
            out.append(seg)
    return out


def _code_with_data(command: str) -> str:
    """Command text with comments/heredoc bodies removed but quoted data restored."""
    code = lex_text(command, keep_quoted=True)
    return re.sub("[\ue000-\ue07f]", lambda m: chr(ord(m.group()) - 0xE000), code)


def claimed(command: str) -> bool:
    # Keep quoted data: `flock /x/cpu_region.GLOBAL.q0.lock "llama-bench ..."` is the
    # canonical form and its lock path is often quoted. Heredoc bodies/comments are gone.
    # The flock must WRAP the launch: same segment, launch after the lock path.
    # `flock LOCK true; llama-bench ...` releases before the launch and is not a claim.
    code = _code_with_data(command)
    if _WRAPPER.search(code):
        return True
    for m in _C_BODY.finditer(code):          # flock REGION.lock -c 'cd x; llama-bench ...'
        head = code[m.start():m.start(2)]
        if re.search(r"\bflock\b", head) and re.search(_LOCKFILE, head) and launch_segments(m.group(2)):
            return True
    for seg in SEPARATORS.split(code.replace("'", " ").replace('"', " ")):
        m = _FLOCK_CLAIM.search(seg)
        if m and any(b in seg[m.end():] for b in LAUNCH_BINARIES):
            return True
    return False


def verdict(command: str) -> str:
    if not launch_segments(command):
        # A launch hidden inside a quoted `bash -c '...'` / `flock LOCK -c '...'`
        # body: re-scan with the quotes opened so it is still seen as a launch.
        # Only `-c` bodies are opened: a multi-line commit message that mentions a
        # launch on its own line is data, and must stay clean.
        bodies = [m.group(2) for m in _C_BODY.finditer(_code_with_data(command))]
        if not any(launch_segments(b) for b in bodies):
            return "clean"
    return "claimed-launch" if claimed(command) else "unclaimed-launch"


def main() -> int:
    data = sys.stdin.read()
    if not data.strip():
        print("error: empty stdin — refusing to emit a verdict", file=sys.stderr)
        return 2
    print(verdict(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
