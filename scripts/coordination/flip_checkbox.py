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
        ``- [ ] **<token>...``  ->  ``- [x] **<token>... ✅ <date> [belief: …|no-belief: …] <verdict>``
    Every other byte of the file is untouched.

TICK SUFFIX (handoff standard Rev 1 §2.2, operator decision 1, 2026-11-19): ONE format,
``✅ <date> [belief: cc|clm_<id>] <verdict>`` or ``✅ <date> [no-belief: <reason>] <verdict>``.
``tick_suffix()`` is the only writer of it and ``parse_tick()`` the shared reader; ``parse_tick`` also
accepts the legacy forms (``✅ date (note)`` from this module before 2026-11-19, ``✅ date [belief: x]``
from churn/wrapup.py, ``✅ date <!-- worker-checkpoint:… -->`` from /log), and a tag
placed elsewhere on the line (``form='tag-elsewhere'``).

SINGLE WRITER — allow-list. Ticks are written only by these callers of this module, and by nothing else:
  * ``scripts/coordination/churn/wrapup.py``   (agents and the dispatcher: ``flip_line``)
  * ``scripts/coordination/worker_checkpoint.py`` (/log: ``tick_suffix``; the only ``allow_unrecorded`` user)
  * ``scripts/coordination/churn/file_result.py`` (row filing: ``flip`` with ``belief="cc"`` + result path)
  * the batch loop (``entry_verdict.py`` / ``compile_inference_batch.py``) reads anchors only
    (``_find_anchor_lines``) and never flips.
A belief is required: ``flip()`` / ``flip_line()`` without one raise ``CheckboxFlipError``.
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


BELIEF_RX = re.compile(r"^(cc|clm_[A-Za-z0-9_-]+|no-belief: \S.*)$")
UNRECORDED = "no-belief: unrecorded"   # only with allow_unrecorded=True (reserved for /log checkpoints)
# `✅ <date>` then optional `[belief: x]` / `[no-belief: x]`, then the verdict (legacy `(note)` accepted).
_TICK_RX = re.compile(r"✅\s*(?P<date>\d{4}-\d{2}-\d{2})(?P<rest>.*)$")
_TAG_RX = re.compile(r"^\s*\[(?:belief:\s*(?P<b>[^\]]+)|(?P<nb>no-belief:\s*[^\]]*))\]")
_MARKER_RX = re.compile(r"\s*<!--.*?-->\s*")
TAG_ANY = re.compile(r"\[(no-belief|belief):\s*([^\]]*)\]", re.I)   # same shape as belief_capture_check.TAG_ANY


def _tag_value(t: re.Match) -> str:
    kind, val = t.group(1).lower(), t.group(2).strip()
    return f"no-belief: {val}" if kind == "no-belief" else val


def belief_tag(belief: str) -> str:
    """`[belief: cc]` / `[belief: clm_x]` / `[no-belief: reason]`. Refuses anything else."""
    b = (belief or "").strip()
    if not BELIEF_RX.match(b):
        raise CheckboxFlipError(f"belief must be cc | clm_<id> | 'no-belief: <reason>', got {belief!r}")
    return f"[{b}]" if b.startswith("no-belief:") else f"[belief: {b}]"


def tick_suffix(date: str, belief: str | None = None, verdict: str = "", allow_unrecorded: bool = False) -> str:
    """The ONE tick suffix: `✅ <date> [belief: …|no-belief: …] <verdict>` (no leading space).

    A belief is REQUIRED (review S2): None raises unless allow_unrecorded=True (/log only). A result tick
    (`cc` / `clm_*`) must carry a verdict."""
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date or ""):
        raise CheckboxFlipError(f"tick date must be YYYY-MM-DD, got {date!r}")
    if not belief:
        if not allow_unrecorded:
            raise CheckboxFlipError("tick needs a belief: cc | clm_<id> | 'no-belief: <reason>'")
        belief = UNRECORDED
    if not belief.startswith("no-belief:") and not (verdict or "").strip():
        raise CheckboxFlipError(f"result tick [belief: {belief}] needs a verdict on the line")
    out = f"✅ {date} {belief_tag(belief)}"
    v = " ".join((verdict or "").split())
    return f"{out} {v}" if v else out


