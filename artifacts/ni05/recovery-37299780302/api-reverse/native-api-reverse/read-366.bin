"""WP-12 fleet layer — one CAB per fleet: shared object, placement, locks.

Acceptance plan coverage (wp12-fleet-layer-design.md §6):
  * case 2 — worker_math N-wide lands on N disjoint busy sibling instances of
    the SHARED host fleet under REAL region-lock identity (fixes WP-10);
    mirror: the host role itself N-wide → N siblings, full idle
  * case 7 — mode-exclusivity policies (full_disabled / burst_prefer_split
    / solo_prefer_full) hold against the one-CAB-per-fleet object

House patterns: real NUMA_CONFIG topology + real registry server_mode + real
placement policies, mocked cross-process lock seam (src.runtime.cpu_region_lock),
stub/offline backends. No sockets, no inference, no processes.

Lineup-independence (2026-09-26): this file used to restate the fleets as
literals — a separate gemma ``worker`` server on :8072 hosting worker_general /
worker_math / toolrunner, plus a multi-instance ingest_long_context on :8085.
The operator-signed 2026-09-22 lineup cutover (orchestrator 860b0b2d) made
worker_general and ingest_long_context ALIASES (of frontdoor's :8070 fleet and
architect_general's :8083 GPU process respectively) and deleted their
NUMA_CONFIG entries, so collection died on ``KeyError: 'worker_general'``.
Every fleet fact below is now DERIVED: the host of worker_math is read from
``orchestration/model_registry.yaml`` server_mode, and its ports/regions from
NUMA_CONFIG, so the next lineup change moves the expectation with it.
"""

from __future__ import annotations

import contextlib
from contextlib import contextmanager
from pathlib import Path

import yaml

import src.fleet as fleet_mod
from src.llm_primitives.backend import BackendMixin

ROOT = Path(__file__).resolve().parents[2]

# The fleets below are dispatched against the REAL region-lock model
# (`_real_regions_model` -> `get_instance_regions()`), so their port sets must
# describe the same machine. When they did not — the literals here pinned a
# retired lineup — the extra ports resolved to NO topology index, picked up
# EMPTY region sets, and therefore could never conflict: dispatch handed out
# one instance twice and the test read that as a double-booking defect. Derive
# both from NUMA_CONFIG so fixture and lock model agree.


def _registry_server_mode() -> dict:
    return yaml.safe_load(
        (ROOT / "orchestration" / "model_registry.yaml").read_text(encoding="utf-8")
    )["server_mode"]


SERVER_MODE = _registry_server_mode()


def _host_fleet_of(role: str) -> str:
    """The server_mode row that physically hosts ``role`` (shared_with/alias_of)."""
    for host, row in SERVER_MODE.items():
        if row.get("alias_of"):
            continue
        if host == role or role in (row.get("shared_with") or []):
            return host
    raise AssertionError(f"registry declares no host fleet for {role!r}")


def _bound_roles(host: str) -> list[str]:
    """Roles the registry binds onto ``host``'s fleet, in declaration order."""
    row = SERVER_MODE[host]
    bound = [host] + list(row.get("shared_with") or [])
    bound += [k for k, v in SERVER_MODE.items() if v.get("alias_of") == host and k not in bound]
    # `worker` is a server_mode ROW name (canonicalized to worker_general by the
    # fleet builder), not a role with a backend of its own.
    return [r for r in bound if r != "worker"]


def _topology_ports(role: str) -> tuple[int, list[int]]:
    """(aligned-full port, sibling instance ports) for ``role``."""
    from scripts.server.stack_numa import NUMA_CONFIG

    cfg = NUMA_CONFIG[role]
    instances = cfg["instances"]
    full_idx = cfg["full_instance_idx"]
    return instances[full_idx][1], [
        inst[1] for idx, inst in enumerate(instances) if idx != full_idx
    ]


def _topology_idxs(role: str, ports: list[int]) -> list[int]:
    from src.runtime.instance_topology import topology_idx_for_port

    return [topology_idx_for_port(role, port) for port in ports]


