from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


def test_build_pool_yaml_only_skips_hf_adapters(tmp_path: Path, monkeypatch) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "benchmark"))
    import question_pool  # noqa: PLC0415

    research_root = tmp_path / "research"
    debug_dir = research_root / "benchmarks" / "prompts" / "debug"
    debug_dir.mkdir(parents=True)
    (debug_dir / "agentic.yaml").write_text(
        yaml.safe_dump(
            {
                "questions": [
                    {
                        "id": "yaml_only_001",
                        "prompt": "Return ok.",
                        "expected": "ok",
                        "scoring_method": "exact_match",
                        "scoring_config": {},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(question_pool, "RESEARCH_ROOT", research_root)

    output = tmp_path / "pool.jsonl"
    stats = question_pool.build_pool(output, yaml_only=True)
    rows = [json.loads(line) for line in output.read_text().splitlines()]

    assert stats["agentic"] == 1
    assert rows[0]["yaml_only"] is True
    assert rows[1]["suite"] == "agentic"
    assert rows[1]["dataset_source"] == "yaml"
