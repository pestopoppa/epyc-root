from __future__ import annotations

from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest import mock

from dashboard import server


class AutoKernelLiveDashboardTest(unittest.TestCase):
    def setUp(self) -> None:
        self._old_root = server.AUTOKERNEL_DEPLOYMENTS_ROOT
        self._old_supervisors_root = server.AUTOKERNEL_SUPERVISORS_ROOT
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name) / "deployments"
        supervisors = Path(self.temp.name) / "supervisors"
        supervisors.mkdir(mode=0o700)
        self.bundle = root / "campaign-a"
        self.state = self.bundle / "state"
        self.operations = self.bundle / "operations"
        (self.bundle / "config").mkdir(parents=True)
        self.state.mkdir()
        (self.operations / "live").mkdir(parents=True)
        config = {
            "config_sha256": "a" * 64,
            "controller": {"state_root": str(self.state),
                           "operations_root": str(self.operations)},
        }
        (self.bundle / "config/deployment.json").write_text(json.dumps(config))
        (self.state / "controller.run.lock").touch()
        server.AUTOKERNEL_DEPLOYMENTS_ROOT = root
        server.AUTOKERNEL_SUPERVISORS_ROOT = supervisors

    def tearDown(self) -> None:
        server.AUTOKERNEL_DEPLOYMENTS_ROOT = self._old_root
        server.AUTOKERNEL_SUPERVISORS_ROOT = self._old_supervisors_root
        self.temp.cleanup()

    def _write_supervisor_graph_mismatch(self, bundle: Path,
                                         config_path: Path) -> Path:
        runtime = server.AUTOKERNEL_SUPERVISORS_ROOT / bundle.name
        runtime.mkdir(mode=0o700)
        config = json.loads(config_path.read_text())
        canonical = server._canonical_json_bytes(config) + b"\n"
        copied = runtime / "deployment-config.json"
        copied.write_bytes(canonical)
        copied.chmod(0o600)
        source = config_path.stat()
        copy_info = copied.stat()
        runtime_info = runtime.stat()
        module_files = {
            "supervisor": "discovery_supervisor.py",
            "deployment_factory": "discovery_deployment_factory.py",
            "secure_runtime": "discovery_supervisor_secure.py"}
        manifest = {}
        module_hashes = {}
        for index, (module, filename) in enumerate(module_files.items(), 1):
            digest = hashlib.sha256(module.encode()).hexdigest()
            relative = f"scripts/kernel_rnd/autokernel/controller/{filename}"
            manifest[relative] = {
                "sha256": digest,
                "source": {"dev": 1, "ino": index, "mode": 0o644,
                           "nlink": 1, "size": index, "uid": os.geteuid()},
                "closure": {"dev": 2, "ino": index, "mode": 0o444,
                            "nlink": 1, "size": index, "uid": 0},
            }
            module_hashes[module] = digest
        content_manifest = {key: value["sha256"]
                            for key, value in manifest.items()}
        content_sha = hashlib.sha256(
            server._canonical_json_bytes(content_manifest)).hexdigest()
        closure = Path("/var/lib/epyc-autokernel/execution-closures") / content_sha
        launch_spec = {
            "schema": server._SUPERVISOR_SPEC_SCHEMA, "kind": "deployment",
            "runtime_root": str(runtime),
            "runtime_root_identity": {
                "dev": runtime_info.st_dev, "ino": runtime_info.st_ino,
                "mode": 0o700, "nlink": runtime_info.st_nlink,
                "uid": runtime_info.st_uid},
            "restart_policy": {"delay_seconds": 2.0, "max_restarts": 0},
            "termination_policy": {"kill_grace_seconds": 5.0,
                                   "term_grace_seconds": 10.0},
            "validate_only": False, "canary": None,
            "python": "/usr/bin/python3",
            "deployment_config": {
                "runtime_leaf": "deployment-config.json",
                "source_path": str(config_path),
                "source_identity": {
                    "dev": source.st_dev, "ino": source.st_ino,
                    "mode": source.st_mode & 0o7777, "nlink": source.st_nlink,
                    "size": source.st_size, "uid": source.st_uid,
                },
                "canonical_size": len(canonical),
                "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
                "identity": {
                    "dev": copy_info.st_dev, "ino": copy_info.st_ino,
                    "mode": 0o600, "nlink": copy_info.st_nlink,
                    "size": copy_info.st_size, "uid": copy_info.st_uid},
            },
            "execution_closure": {
                "path": str(closure), "content_sha256": content_sha,
                "manifest": manifest,
                "manifest_sha256": hashlib.sha256(
                    server._canonical_json_bytes(manifest)).hexdigest(),
                "root_identity": {"dev": 2, "ino": 99, "mode": 0o555,
                                  "nlink": 3, "uid": 0},
            },
            "execution_modules": {
                module: {"path": str(
                    closure / "scripts/kernel_rnd/autokernel/controller" / filename),
                         "sha256": module_hashes[module]}
                for module, filename in module_files.items()
            },
            "cgroup": {"base": "/sys/fs/cgroup", "name": (
                "epyc-autokernel-" + hashlib.sha256(
                    str(runtime).encode()).hexdigest()[:24])},
        }
        spec_sha = hashlib.sha256(
            server._canonical_json_bytes(launch_spec)).hexdigest()
        session_name = "ak-" + spec_sha[:24]
        supervisor = {
            "pid": 1001, "start_ticks": 2002,
            "boot_id": "boot-fixture", "host": "fixture-host",
            "host_id_source": "kernel-hostname",
            "host_id_sha256": "a" * 64}
        tmux = {"session_id": "$0", "pane_id": "%0",
                "pane_pid": 1001, "pane_start_ticks": 2002}
        child = {**supervisor, "pid": 1002, "start_ticks": 2003,
                 "pgid": 1002, "argv_sha256": "b" * 64}
        final_at = "2026-08-21T00:35:10.587741Z"
        updated_at = "2026-08-21T00:35:10.589385Z"
        identity = {
            "child": None, "exit_code": 1, "restart_count": 0,
            "schema": server._SUPERVISOR_IDENTITY_SCHEMA,
            "session_name": session_name,
            "spec_sha256": spec_sha, "state": "stopped",
            "supervisor": supervisor, "tmux": tmux,
            "tmux_socket_name": "epyc-autokernel-supervisors",
            "updated_at": updated_at,
        }
        events = [
            ("supervisor_started", {
                "spec_sha256": spec_sha, "session_name": session_name,
                "supervisor": supervisor, "tmux": tmux}),
            ("child_started", {
                "restart_count": 0, "child": child,
                "stdout": str(runtime / "controller.stdout.log"),
                "stderr": str(runtime / "controller.stderr.log"),
                "cgroup": {"dev": 31, "ino": 55, "mode": 0o700,
                           "nlink": 2, "path": (
                               "/sys/fs/cgroup/" + launch_spec["cgroup"]["name"] +
                               "-1001-0"), "uid": os.geteuid()}}),
            ("child_exited", {"restart_count": 0, "return_code": 1,
                              "cleanup_actions": ["cgroup.remove"],
                              "stop_signal": None}),
            ("restarts_exhausted", {"restart_count": 0,
                                    "last_return_code": 1,
                                    "max_restarts": 0}),
            ("supervisor_stopped", {"exit_code": 1, "restart_count": 0,
                                    "stop_signal": None,
                                    "supervisor": supervisor}),
        ]
        previous = None
        ledger = []
        for sequence, (event, payload) in enumerate(events, 1):
            row = {
                "event": event, "payload": payload,
                "previous_sha256": previous,
                "schema": server._SUPERVISOR_LEDGER_SCHEMA,
                "sequence": sequence, "written_at": final_at,
            }
            digest = hashlib.sha256(server._canonical_json_bytes(row)).hexdigest()
            row["record_sha256"] = digest
            ledger.append(server._canonical_json_bytes(row).decode("utf-8"))
            previous = digest
        files = {
            "identity.json": server._canonical_json_bytes(identity) + b"\n",
            "launch-spec.json": server._canonical_json_bytes(launch_spec) + b"\n",
            "death-ledger.jsonl": "\n".join(ledger) + "\n",
            "controller.stderr.log": (
                "unsafe actor output: SECRET PROMPT MUST NOT ESCAPE\n"
                "DeploymentFactoryError: durable deployment graph differs "
                "from current sealed graph\n"),
        }
        for name, body in files.items():
            path = runtime / name
            if isinstance(body, bytes):
                path.write_bytes(body)
            else:
                path.write_text(body)
            path.chmod(0o600)
        return runtime

    def _rewrite_supervisor_ledger(self, runtime: Path,
                                   rows: list[dict]) -> None:
        previous = None
        encoded = []
        for sequence, source in enumerate(rows, 1):
            row = dict(source)
            row["sequence"] = sequence
            row["previous_sha256"] = previous
            row.pop("record_sha256", None)
            digest = hashlib.sha256(
                server._canonical_json_bytes(row)).hexdigest()
            row["record_sha256"] = digest
            encoded.append(server._canonical_json_bytes(row))
            previous = digest
        (runtime / "death-ledger.jsonl").write_bytes(
            b"\n".join(encoded) + b"\n")

    def _rebind_supervisor_spec(self, runtime: Path, spec: dict) -> None:
        spec_sha = hashlib.sha256(
            server._canonical_json_bytes(spec)).hexdigest()
        session_name = "ak-" + spec_sha[:24]
        (runtime / "launch-spec.json").write_bytes(
            server._canonical_json_bytes(spec) + b"\n")
        identity_path = runtime / "identity.json"
        identity = json.loads(identity_path.read_text())
        identity["spec_sha256"] = spec_sha
        identity["session_name"] = session_name
        identity_path.write_bytes(server._canonical_json_bytes(identity) + b"\n")
        rows = [json.loads(line) for line in
                (runtime / "death-ledger.jsonl").read_text().splitlines()]
        rows[0]["payload"]["spec_sha256"] = spec_sha
        rows[0]["payload"]["session_name"] = session_name
        self._rewrite_supervisor_ledger(runtime, rows)

    def _set_supervisor_terminal_time(self, runtime: Path, *, ledger_at: str,
                                      identity_at: str) -> None:
        rows = [json.loads(line) for line in
                (runtime / "death-ledger.jsonl").read_text().splitlines()]
        for row in rows:
            row["written_at"] = ledger_at
        self._rewrite_supervisor_ledger(runtime, rows)
        identity_path = runtime / "identity.json"
        identity = json.loads(identity_path.read_text())
        identity["updated_at"] = identity_at
        identity_path.write_bytes(server._canonical_json_bytes(identity) + b"\n")

    def _v2_event(self, *, event: str = "planner_started",
                  result: dict | None = None) -> dict:
        row = {
            "schema": server.AUTOKERNEL_DISCOVERY_EVENT_SCHEMA_V2,
            "ts": "2026-08-19T05:00:00Z", "channel": "planner",
            "event": event,
            "campaign_id": "ak-discovery-" + "a" * 16,
            "hypothesis_id": "akh-v2-q5-type-specific-dequant",
            "provider": "codex", "model": "gpt-5.6-sol",
            "effort": "high", "operation_key": "b" * 64,
        }
        identity = {key: value for key, value in row.items()
                    if key not in {"ts", "channel"}}
        row["event_id"] = "ake-" + hashlib.sha256(json.dumps(
            identity, sort_keys=True, separators=(",", ":")
        ).encode("ascii")).hexdigest()
        if result is not None:
            row["result"] = result
        return row

    def test_active_precheckpoint_planner_is_visible(self) -> None:
        with (self.state / "controller.run.lock").open("r") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            payload = server.discovery_live_payload()
            self.assertTrue(payload["active"])
            self.assertIn("first durable checkpoint", payload["status_message"])
            self.assertEqual(payload["_freshness"]["reporting"], "observed")
            self.assertEqual(payload["_freshness"]["staleness_class"], "fresh")

    def test_active_planner_uses_its_stage_budget_in_health_envelope(self) -> None:
        """v14: a healthy bounded planner call is not silent at 329 seconds."""
        started_at = (datetime.now(timezone.utc) - timedelta(seconds=329))
        event = {
            "schema": server.AUTOKERNEL_DISCOVERY_EVENT_SCHEMA,
            "ts": started_at.isoformat().replace("+00:00", "Z"),
            "channel": "planner", "event": "planner_started",
            "campaign_id": "ak-discovery-" + "a" * 16,
            "hypothesis_id": "akh-v2-q5-type-specific-dequant",
            "provider": "codex", "model": "gpt-5.6-sol", "effort": "high",
        }
        (self.operations / "live/planner.jsonl").write_text(
            json.dumps(event) + "\n")

        with (self.state / "controller.run.lock").open("r") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            payload = server.discovery_live_payload()

        self.assertEqual(payload["activity"]["phase"]["id"], "planner")
        self.assertEqual(payload["activity"]["stall"]["state"], "healthy")
        self.assertEqual(payload["activity"]["stall"]["threshold_s"], 900.0)
        freshness = payload["_freshness"]
        self.assertEqual(freshness["reporting"], "observed")
        self.assertEqual(freshness["staleness_class"], "fresh")
        self.assertEqual(freshness["watchdog"]["state"], "ok")
        self.assertEqual(freshness["thresholds"], {
            "warn_s": 900.0, "stale_s": 900.0, "silent_after_s": 900.0})

    def test_only_allowlisted_producer_events_reach_log(self) -> None:
        valid = {
            "schema": server.AUTOKERNEL_DISCOVERY_EVENT_SCHEMA,
            "ts": "2026-08-14T16:00:00Z", "channel": "planner",
            "event": "planner_started", "campaign_id": "ak-discovery-x",
            "hypothesis_id": "akh-x", "provider": "codex",
            "model": "gpt-5.6-sol", "effort": "high",
        }
        rogue = {**valid, "prompt": "secret text"}
        path = self.operations / "live/planner.jsonl"
        path.write_text(json.dumps(valid) + "\n" + json.dumps(rogue) + "\n")
        payload = server.discovery_live_payload()
        self.assertEqual(len(payload["planner_log"]), 1)
        self.assertNotIn("secret text", json.dumps(payload))
        self.assertNotIn("prompt", payload["planner_log"][0])

    def test_v2_dual_stream_identity_is_verified_and_deduplicated(self) -> None:
        event = self._v2_event()
        encoded = json.dumps(event, sort_keys=True) + "\n"
        (self.operations / "live/autokernel.jsonl").write_text(encoded)
        (self.operations / "live/planner.jsonl").write_text(encoded)

        payload = server.discovery_live_payload()

        self.assertEqual(payload["telemetry_integrity"]["state"], "verified")
        self.assertTrue(payload["telemetry_integrity"]["verified"])
        self.assertEqual(payload["telemetry_producer_commit"],
                         "76301d6647586a25f2d56de1b93f1da9ac11a3fa")
        self.assertEqual(len(payload["autokernel_log"]), 1)
        self.assertEqual(len(payload["planner_log"]), 1)
        self.assertEqual(payload["autokernel_log"][0]["event_id"],
                         event["event_id"])
        transitions = [row for row in payload["activity"]["transitions"]
                       if row.get("event") == "planner_started"]
        self.assertEqual(len(transitions), 1)
        self.assertEqual(payload["_freshness"]["unreported"], [])

    def test_dual_stream_snapshot_waits_for_producer_transaction(self) -> None:
        """A global-first partial write must never become a degraded API read."""
        event = self._v2_event()
        encoded = (json.dumps(event, sort_keys=True, separators=(",", ":"))
                   + "\n").encode("ascii")
        global_path = self.operations / "live/autokernel.jsonl"
        planner_path = self.operations / "live/planner.jsonl"
        global_path.touch()
        planner_path.touch()
        partial_written = threading.Event()
        allow_second_write = threading.Event()
        reader_started = threading.Event()
        reader_done = threading.Event()
        result: list[dict] = []
        failures: list[BaseException] = []

        def writer() -> None:
            fds: list[int] = []
            try:
                for path in (global_path, planner_path):
                    fds.append(os.open(path, os.O_RDWR | os.O_APPEND))
                for fd in fds:
                    fcntl.flock(fd, fcntl.LOCK_EX)
                os.write(fds[0], encoded)
                os.fsync(fds[0])
                partial_written.set()
                if not allow_second_write.wait(5):
                    raise TimeoutError("test did not release producer transaction")
                os.write(fds[1], encoded)
                os.fsync(fds[1])
            except BaseException as exc:  # surfaced in the owning test thread
                failures.append(exc)
            finally:
                for fd in reversed(fds):
                    try:
                        fcntl.flock(fd, fcntl.LOCK_UN)
                    finally:
                        os.close(fd)

        def reader() -> None:
            try:
                reader_started.set()
                result.append(server.discovery_live_payload())
            except BaseException as exc:  # surfaced in the owning test thread
                failures.append(exc)
            finally:
                reader_done.set()

        writer_thread = threading.Thread(target=writer)
        reader_thread = threading.Thread(target=reader)
        writer_thread.start()
        self.assertTrue(partial_written.wait(5))
        reader_thread.start()
        self.assertTrue(reader_started.wait(5))
        try:
            self.assertFalse(
                reader_done.wait(0.1),
                "consumer observed the producer's one-stream transaction midpoint")
        finally:
            allow_second_write.set()
        writer_thread.join(5)
        reader_thread.join(5)

        self.assertFalse(failures)
        self.assertFalse(writer_thread.is_alive())
        self.assertFalse(reader_thread.is_alive())
        self.assertEqual(result[0]["telemetry_integrity"]["state"], "verified")
        self.assertEqual(len(result[0]["autokernel_log"]), 1)
        self.assertEqual(len(result[0]["planner_log"]), 1)

    def test_v2_missing_planner_copy_degrades_but_keeps_pulse_visible(self) -> None:
        event = self._v2_event()
        (self.operations / "live/autokernel.jsonl").write_text(
            json.dumps(event) + "\n")

        payload = server.discovery_live_payload()

        integrity = payload["telemetry_integrity"]
        self.assertEqual(integrity["state"], "degraded")
        self.assertEqual(integrity["missing_planner_count"], 1)
        self.assertEqual(len(payload["autokernel_log"]), 1)
        self.assertEqual(payload["planner_log"], [])
        self.assertEqual(payload["activity"]["transitions"][0]["event"],
                         "planner_started")
        self.assertEqual(payload["_freshness"]["unreported"],
                         ["telemetry_stream_integrity"])
        health = server.health_payload()
        self.assertEqual(health["panels"]["kernel_live"]["unreported"],
                         ["telemetry_stream_integrity"])
        self.assertNotEqual(health["status"], "ok")

    def test_busy_producer_transaction_is_bounded_and_not_health_gating(self) -> None:
        """A stuck writer gets a pulse response, not false mirror corruption."""
        event = self._v2_event()
        encoded = (json.dumps(event, sort_keys=True, separators=(",", ":"))
                   + "\n").encode("ascii")
        global_path = self.operations / "live/autokernel.jsonl"
        planner_path = self.operations / "live/planner.jsonl"
        global_path.touch()
        planner_path.touch()
        fds = [os.open(path, os.O_RDWR | os.O_APPEND)
               for path in (global_path, planner_path)]
        try:
            for fd in fds:
                fcntl.flock(fd, fcntl.LOCK_EX)
            os.write(fds[0], encoded)
            started = time.monotonic()
            payload = server.discovery_live_payload()
            elapsed = time.monotonic() - started
        finally:
            for fd in reversed(fds):
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)

        self.assertLess(elapsed, 1.0)
        self.assertEqual(payload["telemetry_snapshot_status"],
                         "producer_write_in_progress")
        self.assertEqual(payload["telemetry_integrity"]["state"],
                         "producer_write_in_progress")
        self.assertEqual(payload["telemetry_integrity"]["missing_planner_count"], 0)
        self.assertEqual(payload["_freshness"]["unreported"], [])

    def test_telemetry_symlink_is_refused(self) -> None:
        event = self._v2_event()
        encoded = json.dumps(event) + "\n"
        target = self.operations / "symlink-target.jsonl"
        target.write_text(encoded)
        (self.operations / "live/autokernel.jsonl").symlink_to(target)
        (self.operations / "live/planner.jsonl").write_text(encoded)

        payload = server.discovery_live_payload()

        self.assertEqual(payload["telemetry_integrity"]["state"], "degraded")
        self.assertFalse(payload["telemetry_integrity"]["verified"])
        self.assertEqual(payload["autokernel_log"], [])
        self.assertIn("unreadable", payload["log_error"])

    def test_telemetry_hardlink_is_refused(self) -> None:
        event = self._v2_event()
        encoded = json.dumps(event) + "\n"
        target = self.operations / "hardlink-target.jsonl"
        target.write_text(encoded)
        os.link(target, self.operations / "live/autokernel.jsonl")
        (self.operations / "live/planner.jsonl").write_text(encoded)

        payload = server.discovery_live_payload()

        self.assertEqual(payload["telemetry_integrity"]["state"], "degraded")
        self.assertFalse(payload["telemetry_integrity"]["verified"])
        self.assertEqual(payload["autokernel_log"], [])
        self.assertIn("single-link regular file", payload["log_error"])

    def test_pre_open_path_swap_cannot_export_replacement_bytes(self) -> None:
        event = self._v2_event()
        encoded = json.dumps(event) + "\n"
        global_path = self.operations / "live/autokernel.jsonl"
        planner_path = self.operations / "live/planner.jsonl"
        replacement = self.operations / "pre-open-replacement.jsonl"
        global_path.write_text(encoded)
        planner_path.write_text(encoded)
        replacement.write_text('{"prompt":"ATTACKER PRE OPEN"}\n')
        real_open = os.open
        swapped = False

        def swapping_open(path: object, flags: int, mode: int = 0o777,
                          *, dir_fd: int | None = None) -> int:
            nonlocal swapped
            if path == "autokernel.jsonl" and not swapped:
                swapped = True
                os.replace(replacement, global_path)
            return real_open(path, flags, mode, dir_fd=dir_fd)

        with mock.patch.object(server.os, "open", side_effect=swapping_open):
            payload = server.discovery_live_payload()

        self.assertTrue(swapped)
        self.assertFalse(payload["telemetry_integrity"]["verified"])
        self.assertEqual(payload["autokernel_log"], [])
        self.assertNotIn("ATTACKER PRE OPEN", json.dumps(payload))

    def test_post_read_path_swap_is_retried_and_never_verified(self) -> None:
        event = self._v2_event()
        encoded = json.dumps(event) + "\n"
        global_path = self.operations / "live/autokernel.jsonl"
        planner_path = self.operations / "live/planner.jsonl"
        replacement = self.operations / "post-read-replacement.jsonl"
        global_path.write_text(encoded)
        planner_path.write_text(encoded)
        replacement.write_text('{"prompt":"ATTACKER POST READ"}\n')
        real_pread = os.pread
        swapped = False

        def swapping_pread(fd: int, count: int, offset: int) -> bytes:
            nonlocal swapped
            raw = real_pread(fd, count, offset)
            if not swapped:
                swapped = True
                os.replace(replacement, global_path)
            return raw

        with mock.patch.object(server.os, "pread", side_effect=swapping_pread):
            payload = server.discovery_live_payload()

        self.assertTrue(swapped)
        self.assertFalse(payload["telemetry_integrity"]["verified"])
        self.assertEqual(payload["autokernel_log"], [])
        self.assertNotIn("ATTACKER POST READ", json.dumps(payload))

    def test_in_place_byte_mutation_during_read_is_retried_and_refused(self) -> None:
        event = self._v2_event()
        encoded = json.dumps(event) + "\n"
        global_path = self.operations / "live/autokernel.jsonl"
        planner_path = self.operations / "live/planner.jsonl"
        global_path.write_text(encoded)
        planner_path.write_text(encoded)
        real_pread = os.pread
        mutated = False

        def mutating_pread(fd: int, count: int, offset: int) -> bytes:
            nonlocal mutated
            raw = real_pread(fd, count, offset)
            if not mutated:
                mutated = True
                global_path.write_text('{"prompt":"ATTACKER BYTE MUTATION"}\n')
            return raw

        with mock.patch.object(server.os, "pread", side_effect=mutating_pread):
            payload = server.discovery_live_payload()

        self.assertTrue(mutated)
        self.assertFalse(payload["telemetry_integrity"]["verified"])
        self.assertEqual(payload["autokernel_log"], [])
        self.assertNotIn("ATTACKER BYTE MUTATION", json.dumps(payload))

    def test_between_stream_path_swap_fails_final_pair_validation(self) -> None:
        event = self._v2_event()
        encoded = json.dumps(event) + "\n"
        global_path = self.operations / "live/autokernel.jsonl"
        planner_path = self.operations / "live/planner.jsonl"
        replacement = self.operations / "between-stream-replacement.jsonl"
        global_path.write_text(encoded)
        planner_path.write_text(encoded)
        replacement.write_text('{"prompt":"ATTACKER BETWEEN STREAMS"}\n')
        real_pread = os.pread
        calls = 0
        swapped = False

        def swapping_second_pread(fd: int, count: int, offset: int) -> bytes:
            nonlocal calls, swapped
            calls += 1
            raw = real_pread(fd, count, offset)
            if calls == 2:
                swapped = True
                os.replace(replacement, global_path)
            return raw

        with mock.patch.object(
                server.os, "pread", side_effect=swapping_second_pread):
            payload = server.discovery_live_payload()

        self.assertTrue(swapped)
        self.assertFalse(payload["telemetry_integrity"]["verified"])
        self.assertNotEqual(payload["telemetry_integrity"]["state"], "verified")
        self.assertNotIn("ATTACKER BETWEEN STREAMS", json.dumps(payload))

    def test_between_stream_byte_mutation_fails_final_pair_validation(self) -> None:
        event = self._v2_event()
        encoded = json.dumps(event) + "\n"
        global_path = self.operations / "live/autokernel.jsonl"
        planner_path = self.operations / "live/planner.jsonl"
        global_path.write_text(encoded)
        planner_path.write_text(encoded)
        real_pread = os.pread
        calls = 0
        mutated = False

        def mutating_second_pread(fd: int, count: int, offset: int) -> bytes:
            nonlocal calls, mutated
            calls += 1
            raw = real_pread(fd, count, offset)
            if calls == 2:
                mutated = True
                with global_path.open("a") as handle:
                    handle.write('{"prompt":"ATTACKER BETWEEN STREAMS BYTE"}\n')
            return raw

        with mock.patch.object(
                server.os, "pread", side_effect=mutating_second_pread):
            payload = server.discovery_live_payload()

        self.assertTrue(mutated)
        self.assertFalse(payload["telemetry_integrity"]["verified"])
        self.assertNotEqual(payload["telemetry_integrity"]["state"], "verified")
        self.assertNotIn("ATTACKER BETWEEN STREAMS BYTE", json.dumps(payload))

    def test_v2_same_identity_with_different_payload_is_alarmed_and_dropped(self) -> None:
        base_result = {"returncode": 0, "stdout_sha256": "c" * 64,
                       "stderr_sha256": "d" * 64}
        all_event = self._v2_event(event="planner_completed", result=base_result)
        planner_event = {**all_event, "result": {
            **base_result, "stdout_sha256": "e" * 64}}
        (self.operations / "live/autokernel.jsonl").write_text(
            json.dumps(all_event) + "\n")
        (self.operations / "live/planner.jsonl").write_text(
            json.dumps(planner_event) + "\n")

        payload = server.discovery_live_payload()

        integrity = payload["telemetry_integrity"]
        self.assertEqual(integrity["state"], "conflict")
        self.assertEqual(integrity["conflict_count"], 1)
        self.assertEqual(integrity["dropped_event_count"], 1)
        self.assertEqual(payload["autokernel_log"], [])
        self.assertEqual(payload["planner_log"], [])
        self.assertNotIn("planner_completed", json.dumps(
            payload["activity"]["transitions"]))
        self.assertEqual(payload["_freshness"]["unreported"],
                         ["telemetry_stream_integrity"])

    def test_v2_invalid_identity_or_extra_field_is_dropped_secret_free(self) -> None:
        event = self._v2_event()
        event["event_id"] = "ake-not-a-sha"
        event["prompt"] = "SECRET ACTOR TEXT"
        (self.operations / "live/autokernel.jsonl").write_text(
            json.dumps(event) + "\n")

        payload = server.discovery_live_payload()

        self.assertEqual(payload["autokernel_log"], [])
        self.assertEqual(payload["telemetry_integrity"]["state"], "degraded")
        self.assertIn("rejected by telemetry contract",
                      payload["telemetry_integrity"]["detail"])
        self.assertNotIn("SECRET ACTOR TEXT", json.dumps(payload))

    def test_v2_wrong_actor_channel_is_rejected(self) -> None:
        # _v2_event deliberately emits channel=planner; that is invalid for a
        # critic lifecycle event even though the identity hash excludes channel.
        event = self._v2_event(event="critic_started")
        (self.operations / "live/autokernel.jsonl").write_text(
            json.dumps(event) + "\n")

        payload = server.discovery_live_payload()

        self.assertEqual(payload["autokernel_log"], [])
        self.assertEqual(payload["telemetry_integrity"]["state"], "degraded")
        self.assertIn("rejected by telemetry contract",
                      payload["telemetry_integrity"]["detail"])

    def test_v1_forbids_v2_identity_fields(self) -> None:
        event = {
            "schema": server.AUTOKERNEL_DISCOVERY_EVENT_SCHEMA,
            "ts": "2026-08-19T05:00:00Z", "channel": "planner",
            "event": "planner_started",
            "campaign_id": "ak-discovery-" + "a" * 16,
            "hypothesis_id": "akh-v2-q5-type-specific-dequant",
            "provider": "codex", "model": "gpt-5.6-sol", "effort": "high",
            "event_id": "ake-" + "b" * 64, "operation_key": "c" * 64,
        }
        (self.operations / "live/autokernel.jsonl").write_text(
            json.dumps(event) + "\n")

        payload = server.discovery_live_payload()

        self.assertEqual(payload["autokernel_log"], [])
        self.assertIn("rejected by telemetry contract",
                      payload["telemetry_integrity"]["detail"])

    def test_v2_terminal_result_shape_is_exact(self) -> None:
        event = self._v2_event(
            event="planner_completed", result={"returncode": 0})
        (self.operations / "live/autokernel.jsonl").write_text(
            json.dumps(event) + "\n")

        payload = server.discovery_live_payload()

        self.assertEqual(payload["autokernel_log"], [])
        self.assertIn("rejected by telemetry contract",
                      payload["telemetry_integrity"]["detail"])

    def test_v2_cross_stream_timestamp_divergence_is_dropped_as_corruption(self) -> None:
        event = self._v2_event()
        drifted = {**event, "ts": "2026-08-19T05:00:01Z"}
        (self.operations / "live/autokernel.jsonl").write_text(
            json.dumps(event) + "\n")
        (self.operations / "live/planner.jsonl").write_text(
            json.dumps(drifted) + "\n")

        payload = server.discovery_live_payload()

        integrity = payload["telemetry_integrity"]
        self.assertEqual(integrity["state"], "conflict")
        self.assertEqual(integrity["timestamp_divergence_count"], 1)
        self.assertEqual(integrity["dropped_event_count"], 1)
        self.assertEqual(payload["autokernel_log"], [])
        self.assertEqual(payload["planner_log"], [])

    def test_v2_mirror_order_divergence_is_dropped_as_corruption(self) -> None:
        started = self._v2_event()
        completed = self._v2_event(event="planner_completed", result={
            "returncode": 0, "stdout_sha256": "c" * 64,
            "stderr_sha256": "d" * 64,
        })
        completed["ts"] = "2026-08-19T05:00:01Z"
        global_rows = [started, completed]
        planner_rows = [completed, started]
        (self.operations / "live/autokernel.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in global_rows))
        (self.operations / "live/planner.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in planner_rows))

        payload = server.discovery_live_payload()

        integrity = payload["telemetry_integrity"]
        self.assertEqual(integrity["state"], "conflict")
        self.assertTrue(integrity["order_divergence"])
        self.assertEqual(integrity["dropped_event_count"], 2)
        self.assertEqual(payload["autokernel_log"], [])
        self.assertEqual(payload["planner_log"], [])

    def test_v2_planner_refusal_is_typed_secret_free_and_advances(self) -> None:
        reason_digest = "f" * 64
        event = self._v2_event(event="planner_refused", result={
            "returncode": 0, "stdout_sha256": "c" * 64,
            "stderr_sha256": "d" * 64,
            "refusal_type": "planner_output_refusal",
            "refusal_reason_sha256": reason_digest,
        })
        encoded = json.dumps(event) + "\n"
        (self.operations / "live/autokernel.jsonl").write_text(encoded)
        (self.operations / "live/planner.jsonl").write_text(encoded)
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": event["ts"], "next": 2, "complete": False,
            "iterations": [{
                "turn": 1, "hypothesis_id": event["hypothesis_id"],
                "status": "planner_refused",
                "refusal_type": "planner_output_refusal",
                "scientific_budget_spent": False,
                "reason": "RAW PLANNER REASON MUST NOT CROSS DASHBOARD",
            }],
        }))

        payload = server.discovery_live_payload()
        activity = payload["activity"]

        self.assertEqual(activity["status"], "stopped")
        self.assertEqual(activity["phase"]["id"], "next_hypothesis")
        self.assertEqual(activity["hypothesis_id"], event["hypothesis_id"])
        self.assertEqual(activity["turn"], 1)
        self.assertTrue(activity["refusal"]["detected"])
        self.assertEqual(activity["refusal"]["type"],
                         "planner_output_refusal")
        self.assertFalse(activity["refusal"]["scientific_budget_spent"])
        self.assertIn(reason_digest[:12], activity["refusal"]["detail"])
        self.assertNotIn("RAW PLANNER REASON", json.dumps(payload))
        self.assertFalse(activity["gpu"]["expected_now"])
        pipeline = {row["id"]: row["state"] for row in activity["pipeline"]}
        self.assertEqual(pipeline["planner"], "complete")
        self.assertEqual(pipeline["planner_validation"], "failed")
        self.assertEqual(pipeline["next_hypothesis"], "waiting")

    def test_v25_new_planner_turn_outranks_prior_same_hypothesis_refusal(
            self) -> None:
        hypothesis = "akh-v2-q5-type-specific-dequant"
        first_operation = "1" * 64
        second_operation = "2" * 64
        reason_digest = "f" * 64

        def event(kind: str, at: str, operation: str,
                  result: dict | None = None) -> dict:
            row = self._v2_event(event=kind, result=result)
            row["ts"] = at
            row["operation_key"] = operation
            identity = {key: value for key, value in row.items()
                        if key not in {"ts", "channel", "event_id", "result"}}
            row["event_id"] = "ake-" + hashlib.sha256(json.dumps(
                identity, sort_keys=True, separators=(",", ":")
            ).encode("ascii")).hexdigest()
            return row

        first_started = event(
            "planner_started", "2026-08-21T05:03:35.223898Z",
            first_operation)
        refused = event(
            "planner_refused", "2026-08-21T05:11:40.141127Z",
            first_operation, {
                "returncode": 0, "stdout_sha256": "c" * 64,
                "stderr_sha256": "d" * 64,
                "refusal_type": "planner_output_refusal",
                "refusal_reason_sha256": reason_digest,
            })
        second_started = event(
            "planner_started", "2026-08-21T05:11:40.338103Z",
            second_operation)
        rows = [first_started, refused, second_started]
        encoded = "".join(json.dumps(row) + "\n" for row in rows)
        (self.operations / "live/autokernel.jsonl").write_text(encoded)
        (self.operations / "live/planner.jsonl").write_text(encoded)
        raw_reason = "SourceCandidateError: RAW AUTHORING DETAIL MUST NOT EXPORT"
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": "2026-08-21T05:11:40.148346Z",
            "next": 2, "complete": False,
            "iterations": [{
                "turn": 1, "hypothesis_id": hypothesis,
                "planner_operation_key": first_operation,
                "status": "planner_refused",
                "refusal_type": "planner_output_refusal",
                "scientific_budget_spent": False,
                "telemetry_event": "planner_refused",
                "telemetry_status": "emitted", "reason": raw_reason,
            }],
            "planning": {
                "turn": 2, "operation_key": second_operation,
                "phase": "actor_entering", "provider_attempt": 0,
                "portfolio_binding": {"hypothesis_id": hypothesis},
                "context": {"authoring_assignment": {
                    "campaign_id": "ak-discovery-" + "a" * 16,
                    "portfolio_binding": {"hypothesis_id": hypothesis},
                }},
            },
        }))

        observed_now = server._parse_semantic_timestamp(
            "2026-08-21T05:12:00.000000Z")
        with (self.state / "controller.run.lock").open("r") as handle, \
                mock.patch.object(server.time, "time", return_value=observed_now):
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            payload = server.discovery_live_payload()
        activity = payload["activity"]

        self.assertEqual(payload["telemetry_integrity"]["state"], "verified")
        self.assertEqual(activity["status"], "running")
        self.assertEqual(activity["phase"]["id"], "planner")
        self.assertEqual(activity["phase"]["label"], "Planner model call")
        self.assertEqual(activity["phase"]["started_at"], second_started["ts"])
        self.assertEqual(activity["turn"], 2)
        self.assertEqual(activity["hypothesis_id"], hypothesis)
        self.assertEqual(activity["waiting_on"], "planner completion")
        self.assertFalse(activity["gpu"]["expected_now"])
        self.assertFalse(activity["gpu"]["claim_held"])
        self.assertFalse(activity["refusal"]["detected"])
        pipeline = {row["id"]: row["state"] for row in activity["pipeline"]}
        self.assertEqual(pipeline["planner"], "running")
        self.assertEqual(pipeline["planner_validation"], "not_reached")
        prior = activity["prior_terminal"]
        self.assertEqual(prior["turn"], 1)
        self.assertEqual(prior["status"], "planner_refused")
        self.assertEqual(prior["stage"], "planner_validation")
        self.assertFalse(prior["scientific_budget_spent"])
        self.assertIn(reason_digest[:12], prior["detail"])
        self.assertEqual(activity["history"]["terminal_count"], 1)
        self.assertEqual(activity["history"]["terminal_rows"], [prior])
        self.assertEqual(activity["transitions"][-1]["event"],
                         "planner_started")
        self.assertNotIn(raw_reason, json.dumps(payload))

    def test_v25_prior_planner_refusal_requires_exact_operation_join(self) -> None:
        state = {"iterations": [{
            "turn": 1,
            "hypothesis_id": "akh-v2-q5-type-specific-dequant",
            "planner_operation_key": "1" * 64,
            "status": "planner_refused",
            "refusal_type": "planner_output_refusal",
            "scientific_budget_spent": False,
            "telemetry_event": "planner_refused",
            "telemetry_status": "emitted",
        }]}
        refusal = self._v2_event(event="planner_refused", result={
            "returncode": 0, "stdout_sha256": "c" * 64,
            "stderr_sha256": "d" * 64,
            "refusal_type": "planner_output_refusal",
            "refusal_reason_sha256": "f" * 64,
        })
        refusal["operation_key"] = "2" * 64
        self.assertEqual(server._discovery_planner_refusal_terminals(
            state, [refusal], "ak-discovery-" + "a" * 16, 2), [])
        refusal["operation_key"] = "1" * 64
        self.assertEqual(server._discovery_planner_refusal_terminals(
            state, [refusal, dict(refusal)],
            "ak-discovery-" + "a" * 16, 2), [])

    def test_v25_planner_successor_requires_state_event_freshness_binding(
            self) -> None:
        campaign = "ak-discovery-" + "a" * 16
        hypothesis = "akh-v2-q5-type-specific-dequant"
        binding = {"hypothesis_id": hypothesis}
        state = {"next": 2, "updated_at": "2026-08-21T05:11:40.148346Z"}
        planning = {
            "turn": 2, "phase": "actor_entering", "provider_attempt": 0,
            "operation_key": "2" * 64, "portfolio_binding": binding,
            "context": {"authoring_assignment": {
                "campaign_id": campaign, "portfolio_binding": binding}},
        }
        prior = {
            "turn": 1, "status": "planner_refused",
            "hypothesis_id": hypothesis,
            "refusal_type": "planner_output_refusal",
            "scientific_budget_spent": False,
            "telemetry_event": "planner_refused",
            "telemetry_status": "emitted",
            "planner_operation_key": "1" * 64,
        }
        event = {
            "event": "planner_started", "campaign_id": campaign,
            "hypothesis_id": hypothesis, "operation_key": "2" * 64,
            "ts": "2026-08-21T05:11:40.338103Z",
        }
        refusal = {
            "event": "planner_refused", "campaign_id": campaign,
            "hypothesis_id": hypothesis, "operation_key": "1" * 64,
            "ts": "2026-08-21T05:11:40.141127Z",
            "result": {
                "returncode": 0, "stdout_sha256": "a" * 64,
                "stderr_sha256": "b" * 64,
                "refusal_type": "planner_output_refusal",
                "refusal_reason_sha256": "c" * 64,
            },
        }
        now = server._parse_semantic_timestamp("2026-08-21T05:12:00Z")
        self.assertTrue(server._discovery_planner_successor_binding(
            state, planning, [refusal, event], prior, campaign, now))
        for field, value in (
                ("operation_key", "3" * 64),
                ("ts", "2026-08-21T05:11:40.100000Z"),
                ("campaign_id", "ak-discovery-" + "b" * 16),
                ("ts", "2026-08-21T05:12:10.000000Z")):
            mutated = dict(event)
            mutated[field] = value
            with self.subTest(field=field):
                self.assertFalse(server._discovery_planner_successor_binding(
                    state, planning, [refusal, mutated], prior, campaign, now))

    def test_v25_critic_and_inflight_require_exact_successor_lineage(self) -> None:
        campaign = "ak-discovery-" + "a" * 16
        hypothesis = "akh-v2-q5-type-specific-dequant"
        prior = {
            "turn": 1, "hypothesis_id": hypothesis,
            "status": "planner_refused",
            "refusal_type": "planner_output_refusal",
            "scientific_budget_spent": False,
            "telemetry_event": "planner_refused",
            "telemetry_status": "emitted",
            "planner_operation_key": "1" * 64,
        }
        refusal_result = {
            "returncode": 0, "stdout_sha256": "a" * 64,
            "stderr_sha256": "b" * 64,
            "refusal_type": "planner_output_refusal",
            "refusal_reason_sha256": "c" * 64,
        }
        planner_result = {"returncode": 0, "stdout_sha256": "d" * 64,
                          "stderr_sha256": "e" * 64}
        critic_result = {"decision": "accept", "stdout_sha256": "f" * 64,
                         "stderr_sha256": "0" * 64}
        events = [
            {"event": "planner_refused", "campaign_id": campaign,
             "hypothesis_id": hypothesis, "operation_key": "1" * 64,
             "ts": "2026-08-21T05:11:40.141127Z", "result": refusal_result},
            {"event": "planner_started", "campaign_id": campaign,
             "hypothesis_id": hypothesis, "operation_key": "2" * 64,
             "ts": "2026-08-21T05:11:40.338103Z"},
            {"event": "planner_completed", "campaign_id": campaign,
             "hypothesis_id": hypothesis, "operation_key": "2" * 64,
             "ts": "2026-08-21T05:18:09.614081Z", "result": planner_result},
            {"event": "critic_started", "campaign_id": campaign,
             "hypothesis_id": hypothesis, "operation_key": "3" * 64,
             "ts": "2026-08-21T05:18:10.047800Z"},
        ]
        pending_state = {"next": 2,
                         "updated_at": "2026-08-21T05:18:09.900000Z"}
        pending = {
            "phase": "critic_pending",
            "row": {"turn": 2, "hypothesis_id": hypothesis},
            "candidate": {"hypothesis_id": hypothesis},
        }
        now = server._parse_semantic_timestamp("2026-08-21T05:20:00Z")
        self.assertTrue(server._discovery_pending_successor_binding(
            pending_state, pending, events, prior, campaign, now))
        self.assertTrue(server._discovery_pending_successor_binding(
            pending_state, {**pending, "turn": 2}, events,
            prior, campaign, now))
        self.assertFalse(server._discovery_pending_successor_binding(
            pending_state, {**pending, "turn": 3}, events,
            prior, campaign, now))
        critic_index = len(events) - 1
        for field, value in (
                ("campaign_id", "ak-discovery-" + "b" * 16),
                ("operation_key", "2" * 64),
                ("hypothesis_id", "akh-wrong"),
                ("ts", "2026-08-21T05:11:40.100000Z"),
                ("ts", "2026-08-21T05:20:10.000000Z"),
                ("result", {"unexpected": True})):
            mutated_events = [dict(row) for row in events]
            mutated_events[critic_index][field] = value
            with self.subTest(stage="critic", field=field, value=str(value)[:20]):
                self.assertFalse(server._discovery_pending_successor_binding(
                    pending_state, pending, mutated_events, prior, campaign, now))

        complete = {
            "event": "critic_completed", "campaign_id": campaign,
            "hypothesis_id": hypothesis, "operation_key": "3" * 64,
            "ts": "2026-08-21T05:19:50.887498Z", "result": critic_result,
        }
        complete_events = [*events, complete]
        source_operation = "4" * 64
        inflight_state = {"next": 2,
                          "updated_at": "2026-08-21T05:19:51.315783Z"}
        inflight = {
            "operation_key": source_operation,
            "row": {"turn": 2, "hypothesis_id": hypothesis,
                    "operation_key": source_operation},
            "candidate": {"hypothesis_id": hypothesis},
        }
        self.assertTrue(server._discovery_inflight_successor_binding(
            inflight_state, inflight, complete_events, prior, campaign, now))
        for field, value in (
                ("campaign_id", "ak-discovery-" + "b" * 16),
                ("operation_key", "2" * 64),
                ("hypothesis_id", "akh-wrong"),
                ("ts", "2026-08-21T05:18:09.000000Z"),
                ("ts", "2026-08-21T05:20:10.000000Z"),
                ("result", {**critic_result, "decision": "reject"})):
            mutated_events = [dict(row) for row in complete_events]
            mutated_events[-1][field] = value
            with self.subTest(stage="inflight", field=field,
                              value=str(value)[:20]):
                self.assertFalse(server._discovery_inflight_successor_binding(
                    inflight_state, inflight, mutated_events, prior,
                    campaign, now))
        tampered_inflight = {**inflight, "operation_key": "5" * 64}
        self.assertFalse(server._discovery_inflight_successor_binding(
            inflight_state, tampered_inflight, complete_events,
            prior, campaign, now))
        for field, value in (
                ("scientific_budget_spent", True),
                ("refusal_type", "other_refusal"),
                ("telemetry_event", "planner_completed"),
                ("telemetry_status", "missing")):
            mutated_prior = {**prior, field: value}
            with self.subTest(stage="prior", field=field):
                self.assertFalse(server._discovery_pending_successor_binding(
                    pending_state, pending, events, mutated_prior,
                    campaign, now))
                self.assertFalse(server._discovery_inflight_successor_binding(
                    inflight_state, inflight, complete_events,
                    mutated_prior, campaign, now))

    def test_state_side_visibility_failure_is_visible_as_historical_loss(self) -> None:
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": "2026-08-19T05:01:00Z", "next": 1,
            "complete": False, "iterations": [],
            "visibility_degraded": [{
                "event": "planner_refused", "operation_key": "b" * 64,
                "error_type": "OSError", "error_sha256": "c" * 64,
            }],
        }))

        payload = server.discovery_live_payload()
        integrity = payload["telemetry_integrity"]

        self.assertEqual(integrity["state"], "legacy")
        historical = integrity["historical_visibility_loss"]
        self.assertTrue(historical["detected"])
        self.assertEqual(historical["count"], 1)
        self.assertEqual(historical["markers"][0]["error_type"],
                         "OSError")
        self.assertEqual(payload["_freshness"]["unreported"], [])
        self.assertNotIn("error", historical["markers"][0])

    def test_v16_planner_terminal_failure_is_not_projected_as_idle(self) -> None:
        """Exact v16 seam: a typed planning failure must remain visible."""
        campaign_id = "ak-discovery-" + "a" * 16
        started_at = "2026-08-19T04:42:39.059499Z"
        failed_at = "2026-08-19T04:48:25.206346Z"
        hypothesis_id = "akh-v2-q5-type-specific-dequant"
        event = {
            "schema": server.AUTOKERNEL_DISCOVERY_EVENT_SCHEMA,
            "ts": started_at, "channel": "planner",
            "event": "planner_started", "campaign_id": campaign_id,
            "hypothesis_id": hypothesis_id, "provider": "codex",
            "model": "gpt-5.6-sol", "effort": "high",
        }
        (self.operations / "live/autokernel.jsonl").write_text(
            json.dumps(event) + "\n")
        (self.operations / "live/planner.jsonl").write_text(
            json.dumps(event) + "\n")
        planning = {
            "turn": 1, "phase": "actor_entering",
            "portfolio_binding": {"hypothesis_id": hypothesis_id},
            "context": {"authoring_assignment": {
                "campaign_id": campaign_id,
            }},
            "failure": {
                "type": "TelemetryError",
                "message": "telemetry result contains a non-allowlisted field",
            },
        }
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": "2026-08-19T04:48:25.203592Z",
            "next": 1, "complete": False, "iterations": [],
            "planning": planning,
        }))
        journal = self.state / "journal"
        journal.mkdir()
        (journal / "events.jsonl").write_text(json.dumps({
            "journal_schema": "epyc.autokernel.journal_entry.v1",
            "event_id": "akj-000000000003-29f8feef6dc9",
            "kind": "STOP_STATE", "seq": 3, "written_at": failed_at,
            "payload": {
                "state": "discovery_planner_terminal_failure",
                "controller_state_sha256": "c" * 64,
            },
        }) + "\n")

        payload = server.discovery_live_payload()
        activity = payload["activity"]

        self.assertFalse(payload["active"])
        self.assertEqual(activity["status"], "failed")
        self.assertEqual(activity["phase"]["id"], "planner_validation")
        self.assertEqual(activity["hypothesis_id"], hypothesis_id)
        self.assertEqual(activity["turn"], 1)
        self.assertTrue(activity["failure"]["detected"])
        self.assertEqual(activity["failure"]["stage"], "planner_validation")
        self.assertIn("non-allowlisted field", activity["failure"]["detail"])
        self.assertIn("fresh sealed deployment", activity["failure"]["recovery"])
        self.assertFalse(activity["gpu"]["expected_now"])
        self.assertFalse(activity["gpu"]["claim_held"])
        pipeline = {row["id"]: row["state"] for row in activity["pipeline"]}
        self.assertEqual(pipeline["planner"], "complete")
        self.assertEqual(pipeline["planner_validation"], "failed")
        self.assertEqual(pipeline["critic"], "not_reached")
        self.assertIn("FAILED", payload["status_message"])
        self.assertEqual(payload["autokernel_log"][0]["event"], "planner_started")
        self.assertEqual(payload["planner_log"][0]["event"], "planner_started")

    def test_path_escape_in_deployment_is_not_read(self) -> None:
        config_path = self.bundle / "config/deployment.json"
        config = json.loads(config_path.read_text())
        config["controller"]["operations_root"] = "/etc"
        config_path.write_text(json.dumps(config))
        payload = server.discovery_live_payload()
        self.assertFalse(payload["available"])
        self.assertEqual(payload["autokernel_log"], [])

    def test_active_campaign_outranks_newer_terminal_progress(self) -> None:
        terminal = self.bundle.parent / "campaign-terminal"
        terminal_state = terminal / "state"
        terminal_operations = terminal / "operations"
        (terminal / "config").mkdir(parents=True)
        terminal_state.mkdir()
        (terminal_operations / "live").mkdir(parents=True)
        (terminal_state / "controller.run.lock").touch()
        (terminal / "config/deployment.json").write_text(json.dumps({
            "config_sha256": "b" * 64,
            "controller": {
                "state_root": str(terminal_state),
                "operations_root": str(terminal_operations),
            },
        }))
        (terminal_state / "state.json").write_text(json.dumps({
            "updated_at": "2099-01-01T00:00:00Z",
            "complete": False,
            "iterations": [],
            "inflight": {
                "exception": {"type": "RuntimeError", "message": "terminal"},
            },
        }))

        with (self.state / "controller.run.lock").open("r") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            payload = server.discovery_live_payload()

        self.assertTrue(payload["active"])
        self.assertEqual(payload["deployment"], "campaign-a")

    def test_pre_controller_supervisor_terminal_selects_newest_deployment(self) -> None:
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": "2026-08-20T00:00:00Z", "next": 1,
            "complete": True, "iterations": [],
        }))
        v21 = self.bundle.parent / "campaign-v21"
        v21_state = v21 / "state"
        v21_operations = v21 / "operations"
        (v21 / "config").mkdir(parents=True)
        v21_state.mkdir()
        (v21_operations / "live").mkdir(parents=True)
        (v21_state / "controller.run.lock").touch()
        config_path = v21 / "config/deployment.json"
        config_path.write_text(json.dumps({
            "config_sha256": "2" * 64,
            "controller": {"state_root": str(v21_state),
                           "operations_root": str(v21_operations)},
        }))
        self._write_supervisor_graph_mismatch(v21, config_path)

        payload = server.discovery_live_payload()

        self.assertEqual(payload["deployment"], "campaign-v21")
        self.assertEqual(payload["launch_evidence"], "supervisor_terminal")
        self.assertFalse(payload["active"])
        self.assertIsNone(payload["state"])
        activity = payload["activity"]
        self.assertEqual(activity["status"], "failed")
        self.assertEqual(activity["phase"]["id"],
                         "deployment_graph_revalidation")
        self.assertFalse(activity["gpu"]["expected_now"])
        self.assertFalse(activity["gpu"]["claim_held"])
        self.assertFalse(activity["resume"]["possible"])
        self.assertIn("fresh sealed successor", activity["failure"]["recovery"])
        stderr = activity["failure"]["stderr"]
        self.assertEqual(set(stderr), {"sha256", "size", "detail"})
        self.assertRegex(stderr["sha256"], r"^[0-9a-f]{64}$")
        encoded = json.dumps(payload)
        self.assertNotIn("SECRET PROMPT", encoded)
        self.assertNotIn("unsafe actor output", encoded)
        self.assertEqual(payload["deployment_history"][0]["deployment"],
                         "campaign-a")
        self.assertEqual(payload["deployment_history"][0]["disposition"],
                         "historical")

    def test_touched_old_launched_config_cannot_outrank_newer_producer(self) -> None:
        old_runtime = self._write_supervisor_graph_mismatch(
            self.bundle, self.bundle / "config/deployment.json")
        self._set_supervisor_terminal_time(
            old_runtime, ledger_at="2026-08-21T00:35:10.500000Z",
            identity_at="2026-08-21T00:35:10.501000Z")
        newer = self.bundle.parent / "campaign-newer"
        newer_state = newer / "state"
        newer_operations = newer / "operations"
        (newer / "config").mkdir(parents=True)
        newer_state.mkdir()
        (newer_operations / "live").mkdir(parents=True)
        (newer_state / "controller.run.lock").touch()
        newer_config = newer / "config/deployment.json"
        newer_config.write_text(json.dumps({
            "config_sha256": "9" * 64,
            "controller": {"state_root": str(newer_state),
                           "operations_root": str(newer_operations)},
        }))
        newer_runtime = self._write_supervisor_graph_mismatch(
            newer, newer_config)
        self._set_supervisor_terminal_time(
            newer_runtime, ledger_at="2026-08-21T00:36:10.500000Z",
            identity_at="2026-08-21T00:36:10.501000Z")
        touched = datetime.now(timezone.utc).timestamp() + 3600
        old_config = self.bundle / "config/deployment.json"
        os.utime(old_config, (touched, touched))

        payload = server.discovery_live_payload()

        self.assertEqual(payload["deployment"], "campaign-newer")
        self.assertEqual(payload["launch_evidence"], "supervisor_terminal")
        self.assertEqual(payload["deployment_history"][0]["deployment"],
                         "campaign-a")

    def test_untrusted_supervisor_terminal_cannot_mask_controller_history(self) -> None:
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": "2026-08-20T00:00:00Z", "next": 1,
            "complete": True, "iterations": [],
        }))
        v21 = self.bundle.parent / "campaign-v21"
        v21_state = v21 / "state"
        v21_operations = v21 / "operations"
        (v21 / "config").mkdir(parents=True)
        v21_state.mkdir()
        (v21_operations / "live").mkdir(parents=True)
        (v21_state / "controller.run.lock").touch()
        config_path = v21 / "config/deployment.json"
        config_path.write_text(json.dumps({
            "config_sha256": "2" * 64,
            "controller": {"state_root": str(v21_state),
                           "operations_root": str(v21_operations)},
        }))
        runtime = self._write_supervisor_graph_mismatch(v21, config_path)
        ledger = runtime / "death-ledger.jsonl"
        ledger.chmod(0o644)

        payload = server.discovery_live_payload()

        self.assertEqual(payload["deployment"], "campaign-a")
        self.assertEqual(payload["launch_evidence"], "controller")
        self.assertTrue(payload["newest_unlaunched_deployment"]["available"])
        self.assertEqual(payload["newest_unlaunched_deployment"]["deployment"],
                         "campaign-v21")

    def test_supervisor_v2_spec_requires_exact_canonical_13_key_grammar(self) -> None:
        config_path = self.bundle / "config/deployment.json"
        config = json.loads(config_path.read_text())
        runtime = self._write_supervisor_graph_mismatch(self.bundle, config_path)
        spec_path = runtime / "launch-spec.json"
        original = json.loads(spec_path.read_text())
        self.assertEqual(len(original), 13)
        for key in tuple(original):
            with self.subTest(remove=key):
                mutated = dict(original)
                mutated.pop(key)
                spec_path.write_bytes(server._canonical_json_bytes(mutated) + b"\n")
                self.assertIsNone(server._supervisor_terminal_observation(
                    self.bundle, config_path, config))
        mutated = dict(original)
        mutated["unexpected"] = "field"
        spec_path.write_bytes(server._canonical_json_bytes(mutated) + b"\n")
        self.assertIsNone(server._supervisor_terminal_observation(
            self.bundle, config_path, config))
        spec_path.write_text(json.dumps(original, indent=2) + "\n")
        self.assertIsNone(server._supervisor_terminal_observation(
            self.bundle, config_path, config))

    def test_supervisor_v3_spec_is_a_separate_exact_graph_module_contract(self) -> None:
        config_path = self.bundle / "config/deployment.json"
        config = json.loads(config_path.read_text())
        runtime = self._write_supervisor_graph_mismatch(self.bundle, config_path)
        spec = json.loads((runtime / "launch-spec.json").read_text())
        spec["schema"] = server._SUPERVISOR_SPEC_SCHEMA_V3
        manifest = spec["execution_closure"]["manifest"]
        for index, logical_path in enumerate(
                server._SUPERVISOR_GRAPH_EXECUTION_MODULES_V3.values(), 100):
            if logical_path in manifest:
                continue
            digest = hashlib.sha256(logical_path.encode()).hexdigest()
            manifest[logical_path] = {
                "sha256": digest,
                "source": {"dev": 1, "ino": index, "mode": 0o644,
                           "nlink": 1, "size": index, "uid": os.geteuid()},
                "closure": {"dev": 2, "ino": index, "mode": 0o444,
                            "nlink": 1, "size": index, "uid": 0},
            }
        content_manifest = {key: value["sha256"]
                            for key, value in manifest.items()}
        content_sha = hashlib.sha256(
            server._canonical_json_bytes(content_manifest)).hexdigest()
        closure = Path("/var/lib/epyc-autokernel/execution-closures") / content_sha
        spec["execution_closure"].update({
            "path": str(closure), "content_sha256": content_sha,
            "manifest_sha256": hashlib.sha256(
                server._canonical_json_bytes(manifest)).hexdigest()})
        for module, binding in spec["execution_modules"].items():
            filename = Path(binding["path"]).name
            binding["path"] = str(
                closure / "scripts/kernel_rnd/autokernel/controller" / filename)
        spec["graph_execution_modules"] = {
            role: {"logical_path": logical_path,
                   "sha256": manifest[logical_path]["sha256"]}
            for role, logical_path in
            server._SUPERVISOR_GRAPH_EXECUTION_MODULES_V3.items()}
        self._rebind_supervisor_spec(runtime, spec)
        self.assertIsNotNone(server._supervisor_terminal_observation(
            self.bundle, config_path, config))

        missing = json.loads(json.dumps(spec))
        missing["graph_execution_modules"].pop("hypothesis_portfolio")
        self._rebind_supervisor_spec(runtime, missing)
        self.assertIsNone(server._supervisor_terminal_observation(
            self.bundle, config_path, config))

        extra = json.loads(json.dumps(spec))
        extra["graph_execution_modules"]["unexpected_role"] = {
            "logical_path": next(iter(manifest)),
            "sha256": manifest[next(iter(manifest))]["sha256"]}
        self._rebind_supervisor_spec(runtime, extra)
        self.assertIsNone(server._supervisor_terminal_observation(
            self.bundle, config_path, config))

        roles = list(server._SUPERVISOR_GRAPH_EXECUTION_MODULES_V3)
        for index, role in enumerate(roles):
            with self.subTest(swapped_role=role):
                swapped = json.loads(json.dumps(spec))
                other = roles[(index + 1) % len(roles)]
                swapped["graph_execution_modules"][role] = dict(
                    swapped["graph_execution_modules"][other])
                self._rebind_supervisor_spec(runtime, swapped)
                self.assertIsNone(server._supervisor_terminal_observation(
                    self.bundle, config_path, config))

        duplicate = json.loads(json.dumps(spec))
        first = dict(next(iter(duplicate["graph_execution_modules"].values())))
        duplicate["graph_execution_modules"] = {
            role: dict(first) for role in roles}
        self._rebind_supervisor_spec(runtime, duplicate)
        self.assertIsNone(server._supervisor_terminal_observation(
            self.bundle, config_path, config))

    def test_coherent_spec_rehash_cannot_forge_runtime_or_config_identity(self) -> None:
        config_path = self.bundle / "config/deployment.json"
        config = json.loads(config_path.read_text())
        runtime = self._write_supervisor_graph_mismatch(self.bundle, config_path)
        original = json.loads((runtime / "launch-spec.json").read_text())
        for path in (("runtime_root_identity", "ino"),
                     ("deployment_config", "identity", "ino"),
                     ("deployment_config", "source_identity", "ino")):
            with self.subTest(path=path):
                mutated = json.loads(json.dumps(original))
                target = mutated
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] += 1
                self._rebind_supervisor_spec(runtime, mutated)
                self.assertIsNone(server._supervisor_terminal_observation(
                    self.bundle, config_path, config))

    def test_ledger_payload_fsm_rejects_every_missing_or_extra_key(self) -> None:
        config_path = self.bundle / "config/deployment.json"
        config = json.loads(config_path.read_text())
        runtime = self._write_supervisor_graph_mismatch(self.bundle, config_path)
        original = [json.loads(line) for line in
                    (runtime / "death-ledger.jsonl").read_text().splitlines()]
        for index, row in enumerate(original):
            for key in tuple(row["payload"]):
                with self.subTest(event=row["event"], missing=key):
                    mutated = json.loads(json.dumps(original))
                    mutated[index]["payload"].pop(key)
                    self._rewrite_supervisor_ledger(runtime, mutated)
                    self.assertIsNone(server._supervisor_terminal_observation(
                        self.bundle, config_path, config))
            with self.subTest(event=row["event"], extra=True):
                mutated = json.loads(json.dumps(original))
                mutated[index]["payload"]["unexpected"] = "field"
                self._rewrite_supervisor_ledger(runtime, mutated)
                self.assertIsNone(server._supervisor_terminal_observation(
                    self.bundle, config_path, config))

    def test_rehashed_ledger_binding_tamper_and_unsafe_stderr_are_refused(self) -> None:
        config_path = self.bundle / "config/deployment.json"
        config = json.loads(config_path.read_text())
        runtime = self._write_supervisor_graph_mismatch(self.bundle, config_path)
        original = [json.loads(line) for line in
                    (runtime / "death-ledger.jsonl").read_text().splitlines()]
        mutations = (
            lambda rows: rows[0]["payload"].__setitem__("session_name", "ak-" + "0" * 24),
            lambda rows: rows[1]["payload"].__setitem__("stderr", "/tmp/escape"),
            lambda rows: rows[1]["payload"]["cgroup"].__setitem__(
                "path", rows[1]["payload"]["cgroup"]["path"] + "-forged"),
            lambda rows: rows[2]["payload"].__setitem__("restart_count", 1),
            lambda rows: rows[2]["payload"].__setitem__(
                "cleanup_actions", ["SIGTERM", "cgroup.remove"]),
            lambda rows: rows[2]["payload"].__setitem__(
                "cleanup_actions", ["cgroup.remove", "cgroup.remove"]),
            lambda rows: rows[3]["payload"].__setitem__("last_return_code", 2),
            lambda rows: rows[4]["payload"].__setitem__("exit_code", 2),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(binding=index):
                rows = json.loads(json.dumps(original))
                mutate(rows)
                self._rewrite_supervisor_ledger(runtime, rows)
                self.assertIsNone(server._supervisor_terminal_observation(
                    self.bundle, config_path, config))

        self._rewrite_supervisor_ledger(runtime, original)
        stderr = runtime / "controller.stderr.log"
        stderr.write_text(
            "DeploymentFactoryError: durable deployment graph differs "
            "from current sealed graph\nunsafe tail\n")
        self.assertIsNone(server._supervisor_terminal_observation(
            self.bundle, config_path, config))

    def test_identity_time_must_follow_terminal_ledger_with_bounded_skew(self) -> None:
        config_path = self.bundle / "config/deployment.json"
        config = json.loads(config_path.read_text())
        runtime = self._write_supervisor_graph_mismatch(self.bundle, config_path)
        identity_path = runtime / "identity.json"
        identity = json.loads(identity_path.read_text())
        for timestamp in ("2026-08-21T00:35:09Z",
                          "2026-08-21T00:35:20Z",
                          "2099-01-01T00:00:00Z"):
            with self.subTest(timestamp=timestamp):
                mutated = dict(identity)
                mutated["updated_at"] = timestamp
                identity_path.write_bytes(
                    server._canonical_json_bytes(mutated) + b"\n")
                self.assertIsNone(server._supervisor_terminal_observation(
                    self.bundle, config_path, config))

    def test_supervisor_runtime_root_and_file_identity_are_fail_closed(self) -> None:
        config_path = self.bundle / "config/deployment.json"
        config = json.loads(config_path.read_text())
        runtime = self._write_supervisor_graph_mismatch(self.bundle, config_path)
        runtime.chmod(0o755)
        self.assertIsNone(server._supervisor_terminal_observation(
            self.bundle, config_path, config))
        runtime.chmod(0o700)

        ledger = runtime / "death-ledger.jsonl"
        ledger.chmod(0o644)
        self.assertIsNone(server._supervisor_terminal_observation(
            self.bundle, config_path, config))
        ledger.chmod(0o600)

        target = runtime / "ledger-target"
        target.write_bytes(ledger.read_bytes())
        target.chmod(0o600)
        ledger.unlink()
        os.link(target, ledger)
        self.assertIsNone(server._supervisor_terminal_observation(
            self.bundle, config_path, config))

    def test_supervisor_stderr_ceiling_and_terminal_signature_are_fail_closed(self) -> None:
        config_path = self.bundle / "config/deployment.json"
        config = json.loads(config_path.read_text())
        runtime = self._write_supervisor_graph_mismatch(self.bundle, config_path)
        stderr = runtime / "controller.stderr.log"
        stderr.write_bytes(b"x" * (64 * 1024 + 1))
        self.assertIsNone(server._supervisor_terminal_observation(
            self.bundle, config_path, config))
        stderr.write_text("signature absent\n")
        self.assertIsNone(server._supervisor_terminal_observation(
            self.bundle, config_path, config))

    def test_nonfinite_json_is_refused_without_breaking_live_endpoint(self) -> None:
        config_path = self.bundle / "config/deployment.json"
        config = json.loads(config_path.read_text())
        runtime = self._write_supervisor_graph_mismatch(self.bundle, config_path)
        spec_path = runtime / "launch-spec.json"
        identity_path = runtime / "identity.json"
        ledger_path = runtime / "death-ledger.jsonl"
        original_spec = spec_path.read_bytes()
        original_identity = identity_path.read_bytes()
        original_rows = [json.loads(line) for line in
                         ledger_path.read_text().splitlines()]

        for token in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(carrier="spec", token=token):
                spec_path.write_bytes(original_spec.replace(
                    b'"validate_only":false',
                    f'"validate_only":{token}'.encode("ascii")))
                self.assertIsNone(server._supervisor_terminal_observation(
                    self.bundle, config_path, config))
                self.assertEqual(
                    server.discovery_live_payload()["launch_evidence"],
                    "unlaunched")
        spec_path.write_bytes(original_spec)

        identity_path.write_bytes(original_identity.replace(
            b'"exit_code":1', b'"exit_code":NaN'))
        self.assertIsNone(server._supervisor_terminal_observation(
            self.bundle, config_path, config))
        self.assertEqual(server.discovery_live_payload()["launch_evidence"],
                         "unlaunched")
        identity_path.write_bytes(original_identity)

        for index, row in enumerate(original_rows):
            with self.subTest(carrier="ledger", event=row["event"]):
                encoded = []
                for row_index, original in enumerate(original_rows):
                    if row_index == index:
                        body = dict(original)
                        body["payload"] = dict(body["payload"])
                        body["payload"]["nonfinite"] = float("nan")
                        encoded.append(json.dumps(
                            body, sort_keys=True, separators=(",", ":"),
                            allow_nan=True).encode("ascii"))
                    else:
                        encoded.append(server._canonical_json_bytes(original))
                ledger_path.write_bytes(b"\n".join(encoded) + b"\n")
                self.assertIsNone(server._supervisor_terminal_observation(
                    self.bundle, config_path, config))
                self.assertEqual(
                    server.discovery_live_payload()["launch_evidence"],
                    "unlaunched")


if __name__ == "__main__":
    unittest.main()
