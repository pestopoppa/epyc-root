# Native HIP P9 publication (2026-11-19)

CAFE-3 row `df2-cafe3-p9-hip-20261119` retains the same scheduled P9 experiment.
The CLI-only smoke was rejected for absent residency; the replacement below
requires native smoke evidence without claiming a P9 verdict. Publication of the
repaired row exited 0 with **GPU busy: smoke queued**. Smoke PASS is pending;
this row is not yet ready or qualified. PASS and third-FAIL event paths are
registered for the dispatcher.

The retained row uses the qualified full HIP R3 receipt at
`/mnt/raid0/llm/tmp/df2/cafe3-hip-build-r3-20261119/RESULT.json`, SHA-256
`47b32712726fbb47f332185744f1fd7f70c984a1db2bfec03afbba6966cfff30`.
Model content identities were reused from the sealed CPU preparation only after
matching their current full file identities; no grant-time weight hashing occurs.
Corpus permissions were finalized before sealing its identity.

All five arms (static 0..3 and adaptive) share full target/draft GPU offload,
exclusive GPU placement, identical models, request settings and build. The fixed
schedule is 3 prompts x 2 repetitions x 5 arms, at most 7680 generated tokens.
The current bound native supervisor records child KFD/VRAM/local-library samples
throughout requests; the grader requires two distinct overlapping samples per
request. Timing is descriptive, with the same +1% best-static, complete identity
and bounded zero-recovery policy as CPU. The repaired publisher-only smoke runs one bounded 32-token completion with
both models fully offloaded. It requires two distinct in-request samples of the
owned child with KFD membership, nonzero VRAM, both models and all hash-bound
local llama/ggml libraries mapped, plus generated tokens and confirmed reaping.
It uses the assigned CPU count and preserves the scheduled P9 protocol. No production kernel is changed.

The original CLI-only smoke failed because it could not establish GPU residency.
Three regression tests now accept valid in-request evidence and reject observations
from a different PID, outside the request, zero VRAM, missing mappings, cutoff,
missing generation, duplicate samples or an unreaped child. The corpus content
hash is unchanged; its prepared identity was resealed after detecting a ctime
change. Model identities remain unchanged and no weight hashing was repeated.

Next: consume the repaired smoke verdict, then file the native result when its
scheduled grant completes. Existing CPU P9 and CAFE-4 R5
rows remain independent; do not duplicate them.

The first native retry exited before model load: the qualified binary rejected
`--spec-type dflash` and listed `draft-dflash` as the supported type. Both the
smoke and the scheduled arm command now use `draft-dflash`. This is a launch
correction, with no change to the P9 decision thresholds. Original native log:
`/mnt/raid0/llm/tmp/df2/cafe3-p9-hip-20261119/cafe3-p9/smoke-dbaok1y6/server.log`,
SHA-256 `329e5048406965539148e9a611c532f96ea35bb63b1c1ccc307391b4bbc0c9f2`.

Publisher sealing chmods files in the row scratch tree and therefore changes
corpus ctime after each attempt. The corpus now lives at
`/mnt/raid0/llm/tmp/df2/cafe3-p9-hip-inputs-20261119/corpus.jsonl`, outside that
tree, with unchanged SHA-256 and read-only permissions set before identity
sealing. Model and corpus identity checks remain strict; none were relaxed.

## Sealed file SHA-256

- `corpus.jsonl`: `28fe6166386a25b548d5529db02df31a4b7f3e24e5180e92982f7bc69ebdcd31`
- `inputs.json`: `2bf64dedf6e473f99c83c9df5f731d3e6a8e4bbdd8677ec2e0d3bfec00ca1014`
- `launch.sh`: `c177bf1faa52a408966540b029e15264f161e5f59c2cf4256601888260665e69`
- `prepared.json`: `7005a0caab8d516bd45d34c563324f2f91b9de41dd21461366db0486354c1599`
- `protocol.json`: `9c7a685d1a8a80bd48a914c7bc06dbced2edd00ca33d7b5c956d93bddc9316b7`
- `runtime.py`: `f4178535577ac5e0f95acf203c5cc5a14ef8d8e483570efe03fa2d9e4116aaea`
- `native_smoke.py`: `e321c3444756c101899775b93741d7599dacd9c2bd9f84837cc33f8ecc1706f3`
- `spec.json`: `3ad7c514aac6170d614fae244b06844fd27b2ab22ea7626e554853b32f751c88`
