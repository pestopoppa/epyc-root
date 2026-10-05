"""SSU-F4: the shared_with recompute-and-diff checker.

Every test here reproduces a REAL error message from the 2026-09-22 lineup change
(session friction audit `artifacts/operator/session-friction-audit-20260922.md` §2,
§1 row 4). A checker that only passes on a clean tree proves nothing, so each defect
is injected into a fixture and the finding is asserted by message, line and expected
value -- and the clean baseline is asserted separately so a vacuous pass is visible.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.validate.check_shared_with_derivations import (  # noqa: E402
    SourceError,
    apply_fixes,
    check_all,
    derive,
    fleet_url,
    load_server_url_fallbacks,
    load_sources,
)


# ---------------------------------------------------------------------------
# a minimal but structurally faithful three-file stack
# ---------------------------------------------------------------------------

MASTER = {
    "server_mode": {
        "frontdoor": {
            "port": 8070,
            "url": "http://localhost:8070",
            "model": "Qwen3.6-35B-A3B-MTP-Q8_0.gguf",
            "model_path": "/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf",
            "model_role": "qwen36_35b_a3b_mtp_q8_local",
            "shared_with": ["worker_general", "worker_math", "toolrunner"],
            "numa_ports": [8080, 8180],
            "numa_instances": 2,
        },
        "architect_general": {
            "port": 8083,
            "model": "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf",
            "model_role": "qwen38_27b_q8_local",
            "shared_with": ["ingest_long_context"],
        },
        "ingest_long_context": {
            "port": 8083,
            "alias_of": "architect_general",
            "model": "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf",
            "model_role": "qwen38_27b_q8_local",
        },
    },
    "roles": {
        "frontdoor": {"model": {"name": "Qwen3.6-35B-A3B-MTP-Q8_0", "quant": "Q8_0"}},
        "worker_general": {"model": {"name": "Qwen3.6-35B-A3B-MTP-Q8_0", "quant": "Q8_0"}},
        "worker_math": {"model": {"name": "Qwen3.6-35B-A3B-MTP-Q8_0", "quant": "Q8_0"}},
        "toolrunner": {"model": {"name": "Qwen3.6-35B-A3B-MTP-Q8_0", "quant": "Q8_0"}},
        "ingest_long_context": {"model": {"name": "Qwen3.8-27B-Q8_0", "quant": "Q8_0"}},
    },
}

MANIFEST = {
    "port_map": {
        "frontdoor": 8070,
        "worker_general": 8070,
        "worker_math": 8070,
        "toolrunner": 8070,
        "architect_general": 8083,
        "ingest_long_context": 8083,
    },
    "role_launch_meta": {
        "frontdoor": {"tier": "hot", "mode": "default"},
        "architect_general": {"tier": "hot", "mode": "default"},
        "embedder": {"tier": "hot", "mode": "embedding", "no_numa": True, "port": 8090},
    },
}

TOPOLOGY = {
    "numa_mode": "both",
    "numa_config": {
        "frontdoor": {"instances": [["0-95", 8070]]},
        "architect_general": {"instances": [["0-23", 8083]], "gpu_host_lane": True},
    },
}


def _write(tmp_path: Path, master=None, manifest=None, topology=None) -> tuple[Path, Path, Path]:
    import copy

    m = copy.deepcopy(MASTER)
    lm = copy.deepcopy(MANIFEST)
    st = copy.deepcopy(TOPOLOGY)
    for mutate, target in ((master, m), (manifest, lm), (topology, st)):
        if mutate is not None:
            mutate(target)
    paths = []
    for name, data in (
        ("model_registry.yaml", m),
        ("launch_manifest.yaml", lm),
        ("stack_topology.yaml", st),
    ):
        p = tmp_path / name
        p.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        paths.append(p)
    return tuple(paths)  # type: ignore[return-value]


def _findings(tmp_path: Path, **mutations):
    master, manifest, topology = _write(tmp_path, **mutations)
    return check_all(load_sources(master, manifest, topology))


def _messages(findings) -> str:
    return "\n".join(f.message for f in findings)


# ---------------------------------------------------------------------------
# the baseline. Without this, every assertion below could be vacuous.
# ---------------------------------------------------------------------------


def test_clean_fixture_has_no_findings(tmp_path):
    assert _findings(tmp_path) == []


def test_derivation_reads_shared_with_not_alias_of(tmp_path):
    master, manifest, topology = _write(tmp_path)
    d = derive(load_sources(master, manifest, topology))
    assert d.alias_to_host == {
        "worker_general": "frontdoor",
        "worker_math": "frontdoor",
        "toolrunner": "frontdoor",
        "ingest_long_context": "architect_general",
    }
    assert d.hosts == {"frontdoor", "architect_general"}


# ---------------------------------------------------------------------------
# 2026-09-22 failure 1: port_map restated the OLD host's port
# ---------------------------------------------------------------------------


def test_port_map_restating_the_old_host_port(tmp_path):
    findings = _findings(
        tmp_path, manifest=lambda m: m["port_map"].__setitem__("toolrunner", 8072)
    )
    assert len(findings) == 1
    f = findings[0]
    assert f.surface == "launch_manifest.port_map"
    assert f.role == "toolrunner"
    assert (
        f.message
        == "port for role 'toolrunner': launcher declares 8072, master "
        "(frontdoor/shared_with) declares 8070"
    )
    assert (f.found, f.expected) == ("8072", "8070")
    assert f.line is not None and f.fixable


def test_port_map_missing_alias_entry_is_found(tmp_path):
    findings = _findings(tmp_path, manifest=lambda m: m["port_map"].pop("worker_math"))
    assert [f.role for f in findings] == ["worker_math"]
    assert findings[0].expected == "worker_math: 8070"


# ---------------------------------------------------------------------------
# 2026-09-22 failure 2: an alias kept its role_launch_meta entry
# ---------------------------------------------------------------------------


def test_alias_keeping_role_launch_meta_reproduces_the_numa_message(tmp_path):
    findings = _findings(
        tmp_path,
        manifest=lambda m: m["role_launch_meta"].__setitem__(
            "worker_general", {"tier": "hot", "mode": "default"}
        ),
    )
    messages = _messages(findings)
    assert (
        "'worker_general' is an alias on 'frontdoor''s process" in messages
    ), messages
    assert (
        "ROLE_LAUNCH_META['worker_general'] has no_numa=False but no NUMA_CONFIG entry"
        in messages
    ), messages
    assert all(f.fixable for f in findings)


def test_host_without_role_launch_meta_is_found(tmp_path):
    findings = _findings(tmp_path, manifest=lambda m: m["role_launch_meta"].pop("frontdoor"))
    messages = _messages(findings)
    assert "hosts aliases" in messages and "no role_launch_meta entry" in messages


def test_declared_shared_with_first_n_is_a_restatement(tmp_path):
    findings = _findings(
        tmp_path,
        manifest=lambda m: m["role_launch_meta"]["frontdoor"].__setitem__(
            "shared_with_first_n", ["worker_general"]
        ),
    )
    assert "phase 2 DERIVES from server_mode.frontdoor.shared_with" in _messages(findings)


# ---------------------------------------------------------------------------
# 2026-09-22 failure 3: a phantom fleet -- alias_of without shared_with
# ---------------------------------------------------------------------------


def test_alias_of_absent_from_shared_with_is_the_root_cause(tmp_path):
    def mutate(master):
        master["server_mode"]["architect_general"]["shared_with"] = []
        master["server_mode"]["ingest_long_context"]["numa_ports"] = [8083]

    findings = _findings(tmp_path, master=mutate)
    messages = _messages(findings)
    assert (
        "role 'ingest_long_context' declares alias_of: architect_general but is absent "
        "from that host's shared_with" in messages
    ), messages
    assert (
        "role 'ingest_long_context' declares numa_ports=[8083] / numa_instances=None "
        "but the NUMA topology has NO entry for it" in messages
    ), messages
    assert "A fleet nothing launches is a phantom" in messages
    # the registry is the SOURCE; the checker reports, it does not rewrite
    assert not any(f.fixable for f in findings if f.file.endswith("model_registry.yaml"))


def test_alias_with_a_numa_config_entry_is_found(tmp_path):
    findings = _findings(
        tmp_path,
        topology=lambda t: t["numa_config"].__setitem__(
            "worker_general", {"instances": [["0-95", 8070]]}
        ),
    )
    assert [f.role for f in findings] == ["worker_general"]
    assert findings[0].surface == "stack_topology.numa_config"
    assert "must carry no NUMA wiring" in findings[0].message
    assert findings[0].fixable


# ---------------------------------------------------------------------------
# 2026-09-22 failure 4: roles.<alias>.model still named the old artifact
# ---------------------------------------------------------------------------


def test_stale_alias_model_reproduces_role_server_conflict(tmp_path):
    findings = _findings(
        tmp_path,
        master=lambda m: m["roles"]["worker_math"].__setitem__(
            "model", {"name": "Qwen2.5-Math-7B-Instruct", "quant": "Q4_K_M"}
        ),
    )
    assert len(findings) == 1
    f = findings[0]
    assert f.message.startswith(
        "Role-server conflict: role model metadata does not match the shared runtime "
        "server model"
    )
    assert f.found == "qwen2.5-math-7b-instruct"
    assert f.expected == "qwen3.6-35b-a3b-mtp-q8_0"
    assert not f.fixable


def test_alias_own_server_mode_row_restating_a_stale_artifact(tmp_path):
    def mutate(master):
        master["server_mode"]["ingest_long_context"]["model"] = (
            "/mnt/raid0/llm/models/Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf"
        )
        master["server_mode"]["ingest_long_context"]["model_role"] = "qwen3_next_80b_local"

    messages = _messages(_findings(tmp_path, master=mutate))
    assert "keeps its own server_mode.model, which restates" in messages
    assert "points model_role at a different catalogue row" in messages


def test_alias_own_port_restating_a_stale_host_port(tmp_path):
    findings = _findings(
        tmp_path,
        master=lambda m: m["server_mode"]["ingest_long_context"].__setitem__("port", 8085),
    )
    surfaces = {f.surface for f in findings}
    assert "master server_mode.<alias>.port" in surfaces


def test_host_model_mismatch_against_its_own_server_row(tmp_path):
    findings = _findings(
        tmp_path,
        master=lambda m: m["roles"]["frontdoor"].__setitem__(
            "model", {"name": "gemma-4-26B-A4B-it-ORIG", "quant": "Q4_K_M"}
        ),
    )
    assert any(f.surface == "master roles.<host>.model" for f in findings)


# ---------------------------------------------------------------------------
# --fix
# ---------------------------------------------------------------------------


def test_fix_converges_and_never_writes_the_registry(tmp_path):
    def mutate_manifest(m):
        m["port_map"]["toolrunner"] = 8072
        m["role_launch_meta"]["worker_general"] = {"tier": "hot", "mode": "default"}

    def mutate_topology(t):
        t["numa_config"]["worker_math"] = {"instances": [["0-95", 8070]]}

    def mutate_master(m):
        m["roles"]["worker_math"]["model"] = {"name": "Qwen2.5-Math-7B-Instruct"}

    master, manifest, topology = _write(
        tmp_path,
        master=mutate_master,
        manifest=mutate_manifest,
        topology=mutate_topology,
    )
    before = master.read_text(encoding="utf-8")

    sources = load_sources(master, manifest, topology)
    findings = check_all(sources)
    applied, skipped = apply_fixes(sources, findings)

    assert any("port_map.toolrunner" in line for line in applied)
    assert any("role_launch_meta.worker_general" in line for line in applied)
    assert any("numa_config.worker_math" in line for line in applied)
    # the registry finding is reported, never rewritten
    assert master.read_text(encoding="utf-8") == before
    assert [f.surface for f in skipped] == ["master roles.<alias>.model"]

    remaining = check_all(load_sources(master, manifest, topology))
    assert [f.surface for f in remaining] == ["master roles.<alias>.model"]


def test_fix_inserts_a_missing_port_map_entry(tmp_path):
    master, manifest, topology = _write(
        tmp_path, manifest=lambda m: m["port_map"].pop("toolrunner")
    )
    sources = load_sources(master, manifest, topology)
    apply_fixes(sources, check_all(sources))
    assert yaml.safe_load(manifest.read_text())["port_map"]["toolrunner"] == 8070
    assert check_all(load_sources(master, manifest, topology)) == []


# ---------------------------------------------------------------------------
# SIXTH SURFACE (SSU-F8): src/config/models.py::_LEGACY_SERVER_URL_FALLBACKS.
#
# The real 2026-09-22 defect, reproduced: the worker lane moved onto frontdoor's
# :8070 process and the last-resort URL table kept naming the retired :8072 fleet.
# `_server_url_default` ENDS in a bare subscript of that table, so the stale rows
# resolved three roles to a fleet with nothing listening in exactly the degraded
# mode the table exists to serve. It read correct only because live runtime facts
# win first. Five surfaces were wired into this checker and did not rot; this one
# was not wired and did.
# ---------------------------------------------------------------------------


FRONTDOOR_FLEET_URL = (
    "full:http://localhost:8070,http://localhost:8080,http://localhost:8180"
)
RETIRED_WORKER_FLEET_URL = (
    "full:http://localhost:8072,http://localhost:8082,http://localhost:8182"
)

# What a correct table says for the fixture stack, DERIVED once here so the tests
# below mutate a row rather than restating the whole table per case.
CLEAN_FALLBACKS = {
    "frontdoor": FRONTDOOR_FLEET_URL,
    "worker_general": FRONTDOOR_FLEET_URL,
    "worker_math": FRONTDOOR_FLEET_URL,
    "toolrunner": FRONTDOOR_FLEET_URL,
    "architect_general": "http://localhost:8083",
    "ingest_long_context": "http://localhost:8083",
    # Outside the alias graph entirely: no shared_with relationship to recompute.
    "worker_fast": "http://localhost:8102",
    "api_url": "http://localhost:8000",
}


def _write_models_py(tmp_path: Path, table: dict | None = None, *, name: str = "models.py") -> Path:
    """A models.py stand-in carrying only the table under test.

    Written as SOURCE, not as data, because the checker parses it with `ast` rather
    than importing it -- `src.config.models` drags in the whole config stack and a
    checker that must run on an uncompiled tree cannot depend on that importing.
    """
    rows = table if table is not None else CLEAN_FALLBACKS
    body = "\n".join(f"    {key!r}: {value!r}," for key, value in rows.items())
    path = tmp_path / name
    path.write_text(
        "_LEGACY_SERVER_URL_FALLBACKS: dict[str, str] = {\n" + body + "\n}\n",
        encoding="utf-8",
    )
    return path


def _fallback_findings(tmp_path: Path, table: dict | None = None, **mutations):
    master, manifest, topology = _write(tmp_path, **mutations)
    models = _write_models_py(tmp_path, table)
    findings = check_all(load_sources(master, manifest, topology, models))
    return [f for f in findings if "_LEGACY_SERVER_URL_FALLBACKS" in f.surface]


def test_fleet_url_reproduces_both_wire_forms():
    """The recompute must emit the SAME wire form the operative layer does, or every
    comparison below is between two differently-shaped renderers rather than a diff."""
    assert fleet_url({"port": 8070, "numa_ports": [8080, 8180]}) == FRONTDOOR_FLEET_URL
    # one instance is emitted bare -- the `full:` prefix would advertise ports that
    # do not exist (the 2026-08-01 coder_escalation comment in models.py)
    assert fleet_url({"port": 8083, "numa_ports": [8083]}) == "http://localhost:8083"
    assert fleet_url({"port": 8086}) == "http://localhost:8086"
    assert fleet_url({}) is None


def test_clean_fallback_table_has_no_findings(tmp_path):
    """Baseline. Non-vacuous: the fixture table must actually cover alias rows."""
    assert _fallback_findings(tmp_path) == []
    d = derive(load_sources(*_write(tmp_path)))
    assert d.aliases & set(CLEAN_FALLBACKS), "fixture table covers no alias — vacuous"


def test_stale_worker_lane_rows_are_the_2026_09_22_defect(tmp_path):
    """THE defect SSU-F8 names, with its real values."""
    table = dict(CLEAN_FALLBACKS)
    for role in ("worker_general", "worker_math", "toolrunner"):
        table[role] = RETIRED_WORKER_FLEET_URL
    findings = _fallback_findings(tmp_path, table)

    assert sorted(f.role for f in findings) == ["toolrunner", "worker_general", "worker_math"]
    for f in findings:
        assert f.found == RETIRED_WORKER_FLEET_URL
        assert f.expected == FRONTDOOR_FLEET_URL
        assert "alias on 'frontdoor'" in f.message
        assert "bare subscript" in f.message
        # a finding without a line is half a finding
        assert f.line and f.line > 0
        # models.py is hand-annotated with cutover history: reported, never rewritten
        assert not f.fixable


def test_stale_fallback_row_points_at_its_own_line(tmp_path):
    table = dict(CLEAN_FALLBACKS)
    table["worker_math"] = RETIRED_WORKER_FLEET_URL
    (finding,) = _fallback_findings(tmp_path, table)
    models = _write_models_py(tmp_path, table)
    line = models.read_text(encoding="utf-8").splitlines()[finding.line - 1]
    assert "worker_math" in line


def test_host_row_drift_is_caught_too(tmp_path):
    """Not only aliases: a HOST whose own row stops matching its declared fleet."""
    table = dict(CLEAN_FALLBACKS)
    table["frontdoor"] = "http://localhost:8070"
    (finding,) = _fallback_findings(tmp_path, table)
    assert finding.role == "frontdoor"
    assert finding.expected == FRONTDOOR_FLEET_URL
    assert "hosts [" in finding.message


def test_row_follows_the_registry_not_the_literal(tmp_path):
    """DERIVED, not repinned: move the fleet in the registry and the SAME table that
    was clean becomes a finding, naming the new ports. A literal-to-literal gate
    cannot do this, which is why the five wired surfaces survived the cutover."""

    def move_the_fleet(m):
        m["server_mode"]["frontdoor"]["port"] = 8090
        m["server_mode"]["frontdoor"]["numa_ports"] = [8091, 8092]

    findings = _fallback_findings(tmp_path, master=move_the_fleet)
    moved = "full:http://localhost:8090,http://localhost:8091,http://localhost:8092"
    assert {f.role for f in findings} == {
        "frontdoor",
        "worker_general",
        "worker_math",
        "toolrunner",
    }
    assert {f.expected for f in findings} == {moved}


def test_roles_outside_the_alias_graph_are_out_of_scope(tmp_path):
    """`worker_fast` / `api_url` restate no shared_with relationship, so there is
    nothing to recompute for them -- and a missing row restates nothing either. The
    table is not required to cover the lineup, only to be right about what it covers."""
    table = {k: v for k, v in CLEAN_FALLBACKS.items() if k != "toolrunner"}
    table["worker_fast"] = "http://localhost:9999"
    table["api_url"] = "http://localhost:9998"
    assert _fallback_findings(tmp_path, table) == []


def test_absent_models_py_source_declares_no_findings(tmp_path):
    """Three-arg `load_sources` (every pre-SSU-F8 caller) leaves the surface unloaded:
    a surface with no source diffs nothing rather than diffing a synthetic registry
    against the real repo's table."""
    master, manifest, topology = _write(tmp_path)
    sources = load_sources(master, manifest, topology)
    assert sources.models_path is None
    assert check_all(sources) == []


