# Decision package: model-evaluation-queue

Destination handoff `handoffs/active/model-evaluation-queue.md` · not in the 1a list; after the 1a folds, manifest fold 10 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 8 · excluded: 1. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. Approve the Hy3 cases (Hy3-FP8 test vector; official IQ1_M ~90 GB as the GGUF path) for AngelSlim / architect-candidacy work?

- Context: `handoffs/active/angelslim-techniques-evaluation.md:109@7eb7a4a3c911` (manifest `handoffs/active/angelslim-techniques-evaluation.md:109@3ac825873dfb`, id `f98dff74e42a`)
- Gated worker box(es): `handoffs/active/angelslim-techniques-evaluation.md:109`, `handoffs/active/angelslim-techniques-evaluation.md:122`

- **Option A**: Approve as a test vector only. *Tradeoff:* Adds a flagship-MoE case; download and disk (~90 GB).
- **Option B (recommended)**: Keep operator-gated (no Hy3 work). *Tradeoff:* No disk/compute; AngelSlim evaluation lacks a flagship MoE case.

**Recommendation: B.** The architect-candidacy bench is itself deferred; add Hy3 when that bench is scheduled.

## 2. A3-ff: design and ratify a new direct-generation behavior screen?

- Context: `handoffs/active/architect-model-selection-bench.md:568@7eb7a4a3c911` (manifest `handoffs/active/architect-model-selection-bench.md:568@3ac825873dfb`, id `83ff1e587b9e`)
- Gated worker box(es): `handoffs/active/architect-model-selection-bench.md:568`

- **Option A**: Design a screen. *Tradeoff:* Enables role candidacy; new protocol to ratify.
- **Option B (recommended)**: No screen; FF stays a scaffold tool. *Tradeoff:* No work; FF cannot be a serving role.

**Recommendation: B.** The operator frames FF as a pre-processing tool; the gate applies only if FF is proposed for a role.

## 3. gemma4 on gfx90a: run the server-arm check of `-fa 0` (12.9% faster tg128)?

- Context: `handoffs/active/architect-model-selection-bench.md:836@7eb7a4a3c911` (manifest `handoffs/active/architect-model-selection-bench.md:836@3ac825873dfb`, id `de075c0db3b9`)
- Gated worker box(es): `handoffs/active/architect-model-selection-bench.md:836`

- **Option A (recommended)**: Run a server-arm check when worker_general moves to GPU. *Tradeoff:* Avoids a FA/MTP/long-context surprise.
- **Option B**: Run it now. *Tradeoff:* Answer ready early; GPU time for a role not on GPU.

**Recommendation: A.** worker_general is not GPU-served today; the box says do not act without the check.

## 4. OpenMLE Sandbox: reconfigure the host to cgroup v1 (gate 2)?

- Context: `handoffs/active/architect-model-selection-bench.md:856@7eb7a4a3c911` (manifest `handoffs/active/architect-model-selection-bench.md:856@3ac825873dfb`, id `d0224244af9b`)
- Gated worker box(es): `handoffs/active/architect-model-selection-bench.md:856`

- **Option A (recommended)**: Decide only after gate (1) images pull and run. *Tradeoff:* No host change now.
- **Option B**: Approve now. *Tradeoff:* Host reboot/reconfig for an unverified image path.

**Recommendation: A.** The box orders it: file (2) only if (1) succeeds.

## 5. CS-8.STT7: record the empty nemo-3.5 output on index 862 how?

- Context: `handoffs/active/conversation-stack.md:744@7eb7a4a3c911` (manifest `handoffs/active/conversation-stack.md:744@3ac825873dfb`, id `41bb2eb5ed62`)
- Gated worker box(es): `CS-8.STT7` (handoffs/active/conversation-stack.md:744)

- **Option A (recommended)**: Count as unparseable under the denominator control. *Tradeoff:* Consistent with the pinned rule.
- **Option B**: Re-run the item. *Tradeoff:* Cleaner; re-runs break resume-safety.

**Recommendation: A.** The denominator control already defines unparseable outputs.

## 6. P3-5: choose the new bake-off arms (deleted tenants).

- Context: `handoffs/active/gpu-serving-tie-in-program.md:155@7eb7a4a3c911` (manifest `handoffs/active/gpu-serving-tie-in-program.md:155@3ac825873dfb`, id `f7e4c4f244f0`)
- Gated worker box(es): `P3-5` (handoffs/active/gpu-serving-tie-in-program.md:155)

- **Option A (recommended)**: Qwen3.8-27B vs the A4 bridge as sequential control (package recommendation). *Tradeoff:* Matches the served model.
- **Option B**: Re-download the deleted Qwen3.6-27B tenants. *Tradeoff:* Keeps continuity; disk and download.

**Recommendation: A.** The served 27B is Qwen3.8; the package recommends it.

## 7. Capture search trajectories on deep-research eval runs (intake-877)?

- Context: `handoffs/active/minddr-deep-research-mode.md:208@7eb7a4a3c911` (manifest `handoffs/active/minddr-deep-research-mode.md:208@3ac825873dfb`, id `6ca412a24fdb`)
- Gated worker box(es): `handoffs/active/minddr-deep-research-mode.md:208`

- **Option A (recommended)**: Capture. *Tradeoff:* Leakage can be audited post hoc; nearly free.
- **Option B**: Skip. *Tradeoff:* No audit trail.

**Recommendation: A.** SearxNG already returns the fields.

## 8. P6b: bench Qwen3.6-35B-A3B-MTP on a fresh experimental build?

- Context: `handoffs/active/qwen-mtp-llamacpp-port.md:91@7eb7a4a3c911` (manifest `handoffs/active/qwen-mtp-llamacpp-port.md:91@3ac825873dfb`, id `3ce696ba405e`)
- Gated worker box(es): `handoffs/active/qwen-mtp-llamacpp-port.md:91`

- **Option A (recommended)**: Re-scope to the current (v10) champion and run. *Tradeoff:* Answers MTP value on today's kernel.
- **Option B**: Retire P6b. *Tradeoff:* No compute; the MTP port lacks its gate bench.

**Recommendation: A.** v8 is no longer production; a current-tree bench is the only meaningful one.

## Excluded (not delivered)

- `handoffs/active/angelslim-techniques-evaluation.md:122`: **merged** into choice for `handoffs/active/angelslim-techniques-evaluation.md:109`. Same Hy3 gating choice.
