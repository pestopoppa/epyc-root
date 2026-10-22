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
    181: (r"A_(?:ckpt|tailonly)(?:_forkoff)?", r"B_identical_resend_and_child_eq_trunk(?:_forkoff)?",
          r"C_length_sweep_drafter_(?:on|off)", rf"D_hit_count_prediction_{_CFG}"),
    182: (r"cold_control_probe", rf"parity_{_CFG}_(?:drafter_on|request_off|launch)", rf"policy_control_{_CFG}",
          r"parity_summary"),
    183: (r"chunk_split_cost", r"end_ckpt_position_and_multi_turn", r"request_lane", r"warm_vs_cold_long_prompt"),
    184: (r"item3_localisation",),
}
_SUB_ARM_RE = {item: re.compile("^(?:" + "|".join(pats) + ")$") for item, pats in KPF18_SUB_ARMS.items()}


def is_sub_arm(arm: Any, item: Any) -> bool:
    """True iff ``arm`` is a declared KPF-18 sub-arm of ``item`` (parity_summary is not a parity column)."""
    rx = _SUB_ARM_RE.get(item) if type(item) is int else None
    return bool(rx and isinstance(arm, str) and rx.match(arm))


_WINDOW = re.compile(r"^(?P<stem>.+)-(?P<arm>[AB])(?P<k>\d+)$")
REQUIRED = ("run_id", "arm", "binary_sha256", "prompt_set_sha256", "window_id", "end_utc", "host", "argv",
            "equivalence", "rows", "record_sha256", "category")  # rows_sha256 absent = attested-absent (VB-KVU-PF.2)
EXT_KEYS = ("checkpoint_set", "hit_components", "hit_length_min", "hit_tokens", "tokens_lost_to_missing_checkpoint",
            "drafter_drop_kind", "request_lane", "cache_skip_control", "pinned_count")


def _digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_row(row: Any) -> list[str]:
    if not isinstance(row, dict):
        return ["row is not an object"]
    problems = []
    if row.get("schema") != SCHEMA:
        problems.append(f"schema is not {SCHEMA}")
    for key in REQUIRED:
        if row.get(key) in (None, "", [], {}):
            problems.append(f"missing {key}")
    arm = row.get("arm")
    if arm not in ARMS:
        if not is_sub_arm(arm, row.get("kpf18_item")):
            problems.append(f"arm {arm!r} not in {sorted(ARMS)} nor a declared KPF-18 sub-arm of item "
                            f"{row.get('kpf18_item')!r}")
        elif row.get("kpf18_arm") != arm:
            problems.append(f"sub-arm {arm!r} without the matching kpf18_arm locator ({row.get('kpf18_arm')!r})")
    rsha = row.get("rows_sha256")
    if rsha is not None and not (isinstance(rsha, str) and re.fullmatch(r"[0-9a-f]{64}", rsha)):
        problems.append("rows_sha256 is present but not a sha256 hex digest")
    if not problems:
        body = {k: v for k, v in row.items() if k != "record_sha256"}
        if _digest(body) != row["record_sha256"]:
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
        varied=VARIED_BY_ARM.get(row.get("arm")), dflash2=row.get("dflash2"),
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
    natives = [{"row": r, "sidecar_path": str(path), "attestation_present": _rows_present(r, path)} for r in rows]
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


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "SCHEMA", "SIDECAR_NAME", "KPF18_SUB_ARMS", "is_sub_arm",
           "native_rows", "project", "validate_row", "frames_for_sidecar"]
