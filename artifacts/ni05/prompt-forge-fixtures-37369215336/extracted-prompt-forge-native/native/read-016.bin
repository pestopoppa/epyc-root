"""Shared question-sampling helpers used by both seed_specialist_routing.py and _v2.

Extracted during the 2026-05-22 Task-B refactor. The two seeding scripts are
97.9% identical; this module hosts the loader + sampling logic, while the
original scripts keep thin wrapper functions of the same names so test
monkeypatches (against `mod._load_from_dataset_adapter`, `mod._load_from_yaml`,
`mod.DEBUG_PROMPTS_DIR`) continue to work unchanged.

All shared functions take state via parameters — no module-level globals
referenced. Wrappers inject `logger`, `debug_prompts_dir`, and the per-version
loader callables; Python's runtime global lookup honors any monkeypatch on
those bindings.
"""

from __future__ import annotations

import hashlib
import importlib.util
import logging
import os
import random
import sys
from pathlib import Path
from typing import Any, Callable, Iterable


_RESEARCH_BENCHMARK_MODULE_CACHE: dict[tuple[str, str, int], Any] = {}


def _file_mtime_ns(path: Path) -> int | None:
    try:
        return path.stat().st_mtime_ns
    except FileNotFoundError:
        return None


def _research_root() -> Path:
    return Path(os.environ.get("EPYC_RESEARCH_ROOT", "/mnt/raid0/llm/epyc-inference-research"))


