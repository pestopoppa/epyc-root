import base64
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / ".claude/skills/kernel-promotion/scripts/quality_parity.py"
)
SPEC = importlib.util.spec_from_file_location("quality_parity", SCRIPT)
parity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parity)


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _set_response(capture, response):
    raw = (json.dumps(response, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    capture["response_b64"] = base64.b64encode(raw).decode("ascii")
    capture["response_sha256"] = _digest(raw)


def _response(capture):
    return json.loads(base64.b64decode(capture["response_b64"]))


def _request_hash(body):
    return _digest(parity.canonical_json(body))


@pytest.fixture
def source():
    shapes = []
    items = []
    for profile in sorted(parity.MANDATORY_SHAPES):
        chat = profile == "worker-vision-cpu-mmproj"
        dflash = profile == "dspark-dflash"
        shape = {
            "id": profile,
            "profile": profile,
            "endpoint": "/v1/chat/completions" if chat else "/completion",
            **{field: _digest(field.encode()) for field in parity.SHAPE_PINS},
        }
        if dflash:
            shape["validated_cap"] = 6
        shapes.append(shape)

        for index in range(4):
            item_id = f"{profile}-{index}"
            long = index % 2 == 1
            prompt = (item_id + " ") * (120 if long else 1)
            body = {"seed": 42, "temperature": 0, "cache_prompt": False, "stream": False,
                    "return_tokens": True}
            token_count = index + 3
            if chat:
                body.update(messages=[{"role": "user", "content": prompt}], max_tokens=token_count)
            else:
                body.update(prompt=prompt, n_predict=token_count)

            content = '{"answer":"café"}' if index == 0 else "The answer is café."
            finish = "length" if index == 3 else "stop"
            output_format = ["json", "prose", "code", "reasoning"][index]
            validator = (
                {"id": "json-object-subset.v1", "expected": {"answer": "café"}}
                if output_format == "json"
                else {"id": "contains-text.v1", "expected": "café"}
            )
            fixture = ["loader-reshape", "recurrent-state", None, None][index]
            for cap in ((0, shape["validated_cap"]) if dflash else (None,)):
                request_body = dict(body)
                response = {
                    "content": content, "stop_type": "limit" if finish == "length" else "eos",
                    "tokens": list(range(token_count)),
                    "tokens_predicted": token_count,
                }
                capture = {}
                if dflash:
                    request_body[parity.CAP_KEY] = cap
                    response["generation_settings"] = {parity.CAP_KEY: cap}
                    capture.update(server_instance="production:123:456", parallel_slots=1, effective_n_max=cap)
                if chat:
                    response = {
                        "choices": [{"finish_reason": finish, "message": {"content": content, "reasoning_content": "café?"}}],
                        "__verbose": {"tokens": response["tokens"]},
                        "usage": {"completion_tokens": token_count},
                    }
                capture["request_sha256"] = _request_hash(request_body)
                _set_response(capture, response)
                items.append({
                    "id": f"{item_id}-{cap}" if dflash else item_id,
                    "shape": profile,
                    "request_body": request_body,
                    "prompt_shape": "long" if long else "short",
                    "output_format": output_format,
                    "fixture": fixture,
                    "expected_finish": finish,
                    "dflash_pair": item_id if dflash else None,
                    "validator": validator,
                    "production": capture,
                })

    return {
        "schema": parity.SOURCE_SCHEMA,
        "capture_source": {"commit": "a" * 40, "tree": "b" * 40, "source_sha256": "c" * 64},
        "runtime": {shape["id"]: {"kernel_commit": "d" * 40, "kernel_tree": "e" * 40,
                                  "binary_sha256": "f" * 64} for shape in shapes},
        "shapes": shapes,
        "items": items,
    }


def test_profile_roles_and_devices_match_compiled_registry():
    import yaml
    registry = Path('/workspace/repos/epyc-orchestrator/orchestration/model_registry.yaml')
    rows = yaml.safe_load(registry.read_text())['server_mode']
    for profile, (role, expected_device) in parity.SERVING_PROFILES.items():
        assert role in rows, profile
        device = str(rows[role].get('device') or 'none').lower()
        assert ('hip' if device.startswith('rocm') else 'cpu') == expected_device, profile
    assert 'worker_general' in rows['frontdoor']['shared_with']
    assert rows['ingest_long_context']['alias_of'] == 'architect_critic'
    assert rows['architect_critic']['acceleration']['spec_type'] == 'draft-dflash'


def test_legacy_pack_remains_readable(source):
    mapping = {'architect-critic-hip-dflash': 'architect-critic-cpu-mtp',
               'ingest-long-context-hip-dflash': 'ingest-long-context-recurrent-no-spec',
               'architect-general-cpu-mtp': 'architect-general-hip',
               'worker-vision-cpu-mmproj': 'worker-vision-hip-mmproj'}
    for shape in source['shapes']:
        shape['profile'] = mapping.get(shape['profile'], shape['profile'])
    pack = parity.build_pack(source, legacy=True)
    pack['tool_source_sha256'] = 'a' * 64
    candidate = _candidate(pack)
    assert _compare(pack, candidate)['status'] == 'pass'


def _candidate(pack):
    captures = [{"id": item["id"], "capture": deepcopy(item["production"])} for item in pack["items"]]
    for row in captures:
        capture = row["capture"]
        if "server_instance" in capture:
            capture["server_instance"] = "candidate:234:567"
    return {
        "schema": parity.CANDIDATE_SCHEMA,
        "pack_sha256": _digest(parity.pack_bytes(pack)),
        "capture_source": deepcopy(pack["capture_source"]),
        "runtime": {shape_id: {**runtime, "kernel_commit": "1" * 40, "binary_sha256": "2" * 64}
                    for shape_id, runtime in pack["runtime"].items()},
        "shapes": deepcopy(pack["shapes"]),
        "items": captures,
    }


def _compare(pack, candidate):
    return parity.compare_pack(pack, _digest(parity.pack_bytes(pack)), candidate)


def test_build_is_deterministic_and_pins_observation_only_evidence(source):
    pack = parity.build_pack(source)
    source["items"].reverse()
    source["shapes"].reverse()
    assert parity.pack_bytes(pack) == parity.pack_bytes(parity.build_pack(source))
    assert len(pack["items"]) == 32
    assert len(pack["coverage_matrix"]["dflash_pairs"]) == 4
    assert min(pack["coverage_matrix"]["shape_counts"].values()) == 4
    assert pack["tool_source_sha256"] == _digest(SCRIPT.read_bytes())
    first = pack["items"][0]
    assert first["seed"] == 42
    assert first["request_sha256"] == _request_hash(first["request_body"])
    assert first["prompt_sha256"] == _request_hash(first["request_body"]["prompt"])
    raw = base64.b64decode(first["production"]["response_b64"])
    assert first["production"]["response_sha256"] == _digest(raw)
    assert first["content_sha256"] == _digest(json.loads(raw)["content"].encode("utf-8"))
    assert first["output_token_ids"] == json.loads(raw)["tokens"]

    changed = _candidate(pack)
    for row in changed["items"]:
        output = _response(row["capture"])
        _set_response(row["capture"], {"timings": {"predicted_ms": 999}, **output})
    report = _compare(pack, changed)
    assert report["status"] == "pass"
    assert report["matched_items"] == 32
    assert report["next_action"] == "record_observation"
    assert report["observation_only"] is True
    assert report["quality_transfer_authorized"] is report["promotion_authorized"] is False
    assert report["candidate_runtime"] != report["production_runtime"]


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ("shortfall", "at least 32 distinct requests"),
        ("profile", "missing mandatory serving profiles"),
        ("shape", "four requests per shape"),
        ("length", "missing prompt_shape"),
        ("format", "missing output_format"),
        ("fixture", "missing fixture"),
        ("finish", "missing expected_finish"),
        ("duplicate_id", "duplicate item ID"),
        ("duplicate_shape", "duplicate shape ID"),
        ("duplicate_body", "duplicate canonical request"),
        ("duplicate_pair", "requires exactly two cap arms"),
    ],
)
def test_rejects_missing_or_duplicate_coverage(source, change, error):
    first, second = source["items"][:2]
    if change == "shortfall":
        source["items"].pop()
    elif change == "profile":
        source["shapes"].pop()
    elif change == "shape":
        original = source["shapes"][0]
        source["shapes"].append({**original, "id": "extra-deployed-shape"})
        source["runtime"]["extra-deployed-shape"] = source["runtime"][original["id"]]
    elif change in ("length", "format", "fixture", "finish"):
        for item in source["items"]:
            if change == "length":
                item["prompt_shape"] = "short"
            elif change == "format":
                item["output_format"] = "prose"
            elif change == "fixture":
                item["fixture"] = None
            else:
                item["expected_finish"] = "stop"
                capture = item["production"]
                response = _response(capture)
                if "choices" in response:
                    response["choices"][0]["finish_reason"] = "stop"
                else:
                    response["stop_type"] = "eos"
                _set_response(capture, response)
    elif change == "duplicate_id":
        source["items"].append(first)
    elif change == "duplicate_shape":
        source["shapes"].append(source["shapes"][0])
    elif change == "duplicate_pair":
        dflash_rows = [item for item in source["items"] if item["dflash_pair"]]
        dflash_rows[2]["dflash_pair"] = dflash_rows[0]["dflash_pair"]
    else:
        second["request_body"] = first["request_body"]
    with pytest.raises(ValueError, match=error):
        parity.build_pack(source)


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("request_hash", "request hash mismatch"),
        ("response_hash", "response byte hash mismatch"),
        ("seed", "fixed seed"),
        ("token", "invalid output token IDs"),
        ("validator", "unsupported semantic validator"),
        ("finish", "failed finish or semantic validation"),
        ("echo", "does not echo"),
        ("cap", "effective n_max differs"),
        ("slots", "requires a server instance with -np 1"),
        ("server", "differs in shape, cap-free body, or server instance"),
    ],
)
def test_rejects_corrupt_or_unverifiable_production_capture(source, mutation, error):
    item = next(item for item in source["items"] if item["dflash_pair"])
    capture = item["production"]
    response = _response(capture)
    if mutation in {"request_hash", "response_hash"}:
        capture[f"{mutation.removesuffix('_hash')}_sha256"] = "f" * 64
    elif mutation == "seed":
        item["request_body"]["seed"] = True
    elif mutation == "token":
        response["tokens"][0] = True
        _set_response(capture, response)
    elif mutation == "validator":
        item["validator"]["id"] = "python-expression"
    elif mutation == "finish":
        item["expected_finish"] = "length"
    elif mutation == "echo":
        response["generation_settings"][parity.CAP_KEY] = 9
        _set_response(capture, response)
    elif mutation == "cap":
        capture["effective_n_max"] = 9
    elif mutation == "slots":
        capture["parallel_slots"] = True
    else:
        capture["server_instance"] = "other-instance"
    with pytest.raises(ValueError, match=error):
        parity.build_pack(source)


