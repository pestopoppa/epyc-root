#!/usr/bin/python3
"""Render ratify_stackchg_kvpool_20261003.sh from tools/ratify_template.sh with sha256 PINS
over every package file the signature covers. Run once, after PACKAGE.md is final; then only
`--validate-only` until it prints VALID, and no edits after that."""
import hashlib
from pathlib import Path

PKG = Path("/mnt/raid0/llm/tmp/stack-change-kvpool-20261003")
OUT = PKG / "ratify_stackchg_kvpool_20261003.sh"
files = ["PACKAGE.md", "intent.yaml",
         "patches/orchestrator/stackchg-kvpool-20261003.orchestrator.patch",
         "patches/research/stackchg-kvpool-20261003.research.patch"]
files += sorted(str(p.relative_to(PKG)) for p in (PKG / "evidence").iterdir() if p.is_file())
files += sorted(str(p.relative_to(PKG)) for p in (PKG / "tools").iterdir()
                if p.is_file() and p.suffix in {".sh", ".py"})
pins = []
for rel in files:
    digest = hashlib.sha256((PKG / rel).read_bytes()).hexdigest()
    pins.append(f'  "{digest} {rel}"')
template = (PKG / "tools" / "ratify_template.sh").read_text()
assert template.count("@@PINS@@") == 1
OUT.write_text(template.replace("@@PINS@@", "\n".join(pins)))
OUT.chmod(0o755)
print(f"wrote {OUT} with {len(pins)} pins")
