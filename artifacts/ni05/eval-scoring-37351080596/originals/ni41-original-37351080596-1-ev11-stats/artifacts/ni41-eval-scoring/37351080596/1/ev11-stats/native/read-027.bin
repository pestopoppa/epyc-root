#!/usr/bin/env python3
"""EV-CONF-2 confidence probe: a direct driver for one OpenAI-compatible llama-server.

This closes the "runner gap" in the EV-CONF-2 probe spec
(``handoffs/active/autopilot-decision-plane-audit-2026-07-22.md``, EV-CONF-2 box).
``eval_batch_serving_evaltower_window.py --mode math_rebaseline`` can only draw
unstratified rows, and only through the orchestrator role. This driver instead:

1. Draws a **stratified** sample from the E7c ``worker_general`` math sidecar:
   ``--n-wrong`` rows E7c scored wrong and ``--n-right`` rows it scored right,
   using ``random.Random(--seed)`` over the sorted question ids. The drawn ids,
   their E7c qid/verdict and a digest are written to ``sample_manifest.json``.
   A re-run must reproduce the same manifest or it refuses to run.
2. Loads the prompts from the research ``math`` dataset adapter (the E7c
   source) and refuses to run if the ``dataset_sha256`` differs from E7c's.
   ``--questions-jsonl`` supplies the rows offline instead.
3. Sends each prompt as a single user turn to ``<endpoint>/v1/chat/completions``
   with the **production sampling of the role** (``--role``, default
   ``worker_general``). Sampling is produced by the backend's own
   ``LlamaServerBackend._apply_deterministic_sampling`` over the registry
   ``RoleConfig``, so it cannot drift from what the orchestrator sends. The
   driver also uses the direct stage's token cap (2048) and stop list
   (``"\\n\\n\\n"``, the Qwen stop token, ``"</answer>"``), restores the
   stripped closing tag, and sets ``logprobs=true`` and
   ``top_logprobs=--top-logprobs`` (default 20).
4. Scores each answer with ``math_verify`` through ``seeding_scoring.score_answer_or_error``.
   A scorer that cannot grade a row excludes it; it is never scored wrong.
5. Writes each row through ``eval_tower._EvalQuestionJsonlWriter`` with the
   EV-CONF-2 ``token_logprobs`` capture (``eval_tower._token_logprob_trace``).
   The output is ``question_results.<arm>.jsonl``, which
   ``confidence_source_compare.py`` reads unchanged. A per-row ``probe`` key
   adds the E7c stratum, the spec-decoding counters and the placeholder count.
6. Records the serving identity (``/v1/models``, ``/props``, ``/slots``,
   declared and observed spec state, sampling payload, registry digest) in
   ``serving_identity.<arm>.json``.
7. Persists **one row at a time** (fsync per row) and resumes: a re-run skips
   every ordinal that already has a non-error row.
8. **Arm A (``A-specoff``) fails closed on speculative decoding.** A ``/slots``
   entry with ``speculative: true`` fails before the first request. Any response
   with ``timings.draft_n > 0``, or any placeholder token (``logprob == 0`` with
   no top-k), fails the run with exit code 3. The offending row goes to
   ``rejected.<arm>.jsonl`` and never into the arm's sidecar.
   ``/props`` is NOT trusted for spec state: llama-server builds its
   ``default_generation_settings`` from the sampling params only, so the
   ``speculative.*`` fields there show defaults, not the launch.
   Arm B (``B-mtp``) requires spec to be declared or observed, and records the
   placeholder fraction. It is the artifact control.

Zero inference happens at import time or under ``--manifest-only``. The launch
recipes for both arms are in ``RUNNER_RECIPES`` (printed by ``--print-recipes``).
This module never launches or stops a server.

Read the result with
``confidence_source_compare.py <out>/question_results.<arm>.jsonl --reweight-prevalence 0.7886``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import sys
import time
import types
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (REPO_ROOT, REPO_ROOT / "scripts" / "autopilot", REPO_ROOT / "scripts" / "benchmark"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import httpx  # noqa: E402

import eval_tower  # noqa: E402

MANIFEST_SCHEMA = "epyc.ev_conf2_probe_manifest.v1"
IDENTITY_SCHEMA = "epyc.ev_conf2_probe_identity.v1"
ARMS = ("A-specoff", "B-mtp")
SPEC_OFF_ARM = "A-specoff"
SPEC_ON_ARM = "B-mtp"
E7C_DIR = REPO_ROOT / "orchestration" / "reports" / "eval_tower_math_rebaseline_E7c"
DEFAULT_E7C_SIDECAR = E7C_DIR / "question_results.ev11-worker_general.jsonl"
DEFAULT_E7C_SUMMARY = E7C_DIR / "summary.json"
DEFAULT_OUT_DIR = REPO_ROOT / "orchestration" / "reports" / "ev_conf2_probe"
SCORING_METHOD = "math_verify"
# direct_stage.py: default_tokens = 2048 for non-MCQ, non-code prompts. E7c's
# worker_general max tokens_generated is exactly 2048.
DIRECT_STAGE_MAX_TOKENS = 2048
# E7c worker_general accuracy (1328/1684); the prevalence for reweighted ECE.
E7C_WORKER_GENERAL_PREVALENCE = 0.7886

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_SPEC_IN_SPEC_OFF_ARM = 3
EXIT_IDENTITY = 4

MODEL = "/mnt/raid0/llm/models/gemma-4-26B-A4B-it-ORIG-Q4_K_M.gguf"
DRAFTER = "/mnt/raid0/llm/models/gemma-4-26B-A4B-it-assistant-v6-Q8_0.gguf"
CHAMPION_BIN = "/mnt/raid0/llm/tmp/build-fold-ef81196d5/bin/llama-server"
_COMMON_LAUNCH = (
    "env -u HSA_OVERRIDE_GFX_VERSION "
    "LD_LIBRARY_PATH=/mnt/raid0/llm/tmp/build-fold-ef81196d5/bin OMP_NUM_THREADS=1 "
    "taskset -c 184-191 "
    f"{CHAMPION_BIN} -m {MODEL} --device ROCm0 -ngl 99 "
    "--jinja --reasoning off -fa on -ctk q8_0 -ctv q8_0 -c 16384 -np 1 "
    "-t 8 -tb 8 -ub 512 --no-mmap --metrics --slots --host 127.0.0.1"
)
# The GPU runner executes these. This module never does.
RUNNER_RECIPES: dict[str, dict[str, str]] = {
    SPEC_OFF_ARM: {
        "port": "18381",
        "launch": f"{_COMMON_LAUNCH} --port 18381",
        "probe": (
            ".venv/bin/python scripts/analysis/confidence_probe.py --arm A-specoff "
            "--endpoint http://127.0.0.1:18381"
        ),
    },
    SPEC_ON_ARM: {
        "port": "18382",
        "launch": (
            f"{_COMMON_LAUNCH} --port 18382 -md {DRAFTER} -ngld 99 -devd ROCm0 "
            "--spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-p-min 0.0"
        ),
        "probe": (
            ".venv/bin/python scripts/analysis/confidence_probe.py --arm B-mtp "
            "--endpoint http://127.0.0.1:18382"
        ),
    },
}
RUNNER_PREAMBLE = """\
# EV-CONF-2 probe on the MI210. This is an inference slot plus a GPU region
# claim, not a stack change. Run the arms SERIALLY, one resident server at a
# time.
# 0. Re-hash the champion binary (it lives under tmp/), then prove linkage:
#      sha256sum {bin}   # expect 869effe5...
#      epyc-inference-research/scripts/utils/verify_ggml_linkage.sh ...
#    During the run, sample VRAM non-zero and the KFD process count at least
#    twice. Invoking the HIP build does not prove a HIP run.
# 1. Dry-draw first (no inference): confidence_probe.py --manifest-only
# 2. For each arm: launch, wait for /health, run the probe, kill ONLY the PID
#    you captured, and confirm it is dead with ps -p. The probe resumes if it
#    is interrupted.
# 3. Read each arm with:
#      confidence_source_compare.py orchestration/reports/ev_conf2_probe/question_results.<arm>.jsonl \\
#        --reweight-prevalence {prev} --out orchestration/reports/ev_conf2_probe/compare.<arm>.json
# 4. Belief write side (VB-EVCONF2, root repo; until root c8c68662 merges, use the
#    /mnt/raid0/llm/worktrees/sub-evconf2-root copy), once per arm, right after step 3:
#      python3 /workspace/scripts/vidya/adapters/confidence_source_capture.py \\
#        --report .../compare.<arm>.json --identity .../serving_identity.<arm>.json \\
#        --arm <arm> --run-id evconf2-probe-<date> --binary-path {bin} --binary-sha256 <step-0 hash>
""".format(bin=CHAMPION_BIN, prev=E7C_WORKER_GENERAL_PREVALENCE)


class ProbeError(RuntimeError):
    """A refusal that must stop the run (identity, manifest or dataset drift)."""

    exit_code = EXIT_IDENTITY


class SpecDecodingDetected(ProbeError):
    exit_code = EXIT_SPEC_IN_SPEC_OFF_ARM


# ── E7c sample ────────────────────────────────────────────────────────────


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_e7c_outcomes(path: Path) -> dict[str, dict[str, Any]]:
    """``question_id -> {qid, correct, ordinal}`` for E7c rows with a real verdict.

    Error rows and non-``scored`` dispositions are excluded, exactly as
    ``confidence_source_compare.load_rows`` does. On a duplicate ordinal, the
    last write wins.
    """
    by_ordinal: dict[int, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("row_type") != "question_result" or not isinstance(row.get("result"), dict):
            continue
        by_ordinal[int(row.get("ordinal", -1))] = row
    out: dict[str, dict[str, Any]] = {}
    for ordinal, row in by_ordinal.items():
        res = row["result"]
        if res.get("error") or res.get("disposition") not in (None, "", "scored"):
            continue
        qid_name = str(res.get("question_id") or "")
        if not qid_name:
            continue
        out[qid_name] = {
            "qid": str(res.get("qid") or ""),
            "correct": bool(res.get("correct")),
            "ordinal": ordinal,
            "answer_hash": res.get("answer_hash"),
            "confidence": res.get("confidence"),
            "tokens_generated": res.get("tokens_generated"),
        }
    return out


def draw_stratified(
    outcomes: Mapping[str, Mapping[str, Any]], *, n_wrong: int, n_right: int, seed: int
) -> list[dict[str, Any]]:
    """Seeded stratified draw. Returns rows in the shuffled probe order."""
    wrong = sorted(k for k, v in outcomes.items() if not v["correct"])
    right = sorted(k for k, v in outcomes.items() if v["correct"])
    if len(wrong) < n_wrong or len(right) < n_right:
        raise ProbeError(
            f"stratum too small: wrong={len(wrong)} (need {n_wrong}) right={len(right)} (need {n_right})"
        )
    rng = random.Random(seed)
    picked = [(k, "e7c_wrong") for k in rng.sample(wrong, n_wrong)]
    picked += [(k, "e7c_right") for k in rng.sample(right, n_right)]
    rng.shuffle(picked)
    rows = []
    for probe_ordinal, (question_id, stratum) in enumerate(picked):
        o = outcomes[question_id]
        rows.append(
            {
                "probe_ordinal": probe_ordinal,
                "question_id": question_id,
                "qid": o["qid"],
                "stratum": stratum,
                "e7c_correct": bool(o["correct"]),
                "e7c_ordinal": o["ordinal"],
                "e7c_answer_hash": o.get("answer_hash"),
                "e7c_confidence": o.get("confidence"),
                "e7c_tokens_generated": o.get("tokens_generated"),
            }
        )
    return rows


def sample_digest(rows: Sequence[Mapping[str, Any]]) -> str:
    h = hashlib.sha256()
    for r in rows:
        h.update(f"{r['question_id']}\x00{r['qid']}\x00{r['stratum']}\x1e".encode())
    return h.hexdigest()


def build_manifest(
    *, sidecar: Path, summary: Path | None, n_wrong: int, n_right: int, seed: int
) -> dict[str, Any]:
    outcomes = load_e7c_outcomes(sidecar)
    rows = draw_stratified(outcomes, n_wrong=n_wrong, n_right=n_right, seed=seed)
    dataset_sha = None
    if summary is not None and summary.exists():
        dataset_sha = (json.loads(summary.read_text()).get("result") or {}).get("dataset_sha256")
    n_scored = len(outcomes)
    n_correct = sum(1 for v in outcomes.values() if v["correct"])
    return {
        "schema": MANIFEST_SCHEMA,
        "source_sidecar": {"path": _rel(sidecar), "sha256": _sha256_file(sidecar)},
        "source_role": "worker_general",
        "source_scored": n_scored,
        "source_accuracy": round(n_correct / n_scored, 4) if n_scored else None,
        "e7c_dataset_sha256": dataset_sha,
        "seed": seed,
        "n_wrong": n_wrong,
        "n_right": n_right,
        "draw": "random.Random(seed).sample(sorted(ids)) wrong then right, then shuffle",
        "sample_sha256": sample_digest(rows),
        "rows": rows,
    }


def _rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def ensure_manifest(out_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Write the manifest, or verify that an existing one draws the identical sample."""
    path = out_dir / "sample_manifest.json"
    if path.exists():
        existing = json.loads(path.read_text())
        if existing.get("sample_sha256") != manifest["sample_sha256"]:
            raise ProbeError(
                f"{path} draws a different sample ({existing.get('sample_sha256')} != "
                f"{manifest['sample_sha256']}); refuse to mix samples in one output dir"
            )
        return existing
    out_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


