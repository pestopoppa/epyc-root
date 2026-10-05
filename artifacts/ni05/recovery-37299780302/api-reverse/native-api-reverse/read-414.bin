"""RTG-55 MHS-5 — labelled CONSTRAIN/REPLACE corpus from Harness-R1's held-out patches."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.autopilot.species.heldout_effect_corpus import (  # noqa: E402
    SCHEMA,
    CorpusIntegrityError,
    classify_patch_effect,
    derive_corpus,
    extract_effect_kinds,
)
from scripts.autopilot.species.prompt_forge import (  # noqa: E402
    MUTATION_EFFECT_RISK,
    MutationEffect,
)

ARTIFACT = ROOT / "orchestration" / "datasets" / "harness_r1_heldout_effect_corpus.json"

BLOCK = "def hook(ctx, nb):\n    return {'kind': 'block_and_prompt', 'message': 'no'}\n"
FORCE = "def hook(ctx, nb):\n    return dict(kind='force_action', action='look')\n"
HINT_ONLY = "def hook(ctx, nb):\n    return {'message': 'try again'}\n"
DYNAMIC = "def hook(ctx, nb):\n    k = nb['k']\n    return {'kind': k}\n"


def test_extract_effect_kinds_reads_literals_without_executing() -> None:
    assert extract_effect_kinds(BLOCK) == ({"block_and_prompt"}, False)
    assert extract_effect_kinds(FORCE) == ({"force_action"}, False)
    assert extract_effect_kinds(HINT_ONLY) == (set(), False)
    assert extract_effect_kinds(DYNAMIC) == (set(), True)
    # Would raise if executed; parsing must not run it.
    assert extract_effect_kinds("raise SystemExit(1)\n") == (set(), False)


@pytest.mark.parametrize(
    ("kinds", "dynamic", "valid", "expected"),
    [
        ({"block_and_prompt"}, False, True, MutationEffect.CONSTRAIN),
        ({"inject_hint"}, False, True, MutationEffect.CONSTRAIN),
        (set(), False, True, MutationEffect.CONSTRAIN),
        ({"rewrite_action"}, False, True, MutationEffect.REPLACE),
        ({"block_and_prompt", "force_action"}, False, True, MutationEffect.REPLACE),
        ({"teleport"}, False, True, MutationEffect.UNKNOWN),
        ({"block_and_prompt"}, True, True, MutationEffect.UNKNOWN),
        ({"force_action"}, False, False, MutationEffect.UNSAFE),
    ],
)
def test_classify_patch_effect(kinds, dynamic, valid, expected) -> None:
    assert classify_patch_effect(kinds, dynamic, valid=valid) is expected


def _write_patch(root: Path, rel: str, code: str) -> str:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps({"actions": [{"type": "add_code_hook", "hook": "h", "code": code}]}).encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _held_out(delta: int, rescued: int, regressed: int) -> dict:
    return {
        "tasks": 100,
        "baseline_pass": 50,
        "patched_pass": 50 + delta,
        "delta_pass": delta,
        "rescued_failures": rescued,
        "regressed_successes": regressed,
    }


def _mini_corpus(root: Path, *, tamper: bool = False) -> Path:
    sha_block = _write_patch(root, "ed/s1/a.json", BLOCK)
    sha_force = _write_patch(root, "ed/s1/b.json", FORCE)
    if tamper:
        (root / "ed/s1/b.json").write_text("{}")
    results = {
        "protocol": "p",
        "target_agent": "t",
        "held_out_tasks": {"a": 100, "b": 100, "c": 100},
        "editors": {
            "ed": {
                "per_seed": {
                    "s1": {
                        "a": {"patch_file": "ed/s1/a.json", "valid": True, "hooks": ["h"],
                              "patch_sha256": sha_block, "held_out": _held_out(10, 12, 2)},
                        "b": {"patch_file": "ed/s1/b.json", "valid": True, "hooks": ["h"],
                              "patch_sha256": sha_force, "held_out": _held_out(-20, 1, 21)},
                        "c": {"patch_file": None, "valid": False, "hooks": [],
                              "validation_error": "Import", "held_out": _held_out(0, 0, 0)},
                    }
                }
            }
        },
    }
    (root / "results.json").write_text(json.dumps(results))
    return root


def test_derive_corpus_labels_and_summarizes(tmp_path: Path) -> None:
    corpus = derive_corpus(_mini_corpus(tmp_path), source_revision="abc")
    assert corpus["schema"] == SCHEMA
    by_bench = {r["benchmark"]: r for r in corpus["rows"]}
    assert by_bench["a"]["effect"] == "constrain"
    assert by_bench["b"]["effect"] == "replace"
    assert by_bench["b"]["effect_risk"] == MUTATION_EFFECT_RISK[MutationEffect.REPLACE]
    assert by_bench["c"]["effect"] == "unsafe"
    summary = corpus["by_effect_valid_only"]
    assert set(summary) == {"constrain", "replace"}
    assert summary["replace"]["delta_pp_mean"] == -20.0
    assert summary["constrain"]["rescue_to_regression"] == 6.0
    assert corpus["worst_valid_patches"][0]["benchmark"] == "b"
    # Labels only: no patch code is carried into the corpus.
    assert "def hook" not in json.dumps(corpus)


def test_derive_corpus_refuses_a_tampered_patch(tmp_path: Path) -> None:
    with pytest.raises(CorpusIntegrityError):
        derive_corpus(_mini_corpus(tmp_path, tamper=True))


# ---------------------------------------------------------------------------
# The committed artifact: the evidence behind the MHS-4 weights
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_artifact_identity(artifact: dict) -> None:
    assert artifact["schema"] == SCHEMA
    assert artifact["source"]["revision"] == "411bb5489ada85e6118897039eab84b4e4aaa4f0"
    assert artifact["source"]["license"] == "Apache-2.0"
    assert len(artifact["rows"]) == 27
    assert sum(r["valid"] for r in artifact["rows"]) == 23


def test_artifact_supports_the_replace_over_constrain_ordering(artifact: dict) -> None:
    """MHS-4's ordinal prior: override patches are the riskier class on held-out tasks."""
    s = artifact["by_effect_valid_only"]
    replace, constrain = s["replace"], s["constrain"]
    assert MUTATION_EFFECT_RISK[MutationEffect.REPLACE] > MUTATION_EFFECT_RISK[MutationEffect.CONSTRAIN]
    assert replace["n_negative"] == replace["n_patches"]  # every override patch regressed
    assert replace["delta_pp_mean"] < 0 < constrain["delta_pp_mean"]
    assert replace["rescue_to_regression"] < 1 < constrain["rescue_to_regression"]


def test_artifact_refutes_constrain_is_regression_free(artifact: dict) -> None:
    """The prior is ordinal, not a safety guarantee: the single worst patch is CONSTRAIN."""
    s = artifact["by_effect_valid_only"]
    assert s["constrain"]["n_negative"] > 0
    assert s["constrain"]["delta_pp_min"] < s["replace"]["delta_pp_min"]
    assert artifact["worst_valid_patches"][0]["effect"] == "constrain"