def test_compare_rejects_mutated_pack_even_with_a_new_digest(source):
    pack = parity.build_pack(source)
    candidate = _candidate(pack)
    pin = _digest(parity.pack_bytes(pack))
    pack["items"][0]["content_sha256"] = "a" * 64
    with pytest.raises(ValueError, match="prospective pin"):
        parity.compare_pack(pack, pin, candidate)
    with pytest.raises(ValueError, match="canonical build"):
        _compare(pack, candidate)


def test_compare_candidate_inventory_and_identity_drift(source):
    pack = parity.build_pack(source)
    candidate = _candidate(pack)
    candidate["items"].append(candidate["items"][0])
    with pytest.raises(ValueError, match="duplicate candidate item ID"):
        _compare(pack, candidate)
    candidate["items"].pop()
    item_id = candidate["items"].pop()["id"]
    report = _compare(pack, candidate)
    assert report["status"] == "incomplete"
    assert report["missing_items"] == [item_id]
    for field in parity.SHAPE_PINS:
        changed = _candidate(pack)
        changed["shapes"][0][field] = "a" * 64
        report = _compare(pack, changed)
        assert report["status"] == "identity_drift"
        assert report["next_action"] == "full_quality_regeneration"


@pytest.mark.parametrize("banked_gap", [False, True])
def test_absent_token_ids_is_incomplete(source, banked_gap):
    capture = source["items"][0]["production"]
    banked = _response(capture)
    if banked_gap:
        del banked["tokens"]
        _set_response(capture, banked)
    pack = parity.build_pack(source)
    candidate = _candidate(pack)
    if not banked_gap:
        row = candidate["items"][0]["capture"]
        response = _response(row)
        del response["tokens"]
        _set_response(row, response)
    report = _compare(pack, candidate)
    assert report["status"] == "incomplete"
    assert report["missing_token_ids"] == [pack["items"][0]["id"]]
    expected = "full_quality_regeneration" if banked_gap else "repeat_affected_role_window"
    assert report["next_action"] == expected


