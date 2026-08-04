# Annex S — core-file deltas (everything OUTSIDE the new annex file)

Companion to [`speech.ANNEX-S-TRANSCRIBED.txt`](speech.ANNEX-S-TRANSCRIBED.txt), which is the complete
final content of the new file `measurement/protocols/speech.md`.

**Every "BEFORE" block below was read from the file as it stands today and is quoted verbatim**, not
reconstructed from the container draft's description of it. Where the container draft's description no
longer matches the file, that is called out under the delta rather than silently corrected into an
edit that would not apply.

Step 0, the only step that creates a file:

```
cp artifacts/operator/autokernel-policy-draft/speech.ANNEX-S-TRANSCRIBED.txt \
   measurement/protocols/speech.md
```

---

## D1 — `MEASUREMENT.md` layout paragraph · line 18 · container §3a

**Container draft said** the clause lives at `MEASUREMENT.md:15-20`. **It does not** — the paragraph
is at `:16-21`, and the draft's proposed replacement block is re-wrapped relative to the file, so
pasting it would rewrite four lines that are not changing. The real delta is a **one-word swap on one
line**, which is also what the Annex K apply did here (`three` → `four`, commit `759843d8`).

BEFORE — `MEASUREMENT.md:16-21`, verbatim:

```
**Document layout (v2).** This core file holds the constitution: claim grammar, metric scoping,
protocol index, noise table, governance, and retroactivity. Full normative protocol text lives in
four annexes in `measurement/protocols/`, which carry the SAME trust boundary and amendment rules as this
file — they are the constitution, filed by family or instrument class, not commentary on it. Daily-use guidance for
sessions is the digest at `agents/shared/MEASUREMENT_POLICY.md`; when in doubt, this file and its
annexes win.
```

AFTER — line 18 only; every other line in the paragraph is byte-identical:

```
five annexes in `measurement/protocols/`, which carry the SAME trust boundary and amendment rules as this
```

Changed words: `four` → `five`. The phrase *"filed by family or instrument class"* is already present
(the Annex K apply put it there); no further change is needed to accommodate a modality-filed annex.

---

## D2 — `MEASUREMENT.md` registry key line · lines 45-47 · container §3b

BEFORE — `MEASUREMENT.md:45-48`, verbatim:

```
Full normative text: **B** = `measurement/protocols/bench-cpu.md`, **Q** =
`measurement/protocols/quality-eval.md`, **G** = `measurement/protocols/gpu-cross-device.md`,
**K** = `measurement/protocols/kernel-research.md`.
Status: ✅ ratified, 📋 staged (operator-apply).
```

AFTER:

```
Full normative text: **B** = `measurement/protocols/bench-cpu.md`, **Q** =
`measurement/protocols/quality-eval.md`, **G** = `measurement/protocols/gpu-cross-device.md`,
**K** = `measurement/protocols/kernel-research.md`,
**S** = `measurement/protocols/speech.md`.
Status: ✅ ratified, 📋 staged (operator-apply).
```

Changed: the `.` after `kernel-research.md` becomes `,` and one line is added. The container draft
wrote the S clause inline and flagged *"(Restore `.md` at transcription.)"* — restored here.

**+1 line.** Everything from the old line 48 onward moves down by one.

---

## D3 — `MEASUREMENT.md` §2 registry rows · appended after line 68 · container §3c

BEFORE — the last two rows of the table plus its terminator, `MEASUREMENT.md:67-70`, verbatim:

```
| P-DFLASH-LINEUP-1 | DFlash lineup enablement (per-lane) | acceptance + t/s ratio (↑) | ✅ 2026-07-25 | G |
| P-AK-SEARCH-1 | Kernel-candidate search inside experimental worktrees, per-backend | search verdict — **not a claim**; direction carried per record | ✅ 2026-08-03 | K |

## 3. Claim grammar & examples
```

AFTER — eight rows inserted immediately after the `P-AK-SEARCH-1` row:

