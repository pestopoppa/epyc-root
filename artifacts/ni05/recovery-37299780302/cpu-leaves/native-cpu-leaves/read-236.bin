from __future__ import annotations

from types import SimpleNamespace

from scripts.benchmark.dataset_adapter_modules.coding import CoderAdapter
from scripts.benchmark.dataset_adapter_modules.math_adapter import MathAdapter


def test_coder_adapter_uses_namespaced_hf_dataset_ids(monkeypatch):
    calls = []

    def load_dataset(name, *args, **kwargs):
        calls.append((name, args, kwargs))
        if name == "openai/openai_humaneval":
            return [
                {
                    "task_id": "HumanEval/0",
                    "prompt": "def add(a, b):\n",
                    "canonical_solution": "return a + b",
                    "test": "assert add(1, 2) == 3",
                    "entry_point": "add",
                }
            ]
        if name == "google-research-datasets/mbpp":
            return [
                {
                    "task_id": 1,
                    "text": "Write add.",
                    "test_list": ["assert add(1, 2) == 3"],
                }
            ]
        raise AssertionError(name)

    monkeypatch.setitem(
        __import__("sys").modules,
        "datasets",
        SimpleNamespace(load_dataset=load_dataset),
    )

    adapter = CoderAdapter()
    adapter._dataset = None
    adapter._humaneval = None
    adapter._mbpp = None

    assert adapter.total_available == 2
    assert calls == [
        ("openai/openai_humaneval", (), {"split": "test"}),
        ("google-research-datasets/mbpp", (), {"split": "test"}),
    ]


def test_math_adapter_uses_namespaced_gsm8k_hf_dataset_id(monkeypatch):
    calls = []

    def load_dataset(name, *args, **kwargs):
        calls.append((name, args, kwargs))
        if name == "openai/gsm8k":
            return [{"question": "1+1?", "answer": "#### 2"}]
        if name == "HuggingFaceH4/MATH-500":
            return [{"problem": "2+2?", "answer": "4", "level": 1, "subject": "algebra"}]
        raise AssertionError(name)

    monkeypatch.setitem(
        __import__("sys").modules,
        "datasets",
        SimpleNamespace(load_dataset=load_dataset),
    )

    adapter = MathAdapter()
    adapter._dataset = None
    adapter._gsm8k = None
    adapter._math500 = None

    assert adapter.total_available == 2
    assert calls == [
        ("openai/gsm8k", ("main",), {"split": "test"}),
        ("HuggingFaceH4/MATH-500", (), {"split": "test"}),
    ]
