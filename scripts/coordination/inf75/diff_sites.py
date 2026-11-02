#!/usr/bin/env python3
"""Extract changed source line coordinates from a zero-context Git patch.

This is an aid for preparing P1c's footprint, not a semantic footprint or a
coverage witness. Insertions/deletions have no corresponding line on the other
side; an empty side must never be treated as evidence of non-execution.
Only ordinary textual, unquoted same-path patches are accepted.
"""
import re


class DiffError(ValueError):
    pass


_FILE = re.compile(r"diff --git a/([^\s]+) b/([^\s]+)\Z")
_HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?\Z")


def extract_changed_lines(patch: str) -> dict:
    """Return line numbers on each side, rejecting unsupported patch syntax."""
    if not isinstance(patch, str) or not patch:
        raise DiffError("empty patch")
    files = {}
    current = None
    old_left = new_left = old_line = new_line = None
    old_end = new_end = 0
    headers = []
    path = None
    mode = None
    for line in patch.removesuffix("\n").split("\n"):
        match = _FILE.fullmatch(line)
        if match:
            if current is not None and (old_left != 0 or new_left != 0):
                raise DiffError("missing or truncated hunk")
            a, b = match.groups()
            if a != b or a in files or '"' in a or "\\" in a:
                raise DiffError("unsupported or duplicate path")
            current = files[a] = {"anchor_lines": [], "candidate_lines": []}
            path = a
            mode = None
            headers = []
            old_end = new_end = 0
            old_left = new_left = None
            continue
        if current is None:
            raise DiffError("missing file header")
        match = _HUNK.fullmatch(line)
        if match:
            if old_left not in (None, 0) or new_left not in (None, 0):
                raise DiffError("truncated hunk")
            old_line, old_count, new_line, new_count = match.groups()
            old_line, new_line = int(old_line), int(new_line)
            old_left = int(old_count) if old_count is not None else 1
            new_left = int(new_count) if new_count is not None else 1
            expected = ["--- /dev/null" if mode == "new" else "--- a/" + path,
                        "+++ /dev/null" if mode == "deleted" else "+++ b/" + path]
            if headers != expected or (mode == "new" and old_left) or (mode == "deleted" and new_left):
                raise DiffError("missing or mismatched file headers")
            old_start = old_line - (old_left > 0)
            new_start = new_line - (new_left > 0)
            if (not (old_left or new_left) or old_start < old_end or new_start < new_end
                    or old_start - old_end != new_start - new_end):
                raise DiffError("invalid or overlapping hunk coordinates")
            old_end, new_end = old_start + old_left, new_start + new_left
            continue
        if old_left is None and line in ("new file mode 100644", "deleted file mode 100644") and not headers and mode is None:
            mode = "new" if line.startswith("new") else "deleted"
            continue
        if old_left is None and line.startswith("index ") and not headers:
            continue
        if old_left is None and line.startswith(("--- ", "+++ ")):
            headers.append(line)
            continue
        if line == r"\ No newline at end of file" and old_left is not None:
            continue
        if old_left is None or not line or line[0] not in "+-":
            raise DiffError("unsupported patch line")
        if line[0] == "-":
            if old_left <= 0 or old_line <= 0:
                raise DiffError("invalid anchor count")
            current["anchor_lines"].append(old_line)
            old_line += 1
            old_left -= 1
        else:
            if new_left <= 0 or new_line <= 0:
                raise DiffError("invalid candidate count")
            current["candidate_lines"].append(new_line)
            new_line += 1
            new_left -= 1
    if old_left != 0 or new_left != 0:
        raise DiffError("missing or truncated final hunk")
    return {"status": "PARTIAL_UNVERIFIED", "files": files}
