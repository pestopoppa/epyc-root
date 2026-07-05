"""Parse EPYC handoff markdown files into structured board/card data.

Pure standard-library module (``re``, ``pathlib``, ``datetime``). No third-party
imports, so it is importable both by the stdlib dashboard server and by the
timeline generator, and is unit-testable in isolation.

Ground rules (see handoffs/README.md):

* **State is the parent directory** (``active`` / ``blocked`` / ``completed`` /
  ``archived``) — authoritative over the free-text ``**Status**:`` field.
* The one deliberate exception is the *Blocked* column, which is
  **status-derived**: an ``active/`` handoff whose ``Status`` begins with
  ``BLOCKED`` is routed into the Blocked column, plus any rows listed in the
  single ``blocked/BLOCKED.md`` aggregation table. See :func:`build_board`.
* Metadata is a block of ``**Key**: value`` lines *above the first* ``##``
  heading (there is no YAML frontmatter). Every field is optional and free-text.
* Task progress is GitHub checkboxes (``- [ ]`` / ``- [x]``). ~46% of active
  handoffs have none; those fall back to a ``✅``-marker count, else no bar.

The parser fails soft everywhere: a malformed field yields ``None``/``NONE``
rather than raising, so a single weird file can never 500 the page.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

STATES: tuple[str, ...] = ("active", "blocked", "completed", "archived")

# A checkbox line, possibly indented / nested. Group 1 = the mark, group 2 = text.
CHECKBOX_RE = re.compile(r"^\s*[-*]\s*\[([ xX])\]\s*(.*)$", re.M)
# A ``**Key**: value`` metadata line (only meaningful above the first ``##``).
# Allows an optional leading list marker so the bulleted ``- **Key**: value``
# variant is matched too.
META_RE = re.compile(r"^\s*(?:[-*]\s+)?\*\*([^*]+)\*\*:\s*(.*)$", re.M)
# A leading ``---`` … ``---`` YAML-ish frontmatter block (a handful of handoffs
# use this instead of bold-markdown metadata).
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\s*?\n", re.S)
FRONTMATTER_KV_RE = re.compile(r"^([A-Za-z][\w \-]*?):\s*(.*)$", re.M)
# First ISO date inside a (possibly prose-laden) value.
DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
# The leading ``# H1`` title.
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.M)
# A "done" marker used by files that track progress in prose, not checkboxes.
DONE_MARK = "✅"  # ✅
# Machine-generated sentinel blocks (capability registry) — strip before parsing.
SENTINEL_RE = re.compile(
    r"<!--\s*[\w:-]+:start\s*-->.*?<!--\s*[\w:-]+:end\s*-->",
    re.S,
)
# Skip these filenames when walking a state directory.
_SKIP_NAMES = {"README.md", "BLOCKED.md"}


# --------------------------------------------------------------------------- #
# File discovery
# --------------------------------------------------------------------------- #
def iter_handoff_files(handoff_root: Path) -> Iterator[tuple[str, Path]]:
    """Yield ``(state, path)`` for every top-level ``*.md`` handoff.

    Non-recursive per state dir (a nested dir such as
    ``completed/docs-chapters-audit/`` is intentionally not treated as a card).
    ``README.md`` and the ``blocked/BLOCKED.md`` aggregation file are skipped —
    ``BLOCKED.md`` is handled specially by :func:`build_board`. A non-``.md``
    file (e.g. a stray ``.yaml`` in ``active/``) is ignored.
    """
    for state in STATES:
        state_dir = handoff_root / state
        if not state_dir.is_dir():
            continue
        for path in sorted(state_dir.glob("*.md")):
            if path.name in _SKIP_NAMES:
                continue
            yield state, path


# --------------------------------------------------------------------------- #
# Field parsing
# --------------------------------------------------------------------------- #
def _metadata_region(text: str) -> str:
    """Return the slice of ``text`` before the first ``##`` heading."""
    # Split on a line that begins a level-2+ heading.
    m = re.search(r"^##\s", text, re.M)
    return text[: m.start()] if m else text


def parse_metadata(text: str) -> dict[str, str]:
    """Extract ``{lowercased key: value}`` from the metadata region.

    Handles three real styles: bold ``**Key**: value`` lines, the bulleted
    ``- **Key**: value`` variant, and a leading ``---`` YAML-ish frontmatter
    block. The first value seen for a key wins.
    """
    meta: dict[str, str] = {}
    fm = FRONTMATTER_RE.match(text)
    if fm:
        for key, value in FRONTMATTER_KV_RE.findall(fm.group(1)):
            meta.setdefault(key.strip().lower(), value.strip())
    region = _metadata_region(text)
    for key, value in META_RE.findall(region):
        meta.setdefault(key.strip().lower(), value.strip())
    return meta


