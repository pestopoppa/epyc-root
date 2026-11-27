# C22 pinned-slot RAM prompt cache incident

C22 restored a cached prompt into a busy GPU slot while handling a second request pinned to it. The first request stopped advancing after 426 new prompt tokens. The same checkpoint position was then evicted 304 times. Sibling requests continued slowly while the GPU waited between batches.

The failing run was `quality-runs/repaired-01` with whole-host CPU and four C22 slots on each device. Its executable identified itself as version 10748 from source `ce6fcbbde1ee58f165283fbfe74910f47bb2efba`. The launch record captured the executable and the mapped common and server implementation libraries during actual serving. Their current bytes match the launch digest manifest. The mapped implementation contains the observed copy-load diagnostic and the mapped common library contains the supported `--cache-ram` option. [Binary and library proof](INCIDENT-BINARY-PROOF.json)

## Breakpoint and mechanism

- At server time 12:54.211, slot 0 admitted task 2286 and its next batch processed 426 prompt tokens. At 12:54.469 a second request selected explicit slot 0 even though task 2286 remained active. At 12:54.495 C22 reported a RAM cache copy-load with longest common prefix 5,495 from an entry of 91,398 tokens. [Exact log lines](INCIDENT-GPU-LOG-EXCERPT.txt)
- The pinned source selects the explicit slot before checking its availability. The similarity loop skips processing slots, leaving a zero keep fraction for the explicit busy slot. This triggers `prompt_save` and `prompt_load` in `get_available_slot` before the task dispatcher checks `is_processing()` and defers the second request. The RAM copy-load writes target and draft state and assigns cached prompt tokens and checkpoints on the selected slot. [Pinned source extracts with Git blob and content digests](C22-SOURCE-EXCERPTS.txt)
- The active task subsequently logged a progress value of 71.91. The source prints a raw ratio of cached-plus-processed prompt length to request length. The 91,398-token state was therefore about 72 times the active request length. The fill loop requires fewer cached tokens than the requested total, while its completion predicate requires equality. The overfull prompt met neither predicate. Repeated near-end checkpointing explains the identical eviction warnings. The zero prefill budget in the log means the batch uses its configured limit. [Log excerpt](INCIDENT-GPU-LOG-EXCERPT.txt) · [Pinned source extracts](C22-SOURCE-EXCERPTS.txt)

## Observation windows

The windows use retained two-second resource samples and the existing decode counters for the same two in-flight sibling requests. Server-relative resource alignment is approximate and is used only to choose windows away from the breakpoint.

| Observation | Before the copy-load | After the copy-load |
|---|---:|---:|
| Resource window | 8 samples over 14.06 s | 45 samples over 88.10 s |
| Sampled GPU busy | 85–99% on 7 of 8 samples | 0% on 44 of 45 samples |
| CPU server core equivalents | 94.87 | 94.79 |
| Slot 2 median rolling decode | 27.785 tokens/s, n=6 | 0.85 tokens/s, n=19 |
| Slot 3 median rolling decode | 30.83 tokens/s, n=6 | 0.87 tokens/s, n=19 |

The CPU server competed for control cores throughout. The stable CPU activity and sharp same-request change at the copy-load locate the failure in the serving state transition. The samples support a within-run incident diagnosis. The completed PAW thinking result predates the breakpoint. The stalled request and sibling outcomes exposed to this slowdown are serving-confounded. [Raw selected resource rows and exact decode log observations](INCIDENT-WINDOWS.json)

## Cache-safe qualification and early replay

V4 gives both C22 servers explicit `--cache-ram 0` and serializes all upstream sends to each physical slot through the adapter. The slot queue observes the case deadline and cancellation. C22 keeps ordinary in-slot KV reuse. In the native cold-load control all eight slots processed 6,294 cold prompt tokens, completed the title queued behind a long request, reused 6,290 prompt tokens on a repeated long request, and then completed the short request. The qualification contains the owned cleanup receipt. [Native control receipt](NATIVE-CONTROL-RECEIPT.json)

The single read-only early replay snapshot bound both active server PIDs to `--cache-ram 0`. The captured CPU and GPU logs had zero RAM copy-load entries and recorded that the cache-idle-slot feature required the disabled cache. In the 28.09-second active window the GPU reported 100% busy on 9 of 15 samples and 3% on one sample. Native decode counts advanced on all four GPU slots during the captured run. This describes only the sampled early replay window. [Captured live observation](CACHE-SAFE-EARLY-OBSERVATION.json)

[Capture script](capture.py) · [Artifact SHA-256 checksums](SHA256SUMS)
