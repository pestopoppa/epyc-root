# Decision package: frontier-lab-automation

Destination handoff `handoffs/active/frontier-lab-automation.md` · fold 9 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 4 · excluded: 0. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. ID-20: decline the TRL + OpenEnv AsyncGRPO bridge and keep only the GPU-free half?

- Context: `handoffs/active/intake-derived-work-2026-07-25.md:210@7eb7a4a3c911` (manifest `handoffs/active/intake-derived-work-2026-07-25.md:210@3ac825873dfb`, id `5dd24a1560c0`)
- Gated worker box(es): `ID-20` (handoffs/active/intake-derived-work-2026-07-25.md:210)

- **Option A (recommended)**: Decline the bridge; keep the GPU-free half. *Tradeoff:* No vLLM control plane to build; RL fine-tuning via this path stays unavailable.
- **Option B**: Build the seven-endpoint control plane and a second GPU path. *Tradeoff:* Enables AsyncGRPO; needs separate GPUs, vLLM >=0.22, full-parameter FT only.

**Recommendation: A.** AsyncGRPO needs server and trainer on separate GPUs and has no LoRA path; recorded as blocked, not dismissed.

## 2. ID-25: backfill `arxiv_id: 2607.05391` and the 9-author list onto intake-362#record and intake-363#record (follow-up recorded by intake-804, never actioned)?

- Context: `handoffs/active/intake-derived-work-2026-07-25.md:273@7eb7a4a3c911` (manifest `handoffs/active/intake-derived-work-2026-07-25.md:273@3ac825873dfb`, id `c1dce92fdded`)
- Gated worker box(es): `ID-25` (handoffs/active/intake-derived-work-2026-07-25.md:273)

- **Option A (recommended)**: Backfill. *Tradeoff:* Records complete; a one-line edit each.
- **Option B**: Leave. *Tradeoff:* The recorded follow-up stays unactioned.

**Recommendation: A.** Derived from our own prior filing; cheap hygiene.

## 3. Stack-cluster HARD-archive: git-mv the superseded + runbook docs to completed/, migrate the two orphan-live boxes into the SSoT, repoint ~10 inbound links?

- Context: `handoffs/active/stale-open-audit-2026-07-18.md:106@7eb7a4a3c911` (manifest `handoffs/active/stale-open-audit-2026-07-18.md:106@3ac825873dfb`, id `b474456cb8a8`)
- Gated worker box(es): `handoffs/active/stale-open-audit-2026-07-18.md:106`

- **Option A (recommended)**: Approve the archive. *Tradeoff:* Active set loses superseded docs; two live boxes move to the SSoT.
- **Option B**: Keep them active. *Tradeoff:* No move; superseded docs stay in the active set.

**Recommendation: A.** The audit certified them superseded; the backlog refactor folds do the same kind of move.

## 4. Stale-open audit: extend to the remaining open handoffs, or close it as superseded?

- Context: `handoffs/active/stale-open-audit-2026-07-18.md:116@7eb7a4a3c911` (manifest `handoffs/active/stale-open-audit-2026-07-18.md:116@3ac825873dfb`, id `1810e7977e81`)
- Gated worker box(es): `handoffs/active/stale-open-audit-2026-07-18.md:116`

- **Option A (recommended)**: Close as superseded by the backlog-refactor manifest. *Tradeoff:* The BRF manifest scored every open box (2,808); no duplicate audit.
- **Option B**: Continue the manual read-through. *Tradeoff:* Duplicates the manifest; automated exact detection is recorded as exhausted.

**Recommendation: A.** The BRF task manifest is an exact census of open boxes.