```
| P-DFLASH-LINEUP-1 | DFlash lineup enablement (per-lane) | acceptance + t/s ratio (↑) | ✅ 2026-07-25 | G |
| P-AK-SEARCH-1 | Kernel-candidate search inside experimental worktrees, per-backend | search verdict — **not a claim**; direction carried per record | ✅ 2026-08-03 | K |
| P-STT-1 | STT transcription correctness: corpus, normalization, match rule, failure taxonomy | corpus WER (↓) + transcript-identity verdict | ✅ 2026-08-03 | S |
| P-STT-2 | STT speed: real-time factor, per-request latency, batch throughput | RTF (↓) · latency s (↓) · audio-s/wall-s (↑) | ✅ 2026-08-03 | S |
| P-STT-3 | STT stability, memory growth, audio-input identity, op-coverage integrity | verdict — **not a claim** | ✅ 2026-08-03 | S |
| P-STT-REL-1 | STT kernel-release decision rule (whisper.cpp tree) | verdict `PASS`/`FAIL`/`PASS_WITH_WAIVER` — **not a claim** | ✅ 2026-08-03 | S |
| P-TTS-1 | TTS text/audio identity and deterministic/numerical checks | identity + numerical verdict — **not a claim** | ✅ 2026-08-03 | S |
| P-TTS-2 | TTS intelligibility floor and reference-waveform distance (human-independent) | round-trip WER (↓) floor + spectral distance (↓) | ✅ 2026-08-03 | S |
| P-TTS-3 | TTS speed: first-audio latency, real-time factor, synthesis throughput | TTFA ms (↓) · RTF (↓) · audio-s/wall-s (↑) | ✅ 2026-08-03 | S |
| P-TTS-REL-1 | TTS kernel-release decision rule (qwentts.cpp tree) | verdict `PASS`/`FAIL`/`PASS_WITH_WAIVER` — **not a claim** | ✅ 2026-08-03 | S |
```

**Two deliberate departures from the container draft's row block, both flagged rather than assumed:**

1. **Status is `✅ 2026-08-03`, not `📋 staged`.** The draft was written before the apply. `📋 staged`
   means *"drafted, awaiting operator apply"*; a row landing in the same transaction that ratifies the
   protocol is ratified. This matches exactly what the Annex K apply did — its draft row also said
   staged, and the applied row reads `✅ 2026-08-03` (commit `759843d8`).
2. **`— **not a claim**` added to the four verdict rows.** Annex K's row carries that marker
   (`search verdict — **not a claim**`), the drafts' own grammar lines say each of these protocols
   emits a verdict and not a claim, and the registry is the surface a reader consults first.

`P-TTS-4` is deliberately absent: TTS stability and op-coverage integrity are governed by `P-STT-3`'s
clauses, which are written backend-agnostically and cited by reference from the TTS family rather than
duplicated. Where a rule already lives, the amendment goes (`kernel-research.md:22-23`).

**+8 lines.**

---

## D4 — `MEASUREMENT.md` CHANGELOG · inserted immediately after the `## CHANGELOG` heading · container §3d

BEFORE — `MEASUREMENT.md:244-250`, verbatim:

```
## CHANGELOG

- **2026-08-02 (v2.x)** — §5 gains **evidence durability**: evidence for a ratified claim must
  live in-repo under `epyc-inference-research/data/<campaign>/` with hashes and a README;
  scratch paths may not be the citation of record. Closes a gap where the constitution
  required evidence hashes but never required the evidence to survive. Enforced by
  `scripts/validate/check_evidence_durability.py`.
```

AFTER — the new bullet becomes the first entry, matching where the current newest entry sits:

