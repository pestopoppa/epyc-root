# Local prefix-rewrite pricing diagnostic

Question: on the pinned frontdoor CPU build, how much native prefill and
request latency does replacing a warm prefix cost, and can later request
savings repay that cost? This is CF-PB-1's local cost input. It does not
adopt a plan-boundary trigger or test answer quality.

Run Qwen3.6-35B-A3B-MTP Q8_0 with production-consolidated-v10
`ffc1bac82eeca6f9099e1ccd9ba49703c460a115` (build 10303; retained CPU
binary/library/model proof), four allocator-assigned physical cores,
private port 19386, split Q8 KV and the existing four-slot/65,536-token
recipe. Pin orchestrator `12afe2858f9dbd4691447926d6cf1864de64348c` for
listener ownership proof. All native completions explicitly use slot 0.
No reload, source-tree build or production-flag change occurs.

Two original prefix sizes, 1,024 and 4,096 native token ids, each pair with
a quarter-length replacement, run for three fixed repetitions. Token ids
100–125 are pre-encoded synthetic inputs, not tokenized document text.
The replacement's first token differs, forcing cache invalidation. Each
path first primes the original prefix with caching disabled, then sends
four growing requests with 32 additional token ids per step and caching
enabled. The retain path preserves the full old prefix; the rewrite path
replaces it on step one and preserves the replacement thereafter. Path
order alternates by repetition. Fixed greedy one-token completions with
EOS ignored and a fixed ASCII `x` grammar bound generation cost; this workload is intentionally distinct
from ordinary variable-length assistant answers.

Require native `timings.cache_n + timings.prompt_n == tokens_evaluated ==
submitted token count`, exactly one generated token and slot 0. Every
warm request must show positive reuse; each prime and first rewrite must
show zero reuse. Record exact native requests/responses, separate cached
and processed tokens, prompt/decode ms, client wall ms, runtime ownership,
loaded-library maps, source/build/model receipt, schedule and file hashes.
Do not equate `tokens_cached` (final slot occupancy) with reused tokens.

For each pair, rewrite overhead is first rewrite cost minus first retain
cost. Later savings are the mean of retain minus rewrite costs on steps
2–4. Report measured four-request total delta. If later savings are
positive, report the point extrapolation
`1 + ceil(max(0, overhead) / later_savings)` requests; otherwise report no
finite extrapolation. Compute separate native prompt+decode and client-wall
versions. Do not substitute SoL-Pi's 12.5 cache ratio. Summary-generation
cost is excluded and would have to be added before adoption; rewriting is
represented by a supplied shorter prefix, not a quality-preserving summary.
The current source's character-length OR-trigger is unchanged, and no step
progress or production summary request is changed by this diagnostic.

Expected signal: shorter-prefix cold prefill adds work at rewrite time;
reused shorter histories may reduce later latency. Timing noise may exceed
the later savings on four cores. Three replicates describe diagnostic
variation only; report each pair and its observed spread, and leave
non-positive savings unresolved rather than adding samples after seeing
results. There is no hypothesis gate or precision claim.

Stop-on-answer after six pairs. Stop-on-futility at the first cache/custody,
HTTP or native-accounting failure, allocator STOP/deadline, or 1,800 seconds;
retain partial records, with no retries/replacements. Gate class is
futility-only. Coverage predicate `completed == 6 and cache_witness_valid
== 1` establishes instrument completion, never trigger adoption. The native
publisher smoke uses one 32-token pair and two follow-ups with four-token
growth, exercising real cold, warm and invalidated-prefix behavior without
running the official matrix. Server termination must be confirmed.

Project these records through the existing `toc_ab` source family and its
shared grading ladder. Bind the immutable inputs and cache witnesses at
write time; the source registration extends `VB-CF3C-POLICY-WIRE` and does
not claim a passing planning-context canary.

Qualification repair: the first smoke stopped with HTTP 500 on an invalid
partial-byte one-token output. Preserve its native PARTIAL/log by path and
SHA-256 in `qualification-history.json`; grammar constrains output to ASCII
without changing prompt/cache geometry or the official schedule. No official
pair ran. Requalification is separate from the six-pair diagnostic.
