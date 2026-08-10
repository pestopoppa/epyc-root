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

FOLD_VERSION = "vidya-pilot-0.2.0"  # 0.2.0: belief state gained corrections/review_required (P2c)
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


# ------------------------------------------------------------------ impact

def cmd_impact(args) -> int:
    from impact import impact_of_retracting  # noqa: PLC0415

    led = _ledger(args)
    records = led.read_all()
    report = impact_of_retracting(
        [r.frame for r in records], args.frame_id, as_of=args.as_of
    ).as_dict()

    human = [
        f"retracting {len(report['retracted_frames'])} frame(s) at frontier {len(records)}",
        f"  affected           {report['affected_count']}"
        f"   (fragile: {report['fragile_count']})",
        f"  verified unaffected {report['verified_unaffected_count']}",
        f"  unaffected but unmapped {report['unaffected_but_unmapped_count']}"
        "   <- NOT a clean bill of health",
    ]
    for item in report["affected"][:20]:
        human.append(
            f"    {item['claim_id']}: {item['before']['pro']['Q']}/{item['before']['pro']['T']}"
            f" -> {item['after']['pro']['Q']}/{item['after']['pro']['T']}"
            f"  [{item['coverage']}]" + ("  FRAGILE" if item["fragile"] else "")
        )
    if report["affected_count"] > 20:
        human.append(f"    ... and {report['affected_count'] - 20} more")
    return _emit(report, args.json, "\n".join(human))


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


# ----------------------------------------------------------------- project

def cmd_project(args) -> int:
    import json as _json  # noqa: PLC0415

    from projection import (  # noqa: PLC0415
        SelectionPolicy, build_manifest, freshness_of, select_beliefs,
    )

    led = _ledger(args)
    result = fold([r.frame for r in led.read_all()], as_of=args.as_of)
    policy = SelectionPolicy(policy_id=args.policy_id, floor=parse_grade(args.floor))
    sel = select_beliefs(result, policy, claim_ids=args.claim or None)
    text, manifest = build_manifest(
        projection_id=args.projection_id, artifact_path=args.out or "(unwritten)",
        selection=sel, fold_result=result, policy=policy, fold_version=FOLD_VERSION)

    payload = {"manifest": manifest.as_dict(), "included": len(sel.included),
               "omitted": len(sel.omitted)}
    if args.out:
        art = Path(args.out)
        art.parent.mkdir(parents=True, exist_ok=True)
        art.write_text(text)
        side = _ledger_path(args).parent / "projections" / f"{args.projection_id}.json"
        side.parent.mkdir(parents=True, exist_ok=True)
        side.write_text(_json.dumps(manifest.as_dict(), indent=2, sort_keys=True))
        payload["artifact"] = str(art)
        payload["sidecar"] = str(side)
        state, reasons = freshness_of(manifest, result, artifact_text=text)
        payload["freshness"] = {"state": state, "reasons": reasons}

    human = [
        f"projection {args.projection_id}: included={len(sel.included)} omitted={len(sel.omitted)}",
        f"  policy={policy.policy_id} floor={policy.floor} digest={policy.digest()[:23]}",
    ]
    if args.out:
        human.append(f"  artifact={payload['artifact']}  sidecar={payload['sidecar']}")
        human.append(f"  freshness={payload['freshness']['state']}")
    for cid, why in sel.omitted[:5]:
        human.append(f"  omitted {cid}: {why}")
    if len(sel.omitted) > 5:
        human.append(f"  ... and {len(sel.omitted) - 5} more omissions (all in the sidecar)")
    return _emit(payload, args.json, "\n".join(human))


# ------------------------------------------------------------------- query

