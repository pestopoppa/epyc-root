"""Tests for factual-risk calibration v2 builder helpers."""

from __future__ import annotations

import sys
import json

from scripts import build_factual_risk_calibration_v2 as builder


def test_import_huggingface_datasets_ignores_local_scripts_package(
    tmp_path,
    monkeypatch,
) -> None:
    scripts_dir = tmp_path / "scripts"
    local_pkg = scripts_dir / "datasets"
    local_pkg.mkdir(parents=True)
    (local_pkg / "__init__.py").write_text("LOCAL = True\n", encoding="utf-8")

    site_dir = tmp_path / "site"
    hf_pkg = site_dir / "datasets"
    hf_pkg.mkdir(parents=True)
    (hf_pkg / "__init__.py").write_text(
        "def load_dataset(*args, **kwargs):\n"
        "    return []\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(builder, "SCRIPT_DIR", scripts_dir)
    monkeypatch.setattr(sys, "path", [str(scripts_dir), str(site_dir)])
    monkeypatch.delitem(sys.modules, "datasets", raising=False)

    module = builder._import_huggingface_datasets()

    assert module.load_dataset() == []
    assert str(hf_pkg) in str(module.__file__)
    assert sys.path == [str(scripts_dir), str(site_dir)]


def test_write_jsonl_streaming_escapes_unicode_line_separators(tmp_path) -> None:
    path = tmp_path / "rows.jsonl"

    builder.write_jsonl_streaming(
        path,
        [{"prompt": "alpha\u2028beta", "label_source": "test"}],
    )

    text = path.read_text(encoding="utf-8")
    assert "\\u2028" in text
    rows = [json.loads(line) for line in text.splitlines()]
    assert rows == [{"prompt": "alpha\u2028beta", "label_source": "test"}]
