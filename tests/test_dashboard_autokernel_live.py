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
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name) / "deployments"
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

    def tearDown(self) -> None:
        server.AUTOKERNEL_DEPLOYMENTS_ROOT = self._old_root
        self.temp.cleanup()

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


if __name__ == "__main__":
    unittest.main()