def cmd_query(args) -> int:
    from gate import UsePolicy, evaluate  # noqa: PLC0415

    led = _ledger(args)
    result = fold([r.frame for r in led.read_all()], as_of=args.as_of)
    policy = UsePolicy(
        use=args.use, floor=parse_grade(args.floor), standard=args.standard,
        allow_conflicted=args.allow_conflicted,
        allow_review_required=args.allow_review_required,
        allow_labelled_stale=args.allow_labelled_stale,
        min_disjoint_supports=args.min_disjoint,
    )
    res = evaluate(args.claim_id, result, policy)
    human = [f"{res.outcome.upper()}  {args.claim_id}  (use={policy.use} floor={policy.floor})"]
    human += [f"  reason: {r}" for r in res.reasons]
    human += [f"  next:   {a}" for a in res.required_next_actions]
    if res.certificate:
        human.append(f"  certificate={res.certificate['certificate_hash']}")

    payload = res.as_dict()
    # R5d: the forward reuse series only accrues if something writes the frames. Logging is on by
    # default and opt-OUT, because the failure mode is silent and unrecoverable -- a query nobody
    # logged cannot be reconstructed later, so a default of "off" would keep R5d blocked forever
    # while every command still appeared to work.
    if not args.no_log:
        from gate import query_served_frame  # noqa: PLC0415

        frame = query_served_frame(res, policy, frontier=result.frontier, at=args.as_of)
        rec = led.append(frame)
        payload["query_served_seq"] = rec.seq
        human.append(f"  logged: seq={rec.seq} (query_served)")

    _emit(payload, args.json, "\n".join(human))
    return 0 if res.usable_as_current else 3


# ------------------------------------------------------------- disposition

def cmd_disposition(args) -> int:
    """Record what a human did about a surfaced obligation (R5b write-time input)."""
    from gate import obligation_disposition_frame  # noqa: PLC0415

    frame = obligation_disposition_frame(
        args.obligation_id, args.disposition, actor=args.actor, at=args.at, note=args.note
    )
    rec = _ledger(args).append(frame)
    return _emit(
        {"seq": rec.seq, "obligation_id": args.obligation_id, "disposition": args.disposition},
        args.json,
        f"recorded {args.disposition} for {args.obligation_id} at seq={rec.seq}",
    )


# -------------------------------------------------------------- live eval

def cmd_eval_live(args) -> int:
    """PR2: score the engine against a corpus drawn from the live ledger."""
    import yaml  # noqa: PLC0415

    from live_eval import run_live  # noqa: PLC0415

    led = _ledger(args)
    index_path = Path(args.index) if args.index else REPO_ROOT / "research" / "intake_index.yaml"
    res = run_live(
        [r.frame for r in led.read_all()],
        yaml.safe_load(index_path.read_text()) or [],
        as_of=args.as_of,
        count=args.count,
        floor=args.floor,
        require_verified=args.verified_only,
    )
    human = [
        f"live corpus: {len(res['families'])} families  score={res['score']}/{res['max_score']}",
        f"  invalidation_recall={res['invalidation_recall']}  "
        f"discrimination={res['discrimination']}  harmful={res['harmful_outcomes']}",
        f"  UNCOVERABLE claims (citing entries, never scored): {res['uncoverable_claims']}",
    ]
    return _emit(res, args.json, "\n".join(human))


# ------------------------------------------------------------------- alias

def cmd_alias_candidates(args) -> int:
    """Propose cross-entry claim aliases and write a human review worksheet (R4b-authoring)."""
    import yaml  # noqa: PLC0415

    from alias_candidates import (  # noqa: PLC0415
        generate_candidates,
        locator_map,
        worksheet_from_candidates,
    )

    led = _ledger(args)
    index_path = Path(args.index) if args.index else REPO_ROOT / "research" / "intake_index.yaml"
    index_entries = yaml.safe_load(index_path.read_text()) or []
    locators = locator_map(index_entries)
    citations = {}
    for entry in index_entries:
        refs = ((entry.get("cross_references") or {}).get("intake_entries")) or []
        citations[entry.get("id")] = {r for r in refs if isinstance(r, str)}
    report = generate_candidates(
        [r.frame for r in led.read_all()],
        min_score=args.min_score,
        limit=args.limit,
        locators=locators,
        citations=citations,
    )
    worksheet = worksheet_from_candidates(report, generated_at=args.at)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(worksheet, sort_keys=False, allow_unicode=True, width=100))
    human = [
        f"claims considered: {report['claims_considered']}",
        f"pairs after blocking: {report.get('blocked_pairs', 0)}  scored: {report['pairs_scored']}",
        f"candidates >= {args.min_score}: {report.get('candidates_above_threshold', 0)} "
        f"(worksheet holds {len(worksheet['rows'])})",
        f"worksheet: {out}  -- every row is 'pending' until a human decides",
    ]
    return _emit({k: v for k, v in report.items() if k != "candidates"}, args.json, "\n".join(human))


