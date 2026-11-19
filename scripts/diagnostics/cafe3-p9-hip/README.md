# Native HIP P9 publication (2026-11-19)

CAFE-3 row `df2-cafe3-p9-hip-20261119` was submitted through `publish_row.py`.
The publisher exited 0 and reported **GPU busy: smoke queued**. This is not a
smoke PASS, ready qualification, native inference result or P9 verdict.

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
and bounded zero-recovery policy as CPU. The smoke executes only the compiled
CLI with devices hidden and no model load. No production kernel is changed.

Next: consume the queued smoke event, repair any reported failure, then file the
native result when its scheduled grant completes. Existing CPU P9 and CAFE-4 R5
rows remain independent; do not duplicate them.

## Sealed file SHA-256

- `corpus.jsonl`: `28fe6166386a25b548d5529db02df31a4b7f3e24e5180e92982f7bc69ebdcd31`
- `inputs.json`: `751b336cb42b495b5a64257fb0d056ae472a7a539ca43d45f49f0e2d11b86f07`
- `launch.sh`: `4c2e18bb514b1fa8af46c4964e244eab64763b4757ec379cee12437ae1e20d6e`
- `prepared.json`: `7fea19f1074fa5596f501ba00badf61d60ce1715abedc48ebd0cea4c2eb1cc78`
- `protocol.json`: `86f118bae1066a657ca38d51b318b0dc10f4ae393dcfae875272a0b815068b18`
- `runtime.py`: `67c79b94b86ffe274e3b3b11552aa7d11d76fd663a216fcf94c4c87aa3b1fd7a`
- `spec.json`: `ae4c922a349a470d812e2e8cfddab3b7c14b14db18001c3ef7db052896bc7ba3`
