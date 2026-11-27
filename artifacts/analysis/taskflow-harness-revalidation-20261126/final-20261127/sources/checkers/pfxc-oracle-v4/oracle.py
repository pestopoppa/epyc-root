"""Verify the PFXC note against the exact warning events in its pinned server log."""

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
from pathlib import Path
import re
import sys

DOC = "docs/research/qwen3.6-35b-a3b-q8-gpu-mtp-cache-sizing.md"
LOG = Path("/mnt/raid0/llm/tmp/taskflow-stage1-canary-r2-20261120/out/server.log")
PROBE = Path("/mnt/raid0/llm/tmp/ak-pfxc-probe-gpu-20261120-r2/out/RESULT.json")
LOG_SHA = "85533337680e2dee4307f67fb0fda5e08beae1b122adc0f53cacf15a08c4e377"
PROBE_SHA = "1512c7b77500b66635c3ac23f46c4a3b6ff28c50f69d8066f5532bd65246f32d"
WARNING = re.compile(r"making room for prompt cache entry, removing oldest entry \(size = ([0-9.]+) MiB\)")
SEPARATOR = re.compile(r":?-{3,}:?")
INTEGER = r"[1-9][0-9]*"
DECIMAL = r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)\.[0-9]+"
SIZE = re.compile(rf"({DECIMAL})(?:\s+MiB)?", re.I)
LIST_ROW = re.compile(rf"(?:(?P<ordinal>{INTEGER})[.)]\s+|[-*+]\s+)?"
                      rf"(?:(?:log\s+)?line\s+(?P<line>{INTEGER})\s*[:–-]\s*)?"
                      rf"(?P<size>{DECIMAL})(?:\s+MiB)?", re.I)


class InvalidNote(ValueError):
    pass


@dataclass(frozen=True)
class Event:
    ordinal: int | None
    source_line: int | None
    size_mib: Decimal


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinned_events():
    if digest(LOG) != LOG_SHA or digest(PROBE) != PROBE_SHA:
        raise InvalidNote("a pinned source capture hash changed")
    with LOG.open() as stream:
        return [(line_no, Decimal(match[1]))
                for line_no, line in enumerate(stream, 1)
                if (match := WARNING.search(line))]


def cells(line):
    row = line.strip()
    if "|" not in row:
        return []
    return [cell.strip(" `*") for cell in row.removeprefix("|").removesuffix("|").split("|")]


def field(label):
    words = re.sub(r"[^a-z0-9#]+", " ", label.lower()).split()
    if "line" in words:
        return "line"
    if "size" in words or "mib" in words:
        return "size"
    if any(word in words for word in ("#", "order", "ordinal", "index", "entry", "event", "no")):
        return "ordinal"
    return None


def event_columns(header):
    roles = [field(cell) for cell in header]
    groups = roles.count("size")
    if not groups or (None in roles and not set(roles).intersection({"ordinal", "line"})):
        return []
    width, remainder = divmod(len(roles), groups)
    if remainder:
        raise InvalidNote("entry table must identify a size in each group of columns")
    columns = []
    for start in range(0, len(roles), width):
        block = [(role, start + offset) for offset, role in enumerate(roles[start:start + width]) if role]
        assigned = dict(block)
        if "size" not in assigned or len(assigned) != len(block):
            raise InvalidNote("entry table has ambiguous size, ordinal or line columns")
        columns.append(assigned)
    if groups > 1 and any("ordinal" not in block for block in columns):
        raise InvalidNote("side-by-side entry groups need explicit ordinals")
    return columns


def table_events(header, rows):
    columns = event_columns(header)
    if not columns:
        return
    for row in rows:
        if len(row) != len(header):
            raise InvalidNote("entry table row has the wrong number of cells")
        for block in columns:
            values = {role: row[index] for role, index in block.items()}
            if not any(values.values()):
                continue
            size = SIZE.fullmatch(values["size"])
            if not size or any(not re.fullmatch(INTEGER, values[key]) for key in values if key != "size"):
                raise InvalidNote(f"malformed entry table group: {values}")
            yield Event(int(values["ordinal"]) if "ordinal" in values else None,
                        int(values["line"]) if "line" in values else None,
                        Decimal(size[1].replace(",", "")))


