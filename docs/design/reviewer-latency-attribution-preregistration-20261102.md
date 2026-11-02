# LB-1 attribution analysis plan — 2026-11-02

Status: preparation; no replay or result. The official LB-1 replay is the RCP-W2 execution in `handoffs/active/bulk-inference-campaign.md`, subject to its OP-6 and anti-double-run conditions. This plan does not authorize a second run or change the measurement constitution. Freeze the corpus, seeds, sampling configuration, software/model/kernel identities and analysis version before exposure; record any departure and treat it as exploratory.

## Question and observations

On the same 50 replay questions, compare shadow OFF and ON, preserving per-question pairing. Capture each request's question and trace identifiers, call class, actor, prompt token count (and bytes if available), completion tokens, enqueue/start/end timestamps, outcome and retry/attempt identity. Record evaluation wall-clock and successful question count for each arm. Count logical reviews separately from actual HTTP attempts, including failures and retries; missing or ambiguous identities must be reported, not silently merged or counted twice. Preserve the raw events and clock source. Model and runtime identities, instrumentation version and era accompany the results.

For each arm report paired per-question call counts and prompt-token distributions by class, service time and queue wait distributions, failures/missingness, and task rate (successful questions per evaluation wall-hour). Queue wait requires timestamps at the actual queue boundary: client elapsed time minus service time is not a substitute. Queue durations spanning unsynchronized clocks are unavailable unless clock alignment is established. Compare elapsed times and token volumes by call class without summing overlapping durations as if they were wall-clock contributions.

## Prespecified interpretations

- **Call-count hypothesis:** the ON arm adds plan-review logical calls or HTTP attempts per question, and their measured service demand accounts for a substantial observed increase in evaluation time. Report both counts and measured service demand; a count increase alone does not establish dominance.
- **Prompt-length hypothesis:** ON plan-review requests carry greater prompt token volume per comparable review than OFF, or than the prespecified reference if OFF has no plan-review calls, with correspondingly greater measured service demand. When there is no comparable OFF call class, report the added prompt volume and duration descriptively; do not claim a paired prompt-length effect.
- **Architect-queue hypothesis:** measured architect queue wait increases on paired ON questions and is a substantial component of the observed latency change. If enqueue/start timestamps are missing, queue attribution is unmeasured, even when client latency increases.

Report the three components together, including overlaps and uncertainty; do not declare a single dominant cause solely from correlations or missing fields. If the timing instrumentation cannot distinguish service, queue and overlap, report the compatible explanations and missing evidence. The old July anchor is historical: a fresh replay can characterize the current system but cannot by itself prove the cause of that earlier regression.

## Before execution

The campaign owner must specify the exact paired arms, frozen question IDs and seeds, model and runtime configuration, instrumentation and analysis commits, baseline/reference for prompt comparisons, and the sequential or fixed-sample analysis required by the applicable measurement protocols. Validate event accounting, trace joins and missing/failed-request handling on synthetic fixtures before exposure. Capture write-side belief provenance at production time under the existing REV-06 source task; no retrospective measurement warrant. The separately scoped synthetic-plan diagnostic is not the RCP-W2 replay and cannot close LB-1.
