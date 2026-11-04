"""Prepare fresh synthetic file-task inputs and separate host-only oracles.

Directory separation does not provide a process or filesystem security boundary.
The caller must seal the acceptance split before tuning and prove isolation
before any untrusted agent or model is launched.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import os
import stat
from pathlib import Path
from typing import Any

from scripts.harness.hs4_file_scoring import NATIVE_SCORER_SHA256, canonical, validate_answer
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


def _suite_rows(public: Path, oracle: Path) -> list[dict[str, Any]]:
    manifest = oracle / "manifest.json"
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError("manifest must be regular")
    rows = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or len(rows) != 18:
        raise ValueError("suite manifest must contain 18 tasks")
    expected_ids = [f"{split}-{i:02d}" for split, n in (("development", 6), ("acceptance", 12)) for i in range(n)]
    if {p.name for p in public.iterdir()} != set(expected_ids):
        raise ValueError("unexpected public suite entries")
    expected_private = {f"{task}.json" for task in expected_ids} | {"manifest.json"}
    if (oracle / "seal.json").exists():
        expected_private.add("seal.json")
    if {p.name for p in oracle.iterdir()} != expected_private:
        raise ValueError("unexpected oracle suite entries")
    index = 0
    for split, n in (("development", 6), ("acceptance", 12)):
        for i in range(n):
            row = rows[index]
            index += 1
            family = ("lookup", "inventory", "reconciliation")[i % 3]
            task = f"{split}-{i:02d}"
            if (not isinstance(row, dict) or row.get("task") != task
                    or row.get("split") != split or row.get("family") != family):
                raise ValueError("suite task order or identity mismatch")
            root = public / task
            oracle_file = oracle / f"{task}.json"
            if oracle_file.is_symlink() or not oracle_file.is_file():
                raise ValueError("oracle must be regular")
            expected = oracle_file.read_text(encoding="utf-8")
            validate_answer(family, expected)
            if (fixture_identity(_files(root)) != row.get("fixture_sha256")
                    or hashlib.sha256(expected.encode()).hexdigest() != row.get("oracle_sha256")
                    or not isinstance(row.get("prompt"), str)
                    or hashlib.sha256(row["prompt"].encode()).hexdigest() != row.get("prompt_sha256")):
                raise ValueError("suite input, prompt or oracle differs from manifest")
    return rows


def _read_only(root: Path) -> None:
    for directory, dirs, files in os.walk(root, topdown=False, followlinks=False):
        for name in files:
            path = Path(directory) / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("suite contains non-regular file")
            path.chmod(0o400)
        for name in dirs:
            path = Path(directory) / name
            if path.is_symlink():
                raise ValueError("suite contains symlink")
            path.chmod(0o500)
    root.chmod(0o500)


def seal_suite(public_root: Path, oracle_root: Path) -> str:
    """Bind prepared bytes, then protect both trees from accidental writes.

    Return the seal's SHA-256 for independent custody. chmod is reversible by
    the owner and is not a filesystem immutability or isolation claim.
    """
    public, oracle = Path(public_root), Path(oracle_root)
    left, right = public.resolve(), oracle.resolve()
    if (public.is_symlink() or oracle.is_symlink() or left == right
            or left in right.parents or right in left.parents):
        raise ValueError("suite roots must be distinct real directories")
    seal = oracle / "seal.json"
    if seal.exists() or seal.is_symlink():
        raise FileExistsError("suite already sealed")
    rows = _suite_rows(public, oracle)
    record = {"schema": "hs4-file-suite-seal/v1", "scorer_sha256": NATIVE_SCORER_SHA256,
              "tasks": rows}
    raw = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    with seal.open("xb") as out:
        out.write(raw)
    _read_only(public)
    _read_only(oracle)
    return hashlib.sha256(raw).hexdigest()


def verify_seal(public_root: Path, oracle_root: Path, expected_sha256: str) -> None:
    """Recheck external seal identity, native scorer pin, source bytes and modes."""
    public, oracle = Path(public_root), Path(oracle_root)
    left, right = public.resolve(), oracle.resolve()
    if (public.is_symlink() or oracle.is_symlink() or left == right
            or left in right.parents or right in left.parents):
        raise ValueError("suite root symlink")
    seal = oracle / "seal.json"
    if seal.is_symlink() or not seal.is_file():
        raise ValueError("seal must be regular")
    raw = seal.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("seal digest mismatch")
    record = json.loads(raw)
    if (record.get("schema") != "hs4-file-suite-seal/v1"
            or record.get("scorer_sha256") != NATIVE_SCORER_SHA256
            or record.get("tasks") != _suite_rows(public, oracle)):
        raise ValueError("sealed suite identity mismatch")
    for root in (public, oracle):
        for directory, dirs, files in os.walk(root, followlinks=False):
            for path in [Path(directory), *(Path(directory) / name for name in dirs + files)]:
                mode = path.lstat().st_mode
                if stat.S_ISLNK(mode) or stat.S_IMODE(mode) & 0o222:
                    raise ValueError("suite contains symlink or writable path")