# ── dataset ───────────────────────────────────────────────────────────────


def _prepare(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Same normalisation as EvalTower.eval_math_rebaseline, so the digest matches.
    for q in questions:
        q.setdefault("suite", "math")
        q["scoring_method"] = SCORING_METHOD
    return questions


def load_questions(questions_jsonl: Path | None) -> list[dict[str, Any]]:
    if questions_jsonl is not None:
        return _prepare(
            [json.loads(line) for line in questions_jsonl.read_text().splitlines() if line.strip()]
        )
    adapters = eval_tower._load_research_benchmark_module("dataset_adapters")
    adapter = adapters.get_adapter("math")
    if adapter is None:
        raise ProbeError("no research dataset adapter for suite 'math'")
    return _prepare(adapter.extract_all())


def resolve_questions(
    manifest: Mapping[str, Any],
    questions: list[dict[str, Any]],
    *,
    allow_dataset_drift: bool,
) -> tuple[list[dict[str, Any]], str]:
    digest = eval_tower.dataset_content_sha256(questions)
    expected = manifest.get("e7c_dataset_sha256")
    if expected and digest != expected and not allow_dataset_drift:
        raise ProbeError(
            f"dataset_sha256 {digest} != E7c {expected} (n={len(questions)}); "
            "the probe must use the E7c question set (--allow-dataset-drift to override)"
        )
    by_id = {str(q.get("id")): q for q in questions}
    picked: list[dict[str, Any]] = []
    for row in manifest["rows"]:
        q = by_id.get(row["question_id"])
        if q is None:
            raise ProbeError(f"sampled question {row['question_id']} missing from dataset")
        qid = eval_tower._question_result_qid(q)
        if row["qid"] and qid != row["qid"]:
            raise ProbeError(
                f"qid drift for {row['question_id']}: dataset {qid} != E7c {row['qid']}"
            )
        picked.append(q)
    return picked, digest


# ── serving request ───────────────────────────────────────────────────────


def production_sampling(role: str, registry_path: Path | None = None) -> dict[str, Any]:
    """The per-request sampling the orchestrator sends for ``role``, plus provenance."""
    from src.backends.llama_server import LlamaServerBackend
    from src.registry.registry_loader import RegistryLoader

    loader = RegistryLoader(registry_path=registry_path, validate_paths=False)
    role_config = loader.get_role(role)
    payload: dict[str, Any] = {}
    request = types.SimpleNamespace(temperature=None, top_k=None, top_p=None, seed=None)
    # _apply_deterministic_sampling never reads `self`; calling it unbound keeps
    # exact parity with the production chat path without building a backend.
    LlamaServerBackend._apply_deterministic_sampling(None, payload, role_config, request)  # type: ignore[arg-type]
    return {
        "payload": payload,
        "chat_template_kwargs": loader.get_role_chat_template_kwargs(role),
        "registry_path": _rel(loader.registry_path),
        "registry_sha256": _sha256_file(Path(loader.registry_path)),
        "role": role,
        "model_path": role_config.model.path,
        "acceleration": {
            "type": role_config.acceleration.type,
            "draft_role": role_config.acceleration.draft_role,
        },
        "provenance": "LlamaServerBackend._apply_deterministic_sampling(role_config)",
    }


def direct_stage_stops() -> list[str]:
    try:
        from src.config import get_config

        qwen_stop = str(get_config().llm.qwen_stop_token)
    except Exception:  # noqa: BLE001 - config unavailable; use the shipped default
        qwen_stop = "<|im_end|>"
    return list(dict.fromkeys(["\n\n\n", qwen_stop, "</answer>"]))


def restore_answer_close_tag(answer: str) -> str:
    """Mirror of ``direct_stage._restore_stripped_answer_stop``."""
    if answer and "<answer>" in answer and "</answer>" not in answer:
        return answer + "</answer>"
    return answer


def build_payload(
    prompt: str,
    *,
    sampling: Mapping[str, Any],
    top_logprobs: int,
    max_tokens: int,
    stop: Sequence[str],
    chat_template_kwargs: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "messages": [{"role": "user", "content": prompt.strip()}],
        "max_tokens": int(max_tokens),
        "stream": False,
        **dict(sampling),
        "logprobs": True,
        "top_logprobs": max(1, min(int(top_logprobs), 20)),
    }
    if stop:
        payload["stop"] = list(stop)
    if chat_template_kwargs:
        payload["chat_template_kwargs"] = dict(chat_template_kwargs)
    return payload


def _get_json(client: httpx.Client, url: str) -> dict[str, Any]:
    try:
        resp = client.get(url, timeout=30.0)
        if resp.status_code != 200:
            return {"_error": f"http_{resp.status_code}"}
        data = resp.json()
        return data if isinstance(data, dict) else {"_list": data}
    except (httpx.HTTPError, ValueError) as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}


