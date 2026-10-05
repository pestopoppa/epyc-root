"""The contention-matrix instance `label` must name the instance's SHAPE.

`label` is a derived convenience field: `regions` / `cpu_list` / `threads` are
ground truth and the label must never contradict them.  It is the field a human
reads when judging whether a measured pair is comparable to a live placement, so
calling a HALF a "quarter" is not cosmetic — `src/scheduling/contention.py`
documents the same role pair as 0.37 BLOCK on overlapping half primaries and
1.716 ALLOW on disjoint siblings.

The pre-fix generator derived it from the instance INDEX
(`"full" if idx == 0 else f"q{idx - 1}"`), so after the 2026-07-30 quarter
retirement — live lineup = one full + two halves — every half was labelled a
quarter, and a role whose primary is itself a half was labelled "full".

Two discriminators were tried and rejected before regions:
  * instance index — the defect itself.
  * thread ratio — `threads` counts LOGICAL cpus including SMT siblings, so a
    48-thread quarter (24 cores x 2 SMT) and a 48-thread half are both 0.5 of a
    96-thread full.  See `test_thread_count_cannot_discriminate_half_from_quarter`.

The tests below pin the shapes, the visible fallback, AND the WIRING — that
`_instance_record` and the within-role bench actually delegate to the shared
helper.  A shape-only test suite stays green when the generator is reverted to
the hardcoded rule, which is exactly how an earlier attempt at this fix let its
own mutation survive.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

from scripts.server import contention_matrix as matrix_tool
from src.runtime import instance_topology
from src.runtime.instance_topology import canonical_shape_for_regions, cpu_list_to_regions

REPO_ROOT = Path(__file__).resolve().parents[2]
SHIPPED_MATRIX = REPO_ROOT / "orchestration" / "contention_matrix.yaml"


def _config() -> dict:
    """A role lineup covering every shape class the labeller must distinguish.

    `shapes` — the retired v7 quarter lineup: idx 0 full, idx 1..4 genuine
    single-region quarters.
    `halves` — the live post-2026-07-30 lineup: idx 0 full, idx 1..2 halves.
    `half_primary` — a role whose PRIMARY (idx 0) is a half, not a full.
    `exotic` — footprints outside the canonical seven: a cross-node span, a
    three-region span, and a GPU role's HT-only host lane (no CPU regions).
    """
    return {
        "shapes": {
            "instances": [
                ("0-95", 8072, 96),
                ("0-23,96-119", 8082, 48),
                ("24-47,120-143", 8182, 48),
                ("48-71,144-167", 8282, 48),
                ("72-95,168-191", 8382, 48),
            ]
        },
        "halves": {
            "instances": [
                ("0-95", 8070, 96),
                ("0-47,96-143", 8080, 48),
                ("48-95,144-191", 8180, 48),
            ]
        },
        "half_primary": {
            "instances": [
                ("0-47,96-143", 8085, 48),
                ("48-95,144-191", 8185, 48),
            ]
        },
        "exotic": {
            "instances": [
                ("184-191", 8083, 8),          # GPU host lane: no CPU regions
                ("0-23,48-71", 8183, 48),      # cross-node span q0+q2
                ("0-71", 8283, 72),            # three-region span q0+q1+q2
            ]
        },
    }


def _label(cfg: dict, role: str, idx: int) -> str:
    """Build the real instance record the generator would emit for (role, idx)."""
    cpu_list, port, _threads = cfg[role]["instances"][idx]
    record = matrix_tool._instance_record(
        role, idx, port, cpu_list_to_regions(cpu_list), cfg
    )
    return record["label"]


# ── The shapes themselves ───────────────────────────────────────────────


def test_half_footprints_are_labelled_half_not_quarter() -> None:
    """The live lineup's two halves. Pre-fix these were "q0"/"q1"."""
    cfg = _config()

    assert _label(cfg, "halves", 1) == "half0"   # cpus 0-47   -> regions q0+q1
    assert _label(cfg, "halves", 2) == "half1"   # cpus 48-95  -> regions q2+q3


def test_primary_instance_that_is_a_half_is_not_labelled_full() -> None:
    """idx 0 is not automatically the whole machine.

    frontdoor's primary is the node0 half (0-47); the old rule called it "full".
    """
    cfg = _config()

    assert _label(cfg, "half_primary", 0) == "half0"
    assert _label(cfg, "half_primary", 1) == "half1"


