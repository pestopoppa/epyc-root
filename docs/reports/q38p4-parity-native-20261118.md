# Q38P-4 native greedy parity and planning context

Run `q38p4-greedy-parity-20261118-r2` completed one native comparison on MI210_0. The two engines accepted the same fixed 512-token input and each returned 128 output tokens. The first difference was at zero-based index 37, where C6 llama.cpp returned token `18266` and vLLM returned `4628`. The engines reported native stops `limit` and `length`, respectively, both normalized to `length`. The capture was accepted and the owner filed a failed parity verdict for this one pair. [Native result](../../data/vidya/parity-native-filed-20261118/official/RESULT.json) · [Owner verdict](../../data/vidya/parity-native-filed-20261118/q38p4-greedy-parity-20261118-r2.verdict.json)

The comparison used the Qwen3-4B-Instruct-2507 BF16 proxy, with an HF model for vLLM 0.33.0 ROCm and a C6 `729599d69871181d67af715a4c2f9162d5153a2e` BF16 GGUF conversion for llama.cpp. The exclusive grant covered MI210_0 and CPUs 184–191 from 19:21 to 19:35 UTC. The two requests ran sequentially and returned HTTP 200. The seal replays nine owned llama.cpp and five owned vLLM in-request GPU samples with mapped HIP linkage. The captured process and listener cleanup checks passed for both arms. The comparison concerns the native output tokens and stops for this input and runtime pair. Its scope is a finite correctness diagnostic. [Native plan](../../data/vidya/parity-native-filed-20261118/official/capture/plan.json) · [Capture seal](../../data/vidya/parity-native-filed-20261118/official/capture/q38p4-greedy-parity.json)

## Planning-context canary

The registered `q38p4-greedy-parity` ingest projected one row into three verified scratch-ledger frames from the original seal and again from its filed copy. The current shared reader presented `q38p4_greedy_divergence: 1 comparisons (n=1)` at target tier to `autokernel.planner` for the exact source commit, canonical plan digest, operator and run ID. The shared grade was `Judged/Located`. The support frame carried `outcome_native=divergence`. The claim is `clm_q38p4-greedy-parity:d044c1613217f0fceeec6265080d323e8bb67d3e709b0b71661bbd91b21ba03f`. [Filed canary receipt](../../data/vidya/parity-native-filed-20261118/planning-canary.json)

The reader returned zero applicable claims for a changed vLLM runtime digest, a different valid run ID, an ordinary GPU model target with the same GGUF filename, and the AutoPilot production lineup. Every read used the same verified scratch ledger. The canary stopped at context assembly and preserved the capture and ledger bytes. This evidence establishes candidate-specific diagnostic wiring. Performance, model quality, broader parity and promotion are outside the comparison's scope.

## Replay

From the repository root, verify the public source and retained-file manifests, then run the canary against the original private capture in a new scratch directory. Eight original socket/container/map files remain private after the PII gate flagged account-number-shaped values; their digests and private locations are retained in [PRIVATE-EVIDENCE.json](../../data/vidya/parity-native-filed-20261118/PRIVATE-EVIDENCE.json). Public capture copies are intentionally incomplete. The canary needs those original private bytes and a current shared reader checkout; model files and runtime binaries are unnecessary for replay.

```bash
packet=data/vidya/parity-native-filed-20261118
(cd "$packet" && sha256sum -c SOURCE.sha256 && sha256sum -c PUBLIC.sha256)

scratch=$(mktemp -d /mnt/raid0/llm/tmp/q38p4-planning-replay.XXXXXX)
python3 -B scripts/vidya/canary/q38p4_parity_context.py \
  /mnt/raid0/llm/tmp/vidya-belief-substrate/parity-native-20261118-r2/official/capture/q38p4-greedy-parity.json "$scratch/read"
```

Success writes `read/receipt.json` and the individual planning answers. The seal file SHA-256 is `b49fcbe37faae7a54c54a1671bd2534c06220d0c7627c9f6ed356a5f42142234`. The exact candidate's rendered context SHA-256 is `8a2b109bac78718530e2dc34dec4bd1d9080fa1db132075545f78204aa592a97` at the receipt's recorded cutoff. [Source manifest](../../data/vidya/parity-native-filed-20261118/SOURCE.sha256) · [Capture manifest](../../data/vidya/parity-native-filed-20261118/CAPTURE.sha256)
