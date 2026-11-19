import importlib.util
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
IMPORTER = HERE.parent / "toc-cmp-3-semantic/semantic.py"
BASE_RUNNER = HERE.parent / "toc-cmp-2-governance/runner.py"


@pytest.fixture
def source_modules(monkeypatch):
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        return module

    semantic = load("semantic", IMPORTER)
    load("cmp2_runner", BASE_RUNNER)
    load("rubric", HERE / "rubric.py")
    controls = load("controls", HERE / "controls.py")
    runner = load("runner", HERE / "runner.py")
    return semantic, controls, runner


def test_schedule_and_original_importer(source_modules):
    semantic, controls, runner = source_modules
    schedule = controls.cases()
    assert [row["case"]["unit"] for row in schedule] == [
        "control/paraphrase", "control/missing-external-evidence",
        "control/folded-conflict", "control/missing-requirement",
    ]
    assert runner.select_attempts(schedule, True) == schedule[:2]
    case = schedule[0]["case"]
    labels = schedule[0]["expected"]
    output = evaluator_answer(case, labels, {**controls.PARAPHRASE,
                                            "verbatim_task": controls.REFERENCE["verbatim_task"]})
    judgment = semantic.import_judgment(case, semantic.canonical(output), "mock")
    assert judgment["semantic_verdict"] == "unknown"
    assert judgment["detail"] == "citation absent from observation for verbatim_task"


def test_schema_uses_only_message_index_and_its_observed_lines(source_modules):
    semantic, controls, runner = source_modules
    row = controls.cases()[0]
    case = row["case"]
    case["observed_messages"].extend([
        {"role": "assistant", "content": "  Independent line.  \n\n  Independent line.  "},
        {"role": "user", "content": " \t "},
    ])
    schema = runner.response_schema(case)
    assert set(schema["required"]) == {"request_id", "judgments"}
    assert schema["additionalProperties"] is False
    assert schema["properties"]["request_id"] == {"const": case["request_id"]}
    judgments = schema["properties"]["judgments"]
    assert judgments["type"] == "object"
    assert judgments["required"] == list(semantic.FIELDS)
    assert set(judgments["properties"]) == set(semantic.FIELDS)
    assert judgments["additionalProperties"] is False
    for judgment in judgments["properties"].values():
        assert judgment["additionalProperties"] is False
        assert set(judgment["required"]) == {"verdict", "rationale", "evidence"}
        assert judgment["properties"]["verdict"]["enum"] == ["entailed", "contradicted", "unknown"]
        assert judgment["properties"]["rationale"] == {"type": "string"}
        evidence = judgment["properties"]["evidence"]
        assert evidence["maxItems"] == 2
        options = evidence["items"]["anyOf"]
        assert len(options) == 2
        assert [option["properties"] for option in options] == [
            {"message": {"const": 0}, "quote": {"enum": list(controls.PARAPHRASE.values())}},
            {"message": {"const": 1}, "quote": {"enum": ["  Independent line.  "]}},
        ]
        assert all(option["additionalProperties"] is False for option in options)
    encoded = semantic.canonical(schema).decode()
    assert all(reference not in encoded for reference in case["reference"].values())
    label_changed = {**row, "expected": dict.fromkeys(semantic.FIELDS, "contradicted")}
    assert runner.response_schema(label_changed["case"]) == schema


def test_model_receipt_maps_cf3c_stat_and_requires_the_same_build(tmp_path):
    spec = importlib.util.spec_from_file_location("qual_prepare", HERE / "prepare.py")
    prepare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prepare)
    model_path = tmp_path / "fixture.gguf"
    previous = {"bin_dir": str(tmp_path), "build_sha256": {"llama-server": "expected-build"}}
    pilot = {"model_path": str(model_path), "model_stat": [1, 2, 3, 4, 5],
             "model_sha256": "expected-weights",
             "build_sha256": {str(tmp_path / "llama-server"): "expected-build"}}
    assert prepare.model_receipt(pilot, previous) == {
        "path": str(model_path), "sha256": "expected-weights",
        "stat_at_hash": {"path": str(model_path.resolve()), "device": 1, "inode": 2,
                         "size": 3, "mtime_ns": 4, "ctime_ns": 5},
    }
    previous["build_sha256"]["llama-server"] = "different-build"
    with pytest.raises(ValueError, match="pilot build differs"):
        prepare.model_receipt(pilot, previous)


def test_packet_verification_rejects_mutated_rubric(tmp_path, monkeypatch, source_modules):
    semantic, controls, runner = source_modules
    packet = tmp_path / "packet"
    packet.mkdir()
    for source in (IMPORTER, HERE / "runner.py", HERE / "controls.py", HERE / "rubric.py"):
        shutil.copy2(source, packet / source.name)
    cases = controls.cases()
    (packet / "cases.json").write_bytes(semantic.canonical(cases))
    build = tmp_path / "llama-server"
    build.write_bytes(b"fixture build")
    model = tmp_path / "fixture.gguf"
    model.write_bytes(b"fixture model")
    manifest = {
        "packet_sha256": {path.name: semantic.digest(path.read_bytes()) for path in packet.iterdir()},
        "bin_dir": str(tmp_path),
        "build_sha256": {build.name: semantic.digest(build.read_bytes())},
        "model": {"path": str(model), "stat_at_hash": runner.base.file_identity(model)},
    }
    seal = semantic.digest(semantic.canonical(manifest))
    (packet / "inputs.json").write_bytes(semantic.canonical({**manifest, "sha256": seal}))
    monkeypatch.setattr(runner, "HERE", packet)
    assert runner.verify()[1] == cases
    with (packet / "rubric.py").open("a") as rubric:
        rubric.write("\n# mutation\n")
    with pytest.raises(ValueError, match="SHA-256 custody mismatch.*rubric.py"):
        runner.verify()


