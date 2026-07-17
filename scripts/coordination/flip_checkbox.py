#!/usr/bin/env python3
"""B8 — anchored, safe checkbox flip in a handoff file.

The batch loop is authorized to flip handoff checkboxes directly (locked
autonomy policy), but every flip must be recorded in wrap-up and must be
*provably* surgical. This helper enforces the anchored-edit + uniqueness
discipline used in prior wrap-ups:

  * The anchor is the exact unchecked-checkbox line for a token:
        ``- [ ] **<token>`` (with a right word boundary after <token>).
  * The token must match EXACTLY ONE such line. 0 matches -> error (nothing to
    flip / already flipped). >1 matches -> error (ambiguous; refuse to guess).
  * The flip rewrites only that one line:
        ``- [ ] **<token>...``  ->  ``- [x] **<token>... ✅ <date> (<note>)``
    Every other byte of the file is untouched.
  * ``dry_run`` defaults to True: the diff is computed and returned but the file
    is never written unless the caller passes ``dry_run=False`` explicitly.

Because the anchor only matches ``- [ ]`` (unchecked), re-running a flip on an
already-flipped token yields 0 matches and raises — the operation is safe
against accidental re-run / double-append.

Stdlib only.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


class CheckboxFlipError(RuntimeError):
    """Raised when an anchor is missing, ambiguous, or a flip is unsafe."""


# ``- [ ]`` then a bold token ``**<token>`` with a right boundary so that
# token ``EV-1`` does NOT match ``- [ ] **EV-11``. Leading indentation (nested
# list items) is allowed. Only the UNCHECKED box matches.
def _anchor_re(token: str) -> re.Pattern[str]:
    return re.compile(r"^(\s*)- \[ \] \*\*" + re.escape(token) + r"(?![\w-])")


@dataclass
class FlipSpec:
    """One requested flip. ``handoff_path`` may be omitted when passed to
    :func:`flip_many` alongside a shared path."""

    checkbox_token: str
    date: str
    evidence_note: str = ""
    handoff_path: str | None = None


def _find_anchor_lines(lines: list[str], token: str) -> list[int]:
    pat = _anchor_re(token)
    return [i for i, line in enumerate(lines) if pat.match(line)]


def _flip_line(line: str, date: str, evidence_note: str) -> str:
    """Flip a single matched line: check the box and append the ✅ stamp.

    Preserves indentation and the existing trailing text; only the checkbox
    glyph changes and the stamp is appended.
    """
    # Replace the first (checkbox) occurrence of ``- [ ]`` with ``- [x]``.
    flipped = line.replace("- [ ]", "- [x]", 1)
    stamp = f" ✅ {date}"
    note = (evidence_note or "").strip()
    if note:
        stamp += f" ({note})"
    return flipped.rstrip() + stamp


def _apply_one(text: str, token: str, date: str, evidence_note: str) -> tuple[str, str]:
    """Apply one flip to ``text``. Returns ``(new_text, changed_line_preview)``.

    Raises :class:`CheckboxFlipError` on 0 or >1 anchor matches.
    """
    # keepends so we can reconstruct byte-for-byte (preserving trailing newline).
    lines = text.splitlines(keepends=True)
    stripped = [ln.splitlines()[0] if ln.splitlines() else "" for ln in lines]
    idxs = _find_anchor_lines(stripped, token)
    if len(idxs) == 0:
        raise CheckboxFlipError(
            f"no unchecked anchor '- [ ] **{token}' found "
            f"(already flipped, or token wrong)"
        )
    if len(idxs) > 1:
        raise CheckboxFlipError(
            f"ambiguous: {len(idxs)} unchecked anchors match token '{token}' "
            f"(lines {[i + 1 for i in idxs]}); refusing to guess"
        )
    i = idxs[0]
    original_line = lines[i]
    # Preserve the original line ending.
    newline = ""
    if original_line.endswith("\r\n"):
        newline = "\r\n"
    elif original_line.endswith("\n"):
        newline = "\n"
    body = original_line[: len(original_line) - len(newline)]
    new_body = _flip_line(body, date, evidence_note)
    lines[i] = new_body + newline
    return "".join(lines), new_body


def _unified_diff(before: str, after: str, path: str) -> str:
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        n=1,
    )
    return "".join(diff)


def flip(
    handoff_path: str | Path,
    checkbox_token: str,
    date: str,
    evidence_note: str = "",
    dry_run: bool = True,
) -> str:
    """Flip a single ``- [ ] **<token>`` checkbox to ``- [x] ... ✅ <date> (<note>)``.

    Returns a unified diff of the change. With ``dry_run=True`` (default) the
    file is NOT written. Raises :class:`CheckboxFlipError` on 0 or >1 matches.
    """
    path = Path(handoff_path)
    try:
        before = path.read_text()
    except FileNotFoundError as exc:
        raise CheckboxFlipError(f"handoff file not found: {path}") from exc

    after, _ = _apply_one(before, checkbox_token, date, evidence_note)
    diff = _unified_diff(before, after, str(path))
    if not dry_run:
        path.write_text(after)
    return diff


def flip_many(
    flips: Iterable[FlipSpec | dict[str, Any]],
    handoff_path: str | Path | None = None,
    date: str | None = None,
    dry_run: bool = True,
) -> dict[str, str]:
    """Apply several flips, grouped by file. Returns ``{path: unified_diff}``.

    Each item is a :class:`FlipSpec` or an equivalent dict with
    ``checkbox_token`` (and optionally ``handoff_path``, ``date``,
    ``evidence_note``). ``handoff_path``/``date`` here supply shared defaults.

    All flips for a file are applied to that file's in-memory content in order;
    uniqueness is re-checked at each step. Nothing is written unless
    ``dry_run=False``. If ANY flip fails, no file is written (all-or-nothing).
    """
    # Normalize and group by resolved path.
    grouped: dict[str, list[FlipSpec]] = {}
    for item in flips:
        if isinstance(item, dict):
            spec = FlipSpec(
                checkbox_token=str(item["checkbox_token"]),
                date=str(item.get("date") or date or ""),
                evidence_note=str(item.get("evidence_note") or ""),
                handoff_path=item.get("handoff_path") or handoff_path,
            )
        else:
            spec = FlipSpec(
                checkbox_token=item.checkbox_token,
                date=item.date or (date or ""),
                evidence_note=item.evidence_note,
                handoff_path=item.handoff_path or handoff_path,
            )
        if not spec.handoff_path:
            raise CheckboxFlipError(
                f"flip for token '{spec.checkbox_token}' has no handoff_path"
            )
        if not spec.date:
            raise CheckboxFlipError(
                f"flip for token '{spec.checkbox_token}' has no date"
            )
        grouped.setdefault(str(Path(spec.handoff_path)), []).append(spec)

    diffs: dict[str, str] = {}
    pending_writes: dict[str, str] = {}
    for path_str, specs in grouped.items():
        path = Path(path_str)
        try:
            before = path.read_text()
        except FileNotFoundError as exc:
            raise CheckboxFlipError(f"handoff file not found: {path}") from exc
        content = before
        for spec in specs:
            content, _ = _apply_one(
                content, spec.checkbox_token, spec.date, spec.evidence_note
            )
        diffs[path_str] = _unified_diff(before, content, path_str)
        pending_writes[path_str] = content

    if not dry_run:
        for path_str, content in pending_writes.items():
            Path(path_str).write_text(content)
    return diffs
