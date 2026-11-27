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

text = (Path(sys.argv[1]) / DOC).read_text()
sections = re.split(r"(?m)^## Candidate:\s*", text)
assert 1 <= len(sections) - 1 <= 3, "expected 1-3 named candidates"
assert "PAW-1" in text and "PAW-2" in text, "compilation prerequisites missing"
for section in sections[1:]:
    assert section.splitlines()[0].strip()
    assert any(pin in section for pin in PINS), "candidate has no pinned source"
    assert any(src in section for src in SOURCES), "candidate has no reviewed loop seam"
    for field in ("Compile-once candidate", "Direct-model baseline", "Comparison"):
        assert field_present(section, field), field
assert not re.search(r"(?mi)^## Candidate:.*json repair", text), "excluded JSON repair"
print("PAW-5 structure and provenance PASS. Review semantic choices and comparator in the full diff.")
