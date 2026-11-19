# KPF-62.3 native auxiliary tokenizer observation

Row `kpf623-tokenizer-roundtrip-20261105` completed at 2026-11-05T03:51:58Z with rc=0; filed on 2026-11-19. Verdict: **OBSERVED** (the observation gate passes).

The sealed 256-case census on Qwen2.5-0.5B Q8_0, vocabulary-only with `add_special=false` and `parse_special=false`, reports:

| Native outcome | Cases |
| --- | ---: |
| EXACT (bytes and expected auxiliary IDs) | 128 |
| DIFFERENT_IDS (same bytes, different IDs) | 0 |
| DIFFERENT_BYTES | 128 |
| UNKNOWN | 0 |

Independently comparing emitted token-ID sequences with the predeclared case sequences gives **128 equal IDs and 128 differing IDs**, irrespective of byte outcome. The differing-ID category in the table is conditional on matching bytes. Its zero count does not establish ID agreement for the 128 differing-byte cases. This finite packet answers the scoped observation question; no further sampling is needed for that question.

All 256 observation IDs match the predeclared case order. The recorded producer completed its before/after sealed header, library, compiler, case-input and source-commit checks, model stat checks, bounded native execution and owned direct-child cleanup. Both build and native tokenizer commands returned zero; the native completion marker is `ROUNDTRIP_COMPLETE 256`. Filing independently checked case order, counts, observation digest, executable digest and matching recorded model stat identities. No benchmark was rerun.

Evidence remains at its original paths:

- Result: `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf623-tokenizer-roundtrip-20261105/out/RESULT.json`, SHA-256 `640347c06ede6d4795a0b0c065c18a9d59b102a30cceb995279f91390c23908a`.
- Observations: the result's `observations_path`, SHA-256 `2cf35c203c08fc918c865e442b91af4a9c850742fb460557df499b6180944e1a`.
- Native executable: the result's attempt directory `/roundtrip`, SHA-256 `173d0dd2047b791aad81f77430b19e1daefc60859548f201ec76eb804cc6aa55`.
- Producer: `docs/reports/kv-cache/kpf623-tokenizer-roundtrip-20261105/worker.py`, git blob `04792391e5753c3bc81a4afd7d1c3796103b58cb`; source tree commit `3ec14227a0e293bfc223c9026ed761ea3bdda9bb`. Packet case SHA-256 `d0a10ccb13f1f0d0464292e85533f966c35d342fc730b9ade88ad445f8acc4c8`.

Limits: mappings are producer-reported; model custody during execution is stat-based. The helper records its executable digest before execution; filing confirms the retained executable still matches, without claiming continuous executable monitoring. Compiler descendant cleanup is not independently established. This result does not establish general tokenizer compatibility, contextual span correctness, selector quality, budget re-admission or G3 acceptance. The observation is a committed conclusion, without retroactively constructing a measurement warrant. Prospective write-side capture belongs to `VB-KPF623-TOKENIZER-WIRE`; a planning-context canary is required before calling that loop wired.