```
## CHANGELOG

- **2026-08-03 (v2.x)** — AMENDMENT: **Annex S** (`measurement/protocols/speech.md`) created as a
  **fifth** annex, filed by modality, holding the STT (`P-STT-1`, `P-STT-2`, `P-STT-3`,
  `P-STT-REL-1`) and TTS (`P-TTS-1`, `P-TTS-2`, `P-TTS-3`, `P-TTS-REL-1`) protocol families — the
  first measurement protocols of any kind for the `whisper_stt` and `qwentts_tts` backends.
  Supersedes the layout sentence at `:16-21` (`four` → `five`) and the annex key line at `:45-47`,
  both as amended 20260803T083005Z; §2 gains eight rows. `P-AK-SEARCH-1`'s owning-annex set is
  **extended** from "B, Q or G" to "B, Q, G or S", with the cross-reference appended in
  `kernel-research.md` in the same apply. Prospective; retro-certifies nothing.

- **2026-08-02 (v2.x)** — §5 gains **evidence durability**: evidence for a ratified claim must
  live in-repo under `epyc-inference-research/data/<campaign>/` with hashes and a README;
  scratch paths may not be the citation of record. Closes a gap where the constitution
  required evidence hashes but never required the evidence to survive. Enforced by
  `scripts/validate/check_evidence_durability.py`.
```