def parse_tick(line: str) -> dict | None:
    """{date, belief, verdict, form} for a ticked line's suffix, or None when it carries neither a `✅ <date>` nor a
    belief tag.

    form: `unified` (`✅ d [belief|no-belief] verdict`), `belief-only` (tag right after the date, no verdict),
    `tag-elsewhere` (a legacy tag NOT right after the date: after a note, before the `✅`, or on a line with no `✅`
    at all — file_result's old auto-tick; date may then be None), `note` (`✅ d (note)` / `✅ d — text`, no tag),
    `marker` (worker_checkpoint `<!-- … -->` only), `bare`.
    The LAST `✅ <date>` on the line is the tick (a parenthesised `(✅ date)` or a `✅` quoted in the task text is
    history). With several tags the one after the last `✅` wins. A same-line HTML comment is stripped from the
    verdict; the verdict is the text after the date with the chosen tag removed.
    """
    m = re.match(r".*" + _TICK_RX.pattern, line)   # greedy prefix: the LAST `✅ date` is the tick
    tags = list(TAG_ANY.finditer(line))
    if not m and not tags:
        return None
    if not m:
        t = tags[-1]
        return {"date": None, "belief": _tag_value(t), "verdict": "", "form": "tag-elsewhere"}
    raw = m.group("rest")
    rest = _MARKER_RX.sub(" ", raw)
    t = _TAG_RX.match(rest)
    if t:
        belief = (t.group("b") or t.group("nb")).strip()
        verdict = " ".join(rest[t.end():].split())
        return {"date": m.group("date"), "belief": belief, "verdict": verdict,
                "form": "unified" if verdict else "belief-only"}
    after = [x for x in tags if x.start() >= m.start("rest")]
    chosen = after[-1] if after else (tags[-1] if tags else None)
    if chosen is not None:
        if chosen.start() >= m.start("rest"):
            off = m.start("rest")
            rest = _MARKER_RX.sub(" ", raw[:chosen.start() - off] + raw[chosen.end() - off:])
        verdict = " ".join(rest.split())
        if re.match(r"^\(.*\)$", verdict):
            verdict = verdict[1:-1].strip()
        return {"date": m.group("date"), "belief": _tag_value(chosen), "verdict": verdict, "form": "tag-elsewhere"}
    verdict = " ".join(rest.split())
    if verdict.startswith(")"):                    # `(✅ date)`: the closing paren of a quoted tick is not a verdict
        verdict = verdict[1:].strip()
    if verdict:
        form = "note"
        if re.match(r"^\(.*\)$", verdict):
            verdict = verdict[1:-1].strip()
    else:
        form = "marker" if "<!--" in raw else "bare"
    return {"date": m.group("date"), "belief": None, "verdict": verdict, "form": form}


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
    belief: str | None = None


def _find_anchor_lines(lines: list[str], token: str) -> list[int]:
    pat = _anchor_re(token)
    return [i for i, line in enumerate(lines) if pat.match(line)]


def flip_line(line: str, date: str, belief: str | None = None, verdict: str = "", trailer: str = "",
              allow_unrecorded: bool = False) -> str:
    """Flip ONE open box line: `[ ]` -> `[x]` and append `tick_suffix(...)` (+ an optional trailer such as an
    HTML marker). Preserves indentation and the existing text; refuses a line that is not an open box."""
    if not re.match(r"^\s*[-*] \[ \]", line):
        raise CheckboxFlipError(f"not an open checkbox line: {line[:80]!r}")
    flipped = re.sub(r"^(\s*[-*]) \[ \]", r"\1 [x]", line, count=1)
    out = flipped.rstrip() + " " + tick_suffix(date, belief, verdict, allow_unrecorded)
    return out + (" " + trailer.strip() if trailer and trailer.strip() else "")


def _flip_line(line: str, date: str, evidence_note: str, belief: str | None = None,
               allow_unrecorded: bool = False) -> str:
    """Back-compat wrapper: the evidence note becomes the verdict of the unified suffix."""
    return flip_line(line, date, belief, evidence_note, allow_unrecorded=allow_unrecorded)


def _apply_one(text: str, token: str, date: str, evidence_note: str, belief: str | None = None,
               allow_unrecorded: bool = False) -> tuple[str, str]:
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
    new_body = _flip_line(body, date, evidence_note, belief, allow_unrecorded)
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
    belief: str | None = None,
    allow_unrecorded: bool = False,
) -> str:
    """Flip a single ``- [ ] **<token>`` checkbox to ``- [x] ... ✅ <date> [belief|no-belief] <note>``.

    Returns a unified diff of the change. With ``dry_run=True`` (default) the
    file is NOT written. Raises :class:`CheckboxFlipError` on 0 or >1 matches.
    """
    path = Path(handoff_path)
    try:
        before = path.read_text()
    except FileNotFoundError as exc:
        raise CheckboxFlipError(f"handoff file not found: {path}") from exc

    after, _ = _apply_one(before, checkbox_token, date, evidence_note, belief, allow_unrecorded)
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
                belief=item.get("belief"),
            )
        else:
            spec = FlipSpec(
                checkbox_token=item.checkbox_token,
                date=item.date or (date or ""),
                evidence_note=item.evidence_note,
                handoff_path=item.handoff_path or handoff_path,
                belief=item.belief,
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
                content, spec.checkbox_token, spec.date, spec.evidence_note, spec.belief
            )
        diffs[path_str] = _unified_diff(before, content, path_str)
        pending_writes[path_str] = content

    if not dry_run:
        for path_str, content in pending_writes.items():
            Path(path_str).write_text(content)
    return diffs