def serving_identity(client: httpx.Client, endpoint: str) -> dict[str, Any]:
    models = _get_json(client, f"{endpoint}/v1/models")
    props = _get_json(client, f"{endpoint}/props")
    slots = _get_json(client, f"{endpoint}/slots")
    slot_list = slots.get("_list") if isinstance(slots.get("_list"), list) else None
    slot_spec = (
        [bool(s.get("speculative")) for s in slot_list if isinstance(s, dict)]
        if slot_list is not None
        else None
    )
    params = ((props.get("default_generation_settings") or {}).get("params") or {})
    return {
        "endpoint": endpoint,
        "v1_models": models,
        "props": {
            k: props.get(k)
            for k in ("model_path", "model_alias", "build_info", "total_slots", "_error")
            if k in props
        }
        | {"n_ctx": (props.get("default_generation_settings") or {}).get("n_ctx")},
        # Recorded, never trusted: /props builds these from sampling defaults only.
        "props_speculative_unreliable": {
            k: params.get(k) for k in ("speculative.types", "speculative.n_max") if k in params
        },
        "slots_error": slots.get("_error"),
        "slots_speculative": slot_spec,
        # None = unknown (/slots disabled or failing); otherwise any slot can speculate.
        "spec_declared": None if slot_spec is None else any(slot_spec),
    }


