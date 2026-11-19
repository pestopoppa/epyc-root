# Composite REPL rendering fixture: futility outcome

Row `dripreview12-20261119T021331Z` ended rc=0 on 2026-11-19. The fixture failed its discrimination objective: the frozen look at 20 paired episodes stopped with `FUTILITY_NO_GAP` (maximum minus minimum correct count ≤2). This is a completed diagnostic decision, not a rendering-equivalence result.

| Rendering | All seven fields correct | bad_final | no_answer |
|---|---:|---:|---:|
| current | 0/20 | 0 | 4 |
| bounded_k3 | 2/20 | 0 | 0 |
| half_first25 | 2/20 | 0 | 2 |

Higher correct rate is better. Native flags are valid=true, done=true, complete=false (30 planned episodes were not reached), with no void cells. Pairwise descriptive exact McNemar p values are 0.5, 0.5, and 1.0. No interim positive claim is permitted. The predeclared extension does not apply after this futility stop; a new fixture variant requires a fresh predeclaration and row.

Native evidence: `/mnt/raid0/llm/tmp/dripreview12-out-20261119T021331Z/result.json`, SHA-256 `a4f9a2f35c3c96a564d535ee4a8978d6b5d9dac609f4e7407ca02a0fd7499e35`. Producer: epyc-orchestrator `scripts/benchmark/run_repl_composite.py` and `repl_composite_fixture.py` at commit `fe2c0b9e3b5c127aef300229a66a9e5197a8a93a`. Decision specification: `/mnt/raid0/llm/tmp/dripreview12-20261119T021331Z/PREDECLARED.md` (frozen before calls). The manifest result_path contains only server/driver receipts; the scientific outcome is in the native result above. No raw evidence is copied here.

Next action: inspect the retained replies and progressive question/output-schema contract before designing another variant. Early FINAL dictionaries in retained replies can use Q1/Q2 keys rather than the oracle field names; this is a diagnostic lead, not a proven root cause. Do not rerun the same fixture. Schema `epyc.repl_composite_result.v1` needs its own prospective write-side projection and planning-context canary; the older preview adapter cannot warrant this run retroactively.