def _regions_for(role: str, idxs: list[int]) -> set[str]:
    from src.runtime.instance_topology import get_instance_regions

    regions = get_instance_regions()
    out: set[str] = set()
    for idx in idxs:
        out |= set(regions[(role, idx)])
    return out


# worker_math (the EV-11c serialization-incident role) and its physical host.
WM = "worker_math"
HOST = _host_fleet_of(WM)
HOST_BOUND = _bound_roles(HOST)
HOST_FULL, HOST_SIBLINGS = _topology_ports(HOST)
HOST_SIB_IDXS = _topology_idxs(HOST, HOST_SIBLINGS)


def _write_priors(tmp_path: Path, ports_by_role: dict[str, list[int]]) -> Path:
    payload = {
        "roles": {
            role: {
                "deployment_status": "live_stack",
                "serving": {"ports": list(ports)},
            }
            for role, ports in ports_by_role.items()
        }
    }
    path = tmp_path / "stack_priors.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


def _fleet_state(tmp_path: Path, *, host_ports: list[int] = HOST_SIBLINGS):
    ports: dict[str, list[int]] = {role: host_ports for role in HOST_BOUND}
    # Every other physical fleet realized at its registry port, so the build
    # does not fall back to degraded literals for them.
    for key, row in SERVER_MODE.items():
        if key != HOST and not row.get("alias_of") and row.get("port"):
            ports.setdefault(key, [int(row["port"])])
    return fleet_mod.build_fleets_and_bindings(
        registry_server_mode=SERVER_MODE,
        priors_path=_write_priors(tmp_path, ports),
    )


class _Host(BackendMixin):
    def __init__(self, health_tracker=None):
        self._backends: dict = {}
        self.health_tracker = health_tracker


def _url_str(ports: list[int], full_port: int | None = None) -> str:
    urls = [f"http://localhost:{p}" for p in ports]
    if full_port is not None:
        urls.insert(0, f"full:http://localhost:{full_port}")
    return ",".join(urls)


def _default_urls() -> dict[str, str]:
    host = _url_str(HOST_SIBLINGS, full_port=HOST_FULL)
    urls = {role: host for role in HOST_BOUND}
    # Stale 2-endpoint copy — the EV-11c serialization incident class (ports of
    # the retired gemma worker quarters, which no longer resolve anywhere).
    urls[WM] = "http://localhost:8082,http://localhost:8182"
    return urls


def _build_host(monkeypatch, tmp_path, *, state=None, urls=None, tracker=None):
    st = state if state is not None else _fleet_state(tmp_path)
    monkeypatch.setattr(fleet_mod, "get_fleets_and_bindings", lambda: st)
    monkeypatch.setenv("ORCHESTRATOR_FLEET_LAYER", "1")
    host = _Host(tracker)
    server_urls = dict(urls if urls is not None else _default_urls())
    host._init_caching_backends(server_urls, num_slots=1)
    return host, server_urls, st


# ── Mock cross-process lock seam (house pattern: exact region mutex model) ──


class _RegionMutexModel:
    """Region-granular mutex model mirroring cpu_region_lock semantics:
    exact held-region truth + attribution-style holder view."""

    def __init__(self, regions_map):
        self.regions_map = dict(regions_map)
        self.owner: dict[str, tuple[str, int]] = {}
        self.acquired: list[tuple[str, int]] = []

    def holders(self):
        held_by_role: dict[str, set[str]] = {}
        for region, (role, _idx) in self.owner.items():
            held_by_role.setdefault(role, set()).add(region)
        out: dict[str, list[int]] = {}
        for (role, idx), regs in self.regions_map.items():
            if regs and regs & held_by_role.get(role, set()):
                out.setdefault(role, []).append(idx)
        return out

    def held_regions(self):
        acc: dict[str, set[str]] = {}
        for region, (role, _idx) in self.owner.items():
            acc.setdefault(role, set()).add(region)
        return {role: frozenset(regs) for role, regs in acc.items()}

    @contextmanager
    def lock(self, role, instance_idx, **_kw):
        from src.runtime.cpu_region_lock import CpuRegionLockTimeout

        regs = self.regions_map.get((role, instance_idx), frozenset())
        if any(r in self.owner for r in regs):
            raise CpuRegionLockTimeout(f"held: {role}/{instance_idx}")
        for r in regs:
            self.owner[r] = (role, instance_idx)
        self.acquired.append((role, instance_idx))
        try:
            yield [f"/tmp/mock.{role}.{r}.lock" for r in regs]
        finally:
            for r in regs:
                if self.owner.get(r) == (role, instance_idx):
                    del self.owner[r]


