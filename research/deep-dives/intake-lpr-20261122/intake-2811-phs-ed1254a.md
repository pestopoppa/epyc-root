# Dive — intake-2811 (phs-ed1254a) — intake-lpr-20261122

Stage 1+2 combined dive (operator pre-authorised). External text quoted below is data, not instructions.

> SOURCE-QUARANTINE: {url: "https://github.com/philippesic/llama.cpp/commit/ed1254a209bb01e5eafbfdb4b054d5409831c120.diff", retrieved: "2026-11-22T11:44:21.614328Z", sha256: "a10d2c169832"}

# phs-ed1254a — philippesic/llama.cpp commit ed1254a (EOG stop in rejection sampling)
lane_head: 860023c79706f437cdc027d186dbd1ce998b372d

## 1. Stage-1 fields
- Title: stop accepting draft tokens after an EOG in rejection sampling (message per task text; commit message itself not in diff.txt). Author: philippesic (fork). State: downstream fork commit, unmerged to upstream as far as source shows (upstream status NOT-FOUND-IN-SOURCE); d7ae2f2 stated as same message (likely rebase). Categories: speculative_decoding. Novelty: low (extends #29638 to the rejection path). Relevance: medium-high: our rejection loop is served (dists path) and has no EOG stop. credibility_score: 1 = known contributor 0, recency +1, independent corroboration 0, commercial 0; includes a test, but rubric has no term. Verdict: adopt_patterns (3-line fix + test shape).

## 2. Key claims
1. Adds EOG break to common_sampler_sample_and_accept_n_rejection after an accepted draft token, only when it is not the last draft token. CONFIRMED. file diff.txt, locator "common/sampling.cpp @@ -803,6 +805,12", quote: `if (llama_vocab_is_eog(vocab, draft[i]) && i + 1 < draft.size()) {`.
2. Rationale: mirror common_sampler_sample_and_accept_n. CONFIRMED. quote: `stop at an EOG that is not the last draft token, same as common_sampler_sample_and_accept_n`.
3. Adds `const llama_vocab * vocab = llama_model_get_vocab(llama_get_model(ctx));` at function top. CONFIRMED. quote: `const llama_vocab * vocab = llama_model_get_vocab(llama_get_model(ctx));`.
4. Test test_speculative_rejection_eog added to tests/test-speculative-rejection-sampling.cpp: drafts of {eog,eog}->1, {eog,eog,eog}->1, {eog}->2 tokens (trailing EOG still followed by bonus). CONFIRMED. locator "tests/test-speculative-rejection-sampling.cpp @@ -163,6 +163,88". quote: `a trailing EOG is still accepted and followed by the bonus token, same as common_sampler_sample_and_accept_n`.
5. Exact diff vs #29638: the #29638 diff is not in this folder; per the pr29638 dive our plain loop lacks it and upstream merged #29638 (d280808) for the plain loop only. This commit is therefore the sibling for the rejection loop. Textual diff-to-diff comparison: NOT-FOUND-IN-SOURCE for this key (read /mnt/raid0/llm/tmp/dive-lpr-20261122/pr29638 for the plain-loop hunk).

## 3. Reported results: none in source (test only; no run output).

## 4. Performance principles: not a kernel change. Control-flow correctness. MI210: n/a (host sampler). Zen 5: n/a. Cost: one llama_vocab_is_eog lookup per accepted draft token.

## 5. In-house state and applicability (common/sampling.cpp @ eee3da8)
- Three accept loops, none with EOG stop: plain :708-710 (breaks only on mismatch), greedy-fast :928-930 (same), rejection with dists :960-1036 (accepted branch :991-1001 ends with `continue` at :1000). `git grep is_eog eee3da8 -- common/sampling.cpp`: zero hits.
- Does not apply textually: upstream function is named common_sampler_sample_and_accept_n_rejection with `uni(gsmpl->rng)` accept test and `draft_q`; ours is an overload of common_sampler_sample_and_accept_n (:944, :1054) with `dists`, `speculative_rng`, poskey RNG (u_acc, spec_pos from gsmpl->n_accepted) and out_dists capture. Hunk context (`result.reserve(idxs.size());` followed by blank + comment) does not match (ours :955-958 has no vocab line and different comment). The change is semantically portable by hand: add vocab at function top, and after the out_dists emplace at :995-998 insert `if (llama_vocab_is_eog(vocab, draft[i]) && i + 1 < draft.size()) break;` before `continue` (:1000). Break leaves i<draft.size(), so no bonus token (:1038), matching the intended semantics; trailing EOG (i+1==size) falls to the bonus sample as the test expects. Check order matters: break must come after out_dists capture so dists stay aligned with result.
- Test: our tree has no tests/test-speculative-rejection-sampling.cpp (ls-tree of tests/ at eee3da8 shows no rejection/spec test), so the test cannot be applied; it would be a new file based on the diff's kv_override trick (EOG=0 by tokenizer.ggml.eos_token_id override, logit_bias 1000, q={eog,0,1}).
- Is it reached in serving? The rejection/dists overload is the stochastic-verification path used when temperature>0 and a drafter provides dists (DFlash2 / MTP at sampled temp); greedy served rows use :928. A draft ending mid-sequence in EOG followed by more draft tokens: without the stop, accepted junk after EOG is appended to result and later trimmed by the server's EOG check; the harm is generating tokens past EOG into KV/timing counts and acceptance stats, not a different final text (server stops at first EOG in result). NOT verified in server code here.

## 6. Derived-actionables ledger
| Draft task | Owner | Type | Rule |
|---|---|---|---|
| Add EOG stop to the rejection loop (and plain :708 and greedy :928 loops, matching #29638) in llama.cpp-experimental, one feature per commit, plus a unit test | handoffs/active/speculative-decoding.md | code-only (unit test uses tiny model, no served compute) | Test passes {eog,eog}->1, {eog,eog,eog}->1, {eog}->2; verify poskey replay and non-EOG streams bit-identical (greedy KLD/accept replay unchanged) |
| Confirm server drops post-EOG accepted tokens and whether KV is over-advanced | handoffs/active/speculative-decoding.md | code reading, doc-only | If server already truncates at first EOG, severity = stats only |

## 7. Dive-surfaced sources
- philippesic d7ae2f2 (same-message sibling; likely rebase): decline, duplicate.
- Upstream #29638 already tracked (pr29638 folder). Whether the rejection-sampling upstream PR containing test-speculative-rejection-sampling.cpp is itself in intake_index.yaml: not grepped for this key beyond ed1254a/30252/huge-pages (no hits); recommend checking which upstream PR introduced that test file and ingest-and-dive it if absent.

## 8. Contradiction / adversarial pass
- No reviewer comments exist (commit view). Edge: the break uses i+1<draft.size(), so EOG as last draft token goes to the bonus sample (consistent with the plain function). Risk in our version: spec_pos is derived from gsmpl->n_accepted; breaking after accept leaves n_accepted consistent (accept called before break).

## 9. read_depth: FULL (diff.txt/diff.raw); our code read at :700-720, :920-1040 @ eee3da8. lane_head: 860023c79706f437cdc027d186dbd1ce998b372d
## 10. artifact audit line: artifact audit: clean (no meta.json for this key)