def test_genuine_quarter_is_still_labelled_q() -> None:
    """A one-region instance really is a quarter — the `q` label stays."""
    cfg = _config()

    assert _label(cfg, "shapes", 1) == "q0"
    assert _label(cfg, "shapes", 2) == "q1"
    assert _label(cfg, "shapes", 3) == "q2"
    assert _label(cfg, "shapes", 4) == "q3"


def test_whole_machine_is_labelled_full() -> None:
    cfg = _config()

    assert _label(cfg, "shapes", 0) == "full"
    assert _label(cfg, "halves", 0) == "full"


def test_unrecognised_footprint_is_visibly_named_not_silently_shaped() -> None:
    """No canonical shape -> `inst<idx>`, which asserts nothing about geometry.

    Includes the empty region set: a GPU role's HT-only host lane (cpus
    184-191, 8 threads) holds no CPU regions at all and must not be called
    "full".
    """
    cfg = _config()

    assert _label(cfg, "exotic", 0) == "inst0"   # no CPU regions
    assert _label(cfg, "exotic", 1) == "inst1"   # q0+q2, cross-node
    assert _label(cfg, "exotic", 2) == "inst2"   # q0+q1+q2, three regions


def test_thread_count_cannot_discriminate_half_from_quarter() -> None:
    """Why the region set, and not a thread ratio, is the discriminator.

    A quarter and a half both report 48 logical threads against a 96-thread
    full, because `threads` counts SMT siblings. Same number, different shape.
    """
    cfg = _config()
    quarter = cfg["shapes"]["instances"][1]
    half = cfg["halves"]["instances"][1]

    assert quarter[2] == half[2] == 48
    assert _label(cfg, "shapes", 1) == "q0"
    assert _label(cfg, "halves", 1) == "half0"


# ── The wiring ──────────────────────────────────────────────────────────


def test_instance_record_delegates_labelling_to_the_canonical_shape_helper(
    monkeypatch,
) -> None:
    """`_instance_record` must CALL the helper, not re-derive a label inline.

    Patching the helper at its source module and watching the emitted label
    change is what kills a revert to the hardcoded `f"q{idx - 1}"`: an
    inlined rule ignores the patch and the label comes back "q0".
    """
    cfg = _config()
    seen: list[frozenset] = []

    def _sentinel(regions):
        seen.append(frozenset(regions or ()))
        return "SHAPE-FROM-HELPER"

    monkeypatch.setattr(
        instance_topology, "canonical_shape_for_regions", _sentinel
    )

    record = matrix_tool._instance_record(
        "halves", 1, 8080, cpu_list_to_regions("0-47,96-143"), cfg
    )

    assert record["label"] == "SHAPE-FROM-HELPER"
    assert seen == [frozenset({"q0", "q1"})], "helper was not called with the record's regions"


def test_instance_record_falls_back_visibly_when_the_helper_declines(
    monkeypatch,
) -> None:
    """Helper returns None for a non-canonical footprint -> caller shows `inst<idx>`."""
    cfg = _config()
    monkeypatch.setattr(
        instance_topology, "canonical_shape_for_regions", lambda regions: None
    )

    record = matrix_tool._instance_record(
        "shapes", 3, 8282, cpu_list_to_regions("48-71,144-167"), cfg
    )

    assert record["label"] == "inst3"