@dataclass
class Generation:
    answer: str = ""
    raw_answer: str = ""
    logprob_rows: list[dict[str, Any]] = field(default_factory=list)
    tokens_generated: int = 0
    finish_reason: str = ""
    elapsed_s: float = 0.0
    draft_n: int = 0
    draft_n_accepted: int = 0
    timings: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    infra_reason: str = ""
    served_model: str = ""


def generate(client: httpx.Client, endpoint: str, payload: Mapping[str, Any], timeout: float) -> Generation:
    start = time.time()
    try:
        resp = client.post(f"{endpoint}/v1/chat/completions", json=dict(payload), timeout=timeout)
    except httpx.TimeoutException as exc:
        return Generation(elapsed_s=time.time() - start, error=f"read_timeout: {exc!r}", infra_reason="read_timeout")
    except httpx.HTTPError as exc:
        return Generation(elapsed_s=time.time() - start, error=f"connect_error: {exc!r}", infra_reason="connect_error")
    elapsed = time.time() - start
    if resp.status_code != 200:
        return Generation(
            elapsed_s=elapsed,
            error=f"http_status {resp.status_code}: {resp.text[:200]}",
            infra_reason="http_status",
        )
    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        return Generation(elapsed_s=elapsed, error="empty_response: no choices", infra_reason="empty_response")
    ch = choices[0]
    raw = str((ch.get("message") or {}).get("content") or "")
    lp = ch.get("logprobs")
    rows = [r for r in (lp.get("content") or []) if isinstance(r, dict)] if isinstance(lp, dict) else []
    timings = data.get("timings") or {}
    usage = data.get("usage") or {}
    gen = Generation(
        answer=restore_answer_close_tag(raw.strip()),
        raw_answer=raw,
        logprob_rows=rows,
        tokens_generated=int(usage.get("completion_tokens") or len(rows)),
        finish_reason=str(ch.get("finish_reason") or ""),
        elapsed_s=elapsed,
        draft_n=int(timings.get("draft_n") or 0),
        draft_n_accepted=int(timings.get("draft_n_accepted") or 0),
        timings={k: timings.get(k) for k in ("prompt_n", "predicted_n", "predicted_per_second") if k in timings},
        served_model=str(data.get("model") or ""),
    )
    if not raw.strip():
        gen.error = "empty_response: blank content"
        gen.infra_reason = "empty_response"
    return gen