def test_completion_count_requires_complete_exposed_tokens_and_length_budget(source):
    capture = source["items"][0]["production"]
    response = _response(capture)
    response["tokens"].pop()
    _set_response(capture, response)
    with pytest.raises(ValueError, match="count differs from exposed output token IDs"):
        parity.build_pack(source)

    item = source["items"][0]
    response["tokens"].append(2)
    response["stop_type"] = "limit"
    item["request_body"]["n_predict"] += 1
    capture["request_sha256"] = _request_hash(item["request_body"])
    _set_response(capture, response)
    with pytest.raises(ValueError, match="contradicts the pinned token limit"):
        parity.build_pack(source)


def test_compare_with_missing_completion_count_is_incomplete(source):
    pack = parity.build_pack(source)
    candidate = _candidate(pack)
    row = candidate["items"][0]
    response = _response(row["capture"])
    del response["tokens_predicted"]
    _set_response(row["capture"], response)
    report = _compare(pack, candidate)
    assert report["status"] == "incomplete"
    assert report["missing_completion_counts"] == [row["id"]]


@pytest.mark.parametrize(
    ("changed_field", "expected_reason"),
    [("content", "semantic_validation_failed"), ("tokens", "token_ids_mismatch"),
     ("stop_type", "finish_mismatch"), ("reasoning_content", "content_mismatch")],
)
def test_output_mismatch_selects_full_quality_diagnostic(source, changed_field, expected_reason):
    pack = parity.build_pack(source)
    candidate = _candidate(pack)
    if changed_field == "reasoning_content":
        row = next(row for row in candidate["items"] if row["id"].startswith("worker-vision"))
        response = _response(row["capture"])
        response["choices"][0]["message"][changed_field] = "changed reasoning"
    else:
        row = candidate["items"][0]
        response = _response(row["capture"])
        response[changed_field] = {"content": "changed", "tokens": [4, 5, 6], "stop_type": "limit"}[changed_field]
    _set_response(row["capture"], response)
    report = _compare(pack, candidate)
    assert report["status"] == "fail"
    assert report["next_action"] == "full_quality_diagnostic"
    assert expected_reason in report["failures"][row["id"]]
    assert report["quality_transfer_authorized"] is report["promotion_authorized"] is False


