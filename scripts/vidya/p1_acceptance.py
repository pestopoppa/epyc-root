#!/usr/bin/env python3
"""Belief-redesign Phase-1 acceptance checks AC1-AC5, AC7-AC9, run against a LEDGER COPY.

Read-only. It never writes a ledger, a known-good snapshot or an alarm: instead of `prepare()`
(which writes both) it runs the same read path `prepare()` runs once the ledger is current --
`Ledger.verify()` -> `read_all()` -> ONE `fold()` -> `loop_beliefs.evaluate_frames()` per target,
with the default caps -- plus `loop_beliefs.collect()` on the same fold to count what the caps
hide. Freshness/sync is deliberately not exercised (it would ingest into the copy).

  AC1  DS41-Q4 cpu: >=20 target-tier claims with value+unit+n; >=5 negative outcomes
       (regressed/null/refused) with mechanism ids; tried index >=60 mechanisms.
  AC2  DS41-1017 cpu: target tier 0 with the empty-target banner; >=8 sibling-tier DS41-Q4 lines
       labelled "transfer unproven"; <=3 host lines.
  AC3  Q38FN UD-IQ4_XS cpu: >=15 target-tier value-bearing claims; tried index >=35 mechanisms.
  AC4  Qwen3.8-27B-Q8_0 gpu: >=3 target-tier claims, including the serving floor (81.1 t/s,
       floor 0.81%, n=10) and 2 mechanisms refused by the correctness gate ("MUL_MAT failed on
       ROCm0").
  AC5  (amended 2026-10-21, after the rehearsal backfill) the five CPU models' usable sets are
       PAIRWISE distinct; Qwen3-VL-30B has target tier 0 with the banner; Qwen3.6-35B-A3B's
       target-tier claims, if any, all come from sources scoped to that model (their model_file
       is the target's) -- their source kinds are reported. The original "35B target tier 0"
       predated the KPF-18 35B CPU item-7 claims (lane K), which are real 35B beliefs.
  AC7  (needs --before) every claim in the pre-backfill copy keeps its grade, verdict and gate
       outcome; the pre-backfill frames are an unchanged prefix of the post-backfill copy.
       Adapter-fixture frame ids are pinned by tests/vidya/test_claim_tuple.py (lane A), not here.
  AC9  (belief redesign §12.7, as decided 2026-10-21) role architect_critic (27B gpu; spec_draft,
       kv_profile, routing): PB-HOL-1 AND the 27B KPF-18 item-7 claims each appear on the knob OR
       target tier, shown with their value lines (they are `slot_serving`, so target tier is
       expected; the tier is reported); role frontdoor (Qwen3.6-35B cpu): the 35B KPF-18 item-7
       arms likewise; the lineup target (--stack-regime) returns "No beliefs at this regime"
       until the first post-restart trial.
  AC8  10 random mechanism ids from the DS41 and Q38FN experiments.db stores each appear in the
       answer (detailed line, section index or answer `tried_index`) with an outcome. The pool is
       the mechanisms with at least one row the experiments adapter projects (its own `classify`;
       amended 2026-10-24: status alone admitted scope-gate refusals the adapter never projects).

AC6 (planner-prompt render through both consumers, warm p95) is not in scope of this script.

Usage:
  python3 scripts/vidya/p1_acceptance.py --ledger /mnt/raid0/llm/tmp/.../ledger.copy.jsonl \
      [--before /mnt/raid0/llm/tmp/.../ledger.pre-backfill.jsonl] [--as-of 2026-10-22T08:00:00Z] \
      [--store DS41=<store dir> ...] [--seed 20261022] [--json]
Exit: 0 every check run passed, 1 a check failed, 2 usage/refusal.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import loop_beliefs as lb  # noqa: E402
from fold import fold  # noqa: E402
from gate import evaluate  # noqa: E402
from ledger import Ledger  # noqa: E402

MODELS = Path("/mnt/raid0/llm/models")
TARGETS: dict[str, dict[str, Any]] = {
    # quant values are what the consumers send today (AutoKernel census quant for DS41-Q4,
    # AutoPilot stack_priors quants); override with --quant NAME=Q.
    "DS41-Q4": {"model_path": str(MODELS / "antirez/deepseek-v4.1-flash-gguf/"
                                  "DeepSeek-V4.1-Flash-Q4.gguf"), "quant": "Q8_0",
                "backend": "cpu"},
    "DS41-1017": {"model_path": str(MODELS / "antirez/deepseek-v4.1-flash-gguf/"
                                    "DeepSeek-V4.1-Flash-1017-MXFP4-experts-00001-of-00009.gguf"),
                  "quant": "", "backend": "cpu"},
    "Q38FN": {"model_path": str(MODELS / "unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/"
                                "Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf"),
              "quant": "UD-IQ4_XS", "backend": "cpu"},
    "27B": {"model_path": str(MODELS / "Qwen3.8-27B-Q8_0.gguf"), "quant": "Q8_0",
            "backend": "gpu"},
    "Qwen3.6-35B": {"model_path": str(MODELS / "Qwen3.6-35B-A3B-MTP-Q8_0.gguf"),
                    "quant": "Q8_0", "backend": "cpu"},
    "Qwen3-VL-30B": {"model_path": str(MODELS / "lmstudio-community/"
                                       "Qwen3-VL-30B-A3B-Instruct-GGUF/"
                                       "Qwen3-VL-30B-A3B-Instruct-Q4_K_M.gguf"),
                     "quant": "Q4_K_M", "backend": "cpu"},
}
ROLE_TARGETS: dict[str, dict[str, Any]] = {
    "architect_critic": {**TARGETS["27B"], "role": "architect_critic",
                         "label": "role:architect_critic",
                         "knob_families": ["spec_draft", "kv_profile", "routing"]},
    "frontdoor": {**TARGETS["Qwen3.6-35B"], "role": "frontdoor", "label": "role:frontdoor",
                  "knob_families": ["spec_draft", "kv_profile"]},
}
PBHOL_RE = re.compile(r"pb.?hol", re.I)
KPF_RE = re.compile(r"kpf.?18|prefix.?fork", re.I)
ITEM7_RE = re.compile(r"item.?7|kpf18-run-c", re.I)
CPU_FIVE = ("DS41-Q4", "DS41-1017", "Q38FN", "Qwen3.6-35B", "Qwen3-VL-30B")
CAMPAIGNS = Path("/mnt/raid0/llm/autokernel/campaigns")
DEFAULT_STORES = {
    "DS41": [CAMPAIGNS / "ak-ds41-cpu-decode-20260923/store",
             CAMPAIGNS / "ak-ds41-cpu-decode-20260923/store-b0ba1d427"],
    "Q38FN": [CAMPAIGNS / "ak-q38fn-cpu-decode-20261003/store-b0ba1d427"],
}
STORE_TARGET = {"DS41": "DS41-Q4", "Q38FN": "Q38FN"}
#: experiments.db statuses the experiments adapter projects as mechanism outcomes (DESIGN §5.1;
#: anchor_verified/runtime_observed are BASELINE records, not mechanisms tried).
PROJECTED_STATUSES = ("kept", "keep_candidate", "measured_null", "regression",
                      "measured_serving_gate", "gate_refused", "integrity_refused",
                      "measured_divergence")
NEGATIVE = ("regressed", "null", "refused_correctness", "refused_scope")
FLOOR_27B = {"value": 81.12, "floor_rel": 0.00807, "n": 10}


def _check(name: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"check": name, "pass": bool(ok), "detail": detail}


def _tier_rows(col: dict[str, Any], tier: str = "target") -> list[dict[str, Any]]:
    every = col["rows"] + [r for b in lb.FLAG_BUCKETS for r in col["flagged"][b]]
    return [r for r in every if r["tier"] == tier]


def _value_bearing(row: dict[str, Any]) -> bool:
    return (row["value"] is not None and bool(row["unit"])
            and bool(row["n_pairs"] or row["reps"]))


def _tried(ev: dict[str, Any], tier: str, model_file: str) -> list[dict[str, Any]]:
    return [e for e in ev["tried_index"] if e["tier"] == tier and e["model_file"] == model_file]


def _section_lines(ev: dict[str, Any]) -> list[str]:
    return ev["section"].splitlines()


def _host_lines(ev: dict[str, Any]) -> int:
    lines, inside = _section_lines(ev), False
    count = 0
    for line in lines:
        if line.startswith("### "):
            inside = line.startswith("### Host tier")
            continue
        if inside and line.startswith("- "):
            count += 1
    return count


class Reader:
    def __init__(self, ledger: Path, as_of: str, quant: dict[str, str]):
        started = time.monotonic()
        self.ledger_path = Path(ledger)
        led = Ledger(ledger)
        errors = led.verify()
        if errors:
            raise SystemExit(f"ledger copy does not verify: {errors[0]}")
        self.frames = [record.frame for record in led.read_all()]
        self.as_of = as_of
        self.result = fold(lb.visible_frames(self.frames, as_of), as_of=as_of)
        self.fold_seconds = round(time.monotonic() - started, 1)
        self.quant = quant
        self.cache: dict[tuple[str, str | None], tuple[dict, dict]] = {}

    def target(self, name: str, quant: str | None = None) -> lb.Target:
        raw = dict(TARGETS[name])
        raw["quant"] = self.quant.get(name, raw["quant"]) if quant is None else quant
        return lb.Target.from_mapping(raw)

    def read(self, name: str, quant: str | None = None) -> tuple[dict, dict]:
        key = (name, quant)
        if key not in self.cache:
            target = self.target(name, quant)
            ev = lb.evaluate_frames(self.frames, [target], as_of=self.as_of,
                                    fold_result=self.result)
            col = lb.collect(self.frames, [target], as_of=self.as_of, fold_result=self.result)
            self.cache[key] = (ev, col)
        return self.cache[key]

    def quant_note(self, name: str) -> str:
        """Diagnostic only: the target-tier count with quant unstated, when it differs."""
        if not self.target(name).quant:
            return ""
        strict = len(_tier_rows(self.read(name)[1]))
        loose = len(_tier_rows(self.read(name, quant="")[1]))
        return "" if strict == loose else f" [quant-sensitivity: {loose} with quant unstated]"


def ac1(r: Reader) -> dict[str, Any]:
    ev, col = r.read("DS41-Q4")
    rows = _tier_rows(col)
    valued = [x for x in rows if _value_bearing(x)]
    negative = {x["claim_id"] for x in rows if x["outcome"] in NEGATIVE and x["mechanism_id"]}
    model = r.target("DS41-Q4").model_file
    tried = _tried(ev, "target", model)
    ok = len(valued) >= 20 and len(negative) >= 5 and len(tried) >= 60
    return _check("AC1", ok, f"DS41-Q4 target tier {len(rows)} ({len(valued)} value-bearing, "
                             f"need 20); negative outcomes with mechanism {len(negative)} (need 5)"
                             f"; tried index {len(tried)} (need 60); section "
                             f"{ev['section_bytes']} B{r.quant_note('DS41-Q4')}")


def ac2(r: Reader) -> dict[str, Any]:
    ev, _ = r.read("DS41-1017")
    q4 = r.target("DS41-Q4").model_file
    lines = _section_lines(ev)
    banner_first = (len(lines) > 1 and lines[0] == lb.SECTION_HEADER and bool(ev["banner"])
                    and lines[1] == ev["banner"])
    sibling = [ln for ln in lines if ln.startswith("- ") and "transfer unproven" in ln
               and f"measured on {q4}" in ln]
    hosts = _host_lines(ev)
    ok = ev["tiers"]["target"] == 0 and banner_first and len(sibling) >= 8 and hosts <= 3
    return _check("AC2", ok, f"DS41-1017 target tier {ev['tiers']['target']} (need 0); banner "
                             f"first {banner_first}; sibling DS41-Q4 lines {len(sibling)} (need 8)"
                             f"; host lines {hosts} (max 3); section {ev['section_bytes']} B")


def ac3(r: Reader) -> dict[str, Any]:
    ev, col = r.read("Q38FN")
    rows = _tier_rows(col)
    valued = [x for x in rows if _value_bearing(x)]
    tried = _tried(ev, "target", r.target("Q38FN").model_file)
    ok = len(valued) >= 15 and len(tried) >= 35
    return _check("AC3", ok, f"Q38FN target tier {len(rows)} ({len(valued)} value-bearing, need "
                             f"15); tried index {len(tried)} (need 35); section "
                             f"{ev['section_bytes']} B{r.quant_note('Q38FN')}")


def ac4(r: Reader) -> dict[str, Any]:
    ev, col = r.read("27B")
    rows = _tier_rows(col)
    floors = [x for x in rows if x["outcome"] == "floor" and x["value"] is not None
              and abs(x["value"] - FLOOR_27B["value"]) < 0.06
              and x["noise_floor_rel"] is not None
              and abs(x["noise_floor_rel"] - FLOOR_27B["floor_rel"]) < 0.00006
              and FLOOR_27B["n"] in (x["reps"], x["n_pairs"])]
    refused = {x["mechanism_id"] for x in rows if x["outcome"] == "refused_correctness"
               and x["mechanism_id"]
               and "MUL_MAT failed on ROCm0" in (x["outcome_reason"] + " " + x["text"])}
    in_section = "81.12" in ev["section"] and "MUL_MAT failed on ROCm0" in ev["section"]
    ok = len(rows) >= 3 and bool(floors) and len(refused) >= 2 and in_section
    return _check("AC4", ok, f"27B target tier {len(rows)} (need 3); floor 81.1 t/s/0.81%/n=10 "
                             f"{'found' if floors else 'MISSING'}; correctness-refused mechanisms "
                             f"{sorted(refused)} (need 2); both in section {in_section}"
                             f"{r.quant_note('27B')}")


def ac5(r: Reader) -> dict[str, Any]:
    details, ok = [], True
    ev, _ = r.read("Qwen3-VL-30B")
    banner = bool(ev["banner"]) and (ev["section"] == "" or ev["banner"] in ev["section"])
    vl_ok = ev["tiers"]["target"] == 0 and banner
    ok &= vl_ok
    details.append(f"Qwen3-VL-30B: target {ev['tiers']['target']} (need 0), banner {banner}, "
                   f"usable {len(ev['claim_ids'])}")
    ev, col = r.read("Qwen3.6-35B")
    model = r.target("Qwen3.6-35B").model_file
    rows = _tier_rows(col)
    foreign = [x["claim_id"] for x in rows if x["model_file"] != model]
    kinds: dict[str, int] = {}
    for x in rows:
        kinds[x["source_kind"]] = kinds.get(x["source_kind"], 0) + 1
    ok &= not foreign
    details.append(f"Qwen3.6-35B: target {len(rows)}, all scoped to {model} {not foreign}"
                   + (f" (foreign: {foreign[:5]})" if foreign else "")
                   + f"; source kinds {dict(sorted(kinds.items())) or '{}'}; usable "
                   f"{len(ev['claim_ids'])}")
    usable = {name: frozenset(r.read(name)[0]["claim_ids"]) for name in CPU_FIVE}
    names = list(CPU_FIVE)
    same = [(a, b) for i, a in enumerate(names) for b in names[i + 1:] if usable[a] == usable[b]]
    ok &= not same
    details.append(f"usable sets pairwise distinct across the five CPU models {not same}"
                   + (f" (identical: {same})" if same else ""))
    return _check("AC5", ok, "; ".join(details))


def ac7(before_path: Path, r: Reader) -> dict[str, Any]:
    before_led = Ledger(before_path)
    errors = before_led.verify()
    if errors:
        return _check("AC7", False, f"pre-backfill copy does not verify: {errors[0]}")
    before_records = before_led.read_all()
    after_records = Ledger(r.ledger_path).read_all()
    prefix_ok, prefix_detail = True, ""
    if len(after_records) < len(before_records):
        prefix_ok, prefix_detail = False, "post-backfill copy is shorter than the pre copy"
    else:
        for old, new in zip(before_records, after_records):
            if old.frame_hash != new.frame_hash:
                prefix_ok = False
                prefix_detail = f"frame at seq {old.seq} differs"
                break
    before_frames = [record.frame for record in before_records]
    before = fold(lb.visible_frames(before_frames, r.as_of), as_of=r.as_of)
    policy = lb._policy()
    diffs = []
    for claim_id, belief in sorted(before.beliefs.items()):
        after_belief = r.result.beliefs.get(claim_id)
        if after_belief is None:
            diffs.append(f"{claim_id}: missing after backfill")
            continue
        old_gate, new_gate = evaluate(claim_id, before, policy), evaluate(claim_id, r.result,
                                                                          policy)
        old = (str(belief.pro), str(belief.con), belief.verdict(policy.floor), old_gate.outcome,
               tuple(old_gate.reasons))
        new = (str(after_belief.pro), str(after_belief.con), after_belief.verdict(policy.floor),
               new_gate.outcome, tuple(new_gate.reasons))
        if old != new:
            diffs.append(f"{claim_id}: {old[:4]} -> {new[:4]}")
    ok = prefix_ok and not diffs
    return _check("AC7", ok, f"{len(before.beliefs)} pre-existing claims, {len(diffs)} changed"
                             + (f" (first: {'; '.join(diffs[:5])})" if diffs else "")
                             + f"; pre frames are an unchanged prefix: {prefix_ok}"
                             + (f" ({prefix_detail})" if prefix_detail else "")
                             + "; adapter-fixture frame ids: tests/vidya/test_claim_tuple.py")


def _identity(row: dict[str, Any]) -> str:
    return " ".join(str(row.get(k) or "") for k in ("source_kind", "claim_id", "locator", "text"))


def _shown_value_rows(col: dict[str, Any], ev: dict[str, Any], pattern: re.Pattern[str],
                      item7: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(matching claims on the knob/target tiers, those of them shown with a value line)."""
    every = col["rows"] + [x for b in lb.FLAG_BUCKETS for x in col["flagged"][b]]
    hits = [x for x in every if x["tier"] in ("knob", "target")
            and pattern.search(_identity(x))
            and (not item7 or ITEM7_RE.search(_identity(x)))]
    shown = {cid for c in ev["claims"] for cid in [c["claim_id"], *c.get("linked_claim_ids", [])]}
    valued = [x for x in hits if x["value"] is not None and x["claim_id"] in shown]
    return hits, valued


