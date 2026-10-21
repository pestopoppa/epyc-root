# NIB77 current custody decision — 2026-10-21

Decision only the operator can make: name accountable historical source-custody stewards for the exact inventory below, or explicitly retain existing custody without migration.

Recommendation: retain all current source custody while requesting an explicitly named steward; do not infer that the old service-only roster identity is an active or willing owner. The configured `codex-ak-main-01a11473` identity provides a coordination endpoint, not compute, cleanup, or source ownership authority.

Fresh frozen-tree `git worktree list --porcelain` identifies 35 exact `/laneN` paths, all present. 24 have tracked and/or untracked source status entries; none carries a Git worktree locked marker. Lane-root KEEP absence cannot establish inactivity or authorize deletion. Ancestor KEEP results are preserved separately. These are inventory counts, not active/retirable lane counts. No current session stewardship has been proven from the retained native records. Captured native records remain historical custody evidence; their three numeric PID fields are now absent from /proc. Session working/compacting/idle is unknown without a bound readable runtime instrument, and argv absence is not evidence of inactivity.

Option A: operator names accountable steward(s) for exact paths, with acceptance recorded before any future per-path migration review. Advantage: establishes responsibility. Cost: named acceptance and later native-source review remain necessary.
Option B (recommended interim): retain custody and all source history with no migration. Advantage: immediately preserves safety without assigning an inactive identity. Cost: recovers no capacity.

Neither option authorizes deletion, sparse exclusion, retirement, source mutation, cleanup, benchmark execution, or process termination. Existing dirty/untracked bytes remain untouched. The former “33 historical + two live” division is not restated as current truth.

Evidence: NIB77-current-inventory-v1.json (registration, HEAD, admin originals, status, 33 native records); NIB77-native-record-PID-status-v1.json; NIB77-ancestor-KEEP-v1.json. Original historical reconstruction remains unchanged.

