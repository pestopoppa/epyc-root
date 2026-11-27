# W66 light serving attribution

Both 70-request modes reconcile to their original worker and native timing totals. The largest single prefill was OFF 56, which took 138.240 seconds for 107,912 fresh tokens. The largest decode was ON 28, which took 164.585 seconds for 1,029 tokens. The native log shows the two phases running together. The closest published A3B benchmark used short, uncached prompts and reached its A/A futility threshold. These observations support testing prefix reuse and interference separately before judging the kernel. [Pinned replay plan](autopilot-w66-replay-plan.md)

## Denominators

The analysis matched 140 distinct wire receipt hashes and exported fields against the CSV at `06b010e1361768b7d1d65b83cb4428df28a0d1c3`. A unique match on slot, fresh and generated token counts, and both native timers tied every receipt to a server task. The native log prints durations to 0.01 ms. Where a digest or a join differs, the analyzer fails. All 140 receipts completed with HTTP 200. There were zero cancellations, transport/server errors or post-terminal receipts. Generated, fresh, cached and paired MTP counters are present for all 140. The native reasoning-token split is unknown for all 140. [Reconciliation CSV](../../artifacts/analysis/ap-w66-trace/requests.csv) · [Summary and source digests](../../artifacts/analysis/ap-w66-trace/summary.json)

| Quantity | OFF | ON |
| --- | ---: | ---: |
| Generated tokens | 14,111 | 23,599 |
| Fresh / cached prompt tokens | 226,495 / 4,827,393 | 93,346 / 5,133,330 |
| Paired MTP accepts / proposals | 8,952 / 10,242 (87.4%) | 14,413 / 18,302 (78.8%) |
| Worker wall seconds | 1,133.295 | 1,511.037 |
| Sum of native prefill seconds | 408.547 | 299.837 |
| Sum of native decode seconds | 534.873 | 1,054.300 |
| Generated tokens per worker wall second | 12.45 | 15.62 |
| Generated tokens per summed native decode second | 26.38 | 22.38 |
| Median per-request native decode tok/s | 48.68 | 43.50 |
| Forwarded request wall union, seconds | 1,095.338 | 1,489.506 |
| Timed tool execution union, seconds | 28.046 (73 intervals) | 12.421 (80 intervals) |
| Worker wall less summed native timers, seconds | 189.876 | 156.900 |

The 35 slower-than-median receipts account for 409.508 of OFF's decode seconds (76.6%) and 927.293 of ON's (88.0%). ON generated 67.2% more tokens, used 33.3% more worker wall time and spent 97.1% more native decode time. In the combined two-slot history, the estimated native phase union is 673.692 prefill seconds (474.76 fresh tok/s) and 1,254.798 decode seconds (30.05 generated tok/s). The unions count simultaneous same-phase seconds once using durations right-aligned to server decode completion. The two phase unions can intersect where decode and prefill share a batch. The worker residual includes time before native execution and after native timers, tool time, and unclassified client or harness time. The OpenCode tool intervals use the recorded ran-to-completed timestamps, including intervals that overlap other calls. The tool union overlaps forwarded request windows by 0.053/0.018 seconds for OFF/ON. [Timing summary](../../artifacts/analysis/ap-w66-trace/summary.json)

## Request tails and history

| Target (native task) | Fresh / cached | Prefill / decode seconds | Generated | Decode tok/s | MTP accepts / proposals | Peer prefill during decode, estimated seconds | Prior request and retained tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| OFF 52 (7731) | 512 / 108,476 | 5.750 / 19.418 | 949 | 48.87 | 608 / 680 | 0.000 | OFF 51, 108,476 |
| OFF 56 (8360) | 107,912 / 4,334 | 138.240 / 46.869 | 1,074 | 22.91 | 659 / 830 | 15.322 | OFF 55, 110,845 |
| ON 28 (8195) | 38 / 75,077 | 16.861 / 164.585 | 1,029 | 6.25 | 648 / 760 | 141.921 | ON 27, 75,077 |
| ON 29 (8582) | 38 / 76,143 | 4.195 / 1.769 | 77 | 43.52 | 49 / 54 | 0.000 | ON 28, 76,143 |

OFF 56 consumed 33.8% of all OFF prefill seconds. ON 28 consumed 15.6% of all ON decode seconds despite accepting 85.3% of its MTP proposals. Native log lines 2532–2725 show OFF 56's prefill and batches with one prefill slot and one decode slot while ON 28's decode advanced slowly. The estimated interval join places 138.240 seconds of OFF 56 prefill within ON 28 decode. In the last three-second progress windows surrounding OFF 56's final prefill batch, ON 28 moves from 0.77 tok/s to 46.61 and then 53.26. Both tasks are still active after the transition. The sequence localizes the slowdown to mixed prefill/decode, with possible contributions from the kernel, scheduler and shared host resources. During both requests, all retained sample windows had the bound GPU process present, with at least 53.55 GB VRAM and 93/94 samples for OFF 56/ON 28. The samples lack per-request occupancy. [Server events, peers and resource receipts](../../artifacts/analysis/ap-w66-trace/replay-manifest.json)