def evaluator_answer(case, labels, quotes):
    return {
        "request_id": case["request_id"],
        "judgments": {
            field: {"verdict": label, "rationale": "Fixture result.",
                    "evidence": [] if label == "unknown" else [{"message": 0, "quote": quotes[field]}]}
            for field, label in labels.items()
        },
    }


@pytest.mark.parametrize("dry,fault,completed,calls", [
    (False, None, 4, 4),
    (True, None, 2, 2),
    (False, "citation", 0, 1),
    (False, "label", 1, 2),
    (True, "label", 1, 2),
    (False, "transport", 1, 2),
])
def test_run_schedule_and_fail_fast(tmp_path, monkeypatch, source_modules, dry, fault, completed, calls):
    semantic, controls, runner = source_modules
    canonical = semantic.canonical
    schedule = controls.cases()
    expected_requests = runner.select_attempts(schedule, dry)
    requests = []

    def http(_route, timeout, body):
        row = expected_requests[len(requests)]
        case = row["case"]
        user = json.loads(body["messages"][1]["content"])
        assert user == {key: case[key] for key in ("request_id", "reference", "observed_messages")}
        assert body["response_format"] == {
            "type": "json_object", "schema": runner.response_schema(case),
        }
        assert 0 < timeout <= 420
        requests.append(user["request_id"])
        labels = row["expected"].copy()
        quotes = controls.PARAPHRASE.copy()
        if case["unit"] == "control/folded-conflict":
            quotes = {**controls.REFERENCE, "pinned_governance":
                      "Send the receipt to the external reviewer before reporting the ID."}
        if case["unit"] == "control/missing-external-evidence":
            quotes = controls.EXTERNAL_REFERENCE.copy()
            if fault == "label":
                labels["artifacts"] = "entailed"
            if fault == "transport":
                raise TimeoutError("fixture transport timeout")
        if case["unit"] == "control/paraphrase" and fault == "citation":
            quotes["verbatim_task"] = controls.REFERENCE["verbatim_task"]
        answer = evaluator_answer(case, labels, quotes)
        return canonical({"choices": [{"finish_reason": "stop",
                                       "message": {"content": canonical(answer).decode()}}]})

    class FakeServer:
        pid = 100_001
        exited = False

        def poll(self):
            return 0 if self.exited else None

        def terminate(self):
            self.exited = True

        def wait(self, timeout):
            assert timeout == 5
            assert self.exited

    server = FakeServer()
    monkeypatch.setattr(runner, "base", SimpleNamespace(
        json_bytes=canonical, http=http, remaining=lambda _deadline: 100,
        atomic_json=lambda path, data: path.write_bytes(canonical(data)),
        bind_four_cores=lambda: [0, 1, 2, 3],
        server_ready=lambda *_: {"data": [{"id": runner.ALIAS}]},
        server_identity=lambda *_: {"pid": server.pid},
        owns_listener=lambda pid: pid == server.pid,
    ))
    monkeypatch.setattr(runner, "SCRATCH", tmp_path)
    monkeypatch.setattr(runner, "verify", lambda: (
        {"sha256": "fixture", "bin_dir": str(tmp_path), "model": {"path": "fixture.gguf"}}, schedule))
    monkeypatch.setattr(runner.signal, "signal", lambda *_: None)
    monkeypatch.setattr(runner.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(stdout="fixture linkage"))
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *_args, **_kwargs: server)
    monkeypatch.setenv("FILLER_ID", runner.ROW)
    monkeypatch.setenv("FILLER_DRYRUN", str(int(dry)))
    monkeypatch.setenv("FILLER_DRYRUN_DIR", str(tmp_path))
    monkeypatch.setenv("FILLER_DEADLINE", "4000000000")
    monkeypatch.setenv("FILLER_PIDFILE", str(tmp_path / "pids"))
    monkeypatch.setenv("FILLER_SMOKE_T0", "0")
    assert runner.run() == int(fault is not None)
    directory = tmp_path / ("cmp3-evalqual-r3-native" if dry else "native")
    success_name = "SMOKE.json" if dry else "RESULT.json"
    result = json.loads((directory / ("PARTIAL.json" if fault else success_name)).read_bytes())
    assert result["completed"] == completed
    assert result["coverage_complete"] == (fault is None)
    assert result["server_exited"] is True
    assert requests == [row["case"]["request_id"] for row in expected_requests[:calls]]
    assert (tmp_path / "pids").read_text() == f"{server.pid}\n"
    receipt = json.loads((directory / "RECEIPT.json").read_bytes())
    argv = receipt["argv"]
    assert argv[argv.index("--chat-template-file") + 1] == str(runner.HERE / "chat-template.jinja")
    assert argv[argv.index("--reasoning") + 1] == "off"
    if fault:
        assert not (directory / success_name).exists()
        assert result["error"]
    monkeypatch.setattr(sys, "argv", ["runner.py", "smoke" if dry else "complete"])
    assert runner.main() == int(fault is not None)