def cmd_alias_emit(args) -> int:
    """Turn approved worksheet rows into `claim_alias` frames."""
    import yaml  # noqa: PLC0415

    from alias_candidates import aliases_from_worksheet  # noqa: PLC0415
    from frames import make_frame  # noqa: PLC0415

    import hashlib  # noqa: PLC0415

    worksheet_bytes = Path(args.worksheet).read_bytes()
    worksheet = yaml.safe_load(worksheet_bytes.decode())
    # Digest the FILE, not the parsed structure: the worksheet carries float scores, which
    # the certified canonicalizer rightly refuses. What the frame must pin is which reviewed
    # document produced this decision, and that is the bytes.
    worksheet_digest = "sha256:" + hashlib.sha256(worksheet_bytes).hexdigest()
    groups = aliases_from_worksheet(worksheet)
    led = _ledger(args)
    emitted = []
    for group in groups:
        frame = make_frame(
            frame_type="epyc.vidya/frame/claim_alias/v1",
            assertion={
                "claim_ids": group["claim_ids"],
                "independent": group.get("independent", True),
            },
            provenance={
                "method": "human-review/alias-worksheet",
                "about": group["claim_ids"][0],
                "reviewers": group["reviewers"],
                "notes": group["notes"],
                "worksheet_digest": worksheet_digest,
            },
            actor=args.actor,
            authority_scope="claim-identity",
            created_at=args.at,
        )
        if args.dry_run:
            emitted.append({"claim_ids": group["claim_ids"], "seq": None})
            continue
        rec = led.append(frame)
        emitted.append({"claim_ids": group["claim_ids"], "seq": rec.seq})
    prefix = "(dry run) " if args.dry_run else ""
    human = [f"{prefix}{len(emitted)} alias group(s) from {args.worksheet}"]
    human += [f"  {' == '.join(g['claim_ids'])}" for g in emitted]
    return _emit({"groups": emitted, "dry_run": args.dry_run}, args.json, "\n".join(human))


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


# ------------------------------------------------------------------ consume

def cmd_cite_check(args) -> int:
    """SC12: gate intake citations in project documents (exit 3 = a blocking citation)."""
    from citation_gate import check_paths, summarize  # noqa: PLC0415
    from gate import UsePolicy  # noqa: PLC0415

    led = _ledger(args)
    result = fold([r.frame for r in led.read_all()], as_of=args.as_of)
    policy = UsePolicy(use=args.use, floor=parse_grade(args.floor), standard=args.standard)
    verdicts = check_paths(args.paths or None, result, policy)
    summary = summarize(verdicts)
    human = [
        f"{summary['citations']} citation(s) across {summary['documents']} document(s)",
        "  " + "  ".join(f"{k}={v}" for k, v in summary["by_status"].items() if v),
    ]
    for v in verdicts:
        if v.status in ("ok", "record"):
            continue
        human.append(f"  [{v.status}] intake-{v.entry}  {v.path}")
    _emit({"summary": summary, "verdicts": [v.as_dict() for v in verdicts]}, args.json,
          "\n".join(human))
    return 3 if summary["blocking"] else 0


