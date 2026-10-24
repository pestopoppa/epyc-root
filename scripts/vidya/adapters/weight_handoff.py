"""Adapter for captured weight-handoff receipts (VB-NEW13-WIRE). PROJECTION ONLY; no ladder.

The strict reader lives in ``weight_handoff_reader.py`` and is PINNED exactly as the SC54 reader is
(``qwen4exp_quality.py``): one no-follow FD read of a regular single-link file, size-bounded, the
sha256 must equal ``READER_SHA256`` below, those exact bytes are compiled, and a cached module is
re-verified against the pinned source identity on every use. Editing the reader without re-pinning
here (after review) makes every projection refuse. ``claim_tuple.grade()`` decides every tuple.
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

ADAPTER_ID = "vidya.adapters.weight_handoff/v1"
AUTHORITY = "measurement"
SCHEMA = "epyc.vidya.weight_handoff_measurement.v1"
SOURCE_KIND = SCHEMA
READER_PATH = Path(__file__).with_name("weight_handoff_reader.py")
READER_SHA256 = "87c2f7b072451c710c6a970de646ee2e325d9e8559668b75b68dd1eb540e4f46"
_MODNAME = "_epyc_weight_handoff_reader_v1"
_EXPORTS = frozenset({"DECL_SCHEMA", "LABELS", "PARTIAL_STATUS", "derive_metrics", "load_kld_records",
                      "stat_matches"})


def _read_pinned_source() -> tuple[bytes, dict[str, int | str]]:
    parent = os.open(READER_PATH.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        name = READER_PATH.name
        named_before = os.stat(name, dir_fd=parent, follow_symlinks=False)
        fd = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0), dir_fd=parent)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise ProjectionError("weight-handoff strict reader must be a regular single-link file")
            if before.st_size > (1 << 20):
                raise ProjectionError("weight-handoff strict reader source exceeds the pinned-source size bound")
            digest, chunks, size = hashlib.sha256(), [], 0
            while True:
                block = os.read(fd, 1 << 20)
                if not block:
                    break
                chunks.append(block)
                digest.update(block)
                size += len(block)
            after = os.fstat(fd)
            named_after = os.stat(name, dir_fd=parent, follow_symlinks=False)
            fields = lambda x: (x.st_dev, x.st_ino, x.st_mode, x.st_nlink, x.st_size, x.st_mtime_ns, x.st_ctime_ns)  # noqa: E731
            if (fields(before) != fields(after) or fields(named_before) != fields(named_after)
                    or fields(before) != fields(named_before) or size != before.st_size):
                raise ProjectionError("weight-handoff strict reader changed during pinned FD read")
            if digest.hexdigest() != READER_SHA256:
                raise ProjectionError("weight-handoff strict reader bytes differ from reviewed sha256")
            return b"".join(chunks), {"path": str(READER_PATH.absolute()), "sha256": digest.hexdigest(),
                                      "device": before.st_dev, "inode": before.st_ino, "size_bytes": size,
                                      "mtime_ns": before.st_mtime_ns, "ctime_ns": before.st_ctime_ns}
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
        raise ProjectionError(f"weight-handoff strict reader unavailable: {type(exc).__name__}") from exc
    cached = sys.modules.get(_MODNAME)
    if cached is not None:
        namespace = getattr(cached, "__wh_namespace_objects__", None)
        functions = getattr(cached, "__wh_function_objects__", None)
        cur_ns = {k: v for k, v in vars(cached).items() if not k.startswith("__wh_")}
        cur_fn = {k: v for k, v in cur_ns.items() if isinstance(v, FunctionType) and v.__module__ == _MODNAME}
        loaded = getattr(cached, "__wh_source_bytes__", None)
        if (loaded != source or hashlib.sha256(loaded or b"").hexdigest() != READER_SHA256
                or getattr(cached, "__wh_file_identity__", None) != identity
                or getattr(cached, "__file__", None) != identity["path"]
                or not isinstance(namespace, dict) or namespace.keys() != cur_ns.keys()
                or any(namespace[k] is not cur_ns[k] for k in namespace)
                or not isinstance(functions, dict) or functions.keys() != cur_fn.keys()
                or any(functions[k] is not cur_fn[k] for k in functions)):
            raise ProjectionError("cached weight-handoff reader module does not match pinned source identity")
        return cached
    module = ModuleType(_MODNAME)
    module.__file__ = identity["path"]
    module.__package__ = ""
    try:
        exec(compile(source, identity["path"], "exec", dont_inherit=True), module.__dict__)
    except Exception as exc:
        raise ProjectionError(f"weight-handoff strict reader cannot be loaded: {type(exc).__name__}") from exc
    module.__wh_namespace_objects__ = dict(vars(module))
    module.__wh_function_objects__ = {k: v for k, v in vars(module).items()
                                      if isinstance(v, FunctionType) and v.__module__ == _MODNAME}
    module.__wh_source_bytes__ = source
    module.__wh_file_identity__ = identity
    sys.modules[_MODNAME] = module
    return module


def __getattr__(name: str) -> Any:
    """Helper names the capture and tests reuse; always served from the pinned reader."""
    if name in _EXPORTS:
        return getattr(_reader(), name)
    raise AttributeError(name)


def native_rows(receipt_path: str | Path) -> tuple[ClaimTuple, ...]:
    """Verify the sealed receipt (and its resume chain) and return fully re-derived tuples."""
    try:
        return tuple(_reader().read_project(Path(receipt_path)))
    except ProjectionError:
        raise
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        raise ProjectionError(f"weight-handoff receipt refused: {exc}") from exc


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, ClaimTuple) or native.source_kind != "measurement":
        raise ProjectionError("weight-handoff reader did not return a shared measurement ClaimTuple")
    return native


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "SCHEMA", "READER_PATH", "READER_SHA256", "native_rows", "project"]