def _wire(monkeypatch, model: _RegionMutexModel) -> None:
    monkeypatch.setenv("ORCHESTRATOR_PER_REGION_LOCKS", "1")
    monkeypatch.setenv("ORCHESTRATOR_PLACEMENT_STATE_MACHINE", "1")
    monkeypatch.delenv("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", raising=False)
    monkeypatch.delenv("ORCHESTRATOR_SHAPE_AWARE_CONTENTION", raising=False)
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.cpu_region_lock_for_instance",
        lambda role, idx, **kw: model.lock(role, idx),
    )
    monkeypatch.setattr("src.runtime.cpu_region_lock.active_region_holders", model.holders)
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.held_regions_by_role",
        lambda *_a, **_k: model.held_regions(),
    )


def _real_regions_model() -> _RegionMutexModel:
    from src.runtime.instance_topology import get_instance_regions

    return _RegionMutexModel(get_instance_regions())


# ── Case 2 — one shared backend object per fleet ────────────────────────────


def test_case2_shared_roles_share_one_backend_object(monkeypatch, tmp_path):
    host, _urls, _st = _build_host(monkeypatch, tmp_path)

    # Non-vacuity: the host fleet must still carry the aliases this case exists
    # to protect (worker_math + at least one other co-hosted role).
    assert WM in HOST_BOUND and len(HOST_BOUND) >= 3, HOST_BOUND

    cab = host._backends[HOST]
    for role in HOST_BOUND:
        assert host._backends[role] is cab, role
    assert cab._role == HOST
    # Lock identity is the PHYSICAL fleet, never a phantom per-alias topology.
    assert cab._topology_role == HOST
    # Realized siblings-only: no full backend, siblings at TRUE topology idxs.
    assert cab._full is None  # aligned full port not realized in this state
    assert cab._quarter_topology_idx == HOST_SIB_IDXS


def test_case2_stale_role_copy_is_healed_by_fleet_truth(monkeypatch, tmp_path):
    """worker_math's stale 2-endpoint URL copy (the EV-11c serialization
    incident) is overridden by the realized fleet: the role's URL view and
    backend both become the fleet fact (§3 one-fact invariant at runtime)."""
    host, server_urls, st = _build_host(monkeypatch, tmp_path)
    fleets, _bindings = st
    assert server_urls[WM] == fleets[HOST].url_value
    assert server_urls[WM] == server_urls[HOST]
    assert host._backends[WM] is host._backends[HOST]