def parse_title(text: str, fallback_stem: str) -> str:
    """First ``# H1`` title, else a de-slugified filename."""
    m = H1_RE.search(text)
    if m:
        return m.group(1).strip()
    return fallback_stem.replace("-", " ").replace("_", " ").strip().title()


# Ordered (substring, canonical) rules — first hit wins. Values are uppercased.
_PRIORITY_RULES: tuple[tuple[str, str], ...] = (
    ("P0", "P0"),
    ("CRITICAL", "P0"),
    ("BLOCKER", "P0"),
    ("ACTIVE-HIGH", "HIGH"),
    ("HIGH", "HIGH"),
    ("P1", "HIGH"),
    ("MEDIUM", "MEDIUM"),
    ("MED", "MEDIUM"),
    ("P2", "MEDIUM"),
    ("LOW", "LOW"),
    ("P3", "LOW"),
)


def _priority_from_value(raw: str) -> str:
    """Map a free-text priority value to ``P0|HIGH|MEDIUM|LOW|NONE``.

    Only the **leading token** is classified — values carry trailing rationale
    (``"MED — compiler can start today (no blockers)"``, ``"P2 — ... high
    payoff"``) where an unanchored substring scan would misfire (``BLOCKER`` in
    ``blockers``, ``HIGH`` in ``high payoff``). Matching is word-boundaried on
    that first token only.
    """
    token = re.split(r"[\s—–(;,/]+", (raw or "").strip(), maxsplit=1)[0].upper()
    if not token:
        return "NONE"
    for needle, canonical in _PRIORITY_RULES:
        if re.search(rf"\b{re.escape(needle)}\b", token):
            return canonical
    return "NONE"


def parse_priority(meta: dict[str, str]) -> str:
    """Map a handoff's ``Priority`` metadata to ``P0|HIGH|MEDIUM|LOW|NONE``."""
    return _priority_from_value(meta.get("priority", ""))


def _first_date(value: str | None) -> str | None:
    if not value:
        return None
    m = DATE_RE.search(value)
    if not m:
        return None
    year, month, day = (int(g) for g in m.groups())
    try:
        return datetime(year, month, day).strftime("%Y-%m-%d")
    except ValueError:
        return None  # e.g. a bogus 2026-13-40


_CREATED_KEYS = ("created", "date", "opened", "started")
_UPDATED_KEYS = ("updated", "last updated", "last-updated", "last touched", "revised")


def parse_dates(meta: dict[str, str]) -> dict[str, str | None]:
    """Best-effort ``created``/``updated`` ISO dates, tolerant of key synonyms.

    Real files use ``**Last Updated**`` and ``**Opened**`` as well as the plain
    ``Created``/``Updated`` keys.
    """
    created = next((d for k in _CREATED_KEYS if (d := _first_date(meta.get(k)))), None)
    updated = next((d for k in _UPDATED_KEYS if (d := _first_date(meta.get(k)))), None)
    return {"created": created, "updated": updated}


def count_tasks(text: str) -> tuple[int, int, str, list[dict]]:
    """Return ``(done, total, progress_source, tasks)``.

    * ``progress_source == "checkboxes"``: ``total`` checkboxes, ``done`` checked.
    * ``progress_source == "markers"``: no checkboxes, but ``done`` counts ``✅``
      markers in the body (``total == 0`` → the UI shows a marker chip, no ratio).
    * ``progress_source == "none"``: no progress signal at all.

    ``tasks`` is the structured checklist (only populated for the checkbox case);
    each item is ``{"done": bool, "text": str}``.
    """
    tasks: list[dict] = []
    checked = 0
    for mark, task_text in CHECKBOX_RE.findall(text):
        is_done = mark in ("x", "X")
        checked += 1 if is_done else 0
        tasks.append({"done": is_done, "text": task_text.strip()})
    total = len(tasks)
    if total:
        return checked, total, "checkboxes", tasks

    marker_count = text.count(DONE_MARK)
    if marker_count:
        return marker_count, 0, "markers", []
    return 0, 0, "none", []


