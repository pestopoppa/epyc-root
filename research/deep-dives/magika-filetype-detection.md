# Deep Dive: Magika — AI-Powered Content-Type Detection

**Date**: 2026-04-17
**Intake ID**: intake-398
**Source**: [google/magika](https://github.com/google/magika)
**Paper**: [arXiv:2409.13768](https://arxiv.org/abs/2409.13768) — Fratantonio et al., ICSE 2025
**PyPI**: [magika 1.0.2](https://pypi.org/project/magika/) (2026-02-25, Apache 2.0)

---

## 1. Model Architecture (From the Paper)

Contrary to the "small CNN" framing in several reviews (and in our own initial intake note), **Magika does not use convolutional layers.** The model is a shallow byte-embedding MLP with global pooling.

| Component | Detail |
|---|---|
| Input | Three fixed 512-byte windows: beginning, middle, end of file |
| Whitespace | Stripped from leading/trailing before window selection |
| Padding | Special token `256` when file is shorter than window |
| Byte embedding | Dense layer, one-hot byte -> 128-dim vector |
| Reshape | To 384 x 512 "to effectively reorganize into four-byte chunks" |
| Trunk | Two 256-d Dense layers with GELU activation |
| Pooling | Global max-pool for size invariance |
| Head | Dense + softmax, output dim = class count |
| Regularization | Layer norm, 10% dropout, 10% spatial dropout |
| **Total weights** | **~1 MB on disk** |
| Classes (v1 paper) | 113 canonical content types (70 binary, 43 text) |
| Classes (v1.0.2) | "200+" per repo README |

No recurrence, no attention, no convolution — just a wide MLP trained to map fixed-size byte prefixes/suffixes to class logits. Global max-pool over the reshape axis provides coarse position invariance across the byte window.

### Training Data
- ~24 M training samples (initial release); README now cites ~100 M for current model.
- Stratified, capped at 1 M per class; minimum ~10 K per class. `iso` and `odp` classes trained on ~14 K.
- Sources: GitHub and VirusTotal.
- Validation + test: 1.2 M files each (1 M+ held-out, ~10 K per type).

### Threshold Mechanism
Per-class confidence thresholds are calibrated on validation to **fix precision at 99% and maximize recall**. Below threshold, the classifier falls back to `txt` or `unknown` depending on which class it was most confident about. This is how the paper reports "99% F1" without claiming 99% accuracy on arbitrary input — it is a high-precision classifier that *abstains* when unsure.

### Synthetic OOD Data
Two synthetic classes injected during training: `unknown` (random byte sequences) and `txt` (random printable text). Reported F1 on these synthetic buckets: 94% and 84% — far below the 99% headline, and a direct warning that anything not in the trained vocabulary is a coin-flip.

### Inference Cost (Paper's Own Numbers)

| Scenario | Magika | `file` (libmagic) |
|---|---|---|
| Single file (cold) | 86.73 ms | 5.36 ms |
| Bulk, amortized, 1 CPU | 5.77 ms/file | 0.75 ms/file |
| Bulk, 8 CPUs | 1.39 ms/file | — |

The 86.73 ms single-file number is the model-load cost dominating. Amortized, **Magika is ~7.7x slower per file than libmagic on a single CPU.** The HN critique that the original comparison used multi-core inference is consistent with what the paper itself reports: parity requires threading.

### Paper-Admitted Weak Spots
- Degrades on files shorter than ~100 bytes (not enough byte window to classify confidently — usually falls back to `txt`/`unknown`).
- No polyglot handling in v1.
- Unknown/OOD synthetic F1 of 94% means **~6% of truly unseen formats get confidently misclassified**, matching the anjackson.net review observations (MOV -> MP4, MPEG -> ICO).

---

## 2. Live Measurements on This Box

Installed `magika==1.0.2` in a fresh venv on the EPYC host and measured against a synthetic EPYC-like corpus:

| Metric | Value |
|---|---|
| `import magika` | 206.4 ms |
| `Magika()` construct | 18.3 ms |
| **Total cold-start** | **224.8 ms** |
| 6-file identification | 16.7 ms total -> 2.8 ms/file |
| Installed package size (Linux x86-64) | **3.23 MB** |
| Wheel download | 15.9 MB manylinux, 3.0 MB universal-sdist |
| Runtime dep | onnxruntime (the 15.9 MB wheel bundles the ORT session) |

Per-file latency (2.8 ms) matches the paper's amortized 5.77 ms within 2x — better than advertised, actually, on this hardware. **But the 225 ms cold-start matters**: for one-shot ingest of a single document, Magika's total cost is ~230 ms vs libmagic's ~5 ms.

Accuracy on EPYC-style inputs:

| Input | Magika verdict | Notes |
|---|---|---|
| Markdown README | `markdown` | Correct |
| HTML blog snippet | `html` | Correct |
| **JSON** | **`jsonl`** | **Minor misclass** — JSONL is line-delimited JSON, not the same thing |
| Python source | `python` | Correct |
| YAML config | `yaml` | Correct |
| Plain text | `txt` | Correct |

5 of 6 correct on a canonical corpus. The JSON/JSONL confusion is a real-world example of the "confident-but-wrong on closely-related formats" pattern that caveats in the intake flagged.

**libmagic / `file(1)` was not available on the EPYC host** (no `/usr/bin/file`, no `libmagic.so` in the system), so a live head-to-head is not possible here. All libmagic numbers are from the paper.

---

## 3. Expected Accuracy on EPYC's Actual Corpus

EPYC's research-intake input is **not** an arbitrary byte sequence: it is URL-fetched content where the format is already known from URL/MIME/extension.

| Input source | Actual format distribution | How format is known today |
|---|---|---|
| arXiv paper | PDF (100%) | URL pattern: `arxiv.org/pdf/...` or `/abs/...` |
| GitHub README | Markdown (100%) | Fetched via `gh api` or `raw.githubusercontent.com/.../README.md` |
| HTML blog post | HTML (100%) | Content-Type header from HTTP response |
| HuggingFace model card | Markdown (100%) | Fetched as `README.md` from repo |
| Uploaded PDFs to orchestrator | PDF (100%) | Extension + magic-bytes sniff is trivial |

**This is a five-format, homogeneous, already-labeled corpus.** The hard problem Magika solves (what is this arbitrary blob? is it one of 200 things?) is not a problem EPYC has. The interesting formats Magika helps with — binaries, malware samples, reverse-engineering blobs, exotic compression — are entirely absent from the intake pipeline.

Expected false-positive rate of a trivial classifier (extension + a 4-byte PDF/HTML magic check) on this corpus: **essentially 0%**.

Expected false-positive rate of Magika: also near-zero — but with a non-trivial tail of cases like the JSON/JSONL confusion above, plus the paper-admitted OOD failure modes.

---

## 4. Comparison with OpenDataLoader and libmagic

### OpenDataLoader's built-in filetype handling
OpenDataLoader PDF is, by construction, a **PDF-only** parser. It takes PDFs in, produces Markdown/JSON/HTML out. It does **not** do generic content-type detection — the caller already knows the input is a PDF. The question "does ODL make Magika redundant?" is malformed: they solve different problems.

The real question is: **in the orchestrator's document-ingestion path, is there a stage that needs generic filetype detection?** Reading `pdf_router.py` and `document_preprocessor.py`:

- `pdf_router.py` accepts a file whose caller has already decided it is a PDF. It then routes between `pdftotext` (born-digital) and LightOnOCR (scanned) based on *content quality*, not *file type*. Magika wouldn't help here — the file is already typed, the question is whether the PDF is extractable vs scanned.
- `document_preprocessor.py` orchestrates the chunker/figure analyzer over an already-extracted document. Filetype detection does not appear in the call graph.
- Fetchers (`tools/web/fetch.py`, `tools/web/research.py`) rely on HTTP `Content-Type` headers and URL patterns. These are reliable for our sources.

**There is no current stage in the pipeline where Magika would insert value.** The intake note's recommendation — "pre-parse triage stage" — is hypothetical: no such stage exists, and adding one would be solving a problem we don't have.

### libmagic comparison (apples-to-apples)
| Property | libmagic | Magika |
|---|---|---|
| Install footprint | 2-5 MB (system package) | 15.9 MB wheel, 3.2 MB on disk + onnxruntime |
| Cold-start | <1 ms | 225 ms (onnxruntime init) |
| Per-file latency (1 CPU) | 0.75 ms | 2.8-5.77 ms |
| Per-file latency (multi-CPU) | — (single-threaded in practice) | 1.39 ms |
| Class coverage | ~1700 magic rules | 200+ trained classes |
| False-positive mode | silent when rule missing | confident wrong answer (per anjackson) |
| Threading | CPU-bound, usually 1 thread | ORT session can use multi-core |
| OOD handling | returns generic `data` | returns `txt`/`unknown` below threshold |

libmagic is strictly faster per file and has negligible cold-start. Magika's advantage is textual-format discrimination (Python vs Ruby vs JS source, which libmagic struggles with) and confidence scores. **Neither strength is useful for EPYC's five-format corpus.**

---

## 5. Integration Cost

If we *did* integrate Magika:

| Cost item | Magnitude |
|---|---|
| Python dep add | `magika>=1.0.2` -> pulls `onnxruntime` (~80 MB) |
| Cold-start amortization | Need a persistent process; fine for orchestrator, bad for CLI one-shots |
| GPU device-discovery warning on boot | Harmless but noisy: `ReadFileContents Failed to open file: "/sys/class/drm/card0/device/vendor"` |
| API churn | v1.0.2 already broke the `score` field vs earlier examples — six `Unsupported field error` warnings appeared in our test when copy-pasting the README example. This is a young, churning API. |
| Model-weight distribution | Bundled in wheel — no runtime download, no licensing concern (Apache 2.0). |
| Maintenance | Classes evolve across releases; misclassification profile will drift. |

**Total delta to EPYC**: ~80 MB of dependencies and 225 ms of cold-start to replace 4 lines of Python that do `if url.endswith(".pdf"):` with something that adds no measurable accuracy on the actual corpus.

---

## 6. Recommendation: **Skip.**

Magika is a genuinely interesting piece of applied ML — a 1 MB model that beats libmagic on text-format discrimination across 200 classes, with clean abstention semantics. For Gmail attachment scanning or VirusTotal triage (its actual deployment targets), where the input is truly arbitrary and adversarial, it earns its place.

For EPYC, it is a solution searching for a problem. Our document-ingestion pipeline operates on:
1. Known-format URL fetches (arXiv PDF, GitHub MD, HTML blogs, HF model cards) where the format is declared.
2. User-uploaded files where extension + a 4-byte magic check catches every realistic case.

Adding an 80 MB dependency, 225 ms cold-start, and a stochastic misclassifier (see JSON -> jsonl above) to a pipeline that currently has zero filetype confusion is pure negative value. The opendataloader handoff's document-ingestion plan has no stage where Magika would insert.

**Only reconsider if** we start ingesting truly arbitrary binary corpora (malware samples, forensic dumps, user-uploaded archives with unknown extensions). That is not on any current roadmap.

### What Magika is good for — that we aren't doing
- Large-scale scanning of heterogeneous file dumps (Gmail, VirusTotal).
- Source-code language classification inside a file where extension is missing.
- Security pipelines where adversaries rename files to evade extension-based rules.

None of these describe EPYC.

---

## 7. Verdict Delta

| Field | Initial intake | Post-deep-dive |
|---|---|---|
| Novelty | medium | medium (confirmed — shallow MLP, not CNN, but genuinely small) |
| Relevance | low | **not_applicable** |
| Credibility | 4 | 4 (paper is solid, deployment is real) |
| Verdict | worth_investigating | **not_applicable** |

**Recommended intake-index update**: downgrade `intake-398` verdict from `worth_investigating` to `not_applicable` with rationale "EPYC's document-ingestion corpus is known-format URL fetches; no pipeline stage requires generic filetype detection. Paper is interesting, tool is not useful here."

**Recommended handoff update**: remove the "Research Intake Update — 2026-04-17" section from `opendataloader-pdf-pipeline-integration.md`, or condense it to a single "evaluated, skipped" line referencing this deep dive.

---

## 8. Artifacts Reviewed

- arXiv:2409.13768 full HTML (model architecture, training, benchmarks)
- https://github.com/google/magika (README, usage, scope)
- https://pypi.org/project/magika/ (wheel sizes, versions, deps)
- `/mnt/raid0/llm/epyc-root/handoffs/active/opendataloader-pdf-pipeline-integration.md`
- `/mnt/raid0/llm/epyc-root/research/deep-dives/opendataloader-pdf-pipeline-integration.md`
- `/mnt/raid0/llm/epyc-orchestrator/src/services/pdf_router.py`
- Live measurements: magika 1.0.2 installed in `/tmp/magika_test/.venv` on this EPYC host.
