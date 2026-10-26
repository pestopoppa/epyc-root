"""VB-KVU-PF / VB-KVU-PF.1 read side: project KPF-18 ``epyc.kpf.run.v1`` records into ClaimTuples.

Source class ``measurement``; one ladder (``claim_tuple.grade()``), no private rule. The only admissible
input is a runner-authored ``belief_measurements.jsonl`` line (``kpf18_gate.py`` ``Run.finish``). A line is
refused when its schema is wrong, its ``record_sha256`` does not re-derive, or a required field is absent;
an invalid line voids the WHOLE file (the writer appends complete records; partial validity is corruption).
Pre-extension records (no ``kpf_ext``) still project; the VB-KVU-PF.1 fields are then simply absent, never filled.

VB-KVU-PF.2 (KPF-18.1/.2/.3 arms and the S1 composite). ``arm`` is either a fork-vocabulary arm (``ARMS``) or one of
the DECLARED KPF-18 sub-arms (``KPF18_SUB_ARMS``, the names ``kpf18_arms.py`` ``open_run`` writes, keyed by
``kpf18_item``); a sub-arm record must also carry ``kpf18_arm == arm`` (the runner writes both), and that name is
the locator's arm token. Anything else is refused. A record with no ``rows_sha256`` (the runner wrote no
per-request rows file -- e.g. S1's ``parity_summary``, which issues no request) is ATTESTED-ABSENT: it projects with
an empty ``attestation_sha256`` and ``attestation_present=False``, and the shared ladder grades the absence. No
digest is computed on read for it: a hash taken now would claim a warrant the run never recorded.

Locator: run x arm x dflash2 x prompt-set sha256 x binary sha256 x window id. Item 1's DFlash2-off record shares
window and binary with its DFlash2-on record, so ``dflash2`` is part of the locator and the arm is
``fork_on_dflash2_off`` (VB-KVU-PF.1 fix; the runner used to label it ``fork_on``).

Attestation is the per-request rows JSONL the runner hashed (``rows`` / ``rows_sha256``); it is re-hashed on read,
so a moved or mutated rows file grades DOWN through the shared ladder rather than being skipped.
Equivalence is carried as COUNTS (top-1 agreement, max-abs logit/KLD, identical greedy prefix) against the
fresh-vs-fresh control floor, never as a pass word.

Loop-belief redesign P1-K (DESIGN 12.2). Two additions, both projection only (``claim_tuple.grade()`` decides):

* SCOPE. Every claim carries ``applicability`` read from the record's OWN argv and readback: ``model_file`` (``-m``),
  ``quant`` (the GGUF basename's trailing quant token), ``backend`` (``--device none`` -> cpu, ``ROCmN`` -> gpu),
  ``np``, ``kernel`` (binary realpath + its sha256) and ``build_sha`` (only when the build dir name carries it),
  ``knob_family = "slot_serving"`` (a stack-topology knob, not AutoPilot's action space), ``knobs`` (the flag set held
  FIXED: np, -b/-ub, KV types, kv-unified, flash-attn, spec type, ...) and ``varied`` (the knob the arms change).
  ``device`` is NOT declared: the argv names ``ROCm0``, not the card, and a guessed card would mis-scope the claim.
* VALUE. A ``fork_on`` record that has a paired ``fork_off`` record in the SAME sidecar (window ids ``...-A<k>`` /
  ``...-B<k>``, same binary, prompt set, model and np) also projects one claim per serving measure -- fan-out TTFT
  (median of the children's first-token latency), prompt tokens processed, aggregate decode -- each carrying the
  ``fork_off`` value as ``observation.anchor_value`` and ``effect_rel`` against it. No verdict word and no noise
  floor: the record has neither, and n is one A/B window pair.
"""
from __future__ import annotations

import hashlib
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters._argv_scope import flag as _flag, scope_from_argv  # noqa: E402
from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

SCHEMA = "epyc.kpf.run.v1"
SIDECAR_NAME = "belief_measurements.jsonl"
ADAPTER_ID = "vidya.adapters.kv_prefix_fork/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "kv-prefix-fork-measurement"
ARMS = frozenset({"fork_off", "fork_on", "fork_on_dflash2_off", "champion"})
KNOB_FAMILY = "slot_serving"
# Per-arm knob the arm changes against its comparison arm (DESIGN 12.2 `varied`).
VARIED_BY_ARM = {"fork_off": ["slot_fork"], "fork_on": ["slot_fork"], "fork_on_dflash2_off": ["dflash2"],
                 "champion": ["binary"]}
#: VB-KVU-PF.2: the declared KPF-18 sub-arm set, per ``kpf18_item`` (research
#: ``scripts/benchmark/kpf18/kpf18_arms.py`` ``open_run`` call sites; ``<cfg>`` is the config name the runner derives
#: from the launched argv -- ``mtp``, ``dflash2``, ``nodraft``, ``draft-<x>`` -- or a ``--kpf-config-argv NAME``).
_CFG = r"[A-Za-z0-9][A-Za-z0-9_.-]*"
KPF18_SUB_ARMS = {
    # 3 = KPF-18.0d(item 3, group 3) v2 same-shape control (launcher ``item3v2.py``, one record per fresh load N). Its
    # verdict inputs ride in the record's own top-level ``item3v2`` block (per-load judged classes), not in
    # ``equivalence`` (vs_fresh n = 0); see ``_project_item3v2``.
    3: (r"item3v2_load\d+",),
    181: (r"A_(?:ckpt|tailonly)(?:_forkoff)?", r"B_identical_resend_and_child_eq_trunk(?:_forkoff)?",
          r"C_length_sweep_drafter_(?:on|off)", rf"D_hit_count_prediction_{_CFG}"),
    182: (r"cold_control_probe", rf"parity_{_CFG}_(?:drafter_on|request_off|launch)", rf"policy_control_{_CFG}",
          r"parity_summary"),
    183: (r"chunk_split_cost", r"end_ckpt_position_and_multi_turn", r"request_lane", r"warm_vs_cold_long_prompt"),
    184: (r"item3_localisation",),
    # 185 = KPF-18-S1 remainder (research kpf18 S1R driver): tail-only tail sweep, item-2 pcache grid g<G>s<S>, the
    # long teacher-forced cell, KPF-19.1a flag-off geometry groups, and the step-7 hsf_L<L> length ladder.
    # NB hsf_* records are DECLARED (they validate, so they never void a file) but PROJECT NOTHING (VB-KVU-PF.6): their
    # only projectable number would be a hit count of 0 (the step issues no fork), and their real content -- the
    # save/restore per-cell medians in ``s1r.result`` -- carries no graphs state of its own. The graphs state differs
    # per run (S1R base: graphs disabled in launch_prefix; step-7 rerun: graphs ON, proven only by the launcher's
    # separate graphs_proof.json), so a rate projected from the record alone could not say which it is.
    185: (r"A_tailonly_tail\d+", r"item2_pcache_g\d+s\d+", r"long_teacher_forced", r"kpf191a_flagoff_g\d+",
          r"hsf_L\d+"),
    # 186 = KPF-18-S1.R3 (research ``kpf18_r3.py``, command kpf18r3): step ``long6`` (18.3 part 4, six-pair cold
    # floor, teacher-forced) and step ``item2q`` (item-2 cell g<G>.s<S> with >= 3 Q repeats). Verdict inputs ride in
    # the record's own top-level ``r3`` block (``r3.result``), not in ``equivalence``; see ``_project_r3`` (VB-KVU-PF.7).
    186: (r"long6_teacher_forced", r"item2q_g\d+s\d+"),
    # 187 = KPF-18-S1.R4, occupancy-matched teacher-forced fork localisation.
    # Its own r4.result scores the deviation; the generic hit-token metric does not.
    187: (r"r4_teacher_forced",),
}
_SUB_ARM_RE = {item: re.compile("^(?:" + "|".join(pats) + ")$") for item, pats in KPF18_SUB_ARMS.items()}
#: sub-arms that validate but project nothing (see the 185 note above).
_DECLINED_SUB_ARM = re.compile(r"^hsf_L\d+$")
#: VB-KVU-PF.6: KPF-18 item-3 v2 load records. The launcher wrote no ``kpf18_arm``; the arm token is still sealed by
#: ``record_sha256``, and a complete record's own ``item3v2.load`` must name the same load (a partial, budget-aborted
#: record carries ``partial: true`` and no ``item3v2`` block).
_ITEM3V2 = re.compile(r"^item3v2_load(?P<load>\d+)$")
#: VB-KVU-PF.7: KPF-18-S1.R3 (item 186) arm -> the ``r3.step_id`` its record must name (``kpf18_r3.py`` ``_step_open``).
#: The writer opens the record with ``step_complete: false`` and adds ``result`` only when the step finishes, so a
#: record without ``step_complete: true`` is an incomplete attempt.
_R3_STEP = {"long6": re.compile(r"^long6_teacher_forced$"), "item2q": re.compile(r"^item2q_g\d+s\d+$")}


