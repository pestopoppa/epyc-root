"""Strict verifier projection for fold_gate's prospective structured records."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.champion_fold_gate/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "champion-fold-gate"
SCHEMA = "epyc.champion_fold_gate.v1"
GATE_VERSION = "fold_gate.v4"
MAX_BYTES = 8 << 20
SHA = frozenset("0123456789abcdef")
IDENTICAL_CLASSES = frozenset(("SAME", "EXPLAINED", "EXPLAINED-PATH", "UNEXPLAINED"))
PASS_CLASSES = (IDENTICAL_CLASSES - frozenset(("UNEXPLAINED",))) | frozenset(("EXPLAINED-UI", "EXPECTED"))
ALL_CLASSES = PASS_CLASSES | frozenset(("CODE-DIFF", "UNEXPLAINED", "MISSING", "EXTRA"))
SYMLINK_CLASSES = frozenset(("MATCHED", "SYMLINK-MISSING", "SYMLINK-DIFF", "SYMLINK-DANGLING"))
ACCEPTOR = "fold_gate.v4:EXPLAINED-UI"
LIBRARY_NAME = re.compile(r"^lib(ggml|llama|mtmd).*\.so(\..*)?$")


def _read(path: Path, limit: int = MAX_BYTES) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise OSError(f"not a regular file: {path}")
        with os.fdopen(fd, "rb") as stream:
            raw = stream.read(limit + 1)
    except OSError as exc:
        raise ProjectionError(f"champion-fold-gate input unreadable: {path}: {exc}") from exc
    if len(raw) > limit:
        raise ProjectionError(f"champion-fold-gate input exceeds bound: {path}")
    return raw


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= SHA


def _stem(name: str) -> str:
    return re.sub(r"\.so(\..*)?$", ".so", name)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProjectionError(f"champion-fold-gate refused: {message}")


def _library_proposition(row: dict, base_store: str, candidate_store: str) -> str:
    identity = "is identical" if row["code_identical"] else "is not established as identical"
    pair = (f"{row['base_soname']} -> {row['candidate_soname']}"
            if row["base_soname"] and row["candidate_soname"] else row["soname_stem"])
    return (f"Fold gate v4 classified {row['verdict_class']} for {pair}: executable code {identity} "
            f"between base store {base_store} and candidate store {candidate_store}.")


def _exception_proposition(row: dict) -> str:
    return (f"Fold gate v4 accepted the EXPLAINED-UI exception for {row['soname_stem']} under "
            "its deterministic UI-initializer rule; no other code-difference exception is implied.")


def _store(value: Any, where: str) -> dict:
    _require(isinstance(value, dict) and set(value) == {"store_path", "sha256s_path", "sha256s_sha256"},
             f"{where} store attestation shape")
    _require(all(isinstance(value[k], str) and value[k] for k in ("store_path", "sha256s_path")),
             f"{where} store path missing")
    _require(Path(value["store_path"]).is_absolute() and Path(value["sha256s_path"]).is_absolute(),
             f"{where} store attestation paths must be absolute")
    _require(_is_sha(value["sha256s_sha256"]), f"{where} SHA256SUMS digest malformed")
    _require(str(Path(value["sha256s_path"])) == str(Path(value["store_path"]) / "SHA256SUMS"),
             f"{where} SHA256SUMS path does not bind to its store")
    actual = hashlib.sha256(_read(Path(value["sha256s_path"]), limit=64 << 20)).hexdigest()
    _require(actual == value["sha256s_sha256"], f"{where} SHA256SUMS digest does not re-derive")
    return value


def _document(raw: bytes, path: Path) -> dict:
    try:
        doc = json.loads(raw)
    except ValueError as exc:
        raise ProjectionError(f"champion-fold-gate {path.name}: not JSON") from exc
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        return {}
    _require(set(doc) == {"schema", "gate_version", "recorded_at", "base", "candidate",
                          "libraries", "symlinks", "exceptions", "gate_verdict"},
             "record fields differ from the closed schema")
    _require(doc["gate_version"] == GATE_VERSION, "unsupported gate version")
    _require(isinstance(doc["recorded_at"], str) and doc["recorded_at"].endswith("Z"),
             "record timestamp missing or not UTC")
    try:
        recorded_at = datetime.fromisoformat(doc["recorded_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProjectionError("champion-fold-gate record timestamp is not ISO-8601") from exc
    _require(recorded_at.utcoffset() == timezone.utc.utcoffset(recorded_at),
             "record timestamp is not UTC")
    base, candidate = _store(doc["base"], "base"), _store(doc["candidate"], "candidate")
    _require(isinstance(doc["libraries"], list) and doc["libraries"], "no library records")
    _require(isinstance(doc["symlinks"], list), "symlink records are not a list")
    _require(isinstance(doc["exceptions"], list), "exception records are not a list")
    stems = set()
    seen_classes = []
    for row in doc["libraries"]:
        _require(isinstance(row, dict) and set(row) == {"record_type", "soname_stem", "base_soname",
                 "candidate_soname", "verdict_class", "code_identical", "differing_sections",
                 "decided_proposition"}, "library record shape")
        stem = row["soname_stem"]
        _require(row["record_type"] == "library" and isinstance(stem, str) and stem.startswith("lib"),
                 "library record identity malformed")
        _require(stem not in stems, f"duplicate library stem {stem}")
        stems.add(stem)
        for name in ("base_soname", "candidate_soname"):
            _require(row[name] is None or isinstance(row[name], str), f"{stem} {name} malformed")
        _require(row["base_soname"] is not None or row["candidate_soname"] is not None,
                 f"{stem} has no soname")
        _require(all(LIBRARY_NAME.fullmatch(row[name]) for name in ("base_soname", "candidate_soname")
                     if row[name]), f"{stem} has a foreign soname")
        _require(all(_stem(row[name]) == stem for name in ("base_soname", "candidate_soname") if row[name]),
                 f"{stem} does not match its soname")
        _require(isinstance(row["verdict_class"], str) and row["verdict_class"] in ALL_CLASSES,
                 f"{stem} has unknown verdict")
        _require((row["verdict_class"] != "MISSING" or
                  (row["base_soname"] is not None and row["candidate_soname"] is None)) and
                 (row["verdict_class"] != "EXTRA" or
                  (row["base_soname"] is None and row["candidate_soname"] is not None)),
                 f"{stem} missing/extra class differs from its sonames")
        _require(type(row["code_identical"]) is bool and
                 row["code_identical"] == (row["verdict_class"] in IDENTICAL_CLASSES),
                 f"{stem} code-identity flag differs from its verdict")
        _require(isinstance(row["differing_sections"], list) and
                 all(isinstance(item, str) for item in row["differing_sections"]),
                 f"{stem} differing sections malformed")
        expected = _library_proposition(row, base["store_path"], candidate["store_path"])
        _require(row["decided_proposition"] == expected, f"{stem} proposition does not re-derive")
        seen_classes.append(row["verdict_class"])
    link_classes = []
    for link in doc["symlinks"]:
        _require(isinstance(link, dict) and set(link) == {"name", "base_target", "candidate_target",
                 "candidate_target_exists", "verdict_class"},
                 "symlink record shape")
        _require(isinstance(link["name"], str) and LIBRARY_NAME.fullmatch(link["name"]),
                 "symlink name malformed")
        _require(isinstance(link["base_target"], str) and link["base_target"], "base symlink target missing")
        _require(link["candidate_target"] is None or isinstance(link["candidate_target"], str),
                 "candidate symlink target malformed")
        _require(type(link["candidate_target_exists"]) is bool, "candidate symlink target existence malformed")
        _require(isinstance(link["verdict_class"], str) and link["verdict_class"] in SYMLINK_CLASSES,
                 "unknown symlink verdict")
        target = link["candidate_target"]
        target_status = ("SYMLINK-MISSING" if target is None else
                         "MATCHED" if re.sub(r"\.\d{4,6}$", ".BN", link["base_target"]) ==
                         re.sub(r"\.\d{4,6}$", ".BN", target) and link["candidate_target_exists"] else
                         "SYMLINK-DANGLING" if re.sub(r"\.\d{4,6}$", ".BN", link["base_target"]) ==
                         re.sub(r"\.\d{4,6}$", ".BN", target) else "SYMLINK-DIFF")
        _require(link["verdict_class"] == target_status, "symlink verdict does not re-derive")
        if target is None:
            _require(not link["candidate_target_exists"], "missing symlink target state inconsistent")
        link_classes.append(link["verdict_class"])
    expected_exceptions = {row["soname_stem"]: row for row in doc["libraries"]
                           if row["verdict_class"] == "EXPLAINED-UI"}
    exceptions = {}
    for exception in doc["exceptions"]:
        _require(isinstance(exception, dict) and set(exception) == {"record_type", "exception_class",
                 "library_stem", "accepted_by", "decided_proposition", "differing_sections"},
                 "exception record shape")
        stem = exception["library_stem"]
        _require(isinstance(stem, str), "exception library stem malformed")
        _require(exception["record_type"] == "accepted_exception" and
                 exception["exception_class"] == "EXPLAINED-UI" and
                 exception["accepted_by"] == ACCEPTOR, "exception acceptance identity malformed")
        _require(stem in expected_exceptions and stem not in exceptions,
                 "exception does not match one unique EXPLAINED-UI library")
        _require(exception["differing_sections"] == expected_exceptions[stem]["differing_sections"],
                 f"{stem} exception details differ from library verdict")
        _require(exception["decided_proposition"] == _exception_proposition(expected_exceptions[stem]),
                 f"{stem} exception proposition does not re-derive")
        exceptions[stem] = exception
    _require(set(exceptions) == set(expected_exceptions), "EXPLAINED-UI library is missing its exception record")
    calculated = all(v in PASS_CLASSES for v in seen_classes) and all(v == "MATCHED" for v in link_classes)
    _require(doc["gate_verdict"] == ("PASS" if calculated else "FAIL"),
             "overall gate verdict differs from library/symlink records")
    return doc


def units(path: str | Path) -> list[Path]:
    path = Path(path)
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    return sorted(set(path.glob("fold_gate_record.json")) | set(path.glob("*/fold_gate_record.json")))


def native_rows(path: str | Path) -> tuple[dict, ...]:
    p = Path(path)
    if not p.is_file():
        return ()
    raw = _read(p)
    doc = _document(raw, p)
    if not doc:
        return ()
    digest = hashlib.sha256(raw).hexdigest()
    common = {"record_path": str(p.resolve()), "record_sha256": digest,
              "recorded_at": doc["recorded_at"], "gate_verdict": doc["gate_verdict"],
              "base": doc["base"], "candidate": doc["candidate"]}
    rows = []
    for row in doc["libraries"]:
        rows.append({**common, "record_type": "library", "record": row,
                     "record_key": row["soname_stem"]})
    for row in doc["exceptions"]:
        rows.append({**common, "record_type": "accepted_exception", "record": row,
                     "record_key": f"{row['library_stem']}:{row['exception_class']}"})
    return tuple(rows)


def _stable(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _reopen(native: dict) -> dict:
    rows = native_rows(native["record_path"])
    if not any(_stable(row) == _stable(native) for row in rows):
        raise ProjectionError("champion-fold-gate native record changed since reopening")
    return native["record"]


@register(SOURCE_KIND, source_class="verifier", decided_proposition_field="record.decided_proposition")
def project(native: dict) -> ClaimTuple:
    row = _reopen(native)
    record_type = native["record_type"]
    if record_type == "library":
        stem = row["soname_stem"]
        verdict = row["verdict_class"]
        proposition = row["decided_proposition"]
        value = row["code_identical"]
        metric = "champion_fold_library_code_identity"
    elif record_type == "accepted_exception":
        stem = native["record_key"]
        verdict = row["exception_class"]
        proposition = row["decided_proposition"]
        value = True
        metric = "champion_fold_exception_acceptance"
    else:
        raise ProjectionError(f"champion-fold-gate unknown record type {record_type!r}")
    identity = hashlib.sha256(f"{native['record_sha256']}:{record_type}:{stem}".encode()).hexdigest()[:32]
    return ClaimTuple(measurement_id=f"fold-gate:{identity}", metric=metric, value=value,
                      date=native["recorded_at"], category="CANDIDATE", metric_direction="higher_better",
                      protocol_id="", claim=proposition, decided_proposition=proposition,
                      source_class="verifier", source_kind=ADAPTER_ID, binding_kind="identity",
                      attestation_path=native["record_path"], attestation_sha256=native["record_sha256"],
                      attestation_locator=native["record_path"], attestation_verified=True,
                      extra={"record_type": record_type, "record_key": native["record_key"],
                             "record_sha256": native["record_sha256"], "gate_verdict": native["gate_verdict"],
                             "verdict_class": verdict, "base_store": native["base"],
                             "candidate_store": native["candidate"], "native_record": row})

