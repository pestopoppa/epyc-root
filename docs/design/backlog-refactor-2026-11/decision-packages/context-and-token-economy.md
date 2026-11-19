# Decision package: context-and-token-economy

Destination handoff `handoffs/active/context-and-token-economy.md` · fold 6 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 2 · excluded: 0. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. Push/PR the sub-decision-taxonomy feature branch (RAO/ReDel substrate spike)?

- Context: `handoffs/active/rao-redel-substrate-spike.md:420@7eb7a4a3c911` (manifest `handoffs/active/rao-redel-substrate-spike.md:420@3ac825873dfb`, id `685e8563a9bc`)
- Gated worker box(es): `handoffs/active/rao-redel-substrate-spike.md:420`

- **Option A (recommended)**: Push and open a PR. *Tradeoff:* Branch reviewed on main.
- **Option B**: Keep it local. *Tradeoff:* Work stays unmerged.

**Recommendation: A.** A spike branch left unmerged rots.

## 2. TB-6-ROUTER: wire the np x budget surface into the router (gated on the GPU joining the orchestration stack)?

- Context: `handoffs/active/reasoning-effort-levels.md:241@7eb7a4a3c911` (manifest `handoffs/active/reasoning-effort-levels.md:241@3ac825873dfb`, id `9417d9bec026`)
- Gated worker box(es): `TB-6-ROUTER` (handoffs/active/reasoning-effort-levels.md:241)

- **Option A (recommended)**: Re-check the precondition against the current stack and activate if a GPU role serves. *Tradeoff:* The router gains a concurrency policy; needs the per-model surfaces frozen into the registry.
- **Option B**: Keep gated. *Tradeoff:* No change; the budget->concurrency half of routing stays missing.

**Recommendation: A.** The precondition text says the MI210 is bench-only; the current stack has GPU-served roles, so the gate must be re-read.

