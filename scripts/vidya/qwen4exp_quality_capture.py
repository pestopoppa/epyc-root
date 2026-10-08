#!/usr/bin/env python3
"""SC54 prospective llama-perplexity receipt writer (stdlib only).

Place this wrapper inside the existing measurement/region-lock invocation so it launches
exactly the already-approved producer argv while it captures the producer's actual process,
environment, loaded shared objects, and native output. It makes no quality verdict.
"""
from __future__ import annotations

import argparse
from collections import Counter
import stat
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Any

SCHEMA = "epyc.vidya.qwen4exp_quality_measurement.v1"
ENV_PREFIXES = ("GGML_", "OMP_")

def unique_json_pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError("duplicate JSON key: "+key)
        result[key]=value
    return result
PPL_FINAL = re.compile(r"Final estimate: PPL = ([^\s]+) \+/- ([^\s]+)")
PPL_Q = re.compile(r"^Mean PPL\(Q\)\s*:\s*([^\s]+)\s*±\s*([^\s]+)\s*$", re.M)
PPL_BASE = re.compile(r"^Mean PPL\(base\)\s*:\s*([^\s]+)\s*±\s*([^\s]+)\s*$", re.M)
PPL_RATIO = re.compile(r"^Mean PPL\(Q\)/PPL\(base\)\s*:\s*([^\s]+)\s*±\s*([^\s]+)\s*$", re.M)
PPL_DELTA = re.compile(r"^Mean PPL\(Q\)-PPL\(base\)\s*:\s*([^\s]+)\s*±\s*([^\s]+)\s*$", re.M)
LOG_RATIO = re.compile(r"^Mean ln\(PPL\(Q\)/PPL\(base\)\)\s*:\s*([^\s]+)\s*±\s*([^\s]+)\s*$", re.M)
KLD_MEAN = re.compile(r"^Mean\s+KLD:\s*([^\s]+)\s*±\s*([^\s]+)\s*$", re.M)
KLD_LABELS = ("Maximum", "99.9%", "99.0%", "95.0%", "90.0%", "Median", "10.0%", "5.0%", "1.0%", "0.1%", "Minimum")
KLD_PERCENTILE = re.compile(r"^\s*(Maximum|99\.9%|99\.0%|95\.0%|90\.0%|Median|10\.0%|5\.0%|1\.0%|0\.1%|Minimum)\s+KLD:\s*([^\s]+)\s*$", re.M)
CHUNKS = re.compile(r"(?:--chunks\s+)(\d+)")
RUN_SETTINGS = re.compile(
    r"(?:calculating perplexity|computing):? (?:computing over|over) (\d+) chunks, "
    r"n_ctx=(\d+), batch_size=(\d+), n_seq=(\d+)"
)
PPL_CHUNK_IDS = re.compile(r"\[(\d+)\][0-9.eE+-]+")
KLD_CHUNK_IDS = re.compile(r"^\s*(\d+)\s+[0-9.eE+-]+\s+±", re.M)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def stable_bytes_identity(path: Path, limit: int = 16 << 20) -> tuple[bytes,dict[str,Any]]:
    """Bounded no-follow same-FD read for source-authored declarations."""
    parent=os.open(path.parent,os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0))
    try:
        named=os.stat(path.name,dir_fd=parent,follow_symlinks=False)
        fd=os.open(path.name,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0)|getattr(os,"O_NONBLOCK",0),dir_fd=parent)
        try:
            before=os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size>limit: raise ValueError("declaration is not a bounded regular file")
            chunks=[];size=0;digest=hashlib.sha256()
            while True:
                block=os.read(fd,min(1<<20,limit+1-size))
                if not block:break
                size+=len(block)
                if size>limit:raise ValueError("declaration exceeds retained byte bound")
                chunks.append(block);digest.update(block)
            after=os.fstat(fd);named_after=os.stat(path.name,dir_fd=parent,follow_symlinks=False)
            fields=lambda x:(x.st_dev,x.st_ino,x.st_mode,x.st_size,x.st_mtime_ns,x.st_ctime_ns)
            if fields(before)!=fields(after) or fields(named)!=fields(named_after) or (before.st_dev,before.st_ino)!=(named.st_dev,named.st_ino) or size!=before.st_size: raise ValueError("declaration changed during stable read")
            identity={"path":str(path.absolute()),"sha256":digest.hexdigest(),"size_bytes":size,"mode":before.st_mode,"device":before.st_dev,"inode":before.st_ino,"mtime_ns":before.st_mtime_ns,"ctime_ns":before.st_ctime_ns}
            return b"".join(chunks),identity
        finally:os.close(fd)
    finally:os.close(parent)

def sha256_file(path: Path) -> str:
    return file_identity(path)["sha256"]


