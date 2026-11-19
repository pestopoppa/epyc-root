# Decision package: cpu-decode-roofline-program

Destination handoff `handoffs/active/cpu-decode-roofline-program.md` · fold 16 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 2 · excluded: 0. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. MEAS-1 / OP-41: CPU co-tenancy between builds/benches and timing arms (fencing excluded). Choose A, B or C.

- Context: `handoffs/active/cpu-decode-roofline-program.md:1021@7eb7a4a3c911` (manifest `handoffs/active/cpu-decode-roofline-program.md:1021@3ac825873dfb`, id `3c6895f119bf`)
- Gated worker box(es): `handoffs/active/cpu-decode-roofline-program.md:1021`, `R23-49` (handoffs/active/autokernel-rebuild-program.md:1803)

- **Option A (recommended)**: (A) Serialize: take the region-lock `bench` role around build AND bench (compiles alone suffice, per the peak discriminator). *Tradeoff:* Removes the peak contention that drives the A/A spread; costs autokernel throughput while builds wait.
- **Option B**: (B) Publish a schedule: heavy work advertises windows and sub-5% timing avoids them. *Tradeoff:* Keeps throughput; relies on every producer advertising, and a missed advert re-contaminates.
- **Option C**: (C) Accept and regress: keep measuring, log foreign load per arm, regress it out. *Tradeoff:* No throughput cost; widens every CI and needs the per-arm load log to be complete.

**Recommendation: A.** HARNESS-1 shows the discriminator is the peak, so serialising compiles alone covers it at the lowest cost.

## 2. XFER-4b: the iqk IQ4_NL/MXFP4 allowlist `8c4b282ae` was held out of the all-keeps fold; re-decide it?

- Context: `handoffs/active/cpu-decode-roofline-program.md:3879@7eb7a4a3c911` (manifest `handoffs/active/cpu-decode-roofline-program.md:3879@3ac825873dfb`, id `c41fffea367f`)
- Gated worker box(es): `XFER-4b` (handoffs/active/cpu-decode-roofline-program.md:3879)

- **Option A (recommended)**: Run the prefill A/B plus a paired task-quality eval, then re-decide. *Tradeoff:* Settles the -40.6% c5 signal against quality; costs a CPU window and an eval.
- **Option B**: Keep it held out without re-measuring. *Tradeoff:* No compute; the allowlist stays out of the champion.

**Recommendation: A.** The box names exactly those two measurements as the re-decision basis; the hold-out was pending evidence, not a rejection.

