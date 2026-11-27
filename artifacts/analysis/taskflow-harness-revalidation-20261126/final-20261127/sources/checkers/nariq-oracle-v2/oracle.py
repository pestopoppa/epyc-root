from pathlib import Path
import re
import sys

path = "docs/research/exl3-4-gfx90a-libtrellis-design.md"
text = (Path(sys.argv[1]) / path).read_text()
sections = dict(re.findall(r"(?ms)^## ([^\n]+)\n(.*?)(?=^## |\Z)", text))
required = {
    "Offset decode": ("1528", "fp16", "sum", "4"),
    "Activation preparation": ("fragment", "scale"),
    "Grouped launch": ("input", "matri"),
    "LDS budget": ("byte", "stage"),
    "Wave64 MFMA": ("16x16x16", "fp32", "lane"),
    "Harness coverage": ("lane", "offset", "group"),
}
assert "8e0e016e0cd13f153380bde2bec01add08eae85e" in text, "unbound libtrellis source"
assert "dd090a874c22be58e09b18fc1fc86da7b46b1d85" in text, "unbound local harness source"
assert "test_runtime.hip" in text.lower(), ("document", "test_runtime.hip")
for heading, terms in required.items():
    assert heading in sections, heading
    body = sections[heading].lower().replace("×", "x")
    for term in terms:
        assert term in body, (heading, term)
assert re.search(r"65[, ]?536|64\s*ki?b", sections["LDS budget"], re.I), "LDS ceiling absent"
print("NARIQ document sections and provenance PASS. Review arithmetic, coverage and design correctness separately.")
