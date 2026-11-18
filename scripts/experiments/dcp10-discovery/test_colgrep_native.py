import fcntl
import json
import os
import signal
import sqlite3
import subprocess
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import colgrep_native as native


class NativeLaunchTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.assets = Path(temp.name) / "assets"
        self.assets.mkdir(mode=0o700)
        self.root = Path(temp.name) / "base"
        self.root.mkdir()
        self.data = self.assets / "bases" / self.root.name
        self.data.mkdir(parents=True)
        self.binary = self.assets / "bin/colgrep"
        self.binary.parent.mkdir()
        self.binary.touch(mode=0o700)
        self.model = self.assets / "model"
        self.model.mkdir()
        self.runtime = self.assets / "runtime" / native.RUNTIME_NAME
        self.runtime.parent.mkdir()
        self.runtime.touch()
        self.project = self.data / "colgrep/indices/base-12345678"
        self.argv = [str(self.binary), "search", "-k", "20", "--alpha", "0.95", "--model",
                     str(self.model), "--force-cpu", "--json", "--", "--looks-like-a-flag",
                     str(self.root)]

    def lay_index(self):
        vector = self.project / "index"
        vector.mkdir(parents=True)
        (self.project / ".lock").write_bytes(b"original")
        (self.project / "project.json").write_text(json.dumps({"project_path": str(self.root)}))
        (self.project / "state.json").write_text(json.dumps({
            "cli_version": "1.2.0", "dirty": False, "files": {"source.py": {}},
        }))
        (vector / "metadata.json").write_text(json.dumps({
            "num_chunks": 2, "num_documents": 2, "next_plaid_compatible": True,
        }))
        for chunk, rows in enumerate((3, 1)):
            (vector / f"doclens.{chunk}.json").write_text(json.dumps([rows]))
            (vector / f"{chunk}.codes.npy").write_bytes(
                native._merged_header("<i8", (rows,)) + bytes([chunk + 1]) * rows * 8)
            (vector / f"{chunk}.residuals.npy").write_bytes(
                native._merged_header("|u1", (rows, 2)) + bytes([chunk + 3]) * rows * 2)
        with sqlite3.connect(vector / "metadata.db") as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE VIRTUAL TABLE metadata_fts USING fts5(text)")
            db.execute("INSERT INTO metadata_fts VALUES ('immutable search')")
        db.close()

    def seal_index(self):
        (self.data / native.CONFIG_PATH).write_bytes(native.CONFIG_BYTES)
        native._materialize_merged_arrays(self.project / "index", time.monotonic() + 10)
        native._seal_sqlite(self.project / "index/metadata.db")

    def call_search(self):
        return native.search(self.argv, self.root, self.data, 10)

    def test_search_mounts_presealed_inputs_and_keeps_only_disposable_lock_writable(self):
        self.lay_index()
        self.seal_index()
        sealed_lock = self.project / ".lock"
        captured = {}

        def run(command, **kwargs):
            mounts = [command[i + 1] for i, option in enumerate(command) if option == "--mount"]
            self.assertEqual(len(mounts), 6)
            self.assertTrue(all("readonly,bind-recursive=readonly" in item for item in mounts[:5]))
            self.assertIn(f"src={self.data},dst={native.DATA_IN},", mounts[4])
            self.assertIn("dst=/dcp10/data/colgrep/indices/base-12345678/.lock", mounts[5])
            lock = Path(mounts[5].split("src=")[1].split(",")[0])
            captured["lock"] = lock
            with lock.open("rb") as separately_opened, self.assertRaises(BlockingIOError):
                fcntl.flock(separately_opened, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertIn("--network=none", command)
            self.assertIn("--read-only", command)
            self.assertIn("--pull=never", command)
            self.assertIn("--cap-drop=ALL", command)
            self.assertIn("COLGREP_FORCE_CPU=1", command)
            self.assertIn(f"ORT_DYLIB_PATH={native.RUNTIME_IN}", command)
            self.assertEqual(command[command.index("--cpuset-cpus") + 1], "2,3,4,5")
            self.assertEqual(command[command.index("--memory") + 1], "1048576")
            for key, value in native.THREAD_ENV.items():
                self.assertIn(f"{key}={value}", command)
                self.assertNotIn(key, kwargs["env"])
            self.assertIn("--pids-limit=256", command)
            self.assertEqual(command[-3:], ["--", self.argv[-2], str(self.root)])
            self.assertEqual(kwargs["timeout"], 10)
            self.assertNotIn("HF_TOKEN", kwargs["env"])
            self.assertEqual(kwargs["env"]["DOCKER_HOST"], "unix:///var/run/docker.sock")
            return subprocess.CompletedProcess(command, 0, "[]\n", "")

        with (patch.object(native.shutil, "which", return_value="/usr/bin/docker"),
              patch.object(native.os, "sched_getaffinity", return_value={5, 2, 4, 3, 100, 101, 102, 103}),
              patch.object(native, "_memory_limit", return_value=1048576),
              patch.dict(native.os.environ, {"HF_TOKEN": "token", "DOCKER_HOST": "tcp://example",
                                             "RAYON_NUM_THREADS": "256"}),
              patch.object(native.subprocess, "run", side_effect=run) as invoke):
            self.assertEqual(self.call_search(), "[]\n")
        self.assertEqual(invoke.call_count, 1)
        self.assertFalse(captured["lock"].exists())
        self.assertEqual(sealed_lock.read_bytes(), b"original")

    def test_absent_index_sidecars_or_ambiguous_project_refuse_without_launch(self):
        with patch.object(native.subprocess, "run") as invoke:
            with self.assertRaises(FileNotFoundError):
                self.call_search()
            self.lay_index()
            with self.assertRaises(FileNotFoundError):
                self.call_search()
            (self.project.parent / "parent-project-index").mkdir()
            with self.assertRaisesRegex(ValueError, "exactly one private"):
                self.call_search()
        invoke.assert_not_called()

    def test_missing_or_changed_session_config_refuses_native_search(self):
        self.lay_index()
        self.seal_index()
        config = self.data / native.CONFIG_PATH
        with (patch.object(native.shutil, "which", return_value="/usr/bin/docker"),
              patch.object(native.subprocess, "run") as invoke):
            config.unlink()
            with self.assertRaises(FileNotFoundError):
                self.call_search()
            config.write_bytes(b'{"parallel_sessions":4}\n')
            with self.assertRaisesRegex(native.IsolationError, "thread configuration changed"):
                self.call_search()
        invoke.assert_not_called()

    def test_invalid_arguments_and_unavailable_isolation_never_use_host_binary(self):
        self.lay_index()
        self.seal_index()
        with patch.object(native.subprocess, "run") as invoke:
            original = self.argv[8]
            self.argv[8] = "--force-gpu"
            with self.assertRaises(ValueError):
                self.call_search()
            self.argv[8] = original
            with (patch.object(native.shutil, "which", return_value=None),
                  self.assertRaisesRegex(RuntimeError, "requires the local Docker")):
                self.call_search()
        invoke.assert_not_called()

    def test_timeout_removes_only_the_named_container(self):
        self.lay_index()
        self.seal_index()
        expired = subprocess.TimeoutExpired(["docker", "run"], 10)
        removed = subprocess.CompletedProcess(["docker", "rm"], 0, "", "")
        with (patch.object(native.shutil, "which", return_value="/usr/bin/docker"),
              patch.object(native.subprocess, "run", side_effect=[expired, removed]) as invoke,
              self.assertRaisesRegex(RuntimeError, "exceeded its launch timeout")):
            self.call_search()
        run, cleanup = [call.args[0] for call in invoke.call_args_list]
        self.assertEqual(cleanup, ["/usr/bin/docker", "rm", "-f", run[run.index("--name") + 1]])

    def test_sigterm_removes_container_and_restores_previous_handler(self):
        self.lay_index()
        self.seal_index()
        previous = signal.getsignal(signal.SIGTERM)

        def run(command, **kwargs):
            if command[1] == "run":
                os.kill(os.getpid(), signal.SIGTERM)
            return subprocess.CompletedProcess(command, 0, "", "")

        with (patch.object(native.shutil, "which", return_value="/usr/bin/docker"),
              patch.object(native.subprocess, "run", side_effect=run) as invoke,
              self.assertRaises(SystemExit) as interrupted):
            self.call_search()
        self.assertEqual(interrupted.exception.code, 143)
        self.assertEqual(signal.getsignal(signal.SIGTERM), previous)
        self.assertEqual(invoke.call_args.args[0][1:3], ["rm", "-f"])

    def test_docker_launch_failure_and_native_error_are_distinct(self):
        self.lay_index()
        self.seal_index()
        with patch.object(native.shutil, "which", return_value="/usr/bin/docker"):
            for status, error in ((125, native.IsolationError), (1, native.NativeError)):
                with (patch.object(native.subprocess, "run", return_value=
                                   subprocess.CompletedProcess([], status, "", "stderr")),
                      self.assertRaisesRegex(error, "stderr")):
                    self.call_search()

    def test_build_uses_only_fresh_private_data_and_seals_checkpointed_metadata(self):
        def run(command, **kwargs):
            writable = [item for item in command if "bind-recursive=disabled" in item]
            self.assertEqual(writable, [
                (f"type=bind,src={self.data},dst={native.DATA_IN},"
                 "bind-propagation=rprivate,bind-recursive=disabled"),
            ])
            self.assertEqual(command[-7:], ["init", "--model", native.MODEL_IN, "--force-cpu",
                                            "-y", "--", str(self.root)])
            config = self.data / native.CONFIG_PATH
            self.assertIn(native._mount(config, Path(native.DATA_IN) / native.CONFIG_PATH), command)
            self.assertEqual(json.loads(config.read_bytes()), {"parallel_sessions": 1})
            self.assertEqual(config.stat().st_mode & 0o777, 0o400)
            self.lay_index()
            return subprocess.CompletedProcess(command, 0, "", "")

        with (patch.object(native.shutil, "which", return_value="/usr/bin/docker"),
              patch.object(native.subprocess, "run", side_effect=run) as invoke):
            native.build_index(self.assets, self.root, self.data, 90)
            with self.assertRaisesRegex(ValueError, "fresh, empty private"):
                native.build_index(self.assets, self.root, self.data, 90)
        invoke.assert_called_once()
        wal, shm = native._sidecars(self.project / "index/metadata.db")
        self.assertEqual(wal.stat().st_size, 0)
        self.assertEqual(shm.stat().st_size, 32768)
        with sqlite3.connect((self.project / "index/metadata.db").as_uri() + "?immutable=1",
                             uri=True) as db:
            self.assertEqual(db.execute("SELECT * FROM metadata_fts").fetchall(),
                             [("immutable search",)])
        db.close()
        receipt = json.loads((self.data / "materialization.json").read_text())
        self.assertIs(receipt["inference"], False)
        self.assertEqual(receipt["source_commit"], native.NEXT_PLAID_V1_2_0)
        self.assertEqual(receipt["arrays"]["codes"]["shape"], [6])
        self.assertEqual(receipt["arrays"]["residuals"]["shape"], [6, 2])
        vector = self.project / "index"
        self.assertEqual((vector / "merged_codes.npy").read_bytes(),
                         native._merged_header("<i8", (6,)) + b"\1" * 24 + b"\2" * 8 + bytes(16))
        self.assertEqual((vector / "merged_residuals.npy").read_bytes(),
                         native._merged_header("|u1", (6, 2)) + b"\3" * 6 + b"\4" * 2 + bytes(4))
        manifest = json.loads((vector / "merged_residuals.manifest.json").read_text())
        self.assertEqual((manifest["total_rows"], manifest["padding_rows"], manifest["ncols"],
                          manifest["num_chunks"]), (6, 2, 2, 2))
        self.assertEqual(manifest["metadata_mtime"], (vector / "metadata.json").stat().st_mtime)
        self.assertEqual({name: info["rows"] for name, info in manifest["chunks"].items()},
                         {"0.residuals.npy": 3, "1.residuals.npy": 1})

    def test_materialization_refuses_expired_or_incomplete_build(self):
        self.lay_index()
        index = self.project / "index"
        with self.assertRaisesRegex(native.NativeError, "index build timeout"):
            native._materialize_merged_arrays(index, time.monotonic() - 1)
        bad = index / "0.codes.npy"
        bad.write_bytes(bad.read_bytes()[:-1])
        with self.assertRaisesRegex(ValueError, "incomplete ColGREP NumPy chunk"):
            native._materialize_merged_arrays(index, time.monotonic() + 10)
        self.assertFalse((index / "merged_codes.npy").exists())


if __name__ == "__main__":
    unittest.main()