def _load_research_benchmark_module(module_name: str) -> Any:
    module_path = _research_root() / "scripts" / "benchmark" / f"{module_name}.py"
    mtime_ns = _file_mtime_ns(module_path)
    if mtime_ns is None:
        raise FileNotFoundError(f"research benchmark module not found: {module_path}")

    cache_key = (module_name, str(module_path), mtime_ns)
    cached = _RESEARCH_BENCHMARK_MODULE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    module_hash = hashlib.sha1(f"{module_path}:{mtime_ns}".encode("utf-8")).hexdigest()[:16]
    private_name = f"_epyc_seeding_research_{module_name}_{module_hash}"
    existing = sys.modules.get(private_name)
    if existing is not None:
        _RESEARCH_BENCHMARK_MODULE_CACHE[cache_key] = existing
        return existing

    spec = importlib.util.spec_from_file_location(private_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load research benchmark module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[private_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(private_name, None)
        raise
    _RESEARCH_BENCHMARK_MODULE_CACHE[cache_key] = module
    return module


def build_question_pool() -> dict[str, int]:
    """Rebuild the question pool with the SAME research module the sampler reads.

    EVL-12 A2 residue: ``--rebuild-pool`` used a bare ``from question_pool import``,
    which bound whichever same-named copy ``sys.path`` put first (the orchestrator
    copy sits first), while ``sample_unseen_questions`` binds the research copy by path.
    """
    question_pool = _load_research_benchmark_module("question_pool")
    return getattr(question_pool, "build_pool")()


def load_questions_by_ids(
    question_ids: list[str],
    *,
    logger: logging.Logger,
    pool_path: Path | None = None,
) -> list[dict]:
    """Look up pool questions by ID through the research ``question_pool.load_pool``.

    Accepts bare IDs and ``suite/id``. Returns them in input order, de-duplicated.
    The research module has no ``load_questions_by_ids``, so the lookup lives here and
    binds the same pool reader as the sampler. It never falls back to a bare import
    (EVL-12 A2 residue).
    """
    question_pool = _load_research_benchmark_module("question_pool")
    pool = getattr(question_pool, "load_pool")(pool_path, warn_stale=False)
    by_id: dict[str, dict] = {}
    for questions in pool.values():
        for q in questions:
            by_id[q.get("id", "")] = q

    deduped: list[dict] = []
    seen_ids: set[str] = set()
    missing: list[str] = []
    for qid in question_ids:
        bare_id = qid.split("/", 1)[1] if "/" in qid else qid
        if bare_id in by_id:
            q = by_id[bare_id]
        elif qid in by_id:
            q = by_id[qid]
        else:
            missing.append(qid)
            continue
        if q["id"] not in seen_ids:
            seen_ids.add(q["id"])
            deduped.append(q)

    if missing:
        logger.warning(
            "load_questions_by_ids: %d IDs not found in pool: %s%s",
            len(missing), missing[:5], "..." if len(missing) > 5 else "",
        )
    logger.info("Loaded %d/%d questions by ID", len(deduped), len(question_ids))
    return deduped


def _reference_text(q: dict) -> str:
    return str(q.get("reference") or q.get("reference_answer") or "")


def _normalise_yaml_question(suite_name: str, q: dict) -> dict:
    return {
        "id": q["id"],
        "suite": suite_name,
        "prompt": q["prompt"].strip(),
        "context": str(q.get("context") or ""),
        "expected": q.get("expected", ""),
        "reference": _reference_text(q),
        "image_path": q.get("image_path", ""),
        "tier": q.get("tier", 1),
        "scoring_method": q.get("scoring_method", "exact_match"),
        "scoring_config": q.get("scoring_config", {}),
        "dataset_source": "yaml",
    }


def _normalise_legacy_prompt(suite_name: str, prompt_id: str, q: dict) -> dict:
    scoring_config = dict(q.get("scoring_config") or {})
    if q.get("auto_score") and "legacy_auto_score" not in scoring_config:
        scoring_config["legacy_auto_score"] = q.get("auto_score")
    if q.get("scoring") and "legacy_scoring_rubric" not in scoring_config:
        scoring_config["legacy_scoring_rubric"] = q.get("scoring")
    return {
        "id": str(q.get("id") or prompt_id),
        "suite": suite_name,
        "prompt": str(q["prompt"]).strip(),
        "context": str(q.get("context") or ""),
        "expected": q.get("expected", ""),
        "reference": _reference_text(q),
        "image_path": q.get("image_path", ""),
        "tier": q.get("tier", 1),
        "scoring_method": q.get("scoring_method", "exact_match"),
        "scoring_config": scoring_config,
        "dataset_source": "yaml_legacy_prompts",
    }


def load_from_dataset_adapter(
    suite_name: str,
    sample_count: int,
    seed: int,
    *,
    logger: logging.Logger,
) -> list[dict]:
    """Sample questions from HF dataset adapters (was _load_from_dataset_adapter)."""
    try:
        dataset_adapters = _load_research_benchmark_module("dataset_adapters")
        get_adapter = getattr(dataset_adapters, "get_adapter")
        adapter_suites = getattr(dataset_adapters, "ADAPTER_SUITES")
    except Exception:
        return []

    if suite_name not in adapter_suites:
        return []

    adapter = get_adapter(suite_name)
    if adapter is None:
        return []

    prompts = adapter.sample(n=sample_count, seed=seed)
    if prompts:
        logger.info(f"  [{suite_name}] Sampled {len(prompts)} from "
                     f"{adapter.total_available} HF dataset questions (seed={seed})")
    return prompts


def load_from_yaml(
    suite_name: str,
    sample_count: int,
    seed: int,
    *,
    debug_prompts_dir: Path,
    logger: logging.Logger,
) -> list[dict]:
    """Fall back to static YAML debug prompts (was _load_from_yaml).

    `debug_prompts_dir` is injected so v1/v2 tests that monkeypatch
    `mod.DEBUG_PROMPTS_DIR` still take effect — the caller resolves the
    constant from its module namespace each call.
    """
    try:
        import yaml
    except ImportError:
        return []

    yaml_path = debug_prompts_dir / f"{suite_name}.yaml"
    if not yaml_path.exists():
        return []

    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    questions = data.get("questions", [])
    if not questions and isinstance(data.get("prompts"), dict):
        questions = [
            _normalise_legacy_prompt(suite_name, str(prompt_id), prompt)
            for prompt_id, prompt in data["prompts"].items()
            if isinstance(prompt, dict) and prompt.get("prompt")
        ]
    if not questions:
        return []

    rng = random.Random(seed)
    n = min(sample_count, len(questions))
    sampled = rng.sample(questions, n)
    logger.info(f"  [{suite_name}] Sampled {n}/{len(questions)} from YAML (seed={seed})")

    result = []
    for q in sampled:
        if q.get("dataset_source") == "yaml_legacy_prompts":
            result.append(q)
        else:
            result.append(_normalise_yaml_question(suite_name, q))
    return result


def sample_unseen_questions(
    suites: list[str],
    sample_per_suite: int,
    seen: set[str],
    seed: int,
    *,
    use_pool: bool = True,
    allow_reseen: bool = False,
    # injected dependencies — see module docstring for rationale
    default_suites: Iterable[str],
    load_from_dataset_adapter: Callable[..., list[dict]],
    load_from_yaml: Callable[..., list[dict]],
    logger: logging.Logger,
    question_source: str = "auto",
) -> list[dict]:
    """Sample questions not in the seen set, interleaved across suites.

    If `use_pool=True` (default), tries the pre-extracted question pool first
    (~100ms). Falls back to HF dataset adapters, then YAML.

    If `allow_reseen` (debug mode), backfills with seen questions when a
    suite is exhausted.  Normal mode skips exhausted suites.

    Returns questions interleaved by suite (round-robin) so the orchestrator
    sees diverse question types early rather than processing one suite at a time.
    """
    suite_names = list(default_suites) if suites == ["all"] else suites

    source = str(question_source or "auto").strip().lower()
    if source not in {"auto", "adapter", "yaml"}:
        raise ValueError("question_source must be one of: auto, adapter, yaml")

    # Try the pre-extracted pool first
    if use_pool and source == "auto":
        try:
            question_pool = _load_research_benchmark_module("question_pool")
            pool_file = Path(getattr(question_pool, "POOL_FILE"))
            build_pool = getattr(question_pool, "build_pool")
            load_pool = getattr(question_pool, "load_pool")
            sample_from_pool = getattr(question_pool, "sample_from_pool")

            if not pool_file.exists():
                logger.info("Question pool not found — building automatically (one-time)...")
                build_pool()

            pool = load_pool()
            if pool:
                result = sample_from_pool(
                    pool, suite_names, sample_per_suite, seed, seen,
                    allow_reseen=allow_reseen,
                )
                if result:
                    logger.info(f"Sampled {len(result)} questions from pool (fast path)")
                    return result
                logger.info("Pool returned no results — falling back to adapters")
        except Exception as e:
            logger.warning(f"Pool loading failed ({e}) — falling back to adapters")

    per_suite: list[list[dict]] = []

    for suite_name in suite_names:
        oversample = sample_per_suite * 20

        prompts = []
        if source in {"auto", "adapter"}:
            prompts = load_from_dataset_adapter(suite_name, oversample, seed)
        if not prompts and source in {"auto", "yaml"}:
            prompts = load_from_yaml(suite_name, oversample, seed)

        fresh = [p for p in prompts if p["id"] not in seen]
        if len(fresh) < len(prompts):
            filtered = len(prompts) - len(fresh)
            logger.info(f"  [{suite_name}] Filtered {filtered} previously seen questions")

        per_suite.append(fresh[:sample_per_suite])

    # Interleave: round-robin across suites
    all_prompts: list[dict] = []
    max_len = max((len(s) for s in per_suite), default=0)
    for i in range(max_len):
        for suite_questions in per_suite:
            if i < len(suite_questions):
                all_prompts.append(suite_questions[i])

    return all_prompts
