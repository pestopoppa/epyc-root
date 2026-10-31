"""Deny reads from the live AutoKernel producer tree in dashboard tests."""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from urllib.parse import unquote, urlsplit
from unittest import mock


LIVE_ROOT = Path("/mnt/raid0/llm/autokernel")


def _path_from_sqlite_database(database: object) -> str | None:
    try:
        value = os.fsdecode(os.fspath(database))
    except (TypeError, ValueError):
        return None
    if value.startswith("file:"):
        uri = urlsplit(value)
        if uri.scheme != "file":
            return None
        path = unquote(uri.path)
        if uri.netloc and uri.netloc != "localhost":
            path = f"//{uri.netloc}{path}"
        return path
    return value


def _is_live_path(value: object) -> bool:
    try:
        raw_path = _path_from_sqlite_database(value)
        if raw_path is None:
            return False
        path = os.path.abspath(raw_path)
        root = os.path.abspath(os.fspath(LIVE_ROOT))
        return os.path.commonpath((path, root)) == root
    except (TypeError, ValueError):
        return False


def _deny_live_path(value: object) -> None:
    if _is_live_path(value):
        raise AssertionError(f"test attempted to read live AutoKernel producer path: {value}")


class NoLiveAutokernelReads:
    """Mixin for tests whose evidence must come from repository fixtures."""

    def setUp(self) -> None:
        super().setUp()  # type: ignore[misc]
        original_open = Path.open
        original_is_file = Path.is_file
        original_is_dir = Path.is_dir
        original_glob = Path.glob
        original_rglob = Path.rglob
        original_sqlite_connect = sqlite3.connect

        def guarded_open(path: Path, *args: object, **kwargs: object):
            _deny_live_path(path)
            return original_open(path, *args, **kwargs)

        def guarded_is_file(path: Path) -> bool:
            _deny_live_path(path)
            return original_is_file(path)

        def guarded_is_dir(path: Path) -> bool:
            _deny_live_path(path)
            return original_is_dir(path)

        def guarded_glob(path: Path, *args: object, **kwargs: object):
            _deny_live_path(path)
            return original_glob(path, *args, **kwargs)

        def guarded_rglob(path: Path, *args: object, **kwargs: object):
            _deny_live_path(path)
            return original_rglob(path, *args, **kwargs)

        def guarded_sqlite_connect(database: object, *args: object, **kwargs: object):
            _deny_live_path(database)
            return original_sqlite_connect(database, *args, **kwargs)

        patchers = [
            mock.patch.object(Path, "open", guarded_open),
            mock.patch.object(Path, "is_file", guarded_is_file),
            mock.patch.object(Path, "is_dir", guarded_is_dir),
            mock.patch.object(Path, "glob", guarded_glob),
            mock.patch.object(Path, "rglob", guarded_rglob),
            mock.patch.object(sqlite3, "connect", guarded_sqlite_connect),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)  # type: ignore[attr-defined]

    def test_guard_blocks_path_and_sqlite_apis(self) -> None:
        live_file = LIVE_ROOT / "loop-memory/experiments.db"
        with self.subTest(api="Path.open"), self.assertRaisesRegex(
            AssertionError, "live AutoKernel producer path"
        ):
            live_file.open("rb")
        with self.subTest(api="Path.is_file"), self.assertRaisesRegex(
            AssertionError, "live AutoKernel producer path"
        ):
            live_file.is_file()
        for label, database, uri in (
            ("sqlite raw path", str(live_file), False),
            ("sqlite file URI", f"file:{live_file}?mode=ro", True),
        ):
            with self.subTest(api=label), self.assertRaisesRegex(
                AssertionError, "live AutoKernel producer path"
            ):
                sqlite3.connect(database, uri=uri)
