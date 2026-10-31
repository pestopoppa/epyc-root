#!/usr/bin/env python3
"""Vidya pilot CLI.

Spec: docs/design/vidya-pilot-spec.md §15.2 (pilot commands), §11 (ledger and checkpoints).

    vidya append     <frame.json>      append a frame to the ledger
    vidya fold       [--as-of TS]      fold the ledger and print derived belief state
    vidya checkpoint [--emit]          compute (and optionally publish) an L1 checkpoint
    vidya verify                       verify the chain, and the checkpoint history if present
    vidya ingest     intake [--limit]  run the research-intake adapter (read-only source)
    vidya ingest     <file source> [--path P]  run a file-shaped adapter (ingest_sources.py)

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
from ledger_home import checkpoint_dir_for, default_ledger_path, scratch_ledger_path  # noqa: E402

FOLD_VERSION = "vidya-pilot-0.2.0"  # 0.2.0: belief state gained corrections/review_required (P2c)
DEFAULT_ORIGIN = "epyc.local/belief-ledger"
REPO_ROOT = Path(__file__).resolve().parents[2]
VIDYA_DIR = REPO_ROOT / ".vidya"
#: Default ledger: the ONE canonical, worktree-independent ledger (ledger_home.py). Worktree-local
#: only via --scratch / VIDYA_SCRATCH=1; VIDYA_LEDGER=<path> overrides; --ledger beats all.
LEDGER_PATH = default_ledger_path(REPO_ROOT)
CHECKPOINT_DIR = VIDYA_DIR / "checkpoints"


def _ledger_path(args) -> Path:
    # The ingest-local spelling already takes precedence for autokernel-experiments.
    # Apply the same explicit target to every adapter before any ledger or lock opens.
    explicit = getattr(args, "ingest_ledger", None) or args.ledger
    if explicit:
        return Path(explicit)
    if getattr(args, "scratch", False):
        return scratch_ledger_path(REPO_ROOT)
    return default_ledger_path(REPO_ROOT)


def _checkpoint_dir(args) -> Path:
    """Checkpoints belong to THEIR ledger, not to a fixed location.

    Deriving this from the ledger path rather than a module constant is not cosmetic: a verify run
    that reads a global checkpoint directory while pointed at a different ledger will compare a
    checkpoint against a log it never attested to, and correctly-but-uselessly report truncation.
    (Caught by the CLI end-to-end test, which ran a five-frame temp ledger against the repo's
    9,449-entry checkpoint.)
    """
    return checkpoint_dir_for(_ledger_path(args), REPO_ROOT)


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
        # SC61: the claim -> live statement-binding frame map, so an attested binding is
        # observable in derived state, not just in the raw ledger.
        "statement_bindings": dict(sorted(result.statement_bindings.items())),
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
    # SC73: an empty ledger must not report chain=OK. The latest published checkpoint IS the
    # declared count -- chain verification alone cannot see truncation-to-nothing, because any
    # prefix of a hash chain chains.
    declared = None
    ckdir = _checkpoint_dir(args)
    if ckdir.exists():
        declared = max((cp.parse_checkpoint(p.read_text())[0].tree_size
                        for p in ckdir.glob("checkpoint-*.txt")), default=None)
    chain_problems = led.verify(expected_count=declared)
    checkpoint_problems: list[str] = []
    records = led.read_all()
    hashes = [r.frame_hash for r in records]

    checkpoint_results = []
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


# ------------------------------------------------- statement binding (SC61)

def cmd_binding_candidates(args) -> int:
    """Propose unbound verifier claims for an `attested` statement-binding review (SC61)."""
    import yaml  # noqa: PLC0415

    from statement_binding import candidate_rows, worksheet_from_candidates  # noqa: PLC0415

    led = _ledger(args)
    rows = candidate_rows([r.frame for r in led.read_all()], limit=args.limit)
    worksheet = worksheet_from_candidates(rows, generated_at=args.at)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(worksheet, sort_keys=False, allow_unicode=True, width=100))
    human = [
        f"candidates: {len(rows)} unbound verifier claim(s) whose decided proposition is not "
        "the claim itself (identity-eligible pairs are never proposed)",
        f"worksheet: {out}  -- every row is 'pending' until a human decides",
    ]
    return _emit({"candidates": len(rows), "out": str(out)}, args.json, "\n".join(human))


def cmd_binding_emit(args) -> int:
    """Turn approved worksheet rows into `claim_statement_binding/v1` frames."""
    import hashlib  # noqa: PLC0415

    import yaml  # noqa: PLC0415

    from statement_binding import bindings_from_worksheet, frame_from_binding  # noqa: PLC0415

    worksheet_bytes = Path(args.worksheet).read_bytes()
    worksheet = yaml.safe_load(worksheet_bytes.decode())
    # Digest the FILE, not the parsed structure, for the same reason alias-emit does: the frame
    # pins which reviewed document produced the decision, and the worksheet may carry text.
    worksheet_digest = "sha256:" + hashlib.sha256(worksheet_bytes).hexdigest()
    bindings = bindings_from_worksheet(worksheet)
    led = _ledger(args)
    emitted = []
    for binding in bindings:
        frame = frame_from_binding(binding, actor=args.actor, at=args.at,
                                   worksheet_digest=worksheet_digest)
        if args.dry_run:
            emitted.append({"claim_id": binding["claim_id"], "frame_id": frame["frame_id"]})
            continue
        rec = led.append(frame)
        emitted.append({"claim_id": binding["claim_id"], "frame_id": frame["frame_id"],
                        "seq": rec.seq})
    prefix = "(dry run) " if args.dry_run else ""
    human = [f"{prefix}{len(emitted)} statement binding(s) from {args.worksheet}"]
    human += [f"  {e['claim_id']} <- {e['frame_id']}" for e in emitted]
    return _emit({"bindings": emitted, "dry_run": args.dry_run}, args.json, "\n".join(human))


# ------------------------------------------------------------------ ingest

AUTOKERNEL_CORPUS_ROOT = Path("/mnt/raid0/llm/autokernel")
INF70_CORPUS_ROOT = Path("/mnt/raid0/llm/tmp/inf70")
# Kept literal (not imported) so `cli.py --help` stays cheap; test_ingest_sources pins it
# equal to ingest_sources.SOURCES.
_FILE_SOURCES = (
    "inf34-a2-raw-prefill",
    "dev-harness-aggregate", "lb49-combined-diagnostic",
    "ufh12-irt-paired",
    "ufh12-gs-coverage",
    "rtg57-vkq-comparison", "rtg57-vkq-oracle",
    "df2-row-exact-akx",
    "hg5-request-event",
    "graph-profiler-measurement",
    "pip02-incremental-teds",
    "odl-unlimited-ocr-run",
    "dtap-timeout-report",
    "pii-staged-gate",
    "ci-fixture-conformance",
    "distillation-pool",
    "managed-tooling-check",
    "contextbench-discovery-score",
    "strategy-projection-report",
    "session-intercall-gap",
    "orchestrator-serving-call",
    "exl3-measurement", "exl3-verifier",
    "research-screen",
    "s4-omega-ab",
    "kv-quant-27b-v10-measurement", "kv-quant-27b-v10-retrofit", "autokernel-served-shape", "embedder-placement-gate", "gfx90a-static-register",
    "repl-retrieval-eval", "repl-embedder-speed",
    "qwen4exp-quality-measurement",
    "evidence-durability",
    "kb-rag-qlen", "inf70-arms", "contention-gate", "contention-matrix", "beam", "tulving",
    "hs-prof1-profile-arms",
    "chat-template-ab", "kpf261-plan-steps", "kv-prefix-fork", "pb-hol", "occ1", "tale-budget", "review-f1", "opencode-shell",
    "memento-lora", "pareval", "eval-tower-band", "fanout-outcome",
    "research-sweep-g1", "research-sweep-g234", "autopilot-journal", "sealed-manifest",
    "mhs-guard-verdicts", "mhs-guard-ops",
    "verify-before-stop-measurement", "eval-suite-discriminability",
    "autopilot-reproposal-rate", "reviewer-fa", "typed-decisions-measurement",
    "ufh13-thesis-measurement",
    "ak-actor-seat",
    "ds41-1017-validation",
    "toc-ab", "skillbank-ab", "harness-improvement", "ak-history",
    "injection-fixture", "chunk-kv",
    "conversation-stack-measurement", "speech-ggml-optest",
    "speech-cpu-measurement", "speech-listen-rating",
    "hil15a-auc", "repl-preview",
    "rus2-probe", "gpu-leak-probe", "v11-oracle-rerun", "ds41-w5d", "akx-lb32", "repl-embedder-parity", "clbench-cache-hit", "spec-rng-1-2", "pb-qcost", "ev19-gold-selfcheck", "oolong", "yarn-gate-agg", "nemotron-bolt-fold", "np-ctx-kvu-measurement", "ufh14-lb7-stall", "ch19-t3-screen",
    "hil17-attribution-ladder", "hil-lb1-loop-score",
    "ak-width-dimension", "ak-width-cells-cpu",
    "moe-routing",
    "gpu-cpu-noise", "launch-affinity", "q38-serving-gate", "fused-decode-div", "champion-fold-gate", "calendar-overrun", "floor-registry", "weight-handoff",
    "hsf5p-microbench", "m4-cpu-recipe-speed", "c6-q4-microbench",
)


def _ingest_autokernel(args) -> int:
    """Walk the AutoKernel runtime corpus through its ten strict adapters.

    The adapters were built, tested and verified against the real corpus (2,601
    gradeable tuples) and had never persisted a row, because this command only ever
    accepted `intake`. The read side was complete; the write side had never fired.
    """
    from adapters.autokernel_corpus import ingest_corpus  # noqa: PLC0415

    root = Path(args.root) if args.root else AUTOKERNEL_CORPUS_ROOT
    if not root.is_dir():
        print(f"no such AutoKernel corpus root: {root}", file=sys.stderr)
        return 2
    led = _ledger(args)
    if getattr(args, "only_new", False):
        # VB-LOOP-SCOPE: project into a collector, then append only what the ledger lacks
        # (new claims, plus one scope re-observation per already-live unscoped claim).
        from scoped_ingest import Collector, append_scoped  # noqa: PLC0415
        sink = Collector()
        report = ingest_corpus(sink, root=root, as_of=args.as_of, limit=args.limit)
        report["only_new"] = append_scoped(led, sink.frames, as_of=args.as_of,
                                           dry_run=args.dry_run)
        report["frames_emitted"] = 0 if args.dry_run else report["only_new"]["frames"]
        report["dry_run"] = args.dry_run
    else:
        report = ingest_corpus(led, root=root, as_of=args.as_of, limit=args.limit,
                               dry_run=args.dry_run)
    human = [
        f"documents matched={report['documents_matched']}  "
        f"rows projected={report['rows_projected']}  "
        f"frames={'(dry run) ' if args.dry_run else ''}{report['frames_emitted']}  "
        f"refused={report['refused']}  declined={report['documents_yielding_no_rows']}  "
        f"not-an-entry-point={report['schema_not_an_entry_point']}",
        f"by adapter: {report['by_adapter'] or '(none)'}",
    ]
    if report["refused"]:
        human.append("refusals (strict readers rejecting records that do not rederive):")
        human.extend(f"  {item['reason'][:110]}" for item in report["refusal_sample"][:5])
    if report.get("only_new"):
        human.append(f"only-new: {_only_new_line(report['only_new'])}")
    human.append("unwired (reported, not skipped silently):")
    human.extend(f"  {name}: {why}" for name, why in report["unwired_adapters"].items())
    return _emit(report, args.json, "\n".join(human))


def _ingest_inf70(args) -> int:
    """Walk the INF-70 CPU decode roofline run directories (SC53).

    Same lesson as `autokernel` above: the adapter was written, tested and
    verified against the real corpus and could never have persisted a row,
    because this command only accepted the adapters listed in its `choices`.
    Wiring the name IS the write side.
    """
    from adapters.inf70_roofline_ledger import ingest_corpus, DEFAULT_CORPUS  # noqa: PLC0415

    root = Path(args.root) if args.root else DEFAULT_CORPUS
    if not root.is_dir():
        print(f"no such INF-70 corpus root: {root}", file=sys.stderr)
        return 2
    led = _ledger(args)
    if getattr(args, "only_new", False):
        from scoped_ingest import Collector, append_scoped  # noqa: PLC0415
        sink = Collector()
        report = ingest_corpus(sink, root=root, as_of=args.as_of, limit=args.limit)
        report["only_new"] = append_scoped(led, sink.frames, as_of=args.as_of,
                                           dry_run=args.dry_run)
        report["frames_emitted"] = 0 if args.dry_run else report["only_new"]["frames"]
        report["dry_run"] = args.dry_run
    else:
        report = ingest_corpus(led, root=root, as_of=args.as_of, limit=args.limit,
                               dry_run=args.dry_run)
    human = [
        f"runs matched={report['runs_matched']}  rows projected={report['rows_projected']}  "
        f"frames={'(dry run) ' if args.dry_run else ''}{report['frames_emitted']}",
        f"by kind: {report['by_kind'] or '(none)'}",
    ]
    if report["runs_refused"]:
        human.append("runs refused (not a run directory, or dateless):")
        human.extend(f"  {r['run']}: {r['reason']}" for r in report["runs_refused"])
    if report["arms_refused"]:
        # The producer-gap channel: named, never silent. An arm listed here is a
        # measurement that exists and cannot be cited until its producer is fixed.
        human.append("arms refused (strict reader: the record does not rederive):")
        human.extend(f"  {r['run']} {r['arm']}: {r['reason'][:110]}"
                     for r in report["arms_refused"])
    if report["rows_refused"]:
        human.append("rows refused (native_rows and project() disagree -- a defect):")
        human.extend(f"  {r['run']} {r['kind']}: {r['reason'][:110]}"
                     for r in report["rows_refused"])
    if report.get("only_new"):
        human.append(f"only-new: {_only_new_line(report['only_new'])}")
    return _emit(report, args.json, "\n".join(human))


def _only_new_line(result: dict) -> str:
    return (f"new claims={result['new_claims']}  rescoped={result['rescoped']}  "
            f"already present={result['already_present']}  refused={len(result['refused'])}  "
            f"frames={'(dry run) ' if result.get('dry_run') else ''}{result['frames']}")


def _ingest_autokernel_serving(args) -> int:
    """VB-LOOP-SCOPE producer-time entry point: one loop store's serving A/B receipts."""
    from scoped_ingest import ingest_scoped_store  # noqa: PLC0415

    if not args.root or not Path(args.root).is_dir():
        print(f"autokernel-serving needs --root <loop store or campaign dir> (got {args.root!r})",
              file=sys.stderr)
        return 2
    report = ingest_scoped_store(_ledger(args), Path(args.root), as_of=args.as_of,
                                 dry_run=args.dry_run, memo_path=args.memo,
                                 experiments_full=getattr(args, "experiments_full", False))
    human = (f"receipts listed={report['receipts_listed']}  known={report['receipts_known']}  "
             f"read={report['receipts_read']}  v2={report.get('v2_projected', 0)}  "
             f"floors={report.get('floors_projected', 0)}  "
             f"experiments={report.get('experiments_projected', 0)}  "
             f"refused={len(report['refusals'])}  "
             f"new claims={report['new_claims']}  rescoped={report['rescoped']}  "
             f"frames={'(dry run) ' if args.dry_run else ''}{report['frames_appended']}  "
             f"seconds={report['seconds']}")
    return _emit(report, args.json, human)


