from __future__ import annotations

import json
from pathlib import Path

from src.edit_transaction import EditResult

from scripts.benchmark import bep_edit_mode_wiring as wiring
from scripts.benchmark import bep_edit_transaction_validate as txn


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")


def test_transaction_header_attests_run_metadata(monkeypatch, tmp_path):
    monkeypatch.setattr(txn, "_orch_head", lambda: "abc123")
    header = txn._attested_header(
        mode="module",
        scratch_root=tmp_path / "scratch",
        task_ids=["t1", "t2"],
        probe_ids=[],
    )

    assert header["kind"] == "attested-run-header"
    assert header["orch_head"] == "abc123"
    assert header["scratch_root"] == str(tmp_path / "scratch")
    assert header["edit_root"] == str(tmp_path / "scratch")
    assert header["task_ids"] == ["t1", "t2"]
    assert header["mode"] == "module"


def test_transaction_failure_classification_covers_hard_buckets():
    assert txn._classify_failure(
        EditResult(ok=False, error="edit scope too large: 99 file(s) exceeds cap (50)"),
        raw="",
        verifier_ok=False,
        llm_error=None,
    ) == "scope-cap reject"
    assert txn._classify_failure(
        EditResult(ok=False, error="no valid file blocks parsed from model output"),
        raw="",
        verifier_ok=False,
        llm_error=None,
    ) == "parse/no blocks"
    assert txn._classify_failure(
        EditResult(ok=False, error="SyntaxError: invalid syntax"),
        raw="<<<FILE: a.py>>>\nX = 1\n<<<END>>>",
        verifier_ok=False,
        llm_error=None,
    ) == "rollback/self-check"
    assert txn._classify_failure(
        EditResult(ok=True),
        raw="<<<FILE: a.py>>>\nX = 1\n<<<END>>>",
        verifier_ok=False,
        llm_error=None,
    ) == "verifier fail"
    assert txn._classify_failure(
        None,
        raw="",
        verifier_ok=False,
        llm_error=txn.ChatHTTPError(412, "precondition"),
    ) == "412/precondition"


def test_transaction_main_emits_attested_header_and_summary(monkeypatch, tmp_path, capsys):
    tasks_path = tmp_path / "tasks.jsonl"
    solutions_path = tmp_path / "solutions.jsonl"
    scratch = tmp_path / "scratch"
    _write_jsonl(tasks_path, [{
        "id": "tmini",
        "prompt": "Update a.py",
        "files": {"a.py": "X = 1\n"},
        "verifier_cmd": "true",
    }])
    _write_jsonl(solutions_path, [{
        "id": "tmini",
        "write": {"a.py": "X = 2\n"},
        "delete": [],
    }])

    monkeypatch.setattr(txn, "TASKS_PATH", tasks_path)
    monkeypatch.setattr(txn, "SOLUTIONS_PATH", solutions_path)
    monkeypatch.setattr(txn, "_orch_head", lambda: "abc123")
    monkeypatch.setattr(txn, "_run_verifier", lambda root, cmd: True)

    code = txn.main(["--mode", "module", "--scratch-root", str(scratch)])
    out = capsys.readouterr().out

    assert code == 0
    assert "[attest]" in out
    assert '"mode": "module"' in out
    assert '"bucket": "pass"' in out
    assert '"task_id": "tmini"' in out
    assert "[summary] edit-transaction 1/1 pass" in out


def test_transaction_main_rolls_back_on_in_transaction_verifier_failure(monkeypatch, tmp_path, capsys):
    tasks_path = tmp_path / "tasks.jsonl"
    solutions_path = tmp_path / "solutions.jsonl"
    scratch = tmp_path / "scratch"
    _write_jsonl(tasks_path, [{
        "id": "tmini",
        "prompt": "Update a.py",
        "files": {"a.py": "X = 1\n"},
        "verifier_cmd": "false",
    }])
    _write_jsonl(solutions_path, [{
        "id": "tmini",
        "write": {"a.py": "X = 2\n"},
        "delete": [],
    }])

    monkeypatch.setattr(txn, "TASKS_PATH", tasks_path)
    monkeypatch.setattr(txn, "SOLUTIONS_PATH", solutions_path)
    monkeypatch.setattr(txn, "_orch_head", lambda: "abc123")
    monkeypatch.setattr(txn, "_run_verifier", lambda root, cmd: False)

    code = txn.main(["--mode", "module", "--scratch-root", str(scratch)])
    out = capsys.readouterr().out

    assert code == 0
    assert '"bucket": "verifier fail"' in out
    assert '"txn_ok": false' in out
    assert "[summary] edit-transaction 0/1 pass" in out
    assert (scratch / "a.py").read_text() == "X = 1\n"


