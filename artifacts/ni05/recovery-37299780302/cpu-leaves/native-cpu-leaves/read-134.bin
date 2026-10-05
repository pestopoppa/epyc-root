from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.calibration.build_irt_prompt_embeddings import (
    build_artifacts,
    embed_records,
    load_prompt_embedding_artifact,
    write_keyed_irt_scores,
)
from scripts.calibration.irt_cold_start_ab import load_baseline_records


def _write_baseline(path: Path, n: int = 3) -> Path:
    path.write_text(
        json.dumps(
            {
                "model_role": "unit",
                "results": {
                    "general": {
                        f"q{i}": {
                            "question_id": f"qid-{i}",
                            "prompt": f"Prompt {i}",
                            "algorithmic_score": 1 + i,
                            "tokens_per_second": 10 + i,
                        }
                        for i in range(n)
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def _fake_embed(text: str) -> np.ndarray:
    idx = int(text.rsplit(" ", 1)[-1])
    vec = np.array([idx, idx + 1, idx + 2, idx + 3], dtype=np.float32)
    return vec / np.linalg.norm(vec)


def test_embed_records_preserves_prompt_keys(tmp_path: Path) -> None:
    baseline = _write_baseline(tmp_path / "baseline.json", n=2)
    _, records = load_baseline_records(baseline)

    embedded = embed_records(records, _fake_embed)

    assert embedded["embeddings"].shape == (2, 4)
    assert embedded["prompt_hashes"].shape == (2,)
    assert embedded["question_ids"].tolist() == ["qid-0", "qid-1"]
    assert embedded["suites"].tolist() == ["general", "general"]


def test_build_artifacts_writes_keyed_embeddings(tmp_path: Path) -> None:
    baseline = _write_baseline(tmp_path / "baseline.json", n=2)
    output = tmp_path / "embeddings.npz"

    report = build_artifacts(baseline, output, embed_text=_fake_embed, embedder_urls=["mock://embed"])
    saved = np.load(output, allow_pickle=True)

    assert report["embeddings"]["records"] == 2
    assert report["embeddings"]["embedding_dim"] == 4
    assert saved["metadata"].item()["embedder_urls"] == ["mock://embed"]
    assert saved["embeddings"].shape == (2, 4)


def test_write_keyed_irt_scores_projects_embeddings(tmp_path: Path) -> None:
    baseline = _write_baseline(tmp_path / "baseline.json", n=2)
    _, records = load_baseline_records(baseline)
    embedded = embed_records(records, _fake_embed)
    irt = tmp_path / "irt.npz"
    np.savez(
        irt,
        metadata=np.array({"response_source": "label_proxy"}, dtype=object),
        embedding_dim=np.array(4, dtype=np.int64),
        projector_feature_mean=np.zeros(4, dtype=np.float32),
        projector_feature_scale=np.ones(4, dtype=np.float32),
        projector_weights=np.array(
            [
                [1.0, 0.0],
                [0.0, 1.0],
                [0.0, 0.0],
                [0.0, 0.0],
                [0.5, 0.5],
            ],
            dtype=np.float32,
        ),
        projector_target_mean=np.zeros(2, dtype=np.float32),
        projector_target_scale=np.ones(2, dtype=np.float32),
    )

    output = tmp_path / "keyed_irt.npz"
    metadata = write_keyed_irt_scores(output, embeddings_artifact=embedded, irt_scores_path=irt)
    saved = np.load(output, allow_pickle=True)

    assert metadata["records"] == 2
    assert metadata["response_source"] == "label_proxy"
    assert saved["prompt_hashes"].tolist() == embedded["prompt_hashes"].tolist()
    assert saved["latent_difficulty"].shape == (2,)
    assert saved["latent_discrimination"].shape == (2,)


def test_build_artifacts_can_write_embeddings_and_keyed_scores(tmp_path: Path) -> None:
    baseline = _write_baseline(tmp_path / "baseline.json", n=2)
    irt = tmp_path / "irt.npz"
    np.savez(
        irt,
        embedding_dim=np.array(4, dtype=np.int64),
        projector_feature_mean=np.zeros(4, dtype=np.float32),
        projector_feature_scale=np.ones(4, dtype=np.float32),
        projector_weights=np.ones((5, 2), dtype=np.float32),
        projector_target_mean=np.zeros(2, dtype=np.float32),
        projector_target_scale=np.ones(2, dtype=np.float32),
    )

    report = build_artifacts(
        baseline,
        tmp_path / "embeddings.npz",
        embed_text=_fake_embed,
        irt_scores_path=irt,
        output_irt_scores=tmp_path / "keyed_irt.npz",
    )

    assert report["embeddings"]["records"] == 2
    assert report["irt_scores"]["records"] == 2


def test_load_prompt_embedding_artifact_reads_saved_npz(tmp_path: Path) -> None:
    cache = tmp_path / "cached_embeddings.npz"
    np.savez_compressed(
        cache,
        embeddings=np.arange(12, dtype=np.float32).reshape(3, 4),
        prompt_hashes=np.array(["h0", "h1", "h2"], dtype=object),
        question_ids=np.array(["q0", "q1", "q2"], dtype=object),
        suites=np.array(["general", "general", "general"], dtype=object),
        question_keys=np.array(["k0", "k1", "k2"], dtype=object),
    )

    loaded = load_prompt_embedding_artifact(cache)
    assert loaded["embeddings"].shape == (3, 4)
    assert loaded["question_ids"].tolist() == ["q0", "q1", "q2"]


def test_build_artifacts_reuses_cached_prompt_embeddings(tmp_path: Path) -> None:
    baseline = _write_baseline(tmp_path / "baseline.json", n=2)
    _, records = load_baseline_records(baseline)
    embedded = embed_records(records, _fake_embed)

    cache = tmp_path / "cached_embeddings.npz"
    np.savez_compressed(
        cache,
        embeddings=embedded["embeddings"],
        prompt_hashes=embedded["prompt_hashes"],
        question_ids=embedded["question_ids"],
        suites=embedded["suites"],
        question_keys=embedded["question_keys"],
    )

    loaded = load_prompt_embedding_artifact(cache)
    assert loaded["embeddings"].shape == embedded["embeddings"].shape
    assert loaded["prompt_hashes"].tolist() == embedded["prompt_hashes"].tolist()

    report = build_artifacts(
        baseline,
        tmp_path / "reused_embeddings.npz",
        prompt_embedding_artifact=loaded,
    )
    reused = np.load(tmp_path / "reused_embeddings.npz", allow_pickle=True)

    assert report["embeddings"]["records"] == 2
    assert np.array_equal(reused["embeddings"], embedded["embeddings"])


def test_build_artifacts_rekeys_cached_prompt_embeddings_to_baseline_order(tmp_path: Path) -> None:
    baseline = _write_baseline(tmp_path / "baseline.json", n=3)
    _, records = load_baseline_records(baseline)
    embedded = embed_records(records, _fake_embed)
    order = np.array([2, 0, 1])
    cache = tmp_path / "shuffled_embeddings.npz"
    np.savez_compressed(
        cache,
        embeddings=embedded["embeddings"][order],
        prompt_hashes=embedded["prompt_hashes"][order],
        question_ids=embedded["question_ids"][order],
    )

    report = build_artifacts(
        baseline,
        tmp_path / "rekeyed_embeddings.npz",
        prompt_embedding_artifact=load_prompt_embedding_artifact(cache),
    )
    rekeyed = np.load(tmp_path / "rekeyed_embeddings.npz", allow_pickle=True)

    assert report["embeddings"]["records"] == 3
    assert np.array_equal(rekeyed["embeddings"], embedded["embeddings"])
    assert rekeyed["prompt_hashes"].tolist() == embedded["prompt_hashes"].tolist()


def test_build_artifacts_rejects_cached_prompt_embedding_miss(tmp_path: Path) -> None:
    baseline = _write_baseline(tmp_path / "baseline.json", n=2)
    _, records = load_baseline_records(baseline)
    embedded = embed_records(records[:1], _fake_embed)
    cache = tmp_path / "partial_embeddings.npz"
    np.savez_compressed(
        cache,
        embeddings=embedded["embeddings"],
        prompt_hashes=embedded["prompt_hashes"],
    )

    with pytest.raises(ValueError, match="cached embeddings missing 1 baseline prompt"):
        build_artifacts(
            baseline,
            tmp_path / "reused_embeddings.npz",
            prompt_embedding_artifact=load_prompt_embedding_artifact(cache),
        )
