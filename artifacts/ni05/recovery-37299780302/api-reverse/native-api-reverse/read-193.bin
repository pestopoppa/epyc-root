from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import yaml

from scripts.server import contention_matrix as matrix_tool
from src.scheduling.contention import topology_fingerprint


def _config() -> dict:
    return {
        "frontdoor": {
            "instances": [
                ("0-47,96-143", 8070, 96),
                ("0-23,96-119", 8080, 48),
                ("24-47,120-143", 8180, 48),
                ("48-71,144-167", 8280, 48),
                ("72-95,168-191", 8380, 48),
            ]
        },
        "worker_general": {
            "instances": [
                ("0-95", 8072, 96),
                ("0-23,96-119", 8082, 48),
                ("24-47,120-143", 8182, 48),
                ("48-71,144-167", 8282, 48),
                ("72-95,168-191", 8382, 48),
            ]
        },
        "eval_batch_frontdoor": {
            "instances": [("0-47,96-143", 18070, 96)]
        },
        "ingest_long_context": {
            "instances": [
                ("0-47,96-143", 8085, 96),
                ("0-23,96-119", 8185, 48),
                ("24-47,120-143", 8285, 48),
                ("48-71,144-167", 8385, 48),
                ("72-95,168-191", 8485, 48),
            ]
        },
    }


def test_pair_enumeration_excludes_eval_batch_auxiliary_role() -> None:
    pairs = matrix_tool._enumerate_full_pairs(_config())

    assert ("frontdoor", "worker_general") in pairs
    assert all("eval_batch_frontdoor" not in pair for pair in pairs)


def test_live_pair_selection_uses_healthy_quarters_when_primary_ports_are_down(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        matrix_tool,
        "_port_healthy",
        lambda port, timeout_s=0.5: int(port) in {8080, 8282},
    )

    frontdoor, worker, reason = matrix_tool._select_live_pair_instances(
        _config(),
        "frontdoor",
        "worker_general",
    )

    assert reason is None
    assert frontdoor is not None and frontdoor["port"] == 8080
    assert frontdoor["label"] == "q0"
    assert worker is not None and worker["port"] == 8282
    assert worker["label"] == "q2"


def test_live_pair_selection_reports_missing_role_instead_of_zero_measurement(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        matrix_tool,
        "_port_healthy",
        lambda port, timeout_s=0.5: int(port) == 8080,
    )

    frontdoor, worker, reason = matrix_tool._select_live_pair_instances(
        _config(),
        "frontdoor",
        "worker_general",
    )

    assert frontdoor is None
    assert worker is None
    assert reason == "missing_live_instance:worker_general"


def test_live_pair_selection_uses_secondary_live_ports_for_nonquarterable_role(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        matrix_tool,
        "_port_healthy",
        lambda port, timeout_s=0.5: int(port) in {8185, 8380},
    )

    frontdoor, ingest, reason = matrix_tool._select_live_pair_instances(
        _config(),
        "frontdoor",
        "ingest_long_context",
    )

    assert reason is None
    assert frontdoor is not None and frontdoor["port"] == 8380
    assert frontdoor["label"] == "q3"
    assert ingest is not None and ingest["port"] == 8185
    assert ingest["label"] == "q0"


