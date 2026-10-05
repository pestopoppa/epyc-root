"""Tests for AdmissionController per-backend concurrency limiter."""

from pathlib import Path
import threading

import yaml

from src.api.admission import (
    STACK_PRIORS_PATH,
    AdmissionController,
    FALLBACK_LIMITS,
    _limits_from_stack_priors,
    _limits_from_stack_manifest,
    _load_default_limits,
)


def _expected_priors_limits(path: Path = STACK_PRIORS_PATH) -> dict[str, int]:
    """Re-derive the per-URL admission limits straight from the priors FILE.

    Deliberately independent of ``src.registry.stack_priors`` (a test that calls
    the production helper and compares it to itself proves nothing): this walks
    the raw YAML with the precedence the contract states — per-port
    ``runtime.cache.slots_by_port`` is the authority for a port, then the launch
    ENTRY's own ``slots``, then the role-level ``serving.slots`` for a declared
    port with neither. Collisions (two roles on one URL, e.g. an alias and its
    host) resolve with ``max`` exactly as the launcher's ``-np`` must.
    """
    artifact = yaml.safe_load(Path(path).read_text()) or {}
    roles = artifact.get("roles") or {}
    limits: dict[str, int] = {}

    def _bump(url: str, value: int) -> None:
        limits[url] = max(value, limits.get(url, 0))

    def _slots(value: object) -> int | None:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            return None
        return value

    for record in roles.values():
        if not isinstance(record, dict) or record.get("deployment_status") != "live_stack":
            continue
        serving = record.get("serving") or {}
        launch = serving.get("launch") or {}
        role_slots = _slots(serving.get("slots"))

        covered: set[int] = set()
        by_port = ((launch.get("runtime") or {}).get("cache") or {}).get("slots_by_port") or {}
        for raw_port, raw_slots in by_port.items():
            port, slots = _slots(raw_port), _slots(raw_slots)
            if port is None or slots is None:
                continue
            covered.add(port)
            _bump(f"http://localhost:{port}", slots)

        for entry in launch.get("entries") or []:
            port = _slots((entry or {}).get("port"))
            if port is None or port in covered:
                continue
            slots = _slots(entry.get("slots")) or role_slots
            if slots is None:
                continue
            covered.add(port)
            _bump(f"http://localhost:{port}", slots)

        if role_slots is None:
            continue
        for raw_port in serving.get("ports") or []:
            port = _slots(raw_port)
            if port is not None and port not in covered:
                _bump(f"http://localhost:{port}", role_slots)
        endpoint = serving.get("endpoint")
        if isinstance(endpoint, str):
            _bump(endpoint, limits.get(endpoint, role_slots))

    return limits