# ── persistence ───────────────────────────────────────────────────────────


class ProbeSidecarWriter(eval_tower._EvalQuestionJsonlWriter):
    """The eval-tower writer, plus an additive per-row ``probe`` key."""

    _pending_probe: dict[str, Any] | None = None

    def append_probe_result(self, *, ordinal: int, result: Any, probe: dict[str, Any]) -> None:
        self._pending_probe = probe
        try:
            self.append_result(ordinal=ordinal, result=result)
        finally:
            self._pending_probe = None

    def append_row(self, row: dict[str, Any]) -> None:
        if self._pending_probe is not None and row.get("row_type") == "question_result":
            row = {**row, "probe": self._pending_probe}
        super().append_row(row)


def completed_ordinals(path: Path, eval_batch_id: str) -> set[int]:
    """Ordinals that already hold a non-error row. Refuses a sidecar from another batch."""
    done: set[int] = set()
    if not path.exists():
        return done
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("eval_batch_id") not in (None, eval_batch_id):
            raise ProbeError(
                f"{path} belongs to batch {row.get('eval_batch_id')!r}, not {eval_batch_id!r}"
            )
        if row.get("row_type") != "question_result":
            continue
        res = row.get("result") or {}
        if res.get("error"):
            done.discard(int(row["ordinal"]))  # last write wins; an error is retried
        else:
            done.add(int(row["ordinal"]))
    return done


