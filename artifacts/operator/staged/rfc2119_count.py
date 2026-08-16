#!/usr/bin/env python3
"""Count directive (RFC-2119 + project-idiom) keyword occurrences in a markdown file.

Used as the P1-4 proof gate: moving incident STORIES to an appendix must not change
the number of DIRECTIVES. Run before and after; the totals must match exactly.
"""
import re
import sys

# RFC 2119 proper, plus the four project idioms that carry the same force in this
# corpus ("never", "always", "do not", "refuse"). Multi-word forms are counted
# first and their spans removed so "MUST NOT" is not also counted as "MUST".
PATTERNS = [
    r"MUST NOT", r"SHALL NOT", r"SHOULD NOT", r"MUST", r"SHALL", r"SHOULD",
    r"REQUIRED", r"RECOMMENDED", r"MAY NOT", r"MAY", r"OPTIONAL",
    r"NEVER", r"ALWAYS", r"DO NOT", r"DON'T", r"REFUSES?", r"REFUSAL",
    r"MANDATORY", r"FORBIDDEN", r"PROHIBITION",
]


def counts(text: str) -> dict:
    out = {}
    remaining = text
    for pat in PATTERNS:
        rx = re.compile(r"\b" + pat + r"\b", re.IGNORECASE)
        found = rx.findall(remaining)
        out[pat] = len(found)
        remaining = rx.sub(" ", remaining)
    out["_TOTAL"] = sum(v for k, v in out.items() if not k.startswith("_"))
    return out


def main() -> int:
    for path in sys.argv[1:]:
        with open(path, encoding="utf-8") as fh:
            c = counts(fh.read())
        parts = " ".join(f"{k}={v}" for k, v in c.items() if v and not k.startswith("_"))
        print(f"{path}\n  TOTAL={c['_TOTAL']}  {parts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