| Exact lane | Status entries |
|---|---:|
| /mnt/raid0/llm/autokernel/campaigns/ak-27b-gpu-verify-20261004/targets/b7b7868ffd944285c8d3dfa0b984cc20960184a1c0c35a10c52d68d4e7700e2a/workers/lane0 | 1 |
| /mnt/raid0/llm/autokernel/campaigns/ak-27b-gpu-verify-20261004/targets/b7b7868ffd944285c8d3dfa0b984cc20960184a1c0c35a10c52d68d4e7700e2a/workers/lane1 | 1 |
| /mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/state-run10d/targets/9816ea2726c4219abe1e6d2079365768818e1ae2fc3f4c7121a0ae5c82ce8868/workers/lane0 | 2 |
| /mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/state-run10g/targets/9816ea2726c4219abe1e6d2079365768818e1ae2fc3f4c7121a0ae5c82ce8868/workers/lane0 | 0 |
| /mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/state-run10g/targets/9816ea2726c4219abe1e6d2079365768818e1ae2fc3f4c7121a0ae5c82ce8868/workers/lane1 | 0 |
| /mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/state-run10g/targets/9816ea2726c4219abe1e6d2079365768818e1ae2fc3f4c7121a0ae5c82ce8868/workers/lane2 | 0 |
| /mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/state-run10g/targets/9816ea2726c4219abe1e6d2079365768818e1ae2fc3f4c7121a0ae5c82ce8868/workers/lane3 | 0 |
| /mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/state-run10g/targets/9816ea2726c4219abe1e6d2079365768818e1ae2fc3f4c7121a0ae5c82ce8868/workers/lane4 | 0 |
| /mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/state-run10g/targets/9816ea2726c4219abe1e6d2079365768818e1ae2fc3f4c7121a0ae5c82ce8868/workers/lane5 | 0 |
| /mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/state-run10g/targets/9816ea2726c4219abe1e6d2079365768818e1ae2fc3f4c7121a0ae5c82ce8868/workers/lane6 | 0 |
| /mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/state-run10h/targets/9816ea2726c4219abe1e6d2079365768818e1ae2fc3f4c7121a0ae5c82ce8868/workers/lane0 | 1 |
| /mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/state-run10i/targets/9816ea2726c4219abe1e6d2079365768818e1ae2fc3f4c7121a0ae5c82ce8868/workers/lane0 | 0 |
| /mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/state-run10i/targets/9816ea2726c4219abe1e6d2079365768818e1ae2fc3f4c7121a0ae5c82ce8868/workers/lane1 | 1 |
| /mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/state-run3/targets/b60bc314c21004925dd786a158481454e6a289e46bbfff0489e3882b2850854f/workers/lane0 | 1 |
| /mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/state-run9c/targets/674cc00c0a4ae9f9a241195fda2adb00c208ef3a9fff980c0b2740162ccfe13d/workers/lane0 | 1 |
| /mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/state-run9d/targets/674cc00c0a4ae9f9a241195fda2adb00c208ef3a9fff980c0b2740162ccfe13d/workers/lane0 | 1 |
| /mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/targets-b0ba1d427/2fdf639c6c6293672a2ba56171fae5f95f7348e0a9be802108117dc20a85ede4/workers/lane0 | 1 |
| /mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/targets-b0ba1d427/b876f301021d646a90d64dd7c14a079b03ffad7eb62b54f374cf2b4afd132e69/workers/lane0 | 0 |
| /mnt/raid0/llm/autokernel/campaigns/ak-q38fn-cpu-decode-20261003/targets-802bf9ac6/2a732697e5195010469da91ceb423b9376671f18ee808a985e7a6fac851ee419/workers/lane0 | 0 |
| /mnt/raid0/llm/autokernel/campaigns/ak-q38fn-cpu-decode-20261003/targets-802bf9ac6/8dce0fa4e7f678651650aab4cec058cf76f83dc0a3aa5db9db08692ee48eb50b/workers/lane0 | 1 |
| /mnt/raid0/llm/autokernel/campaigns/ak-q38fn-cpu-decode-20261003/targets-b0ba1d427/47780f85117868a53da3e8591e48b0c11c78ba13468d4cfe3e0906113895e48a/workers/lane0 | 0 |
| /mnt/raid0/llm/tmp/ak-lanes/lane0 | 2 |
| /mnt/raid0/llm/tmp/ak-lanes/lane2 | 7 |
| /mnt/raid0/llm/tmp/ak-lanes/lane5 | 6 |
| /mnt/raid0/llm/tmp/ak-lanes/lane6 | 4 |
| /mnt/raid0/llm/tmp/ak-loop-lanes/lane0 | 1 |
| /mnt/raid0/llm/tmp/ak-loop-lanes/lane1 | 1 |
| /mnt/raid0/llm/tmp/ak-loop-lanes/lane2 | 1 |
| /mnt/raid0/llm/tmp/ak-loop-lanes/lane3 | 1 |
| /mnt/raid0/llm/tmp/ak-loop-lanes/lane4 | 1 |
| /mnt/raid0/llm/tmp/ak-loop-lanes/lane5 | 1 |
| /mnt/raid0/llm/tmp/ak-loop-lanes/lane6 | 1 |
| /mnt/raid0/llm/tmp/aku-final-glm-gpu-state-20260910-v4/targets/d4aa7739d4f137c67dd8772b99bf57ca355760cf9cc965c4153d4139f9d5f265/workers/lane0 | 1 |
| /mnt/raid0/llm/tmp/aku-final-glm-gpu-state-20260911-v6/targets/d4aa7739d4f137c67dd8772b99bf57ca355760cf9cc965c4153d4139f9d5f265/workers/lane0 | 1 |
| /mnt/raid0/llm/tmp/aku-gpu-original-verification-20260910/fresh-workers/lane0 | 1 |

## Lossless historical registration storage

The preserved `NIB77-frozen-worktree-registration.original` is represented publicly by `NIB77-frozen-worktree-registration.original.json`, a UTF-8 JSON-string container. Parsing its `content` string and encoding it as UTF-8 reproduces the exact historical source bytes, including its final blank line. The decoded SHA-256, decoded byte count, logical filename, and container path are recorded in [`../../../source-storage-map-20261021.json`](../../../source-storage-map-20261021.json). This is a storage-format change only; inventory counts and the retain-custody recommendation do not change.