class TestAdmissionController:
    """Tests for thread-safe admission control."""

    def test_unknown_backend_always_admitted(self):
        ctrl = AdmissionController({"http://localhost:8080": 1})
        assert ctrl.try_acquire("http://unknown:9999") is True

    def test_acquire_within_limit(self):
        ctrl = AdmissionController({"http://localhost:8080": 2})
        assert ctrl.try_acquire("http://localhost:8080") is True
        assert ctrl.try_acquire("http://localhost:8080") is True

    def test_acquire_beyond_limit_rejected(self):
        ctrl = AdmissionController({"http://localhost:8083": 1})
        assert ctrl.try_acquire("http://localhost:8083") is True
        # Second acquire should be rejected (limit=1)
        assert ctrl.try_acquire("http://localhost:8083") is False

    def test_release_allows_new_acquire(self):
        ctrl = AdmissionController({"http://localhost:8083": 1})
        assert ctrl.try_acquire("http://localhost:8083") is True
        assert ctrl.try_acquire("http://localhost:8083") is False
        ctrl.release("http://localhost:8083")
        assert ctrl.try_acquire("http://localhost:8083") is True

    def test_status_shows_in_flight(self):
        ctrl = AdmissionController({"http://localhost:8084": 2})
        ctrl.try_acquire("http://localhost:8084")
        status = ctrl.get_status()
        assert status["http://localhost:8084"]["limit"] == 2
        assert status["http://localhost:8084"]["in_flight"] == 1
        assert status["http://localhost:8084"]["available"] == 1

    def test_from_defaults_creates_controller(self):
        """`from_defaults()` must reproduce the per-port `-np` of the live fleet.

        The expectation is DERIVED from orchestration/derived/stack_priors.yaml —
        the same file `_limits_from_stack_priors` reads — rather than restated as
        literals. The port table legitimately moves with the fleet (2026-07-30
        quarter retirement, 2026-08-02 per-entry `slots`, W1 folding
        vision_escalation onto worker_vision's :8086), and a hard-coded table
        starts asserting a fleet that no longer exists. What must NOT move is the
        contract in src/api/admission.py's own header — "admission limits aligned
        with llama-server slot counts (no idle slots)" — i.e. limit == the `-np`
        the launcher passes for that exact port.
        """
        expected = _expected_priors_limits()
        assert expected, "stack priors declared no live serving ports"

        ctrl = AdmissionController.from_defaults()
        status = ctrl.get_status()

        # Exact key set: this is what fails loudly if from_defaults() silently
        # falls back to the stack MANIFEST table, which carries ports the priors
        # do not (8102, 18070) and disagrees on slot counts.
        assert set(status) == set(expected)
        for url, slots in sorted(expected.items()):
            assert status[url]["limit"] == slots, url

        # Negative pins, both derived: a URL nobody declares must not appear.
        assert "http://localhost:8084" not in expected
        assert "http://localhost:8084" not in status
        # :8087 was vision_escalation's own port before W1 aliased the role onto
        # worker_vision's :8086; it must stay retired, not resurrected.
        assert "http://localhost:8087" not in expected
        assert "http://localhost:8087" not in status

    def test_from_defaults_refreshes_live_loaded_limits(self, monkeypatch):
        monkeypatch.setattr(
            "src.api.admission._load_default_limits",
            lambda path=None: {"http://localhost:9000": 4},
        )

        ctrl = AdmissionController.from_defaults()
        status = ctrl.get_status()
        assert status == {
            "http://localhost:9000": {
                "limit": 4,
                "available": 4,
                "in_flight": 0,
                "waiting_interactive": 0,
                "waiting_background": 0,
            }
        }

    def test_constructor_refreshes_default_limits_when_unspecified(self, monkeypatch):
        monkeypatch.setattr(
            "src.api.admission._load_default_limits",
            lambda path=None: {"http://localhost:9001": 3},
        )

        ctrl = AdmissionController()

        assert ctrl.get_status()["http://localhost:9001"]["limit"] == 3

    def test_limits_from_stack_priors_includes_shared_replica_ports(self, tmp_path: Path):
        priors = tmp_path / "stack_priors.yaml"
        priors.write_text(
            yaml.safe_dump(
                {
                    "roles": {
                        "frontdoor": {
                            "deployment_status": "live_stack",
                            "serving": {
                                "endpoint": "http://localhost:8070",
                                "ports": [8070, 8080, 8180],
                                "slots": 2,
                            },
                        },
                        "coder_escalation": {
                            "deployment_status": "live_stack",
                            "serving": {
                                "endpoint": "http://localhost:8070",
                                "ports": [8070, 8080, 8180],
                                "slots": 1,
                            },
                        },
                        "retired": {
                            "deployment_status": "benchmark_or_candidate",
                            "serving": {
                                "endpoint": "http://localhost:8084",
                                "ports": [8084],
                                "slots": 1,
                            },
                        },
                    }
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        limits = _limits_from_stack_priors(priors)

        assert limits["http://localhost:8070"] == 2
        assert limits["http://localhost:8080"] == 2
        assert limits["http://localhost:8180"] == 2
        assert "http://localhost:8084" not in limits

    def test_load_default_limits_prefers_generated_limits(self, tmp_path: Path):
        priors = tmp_path / "stack_priors.yaml"
        priors.write_text(
            yaml.safe_dump(
                {
                    "roles": {
                        "frontdoor": {
                            "deployment_status": "live_stack",
                            "serving": {
                                "endpoint": "http://localhost:9000",
                                "ports": [9000, 9001],
                                "slots": 3,
                            },
                        }
                    }
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        limits = _load_default_limits(priors)

        assert limits == {
            "http://localhost:9000": 3,
            "http://localhost:9001": 3,
        }

    def test_load_default_limits_falls_back_when_generated_limits_empty(self, tmp_path: Path):
        priors = tmp_path / "stack_priors.yaml"
        priors.write_text(yaml.safe_dump({"roles": {}}), encoding="utf-8")

        assert _load_default_limits(priors) == FALLBACK_LIMITS

    def test_load_default_limits_falls_back_when_stack_priors_malformed(
        self,
        tmp_path: Path,
    ):
        priors = tmp_path / "stack_priors.yaml"
        priors.write_text("roles: [not, valid", encoding="utf-8")

        assert _load_default_limits(priors) == FALLBACK_LIMITS

    def test_manifest_fallback_derives_limits_and_skips_embedders(self, monkeypatch):
        from scripts.server import stack_manifest

        monkeypatch.setattr(
            stack_manifest,
            "HOT_SERVERS",
            [
                {"port": 9100, "roles": ["frontdoor"]},
                {"port": 9101, "roles": ["worker_fast"], "worker_pool": True, "worker_type": "fast"},
                {"port": 9102, "roles": ["worker_general"], "worker_pool": True},
                {"port": 9103, "roles": ["vision_escalation"], "vision": True, "vision_type": "escalation"},
                {"port": 9190, "roles": ["embedder"], "embedding": True},
            ],
        )
        monkeypatch.setattr(stack_manifest, "WARM_SERVERS", [])
        monkeypatch.setattr(stack_manifest, "SERIAL_ROLES", {"frontdoor"})

        assert _limits_from_stack_manifest() == {
            "http://localhost:9100": 1,
            "http://localhost:9101": 4,
            "http://localhost:9102": 1,
            "http://localhost:9103": 1,
        }

    def test_load_default_limits_recomputes_manifest_fallback(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        from scripts.server import stack_manifest

        priors = tmp_path / "stack_priors.yaml"
        priors.write_text(yaml.safe_dump({"roles": {}}), encoding="utf-8")
        monkeypatch.setattr(
            stack_manifest,
            "HOT_SERVERS",
            [{"port": 9200, "roles": ["new_live_role"]}],
        )
        monkeypatch.setattr(stack_manifest, "WARM_SERVERS", [])
        monkeypatch.setattr(stack_manifest, "SERIAL_ROLES", set())

        assert _load_default_limits(priors) == {"http://localhost:9200": 2}

    def test_thread_safety(self):
        """Concurrent acquire/release should not corrupt state."""
        ctrl = AdmissionController({"http://localhost:8080": 2})
        errors = []

        def worker():
            try:
                for _ in range(100):
                    if ctrl.try_acquire("http://localhost:8080"):
                        ctrl.release("http://localhost:8080")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        # All slots should be available after all threads complete
        status = ctrl.get_status()
        assert status["http://localhost:8080"]["in_flight"] == 0