def _append_jsonl(path: Path, row: Mapping[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def _git_head() -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


# ── run ───────────────────────────────────────────────────────────────────


Scorer = Callable[[str, str, str, dict[str, Any]], "tuple[bool | None, str | None]"]


def _default_scorer() -> Scorer:
    eval_tower._require_math_verify()
    from seeding_scoring import score_answer_or_error

    return score_answer_or_error  # type: ignore[return-value]


@dataclass
class ProbeConfig:
    arm: str
    endpoint: str
    out_dir: Path
    role: str = "worker_general"
    top_logprobs: int = 20
    max_tokens: int = DIRECT_STAGE_MAX_TOKENS
    timeout: float = 900.0
    limit: int | None = None
    registry_path: Path | None = None


def run_probe(
    cfg: ProbeConfig,
    manifest: Mapping[str, Any],
    questions: Sequence[dict[str, Any]],
    dataset_sha256: str,
    *,
    client: httpx.Client,
    scorer: Scorer | None = None,
    sampling: Mapping[str, Any] | None = None,
    log: Callable[[str], None] = lambda m: print(m, file=sys.stderr),
) -> dict[str, Any]:
    if cfg.arm not in ARMS:
        raise ProbeError(f"unknown arm {cfg.arm!r}; expected one of {ARMS}")
    endpoint = cfg.endpoint.rstrip("/")
    scorer = scorer or _default_scorer()
    sampling = dict(sampling or production_sampling(cfg.role, cfg.registry_path))
    stops = direct_stage_stops()
    arm = cfg.arm
    out_dir = cfg.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    identity = serving_identity(client, endpoint)
    if identity["v1_models"].get("_error"):
        raise ProbeError(f"endpoint not serving: /v1/models {identity['v1_models']['_error']}")
    if arm == SPEC_OFF_ARM:
        if identity["spec_declared"]:
            raise SpecDecodingDetected(
                f"arm {arm}: /slots reports speculative=true {identity['slots_speculative']}"
            )
        if identity["spec_declared"] is None:
            log(f"WARN arm {arm}: /slots unavailable ({identity['slots_error']}); "
                "relying on per-response draft_n and placeholder detection")
    elif identity["spec_declared"] is False:
        raise ProbeError(f"arm {arm}: /slots reports speculative=false; this is not the MTP arm")

    batch_id = f"evconf2-probe-{arm}-{manifest['sample_sha256'][:12]}"
    sidecar = out_dir / f"question_results.{arm}.jsonl"
    rejected = out_dir / f"rejected.{arm}.jsonl"
    done = completed_ordinals(sidecar, batch_id)
    identity_record = {
        "schema": IDENTITY_SCHEMA,
        "arm": arm,
        "spec_expected": arm == SPEC_ON_ARM,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "eval_batch_id": batch_id,
        "orchestrator_head": _git_head(),
        "dataset_sha256": dataset_sha256,
        "sample_sha256": manifest["sample_sha256"],
        "source_sidecar": manifest.get("source_sidecar"),
        "sampling": sampling,
        "request": {
            "path": "/v1/chat/completions",
            "top_logprobs": cfg.top_logprobs,
            "max_tokens": cfg.max_tokens,
            "stop": stops,
            "restore_answer_close_tag": True,
            "scoring_method": SCORING_METHOD,
        },
        "serving": identity,
        "resumed_with_done": len(done),
    }
    identity_path = out_dir / f"serving_identity.{arm}.json"
    history = []
    if identity_path.exists():
        prev = json.loads(identity_path.read_text())
        history = prev.get("segments", [])
        first = history[0] if history else {}
        for key in ("model_path", "build_info"):
            a, b = (first.get("serving") or {}).get("props", {}).get(key), identity["props"].get(key)
            if a and b and a != b:
                raise ProbeError(f"serving identity changed on resume: {key} {a!r} -> {b!r}")
    history.append(identity_record)
    identity_path.write_text(json.dumps({"segments": history}, indent=2, sort_keys=True) + "\n")

    rows = list(manifest["rows"])
    writer = ProbeSidecarWriter(
        root=out_dir,
        root_source="ev_conf2_confidence_probe",
        eval_batch_id=batch_id,
        trial_id=None,
        label=f"evconf2-probe-{arm}",
        requested_n=len(rows),
        concurrency=1,
        path=sidecar,
    )
    t0 = time.time()
    stats = {"attempted": 0, "scored": 0, "errors": 0, "placeholder_tokens": 0, "tokens": 0,
             "draft_n": 0, "draft_n_accepted": 0, "rows_with_placeholder": 0,
             "agree_with_e7c": 0, "correct": 0}
    try:
        if not done:
            writer.append_start()
        todo = [r for r in rows if int(r["probe_ordinal"]) not in done]
        if cfg.limit is not None:
            todo = todo[: max(0, int(cfg.limit))]
        for row, q in ((r, questions[int(r["probe_ordinal"])]) for r in todo):
            ordinal = int(row["probe_ordinal"])
            scoring_config = q.get("scoring_config") if isinstance(q.get("scoring_config"), dict) else {}
            payload = build_payload(
                str(q.get("prompt", "")),
                sampling=sampling["payload"],
                top_logprobs=cfg.top_logprobs,
                max_tokens=cfg.max_tokens,
                stop=stops,
                chat_template_kwargs=sampling.get("chat_template_kwargs"),
            )
            gen = generate(client, endpoint, payload, cfg.timeout)
            stats["attempted"] += 1
            trace = None
            if not gen.error:
                trace = eval_tower._token_logprob_trace(
                    gen.logprob_rows, answer=gen.answer, scoring_config=scoring_config
                )
            n_placeholder = int((trace or {}).get("n_placeholder", 0))
            probe = {
                "arm": arm,
                "stratum": row["stratum"],
                "e7c_correct": row["e7c_correct"],
                "e7c_answer_hash": row.get("e7c_answer_hash"),
                "draft_n": gen.draft_n,
                "draft_n_accepted": gen.draft_n_accepted,
                "n_placeholder": n_placeholder,
                "placeholder_detection": (trace or {}).get("placeholder_detection"),
                "finish_reason": gen.finish_reason,
                "served_model": gen.served_model,
                "timings": gen.timings,
            }
            if arm == SPEC_OFF_ARM and not gen.error and (gen.draft_n > 0 or n_placeholder > 0):
                _append_jsonl(rejected, {"ordinal": ordinal, "question_id": row["question_id"],
                                         "reason": "speculative_decoding_in_spec_off_arm", "probe": probe})
                raise SpecDecodingDetected(
                    f"arm {arm} row {ordinal} ({row['question_id']}): draft_n={gen.draft_n} "
                    f"n_placeholder={n_placeholder}; spec decoding is ON. Relaunch without "
                    "--spec-type/-md; the row was NOT written to the sidecar"
                )
            if not gen.error and trace is None:
                _append_jsonl(rejected, {"ordinal": ordinal, "question_id": row["question_id"],
                                         "reason": "no_token_logprobs", "probe": probe})
                raise ProbeError(
                    f"row {ordinal}: the server returned no logprobs.content; "
                    "the probe cannot measure confidence (check logprobs/top_logprobs support)"
                )
            correct, error, disposition = False, gen.error, eval_tower.DISPOSITION_SCORED
            if gen.error:
                disposition = eval_tower.DISPOSITION_INFRA_FAILED
            else:
                verdict, score_err = scorer(gen.answer, str(q.get("expected", "")), SCORING_METHOD, scoring_config)
                if score_err:
                    error, disposition = score_err, eval_tower.DISPOSITION_SCORING_FAILED
                else:
                    correct = bool(verdict)
            confidence = None if gen.error else eval_tower._completion_probabilities_confidence(gen.logprob_rows)
            result = eval_tower.QuestionResult(
                question_id=str(q.get("id")),
                suite=str(q.get("suite", "math")),
                prompt=str(q.get("prompt", "")),
                expected=str(q.get("expected", "")),
                qid=row["qid"] or eval_tower._question_result_qid(q),
                answer=gen.answer,
                correct=correct,
                error=error,
                disposition=disposition,
                infra_reason=gen.infra_reason,
                tokens_generated=gen.tokens_generated,
                elapsed_s=gen.elapsed_s,
                route_used=f"{cfg.role}@probe:{arm}",
                scoring_method=SCORING_METHOD,
                confidence=float(confidence) if confidence is not None else 0.0,
                confidence_source=(
                    "completion_probabilities_geomean" if confidence is not None else "binary_correctness_proxy"
                ),
                token_logprobs=trace,
            )
            writer.append_probe_result(ordinal=ordinal, result=result, probe=probe)
            if error:
                stats["errors"] += 1
                log(f"[{arm}] {ordinal} {row['question_id']} ERROR {error[:120]}")
                continue
            stats["scored"] += 1
            stats["correct"] += int(correct)
            stats["agree_with_e7c"] += int(correct == row["e7c_correct"])
            stats["tokens"] += int((trace or {}).get("n_tokens", 0))
            stats["placeholder_tokens"] += n_placeholder
            stats["rows_with_placeholder"] += int(n_placeholder > 0)
            stats["draft_n"] += gen.draft_n
            stats["draft_n_accepted"] += gen.draft_n_accepted
            done.add(ordinal)
            if stats["attempted"] % 10 == 0:
                log(f"[{arm}] {len(done)}/{len(rows)} done, segment scored={stats['scored']}")
        if arm == SPEC_ON_ARM and stats["scored"] and not (stats["draft_n"] or stats["placeholder_tokens"]):
            raise ProbeError(
                f"arm {arm}: {stats['scored']} rows and zero draft tokens/placeholders; spec decoding is not engaged"
            )
        complete = len(done) == len(rows)
        if complete:
            writer.append_complete(completed_n=len(done), elapsed_s=time.time() - t0)
    finally:
        writer.close()
    summary = {
        "arm": arm,
        "eval_batch_id": batch_id,
        "sidecar": str(sidecar),
        "complete": len(done) == len(rows),
        "done": len(done),
        "requested": len(rows),
        "segment": stats,
        "read_with": (
            f"scripts/analysis/confidence_source_compare.py {sidecar} "
            f"--reweight-prevalence {E7C_WORKER_GENERAL_PREVALENCE}"
        ),
    }
    (out_dir / f"probe_summary.{arm}.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--arm", choices=ARMS)
    ap.add_argument("--endpoint", help="OpenAI-compatible base URL, e.g. http://127.0.0.1:18381")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--e7c-sidecar", type=Path, default=DEFAULT_E7C_SIDECAR)
    ap.add_argument("--e7c-summary", type=Path, default=DEFAULT_E7C_SUMMARY)
    ap.add_argument("--n-wrong", type=int, default=100)
    ap.add_argument("--n-right", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--role", default="worker_general")
    ap.add_argument("--registry", type=Path, default=None)
    ap.add_argument("--top-logprobs", type=int, default=20)
    ap.add_argument("--max-tokens", type=int, default=DIRECT_STAGE_MAX_TOKENS)
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--limit", type=int, default=None, help="at most N new rows this segment")
    ap.add_argument("--questions-jsonl", type=Path, default=None)
    ap.add_argument("--allow-dataset-drift", action="store_true")
    ap.add_argument("--manifest-only", action="store_true", help="draw and write the sample; no inference")
    ap.add_argument("--print-recipes", action="store_true", help="print the GPU launch recipes and exit")
    args = ap.parse_args(argv)

    if args.print_recipes:
        print(RUNNER_PREAMBLE)
        for arm, rec in RUNNER_RECIPES.items():
            print(f"# arm {arm}\n{rec['launch']}\n{rec['probe']}\n")
        return EXIT_OK
    try:
        manifest = ensure_manifest(
            args.out_dir,
            build_manifest(
                sidecar=args.e7c_sidecar,
                summary=args.e7c_summary,
                n_wrong=args.n_wrong,
                n_right=args.n_right,
                seed=args.seed,
            ),
        )
        if args.manifest_only:
            print(json.dumps({k: v for k, v in manifest.items() if k != "rows"}, indent=2, sort_keys=True))
            return EXIT_OK
        if not args.arm or not args.endpoint:
            ap.error("--arm and --endpoint are required unless --manifest-only/--print-recipes")
        questions, digest = resolve_questions(
            manifest, load_questions(args.questions_jsonl), allow_dataset_drift=args.allow_dataset_drift
        )
        cfg = ProbeConfig(
            arm=args.arm,
            endpoint=args.endpoint,
            out_dir=args.out_dir,
            role=args.role,
            top_logprobs=args.top_logprobs,
            max_tokens=args.max_tokens,
            timeout=args.timeout,
            limit=args.limit,
            registry_path=args.registry,
        )
        with httpx.Client() as client:
            summary = run_probe(cfg, manifest, questions, digest, client=client)
    except ProbeError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return exc.exit_code
    print(json.dumps(summary, indent=2, sort_keys=True))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