def _tiers(rows: list[dict[str, Any]]) -> str:
    return ",".join(sorted({x["tier"] for x in rows})) or "none"


def ac9(r: Reader, stack_regime: str) -> dict[str, Any]:
    """KPF-18 and PB-HOL-1 are tagged `slot_serving` (stack topology, outside AutoPilot's action
    space), so they are expected on the knob OR target tier -- the tier is reported, not forced."""
    details, ok = [], True
    reads = {}
    for role, raw in ROLE_TARGETS.items():
        target = lb.Target.from_mapping(raw)
        reads[role] = (lb.collect(r.frames, [target], as_of=r.as_of, fold_result=r.result),
                       lb.evaluate_frames(r.frames, [target], as_of=r.as_of,
                                          fold_result=r.result))
    col, ev = reads["architect_critic"]
    pb_hits, pb_valued = _shown_value_rows(col, ev, PBHOL_RE, item7=False)
    kpf_hits, kpf_valued = _shown_value_rows(col, ev, KPF_RE, item7=True)
    ok &= bool(pb_valued) and bool(kpf_valued)
    details.append(f"architect_critic: PB-HOL-1 {len(pb_hits)} claim(s) on tier {_tiers(pb_hits)}"
                   f", {len(pb_valued)} shown with a value line; KPF-18 item 7 {len(kpf_hits)} on "
                   f"tier {_tiers(kpf_hits)}, {len(kpf_valued)} shown with a value line")
    col, ev = reads["frontdoor"]
    arms, arms_valued = _shown_value_rows(col, ev, KPF_RE, item7=True)
    ok &= bool(arms_valued)
    details.append(f"frontdoor: KPF-18 item-7 arms {len(arms)} on tier {_tiers(arms)}, "
                   f"{len(arms_valued)} shown with a value line")
    lineup = lb.Target.from_mapping({"scope": "lineup", "stack_regime": stack_regime,
                                     "knob_families": ["kv_compaction", "orchestrator"],
                                     "label": "lineup"})
    ev = lb.evaluate_frames(r.frames, [lineup], as_of=r.as_of, fold_result=r.result)
    if ev["tiers"]["lineup"]:
        details.append(f"lineup {stack_regime or 'unrecorded'}: {ev['tiers']['lineup']} "
                       "post-restart trial claim(s) present (banner no longer expected)")
    else:
        good = bool(ev["banner"]) and "No beliefs at this regime" in ev["banner"]
        ok &= good
        details.append(f"lineup {stack_regime or 'unrecorded'}: 0 claims, banner {good}")
    return _check("AC9", ok, "; ".join(details))