def test_cmd_run_writes_live_instance_geometry_and_excludes_auxiliary_hash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg = _config()
    output = tmp_path / "matrix.yaml"
    monkeypatch.setattr("stack_numa.NUMA_CONFIG", cfg)
    monkeypatch.setattr(
        matrix_tool,
        "_port_healthy",
        lambda port, timeout_s=0.5: int(port) in {8080, 8282},
    )

    def fake_bench_pair(
        role_a,
        port_a,
        role_b,
        port_b,
        *,
        instance_a=None,
        instance_b=None,
    ):
        return matrix_tool.PairBench(
            roles=tuple(sorted([role_a, role_b])),
            instance_a=instance_a or {"port": port_a},
            instance_b=instance_b or {"port": port_b},
            solo_a=matrix_tool.BenchResult(port=port_a, role=role_a, tps=10, elapsed_s=10),
            solo_b=matrix_tool.BenchResult(port=port_b, role=role_b, tps=10, elapsed_s=10),
            parallel_a=matrix_tool.BenchResult(port=port_a, role=role_a, tps=10, elapsed_s=6),
            parallel_b=matrix_tool.BenchResult(port=port_b, role=role_b, tps=10, elapsed_s=6),
            seq_aggregate_tps=10,
            parallel_aggregate_tps=16.67,
            ratio=1.667,
        )

    monkeypatch.setattr(matrix_tool, "_bench_pair", fake_bench_pair)
    monkeypatch.setattr(matrix_tool, "_binary_metadata", lambda _path: {"git_commit": "test"})
    monkeypatch.setattr(matrix_tool, "_host_metadata", lambda: {"hostname": "test"})

    rc = matrix_tool.cmd_run(
        SimpleNamespace(roles=["frontdoor", "worker_general"], dry_run=False, output=str(output))
    )

    assert rc == 0
    data = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert data["topology_hash"] == topology_fingerprint(
        {
            "frontdoor": cfg["frontdoor"],
            "worker_general": cfg["worker_general"],
        }
    )
    assert data["topology_hash"] != topology_fingerprint(cfg)
    assert data["pairs"][0]["instance_a"]["port"] == 8080
    assert data["pairs"][0]["instance_a"]["label"] == "q0"
    assert data["pairs"][0]["instance_b"]["port"] == 8282
    assert data["pairs"][0]["instance_b"]["label"] == "q2"