def test_a_models_py_without_the_table_is_a_source_error(tmp_path):
    """Silence would be the failure mode this whole file exists to prevent: if the
    table is renamed away, the checker must say so, not report a clean sixth surface."""
    path = tmp_path / "renamed.py"
    path.write_text("SERVER_URLS = {'frontdoor': 'http://localhost:8070'}\n", encoding="utf-8")
    with pytest.raises(SourceError, match="no module-level _LEGACY_SERVER_URL_FALLBACKS"):
        load_server_url_fallbacks(path)


def test_multiline_implicit_concatenation_reads_back_as_one_row(tmp_path):
    """The live table writes its `full:` rows as parenthesised adjacent literals; the
    parser must fold them, or every fleet row would silently drop out of scope."""
    path = tmp_path / "concat.py"
    path.write_text(
        "_LEGACY_SERVER_URL_FALLBACKS: dict[str, str] = {\n"
        '    "frontdoor": (\n'
        '        "full:http://localhost:8070,http://localhost:8080,"\n'
        '        "http://localhost:8180"\n'
        "    ),\n"
        "}\n",
        encoding="utf-8",
    )
    values, lines = load_server_url_fallbacks(path)
    assert values == {"frontdoor": FRONTDOOR_FLEET_URL}
    assert lines == {"frontdoor": 2}