def test_cli_publishes_canonical_pack_exclusively_and_reports_observation(source, tmp_path, capsys):
    source_file = tmp_path / "source.json"
    source_file.write_text(json.dumps(source), encoding="utf-8")
    output = tmp_path / "pack.json"
    build = ["build", "--source", str(source_file), "--output", str(output)]
    assert parity.main(build) == 0
    payload = output.read_bytes()
    pin = capsys.readouterr().out.strip()
    assert pin == _digest(payload)
    with pytest.raises(SystemExit, match="2"):
        parity.main(build)
    assert output.read_bytes() == payload

    candidate_file = tmp_path / "candidate.json"
    candidate_file.write_text(json.dumps(_candidate(json.loads(payload))), encoding="utf-8")
    compare = ["compare", "--pack", str(output), "--pack-sha256", pin, "--candidate", str(candidate_file)]
    assert parity.main(compare) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "pass"
    output.write_bytes(payload + b"\n")
    with pytest.raises(SystemExit, match="2"):
        parity.main(compare)
    assert "prospective pin" in capsys.readouterr().err


@pytest.mark.parametrize("invalid", ['{"schema": 1, "schema": 2}', '{"number": 1e999}', '{"number": NaN}'])
def test_cli_rejects_ambiguous_or_nonfinite_input(tmp_path, invalid):
    source_file = tmp_path / "source.json"
    source_file.write_text(invalid, encoding="utf-8")
    output = tmp_path / "pack.json"
    with pytest.raises(SystemExit, match="2"):
        parity.main(["build", "--source", str(source_file), "--output", str(output)])
    assert not output.exists()


