"""Tests for compiling model-capability descriptors from registries."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.registry.model_descriptors import (
    DescriptorCompileError,
    _canonical_model_id,
    _first_model_native_context_value,
    compile_model_descriptors,
    write_model_descriptors,
)


def _write_yaml(path: Path, data: dict) -> Path:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_canonical_model_id_matches_stable_descriptor_policy() -> None:
    assert _canonical_model_id("Qwen3.6-35B-A3B-Q8_0", "Q8_0") == "qwen3.6-35b-a3b-q8_0"
    assert (
        _canonical_model_id("gemma-4-26B-A4B-it-Q4_K_M", "Q4_K_M")
        == "gemma4-26b-a4b-q4_k_m"
    )
    assert (
        _canonical_model_id("Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf", "Q4_K_M")
        == "qwen3-next-80b-a3b-q4_k_m"
    )
    assert (
        _canonical_model_id("Qwen2.5-VL-7B-Instruct", "Q4_K_M")
        == "qwen2.5-vl-7b-q4_k_m"
    )


def test_compile_merges_same_model_roles(tmp_path: Path) -> None:
    registry_path = _write_yaml(
        tmp_path / "model_registry.yaml",
        {
            "server_mode": {
                "frontdoor": {
                    "port": 8070,
                    "model": "Qwen_Qwen3.6-35B-A3B-Q8_0.gguf",
                    "model_path": "/models/Qwen_Qwen3.6-35B-A3B-Q8_0.gguf",
                    "model_role": "frontdoor",
                    "memory_gb": 37,
                    "throughput": 24.3,
                    "benchmark_score": "170/183 (92.9%)",
                    "benchmark_date": "2026-05-04",
                    "chat_template_kwargs": {"enable_thinking": False},
                    "kv_quant": {"k": "q8_0", "v": "q8_0"},
                    "numa_instances": 1,
                    "numa_ports": [8080],
                },
                "coder_escalation": {
                    "port": 8070,
                    "model": "Qwen_Qwen3.6-35B-A3B-Q8_0.gguf",
                    "model_path": "/models/Qwen_Qwen3.6-35B-A3B-Q8_0.gguf",
                    "model_role": "coder_escalation",
                    "memory_gb": 37,
                    "throughput": 24.3,
                    "benchmark_score": "29/30 (97%)",
                    "chat_template_kwargs": {"enable_thinking": False},
                    "kv_quant": {"k": "q8_0", "v": "q8_0"},
                    "numa_instances": 1,
                },
            },
            "roles": {
                "frontdoor": {
                    "model": {
                        "name": "Qwen3.6-35B-A3B-Q8_0",
                        "quant": "Q8_0",
                        "architecture": "qwen35moe",
                        "size_gb": 37,
                        "ctx_max": 131072,
                        "n_layer": 64,
                        "attention_layers": 16,
                    },
                    "performance": {"quality_pct": 93, "baseline_tps": 24.3},
                    "acceleration": {"type": "none", "lookup": False},
                    "memory": {"pinned": True},
                },
                "coder_escalation": {
                    "model": {
                        "name": "Qwen3.6-35B-A3B-Q8_0",
                        "quant": "Q8_0",
                        "architecture": "qwen35moe",
                        "size_gb": 37,
                        "ctx_max": 131072,
                    },
                    "performance": {"coder_suite": "29/30 (97%)"},
                    "acceleration": {"type": "none", "lookup": False},
                    "memory": {"pinned": True},
                },
                "worker_summarize": {
                    "model": {
                        "name": "Qwen3.6-35B-A3B-Q8_0",
                        "quant": "Q8_0",
                        "architecture": "qwen35moe",
                        "size_gb": 37,
                        "ctx_max": 131072,
                    },
                    "performance": {"long_context": "27/27 (100%)"},
                    "acceleration": {"type": "none", "lookup": False},
                    "memory": {"pinned": True},
                },
            },
        },
    )

    compiled = compile_model_descriptors(
        lean_registry_path=registry_path,
        research_registry_path=None,
        active_roles={"frontdoor", "coder_escalation", "worker_summarize"},
    )

    assert compiled["status"] == "compiled"
    assert len(compiled["models"]) == 1
    model = compiled["models"][0]
    assert model["model_id"] == "qwen3.6-35b-a3b-q8_0"
    assert model["role_bindings"]["roles"] == [
        "coder_escalation",
        "frontdoor",
        "worker_summarize",
    ]
    assert model["role_bindings"]["server_roles"] == ["coder_escalation", "frontdoor"]
    # 0.8387, not the registry's 0.93: `overall` is now the mean over the
    # fixed universal benchmark set (mmlu_pro, gpqa_diamond,
    # livecodebench_v6) from orchestration/public_benchmarks.yaml, which
    # every fleet model reports. The registry figure came from our canonical
    # judge suite, which only ever ran on two of six models and is 74%
    # ceiling-saturated, so it cannot rank the fleet. Nothing is lost: the
    # local measurement is preserved verbatim under quality_by_axis.local.
    assert model["quality"]["suite_vector"]["overall"] == 0.8387
    assert model["quality"]["suite_vector"]["coder"] == 0.9667
    assert model["quality"]["suite_vector"]["long_context"] == 1.0
    assert model["architecture"] == {
        "n_layers": 64,
        "attention_layers": 16,
        "source": "registry.model",
    }
    assert not any("server" in gap or "port" in gap for gap in model["known_gaps"])


def test_compile_projects_quality_score_as_overall_quality(tmp_path: Path) -> None:
    registry_path = _write_yaml(
        tmp_path / "model_registry.yaml",
        {
            "server_mode": {
                "architect_general": {
                    "port": 8083,
                    "model": "Qwen3.5-122B-A10B-Q4_K_M-00001-of-00003.gguf",
                    "model_role": "architect_general",
                    "throughput": 12.19,
                    "chat_template_kwargs": {"enable_thinking": False},
                }
            },
            "roles": {
                "architect_general": {
                    "model": {
                        "name": "Qwen3.5-122B-A10B",
                        "quant": "Q4_K_M",
                        "architecture": "qwen35moe",
                        "size_gb": 69,
                        "ctx_max": 16384,
                    },
                    "performance": {"quality_score": "2.57/3", "baseline_tps": 5.3},
                    "acceleration": {
                        "type": "moe_expert_reduction",
                        "override_key": "qwen35moe.expert_used_count",
                        "experts": 8,
                    },
                    "memory": {"pinned": True},
                },
            },
        },
    )

    compiled = compile_model_descriptors(
        lean_registry_path=registry_path,
        research_registry_path=None,
        active_roles={"architect_general"},
    )

    model = compiled["models"][0]
    # 0.8407 from the universal benchmark mean; see the note above on why
    # public benchmarks outrank a registry scalar for the RANKING figure.
    assert model["quality"]["suite_vector"]["overall"] == 0.8407
    assert model["quality"]["measured"][0]["value"]["quality_score"] == "2.57/3"
    assert compiled["status"] == "compiled"


def test_compile_accepts_structured_thinking_control_evidence(tmp_path: Path) -> None:
    registry_path = _write_yaml(
        tmp_path / "model_registry.yaml",
        {
            "server_mode": {
                "ingest_long_context": {
                    "port": 8085,
                    "model": "Qwen3-Next-80B-A3B-Q4_K_M.gguf",
                    "model_role": "ingest_long_context",
                    "memory_gb": 45,
                    "throughput": 14.4,
                    "thinking_control": {
                        "mode": "template_ignores_enable_thinking",
                        "effective_mode": "native",
                        "evidence": "registry note: current GGUF template ignores enable_thinking",
                    },
                }
            },
            "roles": {
                "ingest_long_context": {
                    "model": {
                        "name": "Qwen3-Next-80B-A3B-Instruct",
                        "quant": "Q4_K_M",
                        "architecture": "ssm_moe_hybrid",
                        "size_gb": 45,
                        "ctx_max": 262144,
                    },
                    "performance": {
                        "long_context_quality": "25/27 (93%)",
                        "baseline_tps": 10.12,
                    },
                    "acceleration": {
                        "type": "moe_expert_reduction",
                        "experts": 4,
                    },
                    "memory": {"residency": "hot", "pinned": True},
                }
            },
        },
    )

    compiled = compile_model_descriptors(
        lean_registry_path=registry_path,
        research_registry_path=None,
        active_roles={"ingest_long_context"},
    )

    model = compiled["models"][0]
    assert model["acceleration"]["enable_thinking"] is None
    assert model["acceleration"]["thinking_control"] == {
        "mode": "template_ignores_enable_thinking",
        "effective_mode": "native",
        "evidence": "registry note: current GGUF template ignores enable_thinking",
    }
    assert "Missing enable_thinking compatibility evidence" not in model["known_gaps"]
    assert compiled["status"] == "compiled"


def test_compile_merges_shared_alias_mismatch_into_runtime_model(tmp_path: Path) -> None:
    registry_path = _write_yaml(
        tmp_path / "model_registry.yaml",
        {
            "server_mode": {
                "worker": {
                    "url": "http://localhost:8072",
                    "port": 8072,
                    "tier": "hot",
                    "slots": 1,
                    "model": "gemma-4-26B-A4B-it-Q4_K_M.gguf",
                    "model_role": "worker_general",
                    "shared_with": ["worker_math"],
                    "memory_gb": 16,
                    "throughput": 60.7,
                    "benchmark_score": "90%",
                    "numa_instances": 4,
                    "numa_ports": [8082, 8182, 8282, 8382],
                    "runtime_requirements": {
                        "binary_dir": "/mnt/raid0/llm/ik_llama.cpp/build/bin",
                    },
                    "acceleration": {
                        "type": "speculative_decoding",
                        "spec_type": "mtp",
                        "draft_max": 2,
                    },
                }
            },
            "roles": {
                "worker_general": {
                    "model": {
                        "name": "gemma-4-26B-A4B-it-Q4_K_M",
                        "quant": "Q4_K_M",
                        "architecture": "gemma4",
                        "size_gb": 16,
                        "ctx_max": 16384,
                    },
                    "performance": {"quality_pct": 90, "baseline_tps": 44.7},
                    "acceleration": {"type": "speculative_decoding", "spec_type": "mtp"},
                    "memory": {"pinned": True, "residency": "hot"},
                },
                "worker_math": {
                    "model": {
                        "name": "Qwen2.5-Math-7B-Instruct",
                        "quant": "Q4_K_M",
                        "architecture": "dense",
                        "size_gb": 4.4,
                        "ctx_max": 32768,
                    },
                    "performance": {"quality_pct": 88, "baseline_tps": 12.4},
                    "acceleration": {"type": "none", "lookup": False},
                    "memory": {"pinned": True, "residency": "hot"},
                },
            },
        },
    )

    compiled = compile_model_descriptors(
        lean_registry_path=registry_path,
        research_registry_path=None,
        active_roles={"worker_general", "worker_math"},
        allow_incomplete=True,
    )

    assert [model["model_id"] for model in compiled["models"]] == [
        "gemma4-26b-a4b-q4_k_m"
    ]
    model = compiled["models"][0]
    assert model["role_bindings"]["roles"] == ["worker_general", "worker_math"]
    assert model["role_bindings"]["server_roles"] == ["worker"]
    assert model["serving"]["binary"] == "ik-pr1744"
    assert model["serving"]["ports"] == [8072, 8082, 8182, 8282, 8382]
    assert model["speed"]["quarter_48t_tps"] == 60.7
    assert not any(gap.startswith("Role-server conflict:") for gap in model["known_gaps"])
    assert not any("ignored non-live role model metadata" in gap for gap in model["known_gaps"])
    assert model["role_bindings"]["alias_overrides"] == [
        {
            "role": "worker_math",
            "served_by": "worker_general",
            "ignored_model_id": "qwen2.5-math-7b-q4_k_m",
            "reason": "server_mode.shared_with runtime takes precedence",
        }
    ]


def test_compile_refuses_missing_load_bearing_fields(tmp_path: Path) -> None:
    registry_path = _write_yaml(
        tmp_path / "model_registry.yaml",
        {
            "server_mode": {},
            "roles": {
                "worker_math": {
                    "model": {
                        "name": "Qwen2.5-Math-7B-Instruct",
                        "quant": "Q4_K_M",
                        "architecture": "dense",
                        "size_gb": 4.4,
                    },
                    "acceleration": {"type": "speculative_decoding", "draft_role": "draft"},
                    "memory": {"pinned": True},
                }
            },
        },
    )

    with pytest.raises(DescriptorCompileError) as exc:
        compile_model_descriptors(
            lean_registry_path=registry_path,
            research_registry_path=None,
            active_roles={"worker_math"},
        )

    assert "Missing quality suite_vector evidence" in str(exc.value)
    assert "Missing server_mode binding" in str(exc.value)


def test_allow_incomplete_records_known_gaps_and_writes(tmp_path: Path) -> None:
    registry_path = _write_yaml(
        tmp_path / "model_registry.yaml",
        {
            "server_mode": {},
            "roles": {
                "worker_math": {
                    "model": {
                        "name": "Qwen2.5-Math-7B-Instruct",
                        "quant": "Q4_K_M",
                        "architecture": "dense",
                        "size_gb": 4.4,
                    },
                    "acceleration": {"type": "speculative_decoding", "draft_role": "draft"},
                    "memory": {"pinned": True},
                }
            },
        },
    )
    output = tmp_path / "model_descriptors.yaml"

    compiled = write_model_descriptors(
        output,
        lean_registry_path=registry_path,
        research_registry_path=None,
        active_roles={"worker_math"},
        allow_incomplete=True,
    )

    loaded = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert compiled["status"] == "compiled_with_gaps"
    assert loaded["models"][0]["known_gaps"]
    assert loaded["models"][0]["modalities"] == ["math", "text"]
    assert "worker_math" in loaded["models"][0]["role_bindings"]["roles"]


def test_compile_enriches_context_and_thinking_from_research_registry(tmp_path: Path) -> None:
    lean_path = _write_yaml(
        tmp_path / "lean.yaml",
        {
            "server_mode": {
                "frontdoor": {
                    "port": 8070,
                    "model": "Qwen_Qwen3.6-35B-A3B-Q8_0.gguf",
                    "model_role": "frontdoor",
                    "throughput": 24.3,
                    "benchmark_score": "170/183 (93%)",
                    "chat_template_kwargs": {"enable_thinking": False},
                }
            },
            "roles": {
                "frontdoor": {
                    "model": {
                        "name": "Qwen3.6-35B-A3B-Q8_0",
                        "quant": "Q8_0",
                        "architecture": "qwen35moe",
                        "size_gb": 37,
                    },
                    "performance": {
                        "quality_pct": 93,
                        "benchmark_date": "2026-05-04",
                    },
                }
            },
        },
    )
    research_path = _write_yaml(
        tmp_path / "research.yaml",
        {
            "roles": {
                "qwen36_q8_0": {
                    "model": {
                        "name": "Qwen3.6-35B-A3B",
                        "path": "/mnt/raid0/llm/models/Qwen_Qwen3.6-35B-A3B-Q8_0.gguf",
                        "quant": "Q8_0",
                        "max_context": 262144,
                        "disable_thinking": True,
                    }
                }
            }
        },
    )

    compiled = compile_model_descriptors(
        lean_registry_path=lean_path,
        research_registry_path=research_path,
        active_roles={"frontdoor"},
    )

    model = compiled["models"][0]
    assert model["ctx_max"] == 262144
    assert model["acceleration"]["enable_thinking"] is False
    assert model["quality"]["measured"][0]["date"] == "2026-05-04"
    assert compiled["status"] == "compiled"


def test_compile_uses_role_endpoint_for_dedicated_vision_role(tmp_path: Path) -> None:
    registry_path = _write_yaml(
        tmp_path / "model_registry.yaml",
        {
            "server_mode": {},
            "roles": {
                "worker_vision": {
                    "port": 8086,
                    "model": {
                        "name": "Qwen2.5-VL-7B-Instruct",
                        "quant": "Q4_K_M",
                        "architecture": "dense",
                        "size_gb": 4.4,
                        "ctx_max": 32768,
                        "mmproj_path": "/models/mmproj.gguf",
                    },
                    "candidate_roles": ["vision"],
                    "server": {"endpoint": "http://localhost:8086"},
                    "acceleration": {
                        "type": "baseline",
                        "disallowed": ["speculative_decoding"],
                    },
                    "performance": {
                        "vl_score": "11/12 (92%)",
                        "benchmark_date": "2026-03-04",
                    },
                }
            },
        },
    )

    compiled = compile_model_descriptors(
        lean_registry_path=registry_path,
        research_registry_path=None,
        active_roles={"worker_vision"},
        allow_incomplete=True,
    )

    model = compiled["models"][0]
    assert model["serving"]["ports"] == [8086]
    assert model["serving"]["numa_policy"] == "role_endpoint_binding"
    assert model["serving"]["requirements"] == {"mmproj_path": "/models/mmproj.gguf"}
    assert model["modalities"] == ["text", "vision"]
    # vision_language, not overall: a vl_score is domain evidence and is no
    # longer promoted to the whole-model scalar.
    assert model["quality"]["suite_vector"]["vision_language"] == 0.9167
    assert model["quality"]["suite_vector"]["vision_language"] == 0.9167
    assert "Missing serving port binding" not in model["known_gaps"]
    assert "Missing server_mode binding" not in model["known_gaps"]


def test_compile_uses_structured_vl_score_as_quality_prior(tmp_path: Path) -> None:
    registry_path = _write_yaml(
        tmp_path / "model_registry.yaml",
        {
            "server_mode": {},
            "roles": {
                "vision_escalation": {
                    "port": 8087,
                    "model": {
                        "name": "Qwen3-VL-30B-A3B-Instruct",
                        "quant": "Q4_K_M",
                        "architecture": "qwen3vlmoe",
                        "size_gb": 18.0,
                    },
                    "candidate_roles": ["vision"],
                    "server": {"endpoint": "http://localhost:8087"},
                    "performance": {
                        "vl_score": {"pct": 92.0, "raw": "11/12"},
                        "benchmark_date": "2026-03-04",
                    },
                }
            },
        },
    )

    compiled = compile_model_descriptors(
        lean_registry_path=registry_path,
        research_registry_path=None,
        active_roles={"vision_escalation"},
        allow_incomplete=True,
    )

    model = compiled["models"][0]
    suite_vector = model["quality"]["suite_vector"]

    # The vl_score lands on its OWN axis...
    assert suite_vector["vision_language"] == 0.92
    assert "Missing quality suite_vector evidence" not in model["known_gaps"]

    # ...and must NOT also become `overall`. This assertion is inverted from
    # what it was: the test previously required overall == 0.92, codifying the
    # defect. A vision benchmark measures vision, and `priors.quality_overall`
    # is the scalar the router reads as whole-model quality — so promoting it
    # told every consumer that an MMMU score described the model's general
    # capability. Qwen3-VL carried 0.636 that way, and Qwen3-Next-80B carried a
    # 27-question long-context score as 0.9259.
    assert "overall" not in suite_vector, (
        "a single-domain score must never be promoted to `overall`; "
        f"got {suite_vector}"
    )
    assert model["quality"]["overall_basis"] is None


def test_compile_marks_qwen_next_as_long_context_modality(tmp_path: Path) -> None:
    registry_path = _write_yaml(
        tmp_path / "model_registry.yaml",
        {
            "server_mode": {
                "ingest_long_context": {
                    "port": 8085,
                    "model": "Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf",
                    "model_role": "ingest_long_context",
                    "throughput": 14.4,
                    "benchmark_score": "25/27 (93%)",
                }
            },
            "roles": {
                "ingest_long_context": {
                    "model": {
                        "name": "Qwen3-Next-80B-A3B-Instruct",
                        "path": "lmstudio-community/Qwen3-Next-80B-A3B-Instruct-GGUF/Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf",
                        "quant": "Q4_K_M",
                        "architecture": "ssm_moe_hybrid",
                        "size_gb": 45,
                    },
                    "candidate_roles": ["ingest", "summarization", "architect"],
                    "performance": {
                        "long_context_quality": "25/27 (93%) on canonical long_context suite",
                    },
                    "memory": {"pinned": True},
                }
            },
        },
    )

    compiled = compile_model_descriptors(
        lean_registry_path=registry_path,
        research_registry_path=None,
        active_roles={"ingest_long_context"},
        allow_incomplete=True,
    )

    model = compiled["models"][0]
    assert model["model_id"] == "qwen3-next-80b-a3b-q4_k_m"
    assert model["modalities"] == ["long_context", "text"]
    assert model["quality"]["suite_vector"]["long_context"] == 0.9259


def test_compile_preserves_benchmark_only_server_model_role(tmp_path: Path) -> None:
    registry_path = _write_yaml(
        tmp_path / "model_registry.yaml",
        {
            "server_mode": {
                "reap_25b": {
                    "url": "http://localhost:8196",
                    "port": 8196,
                    "slots": 1,
                    "model_role": "reap_25b_frontdoor",
                    "model": "cerebras_Qwen3-Coder-REAP-25B-A3B-Q4_K_M.gguf",
                    "model_path": "/models/cerebras_Qwen3-Coder-REAP-25B-A3B-Q4_K_M.gguf",
                    "memory_gb": 15,
                    "tier": "warm",
                    "throughput": 39.6,
                    "benchmark_date": "2026-03-24",
                    "acceleration": {
                        "type": "speculative_decoding",
                        "draft_max": 24,
                        "lookup": True,
                    },
                }
            },
            "roles": {
                "reap_25b_frontdoor": {
                    "model": {
                        "name": "REAP-Qwen3-Coder-25B-A3B-Q4_K_M",
                        "quant": "Q4_K_M",
                        "architecture": "moe",
                        "size_gb": 15,
                    },
                    "candidate_roles": ["frontdoor", "coder", "worker"],
                    "acceleration": {
                        "type": "speculative_decoding",
                        "draft_role": "qwen3-coder-0.75b-q4_0",
                        "draft_max": 24,
                        "lookup": True,
                    },
                    "performance": {
                        "baseline_tps": 39.6,
                        "optimized_tps": 39.6,
                        "benchmark_date": "2026-03-24",
                    },
                    "memory": {"residency": "warm", "pinned": False},
                }
            },
        },
    )

    compiled = compile_model_descriptors(
        lean_registry_path=registry_path,
        research_registry_path=None,
        active_roles={"frontdoor"},
        allow_incomplete=True,
    )

    model = compiled["models"][0]
    assert model["model_id"] == "reap-qwen3-coder-25b-a3b-q4_k_m"
    assert model["modalities"] == ["code", "text"]
    assert model["role_bindings"]["roles"] == ["reap_25b_frontdoor"]
    assert model["role_bindings"]["server_roles"] == ["reap_25b"]
    assert model["serving"]["ports"] == [8196]
    assert model["speed"]["solo_96t_tps"] == 39.6
    assert model["known_gaps"] == [
        "Missing enable_thinking compatibility evidence",
        "Missing quality suite_vector evidence",
        "Missing structured ctx_max",
    ]


def test_first_model_native_context_value_prefers_native_keys() -> None:
    # GGUF-header / registry native keys resolve, coerced to a positive int.
    assert (
        _first_model_native_context_value({"model": {"n_ctx_train": 262144}}, None, [])
        == 262144
    )
    assert (
        _first_model_native_context_value(
            {"model": {"context_length": "131072"}}, None, []
        )
        == 131072
    )
    assert (
        _first_model_native_context_value(
            {}, None, [{"model": {"max_position_embeddings": 40960}}]
        )
        == 40960
    )
    # An effective-only ctx_max is NOT model-native evidence.
    assert (
        _first_model_native_context_value({"model": {"ctx_max": 8192}}, None, []) is None
    )
    # No native evidence at all -> None (a structured gap consumers can see).
    assert _first_model_native_context_value({}, None, []) is None
    # Non-numeric native value coerces to None rather than leaking a bad type.
    assert (
        _first_model_native_context_value({"model": {"n_ctx_train": "big"}}, None, [])
        is None
    )


def test_compile_projects_model_native_ctx_model_max_distinct_from_ctx_max(
    tmp_path: Path,
) -> None:
    lean_path = _write_yaml(
        tmp_path / "lean.yaml",
        {
            "server_mode": {
                "frontdoor": {
                    "port": 8070,
                    "model": "Qwen_Qwen3.6-35B-A3B-Q8_0.gguf",
                    "model_role": "frontdoor",
                    "throughput": 24.3,
                }
            },
            "roles": {
                "frontdoor": {
                    "model": {
                        "name": "Qwen3.6-35B-A3B-Q8_0",
                        "quant": "Q8_0",
                        "architecture": "qwen35moe",
                        "size_gb": 37,
                        "ctx_max": 16384,
                    }
                }
            },
        },
    )
    research_path = _write_yaml(
        tmp_path / "research.yaml",
        {
            "roles": {
                "qwen36_q8_0": {
                    "model": {
                        "name": "Qwen3.6-35B-A3B",
                        "path": "/mnt/raid0/llm/models/Qwen_Qwen3.6-35B-A3B-Q8_0.gguf",
                        "quant": "Q8_0",
                        # Model-native (GGUF-header) context, distinct from the
                        # smaller configured/effective ctx_max above.
                        "n_ctx_train": 262144,
                    }
                }
            }
        },
    )

    compiled = compile_model_descriptors(
        lean_registry_path=lean_path,
        research_registry_path=research_path,
        active_roles={"frontdoor"},
        allow_incomplete=True,
    )

    model = compiled["models"][0]
    assert model["ctx_max"] == 16384
    assert model["ctx_model_max"] == 262144


def test_compile_records_null_ctx_model_max_when_no_native_evidence(
    tmp_path: Path,
) -> None:
    lean_path = _write_yaml(
        tmp_path / "lean.yaml",
        {
            "server_mode": {
                "frontdoor": {
                    "port": 8070,
                    "model": "Qwen_Qwen3.6-35B-A3B-Q8_0.gguf",
                    "model_role": "frontdoor",
                    "throughput": 24.3,
                }
            },
            "roles": {
                "frontdoor": {
                    "model": {
                        "name": "Qwen3.6-35B-A3B-Q8_0",
                        "quant": "Q8_0",
                        "architecture": "qwen35moe",
                        "size_gb": 37,
                        "ctx_max": 16384,
                    }
                }
            },
        },
    )

    compiled = compile_model_descriptors(
        lean_registry_path=lean_path,
        research_registry_path=None,
        active_roles={"frontdoor"},
        allow_incomplete=True,
    )

    model = compiled["models"][0]
    # The field is present in the contract even with no native evidence.
    assert "ctx_model_max" in model
    assert model["ctx_model_max"] is None
