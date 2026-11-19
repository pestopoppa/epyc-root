# KVU-16a sampled load and stack package reconciliation — 2026-11-02

This is a source/evidence reconciliation, not a registry amendment, runtime peak, or proof of
the current live process. It used research `7ac65aecf3ffc761a8818101c93ce8f38a8505ec` and
orchestrator `f678231cb31c2898a1ff7ab8cb9fd183e50e7604`. Both heads and the owning session's
live stack must be re-resolved when a package is prepared.

## What matches and what does not

The retained [result](result.json), [raw samples](samples.jsonl), [server log](server.log),
[model receipt](model-receipt.json) and [linkage receipt](linkage-0.txt) document one isolated
load. They show the production-store GPU image, four slots, unified KV, total context 393216,
batch/ubatch 512, q8_0 K and V, and DFlash2 at depth 7. The target GGUF digest in the receipt
matches research master `roles.qwen38_27b_q8_local.model.sha256`; the served template digest
matches the compiled orchestrator registry. `runtime.sha256` at the retained source directory
rechecked against the current kernel store, but that is not an independent runtime mapping proof.
The server log reports target KV 13056 MiB (12.75 GiB) and a separate drafter KV allocation;
the calculation subtracts only the target KV.

The **configured** `server_mode.architect_critic` in orchestrator
`orchestration/model_registry.yaml` specifies `cache_idle_slots: false`; the recorded argv has
no `--no-cache-idle-slots`. This is an argv discrepancy. Neither the registry nor the isolated
sample establishes the live process's effective setting, and the discrepancy's effect on load
memory is not measured. Compare a fresh owner-provided production launch with its own image,
model and effective environment; do not infer that these shapes are equivalent. Other flags and
their effective values also need a complete normalized comparison, not just the subset above.

The result's maximum sampled own-PID load is 51,338,338,304 bytes = 47.812553 GiB; less the
observed target KV gives 35.062553 GiB. Nineteen raw samples span startup, including two after
health as stated by the producer; raw `phase` is `unknown` and intervals are not uniform. The
sample maximum is an observation, not proof of an unsampled load maximum or the serving runtime
peak. It cannot justify replacing the master scalar or reducing its runtime capacity allowance.
The model receipt pins target `a680f44a…b67e348` and drafter `7f1c9a31…9153751`; the linked
receipt names the production library path. The result records birth-identified cleanup verified.

Research master `orchestration/model_registry.yaml:1736` and the compiled orchestrator
`orchestration/model_registry.yaml:2006` both carry **38.03 GiB**, derived for ubatch 512. The
numerically equal 38.03 GiB in the 2026-10-03 hygiene package was measured at ubatch 2048;
numeric equality does not make the current value a shape-matched measured value. Runtime growth
remains KVU-16i's separate obligation.

## Package state and next concrete work

The old `/mnt/raid0/llm/tmp/stack-change-hygiene-20261003/` bundle combines KVU-16a with
SCG-PRIORS-WARM and DRAFT-SEL-2. Its research patch fails `git apply --check` against research
`7ac65aecf`; it is not a current executable ratification package. Do not reuse its old pins,
signature request or three-task assumptions. Its orchestrator patch applied in a read-only
`git apply --check` against the shared worktree, not a clean current-head checkout; this does not
establish semantic applicability or integration status.

1. At the next authorized boundary, pin both current source heads, the owner-approved actual
   :8083 argv and environment, model/template hashes, production image and all mapped ggml DSOs.
   Normalize only port and slot directory; resolve every other difference, including idle-slot
   policy, batch and ubatch, before claiming shape identity.
2. Prepare a successor load-only producer which samples the process through load and health with
   timestamps and phase boundaries, preserves every sample and missed interval, binds process
   birth identity and mapped libraries, and verifies target KV and cleanup. Predeclare the
   sampling rule and scope of the reported maximum. A sampled maximum remains a sampled maximum.
   Request the applicable GPU/resource grant and obey the operator's current inference/compute
   instructions; do not repurpose the November 2 receipt as a new observation.
3. Reconcile the resulting load observation with KVU-16i's runtime capacity evidence and the
   stack's actual capacity convention. Stage an evidence-linked research-master candidate only
   if the value is supported for the declared shape; generate the lean registry and run the
   current stack-change pipeline's validation in isolated checkouts. Keep original results and
   unknowns intact. Inspect SCG-PRIORS-WARM and DRAFT-SEL-2 against current code separately;
   do not blindly replay the historical bundle.
4. Present the exact current-head patch, compiled delta, validation output and any required
   operator signature as one reviewable package. Do not change a live registry or restart a
   service while preparing it.

Receipt SHA-256: result `dc96006f5f77accf411ccf9eccf3b0702e01c6fdc8183cc43d61385b4cd71d36`,
samples `1125d60cd820d0e5bcc5c3cea3a1c10ba215a0c5553543592bcc38dc00ff4dc0`, server log
`c92dd76f8842efb3f03f42f5742713d51221bd3f1c2bf2f2b8ef86a0bde27cce`, model receipt
`42d05e6400e73d4618a84ec739bee0d00d62f3d4509f01b7534e38efbc74b078`.