def test_wiring_header_attests_run_metadata(monkeypatch, tmp_path):
    monkeypatch.setattr(wiring, "_orch_head", lambda: "abc123")
    header = wiring._attested_header(
        mode="stub",
        edit_root=tmp_path / "root",
        task_ids=["t1"],
        probe_ids=["t1_create_util"],
    )

    assert header["kind"] == "attested-run-header"
    assert header["orch_head"] == "abc123"
    assert header["edit_root"] == str(tmp_path / "root")
    assert header["probe_ids"] == ["t1_create_util"]
    assert header["mode"] == "stub"


def test_wiring_failure_classification_covers_hard_buckets():
    assert wiring._classify_failure(
        result=EditResult(ok=False, error="edit scope too large: 99 file(s) exceeds cap (50)"),
        response_mode="edit",
        response_text="",
        verifier_ok=False,
        llm_error=None,
    ) == "scope-cap reject"
    assert wiring._classify_failure(
        result=EditResult(ok=False, error="no valid file blocks parsed from model output"),
        response_mode="edit",
        response_text="",
        verifier_ok=False,
        llm_error=None,
    ) == "parse/no blocks"
    assert wiring._classify_failure(
        result=EditResult(ok=False, error="SyntaxError: invalid syntax"),
        response_mode="edit",
        response_text="<<<FILE: a.py>>>\nX = 1\n<<<END>>>",
        verifier_ok=False,
        llm_error=None,
    ) == "rollback/self-check"
    assert wiring._classify_failure(
        result=EditResult(ok=True),
        response_mode="edit",
        response_text="<<<FILE: a.py>>>\nX = 1\n<<<END>>>",
        verifier_ok=False,
        llm_error=None,
    ) == "verifier fail"
    assert wiring._classify_failure(
        result=None,
        response_mode=None,
        response_text="",
        verifier_ok=False,
        llm_error=wiring.ChatHTTPError(412, "precondition"),
    ) == "412/precondition"


def test_wiring_main_emits_attested_header_and_summary(monkeypatch, tmp_path, capsys):
    tasks_path = tmp_path / "tasks.jsonl"
    solutions_path = tmp_path / "solutions.jsonl"
    root = tmp_path / "root"
    _write_jsonl(tasks_path, [{
        "id": "t1_create_util",
        "prompt": "Create util",
        "files": {"mathutil.py": "def add(a, b):\n    return a + b\n"},
        "verifier_cmd": "true",
    }])
    _write_jsonl(solutions_path, [{
        "id": "t1_create_util",
        "write": {"mathutil.py": "def add(a, b):\n    return a + b\n"},
        "delete": [],
    }])

    monkeypatch.setattr(wiring, "TASKS_PATH", tasks_path)
    monkeypatch.setattr(wiring, "SOLUTIONS_PATH", solutions_path)
    monkeypatch.setattr(wiring, "PROBE_IDS", ["t1_create_util"])
    monkeypatch.setattr(wiring, "_orch_head", lambda: "abc123")
    monkeypatch.setattr(wiring, "_run_verifier", lambda root, cmd: True)

    code = wiring.main(["--mode", "stub", "--edit-root", str(root)])
    out = capsys.readouterr().out

    assert code == 0
    assert "[attest]" in out
    assert '"mode": "stub"' in out
    assert '"bucket": "pass"' in out
    assert '"response_mode": "edit"' in out
    assert "[summary] edit-mode wiring 1/1 pass" in out


def test_wiring_stub_rolls_back_on_in_transaction_verifier_failure(monkeypatch, tmp_path, capsys):
    tasks_path = tmp_path / "tasks.jsonl"
    solutions_path = tmp_path / "solutions.jsonl"
    root = tmp_path / "root"
    _write_jsonl(tasks_path, [{
        "id": "t1_create_util",
        "prompt": "Update util",
        "files": {"mathutil.py": "def add(a, b):\n    return 0\n"},
        "verifier_cmd": "false",
    }])
    _write_jsonl(solutions_path, [{
        "id": "t1_create_util",
        "write": {"mathutil.py": "def add(a, b):\n    return a + b\n"},
        "delete": [],
    }])

    monkeypatch.setattr(wiring, "TASKS_PATH", tasks_path)
    monkeypatch.setattr(wiring, "SOLUTIONS_PATH", solutions_path)
    monkeypatch.setattr(wiring, "PROBE_IDS", ["t1_create_util"])
    monkeypatch.setattr(wiring, "_orch_head", lambda: "abc123")
    monkeypatch.setattr(wiring, "_run_verifier", lambda root, cmd: False)

    code = wiring.main(["--mode", "stub", "--edit-root", str(root)])
    out = capsys.readouterr().out

    assert code == 0
    assert '"bucket": "verifier fail"' in out
    assert "[summary] edit-mode wiring 0/1 pass" in out
    assert (root / "mathutil.py").read_text() == "def add(a, b):\n    return 0\n"
