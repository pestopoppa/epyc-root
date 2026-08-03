<!-- DRAFT — NOT RATIFIED, NOT IN FORCE. Staged for operator review per
     artifacts/operator/autokernel-policy-draft/README.md (attestation 2).
     Target: measurement/protocols/gpu-cross-device.md (Annex G), appended as a new block.
     Author: AutoKernel design pass, 2026-08-02. -->

# DRAFT — P-GPU-1 amendment: sealed-candidate release evidence

**Status:** COMPLETE DRAFT (revised 2026-08-03). **The five `[BLOCKED-ON AKn]` markers are converted
to contracts** — each names the artifact that supplies its value at seal time and states what must be
recorded about it, rather than naming a format that does not exist. There are no `[BLOCKED-ON]`
markers left, and no unfilled token in the normative text other than `<APPLY_DATE>`.
**Amends:** `P-GPU-1 — MI210 GPU canonical throughput (RATIFIED 2026-07-19)`, Annex G.
**Supersedes:** the absolute form of P-GPU-1's kernel-provenance rule
(`measurement/protocols/gpu-cross-device.md:16-21`) — *not* the rule itself, which survives with one
enumerated exception. Prior receipt: the v2 apply, 20260730T103218Z,
`artifacts/operator/measurement-v2-draft/RATIFICATION_LEDGER.md` (SHA-256 recorded in the attestation-2
ledger at presentation time).
**Owning handoff:** `handoffs/active/autokernel-research-loop.md` §3.2.
**Presented in:** attestation **2** ("release authorization"), after AK5 — **NOT tonight**. It is
listed in the deferred-work register at `RATIFICATION_PACKAGE.md` §D as D6. It is signable in the
sense that it contains no blank; it is not presentable until a seal exists to be sealed.

> **Relationship to tonight's package.** `P-AK-SEARCH-1` **narrows** the *consumption* half of
> `gpu-cross-device.md:16-21`, and tonight's item 3 appends the required one-sentence cross-reference
> to Annex G recording that narrowing. This amendment addresses the *decision-grade* half, which is a
> different clause with a different trigger: consumption bites on every GPU T1 round; decision-grade
> bites only when a freeze needs new GPU evidence. The two are independent, and §S below neither
> assumes nor requires tonight's item 3.

---

## 1. The defect this closes

P-GPU-1 states that a decision-grade claim *"MAY ONLY be produced on a **production-named kernel**"*,
and that measurements on any experimental or candidate kernel are observations only
(`gpu-cross-device.md:16-21`). Retro-certification is permitted but strictly post-promotion, with no
partial upgrades (`:44-48`), and the standing consequence is explicit: *"Ratification of this protocol
enables that post-promotion certification; it never upgrades pre-promotion experimental numbers"*
(`:50-53`).

The consequence is circular. A candidate cannot produce the decision-grade GPU evidence needed to
decide whether it should become production, because it is not yet production. The v8 process resolved
this by provisional promotion followed by production-era certification — defensible once, under
operator attestation, but not a repeatable basis for evaluating candidates before they are promoted.

The CPU side has no equivalent defect. `bench-cpu.md:38-44` defines candidate release identity, and
`:83-88` defines a candidate-versus-production promotion decision rule with ratio bands.
P-BENCH-PREFILL-1 is a candidate-versus-production protocol by construction. **This amendment is
GPU-scoped and does not touch Annex B.**

## 2. What does NOT change

- The **consumption** prohibition is untouched. Experimental GPU measurements still MUST NOT be
  consumed by AutoPilot or any automated optimizer. That prohibition is lifted, narrowly and
  separately, by `P-AK-SEARCH-1` for ranking inside experimental worktrees only.
- Every P-GPU-1 mandatory evidence field remains mandatory. A sealed candidate is not a relaxation of
  evidence; it is a relaxation of *provenance* only, purchased with strictly more identity binding.
- No-partial-upgrades retro-certification (`:44-48`) is unchanged for artifacts that are not sealed
  candidates.