def file_identity(path: Path) -> dict[str, Any]:
    """No-follow, same-FD hash with before/after inode and metadata checks."""
    parent = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        before_name = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        fd = os.open(path.name, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0), dir_fd=parent)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):
                raise ValueError(f"not a regular no-follow file: {path}")
            digest, size = hashlib.sha256(), 0
            while True:
                block = os.read(fd, 8 * 1024 * 1024)
                if not block:
                    break
                digest.update(block); size += len(block)
            after = os.fstat(fd)
            after_name = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            fields = lambda x: (x.st_dev, x.st_ino, x.st_mode, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
            if fields(before) != fields(after) or fields(before_name) != fields(after_name) or (before.st_dev, before.st_ino) != (before_name.st_dev, before_name.st_ino) or size != after.st_size:
                raise ValueError(f"file changed or pathname replaced while hashing: {path}")
            return {"path": str(path.absolute()), "sha256": digest.hexdigest(), "size_bytes": size,
                    "mode": before.st_mode, "device": before.st_dev, "inode": before.st_ino,
                    "mtime_ns": before.st_mtime_ns, "ctime_ns": before.st_ctime_ns}
        finally:
            os.close(fd)
    finally:
        os.close(parent)


def maps_shared_objects(pid: int) -> list[dict[str, Any]] | None:
    try:
        rows = Path(f"/proc/{pid}/maps").read_text(encoding="utf-8", errors="replace").splitlines()
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return None
    found = []
    for row in rows:
        fields = row.split(maxsplit=5)
        if len(fields) == 6 and fields[5].startswith("/") and ".so" in fields[5]:
            major, minor = (int(x, 16) for x in fields[3].split(":"))
            found.append({"path": fields[5], "deleted": fields[5].endswith(" (deleted)"),
                          "device_major": major, "device_minor": minor, "inode": int(fields[4]),
                          "observed_at_utc": utc_now()})
    return found


def monitor_maps(proc: subprocess.Popen[bytes], seen: dict[tuple, dict[str, Any]],
                 stop: threading.Event, *, monotonic_ns=None) -> None:
    """Sample maps at 40 Hz but retain bounded endpoints and exact poll counts only."""
    clock_ns = monotonic_ns or time.monotonic_ns
    next_hash: dict[tuple, int] = {}
    while not stop.is_set() and proc.poll() is None:
        rows = maps_shared_objects(proc.pid)
        now = clock_ns()
        if rows is not None:
            # /proc/maps can contain many regions for one object. Count one sample for
            # each distinct path/device/inode/deleted identity per maps snapshot.
            snapshot: dict[tuple, dict[str, Any]] = {}
            for row in rows:
                key = (row["path"], row["device_major"], row["device_minor"],
                       row["inode"], row["deleted"])
                snapshot.setdefault(key, row)
            for key, row in snapshot.items():
                slot = seen.setdefault(key, {
                    "mapping_first": None, "mapping_latest": None,
                    "mapping_sample_count": 0, "deleted_mapping_observed": False,
                    "live_first": None, "live_latest": None,
                    "live_hash_sample_count": 0, "first_changed_identity": None,
                    "identity_change_observation_count": 0,
                    "live_identity_error": None,
                })
                if slot["mapping_first"] is None:
                    slot["mapping_first"] = row
                slot["mapping_latest"] = row
                slot["mapping_sample_count"] += 1
                slot["deleted_mapping_observed"] |= row["deleted"]
                if row["deleted"]:
                    continue
                if now >= next_hash.get(key, 0):
                    try:
                        identity = file_identity(Path(row["path"]))
                        if (identity["inode"] != row["inode"] or
                                os.major(identity["device"]) != row["device_major"] or
                                os.minor(identity["device"]) != row["device_minor"]):
                            raise ValueError("mapped path device/inode differs at live sample")
                        observation = {"observed_at_utc": utc_now(), "identity": identity}
                        if slot["live_first"] is None:
                            slot["live_first"] = observation
                        elif identity != slot["live_first"]["identity"]:
                            slot["identity_change_observation_count"] += 1
                            if slot["first_changed_identity"] is None:
                                slot["first_changed_identity"] = identity
                        slot["live_latest"] = observation
                        slot["live_hash_sample_count"] += 1
                    except (OSError, ValueError) as exc:
                        # Sticky: an incomplete observation cannot be erased by a later
                        # successful sample. Store one bounded diagnostic only.
                        if slot["live_identity_error"] is None:
                            slot["live_identity_error"] = type(exc).__name__ + ": " + str(exc)[:240]
                    next_hash[key] = now + 1_000_000_000
        stop.wait(0.025)

def compiled_knob_evidence(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Hash and scan the same opened loaded-object inode for exact getenv knob bytes."""
    expected=b"GGML_IQK\0"
    parent=os.open(path.parent,os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0))
    try:
        name_before=os.stat(path.name,dir_fd=parent,follow_symlinks=False)
        fd=os.open(path.name,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0)|getattr(os,"O_NONBLOCK",0),dir_fd=parent)
        try:
            before=os.fstat(fd)
            if not stat.S_ISREG(before.st_mode): raise ValueError("loaded shared object is not a regular file")
            digest=hashlib.sha256();size=0;overlap=b"";found=False
            while True:
                block=os.read(fd,8<<20)
                if not block:break
                size+=len(block);digest.update(block);scan=overlap+block
                if expected in scan:found=True
                overlap=scan[-(len(expected)-1):]
            after=os.fstat(fd);name_after=os.stat(path.name,dir_fd=parent,follow_symlinks=False)
            fields=lambda x:(x.st_dev,x.st_ino,x.st_mode,x.st_size,x.st_mtime_ns,x.st_ctime_ns)
            if fields(before)!=fields(after) or fields(name_before)!=fields(name_after) or (before.st_dev,before.st_ino)!=(name_before.st_dev,name_before.st_ino) or size!=after.st_size:
                raise ValueError("loaded object changed during compiled-knob custody scan")
            ident={"path":str(path.absolute()),"sha256":digest.hexdigest(),"size_bytes":size,"mode":before.st_mode,"device":before.st_dev,"inode":before.st_ino,"mtime_ns":before.st_mtime_ns,"ctime_ns":before.st_ctime_ns}
            ev={"method":"same-fd exact byte scan","required_bytes_hex":expected.hex(),"found_exact":found}
            return ident,ev
        finally:os.close(fd)
    finally:os.close(parent)

def metric(name: str, value: str, spread: str | None, unit: str,
           native_direction: str = "unknown") -> dict[str, Any]:
    v = float(value)
    s = None if spread is None else float(spread)
    if not math.isfinite(v) or (s is not None and not math.isfinite(s)):
        raise ValueError(f"non-finite native metric: {name}")
    return {"native_label": name, "value": v, "unit": unit,
            "native_direction": native_direction,
            "native_spread": s,
            "spread_semantics": "corpus-sampling uncertainty; not run-to-run noise" if s is not None else "not emitted"}


def parse_native_metrics(log_text: str, mode: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if mode in {"ppl", "ppl-anchor"}:
        matches = PPL_FINAL.findall(log_text)
        if len(matches) != 1:
            raise ValueError(f"expected exactly one native Final estimate PPL row, got {len(matches)}")
        value, spread = matches[0]
        out.append(metric("Final estimate: PPL", value, spread, "unknown"))
        return out
    for pattern, label, unit in (
        (PPL_Q, "Mean PPL(Q)", "unknown"),
        (PPL_BASE, "Mean PPL(base)", "unknown"),
        (PPL_RATIO, "Mean PPL(Q)/PPL(base)", "unknown"),
        (PPL_DELTA, "Mean PPL(Q)-PPL(base)", "unknown"),
        (LOG_RATIO, "Mean ln(PPL(Q)/PPL(base))", "unknown"),
        (KLD_MEAN, "Mean KLD", "unknown"),
    ):
        matches = pattern.findall(log_text)
        if len(matches) != 1:
            raise ValueError(f"expected exactly one native {label} row, got {len(matches)}")
        value, spread = matches[0]
        out.append(metric(label, value, spread, unit))
    percentile_rows = KLD_PERCENTILE.findall(log_text)
    if Counter(label for label, _ in percentile_rows) != Counter(KLD_LABELS):
        raise ValueError("native KLD order-statistic labels are duplicated, missing, or unexpected")
    for label, value in percentile_rows:
        out.append(metric(f"{label} KLD", value, None,
                          "unknown"))
    return out


def parse_native_window(log_text: str, mode: str) -> dict[str, Any]:
    settings = RUN_SETTINGS.findall(log_text)
    if len(settings) != 1:
        raise ValueError(f"expected one native scoring-window line, got {len(settings)}")
    n_chunks, n_ctx, batch_size, n_seq = (int(x) for x in settings[0])
    ids = PPL_CHUNK_IDS.findall(log_text) if mode in {"ppl", "ppl-anchor"} else KLD_CHUNK_IDS.findall(log_text)
    chunk_ids = [int(x) for x in ids]
    if chunk_ids != list(range(1, n_chunks + 1)):
        raise ValueError("native output chunk rows are missing, duplicated, or out of order")
    return {"native_chunks_requested_and_reported": n_chunks,
            "scored_chunk_ids": chunk_ids, "scored_chunk_range": [1, n_chunks],
            "n_ctx": n_ctx, "batch_size": batch_size, "n_seq": n_seq,
            "ny_rule": "llama-perplexity all-logits implementation uses n_ctx/2",
            "ny_derived_from_native_n_ctx": n_ctx // 2}


_IDENTITY_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def validate_identity_token(value: str) -> str:
    if not isinstance(value, str) or not _IDENTITY_TOKEN.fullmatch(value):
        raise ValueError("run, pair and arm IDs must be simple 1-128 character identity tokens")
    return value


def output_paths(out_dir: Path, run_id: str, arm_id: str) -> tuple[Path, Path]:
    run_id = validate_identity_token(run_id)
    arm_id = validate_identity_token(arm_id)
    root = Path(out_dir).resolve()
    return (root / f"{run_id}.{arm_id}.native.log",
            root / f"{run_id}.{arm_id}.quality.json")


def _open_parent_dir(path: Path) -> tuple[int, tuple[int, int]]:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        named = os.stat(path, follow_symlinks=False)
        if (not stat.S_ISDIR(opened.st_mode) or
                (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)):
            raise ValueError("output directory changed or is not a real directory")
        return fd, (opened.st_dev, opened.st_ino)
    except Exception:
        os.close(fd)
        raise


def _check_parent_dir(path: Path, fd: int, identity: tuple[int, int]) -> None:
    opened = os.fstat(fd)
    named = os.stat(path, follow_symlinks=False)
    if (opened.st_dev, opened.st_ino) != identity or (named.st_dev, named.st_ino) != identity:
        raise ValueError("output directory pathname changed during publication")


def refuse_existing_outputs(*paths: Path) -> None:
    """Fail before producer start if any immutable receipt/log name already exists."""
    if not paths or any(Path(path).parent != Path(paths[0]).parent for path in paths):
        raise ValueError("native output files must share one output directory")
    parent, identity = _open_parent_dir(Path(paths[0]).parent)
    try:
        for path in paths:
            try:
                os.stat(Path(path).name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                continue
            raise FileExistsError(f"immutable output already exists: {Path(path).name}")
        _check_parent_dir(Path(paths[0]).parent, parent, identity)
    finally:
        os.close(parent)


def open_native_log(path: Path):
    """Create an original native log exclusively relative to a pinned directory FD."""
    parent, identity = _open_parent_dir(path.parent)
    try:
        flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
        fd = os.open(path.name, flags, 0o600, dir_fd=parent)
        try:
            _check_parent_dir(path.parent, parent, identity)
        except Exception:
            os.close(fd)
            os.unlink(path.name, dir_fd=parent)
            raise
        return os.fdopen(fd, "wb")
    finally:
        os.close(parent)


def atomic_json(path: Path, record: dict[str, Any]) -> None:
    """Publish immutable JSON relative to a pinned directory FD; existing names refuse."""
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    record["self_sha256"] = hashlib.sha256(encoded).hexdigest()
    final = json.dumps(record, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
    parent, identity = _open_parent_dir(path.parent)
    tmp_name = None
    try:
        for _attempt in range(10):
            candidate = f".{path.name}.{secrets.token_hex(16)}.tmp"
            try:
                fd = os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                             getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
                             0o600, dir_fd=parent)
            except FileExistsError:
                continue
            tmp_name = candidate
            break
        else:
            raise FileExistsError("could not allocate an exclusive receipt temporary name")
        with os.fdopen(fd, "wb") as stream:
            stream.write(final)
            stream.flush()
            os.fsync(stream.fileno())
        _check_parent_dir(path.parent, parent, identity)
        os.link(tmp_name, path.name, src_dir_fd=parent, dst_dir_fd=parent,
                follow_symlinks=False)
        os.fsync(parent)
        _check_parent_dir(path.parent, parent, identity)
    finally:
        if tmp_name is not None:
            try:
                os.unlink(tmp_name, dir_fd=parent)
            except FileNotFoundError:
                pass
        os.close(parent)


def parse_env(pairs: list[str]) -> dict[str, str]:
    env = dict(os.environ)
    for pair in pairs:
        if "=" not in pair:
            raise ValueError("--env must be NAME=VALUE")
        name, value = pair.split("=", 1)
        if not (name.startswith(ENV_PREFIXES) or name == "LD_LIBRARY_PATH"):
            raise ValueError(f"environment capture restricted to GGML_*, OMP_*, LD_LIBRARY_PATH: {name}")
        env[name] = value
    return env


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--pair-id", required=True,
                    help="shared identity for the paired anchor/candidate window")
    ap.add_argument("--arm-id", required=True)
    ap.add_argument("--mode", choices=("ppl", "ppl-anchor", "kld"), required=True)
    ap.add_argument("--source-revision", required=True,
                    help="revision asserted by the invoking source harness; never substitutes for binary digest")
    ap.add_argument("--model-name", required=True)
    ap.add_argument("--quant", required=True)
    ap.add_argument("--protocol-id", default="unknown",
                    help="human-ratified protocol id actually used, else literal unknown")
    ap.add_argument("--metric-spec", type=Path, required=True,
                    help="producer/measurement-author authored metric declaration fixed before invocation")
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--ny", type=int, required=True,
                    help="native output batch N_y recorded by the source harness; never inferred")
    ap.add_argument("--reference-logits", type=Path,
                    help="digest-pinned `--kl-divergence-base` artifact for KLD mode")
    ap.add_argument("--output-logits", type=Path,
                    help="new `--kl-divergence-base` artifact written by an anchor PPL pass")
    ap.add_argument("--reference-model", type=Path,
                    help="anchor GGUF whose logits are stored in --reference-logits")
    ap.add_argument("--anchor-receipt", type=Path,
                    help="immutable successful PPL-anchor receipt binding paired model/logits/corpus/window for KLD")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--env", action="append", default=[], metavar="NAME=VALUE",
                    help="explicit effective GGML_*/OMP_*/LD_LIBRARY_PATH override")
    ap.add_argument("command", nargs=argparse.REMAINDER,
                    help="exact producer argv after --")
    a = ap.parse_args()
    argv = a.command[1:] if a.command and a.command[0] == "--" else a.command
    if not argv:
        ap.error("empty producer argv")
    if a.ny <= 0:
        ap.error("--ny must be positive and producer-authored by the harness")
    if a.mode == "kld" and a.reference_logits is None:
        ap.error("KLD requires --reference-logits")
    if a.mode == "kld" and a.reference_model is None:
        ap.error("KLD requires --reference-model")
    if a.mode == "kld" and a.anchor_receipt is None:
        ap.error("KLD requires the original prospective PPL-anchor producer receipt")
    if a.mode == "kld" and a.reference_model.resolve()==a.model.resolve():
        ap.error("KLD reference model must be the paired anchor, not the candidate")
    if a.mode != "kld" and (a.reference_logits is not None or a.reference_model is not None or a.anchor_receipt is not None):
        ap.error("--reference-logits/--reference-model are inputs only for KLD mode")
    if a.mode == "ppl-anchor" and a.output_logits is None:
        ap.error("PPL anchor mode requires --output-logits")
    if a.mode == "ppl-anchor":
        try: os.lstat(a.output_logits)
        except FileNotFoundError: pass
        else: ap.error("anchor output path must be absent, including dangling symlinks")
    if a.mode != "ppl-anchor" and a.output_logits is not None:
        ap.error("--output-logits is only valid for PPL anchor mode")
    try:
        for value in (a.run_id, a.pair_id, a.arm_id):
            validate_identity_token(value)
    except ValueError as exc:
        ap.error(str(exc))
    def option_values(*names: str) -> list[str]:
        return [argv[i + 1] for i,item in enumerate(argv[:-1]) if item in names]
    def option_value(*names: str) -> str | None:
        values=option_values(*names)
        return values[0] if len(values)==1 else None
    model_values=option_values("-m","--model");corpus_values=option_values("-f","--file")
    context_values=option_values("-c","--ctx-size");chunks_values=option_values("--chunks")
    if any(len(x)!=1 for x in (model_values,corpus_values,context_values,chunks_values)):
        ap.error("exact producer argv must contain one model, corpus, context and chunk option")
    model_arg=model_values[0];corpus_arg=corpus_values[0];context_arg=context_values[0];chunks_arg=chunks_values[0]
    if model_arg is None or Path(model_arg).resolve() != a.model.resolve():
        ap.error("exact producer argv must name the same --model/-m supplied to the capture")
    if corpus_arg is None or Path(corpus_arg).resolve() != a.corpus.resolve():
        ap.error("exact producer argv must name the same --file/-f supplied to the capture")
    if context_arg is None or chunks_arg is None:
        ap.error("exact producer argv must carry -c/--ctx-size and --chunks")
    kld_flags=argv.count("--kl-divergence");base_values=option_values("--kl-divergence-base")
    if a.mode == "kld":
        if kld_flags!=1 or len(base_values)!=1 or Path(base_values[0]).resolve()!=a.reference_logits.resolve() or argv.index("--kl-divergence")!=len(argv)-1 or argv.index("--kl-divergence-base")+2!=len(argv)-1:
            ap.error("KLD requires exact single --kl-divergence and digest-pinned --kl-divergence-base")
    elif a.mode == "ppl-anchor":
        if kld_flags or len(base_values)!=1 or Path(base_values[0]).resolve()!=a.output_logits.resolve() or argv.index("--kl-divergence-base")+2!=len(argv):
            ap.error("PPL anchor requires one output --kl-divergence-base and no --kl-divergence")
    elif kld_flags or base_values:
        ap.error("PPL mode cannot carry KLD flags")
    # Bind file operands to canonical absolute names used by custody checks and the child.
    a.model=a.model.resolve(strict=True);a.corpus=a.corpus.resolve(strict=True)
    if a.reference_logits is not None:a.reference_logits=a.reference_logits.resolve(strict=True)
    if a.reference_model is not None:a.reference_model=a.reference_model.resolve(strict=True)
    if a.anchor_receipt is not None:a.anchor_receipt=a.anchor_receipt.resolve(strict=True)
    if a.output_logits is not None:a.output_logits=a.output_logits.resolve(strict=False)
    for i,item in enumerate(argv[:-1]):
        if item in {"-m","--model"}:argv[i+1]=str(a.model)
        elif item in {"-f","--file"}:argv[i+1]=str(a.corpus)
        elif item=="--kl-divergence-base":
            resolved=Path(argv[i+1]).resolve(strict=(a.mode!="ppl-anchor"))
            argv[i+1]=str(resolved)

    out_dir = a.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path, receipt_path = output_paths(out_dir, a.run_id, a.arm_id)
    refuse_existing_outputs(log_path, receipt_path)
    env = parse_env(a.env)
    binary = Path(argv[0])
    if not binary.is_absolute():
        from shutil import which
        located = which(argv[0], path=env.get("PATH"))
        if located is None:
            raise SystemExit(f"producer executable not found: {argv[0]}")
        binary = Path(located)
    spec_bytes,spec_before=stable_bytes_identity(a.metric_spec)
    metric_spec=json.loads(spec_bytes.decode("utf-8"),object_pairs_hook=unique_json_pairs,parse_constant=lambda x: (_ for _ in ()).throw(ValueError("non-finite JSON constant: "+x)))
    expected_spec = {"schema", "run_id", "pair_id", "arm_id", "mode", "author", "issued_at_utc", "protocol_id", "metrics"}
    if (not isinstance(metric_spec, dict) or set(metric_spec) != expected_spec or
            metric_spec["schema"] != "epyc.vidya.qwen4exp_quality_metric_declaration.v1" or
            (metric_spec["run_id"], metric_spec["pair_id"], metric_spec["arm_id"], metric_spec["mode"]) != (a.run_id, a.pair_id, a.arm_id, a.mode) or
            not isinstance(metric_spec["author"], str) or not metric_spec["author"].strip() or
            not isinstance(metric_spec["metrics"], dict) or not metric_spec["metrics"]):
        raise ValueError("pre-run metric declaration schema/identity invalid")
    if not isinstance(metric_spec["issued_at_utc"], str):
        raise ValueError("metric declaration timestamp is missing")
    issued = datetime.fromisoformat(metric_spec["issued_at_utc"].replace("Z", "+00:00"))
    if issued.tzinfo is None or issued > datetime.now(timezone.utc):
        raise ValueError("metric declaration timestamp must be timezone-aware and authored before invocation")
    if not isinstance(metric_spec["protocol_id"], str):
        raise ValueError("metric declaration protocol_id must be a string")
    expected_labels=({"Final estimate: PPL"} if a.mode in {"ppl","ppl-anchor"} else
        {"Mean PPL(Q)","Mean PPL(base)","Mean PPL(Q)/PPL(base)","Mean PPL(Q)-PPL(base)","Mean ln(PPL(Q)/PPL(base))","Mean KLD",*(f"{x} KLD" for x in KLD_LABELS)})
    if set(metric_spec["metrics"])!=expected_labels:
        raise ValueError("pre-run metric declaration labels differ from exact native mode output contract")
    for native_label,declaration in metric_spec["metrics"].items():
        if (not isinstance(declaration,dict) or set(declaration)!={"unit","metric_direction","category","metric"} or
            not isinstance(declaration["unit"],str) or not declaration["unit"].strip() or
            declaration["metric_direction"] not in {"higher_better","lower_better"} or
            declaration["category"] not in {"OPTIMUM","BASELINE","CANDIDATE"} or
            not isinstance(declaration["metric"],str) or not declaration["metric"].strip()):
            raise ValueError(f"incomplete source-authored declaration for {native_label}")
    n_ctx_pre=int(context_arg);chunks_pre=int(chunks_arg)
    if n_ctx_pre<=0 or chunks_pre<=0 or a.ny!=n_ctx_pre//2:
        raise ValueError("pre-run Ny/context/chunk controls are invalid or inconsistent")
    binary = binary.resolve(strict=True)
    argv[0] = str(binary)
    binary_before = file_identity(binary)
    model_identity = file_identity(a.model)
    corpus_identity = file_identity(a.corpus)
    ref_identity = file_identity(a.reference_logits) if a.reference_logits else None
    ref_model_identity = file_identity(a.reference_model) if a.reference_model else None
    anchor_receipt_before = file_identity(a.anchor_receipt) if a.anchor_receipt else None
    started = utc_now()
    start_ns = time.time_ns()
    seen_so: dict[tuple, dict[str, Any]] = {}
    stop = threading.Event()
    with open_native_log(log_path) as log:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log,
                                stderr=subprocess.STDOUT, env=env, shell=False)
        monitor = threading.Thread(target=monitor_maps, args=(proc, seen_so, stop), daemon=True)
        monitor.start()
        exit_code = proc.wait()
        end_ns = time.time_ns()
        ended = datetime.fromtimestamp(end_ns / 1e9, timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")
        stop.set()
        monitor.join()
        log.flush()
        os.fsync(log.fileno())
    binary_after = file_identity(binary)
    model_after = file_identity(a.model)
    corpus_after = file_identity(a.corpus)
    ref_after = file_identity(a.reference_logits) if a.reference_logits else None
    ref_model_after = file_identity(a.reference_model) if a.reference_model else None
    anchor_receipt_after = file_identity(a.anchor_receipt) if a.anchor_receipt else None
    log_sha = sha256_file(log_path)
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    output_logits_identity = None
    if a.output_logits is not None:
        try:
            output_logits_identity = file_identity(a.output_logits)
        except (FileNotFoundError, OSError, ValueError) as exc:
            refusal_message = f"declared output logits were not durably written: {exc}"
        else:
            refusal_message = ""
    else:
        refusal_message = ""
    loaded: list[dict[str, Any]] = []
    for map_key, observed in sorted(seen_so.items(), key=lambda x: repr(x[0])):
        raw_path, dev_major, dev_minor, map_inode, deleted = map_key
        row = {
            "path": raw_path,
            "identity_state": "unknown",
            "mapping_observation": {
                "first": observed["mapping_first"], "latest": observed["mapping_latest"],
                "sample_count": observed["mapping_sample_count"],
                "sample_basis": "distinct maps snapshots containing this path/device/inode/deleted identity",
                "deleted_mapping_observed": observed["deleted_mapping_observed"],
            },
            "live_identity_observation": {
                "first": observed["live_first"], "latest": observed["live_latest"],
                "sample_count": observed["live_hash_sample_count"],
                "sample_basis": "successful stable same-inode content hash observations while child was live",
                "identity_change_observation_count": observed["identity_change_observation_count"],
                "first_changed_identity": observed["first_changed_identity"],
                "error_observed": observed["live_identity_error"] is not None,
            },
            "compiled_knob_evidence": {"state": "unknown"},
        }
        if observed.get("live_identity_error"):
            row["identity_error"] = observed["live_identity_error"]
        live_first = observed["live_first"]
        live_latest = observed["live_latest"]
        if deleted or observed["deleted_mapping_observed"] or raw_path.endswith(" (deleted)"):
            row["identity_error"] = "mapped object is deleted; replacement path is not evidence"
        elif observed["live_identity_error"]:
            pass
        elif not live_latest:
            row["identity_error"] = "no same-inode content hash was captured while child was live"
        elif observed["identity_change_observation_count"]:
            row["identity_error"] = "loaded object content identity changed during measured process"
        else:
            so = Path(raw_path)
            try:
                ident, evidence = compiled_knob_evidence(so)
                if live_first["identity"] != live_latest["identity"] or ident != live_latest["identity"]:
                    raise ValueError("loaded object changed between live samples and sealed read")
                if (ident["inode"] != map_inode or os.major(ident["device"]) != dev_major or
                        os.minor(ident["device"]) != dev_minor):
                    raise ValueError("sealed library path does not name mapped device/inode")
                row["after"] = ident
                row["identity_state"] = "matched"
                row["compiled_knob_evidence"] = {
                    **evidence, "state": "present" if evidence["found_exact"] else "absent"}
            except (OSError, ValueError) as exc:
                row["identity_error"] = str(exc)
        loaded.append(row)
    spec_after = file_identity(a.metric_spec)
    metrics: list[dict[str, Any]] = []
    native_window: dict[str, Any] = {}
    refusal: list[str] = []
    if spec_before != spec_after:
        refusal.append("pre-run metric declaration changed during measured process")
    if model_identity != model_after or corpus_identity != corpus_after or ref_identity != ref_after or ref_model_identity != ref_model_after or anchor_receipt_before != anchor_receipt_after:
        refusal.append("model, corpus, anchor receipt, or KLD reference input identity changed during measured process")
    if refusal_message:
        refusal.append(refusal_message)
    try:
        metrics = parse_native_metrics(log_text, a.mode)
        native_window = parse_native_window(log_text, a.mode)
        for item in metrics:
            declaration = metric_spec["metrics"].get(item["native_label"])
            if not isinstance(declaration, dict) or set(declaration) != {"unit", "metric_direction", "category", "metric"}:
                raise ValueError(f"no exact pre-run metric declaration for {item['native_label']}")
            if (not isinstance(declaration["unit"], str) or not declaration["unit"].strip() or
                    declaration["metric_direction"] not in {"higher_better", "lower_better"} or
                    declaration["category"] not in {"OPTIMUM", "BASELINE", "CANDIDATE"} or
                    not isinstance(declaration["metric"], str) or not declaration["metric"].strip()):
                raise ValueError(f"incomplete pre-run metric declaration for {item['native_label']}")
            item["unit"] = declaration["unit"]
            item["metric_direction"] = declaration["metric_direction"]
            item["category"] = declaration["category"]
            item["metric"] = declaration["metric"]
        if set(metric_spec["metrics"]) != {row["native_label"] for row in metrics}:
            raise ValueError("pre-run metric declaration has missing or extra native labels")
    except (ValueError, OverflowError) as exc:
        refusal.append(str(exc))
    if exit_code != 0:
        refusal.append(f"producer_exit_code={exit_code}")
    if binary_before != binary_after:
        refusal.append("producer binary changed during measured process")
    if not loaded:
        refusal.append("no loaded shared-object mappings observed during process")
    if any(row.get("identity_state") != "matched" for row in loaded):
        refusal.append("loaded shared-object identity was unknown or did not match maps inode/device")
    if not any(row["compiled_knob_evidence"].get("state") == "present" and
               row["compiled_knob_evidence"].get("found_exact") is True for row in loaded):
        refusal.append("GGML_IQK compiled-string evidence was not found in a loaded shared object")
    iqk_raw = env.get("GGML_IQK", "unknown")
    iqk_state = {"0": "disabled", "1": "enabled"}.get(iqk_raw, "unknown")
    if iqk_state == "unknown":
        refusal.append("effective GGML_IQK state is absent or unrecognized")
    if a.ny < 32:
        refusal.append("PPL/KLD Ny below 32 is outside the SC54 quality-evaluation regime")
    argv_text = shlex.join(argv)
    n_ctx: int | None = None
    for i, arg in enumerate(argv[:-1]):
        if arg in ("-c", "--ctx-size"):
            try:
                n_ctx = int(argv[i + 1])
            except ValueError:
                pass
    if n_ctx is not None and a.ny != n_ctx // 2:
        refusal.append("producer-authored Ny conflicts with llama-perplexity all-logits n_ctx/2 source semantics")
    if native_window and a.ny != native_window["ny_derived_from_native_n_ctx"]:
        refusal.append("supplied Ny conflicts with native scoring-window context")
    if native_window and chunks_arg != str(native_window["native_chunks_requested_and_reported"]):
        refusal.append("--chunks argument conflicts with native scoring-window count")
    if native_window and context_arg != str(native_window["n_ctx"]):
        refusal.append("-c/--ctx-size argument conflicts with native scoring-window context")
    record: dict[str, Any] = {
        "schema": SCHEMA, "schema_version": 1, "run_id": a.run_id,
        "pair_id": a.pair_id, "arm_id": a.arm_id,
        "instrument": "llama-perplexity", "mode": a.mode, "instrument_class": "quality_eval",
        "producer_source_revision": a.source_revision,
        "protocol_id": metric_spec["protocol_id"],
        "metric_declaration": {"before": spec_before, "after": spec_after, "author": metric_spec["author"], "issued_at_utc": metric_spec["issued_at_utc"], "metrics": metric_spec["metrics"]},
        "started_at_utc": started, "ended_at_utc": ended,
        "measurement_window_ns": {"start": start_ns, "end": end_ns},
        "argv": argv, "argv_display": argv_text,
        "effective_environment": {k: v for k, v in sorted(env.items())
                                  if k.startswith(ENV_PREFIXES) or k == "LD_LIBRARY_PATH"},
        "producer_binary": {"before": binary_before, "after": binary_after,
                            "stable_during_capture": binary_before == binary_after,
                            "reported_version": "unknown (not emitted by captured invocation)"},
        "loaded_shared_objects": loaded,
        "runtime_knobs": {"GGML_IQK": {"value": iqk_state, "raw_value": iqk_raw,
                                         "capture_source": "effective child-process environment"}},
        "model": {**model_identity, "model_name": a.model_name, "quant": a.quant},
        "model_after": model_after, "corpus": corpus_identity, "corpus_after": corpus_after,
        "reference_model": ref_model_identity, "reference_model_after": ref_model_after,
        "reference_logits": ref_identity, "reference_logits_after": ref_after,
        "anchor_receipt": {"before":anchor_receipt_before,"after":anchor_receipt_after} if anchor_receipt_before else None,
        "output_logits": output_logits_identity,
        "ny": a.ny, "n_ctx": n_ctx, "native_scoring_window": native_window,
        "scored_token_count": "unknown (native log does not emit an aggregate token count)",
        "prompt": "not applicable (corpus perplexity/KLD instrument)",
        "chunks_arg": chunks_arg,
        "native_log": {"path": str(log_path), "sha256": log_sha},
        "exit_code": exit_code, "metrics": metrics,
        "scope": {"ppl_is_not_serving_warrant": "perplexity Ny>=32 does not warrant serving Ny=1",
                  "corpus_spread": "± values are corpus sampling uncertainty, not run-to-run noise",
                  "iqk_comparison": "keep runtime IQK states separate; any observed offset is specific to its captured binary, corpus, arguments and window",
                  "direction": "native log does not emit direction; direction comes from the pre-run source-authored metric declaration"},
        "capture_status": "captured" if not refusal else "refused",
        "refusal_reasons": refusal,
    }
    atomic_json(receipt_path, record)
    print(receipt_path)
    return 0 if not refusal else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"SC54 capture refused: {exc}", file=sys.stderr)
        raise SystemExit(3)
