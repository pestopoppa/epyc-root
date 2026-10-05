"""Tests for server lifecycle abstraction (B6)."""

from unittest.mock import Mock, patch

import pytest

from src.backends.server_lifecycle import (
    LlamaServerLifecycle,
    ServerConfig,
    ServerLifecycle,
    ServerType,
    TGILifecycle,
    VLLMLifecycle,
    get_lifecycle,
)


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


class TestProtocol:
    def test_llama_is_lifecycle(self):
        assert isinstance(LlamaServerLifecycle(), ServerLifecycle)

    def test_vllm_is_lifecycle(self):
        assert isinstance(VLLMLifecycle(), ServerLifecycle)

    def test_tgi_is_lifecycle(self):
        assert isinstance(TGILifecycle(), ServerLifecycle)


# ---------------------------------------------------------------------------
# LlamaServerLifecycle
# ---------------------------------------------------------------------------


class TestLlamaServer:
    def test_server_type(self):
        lc = LlamaServerLifecycle()
        assert lc.server_type == ServerType.LLAMA_SERVER

    def test_capabilities(self):
        lc = LlamaServerLifecycle()
        caps = lc.capabilities
        assert caps.streaming
        assert caps.prefix_caching
        assert caps.slot_management
        assert caps.grammar_constrained

    def test_build_basic_command(self):
        lc = LlamaServerLifecycle()
        config = ServerConfig(
            server_type=ServerType.LLAMA_SERVER,
            model_path="/models/qwen3.gguf",
            port=8080,
            num_slots=4,
            context_length=32768,
            threads=48,
        )
        cmd = lc.build_launch_command(config)
        assert cmd[0] == "llama-server"
        assert "-m" in cmd
        assert "/models/qwen3.gguf" in cmd
        assert "--port" in cmd
        assert "8080" in cmd
        assert "-np" in cmd
        assert "4" in cmd
        assert "-t" in cmd
        assert "48" in cmd

    def test_build_command_with_kv_config(self):
        lc = LlamaServerLifecycle()
        config = ServerConfig(
            server_type=ServerType.LLAMA_SERVER,
            model_path="/models/test.gguf",
            port=8081,
            kv_type_k="q4_0",
            kv_type_v="f16",
            kv_hadamard=True,
        )
        cmd = lc.build_launch_command(config)
        assert "-ctk" in cmd
        assert "q4_0" in cmd
        assert "-ctv" in cmd
        assert "f16" in cmd
        # --kv-hadamard no longer passed (upstream v3 auto-enables)
        assert "--kv-hadamard" not in cmd

    def test_build_command_with_extra_args(self):
        lc = LlamaServerLifecycle()
        config = ServerConfig(
            server_type=ServerType.LLAMA_SERVER,
            model_path="/models/test.gguf",
            port=8082,
            extra_args={"slot-save-path": "/cache/slots", "mlock": True},
        )
        cmd = lc.build_launch_command(config)
        assert "--slot-save-path" in cmd
        assert "/cache/slots" in cmd
        assert "--mlock" in cmd

    def test_build_command_without_gpu(self):
        lc = LlamaServerLifecycle()
        config = ServerConfig(
            server_type=ServerType.LLAMA_SERVER,
            model_path="/models/test.gguf",
            port=8083,
            gpu_layers=0,
        )
        cmd = lc.build_launch_command(config)
        assert "-ngl" in cmd
        assert "0" in cmd

    def test_health_check_failure_reason_on_non_200(self):
        lc = LlamaServerLifecycle()
        mock_resp = Mock(status_code=503)

        with patch("httpx.get", return_value=mock_resp):
            status = lc.health_check("http://localhost:8080")

        assert status.healthy is False
        assert status.failure_reason == "http_status"
        assert "503" in status.failure_detail

    def test_health_check_failure_reason_on_exception(self):
        lc = LlamaServerLifecycle()

        with patch("httpx.get", side_effect=RuntimeError("boom")):
            status = lc.health_check("http://localhost:8080")

        assert status.healthy is False
        assert status.failure_reason == "runtime_error"
        assert "boom" in status.failure_detail


# ---------------------------------------------------------------------------
# VLLM / TGI stubs
# ---------------------------------------------------------------------------


class TestVLLM:
    def test_server_type(self):
        assert VLLMLifecycle().server_type == ServerType.VLLM

    def test_build_command(self):
        lc = VLLMLifecycle()
        config = ServerConfig(
            server_type=ServerType.VLLM,
            model_path="meta-llama/Llama-3-70B",
            port=8000,
            context_length=131072,
        )
        cmd = lc.build_launch_command(config)
        assert "vllm" in " ".join(cmd)
        assert "--model" in cmd
        assert "meta-llama/Llama-3-70B" in cmd


class TestTGI:
    def test_server_type(self):
        assert TGILifecycle().server_type == ServerType.TGI

    def test_build_command(self):
        lc = TGILifecycle()
        config = ServerConfig(
            server_type=ServerType.TGI,
            model_path="some-model",
            port=3000,
            context_length=8192,
        )
        cmd = lc.build_launch_command(config)
        assert "text-generation-launcher" in cmd
        assert "--model-id" in cmd


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestFactory:
    def test_get_llama(self):
        lc = get_lifecycle(ServerType.LLAMA_SERVER)
        assert isinstance(lc, LlamaServerLifecycle)

    def test_get_by_string(self):
        lc = get_lifecycle("llama-server")
        assert isinstance(lc, LlamaServerLifecycle)

    def test_get_vllm(self):
        lc = get_lifecycle(ServerType.VLLM)
        assert isinstance(lc, VLLMLifecycle)

    def test_get_tgi(self):
        lc = get_lifecycle(ServerType.TGI)
        assert isinstance(lc, TGILifecycle)

    def test_invalid_type(self):
        with pytest.raises(ValueError):
            get_lifecycle("unknown-server")
