"""Before building a second adapter, measure its ceiling — the discipline P2 established.

The intake adapter's most useful output was not the claims it emitted but the CEILING it hit: an
index entry names a document, so no retrofitted claim could reach `Anchored` however well dived.
That priced instrumenting-writes against parsing-prose in the currency the policy layer uses.

The same question decides whether a progress/measurement adapter is worth writing. Q4 Witnessed
requires "a protocol-admissible measurement with durable attestation" (spec §4.5). So: how many of
our own recorded measurements cite a durable artifact at all? If the answer is near zero, a
retrofit would emit thousands of claims that can never gate anything, and the honest deliverable is
the number rather than the adapter.
"""
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path("/workspace")

# A magnitude with a unit -- the shape of a measured result rather than a count.
MAGNITUDE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?\s*(?:%|x\b|t/s|tok/s|GB|MB|ms|pp\b)")
# Signals that a durable artifact backs the line.
ARTIFACT = re.compile(
    r"(?:artifacts/|data/|\.jsonl|\.json\b|\.csv\b|sha256:|[0-9a-f]{12,}|"
    r"trial \d+|run [0-9a-f]{6,}|execution_manifest)", re.I)
# Signals the line is a plan or an intention, not a result.
HYPOTHETICAL = re.compile(r"\b(should|would|could|expect|plan to|aim to|target|TODO|next)\b", re.I)

files = [f for f in subprocess.run(["git", "ls-files", "progress"], capture_output=True,
                                   text=True, cwd=ROOT).stdout.split() if f.endswith(".md")]

stats = Counter()
examples = {"attested": [], "unattested": []}
for f in files:
    try:
        text = (ROOT / f).read_text(errors="ignore")
    except OSError:
        continue
    for line in text.splitlines():
        line = line.strip()
        if len(line) < 40 or not MAGNITUDE.search(line):
            continue
        stats["measurement_lines"] += 1
        if HYPOTHETICAL.search(line):
            stats["hypothetical"] += 1
            continue
        stats["result_lines"] += 1
        if ARTIFACT.search(line):
            stats["with_artifact"] += 1
            if len(examples["attested"]) < 3:
                examples["attested"].append((f, line[:150]))
        else:
            stats["without_artifact"] += 1
            if len(examples["unattested"]) < 3:
                examples["unattested"].append((f, line[:150]))

print(f"progress files scanned: {len(files)}")
print(f"  lines carrying a magnitude      : {stats['measurement_lines']}")
print(f"  of those, hypothetical/planned  : {stats['hypothetical']}")
print(f"  stated as results               : {stats['result_lines']}")
print(f"    citing a durable artifact     : {stats['with_artifact']}")
print(f"    citing nothing retrievable    : {stats['without_artifact']}")
if stats["result_lines"]:
    print(f"\n  ceiling: {100*stats['with_artifact']/stats['result_lines']:.1f}% of recorded "
          f"results could even be argued toward Q4 Witnessed")
print("\nATTESTED examples:")
for f, line in examples["attested"]:
    print(f"  {f}\n    {line}")
print("\nUNATTESTED examples:")
for f, line in examples["unattested"]:
    print(f"  {f}\n    {line}")