#: Conformance records (no fork-vs-fresh logits): ``kpf_task`` -> declared arms, exactly as the drivers emit them
#: (research ``kpf13_restore_ab.py`` writes ``restore_<config>``; ``kpf174_swa_drafter.py`` writes the four launch arms,
#: one per launch: honest, flag_on, and the two mutants; 17.4b adds the rules-v2 spec-off C1 and junction-sweep
#: launches; ``kpf174c_bisect.py`` writes the one KPF-17.4c spec-off bisect launch). Counts come from the record's own
#: verdict block (kpf13: ``equivalence.configs`` A+B; kpf174 / kpf174c: ``launch_verdict``), never a pass word and never
#: invented.
CONFORMANCE_ARMS = {
    "KPF-13.1": (rf"restore_{_CFG}",),
    "KPF-17.4+17.4a+19.1a": (r"kpf174_191a_flag_off", r"kpf174_mut_dft_partial_noop", r"kpf191a_flag_on",
                             r"kpf191a_mut_dft_no_transfer",
                             # 17.4b (rules v2): C1 honest launch with the drafter flags removed, and the junction
                             # sweep. Both are honest launches (not mutants): they project the PASS fraction.
                             r"kpf174b_c1_spec_off", r"kpf174b_junction_sweep"),
    # VB-KPF174C-ARM: the KPF-17.4c target-restore bisect (rules epyc.kpf174c.rules.v1, speculation OFF). Its
    # launch_verdict counts layout-matched PAIRS (Xc~Cmask, Xe~C0, Ks~C0 of each attempted cell), not cells.
    "KPF-17.4c": (r"kpf174c_bisect_spec_off",),
}
#: tasks whose launch_verdict counts something other than cells: task -> (metric, reps basis, unit noun)
CONF_PAIR_TASKS = {"KPF-17.4c": ("kpf174c_matched_pair_identical_fraction",
                                 "layout-matched pairs (Xc~Cmask, Xe~C0, Ks~C0) attempted in this launch",
                                 "layout-matched pairs bit-identical")}
_CONF_RE = {t: re.compile("^(?:" + "|".join(p) + ")$") for t, p in CONFORMANCE_ARMS.items()}
_MUTANT_ARMS = frozenset({"kpf174_mut_dft_partial_noop", "kpf191a_mut_dft_no_transfer"})


def is_conformance(row: Any) -> bool:
    """True iff the record is a declared conformance arm of its own ``kpf_task``."""
    if not isinstance(row, dict):
        return False
    rx = _CONF_RE.get(row.get("kpf_task")) if isinstance(row.get("kpf_task"), str) else None
    return bool(rx and isinstance(row.get("arm"), str) and rx.match(row["arm"]))


def _conf_counts(row: dict) -> dict | None:
    """The record's own pass/fail/attempts counts, or None when it ran zero cells (aborted launch)."""
    if row.get("kpf_task") == "KPF-13.1":
        cfgs = (row.get("equivalence") or {}).get("configs") or {}
        cells = [cfgs.get(k) for k in ("A", "B")]
        if not all(isinstance(c, dict) for c in cells):
            return None
        return {"attempts": sum(c["attempts"] for c in cells), "pass": sum(c["pass"] for c in cells),
                "fail": sum(c["fail"] for c in cells), "invalid": sum(c.get("invalid") or 0 for c in cells),
                "per_config": {k: {x: c.get(x) for x in ("verdict", "attempts", "pass", "fail", "invalid")}
                               for k, c in zip("AB", cells)}}
    v = row.get("launch_verdict")
    if not isinstance(v, dict):
        return None
    out = {"attempts": v["attempts"], "pass": v["pass"], "fail": v["fail"], "invalid": v.get("invalid") or 0,
           "out_of_scope": v.get("out_of_scope") or 0, "verdict": v.get("verdict")}
    # kpf174c: the unit and the attempt bookkeeping the writer states about its own counts, verbatim
    out.update({k: v[k] for k in ("unit", "pairs_planned", "cells_attempted", "cells_interrupted") if k in v})
    return out


def is_sub_arm(arm: Any, item: Any) -> bool:
    """True iff ``arm`` is a declared KPF-18 sub-arm of ``item`` (parity_summary is not a parity column)."""
    rx = _SUB_ARM_RE.get(item) if type(item) is int else None
    return bool(rx and isinstance(arm, str) and rx.match(arm))


#: KPF-26.1f: the task-outcome record (one per window). Its ``arm`` is this token, it carries ``kpf_outcome`` instead of
#: ``equivalence``, and its attestation is the window's ``cases.jsonl`` (every case, transport errors counted as fails).
OUTCOME_ARM = "kpf261_outcome"
OUTCOME_ARMS = ("A", "B", "A2")  # A = flags off (baseline), B = flags on (treatment), A2 = flags-off rerun (spread)
OUTCOME_KEYS = ("kpf_item", "seed", "manifest_digest", "manifest_sha256", "n_tasks", "n_cases", "reps", "per_arm",
                "spread", "drop", "regress", "improve", "ctrl_regress", "ctrl_improve", "sign_test_p_regress",
                "verdict", "reorder_decision", "gates", "rule", "treatment_applied", "finished_utc")
CONF_VARIED = {"KPF-13.1": ["restore_path"], "KPF-17.4+17.4a+19.1a": ["swa_drafter_launch_arm"],
               "KPF-17.4c": ["restore_path", "kv_layout"]}
_WINDOW = re.compile(r"^(?P<stem>.+)-(?P<arm>[AB])(?P<k>\d+)$")
REQUIRED = ("run_id", "arm", "binary_sha256", "prompt_set_sha256", "window_id", "end_utc", "host", "argv",
            "equivalence", "rows", "record_sha256", "category")  # rows_sha256 absent = attested-absent (VB-KVU-PF.2)
EXT_KEYS = ("checkpoint_set", "hit_components", "hit_length_min", "hit_tokens", "tokens_lost_to_missing_checkpoint",
            "drafter_drop_kind", "request_lane", "cache_skip_control", "pinned_count")


def _digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _validate_outcome(row: dict) -> list[str]:
    out = row.get("kpf_outcome")
    if not isinstance(out, dict):
        return ["outcome record without kpf_outcome"]
    problems = [f"kpf_outcome missing {k}" for k in OUTCOME_KEYS if out.get(k) is None or out.get(k) == ""]
    per_arm = out.get("per_arm")
    if not (isinstance(per_arm, dict) and set(per_arm) == set(OUTCOME_ARMS)):
        problems.append(f"kpf_outcome.per_arm must hold exactly {list(OUTCOME_ARMS)} pass counts")
    else:
        for name, cell in per_arm.items():
            n, ok = (cell or {}).get("n"), (cell or {}).get("pass")
            if not (type(n) is int and type(ok) is int and 0 <= ok <= n and n == out.get("n_cases")):
                problems.append(f"kpf_outcome.per_arm.{name} is not pass/n over n_cases")
    if not row.get("rows_sha256"):
        problems.append("outcome record without rows_sha256: the cases file is its only attestation")
    return problems


def _validate_item3v2(row: dict) -> list[str]:
    """The item-3 v2 locator, absent ``kpf18_arm``: the record's own load block (or its partial flag) must agree."""
    load = int(_ITEM3V2.match(row["arm"])["load"])
    block = row.get("item3v2")
    if block is None:
        return [] if row.get("partial") is True else [
            "item3v2 record with neither an item3v2 block nor partial=true: nothing locates or scores it"]
    if not isinstance(block, dict) or block.get("load") != load:
        return [f"item3v2 block does not name load {load} (got {(block or {}).get('load')!r})"]
    judged = block.get("judged")
    if not (isinstance(judged, dict) and judged and all(
            isinstance(c, dict) and isinstance(c.get("class"), str) for c in judged.values())):
        return ["item3v2 block without per-pair judged classes of its own"]
    if not isinstance(block.get("valid"), bool) or not isinstance(block.get("invalid_reasons"), list):
        return ["item3v2 block without its own valid flag and invalid_reasons list"]
    return []


