<!-- RATIFIED 2026-08-23T08:28:26Z by operator ratification (scripts/operator/ratify_measurement_annex_d_20260823.sh).
     Annex D of MEASUREMENT.md (same trust boundary, same amendment rules).
     Determinism / output-parity protocol family.
     SCOPE OF THIS RATIFICATION: the ANNEX is created. Its two protocols are registered
     in MEASUREMENT.md section 2 as STAGED, not ratified -- no measurement has yet been
     taken under either, and none may be quoted as ratified until one has. -->

# Annex D — Determinism & output-parity protocols

Two protocols. `P-PARITY-1` answers *"do these two decode configurations produce the same tokens?"*
`P-NONDET-1` answers the prior question *"does either of them produce the same tokens as itself?"* —
which must be settled first, because a harness that never repeats a call cannot tell a real
divergence from run-to-run noise.

Both emit a **verdict**, not a rate. Neither is a speed protocol and neither may be quoted beside a
throughput figure.

## P-PARITY-1 — Greedy-output parity between two decode configurations

**Scope.** Any claim of the form "configuration A produces the same output as configuration B" where
the factor under test is a decode-path change: a speculative-decoding type or depth, a KV cache
type, a kernel route, a drafter, a batching mode. **Not** for comparing two different models, two
different weight quantizations, or two prompts.

**Metric.** Per-prompt `PASS` / `FAIL`, plus the **index of the first differing generation token** on
every `FAIL`. **Direction: not applicable — this is a verdict, not a scalar.** An aggregate pass
rate is **not** the metric and MUST NOT be reported as one (see *Reporting*).

### Instrument

- **n >= 5 prompts, minimum, non-negotiable.** A single-prompt parity check returns a false clean
  sheet at a measured rate near 50%: the same upstream reporter went 1/5, then 0/5, then 4/5
  depending on prompt and patch, and one arm was byte-identical on one workload and divergent on the
  other. **A 1-prompt parity result is not a P-PARITY-1 result and may not be labelled as one.**
- **Greedy only.** `temperature 0`, fixed seed, sampling otherwise held identical across arms.
- **Two independent comparison keys, both reported:**
  1. **Stripped-output MD5** — hash of the generated text with the startup banner and the prompt
     echo removed. Removing them is part of the instrument; a hash over unstripped output compares
     the banner.
  2. **Normalized-identity SHA-256** over the tuple `{content, reasoning_content, token_ids}`. This
     catches a divergence that renders to identical text — the case a text hash cannot see.
- **First-divergent-generation-token index** via `llama-tokenize` **on the same vocabulary as the
  run**. It is the *generation* token index — not a character offset, not a prompt-inclusive index.
  A character offset is not comparable across arms.

### Preconditions

- **Fresh process per phase.** Measured: **1/5 divergences with a reused server versus 4/5 with a
  fresh process per phase**, *despite* `cache_prompt=false`. `cache_prompt=false` is **not** a
  substitute for a fresh process and must not be cited as one.
- **ABBA ordering.** Run A, B, B, A. Order effects and process-lifetime effects are both real here;
  ABBA separates them from the factor under test.
- **Explicit rerun-for-determinism.** Before comparing arms, each arm is run under `P-NONDET-1`
  below. **An arm that is not self-identical cannot be compared to anything**, and a parity failure
  measured against a non-deterministic arm is uninterpretable.
- **Confound control — quantized KV.** Run at `-ctk f16 -ctv f16` by default. Quantized KV **alone**
  moves greedy output with the factor under test disabled, so **any quantized-KV arm requires its
  own factor-disabled f16-vs-quantized baseline first**, or non-parity is unattributable.
- **Local-patch route capture (this fork specifically).** Frozen production carries EPYC-local commit
  `a6b4b5263` (`ggml/src/ggml-cuda/mmvq.cu:341-344`), which deliberately routes Q8_0 to a different
  kernel at `ne11 >= 2` and whose own commit message says it is *"numerically-valid (not
  bit-exact)"*. Capture `GGML_CUDA_LOG_MMVQ_ROUTE=1` on **every** arm (a runtime env var,
  `ggml-cuda.cu:1812-1814`, so no rebuild is needed) and report which kernel each batch actually
  took. **A reference arm that takes the same route as the arm under test is not a reference.** Note
  that the equivalent `N==1` vs `N>1` split exists on both CPU paths (`llamafile_sgemm`'s `mnpack`
  register blocking; iqk's `funcs[ny-1]` dispatch), so **batch invariance is not a property any of
  our three compute planes holds** — never assume it.

### Reporting

- **Per prompt: PASS/FAIL, both hashes, and the first-differing-generation-token index on a FAIL.**
- **NEVER an aggregate verdict.** "4/5 passed" is not a result; it is five results, and *which*
  prompt failed is the load-bearing part. An aggregate hides the prompt-dependence that makes n=1
  unsafe in the first place.
- Report the MMVQ route per arm alongside the verdict.
- A parity claim cites `[P-PARITY-1, n=<prompts>, <date>, attest <path>]` per MEASUREMENT.md §3.

### Decision rule

`PASS` on **all** prompts means parity holds **for those prompts, that model, that KV type and that
route** — a durable negative of exactly that scope and no wider. Any `FAIL` is **not** automatically
a defect in the factor under test: attribute it only after the reference arm, the KV baseline and
the route capture together exclude the alternatives. A `FAIL` whose reference arm took the same
kernel route is **unattributable** and is reported as such, not as a divergence.

## P-NONDET-1 — Run-to-run non-determinism detector

**Scope.** Establishing that a single configuration is self-identical, before it is compared to
anything.

**Metric.** Bit-identical / not, plus `max abs Δ` across the N repeats (**lower-better**;
bit-identical is the only passing value when used as a parity precondition).

### Instrument

- **Repeat the identical call N times inside ONE process** (N >= 10). Compare all N outputs to each
  other, not to a stored expectation.
- **A one-shape-per-fresh-process harness cannot run this protocol.** That harness sees a clean first
  call and clears a broken kernel — it is structurally blind to the phenomenon. Measured instance:
  ten identical backward calls in one process returned ten different answers, absmax compounding
  0.40 to 252.88, while the forward pass stayed bit-identical throughout.
- Where a numeric tensor is available, report `max abs Δ` across repeats; where only text is
  available, report the count of distinct outputs among the N.

### Decision rule

Not bit-identical across N means the configuration is **non-deterministic**, and **no parity,
regression or A/B claim may be built on it** until the source is found. Bit-identical across N means
the configuration is admissible as a `P-PARITY-1` arm, for that shape.

**Provenance.** Both protocols generalise the comparison methods and failure modes documented in
llama.cpp issues #27407 and #25618, plus the fla #1156 non-determinism case; adopted as our own
instrument by the wave-2 research-intake plan (row H22) and first consumed by
`handoffs/active/dflash2-block-drafter-experimental-build.md` DF2-6.