def _ingest_autokernel_experiments(args) -> int:
    """Belief-redesign P1-C: AutoKernel `experiments.db` rows -> loop beliefs.

    DRY RUN by default: reads the stores read-only, projects every row, prints counts, touches no
    ledger. Writing needs an EXPLICIT ledger path (`--ledger`, never the env/default resolution)
    and refuses the canonical ledger unless `--i-own-the-canonical-ledger` is given.
    """
    from adapters import autokernel_experiments as exp  # noqa: PLC0415
    from claim_tuple import ProjectionError  # noqa: PLC0415

    stores = [Path(s) for s in (args.store or [])]
    if not stores or any(not (s / "experiments.db").is_file() for s in stores):
        print("autokernel-experiments needs --store <dir holding experiments.db> (repeatable); "
              f"got {[str(s) for s in stores]}", file=sys.stderr)
        return 2
    if args.since_rowid is not None and len(stores) != 1:
        print("--since-rowid is a per-store high-water mark: use it with exactly one --store",
              file=sys.stderr)
        return 2
    explicit = getattr(args, "ingest_ledger", None) or args.ledger
    write = bool(explicit) and not args.dry_run
    target = None
    try:
        if write:
            if not args.as_of:
                print("writing needs --as-of <explicit ingest timestamp>", file=sys.stderr)
                return 2
            target = exp.check_ledger_target(
                explicit, i_own_canonical=getattr(args, "i_own_the_canonical_ledger", False))
        report = exp.ingest(stores, as_of=args.as_of, ledger_path=target,
                            since_rowid=args.since_rowid)
    except (ProjectionError, ValueError, OSError) as exc:
        print(f"autokernel-experiments refused: {exc}", file=sys.stderr)
        return 2
    human = [f"stores={len(report['stores'])}  rows read={report['rows_read']}  "
             f"projected={report['projected']}  frames="
             f"{'(dry run) ' if report['dry_run'] else ''}{report['frames']}  "
             f"retrofit={report['retrofit']}  seconds={report['seconds']}",
             f"by disposition: {report['by_disposition'] or '(none)'}",
             f"by outcome: {report['by_outcome'] or '(none)'}",
             f"by scope basis: {report['by_scope_basis'] or '(none)'}",
             f"not projected: {report['not_projected'] or '(none)'}",
             f"by status: {report['by_status'] or '(none)'}"]
    if report["projection_errors"]:
        human.append("projection errors:")
        human.extend(f"  {line}" for line in report["projection_errors"][:5])
    return _emit(report, args.json, "\n".join(human))


