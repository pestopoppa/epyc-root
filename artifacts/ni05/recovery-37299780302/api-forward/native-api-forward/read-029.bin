from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts/server/affinity_preflight.py"
spec = importlib.util.spec_from_file_location("affinity_preflight", MODULE_PATH)
assert spec is not None and spec.loader is not None
affinity_preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(affinity_preflight)


def test_expected_nodes_for_quarter_cpu_sets() -> None:
    assert affinity_preflight._expected_nodes(affinity_preflight._parse_cpulist("0-23,96-119")) == {0}
    assert affinity_preflight._expected_nodes(affinity_preflight._parse_cpulist("24-47,120-143")) == {1}
    assert affinity_preflight._expected_nodes(affinity_preflight._parse_cpulist("48-71,144-167")) == {2}
    assert affinity_preflight._expected_nodes(affinity_preflight._parse_cpulist("72-95,168-191")) == {3}


def test_expected_nodes_for_node_and_full_cpu_sets() -> None:
    assert affinity_preflight._expected_nodes(affinity_preflight._parse_cpulist("0-47,96-143")) == {0, 1}
    assert affinity_preflight._expected_nodes(affinity_preflight._parse_cpulist("48-95,144-191")) == {2, 3}
    assert affinity_preflight._expected_nodes(affinity_preflight._parse_cpulist("0-95")) == {0, 1, 2, 3}


def test_pages_by_node_from_line() -> None:
    line = "abc default file=/models/model.gguf mapped=30 N0=10 N1=20 kernelpagesize_kB=4"
    assert affinity_preflight._pages_by_node_from_line(line) == {0: 10, 1: 20}


def test_fmt_nodes() -> None:
    assert affinity_preflight._fmt_nodes({2, 0}) == "N0,N2"
    assert affinity_preflight._fmt_nodes(set()) == "(none)"


def test_summarize_mmap_gguf_pages_is_observational() -> None:
    summary = affinity_preflight._summarize_numa_maps(
        [
            "abc default file=/models/model.gguf mapped=100 N0=25 N1=25 N2=25 N3=25",
            "def default anon=10 dirty=10 N0=10",
        ],
        no_mmap=False,
        expected_nodes={0},
        threshold=0.85,
    )

    assert summary["required"] is False
    assert summary["match"] is None
    assert summary["signal_kind"] == "mmap_gguf_pages"
    assert summary["local_fraction"] == 0.25
    assert summary["model_files"] == ["/models/model.gguf"]


def test_summarize_no_mmap_single_node_requires_locality() -> None:
    summary = affinity_preflight._summarize_numa_maps(
        [
            "abc default anon=100 dirty=100 N0=25 N1=25 N2=25 N3=25",
            "def default anon=10 dirty=10 N0=10",
        ],
        no_mmap=True,
        expected_nodes={0},
        threshold=0.85,
    )

    assert summary["required"] is True
    assert summary["match"] is False
    assert summary["signal_kind"] == "anon_pages"
    assert summary["local_fraction"] == 35 / 110