def _store_mechanisms(store: Path) -> dict[str, list[str]]:
    """mechanism_id -> statuses of the rows the experiments adapter actually PROJECTS.

    The pool is decided by the adapter's own `classify`, not by status alone: a `gate_refused` row
    whose refusing gate is a harness/scope verdict (e.g. `oracle_unavailable`) is never projected
    (`scope_gate`), so a mechanism tried only that way has nothing to find and must not be sampled
    (found 2026-10-24: Q38FN `akm-cpu-fa-sparse-mask-bitwalk`, three oracle_unavailable refusals).
    """
    from adapters import autokernel_experiments as exp  # noqa: PLC0415

    out: dict[str, list[str]] = {}
    for row in exp.native_rows(store):
        if row.get("status") not in PROJECTED_STATUSES:
            continue
        mechanism = row.get("mechanism_id")
        if not mechanism or row.get("payload") is None:
            continue
        disposition, _ = exp.classify(row)
        if disposition is None:
            continue
        out.setdefault(str(mechanism), []).append(str(row["status"]))
    return out


def ac8(r: Reader, stores: dict[str, list[Path]], seed: int, k: int = 10) -> dict[str, Any]:
    pool: dict[tuple[str, str], list[str]] = {}
    for family, paths in stores.items():
        for path in paths:
            if not (path / "experiments.db").is_file():
                return _check("AC8", False, f"store {path} has no experiments.db")
            for mechanism, statuses in _store_mechanisms(path).items():
                pool.setdefault((family, mechanism), []).extend(statuses)
    if len(pool) < k:
        return _check("AC8", False, f"only {len(pool)} projected mechanisms in the stores")
    sample = random.Random(seed).sample(sorted(pool), k)
    missing, found = [], []
    for family, mechanism in sample:
        ev, _ = r.read(STORE_TARGET[family])
        entry = next((e for e in ev["tried_index"] if e["mechanism_id"] == mechanism), None)
        detailed = any(c["mechanism_id"] == mechanism and c["outcome"] for c in ev["claims"])
        in_index = entry is not None and entry["outcome"] not in ("", "recorded")
        if detailed or in_index:
            found.append(f"{mechanism}={entry['outcome'] if entry else 'detailed'}"
                         f"{'' if entry is None or entry['in_section'] else '(json only)'}")
        else:
            missing.append(f"{family}:{mechanism} (store statuses "
                           f"{sorted(set(pool[(family, mechanism)]))})")
    return _check("AC8", not missing, f"seed {seed}: {len(found)}/{k} found ({', '.join(found)})"
                                      + (f"; MISSING: {'; '.join(missing)}" if missing else ""))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ledger", required=True, help="post-backfill ledger COPY")
    parser.add_argument("--before", default=None, help="pre-backfill ledger COPY (for AC7)")
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--quant", action="append", default=[], metavar="NAME=QUANT",
                        help=f"override a target's quant ({', '.join(TARGETS)})")
    parser.add_argument("--store", action="append", default=[], metavar="FAMILY=DIR",
                        help="AC8 store dir (DS41= or Q38FN=; repeatable; replaces defaults)")
    parser.add_argument("--seed", type=int, default=20261022)
    parser.add_argument("--stack-regime", default="",
                        help="AC9 lineup target's stack_regime (AP-55 infra_fingerprint digest)")
    parser.add_argument("--skip", action="append", default=[], help="check to skip, e.g. AC8")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    ledger = Path(args.ledger)
    paths = [ledger] + ([Path(args.before)] if args.before else [])
    canonical = lb.CANONICAL_LEDGER.resolve()
    for path in paths:
        if not path.is_file():
            print(f"refused: {path} is not a file", file=sys.stderr)
            return 2
        if path.resolve() == canonical:
            print(f"refused: {path} is the canonical ledger; run against a copy", file=sys.stderr)
            return 2
    quant = {}
    for item in args.quant:
        name, _, value = item.partition("=")
        if name not in TARGETS:
            print(f"unknown target {name!r}", file=sys.stderr)
            return 2
        quant[name] = value
    stores = DEFAULT_STORES
    if args.store:
        stores = {}
        for item in args.store:
            family, _, directory = item.partition("=")
            if family not in STORE_TARGET:
                print(f"unknown store family {family!r}", file=sys.stderr)
                return 2
            stores.setdefault(family, []).append(Path(directory))
    as_of = args.as_of or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    reader = Reader(ledger, as_of, quant)
    skip = {s.upper() for s in args.skip}
    results = []
    for name, fn in (("AC1", ac1), ("AC2", ac2), ("AC3", ac3), ("AC4", ac4), ("AC5", ac5)):
        if name not in skip:
            results.append(fn(reader))
    if "AC7" not in skip:
        results.append(ac7(Path(args.before), reader) if args.before
                       else _check("AC7", False, "not run: --before <pre-backfill copy> missing"))
    if "AC8" not in skip:
        results.append(ac8(reader, stores, args.seed))
    if "AC9" not in skip:
        results.append(ac9(reader, args.stack_regime))
    summary = {"ledger": str(ledger), "before": args.before, "as_of": as_of,
               "frames": len(reader.frames), "fold_seconds": reader.fold_seconds,
               "checks": results, "pass": all(r["pass"] for r in results)}
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f"ledger {ledger} ({len(reader.frames)} frames, fold {reader.fold_seconds} s, "
              f"as_of {as_of})")
        for row in results:
            print(f"{row['check']} {'PASS' if row['pass'] else 'FAIL'}  {row['detail']}")
        print("ALL PASS" if summary["pass"] else "SOME CHECKS FAILED")
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