def note_events(section):
    # Extraction examples may contain numbers but represent no listed event.
    lines = iter(re.sub(r"(?ms)^\s*(?:```[^\n]*|~~~[^\n]*)\n.*?^\s*(?:```|~~~)[ \t]*$", "", section).splitlines())
    line = next(lines, None)
    while line is not None:
        header = cells(line)
        if header:
            line = next(lines, None)
            separator = cells(line) if line is not None else []
            if len(separator) == len(header) and all(SEPARATOR.fullmatch(item) for item in separator):
                rows = []
                line = next(lines, None)
                while line is not None and (row := cells(line)):
                    rows.append(row)
                    line = next(lines, None)
                yield from table_events(header, rows)
            continue
        row = LIST_ROW.fullmatch(line.strip().strip("`* "))
        if row:
            values = row.groupdict()
            yield Event(int(values["ordinal"]) if values["ordinal"] else None,
                        int(values["line"]) if values["line"] else None,
                        Decimal(values["size"].replace(",", "")))
        line = next(lines, None)


def compare_events(listed, source):
    repeated = sorted(line for line, count in Counter(
        event.source_line for event in listed if event.source_line is not None
    ).items() if count > 1)
    if len(listed) != len(source) or repeated:
        detail = f"; duplicate source lines: {', '.join(map(str, repeated))}" if repeated else ""
        raise InvalidNote(f"expected {len(source)} source events exactly once, found {len(listed)}{detail}")
    indexed = [event.ordinal is not None for event in listed]
    if any(indexed):
        if not all(indexed) or sorted(event.ordinal for event in listed) != list(range(1, len(source) + 1)):
            raise InvalidNote(f"entry ordinals must cover 1–{len(source)} exactly once")
        listed = sorted(listed, key=lambda event: event.ordinal)
    for ordinal, (actual, (source_line, size)) in enumerate(zip(listed, source, strict=True), 1):
        if actual.source_line is not None and actual.source_line != source_line:
            raise InvalidNote(f"event {ordinal}: source line {actual.source_line}, expected {source_line}")
        if actual.size_mib != size:
            raise InvalidNote(f"event {ordinal}: size {actual.size_mib} MiB, expected {size} MiB")


def verify(path):
    body = (path / DOC).read_text()
    source = pinned_events()
    sizes = sorted(size for _, size in source)
    if (len(sizes), sizes[0], sizes[-1]) != (41, Decimal("147.505"), Decimal("1348.877")):
        raise InvalidNote("pinned warning sample count or range changed")
    rank = int((Decimal("0.95") * len(sizes)).to_integral_value(rounding=ROUND_CEILING))
    p95 = sizes[rank - 1]
    total = (10 * p95).to_integral_value(rounding=ROUND_CEILING)
    normalized = body.replace(",", "")
    for word in (str(sizes[0]), str(sizes[-1]), str(p95), str(total),
                 "41", "8192", "p95", "37.9", "np1", "np2", "VRAM",
                 "qwen3.6-35b-a3b-q8-gpu-mtp.json", LOG.parts[-3], PROBE.parts[-3], LOG_SHA, PROBE_SHA):
        if word not in normalized:
            raise InvalidNote(f"required trace pin, sizing figure or geometry missing: {word}")
    if any(arm["evictions"] != 0 for arm in json.loads(PROBE.read_text())["arms"].values()):
        raise InvalidNote("distinct probe no longer verifies zero evictions")
    entry = re.search(r"(?ms)^## Entry sizes[ \t]*\n(.*?)(?=^## |\Z)", body)
    if entry is None:
        raise InvalidNote("missing Entry sizes section")
    compare_events(list(note_events(entry[1])), source)
    return len(source)


if __name__ == "__main__":
    try:
        count = verify(Path(sys.argv[1]))
    except (InvalidNote, FileNotFoundError) as exc:
        raise SystemExit(str(exc)) from exc
    print(f"PFXC pinned trace, all {count} source events, sample arithmetic and required note contents PASS.")
