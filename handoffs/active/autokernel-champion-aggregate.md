# AutoKernel — the standing aggregate candidate (champion)

**Owner:** operator audit session, 2026-08-27. **Depends on:** INF-06 (campaign), INF-64 (repair track).
**Operator requirement, 2026-08-27:** *"There should ALWAYS be an aggregate production candidate that
holds all the experimented tweaks and is ready for promotion gate testing."* And: AutoKernel screens
against that aggregate, *"attempting to make it better"*, rather than re-deriving deltas against a
fixed production anchor.

## Start here — open work (2026-09-29)

**Release manifests (2026-10-20):** every champion feature and keep is tracked in one table per kernel set: [`docs/reference/kernel-manifests/llama-v11-manifest.md`](../../docs/reference/kernel-manifests/llama-v11-manifest.md) (next llama.cpp production, v11) and [`docs/reference/kernel-manifests/speech-v2-manifest.md`](../../docs/reference/kernel-manifests/speech-v2-manifest.md) (`production-speech-v2`). Every fold, keep or exclusion edits the manifest in the same commit.

**Pending fold for the champion owner (2026-10-20, REPL-EMB-2.6 session):** the EmbeddingGemma 2 model support is prepared on `experimental/champion-plus-gemma-embedding2-20261020` @ `e94cc2b50f6573677f951cce426fedb6b29416c8` (local branch, worktree `/mnt/raid0/llm/worktrees/llama-champ-gemma-embedding2-20261020`), cut from the champion tip `e33229348` (the branch tip is 10 AK keeps past the ledgered `b0ba1d427`). Two commits, cherry-picks of `d871e67e0`/`966c24d6e`, zero conflicts (disjoint files: `src/` model files vs the champion's `ggml-cpu.c`/`iqk_dispatch.cpp`/`sgemm.cpp`). Parity vs the ST FP32 reference: BF16 min cos 0.999990, Q8_0 0.999323 (gates 0.99/0.98), no non-finite; `test-backend-ops` CPU RMS_NORM/ROPE/SOFT_MAX/FLASH_ATTN_EXT/GET_ROWS/MUL_MAT pass; linkage PASS. Additive; ready to merge at the next consolidation (this session did not touch the champion branch). Detail: `repl-embedding-retrieval.md` REPL-EMB-2.6. **Rebased 2026-10-20 (champ-emb2-rebase): the champion moved to `dd3d9721c` (slotdraft fold), so the fold to take is now `experimental/champion-plus-gemma-embedding2-20261020b` @ `63bc737eaf791e755fc02ce773191d2e52a1b7a0` (pushed to `fork`; worktree `/mnt/raid0/llm/worktrees/llama-gemma-embedding2-20261020b`; commits `f8dd2982b`, `63bc737ea` on top of `dd3d9721c`, zero conflicts, files disjoint from the slotdraft fold's `common/`, `server-context.cpp`, `speculative-simple.cpp`). Rebuilt CPU Release (`llama-server --version` 10347), `strings libllama` shows `gemma-embedding2`, linkage OK. Parity rerun vs the ST FP32 reference on both sets (probe45 and proxy): BF16 min cos 0.999990 (gate 0.99), Q8_0 0.999323 (gate 0.98), zero non-finite, PASS; `test-backend-ops` CPU RMS_NORM/ROPE/SOFT_MAX/FLASH_ATTN_EXT/GET_ROWS/MUL_MAT all OK. The earlier `...20261020` branch (`e94cc2b50`, on `e33229348`) is superseded and left unrewritten.**

**Pending fold for the champion owner (2026-10-21, Nemotron 3.5 Bolt), rebased onto candidate C for C2:**
**C2 = `experimental/c-plus-nemotron-bolt-20261021` @ `49550eda5`** (pushed to `fork`; worktree `/mnt/raid0/llm/worktrees/llama-c-nemotron-bolt-20261021`), cut from C `f0c96dc1f` (`experimental/champion-consolidation-20261020`, untouched).

Commits, one feature each:
- `6cc5602c8` #26693 saver fix
- `796077697` per-layer MoE hparams + Bolt `nemotron_h_moe` fixture
- `b078b5f0c` mtmd `nemotron_omni`

  These three are V11-097. They were clean `-x` picks of `e68cda856`/`64bb5d7b0`/`59c1b915f` and keep the same stable patch-id.
- `159767788` V11-098 hybrid `--cache-reuse` guard (from `8b08c9f25`). One conflict, R1: `tests/CMakeLists.txt`, adjacent `llama_build` lines; kept both.
- `9a44414c4` CT-12.3b (`b4dd52370`). Clean pick, same patch-id.
- Two test-only fixes:
  - `f9c01ce0e`: test-llama-archs skips gemma-embedding2, as upstream #30054 does. On C's own build the fixture generator aborted at gemma-embedding2, so every fixture-dependent ctest was "Not Run". It still aborts next at deepseek41 (`expert_feed_forward_length`), a pre-existing DS41 fixture gap.
  - `49550eda5`: V11-098's server test asserted `generation_settings.n_cache_reuse`, which this server never emits. It now asserts the disable log line. It PASSES on C2 and FAILS on C.

V11-099 (`a62f64d5`) is NOT included. Conflict records: `/mnt/raid0/llm/tmp/nemotron-c2-prep-20261021/conflicts.txt`.

Stores: `kernels/builds/{cpu,gpu}-20261021-49550eda5-c-nemotron` (10411, linkage PASS). Only version-stamped files differ from the gated `…-f9c01ce0e-c-nemotron` stores; libllama/libggml-cpu are byte-identical.

Pre-check gates vs C's `cpu-20261020-f0c96dc1f`, all PASS:
- test-llama-archs, 140 archs: only `nemotron_h_moe` (new MoE row OK) and gemma-embedding2 (error→SKIP) differ.
- CPU test-backend-ops: MUL_MAT_ID 815, MUL_MAT 1145, ADD 99, ARGSORT 98, TOP_K 445, GET_ROWS 111, SSM_SCAN 6, SSM_CONV 45.
- Qwen3.6-35B-A3B-MTP greedy 3x256: byte-identical, draft counters equal.
- test-chat-input-spans: pass.
- test-memory-can-shift and test-recurrent-state-rollback on qwen35 and nemotron_h: pass.
- Server pytests (local GGUFs, `--noconftest`, offline): `test_chat_special_tokens.py` 7/7, `test_cache_reuse_recurrent.py` pass.
- Bolt CPU greedy smoke: identical to the champion-based fold.
- CH-21 real-model check (fixed copy `run_ch21_check_fixed.sh`; the original has a pipefail/`grep -q` SIGPIPE defect and the same nonexistent-field check): PASS on Qwen3.6-35B-A3B-MTP-Q8_0 and Qwen3.8-27B-Q8_0. Evidence: `/mnt/raid0/llm/tmp/nemotron-c2-prep-20261021/`.

The earlier champion-based fold `experimental/champion-plus-nemotron-bolt-20261021` @ `59c1b915f` is superseded for C2.

