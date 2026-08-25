# Document Processing

**Category**: `document_processing`
**Confidence**: verified
**Last compiled**: 2026-08-18 (the stranded lane record landed: the demo DID run on a quant-compliant artifact, the receipt's `held_s` defect is root-caused and fixed forward, and the write-side wiring row survived an id collision)
**Sources**: 19+ documents

## Compiled Update — 2026-08-18: the demo ran on the compliant artifact after all — two receipt corrections from the ported lane record

**Confidence: verified** — read from the ported lane run record, the handoff's annotated rows, and
the named research commits; corrections below supersede the matching statements in the 2026-08-16
update, which is retained unedited per the append-never-edit rule.

### CORRECTION: the 18-page demo ran on the requantized, quant-compliant model

The 2026-08-16 update below states the default Unlimited-OCR artifact was "still non-compliant"
(`output.weight` at Q6_K against a required `lm_head >= Q8_0`). The ported 2026-08-13 lane record
shows the compliance work happened **before** the 22:18Z demo: the model was requantized as
`Unlimited-OCR-Q5_K_M-outq8.gguf` (2.26 GB; `llama-quantize --allow-requantize
--output-tensor-type q8_0`, `output.weight` verified q8_0 via `llama-gguf`, the other 154 tensors
byte-copied rather than re-quantized — no double-quant loss), `DEFAULT_MODEL` was repointed
(research `c733e1ee`), **and the demo ran on it**. What the artifact-gate row still requires is the
immutable SHA-256 + tensor-audit *record* — the compliance gap that remains is documentary, not
material. The rest of the 2026-08-16 assessment stands: prompt/profile mismatch (not "root cause"),
canonical-recipe A/B still owed, no ClaimTuple.

### The `held_s` receipt understated a hold that was in fact full-interval — fixed forward, not backfilled

The stored `inference_window.json` reports `held_s = 1.002881998` and must still never be cited as
full-interval residency proof for the first run. The root cause is now known: the receipt stamped
`held_s` right after `wait_for_health` (~1s in), while the flock itself **was** held for the entire
launch→queries→terminate interval. The fix (research `aca459d9`) recomputes `held_s` at release from
the lease's acquisition stamp, with a test asserting it. The two statements coexist deliberately:
the *mechanism* held for the whole run, but the *stored receipt* cannot prove it — so the first
run's receipt stays inadmissible and the fix applies only to future receipts. A defective receipt is
corrected by the next run's evidence, never by editing the stored one.

### The write-side wiring row survived a namespace collision

The ODL-P2 ClaimTuple wiring task was filed by the run's author on the lane as "SC37" — a number the
main tree had independently given to a different task (and a second colliding filing took SC41). On
forward-port it was renumbered **SC42** with the collision recorded inline and content unchanged.
The row itself is unchanged in substance: the adapter has no write hook, one witness per run (the
run-level locator, not per-page), and the hook must exist before any successor run — retrofitting on
read remains impossible.

### Source References (2026-08-18 lane-record corrections)

- [`opendataloader-pipeline-integration.md`](../handoffs/active/opendataloader-pipeline-integration.md)
  — the annotated quant-compliance row (requantized artifact, `DEFAULT_MODEL` repoint, the demo ran
  on it, SHA-256/tensor-audit still owed) and the run-detail annotation on the Unlimited-OCR status
  row.
- [`progress/2026-08/2026-08-13-mainD.md`](../progress/2026-08/2026-08-13-mainD.md) — the ported
  run record: requantization before the demo, the grant saga, the demo receipts, and the `held_s`
  defect root-cause and fix.
- [`vidya-belief-substrate-program.md`](../handoffs/active/vidya-belief-substrate-program.md) — the
  SC42 row with the renumbering note and the write-side contract.
- [`scripts/vidya/adapters/README.md`](../scripts/vidya/adapters/README.md) — the ODL-P2 source
  register row the wiring task resolves against.

## Compiled Update — 2026-08-16: the numbers behind the 2026-08-13 observations, and why none of them carries warrant

**Confidence: verified** — figures are read from the ODL handoff's completed rows and the belief-kernel
source register; both artifact trees (`/mnt/raid0/llm/tmp/odl013-bench-20260813T1336Z/intrinsic/` and
`/mnt/raid0/llm/tmp/odl-p2-unlimited-ocr-demo-20260813T221821Z/`) were confirmed present on disk for
this compile. **No routing, adoption, or promotion authority attaches to anything below.**

### ODL-011 intrinsic chunk metrics: first real run, and what it can and cannot rank

The non-coreference Ekimetrics arm is now registered in `odl_bench` (`intrinsic.py`, research
`f24b8aa9` + `cd329746`) with SC/BI/ICC/DCC, upstream MIT provenance pinned (intake-580#record), and 30 tests
covering metric direction plus degenerate inputs. An unavailable embedder is preserved as an explicit
`value=None` with a reason rather than a silent zero — the same discipline the belief kernel calls
"absence is recorded, never filled".

First real run (sentence-transformers 5.7.0, `all-MiniLM-L6-v2`, 200 docs per engine over the ODL-013
prediction directories):

| engine | ICC | DCC |
|---|---|---|
| pdftotext | 0.651 | 0.672 |
| opendataloader | 0.643 | 0.654 |
| liteparse | 0.552 | 0.654 |

Two limits keep this from ranking parsers. First, **intrinsic chunk-cohesion scores are not parser
quality** and the parent contract forbids intrinsic-only gating: the contradictory HOPE family and one
common downstream RAG answer-correctness endpoint must be reported on the same digest-pinned Phase-2
fixture before either family informs routing. Second, the notable line in the table — pdftotext, the
weakest structural extractor, leading ICC — is exactly the result that would mislead if read as a
parser verdict. RC/FMRE remain excluded on both licence grounds and a recorded upstream
boundary-corruption defect in that path.

### Unlimited-OCR 18-page demo: a real run whose headline metric is an output-format artifact

The P2 demo executed on 2026-08-13 against 18 OmniDocBench GT pages via
`adapter.py run-model --engine unlimited_ocr` (research `aca459d9`), producing median **5,857 ms per
page**, decode ≈ **392 t/s**, text-block edit distance **0.3624**, table TEDS **0.0117**, reading-order
edit distance **0.2165**.

The verified finding matters more than the scores: **the model emitted coordinate-tagged layout dumps
rather than markdown on all 18 pages**, which is a sufficient explanation for a near-zero TEDS without
any claim about table quality. This is structurally the PaddleOCR-VL retraction repeating — an
off-label invocation profile producing numbers that describe the harness, not the model. Accordingly:

- The **causal** claim is not verified. A bare-passthrough GGUF chat template is confirmed;
  "coordinate output regardless of prompt" is not, and llama.cpp's own source records prompt-dependent
  behaviour. The record must say *demonstrated prompt/profile mismatch*, not *root cause*.
- The mutex evidence does not cover the run. `inference_window.json` reports `held_s = 1.002881998`, so
  it is not full-interval residency proof and must not be cited as one.
- The correct next step is the canonical profile as a fresh matched A/B (`document parsing.`,
  `n_predict=4096`, `n_ctx=16384`, DRY, grounding-strip, per `tools/mtmd/tests/test-deepseek-ocr.py`),
  with a receipt spanning server launch through termination — gated on the operator's all-inference-stop
  order being lifted, and on the artifact gate below.
- The default artifact is still non-compliant: body Q5_K with `output.weight` at Q6_K against a
  required `lm_head >= Q8_0`.

### The provenance status of all of it: measurements without a claim tuple

The demo run carries more warrant than most parser evidence in this program — a protocol (the engine
invocation at a pinned research commit), n = 18 protocol-admissible GT pages, a date, durable per-page
response JSONs plus `model_gated_row_set.json`, and an inference-window receipt. **It still has no
write-side ClaimTuple hook**, so it is registered as a `candidate` source to be wired *prospectively
before the next run*, never reconstructed on read. Two constraints travel with that row:

- **Locator: the demo run, not the page.** One 18-page run is one witness, not eighteen — the same
  same-harness trap that permanently disqualified `benchmarks/results`.
- **Scratch is not attestation.** These artifacts live under `/mnt/raid0/llm/tmp/`, outside any git
  tree, so a path alone proves nothing later; a content digest taken at collect time is what would let
  the claim rise above a located reference.

The general form is on [Knowledge Management](knowledge-management.md): wiring the write side is cheap
and permanent, retrofitting the read side is impossible, because a tuple invented on read claims
warrant the original run never captured.

### Source References (2026-08-16 parser-evidence provenance)

- [`handoffs/active/opendataloader-pipeline-integration.md`](../handoffs/active/opendataloader-pipeline-integration.md)
  — the ODL-011 completed row with the ICC/DCC run, the ODL-013 observation boundary, and the
  Unlimited-OCR correction and rerun contract
- [`handoffs/completed/opendataloader-pipeline-integration-completed-through-2026-08-13.md`](../handoffs/completed/opendataloader-pipeline-integration-completed-through-2026-08-13.md)
  — metric-contract corrections, the RC/FMRE exclusion and its upstream defect, and the quant-gate audit
- [`scripts/vidya/adapters/README.md`](../scripts/vidya/adapters/README.md) — the ODL-P2 register row:
  exact metrics, artifact locations, the coordinate-dump finding, and the run-level locator warning
- [`docs/design/vidya-pilot-spec.md`](../docs/design/vidya-pilot-spec.md) §4.7 — why a pre-hook run is
  skipped rather than back-filled

## Compiled Update — 2026-08-13: later parser evidence advances observation, not selection authority

**Confidence: verified for stored-output replay and the audited record; no routing or adoption decision.**
The Ekimetrics SC/BI/ICC/DCC arm is now implemented and exercised over the ODL-013 prediction sets,
superseding the earlier “unimplemented” snapshot below. The first real embedding run produced usable
ICC/DCC observations, but the contradictory HOPE family and common downstream RAG endpoint remain open;
neither intrinsic family can gate a chunker alone. ODL-013's 600 stored outputs still replay exactly,
and LiteParse still leads aggregate point estimates, but scratch-only storage, absent parser protocol
and precommitted rule, summary-only timing, and an unpinned ODL version keep the result observational.

Unlimited-OCR also completed a mechanically real 18-page observation, but the independent audit found
that its record overclaims the cause. A bare-passthrough GGUF chat template does not prove
prompt-independent coordinate output, the stored mutex receipt covers only about 1.003 seconds rather
than the full server interval, and the timing narrative needs correction. Preserve the observation,
correct those claims, then run a fresh matched A/B with the canonical `document parsing.` profile,
context/prediction limits, DRY settings, grounding-strip, and a new Inference receipt spanning launch
through termination. The operator's stop-all-inference order remains a hard runtime boundary.

The attempted LightOnOCR comparison was correctly refused before compute: `odl_bench` has only a
manifest stub, the dispatch prohibited the HTTP server that is the only implemented producer, and the
known-negative prior lacked a new parser-quality hypothesis. That is a precondition failure, not model
evidence.

### Source References (2026-08-13 later parser evidence)

- [`opendataloader-pipeline-integration.md`](../handoffs/active/opendataloader-pipeline-integration.md)
  — corrected gates and exact rerun contracts.
- [`progress/2026-08/2026-08-13-mainA.md`](../progress/2026-08/2026-08-13-mainA.md) and
  [`progress/2026-08/2026-08-13-mainB.md`](../progress/2026-08/2026-08-13-mainB.md) — producer and
  precondition records.
- [`progress/2026-08/2026-08-13-auditor.md`](../progress/2026-08/2026-08-13-auditor.md) — exact
  evidence audit and verdicts.

## Compiled Update — 2026-08-13: ODL-013 is reproducible evidence, not an adoption decision

**Confidence: verified for corpus/output equality and evaluator replay; observation-only for parser
selection.** This supersedes the preflight-only snapshot below without turning the later run into a
decision record.

The later ODL-013 execution did process the full matched 200-PDF corpus. Each of LiteParse,
OpenDataLoader-local, and pdftotext has the same 200 prediction stems, no zero-byte prediction, and
the stored NID/TEDS/MHS results reproduce exactly when all 600 outputs are replayed through the
pinned upstream evaluator. LiteParse leads the aggregate point estimates, including overall quality,
and remains JVM-free. That makes the run useful comparative evidence.

It does **not** license the recorded `ADOPT` verdict or a routing-default change. The artifact exists
only in local scratch, cites no applicable document-parser protocol/category/attestation, records no
precommitted selection rule, retains only timing summaries rather than per-document latencies, and
does not pin the ODL engine version. Exploratory paired intervals for LiteParse-minus-ODL cross zero
for NID and MHS, so “wins every metric” is true only of aggregate point estimates. The harness also
needs prospective fail-closed handling for extractor return codes, absent candidates, and empty
predictions; all actual stored predictions in this run are non-empty, so this is a harness-accounting
follow-up rather than evidence of an observed failed document.

The operational conclusion is deliberately narrow: preserve or rerun this comparison as durable,
protocol-admissible evidence with a precommitted decision rule, and keep parser/routing defaults
unchanged until then. The matched parser report's `decision-grade fixture` wording is superseded.

### Source References (2026-08-13 ODL-013 audit)

- [`opendataloader-pipeline-integration.md`](../handoffs/active/opendataloader-pipeline-integration.md)
  — corrected decision gate, completed observation rows, and concrete durability/harness follow-ups.
- [`progress/2026-08/2026-08-13-mainA.md`](../progress/2026-08/2026-08-13-mainA.md) and
  [`progress/2026-08/2026-08-13-mainB.md`](../progress/2026-08/2026-08-13-mainB.md) — producer-side
  execution, corpus, and result records.
- [`progress/2026-08/2026-08-13-auditor.md`](../progress/2026-08/2026-08-13-auditor.md) — independent
  replay, statistical caveats, claim-boundary verdict, and follow-up disposition.

## Compiled Update — 2026-08-13: four first-wave preflights produced no decision-grade parser result

**Confidence: verified by commit, artifact, source, and focused-test audit.**

The committed `odl_bench` schema does **not** expose the previously attributed NID/TEDS/MHS trio. Its package rows are structural text edit distance, table TEDS, reading-order edit distance, and speed; NID and MHS live in the sibling `document_extraction_adapter.py`. ODL-011 completed only this premise/contract audit. Ekimetrics SC/BI/ICC/DCC and contradictory HOPE scoring remain unimplemented in the accepted tree, and neither family may gate a chunker until both run on one pinned fixture with the same downstream RAG answer-correctness endpoint.

ODL-013 likewise completed harness preflight, not a comparison. The July born-digital artifacts remain useful scaffolding but contain no representative 2026-08-13 structural/table result or fast-path verdict. The Unlimited-OCR producer/adapter/manifest scaffold is real and passed 26 focused tests, yet its default model is not eligible for the planned demo: `output.weight` is Q6_K while the parent contract requires `lm_head >= Q8_0`. No live model result was produced.

This also retires the old PaddleOCR table numbers as quality evidence: they came from an off-label full-page invocation rather than the official layout-plus-cropped-recognition pipeline. The live decision surface remains ODL/LiteParse representative scoring, a corrected full-corpus PDF bridge, architecture-faithful model arms, and explicit routing policy.

### Source References (2026-08-13 audit)

- [`opendataloader-pipeline-integration.md`](../handoffs/active/opendataloader-pipeline-integration.md) — compact active gates and exact next work.
- [`opendataloader-pipeline-integration-completed-through-2026-08-13.md`](../handoffs/completed/opendataloader-pipeline-integration-completed-through-2026-08-13.md) — landed phases, corrections, and audit disposition.
- [`progress/2026-08/2026-08-13-auditor.md`](../progress/2026-08/2026-08-13-auditor.md) — independent commits/tests/artifact audit.

## Compiled Update — 2026-08-12: the benchmark dataset landed, and every premise about it was wrong

**Confidence: verified** — the two clones were inspected directly on disk for this compile (`git remote -v`, `git rev-parse`, `LICENSE`, `git lfs ls-files`, PDF magic bytes), not restated from the handoff.

**The 200-PDF `opendataloader-bench` dataset is now present** at **`/mnt/raid0/llm/opendataloader-bench-upstream`** @ `7af1d8f`, 180 MB, `ground-truth/` included. That clears the standing blocker on the 200-PDF baseline comparison (our pipeline vs ODL local vs ODL hybrid vs docling vs marker); the run itself is still outstanding.

**All three parenthesised premises of the row that asked for the clone were false**, and each is worth carrying because each would have changed how someone approached it:

| Row said | Measured |
|---|---|
| MIT license | **Apache-2.0** (`LICENSE` line 1) |
| 200 PDFs *via Git LFS* | **No LFS at all** — `git lfs ls-files` returns 0; upstream carries a `chore/remove-lfs-integrate-bench` branch, so a plain clone suffices |
| entrypoint `uv run src/run.py` | **No `src/` in the repo** |

**Presence of a `.pdf` is not presence of a PDF.** All 200 were verified as real payload rather than LFS pointer stubs — every file `%PDF-1.6`, smallest 251 KB, mean 184 KB. In a repo whose history *did* use LFS, a directory listing of 200 filenames is exactly what a pointer-stub checkout also looks like.

### A dataset name collision that had been answering "yes" to the wrong question for 26 days

**`/mnt/raid0/llm/opendataloader-bench` was a clone of a different project**: `git remote -v` gives `github.com/opendatalab/OmniDocBench` @ `147cd5a`, Apache-2.0, 211 PDFs, with its own CLA file. So anyone testing *"is opendataloader-bench cloned?"* by checking that path got an emphatic **yes, backed by 211 real PDFs** — the right key in the wrong universe. Every prose reference to that bare path in the pipeline handoff (including the `pdf_validation.py` and `demo_data/` descriptions) therefore describes **OmniDocBench**, not the ODL benchmark.

**RESOLVED 2026-08-25 (PIP-05)**: the OmniDocBench clone was renamed to `/mnt/raid0/llm/omnidocbench`, so the colliding bare path no longer exists and a bare-name check now fails loudly instead of silently resolving to the wrong project. `/mnt/raid0/llm/opendataloader-bench-upstream` remains the OpenDataLoader 200-PDF benchmark clone; the 2026-07-21 corpus copy still lives at `/mnt/raid0/llm/omnidocbench/{pdfs,ground-truth}/`.

**Standing rule for this pair: cite the two datasets by their full distinct paths, never by the bare name.**

### A compound checkbox takes the checkbox of its easiest clause

The row read *"Clone opendataloader-bench, **add our pipeline as custom engine**"* and had been `[x]` since 2026-07-17 — with every cited artifact covering the *engine* half only. The clone half was never done, and this file's own text ~226 lines further down said so (*"the actual … dataset is still absent"*). **A contradiction sat 223 lines apart inside one document for 26 days**, because a conjunction inherits the truth value of its easier conjunct. The discipline that follows: **split conjunctions into one row per independently verifiable claim.**

### Source References (2026-08-12)

- [`handoffs/active/opendataloader-pipeline-integration.md`](../handoffs/active/opendataloader-pipeline-integration.md) §Benchmark Suite Integration — the clone, the three corrections, and the name-collision filing
- [`progress/2026-08/2026-08-12.md`](../progress/2026-08/2026-08-12.md) — the premise-by-premise verification and the compound-row finding
- [`docs/guides/agent-workflows/verification-failure-catalogue.md`](../docs/guides/agent-workflows/verification-failure-catalogue.md) face 9 (*right key, wrong universe*) — the class the path collision belongs to

## Summary

Document processing in the EPYC orchestrator currently uses a binary routing pipeline by default: born-digital PDFs go through `pdftotext -layout` (fast, ~100ms/page, no structure) while scanned/image PDFs route to LightOnOCR-2-1B (slow, ~1-3s/page on GPU, high accuracy). The gated OpenDataLoader path now supplies structured headings, figure context, figure bboxes, table metadata, scanner-gated structured metadata, a default-inert table-backend seam, and default-off primary body injection warnings to downstream preprocessing. The live ODL hybrid sidecar now exists on `127.0.0.1:5002` and has produced `27/27` structural parses on the 27-PDF manifest; the remaining gap is benchmark-backed comparison and routing policy, not sidecar viability, plus per-page complexity routing and LiteParse born-digital evidence.

OpenDataLoader PDF (intake-161, Apache 2.0) has been evaluated as a comprehensive upgrade. Its local mode uses the XY-Cut++ algorithm (rule-based, no ML) at 0.05s/page -- essentially free and comparable to pdftotext latency. It provides structured JSON output with semantic types (heading, paragraph, table, list, image, caption, formula), bounding boxes, heading hierarchy, and correct reading order (0.91 NID score). The hybrid mode routes complex pages to an AI backend (docling-fast, SmolVLM 256M) achieving 0.90 overall accuracy and 0.93 table accuracy at 0.43s/page, placing first among all evaluated engines above docling (0.86), marker (0.83), and pymupdf4llm (0.57).

A three-phase integration plan has been designed and is actively tracked. Phase 1 replaces pdftotext with OpenDataLoader local mode in `pdf_router.py` -- same latency, better reading order, structured output. Phase 2 (the biggest win) now has its main consumer path wired: ODL headings can drive chunking, ODL figure bboxes replace PyMuPDF image enumeration in structured mode, ODL figure context can enrich VL prompts, ODL tables flow through preprocessing/cache/TaskIR output as first-class table records, and `ORCHESTRATOR_ODL_TABLE_BACKEND` provides the local-vs-future-hybrid routing seam. When `INJECTION_SCANNING` is enabled, unsafe ODL structured headings/captions/tables suppress that additive metadata before it reaches chunking or VL prompts; `ORCHESTRATOR_DOCUMENT_BODY_INJECTION_POLICY=warn` separately scans primary OCR/body pages and emits warnings without mutating source text. Phase 3 deploys the hybrid mode as a sidecar service and integrates the opendataloader-bench 200-PDF dataset for reproducible quality comparison.

The Java 11+ runtime dependency is manageable through a sidecar pattern. The Python SDK wraps a Java CLI where each `convert()` call spawns a JVM, so batch processing or persistent subprocess warming is recommended for production. The structured JSON output improves every downstream consumer: chunker, figure analyzer, LLM context quality.

## Key Findings

### New (2026-07-17, PaddleOCR-VL producer/runtime path closed; table quality still open)

- **PaddleOCR-VL-1.6 is now a real document-specialist candidate with a guarded benchmark producer, not just a model-card idea.** The MI210 smoke passed digit OCR (`7500`) and invoice/receipt extraction at about `484-490 t/s`, and `odl_bench run-model --engine paddleocr_vl_1_6` now consumes OmniDocBench GT page images, writes `<stem>.md` predictions, and scores them through the structural/table/reading-order harness. The first operational demo processed `18/18` pages with median decode `485.30 t/s`, median page latency `2918.78 ms`, text-block edit distance `0.343019`, and reading-order edit distance `0.337318`. Sources: [opendataloader-pipeline-integration.md](../handoffs/active/opendataloader-pipeline-integration.md), [progress 2026-07-17](../progress/2026-07/2026-07-17.md), [k35-optimized-stack-throughput-context-report-2026-07-17.md](../research/deep-dives/k35-optimized-stack-throughput-context-report-2026-07-17.md).
- **Prompt-only HTML-table recovery was negative, which means the remaining table gap is structural/post-processing, not just prompt wording.** The `html_tables` profile improved reading-order edit distance (`0.337318 -> 0.285753`) but still emitted zero HTML `<table>` tags, kept table TEDS at `0.0`, worsened text-block edit distance to `0.429062`, and slowed median page latency to `3245.60 ms`. This is useful because it rules out the cheap "just ask for HTML tables" fix. Sources: [opendataloader-pipeline-integration.md](../handoffs/active/opendataloader-pipeline-integration.md), [progress 2026-07-17](../progress/2026-07/2026-07-17.md), [k35-optimized-stack-throughput-context-report-2026-07-17.md](../research/deep-dives/k35-optimized-stack-throughput-context-report-2026-07-17.md).
- **A scorer-compatible pipe-table post-processing hook helps a little, but it does not close the table-quality problem.** Re-scoring the existing default PaddleOCR-VL predictions after converting aligned pipe rows into HTML tables improved table TEDS from `0.0` to `0.058333` and structure-only TEDS to `0.066667`, with essentially flat text-block edit distance. That is worth keeping as a compatibility fix, but it is not enough to treat PaddleOCR-VL as table-quality-clean. Sources: [opendataloader-pipeline-integration.md](../handoffs/active/opendataloader-pipeline-integration.md), [progress 2026-07-17](../progress/2026-07/2026-07-17.md), [k35-optimized-stack-throughput-context-report-2026-07-17.md](../research/deep-dives/k35-optimized-stack-throughput-context-report-2026-07-17.md).

### New (2026-07-06, ODL hybrid sidecar live checkpoint)

- **The ODL hybrid path now has live sidecar evidence, but benchmark-backed routing policy remains open.** A sidecar implementation added `opendataloader_hybrid` as a named backend in the PDF fast-path probe. The probe checks `opendataloader_pdf` importability and `ORCHESTRATOR_ODL_HYBRID_URL` reachability before calling the hybrid extraction method, and records missing dependencies or unreachable sidecars as explicit `missing_dependency` failures instead of confusing them with extraction quality. A live run under `/mnt/raid0/llm/tmp/odl-hybrid-venv` started `opendataloader-pdf-hybrid` on `127.0.0.1:5002` and returned `27/27` successful parses on the structural manifest with median `1510.743 ms / 1.000`. This advances Phase 3 readiness without claiming the 200-PDF/table-heavy benchmark or a routing-policy flip. Sources: [OpenDataLoader pipeline integration handoff](../handoffs/active/opendataloader-pipeline-integration.md), [progress 2026-07-06](../progress/2026-07/2026-07-06.md).

### New (2026-06-22, OpenDataLoader pipeline Phase 2 landed; hybrid-table routing still open)

- **ODL structured extraction is wired and Phase 2 is complete, but the hybrid-table path remains unbuilt (Phase 3 open).** Phase 1 wired ODL behind default-off adoption gates (`PDF_EXTRACTOR=opendataloader`, `ORCHESTRATOR_ODL_STRUCTURED=1`); Phase 2 (2026-06-21) landed the `ODLStructuredDocument` model, a structured-metadata injection scanner, heading-aware chunking, a table carrier (`TableRef`), figure-bbox replacement, and a default-off document-body warning policy (`ORCHESTRATOR_DOCUMENT_BODY_INJECTION_POLICY=warn`). Phase 3 (hybrid table sidecar/client, opendataloader-bench integration, three-way simple→hybrid→LightOnOCR routing) is still scoped, not built. Intake adds LiteParse (Rust, JVM-free, born-digital fast-path) as `adopt_component` and PaddleOCR-VL-1.6 GGUF benchmarking as deferred; adaptive-chunking (Ekimetrics) vs HOPE disagree on the cohesion signal and need a side-by-side eval. Source: [opendataloader-pipeline-integration.md](../handoffs/active/opendataloader-pipeline-integration.md).

- Current pipeline has NO table extraction -- pdftotext mangles tables, LightOnOCR outputs bboxes but no structured table data [opendataloader-pdf-pipeline-integration.md]
- OpenDataLoader local mode matches pdftotext latency (0.05s/page) while providing reading order (0.91), heading hierarchy, table detection, and figure bboxes [opendataloader-pdf-pipeline-integration.md]
- ODL hybrid achieves 0.90 overall / 0.93 table accuracy, #1 among all evaluated engines [opendataloader-pdf-pipeline-integration.md]
- XY-Cut++ algorithm: recursive segmentation extended with pre-mask processing, multi-granularity segmentation, hierarchical mask mechanism, cross-modal matching. 98.8 BLEU on DocBench-100 [arXiv:2504.10258]
- VL figure analysis is currently blind -- models receive cropped images without document context. This is the single highest-value improvement from ODL integration [opendataloader-pipeline-integration.md]
- ODL local mode is rule-based (XY-Cut++), not ML -- no GPU needed, deterministic output, no weights to convert [opendataloader-pdf-pipeline-integration.md]
- Safety features include hidden text filtering, off-page content removal, and optional PII sanitization [opendataloader-pdf-pipeline-integration.md]
- Java SDK spawns JVM per convert() call -- sidecar pattern or persistent subprocess recommended [opendataloader-pipeline-integration.md]
- The 200-PDF opendataloader-bench dataset (MIT license) could be added to EPYC benchmark infrastructure for reproducible comparisons [opendataloader-pipeline-integration.md]
- neural-txt (intake-718) is a CPU-cheap 135M task-specialist + Outlines constrained-decoding harness for structured NLP (bullets / Q&A pairs / KG triplets) — but it is a CONDITIONAL watch-item with NO live consumer slot: `document_formalizer` is a 1B OCR VLM and the ODL pipeline has no cheap structured-NLP-extraction stage today. Re-surface only if such a stage appears. Educational repo, no benchmarks (observations) [opendataloader-pipeline-integration.md, intake-718]

## Actionable for EPYC

- **Phase 1 (small effort, immediate gains)**: Replace `pdftotext -layout` with `opendataloader_pdf.convert(format="markdown,json")` in `src/services/pdf_router.py`. Keep quality check logic on ODL output. Requires `pip install opendataloader-pdf` and Java 11+.
- **Phase 2 (medium effort, biggest win)**: The gated structured consumer path is wired: enrich VL model prompts with figure semantic type, caption, surrounding text, and heading position from ODL JSON; replace PyMuPDF figure extraction with ODL bboxes; use heading hierarchy instead of regex when present; carry ODL table metadata through preprocessing/cache/TaskIR output; suppress unsafe ODL structured metadata under `INJECTION_SCANNING`; expose a default-inert `ORCHESTRATOR_ODL_TABLE_BACKEND` seam; and expose default-off body warnings through `ORCHESTRATOR_DOCUMENT_BODY_INJECTION_POLICY=warn`. Remaining work: implement the real ODL hybrid table sidecar/client path for 0.93 accuracy.
- **Phase 3 (medium-large effort)**: The sidecar is now live, so the remaining work is benchmark-backed comparison and routing policy. Experiment with swapping hybrid backend to LightOnOCR-2-1B (already running). Implement three-way routing: ODL local (simple) -> ODL hybrid (tables) -> LightOnOCR (scanned) only if the comparison justifies it. Clone opendataloader-bench, add EPYC pipeline as custom engine, run 200-PDF comparison.
- **Document-specialist comparison (new)**: run the guarded PaddleOCR-VL producer against LightOnOCR and ODL on the same structural/table/reading-order corpus, and treat the current HTML/post-processing path as a baseline to beat rather than a solution.
- **Benchmark integration**: the committed `odl_bench` package scores structural text edit distance, table TEDS, reading-order edit distance, and speed. NID/MHS are in the sibling document-extraction adapter and must be explicitly bridged or co-reported when the parent contract uses those names.
- **JVM management**: Pre-warm JVM in persistent subprocess or run ODL as sidecar service on dedicated port.

## Open Questions

- JVM cold start cost -- can we pre-warm via persistent subprocess and what is the startup latency?
- Does the Python SDK support single-page processing, or only whole documents?
- Is the JSON output schema versioned and stable across ODL releases?
- Can LightOnOCR-2-1B serve as the ODL hybrid backend (replacing docling-fast) and would GPU-accelerated OCR beat 0.43s/page?
- What is JVM heap usage for large documents (100+ pages)?
- How does SmolVLM 256M (in ODL hybrid) compare to our Qwen2.5-VL-7B for chart/image description?

## Related Categories

- [Multimodal](multimodal.md) -- Vision pipeline benefits from structured document context; figure analysis is a shared concern
- [Search & Retrieval](search-retrieval.md) -- Better document parsing improves downstream retrieval quality
- [Tool Implementation](tool-implementation.md) -- PDF router is a core orchestrator service

## Source References

- [OpenDataLoader deep dive](/workspace/research/deep-dives/opendataloader-pdf-pipeline-integration.md) -- XY-Cut++ algorithm, benchmark results, four integration strategies, technical considerations
- [OpenDataLoader pipeline integration handoff](/workspace/handoffs/active/opendataloader-pipeline-integration.md) -- Three-phase plan, work items, benchmark suite integration
- [Progress 2026-07-17](/workspace/progress/2026-07/2026-07-17.md) -- PaddleOCR-VL producer proof, negative HTML-table prompt result, and post-processing rescore checkpoint
- [K35 optimized stack throughput/context report](/workspace/research/deep-dives/k35-optimized-stack-throughput-context-report-2026-07-17.md) -- Consolidated MiniCPM-o/PaddleOCR-VL document-specialist evidence and the current table-gap framing
- [intake-161](https://github.com/opendataloader-project/opendataloader-pdf) OpenDataLoader PDF -- Initial intake evaluation
- [arXiv:2504.10258] XY-Cut++ paper -- Algorithm details, DocBench-100 results
- [intake-718](https://github.com/avbiswas/neural-txt) neural-txt (AVB) -- 135M structured-NLP specialist + Outlines constrained decoding; conditional watch-item, no consumer slot, no benchmarks

## ODL structured-output Phase 2 scaffolding (2026-05-06)

Phase 1 of the ODL integration (markdown-only extraction via `_extract_with_opendataloader()`) landed via NIB2-13. Phase 2 — wiring ODL's structured JSON output into figure-analyzer + chunker — landed 2026-05-06 as additive scaffolding, then gained end-to-end producer/consumer follow-ups on 2026-06-21. Existing pdftotext/PyMuPDF/regex-chunker paths are unchanged when `ORCHESTRATOR_ODL_STRUCTURED` is unset.

New module `epyc-orchestrator/src/models/odl_structured.py` defines a normalized layer over ODL JSON: `ODLBoundingBox`, `HeadingNode` (with `build_heading_tree` + `flatten_heading_tree` walkers), `FigureContext` (bbox + semantic_type + caption + surrounding_text + heading_breadcrumb), `TableContext`, and `ODLStructuredDocument.from_json()` that tolerates partial/missing keys across ODL versions.

`pdf_router.py` gains `_extract_with_opendataloader_structured()` — invokes ODL with `format=["markdown","json"]` into a temp dir, parses both outputs, returns `(text, ODLStructuredDocument | None, latency_ms)`. `PDFExtractionResult` gains an optional `structured_data` field (default `None` preserves back-compat). The routing path adds an `ORCHESTRATOR_ODL_STRUCTURED=1` gate that opts into the structured path; falls through to pdftotext on empty ODL output. As of `epyc-orchestrator` `fa1b5460`, `PDFRouter.extract_opendataloader_structured()` also owns the table-backend selection seam. `ORCHESTRATOR_ODL_TABLE_BACKEND=hybrid` is accepted as an explicit future request but falls back to local structured ODL until a sidecar/client exists.

`figure_analyzer.py` gains additive helper `build_figure_prompt_with_context(base_prompt, figure_context)` that folds heading breadcrumb + semantic_type + caption + surrounding_text into the VL prompt when a `FigureContext` is supplied; returns base prompt unchanged when `None`. Existing `FigureAnalyzer` class untouched.

`document_chunker.py` gains additive helper `chunk_by_odl_headings(text, structured_doc, max_section_length=10000)` that slices markdown text at ODL-detected heading boundaries instead of regex matches, with paragraph-boundary sub-split for long sections and a single-section fallback when the structured doc has no headings.

`document_preprocessor.py` now consumes optional structured metadata from TaskIR or local ODL PDF extraction. It passes safe structured headings into chunking, forwards figure contexts into VL analysis, emits table summaries into enriched TaskIR, and suppresses unsafe ODL structured headings/figures/tables when `INJECTION_SCANNING` is enabled. The structured-metadata suppression remains separate from primary OCR text. Primary body text defaults to source behavior, while `ORCHESTRATOR_DOCUMENT_BODY_INJECTION_POLICY=warn` adds page-level injection warnings without mutating or blocking extracted body content.

Sources: [`handoffs/active/opendataloader-pipeline-integration.md`](../handoffs/active/opendataloader-pipeline-integration.md), `epyc-orchestrator/src/models/odl_structured.py`, `epyc-orchestrator/src/services/pdf_router.py`, `epyc-orchestrator/src/services/document_preprocessor.py`, `epyc-orchestrator/tests/unit/test_odl_structured.py`.

## LiteParse — JVM-free born-digital fast-path candidate (2026-05-29)

LiteParse (run-llama/LlamaIndex, Apache-2.0, intake-646 blog / intake-647 repo) is a pure-Rust document parser that occupies a **different design point** from OpenDataLoader and is a *complement, not a replacement*. Deep dive: [`research/deep-dives/liteparse-document-parser-deep-dive.md`](../research/deep-dives/liteparse-document-parser-deep-dive.md).

- **Deployment win vs ODL**: the custom PDFium fork + tesseract-rs are compiled into a self-contained ~13 MB manylinux x86_64 wheel (glibc 2.28+, Py 3.10–3.15). On EPYC, `pip install liteparse` needs **no JVM and no system PDFium/tesseract build** — sidestepping ODL's Java 11+ per-`convert()` JVM-spawn cold-start. LibreOffice (Office→PDF) + ImageMagick (image→PDF) + tessdata are conditional and untouched on the born-digital path.
- **Algorithm**: spatial-grid projection ("preserve layout, don't detect structure") — tables emitted as positioned ASCII-grid text, NOT a markdown table DOM. Output = text + per-item bboxes (viewport 72-DPI `x/y/w/h`, top-left — needs an adapter vs ODL's PDF-point corner-pairs) + page PNGs. **Reading order is implicit; no heading-hierarchy, table, or figure-semantic-type objects.**
- **Why it is NOT an ODL replacement**: it cannot supply Phase 2's structural context (headings → chunker, table DOM, figure semantic-type + caption → VL). It competes with `pdftotext` for the Phase 1 born-digital slot only; ODL stays for structure. Vendor concedes complex/dense-table/scanned/multi-column docs need LlamaParse-cloud-class quality (our equivalent = ODL + VL-OCR).
- **Maturity / credibility**: 6.8k★ / 425 forks / 600 commits / 46 releases, v2.0.3 @ 2026-05-28; real 3-OS CI + HF regression suite + LLM-judge eval framework. Speed claims (457pg/100 MB in 0.777 s; 5–100× small / ~3× large vs the prior Node version) are vendor self-reported and **speed-only — no independent accuracy benchmark** (NID/TEDS/OmniDocBench); its non-markdown output fails standard OCR benchmarks by construction, so a LiteParse-output-aware harness is required for head-to-head scoring.
- **Gated next action**: bench LiteParse-local vs ODL-local vs pdftotext on the born-digital corpus (text fidelity, JVM-free cold-start + RSS, multi-column reading order) under the opendataloader-pipeline-integration handoff (P1b). Verdict: 647 = adopt_component (born-digital fast-path backend), 646 = worth_investigating.

Sources: [`research/deep-dives/liteparse-document-parser-deep-dive.md`](../research/deep-dives/liteparse-document-parser-deep-dive.md), [`handoffs/active/opendataloader-pipeline-integration.md`](../handoffs/active/opendataloader-pipeline-integration.md), [`handoffs/active/pipeline-integration-index.md`](../handoffs/active/pipeline-integration-index.md), intake-646/647.

## neural-txt — cheap structured-NLP specialist, no consumer slot yet (2026-06-20)

neural-txt (AVB, intake-718) is a CPU-cheap **135M task-specialist LM paired with an Outlines constrained-decoding harness** for structured NLP extraction — bullet-point summaries, Q&A pairs, and knowledge-graph triplets. It is the closest research candidate to a "cheap structured-extraction stage" the ODL pipeline could theoretically grow, which is why it is tracked here rather than dismissed.

- **Verdict: CONDITIONAL watch-item — NO live consumer slot today.** The ODL/LightOnOCR pipeline has no cheap structured-NLP-extraction stage, and `document_formalizer` is a 1B OCR VLM (a different design point entirely). There is nothing in the current pipeline that would route work to a 135M structured-NLP specialist. Re-surface this entry ONLY if such a stage appears in the pipeline (e.g. a post-OCR triplet/Q&A extraction step feeding a KB or RAG index).
- **Constrained-decoding is the transferable part**: the Outlines-style schema-constrained decoding harness (guarantee well-formed bullets / KG-triplet JSON without post-hoc parsing) is the engineering pattern worth remembering even though the 135M weights themselves have no slot — it is the same reliability lever as the privacy-parser/PII-span work tracked elsewhere in this handoff (intake-449/452), applied to extraction output rather than masking.
- **Confidence: external — educational repo, no benchmarks.** All capability claims are observations (no decision-grade numbers); do not gate any pipeline change on neural-txt figures. Its reward-model reranking half (NeuralTxtReward / neuraltxt-reward-tiny) is folded into intake-719 / the AVB offline-reward digest, not duplicated here.

Sources: [`handoffs/active/opendataloader-pipeline-integration.md`](../handoffs/active/opendataloader-pipeline-integration.md) (Research Intake Update 2026-06-20), intake-718.
