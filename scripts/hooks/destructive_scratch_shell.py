"""Quote-aware shell substitution masking for the scratch invocation scanner.

Mask before splitting words/commands, restore after. This does not evaluate any
shell syntax. An unmatched substitution retains the scanner's fail-open boundary.
"""
from __future__ import annotations


def _end(text, start):
    if text[start] == "`":
        i = start + 1
        while i < len(text):
            if text[i] == "\\":
                i += 2
            elif text[i] == "`":
                return i + 1
            else:
                i += 1
        return None
    depth, quote, i = 1, None, start + 2
    while i < len(text):
        c = text[i]
        if c == "\\" and quote != "'":
            i += 2
            continue
        if quote is not None:
            if c == quote:
                quote = None
        elif c in "'\"":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def mask_substitutions(text):
    prefix = "__EPYC_SCRATCH_SUBSTITUTION_"
    while prefix in text:
        prefix += "_"
    result, replacements, quote, i = [], [], None, 0
    while i < len(text):
        c = text[i]
        if c == "\\" and quote != "'" and i + 1 < len(text):
            result.append(text[i:i + 2])
            i += 2
            continue
        if quote != "'" and (text.startswith("$(", i) or c == "`"):
            end = _end(text, i)
            if end is not None:
                expression = text[i:end]
                body = expression[1:-1] if c == "`" else expression[2:-1]
                marker = f"{prefix}{len(replacements)}__"
                replacements.append((marker, expression, body))
                result.append(marker)
                i = end
                continue
        if quote is not None:
            if c == quote:
                quote = None
        elif c in "'\"":
            quote = c
        result.append(c)
        i += 1
    return "".join(result), replacements
