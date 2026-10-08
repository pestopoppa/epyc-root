"""Strict SC54 reader for prospectively captured qwen4exp PPL/KLD quality receipts.

Receipt parsing is delegated to one review-pinned strict reader. Rows project into the shared
measurement ClaimTuple class; this adapter registers no ladder and never backfills historical data.
"""
from __future__ import annotations

import hashlib
import os
import stat
import sys
from pathlib import Path
from types import FunctionType, ModuleType
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.qwen4exp_quality/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "epyc.vidya.qwen4exp_quality_measurement.v1"
READER_PATH = Path(__file__).with_name("qwen4exp_quality_reader.py")
READER_SHA256 = "172e046bc596f2d1afa12ac0617ea6b2737f0536fd7c443508c5a1c231ba3532"


def _read_pinned_source() -> tuple[bytes, dict[str, int | str]]:
    """Read and hash one no-follow FD; return those exact bytes for compilation."""
    parent = os.open(READER_PATH.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                     getattr(os, "O_NOFOLLOW", 0))
    try:
        name = READER_PATH.name
        named_before = os.stat(name, dir_fd=parent, follow_symlinks=False)
        fd = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) |
                     getattr(os, "O_NONBLOCK", 0), dir_fd=parent)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise ProjectionError("SC54 strict reader must be a regular single-link file")
            if before.st_size > (1 << 20):
                raise ProjectionError("SC54 strict reader source exceeds the pinned-source size bound")
            digest = hashlib.sha256()
            chunks = []
            size = 0
            while True:
                block = os.read(fd, 1 << 20)
                if not block:
                    break
                chunks.append(block)
                digest.update(block)
                size += len(block)
            after = os.fstat(fd)
            named_after = os.stat(name, dir_fd=parent, follow_symlinks=False)
            fields = lambda x: (x.st_dev, x.st_ino, x.st_mode, x.st_nlink, x.st_size,
                                x.st_mtime_ns, x.st_ctime_ns)
            if (fields(before) != fields(after) or fields(named_before) != fields(named_after) or
                    fields(before) != fields(named_before) or size != before.st_size):
                raise ProjectionError("SC54 strict reader changed during pinned FD read")
            source = b"".join(chunks)
            if digest.hexdigest() != READER_SHA256:
                raise ProjectionError("SC54 strict reader bytes differ from reviewed sha256")
            identity = {"path": str(READER_PATH.absolute()), "sha256": digest.hexdigest(),
                        "device": before.st_dev, "inode": before.st_ino, "size_bytes": size,
                        "mtime_ns": before.st_mtime_ns, "ctime_ns": before.st_ctime_ns}
            return source, identity
        finally:
            os.close(fd)
    finally:
        os.close(parent)


def _reader() -> ModuleType:
    try:
        source, identity = _read_pinned_source()
    except ProjectionError:
        raise
    except OSError as exc:
        raise ProjectionError(f"SC54 strict reader unavailable: {type(exc).__name__}") from exc
    name = "_epyc_qwen4exp_quality_reader_v1"
    cached = sys.modules.get(name)
    if cached is not None:
        loaded_source = getattr(cached, "__sc54_source_bytes__", None)
        loaded_identity = getattr(cached, "__sc54_file_identity__", None)
        functions = getattr(cached, "__sc54_function_objects__", None)
        namespace = getattr(cached, "__sc54_namespace_objects__", None)
        current_namespace = {key: value for key, value in vars(cached).items()
                             if not key.startswith("__sc54_")}
        current_functions = {key: value for key, value in current_namespace.items()
                             if isinstance(value, FunctionType) and value.__module__ == name}
        if (loaded_source != source or hashlib.sha256(loaded_source or b"").hexdigest() != READER_SHA256 or
                loaded_identity != identity or getattr(cached, "__file__", None) != identity["path"] or
                getattr(cached, "__sc54_source_sha256__", None) != READER_SHA256 or
                not isinstance(namespace, dict) or namespace.keys() != current_namespace.keys() or
                any(namespace[key] is not current_namespace[key] for key in namespace) or
                not isinstance(functions, dict) or functions.keys() != current_functions.keys() or
                any(functions[key] is not current_functions[key] for key in functions)):
            raise ProjectionError("cached SC54 reader module does not match pinned source identity")
        return cached
    module = ModuleType(name)
    module.__file__ = identity["path"]
    module.__package__ = ""
    try:
        code = compile(source, identity["path"], "exec", dont_inherit=True)
        exec(code, module.__dict__)
    except Exception as exc:
        raise ProjectionError(f"SC54 strict reader cannot be loaded: {type(exc).__name__}") from exc
    functions = {key: value for key, value in vars(module).items()
                 if isinstance(value, FunctionType) and value.__module__ == name}
    module.__sc54_namespace_objects__ = dict(vars(module))
    module.__sc54_source_bytes__ = source
    module.__sc54_source_sha256__ = READER_SHA256
    module.__sc54_file_identity__ = identity
    module.__sc54_function_objects__ = functions
    sys.modules[name] = module
    return module


def native_rows(receipt_path: str | Path) -> tuple[ClaimTuple, ...]:
    """Verify the sealed receipt and return only fully re-derived native metric tuples."""
    try:
        return tuple(_reader().read_project(Path(receipt_path), ClaimTuple))
    except ProjectionError:
        raise
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        raise ProjectionError(f"SC54 receipt refused: {exc}") from exc


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, ClaimTuple) or native.source_kind != "measurement":
        raise ProjectionError("SC54 reader did not return a shared measurement ClaimTuple")
    return native


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "native_rows", "project"]