- Nothing here authorizes a freeze, a cutover, an era-registry write, or an AutoPilot baseline apply.
  All four remain human-only (`MEASUREMENT.md:140-142`).

## 3. Normative text (proposed append to Annex G)

> ### P-GPU-1 §S — Sealed-candidate release evidence (AMENDMENT, ratified `<APPLY_DATE>`)
>
> **Scope.** This section creates exactly one exception to the kernel-provenance rule above. It
> applies only to a **sealed release candidate** under evaluation for promotion to a new
> production-named kernel, and only for the release-gating comparison against the incumbent
> production kernel. It does not apply to exploratory, search, ranking, or campaign-internal
> measurement, which remain observations.
>
> **Definition — sealed release candidate.** An artifact is a sealed release candidate ONLY IF ALL of
> the following are recorded, immutable at seal time, and hash-bound into one bundle:
>
> 1. **production base** — the incumbent production branch, commit, and binary SHA-256, verified clean;
> 2. **candidate commit** — a clean, committed tree whose built binary reports that commit;
> 3. **ancestry proof** — the candidate commit is a descendant of the production base;
> 4. **complete source snapshot** — content-addressed tree hash, plus the project agent-file overlay
>    required by the promotion checklist;
> 5. **toolchain identity** — compiler, ROCm/HIP runtime and driver versions, build flags, and build
>    environment;
> 6. **binary and linkage identity** — SHA-256 of the binary and of every linked library, plus `ldd`
>    output, per the Annex B release-identity pattern (`bench-cpu.md:38-44`), which this section
>    adopts by reference rather than restating;
> 7. **evaluator identity** — the SHA-256 of the evaluator bundle that produced the evidence, as
>    resolved at run time and recorded in the run attestation, together with the **runtime
>    source-label attestation** (the resolved path and content hash of every module actually loaded).
>    This section names no bundle layout and no hashing scheme: it requires that a single value
>    identify the evaluator, that it be re-verified at seal time against the value every contributing
>    run recorded, and that any disagreement void the seal. *(Contract, not a literal: whatever
>    directory-hash scheme the evaluator ships, the property is that the seal and the runs agree on
>    one value.)*
> 8. **derived scope manifest** — the release plan under which the evidence was collected, identified
>    by its SHA-256 over its serialized bytes, plus the plan's own declared cell enumeration. This
>    section names no plan format: it requires that the plan be a **single hashable artifact** rather
>    than a view computed on demand, that every cell in the evidence matrix resolve to a cell the plan
>    enumerates, and that the plan hash be recorded in the seal. A plan that cannot be hashed as one
>    object cannot be sealed against. *(Contract on the release-plan compiler.)*
> 9. **evidence hash tree** — a single root hash over the complete evidence set the seal covers,
>    computed from a per-file `SHA256SUMS` under the campaign evidence root
>    (`MEASUREMENT.md:149-156`), with every artifact carrying the durability class the retention
>    clause of `MEASUREMENT.md` §5 defines. This section names no tree layout: it requires that one
>    value cover the whole evidence set, that it be recomputable from the retained files, and that
>    `hash-and-provenance-only` artifacts contribute their recorded hash rather than being silently
>    absent. *(Contract on the evidence root, satisfied by any layout meeting it.)*
> 10. **immutability attestation** — the seal is created with a no-replace operation into a containing
>     directory that is fsynced, and no component is rebuilt or edited after sealing.
>
> A candidate missing ANY field is not sealed, and its measurements remain observations. **Each of
> fields 7–9 is satisfied by a recorded value plus a recomputation, never by a promise:** a seal whose
> field cannot be recomputed from the retained artifacts at verification time is not a seal.
>
> **What a sealed candidate MAY do.** Produce P-GPU-1 decision-grade evidence for, and only for, the
> release-gating comparison against the named incumbent, provided every P-GPU-1 mandatory evidence
> field is present and the run satisfies P-GPU-1's host-interference, device-claim, and
> before-and-after state requirements.
>
> **What a sealed candidate MAY NOT do.** Gate any keep / revert / deploy / buy / close decision other
> than the single promote decision it was sealed for; be consumed by an automated optimizer; be
> retro-certified into a different comparison; survive any post-seal modification; or be reused across
> a changed evaluator, scope manifest, host topology hash, or instrument era.
>
> **Backend scope — a backend owes evidence only if its binary changed.** A source tree may serve
> more than one production backend (`llama.cpp` serves both `cpu` and `gpu`). For each backend the
> tree serves, the release plan compiler MUST determine whether the candidate's binary for that
> backend differs from the incumbent's, by the two-stage test in §4. Where it does not differ, the
> incumbent's evidence transfers by identity, that backend's cells are dropped from the matrix, and a
> transfer receipt naming the incumbent evidence artifacts and their SHA-256s is recorded. Where it
> differs, that backend owes full candidate-grade evidence under its own protocol.
>
> **Prospective.** Applies only to seals created after ratification. No pre-amendment experimental
> artifact may be retro-sealed.
>
> **Grammar.** `<metric> <value> [P-GPU-1 §S, sealed <seal_sha256[:12]>, vs <incumbent_version>,
> n=<reps>, YYYY-MM-DD, attest <ref>]`.

