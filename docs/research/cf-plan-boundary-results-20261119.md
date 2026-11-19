# Local prefix-rewrite pricing result — 2026-11-19

`cf-plan-boundary-20261118` ended rc=0 and passed its registered coverage
predicate: `completed == 6 and cache_witness_valid == 1`. All six fixed
pairs completed, `error=null`, and `server_exited=true`. This establishes
completion of the [prospective diagnostic](../design/cf-plan-boundary-protocol-20261118.md).
The existing deterministic FILED receipt records the same pass.

Replacing a warm prefix with its quarter-length replacement increased total
latency in every observed four-request window. Lower latency is better;
positive overhead and positive four-request delta mean rewriting cost more.
Later savings are retain minus rewrite on requests 2–4, where positive is
better. No pair repaid the first-request rewrite cost within the measured
window.

| Prefix / repetition | Native rewrite overhead ms | Native later savings ms/request | Native four-request extra ms | Native extrapolated requests | Wall four-request extra ms | Wall extrapolated requests |
|---|---:|---:|---:|---:|---:|---:|
| 1024/0 | 3800.571 | 68.618 | 3594.717 | 57 | 3594.267 | 57 |
| 4096/0 | 15940.681 | 274.082 | 15118.435 | 60 | 15116.330 | 60 |
| 1024/1 | 3680.862 | 99.001 | 3383.859 | 39 | 3383.372 | 39 |
| 4096/1 | 15820.483 | 270.556 | 15008.816 | 60 | 15006.723 | 60 |
| 1024/2 | 3696.806 | 13.192 | 3657.229 | 282 | 3656.902 | 280 |
| 4096/2 | 16391.332 | 215.071 | 15746.120 | 78 | 15743.947 | 78 |

For 1,024→256 tokens, native overhead spans 3,680.862–3,800.571 ms,
later savings 13.192–99.001 ms/request, and extrapolated break-even 39–282
requests (wall: 39–280). For 4,096→1,024 tokens, overhead spans
15,820.483–16,391.332 ms, later savings 215.071–274.082 ms/request,
and extrapolated break-even 60–78 requests for both clocks. These are
three descriptive repetitions per size; the wide small-prefix spread makes
a fixed break-even constant unsuitable even for this diagnostic.

The extrapolation is `1 + ceil(max(0, overhead) / mean_later_savings)`.
It assumes the observed later saving persists beyond four requests; that
assumption was not measured. There are no confidence or population claims.
This synthetic, greedy one-token ASCII-output workload on four CPU cores
uses explicit slot 0, growing prefixes and a first-token replacement that
forces cache invalidation. It is not an answer-quality or production
trajectory test. Native cold rewrite processed 288 or 1,056 tokens versus
32 for the retained warm request; subsequent requests processed 32 on both
paths. Native prompt+decode and client-wall accounting remain separate.

Recommendation: retain this local rewrite charge in prospective trigger
costing; do not adopt a plan-boundary trigger from these observations.
Summary-generation cost is excluded, the shorter input is supplied rather
than generated, and quality preservation is untested. CF-PB-1 remains open
for its adoption question. Production compaction flags, the character-length
OR-trigger and summary-request step-progress handling are unchanged.

## Evidence identity

Native result: `/mnt/raid0/llm/tmp/delegation-context-preassembly/cf-plan-boundary/native/RESULT.json`, SHA-256 `7b6fa5aa2be0b13889aa116246f1d4952a46c6a6b6a6137a6a41bfc193025cb2`.

Input seal: `de8e47c60dcfb1137dea74b34585fe5c14a40c248df0a66170003454bd1205f4`. The result binds per-file native
request/response, cache-accounting, timing and runtime-window hashes.
The pinned model is Qwen3.6-35B-A3B-MTP Q8_0, kernel
`ffc1bac82eeca6f9099e1ccd9ba49703c460a115` / build 10303; source, serving
and accounting requirements are in the prospective protocol. Original
records remain at their paths; no raw artifacts are copied into this repo.
The existing `VB-CF3C-POLICY-WIRE` source registration already includes
`epyc.cf_plan_boundary.native.v1`; projection and planning-context canary
remain pending. This conclusion is recorded as committed knowledge, with
no retrospective measurement warrant invented.