**DFlash LiLiCorr drafter (separate branch, its own gates; not part of C2):** `experimental/c-plus-nemotron-bolt-dflash-20261021` @ `58a98f088` on C2 `49550eda5`. Commits:
- `30e7d8b14` optional DFlash attn sinks (#27804 part)
- `bbbda2e58` NVFP4 per-tensor scales in the drafter (#26905 + #28000)
- `4d01b71b2` nemotron-h layer-input extraction (#26905)
- `9aed8680d` token+embd draft batches take the noise graph. This is the champion's stand-in for upstream's `llama_batch_ext` `embd_state`; no batch/API change.
- `acb26f310` blocks past `n_layer_all` go with the output buffers (#29831 hunk)
- `58a98f088` LiLiCorr (#30506 C++ parts)

Design: `/mnt/raid0/llm/tmp/nemotron-c2-prep-20261021/dflash-port-design.md`. Stores: `{cpu,gpu}-20261021-58a98f088-c-nemotron-dflash` (10417).

Gates, all PASS:
- Qwen3.6 MTP greedy: byte-identical vs C2.
- Qwen3.8-27B DFlash2 greedy 3x64: byte-identical, equal counters.
- CPU test-backend-ops on the 23 scorer ops: all pass.
- Bolt+LiLiCorr CPU smoke: it loads and drafts are accepted. Greedy accepted 47/94, 53/59, 48/85 at 18.5-30.1 t/s vs 17.5-17.9 t/s without the drafter. With `LLAMA_SPEC_EXACT=serial` the output is identical to no-spec on all 3 prompts. The default batched verify diverges once on prompt 1; that comes from target numerics, not the drafter. At temp 1.0 it accepted 88/230, 95/181, 92/205.

Not run: DS41 DSpark identity. It is structural only: graph_dsv4/dsv41 are untouched and the new paths are flag-gated.

- [x] **NEMO-LILI-1 — MI210 spec speed run (indicative).** ✅ 2026-10-21: build `gpu-20261021-58a98f088-c-nemotron-dflash`, NVIDIA recipe flags, host 72-79. No drafter: tg 52.0-52.6 t/s, pp 939 t/s (1804 tok). LiLiCorr: tg 32.4/52.1/34.8/59.1 t/s on 4 greedy prompts, acceptance 49% (36-78%), pp 744 t/s; temp 1.0: 33-66 t/s. Net: wins only on high-acceptance prompts, ~35% slower on prose (a round ~97 ms vs 19 ms per plain token). `LLAMA_SPEC_EXACT=serial` output identical to no-drafter; batched verify diverges (target numerics). VRAM 21.5 / 23.6 GiB, KFD pid proven. Records: `/mnt/raid0/llm/tmp/nemotron-c2-prep-20261021/gpu_{nospec,spec,spec_serial}.json`.
  - *(2026-10-21 result, Bolt base build `59c1b915f`, harvested 2026-10-27 by workspace-58.)* performance, INDICATIVE ONLY, no predeclared gate (shared claim, host load ~98). MI210: coherent with reasoning on and off (8/8, no loops), 21.5 GiB VRAM, KFD residency proven; llama-bench pp512 899.2 / tg128 53.4 t/s; NVIDIA-recipe server tg 51.2 t/s. CPU 24 threads: pp512 56.1 / tg128 12.7 t/s. Not citable as a champion speed claim. Source `progress/2026-10/2026-10-21-nemotron-bolt.md:7`; records `/mnt/raid0/llm/tmp/nemotron-c2-prep-20261021/`. [belief: cc]
- [ ] **NEMO-LILI-2 — profile one DFlash round on the MI210** (target batched 7-token verify vs drafter encode/inject/draft decodes) to find why a round costs ~5x a plain token; and the drafter-on-CPU control aborts at reserve (the drafter shares the target's ROCm-resident `output.weight`; affects any DFlash drafter). Low-priority GPU filler (operator 2026-10-21: "book a gpu slot but low priority").
- [ ] **NEMO-BOLT-PROF — per-op rocprof of one Bolt decode step on the MI210** (IQ2_XXS expert MUL_MAT_ID, NVFP4 Mamba in/out, SSM scan): why Bolt decodes at ~53 t/s vs ~100 t/s for Qwen3.6-35B-A3B Q8 on the same card. Same low-priority GPU filler slot as NEMO-LILI-2 (~20-30 min, ~24 GB).
  - *(2026-10-25 observation, workspace-58 wrap-up; no tick: block-correctness observation, no decision edge.)* Calendar item `nemo-gpu-prof` (`/mnt/raid0/llm/tmp/cal-1025/nemo-gpu-prof/`, MI210 exclusive, champion store `gpu-20261023-dcc853b55-c3`, rocprofv3 kernel trace, HIP graphs ON, predeclaration sha256 `914fd9b1…92ca`) ran both passes COMPLETE. Evidence: research `data/nemo-gpu-prof/` (committed `84ae00217`, on main via `237a7a789`); the 306 MB raw traces stay in `out/pass-{L,B}/`.
    - Pass L profiled **Qwen3.8-27B-Q8_0 + DFlash2** (the :8083 argv at `-np 1 -c 16384`), not Nemotron + LiLiCorr, so it does not answer NEMO-LILI-2 as written. A DFlash round is 78.2 ms busy: the target 7-token verify is 67.1 ms (Q8_0 `mul_mat_q` 70%), and drafter encode/inject/draft is about 11.1 ms (segment-size heuristic). Wall: round about 124 ms vs a plain token 57 ms (2.2×); spec 44.4 t/s vs plain 17.5 t/s; 130/202 drafts accepted.
    - Pass B profiled Nemotron-3.5-Bolt-74B-A9B IQ2_XXS. Decode wall is 33.9 ms/step. Kernel-category share: mul_mat_vec 56.8% (the IQ2_XXS route), norm 15.1%, copy/convert 12.3%, elementwise 5.2%, ssm_scan 4.8%.
    - Defect in the analysis: with graphs ON, the 50 µs gap segmenter cut plain decode into one-dispatch segments (L plain-token "busy" 0.012 ms, ratio 6,351×; B 0.0105 ms per "step"). So the per-token and per-step busy figures are artefacts; only the category shares and the spec-round split are usable.
    - [ ] **NEMO-PROF-RESEG — re-segment the stored nemo-gpu-prof traces by token boundary (filed 2026-10-25).** Re-run `analyze_prof.py` on `out/pass-{L,B}/` with token boundaries taken from the server timings (or the graph-launch markers), not the 50 µs gap, so plain-token and Bolt-step busy ms are real. Analysis only, no GPU. Copy the traces to a durable home first. Done when both passes report a per-token busy ms consistent with wall.
    - NEMO-LILI-2 and NEMO-BOLT-PROF stay open. A separate re-run box is not filed, because NEMO-LILI-2 already is that task: its next run must use the Bolt target with the LiLiCorr drafter (the `gpu-20261021-58a98f088-c-nemotron-dflash` build and the NEMO-LILI-1 recipe). NEMO-BOLT-PROF closes on NEMO-PROF-RESEG.

**Current champion: C5 `c72ec82f5` (CAS 2026-10-25T08:24:10Z)** (previously `dd3d9721c`, 2026-10-20) on `ak/champion/llama-cpp-ffc1bac82eec` — the "slotdraft" fold below, on top of `e33229348` (AutoKernel keeps of 2026-10-06/08 had advanced it past the ledgered `b0ba1d427`). Builds: `kernels/builds/cpu-20261020-dd3d9721c`, `kernels/builds/gpu-20261020-dd3d9721c`. The paragraph below describes the 2026-10-04 state. Branches cut from `e33229348` (e.g. the pending EmbeddingGemma 2 fold above) rebase onto `dd3d9721c`.

**As of 2026-10-04 the champion was `b0ba1d427` on `ak/champion/llama-cpp-ffc1bac82eec` (since advanced; the ref now points at `dd3d9721c`, per the line above)** (v10 lineage; advanced 2026-10-04 four times:
KVU-19 `90c12df42` → `1bceceb05`; all-keeps `1bceceb05` → `61bdb185c`; CPU FA overflow `61bdb185c` → `9a3f1392a`; W
`9a3f1392a` → `b0ba1d427`; see the fold ledger entries below). This is the GLOBAL champion branch. Builds:
`kernels/builds/cpu-20261004-b0ba1d427` and `kernels/builds/gpu-20261004-b0ba1d427` (10332).

**Fold ledger - 2026-10-24, CH-29 / C3 (V11-100 YaRN K-shift fix)** (coordinator 3c4ca599, operator-approved via the decision tool 2026-10-24). `dcc853b55` = `141e4bcf5` + one commit (test-yarn-kshift + `build_rope_shift` passes no magnitude factor). Guarded CAS `141e4bcf5 -> dcc853b55` at 2026-10-24T07:50:06Z, `ak-loop-tree` read-tree two-tree form (clean, HEAD dcc853b55), fork fast-forward push verified (`git ls-remote fork`). Images `kernels/builds/{cpu,gpu}-20261023-dcc853b55-c3` (PROVENANCE status CHAMPION). Gates (all in `/mnt/raid0/llm/tmp/c3-fold-prep/`): G-a unit tests incl. test-yarn-kshift PASS, G-b `fold_gate.py` only libllama.so changed, G-c version/linkage PASS, G-d GPU ROPE/FA/MUL_MAT counts identical to the 141e4bcf5 control, G-e Q38FN greedy identity IDENTICAL p1-p3 (`GATE_bc.done`), G-f GPU 27B DFlash2 A/B identity C3==P on 15 pairs, pp -0.21% / tg -0.07% inside the P-vs-P floor (`GATE_e.done`), G-g df29 probe on the ROCWMMA-OFF side image 10/10 runs 0 non-finite (`GATE_g.done`; CH-20 item 3, not CAS-blocking). Q38FN CPU timing +3.63% (49.18 -> 50.96 tok/s, 5 pairs) is a SIGN claim only (no calibrated Q38FN floor; the change is not on the decode path), not claimed as a gain. Production unchanged (v10 ffc1bac82). Consequence: CH-30 (GPU-LEAK-1c, cut on 141e4bcf5) must be re-cut on dcc853b55 before its fold (fresh-tip rule).

**Fold ledger - 2026-10-23, CH-28 (llama-bench harden-init)** (coordinator 3c4ca599; fix authored by workspace-f8). `141e4bcf5` = `49550eda5` + one commit: llama-bench value-initialises `cmd_params`, so `autokernel_harden` is no longer indeterminate. Touches only `tools/llama-bench/llama-bench.cpp` and tests (`test-llama-bench-params-init`). Store images `kernels/builds/{cpu,gpu}-20261023-141e4bcf5-lbh`, version 10412, PROVENANCE.md present. Gate (`/mnt/raid0/llm/tmp/ch28-fold-20261023/`: `GATE_ACCEPTANCE.md`, `gate_*.v2.out`, `DONE`): ctest PASS; 6/6 unrequested llama-bench rows unhardened; versions OK; libs identical or explained, except `libllama-server-impl` `_GLOBAL__sub_I_ui.cpp` (gzip sizes of the non-deterministically rebuilt web-UI bundle; source diff for tools/ui, server, ggml, src, common, include and mtmd is empty). Main accepted this as a documented exception. `/mnt/raid0/llm/tmp/ak-loop-tree` refreshed and clean. Moved: guarded CAS `49550eda5` -> `141e4bcf5` (FF, ~11:10Z). Fork push NOT done (CH-28b). Follow-ups: CH-28a, CH-28b, CH-28c.

**Fold ledger - 2026-10-23, candidate C2** (operator-approved; coordinator 3c4ca599). C2 = `experimental/c-plus-nemotron-bolt-20261021` @ `49550eda5` = candidate C `f0c96dc1f` + 7 commits (V11-097 x3, V11-098, V11-095/CT-12.3b, 2 test-only), zero `ggml/` diff vs C. Decision record: `/mnt/raid0/llm/tmp/c2-regate-20261021/C2_CAS_DECISION.md`.
- **Gates:** e (GPU 27B DFlash2 A/B) PASS; c (Q38FN greedy identity) PASS; nemotron GPU/CPU PASS; vision (mtmd `nemotron_omni`) PASS. b (Q38FN CPU timing) was INVALID on predeclared rule 1 twice (run 2: anchor CV 6.5% > 6%, effect +0.34%, candidate slower 4/12; run 3: anchor 41.47 CV 8.4%, candidate 42.38 CV 2.9%, effect +2.17%, slower 1/12, medians < 45); both pass rule 2. **Waived by the operator, 2026-10-23 ~07:15Z ("Advance C2 by waiver"), rule 1 only.** Waiver record: [`artifacts/operator/c2-cas-waiver-20261023.md`](../../artifacts/operator/c2-cas-waiver-20261023.md).
- **Moved:** guarded CAS `update-ref` `dd3d9721c` -> `49550eda5` (fast-forward verified, ~07:20Z), `ak-loop-tree` refreshed (`read-tree -m -u`, clean at `49550eda5`). Store images `kernels/builds/{cpu,gpu}-20261021-49550eda5-c-nemotron` (10411). Not pushed to `fork` yet (open task below).
- **Notices:** CH-22 pings sent to workspace-7b and workspace-58 (~07:25Z); f8's session is offline, relayed through workspace-58. workspace-7b acked ~07:35Z: no AK runs in flight; its Q38FN `inputs-fa-20261022` bundle and the three floors measured on `dd3d9721c` (serving 2.483%, 64k decode 1.365%, 64k prefill 1.106%) are marked superseded (`ANCHOR-SUPERSEDED.txt`) because C2 changes `ggml-cpu/ops.cpp` and `qwen35moe.cpp` vs `dd3d9721c`; its next Q38FN window rebuilds the bundle on `49550eda5` with `--new-anchor-epoch` and re-calibrates the floors before judging any keep. No CHAMPION_BUILD constants in 7b's scripts.
- **Manifest:** `docs/reference/kernel-manifests/llama-v11-manifest.md` rows moved to IN @ `49550eda5` (all former IN-C rows plus V11-095/097/098); the old "C2" name (`b4dd52370`) is retired.
- [x] **CH-25 - push the champion ref `ak/champion/llama-cpp-ffc1bac82eec` (now `49550eda5`) to the `fork` remote.** Pending operator permission (the CAS itself is local). Recorded 2026-10-23. ✅ 2026-10-23: operator approved; `git push fork` fast-forward dd3d9721c..49550eda5, `ls-remote fork` confirms 49550eda5.
- [x] **CH-26 - re-anchor `dd3d9721c` references on `49550eda5`.** Do NOT edit running scripts; re-anchor at each owner's next launch. Found 2026-10-23: `/mnt/raid0/llm/tmp/ds41-1017-baseline-20261021/gate_1017.py:80` (`CHAMPION_BUILD`, also `--build` help at :767), `chained_launch.sh`, `chained_launch_c2.sh`, `smoke_1017.py`; `/mnt/raid0/llm/tmp/c2-regate-20261021/bundle_gate_c2.sh` (`CHAMP`/`CHAMP_GPU` at :33/:37) and `nemotron_gpu_gates.sh`; `/mnt/raid0/llm/tmp/champ-consolidation-20261020/bundle_gate.sh`; research repo `scripts/kernel_rnd/autokernel/loop/{floor_registry,champion_reanchor}.py` (campaign anchor logic, `champion_reanchor.py` is the existing tool), `scripts/benchmark/m12_launch_argv.py:37` (`DEFAULT_BUILD` gpu-20261020-dd3d9721c), `scripts/benchmark/gpu_cpu_noise/gpu_cpu_noise_driver.py`, `orchestration/model_registry.yaml:13468` (`build_dir`/`commit`; registry champion-of-record stays FROZEN until a stack-change, so leave it). Floors measured on `dd3d9721c` are valid only pre-C2. ✅ 2026-10-23: research `a0f912603` re-anchors `m12_launch_argv.py` DEFAULT_BUILD and `gpu_cpu_noise_driver.py` GPU_BUILD/GPU_EXPECT_BUILD (b10411-49550eda5) plus test (7/7, 17/17 pass); `gate_1017.py:80,767` re-pointed (backup .bak-pre-ch26). Left as history: c2-regate/champ-consolidation gates, DS41-1017 comparison records, floor_registry docstrings, artifacts/*, frozen model_registry.yaml. champion_reanchor.py resolves dynamically. Orchestrator: no matches.
- [ ] **CH-26a - re-measure the M12 long-context GPU recipe on 10411 (49550eda5)**, then re-anchor `docs/m12-long-context-gpu-recipe.md` (research), which still records the dd3d9721c build it was measured on.
  - *(2026-10-27, workspace-58 results harvest)* Re-measured on C5 c72ec82f5/10419 (MAIN-accepted replacement for 10411; 10411 itself not re-measured): VERDICT PASS 9/9 requests, 2 arms. Warm cache share (gate >=0.95): 35B-MTP np4 B 0.9805, C 0.99996, E 0.9893, F 0.9804; 27B-DFlash2 B 0.9805, C 0.99996. Warm processed tokens (gate <=4100): 2045/4/2052/2048 and 2045/4; cold legs 100% processed (35B A 104698 tok 87.2 s, D 191447 tok 245.0 s; 27B A 104698 tok 239.1 s). One sample per leg, no speed claim. Artifact `/mnt/raid0/llm/tmp/cal-1026/ch26a-m12-c5-longctx/out/VERDICT.json + out/35b/receipt.json + out/27b/receipt.json`. Measurement half met; doc re-anchor not done, box stays open. [belief: cc]
  - [ ] **CH-26a.1 — re-anchor research `docs/m12-long-context-gpu-recipe.md` on store gpu-20261024-c72ec82f5-c5 (10419) from the 2026-10-26 receipts**; done when its binary, source, loader rows and commands name c72ec82f5 (then tick CH-26a).
  - *(Evidence, workspace-58, 2026-10-26; not a tick.)* Native PASS pending the final per-leg metric extract: `/mnt/raid0/llm/tmp/cal-1026/ch26a-m12-c5-longctx/out/VERDICT.json` (2 arms, 9 requests, PASS, rc0 22:15:34Z, claim "current C5 M12 reader recipe protocol only"). The old 49550eda5 measurement claim is NOT reused; no metric box ticked.
- [ ] **CH-26b - re-measure the DS41-1017 noise floor on 49550eda5** before any DS41 judgement: `gate_1017.py` now defaults to the new champion, but every existing floor sample was taken on dd3d9721c.
- [ ] **CH-27 - re-calibrate the Q38FN floors on the CURRENT champion (was `49550eda5`; owner workspace-58 from 2026-10-24, transferred from workspace-7b).** Rebuild the bundle on the champion's store image, re-measure serving / 64k decode / 64k prefill floors (old: 2.483% / 1.365% / 1.106%, superseded), before judging any keep. Acked by 7b 2026-10-23 ~07:35Z. The DS41 1017 floor (2.862%, `dd3d9721c`) needs the same re-anchor (CH-20.1). Handover: `/mnt/raid0/llm/tmp/handover-7b-to-ws58-20261024.md`. **⛔ OPERATOR HOLD 2026-10-24: "DO NOT LAUNCH AUTOKERNEL".** This item runs AK `run.py`, so do not arm, book or start it until the operator tells workspace-58 directly that AutoKernel is to be launched.
  - [x] Harness fixes the window needs, landed on research main `eb753e422` (`b6e80d24e` stale CMake dir clear + abort evidence; `f131a9f7b` bench-floor print; `eb753e422` store-image anchor on an experimental lane, exact store COR on a plain advance, anchor-keyed 64k floor through the registry). 417 loop tests pass. ✅ 2026-10-24
  - [x] Bundle + launchers prepared and dry-run verified on `141e4bcf5`: bundle `/mnt/raid0/llm/autokernel/campaigns/ak-q38fn-cpu-decode-20261003/inputs-ch27-20261023/`, launchers `/mnt/raid0/llm/tmp/ak-q38fn-ch27-20261024/` (`ch27_grant_wait.sh` → `ch27_window.sh` → `precheck.sh` → `champion_reanchor apply --execute` → `ch27_run.sh window`); `ch27_window.sh --apply-dry` PASS (actionable, anchor `cpu-20261023-141e4bcf5-lbh`, COR `cpu-20261020-dd3d9721c`, 48 serving calibration launches). Nominal ~80 min (worst ~99, hard stop at grant + 5400 s), peak RAM ~95 GiB. ✅ 2026-10-23
  - [x] ~~Re-anchor that bundle on the current champion `dcc853b55` (C3, changes `src/llama-kv-cache.cpp` K-shift) via store image `cpu-20261023-dcc853b55-c3`, update `ch27_grant_wait.sh`'s hard-coded 13:30Z deadline, re-run `ch27_window.sh --apply-dry`.~~ (closed 2026-10-29 audit: SUPERSEDED → re-anchor on C3 dcc853b55 replaced by operator decision 2026-10-25 to run bounded recal on C5 c72ec82f5 (L103))
  - [x] ~~Register the `ch27-q38fn-floors` FILLERS row with a live `ch27_grant_wait.sh` pid (whole host quiet + GPU idle, 200 GiB, 5700 s) and get it booked. The 2026-10-24 ~06:37Z slot was skipped: no row, no pid.~~ (closed 2026-10-29 audit: SUPERSEDED → 2026-10-24 FILLERS-row slot skipped; booking replaced by C5 bounded window + CH-27a re-book (L103-105))
  - [ ] **CH-27 bounded recal run on C5 `c72ec82f5`** (operator decision 2026-10-25 via decision tool): the AK hold is lifted ONLY for ONE bounded Q38FN floor-recalibration window (serving / 64k decode / 64k prefill floors) on champion C5 `c72ec82f5`. No AK search. The hold stays in force for everything else. Launcher prepared (not armed): `/mnt/raid0/llm/tmp/cal-1025/ch27-q38fn-floors/`. Done when the floors are written for the C5 anchor.
    - *(2026-10-27, workspace-58 results harvest)* Window 03:25Z aborted at precheck, rc=20, 0 floors measured: planner rejected store image `cpu-20261024-c72ec82f5-c5` (CMake recipe digest differs from the reference build). Other prechecks passed. Artifact `/mnt/raid0/llm/tmp/codex-ni-20261026-ch27-actual-floor/recipe/plan-for-dry.json`. [no-belief: invalid, nothing measured]
    - [ ] **CH-27a — repair (or explain) the C5 CPU store image recipe-digest mismatch, re-run the ch27_run dry plan to actionable=true, then re-book the bounded window.**
      - *(2026-10-30, codex-ni prep; not a task tick.)* Research source fix is promoted on main at `2900939bc4ddbeedf82720f80c32627592219cf6` (lane `63b4e48cc308d64aba627cd50a693bfe73f26e16`), with the two reviewed source files and 829 source guards unchanged. Diagnostic READY `codex-ni-ch27-c5-raw-recalibration-20261030` is rank 1, keeper accepted 16:25:13Z. It preserves whole-host 0-95/t48/GPU-quiet profile, 24 calibration pairs/48 launches and five comparison pairs; prospective current-C5 raw CMake flags are explicit, historical dd3 COR remains separate, and strict raw recipe digests are unchanged. Native Q38 smoke was 46.005 s/~79 GB and deliberately nonadmitted; cutoff was partial after compute/cleanup. No floor or regression result exists. Evidence: `/mnt/raid0/llm/tmp/codex-ni-ch27-recipe-provenance-prep-20261030/{PROVENANCE.json,FULL-PLAN.json,PREDECLARATION.json,KEEPER-ACCEPTANCE.json,TASK-REPORT.md}`. CH-27 remains in its existing calibration-loop source family; no generic committed-conclusion path is proposed, and this evidence does not complete the floor task.
- [x] **CH-28 - fold the llama-bench `cmd_params` initialisation fix into the next champion (manifest V11-103).** Branch `experimental/llama-bench-harden-init-20261023` @ `141e4bcf5` (one commit on `49550eda5`, pushed to `fork`; files `tools/llama-bench/llama-bench.cpp` +17/-1, `tests/test-llama-bench-params-init.py`, `tests/CMakeLists.txt`). Defect: `parse_cmd_params()` declared `cmd_params params;` and never copied `autokernel_harden` / `autokernel_seed` / `autokernel_ready_timeout_ms` from `cmd_params_defaults` (UB since `0492c2319`, 2026-08-11; in v10 `ffc1bac82`, `dd3d9721c` and `49550eda5`), so about half of all llama-bench processes ran the hardened protocol unrequested. Fix: `cmd_params params{};` plus an explicit defaults copy of every non-vector field (a wholesale `= cmd_params_defaults` would merge user vectors with the defaults). Only `tools/llama-bench` and a test change: libllama, libggml* and llama-server are untouched, so it can ride the next fold without a serving gate, and it should not wait for a large bundle (every llama-bench built from the champion is a broken instrument until it lands). Gates on the trial-merged build: ctest `test-llama-bench-params-init` passes (it fails on `49550eda5` with 8 violations); `llama-bench` builds; 50 runs of a tiny GGUF (`-p 0 -n 1 -r 1 -o jsonl`, no `--autokernel-harden`) each emit at least one row and never `"autokernel_hardened": true`, and a positive control with `--autokernel-harden 1` does (a nonexistent model is a vacuous check: llama-bench exits at model load, before the hardened branch and before any row). Fleet clean-up of rows already written is LBH-1..3 in `autokernel-rebuild-program.md`. (filed 2026-10-23, workspace-f8) ✅ 2026-10-23: folded, guarded CAS `49550eda5` -> `141e4bcf5` (session 3c4ca599); see the fold ledger "2026-10-23, CH-28".
- [x] **CH-28a - give `gate.sh` a UI-asset class**: the `tools/ui` web-UI bundle is rebuilt non-deterministically (gzip sizes differ, visible as `_GLOBAL__sub_I_ui.cpp` in `libllama-server-impl`), so future folds with an empty ui/server source diff need no manual acceptance. ✅ 2026-10-23: `fold_gate.py` / `libcmp.py` EXPLAINED-UI class (code diff confined to `_GLOBAL__sub_I_ui.cpp` `movq` immediates AND `git diff base cand -- tools/ui tools/server` empty, proved by the driver); validated on 141e4bcf5 vs 49550eda5 (cpu+gpu PASS, no manual exception). Tool: epyc-inference-research `scripts/kernel_rnd/fold_gate/` (`62c2e09da`). Determinism of the bytes themselves: pin `tools/ui/dist` (priority 1 in `scripts/ui-assets.cmake`) - proposed in CH-28d.
- [x] **CH-28b - push the champion ref `ak/champion/llama-cpp-ffc1bac82eec` (now `141e4bcf5`) to the `fork` remote.** Pending operator OK (the CAS itself is local). ✅ 2026-10-23: operator approved; `git push fork` fast-forward 49550eda5..141e4bcf5; `ls-remote fork` confirms 141e4bcf5.
- [x] **CH-28c - replace the heuristic libggml-hip device-code comparison** in the gate with a deterministic check, e.g. compare the code objects after stripping `__FILE__` strings. ✅ 2026-10-23: `hipdev.py` - gfx code objects resolved-operand disassembly + rodata/kernel-descriptor compare modulo build root; kernels must be identical, only non-kernel `no_device_code` may differ (46 of 135 objects, counted). GPU 141e4bcf5 vs 49550eda5 PASS, 0 other. Residual: those 46 helper bodies are structurally, not instruction-verified; CH-28d removes the residue.
- [ ] **CH-28d - adopt path-independent builds in the fold recipe (proposal, needs operator OK to touch `build_store.sh`).** *(2026-10-23: implemented in the NEW file `/mnt/raid0/llm/tmp/c3-fold-prep/build_store.sh` (prefix maps incl. HIP, UI dist pin, per main's relay); the CH-28 script is untouched; stays open until the C3 build is run twice/verified `mode=exact` on the fold after C3.)* (1) `-ffile-prefix-map=<worktree>=. -fmacro-prefix-map=<worktree>=.` in CMAKE_C/CXX/HIP_FLAGS so `__FILE__` in device code is path-independent and the hip comparison becomes `mode=exact`; (2) copy the previous champion image's `tools/ui/dist` into `<fold worktree>/tools/ui/dist` before configure so ui.cpp is byte-stable and EXPLAINED-UI is never needed. Verify by building twice and running `fold_gate.py` (expect no EXPLAINED-UI, hip `mode=exact`).
- [x] **CH-29 - build, gate and CAS the C3 fold: `experimental/champion-c3-20261023` @ `dcc853b5559bef4e50acf251f4910f7f4e0ba538` (champion 141e4bcf5 + V11-100 YaRN K-shift fix with `test-yarn-kshift`, one commit, pushed to fork).** Plan, scripts and evidence paths: `/mnt/raid0/llm/tmp/c3-fold-prep/PLAN.md` (`build_store.sh`, `gate_c3.sh`, `c3_build_job.sh`, `gpu_slice_c3.sh`, `bundle_gate_c3.sh`; none run). Steps: (1) CPU build-role grant ~35 min: build `kernels/builds/{cpu,gpu}-20261023-dcc853b55-c3` (CH-28d prefix maps + pinned UI dist), `gate_c3.sh` (test-yarn-kshift, test-rope, fused-rope, dca, CPU ROPE 448/448, `fold_gate.py --expected-changed libllama.so` vs the 141e4bcf5 image; the C3-vs-141e4bcf5 hip compare still shows build-path differences because 141e4bcf5 had no prefix map, the first `mode=exact` fold is the one after C3); (2) GPU correctness slice ~25 min (`test-backend-ops -b ROCm0` ROPE/FLASH_ATTN_EXT/MUL_MAT vs the 141e4bcf5 control); (3) Q38FN greedy identity (`bundle_gate_c3.sh --items c`, ~5 min) and the 27B GPU A/B (`--items e`, 15 pairs, ~26 min); (4) V11-FA-6 route gate on a `-c3-rwoff` image (640/640 + df29 10 runs, ~15 min GPU); (5) guarded CAS 141e4bcf5 -> dcc853b55 (recipe in `ch28-fold-20261023/PLAN.md` section 3), manifest V11-100 PEND -> IN. SEPARATE REQUEST: the TIMING gate `--items b` (Q38FN 5 pairs, whole-host quiet, ~7 min). Excluded from C3 with reasons (V11-086 HOLD, V11-102 gate rerun owed, V11-099/101/044 held or failed their own gate, CH-24 smokes unrun, CPU-FA-VKQ-1 superseded): PLAN section 1. Recorded 2026-10-23, fold-prep subagent of 3c4ca599.
  - *(2026-10-24, 3c4ca599.)* DONE: CAS'd `141e4bcf5 -> dcc853b55` at 07:50:06Z with operator approval, fork pushed; all gates in the CH-29 fold ledger entry above. Harness fixes made on the way: `bundle_gate_c3.sh` re-exec'd a non-existent `bundle_gate_c2.sh` (fixed) and its CPU-quiet preflight now applies to items b,c only; the df29 probe was rebuilt against C3 headers (`c3-fold-prep/fa_nan_probe_c3`; the 10-04 binary SEGVs on the C3 libllama ABI); the G-g wrapper treats the ROCm0 banner as a note (VRAM delta + HIP lib mapped are the residency gate).
  - 2026-10-27 harvest (g2conc-c3 ended 2026-10-24T09:40Z, g2conc-recheck ended 10:31Z; G2-CONC on the C3 binary `dcc853b55`, `/mnt/raid0/llm/tmp/ws58-g2conc-20261024/RESULT.json`, `recheck/RESULT.json`, `PREDECLARED.md` AMENDMENTS 5-6): A5 re-run (detector `degeneracy.v2.1-g2conc`; the A4 FAIL was a detector false positive, kept as recorded) = **PASS**, 0 regressions in arm a (12/12 pass; 4 identical, 5 tier-1, 3 tier-2 judged EQUIVALENT by Fable), ubatch rows >= 32 observed (max 476). AMENDMENT-6 re-check of the b2-long2 arithmetic slip (1,500 polls/s): solo 5/5 CORRECT vs concurrent 4/5 CORRECT (wb-wa = 1 <= 1) = **PASS, numeric noise, A5 PASS stands**. Classification: correctness-only gate, C3 only (AMENDMENT 7 forbids inheriting it to C5; C5 is under CH-31). Post hoc, the same C3 runs read 4/5 REDESIGN concurrent vs 0/5 solo on the final recommendation, the batch dependence recorded in AMENDMENT 9. [belief: cc]
- [x] **CH-30 - fold GPU-LEAK-1c (`experimental/gpu-leak1c-hip-graph-20261023` @ `0a1fa49ee`; ggml-cuda only; manifest V11-104).** 3 commits on champion 141e4bcf5: fd0268ca3 (upstream #26771), 9aba0e3b4 (HIP release stale graph exec + re-instantiate), 0a1fa49ee (env-gated `GGML_CUDA_GRAPH_MEMLOG`). Validated: E1 slope 0.0 vs 290.27 MiB/request (GPU-LEAK-1c-V). Needs before CAS: (1) GPU correctness slice (`test-backend-ops -b ROCm0` FA/MUL_MAT/ROPE etc., as for C3); (2) `fold_gate.py` (code differs in libggml-hip only, expected); (3) short 27B GPU A/B speed check, graphs on, vs the champion. Recommendation: KEEP the MEMLOG commit as a diagnostic (env-gated, off by default) rather than dropping it. Stack after or with CH-29 (rebase if C3 lands first). Recorded 2026-10-23, 3c4ca599.
  - *(2026-10-24, fold-prep subagent of 3c4ca599.)* RE-CUT on the C3 champion, per the fresh-tip rule. The champion is now `dcc853b55` (C3, CAS 2026-10-24); the old base `141e4bcf5` is stale. New branch `experimental/champion-c4-20261024` @ `cdb4d8c77c2300f61c404a3df6d1950934b39c98` (fork, build 10417; worktree `/mnt/raid0/llm/worktrees/c4-fold-20261024`): the 3 CH-30 commits cherry-picked cleanly (`fd0268ca3` -> `652930282`, `9aba0e3b4` -> `a9c38f8e0`, `0a1fa49ee` -> `2a6c1201c`; ggml-cuda only) plus ws58 patch 0002 (`cdb4d8c77`, CH-20.2: test-llama-archs skips deepseek41 / deepseek41-dspark; full run rc 0, 118 OK). The old branch `experimental/gpu-leak1c-hip-graph-20261023` @ `0a1fa49ee` is kept as the validation record only. NOT folded: ws58 patch 0001 (14c57cbe9 / CH-24), because the fused qwen4exp decode is ON by default in code (`llama-context.cpp:1392`, only `GGML_FUSED_DECODE_OFF` disables it) and the live `architect_general` launch env (`stack_env.py _ROLE_ENV_BLOCKS`) does not set it, while FD-DIV-1b found a second fused-MoE defect 0001 does not fix; it stays for a later fold. Prep package `/mnt/raid0/llm/tmp/c4-fold-prep/` (PLAN.md; build_store.sh, gate_c4.sh, c4_build_job.sh, gpu_slice_c4.sh, c4_leak_job.sh, c4_gate_e_job.sh, bundle_gate_c4.sh; none run; rows in ROWS.md validated on a copy). Gates: build + fold_gate vs the C3 images (gpu expect only libggml-hip.so changed, cpu code-identical, no CPU greedy-identity or timing slot needed), GPU correctness slice vs the C3 control, **GPU-LEAK-1c-V on the C4 image (slope <= 10 MiB/request with graphs ON, MEMLOG net 0)**, and the 27B DFlash2 A/B identity C3 vs C4 (graphs on). Then guarded CAS dcc853b55 -> cdb4d8c77, V11-104 PEND -> IN, CH-30b. Open finding for the stack owner: `_ROLE_ENV_BLOCKS["architect_general"]` should set `GGML_FUSED_DECODE_OFF=1` (or confirm the running :8074 env).
  - *(2026-10-24, 3c4ca599.)* C4 build gates PASS (q3 grant 08:53Z, `c4-fold-build` complete 09:00Z): images `kernels/builds/{cpu,gpu}-20261024-cdb4d8c77-c4`; cpu fold_gate byte-identical 12 / explained 2 / unexplained 0 (code-identical to C3), gpu likewise with exactly 1 expected change (`libggml-hip`), linkage PASS both, MEMLOG compiled into the gpu image only. Remaining gates armed: `c4-gpu-correctness`, `c4-leak-check`, `c4-gate-e` (GPU lane, after `kpf18-s1-r3`). 0001 (14c57cbe9 / CH-24) NOT folded: the fused qwen4exp path is default-ON and production `architect_general` does not set `GGML_FUSED_DECODE_OFF` (see FD-OFF-PROD).
  - *(2026-10-24, 3c4ca599 wrap-up.)* C4 gates: `c4-gpu-correctness` SLICE PASS 11:31Z (all op counts match C3, e.g. MUL_MAT_ID 815/815, GET_ROWS 47/47); `c4-leak-check` GPU-LEAK-1c-V PASS 11:39Z (slope 0.0 MiB/req graphs-on vs the ~290 MiB/req defect, MEMLOG pairs net 0, decode tps +0.08%); `c4-gate-e` 27B A/B 09:51Z identity 15/15 but its own P-vs-P floor was pp 62% / tg 8.8% (C3 quiet run 4.46% / 2.00%; arms 11-18 dropped on BOTH P and C = host contention), so speed is INCONCLUSIVE: result set aside as `c4-fold-prep/GATE_e.done.noisy-20261024T0951Z`, wrapper now records floors > 10%/4% as NOISY and retries; re-run booked in the quiet window. Remaining before the C4 CAS: that quiet re-run, then operator approval. Owner from 2026-10-24 ~14:00Z: workspace-58 (handover `/mnt/raid0/llm/tmp/handover-3c4ca599-to-ws58-20261024.md`).
  - *(2026-10-24 21:06Z, workspace-58: C4 gate e re-run PASS. CORRECTED 2026-10-25: "all C4 gates now PASS" was wrong, see the end of this bullet.)* Re-run `/mnt/raid0/llm/tmp/c4-fold-prep/runs/20261024T204042Z/` -> `c4-fold-prep/GATE_e.done` rc 0: `RESULT mtp: PASS=True arms P=15 C=15 identity C==P=True P-self=True pp_tps_median:+0.58% (floor 2.12%) tg_tps_median:-0.00% (floor 2.00%)`, floors inside the wrapper's 10%/4% bar. Earlier runs were NOISY and set aside, not regraded (09:16Z pp floor 62%; 18:04Z pp floor 40.8% from ONE outlier arm 9P pp 490.8 vs ~795 for the rest, tg clean 2.0%): `GATE_e.done.noisy-*`. Remaining: the operator-approved CAS (recipe `/mnt/raid0/llm/tmp/ch28-fold-20261023/PLAN.md` section 3); CH-30 and the manifest rows are ticked at the CAS, not before. **Correction (2026-10-25, workspace-58 CAS subagent):** gate G-a (a0) FAILED on the C4 GPU image: `test-llama-archs` (full) rc=134, `ggml-backend-meta.cpp:474: GGML_ASSERT(ggml_backend_buffer_is_meta(tensor->buffer)) failed` on the `qwen4exp | Meta` row (`c4-fold-prep/GATE_gpu.txt`, `a_llama_archs_gpu.log`; the C5 GPU image fails the same way, `c5-fold-prep/GATE_gpu.txt`; both CPU images rc 0). It was hidden by a gate-script bug: `gate_c4.sh` / `gate_c5.sh` set `fail=1` inside the `$(...)` command substitution that prints PASS/FAIL, i.e. in a subshell, so the failure never reached the summary and the files end `GATE gpu PASS`. The first CAS attempt (2026-10-25) stopped at that precondition. OPERATOR RULING: "Proceed only if C3 also fails". The predeclared C3 control (`/mnt/raid0/llm/tmp/cal-1025/c3-llama-archs-control/`, same argv/env on the C3 image `gpu-20261023-dcc853b55-c3`) returned `VERDICT.json` = **PRE-EXISTING** (rc 134, the same assert on the same row, 0 failing rows before it), so a0 is a pre-existing defect, recorded as META-ASSERT-1 (assigned to Codex), and not a CAS blocker. All other C4 gates (G-a a1-a5, G-b..G-g) PASS.
  - *(2026-10-25, workspace-58 CAS subagent.)* DONE: guarded CAS `dcc853b5559bef4e50acf251f4910f7f4e0ba538 -> cdb4d8c77c2300f61c404a3df6d1950934b39c98` (C4) at 2026-10-25T08:23:52Z, operator-approved (a0 = PRE-EXISTING META-ASSERT-1 per the operator ruling above); `ak-loop-tree` read-tree two-tree form, clean, HEAD and tree = C4 (`d1aa015e4`); fork fast-forward push `dcc853b55..cdb4d8c77` 08:23:55Z, verified with `git ls-remote fork`. Images `kernels/builds/{cpu,gpu}-20261024-cdb4d8c77-c4` (10417). C4 was champion for 18 s: C5 was CAS'd on top at 08:24:10Z (CH-31). Production unchanged (v10 ffc1bac82). Manifest V11-104 IN. CH-30b now actionable. [no-belief: champion CAS is a ref operation; gate evidence is in c4/c5-fold-prep]
  - [ ] **CH-30-F1 - gate-e pp noise floor was blown by a single outlier arm in 2 of 3 runs**: consider an outlier-robust floor estimator (owner/operator rule change; no regrade of the set-aside runs). Filed 2026-10-24, workspace-58.
- [ ] **CH-30b - after CH-30 folds, remove leak-only workarounds**: the VRAM-recycle guard `YG_RECYCLE_GIB` (default 60) in `/mnt/raid0/llm/tmp/fillers-3c4ca599/jobs/yarn_gate_lib.sh`, and f8's graphs-off (`GGML_CUDA_DISABLE_GRAPHS`) workarounds where they exist only for this leak (f8's chain not located by grep in tmp/fillers; f8 to list its own; note only, not edited here). Do not remove if graphs-off serves another purpose.
- [ ] **META-ASSERT-1 - pre-existing champion-line defect: `test-llama-archs` aborts on the qwen4exp `Meta` multi-device row.** rc 134 at `ggml-backend-meta.cpp:474` (`GGML_ASSERT(ggml_backend_buffer_is_meta(tensor->buffer))`). Present on C3, C4 and C5; the C3 control `/mnt/raid0/llm/tmp/cal-1025/c3-llama-archs-control/VERDICT.json` = PRE-EXISTING. The operator ruled it non-blocking for the 10-25 CAS. Fix: assigned to Codex (META-ASSERT-1, due 10-27), on an experimental branch cut from C5. Done when: gate (a0) is rc 0 on the next champion fold.
  - 2026-10-29: `codex-ni-meta-fix-build-r3-20261029` completed the predeclared model-free private C5 host-view build diagnostic → **correctness-only**. CPU and HIP house-profile builds completed with empty profile cache diffs and verified build hashes. In each build, the host-view fixture exited successfully and the mixed Meta/host trailing-view, two-device partial-reduction fixture reported PASS; the baseline host-view and candidate foreign-compute negative controls both produced the expected SIGABRT and exact Meta buffer assertion. The HIP-linked fixtures do not establish GPU execution or residency. Base `c72ec82f5417bb2937310326120f149b665e8400`, patch SHA-256 `92eb7a0cc2b9c56ca2a910ec870961604fdc7d305d236a9b80e3af4aa3147968`; completion marker SHA-256 `4e1e622415f175843ce6b1d812bd2ccc31239e4bdf7f6ff759f9034fefa80327`. Original attempt: `/mnt/raid0/llm/tmp/codex-ni-20261027-meta-fix-prep/repair-r3/successor/build-attempts/end-*/` (select the attempt containing that completion and build hashes). No model, quality, performance, promotion or next-fold a0 verdict; parent remains open. [belief: cc]
  - 2026-10-28: narrow diagnostic `codex-ni-meta-gpu-arch-20261027` (`test-llama-archs --arch qwen4exp --seed 42`, fix-prep build on C5 base `c72ec82f5`, source `520ad4f55`): fixture rc 0, Meta MoE row NMSE vs CPU OK (1.02e-13), MI210 row OK, 9 positive device samples; Meta roundtrip SKIP (tensor split fixture limitation). No numeric threshold was predeclared beyond the harness OK/FAIL, so this is recorded as diagnostic observation -> correctness-only. The exit criterion (gate a0 rc 0 on the next champion fold, full `test-llama-archs`) is NOT met; model_quality_claim=false, full_c5_gate=OPEN. Evidence: /mnt/raid0/llm/tmp/codex-ni-20261027-meta-gpu-arch-ready/packet/run/results.json. [belief: cc]
  - *(2026-10-30, codex-ni prep; not a task tick.)* META full-suite diagnostic READY `codex-ni-meta-full-arch-r1-20261030` was published and keeper ARMED at 16:18:54Z (poller 279944), reusing the existing completed R3 HIP build; source `520ad4f55` matches the compiled candidate and its native symbol is present. Full smoke rc 0 in 11.579 s: 432 rows, 535 OK cells, 329 expected SKIP cells, 118 meaningful HIP NMSE OK cells, 93 residency samples, zero unexpected statuses/FAIL. Cutoff rc 75/partial=true after observing completed MI210 NMSE-OK rows; 2.125 s, 13 residency samples, cleanup verified. Ten full repetitions are only predeclared/scheduled; F1 champion-fold remains open. No production, build, source or CAS change in this prep. Evidence: `/mnt/raid0/llm/tmp/codex-ni-meta-full-arch-ready-20261030/{FULL-SMOKE-PROOF.json,CUTOFF-PROOF.json,ELF-SOURCE-PROOF.json,KEEPER-PROOF.json,PREDECLARED.md}`. File committed conclusion through existing `VB-CC-PILOT`; no native measurement warrant or full-task tick.
    - [ ] **META-ASSERT-1a (filed 2026-10-28):** land source `520ad4f55` on an experimental branch from the current champion tip and re-run the FULL `test-llama-archs` (all arches, not only qwen4exp) on the GPU image; the Meta roundtrip SKIP is a fixture limitation to record, not a pass.
      - *(2026-10-28 test-only diagnostic.)* V2 reproduced a finite exact-roundtrip mismatch for qwen4exp MI210 MoE: original bits `37450b48`, reload `37450b4a`, delta `1.8189894035458565e-12`; 111 during-run own HIP/KFD/positive-VRAM samples, cleanup verified. Cause unresolved, no tolerance change or META READY; the full gate stays open. [Evidence and limits](../../progress/2026-10/2026-10-28-hpr-meta-ready.md). [belief: cc]
      - *(2026-10-28 23:39Z, ws58 results filing: `meta-assert1-qwen4exp-gpu-20261028`, GPU, rc0 complete, wall 10.4 s, 2 stages.)* Private fix-prep HIP build (source `520ad4f55` = C5 `c72ec82f5` + 1 commit, `buildhip/`, BUILD.sha256 and linkage verified) ran `test-llama-archs -a qwen4exp -s 1234` then FULL `test-llama-archs -s 1234`; both exited rc 0, the `ggml-backend-meta.cpp:474` abort did NOT recur, 38 positive own-PID VRAM samples (peak 755 MiB). Full suite: 136 arch names, zero FAIL; MI210 NMSE OK 118 / SKIP 26 (max 4.64e-08, mpt), CPU OK 118 / SKIP 26 (all 0.00), Meta NMSE OK 93 / SKIP 51 (max 1.98e-10, codeshell), roundtrip OK 103 / SKIP 41 on MI210 and CPU, SKIP on all 144 Meta rows (known tensor-split fixture limitation, recorded as SKIP not pass). qwen4exp: MI210 MoE 9.63e-14 OK + roundtrip OK, CPU 0 OK, Meta MoE 9.63e-14 OK / roundtrip SKIP (both stages identical). Predeclared rule is only the harness OK/FAIL (manifest: diagnostic, no model-quality or promotion verdict), so this is a correctness-only diagnostic observation: no threshold invented. Verdict: the original rc-134 Meta assert is absent on the patched C5 build and the full GPU suite is clean once. Box NOT ticked: (a) it ran a private build, not a built `kernels/builds` GPU image, so gate a0 on an image is not yet shown; (b) the 2026-10-28 19:43Z smoke saw an intermittent qwen4exp MI210 MoE roundtrip FAIL (1 of 3 full runs), so a single clean run does not retire it. Evidence: `/mnt/raid0/llm/tmp/codex-meta-assert-next-20261028/attempts/run-1793230774*/` (`0001-full-architecture.log`, `RESULT.json`). Full C5/a0 gate stays OPEN, model_quality_claim=false. [belief: cc]
      - [ ] **META-ASSERT-1a-F1 (filed 2026-10-28, ws58):** carry `520ad4f55` into the next champion fold (C6 candidate) and run gate a0 (full `test-llama-archs`, GPU image) on the BUILT image; that rc 0 is the META-ASSERT-1 done condition and ticks 1a and its parent.
      - [x] **META-ASSERT-1a-F2 (filed 2026-10-28, ws58):** repeat the full GPU `test-llama-archs` on the same patched build several times (count named in the row, since the earlier intermittent roundtrip FAIL was 1 of 3) to bound the qwen4exp MI210 roundtrip flake against this clean run; owner: Codex via a backlog row. ✅ 2026-10-30 [belief: cc]
         - Exact candidate-only rule met: ten full native architecture suites on the same pinned private C5 plus host-view patch, seed 1234. Each suite retained 432 rows, 535 OK + 329 predeclared SKIP cells, zero FAIL/unexpected statuses and 118 meaningful HIP NMSE OK cells. All 870 during-run observations showed own KFD VRAM and HIP mapping; writer and cleanup passed. F1, META-ASSERT-1a and META-ASSERT-1 remain open for champion-fold a0; no quality or promotion claim. [Original event audit](../../artifacts/compute/results-filing-20261030-1650.json). [belief: cc]
  - *(2026-10-28 23:39Z, Codex diagnostic.)* `meta-assert1-qwen4exp-gpu-20261028` ran the private C5 `c72ec82f5` candidate plus host-view patch `92eb7a0c…` under a real q3/GPU grant and ended rc0. The previously failing qwen4exp/Meta MoE row returned OK (NMSE 9.63e-14, roundtrip SKIP) in both the single-architecture and full `test-llama-archs` invocations; the full native output has 226 rows containing SKIP and no FAIL/ERROR/ABORT lines. Original logs and binary/source hashes are under `/mnt/raid0/llm/tmp/codex-meta-assert-next-20261028/attempts/`, with the exact attempt in `RUN_COMPLETE.json`; supervisor recorded owned GPU residency and drained children. This is a bounded private-candidate diagnostic, not the gate on the next champion fold, a model-level regression test, or a promotion; META-ASSERT-1 remains open. [belief: cc]
  - *(2026-10-27 18:45Z, ws58 results harvest.)* GPU stage ran 15:39Z: `test-llama-archs` SIGABRT rc -6 (= 134); residency observed (146 same-sample proofs, peak 545 MiB); 5 `META_ASSERT_DIAG` lines. NI MAIN accepted it as the EXPECTED diagnostic capture (the GPU-UNEXPECTED label was a -6/134 compare bug). The Meta assert is a real open defect; the fix build is being prepared. Out `/mnt/raid0/llm/tmp/codex-ni-20261027-meta-assert1/out`. Stays open. [no-belief: diagnostic capture of a known defect, no fix]
      - *(2026-10-27 21:35Z, ws58 results filing, META-ASSERT-1 quarter recovery.)* `codex-ni-meta-recovery-q0-20261027` rc0 complete at 20:41:20Z (3 s window, q0): artifact-only recovery of the sealed original Meta build artifacts ACCEPTED by NI MAIN (`RECOVERY-ACCEPTED` byte-matches `RECOVERY-WORK-DONE`; RSS 25 MB, drained). Scratch `/mnt/raid0/llm/tmp/codex-ni-20261027-quarter-recovery-variants/meta/`. Artifact verification only: no GPU, no model, no correctness result, and the Meta assert stays an open defect. [no-belief: artifact recovery, no measurement]
      - *(2026-10-27, NI main accepted bounded diagnostic.)* The actual single-architecture qwen4exp Meta MoE fixture returned rc 0, NMSE 1.02e-13, with nine during-run positive KFD samples; Meta roundtrip skipped. [Independent audit and scope](../../artifacts/ni/meta-actual-gpu-audit-20261027/README.md). Full a0 on the next champion fold remains the done condition. [belief: cc]
  - *(2026-10-27 16:05Z, ws58 results harvest.)* Stage 1 (q2 build, `/mnt/raid0/llm/tmp/codex-ni-20261027-meta-assert1/out`) rc0 at 15:10:48Z: BUILD-COMPLETE, source c72, patch da444291, 16 SHA lines, knobs.diff EMPTY (same feature settings as C5), diagnostic symbol present. Stage 2 (GPU) is queued. Progress only; no correctness claim, box stays open. [no-belief: diagnostic build, no measurement]
      - *(2026-10-27 evening, ws58.)* qwen4exp synthetic GPU: MAIN accepted the bounded observation, NMSE 1.02e-13. META-ASSERT-1 stays OPEN. [no-belief: bounded synthetic observation, not a gate]
- [x] **CH-GATE-SUBSHELL - fix the fold gate scripts' `fail=1`-inside-`$(...)` bug.** The assignment runs in a subshell, so gate (a) unit-test failures could not fail the gate. Sites: `/mnt/raid0/llm/tmp/c4-fold-prep/gate_c4.sh:32-33`, `/mnt/raid0/llm/tmp/c5-fold-prep/gate_c5.sh:40`, and the c3 script. Assigned to Codex G1, due 10-25 14:00Z. Every future fold gate must use the fixed template.
  - 2026-10-27 (ws58, NI MAIN accepted): closed. Fresh tracked C3/C4/C5 fold-gate templates use parent-scope verdict helpers and aggregate nonzero results; the planted-failure regressions are recorded in `scripts/champion/fold_gates/BUNDLE-VERDICTS.md` and `BUNDLE-SOURCES.SHA256` (raw: `/mnt/raid0/llm/tmp/codex-ni-20261025-bundle-gate-audit/launcher.out`, `c5-validation/test.log`). The current c4/c5 prep scripts call `gate_set_verdict` directly in parent flow (audited SHA256 C4 `71c50f46d294...`, C5 `3790fb9490a2...`). No new tests or benchmarks were run for this closure. META-ASSERT-1 stays open; no kernel or graph correctness claim. [no-belief: operational shell-gate regression/adoption; no measurement]
  - 2026-10-28 (ws58, NI current-source audit): confirmed already repaired. Current `/mnt/raid0/llm/tmp/{c3,c4,c5}-fold-prep/gate_{c3,c4,c5}.sh` define `gate_set_verdict()` (assigns `GATE_VERDICT=FAIL; fail=1` in gate-process scope) called after captured rc values; none has `fail=1` inside a command substitution. `test_current_gate_verdict.py` (`/mnt/raid0/llm/tmp/codex-ni-20261028-gate-subshell-audit/`) ran rc=0 and rc=7 controls on all three: six controls and static checks pass. Does not execute the full fold gates or native binaries; gate scripts unmodified. The stale defect wording is superseded by "already repaired"; item stays [x]. [belief: cc]
- [x] **CH-31 - build, gate and CAS the C5 fold: `experimental/champion-c5-20261024` @ `c72ec82f5417bb2937310326120f149b665e8400` (C4 `cdb4d8c77` + 2 commits, fork, build 10419; worktree `/mnt/raid0/llm/worktrees/c5-fold-20261024`).** `4976a189f` makes the qwen4exp (Qwen3.8-Flash-Next) fused single-token decode OFF by default in code: it runs only with `GGML_FUSED_DECODE_ON=1`; `GGML_FUSED_DECODE_OFF` (any value) is kept for back-compat and wins when both are set; resolved by the new `llama_fused_decode_env_enabled()`; `test-qwen4exp-fused-rope` gains a knob truth table (default / OFF / ON=0 / ON+OFF -> graph, ON -> fused). `c72ec82f5` is ws58 patch 0001 (`14c57cbe9`, CH-24) via `git am`, clean, content unchanged. The fused path stays opt-in until FD-DIV-1b is fixed (INF-67). Libs: libllama only (no ggml change). Plan, scripts and evidence: `/mnt/raid0/llm/tmp/c5-fold-prep/PLAN.md` (none run). Gates: (1) `c5-fold-build` (one build quarter): unit tests incl. the truth table, `fold_gate.py --expected-changed libllama.so` vs the C4 images, version/linkage, CH-24 source audit + strings, writes `/mnt/raid0/llm/tmp/compute-flags/C5_IMAGE` on the cpu PASS; (2) `c5-cpu-correctness` (one quarter): Q38FN greedy identity with the DEFAULT env (champion OFF=1 vs C5 no-knob and C5 OFF=1, IDENTICAL required) plus the fused opt-in smoke (KNOWN DEFECTIVE, no correctness claim; 0 files under `/tmp/qwen4exp-builds`); (3) **G2-CONC (INF-70, BLOCKING PROMOTION GATE, must run on the PROMOTION CANDIDATE BINARY), CAS- and promotion-blocking, job `g2conc-c5` owned by workspace-58, booked once C5_IMAGE exists**; (4) `c5-gate-b` (whole host quiet): Q38FN timing sign claim, not CAS-blocking. No GPU gate: every libggml* is unchanged vs C4, so C4's GPU results stand. Then the guarded CAS onto the C4 result, manifest V11-106/V11-107 PEND -> IN. Recorded 2026-10-24, fold-prep subagent of 3c4ca599.
  - *(2026-10-24 11:01Z, 3c4ca599.)* Gate (2) `c5-cpu-correctness` PASSED: C5DEF == CHAMP and C5OFF == CHAMP on p1-p3; the fused-ON smoke diverges at token 2, runs ~24x slower, and writes 0 files under `/tmp/qwen4exp-builds`.
  - *(2026-10-24, 3c4ca599.)* Gate (3) G2-CONC on C5 is graded PASS-pending-operator-call by workspace-58 (Fable tier-2 8/8 EQUIVALENT; records `/mnt/raid0/llm/tmp/ws58-g2conc-20261024/runs/cpu-20261024-c72ec82f5-c5/`). One b2-long2 recommendation divergence awaits the operator's call.
  - *(2026-10-24, 3c4ca599 wrap-up.)* G2-CONC status refined: the operator gave two answers on b2-long2 (accept in 3c4ca599; re-check first in workspace-58), so the conservative one applies: G2-CONC = PASS pending the AMENDMENT-8 b2-long2 re-check (`g2conc-c5-recheck`, 5 solo vs 5 concurrent, Ship vs Redesign). G2-CONC's rule is absolute (candidate concurrent vs the same binary solo); banked C3 runs classify solo 0/5 vs concurrent 4/5 REDESIGN, so a re-check FAIL would be a property of the current kernel line, not of C5 - the operator then decides between blocking C5 and filing a champion-line concurrency defect with G2-CONC amended to candidate-vs-champion. Remaining C5 gate: `c5-gate-b` (quiet window). Owner from ~14:00Z: workspace-58.
  - *(2026-10-24 ~14:1xZ, workspace-58: OPERATOR DECISION "Amend rule; file defect".)* The AMENDMENT-8 re-check FAILED under the absolute rule (`recheck-rec/VERDICT` = FAIL: solo 5 SHIP / 0 REDESIGN, identical 846-token output at -t 24/23/20/16/12; concurrent 2 SHIP / 3 REDESIGN). **AMENDMENT 9** (`/mnt/raid0/llm/tmp/ws58-g2conc-20261024/PREDECLARED.md`, sha256 `60a38397db517c464ec2a9b0b30f5c3c415b3dd3448f41a0d909ff9a0d986963`) makes G2-CONC RELATIVE: a candidate passes if, under the same protocol, it is no worse than the current champion under concurrency, plus the unchanged absolute checks (errors, capped outputs, degeneracy). Counts re-derived from the files: C5 concurrent REDESIGN 3/5 vs C3 champion 4/5 (`recheck/runs`, AMENDMENT-8 classifier `classify_rec`, solo 0/5 on C3) -> **G2-CONC on C5 = PASS** (Fable tier-2 8/8 EQUIVALENT stands). The AMENDMENT-8 FAIL stays recorded as observed. CH-31 itself stays open: gate (4) `c5-gate-b` and the guarded CAS remain.
  - *(2026-10-24 ~21:10Z, workspace-58: C5 gates complete.)* `c5-gate-b` `/mnt/raid0/llm/tmp/c5-fold-prep/GATE_b.done` rc 0 18:38:25Z: anchor 51.45 vs candidate 51.03 tok/s = -0.810%, floor None, decisive None. Per `c5-fold-prep/PLAN.md` row G-tb this is a SIGN claim only, informational, blocks nothing. All C5 gates are now complete; the C5 CAS follows C4's (operator-approved). CH-31 stays unticked until the CAS.
  - *(2026-10-25, workspace-58 CAS subagent.)* DONE: guarded CAS `cdb4d8c77c2300f61c404a3df6d1950934b39c98 -> c72ec82f5417bb2937310326120f149b665e8400` (C5) at 2026-10-25T08:24:10Z, operator-approved, right after the C4 CAS; `ak-loop-tree` read-tree two-tree form, clean, HEAD and tree = C5 (`04e57805e`); fork fast-forward push `cdb4d8c77..c72ec82f5` 08:24:14Z, verified with `git ls-remote fork`. **Champion is now C5 `c72ec82f5`**, images `kernels/builds/{cpu,gpu}-20261024-c72ec82f5-c5` (10419; PROVENANCE status CHAMPION, C3 and C4 images SUPERSEDED). Gates: G-a a1-a5 PASS, a0 GPU rc 134 = the same PRE-EXISTING META-ASSERT-1 (C4 correction above; the gate_c5.sh summary had the same subshell bug); G-b..G-d PASS; G-c5 IDENTICAL p1-p3 both arms; G-s PASS; G2-CONC PASS (AMENDMENT 9); G-tb -0.81% decisive None (informational). Manifest V11-106 and V11-107 IN. Production unchanged (v10 ffc1bac82); promotion is workspace-58's. [no-belief: champion CAS is a ref operation; gate evidence is in c4/c5-fold-prep]
  - [ ] **CH-31-DEF1 — champion-line batched-decode batch-invariance defect (not a gate on C5).** Greedy output at concurrent `-np 4` diverges from the same binary run solo (b2-long2: solo SHIP x5 identical vs concurrent REDESIGN 3/5 on C5, 4/5 on C3), so the defect is present in the champion C3 too and is a property of the CPU batched-decode kernel line. Detector `degeneracy.v2.1`, Fable tier-2 judge. Owner workspace-58. Next step: localize which op breaks batch invariance (bisect per-op solo-vs-batched row identity on a small model). Filed 2026-10-24 (operator decision, AMENDMENT 9).

**Fold ledger — 2026-10-20, consolidation of every measured keep and validated feature (candidate "C")** (operator directive 2026-10-20: *"If it was measured as a keep it should be folded into its champion! go ahead and consolidate everything into the champions."*; prepared by `champ-consolidation`; ledger written on the coordinator's authority because ak-ds41-main and workspace-76 have had no heartbeat since 2026-10-08). **The champion has NOT moved**: `ak/champion/llama-cpp-ffc1bac82eec` is still `dd3d9721c` (checked at start and at close). C is `experimental/champion-consolidation-20261020` @ `f0c96dc1f` (pushed to `fork`; worktree `/mnt/raid0/llm/worktrees/llama-champ-consolidation-20261020`), 59 commits on `dd3d9721c`; the CAS waits for the GPU gates and the bundle gate (both staged below).
- **Folded (FOLD set), old→new sha map: `/mnt/raid0/llm/tmp/champ-consolidation-20261020/shamap.tsv`** (rebuilt from the `(cherry picked from commit …)` trailers, so it is the ground truth; the conflict log with a reason for every resolution is `conflicts.txt` beside it):
  - A, small and opt-in: EmbeddingGemma 2 (`f8dd2982b`, `63bc737ea`, zero conflicts); V11-049 upstream #27870 MMA divergent-barrier fix (`e9b3b04df`; folded as a pick, unlike #30514/#30580 which ride the CH-18 pull, because it carries a measured champion-side failure: the 27B probe fails 6/10 on the ROCWMMA-OFF route without it and passes with it; **also listed for the CH-18 pull: reconcile at the v11 pull so it is not applied twice**); KPF-17a shared-trunk FA tests (`ada3fa92e`, conditional on the CPU `-o FLASH_ATTN_EXT` re-pass, see gates; **the KVU-19a 64-case harness is still owed**); test-backend-ops guard bands (4 commits, `AKX_GUARD_BANDS` opt-in, default off); OP-80 sparse-FA mask capture (6 commits, opt-in env).
  - B, Q38FN keeps: `51c375478` (+2.158%), `e530a831e` (+0.054%, noise scale), `b308133e2` (+0.593%), and the q38fn-lane served-shape case set `6ed37bec8`.
  - C, the 14 held DS41 keeps: **9 applied** (`seed-accum`, `q4k-x4t-zmm-widen`, `bscale-cvtph`, `two-row-tail-tiles`, `zmm-pair-unroll`, `q4k-activation-metadata-reuse`, `q8-rn3-single-pair-loop`, `rmsnorm-eight-double-chains`, `rmsnorm-single-pass-output`; sources are the Zp-rebased commits) and **5 SUBSUMED** (empty after conflict resolution because the champion's 10 unledgered keeps already carry the same optimisation; each is proved present by a source grep at the candidate HEAD plus the `GGML_MMID_SLAB` string gate in `presence_cpu.txt`, and cited per manifest row with the code: `ggml_iqk_try_mul_mat_id` grain blocks `const int64_t grain = activation_type == GGML_TYPE_Q8_K ? 256 : 128; units = ne11 * ne12 * ngrain_row` for `4348de400`; `ggml_compute_forward_mul_mat` `nblocks = src1_nrows_total * blocks_per_row` for `e33229348`; `ids->ne[1] >= 2 && <= 8`, `cne1 > 8` gate, `checked_counts` and `first < end` skip for `253e50c32`: `mmid-flat-qact-rows`, `mmid-qact-block-partition`, `dense-qact-flat-block-partition` by `4348de400` / `e33229348`; `mmid-verify-flat-slabs` and `mmid-deduplicate-empty-selection` by `253e50c32`, whose `cne1 <= 8` gate is also exactly what the C112 shape gate `70e7133a1` was, so the gate commit is not needed). The Z bundle result that held these out ("DS41 −2.51% vs floor 4.533%, Q38FN −1.40%, greedy identical") is *not decisive* by the ledger's own rule, not a recorded regression; the bundle gate below re-tests them on the new base.
  - D, GLM-5.3 keeps (measured on a model deleted 2026-09-22): 16 clean picks (9 `recover` commits + `akm-q5k-avx512-fullblock-vnni`, `q8dot-f16c-scale-outer4`, `gdn-f32-dot4-shared-vector`, `gdn-snapshot-update-dual-store`, `q8-mulmat-direct-nrc2-store`, `moe-up-gate-safe-fusion`, `moe-fused-expert-cohorts`) + the row-exact prerequisite `04ffb8ad0` (conflict R10: union with the DS41 `batched-greedy-inexact` mode) + `akm-moe-rowexact-weighted-slabs` **re-ported by hand** (`f0c96dc1f`, active only when `mmid_rowexact` && Q4_K/Q5_K && cne1 ≤ `GGML_ROWEXACT_N`, so every other case is byte-identical). `akm-moe-rowexact-qact-2d-partition` (+18.168%) is SUBSUMED by `4348de400` (flat activation grain blocks over `ne11 * ne12 * ngrain_row` in `ggml_iqk_try_mul_mat_id`; the keep used a fixed 128-element grain for Q4_K/Q5_K, the champion uses 256 for Q8_K activations, same bytes, finer vs coarser balance only). **`akm-openmp-native-spin-barrier` (`340482439`) was folded and then DROPPED (R15)**: it makes `ggml_barrier` use the native atomic barrier on OpenMP builds, and the champion's qwen4exp fused decode (INF-64) calls `ggml_compute_forward_gated_delta_net` from `fused_gdn_layer` with synthetic compute params, where the native barrier never releases: `test-qwen4exp-fused-rope` (6 s on `dd3d9721c`) hung more than 25 min on the earlier build (gdb: `ggml_barrier <- ggml_compute_forward_gated_delta_net <- fused_gdn_layer`). A correctness failure against the champion's own gate; 6 s and OK again after the drop.
  - E: Dual Chunk Attention (`9264f8095`, opt-in `--dca-chunk-size`, one trivial CMake conflict) and the EXL3 CPU backend (13 commits, clean, new types only).
- **NOT folded, with the quoted reason:**
  - kv-prefix-fork p1r2 `14d603f3a`: operator-session ruling 2026-10-20 "NOT a keep: its KPF-18 gate is still running".
  - Upstream pulls #30514 / #30580: CH-18 "never a cherry-pick onto v10; champion folds only through the fold-ledger route" (they ride the fresh-production pull).
  - GLM Q4_K/kquant kernel keeps (`96682e27b 96d22da77 c5baa22ba 5d1acd349 ef37bc548 35186deaf 6e4078401 502075809`) and `d2861045f`: rewrite the same `mul_mat_qX_K_q8_2_X4_T` Q4_K kernel the champion's DS41 keeps already rewrote (`ActivationMetadata` hoist); `d2861045f` applied textually but did not compile (`d8` undeclared, line 1051), so it was dropped by rebase. Alternative implementations of one loop, measured on different models; the champion's was measured on a served model.
  - 2026-10-27 harvest (v11-050-gpu ended 2026-10-24T05:40Z, v11-051-gpu 05:57Z, v11-052-gpu 05:24Z; mi210_0 exclusive, candidate B vs baseline C store build, 3 reps ABA; `/mnt/raid0/llm/tmp/v11-runs/05{0,1,2}/20261024T*/DECISION.json`): all three predeclared decisions = **HOLD**; exactness suites 0 fails (050: 2978/2978 x3; 051: 2978/2978 x3; 052: MUL_MAT 1145 + MUL_MAT_ID 815). V11-050 (fp32 VKQ): no stricter-exactness benefit (delta 0); pp512 -0.19%, pp2048 +0.18%, tg128 -1.70% (base spread 5.2%), all inside floors (tg 2.00% / pp 9.91%). V11-051 (D=256 16-col cap): default-on beats TUNE=0 beyond floor at 0 of 4 shapes (needs >= 2): pp128 +6.8% (base spread 6.7%), pp512 -0.11%, pp2048 -0.03%, tg128 -0.01%. V11-052 (MMQ route ne11>=5): pp5 +4.6%, pp6 +16.2%, pp8 +37.3% (d2048 +37.6%, d49152 +29.5%), pp4 -0.4% (d2048 -4.4%, arm spread 11.7%), tg128 -0.18%; serving A/B tg gain not beyond max(2.00%, spread) or A/B guard unmet, so no per-type cut is folded. Higher t/s is better; quiet-class floors from each PREDECLARED.md. No fold into a candidate follows from these runs. [belief: cc]
  - Needs measurement, not default-on: V11-050 #28576 ("no number read"), V11-051 D=256 16-column cap ("GPU-unvalidated", default-on), V11-052 `289cbafa3` (n=1, "27B pp4 −32%" on the same run, no env knob), V11-086 CPU FA FP32-VKQ arms ("bench pending"), V11-064 loader fix (parked by the operator 2026-09-27, unmeasured), V6R-1..3 (untriaged), V11-066/067 (not built).
  - Excluded by the source: V11-084 `74ee5c502` ("unledgered, `measurement_invalid`"); V11-085 KVU-19b c2 ("~14% slower on aligned 4x8 verify and breaks skip-on == skip-off exactness (6/119 cases)"); V11-087 MMQ J cap ("NEGATIVE, rejected 2026-09-27", p=64 −12.6%); V11-089 `inf70/sync17-fix2` ("DO NOT FOLD, measured REGRESSION" −2.136%); V11-090 ngram (retracted); V11-069 iqk IQ4_NL/MXFP4 allowlist ("slower and changes output"); V11-088 GLM5Next text+MTP (WIP, subject model deleted); `3376147f8` (ds41-lane variant of the served-shape case set: alternate calibration of the same case-set name, conflicts in place with the folded variant).
- **Conflicts resolved (14 records R1–R14 in `conflicts.txt`):** R1 `51c375478` solo-rows bound 3→5 keeping the SUM_ROWS rule; R2 `6ed37bec8` both thread knobs honoured; R4–R9 five DS41 keeps subsumed; R10 `15bb18cfc` union with `batched-greedy-inexact` (enum, names, parse, startup check, proc-address table); R12 CMake union; R13 `d2861045f` dropped; R14 `f75e2a699` re-ported. No gitnexus impact was run: llama.cpp is not in the epyc-root graph, so the blast radius was taken from the per-hunk conflict analysis and the builds + suites below.
- **Build proof (CPU `cpu-20261020-f0c96dc1f`, GPU `gpu-20261020-f0c96dc1f`, both `llama-server --version` 10404 `(f0c96dc1f)`):** champion recipes (`native-openmp-gcc15-cpu-v1`; `gfx90a-house-v1` with **`GGML_HIP_ROCWMMA_FATTN=ON`, `GGML_NATIVE=ON`, `GGML_HIP_MMQ_MFMA=ON`**), CMakeCache `GGML_*/LLAMA_*` entries diff-empty against the `dd3d9721c` store builds; binary mtimes (21:10–21:14Z) later than the last commit (21:10:01Z); `SHA256SUMS` verified; `verify_ggml_linkage.sh` PASS on both; the manifest presence gates (`presence_cpu.txt`: 15 strings gates against the champion build, 7 test binaries, G-ANC, one trailer check per fold row) **0 failures**. The build scripts and the proof are beside the sha map.
- **Gates run tonight (CPU, no region free, co-run at `nice -n 19` pinned to 72-87,168-183 under the operator session's q3 agreement and to q1 24-47 for the greedy servers; nothing on 88-95/184-191):**
  - **Final build `f0c96dc1f` (CPU `cpu-20261020-f0c96dc1f`, GPU `gpu-20261020-f0c96dc1f`)**, from a clean tracked tree; earlier intermediate images (`04c2964ae`, `da367c130`, `746bdb360`) are superseded and were built before the spin-barrier drop.
  - CPU `test-backend-ops -b CPU`, `GGML_IQK=1`, all ops: **16817/16878 passed**. The 61 failures are pre-existing: EXP 4, EXPM1 4, DIAG_MASK_INF 3 fail identically on `dd3d9721c` (control run on the champion store build), and LIGHTNING_INDEXER (50 here) is NONDETERMINISTIC run to run on both builds (champion 55/108 and 55/108 on two runs; candidate 56/108 to 59/108 on its runs; "ERR is invalid"). Dedicated runs on the final build: FLASH_ATTN_EXT **5207/5207** (the KPF-17a re-pass: 5182 + 25 shared-trunk cases), MUL_MAT **1145/1145**, MUL_MAT_ID **815/815** with `GGML_ROWEXACT_N=9` and `=24` (the weighted-slab re-port path is reached by the Q4_K/Q5_K n=4,5 cases; branch execution was not separately instrumented).
  - Unit tests on the final build: `test-repack-parallel` 150/150 bit-exact, `test-gather-rows-e4m3-e8m0` pass, `test-dca` OK (chunk>ctx logits bit-identical to plain on qwen2/qwen35/qwen35moe), `test-exl3` ALL PASS (scalar = VNNI = VBMI), `test-qwen4exp-fused-rope` OK (6 s, NMSEs identical to the champion). `test-rowexact-backend-toggle`: dense-q8 and dense-f32 pass (restored=1, difference_witness=1); **mode `mmid` returns rc=3 (restored=1, difference_witness=0 at ROWEXACT_N 4/8/16/32, also with `GGML_MMID_SLAB=0`)**: toggling row-exactness off does not change the Q4_K 4-token x 8-expert output on C, **control/bisect result (coordinator step 2, 2026-10-20 ~22:55Z): NOT introduced by the fold.** The champion cannot be a control (`dd3d9721c` has neither the test nor `ggml_backend_cpu_set_rowexact`; the test arrives with the `04ffb8ad0` port), so I bisected the C history: building only the champion + the row-exact prerequisite (`5251e5cc6`, the first and only commit that carries the test) gives the same `mmid` result as the final C (`difference_witness=0` at ROWEXACT_N 8/32, slab on and off; dense-q8 witness=1), so none of C's other 58 commits (including the `f75e2a699` re-port) changes it. The port's own source branch `experimental/glm53-keeps-on-v10-20260922` @ `15bb18cfc` (v10 base) gives witness=0 for BOTH dense and mmid under every env tried (ROWEXACT_N 8/32, with and without GGML_IQK_Q8_0), so the test does not witness a difference on its home base with these envs either; the original harness environment was not found. Verdict: pre-existing in the port (its test needs the GLM harness env, or the Q4_K multi-row kernel equals the single-row one at that shape); the toggle itself works on dense. Evidence: `/mnt/raid0/llm/tmp/champ-consolidation-20261020/bisect/{prereq,v10glm}.result`.
  - Greedy identity (own servers on non-production ports): Qwen3.6-35B-A3B-MTP-Q8_0, MTP on, 3 prompts x 256 tokens, `-t 24`: candidate **byte-identical** to the champion `dd3d9721c` on 3/3 with equal draft counters (302/179, 257/190, 317/174) (run on the final build `f0c96dc1f`; the earlier `746bdb360` run was also identical). Q38FN (UD-IQ4_XS, frozen prompts p1 p2 p3, 128 tokens, n_probs 2, drafter stripped): **IDENTICAL 3/3** vs the champion on `f0c96dc1f` (and on `746bdb360` earlier).
  - Not run tonight: GPU gates and the bundle gate (staged), the KVU-19a 64-case harness, `test-backend-ops` on HIP.
  - **Deviations recorded:** (1) rule slip, timing pairing: my greedy servers ran at `nice -n 19` on q0 (CPUs 0-23) in the windows 21:08:36Z-~21:15Z, 21:34:30Z-21:51:39Z and 22:09:39Z-~22:31Z (the last is the Q38FN champion arm; the status read at 22:29Z showed q0 held by `bench-cpu qwentts-threadpool-final`). Reported to the coordinator, who passed the windows to the threadpool agent so it can discard and re-run the affected timing legs. (2) no region was free at the start, so builds and tests co-ran at `nice -n 19` pinned to 72-87,168-183 under the operator session's q3 agreement until the coordinator released q3 (then held under build claim `champ-consolidation-phase3`); the greedy servers also used q1 (24-47, `build` holders). Nothing ran on 88-95/184-191. (3) A first build `04c2964ae` failed (uncompilable `d2861045f`, R13) and a second `da367c130`/`746bdb360` carried the hanging spin barrier (R15); both were superseded by `f0c96dc1f`.
- **Staged, not run (host exclusive until 06:30Z):** `/mnt/raid0/llm/tmp/champ-consolidation-20261020/gpu_gates.sh` (HIP `test-backend-ops` FLASH_ATTN_EXT/MUL_MAT/MUL_MAT_ID + the whole ROCm0 suite with a champion control, and the 27B DFlash2 greedy identity from the Y recipe; the #27870 gate on the ROCWMMA-OFF route still needs an OFF build) and `/mnt/raid0/llm/tmp/champ-consolidation-20261020/bundle_gate.sh` (the Y/Z bundle recipe: DS41 and Q38FN 5-pair ABA of C vs `dd3d9721c` with the loop's own floor selector (DS41 4.533%, Q38FN uncalibrated = sign only), greedy identity, plus item (d), the bundle gate the ten unledgered post-Y keeps never had: `dd3d9721c` vs `b0ba1d427`). Dry-runs of both pass their preflight and resolve all builds and floors.
- **Ten unledgered keeps (V11-033..042)** are recorded here for the first time: `ce2943a03` +2.673%, `86fd98e25` +0.627%, `8b8d28711` +1.112%, `0d270f99b` +3.932%, `96870b11c` +0.350%, `253e50c32` +0.120%, `a331665d4` +3.357%, `4348de400` +2.048%, `7e8aa3665` +1.611%, `e33229348` +0.848% (per-keep 5-pair screening, commit subjects; NOT additive, CH-16). Their bundle gate is item (d).
- **GPU gates ran 2026-10-20 22:36-23:15Z under the coordinator's chain (`gpu_gates.sh`, run `/mnt/raid0/llm/tmp/champ-consolidation-20261020/gpu-gates-runs/20261020T223604Z/`), candidate `gpu-20261020-f0c96dc1f` vs champion `gpu-20261020-dd3d9721c`:** ROCm0 FLASH_ATTN_EXT **2978/2978**, MUL_MAT **1145/1145**, MUL_MAT_ID **815/815**; 27B DFlash2 greedy identity (live :8083 argv, 3 prompts x 128 tokens): **BYTE-IDENTICAL 3/3** with equal draft counters (95/213, 100/186, 90/253); the servers were up ~10 s each because the weights were page-cached, 128 tokens at ~45 tok/s were generated per prompt (server log), and the verdict lines print at the end of the script. Whole ROCm0 suite: C **13041/13094** (53 failures) vs the champion control **13010/13063** (53 failures); the non-LIGHTNING_INDEXER failures are identical (EXP, EXPM1, DIAG_MASK_INF, as on CPU) and the LIGHTNING_INDEXER failures are the same nondeterministic family on both, so no failure counts against C. Still not run: the #27870 ROCWMMA-OFF route probe (needs an OFF build) and the bundle gate.
- **Security fold, 2026-10-21 (coordinator request): CT-12.3b `6dfbc9e86` (control-token spellings in chat request data tokenize as text; opt-out `--chat-input-parse-special`) is carried by candidate C2 = `experimental/champion-consolidation-c2-20261021` @ `b4dd52370` (fork), the commit cherry-picked onto C `f0c96dc1f` without conflict.** C's own branch is unchanged so the bundle gate keeps measuring the candidate it started on. C2 gate script `/mnt/raid0/llm/tmp/champ-consolidation-20261020/c2/c2_job.sh` (queued as a build-role claim on q3, it does not run inside 11:15-14:45Z): CPU+GPU store builds, `test-chat-input-spans`, `test_chat_special_tokens.py`, CT-12.4 template-golden A/B vs the champion, the chat-path unit tests; the 27B greedy re-check is `c2/gpu_greedy_c2.sh --execute --deadline ...` after the GPU timing window. Results are recorded below when they land.
- **2026-10-21 status note (wrap-up 3c4ca599-c; dated record, no result invented).** (1) Bundle gate Block B (items a-d) ran 11:25-12:32Z, rc=0, run `/mnt/raid0/llm/tmp/champ-consolidation-20261020/runs/blockB-20261021T112507Z/` (`bundle_gate.log`, `a/ b/ c/ d1/` JSON): **(a) DS41 C `f0c96dc1f` vs champion `dd3d9721c`, 5 pairs: anchor 23.15 vs candidate 20.18 tok/s = -12.821%, floor 4.533%, decisive=True as printed, but the run is VOID (coordinator ruling 2026-10-21: cold page cache; amended in place from the wrap-up's "regression beyond the floor"):** pair series in run order (anchor / candidate tok/s, order candidate-first, anchor-first, candidate-first, anchor-first, candidate-first): 20.49 / 15.12, 21.68 / 18.67, 23.15 / 20.18, 26.76 / 26.15, 26.59 / 26.63. BOTH arms ramp from ~15-20 up to ~26.5 tok/s over the first three pairs and then settle; C is lower inside each early pair (-26%, -14%, -13%) and the settled pairs 4 and 5 are -2.3% and +0.2%. The 519 GB Sept Q4 was not in the page cache (the cache held the 1017 shards, 746 GB buff/cache at 11:02Z), so the first launches ran during a cache flip and reclaim; the median-based effect inherited the transient. The wrap-up's observation that the host was ~172% of one CPU busy at 11:25:10Z is a contributing factor (the preflight allows up to 1200%). The warm item right after it, (d1), shows the settled behaviour (+1.015%, not decisive). The -12.821% is therefore NOT a measurement of C. (b) Q38FN C vs champion +1.747% (no calibrated floor, sign claim only); (c) Q38FN greedy identity champion / C: p1 p2 p3 IDENTICAL; (d1) DS41 champion vs `b0ba1d427` +1.015%, floor 4.533, decisive=False; (d2) Q38FN champion vs `b0ba1d427` +1.758% (no floor); (d3) greedy identity IDENTICAL 3/3. The log notes the host was busy at ~172% of one CPU at 11:25:10Z, before item (a); see the VOID reading of (a) above (cold page cache). CH-20 stays unticked. Item e (GPU A/B) PASSED earlier. Same window: the DS41-1017 smoke test finished 12:37:35Z, `all_ok` true and champion/candidate token-identical (`SMOKE_OK` written), which un-gates the armed baseline launcher. (2) C2 prep by workspace-5c: `experimental/c-plus-nemotron-bolt-20261021` @ `159767788` = candidate C + Nemotron 3.5 Bolt (V11-097) + the V11-098 hybrid can_shift guard; CT-12.3b (V11-095) is being stacked on top as the C2 security carrier; its pre-check gates run after 13:35Z. C itself is unchanged, so Block B keeps measuring the candidate it started on.
  - [ ] **CH-20.1 - item (a) (DS41 C vs champion on the Sept Q4 + DSpark recipe) is VOID and is superseded; two follow-ups replace the re-run + bisect.** (i) Item (a) is superseded for the target path by the armed 2026-10-22 06:30Z DS41-1017 baseline compare (`/mnt/raid0/llm/tmp/ds41-1017-baseline-20261021/`, `chained_launch.sh`, `RUN_RECORD.json`): 24 A/A pairs for the first 1017 process-level floor, then 5 pairs of C vs champion `dd3d9721c` on the 1017 target-only recipe, with a page-cache warm-up step before the first launch. Done when `RUN_RECORD.json` exists and its compare row is recorded here; a delta inside the floor is not decisive. (ii) Re-gate the CPU DSpark speculative path on 1017 once a 1017 drafter exists (DS41-W6): same bundle recipe as (a), warm cache, quiet host, with its own floor. If either reproduces a drop beyond its floor, bisect the C layers by commit order (A..E). Decides whether C can be the CAS candidate. (filed 2026-10-21; rewritten 2026-10-21 per coordinator ruling)
  - *(2026-10-22, f8; box stays open.)* CH-20.1 (i): the 1017 floor half is DONE: 2.862% (unit process, n = 24, k = 5, interval 1.974-5.757%, build `dd3d9721c`, valid only pre-W5.1a), floor file under `/mnt/raid0/llm/tmp/ds41-1017-baseline-20261021/aa/floor-store/`; the C2 compare (5 pairs) is running (DS41-W5b-compare), so `RUN_RECORD.json` and the compare row are not yet recorded here.
  - **2026-10-21 Block B record (runner for coordinator 3c4ca599; supplements the wrap-up note above, nothing there is removed except the (a) reading).** Evidence `artifacts/champion-consolidation-20261020/blockB-20261021/` (compare JSONs a, b, d1, d2 slimmed to the scalar and sample fields, with the 60 MB residency and belief_capture blocks omitted and the full files kept in the run dir; greedy c and d3, `bundle_gate.log`, `sept_pins.json`). Claim: `region-lock run --cpu-list 0-95 --role bench --gpu-quiet exclusive`, 11:25:07-12:37:35Z, one claim for the bundle plus the 1017 smoke test. Pinned Sept artifacts (so a rerun is unambiguous after the Sept retirement): target `DeepSeek-V4.1-Flash-Q4.gguf` sha256 `a5e2e2c3ada4b2e98d9f9e4b50f6d9c2a12c2c96f5da165c07e13aff9264984e`, drafter `DeepSeek-V4.1-Flash-DSpark.gguf` sha256 `522ce00dedffc369019a6f5917bcd3dfcb343cf7cfdd36c3758e471177b0f3c5`, recipe `ds41-00d118d44-cpu-t48-dspark-b2` template_hash `fe8ee8f3...0612b`, execution_digest `cdb0535c...d623`, launch json sha256 `83be159f...3de9d`. **(b) Q38FN C vs champion +1.747%** (anchor 50.11, candidate 50.99 tok/s; sign claim, no calibrated floor). **(c) Q38FN greedy identity champion / C: IDENTICAL on 3/3 prompts.** **(d1) DS41 champion vs `b0ba1d427` +1.015%, floor 4.533% (process unit), decisive=False (inside the floor)** (anchor 25.89, candidate 26.15; the first anchor sample 21.99 is the cold launch). **(d2) Q38FN champion vs `b0ba1d427` +1.758%** (sign claim; samples noisy in pairs 3-4: candidate 34.71 and 42.31, anchor 45.51 and 44.69, cause not attributed). **(d3) Q38FN greedy identity `b0ba1d427` / `dd3d9721c`: IDENTICAL 3/3** - this closes the greedy-identity half of the ten-unledgered-keeps bundle gate (V11-033..042: the speed half is d1 not decisive at +1.015% inside 4.533%, d2 +1.758% sign only). **1017 smoke test PASS** (`SMOKE_RESULT.json`): both builds loaded the 9-shard 1017 MXFP4, served the frozen request twice with 256 tokens each time identical, champion/candidate token-identical; champion load 105 s, 17.04/17.16 tok/s; candidate load 95 s, 16.79/16.83 tok/s; MemAvailable 1100.8/1103.9 GiB before loads; overlap with f8's KPF-18 item 4 on the MI210 recorded in the file. CH-20 stays unticked.
  - [ ] **CH-20.2 - `test-llama-archs` fixture generation aborts at `deepseek41` ("Dense": `key not found in model: deepseek41.expert_feed_forward_length`), so every fixture-dependent ctest is "Not Run" on a store build; fix the fixture generator (or skip the arch with a recorded reason, as C2 `f9c01ce0e` did for gemma-embedding2).** Evidence: `/mnt/raid0/llm/tmp/nemotron-c2-prep-20261021/archs_cmp.log` (`deepseek41` and `deepseek41-dspark` fail on the champion control AND on C2, so it is pre-existing, not a C2 regression) and `ctest_unit_b.log`. Until fixed, the C2 gate accepts 5c's direct runs of `test-memory-can-shift` and `test-recurrent-state-rollback` (rc 0 on qwen35 and nemotron_h; main ruling 2026-10-21). Owner of the fix is the champion-fold/manifest owner, not c2-regate. (filed 2026-10-21 by c2-regate at main's request)
  - **2026-10-21 C2 re-gate (c2-regate, plan `/mnt/raid0/llm/tmp/c2-regate-20261021/PLAN.md`).** Candidate C2 = `experimental/c-plus-nemotron-bolt-20261021` @ `49550eda5` supersedes C as the next champion candidate (the old "C2" `b4dd52370` is retired, manifest V11-095). DS41 1017 arm switched C -> C2 (`chained_launch_c2.sh`); items b,c,e and the Nemotron GPU leg are armed as chained launchers under `/mnt/raid0/llm/tmp/c2-regate-20261021/flags/`. CAS NOT done; it is main's decision after the gates.
- **Owed before the CAS:** GPU gates, bundle gate (a–d), KVU-19a 64-case harness (KPF-17a), DCA 400K/500K needle A/B and YaRN native-window gate, EXL3 model-level windows. If the bundle gate shows a regression beyond the floor, the layers are separable by commit order (A, B, C, D, E in that order; `git rebase -i` drop of the offending layer).
- **NEEDS-MEASUREMENT items are staged** under `/mnt/raid0/llm/tmp/champ-consolidation-20261020/measure/` (`lib.sh`, `build_arm.sh`, one script per item: V11-050 `m_V11-050_fp32vkq.sh`, V11-051 `m_V11-051_d256cap.sh`, V11-052 `m_V11-052_kqroute.sh`, V11-086 `m_V11-086_cpu_fa_vkq.sh`, V11-064 `m_V11-064_loader_team.sh`, V6R-1..3 `m_V6R-1_2_3_triage.sh`, V11-066/067 `m_V11-066_067_q38_t10.sh`), each with its gate, arms (C vs C + item) and a predeclared keep rule from the ledger floors (DS41 4.533% process unit, Q38FN sign-only, GPU tg 2.00%, pp 9.91%). They are dry-run by default; `--execute` after 06:30Z. **The GPU `ab_probe.py` harness (`/mnt/raid0/llm/tmp/gpu-champion-ab/`) is no longer on disk**, so the GPU arms use llama-bench ABA plus test-backend-ops plus the 27B greedy identity until main restores or replaces it. Each item that measures a keep folds into the next candidate.
  - **2026-10-22 (v11-086-unhold) — V11-086 UN-HELD and retargeted.** Operator: "Can we schedule this test also please?" (relayed by workspace-58); the change applies to every F16-V CPU model, so the DS41 hold covered only the workload. Re-port `5bde1b83d`+`13bdbdc4d` onto C as ONE commit, without `2ad8bff36`: `experimental/fa-vkq-reg-on-c-20261022` @ `8110933ba` (fork). Answer to "does C already give FP32 VKQ?": only partly — C (`9a3f1392a`) accumulates F16 V in FP16 + end-of-row overflow check and recomputes ONLY overflowed rows in FP32 (`GGML_FA_VKQ_F32=1` forces FP32 every row); the picks add only option A (64-cell scored blocks, one rescale per block, FP32 accumulator in DV/16 zmm registers) and the knob `GGML_FA_VKQ_REG=1|auto`; unset = C's path unchanged. Two adaptations: the KVU-19 -INF run skip is kept in the REG loop; REG never runs under the CPU reference backend, so a knob-set test-backend-ops run checks REG against the hybrid (it was vacuous on the branch tip). Workload moved DS41 -> Qwen3.8-Flash-Next (architect_general, f16 KV, D=256): frontdoor serves q8_0 KV, where no FA-VKQ path runs. Build+correctness filler `v11-086-fa-vkq-build` (job `/mnt/raid0/llm/tmp/fillers-3c4ca599/jobs/v11_086_fa_vkq_build_job.sh`, tbo FA x6 + FA harness -> `/mnt/raid0/llm/tmp/v11-runs/086v2/correctness/INTEGRITY.json`); timing poller `v11-086-cpu` re-armed from `v11drv/v11_driver_086v2.py` (rule `predeclared/086v2/PREDECLARED_086v2.md`, sha `48897be2`, decision default_on_VKQ_REG_auto / fold_opt_in_default_off / hold). Slot requested from workspace-58: block-timing-quiet whole host, ~1h45m, 95 GiB (weights 87.3 + MTP 2.6 + KV/state ~1 + 4). No result yet.
  - **2026-10-22 (v11-086-integrity) — integrity = HOLD as written (`tbo_fa_100` False), but no REG bug: the 12 failures are the FP16-accumulating test oracle.** The `cpu_fa_longctx_v1` set failed 5230/5242 on B REG=1 and REG=auto: D=256 nb=1..5 at kv 65536/131072 (ERR 1.31e-3..3.00e-3) and D=512 nb=1 at kv 32768/65536 (7.0e-4, 1.45e-3), threshold 5e-4. The `use_ref` oracle accumulates F16-V VKQ in FP16 over the full KV. ERR grows linearly with KV at the same ~2.2e-8 per cell on REG and non-REG paths. The two D=512 failures cannot run REG (DV>256), and their nb>=2 siblings, which run the oracle's own loop, pass. The fixed-seed harness puts REG vs C at 3.3e-5..8.9e-5 for 1024-4096 visible cells, and at exactly 0 wherever REG is off. Prediction: C and B-unset fail the 4 nb=1 cells (split-KV), and REG adds the 8 nb>=2 cells by being more accurate than the oracle. Parser fixed (ANSI colour hid every FAIL line; INTEGRITY.json regenerated, still False). **Next:** main arms filler `v11-086-longfa` (job `/mnt/raid0/llm/tmp/fillers-3c4ca599/jobs/v11_086_longfa_job.sh`; arms C, B-unset, C SPLIT_KV=0, C VKQ_F32=1; long cases only; ~10 min, build role). After that, the oracle/tolerance decision package in `progress/2026-10/2026-10-22-v11-086-integrity.md` goes to the operator. Timing poller `v11-086-cpu` stays BACKLOG.
  - [x] **V11-086-DRV — fix the timing driver's correctness parser (filed 2026-10-22, 3c4ca599).** `v11drv/v11_driver_086v2.py::parse_tbo` matches `\bFAIL\b` and NMSE, but the build prints `ERR` with ANSI colors, so it would misread the build's own tbo output. Reuse `parse_tbo_text` from `fa086v2_integrity.py`. Apply only after the live `v11-086-cpu` poller is idle (never edit a script a running poller may execute). Done when the driver parses a captured build log the same as `parse_tbo_text`. ✅ 2026-10-23 (3c4ca599): `parse_tbo` now delegates to `parse_tbo_text` (ANSI-stripped; ERR+NMSE; `max_nmse_on_fail` kept, `max_err_on_fail`/`failed_cases`/`parser_consistent` added). Applied atomically while no driver process was running (the `v11-086-cpu` poller was waiting); backup `v11_driver_086v2.py.bak-pre-drv`; `--selftest` gained a check on the captured LONGFA `first_fails` (28 checks OK).
  - **2026-10-23 (v11-086-longfa) — long-context FA baseline measured; the 4 nb=1 failures are PRE-EXISTING on C and independent of REG.** `/mnt/raid0/llm/tmp/v11-runs/086v2/longfa/LONGFA.json` (filler `v11-086-longfa`, rc 0, 35 long `FLASH_ATTN_EXT` cases, `all_predictions_met` true, no unpredicted fails): C 31/35, B-unset 31/35 with the identical fail set (the 4 nb=1 cells, all prec=f32 K/V f16: D256 kv 65536/131072, D512 sinks=1 kv 32768/65536; ERR 6.7e-4..2.9e-3 vs 5e-4); C `GGML_FA_SPLIT_KV=0` 35/35; C `GGML_FA_VKQ_F32=1` 35/35. Supported: those 4 failures exist without V11-086 (REG is off in C and B-unset) and vanish when either split-KV is off or accumulation is FP32, so they are the FP16-accumulation disagreement between the oracle's single full-KV chain and C's default split-KV path. NOT measured: which side is closer to exact (no FP64 reference run; the near-FP32 claim for split-KV comes from the earlier harness dumps), and REG under any FP32-oracle arm. The other 8 failures (D256 nb>=2) are not on C (C passes them), so they are REG-vs-FP16-oracle differences, still unverified against an FP32 oracle. Integrity stays HOLD as written. Decision package: `/mnt/raid0/llm/tmp/v11-runs/086v2/longfa/DECISION.md` (the predeclared rule can only be amended by the operator).
  - [x] **V11-086-LONGFA — run the long-context FA baseline (C, B-unset, C SPLIT_KV=0, C VKQ_F32=1).** ✅ 2026-10-23 (3c4ca599): result and conclusion in the entry above.
  - **2026-10-23 (v11-086-fp32-oracle) — OPERATOR DECISION: option B (FP32 `use_ref` oracle, tolerance stays 5e-4); amendment recorded, rerun predeclared (3c4ca599).** Gate location: the integrity rule lives in `/mnt/raid0/llm/tmp/fillers-3c4ca599/v11drv/predeclared/086v2/PREDECLARED_086v2.md` (sha-pinned `48897be2`, outside `MEASUREMENT.md` and `measurement/protocols/`, which do not define it), so no ratify script is needed: the amendment is the addendum `predeclared/086v2/ORACLE_AMENDMENT_20261023.md` (sha `f0ef6c54`, pinned by hand in `PINNED.sha256`; the v1/v2 files are unchanged). Oracle change = ONE commit per base, both pushed to `fork`: `experimental/v11-086-fp32-oracle-20261023` @ `d6cabef11` (on B `8110933ba`; `ggml/src/ggml-cpu/ops.cpp:9436-9438`, `vkq_f16_first` and `vkq_check` gain `&& !params->use_ref`) and `experimental/v11-086-fp32-oracle-on-c-20261023` @ `df3e0f8cf` (same edit on C `f0c96dc1f`; the `vkq_check` line differs between C and B, so the B commit does not cherry-pick onto C). Only `libggml-cpu`'s reference path changes; non-reference execution is bit-unchanged. Rerun job (NOT armed, NOT run): `/mnt/raid0/llm/tmp/fillers-3c4ca599/jobs/v11_086_fp32_oracle_job.sh` (2 fresh builds ~1.5 min wall each at 32 threads, ~50 core-min each; phase 1 standard corpus on C ~11 min, gate; phase 2 standard on Bunset/B1/Bauto ~35 min plus the 35-case long set on 4 arms ~2 min; ~50 min serial, resumable), scorer `v11drv/fa086v2_oracle_rerun.py` (smoke-tested on the old logs). **Prediction (declared before any run):** standard 100% on all arms; long set B REG=1/auto 35/35; **C and B-unset 27/35, failing exactly the 8 D256 nb>=2 cells** (C FP16 hybrid vs an FP32 oracle, the mirror of REG vs the FP16 oracle). So the letter of the old rule ("100% on C") would HOLD again; the addendum states clause A3 in advance (A1 standard 100% x4; A2 long 100% on B; A3 C and B-unset long failing sets identical, recorded as the champion's FP16-accumulation property). **Operator to confirm A3**; until struck, main proceeds under it. If confirmed by the data, REG is the more accurate path at long KV on D256, which bears on the decision. V11-086 stays HOLD until the rerun is read.
  - [x] **V11-086-ORACLE-1 — build the two FP32-oracle stores (C+oracle `df3e0f8cf`, B+oracle `d6cabef11`).** Main books a build slot (32 threads, ~10 min incl. linkage) and arms `v11_086_fp32_oracle_job.sh` as filler `v11-086-fp32-oracle` (class cpu, correctness, no quiet host). Done when both `kernels/builds/cpu-20261023-*-fp32oracle-{c,b}` exist with `SHA256SUMS` + `LINKAGE.txt` PASS. ✅ 2026-10-23 (3c4ca599): both stores built, `SHA256SUMS` + `LINKAGE.txt` PASS (`kernels/builds/cpu-20261023-{df3e0f8cf-fp32oracle-c,d6cabef11-fp32oracle-b}`).
  - [x] **V11-086-ORACLE-2 — PHASE 1: standard corpus on C+oracle (the ~3.6e-4 near-kv16k cases).** `std_C` must be 5207/5207 under tolerance 5e-4; else the job writes `PHASE1_FAIL` and stops, and the oracle change returns to the operator. Done when `fp32oracle/std_C.rc` and the phase-1 verdict are recorded. ✅ 2026-10-23 (3c4ca599): `std_C` rc 0, 5207/5207 under 5e-4, no `PHASE1_FAIL` (the near-kv16k cases stay under tolerance on the oracle).
  - [x] **V11-086-ORACLE-3 — PHASE 2: long set on 4 arms + standard on Bunset/B1/Bauto.** Arms C, B-unset, B REG=1, B REG=auto; compare with the prediction above. Done when `/mnt/raid0/llm/tmp/v11-runs/086v2/fp32oracle/ORACLE_RERUN.json` exists and its `prediction_met` is read. ✅ 2026-10-23 (3c4ca599): `ORACLE_RERUN.json` written 16:51:48Z; `prediction_met` read: std 100% x4 and C == B-unset hold, **long B 35/35 and C 27/35 FAILED** (27/35 on B, 19/35 on C). Numbers in the decision entry below.
  - [ ] **V11-086-ORACLE-4 — install the amended INTEGRITY.json and re-arm the timing poller.** After ORACLE-3: move `correctness/INTEGRITY.json` to `.bak-pre-fp32-oracle`, write `ORACLE_RERUN.json["integrity_amended"]` in its place, then FILLERS `v11-086-cpu` goes BACKLOG(blocker=harness fix: INTEGRITY refresh) -> ARMED. Not before: with `tbo_fa_100` False the driver forces `hold` after a 1h45m whole-host run (`v11_driver_086v2.py` `decide_086`). **Install DONE 2026-10-23 (3c4ca599, ~16:56Z):** amended `correctness/INTEGRITY.json` written (`tbo_fa_100` TRUE under the operator rule; `tbo_fa_100_letter` FALSE and `tbo_fa_100_A2_as_pinned` FALSE kept alongside; backup `INTEGRITY.json.bak-pre-fp32-oracle`; script `v11drv/oracle4_install.py`); `v11_driver_086v2.py 086 --check-builds` rc 0, driver `--selftest` OK (28 checks); no timing run. **Box stays open for the re-arm only:** FILLERS `v11-086-cpu` BACKLOG -> ARMED is main's (draft with the filler_run9 launcher: `/mnt/raid0/llm/tmp/v11-runs/086v2/REARM.md`; the live poller 1995971 runs filler_run2 and must be replaced by captured PID).
  - **2026-10-23 (v11-086-oracle4) — FP32-oracle rerun READ; OPERATOR DECISION: "A3 as accepted: REG passes" (~16:55Z); integrity installed (3c4ca599).** `/mnt/raid0/llm/tmp/v11-runs/086v2/fp32oracle/ORACLE_RERUN.json` (written 16:51:48Z). **Standard corpus 5207/5207 on all four arms** (C, Bunset, B1, Bauto; A1 true). **Long set (35):** C and Bunset 19/35 with IDENTICAL 16-key fail sets (A3-identity true) = hsv=256 kv 65536/131072 nb=2..5 plus hsv=512 kv 32768/65536 nb=2..5, max err 2.97e-3; B1 and Bauto 27/35, failing exactly the 8 hsv=512 kv 32768/65536 nb=2..5 keys (a subset of C's set), max err 1.4e-3. REG therefore fixes all 8 D256 cells and none of the 8 D512 cells. Every nb=1 cell passes on every arm. **Failed prediction (recorded):** the amendment predicted B 35/35 and C 27/35 failing only the 8 D256 cells; actual B 27/35 and C 19/35 (16 fails), so the FP16-accumulation story covers D256 but the D512 half was not predicted. **Pinned amendment as written:** `tbo_fa_100` = A1 and A2 and A3 with A2 = REG 35/35 is FALSE. **Operator ruling:** A3 is "REG is judged only on cells outside the C/B-unset common fail set"; A2 is superseded by it: a candidate passes iff its long-set fail set is a subset of the C-and-Bunset common fail set AND A1 AND A3-identity. B1 and Bauto fail sets (8 each) are subsets of the 16-key common set, so `tbo_fa_100` = TRUE. Decision addendum `/mnt/raid0/llm/tmp/fillers-3c4ca599/v11drv/predeclared/086v2/OPERATOR_DECISION_A3_20261023.md` (sha `88d99e7b`, appended to `PINNED.sha256`). The decision rule is otherwise unchanged and still reads `tbo_fa_100`; V11-086 leaves the integrity HOLD and goes to timing. The D512 cells are NOT declared correct: they fail on the champion and the candidate alike vs the FP32 oracle (operator: keep investigating, V11-086-D512 below).
  - [x] **V11-086-D512 — find out why the 8 hsv=512 (sinks=1) kv 32768/65536 nb=2..5 cells fail the FP32 oracle on every arm incl. REG.** Static read (B `8110933ba`, `ggml/src/ggml-cpu/ops.cpp`), H1: `fa_vacc_f16_select(512)` -> NR=32 -> `default: return nullptr` (9289-9312), so `vkq_reg` is false (9431, 9435) under REG=1 and auto; the hybrid FP16 chain runs whole-KV (9628-9688) because nb>=2 is never split-KV (10265) and never tiled (Q tile 64, 10326-10330). Error is ~2.1e-8*kv on D256-on-C and D512 alike (D-independent FP16 accumulation); the per-cell D512 errors are in the same band on all four arms. H2 (only if H1 fails): sinks=1 path (9704-9719) or the F16 Q.K dot (D512 cells carry sinks=1, D256 long cells sinks=0). One probe, designed and NOT run: `/mnt/raid0/llm/tmp/fillers-3c4ca599/jobs/v11_086_d512_probe_job.sh` (5 arms on the B+oracle store, 8 keys, ~5 min, CPU correctness, build role; prediction: unset, REG=1, VKQ_F16=1, SPLIT_KV=0 0/8 pass, `GGML_FA_VKQ_F32=1` 8/8 pass), FILLERS row draft `/mnt/raid0/llm/tmp/v11-runs/086v2/D512_ROW.md`. Done when `/mnt/raid0/llm/tmp/v11-runs/086v2/d512/probe/D512_PROBE.json` is read and the fix path is chosen (D512 REG variant with two 16-zmm halves vs VKQ_F32 at D512 vs leave as a champion property). ✅ 2026-10-23 (3c4ca599): D512 fixed: `experimental/v11-086-d512-reg-20261023` @ e70926716 (on REG 8110933ba; `fa_vacc_f16_select` case 32 -> `fa_vacc_f16_block_x2<16>`, DV=512 as two 16-zmm halves, per-lane FP32; pushed to fork). Validated on build `cpu-20261023-0182ff29c-d512val` (fix + FP32 oracle d6cabef11, branch `experimental/v11-086-d512-val-20261023` @ 0182ff29c), job v11-086-d512-val COMPLETE 18:05:51Z, `/mnt/raid0/llm/tmp/v11-runs/086v2/d512/val/D512_VAL.json`: new 19-case `cpu_fa_d512_reg_v1` 19/19 with REG=1 and auto (REG-unset control 9/19, as pre-fix); long set 35/35 with REG=1 and auto (was 27/35; REG-unset fail set = pre-fix Bunset set); standard corpus 5207/5207 with REG=1, auto, unset; all_gated_met true, fix_validated true.
  - **2026-10-23 (v11-086-d512-fix) — PROBE READ: H1 CONFIRMED; D512 REG fix committed, validation prepared, NOT run (3c4ca599).** `/mnt/raid0/llm/tmp/v11-runs/086v2/d512/probe/D512_PROBE.json` (`all_predictions_met` true, B+oracle store): the 8 D512 nb 2..5 kv 32768/65536 cells are 0/8 under unset, `GGML_FA_VKQ_REG=1`, `GGML_FA_VKQ_F16=1` and `GGML_FA_SPLIT_KV=0` (ERR 6.7e-4..1.5e-3) and 8/8 under `GGML_FA_VKQ_F32=1`, so the residual is the FP16 accumulation chain and REG never reached D512. Fix, option (a): `experimental/v11-086-d512-reg-20261023` @ `e70926716` (fork, plain push; one commit on the REG branch `8110933ba`): `fa_vacc_f16_select` gains `case 32` -> `fa_vacc_f16_block_x2<16>`, DV=512 accumulated as two independent halves of 16 zmm registers (32 accumulators would fill the whole register file and spill); each output lane keeps its own FP32 accumulator, same weights and V-row order, so the result equals a 2x-wide block and only the `w[]` loop runs twice per 64-cell block. Chosen over (b) (fall back to the FP32 accumulate path) because it is a 20-line change that keeps REG's speed at D512 and every other head dim is untouched; (b) would have cost 3-14% decode on FA-bound shapes. Test: new case set `cpu_fa_d512_reg_v1` in `tests/test-backend-ops.cpp` (19 cases: D512 kv 4097/4160/32800 x nb 1/2/5 with block tails, unmasked D512, MLA 576/512, and the 8 failing long cells); the long cells need the FP32 `use_ref` oracle (`experimental/v11-086-fp32-oracle-20261023` @ `d6cabef11`), so validation runs on `experimental/v11-086-d512-val-20261023` @ `0182ff29c` (= fix + cherry-pick of the oracle; fork). No build or run happened in this step (the syntax is reviewed, not compiled). This box stays unticked until V11-086-D512-V reads.
  - [x] **V11-086-D512-V — validate the D512 REG fix (CPU build role, ~1 h, 32 threads, correctness only).** Main arms filler `v11-086-d512-val` from the draft row `/mnt/raid0/llm/tmp/v11-runs/086v2/d512/VAL_ROW.md` (job `/mnt/raid0/llm/tmp/fillers-3c4ca599/jobs/v11_086_d512_val_job.sh`, `bash -n` ok, scorer `v11drv/fa086v2_d512_val.py`; builds `0182ff29c` into `kernels/builds/cpu-20261023-0182ff29c-d512val`). Prediction (declared before any run): `d512_V1`/`d512_Vauto` 19/19, `long_V1`/`long_Vauto` 35/35 (before: 27/35), standard 5207/5207 on REG=1, auto and unset, control `long_Vunset` 19/35 with the same fail set as `fp32oracle/long_Bunset`. Done when `/mnt/raid0/llm/tmp/v11-runs/086v2/d512/val/D512_VAL.json` exists and `fix_validated` is read; then tick V11-086-D512 and fold `e70926716` with the REG feature. ✅ 2026-10-23 (3c4ca599): D512 fixed: `experimental/v11-086-d512-reg-20261023` @ e70926716 (on REG 8110933ba; `fa_vacc_f16_select` case 32 -> `fa_vacc_f16_block_x2<16>`, DV=512 as two 16-zmm halves, per-lane FP32; pushed to fork). Validated on build `cpu-20261023-0182ff29c-d512val` (fix + FP32 oracle d6cabef11, branch `experimental/v11-086-d512-val-20261023` @ 0182ff29c), job v11-086-d512-val COMPLETE 18:05:51Z, `/mnt/raid0/llm/tmp/v11-runs/086v2/d512/val/D512_VAL.json`: new 19-case `cpu_fa_d512_reg_v1` 19/19 with REG=1 and auto (REG-unset control 9/19, as pre-fix); long set 35/35 with REG=1 and auto (was 27/35; REG-unset fail set = pre-fix Bunset set); standard corpus 5207/5207 with REG=1, auto, unset; all_gated_met true, fix_validated true.
  - **2026-10-23 (v11-086-d512-validated) — V11-086-D512 VALIDATED (3c4ca599).** Fold candidate for V11-086 is now `8110933ba` + `e70926716` (REG plus D512): at the next champion fold the REG feature MUST include e70926716. The booked timing run `v11-086-cpu` (10-25 05:05Z) measures 8110933ba on Qwen3.8-Flash-Next (D=256); the D512 path does not run there, so it is unaffected and stays valid for the REG speed decision.
  - [x] **V11-086-CHAMP-NB1 — file the champion long-context accuracy property.** C (FP16 hybrid, `SPLIT_KV` default) differs from an FP32 oracle by 7e-4..3e-3 on D256 nb>=2 kv>=65536 (predicted) and its nb=1 cells fail the FP16 oracle only through split-KV; production runs `GGML_FA_SPLIT_KV=0`. Record in the v11 manifest once ORACLE-3 confirms it. ✅ 2026-10-23 (3c4ca599): filed as KP-1 in `docs/reference/kernel-manifests/llama-v11-manifest.md` (section *Known accuracy properties of the champion*). The MEASURED half (the four nb=1 cells fail only through split-KV: C 31/35, C `SPLIT_KV=0` 35/35, `VKQ_F32=1` 35/35; registry sets `GGML_FA_SPLIT_KV=0` on `architect_general` and `qwen38_flash_next_ud_iq4xs_local`, other CPU roles get the compiled default ON) is filed as fact. The D256 nb>=2 vs FP32-oracle half stays labelled PREDICTED in KP-1 and is updated in place when V11-086-ORACLE-3 reads; that update belongs to ORACLE-3, not to this box.
  - **2026-10-25 (v11-086-b-stall-diag) — B is NOT stalled. Its llama-bench rows run the hardened protocol unrequested, so B does 4 depth fills where C does 1 (workspace-58).**
    - **Evidence:** epyc-inference-research `data/v11-086/b-stall-diag-20261025/` (README, VERDICT.json, PREDECLARATION.md sha `cf90e159`, which matches its `.sha256`).
    - **Setup:** one quarter, `-t 24`, the single cell `tg32@d32768`, C `f0c96dc1f` first, then B `8110933ba`. Linkage PASS for both arms.
    - **Predeclared verdict: GRAY-2-5X.**
      - Job walls: B 1449 s, C 400 s, ratio 3.62. Both walls are upper bounds because of the 30 s poll.
      - Process walls from bench-JSON mtimes: B 1435 s, C 371 s, ratio 3.87.
      - tg32 avg_ts: B 8.92 t/s, C 8.45 t/s, so the rate ratio C/B is 0.95.
      - Meaning: B is slower by the measured ratio, not stalled. No defect claim.
    - **OBSERVATION: where the time goes.**
      - Load plus context takes about 6 to 7 s on each arm.
      - B's row says `autokernel_hardened: true` although the argv has no `--autokernel-harden`. C's row says false.
      - At `-r 1` the hardened path runs 2 contexts. That means 2 warmup fills, then a measured fill and a replicate fill, so 4 fills of 32768 tokens. C runs 1.
      - Per fill: B about 353 s, C about 361 s, so B/C is about 0.98.
      - **The whole 3.62x is in the depth-fill phase, and it is fill COUNT, not fill speed.**
    - **The 10-24 whole-host 086v2 rows show the same thing.**
      - Bunset0 and Bauto0 rows are all hardened. C0 is not.
      - Hardened B `pp5@d32768` at `-r 3` means 6 contexts and 12 fills. It took 2194 s and 2189 s, about 182.6 s per fill.
      - C0's single fill took 182 s, and its `tg32@d32768` cell reused the cached depth state (10 s).
      - The 3000 s per-launch cap killed both B launches 13 min into the second 12-fill cell. That is the "stall" in V11-086-SLOW-1.
      - Copies are in `whole-host-086v2-20261024/`.
    - **Cause:** this is the known V11-103 llama-bench uninitialised-flag defect (CH-28, fixed in `141e4bcf5` / build 10412). Builds 10404 and 10405 both predate the fix.
    - **Why this blocks an A/B:**
      - Across the processes so far, B was hardened 3/3 and C 0/2. Whether that split is random or fixed per binary is not established.
      - The 086v2 A/B as it stands would compare two different protocols.
      - The LBH-3 guard and `scripts/vidya/adapters/_llama_bench_protocol.py` refuse such rows (`unrequested_hardened`).
    - **Probe defect:**
      - `job.sh` probed `ps --ppid $cp | head -1`, which is the `env`/`numactl`/`taskset`/`timeout` exec chain (rss 7276 kB, 1 thread), not llama-bench.
      - Fix, self-tested on a sleep chain: `lb_pid() { local p; for p in $(cat /proc/$1/task/*/children 2>/dev/null); do [ "$(cat /proc/$p/comm 2>/dev/null)" = llama-bench ] && { echo "$p"; return 0; }; lb_pid "$p" && return 0; done; return 1; }; bp=$(lb_pid "$cp")`.
      - Not filed as a task: `job.sh` is a completed one-off, and the fix sits in the evidence README for any reuse of the probe template.
    - **Window sizing. Per fill and per token, B runs at C's speed, so size from the fill count.**
      - **(a) Ordinary protocol on every arm.** Per B launch ≈ C0's 202 s. 9 launches is 1,818 s. Add 1,500 s for the serving gate (the row estimate; 4.3 min was observed on 10-24). The total is 3,318 s, about 55 min.
        - With the 1.5x margin that is 4,977 s, so **min-window 1h25m**. The existing `v11-086-cpu` min-window of 6,300 s (1h45m) and its 3,000 s per-launch cap both cover it.
        - It can fit a free whole-host gap before inf66 takes the host at 19:30Z today.
      - **(b) B left hardened.** Per B launch ≈ 7 + 13 + 2194 + 2215 s, about 4,430 s.
        - 6 B launches, plus 3 C launches at 202 s, plus the gate, is 28,686 s, about 7.97 h. With the 1.5x margin that is about 12 h, and the per-launch cap must be ≥ 6,650 s.
        - It fits no whole-host bin before about 10-26 22:00Z: inf66 holds the host 19:30Z–03:20Z, then EB holds q2+q3 from 10-26 03:30Z for about 18.5 h.
        - It also yields rows that the protocol guard refuses.
      - **The SLOW-1 "8 h quiet" booking is withdrawn.** It is about 4.8x too large for (a) and too small for (b).
  - [x] **V11-086-SLOW-1D — quarter diagnostic: does B hang or run slow on `tg32@d32768`?** ✅ 2026-10-25 (workspace-58): verdict GRAY-2-5X (wall B/C 3.62, rate C/B 0.95). The ratio is all depth-fill COUNT (B's rows are unrequested-hardened, 4 fills vs 1); per fill B/C is 0.98. Evidence: research `data/v11-086/b-stall-diag-20261025/`. [belief: cc]
  - [x] **V11-086-SLOW-2 — make the 086v2 bench protocol ordinary on every arm before any rerun.** ✅ 2026-10-27 [belief: cc]
    - Fastest fix: rebuild `llama-bench` and `libllama-bench-impl.so` for both store builds with the V11-103 fix `141e4bcf5`. It touches only `tools/llama-bench`, so the pinned `libggml-cpu` sha256s and the kernel under test are unchanged.
    - Belt and braces: the driver refuses or relaunches any launch whose row says `autokernel_hardened: true` without `--autokernel-harden` (the LBH-3 rule).
    - Alternative: the fold path. Rebuild B as current champion + `8110933ba` + `e70926716` against the current champion as C. Both already carry V11-103.
    - Done when one `-p 0 -n 32 -d 32768 -r 1` launch per arm shows `autokernel_hardened: false` on both arms.
    - Closure evidence: refreshed C/B bench-only candidates include V11-103 `141e4bcf5` with the measured `libggml-cpu` hashes unchanged; the completed 086v2 rerun has 9/9 launches and 36/36 raw rows with boolean `autokernel_hardened: false`, including `tg32@d32768` on C, B-unset, and B-auto. The driver validates this raw protocol before parsing rows. Evidence: `/mnt/raid0/llm/tmp/codex-ni-v11-086-slow2-20261025/night-repin-prep/results/run/` (`COMPLETE`, `results.json`, `bench_*.json`, `DECISION.json`). This is protocol closure, not a production fold.
  - [x] **V11-086-RERUN — the sized whole-host 086v2 timing run (all 9 launches + serving gate).** After SLOW-2. Book 1h45m whole-host quiet (min-window 1h25m = 55 min expected × 1.5). Keep the 3,000 s per-launch cap and the predeclared `PREDECLARED_086v2.md` rule. Done when `086v2/20*/COMPLETE` exists and DECISION is read. ✅ 2026-10-27 [belief: cc]
    - *(2026-10-27, workspace-58 results harvest)* DECISION `fold_opt_in_default_off` (rule 086v2, predeclared sha 48897be2). tok/s higher=better, effect=median(Bauto)/median(C)-1, n=3 launches/arm: pp5 -0.34% (floor 5.86), tg32 -1.88% (2.38), pp5@32k +0.01% (2.03), tg32@32k +0.41% (8.34); all within floor, no gain; serving sign -0.61% (43.67->43.40, ok). Performance NULL. Artifact `/mnt/raid0/llm/tmp/codex-ni-v11-086-slow2-20261025/night-repin-prep/results/run/DECISION.json`.
    - [ ] **V11-086-FOLD — carry GGML_FA_VKQ_REG opt-in default-off in the next champion fold ledger (no default change; perf null on Q38FN).**
  - **2026-10-20 (ab-probe-restore) — the GPU `ab_probe.py` harness is RESTORED and committed.** The sentence above ("no longer on disk ... until main restores or replaces it") is superseded. It was a never-committed scratch file; no git history or branch held it. Recovered **byte-exact** from the Claude session transcripts by replaying its original `Write` (workspace-8d, 2026-09-29 04:01Z) and every later in-place patch (04:08Z, 07:14-07:22Z; one `Edit` that failed in the original session is skipped). The replay's sha256 is `bd195fa6fe3575d50ef4e23a68dd5aad9e61f5201497118cf20abb646489182b`, identical to the `probe_version` recorded in the 2026-10-04 KVU-19 receipts, and `ab_probe.py summarize` over the preserved 15-arm champion-only run reproduces its `result.json` verdict and arms exactly. Committed unmodified (its hash is the protocol identity) in epyc-inference-research `3c428ac00`: `scripts/benchmark/ab_probe.py`, `ab_arms.sh` (the 2026-10-04 fold copy with HERE = own dir and an overridable P arm), and `gpu_champion_ab.sh` (one entry point for any two store GPU builds; `--dry-run` default; `--execute` refuses without `AB_INSIDE_CLAIM=1`, i.e. outside `region-lock --gpu-quiet exclusive`). Protocol (unchanged from the receipts): `P C P C ...` x15 on :8197, the :8083 DFlash2 argv, `-t 8` on cores 72-79 membind 3, probe `mtp --identity-tokens 256 --probs-tokens 64 --pp-items 300 --pp-reps 2 --tg-n 256 --tg-reps 2`, floor = max(2.00%, P-vs-P spread). Wired: `measure/lib.sh` `gpu_ab()` (used by `m_V11-050` and `m_V11-052`) and `bundle_gate.sh` item `e` (champion `dd3d9721c` vs C, runs alone under `--gpu-quiet exclusive`); dry-runs pass sha256 and ggml linkage for both GPU builds. Nothing was run: no server, no GPU, no bench.
- **Port plan for the GLM Q4_K/kquant kernel keeps (first item of the next consolidation step, not dropped):** the 8 keeps (`96682e27b 96d22da77 c5baa22ba 5d1acd349 ef37bc548 35186deaf 6e4078401 502075809`) plus `d2861045f` are alternative kernels for `mul_mat_qX_K_q8_2_X4_T`. Plan: (1) build a Q4_K-only microbench harness on the shapes of the served Q4_K models (DS41 expert Q4_K, UD-Q4_K_M 27B), (2) port each on top of the champion's `ActivationMetadata` layout one at a time (they assume a `d8[]` array that the champion removed), (3) keep a port only if the kernel op-test passes and DS41 gate_compare beats the floor 4.533% or Q38FN sign >= 0 with greedy identity. The row-exact weighted slab keep (`f75e2a699`) is already re-ported in C.

**Fold ledger — 2026-10-20, slot-file draft state + checkpoints ("slotdraft")** (operator-authorized: fold if the #30574 port keeps MTP draft acceptance across slot restore; prepared by a subagent, CAS by the operator): 3 commits on `e33229348`: `1c999e15b` (port of upstream #26004, context checkpoints in the slot file), `deb387b8b` (port of #30574, MTP draft state in the slot file), `dd3d9721c` (test import fix). Files: tools/server/server-context.cpp + tests, common/common.{cpp,h} (checkpoint load returns bool instead of GGML_ABORT), examples/speculative-simple; no ggml/ or src/ change, so CPU kernels and GPU-resident paths are untouched.
- **Evidence** (`/mnt/raid0/llm/tmp/slotdraft-30574/REPORT.md`): Qwen3.6-35B-A3B-MTP-Q8_0, 7,680-token slot, np2, split and unified KV: restored/live acceptance 0.98–1.02, decode 0.99–1.02, restored output byte-identical; control (champion) 0.53–0.85 acceptance, 0.71–0.85 decode. Slot file +175 MB (149.6 → 324.9 MB).
- **Gates** (`/mnt/raid0/llm/tmp/champ-fold-slotdraft-20261020/`): server test_slot_save.py on the store build 15/15 (control 6/15); greedy identity on the frontdoor model, MTP on, 3 prompts × 256 tokens, candidate ≡ champion byte-identical with equal draft counters; test-backend-ops not run (no ggml change).
- **Builds:** `kernels/builds/cpu-20261020-dd3d9721c` and `gpu-20261020-dd3d9721c` (10345, HIP compile + linkage only, no GPU), champion recipes, CMakeCache equal to `*-20261006-4348de400` apart from the RPATH relocatability entries, SHA256SUMS + PROVENANCE.md + `verify_ggml_linkage.sh` PASS. GPU serving validation of the HIP image pending.
- **Moved:** guarded CAS `update-ref` `e33229348` → `dd3d9721c` (fast-forward), `ak-loop-tree` refreshed, pushed to fork (fork was at `b0ba1d427`, so the push also publishes the 10 intervening local champion commits).

**Fold ledger — 2026-10-04, candidate W** (stack owner's fixes, folded by ak-ds41-main), 7 clean cherry-picks (map
`/mnt/raid0/llm/tmp/fold-W-20261004/shamap.tsv`):
- **Prefill budget** (from `98c0ce12a`): `--prefill-budget-decoding` / `--prefill-budget-target-ms`, default OFF and
  byte-identical when off. KVU-16g (3 decoders at 20k + an 80k neighbour prefill): pb512 decode-under-prefill ×2.92 with
  solo prefill −4% vs `-b 512`'s ×3.22 / −14%. The :8083 switch lands with v11.
- **FA-INT64-OFFSET** (`6152cdf7a`, `4f21c3477`, `0c4801127`): WMMA int64 offsets past ~524k cells at ub 2048, plus int32
  product fixes in tile/MMA/vec and mask_ne0 test cases. Offsets identical wherever int32 didn't overflow.
- **FN-FIX** (`5bfdcd18c`, `6c126e975`, `45d8f2937`): the fused decode takes rope params from the context; the path is off
  in production (`GGML_FUSED_DECODE_OFF=1`).
- **Gates:** G0 0 losses (source, CPU, GPU). CPU test-backend-ops `GGML_IQK=1` all pass (FA 5182/5182, mask_ne0 4/4),
  `test-qwen4exp-fused-rope` 3/3. GPU: FA 2953/2953, mask_ne0 4/4, MUL_MAT 1139/1139; 27B greedy W ≡ champion
  byte-identical 3/3. CPU serving (`runs/20261004T195408Z`, :8083 serving): DS41 W vs C −0.89% (floor 4.533%, not
  decisive), Q38FN −0.04%, greedy identical 3/3.
- **Moved:** CAS `9a3f1392a` → `b0ba1d427` (fast-forward), `ak-loop-tree` refreshed, pushed to fork.

**Fold ledger — 2026-10-04, CPU FA fp16-VKQ overflow fix ("Yfa")** (stack owner's fix, folded by ak-ds41-main): `057270556` +
`a99e5330a` from `experimental/cpu-fa-fp32-vkq-20261004`, ported onto Y without the opt-in arms `2ad8bff36`/`5bde1b83d`
(one commit; conflict with KVU-19's −INF mask-run skip resolved keeping the skip). ggml-cpu `ops.cpp` `_one_chunk` only.
Evidence: bit-identical to the champion on the KVU-19 FA harness (86 + 141 cases, aggregate hashes equal); stack owner's
harness: 74 non-overflow cases bit-identical, 10 NaN cases finite. CPU gates (`runs/20261004T150904Z`, `--gpu-quiet
shared`): DS41 Yfa vs Y −1.18% (floor 4.533%, not decisive); Q38FN −0.04%; greedy identical 3/3. CPU test-backend-ops green;
GPU image linkage PASS (GPU FA path untouched, no GPU slot by agreement). CAS `61bdb185c` → `9a3f1392a` (fast-forward),
`ak-loop-tree` refreshed, pushed to fork.

**Fold ledger — 2026-10-04, all-keeps fold (candidate "Y")** (prepared and CAS'd by ak-ds41-main; operator chose scope):
- **Folded onto `1bceceb05`:** the DS41 port (4 commits) + `ebb68dc55` profiling (compiled out unless `GGML_CPU_PROF`), the
  serving-gated DS41 keeps (the a1faab471 bundle +7.113% and the COR `053c3bd82` bundle +11.18%), and `656c9a66b`
  (stack owner's private per-context arena for the HIP-graph MMVQ q8_1 cache; KVU-16h: VRAM growth +0.057 vs +5.83 GiB,
  decode +1.0% no-draft / +4.9% drafted). Old→new sha map: `/mnt/raid0/llm/tmp/fold-allkeeps-20261004/shamap.tsv`.
- **Held out:**
  - **iqk IQ4_NL/MXFP4 allowlist `8c4b282ae`**: Q38FN serving X vs Y −1.26% (no decode gain) and it changes Q38FN output
    (greedy diverges at token 17 on 1 of 3 prompts, Y ≡ champion on 3/3). Its +40.6% is a 256-row microbench (c5) only.
    Next: Q38FN prefill A/B + paired task-quality eval before any fold (operator 2026-10-04).
  - **14 held DS41 keeps** (post-COR, per-keep 5-pair evidence only): two bundle-level nulls — `dca32b0e3` DIVERGED
    (+0.10% vs 4.533% floor) and the 2026-10-04 Z bundle gate (Z = X + 14 keeps vs X: DS41 −2.51%, floor 4.533%; Q38FN
    −1.40%; greedy identical). Not folded. Rebased onto Y as `70e7133a1` (Z') in case of re-gating; the C112 shape gate
    (`9b148baab` limited to per-expert rows ≤ 8) travels with them.
  - `74ee5c502` (unledgered, `measurement_invalid`) excluded; 3 empty merges dropped.
- **CPU gates (5g, 2026-10-04, `--gpu-quiet shared`, `/mnt/raid0/llm/tmp/fold-allkeeps-20261004/runs/20261004T125648Z/`):**
  DS41 X vs COR −1.56% (floor 4.533%, not decisive: the gated keeps reproduce on the new base); Q38FN X vs champion
  `1bceceb05` +4.52% (no calibrated floor; sign only, from the DS41 keeps since Y has them too); Y greedy ≡ champion.
- **GPU gates:** X paired receipt vs v10 (14 pairs) tg −0.23% [−0.57, +0.23], pp −0.12%, identity equal; Y smoke: FA
  2949/2949, MUL_MAT 1139/1139, 27B greedy Y ≡ X byte-identical 3/3; P3 v2 on X matches the KVU-19 champion at L3.
  **Standing receipt (champion-only, Y vs stored v10 serving baseline, 14 launches, unpaired):** tg +0.35%; pp +18.2%
  is NOT credible as a gain (unpaired, beyond the 9.91% paired floor, X's paired run 3 h earlier gave −0.12%): read as
  host drift. Run `receipt-ab/champion-only-61bdb185c-20261004T144303Z/`.
- **CPU correctness:** G0 0 losses (source + CPU build); test-backend-ops `GGML_IQK=1` MUL_MAT 1139/1139, MUL_MAT_ID
  815/815, FA 5178/5178; shape_check 28/28; dsv41/repack/gather tests rc 0.
- **Moved:** guarded CAS `update-ref` `1bceceb05` → `61bdb185c` (fast-forward), `ak-loop-tree` refreshed (`read-tree -m -u`,
  clean), pushed to fork.
- **Next fold candidate ready:** `9a3f1392a` (Yfa) = Y + the CPU FA fp16-VKQ overflow fix (ported without the opt-in arms;
  bit-identical on the KVU-19 FA harness, 86 + 141 cases). Resolve the tip
live before quoting it.

**Fold ledger — 2026-10-04, KVU-19 fold** (executed by workspace-ec, ledgered by ak-ds41-main):
- **Folded:** `ac97e305a` (KVU-19a FA masked-block skip, GPU), `a0d0ae238` (its CPU half), `1bceceb05` (KVU-19b commit 1:
  `n_seq` hint routes rows-are-sequences batches to the vec kernel). Fast-forward of `90c12df42`, no conflicts, moved with a
  guarded CAS `update-ref`, so the champion shas are exactly the shas the store images were built from. `ak-loop-tree`
  refreshed with `read-tree -m -u` (clean). Pushed to fork.
- **Held out:** KVU-19b commit 2 `c7f5ac9ad` (WMMA sequence tiles): ~14% slower on aligned 4×8 verify and it breaks its own
  skip-on ≡ skip-off exactness (6/119 cases); its planner is confirmed absent from the folded binary. Rework is with
  workspace-ec.
- **Gates (fold slot VERDICT PASS):** G0 kernel-coverage fold-check PASS, 0 losses (no GPU coverage; the slot is the GPU
  gate). Exactness E1–E8 PASS (skip on ≡ off, bit-identical). CPU harness 86 + 141 cases bit-identical, CPU
  test-backend-ops 5178/5178; GPU test-backend-ops 2949/2949 + 81/81 ×3. 27B DFlash2 paired smoke: champion ≡ skip-off ≡
  skip-on, byte-identical (36% accept).
- **Perf:** 4×1 decode at 327k occupied cells 9.17 → 5.51 ms; single-row FA with 114k foreign cells 2335 → 284 µs. At
  serving scale (KVU-16b replay on the combined 19a+19b build, `artifacts/gpu-slot-ak-20261004/`), the skip made each
  prefill chunk 4.5× cheaper at 240–280k occupied cells.
- **Serving-level (P3 v2 A1, 2026-10-04 09:11Z, champion image `gpu-20261004-1bceceb05`, same binary, skip ON vs OFF):** at
  L3 ≈355k occupied cells with 3 parked neighbours, drafted 34.98 vs 15.74 tok/s (2.22×; loss vs L0 −0.19% vs −55.4%),
  no-draft 21.53 vs 8.45 (2.55×; −1.4% vs −60.3%); no-draft text sha identical ON = OFF; VRAM own peak 51.7 GiB. Meets
  KVU-19b's "L3 loss < 10%" for single-sequence decode with neighbours. `/mnt/raid0/llm/tmp/gpu-slot-ak-20261004/results/20261004T091103Z/`.
- **Standing receipt (PAIRED, n=14, operator decision (B): v10 measured once on the current protocol):** P = v10 `ffc1bac82`,
  C = champion `1bceceb05`, current :8083 DFlash2 argv, `ab_probe` serving (probe sha256 `bd195fa6…`). tg **+0.61%**
  [95% CI −0.20, +1.41] (P 40.13 / C 40.37 tok/s); pp −0.21% (floor 9.91%); output identity all-equal C = P; SW-9: C carries
  all probs, P has the gap. Raw run dir `/mnt/raid0/llm/tmp/champion-fold-kvu19-20261004/receipt-ab/paired-20261004T094057Z/` was DELETED ~11:37Z by a dry-run cleanup (per-launch JSONs and server logs lost; the loop-memory `source.path` now dangles); the full run log, RESULT line and copies of the four loop-memory records are preserved in `artifacts/champion-fold-kvu19-20261004/paired-receipt-20261004T094057Z/` (README);
  ingested via research `production.py ingest-serving` into `loop-memory/production-baseline.ffc1bac82eec.serving_probe-{pp,tg}.json`
  (the v10 serving baseline future champions run single-arm against) and `champion-vs-production.serving_probe.json`.
  Short-context single-stream is neutral, as expected: the fold's gains are at high occupancy (P3 v2 above, KVU-16b replay).
- **Loop anchors:** DS41 and Q38FN anchors still have `90c12df42` as an ancestor but are not the champion; both reseed on
  `1bceceb05` at relaunch (INF-77 DS41-C121).
- **Production:** carried by v11 via kernel-promotion (full candidate validated as a whole; no interim v10.x). Before any sweep folds "an unfolded
CPU branch", read the **DO-NOT-FOLD ledger** below.

DS41's champion of record on its own campaign lineage is `a1faab471e83`, with 4 serving-gated keeps (DS41-C68,
+7.113%). Folding them into the global champion is DS41-C47/C68, owned by workspace-76:
[`deepseek-v41-flash-evaluation.md`](deepseek-v41-flash-evaluation.md).

| task | what to do |
|---|---|
| **V6R-4a / V6R-4c** | Ride the v11 candidate gate (the fast loader; V6R-4c PARKED by the operator 2026-09-27) |
| **V6R-4b** | Operator: OP-58, ratify the forward-port rule |
| **HEAD-3** | The 35B np=24/32 ceiling; needs an operator go for ~12 min of exclusive GPU |
| **CH-8** | AutoKernel's GPU builder omits `GGML_HIP_ROCWMMA_FATTN` |
| **CH-14 / CH-16** | Manual-research loop runbook (start from `scripts/benchmark/serving_evidence_refresh_runbook.md`, research repo); correct the loop champion's inflated per-commit claims |
| **FOLD-0 / V6R-1..3** | INF-70's residual fold items; v6-fork triage (DiffT-V2, KV context-shift, paged-attn) |
| **not on this page** | `AK-INST-3`, `AK-INST-2`, `AK-DEPLOY-2` live in [`autokernel-restart-and-strip.md`](autokernel-restart-and-strip.md). |

Closed work and superseded champion-state narration: § *Completed Scope*.

## Completed Scope

| Scope | Where |
|---|---|
| CH-1 … CH-7, CH-9 … CH-13, the CH-1 implementation notes, CHAMP-2, CHAMP-3 | [completed ledger](../completed/autokernel-champion-aggregate-completed-through-2026-09-29.md) |
| Champion-state narration: RECONCILED 2026-08-31 (`a2728701`, +12.618% tg128), STANDING 2026-09-03 (`732389d6`), CONSOLIDATION 2026-09-08 (`ef81196d5`) | [archived history](../archived/autokernel-champion-aggregate-history-through-2026-09-29.md) |

## The finding that reframes this

**`champion.py` already implements composition, not best-of.** `compatible_groups` is documented as
*"Deterministic **maximal compatible sets**; no ranking and no gain inspection"*, and the module
contract is *"member results are never combined into a new result… Member performance fields are not
read anywhere in this module."* The composed tree is rebuilt and re-measured **as a whole** and must
earn its own T0/T1/T2 against the anchor; it even names a branch, `ak/champion/<tree>-<anchor12>`.

So the design is right and matches the requirement. Three things are wrong with the reality:

1. **It has never run.** `champion.py` is reachable only from `release/closeout.py` and
   `release/live_material.py`, never from the discovery controller. Dashboard funnel:
   `{candidate: 38, champion: 0, promotable: 0, strict_keep: 1}`.
2. **Nothing makes it always-exist.** Composition is an end-of-campaign release action, not a
   standing invariant.
3. **Discovery screens against the frozen anchor, not the champion**, so gains cannot compound.

## What may and may not go in — measured, not assumed

Audited 2026-08-27. Only **two** unpromoted items are real llama.cpp source diffs, and both fork off
v9 (`0db32c06e`) exactly:

| Arm | Branch | Size | ggml? | Status |
|---|---|---|---|---|
| MoE-Spec (`moe_spec_budget`) | `inf40-moespec-v9` @ `c7c37a0d9` | 8 files, ~81 LOC | none | flag-gated **default 0**; strongest genuine arm |
| DFlash2 block drafter | `ak/dflash2-qwen38-20260820` @ `2046c64e9` | 20 files | none | **ADMIT (operator, 2026-08-27)**: a PARALLEL spec-decode capability, not an MTP replacement — see the ruling below |

**Verified independently: their file sets overlap in exactly one file — `src/llama-context.cpp` —
and neither touches `ggml/`.** Composition is mechanically near-trivial.

Everything else on the intuitive list is a different class and must NOT be composed as a diff:

- **Already in v9**: `GGML_IQK` (since v8), MMQ `a6b4b5263`, HIP graphs (upstream default ON).
- **Build/runtime configuration**, not source: `GGML_HIP_MMQ_MFMA` (+26.6% prefill), `ubatch`
  512→1024 (+46.9%), `-fa` (+4.9%), `GGML_IQK`. These belong in the candidate's **build recipe**,
  which `champion.py` does not currently model — a real gap.
- **Retracted**: ngram 2.8× (warm-context self-copy artifact; corrected to −0.0%/+0.2%/+1.7% CPU and
  **−17.4%** on 122B-IQ2 GPU).
- **Unexploited source residue**: iqk `IQ1_S`/`IQ1_M` are vendored (`iqk_gemm_1bit.cpp`) but omitted
  from CMake, audited clean 2026-07-29, never staged; `iqk_flash_attn.cpp` present, not built.

**Do not seed the champion from the dashboard's 44 rows.** 43 are screening-only `promotion_claim:
false` observations with `"SEARCH RECORD, NOT A CLAIM"` receipts, and the single `strict_keep`
(+28.86% `GGML_IQK` prefill) is a positive-control canary re-measuring a feature already frozen into
production. Banking those would launder observations into a champion — the exact failure the
apparatus exists to prevent — and would destroy the comparability of every later result.

## Tasks

- CH-1 … CH-7 are done (2026-08-28/30); CH-6 settled that neither config leader belongs in the champion. § *Completed Scope*.
- [x] **CH-8 (new, 2026-08-27) — AutoKernel's GPU builder omits the house flash-attention flag.** ✅ 2026-10-29 (audit: box text "RULED 2026-08-28, and done": research 71db62e9e Merge lane/ch8-build-flags-20260828 (GGML_HIP_ROCWMMA_FATTN ON, GGML_NATIVE ON)) [no-belief: audit-reconciliation]
  `discovery_deployment_factory.py:2052` passes only `GGML_HIP=ON`, `AMDGPU_TARGETS=gfx90a`,
  `GGML_NATIVE=OFF`, so every AutoKernel GPU candidate is built with `GGML_HIP_ROCWMMA_FATTN`
  **OFF** while production, the AK-BH factorial builds and the standalone DF2 build are all ON.
  Consequences: candidates are measured on a different flash-attention kernel than production runs,
  which undercuts transferability of any GPU result; and the OFF path is the one measured below to
  produce non-finite values at longer sequences under `-fa on`.
  **RULED 2026-08-28, and done.** Operator: *"if it leads to better performance finds, I don't care
  if it breaks comparability with prior GPU screens. We only added the GPU recently anyways."*
  Prior GPU screens are therefore **superseded, not reconciled** — they were taken on a kernel
  configuration production does not run. Two flags changed in
  `discovery_deployment_factory.py` (research `71db62e9`):

  | flag | was | now |
  |---|---|---|
  | `GGML_HIP_ROCWMMA_FATTN` | unset → CMake default **OFF** | **ON** |
  | `GGML_NATIVE` | explicitly **OFF** | **ON** |

  `GGML_NATIVE` was ruled the same way and for the same reason: every reference build on this host
  is ON, and matching production is what makes a find transferable. It is the portability trade
  taken deliberately — OFF is what a portable build wants, and this is a single-host program.
  Verified by mutation test that both survive `_sealed_cmake_defines()` rather than being dropped
  as unknown keys (only the RPATH keys are force-overridden there), and confirmed present in the
  live v33 execution closure.

  The repo README gained a *"Build configuration — read this before forking or reproducing"*
  section at the operator's request, recording which flags are host-specific and why, so a fork
  knows these numbers hold for this hardware and these flags and that reproducing them elsewhere
  means re-measuring rather than re-reading.

  Scope discipline, unchanged: the non-finite behaviour was observed in the DFlash
  **target-feature** path; whether plain non-speculative decode also degrades at length on an OFF
  build is **not measured** and is not asserted.
- CH-9 is done (2026-08-28): § *Completed Scope*.
- [ ] **CH-17 (new, 2026-10-03) — every kernel freeze re-selects each role's spec-decode recipe.** A v-next
  promotion checklist item (kernel-promotion skill and its `promotion_gates.yaml`, and the v11 candidate gate
  with V6R-4a). Origin: the 2026-08-27 ruling 3 said "adjust the lean registry compiler at promotion time"; the
  v10 freeze (`ffc1bac82`) was even qualified on DFlash2 vs MTP (np4 ratio 1.239), yet the promotion only re-ran
  `stack_change_pipeline.py update`, and :8083 kept `draft-mtp` until 2026-10-03 (drafter-compile DESIGN §4 item
  8, `/mnt/raid0/llm/tmp/drafter-compile-20261001/DESIGN.md`). Acceptance: for each served model, list the
  drafters the new kernel supports (`llama-server --help` spec types; master `drafters`), compare the
  qualification evidence per drafter, and either change `stack_topology.yaml` `drafter_selection` or record
  "selection unchanged, because …" in the promotion receipt. The step blocks the freeze until done. Now that
  DRAFT-SEL-1 makes the selection a compile input, this is a data edit, not a compiler change.
- [ ] **CH-18 — v11 pull-fresh upstream list (kernel workflow step 1; never a cherry-pick onto v10; champion folds only through the fold-ledger route).** Record in this handoff the upstream fixes that enter llama.cpp-experimental through the next fresh-production pull, in order: #30514 (plain KV honours PARTIAL_ONLY), #26004 (checkpoints in the slot file), #30574 (draft state in the slot file; ported ahead of the pull on `experimental/slotdraft-30574-20261020` per the operator on 2026-10-20 and folded into the champion if KVU-12.2's gate passes, so the pull reconciles with that fold rather than re-applying it), #30580 (SWA reuse-threshold off-by-two; v10 still carries it at server-context.cpp:3398). **Added 2026-10-20 (kernel-manifests sweep):** #27870 (MMA divergent-barrier race, `fattn-mma-f16.cuh`; the DF2 ROCWMMA-OFF pin in `dflash2-block-drafter-experimental-build.md` waits for it as V11-FA-6; 27B probe fails 6/10 with OFF, passes with OFF + #27870 alone) and #28576 (fp32 VKQ accumulation on MFMA: perf-only on MMA-routed MFMA shapes, not an overflow fix; its occupancy 4 to 3 retune is the CDNA D=64/ncols=64 config only; decided 2026-10-22 as carried by the pull, V11-FA-7). Both are picked on `experimental/v11-fa-ab-20261004` (`e9b3b04df`, `5026470c6`); the pull step must carry or consciously drop them. The V11-FA-1..6 and `KVU-19b-rework-c2-cal` task texts are referenced by `routing-and-optimization-index.md` (RTG-57) but are missing from `kv-unified-stack-rollout.md`; restore them there. Watch list, not pulled while open or unmerged: #30141 (MTP get/set_state), #29480 (iSWA seq_pos_max assertion), the upstream follow-up for the SWA pos_min TODO (not located; search before the candidate). Promotion-checklist notes: #26640 changes the slot-file format for all slots, so a file written by a build carrying it is not restorable on a v10 rollback (decide at promotion whether to carry it). The candidate's full-build validation includes KPF-19.1's rebase check on the pulled tree, KVU-12.2's gate (b) re-run, a Gemma-class restore that reprocesses the same token count as a never-saved slot, checkpoint size measured on our Qwen3.6 MTP slots, and a check whether the launch recipes pass --spec-draft-p-min and --spec-draft-n-max explicitly (the study's frontdoor argv omits p-min and so rides the upstream default that #23269 changed). Done when the list is the pull step's input and every check has a recorded result.
  - *(2026-10-20.)* #26004 and #30574 are already in the champion (`dd3d9721c`, slotdraft fold); the pull reconciles with that fold rather than re-applying them.
  - *(2026-10-20, workspace-f8.)* upstream list recorded: #30514 MERGED e467e5b5e (not in champion), #26004 MERGED 033df86b6 (champion port 1c999e15b), #30574 MERGED ea736c1d5 (champion port deb387b8b), #30580 MERGED 61ad80bf9 (not in champion; SWA threshold still at server-context.cpp:3759 @ dd3d9721c), #30141 and #29480 OPEN. Launch recipe: frontdoor (draft_max 4) and :8083 (draft_max 7) pass --spec-draft-n-max but no p-min; registry has no draft_p_min; launcher would emit --draft-p-min at orchestrator_stack.py:483. Full-build checks (KPF-19.1, KVU-12.2 gate b, Gemma restore, checkpoint size) still pending; evidence /mnt/raid0/llm/tmp/zero-inference-20261020/CH-18/REPORT.md.
  - *(2026-10-21, noninf-ak; docs only, no llama.cpp tree touched.)* Cross-check against `llama-v11-manifest.md`: every PR on this list has a manifest row except #23269, now V11-096 (status IN: `d14ce3dab` is an ancestor of v10 base `ffc1bac82`, champion `dd3d9721c` and candidate C `f0c96dc1f`; it is a launch-recipe check, not a pull item). #30141, #29480 and #26640 stay watch-list notes. The V11-FA-1..6 and `KVU-19b-rework-c2-cal` task texts are restored in `kv-unified-stack-rollout.md` (commit `d58966bbb`, byte-exact from `465954bc0^`); they were lost ACCIDENTALLY in `465954bc0` (2026-10-07, "HYBRID-PREFIX-REUSE task"), a stale-base overwrite that deleted 892 of that file's lines while adding 12. The same loss removed other tasks (e.g. KVU-15a, KVU-7, KVU-18, KVU-19b parent) that are NOT restored here; see the report to main. Still owed before ticking: the full-build checks above.
  - [ ] **CH-18.a — upstream note: hung-up non-streaming requests are not cancelled under load.** `server_response::recv_with_timeout` (tools/server/server-queue.cpp:289) restarts its full 1 s wait on any task's notify, so a disconnected client's request keeps computing and holding KV while other tasks produce results (0/5 cancelled with /slots polling). Check upstream for a fix in the v11 pull; otherwise propose a deadline-based wait. (found 2026-10-20 by the KPF-17 fix pass)
  - [ ] **CH-18.b — upstream note: SWA `pre_decode` re-decodes from a checkpoint whenever pos_next ≤ n_swa.** `pos_min_thold = max(0, pos_next - n_swa - …)` is 0 there, so `pos_min >= pos_min_thold` always holds. The slot restores its newest checkpoint and re-decodes the tail even when the live SWA cache fully covers the window (wasted prefill on short-context SWA reuse; the truncation also bumps the P2 content epoch). Seen on gemma-3-1b in KPF-17 job 26 (2026-10-21). Check the v11 pull for an upstream change (related: TAG_CHECKPOINTS_FIX_POS_MIN, #30580's SWA threshold); otherwise propose gating on a real window shortfall.
  - [x] **CH-18.c — run the operator-approved follow-up kernel intake** (approved 2026-10-22 in the Locals+agent-beacon intake, not yet run; `.research-session.json` operator steering seq 10): ik_llama.cpp FlashMLA PRs 277 and 243, the ik q8_0 repack commits plus ik issue 1205, and ggml PR 28576 (= V11-050 / V11-FA-7, so check it against that row first). Full research-intake flow; bind any keep to this v11 list or the fold-ledger route. (filed 2026-10-22, f8) Ran 2026-10-22 as `intake-kernel-followup-20261022` (intake-2494..2510); #28576 decided as carried by the pull (V11-FA-7); outcomes filed under AKX-ALL-LB4.6 to LB4.9, AKX-ALL-10.1, AKX-ALL-LB3.1, V11-FA-8 and DS41-C123.1a. ✅ 2026-10-22
  - [ ] **CH-18.d — v11 pull-list additions from the speech intake (2026-10-22; verified absent from champion `dd3d9721c` and v10 `ffc1bac82` by git ancestry).** (1) #28957 (`6a2743f02`, bitonic argsort for rows wider than one block): after the pull, on the candidate's gfx90a HIP build, run test-backend-ops `-o ARGSORT` including the 1025/2047/2048-column cases and `-o TOP_K`, residency proven; v10 is unaffected in production because supports_op keeps argsort rows at or below 1024 on non-CUB builds and wider rows fall back to the CPU. (2) #29231 carries the same OCP fp8 guard as our `0ebf1b4d7` (present in v10 and the champion): drop `0ebf1b4d7` at the pull instead of resolving a conflict, and confirm by a ROCm 6.2 HIP compile plus a grep for `HIP_VERSION >= 60300000` in `vendors/hip.h`. (3) #30629 (`2851b3bcb`, mtmd audio stream with voxtral-realtime): confirm it is in the pulled tree and whether the CLI/server follow-up has landed, then run the ggml-org Voxtral-Mini-4B-Realtime-2602 Q8_0 GGUF through mtmd on one fixed clip against HF transformers output; if the server path is missing, transcribe.cpp (conversation-stack CS-8.STT2) stays the Voxtral runtime. Correctness work inside the v11 candidate validation; v10 stays untouched; records through VB-SPEECH-KOPT-1. (intake-2362#record, intake-2383#record)

- [x] **CH-22 - duty on the C2 CAS: ping f8 (`uds:/tmp/cc-socks/721113.sock`), 5c (`uds:/tmp/cc-socks/3944010.sock`) and workspace-7b with the CAS sha.** f8 ticks CT-12.5; 7b's AK Q38FN timing ABA must measure against the CURRENT champion. Owner: coordinator 3c4ca599 (or its successor). C2 = `experimental/c-plus-nemotron-bolt-20261021` @ `49550eda5`. Recorded 2026-10-21 by wrap-up 3c4ca599. ✅ 2026-10-23 (pings sent to workspace-7b and workspace-58 ~07:25Z; f8 relayed via workspace-58; 7b acked ~07:35Z).
- [x] **CH-23 - fold V11-100 (YaRN K-shift pure-rotation fix, `experimental/yarn-kshift-fix-20261021` @ `b67a5b9bc`, llama fork) into the consolidation AFTER C2 is CAS'd.** One feature per forward-port commit; its test travels with it (OP-58 rule). Cross-ref KPF-62.1. Recorded 2026-10-21.
  - *(2026-10-23, fold-prep subagent; box stays open until the CAS.)* Forward-ported as ONE commit (test + fix squashed) `dcc853b55` on champion 141e4bcf5 = `experimental/champion-c3-20261023` (pushed to fork); one trivial `tests/CMakeLists.txt` conflict. Gate state: `test-yarn-kshift` fails on the champion and passes with the fix; the YaRN native gate is FINAL NOT-FAIL (`/mnt/raid0/llm/tmp/yarn-native-gate-out/decision.json`, underpowered, v10 GPU build, does not exercise K-shift). Build, gates and CAS are CH-29.
  - *(2026-10-24, 3c4ca599.)* Done by CH-29: V11-100 is in champion dcc853b55 (C3 CAS 2026-10-24T07:50:06Z); see the CH-29 fold ledger.
  - *(2026-10-21 result, harvested 2026-10-27 by workspace-58.)* correctness-only. `test-yarn-kshift` on champion `dd3d9721c` FAILS: YaRN x4 round-trip K NMSE 8.79e-2, shifted-vs-fresh 1.92e-2, non-YaRN `attn_factor` 1.1 round trip 4.41e-2 (m=1 models 3e-15). With fix `b67a5b9bc`: all <=2e-9, non-YaRN digests bit-identical, CPU ROPE 448/448; HIP ROPE not run. Gate (test passes with the fix): met. No performance claim. Evidence `/mnt/raid0/llm/tmp/yarn-kshift-fix-20261021/prefix_run.log`. [belief: cc]
- [ ] **CH-24 - v11 promotion: gate or strip the unconditional qwen4exp fused-path debug output.** The v10 production libllama carries unconditional fused-path debug prints and per-token writes to `/tmp/qwen4exp-builds/*.bin` from the INF-64 bring-up commits `78922ed81` and `a56a79cc0`; they are inert only because Q38FN serving sets `GGML_FUSED_DECODE_OFF=1` (found 2026-10-22 by the NEW-10 smoke-abort RCA). `14c57cbe9` (`experimental/new10-ple-type-fix-20261022`, FD-DIV-1a in `cpu-fused-decoder-blocks.md`) already gates them on `GGML_FUSED_DECODE_TRACE`; fold it through the champion route with a v11 manifest row, or strip the output in the v11 candidate. Done when `strings` on the v11 candidate's libllama shows no ungated `/tmp/qwen4exp-builds` path and a fused-ON decode writes nothing under `/tmp`. (filed 2026-10-22, workspace-58 wrap-up)
  - *(2026-10-24, 3c4ca599.)* PREMISE CORRECTION: production `architect_general` (:8074, Flash-Next) does NOT set `GGML_FUSED_DECODE_OFF`: `stack_env.py` has an empty `architect_general` block, `build_launch_env()` strips ambient GGML_*, `/etc/environment` sets none, and the only `GGML_FUSED_DECODE_OFF: '1'` is in the registry's descriptive `optimal_cpu_serving` block that no code reads. So the v10 fused path (and its `/tmp/qwen4exp-builds` writes) runs whenever :8074 serves; 52 such files are newer than the v10 freeze (attribution to :8074 unproven; its last log is 10-11). The research recipes and AK q38fn campaigns do set OFF=1. Tracked as FD-OFF-PROD in `cpu-fused-decoder-blocks.md`.
  - *(2026-10-24, C5 fold-prep subagent of 3c4ca599.)* Resolution path: folded through the champion route as C5 commit `c72ec82f5` (ws58 patch 0001 = `14c57cbe9`, clean `git am` on C4 + the default-OFF commit `4976a189f`), manifest V11-107. Source half already shown: `ch24_src_audit.py` on the C5 tree is AUDIT PASS (55 `/tmp/qwen4exp-builds` sites, all behind TRACE / DUMP_* / LAYER_CMP); the v10 tree fails it with exactly `f_res_hc.bin` and `f_embd_tok.bin` (`/mnt/raid0/llm/tmp/c5-fold-prep/controls/audit_v10src.txt`). (The champion line already had those two gated before C5; 0001 adds the stderr print gating, the layout refusal, the ple_conv1d widen and the NaN top-k abort.) Done-when evidence comes from CH-31: `gate_c5.sh` (d1) (`strings` on the C5 libllama: every literal is a gated one) and item s of `c5-cpu-correctness` (a fused-ON decode writes 0 files under `/tmp/qwen4exp-builds`). Tick when both PASS; the v11 candidate inherits it at the next promotion.
  - *(2026-10-25, workspace-58 wrap-up; NOT ticked: the operator ticks CH-24 at the production promotion.)* Both done-when conditions already PASS on C5, now the champion (CAS 08:24:10Z): `/mnt/raid0/llm/tmp/c5-fold-prep/GATE_cpu.txt` (d1) source audit 55/55 sites gated and `strings` on `libllama.so.0.0.10419` 55 literals, 0 ungated; `GATE_cs.done` item (s) fused-ON smoke `tmp_new_files=0`. The v11 candidate inherits C5.
- [x] ~~**CH-20 - candidate C (`experimental/champion-consolidation-20261020` @ `f0c96dc1f`) owed-before-CAS gates, then the guarded CAS.** The GPU gates already ran (2026-10-20 22:36-23:15Z: ROCm0 FLASH_ATTN_EXT 2978/2978, MUL_MAT 1145/1145, MUL_MAT_ID 815/815, 27B DFlash2 greedy identity 3/3; see the candidate C ledger above), and the `test-rowexact-backend-toggle` `mmid` bisect closed 'NOT introduced by the fold'. What is still owed, each with its own recorded result before the CAS: (1) bundle gate `/mnt/raid0/llm/tmp/champ-consolidation-20261020/bundle_gate.sh` (items a-d, including the ten unledgered post-Y keeps, `dd3d9721c` vs `b0ba1d427`) in a CPU window; (2) the KVU-19a 64-case harness (KPF-17a); (3) the #27870 ROCWMMA-OFF route probe on an OFF build (see V11-FA-6 in `kv-unified-stack-rollout.md`); (4) the DCA 400K/500K needle A/B (YARN-DCA-E1) and the YaRN native-window gate (`yarn-context-extension-research.md`); (5) EXL3 model-level windows (`exl3-cpu-mi210-implementation.md`); (6) the NEEDS-MEASUREMENT scripts under `/mnt/raid0/llm/tmp/champ-consolidation-20261020/measure/` run with `--execute` (V11-050/051/052/086/064, V6R-1..3, V11-066/067); (7) the GLM Q4_K/kquant port plan: Q4_K microbench on the served shapes, port each of the 8 keeps onto the champion `ActivationMetadata` layout one at a time, keep a port only if the op-test passes and DS41 gate_compare beats 4.533% or Q38FN sign >= 0 with greedy identity; (8) `test-rowexact-backend-toggle` mode `mmid` rc=3 is pre-existing in the port (the original GLM harness environment was not found): locate that environment or retire the mode; (9) point the GPU gates at the restored `ab_probe.py` (research `3c428ac00`, sha256 `bd195fa6...`). Then the guarded CAS; if a layer fails, drop it by commit order (A, B, C, D, E). Done when every gate has a recorded result and the CAS has run. Champion ref has not moved. (filed 2026-10-20)~~ (closed 2026-10-29 audit: SUPERSEDED → candidate C f0c96dc1f superseded: 49550eda5 then C5 c72ec82f5 (CAS 2026-10-25T08:24Z) became champion (header "Current champion C5"))
  - **2026-10-21 CH-20 (1) side result, GPU serving A/B (bundle item `e`) PASS (candidate C stays owed the CPU bundle a-d, so CH-20 is NOT ticked).** `bundle_gate.sh --items e --execute`, run `champ-consolidation-20261020/runs/20261021T085251Z/e/`, evidence `artifacts/champion-consolidation-20261020/item-e-gpu-ab/` (`result.json` schema `epyc.gpu_champion_ab.result.v1`, `ab_arms.log`, linkages, `bundle_gate.log`). Champion `dd3d9721c` (P, build 10345) versus C `f0c96dc1f` (C, build 10404), 27B Q8 DFlash2 argv of the 2026-10-04 receipt, 15 P/C pairs alternating on one spare port with the restored `ab_probe.py`, `-t 8` on 72-79 membind 3. All checks true: identity C == P and P self-deterministic (same two digests on every one of the 30 arms), SW-9 champion probs on every token, linkage PASS on both builds with own libggml-hip mapped, GPU-resident on all arms, affinity OK. Speed: pp median C/P **-0.99%** (noise floor 2.00%, P spread 1.74%), tg median C/P **+0.27%** (floor 2.75%); neither is a regression (both within noise). Claim note: it was launched with the script's `--cpu-list 0-95` claim, which held all four quarters for ~26 min; a launch mistake that does not affect the result (the later launchers claim `gpu-quiet` only).

### Research intake 2026-10-22 — Locals + Beacon (intake-2386..2460)

- [x] **CH-LB1 — Guard the CPU gated-delta-net op against a BF16 recurrent state on the experimental line (reject in supports_op or abort when the state tensor is not F32; the env var that selects a BF16 state is read regardless of backend) and audit every CPU launcher env for that variable (intake-2386).** ✅ 2026-10-22
  - *(2026-10-22, f8 locals-d, code done, NOT built, box stays open.)* Fix on `experimental/locals-kernel-fixes-20261022` (worktree `/mnt/raid0/llm/worktrees/llama-locals-kernel-fixes-20261022`, cut from the champion `ak/champion/llama-cpp-ffc1bac82eec` = `dd3d9721c`; local, not pushed) commit `5f1eee195`: CPU `supports_op` returns false for `GATED_DELTA_NET` unless the state (`src[5]`) and dst are F32; `ggml_compute_forward_gated_delta_net` aborts with a named message if a non-F32 state still arrives; `llama-model.cpp` logs a warning when `GGML_CUDA_GDN_STATE_BF16` selects BF16. Tests: new `tests/test-gdn-state-guard.cpp` (ctest; supports_op contract for K=1/4, scalar and KDA gate) and two BF16-state `test-backend-ops` cases behind the opt-in set `TEST_BACKEND_OPS_EXTRA_CASES=gdn_bf16_state` (the default corpus and all case names are unchanged, so AK case counts do not move). **Build+test spec:** recipe native-openmp-gcc15-cpu-v1 (the cmake line of `/mnt/raid0/llm/tmp/f8-fillers-20261022/rng/job.sh`, own build dir in the worktree, build-role claim; peak ~12 GiB private, ~40 min cold at filler width), targets `test-gdn-state-guard test-backend-ops`; (1) `bin/test-gdn-state-guard`: four lines `F32 state supported=1`, `BF16 state supported=0`, then `OK`, rc 0 (< 1 s); (2) `bin/test-backend-ops -b CPU -o GATED_DELTA_NET`: every existing case OK, rc 0 (~1 min); (3) `TEST_BACKEND_OPS_EXTRA_CASES=gdn_bf16_state bin/test-backend-ops -b CPU -o GATED_DELTA_NET`: the two BF16 cases print `not supported [CPU]`, rest OK, rc 0; (4) `strings libggml-cpu.so` shows `CPU backend supports an F32 recurrent state only`. RAM < 1 GiB for the tests. **Launcher env audit (done):** `GGML_CUDA_GDN_STATE_BF16` appears in no orchestrator launcher (0 hits in epyc-orchestrator), not in `/etc/environment`, and in no readable live `llama-server` environment; in research it is set only by `scripts/benchmark/run_autokernel_historical_replay.py` (ROCm replay arms `expert_on`/`expert_off`, HIP binary) and listed in the `akx_width_invariance/width_probe.cpp` env allowlist. No CPU launcher sets it. Tick when (1)-(3) pass.
  - *(2026-10-22, workspace-f8.)* ✅ 2026-10-22 Build+test PASSED on `experimental/locals-kernel-fixes-20261022` @ `452887155` (12:33:58Z; `build-cpu-off`, linkage in-tree): `test-gdn-state-guard` OK rc 0; `test-backend-ops -b CPU -o GATED_DELTA_NET` 38/38; with `TEST_BACKEND_OPS_EXTRA_CASES=gdn_bf16_state` the two BF16 cases are `not supported [CPU]` (2/2), rest OK. `452887155` is the test-file include fix. Evidence `/mnt/raid0/llm/tmp/f8-fillers-20261022/locals-d/off/out/steps.txt`.
  - [ ] CH-LB1.1 — fold `5f1eee195` + `452887155` into the next champion through the fold ledger (FOLD.md + trial merge on the champion tip, ledger here); re-run (1)-(3) on the trial-merged build.
    - *(2026-10-23, workspace-f8 midday wrap-up: the champion tip moved.)* The champion advanced `dd3d9721c` -> `49550eda5` (~07:20Z). `5f1eee195` and `452887155` are NOT ancestors of `49550eda5` (checked with `git merge-base --is-ancestor`), and the iqk-port re-cut `experimental/locals-kernel-fixes-20261023` @ `540578f55` deliberately does not carry them (only the test helper from `5f1eee195` came over, as `51dfed7af`). They live on `experimental/locals-kernel-fixes-20261022` (pushed to `fork`, cut from `dd3d9721c`). So this fold's trial merge is onto `49550eda5` (or its successor), and (1)-(3) re-run on that build.
    - *(2026-10-24, workspace-f8 sweep.)* **Trial merge ready, not built.** `experimental/ch-lb1-fold-20261024` @ `d95ce6267` (pushed to `fork`; worktree `/mnt/raid0/llm/worktrees/llama-ch-lb1-fold-20261024`) = champion `dcc853b55` (C3) + `8e7463856` (cherry-pick -x of `5f1eee195`; test-only conflicts in `tests/CMakeLists.txt` and `tests/test-backend-ops.cpp`, both sides kept, the helper placed after `AK-SERVED-SHAPE-END` as in `51dfed7af`) + `d95ce6267` (`452887155`, clean). Diff vs `dcc853b55`: the 6 CH-LB1 files (+128/-5); libggml-cpu and libllama change. FOLD.md: [`docs/design/ch-lb1-gdn-state-guard-fold-20261024.md`](../../docs/design/ch-lb1-gdn-state-guard-fold-20261024.md) (scratch copy `/mnt/raid0/llm/tmp/f8-launchers-20261024/ch-lb1-1-fold/FOLD.md`). CAS gates it lists: (1)-(4) on the trial build, store images via CH-28d `build_store.sh`, `fold_gate.py --expected-changed libggml-cpu.so --expected-changed libllama.so` (cpu+gpu, libggml-hip IDENTICAL), version/linkage, Q38FN greedy identity vs C3; no timing gate. (1)-(4) launcher `/mnt/raid0/llm/tmp/f8-launchers-20261024/ch-lb1-1-fold/` (PREDECLARATION sha256 `192b7e20…`, DRY rc 0, FILLERS row BACKLOG; CPU build role, one quarter, >= 30 min). Overlap: zero files with C4 (`cdb4d8c77`, ggml-cuda only) and with UFH14-LB1.1's `0daa3ca8d` (`common/sampling.cpp` + server pytest), both `merge-tree` clean. Recommendation: follow the C4 CAS (re-cherry-pick onto the C4 tip, expected clean) and fold `0daa3ca8d` in the same fold; `452887155` is CH-LB1's own (an include fix in its test), not a UFH14 dependency. Hazard: the V11-102 iqk line's `51dfed7af` duplicates the test helper; whichever lands second drops it. Champion unchanged (dcc853b55), production unchanged (v10). WAITS-ON-EVENT: a CPU build grant for `ch-lb1-1-fold`, then coordinator 3c4ca599's guarded CAS after C4.
    - *(2026-10-24 14:14Z, workspace-f8.)* **BUILD+TEST PASSED on the trial-merged tree** (`experimental/ufh14-lb1-1-fold-20261024` @ `679257217` = `dcc853b55` + UFH14-LB1.1 + CH-LB1.1; `/mnt/raid0/llm/tmp/f8-launchers-20261024/ufh14-lb1-1-fold/`, `RUN_RECORD.json` all_pass=true, 8/8 steps OK, `BUILD_OK`+`PASSED`): both gate strings present, `test-gdn-state-guard` rc 0, `test-backend-ops` GATED_DELTA_NET 38/38, BF16-state not-supported rows +2, server pytest 3/0/0. This re-runs (1)-(3) on the trial-merged build; the box stays OPEN until the fold CAS, which waits on C4's CAS.

## The champion as built — 2026-08-27

`ak/champion/llama-cpp-0db32c06e3e5` @ `5c278648a4af2735587b4023613310ccf2341f46` — 35 files,
+3371/−146 over frozen v9, both merges clean, `llama-server` version 10139:

```
5bbcc5498  reviewed measurement instrument (correctness oracle, llama-bench, iqk sources)
 + c7c37a0d9  MoE-Spec  — per-batch top-B expert budget, --moe-spec-budget, default 0 (inert)
 + 2046c64e9  DFlash2   — block-diffusion drafter, a parallel --spec-type pathway
= 5c278648a  the champion
```

It exposes **both** `--moe-spec-budget` and `--spec-type draft-dflash` alongside `draft-mtp`, and it
loads the DFlash2 GGUF that frozen v9 refuses (`wrong number of tensors; expected 81, got 58`).

**The champion must be built ON the reviewed instrument.** A first attempt (`fdc56acb3`) was
synthesised onto raw v9 and was refused by `_instrument_review_receipt`. That refusal was correct:
it had dropped the measurement apparatus, so every screen would have run on a baseline missing its
own instruments. Exactly one pinned measurement blob changed in the rebuild — `llama-bench.cpp`
(MoE-Spec's 8-line env-var fallback for a flag that defaults to 0). `test-backend-ops.cpp`, the
correctness oracle that decides verdicts, is **unchanged**.

### The build flag that is not optional

`GGML_HIP_ROCWMMA_FATTN` **defaults to OFF** (`ggml/CMakeLists.txt:219`). On gfx90a with `-fa on`
the non-rocWMMA flash-attention path produces **non-finite values at longer sequence lengths**.
Measured on the champion built with it OFF: every one of the 12 pinned olympiadbench prompts failed
on task 0 —

```
E process: rejecting DFlash batch after 3020800/3020800 non-finite target features (limit=16)
E srv  decode: failed to process speculative batch
```

— while a 25-character prompt succeeded on the same binary. **Prompt length is the discriminator**,
which is why a short smoke test passes and hides it.

Attribution was verified rather than assumed. The first hypothesis — that merging MoE-Spec into
DFlash2 broke it — was **wrong**: the standalone DFlash2 build `2046c64e9` ran the identical prompts
and flags at 46.1 / 69.4 / 58.9 t/s with zero non-finite errors, and
`git diff 2046c64e9 5c278648a -- src/ common/` is **+67 insertions, 0 deletions**, so DFlash's
source is byte-identical between them. Rebuilt with the flag ON: all prompts pass, zero errors.
MoE-Spec is separately exonerated — it is guarded by `moe_spec_budget > 0` (`llama-graph.cpp:1985`)
and defaults to 0, so the champion carries the capability, not the behaviour.

Had the gates not been run before relaunching discovery, AutoKernel would have spent days screening
against a reference that fails on every real prompt.

## Why this is safe

Production is FROZEN (`production-consolidated-v9` @ `0db32c06`, branch pattern pinned in
`human_only_paths.yaml`, `on_pin_mismatch: refuse`); AutoKernel builds only in throwaway worktrees
off `llama.cpp-experimental`; every discovery receipt is `promotion_claim: false` by construction.
Per the 2026-08-27 ruling ([`ruling_op19_e8_chain_20260827.json`](../../artifacts/operator/ruling_op19_e8_chain_20260827.json)),
gates bind at the PROMOTION boundary, not at discovery.

## Operator rulings — 2026-08-27

These settle the open questions in this handoff. Recorded here because they change what the
champion is *for*.

1. **AutoKernel is NOT responsible for promoting kernels to production.** It runs with minimal
   friction. Every promotion gate is operator approval at promotion time, *outside* AutoKernel.
   The champion is a standing, ready-to-test aggregate — not a release process.

2. **CH-3 settled: SOLE-CHAMPION screening.** Dual-arm is unnecessary. If Champion₀ = production and
   every step is measured better than the previous champion, each champion is by construction better
   than production. The drift risk is real — v29 and v31 both produced S1 positives (+4.89%, +5.37%)
   that flipped negative on replication — and it is caught by the mandatory re-validation of the
   COMPOSED champion against the production anchor at composition time, which `champion.py` already
   requires. That re-validation is not optional.

3. **DFlash2 is a PARALLEL spec-decode pathway, and the kernel must SUPPORT it.** Correcting an
   earlier mischaracterisation in this file: "`--spec-type` takes one value" binds a single *server
   instance*, not the kernel. Roles run separate servers, so one kernel supporting both spec types
   serves MTP for most of the stack and DFlash2 for Qwen3.8-27B at the same time. DFlash2 therefore
   composes as ADDED CAPABILITY, not a mutually-exclusive swap, and the earlier "policy-barred /
   not additive" framing is withdrawn. Not every model has a DFlash2 drafter head; current intent is
   Qwen3.8-27B only, with the rest of the stack staying on MTP. The lean registry compiler is
   adjusted at promotion time to select per role.
   *(2026-10-03: the compiler adjustment was NOT made at the v10 promotion; it landed only with
   STACKCHG-DFLASH2-20261003 as DRAFT-SEL-1, orch `d3233170`. :8083 serves DFlash2 since then. The
   freeze-time re-selection that would have caught it is CH-17.)*

4. **Run the DFlash2 gates.** DF2-5 (np=8 concurrency) and DF2-6 (exact greedy parity) are approved
   to run. Note DF2-6 may fail for a reason unrelated to DFlash2: the in-production MMQ patch
   `a6b4b5263` is numerically valid but **not bit-exact**, so a parity failure must be attributed
   before it is charged to DFlash2.

5. **Manual research admits as a MEMBER, never as a claim.** `champion.py`'s contract already
   supports exactly this: "member results are never combined into a new result… a champion can cite
   only a *combined candidate's* passing T0/T1/T2 events against the current sealed production
   anchor." So an externally developed source arm enters as a member and the COMPOSED tree is
   rebuilt and re-measured; its original numbers are never inherited. The earlier caution in this
   file applies ONLY to the 43 config screening rows, which carry no source diff and therefore
   re-enter as build-recipe settings to be re-tested (CH-6), not as banked results.

## Open follow-on from 2026-08-28

- CH-10 … CH-13 are done (2026-08-28): § *Completed Scope*.
- [ ] **CH-14 (new, 2026-08-28) — document the manual-research loop as a runbook.** CH-7 + CH-13
      now compose into a complete loop (research → admit → gate → attest → visible standing), but
      it is only reconstructible by reading two handoffs and three scripts. Write it up in
      `docs/guides/` as the standing procedure, with the authority boundary stated explicitly so a
      future session does not "simplify" it by emitting a campaign receipt.

## 2026-08-30 — the champion finally has a measured effect against production on the DEFAULT path

CH-12 (retracted and corrected on 2026-08-28) established that the champion's measured effect vs
production existed *on the DFlash2 serving path production cannot reach at all*. What did **not**
exist was an effect on the default path beyond "no regression": CH-4's rows were 748.34 → 768.83
pp512 and 28.21 → 28.20 tg128, read honestly as no change.

**That gap is now closed, for the LOOP champion.** Note the two champions are different objects
and must not be conflated: CH-4/CH-12 measured the *manual-admission* champion `5c278648a`
(MoE-Spec + DFlash2); what follows measures the *loop* champion `5ad3e36d` on
`ak/loop-champion-20260828`, 36 commits above frozen v9.

| surface | production `0db32c06` | champion `5ad3e36d` | effect | floor | reading |
|---|---|---|---|---|---|
| **tg128** | 264.918 tok/s | 287.499 tok/s | **+8.524%** | 1.188% (calibrated) | **decisive by 7.2×** |
| **pp512** | — | — | +0.090% | 0.029% (uncalibrated) | **NO CHANGE** |

Both arms built fresh from named commits with the identical recipe · 20 alternating pairs · one
claim held across both surfaces · neither arm drifting · 40/40 resident · clocks pinned 1700 MHz on
all 80 invocations · correctness oracle rc=0, `2/2 backends passed`, on **both** arms. Stored as
`/mnt/raid0/llm/autokernel/loop-memory/champion-vs-production.json`
(`epyc.autokernel.champion_vs_production.v1`), five capability entries each carrying its evidence
path. The pp512 `decisive=True` is a floor artifact — and the changed files predict ~0 prefill
independently, since the 36 commits touch only the matrix-*vector* decode path and FA-vec and
nothing in `mmq.*`.

- [x] **CH-15 — the house recipe reproduces production's frozen build on BOTH backends.**
      ✅ 2026-08-30. Established by comparing *artifacts* rather than flags: production's shipped
      `libggml-cpu.so` vs our fresh v9 build, **584 defined symbols each, zero diff**; production's
      `libggml-hip.so` vs ours, **918 distinct device kernels each, zero symbols unique to either
      side**. This matters here because `champion.py`'s anchor identity and CH-1's build recipe both
      rest on our recipe standing in for production's, which was previously unevidenced.
      Follow-on, filed in INF-66 as **R18-A**: flip `build_recipe.py:43`'s
      `PRODUCTION_RECIPE_IS_VERIFIABLE = False` with this evidence attached.
- [ ] **CH-16 — the loop champion's per-commit claims are inflated 20× and must be corrected where
      a reader of the branch will land.** The 36 commit messages on `ak/loop-champion-20260828`
      claim gains **compounding to +171.7%** (arithmetic sum +101.8%) against a measured block
      effect of **+8.524%** — the same cumulative-attribution defect as run 17's (INF-66 D14) at
      twenty times the magnitude. **No individual percentage on that branch is a marginal effect.**
      Commit messages are immutable, so the correction goes at the tip
      (`NOTES-attribution.md`) and into `loop/program.md`'s *Settled — do not re-open* section.
      Owned by INF-66 as **R18-C**; listed here because this page is where someone comes to ask
      what the champion is worth. **Blocked on run 19 finishing** — `ak-loop-tree` is off limits
      while it runs.

- [x] **KM-1 - attach per-keep campaign evidence to the v11 manifest rows V11-026..042 and V11-053..055, or mark each row `commit-subject-only`.** `docs/reference/kernel-manifests/llama-v11-manifest.md` at-risk item 8: the AK keep records behind those commit subjects were not located as per-keep artifacts, so the commit subject is the only cited source (README rule 3 requires a gain to be copied from a cited artifact). Look in the campaign state under `/mnt/raid0/llm/autokernel/campaigns/` and the serving cell JSON; for any row with no artifact write `commit-subject-only` in its evidence cell. Low priority, near CH-16 because both concern keep-claim provenance. (filed 2026-10-20)
  - *(2026-10-24, batch-a.)* Located the per-keep AK records for all 20 rows. They are `status = 'kept'` rows in the campaign stores' `experiments.db` (table `experiments`, matched by `mechanism_id`), and every `effect_fraction` equals the manifest gain: V11-026..032 in `ak-ds41-cpu-decode-20260923/store`; V11-034/035/037/038 in `ak-ds41-cpu-decode-20260923/store-b0ba1d427`; V11-033/036/039..042 and V11-053..055 in `ak-q38fn-cpu-decode-20261003/store-b0ba1d427`. Each manifest row's evidence cell now cites db path, attempt_id prefix, status and effect_fraction; at-risk item 8 rewritten. No row is `commit-subject-only`. Caveat kept: a 5-pair screening number (CH-16), not a marginal effect. Done-when met (all 20 have the artifact). attempt_id is a 12-char prefix in the cell; V11-029's record is the second `q4k-x4t` keep (attempt 96273bec, 1.074%). The db rows were read read-only (sqlite mode=ro); no store was modified. Landed on main with the manifest edit.

## FOLD — INF-70 CPU kernel work into THE champion (operator request 2026-09-07)

Plan: [`docs/design/inf70-cpu-fold-into-champion-20260907.md`](../../docs/design/inf70-cpu-fold-into-champion-20260907.md).
Same lineage (fork `270b48ed6` on this branch), merge-tree **0 conflicts**; two default-ON blockers on
the CPU side must be fixed first; PROD-2 was operator-deferred 09-06 and today's request reverses it.

- [x] **FOLD-OP — operator decided 2026-09-07** ✅: (a) fold IS wanted — no reversal ceremony needed,
      folding at the right time is fine (NOTE: the CPU work is NOT yet in the champion; it sits on
      `inf70/champion @ 6f032c48d`, forked from this lineage but unmerged); (b) **timing: fold as soon as
      run 29 ends — the operator will stop it to reboot the machine; that reboot boundary is the fold
      trigger.** Do not stop run 29 for the fold; do not hand FOLD-0 to `inf70-audit` yet — this was a
      preliminary investigation for clarity on blockers. Surface FOLD-0 to `inf70-audit` when the
      run-29 / reboot boundary approaches, so the fold-ready commit is prepared in time.
- [ ] **FOLD-0 (`inf70-audit`, own branch)** — *note 2026-09-08: the re-base onto the CPU champion
      (`inf70/champion3` @ `9c4f73e29`) was done by INF-70 inside the fold candidate, so `ef81196d5` already
      carries champion3; the remaining FOLD-0 items below are theirs to close in their own turn*: fold-ready commit on `6f032c48d` — `GGML_OP_MOE_TOPK_NORM`
      opt-in (or CUDA kernel + test-backend-ops case), INF-64 fused decode opt-in, `ggml-alloc.c` stray
      define; re-run greedy bit-identity + `test-backend-ops -b CPU`; record the PROD-2 reversal in the
      INF-70 ledger; **push** `inf70/champion` (private clone today).
- [x] **FOLD-1 (champion owner)** ✅ 2026-09-08: loop stopped at the boundary (verified dead), pre-fold GPU tip
      tagged `ak/pre-fold-gpu-tip-20260908` (pushed), fold candidate `ef81196d5` built at
      `/mnt/raid0/llm/tmp/build-fold-ef81196d5`; `verify_ggml_linkage.sh` PASS.
- [x] **FOLD-2 gates, SAME merged tree** ✅ 2026-09-08 — all PASS with real tallies on `ef81196d5`:
      G1 `test-backend-ops -o SSM_SCAN -b ROCm0` 7/7 OK (incl. K=4/K=3 rollback), G2 MUL_MAT 1140/1140 OK
      (326 unsupported type combos), G3 GATED_DELTA_NET 39/39, G4 dispatch **observed** (`llama-bench -v` +
      `GGML_SCHED_DEBUG=2`: 27,516 nodes, SSM_SCAN=0, SSM_CONV 576 + GATED_DELTA_NET 576 on ROCm0, CPU holds only
      12 GET_ROWS), G5 tg128 vs gen-021 **+0.052%** (20 pairs, floor 0.638%, not decisive). Result file
      `/mnt/raid0/llm/tmp/fold-window-20260908/fold2-result.json`. NOTE: the first G1-G4 run reported PASS with
      **OK=0** (ANSI-coloured verdicts defeated the `\bOK\b` match; `llama-bench` swallowed scheduler logs
      without `-v`) — structural guards added: a gate PASSES only with ≥1 case run AND an agreeing `N/N tests
      passed` tally, and the graph check only with a plausible node count AND the expected recurrent ops present.
- [x] **FOLD-3** ✅ 2026-09-08 — **fast-forward + push, NOT a relaunch** (operator directive: no relaunch):
      `ak/champion/llama-cpp-0db32c06e3e5` `bff30cebe` → **`ef81196d5`** (`--ff-only`, tip == candidate) at
      11:16:49Z, lineage verified (`bff30cebe`, `445e93a8`, `9c4f73e29`, production `0db32c06e` all ancestors),
      worktree clean, pushed to fork `pestopoppa/llama.cpp`. Production branch untouched. Consolidated champion =
      GPU tip (6 unconfirmed keeps) + CPU champion3 `9c4f73e29`. PROD-1 still owes the CPU launch recipe before
      any promotion headline.

### CONSOLIDATION COMPLETE — `ef81196d5`, 2026-09-08

- [x] **FOLD-4 — consolidation is CLOSED; there are no CPU keeps pending** ✅ 2026-09-08. INF-70 reported
      its final RETEST-1 results at ~12:10Z with **no keeps to fold**. The consolidated champion is
      **`ef81196d5`** on `ak/champion/llama-cpp-0db32c06e3e5` = GPU tip `bff30cebe` + CPU champion3
      `9c4f73e29`, FOLD-2 G1–G5 all PASS. The operator's standing condition — *no kernel research until a
      FULLY consolidated champion* — is **satisfied**. Loop relaunch remains a **separate operator go**;
      nothing on this page launches or schedules it.

#### Inherited v6-fork candidates — from INF-32, archived 2026-09-14

`llamacpp-v6-consolidation.md` (INF-32) was archived 2026-09-14 as superseded by v9. Its three
unresolved `NEEDS-OPERATOR-REVIEW` rows are relocated here so they do not vanish with the page. They
are **un-triaged candidates, NOT queued folds** — nothing here is scheduled, and each is subject to the
operator's standing gate on new kernel research. Full context:
[`llamacpp-v6-consolidation.md`](../archived/llamacpp-v6-consolidation.md). The other two rows on that
page are closed: SWA slot-reuse (`d1c72d7fc`/`603702769`) and `--moe-n-expert` (`86901388a`) both
verified **DROP** 2026-08-12 — the SWA pair is a per-sequence-blind regression, and v9 already covers
expert masking with stock `--override-kv <arch>.expert_used_count=int:N`.

- [ ] **V6R-1 — Differential-Transformer-V2 arch (`36ceed44d` / `23973ea66`)**: eval-gated, not in the
      deployed registry. Triage question is whether any registry model wants the arch at all before any
      port cost is spent.
- [ ] **V6R-2 — streaming KV context-shift controls (`632ce0f92`)**: check first whether v9/upstream
      already ships equivalent context-shift controls (the `--moe-n-expert` outcome is the precedent —
      the stock flag had arrived).
- [ ] **V6R-3 — paged-attn upstream-overlap**: the v6 work was resolved and runtime-verified on branch
      `f1-paged-attn` @ `112022a0b` (iswa graph block-table wiring `ea50522a7`; opt-in, off-by-default,
      bit-exact on plain Qwen3.6-35B and SWA gemma-4-31B) but was never folded. It is build-10079-era
      against a 10241-class champion, so folding means a re-base and a re-measure at the current floor.
- [x] **V6R-4 — parallel model load (repack + reader), lost in the v6 bundled revert.** ✅ 2026-09-25 (main-ak-seat)
      The OpenMP repack parallelization (`52ddd3200`, 2025-12-21; upstream PR #18239 closed unmerged) left the
      lineage when v6 Stage 1a `814e81782` was reverted as a whole (`358f0c748`); full record in
      `docs/reference/agent-config/INCIDENT_LOG.md` → INC-20260925. Re-ported onto the v10-lineage champion as
      `25132e042` (test restored and extended, 150/150 bit-exact) plus a parallel pread reader run as an OpenMP team,
      `90c12df42` (`--load-threads` / `LLAMA_ARG_LOAD_THREADS`; the old loader thread was pinned to CPU 0 by libgomp
      under `OMP_PROC_BIND=spread`). Bit-exact (tokens, KL on logits); 27B load 3.2x warm / 2.1x cold. Under
      `GGML_IQK=1` the DS41 recipe touches no CPU_REPACK tensor, so the reader is the whole DS41 win.
      **Champion advanced** `ak/champion/llama-cpp-ffc1bac82eec` `2b57340bf` → `90c12df42`, pushed to the fork
      (workspace-8d notified). Gates (research `a5906f24`, `data/champion-advance-fastload-20260925/`): DS41 519 GB
      load 254.0 / 277.7 s (anchor) → 98.2 s (fast loader), with a 262.6 s single-thread control on the same binary;
      production-recipe decode A/B cut by the operator after one pair (frontdoor 42.23 vs 41.79 tok/s, 0.99,
      identical output). Builds: `kernels/builds/cpu-20260925-90c12df42` (candidate) and
      `cpu-20260925-2b57340bf` (base), ggml linkage PASS. The DS41 campaign re-anchored on it (INF-77 DS41-C32).
  - [ ] **V6R-4a — carry the fast loader into production v11.** It rides the champion, so a v11 promotion from the
        champion tip inherits it; the promotion checklist must still prove it. Acceptance, at the v11 candidate
        gate: `25132e042` and `90c12df42` are ancestors of the candidate; `tests/test-repack-parallel` passes;
        a CPU load with auto load threads is measured against v10 on one production model; and the decode A/B
        that was cut at one pair here is run to the promotion protocol's full pair count.
        2026-10-01 (V6R-4d): the GPU half of champion `90c12df42` is validated no-regression vs v10, with SW-9
        exercised on GPU (pp +0.39%, tg -0.46%, floor 2%; identity and residency PASS). A v11 candidate built from a
        descendant tip, such as the DS41-C68 fold, still reruns that A/B (`gpu-champion-ab`) on its own full GPU build.
  - [ ] **V6R-4b — operator ratification of the forward-port rule** (OP-58 when the index row lands). Proposed
        text for `CLAUDE.md` § *Experimental Kernel Workflow*: forward-port one feature per commit; before
        reverting a bundled commit, split it and revert only the gated-out parts; a feature's test travels with it
        through every consolidation. Origin: INC-20260925. The operator ratifies; no session edits `CLAUDE.md` for
        this.
        2026-10-04 correction and status: INC-20260925 lost **our own** OpenMP parallel repack (`52ddd3200`,
        upstream PR #18239 closed unmerged) in the bundled v6 Stage 1a revert. It did not lose an upstream kernel.
        `docs/reference/agent-config/INCIDENT_LOG.md` already says this correctly. Repeat the correction wherever a
        summary calls the lost code "upstream". The operator was offered the OP-58 sign-off package in chat on
        2026-10-04, and it is still **unratified**. Nothing else depends on it. The DS41-C116 kernel-preservation
        gate (`kernel_coverage.py`, G0 at fold, research `4f8f11c7`) now enforces the "test travels with the
        feature" half in code, without the rule being ratified.

  - [ ] **V6R-4c — the fast loader's AUTO reader team must equal the compute thread count.** Found by INF-77 DS41-C57
        (2026-09-27, `/mnt/raid0/llm/tmp/ds41-c57-cpu0-20260927/`). `llama-model-loader.cpp:1689` sizes the auto pread
        team as `min(32, max_threads)`. Under GNU libgomp with `OMP_PLACES=cores` over 96 places, a 32-thread team
        ahead of the 48-thread compute team leaves libgomp throttled, and every decode barrier sleeps: about -11% tok/s
        and up to 13% request spread on DS41. The isolated long-wait micro-bench reproduces it (`gomp/results3.txt`).
        Fix on an experimental branch from the current champion tip, in the `90c12df42` lineage: default the auto team to
        `n_threads` (the compute `-t`), keeping `--load-threads` / `LLAMA_ARG_LOAD_THREADS` as the override. Acceptance:
        bit-exact load (tokens plus KL on logits, as for V6R-4); load time within noise of today's auto setting; and DS41
        under `OMP_PLACES=cores` spins (median OMP voluntary switches ~0) with no `--load-threads` flag. Check whether
        production v10 carries the fast loader; production resolves libomp with `KMP_BLOCKTIME=10`, so it is expected to
        be unaffected, but that is unmeasured. Rides V6R-4a into v11. Until it lands, DS41 carries the recipe arm (DS41-C59).
    - PARKED 2026-09-27 (operator): Loader-default fix prepared at e665242f0 (branch `experimental/loader-team-follows-threads-20260927`, 7 lines in `common/common.cpp` `common_model_params_to_llama`: auto load threads follow `-t`, plus the matching `--load-threads` help string in `common/arg.cpp`; cut from the AK champion tip `90c12df42`, pushed to fork), not built or benchmarked. The runtime-arm flag covers DS41 now (DS41-C59, `--load-threads 48`); resume by taking e665242f0 through the experimental workflow (build, then this item's acceptance: bit-exact load, load time within noise, DS41 spinning with no flag) into the champion, and from there into v11 via V6R-4a.

  - [x] **V6R-4d — live GPU no-regression validation of the champion's HIP build.** ✅ 2026-10-01 (all parts done; V6R-4d.2 below) The GPU half of the champion now
        exists: **`kernels/builds/gpu-20260929-90c12df42`**, the HIP (gfx90a) twin of `cpu-20260925-90c12df42`, built
        2026-09-29 (workspace-8d, operator-approved). It uses recipe `gfx90a-house-v1`, and its CMakeCache is identical
        to v10's `gpu-20260921-ffc1bac82` on every GGML/LLAMA/target/compiler entry. It reports `10308 (90c12df42)`.
        SW-9 is compiled in: `libllama-common.so` exports both `out_dists` overloads of
        `common_sampler_sample_and_accept_n`, and v10 GPU has 0. `verify_ggml_linkage.sh` PASS. RUNPATH carries no empty
        element. Record: that directory's `PROVENANCE.md`. No `ggml-cuda`/`ggml-hip` source differs from v10, so the
        GPU risk is host-side (server, sampling, loader). **No live check has been run.** The MI210 is full with the
        production 27B (67.0/68.7 GB). Gate: the 2nd MI210, or an operator-approved displacement window. Acceptance:
        the GPU device appears in the startup log, speed is within the floor of `production/gpu` on the production 27B,
        output is byte-identical at `n_probs=0`, and draft-mtp `n_probs>0` returns probs on every token. **Standing
        rule: every future champion advance produces BOTH a CPU and a GPU store build of the same commit**
        (single-champion invariant: one commit, one build per device). A CPU-only advance leaves the GPU path on a
        pre-advance build; that is how SW-9 went five days without a GPU build.
      - 2026-09-29 07:05-07:09Z — **attempted in the bundled :8083 window; not completed.** The A/B step
        (`/mnt/raid0/llm/tmp/gpu-champion-ab/`, order P C P on :8197, host threads on 72-79) failed three times in a
        row on over-strict per-arm checks, each before the first probe. No A/B number exists. :8083 was restored on
        v10 each time (thesis handoff ARCHSWAP-4).
        - 07:05Z: the `--slot-save-path` dir was never created, so llama-server rejected the argument.
        - 07:07Z: the device-line regex expected `using device ROCm0` / `offloaded N/N layers`. The v10 server prints
          neither at verbosity 3; its only ROCm line is a sampler-support warning.
        - 07:08Z: the thread-affinity check reported `OUTSIDE:[0..7]`. ROCr's async-event thread (wchan
          `kfd_wait_on_events`) has its affinity reset to 0-191 by the runtime. This is normal: it is identical in all
          four live GPU processes (production :8083 and :8086, whisper, tts).
        - Fixed offline the same day. Every per-arm check (device, placement, `/props`, watcher, sampler) is now an
          `ab_probe.py` subcommand that prints what it saw. `selftest/live_checks.sh` runs each check read-only against
          today's arm logs and the live production servers.
        - **Re-planned for the vision (:8086) window.** That window tests identity, speed and residency only:
          Qwen3-VL has no MTP drafter, so it cannot exercise SW-9.
        - **The SW-9 GPU check (draft-mtp `n_probs>0`) needs an MTP model**: a :8083 window or the 2nd MI210.
      - [x] **V6R-4d.0 — harden the A/B per-arm checks.** ✅ 2026-09-29 — every check (device by KFD VRAM ≥ 1 GB,
            per-thread placement re-checked after the probe, `/props`, a paused-mode watcher, the summary) is an
            `ab_probe.py` subcommand that prints what it saw; `selftest/live_checks.sh` passes 24/24 read-only against
            the arm logs and live :8083/:8086 (`/mnt/raid0/llm/tmp/gpu-champion-ab/`). Lesson:
            INC-20260929-dry-run-missed-live-checks.
      - [x] **V6R-4d.1 — run the champion HIP A/B in the vision (:8086) window.** Tests identity, speed and residency
            (`vision_ab.sh`). Needs a DS41 pause coordinated with workspace-76 over the bus; this is not an operator
            decision.
            ✅ 2026-10-01 — **covered, superseded by V6R-4d.2.** The vision window was planned only because no MTP
            window existed. The production-27B A/B below checks identity, speed and residency on the production
            model itself, plus SW-9, so a separate :8086 run would add nothing.
      - [x] **V6R-4d.2 — the SW-9 GPU check (draft-mtp `n_probs>0` returns probs on every token)** on an MTP model: a
            :8083 window (DS41 pause, workspace-76) or the 2nd MI210.
            ✅ 2026-10-01 — **PASS** (workspace-8d). Run 12:14 to 12:16:40Z in workspace-76's DS41 pause, on the
            production model Qwen3.8-27B Q8_0 with its MTP draft. The MI210 device lock was held for the A/B only.
            - Builds: P = production v10 `kernels/production/gpu` (`gpu-20260921-ffc1bac82`, build_info
              b10303-ffc1bac82); C = champion `kernels/builds/gpu-20260929-90c12df42` (b10308-90c12df42).
            - Arms: P C P on :8197, host threads `-t 8` on cores 72-79, membind 3.
            - Every arm was checked for KFD VRAM residency, its own `libggml-hip` mapped, placement OK, and
              `/props` build_info.
            - pp/tg tok/s: P 886.9/39.01, C 884.4/38.83, P 875.1/39.00.
            - RESULT: `PASS=True; identity C==P True; P-self True; pp_tps_median +0.39% (floor 2.00%);
              tg_tps_median -0.46% (floor 2.00%); sw9_C_all_probs=True; sw9_P_gap=True`. That is, C returns probs on
              every draft-mtp token and v10 P still shows the gap.
            - Restore: production :8083 relaunched on v10 (PID 1677674, slot dir `architect_critic`), /health ok.
            - Evidence: run dir `/mnt/raid0/llm/tmp/gpu-champion-ab/runs/w8083-20261001T121346Z/` (`result.json`
              sha256 `ef3b32b79c043b772abb8cc152f52ceb1f0b4a1d43ea85c399e6676ef18a5821`, schema
              `epyc.gpu_champion_ab.result.v1`); log `/mnt/raid0/llm/tmp/gpu-champion-ab/run_27b_ab_lockonly.log`.
            - Implication: the GPU side of the champion `90c12df42` is no-regression vs v10, with the SW-9 fix
              exercised on GPU. The v11 consequence is recorded under V6R-4a.

#### DO-NOT-FOLD ledger — branches that exist on the CPU lineage and must NOT be picked up by a sweep

| branch @ commit | disposition | why | condition if ever folded |
|---|---|---|---|
| `inf70/sync17-fix2` @ `2516c9807` | **DO NOT FOLD — CLAIM, and the claim is a REGRESSION** | **−2.136%** (ratio 0.9786, CI [0.9771, 0.9804], p=0.0286, n=4v4 in one hot session, 24/24 outputs byte-identical). Both knobs default **ON** on that branch, **and that default IS the regression**. | If ever folded, **both knobs must flip default OFF**. Its value is as an **instrument**, not a keep. |

**Why this negative is admissible where SYNC-19's was not.** The `P` arm is a *directional positive
control*: the knob demonstrably reaches dispatch, confirmed by per-arm server knob readback. Decomposition
of the −2.136%: **C→P (FIX-3's yield alone) −1.883%**; **P→F (column split alone) −0.258%**. The tiny-solo
run was the better choice — the same barrier arithmetic that refuted `inf10-gemv-fusion`. SYNC-19's model
predicted **+3.31%**; the sign is wrong.

- CHAMP-2 (THP shim: KEEP) and CHAMP-3 (multi-launch headline with a session-unit CI) are done (2026-09-08): § *Completed Scope*.

---

## CHAMPION MAXIMUM-PERFORMANCE HEADLINES — 2026-09-08, TWO MODELS (the postable numbers)

**Canonical, citable artifact: [`docs/design/champion-max-performance-20260908.md`](../../docs/design/champion-max-performance-20260908.md).**
Quote from there; do not re-derive from this summary and do not re-type the recipe.

### First headline model — Qwen3.8-27B-Q8_0 (dense, DFlash2 drafter)

Champion `ef81196d5` (everything folded), Qwen3.8-27B-Q8_0, MI210 gfx90a, DFlash2 drafter, canonical serving
recipe `qwen3.8-27b-q8-gpu-dflash2-np4` with **only `np` varied**, 3 launches per point, **residency `proven` on
all 12 launches**, peak VRAM 33.1–43.1 GiB, sclk pinned 1700 MHz. Unit: **LAUNCH**.

| slots (`np`) | aggregate tok/s | per slot | p95 dev across 3 launches | runs |
|---:|---:|---:|---:|---|
| 1 | **79.25** | 79.25 | 0.44% | 79.2, 79.2, 79.6 |
| 2 | 109.41 | 54.70 | 1.60% | 109.4, 108.9, 111.2 |
| 4 | 167.76 | 41.94 | 3.33% | 167.8, 162.2, 169.7 |
| 8 | **179.12** | 22.39 | 1.82% | 182.4, 178.2, 179.1 |

> **79.25 tok/s single user · 179.12 tok/s aggregate at peak concurrency.**

- **`np=4` is the operating point.** The curve turns over hard between 4 and 8 slots: **+6.8% aggregate for
  roughly HALF the per-user rate.** np=4 delivers **93.7% of peak aggregate** while each user still sees
  ~42 tok/s. The canonical recipe is already np=4 — this **confirms** the standing choice, it does not change it.
- **Dispersion GROWS with concurrency** (0.44% at np=1 → 3.33% at np=4). A single reading at np=4 is far less
  trustworthy than one at np=1; anything gated at np=4 must state its `n`. Directly relevant to R23-61.

Raw: `/mnt/raid0/llm/tmp/maxperf-20260908/sweep.json` + `sweep.log`; promoted into the research repo (`data/`) at
commit `48a6f6f2`.

- [x] **HEAD-1 — file the maximum-performance sweep as a canonical citable artifact** ✅ 2026-09-08
      (`docs/design/champion-max-performance-20260908.md`; referenced from this page).

### SECOND HEADLINE MODEL — Qwen3.6-35B-A3B-MTP-Q8_0, same champion, same GPU (2026-09-08 19:37:30-20:14:00Z)

Recipe `qwen3.6-35b-a3b-q8-gpu-mtp` (**new**, research `c3e362a1`), **MTP self-drafting — no separate
drafter**, `draft_n_max=4`, only `np` varied. 24 launches, **residency `proven` 24/24**, 2,952 samples,
sclk flat 1700 MHz at *every* point. Unit: **LAUNCH**. Details and per-point `recipe_hash`:
`docs/design/champion-max-performance-20260908.md` §6.

| slots (`np`) | aggregate tok/s | per slot | p95 dev | peak VRAM | launches |
|---:|---:|---:|---:|---:|---:|
| **1** | **112.68** | 112.68 | **2.70%** | 36.61 GiB | **6** |
| 2 | 130.54 | 65.27 | 1.38% | 36.90 GiB | 3 |
| 4 | 189.57 | 47.39 | 1.13% | 37.50 GiB | 3 |
| 8 | 242.75 | 30.34 | 1.23% | 38.78 GiB | 3 |
| 12 | 268.12 | 22.34 | 1.88% | 40.16 GiB | 3 |
| **16** | **310.96** | 19.43 | 2.53% | 41.37 GiB | 3 |

> **112.68 tok/s single user · 310.96 tok/s aggregate at 16 slots — and 16 slots is the HIGHEST MEASURED
> POINT, NOT the ceiling.**

- **IT HAS NOT SATURATED.** Marginal aggregate gain per step: +15.85% (1→2), +45.22% (2→4), **+28.05%**
  (4→8), +10.45% (8→12), **+15.98%** (12→16). The last step is the *second largest* — the decay is not even
  monotonic. Peak VRAM at np=16 is **41.4 of 64 GiB**, growing ~1.2 GiB per doubling: memory is not the
  constraint either. 24 and 32 slots were offered and the operator declined (*"lets stop here"*). Filed as
  **HEAD-3** so the unfinished curve is a recorded decision, not a gap.
- **IT BEATS THE 27B AT BOTH ENDS — and this is ARCHITECTURE, NOT A KERNEL RESULT.** +42.2% single-user
  (112.68 vs 79.25) and +73.6% peak aggregate (310.96 vs 179.12), despite being the larger file on disk
  (35.21 GiB vs 27.05 GiB, or 28.97 GiB counting the 27B's DFlash2 drafter). **Same binary on both runs.**
  The 27B is `qwen35`, dense, 65 blocks, d=5120, FFN 17408 — every token reads essentially all of it. The 35B
  is `qwen35moe`, 41 blocks, d=2048, **8 of 256 experts routed per token** plus one shared expert of width
  512. Decode is weight-bandwidth-bound, so the rate tracks bytes *read per token*, not bytes on disk.
  **Anyone who reads "35B > 27B" as a kernel result concludes the champion scales with model size, which is
  the opposite of true.**
- **THE TWO MODELS GET DIFFERENT OPERATING-POINT ADVICE, structurally.** The 27B curve turns over at 4→8
  (+6.8% aggregate for ~half the per-user rate) → **np=4**, 93.7% of peak, ~42 tok/s per user. The 35B is
  still climbing at 16 → **np=16** of what was measured, 311 aggregate, ~19 tok/s per user. A dense model
  saturates the memory system early; an MoE at low batch does not, because extra concurrent tokens route
  into expert reads that are already being paid for.
- **THE np=1 SPREAD IS A PROPERTY OF THIS MODEL, NOT A SMALL SAMPLE.** Doubling n did not tighten it:
  2.350% p95 dev at n=3 → **2.696% at n=6** (slightly *wider*). Against the 27B's **0.44%** at the same slot
  count on the same GPU in the same window — a **6.1×** difference. **Every single-user headline for the 35B
  must carry that ~2.7% between-launch dispersion**; a 27B-grade ±0.5% precision is not available on this
  model at np=1 and implying one is a `FLOOR-UNIT-1` violation.

- [x] **HEAD-2 — Qwen3.6-35B-A3B GPU concurrency sweep measured and filed** ✅ 2026-09-08
      (24 launches, residency proven 24/24; recipe `qwen3.6-35b-a3b-q8-gpu-mtp` committed at research
      `c3e362a1`; numbers in `docs/design/champion-max-performance-20260908.md` §6).
- [x] ~~**HEAD-3 — the 35B concurrency ceiling is UNMEASURED above np=16.** The curve had not saturated~~ (closed 2026-10-29 audit: OBSOLETE → box text: operator said "lets stop here" at np=24/32 on 2026-09-08 - recorded decision, not oversight (L912-916))
      (+15.98% on the last step, the second-largest of the six) and VRAM stood at 41.4 of 64 GiB. `np=24`
      and `np=32` were offered on 2026-09-08 and the operator said *"lets stop here"* — so this is a
      **recorded decision, not an oversight**. Reopening costs ~2 launches × 2 points ≈ 12 min of exclusive
      GPU. Blocked on nothing but an operator go for the host. Until it is run, **never quote 310.96 tok/s
      as a maximum** — it is the highest measured point.
- [x] **HEAD-4 — promote the 35B sweep out of scratch into the research repo `data/`.** ✅ 2026-09-16
      Research `data/ak-champion-maxperf-35b-2026-09-08/` (JSON/logs/`sweep.py` at `8c5a9652`; the other two
      as-executed scripts, `SHA256SUMS` and a README step correction at `1eb4a89b`). Files byte-identical to
      scratch; every table value recomputed from the JSON and matched `docs/design/champion-max-performance-20260908.md` §6.
      Belief-kernel write-side wiring filed as SC82 in `vidya-belief-substrate-program.md` (the 2026-09-08 sweeps are pre-hook).
- [x] **MTP-27B-1 — the 27B is ALSO MTP-capable, and that is the missing PROD-BASE-1 denominator.** ✅ 2026-09-21
      — v9 measured on the 27B with MTP self-draft (`mtp-Qwen3.8-27B-Q8_0.gguf`, recipe
      `qwen3.8-27b-q8-gpu-mtp`) at ctx 65536: **61.32 / 85.76 / 136.06 / 169.63** across np 1/2/4/8. That IS the
      denominator; the champion on DFlash2 gives 80.87 / 108.75 / 168.64 / 184.48, ratios **1.319 / 1.268 /
      1.239 / 1.088**. Recipe-to-recipe, each kernel at the best configuration it can run (operator direction). The
      Qwen3.8-27B GGUF carries the MTP head (`blk.64.nextn.eh_proj/.enorm/.hnorm/.shared_head_norm`,
      `qwen35.nextn_predict_layers = 1`) — the same shape the 35B has at `blk.40`. It could not be expressed
      as a recipe until `c3e362a1` made `spec_decode.drafter` optional, so it has never been measured through
      the loop. **MTP self-draft is exactly what frozen production supports for this model** (v9 cannot load
      the DFlash2 GGUF at all), so a `qwen3.8-27b-q8-gpu-mtp` recipe is the denominator PROD-BASE-1 needs.
      Write the recipe, sweep `np`, and the champion-vs-production comparison becomes measurable on a lane
      production actually has. Depends on PROD-BASE-1 for the production-side arm; the champion-side arm is
      runnable today. Blocked on nothing but host time.

## ⚠ THERE IS NO CHAMPION-VS-PRODUCTION RATIO FOR THIS CONFIGURATION, AND THERE NEVER WAS ONE

**Production v9 never ran this lane.** `artifacts/operator/ratify_v9_final_freeze_20260811.json` →
`production_certification` records:

| field | value |
|---|---|
| `qwen36_27b_q8_dflash` | `lane_ineligible_acceptance_below_floor` |
| `dflash_kernel_capability` | `certified` |
| `dflash_lineup_enabled` | **`false`** |

So production was frozen with the DFlash drafter **compiled in but deliberately NOT enabled for the 27B** —
acceptance was below floor at the time. The v9 qualification summary
(`artifacts/operator/v9-qualification-20260810T235723Z-0db32c06e/summary.json` →
`gates.gpu_candidate_functional_observation`) carries GPU decode for **other roles only**: architect native MTP
**53.359** tok/s, coder (request_cap 0, no draft activity) **30.268**, worker vision **96.671** — and that block
is itself stamped `decision_grade: false`.

Three separate reasons the comparison does not exist:

1. **Different model.** The key is `qwen36_27b_q8_dflash` — **Qwen3.6**-27B, not 3.8. Qwen3.8-27B replaced
   Qwen3.6-27B-MTP-Q8_0 in production only on 2026-08-20/21, **nine days after** this freeze.
2. **Different drafter, and the frozen binary cannot load ours.** Frozen v9 **rejects the DFlash2 GGUF outright**
   — `wrong number of tensors; expected 81, got 58`. Production's ceiling for Qwen3.8-27B is **MTP self-draft**,
   not DFlash2.
3. **The lane was disabled on purpose.** `dflash_lineup_enabled: false` is a decision, not an omission.

> **The champion's advantage on this surface is partly a CAPABILITY, not a speed delta.** Anyone quoting a
> champion-vs-production ratio for Qwen3.8-27B + DFlash2 is quoting a number that was never measured, because
> production cannot produce the denominator.

- [x] **PROD-BASE-1 — if a champion-vs-production headline is ever wanted, measure production AT ITS OWN BEST.** ✅ 2026-09-21
      Its own `np` sweep, whatever spec configuration it actually supports (MTP self-draft for Qwen3.8-27B),
      under the same host discipline and with residency proven — **never** forcing production through the DFlash2
      recipe, which measures a lane it does not have and would report a capability gap as a speed gap. Until that
      exists, the champion headline stands **alone**, as an absolute number, with no ratio attached. Not blocked
      on anything; not scheduled — it needs the host and an operator go.

## METHODOLOGICAL CAUTION — a BENCH-surface number is not a SERVING number

**Recorded as an error of mine, 2026-09-08.** I quoted the `tg128` llama-bench figures (production 29.4 /
champion 31.0, **+5.63%**) as "single-stream GPU decode". That was wrong.

**`llama-bench` cannot do speculative decoding at all.** `tg128` is therefore a **bench PROXY** for a serving
path that has a drafter in it, and it understates the real single-stream serving rate by **~2.5×**
(**79.25** measured on the recipe vs **31.0** on the bench surface). It also violated the standing rule that
**headline numbers come from the production recipe**.

| surface | valid use | invalid use |
|---|---|---|
| `tg128` / llama-bench | **A/B kernel comparison** — both arms share the surface, so the drafter's absence cancels | **any absolute headline**, any cross-surface ratio, anything the operator would post |
| serving recipe (`serving.calibrate_floor` / the gate) | absolute headlines, operating-point choice, capacity claims | — |

The +5.63% tg128 delta is **not retracted as an A/B** — it remains a valid kernel-vs-kernel comparison on its own
surface. What is retracted is its use as a **rate**. Compiled into the wiki with the R23-58 bounded null.

- [x] **METH-BENCH-1 — the bench-vs-serving distinction is recorded where headlines are formed** ✅ 2026-09-08
      (this page, `docs/design/champion-max-performance-20260908.md`, and the wiki compile).

**RATIFIED INTO THE CONSTITUTION BY THE OPERATOR, 2026-09-08 — this rule is no longer campaign-local.**
The operator ran `scripts/operator/ratify_measurement_bench_vs_serving_20260908.sh --apply`; committed as
`b05c4433` (154 additions to `MEASUREMENT.md`, 35 to the agent digest, zero deletions, no code, no threshold,
no gate behaviour changed). This caution is now **`INSTRUMENT-CLASS-1`** in `MEASUREMENT.md`, alongside
**`FLOOR-UNIT-1`** (a floor carries its `unit`, is calibrated at n≥24, and records `n` and an interval) and
**`BOUNDED-NULL-1`** (a null states the effect sizes its power excludes and cites a both-directions positive
control). `autokernel-rebuild-program.md` → **RATIFY-MEAS-1** is closed.

**The open successor is `RATIFY-MEAS-2`** (`autokernel-rebuild-program.md`): there is **no `P-SERVE-*`
protocol row in the registry**, so every serving number this campaign quotes — including both headlines above —
formally cites no protocol. That is the next amendment, and it was deliberately left out of RATIFY-MEAS-1
rather than smuggled in.

## Research intake 2026-10-20 — DeepInfer (research intake entries 2116–2142, see research/intake_index.yaml)

Operator-approved 2026-10-20 via research intake (plan sha256 recorded in the session's stage3_filing).

- [ ] **CH-19 — Screen the dead iqk_moe_fused_up_gate hook as a default-off fused MoE up+gate+SwiGLU node (intake-2123#record, intake-2124#record).** Add a caller in the CPU MUL_MAT_ID path behind a default-0 knob (fix the non-IQK stub signature); gate on MUL_MAT_ID test-backend-ops and decode-logit NMSE; then a same-window ABA on the champion for Qwen3.6-35B-A3B Q8_0 decode (frozen manifest, 5 interleaved pairs, predeclared keep at >= the window floor); drop if within noise.
  - *(2026-10-20.)* Implemented on `experimental/intake-fixes-20261020` (CH-19 2f5873d60), queued for CPU correctness tests. Gated by an ENV var (`GGML_CPU_FUSED_UPGATE`): before any champion fold this must become an argv/request/metadata switch (ONE-champion rule: no env-only gates; env only as a diagnostic kill switch).
  - *(2026-10-21.)* `ch19-fused-path-engaged` FAILS: the fusion never engages. `ggml_can_fuse` (ggml-impl.h:669) requires each node to consume the previous one, but the gate MUL_MAT_ID does not consume the up MUL_MAT_ID, so the {MUL_MAT_ID, MUL_MAT_ID, GLU} predicate is always false; fused-vs-unfused NMSE was exactly 0 because the unfused path ran both times (vacuous). Results `/mnt/raid0/llm/tmp/intake-fixes-20261020/queue-results/51-intakefix-tests/`.
  - [x] **CH-19.1 — fix the fusion predicate** in `ggml_cpu_try_fuse_ops` (up and gate each used exactly once, only by the GLU, same shape — or `ggml_can_fuse_subgraph_ext`), rebuild, rerun 51-intakefix-tests until `ch19-fused-path-engaged` passes with a real NMSE. ✅ 2026-10-21
  - *(2026-10-21.)* CH-19.1 done: b51a0047d. Graph order is gate, up, SWIGLU (sibling MUL_MAT_IDs); new predicate `ggml_cpu_can_fuse_moe_up_gate` (ggml_can_fuse_subgraph + SWIGLU split, not swapped, src0=gate/src1=up, use_count 1, shared src1+ids, same shape). Also: barrier before fallback if the iqk kernel fails after writing wdata (race with the unfused MUL_MAT_ID). Engaged per cell (one process per cell, marker present) on Q4_K/Q8_0 x nt=1/8; fused-vs-unfused NMSE = 0 exactly in all 4 (same iqk GEMMs, iqk v_silu == ggml_v_silu), test-backend-ops CPU-vs-ref MUL_MAT_ID 815/815, MUL_MAT_ID_FUSION 13/13, SWIGLU 24/24. Results `/mnt/raid0/llm/tmp/intake-fixes-20261020/queue-results/52-ch19-fix-tests/`. Qwen3.6-35B-A3B-MTP-Q8_0 has separate ffn_gate_exps/ffn_up_exps (no merged gate_up), so the fusion applies to the frontdoor.
  - [x] **CH-19 pre-fold: replace the `GGML_CPU_FUSED_UPGATE` env gate with an argv/request/metadata switch** (ONE-champion rule; env only as a diagnostic kill switch). Closing CH-19 requires this box. (filed 2026-10-20) ✅ 2026-10-21
  - *(2026-10-21.)* Switch landed: 57d96e2cb (pushed to `fork`). `--cpu-fused-moe-upgate on|off` (common arg: llama-server and all common tools; llama-bench as a sweepable instance param, recorded as output field `cpu_fused_moe_upgate`) -> `llama_context_params.cpu_fused_moe_upgate` (default false) -> `ggml_backend_cpu_set_fused_moe_upgate` (proc address, same pattern as `use_ref`) -> `ggml_cplan.fused_moe_upgate`. `GGML_CPU_FUSED_UPGATE=0` is now a kill switch only; no env value can enable the fusion. Predicate/kernel unchanged. 27/27 checks (switch off == default bit-exact, env=1 cannot enable, env=0 kills on, per-cell engagement + NMSE 0, test-backend-ops unchanged, both binaries expose the flag): `/mnt/raid0/llm/tmp/intake-fixes-20261020/queue-results/53-ch19-switch-tests/`.
  - [x] **CH-19.2 — T3 speed screen** (script `/mnt/raid0/llm/tmp/cpu-queue-f8/timing/t3-ch19-screen.sh`, ~70 min exclusive full-host CPU; slot pending on the shared calendar). Canonical recipe via `bench_canonical.sh`, Qwen3.6-35B-A3B-MTP-Q8_0, pp512/tg128 at d0 and d8192, 5 ABAB pairs x r=3, marker-gated validity; binary is the in-worktree build `build-ch19/` (keep it until T3 has run). (filed 2026-10-21)
  - *(2026-10-21, workspace-f8.)* CH-19.2 RAN 19:10-19:16Z (exclusive window, 5 ABAB pairs x r=3, `bench_canonical.sh`, 0 invalid arms, marker-gated). Out `/mnt/raid0/llm/tmp/intake-fixes-20261020/t3-ch19-screen/20261021T191000Z/` (`summary.txt`, `records.jsonl`, `provenance.json`; built_from `57d96e2cb`, `build-ch19/`). ON/OFF medians (fused up+gate vs unfused): pp512 d0 0.9850 (min 0.9604, max 1.0472), tg128 d0 0.9958 (0.9737-1.0029), pp512 d8192 0.9901 (0.9757-1.0251), tg128 d8192 0.9755 (0.9554-1.0088). OFF tg128 d0 56.74 t/s, ON 56.46. The fused node is NOT faster on any cell (all four median ratios below 1.0). The screen is valid; the keep question is decided by the next box.
  - [x] **CH-19.3 — apply the predeclared verdict to the T3 result.** ✅ 2026-10-21 VERDICT: PARKED (backlog audit `/mnt/raid0/llm/tmp/inference-backlog-audit-20261021/REPORT.md` §1 CH-19). Keep needs ON/OFF at or above the same-window floor on the Qwen3.6-35B-A3B Q8_0 decode (tg128); the four median ratios are 0.9755-0.9958, so by the CH-19 rule ("drop if within noise") the default-off hook is dropped unless the window floor shows a real regression to explain. Read the window floor from the records, write the verdict (drop or park the branch `experimental/intake-fixes-20261020` CH-19 commits), and record it here; do not fold into the champion. (filed 2026-10-21)
    - *(2026-10-21, verdict.)* The fused up+gate+SwiGLU node is not faster on any cell: ON/OFF median ratios (t/s, higher = better) 0.9755-0.9958 (pp512 d0 0.9850, tg128 d0 0.9958, pp512 d8192 0.9901, tg128 d8192 0.9755), and its output is bit-identical to the unfused path (NMSE exactly 0), so there is nothing to trade for the extra code. Do NOT fold into the champion. The CH-19 commits on `experimental/intake-fixes-20261020` stay on that branch only; DELETE them unless an optional, low-priority DS41-1017 data point (mergeable into the DS41 session S3, `--cpu-fused-moe-upgate on|off`, same-window ABA on the 1017 build) shows a gain. Evidence: `/mnt/raid0/llm/tmp/intake-fixes-20261020/t3-ch19-screen/20261021T191000Z/`.
  - [ ] **CH-19.4 — optional, low-priority: DS41-1017 fused-up/gate data point** (merge into the DS41-1017 correctness/timing session S3; no dedicated slot). `--cpu-fused-moe-upgate on` vs `off` on the 1017 MXFP4 build in the same window; if ON/OFF is at or above the window floor, reopen CH-19 for the DS41 lane; otherwise delete the CH-19 commits from `experimental/intake-fixes-20261020`. (filed 2026-10-21 from CH-19.3)
- [x] **CH-21 — Hybrid `--cache-reuse` engine fix (in progress as hybrid-cache-reuse-fix).** The server tail of `llama_memory_recurrent` is not shifted by `seq_add` (it moves only the tail cell `pos`) and `seq_rm` on a recurrent tail inside the range returns false unless within `n_rs_seq` rollback while the server ignores the return, so enabling `--cache-reuse` on a hybrid can silently reuse a wrong state. Fix on an experimental branch from the champion tip: refuse or correctly handle the shift for recurrent memory, with a test that a hybrid with `--cache-reuse` set is bit-identical to the same run without it. Add the manifest row to `docs/reference/kernel-manifests/llama-v11-manifest.md` in the same commit (fold only into the champion). Premise of the defect: DESIGN.md section 0 of the chunk-KV design and the cache-reuse-hazard check. Acceptance: the test passes on Qwen3.6-35B-A3B and Qwen3.8-27B with `--cache-reuse 256`, the manifest row exists, and production argv still sets no `--cache-reuse`. Estimate: 2-4 days. Real-model acceptance PASS 2026-10-21 (run by workspace-5c on C2 build `cpu-20261021-f9c01ce0e-c-nemotron`, tip `experimental/c-plus-nemotron-bolt-20261021` @ `49550eda5`): both Qwen3.6-35B-A3B-MTP-Q8_0 and Qwen3.8-27B-Q8_0 logged the load-time disable line, logged the per-request ignore line, and served the `--cache-reuse 256` request. Evidence: `/mnt/raid0/llm/tmp/nemotron-c2-prep-20261021/ch21-f9c01ce0e.out` (copied to `artifacts/ch21-realmodel-20261021/`). Check-script fix: the original `/mnt/raid0/llm/tmp/ch21-realmodel-check/run_ch21_check.sh` could not pass because `strings | grep -q` under `pipefail` returned 141 (SIGPIPE), and it asserted `generation_settings.n_cache_reuse`, which the server never emits. Replaced by `/mnt/raid0/llm/tmp/nemotron-c2-prep-20261021/run_ch21_check_fixed.sh` (original kept as `run_ch21_check.sh.broken`).
  - *(2026-10-21, dpf-specs.)* Fix on `experimental/hybrid-cache-reuse-guard-20261021` @ `8b08c9f25`, manifest row V11-098, folded into `experimental/c-plus-nemotron-bolt-20261021`; tiny-model tests only. STAYS OPEN: the real-model check (35B-A3B and 27B started with `--cache-reuse 256` must log the disable line and report `n_cache_reuse` 0) is a short correctness run, server start and log only. Ready-to-run script, window-guarded (`WINDOW_CONFIRMED=1`, takes the built `llama-server`): `/mnt/raid0/llm/tmp/ch21-realmodel-check/run_ch21_check.sh`.

## Bundle preflight observation contract — filed 2026-10-25

- [ ] **CH-OBS-BUNDLE — make the runnable C3/C4/C5 bundle preflight three-valued before its next operational use.** `scripts/champion/fold_gates/bundle_gate_c{3,4,5}.sh` currently treat an empty or failed `ps -eo args= | awk ...` pipeline as no DS41/Q38FN AutoKernel loop. A missing/unreadable process channel or argv drift must instead refuse launch (`unobservable` means busy for this exclusion check). Adopt `scripts/coordination/observer_guard.sh` with two independent identity channels and an `observe` entrypoint; validate present/absent/blind/disagreement with synthetic stand-ins and prove preflight never launches while blind. Determine the authoritative second channel from the actual loop lifecycle before choosing it; do not invent a heartbeat relationship. Preserve the reviewed verdict helpers and Q38FN sign-only semantics, do not run a real inference gate, and do not rewrite historical/adopted TMP scripts. Register the tracked runnable copies as `v1` only when the behavioural proof passes, then close this task. The exact-byte original C5 fixture stays an exempt reference input. This task records the existing exclusion-observer gap discovered by the normal publication hook; portable verdict regressions already passed, and that passing proof is not a claim about this preflight's liveness observation.

2026-10-30 00:20 filing: original FA4r4ended00:01:49rc75 after3seconds at151GiBdisk admission (150floor+1GiBoutputreserve), before an attributable228-case run; no normalcompletion or V11-FA-4a/4bverdict. A separate00:06:34rc1retry endedINCOMPLETE withverifiedcleanup because process evidence vanished withoutmatching launchsidecar/pidfdexit. Its ONpartial228/224OK/4nonfinite andmodelprobe0/10nonfinite are retained separately, withno OFFpair or exact-set/band/quality decision. Owneraction: repair captured-process evidence and requalify under the existing resource/grant rules. [Exact timestamped native segments](../../artifacts/compute/results-filing-20261030-0020.json). [belief: cc]

**2026-10-30 C3 native profiling compatibility prerequisite:** exact original L control on the v10-based instrument failed on non-finite DFlash target features; exact original B failed before a request because the Bolt GGUF expert-count type was unsupported. These originals remain failures, distinct from successful tiny canaries. A reusable experimental lane now contains full C3 plus native instrumentation at479ee3bbb, with current frozen production as ancestor. Its relocatable CPU build packet passed a real object-compile smoke and deadline cleanup control; the full linked build has not run. The separate c3.v2 prospective reader preserves v1 and refuses unsealed or canary inputs. Actual build-artifact sealing and new real L/B controls remain necessary before profiling READY. [Publication audit](../../artifacts/compute/codex3-publications-20261030-1415.json). [no-belief: source/build preparation; no original profile result]