**Finding — the container draft's `<APPLY_DATE>` placeholder is resolved to `2026-08-03`, and the
precedent it points at is missing.** `MEASUREMENT.md` §5 requires every amendment to add *"a one-line
entry to the CHANGELOG block at the end of this core file"*. **The Annex K apply did not do this.**
`RATIFICATION_PACKAGE.md` §E.10 specifies five CHANGELOG bullets for attestation 1a, and none of them
is in `MEASUREMENT.md` today — its newest CHANGELOG entry is still 2026-08-02, while five ratified
2026-08-03 blocks (`MI210-SUBSTRATE-CONSTANTS-1`, `AGGREGATION-SPEEDUP-1`, `PAIRED-CI-1`,
`CENSORING-1`, `CONFORMANCE-VECTORS-1`) sit *below* the CHANGELOG with no entries. The apply script
itself defers them (`apply_ratification.sh:573`: *"add the CHANGELOG bullets (package §E.10) for the
items that landed"*), and the deferral was never closed. **This is not an Annex S delta and I have not
written it**, but the operator may wish to land the five missing Annex-K-era bullets in the same edit,
since the file is open anyway.

---

## D5 — repo-root `CHANGELOG.md` · appended at end of file, after line 911

The repo-root changelog is where the 2026-08-03 ratifications were actually recorded, one line each,
appended at EOF.

BEFORE — `CHANGELOG.md:905-911`, verbatim (file ends at 911):

```
- 2026-08-03: MI210-SUBSTRATE-CONSTANTS-1 ratified — peak FLOPS, achievable HBM bandwidth and PCIe H2D/D2H measured; ridge stated on both bases with a binding no-mixing rule.
- 2026-08-03: AGGREGATION-SPEEDUP-1 ratified.
- 2026-08-03: PAIRED-CI-1 ratified.
- 2026-08-03: CENSORING-1 ratified.
- 2026-08-03: P-AK-SEARCH-1-A1 ratified.
- 2026-08-03: CONFORMANCE-VECTORS-1 ratified.
- 2026-08-03: Annex K narrowing cross-reference added under P-AK-SEARCH-1, completing the P-AK-SEARCH-1-A1 apply per the annex admission test.
```

AFTER — one line appended:

```
- 2026-08-03: Annex S created (measurement/protocols/speech.md) — STT (P-STT-1..3, P-STT-REL-1) and TTS (P-TTS-1..3, P-TTS-REL-1) protocol families ratified; first measurement protocols for the whisper_stt and qwentts_tts backends; P-AK-SEARCH-1's owning-annex set extended to "B, Q, G or S".
```

The container draft names only `MEASUREMENT.md` §CHANGELOG (its §3d) and does not mention the root
changelog. It is included here because the entire 2026-08-03 ratification series is recorded there and
omitting Annex S would make that series incomplete.

---

## D6 — `measurement/protocols/kernel-research.md` appended cross-reference · container §3e, operator item S5

Annex K's own narrowing carve-out (`kernel-research.md:19-23`) requires that when a K-filed rule's
meaning is changed by another annex, *"the owning annex receives an appended cross-reference in the
same apply"*. `P-AK-SEARCH-1`'s scope clause enumerates the annexes a search number may be re-measured
under; Annex S extends that set.

**Placement — a decision, with the alternative stated.**

- **RECOMMENDED: append at the END of `kernel-research.md`**, after the `P-AK-SEARCH-1-A1` block
  (currently ends at line 450, file is 451 lines). **This renumbers nothing**, so every
  `kernel-research.md:NNN` anchor in Annex S, in Annex K itself, and in the owning handoff stays
  valid. It also matches the precedent for a file-level amendment: `P-AK-SEARCH-1-A1` is itself an
  end-of-file append.
- **Alternative: insert directly under the `## P-AK-SEARCH-1` heading**, beside the existing
  `**NARROWED 2026-08-03 by P-AK-SEARCH-1-A1**` bracket at line 42. Better discoverability for a
  reader arriving at the rule — the exact argument
  `artifacts/operator/ratify_annexk_narrowing_xref_20260803.sh` was written to make. **Cost: +2 lines
  at line 43, which invalidates every `kernel-research.md:NNN` anchor above 42 across the whole
  corpus, including 15 of them inside Annex S.** If the operator prefers this, the Annex S anchors
  listed in the *Anchor-drift ledger* below must each be incremented by 2 before the annex is copied.

AFTER — appended at end of file (recommended placement):

```
## P-AK-SEARCH-1 — owning-annex set extended 2026-08-03 (Annex S)

`P-AK-SEARCH-1`'s scope clause (`:55-58`) requires a search number presented outside the loop to be
re-measured under *"its owning protocol in Annex B, Q or G"*. That set is **extended to B, Q, G or S**.
Annex S (`measurement/protocols/speech.md`) supplies the owning protocols for `whisper_stt` and
`qwentts_tts`, which had none when this protocol was ratified. Nothing else in that clause changes,
`P-AK-SEARCH-1`'s search authority is neither widened nor narrowed, and no denial in *"What this
protocol does NOT authorize"* is affected.
```

This is an **append**, not an edit of the existing sentence.

---

## D7 — operator item S4 · `artifacts/operator/ratify_speech_kernel_freeze_20260731.json`

**Described, not emitted — this is a human-only receipt amendment and it is independent of D1-D6.**

The receipt records `whisper_cpp.measurements_anchored.wer_pct: 2.35`. In the source artifact
`/mnt/raid0/llm/tmp/stt_wer_results.json`, `2.35 %` is the **`faster-whisper large-v3-turbo int8 CPU
48t`** arm — CTranslate2, a different engine on a different runtime. The `whisper.cpp
large-v3-turbo f16 MI210` arm in that same file is **63 / 1870 = 3.37 %**. The receipt therefore
anchors the whisper.cpp kernel to a WER measured on a binary that is not whisper.cpp, wrong by ~1 pp
in the flattering direction, and every future `whisper_stt` non-inferiority comparison would inherit
that denominator.

`MEASUREMENT.md:174-175` forbids destroying primary records, so the recommended form is a
**superseding receipt** naming the prior path and its SHA-256 — never an in-place edit
(`MEASUREMENT.md:116-118`; `bench-cpu.md:163-168` is the in-corpus precedent for a supersession
record). Striking D1-D6 does not remove this defect and applying them does not fix it.

The finding itself is carried inside the annex (*Metric-direction defect closed by this annex*), which
is correct: an annex may record a finding, and only a human may amend a ratified receipt.

---

## Deltas the container describes that are NOT required

- **`agents/shared/MEASUREMENT_POLICY.md`** — no change. The digest does not enumerate the annexes; it
  points at `MEASUREMENT.md` as canonical authority (`:3`) and names annexes only where it cites a
  specific rule (`:38`, Annex B §E). Nothing in it becomes false when a fifth annex exists.
- **`coordination/session-bus/human_only_paths.yaml`** — no change and **no `.sha256` pin rewrite**.
  The existing entry `glob: "measurement/protocols/*.md"` (`:32-34`) already declares the new file
  human-only, so the trust boundary covers `speech.md` the moment it exists. (The separate, already
  filed defect that `check_trust_boundary_edit.sh` quotes its matcher's RHS so no `glob:` entry
  matches at runtime — `RATIFICATION_PACKAGE.md` §A, §G.2 — is unchanged by this apply and is not an
  Annex S item.)
- **No new registry outside `MEASUREMENT.md` §2.** A repo-wide search for consumers of protocol ids
  (`P-AK-SEARCH-1` as the probe) finds only narrative and apply-script references —
  `research/intake_index.yaml`, `handoffs/active/*`, `progress/*`, `.research-session.json`, and the
  two 2026-08-03 ratify scripts. There is no machine-readable protocol registry that needs eight new
  rows.

---

## Anchor-drift ledger — read before applying

**1. `MEASUREMENT.md` line anchors move.** D2 adds 1 line and D3 adds 8, so every anchor at or below
today's line 48 shifts by **+9**; D4 then shifts everything below the `## CHANGELOG` heading by a
further 9 (the length of the new bullet). Annex S carries five `MEASUREMENT.md:NNN` citations that
land in the shifted region: `:25-26` and `:39-41` are above §2 and are unaffected; `:83-84`,
`:116-118`, `:140-142`, `:146-156` and `:174-175` are not.

**These were transcribed exactly as the drafts wrote them, deliberately.** They are already 2 lines
stale — the Annex K apply inserted 2 lines above them and did not renumber — and the ratified Annex K
carries the identical stale anchors (`MEASUREMENT.md:141-142`, `:146-156`, `:83-84`, `:85-95` all
appear in `kernel-research.md` and all point 2 lines high). Writing corrected anchors into Annex S
would leave two annexes disagreeing about the same clause. The verified current locations are:

| cited as | actually at (today) | after this apply | clause |
|---|---|---|---|
| `MEASUREMENT.md:83-84` | `:85-86` | `:94-95` | comparisons only within a protocol + instrument version |
| `MEASUREMENT.md:116-118` | `:118-120` | `:127-129` | amendments: human-only, append-or-version |
| `MEASUREMENT.md:140-142` | `:143-144` | `:152-153` | the five human-only writes |
| `MEASUREMENT.md:146-156` | `:148-158` | `:157-167` | evidence must be DURABLE |
| `MEASUREMENT.md:174-175` | `:176-177` | `:185-186` | never destroy primary records |

Each of those citations carries its quoted phrase in the surrounding text, so all five remain
resolvable by search. **Recommendation:** leave them, and if the operator wants them exact, run one
renumbering pass over `kernel-research.md` *and* `speech.md` together after the apply, so the corpus
stays internally consistent.

**2. `kernel-research.md`, `gpu-cross-device.md` and `bench-cpu.md` anchors were corrected.** None of
those three files is renumbered by this apply (given D6's recommended placement), so a corrected
anchor stays correct. The drafts' values and the transcription's values:

| draft cited | transcribed as | why |
|---|---|---|
| `kernel-research.md:50-51` | `:51-52` | P-AK-SEARCH-1 Scope, "on every declared backend adapter" |
| `kernel-research.md:54-56` | `:55-58` | "its owning protocol in Annex B, Q or G" is at `:57` |
| `kernel-research.md:87-133` | `:89-135` | the nine denials |
| `kernel-research.md:120-125` | `:122-127` | denial 6, no self-amendment |
| `kernel-research.md:181-183` | `:185-186` | the `contribution_floor` declaration |
| `kernel-research.md:193-268` | `:195-270` | campaign calibration block |
| `kernel-research.md:198-200` | `:202` | "recomputed … whenever anchor identity changes" |
| `kernel-research.md:274-283` | `:277-285` | the e-process / never-an-LCB bullet |
| `kernel-research.md:302-305` | `:304-307` | anchor gate, VOID window journaled `INVALID` |
| `kernel-research.md:306-316` | `:308-318` | selection/confirmation split |
| `kernel-research.md:329-331` | `:331-332` | control 3, degraded-negative |
| `kernel-research.md:332-334` | `:333-336` | control 4, A/A |
| `kernel-research.md:362-364` | `:364-366` | oracles never self-reported; cache state |
| `kernel-research.md:381-400` | `:383-402` | search-record grammar |
| `kernel-research.md:445-448` | `:446-450` | "adopted as SHAPE, not as thresholds" |
| `gpu-cross-device.md:136-137` | `:141-142` | **was materially wrong** — `:136-137` is *"Stress is an input, not an observation"*; interleaving/order-randomization is at `:141-142` |
| `gpu-cross-device.md:149-150` | `:154-155` | **was materially wrong** — `:149-150` is *"forced role targets, never live /chat"*; "no detectable trade … is a decision, not a failed experiment" is at `:154-155` |
| `gpu-cross-device.md:106-111` | `:111-116` | `:106-111` is the tokens/s-commensurability clause; *"The net is measured directly, never reconstructed"* is at `:111-116` |

Verified unchanged and correct as drafted: `kernel-research.md:11-17`, `:19-23`, `:22-23`, `:25-26`,
`:355-360`; `gpu-cross-device.md:16-21`; `bench-cpu.md:8-10`, `:17-19`, `:21-22`, `:38-44`, `:83-88`,
`:89-90`, `:163-168`, `:231-233`.

---

## Apply order

1. `cp` the transcription to `measurement/protocols/speech.md` (step 0 above).
2. D1, D2, D3, D4 — `MEASUREMENT.md`, in that order (later anchors shift as earlier edits land).
3. D5 — `CHANGELOG.md`.
4. D6 — `measurement/protocols/kernel-research.md`.
5. D7 — independent; schedule separately.

Striking a line: **D1+D2+D4+D5 ride with the annex itself and cannot be struck separately from it.**
D3's rows may be struck per family — dropping the four `P-STT-*` rows or the four `P-TTS-*` rows —
but a protocol that is in the annex and not in the registry is unciteable under
`MEASUREMENT.md:242` (*"cite a protocol from §2. No protocol → observation, not claim"*), so striking
rows without striking the corresponding protocol text is not a coherent partial apply. **D6 must be
struck only together with the annex**: without it, `P-AK-SEARCH-1`'s owning-annex list still reads
"B, Q or G" while Annex S exists, and Annex K's own narrowing carve-out is violated by its own apply.
D7 stands alone in both directions.

---

## Two things I judged rather than transcribed, flagged for the operator

1. **The header timestamp.** Annex K's opening comment reads `RATIFIED 20260803T083005Z` — a
   second-precision apply token. Annex S's reads `RATIFIED 2026-08-03`, because the apply timestamp
   does not exist until the operator applies. If second precision is wanted, substitute the token in
   line 1 of the transcription; nothing else in the file depends on it.
2. **`attest <ref>` in three verdict grammars.** `P-STT-3`, `P-TTS-1` and the two `*-REL-1` grammars
   each end with `attest <ref>`, while their own scope lines say they emit *"a verdict, not a claim"*.
   Annex K reasoned the opposite way for its own non-claim record: *"The grammar carries no `attest
   <ref>` field. Attestation in this constitution refers to a claim (`MEASUREMENT.md:13`), and this
   record is not one."* This is a substantive normative inconsistency between the two annexes, not a
   transcription artifact, so **it was transcribed as drafted and is raised here rather than fixed**.
   Resolving it means either dropping `attest <ref>` from those four grammars or recording why a
   speech verdict attests where a search verdict does not.
