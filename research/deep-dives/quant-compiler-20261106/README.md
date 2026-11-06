# LinQuant / Together Compiler intake — Stage-2 dive run (2026-11-06)

**Run**: `intake-quant-compiler-20261106` · **Lane**: `/mnt/raid0/llm/worktrees/intake-quant-compiler-20261106`
**Entries**: intake-2641 … intake-2649 · **Plan**: [`research/intake-stage3-plan-2026-11-06-linquant-tkcc.md`](../../intake-stage3-plan-2026-11-06-linquant-tkcc.md)

## Waves

| Wave | Sources | Entries |
|---|---|---|
| 1 (submitted) | LinQuant paper, LinQuant repo, Together Compiler (alphaXiv), Together vendor post | 2641, 2642, 2643, 2644 |
| 2 (expansions) | SSDi8, Quamba2, KREX | 2645, 2646, 2647 |
| 3 (dive-surfaced, ingested and dived in one pass) | MambaQuant, Kerncap | 2648, 2649 |
| 4 | unused | — |

## Headline findings

1. **LinQuant does not transfer as a quantization gain.** Six of seven invariances act on activations and never meet Q4_K/IQ block layouts; the GDN core is FP32 with no INT8 operand path; the "free latency" claim is a property of SSDi8's fused pass, absent here; no decode evidence exists. Its durable value is the invariance algebra and the float64 reference implementation as a conformance oracle.
2. **The rotation dispute is resolved.** MambaQuant's fixed-granularity control is positive in all four tested cells, refuting SSDi8's general anti-Hadamard claim; the gap SSDi8 measured is scale granularity. LinQuant's key rotation is a boundary extension on the axis SSDi8 excludes.
3. **TKCC's transferable finding is setup cost.** Build is 75.7% and measurement 3.9% of a median iteration locally; 44 of 51 rebuilds were byte-identical; the build runs `-j 1` on a 192-thread host. Its tiering already exists here at finer scope; its context ablation compares role-specialised peers, not our stage decomposition; its keep gate is weaker than ours on every axis.
4. **KREX's premise does not hold on this host.** The GPU is exclusive by grant. What transfers is declaring a timing region and treating p95 inflation as a gate input: with 3.90% p95, independent arms imply a 5.52% floor at which a true 3% win is unresolvable.
5. **Quamba2's 3x generation gain is weight streaming**, not an activation mechanism. The transferable byte lever is 4-bit head/embeddings.

## Dive-surfaced sources (Stage-2 close-out)

| Source | What it would settle | Bearing entry | Recommendation |
|---|---|---|---|
| MambaQuant `arXiv:2501.13484` | The third position on SSM rotation: aligns, then rotates | 2641, 2645, 2646 | **ingested and dived** (2648) |
| Kerncap `arXiv:2605.03208` | Kernel extraction/isolation on AMD for measurement fixtures | 2643, 2647 | **ingested and dived** (2649) |
| Quamba `arXiv:2410.13229` | Precedence for the "first PTQ for Mamba" claim | 2648 | decline — no decision depends on the priority claim |
| DAMP `arXiv:2608.27513` | Decay-aware recurrent-state quantization | 2641 | decline — state bytes are ~0.17% of per-token traffic; re-open with a state-byte line |
| Nazari & Rusch `arXiv:2602.04852` | Origin of the rotation/decay commutation condition | 2641 | decline — the condition is already stated and proved |
| Chahine `arXiv:2510.02823` | Whether in-training compression changes quantizability | 2641 | decline — no training lane |
| Effective state-size `arXiv:2504.19561` | Whether the GDN state is effectively smaller | 2641 | decline — same state-byte premise |
| QServe `arXiv:2405.04532` | Sole authority for excluding W4A4 | 2645 | decline — no W4A4 lane |
| `github.com/cau-hai-lab/SSDi8` | The kernels that are the mechanism | 2645 | decline — artifact, only needed if a build is approved |
| `AMDResearch/intellikit` | Kerncap artifact | 2649 | decline now — ROCm 7.0 gate |
| CRIUgpu / Kokkos Kernels / rr | Process-level alternatives to snapshot capture | 2649 | decline — no capture work until the ROCm gate |
| I-LLM / S-SiLU, HadMamba2, RepQ-ViT | Lineage and whether the Hadamard control is identical | 2648 | decline — mechanism already stated; no decision depends on it |

All declines are recorded in the bearing entries' `dive_corrections` or notes.

## Method and audit

- Every dive read primary source text from disk (arXiv HTML v1/v4 or the alphaXiv paper markdown; repo at a pinned HEAD; blog HTML). Read depth is `FULL` except 2641 and 2642, which are `PARTIAL` for figures and the uninitialised SSDi8 submodule.
- An independent second reader re-checked all 40 claim anchors: 0 hash mismatches, 0 genuinely absent quotes; one fabricated quote (2646 claim 3) and four wrong-direction or unsupported anchors were found and fixed; 7 locators were corrected. Report: [second-reader-anchor-audit.md](second-reader-anchor-audit.md).
- Quote convention: prose is source-faithful; HTML/LaTeX math glyphs are transliterated (× as x, − as -, superscripts as ^, elided spans as `(...)`), and table-derived or inferred spans are marked in `setup_scope`.
- Stage-1 entries were persisted before any dive; all nine carry `claim_anchors` and `claim_corrections`.
- Artefacts (raw text, hashes, drafts, quote verifiers) are under `/mnt/raid0/llm/tmp/dive-quant-compiler-20261106/`; the dive reports here are the permanent record.
