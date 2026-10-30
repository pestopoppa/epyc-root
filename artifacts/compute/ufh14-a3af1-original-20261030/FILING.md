### UFH14-A3A-F1 option (a): original three-arm diagnostic (2026-10-30)

`codex-ni-ufh14-a3af1-r1-20261030` completed its fixed historical first-request replay (rc 0, not partial; writer and cleanup verified; 2,323 own-process residency samples). Cold, historical one-warm, and all-four-warm arms each used a fresh load; both historical member bodies were retained and the warm arms used the 3-second stagger. The four warmup native log segments independently say `selected slot by id` for 0, 1, 2, and 3 respectively. Their `(cache_n, prompt_n, prompt_ms)` were `(0,56794,95520.177)`, `(0,56794,117109.297)`, `(0,56794,96006.051)`, `(0,56794,118339.110)`; these are cold warmups, not cache hits.

| Arm | Member | Client TTFT (s) | Native prefill (s) | cache_n | prompt_n | First byte (s) | First recorded event (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Cold | 0 | 112.337 | 112.247049 | 0 | 56799 | 0.090 | 112.337 |
| Cold | 1 | 270.280 | 261.497385 | 0 | 56799 | 8.783 | 270.280 |
| One warm | 0 | 0.284 | 0.179235 | 56794 | 5 | 0.103 | 0.284 |
| One warm | 1 | 174.638 | 174.411279 | 0 | 56799 | 0.227 | 174.638 |
| All four warm | 0 | 0.274 | 0.176888 | 56794 | 5 | 0.098 | 0.274 |
| All four warm | 1 | 0.968 | 0.552037 | 56794 | 5 | 0.416 | 0.968 |

Client TTFT is the captured arrival of the first nonempty generated output-text, reasoning, or function-arguments delta minus client request start. Raw SSE records are matched by count, order, type and timing to captured arrivals. First byte and first event remain separate; lower is better for TTFT and native prefill. One-warm member 1 is a cache miss; both all-four-warm members report cached prefixes. This is one descriptive group per arm, with correlated members; no threshold, performance keep, F2/decode-stall, quality, or production conclusion follows. A chunk may contain multiple tokens. The group CLI refuses the warm arms because one-token warmup streams contain no generated-output delta; each member above was projected independently with the unchanged reader's `project()` and joined by unique request SHA to native timings. This does not assert a warmup TTFT.

Native private bundle: `/mnt/raid0/llm/tmp/codex-ni-ufh14-a3af1-20261030/attempts/run-1793386153401272778/` (all member and warmup raw SSE, native selected-slot logs, timing bindings, server/linkage logs, VRAM and result). Read-only projection and hashes: `/mnt/raid0/llm/tmp/codex3-filing-1650-20261030/member-projections.json` SHA-256 `6ba4758e452b06feaf2b153e6d300c263114f3db30af4d52b3daf1ed62ee13e8`; `SHA256SUMS` SHA-256 `aaee12c1028d1911f07bf2fb965dce422a032c6b7018c0ddb2948937d3cbf703`. Native measurements are not retroactively assigned a measurement warrant. [belief: cc]
