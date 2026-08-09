#!/usr/bin/env python3
"""Vidya pilot CLI.

Spec: docs/design/vidya-pilot-spec.md §15.2 (pilot commands), §11 (ledger and checkpoints).

    vidya append     <frame.json>      append a frame to the ledger
    vidya fold       [--as-of TS]      fold the ledger and print derived belief state
    vidya checkpoint [--emit]          compute (and optionally publish) an L1 checkpoint
    vidya verify                       verify the chain, and the checkpoint history if present
    vidya ingest     intake [--limit]  run the research-intake adapter (read-only source)

Every command prints the ledger frontier and the fold/policy versions it used, because an answer
without its frontier is not reproducible. Every command is machine-readable with --json.

Shadow-only: nothing here writes outside `.vidya/`, and nothing gates any production decision.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import checkpoint as cp  # noqa: E402
from canonical import content_hash  # noqa: E402
from fold import fold  # noqa: E402
from frames import validate_frame  # noqa: E402
from lattice import parse_grade  # noqa: E402
from ledger import Ledger  # noqa: E402

FOLD_VERSION = "vidya-pilot-0.1.0"
DEFAULT_ORIGIN = "epyc.local/belief-ledger"
REPO_ROOT = Path(__file__).resolve().parents[2]
VIDYA_DIR = REPO_ROOT / ".vidya"
LEDGER_PATH = VIDYA_DIR / "ledger.jsonl"
CHECKPOINT_DIR = VIDYA_DIR / "checkpoints"


def _ledger_path(args) -> Path:
    return Path(args.ledger) if args.ledger else LEDGER_PATH


def _checkpoint_dir(args) -> Path:
    """Checkpoints belong to THEIR ledger, not to a fixed location.

    Deriving this from the ledger path rather than a module constant is not cosmetic: a verify run
    that reads a global checkpoint directory while pointed at a different ledger will compare a
    checkpoint against a log it never attested to, and correctly-but-uselessly report truncation.
    (Caught by the CLI end-to-end test, which ran a five-frame temp ledger against the repo's
    9,449-entry checkpoint.)
    """
    return _ledger_path(args).parent / "checkpoints"


def _ledger(args) -> Ledger:
    return Ledger(_ledger_path(args))


def _emit(payload: dict, as_json: bool, human: str) -> int:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(human)
    return 0


# ------------------------------------------------------------------ append

def cmd_append(args) -> int:
    frame = json.loads(Path(args.frame).read_text())
    validate_frame(frame)
    led = _ledger(args)
    rec = led.append(frame)
    return _emit(
        {"seq": rec.seq, "frame_hash": rec.frame_hash, "frame_id": frame.get("frame_id")},
        args.json,
        f"appended seq={rec.seq} frame_hash={rec.frame_hash}",
    )


# -------------------------------------------------------------------- fold

def cmd_fold(args) -> int:
    led = _ledger(args)
    repair: list[str] = []
    records = led.read_all(repair_report=repair)
    result = fold([r.frame for r in records], as_of=args.as_of)
    floor = parse_grade(args.floor) if args.floor else None

    payload = {
        "frontier": result.frontier,
        "as_of": result.as_of,
        "fold_version": FOLD_VERSION,
        "state_hash": result.state_hash(),
        "iterations": result.iterations,
        "beliefs": [result.beliefs[c].as_dict(floor) for c in sorted(result.beliefs)],
        "ignored_frame_types": result.ignored_frame_types,
        "counted_judgments": len(result.counted_judgments),
        "superseded_judgments": len(result.superseded_judgments),
    }
    if repair:
        payload["ledger_repairs"] = repair

    lines = [
        f"frontier={result.frontier}  as_of={result.as_of}  fold={FOLD_VERSION}",
        f"state_hash={result.state_hash()}",
        f"beliefs={len(result.beliefs)}  iterations={result.iterations}"
        + (f"  floor={floor}" if floor else ""),
    ]
    for cid in sorted(result.beliefs):
        b = result.beliefs[cid]
        verdict = f"  {b.verdict(floor)}" if floor else ""
        wit = f"  witnesses={','.join(b.pro_witnesses)}" if b.pro_witnesses else ""
        lines.append(f"  {cid}: pro={b.pro} con={b.con}{verdict}{wit}")
    if repair:
        lines.extend(f"  REPAIR: {r}" for r in repair)
    return _emit(payload, args.json, "\n".join(lines))


# -------------------------------------------------------------- checkpoint

def cmd_checkpoint(args) -> int:
    led = _ledger(args)
    records = led.read_all()
    hashes = [r.frame_hash for r in records]
    chk = cp.checkpoint_for(args.origin, hashes)
    note = cp.format_checkpoint(chk)

    payload = {
        "origin": chk.origin,
        "tree_size": chk.tree_size,
        "root_hash": chk.root_hash.hex(),
        "note": note,
    }

    ckdir = _checkpoint_dir(args)
    if args.emit:
        ckdir.mkdir(parents=True, exist_ok=True)
        out = ckdir / f"checkpoint-{chk.tree_size:08d}.txt"
        # Consistency against the previous checkpoint is what proves the log never rewrote
        # history. A signature alone would not: it attests to the current tree, not to the tree
        # being an extension of the one we trusted before.
        prior = sorted(ckdir.glob("checkpoint-*.txt"))
        if prior:
            prev_chk, _ = cp.parse_checkpoint(prior[-1].read_text())
            if prev_chk.tree_size > chk.tree_size:
                print(
                    f"REFUSING: previous checkpoint covers {prev_chk.tree_size} entries but the "
                    f"ledger now has {chk.tree_size}. A shrinking log is a rewrite.",
                    file=sys.stderr,
                )
                return 1
            if prev_chk.tree_size > 0:
                leaves = [h.encode("utf-8") for h in hashes]
                proof = cp.consistency_proof(leaves, prev_chk.tree_size)
                payload["consistency_proof_len"] = len(proof)
                payload["consistent_with"] = prev_chk.tree_size
        out.write_text(note)
        try:
            payload["written"] = str(out.relative_to(REPO_ROOT))
        except ValueError:
            payload["written"] = str(out)

    human = (
        f"origin={chk.origin} tree_size={chk.tree_size}\n"
        f"root={chk.root_hash.hex()}\n"
        + (f"written={payload.get('written')}" if args.emit else "(not written; pass --emit)")
    )
    return _emit(payload, args.json, human)


# ------------------------------------------------------------------ verify

def cmd_verify(args) -> int:
    led = _ledger(args)
    # Chain problems and checkpoint problems are reported on SEPARATE keys. Folding them into one
    # flag misdiagnoses: a caller reading `chain_ok` for a checkpoint mismatch would conclude the
    # ledger file was corrupt when in fact it is internally consistent and simply not the history
    # that was published. That distinction IS the L1 rung -- a rewriter who recomputes the chain
    # leaves L0 pristine, and only the externally-held checkpoint catches them.
    chain_problems = led.verify()
    checkpoint_problems: list[str] = []
    records = led.read_all()
    hashes = [r.frame_hash for r in records]

    checkpoint_results = []
    ckdir = _checkpoint_dir(args)
    if ckdir.exists():
        leaves = [h.encode("utf-8") for h in hashes]
        for path in sorted(ckdir.glob("checkpoint-*.txt")):
            chk, _sigs = cp.parse_checkpoint(path.read_text())
            if chk.tree_size > len(leaves):
                checkpoint_problems.append(
                    f"{path.name}: covers {chk.tree_size} entries but the ledger has "
                    f"{len(leaves)} — history was truncated"
                )
                continue
            recomputed = cp.merkle_root(leaves[: chk.tree_size])
            ok = recomputed == chk.root_hash
            if not ok:
                checkpoint_problems.append(
                    f"{path.name}: root mismatch at tree_size={chk.tree_size} — the ledger prefix "
                    "this checkpoint attested to has been altered"
                )
            checkpoint_results.append({"file": path.name, "tree_size": chk.tree_size, "ok": ok})

    all_problems = chain_problems + checkpoint_problems
    payload = {
        "frontier": len(records),
        "chain_ok": not chain_problems,
        "checkpoints_ok": not checkpoint_problems,
        "ok": not all_problems,
        "chain_problems": chain_problems,
        "checkpoint_problems": checkpoint_problems,
        "checkpoints": checkpoint_results,
    }
    human = (
        f"frontier={len(records)}  chain={'OK' if not chain_problems else 'FAILED'}  "
        f"checkpoints={'OK' if not checkpoint_problems else 'FAILED'}\n"
        + "\n".join(
            f"  checkpoint {c['file']} @{c['tree_size']}: {'OK' if c['ok'] else 'MISMATCH'}"
            for c in checkpoint_results
        )
        + ("\n" + "\n".join(f"  PROBLEM: {p}" for p in all_problems) if all_problems else "")
    )
    _emit(payload, args.json, human)
    return 0 if not all_problems else 1


# ------------------------------------------------------------------ ingest

def cmd_ingest(args) -> int:
    if args.adapter != "intake":
        print(f"unknown adapter {args.adapter!r}", file=sys.stderr)
        return 2
    from adapters.research_intake import ingest_intake_index  # noqa: PLC0415

    led = _ledger(args)
    report = ingest_intake_index(
        led,
        index_path=Path(args.index) if args.index else REPO_ROOT / "research" / "intake_index.yaml",
        limit=args.limit,
        dry_run=args.dry_run,
        as_of=args.as_of,
    )
    human = [
        f"entries read={report['entries_read']}  frames={'(dry run) ' if args.dry_run else ''}"
        f"{report['frames_emitted']}",
        f"grade distribution: {report['grade_distribution']}",
        f"ceiling: {report['ceiling_note']}",
    ]
    return _emit(report, args.json, "\n".join(human))


# -------------------------------------------------------------------- main

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="vidya", description=__doc__.splitlines()[0])
    p.add_argument("--ledger", help=f"ledger path (default {LEDGER_PATH})")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("append", help="append a frame from a JSON file")
    a.add_argument("frame")
    a.set_defaults(func=cmd_append)

    f = sub.add_parser("fold", help="fold the ledger into belief state")
    f.add_argument("--as-of", required=True, help="explicit evaluation time (never defaulted)")
    f.add_argument("--floor", help="policy floor, e.g. 'Verified/Anchored'")
    f.set_defaults(func=cmd_fold)

    c = sub.add_parser("checkpoint", help="compute an L1 checkpoint over the ledger")
    c.add_argument("--origin", default=DEFAULT_ORIGIN)
    c.add_argument("--emit", action="store_true", help="write it under .vidya/checkpoints/")
    c.set_defaults(func=cmd_checkpoint)

    v = sub.add_parser("verify", help="verify the chain and any published checkpoints")
    v.set_defaults(func=cmd_verify)

    i = sub.add_parser("ingest", help="run a source adapter")
    i.add_argument("adapter", choices=["intake"])
    i.add_argument("--index", help="path to intake_index.yaml")
    i.add_argument("--limit", type=int, help="only the first N entries")
    i.add_argument("--as-of", required=True, help="explicit ingest timestamp")
    i.add_argument("--dry-run", action="store_true", help="report without appending")
    i.set_defaults(func=cmd_ingest)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