@pytest.fixture
def comparison_reader(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPT.parents[4] / "scripts/vidya"))
    from adapters import quality_pack_comparison

    return quality_pack_comparison


@pytest.mark.parametrize(
    ("change", "status", "exit_code", "mismatches"),
    [
        ("none", "pass", 0, 0),
        ("tokens", "fail", 1, 1),
        ("tokens_and_gap", "fail", 1, None),
        ("missing", "incomplete", 2, None),
        ("drift", "identity_drift", 2, None),
        ("bad_candidate", "invalid_input", 2, None),
        ("bad_pin", "invalid_input", 2, None),
    ],
)
def test_cli_captures_native_comparison_dispositions(
    source, tmp_path, capsys, comparison_reader, change, status, exit_code, mismatches,
):
    from claim_tuple import grade

    pack = parity.build_pack(source)
    candidate = _candidate(pack)
    first, second = candidate["items"][:2]
    if change in {"tokens", "tokens_and_gap"}:
        response = _response(first["capture"])
        response["tokens"][0] = 900
        _set_response(first["capture"], response)
        if change == "tokens_and_gap":
            response = _response(second["capture"])
            del response["tokens"]
            _set_response(second["capture"], response)
    elif change == "missing":
        candidate["items"].pop()
    elif change == "drift":
        candidate["shapes"][0]["model_sha256"] = "0" * 64
    pack_file, candidate_file, capture = (tmp_path / name for name in ("pack", "candidate", "comparison"))
    pack_file.write_bytes(parity.pack_bytes(pack))
    raw_candidate = json.dumps(candidate, indent=2).encode() + b"\n\n"
    candidate_file.write_bytes(b'{"schema":' if change == "bad_candidate" else raw_candidate)
    pin = "0" * 64 if change == "bad_pin" else candidate["pack_sha256"]
    args = ["compare", "--pack", str(pack_file), "--pack-sha256", pin, "--candidate",
            str(candidate_file), "--capture", str(capture)]
    if status == "invalid_input":
        with pytest.raises(SystemExit, match="2"):
            parity.main(args)
    else:
        assert parity.main(args) == exit_code
    output = capsys.readouterr()
    payload = capture.read_bytes()
    record = json.loads(payload)
    assert record["validator_source_sha256"] == _digest(SCRIPT.read_bytes())
    for key, path in (("pack", pack_file), ("candidate", candidate_file)):
        assert base64.b64decode(record[key]["bytes_b64"]) == path.read_bytes()
        assert record[key]["sha256"] == _digest(path.read_bytes())
    if status == "invalid_input":
        assert record["report"] is None and record["error"]["status"] == status
    else:
        assert record["error"] is None and record["report"] == json.loads(output.out)
        assert record["report"]["status"] == status
        assert record["coverage"] == pack["coverage_matrix"]
    if status in {"incomplete", "identity_drift", "invalid_input"}:
        assert record["checks"] == {}
    if change in {"tokens", "tokens_and_gap"}:
        assert record["checks"][first["id"]]["tokens_match"] is False
        expected = None if change == "tokens_and_gap" else True
        assert record["checks"][second["id"]]["tokens_match"] is expected
    rows = comparison_reader.native_rows(capture)
    if mismatches is None:
        assert rows == ()
    else:
        row, = rows
        claim = comparison_reader.project(row)
        assert grade(claim)[:2] == ("Judged", "Located")
        assert claim.value == mismatches and claim.extra["checked_items"] == 32
        assert claim.observation["outcome_native"] == status
        assert "Supplied runtime and model identities are declarations." in claim.claim
    with pytest.raises(SystemExit, match="2"):
        parity.main(args)
    assert "File exists" in capsys.readouterr().err
    assert capture.read_bytes() == payload


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ("legacy_report", "sealed comparison requires fields"),
        ("broken_seal", "comparison content seal differs"),
        ("candidate_hash", "original input byte hash"),
        ("validator_hash", "validator source differs"),
        ("checks", "outcome or coverage does not re-derive"),
        ("coverage", "outcome or coverage does not re-derive"),
        ("report", "outcome or coverage does not re-derive"),
    ],
)
def test_comparison_reader_refuses_legacy_or_tampered_native_capture(
    source, tmp_path, comparison_reader, change, error,
):
    from claim_tuple import ProjectionError

    pack = parity.build_pack(source)
    candidate = _candidate(pack)
    capture = tmp_path / "comparison.json"
    parity.capture_comparison(parity.pack_bytes(pack), candidate["pack_sha256"],
                              parity.canonical_json(candidate), capture)
    record = json.loads(capture.read_bytes())
    if change == "legacy_report":
        record = record["report"]
    elif change == "broken_seal":
        record["content_sha256"] = "0" * 64
    else:
        if change == "candidate_hash":
            record["candidate"]["sha256"] = "0" * 64
        elif change == "validator_hash":
            record["validator_source_sha256"] = "0" * 64
        elif change == "checks":
            record["checks"][pack["items"][0]["id"]]["tokens_match"] = False
        elif change == "coverage":
            record["coverage"]["dflash_pairs"].pop()
        else:
            record["report"]["promotion_authorized"] = True
        record.pop("content_sha256")
        record["content_sha256"] = _digest(parity.canonical_json(record))
    capture.write_bytes(parity.pack_bytes(record))
    with pytest.raises(ProjectionError, match=error):
        comparison_reader.native_rows(capture)


