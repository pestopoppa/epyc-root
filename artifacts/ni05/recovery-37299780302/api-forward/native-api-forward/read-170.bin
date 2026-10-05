"""Tests for ColBERT export/download artifact profiles."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from scripts.benchmark.colbert import export_lateon_onnx_int8 as export


def test_lateon_profile_declares_prebuilt_onnx_runtime_files():
    profile = export.resolve_profile("lateon")

    assert profile.repo_id == "lightonai/LateOn"
    assert profile.ships_prebuilt_onnx is True
    assert "model_int8.onnx" in profile.download_files
    assert profile.default_out == Path("/mnt/raid0/llm/models/lateon-onnx-int8")


def test_reason_mxbai_profile_is_source_only():
    profile = export.resolve_profile("reason-mxbai")

    assert profile.repo_id == "DataScience-UIBK/Reason-mxbai-colbert-v0-32m"
    assert profile.ships_prebuilt_onnx is False
    assert "model.safetensors" in profile.download_files
    assert "model_int8.onnx" not in profile.download_files
    assert profile.model_slot_env == "REASON_MXBAI_MODEL_PATH"


def test_known_model_id_selects_matching_profile():
    profile = export.resolve_profile(
        "lateon",
        "DataScience-UIBK/Reason-mxbai-colbert-v0-32m",
    )

    assert profile.name == "reason-mxbai"


def test_custom_model_id_reuses_selected_manifest():
    profile = export.resolve_profile("reason-mxbai", "example/custom-colbert")

    assert profile.name == "custom:example/custom-colbert"
    assert profile.repo_id == "example/custom-colbert"
    assert profile.ships_prebuilt_onnx is False
    assert profile.download_files == export.MODEL_PROFILES["reason-mxbai"].download_files


def test_artifact_plan_is_serializable():
    profile = export.resolve_profile("reason-mxbai")
    plan = export.artifact_plan(profile, Path("/tmp/reason"))

    assert plan["profile"] == "reason-mxbai"
    assert plan["out"] == "/tmp/reason"
    assert plan["runtime_files"] == ["model_int8.onnx", "tokenizer.json"]


def test_source_only_profile_fails_fast_without_onnx(tmp_path):
    profile = export.resolve_profile("reason-mxbai")
    (tmp_path / "tokenizer.json").write_text("{}", encoding="utf-8")

    with pytest.raises(export.OnnxArtifactsMissingError, match="does not ship"):
        export.ensure_onnx_artifacts(tmp_path, profile)


def test_print_plan_json_does_not_download(capsys):
    rc = export.main(["--profile", "reason-mxbai", "--print-plan", "--json"])

    assert rc == 0
    out = capsys.readouterr().out
    assert '"profile": "reason-mxbai"' in out
    assert '"ships_prebuilt_onnx": false' in out


def test_main_returns_export_required_for_source_only_parity(tmp_path):
    rc = export.main([
        "--profile",
        "reason-mxbai",
        "--out",
        str(tmp_path),
        "--no-download",
    ])

    assert rc == 3


def test_reason_mxbai_artifact_plan_includes_export_contract():
    profile = export.resolve_profile("reason-mxbai")
    plan = export.artifact_plan(profile, Path("/tmp/reason"))
    export_plan = plan["export_plan"]

    assert export_plan["fp32_onnx"] == "/tmp/reason/model.onnx"
    assert export_plan["int8_onnx"] == "/tmp/reason/model_int8.onnx"
    assert export_plan["input_names"] == ["input_ids", "attention_mask"]
    assert export_plan["output_names"] == ["token_embeddings"]
    assert export_plan["opset"] == 18
    assert export_plan["dynamic_axes"]["token_embeddings"] == {0: "batch", 1: "sequence"}
    assert export_plan["required_dependencies"] == [
        "torch",
        "onnx",
        "onnxscript",
        "onnxruntime",
        "pylate",
    ]


def test_wrapper_calls_pylate_with_feature_dict():
    calls = []

    class FakePyLateModel:
        def __call__(self, features):
            calls.append(features)
            return {"token_embeddings": "embeddings"}

    wrapper = export.PyLateColBERTTokenEmbeddingsWrapper(FakePyLateModel())

    assert wrapper("ids", "mask") == "embeddings"
    assert calls == [{"input_ids": "ids", "attention_mask": "mask"}]


def test_wrapper_extracts_token_embeddings_from_pylate_output_types():
    assert export.PyLateColBERTTokenEmbeddingsWrapper._extract_token_embeddings({
        "token_embeddings": "by-key"
    }) == "by-key"
    assert export.PyLateColBERTTokenEmbeddingsWrapper._extract_token_embeddings(["first", "second"]) == "first"
    assert export.PyLateColBERTTokenEmbeddingsWrapper._extract_token_embeddings(
        types.SimpleNamespace(token_embeddings="via-attr")
    ) == "via-attr"


def test_quantize_onnx_int8_calls_quantize_dynamic_with_contract_paths(monkeypatch, tmp_path):
    calls = {}
    fake_quant_mod = types.ModuleType("onnxruntime.quantization")

    def fake_quantize_dynamic(model_input, model_output, *, per_channel, op_types_to_quantize, weight_type):
        calls["model_input"] = model_input
        calls["model_output"] = model_output
        calls["per_channel"] = per_channel
        calls["op_types_to_quantize"] = tuple(op_types_to_quantize)
        calls["weight_type"] = weight_type

    fake_quant_mod.quantize_dynamic = fake_quantize_dynamic
    fake_quant_mod.QuantType = types.SimpleNamespace(QInt8="QINT8")
    fake_onnxruntime = types.ModuleType("onnxruntime")
    fake_onnxruntime.quantization = fake_quant_mod
    monkeypatch.setitem(sys.modules, "onnxruntime", fake_onnxruntime)
    monkeypatch.setitem(sys.modules, "onnxruntime.quantization", fake_quant_mod)

    source = tmp_path / "model.onnx"
    target = tmp_path / "model_int8.onnx"
    source.write_text("fp32", encoding="utf-8")

    result = export.quantize_onnx_int8(source, target, per_channel=True, op_types_to_quantize=("MatMul",))

    assert result == target
    assert calls["model_input"] == str(source)
    assert calls["model_output"] == str(target)
    assert calls["per_channel"] is True
    assert calls["op_types_to_quantize"] == ("MatMul",)
    assert calls["weight_type"] == "QINT8"


def test_export_int8_option_fails_fast_on_missing_deps(tmp_path, monkeypatch):
    monkeypatch.setattr(export, "_require_reason_mxbai_export_dependencies", lambda: (_ for _ in ()).throw(
        export.ExportDependencyError("missing deps"),
    ))

    rc = export.main([
        "--profile",
        "reason-mxbai",
        "--out",
        str(tmp_path),
        "--no-download",
        "--export-int8",
        "--no-parity",
    ])

    assert rc == 4