def cmd_corrections(args) -> int:
    """SC13: the correction adjudication queue, ranked by how much cites the entry."""
    from correction_queue import pending  # noqa: PLC0415

    led = _ledger(args)
    frames = [r.frame for r in led.read_all()]
    rows = pending(frames, fold(frames, as_of=args.as_of))
    human = [f"{len(rows)} unadjudicated correction(s) blocking "
             f"{sum(len(r.claim_ids) for r in rows)} claim(s)"]
    for r in rows[:args.limit]:
        human.append(f"  {r.entry_id}  citations={r.citations}  claims={len(r.claim_ids)}"
                     + (f"  copies={r.copies}" if r.copies > 1 else ""))
    _emit({"pending": len(rows), "rows": [r.as_dict() for r in rows]}, args.json, "\n".join(human))
    return 0


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

    im = sub.add_parser("impact", help="hypothetical retraction: what changes if these frames go?")
    im.add_argument("frame_id", nargs="+")
    im.add_argument("--as-of", required=True)
    im.set_defaults(func=cmd_impact)

    v = sub.add_parser("verify", help="verify the chain and any published checkpoints")
    v.set_defaults(func=cmd_verify)

    pr = sub.add_parser("project", help="compile a dependency-declared projection")
    pr.add_argument("projection_id")
    pr.add_argument("--as-of", required=True)
    pr.add_argument("--floor", default="Verified/Anchored")
    pr.add_argument("--policy-id", default="wiki-authoritative-v1")
    pr.add_argument("--claim", action="append", help="restrict to these claim ids")
    pr.add_argument("--out", help="write the artifact here (and a sidecar next to the ledger)")
    pr.set_defaults(func=cmd_project)

    q = sub.add_parser("query", help="apply a use policy to one claim (exit 3 = not usable)")
    q.add_argument("claim_id")
    q.add_argument("--as-of", required=True)
    q.add_argument("--floor", default="Verified/Anchored")
    q.add_argument("--use", default="wiki-authoritative")
    q.add_argument("--standard", default="DV")
    q.add_argument("--allow-conflicted", action="store_true")
    q.add_argument("--allow-review-required", action="store_true")
    q.add_argument("--allow-labelled-stale", action="store_true")
    q.add_argument("--min-disjoint", type=int, default=1)
    q.add_argument(
        "--no-log",
        action="store_true",
        help="do NOT append a query_served frame (suppresses the R5 reuse series for this query)",
    )
    q.set_defaults(func=cmd_query)

    d = sub.add_parser("disposition", help="record a human disposition of a surfaced obligation")
    d.add_argument("obligation_id")
    d.add_argument("disposition", choices=["accepted", "acted", "deferred", "dismissed"])
    d.add_argument("--actor", required=True)
    d.add_argument("--at", required=True)
    d.add_argument("--note", default="")
    d.set_defaults(func=cmd_disposition)

    el = sub.add_parser("eval-live", help="score the engine against a live-ledger corpus (PR2)")
    el.add_argument("--as-of", required=True)
    el.add_argument("--index", help="path to intake_index.yaml")
    el.add_argument("--count", type=int, default=6, help="mutation families to draw")
    el.add_argument("--floor", default="Verified/Anchored")
    el.add_argument("--verified-only", action="store_true",
                    help="draw only dived entries, so the retraction path is exercised")
    el.set_defaults(func=cmd_eval_live)

    ac = sub.add_parser("alias-candidates", help="propose cross-entry claim aliases for review")
    ac.add_argument("--out", required=True, help="worksheet path to write")
    ac.add_argument("--at", required=True, help="generation timestamp")
    ac.add_argument("--index", help="path to intake_index.yaml (for source-locator identity)")
    ac.add_argument("--min-score", type=float, default=0.35)
    ac.add_argument("--limit", type=int, default=200)
    ac.set_defaults(func=cmd_alias_candidates)

    ae = sub.add_parser("alias-emit", help="emit claim_alias frames from an approved worksheet")
    ae.add_argument("worksheet")
    ae.add_argument("--actor", required=True)
    ae.add_argument("--at", required=True)
    ae.add_argument("--dry-run", action="store_true")
    ae.set_defaults(func=cmd_alias_emit)

    i = sub.add_parser("ingest", help="run a source adapter")
    i.add_argument("adapter", choices=["intake"])
    i.add_argument("--index", help="path to intake_index.yaml")
    i.add_argument("--limit", type=int, help="only the first N entries")
    i.add_argument("--as-of", required=True, help="explicit ingest timestamp")
    i.add_argument("--dry-run", action="store_true", help="report without appending")
    i.set_defaults(func=cmd_ingest)

    cc = sub.add_parser("cite-check", help="gate intake citations in project documents")
    cc.add_argument("paths", nargs="*", help="files or dirs (default: handoffs, wiki, docs)")
    cc.add_argument("--as-of", required=True)
    cc.add_argument("--floor", default="Hinted/Located")
    cc.add_argument("--use", default="handoff-rationale")
    cc.add_argument("--standard", default="DV")
    cc.set_defaults(func=cmd_cite_check)

    cq = sub.add_parser("corrections", help="the unadjudicated-correction queue")
    cq.add_argument("--as-of", required=True)
    cq.add_argument("--limit", type=int, default=20)
    cq.set_defaults(func=cmd_corrections)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
