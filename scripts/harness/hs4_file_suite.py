"""Prepare fresh synthetic file-task inputs and separate host-only oracles.

Directory separation does not provide a process or filesystem security boundary.
The caller must seal the acceptance split before tuning and prove isolation
before any untrusted agent or model is launched.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path
from typing import Any

from scripts.harness.hs4_file_scoring import canonical
from scripts.harness.hs4_file_trials import _files, fixture_identity


def prepare_suite(public_root: Path, oracle_root: Path) -> list[dict[str, Any]]:
    public = Path(public_root).resolve(strict=False)
    oracle = Path(oracle_root).resolve(strict=False)
    if public == oracle or public in oracle.parents or oracle in public.parents:
        raise ValueError("public and oracle roots must be disjoint")
    if public.exists() or oracle.exists():
        raise FileExistsError("suite roots must be fresh")
    public.mkdir(mode=0o700)
    oracle.mkdir(mode=0o700)
    metadata = []
    used_keys: set[str] = set()
    for split, count in (("development", 6), ("acceptance", 12)):
        for i in range(count):
            family = ("lookup", "inventory", "reconciliation")[i % 3]
            task = f"{split}-{i:02d}"
            root = public / task
            root.mkdir(mode=0o700)
            key = "item" + secrets.token_hex(8)
            while key in used_keys:
                key = "item" + secrets.token_hex(8)
            used_keys.add(key)
            left = secrets.randbelow(90) + 1
            delta = secrets.randbelow(9) + 1
            if family == "lookup":
                path = "records/" + key + ".txt"
                (root / "records").mkdir()
                (root / path).write_text(f"id={key}\n", encoding="utf-8")
                prompt = (f"Find the file containing id={key}. Respond only as canonical compact "
                          'JSON {"path":"relative/path"}.')
                answer = {"path": path}
            elif family == "inventory":
                (root / "inventory.csv").write_text(f"item,quantity\n{key},{left}\nother,{delta}\n", encoding="utf-8")
                prompt = ('Sum quantity in inventory.csv. Respond only as canonical compact JSON {"total":0}.')
                answer = {"total": left + delta}
            else:
                (root / "left.csv").write_text(f"item,quantity\n{key},{left}\n", encoding="utf-8")
                (root / "right.csv").write_text(f"item,quantity\n{key},{left + delta}\n", encoding="utf-8")
                prompt = ('Report differing quantities in left.csv and right.csv, sorted by item. '
                          'Respond only as canonical compact JSON {"mismatches":[{"item":"name","left":0,"right":1}]}.')
                answer = {"mismatches": [{"item": key, "left": left, "right": left + delta}]}
            oracle_file = oracle / f"{task}.json"
            with oracle_file.open("x", encoding="utf-8") as out:
                out.write(canonical(answer))
            oracle_file.chmod(0o600)
            prompt_bytes = prompt.encode()
            metadata.append({"task": task, "split": split, "family": family,
                             "fixture_sha256": fixture_identity(_files(root)),
                             "prompt": prompt, "prompt_sha256": hashlib.sha256(prompt_bytes).hexdigest(),
                             "oracle_sha256": hashlib.sha256(canonical(answer).encode()).hexdigest()})
    # Metadata contains hashes, not oracle bytes; preserve outside agent workspace.
    (oracle / "manifest.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    (oracle / "manifest.json").chmod(0o600)
    return metadata
