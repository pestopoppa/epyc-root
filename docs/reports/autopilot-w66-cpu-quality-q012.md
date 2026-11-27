# Real W66 continuation quality on q0–q2

Preserving history reproduced the cache benefit on a real W66 conversation. Its first follow-up returned output in 6.22 seconds versus 410.05 seconds with preservation disabled. The first requests carry identical messages, tools and sampling. Only their template kwargs differ. Neither bounded continuation produced an accepted repair, so this run leaves quality neutrality unresolved. [Paired input check and native results](../../artifacts/analysis/ap-w66-cpu-quality-q012/summary.json)

| Quantity | Preservation OFF | Preservation ON |
|---|---:|---:|
| First request fresh / cached tokens | 75,542 / 5,491 | 96 / 81,165 |
| First request native prefill seconds | 409.896 | 6.067 |
| First delivered output seconds | 410.049 | 6.221 |
| Completed/closed request receipts | 11 | 28 |
| Closed native generated-token counters | 1,788 | 5,622 |
| Sum native prefill / decode seconds | 471.90 / 118.67 | 190.00 / 396.24 |
| Working-window wall seconds including final checks | 602.15 | 601.71 |
| Final artifact | No edit | Partial allowed-file edit |
| Independent original tests | 1 failed, 1 passed | 1 failed, 1 passed |
| Accepted repairs | 0 | 0 |

The first-output reduction was 65.9×, saving 403.8 seconds. ON used the freed time for more work and produced an edit near its deadline. Its patch reads `self.pair.candidate.snapshot_digest` during startup, before `compare()` initializes `self.pair`. That raises AttributeError. The original hardcoded receipt assertion remains. The patch fails before runtime receipt verification and substitution testing. The independent grader preserves this result as a failed partial repair. [ON frozen patch](../../artifacts/analysis/ap-w66-cpu-quality-q012/preserve-on/followup.patch.gz) · [Independent grade](../../artifacts/analysis/ap-w66-cpu-quality-q012/preserve-on/independent-grade.json)

OFF retained the original failing fixture and produced no candidate for substitution testing. Both arms stayed within source scope. Empty OFF output means no repair was produced. The ON edit preserves the original nonreceipt assertions but fails to repair the fixture. The two arms each received one identical criterion-focused follow-up. No solution patch was supplied. [OFF grade](../../artifacts/analysis/ap-w66-cpu-quality-q012/preserve-off/independent-grade.json)

## Starting state and controls

An initial 15-minute common-sampler OpenCode attempt inspected the pinned W66 source and produced no edit. Its persisted session became a single frozen checkpoint. Each arm received an independent copy of that conversation and working tree. The recorded final request reconstructed each native cache, generating one discarded token. Reconstruction took 355.71 seconds OFF and 354.37 seconds ON. The working window started afterward. Each arm then received the same new user message, covering the original tests and exact receipt identity. Their first requests retain all 119 checkpoint messages unchanged and append that user message. This is a paired continuation from a shared inspection checkpoint.

The independent baseline reproduces exactly the intended W66 failure while the unchanged serial companion passes. A historical positive control passes both tests. Its qualified substitution control replaces the receipt with a valid same-content receipt having a different locator and digest, and the exact identity assertion rejects it. Grading uses private root/app scaffolds and the original isolation observer in separate network-isolated containers. [Control verdicts](../../artifacts/analysis/ap-w66-cpu-quality-q012/control-verdicts.json)

Two setup defects were repaired before the final paired continuation. Git's default grep thread count exceeded the sandbox PID headroom. Both worker and grader now set `grep.threads=1`. The timeout adapter assumed every successful API response had a `data` envelope. It now accepts wrapped, unwrapped and empty acknowledgements, with four deterministic controls. The initial unqualified setup and a greedy-sampler diagnostic remain excluded from the preservation comparison. Greedy sampling had carried over from the synthetic test. Final inference uses the previously qualified common sampler. The timeout failure preserved the initial session, which was recovered without repeating its inspection pass. The evidence archive retains setup failures and corrections separately. [Bound archive and sources](../../artifacts/analysis/ap-w66-cpu-quality-q012/README.md)

## Recipe and placement

Both arms use thinking OFF. The changed setting is `preserve_thinking`, with its native preservation alias. The CPU C22 build is `ce6fcbbde1ee58f165283fbfe74910f47bb2efba`, using A3B Q8_0, MTP D2, one split-KV slot, 131,072 context, f16 KV, 2,048 batch/microbatch, 72 threads and `--no-mmap`. Sampling is temperature 0.6, top-p 0.95, top-k 20, min-p 0, presence penalty 0, repeat penalty 1 and seed 223355. Each continuation had a 600-second wall bound and 16,000-token ceiling.

Stock OpenCode 2.2.5 supplied edit, write, shell, execute, read, grep, glob, question, skill, subagent, webfetch and websearch tools. The local case containers were network-isolated. No explicit execution-tool restriction was introduced. Tools and source availability were identical between arms.

The server and all worker/grader containers were confined to physical CPUs 0–71 and memory nodes 0–2. All 751 server thread-affinity samples stayed inside that CPU set. No server GPU residency appeared in KFD, and the loaded-library record contains no HIP library. The owned server exited with code zero and its PID was absent after cleanup. The runner removed its owned containers.

Closed wire receipts contain 9 OFF and 86 ON generated tokens from final interrupted requests that arrived after the terminal snapshots. The terminal values are 1,779/5,536 plus one unknown request each. Both original snapshots and later native counters are retained. The summary supplies native decode and end-to-end generated-token rates. One stream was active at a time, and no concurrent aggregate is inferred.

The original source regression remains unfixed by these two model attempts. This single checkpoint does not establish a broader quality effect or a model capability ceiling. It does establish that the template transition caused minutes of avoidable prompt processing in this CPU workload.

Next: RTG-02 retains AP-W66-PAIR for the GPU peer-interference comparison and a successful-artifact quality control.
