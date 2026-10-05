"""Attestation validator for the transcribed DTAP judges (CJ-12).

Before CJ-12 nothing in the tree ever CHECKED `manifest.json`: `tools/transcribe.py`
WROTE the digests at authoring time against a disposable upstream clone and no
runtime, test, or script ever recomputed them. The byte-identity claim was
therefore unfalsifiable on this host. This module is that missing check, and it
is what makes the CJ-12 contract amendment safe: the guard may wrap a judge, but
it may never quietly change one.

What is verified (all of it locally, with no upstream clone):

  1. UPSTREAM BYTES — `sha256(judges/<case>/judge.py)` equals the manifest's
     `transcribed_judge_sha256`. Editing ANY judgment byte fails this.
  2. UPSTREAM PROVENANCE — the digest in each file's attribution header equals
     the manifest's `upstream_judge_sha256`, so the recorded upstream identity
     and the file's own claim about itself cannot drift apart.
  3. WRAPPER IDENTITY — `sha256(harness/judge_guard.py)` equals
     `meta.judge_guard.sha256`. OUR bytes, hashed separately from upstream's;
     the two facts are never mixed into one digest.
  4. GUARD EFFECT — the escalating/suppressing/narrow handler map recomputed from
     each untouched judge equals the map recorded in the manifest, so what the
     wrapper does to each judge is itself attested and auditable.
  5. COVERAGE — the manifest case set and the `judges/` directory agree.

`--update` re-attests: it recomputes 3-5 from disk and rewrites only those
fields. It NEVER writes `upstream_judge_sha256`, `upstream_config_sha256` or
`transcribed_judge_sha256` — a validator that can rewrite the thing it validates
is not a validator, and the upstream digests can only come from upstream.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .judge_guard import CONTRACT, guard_identity, scan_judge

DTAP_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = DTAP_DIR / "manifest.json"
JUDGES_DIR = DTAP_DIR / "judges"

_HEADER_SHA_RE = re.compile(r"^# upstream file SHA-256: ([0-9a-f]{64})$", re.M)


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def case_guard_record(judge_path: Path) -> Dict[str, Any]:
    """The wrapper-side facts for one case. Contains no upstream bytes."""
    guard = scan_judge(judge_path)
    record: Dict[str, Any] = {
        "wrapper": "harness/judge_guard.py",
        "judge_bytes_modified": False,
    }
    record.update(guard.handler_map())
    record["handler_map_sha256"] = guard.handler_map_sha256()
    return record


def verify(manifest_path: Optional[Path] = None, judges_dir: Optional[Path] = None) -> Tuple[bool, List[str]]:
    """Return (ok, problems). Never raises on a bad manifest — it reports."""
    manifest_path = Path(manifest_path or MANIFEST_PATH)
    judges_dir = Path(judges_dir or JUDGES_DIR)
    problems: List[str] = []
    manifest = json.loads(manifest_path.read_text())
    meta = manifest.get("meta", {})
    cases = manifest.get("cases", {})

    # 3. wrapper identity (ours), recorded distinctly from upstream's digests
    identity = guard_identity()
    recorded = meta.get("judge_guard")
    if not isinstance(recorded, dict):
        problems.append("meta.judge_guard is missing: the wrapper has no recorded identity")
    else:
        if recorded.get("sha256") != identity["sha256"]:
            problems.append(
                f"meta.judge_guard.sha256 {recorded.get('sha256')!r} != "
                f"sha256(harness/judge_guard.py) {identity['sha256']!r} "
                "(the exception-reporting wrapper changed; re-attest with --update)"
            )
        if recorded.get("module") != identity["module"]:
            problems.append(f"meta.judge_guard.module {recorded.get('module')!r} unexpected")
    if meta.get("transcription_contract") != CONTRACT:
        problems.append(
            f"meta.transcription_contract {meta.get('transcription_contract')!r} != {CONTRACT!r}"
        )

    # 5. coverage
    on_disk = {p.parent.name for p in Path(judges_dir).glob("*/judge.py")}
    for missing in sorted(on_disk - set(cases)):
        problems.append(f"judge on disk with no manifest entry: {missing}")
    for missing in sorted(set(cases) - on_disk):
        problems.append(f"manifest case with no judge on disk: {missing}")

    for case_id in sorted(set(cases) & on_disk):
        entry = cases[case_id]
        judge_path = Path(judges_dir) / case_id / "judge.py"
        # 1. upstream judgment bytes, unchanged
        actual = _sha256_file(judge_path)
        expected = entry.get("transcribed_judge_sha256")
        if actual != expected:
            problems.append(
                f"{case_id}: judge.py sha256 {actual} != attested "
                f"transcribed_judge_sha256 {expected} — the JUDGMENT LOGIC was edited"
            )
        # 2. the file's own upstream claim vs the manifest's
        header = _HEADER_SHA_RE.search(judge_path.read_text())
        if header is None:
            problems.append(f"{case_id}: attribution header carries no upstream SHA-256")
        elif header.group(1) != entry.get("upstream_judge_sha256"):
            problems.append(
                f"{case_id}: header upstream SHA-256 {header.group(1)} != manifest "
                f"upstream_judge_sha256 {entry.get('upstream_judge_sha256')}"
            )
        # 4. what the wrapper does to this judge
        rec = entry.get("guard")
        if not isinstance(rec, dict):
            problems.append(f"{case_id}: no guard record (manifest predates CJ-12)")
            continue
        fresh = case_guard_record(judge_path)
        if rec != fresh:
            problems.append(
                f"{case_id}: guard record does not match a fresh scan of the judge "
                f"(recorded {rec}, computed {fresh})"
            )
    return (not problems), problems


def update(manifest_path: Optional[Path] = None, judges_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Re-attest the WRAPPER-side facts only. Upstream digests are never touched."""
    path = Path(manifest_path or MANIFEST_PATH)
    judges_dir = Path(judges_dir or JUDGES_DIR)
    manifest = json.loads(path.read_text())
    manifest.setdefault("meta", {})["judge_guard"] = guard_identity()
    manifest["meta"]["transcription_contract"] = CONTRACT
    for case_id, entry in manifest.get("cases", {}).items():
        judge_path = Path(judges_dir) / case_id / "judge.py"
        if judge_path.exists():
            entry["guard"] = case_guard_record(judge_path)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main(update_manifest: bool = False) -> int:
    if update_manifest:
        update()
        print(f"re-attested wrapper facts in {MANIFEST_PATH}")
    ok, problems = verify()
    n_cases = len(json.loads(Path(MANIFEST_PATH).read_text()).get("cases", {}))
    if ok:
        print(f"attestation OK: {n_cases} judges byte-identical to their attested digests; "
              f"wrapper {guard_identity()['sha256'][:12]} pinned; contract {CONTRACT}")
        return 0
    print("ATTESTATION FAILED:")
    for p in problems:
        print(f"  - {p}")
    return 1