def test_cmd_run_refuses_to_write_zero_throughput_matrix(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg = _config()
    output = tmp_path / "matrix.yaml"
    monkeypatch.setattr("stack_numa.NUMA_CONFIG", cfg)
    monkeypatch.setattr(
        matrix_tool,
        "_port_healthy",
        lambda port, timeout_s=0.5: int(port) in {8080, 8282},
    )

    def zero_bench_pair(
        role_a,
        port_a,
        role_b,
        port_b,
        *,
        instance_a=None,
        instance_b=None,
    ):
        return matrix_tool.PairBench(
            roles=tuple(sorted([role_a, role_b])),
            instance_a=instance_a or {"port": port_a},
            instance_b=instance_b or {"port": port_b},
            solo_a=matrix_tool.BenchResult(port=port_a, role=role_a, tps=0, elapsed_s=0),
            solo_b=matrix_tool.BenchResult(port=port_b, role=role_b, tps=0, elapsed_s=0),
            parallel_a=matrix_tool.BenchResult(port=port_a, role=role_a, tps=0, elapsed_s=0),
            parallel_b=matrix_tool.BenchResult(port=port_b, role=role_b, tps=0, elapsed_s=0),
            seq_aggregate_tps=0,
            parallel_aggregate_tps=0,
            ratio=0,
        )

    monkeypatch.setattr(matrix_tool, "_bench_pair", zero_bench_pair)

    rc = matrix_tool.cmd_run(
        SimpleNamespace(roles=["frontdoor", "worker_general"], dry_run=False, output=str(output))
    )

    assert rc == 2
    assert not output.exists()


def test_cmd_run_refuses_overlap_substituted_pairs_as_unknown(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """The overlapping fallback (no disjoint live placement exists) must NOT be
    recorded as a measured pair row.

    Regression for the APPEND 2026-08-12 inverted-marker-polarity defect: the
    marker fired on the honest overlap fallback while substituted rows entered
    the matrix unmarked, so an overlapping-geometry number could be read by the
    role-keyed gate as the pair's (disjoint-geometry) verdict — the class of
    the shipped frontdoor+ingest 1.89 row. The safest fix is to REFUSE the
    substituted overlapping pair into `unknown_pairs`, where the gate's
    unknown-pair policy (fail-closed for background) applies.
    """
    cfg = {
        # A full-only role can never be disjoint from a half: every pair it
        # forms falls back to the overlap substitution.
        "full_only": {"instances": [("0-95", 8070, 96)]},
        "halves_b": {
            "instances": [
                ("0-95", 8072, 96),
                ("0-47,96-143", 8082, 48),
                ("48-95,144-191", 8182, 48),
            ]
        },
        "halves_c": {
            "instances": [
                ("0-95", 8073, 96),
                ("0-47,96-143", 8083, 48),
                ("48-95,144-191", 8183, 48),
            ]
        },
    }
    output = tmp_path / "matrix.yaml"
    monkeypatch.setattr("stack_numa.NUMA_CONFIG", cfg)
    monkeypatch.setattr(
        matrix_tool,
        "_port_healthy",
        lambda port, timeout_s=0.5: int(port) in {8070, 8082, 8183},
    )

    def fake_bench_pair(
        role_a,
        port_a,
        role_b,
        port_b,
        *,
        instance_a=None,
        instance_b=None,
    ):
        return matrix_tool.PairBench(
            roles=tuple(sorted([role_a, role_b])),
            instance_a=instance_a or {"port": port_a},
            instance_b=instance_b or {"port": port_b},
            solo_a=matrix_tool.BenchResult(port=port_a, role=role_a, tps=10, elapsed_s=10),
            solo_b=matrix_tool.BenchResult(port=port_b, role=role_b, tps=10, elapsed_s=10),
            parallel_a=matrix_tool.BenchResult(port=port_a, role=role_a, tps=10, elapsed_s=6),
            parallel_b=matrix_tool.BenchResult(port=port_b, role=role_b, tps=10, elapsed_s=6),
            seq_aggregate_tps=10,
            parallel_aggregate_tps=16.67,
            ratio=1.667,
        )

    monkeypatch.setattr(matrix_tool, "_bench_pair", fake_bench_pair)
    monkeypatch.setattr(matrix_tool, "_binary_metadata", lambda _path: {"git_commit": "test"})
    monkeypatch.setattr(matrix_tool, "_host_metadata", lambda: {"hostname": "test"})

    rc = matrix_tool.cmd_run(
        SimpleNamespace(
            roles=["full_only", "halves_b", "halves_c"],
            dry_run=False,
            output=str(output),
        )
    )

    assert rc == 0
    data = yaml.safe_load(output.read_text(encoding="utf-8"))
    # The only recordable pair is the disjoint halves_b + halves_c one; neither
    # full_only pair may enter `pairs` in any form.
    assert len(data["pairs"]) == 1
    assert tuple(sorted(data["pairs"][0]["roles"])) == ("halves_b", "halves_c")
    # Both overlap substitutions were refused into unknown_pairs with an
    # explicit reason, so the gate's unknown-pair policy applies to them.
    assert len(data["unknown_pairs"]) == 2
    assert {tuple(sorted(e["roles"])) for e in data["unknown_pairs"]} == {
        ("full_only", "halves_b"),
        ("full_only", "halves_c"),
    }
    assert all("overlap_substituted" in e["reason"] for e in data["unknown_pairs"])


def test_cmd_run_dry_run_reports_overlap_refusal_without_writing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A dry run must say what a real run would do: the overlap substitution is
    REFUSED, not promised as a measurement — a dry run that lies about the run
    it previews is the exact trap that produced the 2026-08-12 dry-run finding.
    """
    cfg = {
        "full_only": {"instances": [("0-95", 8070, 96)]},
        "halves_b": {
            "instances": [
                ("0-95", 8072, 96),
                ("0-47,96-143", 8082, 48),
                ("48-95,144-191", 8182, 48),
            ]
        },
    }
    output = tmp_path / "matrix.yaml"
    monkeypatch.setattr("stack_numa.NUMA_CONFIG", cfg)
    monkeypatch.setattr(
        matrix_tool,
        "_port_healthy",
        lambda port, timeout_s=0.5: int(port) in {8070, 8082},
    )

    rc = matrix_tool.cmd_run(
        SimpleNamespace(roles=["full_only", "halves_b"], dry_run=True, output=str(output))
    )

    assert rc == 0
    assert not output.exists()


def test_cmd_run_scoped_roles_preserves_unmeasured_pairs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """`--roles` must UPDATE the measured rows, never TRUNCATE the matrix.

    Regression for the APPEND 2026-08-12 handoff finding: `pairs` is
    emitter-owned, so a role-scoped run previously emitted only the measured
    subset (3 pairs in, 1 out; against the default output that destroyed 14 of
    15 rows). The emitted file must keep every existing pair / unknown-pair
    entry whose role pair was NOT measured, verbatim — and stay stamped
    decision_grade=false because a scoped run is not a full re-measurement.
    """
    cfg = _config()
    output = tmp_path / "matrix.yaml"
    output.write_text(
        """version: 1
measured_at: "2026-08-01T00:00:00Z"
host: "old"
topology_hash: "OLD"
default_floor: 0.85

pairs:
  - roles: ['frontdoor', 'ingest_long_context']
    instance_a: {"cpu_list": "0-47,96-143", "instance_idx": 1, "label": "half0", "port": 8080, "regions": ["q0", "q1"], "role": "frontdoor", "threads": 48}
    instance_b: {"cpu_list": "48-95,144-191", "instance_idx": 2, "label": "half1", "port": 8285, "regions": ["q2", "q3"], "role": "ingest_long_context", "threads": 48}
    seq_aggregate_tps: 20.2
    parallel_aggregate_tps: 38.26
    ratio: 1.89
    samples: 1
    verdict: "allow"

unknown_pairs:
  - roles: ['worker_general', 'ingest_long_context']
    reason: "skipped_due_to_pair_frontdoor"

nway_light_roles: ["frontdoor"]
"""
    )
    monkeypatch.setattr("stack_numa.NUMA_CONFIG", cfg)
    monkeypatch.setattr(
        matrix_tool,
        "_port_healthy",
        lambda port, timeout_s=0.5: int(port) in {8080, 8282},
    )

    def fake_bench_pair(
        role_a,
        port_a,
        role_b,
        port_b,
        *,
        instance_a=None,
        instance_b=None,
    ):
        return matrix_tool.PairBench(
            roles=tuple(sorted([role_a, role_b])),
            instance_a=instance_a or {"port": port_a},
            instance_b=instance_b or {"port": port_b},
            solo_a=matrix_tool.BenchResult(port=port_a, role=role_a, tps=10, elapsed_s=10),
            solo_b=matrix_tool.BenchResult(port=port_b, role=role_b, tps=10, elapsed_s=10),
            parallel_a=matrix_tool.BenchResult(port=port_a, role=role_a, tps=10, elapsed_s=6),
            parallel_b=matrix_tool.BenchResult(port=port_b, role=role_b, tps=10, elapsed_s=6),
            seq_aggregate_tps=10,
            parallel_aggregate_tps=16.67,
            ratio=1.667,
        )

    monkeypatch.setattr(matrix_tool, "_bench_pair", fake_bench_pair)
    monkeypatch.setattr(matrix_tool, "_binary_metadata", lambda _path: {"git_commit": "test"})
    monkeypatch.setattr(matrix_tool, "_host_metadata", lambda: {"hostname": "test"})

    rc = matrix_tool.cmd_run(
        SimpleNamespace(roles=["frontdoor", "worker_general"], dry_run=False, output=str(output))
    )

    assert rc == 0
    data = yaml.safe_load(output.read_text(encoding="utf-8"))
    # The measured pair is refreshed...
    measured_row = next(
        r for r in data["pairs"] if tuple(sorted(r["roles"])) == ("frontdoor", "worker_general")
    )
    assert measured_row["instance_a"]["port"] == 8080
    assert measured_row["instance_b"]["port"] == 8282
    assert measured_row["ratio"] == 1.67
    # ...and the unmeasured pair survives VERBATIM instead of being truncated.
    preserved_row = next(
        r
        for r in data["pairs"]
        if tuple(sorted(r["roles"])) == ("frontdoor", "ingest_long_context")
    )
    assert preserved_row["ratio"] == 1.89
    assert preserved_row["verdict"] == "allow"
    assert preserved_row["instance_b"]["port"] == 8285
    # Unmeasured unknown-pair entries and hand-authored policy survive too.
    assert any(
        tuple(sorted(e["roles"])) == ("ingest_long_context", "worker_general")
        for e in data["unknown_pairs"]
    )
    assert data["nway_light_roles"] == ["frontdoor"]
    # A scoped run demotes: it is not decision-grade.
    assert data["decision_grade"] is False