The CSV ranks all receipts by native phase seconds and combined native seconds. OFF 56 and ON 28 are first and second in combined native seconds (185.109 and 181.445), followed by ON 27 (107.735) and ON 20 (104.367). It also ranks descriptive excess over same-mode, same-sampler, same-template, same tool-count and finish-class peers. Prompt depth is within ±10%, fresh tokens within a factor of two after flooring both at 64, and generated length within the greater of ±50% or 64 tokens. At least two peers are required. Prefill uses their median observed seconds. Decode scales each peer's seconds per token to the target's output length before taking the median. Peer batch occupancy, request content and exact cache state vary. The leading prefill excesses are OFF 33 (+13.106 s) and ON 27 (+10.925 s); the leading decode excesses are ON 20 (+40.546 s) and OFF 37 (+37.694 s). Controls exist for 39 OFF and 37 ON requests. There are no qualified controls for OFF 56 or ON 28, so their excesses are unknown and their observed durations remain ranked. These excesses provide candidates for controlled replay. [Per-request ranks and control sequences](../../artifacts/analysis/ap-w66-trace/requests.csv)

Both units' first requests had zero cached tokens following recorded slot erases. The manifest binds 51, 55, 27 and 28 ordered predecessors for OFF 52, OFF 56, ON 28 and ON 29. The immediate predecessor's entire message list (106, 114, 58 and 60 messages, respectively) remains identical on the wire at the start of each target's message list. OFF 56 added three messages, including a user message, and went from 110,845 retained tokens in the preceding native release record to 4,334 reused. Wire message equality does not establish rendered token or recurrent checkpoint identity. The logs and bodies do not prove what caused the loss. The retained slot-save directory is empty, and the exact live KV, draft, and checkpoint state at each target remains unknown. [Hashed bodies and predecessor plans](../../artifacts/analysis/ap-w66-trace/replay-manifest.json)

## Why the OFF 56 prompt lost its prefix

We passed the two original request bodies through the C22 server's OpenAI-compatible formatter and the model's vocabulary. The probe loads vocabulary only. The rendered prompt lengths, 110,761 tokens for OFF 55 and 112,246 for OFF 56, agree exactly with their wire totals. All 114 prior message objects carry over. Only 5,962 leading tokens survive formatting. The template changes how it writes previous assistant turns when a new user turn arrives. The server reused 4,334 tokens, leaving a further 1,628-token difference within that common prefix. The saved evidence does not locate its cause. [Control receipt and build identities](../../artifacts/analysis/ap-w66-replay-inputs/native-prefix.json)

Two offline controls each recovered all 110,761 leading tokens. Removing the newly appended user message isolates the transition. Keeping the message and setting `preserve_thinking=true` consistently on both requests preserves the prefix while changing the next rendered prompt length to 112,462. The second control gives the live comparison a specific treatment. It changes template semantics, so verify output quality and actual cache reuse before treating it as a speed improvement, especially on thinking-on work. Neither control measured elapsed savings. [C22 vocabulary-only probe](../../scripts/autopilot_replay/w66_prefix.cpp)

## Benchmark comparison

The C22 S5-r2 A3B GPU row is the closest available configuration comparison. Source-built C22 matches W66 at `ce6fcbbde1ee58f165283fbfe74910f47bb2efba`. The comparison arms were production v10 `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`, C21 `98ff8a42a00ce816522fc913bbcfc414fe850d54`, and C22. S5-r2 scored four blocks before A/A futility at 1.0284 against a 2% guard. Its paired C22/v10 ratio was 0.9662 [0.9313, 1.0024]. The C22 arm's scored mean was 131.39 tok/s. Across all 20 captured C22 sequential visit requests the weighted native rate was 130.36 tok/s, and across eight separate four-stream report-only load requests it was 57.15 tok/s. The latter uses summed stream decode seconds for comparability with W66's weighted rate. [Hashed S5-r2 receipts and rates](../../artifacts/analysis/ap-w66-trace/summary.json) · [Campaign record](../../progress/2026-11/2026-11-26-autokernel.md)

| Setting | W66 light | Closest S5-r2 A3B GPU | S1-r2 GPU result |
| --- | --- | --- | --- |
| Kernel | C22 | v10/C21/C22 | v10/C21/C22 |
| GPU / threads | MI210, 8/8, ROCm0 | MI210, 8/8, ROCm0 | MI210, 8, ROCm0 |
| Target weights | Qwen3.6-35B-A3B-MTP Q8_0 | Same model/quant | Qwen3.8-27B Q8_0 |
| Active vs configured slots | Two W66 slots with mixed-phase overlap, four configured | One at a time for scored visits, four concurrent for load, four configured | One at a time for scored visits, separate four-configured-slot load unit with three prompts |
| Prompt and configured depth | 925–112,246 total wire prompt tokens, 131,072 per slot | 907–1,458 fresh prose tokens, 4,096 per slot | 7,939–8,640 fresh prose tokens, 393,216 configured context with unified KV |
| KV and batching | f16 K/V, separate slot KV, cross-slot RAM cache disabled, batch/ubatch 2,048 | f16 K/V, `cache_prompt=false`, no explicit unified-KV or RAM-cache flag, batch/ubatch 2,048 | q8_0 K/V, unified, `cache_prompt=false`, batch/ubatch 512 |
| Sampler and reasoning | Main requests T=0.6, top_p=.95, top_k=20, min_p=0, repeat=1, presence=0, seed 223355, thinking ON/OFF with metadata requests distinguished | Greedy T=0, top_k=1, prompt-indexed seed, ignore EOS, reasoning off | Greedy T=0, top_k=1, prompt-indexed seed, ignore EOS |
| Generation | 9–2,069 tokens, tool calls or normal stop | Fixed 256 tokens | Fixed 256 tokens |
| Speculation | Self-MTP D=2 | Self-MTP D=2 | Separate Q8_0 DFlash2 draft, D=7 |

