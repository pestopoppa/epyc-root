# Upfront comparator checkpoint continuation — 2026-11-19

D-RI-PREVIEW-1.2 continuation row: `dripreview15-resume-20261119`.
This resumes `dripreview15-upfront-20261119`; it creates no new experimental arm.

Native checkpoints remain in place at
`/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview15-upfront-out-20261119/cells/`.
Each rendering has five retained records with native indices 0–4. No copied cells,
renumbering, discarded prefix or model-accuracy verdict.

The unmodified bound driver skips completed indices and interleaves missing ones.
The original fixture, model, temperature, token/turn limits and contract binding
remain fixed. Original n=10/20 futility looks and n=30 cap remain fixed; separation
requires full-n gap >=0.30 and exact two-sided McNemar p<0.05/3. Partial hard ends
remain inconclusive. D-RI-PREVIEW-1.2 remains open pending a separating fixture or
an explicit unseparable verdict.

The continuation checks the original byte-prefix hashes, contiguous indices,
every record binding and n<=30 before running. Seven synthetic validator cases
passed: original prefix, valid append, changed prefix, gap, wrong binding,
truncated line and cap overflow. Native records were untouched by these tests.
Shell syntax and source-manifest preconditions passed.

Booking is resumable: minimum window 5400 s, maximum 10800 s, remaining estimate
72000 s. The minimum excludes the observed approximately 74-minute interrupted
windows. Estimate is a planning assumption of 75 remaining cell-episodes at 900 s
plus margin, not a measured timing claim. Completed episodes checkpoint immediately;
an interrupted active episode can replay. No gate rule changes.

Operational scripts and spec:
`/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview15-resume-20261119/`.
The retained original sibling wrappers and frozen PREDECLARED.md are referenced
in place and verified by the continuation source manifest. New native summary:
`dripreview15-resume-20261119/out/result.json` under the same scratch parent.
Row result stream: `dripreview15-resume-20261119/out/results.jsonl`.

SHA-256 bindings (existing files):

- Original `cells/worker_general__bounded_k3.jsonl` prefix: `0fc69fbc04452a18252d640ead11cedc9b4d5ade1e2b117a3c15030bb5a3f3b9`.
- Original `cells/worker_general__current.jsonl` prefix: `24db64008dcffa9b1512e71ca8d5042169e8832368890167a41799d2918fb8ff`.
- Original `cells/worker_general__half_first25.jsonl` prefix: `c820415dea601ba6f7c5e3b4974612b5606b71b84ffe496d6d39903d8f67b046`.
- Continuation `SOURCE.sha256`: `efe3a93cea82505507a7952da51a686bb60b77fffd3734124b3bcf96569e7e2b`.
- Continuation `checkpoint.json`: `2427a66c0ca9f4c43d9cad1b37b1697adb7d47b6d99e925516d01d72b90fc1a1`.
- Continuation `launch.sh`: `eb2ceb63e1d677cf008047e93996010dfb0ec930ac0c35207e47e2fa776ff656`.
- Continuation `job.sh`: `dcd0da9eb0cdd98a383a7f27168e9374cf37a5c427fe7897f84cef6f3ab36d88`.
- Continuation `precond.sh`: `036aa1cb65cfbd2889787ebd1b5682c10ce4200d2ce5ede855d025e58a69c8d7`.
- Continuation `verify_checkpoint.py`: `40a9e631059ab017e69e4af7a15f15d96239cd8486354cffc51706f6b1c44d14`.
- Continuation `CONTINUATION.md`: `73a99cd109c00afee651335977352b09fe944786fb5bb44e0e30c2d2404a84ff`.


GitNexus status and upstream impact are unavailable because this lane has no
index. Static scope: scratch launch scripts and checkpoint admission, no production
application/kernel edits. Existing prospective VB-REPL-COMPOSITE-WRITE covers the
unchanged native result schema; smoke supplies plumbing evidence only.

Publication: `publish_row.py --smoke-now` reported **SMOKE PASS** on CPUs
116–119 at 2026-11-19T23:34:01Z, smoke predicate exited 0, clean partial-native
rc=75. Row PUBLISHED with window/book 10800 s, minimum 5400 s and
resumable=true. This is plumbing acceptance, with no scored-cell finding.
