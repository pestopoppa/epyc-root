# EXP01 input recovery, 2026-11-18

This packet restores the exact 36,914,690,368-byte non-MTP Q8_0 source in private scratch and schedules a fresh calibration and requantization on the archived ik CPU recipe. The source repository HEAD and embedded native build prefix are `c04881fc0f31dae5f8ec59c1d683889f0c9dfa11` and `c04881fc0`. Tooling pins bind the executable, resolved ggml and llama libraries, linked paths, launcher, builder, corpus and item-set receipts. The publisher records the deployed allocator engine digest in its PASS receipt. The original pilot and control retain their historical identities. Newly generated matrix and GGUF files carry their own run identity and need a separate content check before official use.

| Input | SHA-256 | Original source |
| --- | --- | --- |
| Qwen3.6-35B-A3B non-MTP Q8_0 | `afddb074d3ce9ec8a3f64bfe7288a6c33f0d3a629be3caf4b5de1386a582dbd5` | [Pinned Hugging Face revision d98fa7286](https://huggingface.co/bartowski/Qwen_Qwen3.6-35B-A3B-GGUF/blob/d98fa7286daa6544d050929df95e436741ee739b/Qwen_Qwen3.6-35B-A3B-Q8_0.gguf) |
| Wikitext-2 test calibration corpus | `bfe9eb16ab9987fb88bde4ea9a30a00f2a45db01dfc14bad78d05325789c4f12` | `/mnt/raid0/llm/tmp/brf-exp01/calib/wiki.test.raw` |
| 24 paired items for successor official capture | `96dc98cf6b2cfdd65897f1deaf2b6f8481225d013851262cf08d6171f150fdbc` | `/mnt/raid0/llm/tmp/brf-exp01/items/exp01-items-24.jsonl` |
| Qwen3-0.6B Q8_0 smoke fixture | `c159d1518f16bc42533d9a09f034eb598b670341adc2b08b9a9751614aea71eb` | `/mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf` |

The publisher smoke uses four allocated CPUs and threads, one 512-token matrix chunk from the Qwen3-0.6B fixture, and one native IQ4_KT conversion of its `blk.0.ffn_up.weight` tensor. Other quantized weights pass through as Q8_0. The original full-fixture attempt hit the 300-second first-progress limit. The narrowed smoke emits its result after rederiving the matrix and confirming that the native quantizer performed exactly the named conversion. It establishes publisher readiness for the recovery row. Full recovery acceptance requires the official input build and post-build seals. The official input build uses one 24-CPU quarter, one shared 560×512 imatrix with `--no-ppl -no-fug -no-fmoe`, and Q4_K_M, IQ2_XXS, IQ4_KT and IQ2_KT outputs. Each uses `--allow-requantize` and that exact matrix. Both modes retain their native logs and terminal dispositions in fresh attempt paths. Official terminal success is `complete-unsealed` because model hashes are calculated outside allocator grants.

The runnable copy is `/mnt/raid0/llm/tmp/vidya-belief-substrate/exp01-ready-20261118`. The allocator's work directory is the dedicated `engine-work/` subdirectory so its recursive exit-time permissions normalization leaves the pinned inputs’ stat identities intact. The source download uses validated disjoint HTTP ranges and a one-time complete SHA-256 pass. The detached recovery records its PID, boot ID, process start ticks, exact command and lock path in `inputs/Q8-RECOVERY-OWNER.json`. It writes `inputs/Q8-RECOVERY-TERMINAL.json` on exit or TERM, INT or HUP, and writes `inputs/Q8-VERIFIED.json` on successful SHA-256 verification. The runtime checks the verified source's exact device, inode, size, mtime and ctime. The archived parent, tooling and fixture receipts include machine-local stat fields. Recreate these receipts if the source files move.

Run these from the current Vidya worktree after the Q8 receipt is present.

```bash
packet=/mnt/raid0/llm/tmp/vidya-belief-substrate/exp01-ready-20261118
python3 "$packet/recovery_capture.py" check
ROWFLOW_REPO="$PWD" python3 /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/publish_row.py "$packet/spec.json" --smoke-now
```

The [offline controls](offline-controls.txt) cover legacy and invalid grant identities, attempt isolation, failure filing and owned process-group cleanup. They run without any model launch.