def test_capture_keeps_pack_validator_source_pin(source, tmp_path, comparison_reader):
    pack = parity.build_pack(source)
    pack["tool_source_sha256"] = "0" * 64
    candidate = _candidate(pack)
    output = tmp_path / "comparison.json"
    with pytest.raises(ValueError, match="canonical build or tool source"):
        parity.capture_comparison(parity.pack_bytes(pack), candidate["pack_sha256"],
                                  parity.canonical_json(candidate), output)
    record = json.loads(output.read_bytes())
    assert record["report"] is None and record["error"]["status"] == "invalid_input"
    assert comparison_reader.native_rows(output) == ()


def test_assemble_complete_fragments_runs_compare_and_reports_declared_argv(source, tmp_path):
    import subprocess
    import sys
    pack = parity.build_pack(source)
    payload = parity.pack_bytes(pack)
    pin = _digest(payload)
    pack_path = tmp_path / 'pack.json'
    pack_path.write_bytes(payload)
    candidate = _candidate(pack)
    fragments = []
    for shape in pack['shapes']:
        sid = shape['id']
        ids = {item['id'] for item in pack['items'] if item['shape'] == sid}
        fragment = {'schema': 'epyc.ak_gate.parity_fragment.v1', 'pack_sha256': pin, 'arm': 'ON',
                    'shape': sid, 'argv_sha256': '1' * 64, 'runtime': candidate['runtime'][sid],
                    'items': [item for item in candidate['items'] if item['id'] in ids]}
        out = tmp_path / sid / 'out'
        (out / 'parity').mkdir(parents=True)
        path = out / 'parity' / 'ON.fragment.json'
        path.write_text(json.dumps(fragment))
        (out / 'RESULT.json').write_text(json.dumps({'verdict': 'KEEP_ON', 'correctness': {'served_quality': {
            'parity': {'ON': {'fragment_path': 'parity/ON.fragment.json', 'status': 'incomplete'}}}}}))
        fragments.append(str(path))
    cli = SCRIPT.parents[4] / 'scripts/coordination/rowflow/parity_assemble.py'
    proc = subprocess.run([sys.executable, str(cli), '--pack', str(pack_path), '--pack-sha256', pin,
                           '--output-dir', str(tmp_path / 'out'), *fragments], text=True, capture_output=True)
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)['ON']
    assert result['status'] == 'pass'
    assert result['argv_sha256'] == {shape['id']: '1' * 64 for shape in pack['shapes']}
    assert json.loads(Path(result['report_path']).read_text())['status'] == 'pass'
    row = json.loads((tmp_path / pack['shapes'][0]['id'] / 'out' / 'RESULT.json').read_text())
    assert row['verdict'] == 'KEEP_ON'
    assert row['correctness']['served_quality']['parity']['ON']['verdict'] == 'pass'
    assert row['correctness']['served_quality']['parity']['ON']['status'] == 'pass'
    assert row['correctness']['served_quality']['parity']['ON']['report_path'] == result['report_path']