def _validate_r3(row: dict) -> list[str]:
    """The KPF-18-S1.R3 locator: the record's own ``r3`` block must name the step its arm belongs to."""
    block = row.get("r3")
    if not isinstance(block, dict):
        return ["item-186 (KPF-18-S1.R3) record without its own r3 block: nothing locates or scores it"]
    step = block.get("step_id")
    rx = _R3_STEP.get(step) if isinstance(step, str) else None
    if not (rx and rx.match(row["arm"])):
        return [f"r3 block step_id {step!r} is not the step of arm {row['arm']!r}"]
    if not (isinstance(block.get("predeclaration_sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", block["predeclaration_sha256"])):
        return ["r3 block without its own predeclaration_sha256"]
    if not isinstance(block.get("step_complete"), bool):
        return ["r3 block without its own step_complete flag"]
    if block["step_complete"] and not isinstance(block.get("result"), dict):
        return ["r3 block says step_complete but carries no result of its own"]
    return []


def _validate_r4(row: dict) -> list[str]:
    """R4's declared locator and native result envelope; never weaken the record seal."""
    block = row.get("r4")
    if not isinstance(block, dict):
        return ["item-187 record without its own r4 block"]
    if block.get("step_id") != "r4" or block.get("step") != "r4":
        return ["r4 block does not name step r4"]
    if not isinstance(block.get("predeclaration_sha256"), str) or not re.fullmatch(
            r"[0-9a-f]{64}", block["predeclaration_sha256"]):
        return ["r4 block without its own predeclaration_sha256"]
    if not isinstance(block.get("step_complete"), bool):
        return ["r4 block without its own step_complete flag"]
    if block["step_complete"] and not isinstance(block.get("result"), dict):
        return ["r4 block says step_complete but carries no result of its own"]
    return []


def _intkeys(obj: Any) -> Any:
    """Diagnostic only: ``obj`` with digit-string dict keys turned back into ints (never used to ACCEPT a row)."""
    if isinstance(obj, dict):
        return {(int(k) if isinstance(k, str) and k.isdigit() else k): _intkeys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_intkeys(v) for v in obj]
    return obj


def validate_row(row: Any) -> list[str]:
    if not isinstance(row, dict):
        return ["row is not an object"]
    problems = []
    if row.get("schema") != SCHEMA:
        problems.append(f"schema is not {SCHEMA}")
    outcome = row.get("arm") == OUTCOME_ARM
    conformance = is_conformance(row)
    for key in REQUIRED:
        if (outcome or conformance) and key == "equivalence":
            continue  # an outcome record scores task pass/fail, not fork-vs-fresh logits
        if row.get(key) in (None, "", [], {}):
            problems.append(f"missing {key}")
    arm = row.get("arm")
    if outcome:
        problems.extend(_validate_outcome(row))
    elif conformance:
        n_cells = row.get("n_cells")
        if type(n_cells) is not int or n_cells < 0:
            problems.append("conformance record without an integer n_cells")
        elif n_cells > 0:
            try:
                counts = _conf_counts(row)
                ok = counts is not None and counts["attempts"] > 0 and counts["pass"] + counts["fail"] \
                    + counts["invalid"] <= counts["attempts"]
            except (KeyError, TypeError):
                ok = False
            if not ok:
                problems.append("conformance record with cells but no verdict counts of its own "
                                "(attempts/pass/fail): the counts cannot be invented on read")
    elif arm not in ARMS:
        if not is_sub_arm(arm, row.get("kpf18_item")):
            problems.append(f"arm {arm!r} not in {sorted(ARMS)} nor a declared KPF-18 sub-arm of item "
                            f"{row.get('kpf18_item')!r}")
        elif _ITEM3V2.match(arm) and row.get("kpf18_item") == 3 and "kpf18_arm" not in row:
            problems.extend(_validate_item3v2(row))
        elif row.get("kpf18_arm") != arm:
            problems.append(f"sub-arm {arm!r} without the matching kpf18_arm locator ({row.get('kpf18_arm')!r})")
        elif row.get("kpf18_item") == 186:
            problems.extend(_validate_r3(row))
        elif row.get("kpf18_item") == 187:
            problems.extend(_validate_r4(row))
    rsha = row.get("rows_sha256")
    if rsha is not None and not (isinstance(rsha, str) and re.fullmatch(r"[0-9a-f]{64}", rsha)):
        problems.append("rows_sha256 is present but not a sha256 hex digest")
    if not problems:
        body = {k: v for k, v in row.items() if k != "record_sha256"}
        if _digest(body) != row["record_sha256"]:
            if _digest(_intkeys(body)) == row["record_sha256"]:
                problems.append("record_sha256 does not re-derive from the stored JSON; it re-derives only if "
                                "digit-string dict keys are int (the writer hashed int-keyed dicts before JSON "
                                "stringified them, which sorts keys differently): WRITE-SIDE defect, refused "
                                "rather than weakening the integrity gate")
            else:
                problems.append("record_sha256 does not re-derive")
    return problems


def _rows_path(row: dict, sidecar: Path) -> Path:
    declared = Path(row["rows"])
    sibling = sidecar.parent / "rows" / declared.name  # the rows dir that travels with the sidecar wins
    return sibling if sibling.is_file() else declared


def _rows_present(row: dict, sidecar: Path) -> bool:
    if not row.get("rows_sha256"):
        return False  # attested-absent: nothing was hashed at write time, so nothing is re-derived now
    path = _rows_path(row, sidecar)
    if not path.is_file():
        return False
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest() == row["rows_sha256"]


def _applicability(row: dict) -> dict:
    """The scope this record states about itself (argv + readback); see ``_argv_scope``."""
    readback = row.get("argv_readback")
    return scope_from_argv(
        row.get("argv"), binary=row.get("binary_realpath") or row.get("binary"),
        binary_sha256=row.get("binary_sha256"), family=KNOB_FAMILY,
        varied=VARIED_BY_ARM.get(row.get("arm")) or CONF_VARIED.get(row.get("kpf_task")), dflash2=row.get("dflash2"),
        readback_ok=not (isinstance(readback, dict) and readback.get("proc_cmdline_matches_argv") is False))


def _children(row: dict) -> list[float]:
    values = row.get("ttft_ms")
    if not isinstance(values, list):
        return []
    return [float(v) for v in values if type(v) in (int, float) and v >= 0]


#: serving measure -> (record -> value | None, metric, unit, direction, reps getter, label)
def _m_ttft(row: dict):
    kids = _children(row)
    return (statistics.median(kids), len(kids)) if kids else None


def _m_prefill(row: dict):
    v = row.get("prompt_tokens_processed")
    return (v, 1) if type(v) is int and v >= 0 else None


def _m_decode(row: dict):
    agg = (row.get("decode_tok_s") or {}).get("aggregate") if isinstance(row.get("decode_tok_s"), dict) else None
    return (agg, 1) if type(agg) in (int, float) and agg >= 0 else None


MEASURES = {
    "fanout_ttft_ms": (_m_ttft, "kpf_fanout_ttft_median_ms", "ms", "lower_better",
                       "median first-token latency over the fan-out children in one window"),
    "prompt_tokens_processed": (_m_prefill, "kpf_prompt_tokens_processed", "tokens", "lower_better",
                                "one window's llama-server prompt-token counter"),
    "aggregate_decode_tok_s": (_m_decode, "kpf_aggregate_decode_tok_s", "t/s", "higher_better",
                               "one window's aggregate decode rate"),
}


def _pair_key(row: dict) -> tuple | None:
    """Identity under which a ``fork_off`` and a ``fork_on`` window are one A/B pair, or None."""
    m = _WINDOW.match(str(row.get("window_id") or ""))
    argv = row.get("argv") if isinstance(row.get("argv"), list) else []
    if not m:
        return None
    return (m["stem"], m["k"], row.get("kpf18_item"), row.get("binary_sha256"),
            row.get("prompt_set_sha256"), _flag(argv, "-m", "--model"), _flag(argv, "-np", "--parallel"))


def _serving_natives(natives: list[dict]) -> list[dict]:
    """One native per (paired fork_on record, serving measure present on both arms)."""
    offs: dict = {}
    for n in natives:
        row = n["row"]
        key = _pair_key(row)
        if key and row["arm"] == "fork_off" and _WINDOW.match(row["window_id"])["arm"] == "A":
            offs.setdefault(key, n)
    out = []
    for n in natives:
        row = n["row"]
        key = _pair_key(row)
        if not key or row["arm"] != "fork_on" or _WINDOW.match(row["window_id"])["arm"] != "B":
            continue
        off = offs.get(key)
        if off is None:
            continue
        for name, (getter, *_rest) in MEASURES.items():
            if getter(row) is not None and getter(off["row"]) is not None:
                out.append({"row": row, "sidecar_path": n["sidecar_path"], "measure": name,
                            "anchor": off["row"],
                            "attestation_present": bool(n["attestation_present"] and off["attestation_present"])})
    return out


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    path = Path(sidecar_path)
    if not path.is_file():
        return ()
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            return ()
        if validate_row(row):
            return ()
        rows.append(row)
    if len({r["record_sha256"] for r in rows}) != len(rows):
        return ()
    natives = [{"row": r, "sidecar_path": str(path), "attestation_present": _rows_present(r, path)} for r in rows
               if not _DECLINED_SUB_ARM.match(str(r.get("arm")))]
    return tuple(natives + _serving_natives(natives))


def _metric(row: dict) -> tuple[str, Any, str, int, str]:
    eq = (row.get("equivalence") or {}).get("vs_fresh") or {}
    n = int(eq.get("n") or 0)
    if n > 0:
        agree = eq.get("first_token_top1_agree", eq.get("top1_agree"))  # canonical name, legacy fallback
        if agree is None:
            raise ProjectionError("vs_fresh equivalence has no top-1 agreement count")
        return ("kpf_vs_fresh_first_token_top1_agree_fraction", round(agree / n, 6), "fraction", n,
                "fork-vs-fresh comparisons scored")
    ext = row.get("kpf_ext") or {}
    hit = ext.get("hit_tokens", row.get("n_fork_tokens"))
    if hit is None:
        raise ProjectionError("record has neither vs_fresh equivalence nor hit tokens to project")
    return "kpf_hit_tokens", hit, "tokens", 1, "one run total"


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("KPF native row must retain the runner record")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("KPF row is not a runner-authored record: " + "; ".join(problems))
    sidecar = Path(native.get("sidecar_path") or ".")
    present = _rows_present(row, sidecar)
    if row["arm"] == OUTCOME_ARM:
        return _project_outcome(row, sidecar, present)
    if is_conformance(row):
        return _project_conformance(row, sidecar, present)
    if _ITEM3V2.match(row["arm"]) and row.get("kpf18_item") == 3:
        return _project_item3v2(row, sidecar, present)
    if row.get("kpf18_item") == 186:
        return _project_r3(row, sidecar, present)
    if row.get("kpf18_item") == 187:
        return _project_r4(row, sidecar, present)
    if _DECLINED_SUB_ARM.match(row["arm"]):
        raise ProjectionError(f"KPF sub-arm {row['arm']} projects nothing: its only number is a 0 hit count")
    if native.get("measure"):
        return _project_measure(native, row, sidecar, present)
    metric, value, unit, reps, basis = _metric(row)
    dflash2 = bool(row.get("dflash2"))
    locator = (f"kpf:{row['run_id']}:{row['arm']}:dflash2={str(dflash2).lower()}:ps={row['prompt_set_sha256'][:16]}:"
               f"bin={row['binary_sha256'][:16]}:win={row['window_id']}")
    ext = row.get("kpf_ext") or {}
    return ClaimTuple(
        measurement_id="kpf-" + hashlib.sha256(row["record_sha256"].encode()).hexdigest()[:32],
        metric=metric,
        value=value,
        date=row["end_utc"],
        category=row["category"],
        claim=(f"KPF-18 item {row.get('kpf18_item')} arm {row['arm']}: {metric} = {value} "
               f"(counts against a fresh-vs-fresh control floor; n=1 per cell, no codified protocol)"),
        metric_direction="higher_better",
        protocol_id="",
        reps=reps,
        reps_basis=basis,
        unit=unit,
        attestation_path=str(_rows_path(row, sidecar)),
        attestation_sha256=row.get("rows_sha256") or "",
        attestation_locator=locator,
        attestation_present=present,
        attestation_verified=True if present else None,
        source_kind=SOURCE_KIND,
        extra={
            "schema": row["schema"], "run_id": row["run_id"], "arm": row["arm"], "dflash2": dflash2,
            "kpf18_item": row.get("kpf18_item"), "kpf18_arm": row.get("kpf18_arm"),
            "attestation_absent": None if row.get("rows_sha256") else
            "record carries no rows_sha256: the runner hashed no per-request rows file (attested-absent)",
            "window_id": row["window_id"],
            "gpu_window_id": row.get("gpu_window_id"), "binary_sha256": row["binary_sha256"],
            "prompt_set_sha256": row["prompt_set_sha256"], "host": row["host"], "argv": row["argv"],
            "start_utc": row.get("start_utc"), "end_utc": row["end_utc"],
            "record_sha256": row["record_sha256"], "sidecar_path": native.get("sidecar_path", ""),
            "equivalence": row["equivalence"], "ttft_ms": row.get("ttft_ms"),
            "prompt_tokens_processed": row.get("prompt_tokens_processed"), "cache_n": row.get("cache_n"),
            "n_fork_tokens": row.get("n_fork_tokens"), "unique_cells_peak": row.get("unique_cells_peak"),
            "decode_tok_s": row.get("decode_tok_s"),
            "kpf_ext": {k: ext.get(k) for k in EXT_KEYS} if ext else None,
        },
        applicability=_applicability(row),
    )


def _project_conformance(row: dict, sidecar: Path, present: bool) -> ClaimTuple:
    """A KPF-13.1 / KPF-17.4 conformance record: the record's OWN cell counts, as a pass (or detect) fraction.

    A mutant arm projects the DETECTED fraction (cells that failed under the injected defect / attempts); every other
    arm the pass fraction. A zero-cell record (aborted launch) projects as an attested zero-cell attempt:
    ``kpf_conformance_cells_scored`` = 0, never dropped and never given a rate. The producer's verdict words and
    ``decision_grade`` ride in ``extra`` verbatim; the grade is ``claim_tuple.grade()``'s alone.

    VB-KPF174C-ARM: a ``CONF_PAIR_TASKS`` record (KPF-17.4c) counts layout-matched PAIRS, so it projects the
    bit-identical pair fraction under its own metric name; its predeclared decision words (``locus``,
    ``explains_174b``, ``decision_grade``) are copied into ``extra`` from the record's ``decisions``, never re-derived.
    """
    arm, counts = row["arm"], _conf_counts(row)
    mutant = arm in _MUTANT_ARMS
    pair = CONF_PAIR_TASKS.get(row["kpf_task"])
    if row["n_cells"] == 0 or counts is None:
        metric, value, unit, reps = "kpf_conformance_cells_scored", 0, "cells", 1
        basis, shown = "aborted/zero-cell attempt: the launch scored no cell", "0 cells scored (aborted attempt)"
    elif pair:
        metric, basis, noun = pair
        value, unit, reps = round(counts["pass"] / counts["attempts"], 6), "fraction", counts["attempts"]
        shown = f"{counts['pass']}/{counts['attempts']} {noun}"
    else:
        num = counts["fail"] if mutant else counts["pass"]
        metric = "kpf_mutant_detected_fraction" if mutant else "kpf_conformance_cell_pass_fraction"
        value, unit, reps = round(num / counts["attempts"], 6), "fraction", counts["attempts"]
        basis = "conformance cells attempted in this launch"
        shown = f"{num}/{counts['attempts']} cells {'detected' if mutant else 'pass'}"
    decisions = row.get("decisions") if isinstance(row.get("decisions"), dict) else \
        (row.get("equivalence") or {}).get("decisions")
    words = {k: (decisions or {}).get(k) for k in ("locus", "explains_174b", "decision_grade")} if pair else {}
    locator = (f"kpf:{row['run_id']}:{row['arm']}:task={row['kpf_task']}:ps={row['prompt_set_sha256'][:16]}:"
               f"bin={row['binary_sha256'][:16]}:win={row['window_id']}")
    return ClaimTuple(
        measurement_id="kpf-" + hashlib.sha256(row["record_sha256"].encode()).hexdigest()[:32],
        metric=metric, value=value, unit=unit, date=row["end_utc"], category=row["category"],
        claim=(f"{row['kpf_task']} arm {arm}: {shown}; counts from the record's own verdict block, "
               f"n per cell as listed, no codified protocol"),
        metric_direction="higher_better", protocol_id="", reps=reps, reps_basis=basis,
        attestation_path=str(_rows_path(row, sidecar)), attestation_sha256=row.get("rows_sha256") or "",
        attestation_locator=locator, attestation_present=present,
        attestation_verified=True if present else None, source_kind=SOURCE_KIND,
        extra={"schema": row["schema"], "run_id": row["run_id"], "arm": arm, "kpf_task": row["kpf_task"],
               "dflash2": bool(row.get("dflash2")), "counts": counts, "n_cells": row["n_cells"],
               "mutant_arm": mutant, "decisions": decisions, "rules_sha256": row.get("rules_sha256"),
               "attestation_absent": None if row.get("rows_sha256") else
               "record carries no rows_sha256: the launch wrote no cells (attested-absent)",
               "window_id": row["window_id"], "binary_sha256": row["binary_sha256"],
               "prompt_set_sha256": row["prompt_set_sha256"], "host": row["host"], "argv": row["argv"],
               "start_utc": row.get("start_utc"), "end_utc": row["end_utc"],
               "record_sha256": row["record_sha256"], "sidecar_path": str(sidecar), **words},
        applicability=_applicability(row))


def _project_item3v2(row: dict, sidecar: Path, present: bool) -> ClaimTuple:
    """VB-KVU-PF.6: one KPF-18 item-3 v2 load, as the record's OWN per-pair judged classes.

    value = the number of JUDGED pairs (``item3v2.judged`` keys, less those the launcher itself names ``*_recorded``:
    recorded, not judged, per its predeclaration) whose class is ``fork_effect_candidate``; reps = judged pairs. Every
    pair's class, first divergence, margin and A/A floor ride in ``extra`` verbatim. The run verdict (``FORK_EFFECT``)
    is the launcher's ``verdict.py`` over all loads and lives in VERDICT.json, not in a record: it is not re-derived
    here. A budget-aborted partial load (``partial: true``, no block) and an invalid load project as attested
    incomplete attempts (``kpf18_item3v2_judged_pairs_scored`` = 0) -- kept, never dropped, never given a count.
    """
    block = row.get("item3v2")
    load = int(_ITEM3V2.match(row["arm"])["load"])
    locator = (f"kpf:{row['run_id']}:{row['arm']}:item=3v2:ps={row['prompt_set_sha256'][:16]}:"
               f"bin={row['binary_sha256'][:16]}:win={row['window_id']}")
    common = dict(
        measurement_id="kpf-" + hashlib.sha256(row["record_sha256"].encode()).hexdigest()[:32],
        date=row["end_utc"], category=row["category"], protocol_id="",
        attestation_path=str(_rows_path(row, sidecar)), attestation_sha256=row.get("rows_sha256") or "",
        attestation_locator=locator, attestation_present=present,
        attestation_verified=True if present else None, source_kind=SOURCE_KIND,
        applicability=_applicability(row))
    extra = {"schema": row["schema"], "run_id": row["run_id"], "arm": row["arm"], "kpf18_item": 3, "load": load,
             "kpf18_arm": None, "locator_note": "launcher wrote no kpf18_arm; arm token + item3v2.load locate it",
             "window_id": row["window_id"], "gpu_window_id": row.get("gpu_window_id"),
             "binary_sha256": row["binary_sha256"], "prompt_set_sha256": row["prompt_set_sha256"],
             "host": row["host"], "argv": row["argv"], "start_utc": row.get("start_utc"), "end_utc": row["end_utc"],
             "record_sha256": row["record_sha256"], "sidecar_path": str(sidecar), "checks": row.get("checks")}
    if not isinstance(block, dict) or block.get("valid") is not True:
        reasons = list((block or {}).get("invalid_reasons") or []) if isinstance(block, dict) else []
        why = "partial (budget-aborted) load" if row.get("partial") is True else "invalid load: " + "; ".join(
            map(str, reasons))
        return ClaimTuple(
            metric="kpf18_item3v2_judged_pairs_scored", value=0, unit="judged stream pairs",
            claim=(f"KPF-18 item 3 v2 load {load}: incomplete attempt ({why}); 0 judged pairs scored, does not "
                   f"count toward the predeclared n"),
            metric_direction="higher_better", reps=1,
            reps_basis="aborted/incomplete attempt: the load scored no judged pair", **common,
            extra={**extra, "partial": row.get("partial") is True, "valid": False, "invalid_reasons": reasons,
                   "ttft_ms": row.get("ttft_ms"), "n_fork_tokens": row.get("n_fork_tokens")},
            observation={"outcome_native": why[:120]})
    judged = {k: v for k, v in block["judged"].items() if not k.endswith("_recorded")}
    if not judged:
        raise ProjectionError("item3v2 block has no judged (non-recorded) pair")
    classes = {k: v["class"] for k, v in block["judged"].items()}
    hits = sum(1 for v in judged.values() if v["class"] == "fork_effect_candidate")
    shown = ", ".join(f"{k} {c}" for k, c in classes.items())
    return ClaimTuple(
        metric="kpf18_item3v2_judged_pairs_fork_effect_candidate", value=hits, unit="judged stream pairs",
        claim=(f"KPF-18 item 3 v2 load {load} (fresh load, arm order {block.get('arm_order')}): {hits}/{len(judged)} "
               f"judged pairs classed fork_effect_candidate (margin above the same-timing A/A floor); per pair: "
               f"{shown}; *_recorded pairs are recorded, not judged; one load, no codified protocol"),
        metric_direction="lower_better", reps=len(judged),
        reps_basis="judged stream pairs on one fresh load (classes from the record's own item3v2 block)", **common,
        extra={**extra, "valid": True, "invalid_reasons": [], "partial": False, "classes": classes,
               "judged": {k: {f: v.get(f) for f in ("class", "first_divergence", "aa_first_divergence",
                                                    "floor_max_abs_dlogprob", "margin_nofork", "n_compared")}
                          for k, v in block["judged"].items()},
               "arm_order": block.get("arm_order"), "block_order": block.get("block_order"),
               "group": block.get("group"), "predeclaration_sha256": block.get("predeclaration_sha256")},
        observation={"outcome_native": ",".join(f"{k}:{c}" for k, c in classes.items())[:120]})


def _num(x: Any) -> bool:
    return type(x) in (int, float) and x == x and abs(x) != float("inf")


def _project_r3(row: dict, sidecar: Path, present: bool) -> ClaimTuple:
    """VB-KVU-PF.7: one KPF-18-S1.R3 step, as COUNTS from the record's OWN ``r3.result``.

    ``long6`` (18.3 part 4): value = the worst child-vs-cold mean |dlogprob| (``worst_child_vs_cold``), reps = the
    teacher-forced positions valid in every arm (``n_common_valid``); the six-pair cold floor (``floor_used``) is the
    ``observation.anchor_value``. ``item2q`` (item 2, one cell): value = fork-vs-own pairs OK against the >= 3-Q
    placement floor (``judge.n_ok``), reps = pairs judged (``judge.n_pairs``); the valid-Q count rides in the claim and
    ``extra``. The step's predeclared verdict word (``r3.result.verdict``) rides in ``extra`` and
    ``observation.outcome_native`` VERBATIM -- it is never re-derived or normalised here. A record whose step did not
    finish (``step_complete`` false), or whose result lacks the counts (an invalid arm, no judgeable floor), projects
    ``kpf18_r3_steps_scored`` = 0 as an attested incomplete attempt: kept, never dropped, never given a count.
    """
    block = row["r3"]
    step = block["step_id"]
    result = block.get("result") if block.get("step_complete") is True else None
    locator = (f"kpf:{row['run_id']}:{row['arm']}:item=186:step={step}:ps={row['prompt_set_sha256'][:16]}:"
               f"bin={row['binary_sha256'][:16]}:win={row['window_id']}")
    common = dict(
        measurement_id="kpf-" + hashlib.sha256(row["record_sha256"].encode()).hexdigest()[:32],
        date=row["end_utc"], category=row["category"], protocol_id="",
        attestation_path=str(_rows_path(row, sidecar)), attestation_sha256=row.get("rows_sha256") or "",
        attestation_locator=locator, attestation_present=present,
        attestation_verified=True if present else None, source_kind=SOURCE_KIND,
        applicability=_applicability(row))
    verdict = (result or {}).get("verdict")
    extra = {"schema": row["schema"], "run_id": row["run_id"], "arm": row["arm"], "kpf18_item": 186,
             "kpf18_arm": row.get("kpf18_arm"), "kpf_task": row.get("kpf_task"), "step": step,
             "step_complete": block.get("step_complete"), "fresh_load": block.get("fresh_load"),
             "group": block.get("group"), "predeclaration_sha256": block.get("predeclaration_sha256"),
             "verdict": verdict, "window_id": row["window_id"], "gpu_window_id": row.get("gpu_window_id"),
             "binary_sha256": row["binary_sha256"], "prompt_set_sha256": row["prompt_set_sha256"],
             "host": row["host"], "argv": row["argv"], "start_utc": row.get("start_utc"), "end_utc": row["end_utc"],
             "record_sha256": row["record_sha256"], "sidecar_path": str(sidecar), "checks": row.get("checks")}
    why, tup = None, None
    if not isinstance(result, dict):
        why = "step did not finish (step_complete false, no result)"
    elif step == "long6":
        worst, floor, n = result.get("worst_child_vs_cold"), result.get("floor_used"), result.get("n_common_valid")
        valid = result.get("arm_valid")
        if not (_num(worst) and _num(floor) and floor > 0 and type(n) is int and n > 0
                and isinstance(valid, dict) and valid and all(v is True for v in valid.values())):
            why = "long6 result without a valid worst/floor/common-position count"
        else:
            judged = result.get("judged_pairs") or []
            obs = {"anchor_value": floor, "effect_rel": (worst - floor) / floor, "outcome_native": str(verdict)[:120]}
            if judged:
                obs["n_pairs"] = len(judged)
            pc = result.get("pcache_reading") if isinstance(result.get("pcache_reading"), dict) else {}
            tup = dict(
                metric="kpf18_r3_long6_worst_child_vs_cold_mean_abs_dlogprob", value=worst,
                unit="nats (mean |dlogprob| per position)",
                claim=(f"KPF-18-S1.R3 long6 (18.3 part 4, T={result.get('T')}, P={result.get('n_task')}): worst "
                       f"child-vs-cold mean |dlogprob| {worst:.6g} ({result.get('worst_pair')}) vs the "
                       f"{len(result.get('floor_pairs') or [])}-pair cold-vs-cold floor {floor:.6g} "
                       f"({result.get('floor_pair')}), ratio {worst / floor:.4g}, over {n} common teacher-forced "
                       f"positions; counts from the record's own r3.result, one fresh load, no codified protocol"),
                metric_direction="lower_better", reps=n,
                reps_basis="teacher-forced positions valid in every arm (one fresh load; r3.result.n_common_valid)",
                observation=obs,
                extra={**extra, "floor_used": floor, "floor_raw": result.get("floor_raw"),
                       "floor_pair": result.get("floor_pair"), "floor_pairs": result.get("floor_pairs"),
                       "judged_pairs": judged, "worst_pair": result.get("worst_pair"),
                       "ratio_worst_over_floor": result.get("ratio_worst_over_floor"),
                       "within_floor": result.get("within_floor"),
                       "predeclared_rule_satisfied": result.get("predeclared_rule_satisfied"),
                       "d": {k: {f: (v or {}).get(f) for f in ("mean_abs_dlogprob", "max_abs_dlogprob", "n_positions",
                                                               "n_exact_equal")}
                             for k, v in (result.get("d") or {}).items()},
                       "n_valid": result.get("n_valid"), "arm_valid": valid,
                       "pcache_label": pc.get("label"), "pcache_weight": pc.get("weight")})
    else:  # item2q
        judge = result.get("judge") if isinstance(result.get("judge"), dict) else {}
        n_pairs, n_ok, n_q = judge.get("n_pairs"), judge.get("n_ok"), result.get("n_q_valid")
        if not (result.get("fo_valid") is True and judge.get("judgeable") is True and type(n_pairs) is int
                and n_pairs > 0 and type(n_ok) is int and 0 <= n_ok <= n_pairs and type(n_q) is int):
            why = "item2q result without a judgeable fork-vs-own pair count (F/O invalid or no placement floor)"
        else:
            fo = result.get("fork_vs_own") or {}
            tup = dict(
                metric="kpf18_r3_item2q_fork_vs_own_pairs_ok", value=n_ok, unit="fork-vs-own pairs",
                claim=(f"KPF-18-S1.R3 item2q cell {result.get('cell')} (T={result.get('T')}, S={result.get('S')}): "
                       f"{n_ok}/{n_pairs} fork-vs-own pairs OK against the placement floor of {n_q} valid Q "
                       f"repeat(s) (Q-vs-own prefixes {result.get('q_vs_own_prefixes')}, fork-vs-own prefix "
                       f"{fo.get('prefix')}); counts from the record's own r3.result, no codified protocol"),
                metric_direction="higher_better", reps=n_pairs,
                reps_basis="fork-vs-own pairs judged against the record's own Q-vs-own placement floor",
                observation={"outcome_native": str(verdict)[:120]},
                extra={**extra, "cell": result.get("cell"), "T": result.get("T"), "S": result.get("S"),
                       "n_q": result.get("n_q"), "n_q_valid": n_q, "q_vs_own_prefixes": result.get("q_vs_own_prefixes"),
                       "fork_vs_own": {f: fo.get(f) for f in ("top1", "prefix", "n_cmp", "maxabs_union", "kld",
                                                              "tokens_identical", "identical")},
                       "judge": {f: judge.get(f) for f in ("n_pairs", "n_aa", "n_ok", "n_not_ok", "n_top1",
                                                           "n_within", "n_prefix_ok", "aa_floor", "floor_thin",
                                                           "bit_identity_owed", "predeclared_rule_satisfied")}})
    if tup is None:
        return ClaimTuple(
            metric="kpf18_r3_steps_scored", value=0, unit="R3 steps",
            claim=(f"KPF-18-S1.R3 step {step} ({row['arm']}): incomplete attempt ({why}); 0 steps scored, does not "
                   f"count toward the predeclared verdict inputs"),
            metric_direction="higher_better", reps=1,
            reps_basis="aborted/incomplete attempt: the step scored nothing", **common,
            extra={**extra, "incomplete_reason": why}, observation={"outcome_native": why[:120]})
    return ClaimTuple(**tup, **common)


def _project_r4(row: dict, sidecar: Path, present: bool) -> ClaimTuple:
    """Project native R4 localisation, not hit tokens or a performance verdict.

    The 256 positions are paired positions within ONE load, never independent runs.
    ChildX/factorial and cross-load readings retain the producer's zero weight.
    Invalid/incomplete attempts use a separate scored-step count, never a zero distance.
    """
    block = row["r4"]
    result = block.get("result") if block["step_complete"] else None
    result = result if isinstance(result, dict) else {}
    common = dict(
        measurement_id="kpf-" + hashlib.sha256(row["record_sha256"].encode()).hexdigest()[:32],
        date=row["end_utc"], category=row["category"], protocol_id="",
        attestation_path=str(_rows_path(row, sidecar)), attestation_sha256=row.get("rows_sha256") or "",
        attestation_locator=(f"kpf:{row['run_id']}:{row['arm']}:item=187:step=r4:"
                             f"ps={row['prompt_set_sha256'][:16]}:bin={row['binary_sha256'][:16]}:win={row['window_id']}"),
        attestation_present=present, attestation_verified=True if present else None,
        source_kind=SOURCE_KIND, applicability=_applicability(row))
    extra = {key: row.get(key) for key in (
        "schema", "run_id", "arm", "kpf_task", "kpf18_item", "kpf18_arm", "record_sha256",
        "binary_sha256", "prompt_set_sha256", "window_id", "gpu_window_id", "argv", "host",
        "start_utc", "end_utc", "checks")}
    # Preserve native provenance and verdict inputs, including explicitly zero-weight readings.
    extra.update(r4=block, sidecar_path=str(sidecar), verdict=result.get("verdict"))
    value, floor, n = (result.get(k) for k in ("d_child_vs_coldE", "floor_used", "n_common_valid"))
    valid = result.get("arm_valid")
    judged = ("child", "child2", "coldA", "coldB", "coldE")
    verdict = result.get("verdict")
    scored = (block["step_complete"] and block.get("fresh_load") is True
              and _num(value) and value >= 0 and _num(floor) and floor > 0
              and type(n) is int and n >= 16 and result.get("prompt_ge_50k") is True
              and isinstance(valid, dict) and all(valid.get(arm) is True for arm in judged)
              and verdict in {"FORK_PATH_NOT_REPRODUCIBLE", "OCCUPANCY_NUMERICS", "FORK_PATH_SPECIFIC",
                              "BETWEEN_FLOOR_AND_COLD_SPREAD"})
    if not scored:
        why = "R4 incomplete, invalid or abstaining native localisation; no judged distance scored"
        return ClaimTuple(
            metric="kpf18_r4_steps_scored", value=0, unit="R4 steps", metric_direction="higher_better",
            claim=f"KPF-18-S1.R4 ({row['arm']}): {why}; 0 steps scored",
            reps=1, reps_basis="aborted/incomplete attempt: the step scored nothing",
            observation={"outcome_native": str(verdict or why)[:120]},
            extra={**extra, "incomplete_reason": why}, **common)
    return ClaimTuple(
        metric="kpf18_r4_child_vs_coldE_mean_abs_dlogprob", value=value,
        unit="mean absolute log-probability difference", metric_direction="lower_better",
        claim=(f"KPF-18-S1.R4: occupancy-matched child-vs-coldE mean |dlogprob| {value:.6g}, "
               f"native cold floor {floor:.6g}, over {n} common teacher-forced positions; "
               "one fresh load, an observation at the recorded build and argv"),
        reps=n, reps_basis="teacher-forced positions valid in five judged arms; one fresh load, NOT independent runs",
        observation={"anchor_value": floor, "outcome_native": str(verdict)[:120]}, extra=extra, **common)


def _project_measure(native: dict, row: dict, sidecar: Path, present: bool) -> ClaimTuple:
    """One serving measure of a fork_on window, against its paired fork_off window (P1-K)."""
    name = native["measure"]
    if name not in MEASURES:
        raise ProjectionError(f"KPF serving measure {name!r} is not one of {sorted(MEASURES)}")
    anchor = native.get("anchor")
    problems = validate_row(anchor) if isinstance(anchor, dict) else ["anchor is not a record"]
    if problems:
        raise ProjectionError("KPF anchor is not a runner-authored record: " + "; ".join(problems))
    if (row["arm"] != "fork_on" or anchor["arm"] != "fork_off" or _pair_key(row) is None
            or _pair_key(row) != _pair_key(anchor)):
        raise ProjectionError("KPF serving measure needs a fork_on window and its paired fork_off window")
    getter, metric, unit, direction, basis = MEASURES[name]
    got, base = getter(row), getter(anchor)
    if got is None or base is None:
        raise ProjectionError(f"KPF serving measure {name} is absent on one arm")
    (value, reps), (anchor_value, _) = got, base
    present = bool(present and _rows_present(anchor, sidecar))
    obs: dict = {"anchor_value": anchor_value, "n_pairs": 1}
    if anchor_value:
        obs["effect_rel"] = (value - anchor_value) / anchor_value
    locator = (f"kpf:{row['run_id']}:{row['arm']}:measure={name}:vs={anchor['record_sha256'][:16]}:"
               f"ps={row['prompt_set_sha256'][:16]}:bin={row['binary_sha256'][:16]}:win={row['window_id']}")
    shown = f"{value:g}" if isinstance(value, float) else str(value)
    base_shown = f"{anchor_value:g}" if isinstance(anchor_value, float) else str(anchor_value)
    effect = f" ({obs['effect_rel'] * 100:+.1f}%)" if "effect_rel" in obs else ""
    return ClaimTuple(
        measurement_id="kpf-" + hashlib.sha256(f"{row['record_sha256']}:{name}".encode()).hexdigest()[:32],
        metric=metric, value=value, unit=unit, date=row["end_utc"], category=row["category"],
        claim=(f"KPF-18 item {row.get('kpf18_item')} slot-fork on vs off ({row['window_id']} vs "
               f"{anchor['window_id']}): {metric} {shown} {unit} vs {base_shown} {unit}{effect}; "
               f"{basis}; n=1 A/B window pair, no codified protocol, no verdict"),
        metric_direction=direction, protocol_id="", reps=reps, reps_basis=basis,
        attestation_path=str(_rows_path(row, sidecar)), attestation_sha256=row.get("rows_sha256") or "",
        attestation_locator=locator, attestation_present=present,
        attestation_verified=True if present else None, source_kind=SOURCE_KIND,
        extra={"schema": row["schema"], "run_id": row["run_id"], "arm": row["arm"], "measure": name,
               "anchor_run_id": anchor["run_id"], "anchor_record_sha256": anchor["record_sha256"],
               "window_id": row["window_id"], "anchor_window_id": anchor["window_id"],
               "record_sha256": row["record_sha256"], "sidecar_path": native.get("sidecar_path", "")},
        applicability=_applicability(row), observation=obs)


# ------------------------------------------------------------------ KPF-26.1f: task-outcome records
_OUTCOME_NORM = {"WITHIN_SPREAD": "null", "UNCHANGED": "null", "CHANGED": "regressed", "INVALID": "refused_scope"}


def _project_outcome(row: dict, sidecar: Path, present: bool) -> ClaimTuple:
    """One KPF-26.1 window: flag-on (B) pass rate against the flag-off (A) baseline, spread as the floor.

    A normalisation of the producer's OWN verdict word into the observation vocabulary (``outcome_native`` keeps
    it verbatim); the verdict is never re-derived here and the grade is ``claim_tuple.grade()``'s alone.
    """
    out = row["kpf_outcome"]
    per = out["per_arm"]
    rate = {k: per[k]["pass"] / per[k]["n"] for k in OUTCOME_ARMS}
    verdict = out["verdict"]
    obs: dict = {"anchor_value": rate["A"], "n_pairs": out["n_cases"], "outcome_native": str(verdict)[:120]}
    if rate["A"]:
        obs["effect_rel"] = (rate["B"] - rate["A"]) / rate["A"]
        obs["noise_floor_rel"] = abs(out["spread"]) / rate["A"]
    if verdict in _OUTCOME_NORM:
        obs["outcome"] = _OUTCOME_NORM[verdict]
        obs["decisive"] = verdict == "CHANGED"
    if verdict == "INVALID":
        failed = sorted(k for k, v in (out.get("gates") or {}).items() if v is not True)
        obs["outcome_reason"] = ("predeclared validity gate(s) failed: " + ", ".join(failed))[:300] if failed else \
            "producer verdict INVALID"
    cells = ", ".join(f"{k} {per[k]['pass']}/{per[k]['n']}" for k in OUTCOME_ARMS)
    locator = (f"kpf:{row['run_id']}:{row['arm']}:seed={out['seed']}:manifest={out['manifest_digest'][:16]}:"
               f"bin={row['binary_sha256'][:16]}:win={row['window_id']}")
    return ClaimTuple(
        measurement_id="kpf-" + hashlib.sha256(row["record_sha256"].encode()).hexdigest()[:32],
        metric="kpf261_flag_on_task_pass_rate", value=rate["B"], unit="fraction", date=row["end_utc"],
        category=row["category"],
        claim=(f"KPF-26.1 {row['window_id']} (seed {out['seed']}, manifest {out['manifest_digest'][:12]}): task pass "
               f"{cells}; spread {out['spread']:g}, drop {out['drop']:g}, {out['regress']} regress / "
               f"{out['improve']} improve; producer verdict {verdict} ({out['reorder_decision']}); "
               f"one window, predeclared rule, no codified protocol"),
        metric_direction="higher_better", protocol_id="", reps=out["n_cases"],
        reps_basis="task cases scored per arm (every case counted; errors and timeouts are fails)",
        attestation_path=str(_rows_path(row, sidecar)), attestation_sha256=row.get("rows_sha256") or "",
        attestation_locator=locator, attestation_present=present,
        attestation_verified=True if present else None, source_kind=SOURCE_KIND,
        extra={"schema": row["schema"], "run_id": row["run_id"], "arm": row["arm"], "window_id": row["window_id"],
               "seed": out["seed"], "manifest_digest": out["manifest_digest"], "per_arm": per,
               "spread": out["spread"], "drop": out["drop"], "regress": out["regress"], "improve": out["improve"],
               "ctrl_regress": out["ctrl_regress"], "ctrl_improve": out["ctrl_improve"],
               "sign_test_p_regress": out["sign_test_p_regress"], "verdict": verdict,
               "reorder_decision": out["reorder_decision"], "gates": out["gates"], "rule": out["rule"],
               "treatment_applied": out["treatment_applied"], "binary_sha256": row["binary_sha256"],
               "prompt_set_sha256": row["prompt_set_sha256"], "argv": row["argv"],
               "argv_source": row.get("argv_source"), "host": row["host"], "end_utc": row["end_utc"],
               "record_sha256": row["record_sha256"], "sidecar_path": str(sidecar)},
        applicability=scope_from_argv(
            row.get("argv"), binary=row.get("binary_realpath") or row.get("binary"),
            binary_sha256=row.get("binary_sha256"), family="prompt_assembly",
            varied=["ORCHESTRATOR_PREFIX_INDEX+ORCHESTRATOR_PREFIX_INDEX_FORK"]),
        observation=obs)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def outcome_record(win_dir: str | Path, summary_path: str | Path, *, binary: str | Path, model: str, n_slots: int,
                   host: str | None = None, run_id: str | None = None) -> dict:
    """Build the ``epyc.kpf.run.v1`` outcome record for ONE KPF-26.1 window from its on-disk artefacts.

    Re-derives from ``cases.jsonl`` (the per-arm pass counts and the regress / improve / ctrl counts) and refuses the
    window when they disagree with ``summary.json``, when ``manifest.json``'s digest is not the summary's, or when the
    window is not complete: a record is only as good as the files it can be re-hashed against. The verdict, the rule
    text and the gates are carried VERBATIM from the runner's summary -- nothing is graded or re-decided here.
    ``binary`` / ``model`` / ``n_slots`` are the launch facts the runner did not record (it wrote no launch argv); the
    reconstructed argv says so in ``argv_source``.
    """
    import socket

    win, summary_path = Path(win_dir), Path(summary_path)
    summary = json.loads(summary_path.read_text())
    manifest = json.loads((win / "manifest.json").read_text())
    treatment = json.loads((win / "treatment.json").read_text()) if (win / "treatment.json").is_file() else {}
    cases_path = win / "cases.jsonl"
    cases = [json.loads(x) for x in cases_path.read_text().splitlines() if x.strip()]
    if summary.get("complete") is not True or summary.get("stopped"):
        raise ProjectionError(f"{summary_path}: window not complete (complete={summary.get('complete')!r}, "
                              f"stopped={summary.get('stopped')!r}); an unfinished window is not a record")
    if manifest.get("digest") != summary.get("manifest_digest") or manifest.get("seed") != summary.get("seed"):
        raise ProjectionError(f"{summary_path}: manifest.json digest/seed disagree with the summary")
    per_arm = {a: {"pass": sum(1 for c in cases if c["arm"] == a and c["pass"] is True),
                   "n": sum(1 for c in cases if c["arm"] == a)} for a in OUTCOME_ARMS}
    n_cases = summary["n_cases"]
    if any(cell["n"] != n_cases for cell in per_arm.values()):
        raise ProjectionError(f"{summary_path}: cases.jsonl does not hold n_cases={n_cases} cases for every arm")
    cell: dict = {}
    for c in cases:
        cell.setdefault((c["rep"], c["wave"], c["step"]), {})[c["arm"]] = c["pass"] is True
    derived = {"regress": sum(1 for v in cell.values() if v["A"] and not v["B"]),
               "improve": sum(1 for v in cell.values() if not v["A"] and v["B"]),
               "ctrl_regress": sum(1 for v in cell.values() if v["A"] and not v["A2"]),
               "ctrl_improve": sum(1 for v in cell.values() if not v["A"] and v["A2"])}
    for key, got in derived.items():
        if summary.get(key) != got:
            raise ProjectionError(f"{summary_path}: {key} is {summary.get(key)!r} in the summary but {got} in cases.jsonl")
    rates = {a: per_arm[a]["pass"] / n_cases for a in OUTCOME_ARMS}
    for a in OUTCOME_ARMS:
        if abs(round(rates[a], 4) - summary["pass_rate"][a]) > 1e-9:
            raise ProjectionError(f"{summary_path}: pass_rate[{a}] disagrees with cases.jsonl")
    for key, got in (("spread", abs(rates["A"] - rates["A2"])), ("drop", rates["A"] - rates["B"])):
        if abs(got - summary[key]) > 6e-5:
            raise ProjectionError(f"{summary_path}: {key} {summary[key]!r} is not re-derivable from the pass counts")
    binary_real = str(Path(binary).resolve())
    argv = [binary_real, "-m", model, "-np", str(n_slots)]
    out = {"kpf_item": "26.1", "seed": summary["seed"], "manifest_digest": summary["manifest_digest"],
           "manifest_sha256": _sha256_file(win / "manifest.json"), "n_tasks": manifest.get("n_tasks"),
           "n_cases": n_cases, "reps": summary.get("reps"), "per_arm": per_arm, "spread": summary["spread"],
           "drop": summary["drop"], **derived, "sign_test_p_regress": summary["sign_test_p_regress"],
           "verdict": summary["verdict"], "reorder_decision": summary["reorder_decision"],
           "gates": summary["gates"], "rule": summary["rule"], "treatment_applied": treatment.get("applied"),
           "baseline_transport_errors": summary.get("baseline_transport_errors"),
           "B_transport_errors": summary.get("B_transport_errors"), "incomplete_cases": summary.get("incomplete_cases"),
           "text_identical_A_B": summary.get("text_identical_A_B"),
           "text_identical_A_A2_control": summary.get("text_identical_A_A2_control"),
           "finished_utc": summary["finished_utc"]}
    rid = run_id or f"kpf261-seed{summary['seed']}"
    row = {"schema": SCHEMA, "kpf_task": "KPF-26.1", "run_id": rid, "arm": OUTCOME_ARM,
           "binary": str(binary), "binary_realpath": binary_real, "binary_sha256": _sha256_file(Path(binary_real)),
           "argv": argv,
           "argv_source": {"source": "reconstructed",
                           "basis": "binary from linkage.txt, model from the server log's load_model line, n_slots from "
                                    "its n_slots line; the runner recorded no launch argv, so no other flag is claimed"},
           "prompt_set": "manifest.json", "prompt_set_sha256": summary["manifest_digest"],
           "window_id": f"{rid}-win", "start_utc": None, "end_utc": summary["finished_utc"],
           "host": host or socket.gethostname(), "rows": str(cases_path.resolve()), "rows_sha256": _sha256_file(cases_path),
           "kpf_outcome": out, "instrument_class": "task-outcome", "category": "CANDIDATE",
           "grading_note": "one window, predeclared outcome rule, no codified protocol: an OBSERVATION; projects "
                           "under VB-KVU-PF through claim_tuple.grade()"}
    row["record_sha256"] = _digest(row)
    return row


def write_outcome_sidecar(sidecar: str | Path, row: dict) -> bool:
    """Append ``row`` to a ``belief_measurements.jsonl`` unless its ``record_sha256`` is already there."""
    path = Path(sidecar)
    have = {json.loads(x).get("record_sha256") for x in path.read_text().splitlines() if x.strip()} \
        if path.is_file() else set()
    if row["record_sha256"] in have:
        return False
    with open(path, "a") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    return True


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


def main(argv: list[str] | None = None) -> int:
    """``kv_prefix_fork.py write-outcome``: one KPF-26.1 window dir -> a line in ``belief_measurements.jsonl``."""
    import argparse

    ap = argparse.ArgumentParser(description=main.__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write-outcome")
    w.add_argument("--win-dir", required=True)
    w.add_argument("--summary", required=True)
    w.add_argument("--sidecar", required=True)
    w.add_argument("--binary", required=True)
    w.add_argument("--model", required=True)
    w.add_argument("--n-slots", type=int, required=True)
    w.add_argument("--run-id")
    a = ap.parse_args(argv)
    row = outcome_record(a.win_dir, a.summary, binary=a.binary, model=a.model, n_slots=a.n_slots, run_id=a.run_id)
    print(json.dumps({"run_id": row["run_id"], "record_sha256": row["record_sha256"],
                      "written": write_outcome_sidecar(a.sidecar, row)}))
    return 0


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "SCHEMA", "SIDECAR_NAME", "KPF18_SUB_ARMS", "is_sub_arm",
           "CONFORMANCE_ARMS", "is_conformance",
           "native_rows", "project", "validate_row", "frames_for_sidecar", "OUTCOME_ARM", "outcome_record",
           "write_outcome_sidecar"]


if __name__ == "__main__":
    raise SystemExit(main())