S1-r2 is the source of the cited near-50% 27B gain. Its weighted C22 sequential decode was 68.75 tok/s and its separate load control was 10.52 tok/s per summed decode second. The 27B model, DFlash recipe, KV, short benchmark versus tool-session state and occupancy all differ. Neither benchmark supplies matched excess seconds for W66. [Hashed S1-r2 receipts](../../artifacts/analysis/ap-w66-trace/summary.json) · [27B and A3B scope](../../progress/2026-11/2026-11-26-autokernel.md)

## Controlled comparisons this evidence supports

1. For ON 28, rebuild predecessor state independently for each arm, compare isolated decode with a peer that is prefilling an OFF 56-like prompt on the other slot, and verify the window overlaps. Replay ON 29 and OFF 52 when the peer is decoding to separate ordinary multi-stream cost from prefill overlap. Bind the target's sampler, slot, role, template, device, affinity and loaded binary/libraries. Preserve observed fresh/cached counts and MTP acceptance, which may change with the batch.
2. For OFF 56, compare a controlled warm prefix against an erased slot at the same isolated occupancy. Observe actual fresh/cached counts and rendered prefix identity. The historical 110,845-token release and 4,334-token reuse are the check for reproducing the original transition. Label a matched controlled reconstruction separately whenever the original transition or state fails to reproduce. Rebuild independently before both arms. Reasoning histories and tool results arrive as saved inputs; generated tool calls stay inert.
3. Compare each target with itself. The exemplars include outputs of 77 and 1,074 tokens, and paired arms can also diverge in length. Save full counters and end reasons. Add a fixed-length decode control when divergence obscures the serving comparison. Slow decoding in matched, isolated, long-context states would support a direct kernel/recipe comparison. A repeatable slowdown confined to peer prefill supports an admission or batching experiment. Keep native seconds and actual task wall recoverability separate. Apply the replay plan's pair limits, reversals and stop criterion. [Controlled replay protocol](autopilot-w66-replay-plan.md)

## Reproduce offline

From a root checkout containing the replay input JSON and commit `06b010e1361768b7d1d65b83cb4428df28a0d1c3`, run the following on the EPYC host. The input JSON names the two retained wire ledgers and body directories. The replay manifest and summary name the retained runtime logs, OpenCode sessions, worker receipts, benchmark results and filing receipts with SHA-256 digests. Requests remain on the host. Repository artifacts carry hashes, numeric timings, structural metadata and source pointers.

```bash
out="$(mktemp -d)"
python3 scripts/autopilot_replay/w66_trace.py --output "$out"
(cd "$out" && sha256sum -c SHA256SUMS)
diff -r artifacts/analysis/ap-w66-trace "$out"
```

The prefix probe uses source headers from the recorded C22 commit and links the recorded GPU build's chat parser and tokenizer. It creates no inference context. To reproduce the comparison, point `wire` at the OFF unit's wire directory in the replay manifest and run the following from the root checkout.

```bash
headers=$(mktemp -d)
c22=/mnt/raid0/llm/kernels/builds/gpu-20261126-ce6fcbbde-c22-composite/bin
model=/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf
wire=$(python3 -c 'import json,pathlib; m=json.load(open("artifacts/analysis/ap-w66-replay-inputs/requests.json")); print(pathlib.Path(next(r["wire_receipt_path"] for r in m["requests"] if r["seq"]=="56")).parent)')
git -C /workspace/repos/epyc-llama archive ce6fcbbde common include ggml/include vendor tools/server/server-common.h tools/mtmd/mtmd.h | tar -x -C "$headers"
export LD_LIBRARY_PATH="$c22:/opt/rocm/lib"
g++ -std=c++17 scripts/autopilot_replay/w66_prefix.cpp -I"$headers/tools/server" -I"$headers/tools/mtmd" -I"$headers/common" -I"$headers/include" -I"$headers/ggml/include" -I"$headers/vendor" -L"$c22" -Wl,-rpath-link,"$c22" -lllama-server-impl -lllama-common -lllama -lggml -lggml-base -o "$headers/w66_prefix"
"$headers/w66_prefix" "$model" <(gzip -dc "$wire"/*-0055.json.gz) <(gzip -dc "$wire"/*-0056.json.gz)
```

Next: AP-W66-PAIR owner uses the sealed predecessor and peer inputs when live replay is authorized.