def _ingest_file_source(args) -> int:
    """The file-shaped adapters (``ingest_sources.SOURCES``): KB-RAG query length, SC75
    INF-70 serving arms, and every sidecar reader that had no ingest name before 2026-09-16."""
    import ingest_sources  # noqa: PLC0415

    paths = [Path(p) for p in (args.path or [])] or ([Path(args.root)] if args.root else None)
    try:
        report = ingest_sources.ingest(_ledger(args), args.adapter, paths, as_of=args.as_of,
                                       limit=args.limit, dry_run=args.dry_run,
                                       only_new=getattr(args, "only_new", False))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return _emit(report, args.json, ingest_sources.human(report))


def cmd_ingest(args) -> int:
    # Reject absent directory corpora before creating the ledger or writer lock.
    # Keep the existing adapter-local validation for direct internal callers.
    if args.adapter in ("autokernel", "inf70"):
        default = (AUTOKERNEL_CORPUS_ROOT if args.adapter == "autokernel"
                   else INF70_CORPUS_ROOT)
        root = Path(args.root) if args.root else default
        if not root.is_dir():
            label = "AutoKernel" if args.adapter == "autokernel" else "INF-70"
            print(f"no such {label} corpus root: {root}", file=sys.stderr)
            return 2
    # one host-wide critical section per ingest: dedup-read and append must not interleave with
    # another session's ingest into the shared canonical ledger
    if args.dry_run:
        return _cmd_ingest(args)
    # VB-LOOP-SCOPE: these paths project outside the lock and hold it only for their own
    # dedup-read + append (scoped_ingest.append_scoped), so a slow corpus read never blocks
    # every other writer of the shared ledger.
    if args.adapter in ("autokernel-serving", "autokernel-experiments") or (
            getattr(args, "only_new", False) and args.adapter in ("autokernel", "inf70")):
        return _cmd_ingest(args)
    with _ledger(args).write_lock():
        return _cmd_ingest(args)