def _status_short(status: str, limit: int = 140) -> str:
    """A compact one-line status for the card chip."""
    # Collapse whitespace, cut at the first sentence/em-dash boundary if short.
    flat = re.sub(r"\s+", " ", status).strip()
    if len(flat) <= limit:
        return flat
    return flat[: limit - 1].rstrip() + "…"  # ellipsis


# A handoff physically in ``active/`` whose status reads as blocked/parked/waiting
# is routed to the Blocked column. Kept HIGH-PRECISION: negative guards win, so an
# ambiguous item stays in Active rather than being wrongly flagged Blocked. Applied
# to the FULL status (not the truncated chip), so a mid-sentence signal isn't lost.
_BLOCKED_NEG_RE = re.compile(
    r"does\s*n[o']?t\s+(?:block|gate)|is\s+not\s+blocked|not\s+blocked\b|"
    r"un-?blocked|no\s+longer\s+blocked|blocker[s]?\b[^.;]*\b(?:resolved|cleared|lifted|gone)",
    re.I)
_BLOCKED_LEAD_RE = re.compile(
    r"^\s*\**\s*(?:BLOCKED|QUEUED|PARKED|PROPOSAL|ON[\s-]*HOLD|DEFERRED|PAUSED|AWAITING)\b",
    re.I)
_BLOCKED_POS_RE = re.compile(
    r"\bblocked\s+(?:on|by|pending|awaiting|until)\b|\bwaiting\s+(?:on|for)\b|"
    r"\bawaiting\b|\bon\s+hold\b|\bparked\b|\bneeds?\s+operator\b|"
    r"\bpending\s+operator\b|\bneeds?\s+approval\b|\bpending\s+approval\b",
    re.I)


def _is_blocked_status(status: str) -> bool:
    """True if a handoff's status reads as blocked / parked / waiting-on-a-dependency.

    Used to route an ``active/`` handoff into the Blocked column. High-precision:
    the negative guards (``does not block``, ``blocker … resolved``) win, so
    ambiguous or already-cleared items stay in Active.
    """
    s = status or ""
    if _BLOCKED_NEG_RE.search(s):
        return False
    return bool(_BLOCKED_LEAD_RE.match(s) or _BLOCKED_POS_RE.search(s))