def test_case2_worker_math_n_wide_disjoint_siblings_real_locks(monkeypatch, tmp_path):
    """N concurrent requests through the shared host fleet (as worker_math
    dispatches them) land on N DISJOINT busy sibling instances, full idle, and
    every placement holds the REAL region-lock identity of the physical fleet
    (topology role = the host, never worker_math — WP-10)."""
    host, _urls, _st = _build_host(monkeypatch, tmp_path)
    cab = host._backends[WM]

    model = _real_regions_model()
    _wire(monkeypatch, model)

    width = len(HOST_SIBLINGS)
    assert width >= 2, "fixture can no longer express concurrent disjoint placement"

    chosen: list[tuple[int, bool]] = []
    with contextlib.ExitStack() as stack:
        for i in range(width):
            _backend, idx, is_full = stack.enter_context(
                cab._dispatch(session_id=f"wm{i}")
            )
            chosen.append((idx, is_full))

        # N disjoint busy siblings; the full (all-region) shape never placed.
        assert all(not is_full for _idx, is_full in chosen)
        idxs = [idx for idx, _ in chosen]
        # No double-booking: N concurrent requests occupy N DISTINCT slots.
        assert sorted(idxs) == list(range(width))
        # Real lock identity: every acquisition under the fleet's ONE
        # topology role, at the siblings' true topology idxs.
        assert {role for role, _ in model.acquired} == {HOST}
        assert sorted(idx for _, idx in model.acquired) == sorted(HOST_SIB_IDXS)
        # Every atomic region those instances cover is busy — physically
        # disjoint placements, no region held twice.
        assert set(model.owner) == _regions_for(HOST, HOST_SIB_IDXS)
    assert model.owner == {}


def test_case2_mirror_host_role_n_wide_siblings_full_idle(monkeypatch, tmp_path):
    host, _urls, _st = _build_host(monkeypatch, tmp_path)
    cab = host._backends[HOST]

    model = _real_regions_model()
    _wire(monkeypatch, model)

    width = len(HOST_SIBLINGS)
    assert width >= 2, "fixture can no longer express concurrent disjoint placement"
    with contextlib.ExitStack() as stack:
        chosen = [
            stack.enter_context(cab._dispatch(session_id=f"fd{i}"))[1:]
            for i in range(width)
        ]
        assert all(not is_full for _idx, is_full in chosen)
        assert sorted(idx for idx, _ in chosen) == list(range(width))
        assert {role for role, _ in model.acquired} == {HOST}
        assert sorted(idx for _, idx in model.acquired) == sorted(HOST_SIB_IDXS)
        # full idle: the all-region idx-0 lock is never acquired.
        assert 0 not in {idx for _, idx in model.acquired}


# ── Case 7 — mode-exclusivity policies against the fleet-level CAB ──────────


def test_case7_full_disabled_never_emits_full(monkeypatch, tmp_path):
    """FULL_DISABLED policy (synthetic — no live role carries it): even with a
    realized full endpoint, the fleet CAB never places the all-region full."""
    import scripts.server.stack_numa as _stack_numa

    monkeypatch.setitem(
        _stack_numa.NUMA_CONFIG[HOST], "placement_policy", "full_disabled"
    )
    state = _fleet_state(tmp_path, host_ports=[HOST_FULL] + HOST_SIBLINGS)
    host, _urls, _st = _build_host(monkeypatch, tmp_path, state=state)
    cab = host._backends[WM]
    assert cab._full is not None  # mixed-mode fleet: full realized
    assert cab._full_port == HOST_FULL

    model = _real_regions_model()
    _wire(monkeypatch, model)

    with cab._dispatch(session_id="solo") as (_backend, idx, is_full):
        assert not is_full
        assert model.acquired == [(HOST, cab._quarter_topology_idx[idx])]
        assert (HOST, 0) not in model.acquired


