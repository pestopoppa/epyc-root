Candidate manifest preparation, 2026-11-04
=========================================

`candidate_manifest.py` specifies a 40-case candidate from the original 500-row
SWE-bench Verified JSON pinned to SHA-256
`b087b5dad72b3e765a6cf93a9e7d516d8796698a0fd358abb73c6627df19f66e`.
The only selection input is instance identity: sort by SHA-256 of UTF-8
`epyc-p5-candidate-swe-verified-40-v1` + NUL + instance ID, breaking ties by ID,
and take the first 40. Forty is a bounded instrument-review candidate, consistent
with the existing SWE-40 scale; it is not a power calculation or an approval of
the eventual experiment. No outcomes, difficulty, repository, or successful
scorer execution enter selection. No model or scorer is called.

The generated `questions.json` contains only ID, repository, base commit, and
the source problem statement as prompt. `manifest.eval-only.json` contains
source-row, question, gold-patch and test-patch hashes, plus base/repository and
explicit FAIL_TO_PASS/PASS_TO_PASS identities. The latter file is for evaluation
review only and must never be supplied to a model. Solution patches, test
patches and hints are never copied into questions. Source problem statements
are retained verbatim; the allowlist is not a semantic review of their contents.

Freeze creates a new directory exclusively, writes deterministic JSON and
`SHA256SUMS`, and makes each output file mode 0444. Verification reconstructs
all artifacts from the pinned original and compares exact bytes. The tool
refuses to overwrite a directory or silently repin changed source bytes.
These are content pins, not a tamper-proof filesystem boundary. Approval,
broader scorer validation, source-control capture and exposure authorization
remain separate; P5-2 remains open.

**Current status: candidate frozen and source-verified; not approved.** Three
targeted tests passed, then freeze and verification passed under one fresh
build claim on CPUs 48–51, timeout one second. The frozen artifacts and native
verification JSON are in `docs/reports/p5-question-candidate-20261104/`.
The initial lightweight validation claim on CPUs 24–27 was denied with exit 75:

```text
[region-lock] acquiring regions [] as role='build' (timeout_s=1.0) …
[region-lock] waiting 0.0s for q1 (cpu_core.24.lock) as role='build' tag='p5-candidate-manifest': held by pid 2761895 role=? tag=- age=3s
[region-lock] TIMEOUT acquiring regions []: region lock timeout after 1.0s (role=build, region=q1, tag=p5-candidate-manifest)
```

The owning session then explicitly authorized the single fresh 48–51 claim.
No polling, inference, or scorer run occurred. Test temporary files were created
under `/mnt/raid0/llm/tmp/gpu-serving-tie-in/candidate-manifest/` and removed,
including the empty task scratch directory. No full dataset copy was made.
GitNexus status returned
“Repository not indexed”; this preparation adds files only and changes no
production symbol. Before revising its new test fixture to avoid copying the
dataset, `gitnexus impact test_changed_dataset_refused --direction upstream`
was attempted and refused ambiguous repository selection. No production caller
blast radius is introduced. `gold_binding.py` and the handoff are untouched.

Reproduce the three source-based tests under an available claim:

```bash
/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock run --cpu-list 48-51 --role build --timeout-s 1 --tag p5-candidate-manifest -- /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 /mnt/raid0/llm/worktrees/mains/h-gpu-serving-tie-in/scripts/coordination/gpu-serving-tie-in/p5-gold-validation/test_candidate_manifest.py
```

The tests check independent selection reconstruction and the prompt allowlist,
changed-source rejection, round-trip verification, overwrite refusal and
tamper rejection. The actual freeze used this command under the same claim
as the passing tests (it now refuses because the frozen directory exists):

```bash
/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock run --cpu-list 48-51 --role build --timeout-s 1 --tag p5-candidate-manifest -- /usr/bin/python3 /mnt/raid0/llm/worktrees/mains/h-gpu-serving-tie-in/scripts/coordination/gpu-serving-tie-in/p5-gold-validation/candidate_manifest.py freeze --dataset /mnt/raid0/llm/epyc-inference-research/artifacts/architect-code-eval-20260724/swebench_verified.json --directory /mnt/raid0/llm/worktrees/mains/h-gpu-serving-tie-in/docs/reports/p5-question-candidate-20261104
```

Use `verify` with the same dataset and directory arguments to check the frozen
bytes. Preserve that command's JSON output alongside the artifact pins before
review. Do not describe this candidate as approved or the scorer as validated
on these forty cases.
