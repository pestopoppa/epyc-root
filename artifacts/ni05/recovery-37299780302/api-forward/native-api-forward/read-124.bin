"""Additional branch coverage for scripts.lib.executor execution paths."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from scripts.lib.executor import Config, Executor, ServerManager


def test_server_manager_run_inference_parses_sse_and_includes_spec_n_max():
    manager = ServerManager(port=9999, registry=MagicMock(data={}))
    session = MagicMock()

    response = MagicMock(status_code=200, text="")
    response.iter_lines.return_value = iter(
        [
            "",
            "data: not-json",
            (
                'data: {"content":"ok","stop":true,'
                '"timings":{"predicted_per_second":12.5,"prompt_n":2,"predicted_n":1,"predicted_ms":7.0}}'
            ),
        ]
    )
    session.post.return_value = response
    manager._http_session = session

    result = manager.run_inference("prompt", speculative_n_max=7, timeout=1)

    assert result.success is True
    assert result.tokens_per_second == 12.5
    assert "tokens per second" in result.raw_output
    payload = session.post.call_args.kwargs["json"]
    assert payload["speculative.n_max"] == 7


def test_server_manager_run_inference_timeout_without_partial_marks_timeout():
    manager = ServerManager(port=9999, registry=MagicMock(data={}))
    session = MagicMock()
    session.post.side_effect = requests.exceptions.Timeout("timeout")
    manager._http_session = session

    result = manager.run_inference("prompt", timeout=1)

    assert result.success is False
    assert result.timed_out is True
    assert result.partial is False
    assert result.failure_reason == "timeout"


def test_server_manager_run_inference_request_error_after_partial_keeps_partial():
    manager = ServerManager(port=9999, registry=MagicMock(data={}))
    session = MagicMock()

    response = MagicMock(status_code=200, text="")
    response.iter_lines.return_value = iter(
        [
            'data: {"content":"partial"}',
            requests.exceptions.RequestException("stream dropped"),
        ]
    )

    def _iter_lines(*args, **kwargs):  # noqa: ANN001
        yield 'data: {"content":"partial"}'
        raise requests.exceptions.RequestException("stream dropped")

    response.iter_lines.side_effect = _iter_lines
    session.post.return_value = response
    manager._http_session = session

    result = manager.run_inference("prompt", timeout=1)

    assert result.timed_out is True
    assert result.partial is True
    assert result.failure_reason == "timeout_partial"
    assert "partial" in result.raw_output


def test_server_manager_vl_success_with_image_uses_client_tps_fallback():
    manager = ServerManager(port=9999, registry=MagicMock(data={}))
    manager.mmproj_path = "mmproj.gguf"
    session = MagicMock()
    session.post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(
            return_value={
                "choices": [{"message": {"content": "vision answer"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 10},
                "timings": {},
            }
        ),
    )
    manager._http_session = session

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as img:
        img.write(b"\xff\xd8\xff\xd9")
        image_path = img.name

    try:
        with patch("scripts.lib.executor.time.time", side_effect=[100.0, 101.0]):
            result = manager.run_inference("describe", image_path=image_path, timeout=1)
    finally:
        Path(image_path).unlink(missing_ok=True)

    assert result.success is True
    assert result.tokens_per_second == 10.0
    assert "vision answer" in result.raw_output
    payload = session.post.call_args.kwargs["json"]
    content_items = payload["messages"][0]["content"]
    image_item = next(item for item in content_items if item["type"] == "image_url")
    assert image_item["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_executor_build_command_spec_uses_spec_binary_without_no_conversation():
    executor = Executor(registry=MagicMock(), validate=False)
    cfg = Config.spec(8, "/models/draft.gguf")

    def _binary(name, registry=None):  # noqa: ANN001
        mapping = {
            "speculative": "/bin/llama-speculative",
            "lookup": "/bin/llama-lookup",
            "completion": "/bin/llama-completion",
        }
        return mapping[name]

    with (
        patch("scripts.lib.executor._numa_prefix", return_value=[]),
        patch("scripts.lib.executor.get_binary", side_effect=_binary),
    ):
        cmd = executor.build_command("model.gguf", cfg, "/tmp/prompt.txt")

    assert cmd[0] == "/bin/llama-speculative"
    assert "--no-conversation" not in cmd
    assert "-md" in cmd and "/models/draft.gguf" in cmd
    assert "--spec-draft-n-max" in cmd and "8" in cmd


def test_executor_build_command_spec_omits_same_file_md_for_embedded_nextn():
    executor = Executor(registry=MagicMock(), validate=False)
    cfg = Config.spec(4, "/models/qwen-mtp.gguf")

    def _binary(name, registry=None):  # noqa: ANN001
        mapping = {
            "speculative": "/bin/llama-speculative",
            "lookup": "/bin/llama-lookup",
            "completion": "/bin/llama-completion",
        }
        return mapping[name]

    with (
        patch("scripts.lib.executor._numa_prefix", return_value=[]),
        patch("scripts.lib.executor.get_binary", side_effect=_binary),
    ):
        cmd = executor.build_command("/models/qwen-mtp.gguf", cfg, "/tmp/prompt.txt")

    assert cmd[0] == "/bin/llama-speculative"
    assert "-md" not in cmd
    assert cmd[cmd.index("--spec-type") + 1] == "draft-mtp"
    assert cmd[cmd.index("--spec-draft-n-max") + 1] == "4"


def test_executor_build_command_moe_lookup_includes_lookup_and_override_flags():
    executor = Executor(registry=MagicMock(), validate=False)
    cfg = Config.compound_moe_lookup(4, "qwen3moe.expert_used_count", 5)

    def _binary(name, registry=None):  # noqa: ANN001
        mapping = {
            "speculative": "/bin/llama-speculative",
            "lookup": "/bin/llama-lookup",
            "completion": "/bin/llama-completion",
        }
        return mapping[name]

    with (
        patch("scripts.lib.executor._numa_prefix", return_value=[]),
        patch("scripts.lib.executor.get_binary", side_effect=_binary),
    ):
        cmd = executor.build_command("model.gguf", cfg, "/tmp/prompt.txt")

    assert cmd[0] == "/bin/llama-lookup"
    assert "--draft-max" in cmd and "5" in cmd
    assert "--override-kv" in cmd
    assert "qwen3moe.expert_used_count=int:4" in cmd


def test_get_configs_for_dense_adds_spec_and_lookup_speed_variants():
    executor = Executor(registry=MagicMock(), validate=False)
    reg = MagicMock()
    reg.get_forbidden_configs.return_value = []
    reg.get_drafts_for_model.return_value = ["draft_small"]
    reg.get_role_config.return_value = {"tier": "B", "model": {"size_gb": 10}}
    reg.get_model_path.side_effect = lambda role: "/models/draft.gguf" if role == "draft_small" else "/models/main.gguf"

    with patch("os.path.exists", return_value=True):
        configs = executor.get_configs_for_architecture("dense", "main", registry=reg)

    names = {cfg.name for cfg in configs}
    assert "baseline" in names
    assert "spec_draft_small_k4" in names
    assert "spec_draft_small_k48" in names
    assert "lookup_n3" in names and "lookup_n4" in names and "lookup_n5" in names
    for cfg in configs:
        if cfg.config_type in {"spec", "lookup"}:
            assert cfg.speed_test_only is True


def test_get_configs_for_moe_respects_forbidden_lookup_and_spec():
    executor = Executor(registry=MagicMock(), validate=False)
    reg = MagicMock()
    reg.get_forbidden_configs.return_value = ["prompt_lookup", "speculative_decoding"]
    reg.get_moe_override_key.return_value = "qwen3moe.expert_used_count"
    reg.get_baseline_experts.return_value = 8

    configs = executor.get_configs_for_architecture("qwen3moe", "worker", registry=reg)

    names = [cfg.name for cfg in configs]
    assert names == ["baseline", "moe4", "moe6"]


def test_get_configs_for_ssm_moe_hybrid_adds_only_moe_variants():
    executor = Executor(registry=MagicMock(), validate=False)
    reg = MagicMock()
    reg.get_forbidden_configs.return_value = []
    reg.get_moe_override_key.return_value = "qwen3moe.expert_used_count"
    reg.get_baseline_experts.return_value = 6

    configs = executor.get_configs_for_architecture("ssm_moe_hybrid", "worker", registry=reg)

    names = [cfg.name for cfg in configs]
    assert names == ["baseline", "moe4"]


def test_compound_moe_spec_uses_draft_stem_when_name_missing():
    cfg = Config.compound_moe_spec(
        experts=4,
        override_key="qwen3moe.expert_used_count",
        k=8,
        draft_path="/models/draft-small.gguf",
        draft_name="",
    )
    assert cfg.name == "moe4_spec_draft-small_k8"


def test_get_configs_for_moe_adds_lookup_and_spec_compounds_from_drafts():
    executor = Executor(registry=MagicMock(), validate=False)
    reg = MagicMock()
    reg.get_forbidden_configs.return_value = []
    reg.get_moe_override_key.return_value = "qwen3moe.expert_used_count"
    reg.get_baseline_experts.return_value = 8
    reg.get_drafts_for_model.return_value = ["draft_role"]
    reg.get_model_path.side_effect = (
        lambda role: "/models/main.gguf" if role == "worker" else "/models/draft.gguf"
    )
    reg.get_role_config.side_effect = (
        lambda role: {"model": {"size_gb": 0}} if role == "worker" else {"tier": "D"}
    )

    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.getsize", return_value=10 * (1024**3)),
    ):
        configs = executor.get_configs_for_architecture("qwen3moe", "worker", registry=reg)

    names = {cfg.name for cfg in configs}
    assert "moe4_lookup_n4" in names
    assert "moe4_spec_draft_role_k8" in names
    assert "moe4_spec_draft_role_k16" in names
    assert "moe4_spec_draft_role_k24" in names


def test_build_command_completion_moe_and_moe_spec_flags():
    executor = Executor(registry=MagicMock(), validate=False)

    def _binary(name, registry=None):  # noqa: ANN001
        mapping = {
            "speculative": "/bin/llama-speculative",
            "lookup": "/bin/llama-lookup",
            "completion": "/bin/llama-completion",
        }
        return mapping[name]

    with (
        patch("scripts.lib.executor._numa_prefix", return_value=[]),
        patch("scripts.lib.executor.get_binary", side_effect=_binary),
    ):
        baseline_cmd = executor.build_command("model.gguf", Config.baseline(), "/tmp/prompt.txt")
        moe_cmd = executor.build_command(
            "model.gguf",
            Config.moe(4, "qwen3moe.expert_used_count"),
            "/tmp/prompt.txt",
        )
        moe_spec_cmd = executor.build_command(
            "model.gguf",
            Config.compound_moe_spec(
                4, "qwen3moe.expert_used_count", 8, "/models/draft.gguf", "draft"
            ),
            "/tmp/prompt.txt",
        )

    assert baseline_cmd[0] == "/bin/llama-completion"
    assert "--no-conversation" in baseline_cmd
    assert "--override-kv" in moe_cmd
    assert "qwen3moe.expert_used_count=int:4" in moe_cmd
    assert "-md" in moe_spec_cmd and "/models/draft.gguf" in moe_spec_cmd
    assert "--spec-draft-n-max" in moe_spec_cmd
    assert "--override-kv" in moe_spec_cmd
