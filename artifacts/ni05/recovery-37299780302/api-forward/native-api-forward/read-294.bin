"""UFH-12 Phase 0 (REPL-EMB-0.1): declared embedder placement.

Origin: on 2026-09-26 /proc showed all six BGE embedders (:8090-:8095) binding
their 4 OMP compute threads to the SAME core places 0/96 32/128 48/144 88/184,
because the pool had no placement (`no_numa: true`, empty spawn prefix) and the
canonical OMP env (spread + cores) then chose identical places in every process.
These tests pin the declaration, its import-time invariants, and the launcher
path that honours it.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from scripts.server import orchestrator_stack as oss
from scripts.server import stack_manifest as sm
from scripts.server.stack_numa import GPU_HOST_LANE, _nodes_touched, _parse_cpus


def _fold(spec: str) -> set[int]:
    return {c % 96 for c in _parse_cpus(spec)}


# ── the live declaration ────────────────────────────────────────────────────


def test_every_pool_port_has_a_declared_placement() -> None:
    assert set(sm.EMBEDDER_PORTS) <= set(sm.EMBEDDING_PLACEMENT)


def test_declared_cpusets_are_disjoint_after_smt_folding() -> None:
    ports = sorted(sm.EMBEDDING_PLACEMENT)
    for i, a in enumerate(ports):
        for b in ports[i + 1:]:
            assert not (
                _fold(sm.EMBEDDING_PLACEMENT[a].cpuset) & _fold(sm.EMBEDDING_PLACEMENT[b].cpuset)
            ), (a, b)


def test_each_placement_is_one_node_and_matches_recipe_threads() -> None:
    for port, placement in sm.EMBEDDING_PLACEMENT.items():
        assert _nodes_touched(placement.cpuset) == [placement.numa_node]
        assert len(_parse_cpus(placement.cpuset)) == sm.EMBEDDING_SERVER_RECIPES[port]["threads"]


def test_placement_stays_off_speech_cores_and_gpu_host_lane() -> None:
    fenced = _fold(GPU_HOST_LANE[0])
    for svc in sm.AUX_SERVICES.values():
        if svc.cpuset:
            fenced |= _fold(svc.cpuset)
    for port, placement in sm.EMBEDDING_PLACEMENT.items():
        assert not (_fold(placement.cpuset) & fenced), port


def test_pool_recipe_gives_each_slot_the_full_bge_window() -> None:
    for port in sm.EMBEDDER_PORTS:
        recipe = sm.EMBEDDING_SERVER_RECIPES[port]
        assert recipe["context_tokens"] // recipe["slots"] >= 512, port


# ── the validator refuses each defect class ─────────────────────────────────


def _recipes(**threads_by_port: int) -> dict[int, dict]:
    return {int(p[1:]): {"threads": t} for p, t in threads_by_port.items()}


def _load(declared, *, recipes, pool_ports, aux=None):
    return sm._load_embedding_placement(
        declared, recipes=recipes, pool_ports=pool_ports, aux_services=aux or {}
    )


def test_validator_accepts_a_clean_declaration() -> None:
    out = _load(
        {1: {"cpuset": "136-139"}, 2: {"cpuset": "144-147"}},
        recipes=_recipes(p1=4, p2=4),
        pool_ports=[1, 2],
    )
    assert out[1].numa_node == 1 and out[2].numa_node == 2


@pytest.mark.parametrize(
    ("declared", "threads", "needle"),
    [
        ({1: {"cpuset": "136-139"}}, {"p1": 4, "p2": 4}, "without a declared placement"),
        (
            {1: {"cpuset": "40-43"}, 2: {"cpuset": "136-139"}},
            {"p1": 4, "p2": 4},
            "share physical cores",
        ),
        ({1: {"cpuset": "44-51"}, 2: {"cpuset": "136-139"}}, {"p1": 8, "p2": 4}, "spans NPS4 nodes"),
        ({1: {"cpuset": "136-139"}, 2: {"cpuset": "144-147"}}, {"p1": 8, "p2": 4}, "recipe -t 8"),
        ({1: {"cpuset": "184-187"}, 2: {"cpuset": "144-147"}}, {"p1": 4, "p2": 4}, "GPU host lane"),
        ({1: {"cpuset": "0-3,x"}, 2: {"cpuset": "144-147"}}, {"p1": 4, "p2": 4}, "not a cpu list"),
    ],
)
def test_validator_refuses(declared, threads, needle) -> None:
    with pytest.raises(ValueError, match=needle):
        _load(declared, recipes=_recipes(**threads), pool_ports=[1, 2])


def test_validator_refuses_a_speech_core_sibling() -> None:
    aux = {"whisper": SimpleNamespace(cpuset="0-23")}
    with pytest.raises(ValueError, match="aux whisper"):
        _load({1: {"cpuset": "96-99"}}, recipes=_recipes(p1=4), pool_ports=[1], aux=aux)


# ── the launcher honours it ─────────────────────────────────────────────────


def test_pool_command_carries_the_new_context_and_no_mmap() -> None:
    cmd = oss._build_embedding_command(port=8090)
    assert cmd[cmd.index("-c") + 1] == "2048"
    assert cmd[cmd.index("-np") + 1] == "4"
    assert "--no-mmap" in cmd


def test_warm_candidate_command_is_unchanged_by_the_pool_recipe() -> None:
    cmd = oss._build_embedding_command(port=8096)
    assert "--no-mmap" not in cmd
    assert cmd[cmd.index("-c") + 1] == "32768"


def test_embedding_spawn_prefix_is_membind_plus_exact_taskset() -> None:
    placement = sm.EmbedderPlacement(cpuset="144-147", numa_node=2)
    with patch.object(oss, "enforce_placement", return_value=None):
        prefix = oss._embedding_spawn_prefix(8092, placement, bench_force=False)
    assert prefix == ["numactl", "--membind=2", "--", "taskset", "-c", "144-147"]


def test_embedding_spawn_prefix_refuses_a_re_pin() -> None:
    placement = sm.EmbedderPlacement(cpuset="144-147", numa_node=2)
    with patch.object(oss, "enforce_placement", return_value="100-103"):
        assert oss._embedding_spawn_prefix(8092, placement, bench_force=False) is None


def test_start_server_launches_a_pool_embedder_on_its_declared_cpuset(
    tmp_path, monkeypatch
) -> None:
    fake_proc = SimpleNamespace(pid=4345)
    monkeypatch.setattr(oss, "LOG_DIR", tmp_path)
    monkeypatch.setattr(oss, "_write_llama_marker", lambda *a, **kw: None)
    monkeypatch.setattr(oss, "wait_for_health", lambda *a, **kw: True)
    monkeypatch.setattr(oss, "build_launch_env", lambda *a, **kw: {})
    with (
        patch.object(oss, "enforce_placement", return_value=None),
        patch.object(oss, "_bench_guarded_numa_prefix") as generic,
        patch.object(oss.subprocess, "Popen", return_value=fake_proc) as popen,
    ):
        info = oss.start_server(
            port=8093,
            roles=["embedder_3"],
            registry=SimpleNamespace(),
            embedding_mode=True,
        )
    assert info is not None
    argv = popen.call_args.args[0]
    assert argv[:6] == ["numactl", "--membind=2", "--", "taskset", "-c", "148-151"]
    assert argv[6].endswith("llama-server")
    generic.assert_not_called()
