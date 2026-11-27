from pathlib import Path
import re
import sys

DOC = "docs/reference/harness-candidates/paw-5-compile-once-candidates.md"
PINS = (
    "332ceb2e14d16f2031bd17b1f7c839ce8276a24b",
    "dd090a874c22be58e09b18fc1fc86da7b46b1d85",
)
SOURCES = (
    "src/graph/context_arm_ab.py",
    "src/api/routes/chat_pipeline/repl_executor.py",
    "scripts/kernel_rnd/autokernel/loop/loop.py",
)
def substantive(body):
    # Ignore empty headings/comments and distinguish a table header from its data.
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    table = []
    for line in lines:
        if re.match(r"^#{1,6}\s", line):
            continue
        if "|" in line:
            table.append(line)
            continue
        if re.search(r"[A-Za-z0-9]", line):
            return True
    for i, line in enumerate(table):
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", c or " ") for c in cells):
            # A Markdown table requires at least one nonempty data row.
            return any(any(re.search(r"[A-Za-z0-9]", c) for c in row.strip("|").split("|"))
                       for row in table[i + 1:])
    return False


def field_present(section, field):
    label = re.escape(field)
    header = rf"(?:\*\*{label}(?:[.:]\*\*|\*\*[ \t]*[.:]?)|{label}[.:]?)"
    # Retain all v3 inline spellings.
    if re.search(rf"(?mi)^[ \t]*(?:[-*][ \t]+)?{header}[ \t]+\S", section):
        return True
    # Standalone bold/plain field labels may introduce a following block.
    lines = section.splitlines()
    any_label = r"(?:Compile-once candidate|Direct-model baseline|Comparison)"
    next_field = rf"(?:\*\*{any_label}(?:[.:]\*\*|\*\*[ \t]*[.:]?)|{any_label}[.:]?)"
    for i, line in enumerate(lines):
        if not re.fullmatch(rf"[ \t]*(?:[-*][ \t]+)?{header}[ \t]*", line, flags=re.I):
            continue
        end = len(lines)
        for j in range(i + 1, len(lines)):
            if re.match(r"[ \t]{0,3}#{1,6}[ \t]+", lines[j]) or re.match(rf"[ \t]*(?:[-*][ \t]+)?{next_field}(?:[ \t]+|$)", lines[j], flags=re.I):
                end = j
                break
        if substantive("\n".join(lines[i + 1:end])):
            return True
    # ATX Markdown headings delimit their following block at the next heading
    # at the same or shallower level, rather than requiring same-line prose.
    lines = section.splitlines()
    for i, line in enumerate(lines):
        m = re.fullmatch(r"[ \t]{0,3}(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*", line)
        if not m or m.group(2).strip().strip("*").rstrip(".:").strip().casefold() != field.casefold():
            continue
        end = len(lines)
        for j in range(i + 1, len(lines)):
            other = re.match(r"[ \t]{0,3}(#{1,6})[ \t]+", lines[j])
            if other and len(other.group(1)) <= len(m.group(1)):
                end = j
                break
        if substantive("\n".join(lines[i + 1:end])):
            return True
    return False

def shared_source_bindings(preamble, section):
    """Resolve a candidate's explicit source/seam mention through its source table.

    Source-table placement is presentation. Each row must bind a supplied file
    to its correct immutable revision, and the candidate must resolve that row
    by an exact filename or its explicit multiword seam name. Presence of an
    unrelated pin elsewhere in the document is insufficient.
    """
    expected = {SOURCES[0]: PINS[0], SOURCES[1]: PINS[0], SOURCES[2]: PINS[1]}
    bindings = []
    for line in preamble.splitlines():
        if "|" not in line:
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) != 3:
            continue
        for source, pin in expected.items():
            if source not in cells[0] or cells[1] != pin:
                continue
            filename = Path(source).name
            seam = cells[2].split(",", 1)[0].strip().strip("`")
            by_filename = re.search(rf"(?<![A-Za-z0-9_.]){re.escape(filename)}(?![A-Za-z0-9_.])", section)
            matching_rows = [row for row in preamble.splitlines() if "|" in row
                             and len(row.strip().strip("|").split("|")) == 3
                             and row.strip().strip("|").split("|")[-1].split(",", 1)[0].strip().strip("`").casefold() == seam.casefold()]
            by_seam = len(seam.split()) >= 2 and len(matching_rows) == 1 and re.search(rf"(?<!\w){re.escape(seam)}(?!\w)", section, re.I)
            if by_filename or by_seam:
                bindings.append((source, pin))
    return bindings

text = (Path(sys.argv[1]) / DOC).read_text()
sections = re.split(r"(?m)^## Candidate:\s*", text)
assert 1 <= len(sections) - 1 <= 3, "expected 1-3 named candidates"
assert "PAW-1" in text and "PAW-2" in text, "compilation prerequisites missing"
for section in sections[1:]:
    assert section.splitlines()[0].strip()
    shared = shared_source_bindings(sections[0], section)
    assert any(pin in section for pin in PINS) or shared, "candidate has no pinned source"
    assert any(src in section for src in SOURCES) or shared, "candidate has no reviewed loop seam"
    for field in ("Compile-once candidate", "Direct-model baseline", "Comparison"):
        assert field_present(section, field), field
assert not re.search(r"(?mi)^## Candidate:.*json repair", text), "excluded JSON repair"
print("PAW-5 structure and provenance PASS. Review semantic choices and comparator in the full diff.")
