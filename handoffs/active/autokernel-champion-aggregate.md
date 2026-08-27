# AutoKernel — the aggregate champion, and the manual→champion admission pipeline

**Owner:** operator audit session (2026-08-27), which holds GPU compute.
**Code branch:** `lane/df2-gates-20260827` (merged to `main` as `c84ecdb7`) in
**epyc-inference-research**; the champion kernel branch is `ak/champion/llama-cpp-0db32c06e3e5`
in the llama.cpp tree. This rider lives in epyc-root with the rest of `handoffs/`.
**Trigger:** operator ruling, 2026-08-27 — *"there should always be an aggregate production
candidate that holds all the experimented tweaks and is ready for promotion gate testing"* and
*"autokernel is ultimately comparing to the aggregate candidate, attempting to make it better"*.

Rider on [`autokernel-research-loop.md`](autokernel-research-loop.md) and sibling of
[`autokernel-restart-and-strip.md`](autokernel-restart-and-strip.md). Owning index row:
**INF-64** in [`inference-research-index.md`](inference-research-index.md).

## What changed, and why it is not a redefinition

The champion had been read as *the single best-performing experiment*. The operator's ruling is
that it is **the accumulation of every improvement found so far**, kept permanently ready for
promotion gate testing. AutoKernel screens against it, so each new experiment must beat the
accumulated state rather than re-derive a delta against frozen production forever.

Because Champion₀ is seeded from the production anchor, an improvement on the champion is by
construction also an improvement on production — which is what makes the accumulation safe to
compare against. Production stays the **promotion** reference: a composed champion still earns its
own T0/T1/T2 against the sealed anchor before it means anything. That is the drift catcher for a
chain of small unreplicated wins.

**AutoKernel is not responsible for promoting kernels to production** (operator, 2026-08-27). All
promotion gates are handled through operator approval at promotion time, outside AutoKernel.

## The champion as built

`ak/champion/llama-cpp-0db32c06e3e5` @ `5c278648a4af2735587b4023613310ccf2341f46` — 35 files,
+3371/−146 over frozen v9, both merges clean:

```
5bbcc5498  reviewed measurement instrument (correctness oracle, llama-bench, iqk sources)
 + c7c37a0d9  MoE-Spec  — per-batch top-B expert budget, --moe-spec-budget, default 0 (inert)
 + 2046c64e9  DFlash2   — block-diffusion drafter, a parallel --spec-type pathway
= 5c278648a  the champion            (llama-server version 10139)
```

Exposes **both** `--moe-spec-budget` and `--spec-type draft-dflash` alongside `draft-mtp`: one
kernel serves MTP across the stack and DFlash2 for Qwen3.8-27B.

**Synthesised into one arm, not composed as two members.** `compatibility()` conservatively treats
any two arms touching the same file as an explicit conflict, and both touch `src/llama-context.cpp`
— so as separate members they could never compose. Merged into a single arm they compose trivially,
and the combination earns its gates as a unit, so interactions are measured rather than assumed.

