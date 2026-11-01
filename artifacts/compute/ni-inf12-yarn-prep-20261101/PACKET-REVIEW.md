# YARN r2 review packet

- Fresh row identity: `codex-ni-yarn-e1-mem-phase-r2-20261101`; old r1 admission failure stays immutable.
- Exact planned maximum: A1/high N19, 498,965 tokens; rendered SHA `8307912edb92fa5df0de817f687e0651fa5e05209aefbb2de9c03db303caa5c4`.
- Request manifest SHA `2ea9ec467f77fffdf3079d70c1a96e03041e62c2e9d2d380c53eb31c638c30e0`.
- Recipe SHA `fbff79e22b601fb32210338fd3bd90e4a124730a439fa019dc10c14ede3a8161`; fixture SHA `f25a42521e041e0dc6530075fb6df3afc3695d044f34c5857bc215b1e0f28cdf`.
- Source dependency SHA `e958f225c98dd4000c453492548dda05331fba34a93938207f2bee87c0dbd20f`; candidate engine only, not deployed canonical source.
- Qualification recipe binds E1/W binaries and four DSOs each, model edge identity, template, exact request and explicit split-KV mode.
- Paired E1/W A1/high full 400k seed + exact 500k N19 work unit is required; current-image complete timing is MISSING.
- Three-pair historical floor 17,127.348s (~4.76h), before loads/probes/analysis/cleanup; +25% planning reserve ~5.95h is not a fit/adequacy proof.
- Six original science cells unchanged; qualification is not the scientific verdict.
- No READY, keeper qualification, native GPU test, or manifest publication performed.
- Behavioral/model-free suite: 8 passed, including empty/cross-recipe event rejection, request/hash/KV/context refusal cases, and owner-booking/window validation. Python compile, shell syntax, and all 52 source hashes passed.