def _cmd_ingest(args) -> int:
    if not args.as_of and args.adapter != "autokernel-experiments":
        print(f"ingest {args.adapter} needs --as-of <explicit ingest timestamp>", file=sys.stderr)
        return 2
    if getattr(args, "only_new", False) and args.adapter not in (
            *_FILE_SOURCES, "autokernel", "inf70", "autokernel-serving"):
        print("--only-new is supported only for file-shaped sources, autokernel and inf70",
              file=sys.stderr)
        return 2
    if args.adapter in _FILE_SOURCES:
        return _ingest_file_source(args)
    if args.adapter == "autokernel-serving":
        return _ingest_autokernel_serving(args)
    if args.adapter == "autokernel-experiments":
        return _ingest_autokernel_experiments(args)
    if args.adapter == "autokernel":
        return _ingest_autokernel(args)
    if args.adapter == "inf70":
        return _ingest_inf70(args)
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

def cmd_sync(args) -> int:
    """Keep the canonical ledger current with origin/main's intake index (see sync.py).

    --check : report ledger lag vs the index, write nothing; exit 1 if stale (wrap-up freshness CHECK).
    default : fold the index in if it is not already folded (idempotent, append-only).
    """
    import sync as vsync  # noqa: PLC0415

    path = _ledger_path(args)
    index = Path(args.index) if args.index else None
    if args.check:
        st = vsync.status(path, index, from_worktree=args.from_worktree)
        human = (f"ledger {'FRESH' if st['fresh'] else 'STALE'}: index max intake-{st['index_max_id']} "
                 f"({st['index_entries']} entries), ledger synced through intake-{st['synced_max_id']}, "
                 f"lag {st['lag_entries']}, source {st['index']}, last sync {st['last_sync']}, ledger {st['ledger']}")
        _emit(st, args.json, human)
        return 0 if st["fresh"] else 1
    rep = vsync.sync(path, index, as_of=args.as_of, force=args.force,
                     from_worktree=args.from_worktree)
    if args.quiet:
        return 0
    return _emit(rep, args.json, f"sync: {rep['action']}  frames={rep.get('frames_emitted', 0)}  "
                 f"synced through intake-{rep['synced_max_id']}")


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
    p.add_argument("--scratch", action="store_true",
                   help="use the worktree-local .vidya/ledger.jsonl (tests only; NOT the canonical ledger)")
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

    bc = sub.add_parser("binding-candidates",
                        help="propose unbound verifier claims for an attested binding review")
    bc.add_argument("--out", required=True, help="worksheet path to write")
    bc.add_argument("--at", required=True, help="generation timestamp")
    bc.add_argument("--limit", type=int, help="only the first N candidates")
    bc.set_defaults(func=cmd_binding_candidates)

    be = sub.add_parser("binding-emit",
                        help="emit claim_statement_binding frames from an approved worksheet")
    be.add_argument("worksheet")
    be.add_argument("--actor", required=True)
    be.add_argument("--at", required=True)
    be.add_argument("--dry-run", action="store_true")
    be.set_defaults(func=cmd_binding_emit)

    i = sub.add_parser("ingest", help="run a source adapter")
    i.add_argument("adapter", choices=["intake", "autokernel", "inf70", "autokernel-serving",
                                       "autokernel-experiments", *_FILE_SOURCES])
    i.add_argument("--path", action="append",
                   help="file or directory for a file-shaped source (repeatable)")
    i.add_argument("--index", help="path to intake_index.yaml")
    i.add_argument("--root", help="corpus root for the autokernel adapter "
                                  f"(default {AUTOKERNEL_CORPUS_ROOT}) or for the "
                                  f"inf70 adapter (default {INF70_CORPUS_ROOT})")
    i.add_argument("--limit", type=int, help="only the first N entries")
    i.add_argument("--as-of", help="explicit ingest timestamp (required by every adapter "
                                   "except a dry-run autokernel-experiments)")
    i.add_argument("--dry-run", action="store_true", help="report without appending")
    i.add_argument("--store", action="append",
                   help="autokernel-experiments: a loop store dir holding experiments.db "
                        "(repeatable)")
    i.add_argument("--since-rowid", type=int,
                   help="autokernel-experiments: only rows with rowid above this (one store)")
    i.add_argument("--ledger", dest="ingest_ledger",
                   help="ledger to WRITE (same as global --ledger; this spelling wins if both "
                        "are given). autokernel-experiments stays a dry run without an explicit ledger")
    i.add_argument("--i-own-the-canonical-ledger", action="store_true",
                   help="autokernel-experiments: allow --ledger to be the canonical ledger "
                        "(owning session only)")
    i.add_argument("--only-new", action="store_true",
                   help="skip claims with live evidence (file-shaped sources); for autokernel "
                        "and inf70, also re-scope live unscoped claims (scoped_ingest.py)")
    i.add_argument("--memo", help="autokernel-serving: refused-receipt memo file (optional)")
    i.add_argument("--experiments-full", action="store_true",
                   help="autokernel-serving: read every experiments.db row (the backfill), not "
                        "only rows above the memo watermark")
    i.set_defaults(func=cmd_ingest)

    sy = sub.add_parser("sync", help="keep the canonical ledger current with the intake index")
    sy.add_argument("--check", action="store_true", help="report lag only; exit 1 if stale")
    sy.add_argument("--index", help="read this local file instead of origin/main")
    sy.add_argument("--from-worktree", action="store_true",
                    help="read this checkout's research/intake_index.yaml, not origin/main "
                         "(tests, Stage-1 pre-merge previews)")
    sy.add_argument("--as-of", help="ingest timestamp (default now)")
    sy.add_argument("--force", action="store_true")
    sy.add_argument("--quiet", action="store_true")
    sy.set_defaults(func=cmd_sync)

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