def _scrub_html(md: str) -> str:
    """Light defensive scrub of raw markdown before client-side rendering.

    Handoffs are trusted internal localhost-only docs, but we still strip the
    obvious script-injection vectors so a pasted snippet can't run in the modal.
    This is not a full sanitizer (the content is trusted); it is defense in depth.
    """
    md = re.sub(r"<\s*script\b.*?<\s*/\s*script\s*>", "", md, flags=re.S | re.I)
    md = re.sub(r"<\s*script\b[^>]*>", "", md, flags=re.I)
    md = re.sub(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", md, flags=re.I)
    md = re.sub(r"javascript:", "", md, flags=re.I)
    return md


# --------------------------------------------------------------------------- #
# Card assembly
# --------------------------------------------------------------------------- #
def parse_file(state: str, path: Path, *, detail: bool = False) -> dict:
    """Parse one handoff into a card dict.

    ``detail=False`` returns a compact card (for the board). ``detail=True``
    additionally returns the full status, the scrubbed markdown ``body`` and the
    structured ``tasks`` list (for the modal).
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    # Strip machine-generated sentinel blocks (e.g. master-handoff-index.md).
    text = SENTINEL_RE.sub("", text)

    meta = parse_metadata(text)
    dates = parse_dates(meta)
    done, total, source, tasks = count_tasks(text)
    status_full = meta.get("status", "")
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0

    # Title: H1 heading, else a frontmatter ``title:`` field, else the filename.
    h1 = H1_RE.search(text)
    if h1:
        title = h1.group(1).strip()
    elif meta.get("title"):
        title = meta["title"]
    else:
        title = path.stem.replace("-", " ").replace("_", " ").strip().title()

    card = {
        "id": f"{state}/{path.stem}",
        "state": state,
        "title": title,
        "priority": parse_priority(meta),
        "status_short": _status_short(status_full),
        "blocked_hint": _is_blocked_status(status_full),
        "done": done,
        "total": total,
        "progress_source": source,
        "created": dates["created"],
        "updated": dates["updated"],
        "mtime": round(mtime, 3),
    }
    if detail:
        card["status"] = status_full
        card["categories"] = meta.get("categories", "")
        card["tasks"] = tasks
        card["body"] = _scrub_html(text)
    return card


# --------------------------------------------------------------------------- #
# BLOCKED.md table parsing
# --------------------------------------------------------------------------- #
def _split_table_row(line: str) -> list[str]:
    """Split a markdown table row into trimmed cells."""
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def _is_separator_row(cells: Iterable[str]) -> bool:
    return all(re.fullmatch(r":?-{2,}:?", c or "") for c in cells) if cells else False


def _link_target(cell: str) -> str | None:
    """Extract a ``handoffs/...`` basename from a ``[text](path.md)`` cell."""
    m = re.search(r"\(([^)]+\.md)\)", cell)
    if not m:
        return None
    target = m.group(1)
    stem = Path(target).stem
    # Normalise ``../active/foo.md`` and ``foo.md`` to an ``active/foo`` id when we can.
    for state in STATES:
        if f"/{state}/" in target or target.startswith(f"{state}/"):
            return f"{state}/{stem}"
    return None


def parse_blocked_table(handoff_root: Path) -> list[dict]:
    """Parse ``blocked/BLOCKED.md`` into synthetic blocked cards.

    Skips the ``_None currently tracked here_`` placeholder row. Returns an empty
    list when nothing is genuinely blocked (the common case).
    """
    path = handoff_root / "blocked" / "BLOCKED.md"
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    # Isolate the "Current Blocked Work" table section.
    section = text
    m = re.search(r"^##\s+Current Blocked Work\s*$", text, re.M)
    if m:
        rest = text[m.end():]
        nxt = re.search(r"^##\s", rest, re.M)
        section = rest[: nxt.start()] if nxt else rest

    rows: list[dict] = []
    header_seen = False
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = _split_table_row(line)
        if _is_separator_row(cells):
            continue
        if not header_seen:
            header_seen = True  # first pipe row is the header
            continue
        if not cells or not cells[0]:
            continue
        title = cells[0]
        # Skip the placeholder / "none tracked" sentinel row.
        if re.search(r"_?none\b", title, re.I) and "track" in " ".join(cells).lower():
            continue
        if title.startswith("_") and title.endswith("_"):
            continue
        handoff = cells[3] if len(cells) > 3 else ""
        rows.append(
            {
                "id": _link_target(handoff) or f"blocked/{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') or 'item'}",
                "state": "blocked",
                "title": re.sub(r"\*+", "", title).strip(),
                "priority": _priority_from_token(cells[2] if len(cells) > 2 else ""),
                "status_short": _status_short(cells[4] if len(cells) > 4 else ""),
                "blocked_on": cells[1] if len(cells) > 1 else "",
                "done": 0,
                "total": 0,
                "progress_source": "none",
                "created": None,
                "updated": None,
                "activity": None,
                "activity_source": None,
                "mtime": 0.0,
            }
        )
    return rows


def _priority_from_token(token: str) -> str:
    return _priority_from_value(token)


# --------------------------------------------------------------------------- #
# Board
# --------------------------------------------------------------------------- #
def build_board(handoff_root: Path, *, file_activity: dict | None = None,
                dirty_ids: set | None = None) -> dict:
    """Assemble the full kanban payload from a live directory scan.

    Columns are keyed by the four states. Active handoffs whose ``Status`` begins
    with ``BLOCKED`` are moved into the Blocked column (status-derived), joined by
    any rows in ``blocked/BLOCKED.md``.

    ``file_activity`` (``{"state/stem": "YYYY-MM-DD", ...}``, the git-derived
    last-touched map) and ``dirty_ids`` (handoffs with uncommitted edits) are
    optional recency signals; when omitted the board falls back to frontmatter
    dates exactly as before. See ``_derive_activity``.
    """
    columns: dict[str, list[dict]] = {s: [] for s in STATES}

    for state, path in iter_handoff_files(handoff_root):
        card = parse_file(state, path)
        # Derive the recency signal while the card still carries its real id
        # (the blocked reroute below keeps the id but rewrites ``state``).
        _derive_activity(card, file_activity, dirty_ids)
        # Status-derived Blocked column: an active handoff whose full Status reads
        # as blocked/parked/waiting (see ``_is_blocked_status``) moves here.
        if state == "active" and card.get("blocked_hint"):
            card = {**card, "state": "blocked"}
            columns["blocked"].append(card)
        else:
            columns[state].append(card)

    columns["blocked"].extend(parse_blocked_table(handoff_root))

    # Stable, useful ordering per column.
    for state, cards in columns.items():
        cards.sort(key=_card_sort_key(state))

    counts = {s: len(columns[s]) for s in STATES}
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "columns": columns,
        "counts": counts,
        "backlog": _backlog_summary(columns),
    }


def _backlog_summary(columns: dict[str, list[dict]]) -> dict:
    """Exact outstanding-work snapshot: how far from clearing the backlog.

    Outstanding = the Active + Blocked columns. ``open_tasks`` counts unchecked
    checkboxes there; ``pct_open_done`` is progress within outstanding handoffs
    that have task checklists; ``pct_all_done`` is over every tracked task.
    """
    OPEN = ("active", "blocked")
    open_handoffs = sum(len(columns[s]) for s in OPEN)
    open_tasks = open_done = open_total = 0
    for s in OPEN:
        for c in columns[s]:
            if c.get("progress_source") == "checkboxes":
                open_total += c["total"]
                open_done += c["done"]
                open_tasks += c["total"] - c["done"]
    all_done = all_total = 0
    for cards in columns.values():
        for c in cards:
            if c.get("progress_source") == "checkboxes":
                all_total += c["total"]
                all_done += c["done"]
    # Outstanding handoffs with no checklist can't be measured in tasks — surface
    # the count so the number isn't silently read as "0 work left".
    open_untracked = sum(
        1 for s in OPEN for c in columns[s] if c.get("progress_source") != "checkboxes"
    )
    return {
        "open_handoffs": open_handoffs,
        "open_untracked_handoffs": open_untracked,
        "open_tasks": open_tasks,
        "open_tasks_done": open_done,
        "open_tasks_total": open_total,
        "pct_open_done": round(100 * open_done / open_total, 1) if open_total else None,
        "all_tasks_done": all_done,
        "all_tasks_total": all_total,
        "pct_all_done": round(100 * all_done / all_total, 1) if all_total else None,
    }


_PRIORITY_ORDER = {"P0": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "NONE": 4}


def _derive_activity(card: dict, file_activity: dict | None,
                     dirty_ids: set | None) -> None:
    """Set ``card['activity']`` (recency date) and ``card['activity_source']``.

    The date is the **max** of the available candidates — a stale frontmatter
    ``Updated`` field must not out-rank a newer commit — falling back to
    ``created``, else ``None``:

    * ``updated`` — the file's declared ``Updated``/``Last Updated`` date;
    * ``git``     — the last commit day that touched the file (``file_activity``);
    * ``wip``     — the file's mtime date, but **only when git-dirty** (covers
      uncommitted/untracked edits; the dirty gate keeps bulk-``touch`` noise out).

    Candidates are ordered most-current-first so a date tie labels ``wip > git >
    updated`` (``max`` keeps the first of equal maxima). Purely additive: with no
    signals passed, ``activity`` is the frontmatter ``updated`` (else ``created``).
    """
    cid = card.get("id", "")
    candidates: list[tuple[str, str]] = []
    if dirty_ids and cid in dirty_ids and card.get("mtime"):
        wip = datetime.fromtimestamp(card["mtime"], timezone.utc).strftime("%Y-%m-%d")
        candidates.append(("wip", wip))
    if file_activity and (git_day := file_activity.get(cid)):
        candidates.append(("git", git_day))
    if card.get("updated"):
        candidates.append(("updated", card["updated"]))

    if candidates:
        source, activity = max(candidates, key=lambda t: t[1])
    elif card.get("created"):
        source, activity = "created", card["created"]
    else:
        source, activity = None, None
    card["activity"] = activity
    card["activity_source"] = source


def _card_sort_key(state: str):
    if state in ("completed", "archived"):
        # Most-recently-touched first.
        return lambda c: (-(c.get("mtime") or 0.0), c["title"].lower())
    # Active/blocked: priority first, then most-recent activity (git/mtime-derived,
    # falling back to frontmatter dates). Synthetic BLOCKED.md rows have no activity.
    return lambda c: (
        _PRIORITY_ORDER.get(c.get("priority", "NONE"), 4),
        c.get("activity") is None,
        _neg_date(c.get("activity")),
        c["title"].lower(),
    )


def _neg_date(iso: str | None) -> float:
    """Numeric sort key that puts later dates first (ascending sort, descending date).

    Must be numeric, not a formatted string: negating a timestamp and
    zero-padding does NOT reverse lexicographic order (the constant sign +
    magnitude digits still sort ascending), which silently ordered columns
    oldest-first. Accepts a bare ``YYYY-MM-DD`` or a full ISO timestamp.
    """
    if not iso:
        return 0.0
    try:
        return -datetime.fromisoformat(iso).timestamp()
    except ValueError:
        return 0.0
