<!-- DRAFT — NOT RATIFIED, NOT IN FORCE. Staged for operator review per
     artifacts/operator/autokernel-policy-draft/README.md (attestation 2).
     Target: measurement/protocols/gpu-cross-device.md (Annex G), appended as a new block.
     Author: AutoKernel design pass, 2026-08-02. -->

# DRAFT — P-GPU-1 amendment: sealed-candidate release evidence

**Status:** SKELETON. Normative text is drafted; bindings marked **[BLOCKED-ON AKn]** reference
artifacts that do not yet exist and MUST be filled before this is presented for ratification.
**Amends:** `P-GPU-1 — MI210 GPU canonical throughput (RATIFIED 2026-07-19)`, Annex G.
**Supersedes:** the absolute form of P-GPU-1's kernel-provenance rule
(`measurement/protocols/gpu-cross-device.md:16-21`) — *not* the rule itself, which survives with one
enumerated exception. Prior receipt path and SHA-256 to be named at ratification.
**Owning handoff:** `handoffs/active/autokernel-research-loop.md` §3.2.
**Presented in:** attestation 2 ("release authorization"), after AK5.

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

> ### P-GPU-1 §S — Sealed-candidate release evidence (AMENDMENT, ratified <DATE>)
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
> 7. **evaluator identity** — the immutable evaluator bundle SHA-256 **[BLOCKED-ON AK3]**;
> 8. **derived scope manifest** — the release plan and its SHA-256 **[BLOCKED-ON AK5]**;
> 9. **evidence hash tree** — a hash over the complete evidence directory **[BLOCKED-ON AK1]**; and
> 10. **immutability attestation** — the seal is created with a no-replace operation into a containing
>     directory that is fsynced, and no component is rebuilt or edited after sealing.
>
> A candidate missing ANY field is not sealed, and its measurements remain observations.
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

## 5. Bindings still blocked

| Binding | Blocked on | Why it cannot be written yet |
|---|---|---|
| evaluator bundle SHA-256 semantics | AK3 | the bundle's contents and hashing scheme are defined by the evaluator implementation |
| derived scope manifest format | AK5 | the release-plan compiler defines it |
| evidence hash tree | AK1 | depends on the evidence root layout and durability classes |
| build-target closure extraction | AK2/AK3 | depends on the campaign build system integration |
| device-claim receipt field | AK2 | the MI210 claim does not exist yet |

Ratifying any of these against a schema sketch risks a binding the implementation cannot satisfy, and
protocols are append-or-version and never silently edited (`MEASUREMENT.md:116-118`). Hence the
draft-early / ratify-last sequencing recorded in the owning handoff §14 AK0.

## 6. Ratification checklist (attestation 2)

- [ ] Fill every **[BLOCKED-ON]** binding from the delivered artifacts.
- [ ] Append §S to `measurement/protocols/gpu-cross-device.md` — append, never edit in place.
- [ ] Add the one-line `MEASUREMENT.md` CHANGELOG entry.
- [ ] Name the superseded receipt path and SHA-256 for the provenance rule's absolute form.
- [ ] Add or update the `MEASUREMENT.md` §2 protocol-registry row.
- [ ] Write `RATIFICATION_LEDGER.md` enumerating every semantic delta versus the current annex text.
- [ ] Verify every cited evidence path resolves in-repo (`check_evidence_durability.py`).
- [ ] Pre-validate the apply command sequence end-to-end.
- [ ] Present alongside `epyc.autokernel.operator_waiver.v1` as one attestation with strikeable lines.

## 7. Open questions for the operator

1. **Placement.** §S fits Annex G cleanly. Confirm it belongs there rather than in a new Annex K
   alongside `P-AK-SEARCH-1`.
2. **Single-use seals.** The draft forbids reusing a seal across a changed evaluator, scope manifest,
   topology hash, or era. That is strict — a failed freeze followed by an evaluator patch would
   require a fresh seal and a fresh T3. The alternative is to allow reuse when the change is provably
   irrelevant to the affected cells, which is cheaper but introduces exactly the "provably irrelevant"
   judgement call this protocol family otherwise avoids. Recommendation: keep it strict.
3. **Whether §S should also cover the speech kernels.** `whisper.cpp` and `qwentts.cpp` have no GPU
   protocol at all yet, so their sealed-candidate rules can be written natively when their protocols
   are authored, rather than inherited from a GPU amendment. Recommendation: leave them out.