**The champion must be built ON the reviewed instrument.** A first attempt (`fdc56acb3`) was
synthesised onto raw v9 and was refused by `_instrument_review_receipt`. That refusal was correct:
it had dropped the measurement apparatus, so every screen would have run on a baseline missing its
own instruments. Exactly one pinned measurement blob changed in the rebuild — `llama-bench.cpp`
(MoE-Spec's 8-line env-var fallback for a flag that defaults to 0). `test-backend-ops.cpp`, the
correctness oracle that decides verdicts, is **unchanged**.

## The build flag that is not optional — read before building any GPU candidate

`GGML_HIP_ROCWMMA_FATTN` **defaults to OFF** (`ggml/CMakeLists.txt:219`). On gfx90a with `-fa on`,
the non-rocWMMA flash-attention path produces **non-finite values at longer sequence lengths**.
Measured 2026-08-27 on the champion built with it OFF: every one of the 12 pinned olympiadbench
prompts failed on task 0 with

```
E process: rejecting DFlash batch after 3020800/3020800 non-finite target features (limit=16)
E srv  decode: failed to process speculative batch
```

while a 25-character prompt succeeded on the same binary. **Prompt length is the discriminator**,
which is why a short smoke test passes and hides it.

Attribution was checked rather than assumed: the standalone DFlash2 build `2046c64e9` ran the
identical prompts with the identical flags at 46.1 / 69.4 / 58.9 t/s and zero non-finite errors,
and `git diff 2046c64e9 5c278648a -- src/ common/` is **+67 insertions, 0 deletions** — DFlash's
source is byte-identical between the two. The merge was not at fault; the build flag was.
Rebuilt with `-DGGML_HIP_ROCWMMA_FATTN=ON`: all prompts pass, zero non-finite errors.

Production, the AK-BH factorial builds and the standalone DF2 build are all ON. ON is the house
standard; anything else is a divergence that must be justified.

## Tasks

- [x] **CH-1 — Champion₀ seeded from the production anchor.** `champion_seed.py` measures the real
      frozen binaries (`binary_sha256` + `linkage_sha256` of the resolved `(soname, path)` table,
      refusing an unresolved library rather than hashing it as absent) and hands `champion.py` a
      sealed anchor. ✅ 2026-08-27
- [x] **CH-3 — The measurement instrument IS the champion**, so gains compound. No controller
      change was required: the anchor arm has always been built from the instrument, and
      `_verify_instrument` only requires a descendant of the frozen production head. ✅ 2026-08-27
- [x] **CH-7 — Manual research merged into the champion.** MoE-Spec and DFlash2, both obtained by
      manual inference research, are in the champion — DFlash2 preserved rather than rediscovered.
      The reusable admission path is: external branch → merge onto the current champion → build with
      the house flags → gates → re-pin. ✅ 2026-08-27
- [ ] **CH-2 — Always-exists invariant.** A champion must exist from the first moment of a campaign
      and be re-seeded on each promotion. `seed_champion()` exists and is unit-tested; wire it into
      campaign start so no campaign can run without one.
- [ ] **CH-4 — MoE-Spec as a formally admitted member.** It is in the champion source but has not
      earned its own T0/T1/T2. Needs compute. Note `--moe-spec-budget` defaults to 0 and is guarded
      by `moe_spec_budget > 0` (`llama-graph.cpp:1985`), so it is inert until a role selects it —
      the champion carries the capability, not the behaviour.
- [ ] **CH-5 — DFlash2 gates.** DF2-5 (concurrency) and DF2-6 (greedy parity) are the blocking
      gates; see [`dflash2-block-drafter-experimental-build.md`](dflash2-block-drafter-experimental-build.md).
      Runners exist as of `c84ecdb7`. DF2-5 grid launched 2026-08-27 22:15Z against the champion.
      Attribute any DF2-6 failure carefully: in-production `a6b4b5263` is numerically valid but
      **not bit-exact** by its own commit message.
- [ ] **CH-6 — the two "config leaders" — REVISED 2026-08-27, do not re-run as originally framed.**
      - `ubatch 512→1024 (+46.9%)` is a **null arm and must not be re-run.** llama.cpp clamps
        `n_ubatch = min(n_batch, n_ubatch)` (`src/llama-context.cpp:265`), so the screen's
        `-b 512 -ub 1024` ran **both arms at an effective ubatch of 512 on one identical binary**.
        The +46.9% is a bimodal sample (`25409, 18083, 25372, 16175, 25381`) whose median landed on
        the fast mode, against an anchor bank ~30% below the independently measured steady state
        (AK-BH-2, n=30). Its `batch_up` sibling, equally null, reported +0.59% by landing on the
        other mode. A guard now refuses this class at the producer
        (`run_autokernel_gpu_discovery.py`, `c84ecdb7`), mutation-tested to fire on `ubatch_up` and
        stay silent on `ubatch`-down, `batch`, `batch_up`, `poll_zero` and `mmap`.
      - `MMQ_MFMA ON→OFF (+26.6%)` **is real** for `Qwen2.5-Coder-0.5B-Q4_K_M @ pp512, np=1,
        gfx90a`, independently reproduced at n=30 (+26.81%). But it is a **build-time** config flag:
        `champion.py` requires source evidence for every member, so it is unconstructible as one,
        and `discovery_static_registry` accepts no CMake flag from planner output. The open question
        is not the 0.5B pp512 number but whether it survives a real model and `-np > 1`, where the
        champion's own state file records MMQ forcing *inverting* on MoE workloads
        (B2 −30%, B4 −21%, B8 −10.5%). Re-run as a build-config A/B on the champion, framed that
        way — never as a champion member.
- [ ] **CH-8 (new, 2026-08-27) — AutoKernel's GPU builder omits the house flash-attention flag.**
      `discovery_deployment_factory.py:2052` passes only `GGML_HIP=ON`, `AMDGPU_TARGETS=gfx90a`,
      `GGML_NATIVE=OFF`, so every AutoKernel GPU candidate is built with `ROCWMMA_FATTN` **OFF**
      while production runs ON. Consequences: candidates are measured on a different
      flash-attention kernel than production uses, which undercuts transferability of any GPU
      result; and the OFF path is the one measured above to produce non-finite values at longer
      sequences under `-fa on`. **Decision required before changing it** — adding the flag changes
      the sealed build identity and breaks comparability with every prior GPU screen, so it is an
      operator call, not a silent fix. Scope note: the non-finite behaviour was observed in the
      DFlash target-feature path; whether plain non-speculative decode also degrades at length on
      the OFF build is **not yet measured** and must not be asserted.

## Superseded

The DF2 handoff header states *"No DFlash2 result may enter the kernel-source champion frontier."*
That line is **superseded** by the operator ruling of 2026-08-27: *"It is the superior spec decode
path for running qwen3.8-27b. Our future production candidate should support this new spec decode
type"*, and *"DFlash2 is a parallel spec decode pathway. Not all models have dflash2 drafter heads.
When we promote to production, we will adjust the lean registry compiler accordingly."* DFlash2 is
in the champion by that ruling. Recorded here rather than silently contradicted.