## 4. The backend-unchanged test

**This section corrects the first formulation of the escape, which was wrong.** Naive byte-identity of
the built binary does not work: llama.cpp/ROCm builds embed build IDs, timestamps, and absolute paths,
so a freshly built binary is essentially never byte-identical to one built months earlier in a
different directory. A test formulated that way would never fire, and the escape would be decorative.

The test is therefore two-stage, with the cheap stage as the gate and the expensive stage as
confirmation.

**Stage 1 — source-closure identity (the gate).**

1. Obtain the backend's build-target dependency closure from the build system itself — the generated
   dependency information for the target (CMake/Ninja depfiles), never a hand-maintained file list or
   a directory-prefix guess.
2. `git diff --name-only <production_base>..<candidate_commit>` restricted to that closure.
3. The backend is **unchanged** if and only if that diff is empty **and** toolchain identity, build
   flags, and build environment are identical between the two builds.

This is deterministic, cheap, and independent of build reproducibility.

**Stage 2 — normalized binary confirmation (required before dropping cells).**

1. Rebuild the **production base commit** in the candidate's build environment — same paths, same
   toolchain, same flags — so both binaries share one non-determinism regime.
2. Compare normalized hashes: `.text`, `.rodata`, `.data.rel.ro`, and the dynamic symbol table,
   excluding `.comment`, `.note.gnu.build-id`, and debug sections.
3. Identical ⇒ confirmed unchanged.

**Disagreement is a hard finding, never a silent preference for the cheaper answer.** If stage 1 says
unchanged and stage 2 disagrees, the closure is wrong or the build is not deterministic. The backend
owes full evidence, and the discrepancy is recorded as a defect against the build-identity machinery.

**Transfer validity.** Even for an unchanged backend, the incumbent's evidence transfers only if it is
still in scope: same models and recipes, same host topology hash, and no instrument-era boundary
crossed for that backend. Otherwise the cells are re-measured despite the binary being unchanged.

## 5. The five former `[BLOCKED-ON]` bindings, converted

Each was blocked because it named a **format** the implementation had not chosen. Each is now a
**property** the implementation must exhibit, which the constitution can state without knowing the
format — the same conversion `P-AK-SEARCH-1` §1 performs, and for the same reason: protocols are
append-or-version and never silently edited (`MEASUREMENT.md:116-118`), so a ratified format is
expensive to walk back and a ratified property is not.

