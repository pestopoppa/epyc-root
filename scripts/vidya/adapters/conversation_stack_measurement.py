"""VB-SPEECH-CONV-1 (+1B..1E): the conversation-stack voice-measurement write side and projection.

INF-79 (`handoffs/active/conversation-stack.md`) produces a new measurement family -- interlocutor
bake-offs on the reference harness, GPU co-residency, end-to-end voice turns, the quantization
ladder, and since 2026-10-22 the STT bake-off (CS-8.STT3/STT5/STT6/STT7), the lexicon trial
(CS-8.LEX2), the VAD gate grid / end-of-turn / time-to-final (CS-22.V1/L1/T1), the LID router
(CS-26.LID1, as a ``generic`` row), the barge-in records (CS-49, CS-4 set 5) and the degraded-mode
contention screen (CS-26.F1). This module is filed BEFORE the first run: a producer writes
self-hashed rows through :func:`write_belief_measurements` (or maps a CS-8 scorer record through
:func:`stt_record_from_scorer` first) and the strict reader re-validates every row.

PROJECT, NEVER GRADE. ``project()`` maps one row into a :class:`ClaimTuple`;
``claim_tuple.grade()`` decides (spec §4.7). No ladder lives here and none may be added.

Row envelope (every kind): ``schema`` (the schema version), ``row_sha256`` (the row hash),
``run_id``, ``producer``, ``emitted_at``, ``date``, ``measurement_id``, ``record_kind``,
``subject``, ``metric``, ``value``, ``unit``, ``metric_direction`` (explicit, per metric),
``metric_direction_native``, ``category``, ``claim``, ``protocol_id`` (null until an admissible
protocol exists for the kind), ``reps``, ``reps_basis``, ``results_path`` + ``results_sha256``
(the attestation), ``harness`` and ``fields``.

``harness`` (the base VB-SPEECH-CONV-1 bullet, every measured kind): model and quant; the runtime
(``reference`` harness vs ``port``) with its binary sha256 or upstream digest; device and host-lane
placement; the co-tenant state sampled during the row (LLM, device, np, generating yes/no); and
whether the score is LLM-judged (then the judge pin -- the SC58 caution).

Record kinds (``record_kind``) and their extra fields (``fields``):

* ``generic`` -- the base harness row; any metric with an explicit direction.
* ``stt_arm_wer`` (1B) -- runner id/commit/ggml version, quant, backend, device + residency proof,
  weights sha256, decode options (+ KV dtype for transcribe.cpp whisper rows), language mode, the
  streaming lookahead (att_context right | delay_ms | unified (L,C,R)), normaliser id+sha, reference
  set id+track, scorer sha (+ secondary scorer sha and package versions), manifest sha256, n,
  unk_count + unk_ban, segmentation mode, stratum, ``corpus_id@manifest_sha256[:12]``,
  confirmation_reuse_n, the scorer ``column`` (``v1`` | ``v2_candidate``) and
  ``whisper_parity_gate_ref``.
* ``stt_fitting_screen`` (1B) -- arm, model revision, probe, accept_ref + interval, n_eligible,
  panel, predictions sha256, language, stratum; written in the SAME write as its WER row
  (``paired_wer_measurement_id``), which the reader re-checks file-wide.
* ``stt_lexicon_trial`` (1B) -- the STT-arm fields plus lexicon sha256, boost alpha, list scope,
  case policy, term recall/precision, insertions per hour and non-list-word WER.
* ``vad_arm`` / ``end_of_turn`` / ``time_to_final`` (1C).
* ``interruption`` (1D) -- timing oracle + gate under test (CS-45.2 circularity rule).
* ``coresidency_degraded`` (1E) -- A/B/A leg arm ids, region-lock claim id + cpu list, thread
  counts, the neighbour's identity and tok/s per leg, per-thread CPU time of the speech process.
* ``literature_reference`` -- vendor / model-card / leaderboard / hosted-board numbers and published
  reference rows (TurnBench, Full-Duplex-Bench, HumDial, VAP). These are NEVER our measurements:
  the reader keeps them out of :func:`native_rows`, ``project()`` refuses them, and
  :func:`literature_rows` hands them to the research-intake (``literature``-class) lane with their
  date, set list and normaliser.

Named refusals (each a ``ProjectionError`` at projection, a ``CaptureError`` at write):

* an STT tuple whose runner is not ``production-speech-v1`` and carries no
  ``whisper_parity_gate_ref`` (CS-8.STT3: a failing runner's whisper rows are never used);
* a confirmation/private-stratum tuple that carries per-utterance values (the loop sees aggregates
  only; CS-8.STT6 per-item files stay sealed);
* a VAD tuple without its weights sha256;
* an interruption tuple whose timing oracle IS the gate under test (CS-45.2 (c));
* a degraded-mode tuple without A/B/A arm ids or the region-lock claim id.

Direction vocabulary. ``ClaimTuple`` knows exactly ``higher_better`` / ``lower_better``. The
producer words map as follows, and the producer's own word is kept verbatim in
``metric_direction_native``: ``lower`` -> ``lower_better``; ``higher`` -> ``higher_better``;
``higher_is_correct`` / ``higher-is-correct`` (t_stop on backchannel, off-talk and background
speech: the system SHOULD keep talking, so a longer time-to-stop is the correct behaviour) ->
``higher_better``. The fitting screen's accept-ref is a fitting INDICATOR (higher = more fitting =
less trustworthy public WER), so it is fixed ``lower_better``. This is a vocabulary mapping, not a
grading rule.

Protocol. Until the CS-2 Annex S amendment is ratified every row projects with an empty
``protocol_id`` -- an OBSERVATION. The only admissible citation today is the ratified ``P-STT-1``
on an STT-arm WER row in the ``v1`` column; a ``v2_candidate`` column row (``candidate: true``)
projects as an observation, never as a gradeable claim against P-STT-1. A non-admissible citation
is kept verbatim in ``extra.protocol_id_native`` and the tuple is graded as the observation it is.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

SCHEMA = "epyc.vidya.conversation_stack_measurement.v1"
SIDECAR_NAME = "conversation_stack.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.conversation_stack_measurement/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "conversation-stack-measurement"

PRODUCTION_SPEECH_TAG = "production-speech-v1"
#: whisper.cpp production-speech-v1 (`b30737922`, CLAUDE.md production kernel set). A runner that
#: names the production tag must also carry the production commit, or the parity-gate exemption
#: could be claimed by a label.
PRODUCTION_WHISPER_COMMIT_PREFIX = "b3073792"

LITERATURE_KIND = "literature_reference"
STT_KINDS = frozenset({"stt_arm_wer", "stt_lexicon_trial"})
RECORD_KINDS = frozenset({
    "generic", "stt_arm_wer", "stt_fitting_screen", "stt_lexicon_trial", "vad_arm", "end_of_turn",
    "time_to_final", "interruption", "coresidency_degraded", LITERATURE_KIND,
})

# --- the direction vocabulary (mapping, not grading) -----------------------------------------
LOWER, HIGHER = "lower_better", "higher_better"
NATIVE_DIRECTION_ALIASES = {
    "lower": LOWER, "lower_better": LOWER, "lower-better": LOWER,
    "higher": HIGHER, "higher_better": HIGHER, "higher-better": HIGHER,
    "higher_is_correct": HIGHER, "higher-is-correct": HIGHER,
}
#: Known metrics and their fixed direction (VB-SPEECH-CONV-1 + the 2026-10-20 extension). A row
#: naming one of these with the other direction is refused; an unknown metric on a ``generic`` row
#: must carry its own explicit direction.
METRIC_DIRECTIONS = {
    # lower_better
    "false_cut_rate": LOWER, "eot_fpr": LOWER, "int_fpr": LOWER, "latency_ms": LOWER,
    "turn_latency_ms": LOWER, "eot_latency_ms": LOWER, "interruption_t_stop_s": LOWER,
    "cancel_latency_ms": LOWER, "cpu_ms": LOWER, "ttfa_ms": LOWER, "rtf": LOWER,
    "stt_rtf_solo": LOWER, "stt_rtf_corun": LOWER, "wer_pct": LOWER, "stt_corpus_wer": LOWER,
    "co_tenant_slowdown": LOWER, "time_to_final_after_vad_end_s": LOWER,
    "stt_fitting_accept_ref": LOWER, "lexicon_insertions_per_hour": LOWER,
    "lexicon_non_list_word_wer": LOWER, "lid_latency_ms": LOWER,
    # higher_better
    "eot_recall": HIGHER, "pasr": HIGHER, "interruption_respond_rate": HIGHER,
    "routing_precision": HIGHER, "routing_recall": HIGHER, "paralinguistic_accuracy": HIGHER,
    "exact_value_retention": HIGHER, "lid_accuracy": HIGHER, "lexicon_term_recall": HIGHER,
    "lexicon_term_precision": HIGHER, "neighbour_tok_s": HIGHER,
    # higher-is-correct, mapped to higher_better (see module docstring)
    "t_stop_backchannel_s": HIGHER, "t_stop_off_talk_s": HIGHER,
    "t_stop_background_speech_s": HIGHER,
}
HIGHER_IS_CORRECT_METRICS = frozenset({
    "t_stop_backchannel_s", "t_stop_off_talk_s", "t_stop_background_speech_s"})

LEXICON_METRIC_FIELD = {
    "lexicon_term_recall": "term_recall", "lexicon_term_precision": "term_precision",
    "lexicon_insertions_per_hour": "insertions_per_hour",
    "lexicon_non_list_word_wer": "non_list_word_wer",
}
KIND_METRICS: dict[str, frozenset[str] | None] = {
    "generic": None,
    "stt_arm_wer": frozenset({"stt_corpus_wer"}),
    "stt_fitting_screen": frozenset({"stt_fitting_accept_ref"}),
    "stt_lexicon_trial": frozenset(LEXICON_METRIC_FIELD),
    "vad_arm": frozenset({"false_cut_rate", "eot_fpr", "eot_recall", "int_fpr", "eot_latency_ms",
                          "latency_ms", "cpu_ms"}),
    "end_of_turn": frozenset({"eot_recall", "eot_fpr", "int_fpr", "false_cut_rate",
                              "eot_latency_ms", "latency_ms", "cpu_ms"}),
    "time_to_final": frozenset({"time_to_final_after_vad_end_s"}),
    "interruption": frozenset({"interruption_t_stop_s", "t_stop_backchannel_s",
                               "t_stop_off_talk_s", "t_stop_background_speech_s",
                               "cancel_latency_ms", "int_fpr", "interruption_respond_rate",
                               "pasr"}),
    "coresidency_degraded": frozenset({"stt_rtf_corun", "stt_rtf_solo", "neighbour_tok_s",
                                       "co_tenant_slowdown", "cpu_ms"}),
    LITERATURE_KIND: None,
}

# --- protocol admissibility ------------------------------------------------------------------
#: Ratified protocols a row of each kind may carry into ``ClaimTuple.protocol_id``. EMPTY on purpose:
#: MEASUREMENT.md's protocol table says P-STT-1 WER is "not a claim without its owning release
#: protocol" (P-STT-REL-1, itself a verdict, not a claim), and a bake-off arm run in an experimental
#: tree is a P-AK-SEARCH-1 search record. So even a complete v1-column STT row stays an OBSERVATION
#: (its native citation is kept in ``extra.protocol_id_native``). Add an id here only when a ratified
#: instrument makes that row kind a claim (e.g. the CS-2 Annex S amendment; human-only).
ADMISSIBLE_PROTOCOLS: dict[str, frozenset[str]] = {}
TIME_TO_FINAL_METHOD = "aa-forced-endpoint-v1"

# --- vocabularies ----------------------------------------------------------------------------
RUNTIME_KINDS = frozenset({"reference", "port"})
REFERENCE_MARKER = "reference harness; not a serving claim"
LANGUAGE_MODES = frozenset({"forced", "auto"})
STT_COLUMNS = frozenset({"v1", "v2_candidate"})
VAD_RUNTIMES = frozenset({"onnx", "ggml", "jit"})
VAD_PARAMS = ("threshold", "smoothing", "padding", "min_speech", "min_silence")
TURN_ARMS = frozenset({"silence", "smart_turn", "parakeet_eou", "text_llm_prompt"})
TIMING_ORACLES = frozenset({"synthetic_timeline", "asr_word_times"})
INTERRUPTION_SETS = frozenset({"CS-49", "CS-4.set5"})
LITERATURE_SOURCES = frozenset({"vendor", "model_card", "leaderboard", "hosted_board", "paper"})
CONFIRMATION_STRATA = frozenset({"confirmation", "private", "confirmation-private",
                                 "private-confirmation", "human_recorded-confirmation"})
PER_UTTERANCE_KEYS = frozenset({"utterances", "utterance_ids", "utterance_results", "per_item",
                                "per_clip", "per_utterance"})
JUDGE_KEYS = ("model", "model_digest", "prompt_sha256", "temperature", "seed")

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SHA_LIKE = re.compile(r"^[0-9a-f]{7,64}$")
_AT_HASH12 = re.compile(r"^.+@[0-9a-f]{12}$")


def _hex64(v: Any) -> bool:
    return isinstance(v, str) and bool(_HEX64.match(v))


def _sha_like(v: Any) -> bool:
    return isinstance(v, str) and bool(_SHA_LIKE.match(v))


def _pos_int(v: Any) -> bool:
    return ns.nonneg_int(v) and v >= 1


def _nonneg(v: Any) -> bool:
    return ns.finite(v) and v >= 0


def _unit_interval(v: Any) -> bool:
    return ns.finite(v) and 0 <= v <= 1


def is_production_runner(runner_id: Any) -> bool:
    return isinstance(runner_id, str) and (
        runner_id == PRODUCTION_SPEECH_TAG or runner_id.endswith("@" + PRODUCTION_SPEECH_TAG))


def is_confirmation_stratum(stratum: Any) -> bool:
    if not isinstance(stratum, str):
        return False
    s = stratum.strip().lower()
    return s in CONFIRMATION_STRATA or s.startswith(("confirmation", "private"))


def _per_utterance_paths(obj: Any, path: str = "") -> list[str]:
    """Every key under ``obj`` that carries per-utterance values (recursive)."""
    found: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            here = f"{path}.{key}" if path else str(key)
            k = str(key).lower()
            if k in PER_UTTERANCE_KEYS or "per_utterance" in k or k.startswith("utterance_"):
                found.append(here)
            found.extend(_per_utterance_paths(value, here))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, dict) and "utterance_id" in item:
                found.append(f"{path}[{i}].utterance_id")
            found.extend(_per_utterance_paths(item, f"{path}[{i}]"))
    return found


def _norm(text: Any) -> str:
    return " ".join(str(text or "").split()).casefold()


# --- per-block validators (each returns problems; empty == valid) ------------------------------

def _harness_problems(h: Any) -> list[str]:
    if not isinstance(h, dict):
        return ["harness must be an object (model, quant, runtime, device, host_lane, co_tenant)"]
    p = [f"harness.{k} must be a non-empty string"
         for k in ("model", "quant", "device", "host_lane") if not ns.text(h.get(k))]
    rt = h.get("runtime")
    if not isinstance(rt, dict) or rt.get("kind") not in RUNTIME_KINDS:
        p.append(f"harness.runtime.kind must be one of {sorted(RUNTIME_KINDS)} (reference vs port)")
    elif not (_hex64(rt.get("binary_sha256")) or ns.text(rt.get("upstream_digest"))):
        p.append("harness.runtime must carry binary_sha256 (64-hex) or upstream_digest")
    ct = h.get("co_tenant")
    if not isinstance(ct, dict) or ct.get("sampled_during_row") is not True \
            or not isinstance(ct.get("present"), bool):
        p.append("harness.co_tenant must record present (bool) and sampled_during_row=true -- "
                 "co-tenant state is part of the measurand and is sampled, never assumed")
    elif ct["present"]:
        if not (ns.text(ct.get("llm")) and ns.text(ct.get("device")) and _pos_int(ct.get("np"))
                and isinstance(ct.get("generating"), bool)):
            p.append("harness.co_tenant (present) must name llm, device, np (int >= 1) and "
                     "generating (bool)")
    judged = h.get("llm_judged")
    if not isinstance(judged, bool):
        p.append("harness.llm_judged must be a boolean (SC58: an LLM-judged score names its judge)")
    elif judged:
        j = h.get("judge")
        if not isinstance(j, dict) or not all(k in j for k in JUDGE_KEYS) or not (
                ns.text(j.get("model")) and ns.text(j.get("model_digest"))
                and _hex64(j.get("prompt_sha256"))):
            p.append(f"harness.judge must pin {list(JUDGE_KEYS)} (prompt_sha256 64-hex) for an "
                     "LLM-judged row -- pin the DIGEST, not the name (SC58)")
    return p


def _lookahead_problems(f: Mapping[str, Any], where: str) -> list[str]:
    la = f.get("lookahead")
    ok = (ns.nonneg_int(f.get("att_context_right")) or _nonneg(f.get("delay_ms"))
          or (isinstance(la, list) and len(la) == 3 and all(ns.nonneg_int(x) for x in la)))
    return [] if ok else [
        f"{where}: a streaming arm must carry att_context_right, delay_ms or the unified "
        "(L,C,R) lookahead"]


def _stt_arm_problems(f: Mapping[str, Any], h: Mapping[str, Any]) -> list[str]:
    p: list[str] = []
    for k in ("runner_id", "runner_commit", "ggml_version", "quant", "backend", "device",
              "residency_proof", "language", "normaliser_id", "reference_set_id",
              "reference_set_track", "segmentation_mode", "stratum", "corpus_id"):
        if not ns.text(f.get(k)):
            p.append(f"fields.{k} must be a non-empty string")
    for k in ("weights_sha256", "normaliser_sha256", "manifest_sha256"):
        if not _hex64(f.get(k)):
            p.append(f"fields.{k} must be a 64-hex sha256")
    if not _sha_like(f.get("scorer_sha256")):
        p.append("fields.scorer_sha256 must be a hex sha (7..64)")
    if not isinstance(f.get("decode_options"), dict) or not f["decode_options"]:
        p.append("fields.decode_options must be a non-empty object")
    if f.get("language_mode") not in LANGUAGE_MODES:
        p.append(f"fields.language_mode must be one of {sorted(LANGUAGE_MODES)}")
    if not _pos_int(f.get("n")):
        p.append("fields.n must be an integer >= 1")
    if not ns.nonneg_int(f.get("unk_count")) or not isinstance(f.get("unk_ban"), bool):
        p.append("fields.unk_count (int >= 0) and fields.unk_ban (bool) are required")
    if not ns.nonneg_int(f.get("confirmation_reuse_n")):
        p.append("fields.confirmation_reuse_n must be an integer >= 0")
    # P-STT-1's corpus grammar binds the CORPUS manifest (utterance_id, pcm_sha256,
    # reference_text_sha256), which is identical across arms; the scorer records it as
    # `corpus_manifest_sha256` beside the per-arm raw `manifest_sha256`. Bind to it when present.
    bind = f.get("corpus_manifest_sha256") if _hex64(f.get("corpus_manifest_sha256")) \
        else f.get("manifest_sha256")
    if _hex64(bind) and ns.text(f.get("corpus_id")) and not (
            _AT_HASH12.match(f["corpus_id"]) and f["corpus_id"].endswith("@" + bind[:12])):
        p.append("fields.corpus_id must be corpus_id@<corpus manifest sha256>[:12]")
    column = f.get("column")
    if column not in STT_COLUMNS:
        p.append(f"fields.column must be one of {sorted(STT_COLUMNS)}")
    elif f.get("candidate") is not (column == "v2_candidate"):
        p.append("fields.candidate must be true exactly when column == 'v2_candidate'")
    if not isinstance(f.get("streaming"), bool):
        p.append("fields.streaming must be a boolean (offline arms never sit in a streaming column)")
    elif f["streaming"]:
        p += _lookahead_problems(f, "fields")
    runner = str(f.get("runner_id") or "")
    if "transcribe.cpp" in runner.lower() and "whisper" in str(h.get("model", "")).lower() \
            and not ns.text(f.get("kv_dtype")):
        p.append("fields.kv_dtype is required on a transcribe.cpp whisper row")
    sec = f.get("secondary_scorer")
    if sec is not None and not (isinstance(sec, dict) and _sha_like(sec.get("sha256"))
                                and isinstance(sec.get("package_versions"), dict)
                                and sec["package_versions"]):
        p.append("fields.secondary_scorer, when used, must carry sha256 and package_versions")
    tax = f.get("taxonomy")
    if tax is not None and not (isinstance(tax, dict)
                                and all(ns.nonneg_int(v) for v in tax.values())):
        p.append("fields.taxonomy must map category -> count (int >= 0)")
    # The two named 1B rules.
    if is_production_runner(runner):
        if not str(f.get("runner_commit", "")).startswith(PRODUCTION_WHISPER_COMMIT_PREFIX):
            p.append(f"runner names {PRODUCTION_SPEECH_TAG} but runner_commit is not "
                     f"{PRODUCTION_WHISPER_COMMIT_PREFIX}…: the parity-gate exemption cannot be "
                     "claimed by a label")
    elif not ns.text(f.get("whisper_parity_gate_ref")):
        p.append(f"REFUSED: runner {runner!r} is not {PRODUCTION_SPEECH_TAG} and the row carries "
                 "no whisper_parity_gate_ref (CS-8.STT3: a runner's whisper numbers are used only "
                 "after it passes the parity gate)")
    return p


def _fitting_problems(row: Mapping[str, Any], f: Mapping[str, Any]) -> list[str]:
    p = [f"fields.{k} must be a non-empty string"
         for k in ("arm", "model_revision", "probe", "panel", "language", "stratum",
                   "paired_wer_measurement_id") if not ns.text(f.get(k))]
    if not _hex64(f.get("predictions_sha256")):
        p.append("fields.predictions_sha256 must be a 64-hex sha256")
    if not _pos_int(f.get("n_eligible")):
        p.append("fields.n_eligible must be an integer >= 1 (an unmeasured language is not written)")
    ar, ci = f.get("accept_ref"), f.get("accept_ref_ci")
    if not _unit_interval(ar):
        p.append("fields.accept_ref must be a number in [0, 1]")
    elif not (isinstance(ci, list) and len(ci) == 2 and all(_unit_interval(x) for x in ci)
              and ci[0] <= ar <= ci[1]):
        p.append("fields.accept_ref_ci must be [lo, hi] in [0, 1] bracketing accept_ref")
    elif row.get("value") != ar:
        p.append("value must equal fields.accept_ref")
    if f.get("gates", False) is not False:
        p.append("fields.gates must be false: the fitting screen reports, never gates")
    if row.get("reps") != f.get("n_eligible"):
        p.append("reps must equal fields.n_eligible")
    return p


def _lexicon_problems(row: Mapping[str, Any], f: Mapping[str, Any]) -> list[str]:
    p: list[str] = []
    if not _hex64(f.get("lexicon_sha256")):
        p.append("fields.lexicon_sha256 must be a 64-hex sha256")
    if not ns.finite(f.get("boost_alpha")):
        p.append("fields.boost_alpha must be a finite number")
    for k in ("list_scope", "case_policy"):
        if not ns.text(f.get(k)):
            p.append(f"fields.{k} must be a non-empty string")
    for k in ("term_recall", "term_precision"):
        if not _unit_interval(f.get(k)):
            p.append(f"fields.{k} must be a number in [0, 1]")
    for k in ("insertions_per_hour", "non_list_word_wer"):
        if not _nonneg(f.get(k)):
            p.append(f"fields.{k} must be a finite number >= 0")
    src = LEXICON_METRIC_FIELD.get(row.get("metric"))
    if src and ns.finite(f.get(src)) and row.get("value") != f[src]:
        p.append(f"value must equal fields.{src} for metric {row.get('metric')!r}")
    return p


def _vad_problems(f: Mapping[str, Any]) -> list[str]:
    p: list[str] = []
    if not _hex64(f.get("weights_sha256")):
        p.append("REFUSED: a VAD tuple without its weights_sha256 (64-hex) -- the arm is the "
                 "weights, and an unpinned VAD number cannot be re-derived")
    for k in ("vad_model", "language", "dataset_revision"):
        if not ns.text(f.get(k)):
            p.append(f"fields.{k} must be a non-empty string")
    if f.get("runtime") not in VAD_RUNTIMES:
        p.append(f"fields.runtime must be one of {sorted(VAD_RUNTIMES)}")
    if not (ns.finite(f.get("hop_ms")) and f["hop_ms"] > 0):
        p.append("fields.hop_ms must be a positive number")
    params = f.get("params")
    if not isinstance(params, dict) or not all(ns.finite(params.get(k)) for k in VAD_PARAMS):
        p.append(f"fields.params must carry the full arm parameter set {list(VAD_PARAMS)}")
    if not _hex64(f.get("corpus_manifest_sha256")):
        p.append("fields.corpus_manifest_sha256 must be a 64-hex sha256")
    if not (ns.text(f.get("confidence_mask")) or (isinstance(f.get("confidence_mask"), dict)
                                                   and f["confidence_mask"])):
        p.append("fields.confidence_mask must be recorded")
    return p


def _eot_problems(f: Mapping[str, Any]) -> list[str]:
    p: list[str] = []
    arm = f.get("turn_arm")
    if arm not in TURN_ARMS:
        p.append(f"fields.turn_arm must be one of {sorted(TURN_ARMS)}")
    if not ns.text(f.get("interim_source")):
        p.append("fields.interim_source must name the STT arm that produced the transcript "
                 "('none' for the silence arm)")
    if arm == "text_llm_prompt" and not _hex64(f.get("prompt_sha256")):
        p.append("fields.prompt_sha256 (64-hex) is required for the text_llm_prompt arm")
    if f.get("prompt_sha256") is not None and not _hex64(f.get("prompt_sha256")):
        p.append("fields.prompt_sha256 must be a 64-hex sha256 when present")
    return p


def _ttf_problems(f: Mapping[str, Any]) -> list[str]:
    p: list[str] = []
    if f.get("method_protocol") != TIME_TO_FINAL_METHOD:
        p.append(f"fields.method_protocol must be {TIME_TO_FINAL_METHOD!r}")
    if not (ns.finite(f.get("chunk_ms")) and f["chunk_ms"] > 0):
        p.append("fields.chunk_ms must be a positive number")
    if not _hex64(f.get("silero_pin_sha256")):
        p.append("fields.silero_pin_sha256 must be a 64-hex sha256")
    for k in ("stt_arm", "device", "language"):
        if not ns.text(f.get(k)):
            p.append(f"fields.{k} must be a non-empty string")
    if not (isinstance(f.get("clip_id"), str) and _AT_HASH12.match(f["clip_id"])):
        p.append("fields.clip_id must be clip_id@manifest_sha256[:12]")
    return p + _lookahead_problems(f, "fields (the STT arm's att_context or delay setting)")


def _interruption_problems(f: Mapping[str, Any]) -> list[str]:
    p: list[str] = []
    if f.get("record_set") not in INTERRUPTION_SETS:
        p.append(f"fields.record_set must be one of {sorted(INTERRUPTION_SETS)}")
    gate = f.get("gate_under_test")
    if not ns.text(gate):
        p.append("fields.gate_under_test must name the gate being measured")
    oracle = f.get("timing_oracle")
    if not isinstance(oracle, dict) or oracle.get("kind") not in TIMING_ORACLES \
            or not ns.text(oracle.get("id")):
        p.append(f"fields.timing_oracle must carry kind in {sorted(TIMING_ORACLES)} and the id "
                 "of the component that produced the timings")
        return p
    if oracle["kind"] == "asr_word_times" and not (
            isinstance(oracle.get("merge_params"), dict) and oracle["merge_params"]):
        p.append("fields.timing_oracle.merge_params are required for asr_word_times")
    if ns.text(gate) and _norm(gate) in {_norm(oracle["id"]), _norm(oracle.get("asr_id"))}:
        p.append(f"REFUSED: the timing oracle {oracle['id']!r} is the gate under test "
                 f"{gate!r} -- circular timing (CS-45.2 (c): user timing from the synthetic "
                 "timeline, system timing from ASR word times, never from the gate under test)")
    return p


def _coresidency_problems(f: Mapping[str, Any]) -> list[str]:
    p: list[str] = []
    legs = f.get("legs")
    ids = ([leg.get("arm_id") for leg in legs if isinstance(leg, dict)]
           if isinstance(legs, list) else [])
    if not (isinstance(legs, list) and len(legs) == 3 and len(ids) == 3
            and all(ns.text(i) for i in ids) and ids[0] == ids[2] and ids[0] != ids[1]):
        p.append("REFUSED: fields.legs must be the three A/B/A legs with their arm ids "
                 "(legs[0].arm_id == legs[2].arm_id != legs[1].arm_id)")
    elif not all(ns.finite(leg.get("neighbour_tok_s")) and leg["neighbour_tok_s"] > 0
                 for leg in legs):
        p.append("fields.legs[*].neighbour_tok_s must be the neighbour's tok/s in each leg")
    if not ns.text(f.get("region_lock_claim_id")):
        p.append("REFUSED: fields.region_lock_claim_id is required -- a contention number without "
                 "the claim it was taken under is not a claim")
    cpus = f.get("cpu_list")
    if not (ns.text(cpus) or (isinstance(cpus, list) and cpus
                              and all(ns.nonneg_int(c) for c in cpus))):
        p.append("fields.cpu_list must be recorded")
    tc = f.get("thread_counts")
    if not isinstance(tc, dict) or not (_pos_int(tc.get("speech")) and _pos_int(tc.get("neighbour"))):
        p.append("fields.thread_counts must carry speech and neighbour (int >= 1)")
    nb = f.get("neighbour")
    if not isinstance(nb, dict) or not ns.text(nb.get("identity")):
        p.append("fields.neighbour.identity must name the neighbour (model, quant, binary)")
    ct = f.get("speech_cpu_time_per_thread_s")
    vals = ct if isinstance(ct, list) else list(ct.values()) if isinstance(ct, dict) else []
    if not vals or not all(_nonneg(v) for v in vals):
        p.append("fields.speech_cpu_time_per_thread_s must be per-thread CPU seconds of the "
                 "speech process")
    return p


def _literature_problems(row: Mapping[str, Any]) -> list[str]:
    f = row.get("fields")
    if not isinstance(f, dict):
        return ["fields must be an object"]
    p: list[str] = []
    if f.get("source_kind") not in LITERATURE_SOURCES:
        p.append(f"fields.source_kind must be one of {sorted(LITERATURE_SOURCES)}")
    for k in ("source_name", "source_url"):
        if not ns.text(f.get(k)):
            p.append(f"fields.{k} must be a non-empty string")
    if not (isinstance(f.get("published_date"), str)
            and re.match(r"^\d{4}-\d{2}-\d{2}$", f["published_date"])):
        p.append("fields.published_date must be YYYY-MM-DD")
    sets = f.get("set_list")
    if not (isinstance(sets, list) and sets and all(ns.text(s) for s in sets)):
        p.append("fields.set_list must name the evaluation sets")
    if "wer" in str(row.get("metric", "")).lower() and not ns.text(f.get("normaliser")):
        p.append("fields.normaliser is required on a literature WER number")
    return p


# --- the row ---------------------------------------------------------------------------------

def _direction_problems(row: Mapping[str, Any], kind: str) -> list[str]:
    metric, direction = row.get("metric"), row.get("metric_direction")
    p: list[str] = []
    allowed = KIND_METRICS.get(kind)
    if allowed is not None and metric not in allowed:
        p.append(f"record_kind {kind!r} admits metrics {sorted(allowed)} (got {metric!r})")
    if direction not in (LOWER, HIGHER):
        p.append("metric_direction must be recorded as higher_better or lower_better")
    elif metric in METRIC_DIRECTIONS and METRIC_DIRECTIONS[metric] != direction:
        p.append(f"metric {metric!r} is {METRIC_DIRECTIONS[metric]} (got {direction!r})")
    native = row.get("metric_direction_native")
    if not ns.text(native):
        p.append("metric_direction_native must keep the producer's own direction word")
    elif kind != "stt_fitting_screen" and NATIVE_DIRECTION_ALIASES.get(native) != direction:
        p.append(f"metric_direction_native {native!r} does not map to {direction!r}")
    return p


def _identity(row: Mapping[str, Any]) -> str:
    kind = row["record_kind"]
    if kind == LITERATURE_KIND:
        return "csmlit_" + ns.content_hash({
            "run_id": row["run_id"], "kind": kind, "subject": row.get("subject"),
            "metric": row["metric"], "fields": row.get("fields")})[:24]
    return "csm_" + ns.content_hash({
        "run_id": row["run_id"], "kind": kind, "subject": row.get("subject"),
        "metric": row["metric"], "results": row.get("results_sha256"),
        "harness": row.get("harness"), "fields": row.get("fields")})[:24]


_KIND_CHECKS = {
    "vad_arm": lambda row, f, h: _vad_problems(f),
    "end_of_turn": lambda row, f, h: _eot_problems(f),
    "time_to_final": lambda row, f, h: _ttf_problems(f),
    "interruption": lambda row, f, h: _interruption_problems(f),
    "coresidency_degraded": lambda row, f, h: _coresidency_problems(f),
    "stt_arm_wer": lambda row, f, h: _stt_arm_problems(f, h),
    "stt_lexicon_trial": lambda row, f, h: _stt_arm_problems(f, h) + _lexicon_problems(row, f),
    "stt_fitting_screen": lambda row, f, h: _fitting_problems(row, f),
    "generic": lambda row, f, h: [],
}


def validate_row(row: Any) -> list[str]:
    """Every problem with one row. Empty means the row is a well-formed producer capture."""
    if not isinstance(row, dict):
        return ["row is not a JSON object"]
    p: list[str] = []
    if row.get("schema") != SCHEMA:
        p.append(f"schema must be {SCHEMA!r}")
    kind = row.get("record_kind")
    if kind not in RECORD_KINDS:
        return p + [f"record_kind must be one of {sorted(RECORD_KINDS)}"]
    for key in ("run_id", "producer", "measurement_id", "metric", "unit", "claim", "subject"):
        if not ns.text(row.get(key)):
            p.append(f"{key} must be a non-empty string")
    if not ns.utc_timestamp(row.get("emitted_at")):
        p.append("emitted_at must be a UTC timestamp")
    if not ns.finite(row.get("value")):
        p.append("value must be a finite number")
    p += _direction_problems(row, kind)
    if kind == LITERATURE_KIND:
        if row.get("source_class") != "literature":
            p.append("a literature_reference row must say source_class='literature'")
        p += _literature_problems(row)
    else:
        if row.get("source_class", "measurement") != "measurement":
            p.append("a measured row is source_class='measurement'")
        if not ns.text(row.get("date")) or not ns.text(row.get("results_path")):
            p.append("date and results_path must be non-empty strings")
        if not _hex64(row.get("results_sha256")):
            p.append("results_sha256 must be a 64-hex digest over the attested file")
        if row.get("category") not in ns.CATEGORIES:
            p.append("category must be exactly one of OPTIMUM/BASELINE/CANDIDATE")
        pid = row.get("protocol_id")
        if pid is not None and not ns.text(pid):
            p.append("protocol_id must be null or a non-empty string")
        if not _pos_int(row.get("reps")):
            p.append("reps must be an integer >= 1")
        if not (ns.text(row.get("reps_basis"))
                and row["reps_basis"].startswith(("scored:", "attempted:"))):
            p.append("reps_basis must say whether n was scored:… or attempted:…")
        h, f = row.get("harness"), row.get("fields")
        p += _harness_problems(h)
        if not isinstance(f, dict):
            p.append("fields must be an object")
        else:
            p += _KIND_CHECKS[kind](row, f, h if isinstance(h, dict) else {})
            if kind in STT_KINDS and row.get("reps") != f.get("n"):
                p.append("reps must equal fields.n (scored utterances)")
            if isinstance(h, dict) and isinstance(h.get("runtime"), dict) \
                    and h["runtime"].get("kind") == "reference" \
                    and REFERENCE_MARKER not in str(row.get("claim", "")):
                p.append(f"a reference-harness row's claim must say {REFERENCE_MARKER!r}")
            if is_confirmation_stratum(f.get("stratum")):
                leaks = _per_utterance_paths({"fields": f, "harness": h})
                if leaks:
                    p.append("REFUSED: a confirmation-stratum tuple carries per-utterance values "
                             f"({', '.join(leaks)}); the loop sees aggregates only (CS-8.STT6)")
    if not p and row.get("measurement_id") != _identity(row):
        p.append("measurement_id does not re-derive from its identity parts")
    return p + ns.self_hash_problems(row)


# --- write side --------------------------------------------------------------------------------

def stt_record_from_scorer(scorer: Mapping[str, Any], *, harness: Mapping[str, Any],
                           category: str = "CANDIDATE",
                           subject: str | None = None) -> dict[str, Any]:
    """Map one CS-8 ``scripts/speech/stt_bakeoff`` scorer record (flat names, arm descriptor nested
    under ``arm`` or flat) into an ``stt_arm_wer`` record for :func:`write_belief_measurements`.

    Pure renaming: nothing is invented. ``harness`` is required because the scorer does not sample
    co-tenant state or placement; a missing scorer field stays missing and the writer refuses it.
    """
    rec = dict(scorer)
    arm = rec.pop("arm", None)
    if isinstance(arm, dict):
        for key, value in arm.items():
            rec.setdefault(key, value)
    norm = rec.pop("normaliser", None)
    if isinstance(norm, dict):
        rec.setdefault("normaliser_id", norm.get("id"))
        rec.setdefault("normaliser_sha256", norm.get("sha256"))
    ref = rec.pop("reference_set", None)
    if isinstance(ref, dict):
        rec.setdefault("reference_set_id", ref.get("id"))
        rec.setdefault("reference_set_track", ref.get("track"))
    value = next((rec.pop(k) for k in ("value", "wer_pct", "wer") if k in rec), None)
    metric = rec.pop("metric", None)
    native_dir = rec.pop("metric_direction", None)
    unit = rec.pop("unit", "wer_pct")
    protocol = rec.pop("protocol_id", None)
    if "schema_version" in rec:
        rec["native_schema_version"] = rec.pop("schema_version")
    # Scorer vocabulary -> this writer's: `reference_track` is the reference-set track, and the
    # scorer's `corpus_key` (corpus_id@corpus_manifest_sha256[:12]) is what this writer calls
    # `corpus_id`; the bare scorer corpus name is kept beside it, never lost.
    if "reference_track" in rec:
        rec.setdefault("reference_set_track", rec.pop("reference_track"))
    if "corpus_key" in rec:
        rec["corpus_name"] = rec.get("corpus_id")
        rec["corpus_id"] = rec.pop("corpus_key")
    rec.setdefault("streaming", False)
    return {"record_kind": "stt_arm_wer", "metric": metric, "value": value, "unit": unit,
            "metric_direction": native_dir, "category": category, "protocol_id": protocol,
            "subject": subject or f"{rec.get('runner_id')}:{rec.get('arm_id', harness.get('model'))}"
                                  f":{rec.get('language')}:{rec.get('stratum')}:{rec.get('column')}",
            "harness": dict(harness), "fields": rec}


def _claim_text(rec: Mapping[str, Any], direction: str) -> str:
    h = rec["harness"] if isinstance(rec.get("harness"), dict) else {}
    rt = h.get("runtime") if isinstance(h.get("runtime"), dict) else {}
    ct = h.get("co_tenant") if isinstance(h.get("co_tenant"), dict) else {}
    tenant = (f"co-tenant {ct.get('llm')} on {ct.get('device')} np={ct.get('np')} "
              f"generating={ct.get('generating')}" if ct.get("present") else "no co-tenant")
    text = (f"conversation-stack {rec['record_kind']} {rec['metric']}={rec['value']:.6g} "
            f"{rec.get('unit')} ({direction}) for {rec.get('subject')} "
            f"[{h.get('model')} {h.get('quant')}, {rt.get('kind')} runtime, device "
            f"{h.get('device')}, lane {h.get('host_lane')}, {tenant}]")
    if rt.get("kind") == "reference":
        text += f" -- {REFERENCE_MARKER}"
    return text


def build_row(rec: Mapping[str, Any], *, run_id: str, producer: str, emitted_at: str,
              results_path: str | None = None, results_sha256: str | None = None) -> dict:
    """One sealed row from one record. Raises CaptureError (with every problem) if it is invalid."""
    kind = rec.get("record_kind")
    if kind not in RECORD_KINDS:
        raise CaptureError(f"unknown record_kind {kind!r}")
    native_dir = rec.get("metric_direction_native", rec.get("metric_direction"))
    if kind == "stt_fitting_screen":
        direction = LOWER
    else:
        direction = NATIVE_DIRECTION_ALIASES.get(str(native_dir)) if native_dir else \
            METRIC_DIRECTIONS.get(str(rec.get("metric")))
    row: dict[str, Any] = {
        "schema": SCHEMA, "run_id": run_id, "producer": producer, "emitted_at": emitted_at,
        "record_kind": kind, "subject": rec.get("subject"), "metric": rec.get("metric"),
        "value": rec.get("value"), "unit": rec.get("unit"), "metric_direction": direction,
        "metric_direction_native": native_dir or direction, "fields": dict(rec.get("fields") or {}),
    }
    if not ns.finite(row["value"]):
        raise CaptureError(f"{kind}: value must be a finite number")
    if kind == LITERATURE_KIND:
        row["source_class"] = "literature"
        row["claim"] = rec.get("claim") or (
            f"LITERATURE ({row['fields'].get('source_kind')}: {row['fields'].get('source_name')}, "
            f"{row['fields'].get('published_date')}) reports {row['metric']}={row['value']:.6g} "
            f"{row['unit']} for {row['subject']} -- not our measurement")
    else:
        f = row["fields"]
        reps = rec.get("reps") or (f.get("n_eligible") if kind == "stt_fitting_screen"
                                   else f.get("n"))
        basis = rec.get("reps_basis") or ("scored:eligible_items" if kind == "stt_fitting_screen"
                                          else "scored:utterances" if kind in STT_KINDS
                                          else "scored:events")
        category = rec.get("category") or ("BASELINE" if rec.get("is_control") else "CANDIDATE")
        row.update(date=emitted_at[:10], category=category, protocol_id=rec.get("protocol_id"),
                   reps=reps, reps_basis=basis, results_path=results_path,
                   results_sha256=results_sha256, harness=dict(rec.get("harness") or {}))
        row["claim"] = _claim_text(row, direction or "?") if ns.finite(row["value"]) else ""
    try:
        row["measurement_id"] = _identity(row)
    except CaptureError as exc:
        raise CaptureError(f"{kind}: {exc}") from exc
    ns.seal(row)
    problems = validate_row(row)
    if problems:
        raise CaptureError(f"{kind}: refusing to emit an invalid row: " + "; ".join(problems))
    return row


def _same_write_problems(rows: list[dict]) -> list[str]:
    """The 1B same-write rule: a fitting-screen row names a WER row of the same arm in this file."""
    wer = {r["measurement_id"]: r for r in rows if r.get("record_kind") == "stt_arm_wer"}
    p = []
    for r in rows:
        if r.get("record_kind") != "stt_fitting_screen":
            continue
        paired = wer.get(r["fields"].get("paired_wer_measurement_id"))
        arm = r["fields"].get("arm")
        if paired is None:
            p.append(f"fitting-screen row {r['measurement_id']} names no stt_arm_wer row in the "
                     "same write")
        elif arm not in {paired["fields"].get("arm_id"), paired["harness"].get("model")} \
                and str(arm) not in paired["subject"]:
            p.append(f"fitting-screen row {r['measurement_id']} pairs a WER row of another arm")
    return p


def write_belief_measurements(
    out_dir: str | Path, *, run_id: str, producer: str, results_path: str | Path,
    records: list[Mapping[str, Any]], emitted_at: str | None = None,
) -> Path:
    """Write ``<out_dir>/conversation_stack.beliefs.jsonl`` atomically. Raises CaptureError.

    ``records``: each ``{record_kind, subject, metric, value, unit, metric_direction (the producer's
    word), category | is_control, protocol_id?, reps?, reps_basis?, harness, fields}``. A fitting
    screen row is linked to its WER row by ``fields.paired_wer_measurement_id``; pass
    ``"@<index>"`` (the index of the WER record in ``records``) and the writer resolves it, which is
    what makes the two one write.
    """
    results = Path(results_path)
    if not results.is_file():
        raise CaptureError(f"results artifact missing: {results}")
    if not records:
        raise CaptureError("at least one record is required")
    digest = ns.file_sha256(results)
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows: list[dict] = []
    for rec in records:
        rec = dict(rec)
        fields = dict(rec.get("fields") or {})
        ref = fields.get("paired_wer_measurement_id")
        if isinstance(ref, str) and ref.startswith("@"):
            try:
                fields["paired_wer_measurement_id"] = rows[int(ref[1:])]["measurement_id"]
            except (ValueError, IndexError) as exc:
                raise CaptureError(f"unresolvable paired_wer_measurement_id {ref!r}") from exc
        rec["fields"] = fields
        rows.append(build_row(rec, run_id=run_id, producer=producer, emitted_at=when,
                              results_path=str(results), results_sha256=digest))
    problems = _same_write_problems(rows)
    if problems:
        raise CaptureError("; ".join(problems))
    if len({r["measurement_id"] for r in rows}) != len(rows):
        raise CaptureError("duplicate measurement identity in one write")
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


# --- read side ---------------------------------------------------------------------------------

def _load(sidecar_path: str | Path) -> list[dict] | None:
    path = Path(sidecar_path)
    if not path.is_file():
        return None
    rows = ns.load_rows(path, validate_row)
    if not rows or _same_write_problems(rows):
        return None
    return rows


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    """Measured rows only. An invalid row voids the WHOLE file (the writer is atomic); literature
    rows are never returned here -- see :func:`literature_rows`."""
    rows = _load(sidecar_path)
    if not rows:
        return ()
    return tuple({"row": r, "sidecar_path": str(sidecar_path),
                  "attestation_present": ns.results_present(r)}
                 for r in rows if r["record_kind"] != LITERATURE_KIND)


def literature_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    """Vendor/card/leaderboard/hosted-board and published reference rows, for the research-intake
    (``literature``-class) lane. Never projected here as measurements."""
    rows = _load(sidecar_path)
    return tuple(r for r in rows or () if r["record_kind"] == LITERATURE_KIND)


def rows_for_run(run_dir: str | Path) -> tuple[dict, ...]:
    return native_rows(Path(run_dir) / SIDECAR_NAME)


def _projected_protocol(row: Mapping[str, Any]) -> tuple[str, str]:
    """(protocol_id carried into the tuple, status). Never upgrades; a non-admissible citation is
    kept verbatim in ``extra`` and the tuple is the observation it is."""
    native = row.get("protocol_id")
    if not native:
        return "", "none_cited"
    kind, f = row["record_kind"], row.get("fields") or {}
    if f.get("candidate") is True or f.get("column") == "v2_candidate":
        return "", "v2_candidate_column_unratified"
    if native in ADMISSIBLE_PROTOCOLS.get(kind, frozenset()):
        return native, "admissible"
    return "", "not_admissible_for_kind_until_cs2_annex_s"


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    """Projection only: one producer row -> one ClaimTuple. ``claim_tuple.grade()`` decides."""
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("conversation-stack native row must retain the producer row")
    row = native["row"]
    if row.get("record_kind") == LITERATURE_KIND:
        raise ProjectionError(
            "conversation-stack literature_reference row refused as a measurement: vendor, card, "
            "leaderboard, hosted-board and published reference numbers enter only as "
            "literature-class claims (research intake), never graded as our measurements")
    problems = validate_row(row)
    if problems:
        raise ProjectionError("conversation-stack row is not a producer-authored capture: "
                              + "; ".join(problems))
    h, f = row["harness"], row["fields"]
    protocol_id, protocol_status = _projected_protocol(row)
    present = ns.results_present(row)
    applicability = {"quant": h["quant"], "device": h["device"], "scope_basis": "native"}
    if row["record_kind"] in STT_KINDS:
        applicability["backend"] = f["backend"]
    model_sha = f.get("weights_sha256")
    if _hex64(model_sha):
        applicability["model_sha256"] = model_sha
    cautions = ["metric_direction is per metric (mixed family)",
                "co-tenant state and device/host-lane placement are part of the measurand"]
    if h["llm_judged"]:
        cautions.append("LLM-judged score: SC58 judgment-frame rules apply (judge pinned)")
    if h["runtime"]["kind"] == "reference":
        cautions.append("reference-harness number: measurement only, never a serving claim for "
                        "the llama.cpp port")
    if row["metric"] in HIGHER_IS_CORRECT_METRICS:
        cautions.append("higher-is-correct t_stop mapped to higher_better")
    locator = (f"conversation-stack:{row['run_id']}:{row['record_kind']}:{row['subject']}:"
               f"{row['results_path']}")
    return ClaimTuple(
        measurement_id=row["measurement_id"], metric=row["metric"], value=row["value"],
        date=row["date"], category=row["category"], claim=row["claim"],
        metric_direction=row["metric_direction"], protocol_id=protocol_id, reps=row["reps"],
        reps_basis=row["reps_basis"], unit=row["unit"],
        attestation_sha256=row["results_sha256"], attestation_locator=locator,
        attestation_present=present,
        # `present` IS the write-boundary verification: the file was re-read and re-hashed.
        attestation_verified=True if present else None,
        source_kind=SOURCE_KIND, applicability=applicability,
        extra={"schema": row["schema"], "record_kind": row["record_kind"],
               "producer": row["producer"], "emitted_at": row["emitted_at"],
               "run_id": row["run_id"], "row_sha256": row["row_sha256"],
               "sidecar_path": native.get("sidecar_path", ""),
               "metric_direction_native": row["metric_direction_native"],
               "protocol_id_native": row.get("protocol_id"), "protocol_status": protocol_status,
               "serving_claim": False, "cautions": cautions, "harness": h, "fields": f},
    )


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "SCHEMA", "SIDECAR_NAME", "SOURCE_KIND", "build_row", "frames_for_sidecar",
           "literature_rows", "native_rows", "project", "rows_for_run", "stt_record_from_scorer",
           "validate_row", "write_belief_measurements"]