def test_live_models_py_table_agrees_with_the_live_registry():
    """Regression fence on the real tree (skipped where the master registry is not
    present), so the surface is exercised against the values that actually ship."""
    master = Path("/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml")
    models = REPO_ROOT / "src" / "config" / "models.py"
    if not master.exists() or not models.exists():
        pytest.skip("live sources not present in this checkout")
    sources = load_sources(
        master,
        REPO_ROOT / "orchestration" / "launch_manifest.yaml",
        REPO_ROOT / "orchestration" / "stack_topology.yaml",
        models,
    )
    # non-vacuity: the live table must actually cover the live alias graph
    d = derive(sources)
    assert d.aliases & set(sources.fallbacks)
    stale = [f.render() for f in check_all(sources) if "_LEGACY" in f.surface]
    assert stale == [], "\n".join(stale)


# ---------------------------------------------------------------------------
# the live tree: a regression fence, not a pass/fail gate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        Path("/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml"),
        REPO_ROOT / "orchestration" / "launch_manifest.yaml",
        REPO_ROOT / "orchestration" / "stack_topology.yaml",
    ],
)
def test_live_sources_are_readable(path):
    if not path.exists():
        pytest.skip(f"{path} not present in this checkout")
    assert isinstance(yaml.safe_load(path.read_text(encoding="utf-8")), dict)


