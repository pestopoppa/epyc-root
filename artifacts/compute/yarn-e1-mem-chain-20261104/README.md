# YARN-E1-MEM continuous A1 chain

Historical E1 source 9a3f1392a (version 10325), Qwen3.8-27B Q8_0. One A1 YaRN server, np1/context 524288, q8_0 KV, no draft; smoke then 128k, 240k, 400k, 500k on that same process. Peak own-PID VRAM is lower-is-better. The existing box requires a fully captured continuous-chain peak at most 55 GiB, or attribution of the excess; safety stop remains 63.8 GiB. No current champion, quality, throughput, or production claim.

Row: `codex-ni-yarn-e1-mem-chain-r1-20261104`. Live launcher and immutable prepared inputs are under `/mnt/raid0/llm/tmp/yarn-e1-mem-chain-20261104/`. These files preserve the driver and preparation/specification source; the launcher deliberately points at that scratch directory. `SOURCE.sha256` also identifies the external prepared input segments and sampler/shim files retained with the row; this directory is not a standalone benchmark checkout.

The full model digest and heavy input accounting were prepared once outside the grant. The content-hashed image is bound to the unique source version; launch checks image and harness digests, then inexpensive model snapshot metadata. Native response token accounting remains part of measurement. The precomputed segment lengths are used only for the existing cache-reuse allowance; native prompt/cache token counts remain observed. Each phase requires five successful needle calls, one local probe and an own-PID residency observation during its window. Raw custody is sealed after all owned processes are confirmed stopped. Partial attempts stay explicit.

The publisher returned GPU-busy and queued the native entry smoke. This is submitted, **not yet smoke-PASS or readied**. No long inference was started by this session. The queued smoke must exercise the actual E1/A1 server and completion path before admission; the long chain runs only through its eventual grant.

Engineering checks: three model-free capture-validator fixtures passed; the separate owned-child cleanup regression passed with a real captured non-inference child and no GPU. The native smoke is isolated from the long chain’s output directory.

Integration note: the source/spec here preserve the original submission at a 3600 s cap. Incoming main records operator approval on 2026-11-04 to raise the live CHAIN window to 6800 s. That later amendment is authoritative; this archived preparation is not a claim about current launcher contents or a completed run.
