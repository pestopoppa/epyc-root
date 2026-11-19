# Decision package: mi210-serving-program

Destination handoff `handoffs/completed/mi210-serving-program.md` · fold 11 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 4 · excluded: 1. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. If F1 justifies proceeding, amend the instrument era / skew gate (`:26` static-at-load and roadmap:254) to record that the skew verdict tested caching, not overlap?

- Context: `handoffs/active/fable5-window2-findings-02-heterogeneous-gpu.md:335@7eb7a4a3c911` (manifest `handoffs/active/fable5-window2-findings-02-heterogeneous-gpu.md:335@3ac825873dfb`, id `6081d798aab4`)
- Gated worker box(es): `handoffs/active/fable5-window2-findings-02-heterogeneous-gpu.md:335`

- **Option A (recommended)**: Amend both records when F1 lands. *Tradeoff:* Keeps the measurement record honest; a trust-boundary amendment needs the operator.
- **Option B**: Leave as-is. *Tradeoff:* No amendment work; the skew gate keeps a verdict about the wrong mechanism.

**Recommendation: A.** A gate that names the wrong mechanism misroutes later decisions; the amendment is conditional on F1 anyway.

## 2. intake-576 (Nemotron Diffusion): implement or procure a maintained stock-v7 server/parser path, design diffusion-aware constrained decode, or keep it out?

- Context: `handoffs/active/gpu-acceleration-path.md:568@7eb7a4a3c911` (manifest `handoffs/active/gpu-acceleration-path.md:568@3ac825873dfb`, id `9fda0f8b091a`)
- Gated worker box(es): `handoffs/active/gpu-acceleration-path.md:568`

- **Option A**: Implement a maintained server/parser path with separated reasoning/content. *Tradeoff:* Unblocks production admission; ongoing maintenance of a parser path.
- **Option B**: Design diffusion-aware constrained decode. *Tradeoff:* Most capable; largest build.
- **Option C (recommended)**: Keep Nemotron Diffusion out of production roles. *Tradeoff:* No cost; the model stays bench-only despite running on the MI210.

**Recommendation: C.** No role in the box needs it today; per policy missing plumbing is a build cost, so re-open as option A when a role names the need.

## 3. Sign OP-81: the GPU host-thread pinning stack change (GPS-PIN-1, ratify script `ratify_stackchg_gpupin_20261022.sh`)?

- Context: `handoffs/active/gpu-serving-tie-in-program.md:321@7eb7a4a3c911` (manifest `handoffs/active/gpu-serving-tie-in-program.md:321@3ac825873dfb`, id `8305ebc4def9`)
- Gated worker box(es): `GPS-PIN-1` (handoffs/active/gpu-serving-tie-in-program.md:321)

- **Option A (recommended)**: Sign; owners reload pinned roles starting with :8083 and run the P1 probe. *Tradeoff:* Deterministic host threads for every pinned launch; one reload per pinned role.
- **Option B**: Defer. *Tradeoff:* No reloads; ROCr threads keep landing on all CPUs (1/196 pinned observed).

**Recommendation: A.** The defect is measured and the package is complete with a ratify script; contention on the SMT siblings affects every GPU number.

## 4. AXA-2 teleport: how to treat the mid-stream quant change (Q4-CPU -> IQ2-GPU is a model swap)?

- Context: `handoffs/active/mi210-big-model-and-acceleration-roadmap.md:104@7eb7a4a3c911` (manifest `handoffs/active/mi210-big-model-and-acceleration-roadmap.md:104@3ac825873dfb`, id `32b1da682efd`)
- Gated worker box(es): `AXA-2` (handoffs/active/mi210-big-model-and-acceleration-roadmap.md:104)

- **Option A**: Restrict teleport to IQ2-acceptable tails/roles. *Tradeoff:* Keeps 122B teleport; quality change mid-stream for those roles.
- **Option B (recommended)**: Same-quant only. *Tradeoff:* No quality discontinuity; forces sub-122B targets on the GPU.

**Recommendation: B.** Same-quant keeps the validation experiments interpretable; the IQ2 option can follow once the divergence test (e) quantifies the swap.

## Excluded (not delivered)

- `P2-5i` (handoffs/active/gpu-serving-tie-in-program.md:194): **decided**. Box states the prohibition is honoured and "nothing to do"; standing rule, not a choice.