| Former blocked binding | Was blocked on | Converted to | Where |
|---|---|---|---|
| evaluator bundle SHA-256 semantics | AK3 | **Contract** — one value identifies the evaluator; the seal re-verifies it against the value every contributing run recorded; disagreement voids the seal. No layout, no hashing scheme | §3 field 7 |
| derived scope manifest format | AK5 | **Contract** — the release plan is a single hashable artifact; every evidence cell resolves to a plan-enumerated cell; the plan hash is in the seal. No format | §3 field 8 |
| evidence hash tree | AK1 | **Contract** — one root hash over the evidence set, recomputable from retained files under `MEASUREMENT.md:149-156`, with `hash-and-provenance-only` artifacts contributing their recorded hash. No tree layout | §3 field 9 |
| build-target closure extraction | AK2/AK3 | **Procedure** — the closure is obtained *from the build system's own generated dependency information*, never from a hand-maintained list or a directory-prefix guess. The procedure is stated; which build system emits it is an implementation detail | §4 stage 1 |
| device-claim receipt field | AK2 | **Contract + disclosed gap** — §3's *"MAY do"* clause requires P-GPU-1's device-claim requirement to be satisfied; §6 records that no conforming MI210 device claim exists on this host today, so no seal can be produced until one does. The protocol states the requirement; it does not invent the mechanism | §3, §6 R1 |

**What remains genuinely blocked is presentation, not text.** Every binding above is satisfiable by
an implementation that has not been written, which is what a contract is for. But a sealed-candidate
amendment cannot be *presented* until there is a seal to verify it against — its acceptance test is
that a real seal passes §3 and a deliberately-defective one fails. That is the draft-early /
ratify-last sequencing recorded in the owning handoff §14 AK0, and it is why this item rides
attestation 2.

## 6. Ratification checklist (attestation 2)

- [ ] **Acceptance test, run before presentation:** a real sealed candidate passes every §3 field, and
      a deliberately-defective seal (one rebuilt component, one absent evidence file, one mutated
      plan) fails at the expected field. A contract that has never rejected anything is untested.
- [ ] Append §S to `measurement/protocols/gpu-cross-device.md` — append, never edit in place.
      Substitute `<APPLY_DATE>`.
- [ ] Add the one-line `MEASUREMENT.md` CHANGELOG entry, naming
      `measurement/protocols/gpu-cross-device.md:16-21`'s absolute form as what is superseded.
- [ ] Name the superseded receipt path and SHA-256 for the provenance rule's absolute form (the v2
      apply, 20260730T103218Z).
- [ ] Add or update the `MEASUREMENT.md` §2 protocol-registry row.
- [ ] Record every semantic delta versus the current annex text in
      `artifacts/operator/autokernel-policy-draft/RATIFICATION_LEDGER.md` (full path).
- [ ] Verify every cited evidence path resolves in-repo, using
      `epyc-inference-research/scripts/validate/check_evidence_durability.py` (the validator lives in
      the research repo, not epyc-root as `MEASUREMENT.md:155` implies).
- [ ] Pre-validate the apply command sequence end-to-end.
- [ ] Present alongside `epyc.autokernel.operator_waiver.v1` as one attestation with strikeable lines.

## 7. Open questions for the operator

1. **Placement — RESOLVED.** §S stays in Annex **G**, where the rule it amends lives. It *replaces*
   the absolute form of a G clause rather than narrowing it, so under `Annex-K-container.draft.md`
   §2 admission test (3) it is an amendment to the owning annex, not an Annex K protocol. Recorded as
   answered so the question is not reopened by accretion.
2. **Single-use seals.** The draft forbids reusing a seal across a changed evaluator, scope manifest,
   topology hash, or era. That is strict — a failed freeze followed by an evaluator patch would
   require a fresh seal and a fresh T3. The alternative is to allow reuse when the change is provably
   irrelevant to the affected cells, which is cheaper but introduces exactly the "provably irrelevant"
   judgement call this protocol family otherwise avoids. Recommendation: keep it strict.
3. **Whether §S should also cover the speech kernels.** `whisper.cpp` and `qwentts.cpp` have no GPU
   protocol at all yet, so their sealed-candidate rules can be written natively when their protocols
   are authored, rather than inherited from a GPU amendment. Recommendation: leave them out.