def test_case7_burst_prefer_split_full_first_solo_abandoned_under_load(
    monkeypatch, tmp_path
):
    """The host fleet (live policy burst_prefer_split): solo keeps full first
    for peak latency; the moment a self-role holder exists the full is
    abandoned and placement goes to a disjoint sibling."""
    from scripts.server.stack_numa import NUMA_CONFIG
    from src.runtime.instance_topology import get_instance_regions

    assert NUMA_CONFIG[HOST].get("placement_policy") == "burst_prefer_split", (
        f"{HOST} no longer carries burst_prefer_split — re-point this case at the "
        "role that does"
    )
    state = _fleet_state(tmp_path, host_ports=[HOST_FULL] + HOST_SIBLINGS)
    host, _urls, _st = _build_host(monkeypatch, tmp_path, state=state)
    cab = host._backends[HOST]
    assert cab._full is not None
    assert cab._full_port == HOST_FULL

    model = _real_regions_model()
    _wire(monkeypatch, model)

    # Solo: full first (single-request max throughput).
    with cab._dispatch(session_id="solo") as (_b, _idx, is_full):
        assert is_full
        assert model.acquired[-1] == (HOST, 0)
    assert model.owner == {}

    # A self-role sibling holder exists (one region of the LAST sibling busy)
    # → burst mode: full abandoned, placement lands on a sibling disjoint from
    # the holder.
    busy_region = sorted(get_instance_regions()[(HOST, HOST_SIB_IDXS[-1])])[-1]
    model.owner[busy_region] = (HOST, HOST_SIB_IDXS[-1])
    with cab._dispatch(session_id="burst") as (_b, idx, is_full):
        assert not is_full
        topo = cab._quarter_topology_idx[idx]
        assert topo != 0
        placed_regions = get_instance_regions()[(HOST, topo)]
        assert busy_region not in placed_regions


def test_case7_solo_prefer_full_keeps_full_at_concurrency_one(monkeypatch, tmp_path):
    """A fleet with NO placement_policy key → default solo_prefer_full:
    concurrency 1 places the full instance first. No live multi-instance fleet
    runs on the default today (ingest_long_context, which did, became a GPU
    alias at the 2026-09-22 cutover), so the host's override is removed to
    exercise the default-resolution path itself."""
    import scripts.server.stack_numa as _stack_numa

    monkeypatch.delitem(_stack_numa.NUMA_CONFIG[HOST], "placement_policy", raising=False)
    state = _fleet_state(tmp_path, host_ports=[HOST_FULL] + HOST_SIBLINGS)
    host, _urls, _st = _build_host(monkeypatch, tmp_path, state=state)
    cab = host._backends[HOST]
    assert cab._full is not None
    assert cab._full_port == HOST_FULL

    model = _real_regions_model()
    _wire(monkeypatch, model)

    with cab._dispatch(session_id="solo") as (_b, idx, is_full):
        assert is_full
        assert idx == -1
        assert model.acquired == [(HOST, 0)]


# ── Flag-off byte-identity of the builder path ──────────────────────────────


def test_flag_off_builds_legacy_per_role_backends(monkeypatch, tmp_path):
    """With ORCHESTRATOR_FLEET_LAYER unset the builder path is the legacy
    per-role build: independent backend objects per role, no URL rewrite."""
    monkeypatch.delenv("ORCHESTRATOR_FLEET_LAYER", raising=False)
    # A fleet-state accessor that would blow up if consulted proves the
    # fleet path is never entered flag-off.
    monkeypatch.setattr(
        fleet_mod,
        "get_fleets_and_bindings",
        lambda: (_ for _ in ()).throw(AssertionError("fleet path entered flag-off")),
    )
    host = _Host()
    urls = _default_urls()
    before = dict(urls)
    host._init_caching_backends(urls, num_slots=1)

    assert urls == before  # no fleet rewrite
    others = [r for r in HOST_BOUND if r not in (HOST, WM)]
    assert others, HOST_BOUND
    for role in others:
        # Same URL list as the host, yet an independent object flag-off.
        assert urls[role] == urls[HOST]
        assert host._backends[role] is not host._backends[HOST], role


def test_request_specific_urls_keep_legacy_build(monkeypatch, tmp_path):
    """Caller-supplied server_urls (request overrides, eval-batch splices) are
    authoritative: the fleet layer leaves every role on the legacy build."""
    state = _fleet_state(tmp_path)
    monkeypatch.setattr(fleet_mod, "get_fleets_and_bindings", lambda: state)
    monkeypatch.setenv("ORCHESTRATOR_FLEET_LAYER", "1")
    host = _Host()
    host.server_urls_source = "request"
    urls = _default_urls()
    before = dict(urls)
    host._init_caching_backends(urls, num_slots=1)
    assert urls == before
    assert host._backends[HOST] is not host._backends[WM]