# ---------------------------------------------------------------------------
# pipeline wiring: the step runs BEFORE the lean compile, so the whole class
# surfaces in one run instead of one class per run.
# ---------------------------------------------------------------------------


def test_pipeline_step_reports_every_class_in_one_pass(tmp_path):
    from scripts.registry.stack_change_pipeline import (
        StackChangePipelineConfig,
        _shared_with_derivations_step,
    )

    def mutate_manifest(m):
        m["port_map"]["toolrunner"] = 8072
        m["role_launch_meta"]["worker_general"] = {"tier": "hot", "mode": "default"}

    def mutate_master(m):
        m["roles"]["worker_math"]["model"] = {"name": "Qwen2.5-Math-7B-Instruct"}
        m["server_mode"]["architect_general"]["shared_with"] = []
        m["server_mode"]["ingest_long_context"]["numa_ports"] = [8083]

    repo = tmp_path / "repo"
    (repo / "orchestration").mkdir(parents=True)
    master, manifest, topology = _write(tmp_path, master=mutate_master, manifest=mutate_manifest)
    manifest.replace(repo / "orchestration" / "launch_manifest.yaml")
    topology.replace(repo / "orchestration" / "stack_topology.yaml")

    config = StackChangePipelineConfig(
        mode="check", repo_root=repo, research_registry=master
    )
    step = _shared_with_derivations_step(config)
    assert step.name == "shared_with_derivations"
    assert step.status == "failed"
    blob = "\n".join(step.errors)
    # all four classes, one run
    assert "port for role 'toolrunner'" in blob
    assert "ROLE_LAUNCH_META['worker_general'] has no_numa=False" in blob
    assert "A fleet nothing launches is a phantom" in blob
    assert "Role-server conflict" in blob


def test_pipeline_step_skips_without_a_master_registry(tmp_path):
    from scripts.registry.stack_change_pipeline import (
        StackChangePipelineConfig,
        _shared_with_derivations_step,
    )

    config = StackChangePipelineConfig(
        mode="check", repo_root=tmp_path, research_registry=None
    )
    assert _shared_with_derivations_step(config).status == "skipped"
