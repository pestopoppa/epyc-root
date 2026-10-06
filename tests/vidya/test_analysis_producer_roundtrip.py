"""Hosted-only, synthetic APP-writer -> ROOT-adapter source-bound round trips.

The capture recipe sets EPYC_ORCHESTRATOR_SOURCE_ROOT to the separately pinned APP source
checkout. This fixture copies and hash-checks the exact producer/dependency bytes into a temporary
project tree, then uses the actual producer normalization/summarization/sealing functions over
synthetic bytes. It never reads the live BEP corpus or a real evaluation run.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
import stat
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

from adapters import eval_suite_discriminability as eval_adapter  # noqa: E402
from adapters import verify_before_stop as mf_adapter  # noqa: E402
import claim_tuple as ct  # noqa: E402
import cli  # noqa: E402
from ledger import Ledger  # noqa: E402


_APP_SHA256 = {
    'scripts/analysis/eval_suite_discriminability.py': '6e3e8e688b74b857d7023e10361ca5c13334f8facbb69cae6a37c3df1648de35',
    'scripts/analysis/mf_vbs1_verify_before_stop.py': '7463afeab66a20c274314e5f0a85472e271dc7e12e10f052b874039d4c0b44da',
    'src/__init__.py': '16e20bce77e6470646b90def0e3d653a3bd9fb024b484f7cd034f96ff8a0a5f8',
    'src/backends/__init__.py': '6e4c4f1fba779a86819e693df18268e2880d3cd77529ae9bbc106989e9dedcf9',
    'src/backends/anthropic.py': '4797b591f37add6d311b3d14cef9e88a1dd8818722faa58e010b02631bcd4a45',
    'src/backends/context_overflow.py': '5c18c272fc528c359f46d527a9d70413d244069b6fd92049d4999d2352553c84',
    'src/backends/llama_server.py': 'cef546d0009917416d544f5e52814def1d71644e06970a5be6c92145f0533e62',
    'src/backends/openai.py': '129ef11391df6e4be4cb6e99c4bde67374ae075af0d072951ae47e3ee5e8b8b0',
    'src/backends/protocol.py': '18d26e35e01da077389fabfd3f5d843fda6604a41cb1fd5fc54aa80d850fe07d',
    'src/backends/serving_calls.py': 'a528b20c6d106e9d5ce4c3a2f95919103bed44bad30cabb863491d768ad1214c',
    'src/config/__init__.py': 'bd0a888d06c952e0899093233241029b6cac2b6c2e1d605fea4b56878fe04d17',
    'src/config/models.py': '9ff0f384f74ffd315be19311f52b32cb9db78a2209248a9040dc7a9b185576b7',
    'src/config/validation.py': 'dc33a052fb1e0962b3546336017d239929a36a8942502a7aa99da064b20e32da',
    'src/env_parsing.py': '2626fb2c47012c56a7f7e99fe03f088977f9b061c77bcd1edf0dfa1e12b7d52f',
    'src/exceptions.py': '5149fe8b548384ad3619ea39b36226ba4980ba03c61298c53ab27b571a62db77',
    'src/llm_primitives/__init__.py': 'cdee7bcf079e3023de6da551cd376e9e6db339d0ac52853eba054e3d3d6ccff9',
    'src/llm_primitives/backend.py': 'cceeaa03e7f7e03371f634f049ca3e86b711fa171cc653f6e261af50cad2d743',
    'src/llm_primitives/config.py': '3ec665e25cc474fb7f3052b0d3169200697738d9ce9bb8862dbcb575878a10d5',
    'src/llm_primitives/cost_tracking.py': '94794e6c2cd20de3775a8dd085b01a2e60feca366989856bef784e40135f7017',
    'src/llm_primitives/inference.py': 'd22b9653615ecf6b46fd3821bfb62b9fcfb24e725fe091db9b2154346666b1bf',
    'src/llm_primitives/mock.py': 'b8e304c4b4b8fe3bad127165fb1a43896832260493b49a33e9df3fea5ce7bdc6',
    'src/llm_primitives/persona.py': 'f78a6741dca6c44e746104600ece8f8a3df7453e5415a4cc65634a1d56c7f330',
    'src/llm_primitives/primitives.py': '6111549ee50a29eb06efa744ae01ca53a1f205ebf89d6fa22ab4f56ca9388399',
    'src/llm_primitives/stat_tests.py': 'd0886ef1b32498475d804b9597347d2934b3dc0553224c0443a98654436af2dc',
    'src/llm_primitives/stats.py': '48893a575027dc7315851155af3c5cd2ee2cbcfbd6a0e7b07b1cdeb52bc82df6',
    'src/llm_primitives/teleport.py': 'c8e42785b24378929f9cf94522cb530aa62ec08a4f12b38b5beaef2ffbb79c2d',
    'src/llm_primitives/tokenizer.py': 'a8bd406cebc7e62ea8a2e2b9ae398f54916003c93e8e74c5a287cbaf6be04a99',
    'src/llm_primitives/tokens.py': '352905c58f38480a05ba865fcf9aeeb64813fda9d4679de51a49959f322c2c8a',
    'src/llm_primitives/types.py': '6ac137723f9541bd270a3b9bba684f102595ac24b620d8db1eab7e656c96e7fc',
    'src/model_server.py': '5185d36cb8484590605c127ec2382b94af5e6175ade8fff05e2110c0229c489b',
    'src/registry/__init__.py': '50ddc75e291c2caaae688bbe94c4f3144a5751eb11e0a65ee35b5632ea3a9c6d',
    'src/registry/kernel_paths.py': 'f5cd510ad2887a6276350c8939147ce66ba78a8eab573d42ee120094c0795066',
    'src/registry/stack_priors.py': '188e4093675afc23308ad1c3b8afd0c4d104f9626d6658ae78849b3ab90fca7f',
    'src/registry_loader.py': '81f3dc46dea4af9eb8df9adb4a73d2e900e1d040d107a73a04053f8ea72b77be',
    'src/roles.py': '408f10be964705638562ec9a6d0e1cd56b26ac849fdb964e8bac0c9a7fe4be61',
    'src/runtime/__init__.py': '8ac7118ea6f4f3134f219d094b325f74006c47a2f220b8a6b04b2355d021f4e0',
    'src/runtime/git_head.py': 'f87a64e1f27716026f4d91aa508f4bfa6731939dbe0ef8713d41a3d658a86b01',
    'src/scheduling/__init__.py': 'a65b963b3d38ca2d680827bfe3debe3e7d91095ea50723c5c40ce6b19dd0df51',
    'src/scheduling/gate_observation.py': '9beb0986cd902292f322176d2f3aaa534ea83a3f5840ecca838dcf07a850d470',
    'src/workload_model.py': '6fff754ce59a70edf28159fa13e071d8b2ea38bef97968cca6508a54924a315f',
}


def _copy_exact(app_root: Path, temp_root: Path, relative: str) -> Path:
    raw = (app_root / relative).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == _APP_SHA256[relative], relative
    target = temp_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return target


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _app_tree(tmp_path: Path) -> tuple[Path, object, object]:
    configured = os.environ.get("EPYC_ORCHESTRATOR_SOURCE_ROOT")
    if not configured:
        pytest.skip("hosted source-bound integration recipe must provide APP source root")
    app_root = Path(configured).resolve()
    temp_root = tmp_path / "synthetic-orchestrator"
    copied = {relative: _copy_exact(app_root, temp_root, relative)
              for relative in sorted(_APP_SHA256)}
    mf_path = copied["scripts/analysis/mf_vbs1_verify_before_stop.py"]
    eval_path = copied["scripts/analysis/eval_suite_discriminability.py"]
    sys.path.insert(0, str(temp_root))
    return temp_root, _load_module(mf_path, "captured_mf_vbs1_producer"), \
        _load_module(eval_path, "captured_eval_discriminability_producer")


def _jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join((json.dumps(row, sort_keys=True) + "\n").encode() for row in rows))


def _assert_ingested_with_shared_grade(tmp_path, capsys, source, adapter, report_path):
    ledger_path = tmp_path / f"{source}.ledger.jsonl"
    rc = cli.main(["--ledger", str(ledger_path), "--json", "ingest", source,
                   "--path", str(report_path), "--as-of", "2026-10-06T12:00:00Z"])
    assert rc == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["refused"] == []
    assert receipt["rows_projected"] > 0
    native_rows = adapter.native_rows(report_path)
    expected = {}
    for native in native_rows:
        tup = adapter.project(native)
        expected[f"clm_{tup.measurement_id}"] = ct.grade(tup)[:2]
    records = Ledger(ledger_path).read_all()
    supports = [record.frame for record in records
                if record.frame["frame_type"].endswith("evidence_supports_claim/v1")]
    assert len(supports) == len(expected)
    for frame in supports:
        assert frame["assertion"]["grade"] == dict(zip(("Q", "T"),
                                                           expected[frame["assertion"]["claim_id"]]))


def _capture_synthetic_bundle(kind, report_path, input_paths):
    configured = os.environ.get("NI08_NATIVE_FIXTURE_CAPTURE_DIR")
    if not configured:
        return
    destination_root = Path(configured).resolve()
    destination = destination_root / f"{kind}-bundle.zip"
    destination_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    candidates = [(f"inputs/{index:02d}-{path.name}", path) for index, path in enumerate(input_paths)]
    candidates.append(("report.json", report_path))
    snapshot_root = report_path.with_name(report_path.name + ".native")
    for snapshot in sorted(snapshot_root.rglob("*")):
        info = snapshot.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise AssertionError(f"non-regular native fixture member: {snapshot}")
        candidates.append((snapshot.relative_to(report_path.parent).as_posix(), snapshot))
    entries = []
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for archive_path, source in candidates:
            data = source.read_bytes()
            info = zipfile.ZipInfo(archive_path)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o600) << 16
            bundle.writestr(info, data)
            entries.append({"path": archive_path, "sha256": hashlib.sha256(data).hexdigest(),
                            "bytes": len(data)})
        manifest = json.dumps({"schema": "epyc.ni08.synthetic_fixture_bundle/v1",
                               "kind": kind, "members": entries}, sort_keys=True,
                              separators=(",", ":")).encode() + b"\n"
        info = zipfile.ZipInfo("bundle-manifest.json")
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (stat.S_IFREG | 0o600) << 16
        bundle.writestr(info, manifest)


def test_actual_mf_producer_snapshot_round_trips_through_root_adapter(tmp_path, monkeypatch,
                                                                       capsys):
    app_root, producer, _ = _app_tree(tmp_path)
    results = app_root / "data/bep_sandbox/synthetic/results.jsonl"
    trace_a = app_root / "data/bep_sandbox/synthetic/traces/a.jsonl"
    trace_b = app_root / "data/bep_sandbox/synthetic/traces/b.jsonl"
    _jsonl(results, [
        {"mode": "real", "task": "a", "arm": "base", "block": 0, "turns": 2,
         "touched_files": ["a.py"], "answer_preview": "done", "trace": {"path": "traces/a.jsonl"}},
        {"mode": "real", "task": "b", "arm": "base", "block": 0, "turns": 2,
         "touched_files": ["b.py"], "answer_preview": "done", "trace": {"path": "traces/b.jsonl"}},
    ])
    _jsonl(trace_a, [{"raw_output": "finished"}])
    _jsonl(trace_b, [{"raw_output": "please run the test yourself"}])
    inputs: list[dict] = []
    missing: list[str] = []
    trajectories = producer.load_trajectories(str(app_root), input_manifest=inputs,
                                              missing_inputs=missing)
    report = producer.summarize(trajectories)
    report_path = app_root / "data/analysis/synthetic-mf.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = producer._seal_report(report, str(app_root), inputs, str(report_path), missing)
    report_path.write_text(json.dumps(report, sort_keys=True))

    monkeypatch.setattr(mf_adapter, "ORCHESTRATOR", app_root)
    native = mf_adapter.native_rows(report_path)
    projected = [mf_adapter.project(row) for row in native]
    assert len(projected) == 3
    assert all(row.category == report["category"] == "BASELINE" for row in projected)
    assert all(row.date == "" and row.extra["role_model"] is None for row in projected)
    assert all(row.attestation_verified for row in projected)
    assert len(report["native_provenance"]["inputs"]) == 3
    _assert_ingested_with_shared_grade(tmp_path, capsys, "verify-before-stop-measurement",
                                       mf_adapter, report_path)
    _capture_synthetic_bundle("mf", report_path, [results, trace_a, trace_b])


def test_actual_eval_producer_snapshot_round_trips_with_native_reps(tmp_path, monkeypatch,
                                                                    capsys):
    app_root, _, producer = _app_tree(tmp_path)
    source = tmp_path / "external-fixture/question_ledger.jsonl"
    _jsonl(source, [
        {"suite": "synthetic", "qid": "q1", "correct": True, "error": False,
         "calibration_id": "run-a"},
        {"suite": "synthetic", "qid": "q1", "correct": False, "error": False,
         "calibration_id": "run-b"},
    ])
    inputs: list[dict] = []
    rows, warnings = producer.load_rows([source], input_manifest=inputs)
    config = producer.AuditConfig()
    report = producer.build_report(rows, config, [str(source)], warnings)
    report_path = app_root / "data/analysis/synthetic-eval.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = producer._seal_report(report, inputs, report_path)
    report_path.write_text(json.dumps(report, sort_keys=True))

    monkeypatch.setattr(eval_adapter, "ORCHESTRATOR", app_root)
    native = eval_adapter.native_rows(report_path)
    projected = {row["metric"]: eval_adapter.project(row) for row in native}
    assert set(projected) == {"pass_rate", "mde", "run_spread", "flip_rate"}
    assert all(row.category == report["category"] == "BASELINE" for row in projected.values())
    assert projected["pass_rate"].reps == 2
    assert projected["mde"].reps == 1
    assert projected["run_spread"].reps == 2
    assert projected["flip_rate"].reps == 1
    assert all(row.attestation_verified for row in projected.values())
    _assert_ingested_with_shared_grade(tmp_path, capsys, "eval-suite-discriminability",
                                       eval_adapter, report_path)
    _capture_synthetic_bundle("eval", report_path, [source])
