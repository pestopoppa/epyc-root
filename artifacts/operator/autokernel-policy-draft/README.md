# AutoKernel policy drafts — staging area

**Status:** DRAFTS ONLY. Nothing here is ratified, and nothing here is in force.
**Owning handoff:** [`handoffs/active/autokernel-research-loop.md`](../../../handoffs/active/autokernel-research-loop.md) §3, §14 AK0.
**Created:** 2026-08-02

## Why this directory exists

`MEASUREMENT.md`, `agents/shared/MEASUREMENT_POLICY.md`, and `measurement/protocols/*.md` are
human-amendment-only and hook-blocked (`coordination/session-bus/human_only_paths.yaml:26-34`;
PreToolUse refusal via `scripts/hooks/check_trust_boundary_edit.sh`, wired at
`.claude/settings.json:76`). An agent cannot write them, and should not try.

Amendments are therefore authored here and presented to the operator as a pre-validated apply bundle,
following the precedent of `artifacts/operator/measurement-v2-draft/`.

## Sequencing: two attestations, not one

`MEASUREMENT_POLICY.md:77-78` asks that queued boundary items be batched into **one attestation
listing each item so the operator may strike lines**. That guards against a per-experiment
ratification cycle. It does not require that items whose referents appear months apart be forced into
the same signature — and doing so would mean ratifying release bindings long before the artifacts they
bind to exist, against a constitution whose protocols are append-or-version and never silently edited
(`MEASUREMENT.md:116-118`).

AutoKernel therefore presents **two** attestations, each internally batched and each presented only
when every item's referent exists and has been validated.

### Attestation 1 — "search authorization" (presented after AK3)

Unblocks autonomous research. Every item's referent exists once AK1–AK3 land.

| Item | Draft | Blocking |
|---|---|---|
| **Annex K creation** plus the core-file layout and registry deltas — operator-approved 2026-08-02 | [`Annex-K-kernel-research-and-release.draft.md`](Annex-K-kernel-research-and-release.draft.md) §1–2 | container for `P-AK-SEARCH-1` |
| `P-AK-SEARCH-1` — search authority, tier scope, e-process construction, pre-committed stopping rule, per-tier reps, anchor gate, selection/confirmation split, four controls, record grammar, void conditions | [`Annex-K-kernel-research-and-release.draft.md`](Annex-K-kernel-research-and-release.draft.md) §3 | AK3 exit ("T1 may legally guide search") |
| `pgrep` substitute — claim-holder witness plus owned-cgroup enumeration as an equivalent P-BENCH-1 / P-GPU-1 precondition (amends B and G in place; **not** an Annex K protocol) | *not yet drafted* | every protocol-conformant measurement |
| Evidence-retention rule — expirable classes and tombstoned expiry, since `MEASUREMENT.md:223-229` puts reclamation under operator authority (a core-file §5 amendment, where durability is stated) | *not yet drafted* | AK1 storage plane |
| `human_only_paths.yaml` additions (evaluator bundle, objective/threshold policy) plus the `.sha256` rewrite. Note the existing `measurement/protocols/*.md` entry is a **glob** and already covers the new annex file — verify, do not amend | *not yet drafted* | AK2/AK3 evaluator immutability |

### Attestation 2 — "release authorization" (presented before the first freeze, after AK5)

Unblocks a freeze. Every item's referent exists only after the sealer and T3 runner exist.

| Item | Draft | Blocking |
|---|---|---|
| P-GPU-1 sealed-candidate amendment | [`P-GPU-1-sealed-candidate-amendment.draft.md`](P-GPU-1-sealed-candidate-amendment.draft.md) | AK7 first supervised freeze, GPU scope only |
| `epyc.autokernel.operator_waiver.v1` | *not yet drafted* | AK5 T3 verdict states; the draft schema suffices for the AK5 dry-run |

**Why the split is safe.** The GPU protocol carries two separate prohibitions
(`gpu-cross-device.md:16-21`). The **consumption** clause — experimental measurements *"MUST NOT be
consumed by AutoPilot or any automated optimizer"* — bites on every GPU T1 round and belongs to
attestation 1. The **decision-grade** clause — a claim may only be produced on a production-named
kernel — bites only when a freeze needs new GPU evidence, and belongs to attestation 2. Building and
validating the evaluator before attestation 1 is legal: fixture-driven acceptance runs are not an
automated optimizer consuming results to choose its next candidate.

## Every ratification bundle must carry

Per `MEASUREMENT.md:116-118`, `:138-145`, and the `bench-cpu.md:132-140` transaction precedent:

- the amended text appended to the **owning annex** (never a silent edit);
- a one-line **CHANGELOG** entry in `MEASUREMENT.md`;
- an explicit statement of **what is superseded**, naming the prior receipt path and SHA-256;
- a **RATIFICATION_LEDGER.md** enumerating every semantic delta;
- a **protocol-registry row** in `MEASUREMENT.md` §2 for each new protocol ID;
- **evidence hashes** for every artifact the bundle cites, each resolving in-repo per
  `MEASUREMENT.md:146-156`;
- a **pre-validated** end-to-end command sequence — a failed validation re-presents the SAME apply
  token with updated hashes, never a restarted chain;
- presentation as one attestation **listing each item separately** so lines may be struck.

## Annex placement — RESOLVED 2026-08-02 (operator)

**Create Annex K (kernel research and release)** as a fourth annex — a new `kernel-research` file
under `measurement/protocols/`, created at ratification. It holds `P-AK-SEARCH-1`, which fits none of
the three declared families (`MEASUREMENT.md:15-20`): it is cross-backend and is a *search* instrument
rather than a measurement family. The rejected alternative — splitting it across B, Q and G — would
fragment one instrument across three files with three amendment histories, and would obscure the
property that matters most about it: that the authority is narrow, unified, and revocable in one
place.

Annex creation is itself a change to the constitution's declared layout, so the layout paragraph and
registry deltas ride inside attestation 1 rather than preceding it. The sealed-candidate amendment
stays in Annex G, where the rule it amends lives.

## A note on filenames in this directory

Annex and protocol filenames are written here **without their `.md` extension**. The repository's
markdown reference guard (`scripts/hooks/agents_reference_guard.sh`, PreToolUse) blocks any edit to a
document that cites a markdown file which does not yet exist — which is precisely what a staged
amendment must do. Writing the extension would make these drafts uneditable. Restore the extensions
when the amendment text is transcribed into the annex at ratification.

## Remaining open question

Whether `P-KERNEL-FREEZE-1` becomes an Annex K protocol or stays as distributed amendments to B and G.
Not needed until attestation 2. Current lean is distributed amendments, since the CPU release rule
already exists at `bench-cpu.md:83-88` and duplicating it into K would create two places to look.