def test_within_role_bench_labels_pairs_by_shape(tmp_path: Path, monkeypatch) -> None:
    """The second generator site (`cmd_bench_within_role`) carries the same rule.

    It emits `same_role.instance_pairs` keyed by instance label; before the fix
    it used its own copy of `"full" if idx == 0 else f"q{idx - 1}"`, so the one
    disjoint pair of the live lineup (the two halves) came out as `q0`+`q1`.
    """
    from src.scheduling import contention as contention_mod

    cfg = _config()
    monkeypatch.setattr("stack_numa.NUMA_CONFIG", cfg)
    monkeypatch.setattr(contention_mod, "load_contention_matrix", lambda _path: None)
    monkeypatch.setattr(
        contention_mod, "topology_fingerprint_for_matrix", lambda _cfg, _m: "live"
    )
    monkeypatch.setattr(
        contention_mod, "role_topology_fingerprint", lambda *a, **k: "role-hash"
    )
    monkeypatch.setattr(
        contention_mod, "matrix_status", lambda _p, current_topology_hash="": contention_mod.MatrixStatus.OK
    )
    monkeypatch.setattr(
        matrix_tool,
        "_bench_nway",
        lambda members, samples=1, safe_sampling=False: {
            "ratio": 1.5,
            "cv": 0.01,
            "verdict": "allow",
            "seq_aggregate_tps": 10.0,
            "parallel_aggregate_tps": 15.0,
        },
    )

    rc = matrix_tool.cmd_bench_within_role(
        SimpleNamespace(
            roles=["halves"],
            live_only=False,
            samples=1,
            safe_sampling=False,
            output=str(tmp_path),
            allow_stale_matrix=True,
        )
    )

    assert rc == 0
    results = json.loads((tmp_path / "j5_within_role_results.json").read_text())
    pairs = results["same_role_instance_pairs"]["halves"]
    # full overlaps both halves, so the only disjoint pair is half0 + half1.
    assert [(p["a"], p["b"]) for p in pairs] == [("half0", "half1")]


# ── The shipped artifact ────────────────────────────────────────────────


def test_shipped_matrix_labels_agree_with_their_own_geometry() -> None:
    """Every stored label must be the shape its own `regions` field implies.

    `regions`/`cpu_list`/`threads` were never wrong; only the derived label
    was. This is the invariant that failed for 25 label tokens (12 halves
    called `q0`, 3 called `q1`, 10 region-less GPU host lanes called `full`).
    """
    text = SHIPPED_MATRIX.read_text(encoding="utf-8")
    records = [
        json.loads(m.group(1))
        for m in re.finditer(r"^    instance_[ab]: (\{.*\})$", text, flags=re.M)
    ]

    assert records, "no instance records found — the parse, not the file, is the bug"

    mismatches = [
        (r["role"], r["instance_idx"], r["cpu_list"], r["regions"], r["label"])
        for r in records
        if r["label"]
        != (canonical_shape_for_regions(r["regions"]) or f"inst{r['instance_idx']}")
    ]

    assert not mismatches, f"labels contradict their own geometry: {mismatches}"


def test_shipped_matrix_has_no_quarter_labels_on_multi_region_instances() -> None:
    """The specific defect, stated directly: no `qN` label spanning >1 region."""
    text = SHIPPED_MATRIX.read_text(encoding="utf-8")
    records = [
        json.loads(m.group(1))
        for m in re.finditer(r"^    instance_[ab]: (\{.*\})$", text, flags=re.M)
    ]

    offenders = [
        (r["role"], r["instance_idx"], r["label"], r["regions"])
        for r in records
        if re.fullmatch(r"q\d", str(r["label"])) and len(r["regions"]) != 1
    ]

    assert not offenders, f"multi-region instances labelled as quarters: {offenders}"


# ── The helper's own contract ───────────────────────────────────────────


def test_canonical_shape_helper_covers_the_seven_shapes_and_declines_the_rest() -> None:
    assert canonical_shape_for_regions({"q0", "q1", "q2", "q3"}) == "full"
    assert canonical_shape_for_regions({"q0", "q1"}) == "half0"
    assert canonical_shape_for_regions({"q2", "q3"}) == "half1"
    for q in ("q0", "q1", "q2", "q3"):
        assert canonical_shape_for_regions({q}) == q
    # Not canonical shapes — the caller, not the helper, decides how to show these.
    assert canonical_shape_for_regions({"q0", "q2"}) is None
    assert canonical_shape_for_regions({"q1", "q2"}) is None
    assert canonical_shape_for_regions({"q0", "q1", "q2"}) is None
    assert canonical_shape_for_regions(frozenset()) is None
    assert canonical_shape_for_regions(None) is None


def test_canonical_shape_helper_accepts_any_region_container() -> None:
    """Records carry `regions` as a sorted LIST; live topology uses frozensets."""
    assert canonical_shape_for_regions(["q0", "q1"]) == "half0"
    assert canonical_shape_for_regions(("q2", "q3")) == "half1"
    assert canonical_shape_for_regions(frozenset({"q0", "q1", "q2", "q3"})) == "full"
