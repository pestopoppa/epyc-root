# C6 q4_K four-column correction candidate

This patch changes the non-fused four-column MMVQ minimum correction to use the sum of the quantized q8 values and their half-rounded scale, as the existing generic path does. `BINDING.json` pins the modified C6 source and patch; the candidate is based on C6 `729599d69871181d67af715a4c2f9162d5153a2e` plus the retained MMVQ/MMQ changes. It is not the production kernel.

The host arithmetic control passed five crafted cases, 1,000 deterministic random cases and four lane-group checks. These tests do not exercise HIP or establish native floating-point correctness. The patch has not been built or tested on a GPU. The fused path has a similar expression and remains outside this patch's scope. The existing candidate failed two native n=4 cases; passing the targeted cases, the full correctness suite, performance checks and candidate custody remain necessary before qualification.
