# KPF-61 third smoke probability review

Aggregate-only review of the retained third publisher smoke. The analysis script reads the two raw response JSON files but prints only counts, equality flags, selected-logprob aggregates, source hashes, and scope/limitations. It does not print prompts, response content, or token strings.

## Bound inputs

- Capsule: `/mnt/raid0/llm/worktrees/mains/h-heterogeneous-slot-fabric-residency/docs/reports/kv-cache/kpf61-third-smoke-20261104/SUMMARY.json`
- Retained attempt directory: `/mnt/raid0/llm/tmp/kvfork/kpf61-cpu-permutation-20261104/out/attempts/e4dfd06df16f49258ee5bdf2ab52c0e8`
- `0-cold-test.response.json`: SHA-256 `84a66e5b0a52b4ab911201c026d5ec8dea5ed33460a06e1f41d5778207f0ede2`
- `0-reorder-test.response.json`: SHA-256 `d51f129c8aaa37092e7169039ac167808000b08123f7314e392e22b7215950af`

`analyze.py` checks each actual digest against both its embedded expected digest and the corresponding capsule `native_file_hashes` entry; it exits if either binding fails.

## Aggregate finding

Both responses have 32 output token IDs and the arrays match. Both have 32 completion-probability rows, and every row in both responses contains exactly 32 `top_logprobs` entries (asserted by the analyzer). Selected token IDs match on every row, while selected-token logprobs differ on all 32. The absolute selected-logprob delta spans `0.00015679001808166504` to `0.04168844223022461`. At row 0, selected token ID 286 has logprob `-3.7098066806793213` (cold) and `-3.7433578968048096` (reorder). The top-32 candidate ID sets differ on 25 rows; top-32 ID ordering differs on all 32.

These are retained probability-row mismatches, not output-token mismatches. The review applies no numerical tolerance and does not compare full logits. It cannot identify the cause or establish a 35B result or full KPF-61 gate verdict. Scope remains the one Qwen3.5-0.8B public-control CPU publisher smoke recorded in the capsule.

## Reproduce

From any working directory, run:

```bash
python3 docs/reports/kv-cache/kpf61-probability-readout-20261104/analyze.py
```

The aggregate JSON in `aggregate-report.json` is the captured output for these retained inputs. Optional `--attempt-dir` and `--capsule` arguments allow an alternate location, but the hard-coded expected digests remain required.

The raw response paths are scratch locators and may be reclaimed; the committed capsule retains their hashes, not the response payloads. Reproduction requires those matching files. [Source provenance review](source-provenance.md) distinguishes a separate dirty worktree at the same commit.
