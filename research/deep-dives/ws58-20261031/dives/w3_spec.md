# ws58 2026-10-31 dive record: w3_spec

Markdown rendering of `w3_spec.yaml` (the original is kept beside it) so the wiki scanner sees this dive. Intake IDs are as the dive recorded them; read them as `#record` references. Digit runs of 12+ digits are written grouped.

```yaml
{
 "new_entries": [
  {
   "id": "intake-2591",
   "arxiv_id": null,
   "url": "https://github.com/ggml-org/llama.cpp/issues/28286",
   "source_type": "repo",
   "title": "llama.cpp #28286: draft-mtp + --parallel > 1 causes cross-slot content contamination (Qwen3.8-Flash-Next, ROCm)",
   "categories": [
    "speculative_decoding",
    "inference_serving",
    "ssm_hybrid"
   ],
   "novelty": "medium",
   "relevance": "high",
   "discovered_via": "expansion",
   "expanded_from": "intake-2577",
   "verdict": "worth_investigating",
   "ingested_date": "2026-10-31",
   "authors": [],
   "key_claims": [
    "With --spec-type draft-mtp and --parallel 4 on Qwen3.8-Flash-Next (qwen4exp, a Gated-DeltaNet hybrid), temp-0 concurrent requests with distinct prompts produced responses that drifted into another slot's content; the reporter ruled out HIP graphs (GGML_CUDA_DISABLE_GRAPHS=1) and a client-side harness artifact.",
    "It does not reproduce at --parallel 1; low-entropy prompts (ROCKET vs BANANA x40) showed zero contamination, so the effect needs content complexity to surface.",
    "The issue was closed by the stale bot on 2026-10-18 with no root cause and no merged fix; the only linked candidate, PR #29454 (fill unwritten rollback snapshot slot on short ubatches), was closed unmerged on 2026-09-27 and its connection to #28286 is stated as unconfirmed.",
    "Environment was a downstream fork on master 458681e1d with the qwen4exp MTP integration, Strix Halo gfx1151 ROCm; not tested on a non-recurrent target."
   ],
   "techniques": [
    "draft-mtp",
    "draft-dflash",
    "recurrent-state rollback (n_rs_seq)"
   ],
   "reported_results": [
    "Issue has 1 comment (stale bot close); no fix PR; PR #29454 closed unmerged 2026-09-27 (issue28286.txt, pr29454.txt)"
   ],
   "cross_references": {
    "chapters": [],
    "handoffs": [
     "qwen-mtp-llamacpp-port.md",
     "dflash2-block-drafter-experimental-build.md",
     "cpu-decode-roofline-program.md"
    ],
    "experiments": [],
    "intake_entries": [
     "intake-2577",
     "intake-1513"
    ]
   },
   "recommended_actions": [
    "Run the temp-0 np>1 identity probe (ledger W3SPEC-1) on the production MTP/DFlash2 shapes."
   ],
   "credibility_score": null,
   "contradicting_evidence": null,
   "referenced_arxiv_ids": [],
   "notes": "GitHub issue; read via API (issue, comments, timeline).",
   "verification": "stage1-unverified",
   "handoffs_updated": [],
   "handoffs_created": [],
   "source_revision": "GitHub API ggml-org/llama.cpp issues/28286 (+comments, timeline, PR #29454) retrieved 2026-10-31; state closed(stale) 2026-10-18",
   "reader_should_conclude": "Stage-1 unverified: do not cite."
  },
  {
   "id": "intake-2592",
   "arxiv_id": null,
   "url": "https://github.com/ggml-org/llama.cpp/issues/28158",
   "source_type": "repo",
   "title": "llama.cpp #28158: Qwen3.8 DFlash/MTP speculative emits token id == n_vocab (248320) on Vulkan",
   "categories": [
    "speculative_decoding",
    "inference_serving",
    "ssm_hybrid"
   ],
   "novelty": "medium",
   "relevance": "medium",
   "discovered_via": "expansion",
   "expanded_from": "intake-2577",
   "verdict": "worth_investigating",
   "ingested_date": "2026-10-31",
   "authors": [],
   "key_claims": [
    "Qwen3.8-27B with --spec-type draft-dflash (z-lab DFlash2) or draft-mtp fails at the first target verify batch with 'invalid token[N] = 248320' (exactly n_vocab) and HTTP 500, reproduced on Vulkan only (gfx1150, gfx1201, gfx1100, 3x RX 6800); CPU control with the same GGUFs works.",
    "A commenter's controlled datapoint reproduced the byte-identical signature by injecting a Vulkan mul_mm tile-layout bug that leaves half of each prefill tile unwritten: the id is always exactly n_vocab, read as a sentinel emitted from NaN draft scores, not an out-of-bounds index; the OP's DFlash2 selector row had all 16 top-k slots at 248320 with NaN scores.",
    "The issue is still open with no maintainer root cause; the only fix PR (#28206) was an AI-generated patch that was closed unmerged on 2026-09-01.",
    "Reports on HIP/ROCm or CUDA are absent from the thread; one counter-datapoint (RX 7900 XTX Vulkan, tip 31288c9c6 + #30591) saw no OOB over 8 server cycles."
   ],
   "techniques": [
    "draft-mtp",
    "draft-dflash",
    "recurrent-state rollback (n_rs_seq)"
   ],
   "reported_results": [
    "Issue open; 9 human comments + 0cc4m; PR #28206 closed unmerged; builds b10666/b10724/10711/ce8caa6 reported"
   ],
   "cross_references": {
    "chapters": [],
    "handoffs": [
     "dflash2-block-drafter-experimental-build.md",
     "qwen-mtp-llamacpp-port.md"
    ],
    "experiments": [],
    "intake_entries": [
     "intake-2577",
     "intake-1513"
    ]
   },
   "recommended_actions": [
    "Knowledge only: Vulkan-specific; keep the loud id validation in llama-batch.cpp; do not add a silent clamp."
   ],
   "credibility_score": null,
   "contradicting_evidence": null,
   "referenced_arxiv_ids": [],
   "notes": "GitHub issue; read via API (issue, comments, timeline).",
   "verification": "stage1-unverified",
   "handoffs_updated": [],
   "handoffs_created": [],
   "source_revision": "GitHub API ggml-org/llama.cpp issues/28158 (+10 comments, timeline, PR #28206) retrieved 2026-10-31; state open",
   "reader_should_conclude": "Stage-1 unverified: do not cite."
  }
 ],
 "entries": [
  {
   "id": "intake-2591",
   "verification": "dive-verified",
   "read_depth": "FULL",
   "source_revision": "GitHub API ggml-org/llama.cpp issues/28286 (+comments, timeline, PR #29454) retrieved 2026-10-31; state closed(stale) 2026-10-18",
   "source_text_path": "scratch:dive-ws58-20261031/dive/w3spec/issue28286.txt",
   "key_claims": [
    "With --spec-type draft-mtp and --parallel 4 on Qwen3.8-Flash-Next (qwen4exp, a Gated-DeltaNet hybrid), temp-0 concurrent requests with distinct prompts produced responses that drifted into another slot's content; the reporter ruled out HIP graphs (GGML_CUDA_DISABLE_GRAPHS=1) and a client-side harness artifact.",
    "It does not reproduce at --parallel 1; low-entropy prompts (ROCKET vs BANANA x40) showed zero contamination, so the effect needs content complexity to surface.",
    "The issue was closed by the stale bot on 2026-10-18 with no root cause and no merged fix; the only linked candidate, PR #29454 (fill unwritten rollback snapshot slot on short ubatches), was closed unmerged on 2026-09-27 and its connection to #28286 is stated as unconfirmed.",
    "Environment was a downstream fork on master 458681e1d with the qwen4exp MTP integration, Strix Halo gfx1151 ROCm; not tested on a non-recurrent target."
   ],
   "reported_results": [
    "Issue has 1 comment (stale bot close); no fix PR; PR #29454 closed unmerged 2026-09-27 (issue28286.txt, pr29454.txt)"
   ],
   "claim_verdicts": [
    {
     "claim_index": 0,
     "verdict": "CONFIRMED",
     "evidence": "issue body"
    },
    {
     "claim_index": 1,
     "verdict": "CONFIRMED",
     "evidence": "Notes on isolation"
    },
    {
     "claim_index": 2,
     "verdict": "CONFIRMED",
     "evidence": "timeline + PR 29454 comments (goodbadwolf close)"
    },
    {
     "claim_index": 3,
     "verdict": "CONFIRMED",
     "evidence": "Environment"
    }
   ],
   "claim_anchors": [
    {
     "claim_index": 0,
     "locator": "issue28286 body, Summary",
     "quote": "With `--spec-type draft-mtp` and `--parallel N` (N > 1), concurrent requests carrying clearly"
    },
    {
     "claim_index": 1,
     "locator": "issue28286 body, Notes on isolation",
     "quote": "- Does not reproduce at `--parallel 1` (single-stream), even under heavy multi-turn use with the"
    },
    {
     "claim_index": 3,
     "locator": "issue28286 body, Environment",
     "quote": "- Model: Qwen3.8-Flash-Next (`qwen4exp` architecture), UD-Q3_K_XL, with the"
    }
   ],
   "claim_corrections": [],
   "depends_on": [],
   "dive_corrections": "Stage-1 record created from the API; issue verified. Key finding: the thread contains no root cause and no fix. Stale-closed is not resolved. The only candidate mechanism (short-ubatch unwritten rollback snapshot slot, PR 29454) was declined by a contributor because the server never rolls back the anchor token (cites #26695), so the mechanism is UNCONFIRMED and un-merged.",
   "reader_should_conclude": "Cite as an UNRESOLVED upstream report of draft-mtp + parallel>1 content mixing on a GDN-hybrid (qwen4exp) target on ROCm; there is no fix commit to look for. Do NOT carry 'fixed upstream' or 'qwen4exp-only'; the reporter says it was not tested on non-recurrent targets. Our v10 tree has the same shape of code (delta-net-base.cpp: trailing snapshot slots left unwritten when ubatch < K).",
   "not_read": "PR #28019 thread read only for context (rs-rollback ask resolved by #28123); linked issue text of #27836 not read."
  },
  {
   "id": "intake-2592",
   "verification": "dive-verified",
   "read_depth": "FULL",
   "source_revision": "GitHub API ggml-org/llama.cpp issues/28158 (+10 comments, timeline, PR #28206) retrieved 2026-10-31; state open",
   "source_text_path": "scratch:dive-ws58-20261031/dive/w3spec/issue28158.txt",
   "key_claims": [
    "Qwen3.8-27B with --spec-type draft-dflash (z-lab DFlash2) or draft-mtp fails at the first target verify batch with 'invalid token[N] = 248320' (exactly n_vocab) and HTTP 500, reproduced on Vulkan only (gfx1150, gfx1201, gfx1100, 3x RX 6800); CPU control with the same GGUFs works.",
    "A commenter's controlled datapoint reproduced the byte-identical signature by injecting a Vulkan mul_mm tile-layout bug that leaves half of each prefill tile unwritten: the id is always exactly n_vocab, read as a sentinel emitted from NaN draft scores, not an out-of-bounds index; the OP's DFlash2 selector row had all 16 top-k slots at 248320 with NaN scores.",
    "The issue is still open with no maintainer root cause; the only fix PR (#28206) was an AI-generated patch that was closed unmerged on 2026-09-01.",
    "Reports on HIP/ROCm or CUDA are absent from the thread; one counter-datapoint (RX 7900 XTX Vulkan, tip 31288c9c6 + #30591) saw no OOB over 8 server cycles."
   ],
   "reported_results": [
    "Issue open; 9 human comments + 0cc4m; PR #28206 closed unmerged; builds b10666/b10724/10711/ce8caa6 reported"
   ],
   "claim_verdicts": [
    {
     "claim_index": 0,
     "verdict": "CONFIRMED",
     "evidence": "OP + maciejdzialo CPU control + enk37/fama-lama"
    },
    {
     "claim_index": 1,
     "verdict": "CONFIRMED",
     "evidence": "tczank 2026-09-22 and maciejdzialo comment 2"
    },
    {
     "claim_index": 2,
     "verdict": "CONFIRMED",
     "evidence": "timeline; PR 28206 comments"
    },
    {
     "claim_index": 3,
     "verdict": "CONFIRMED",
     "evidence": "all reporters Vulkan; tczank 10-22 counter-datapoint"
    }
   ],
   "claim_anchors": [
    {
     "claim_index": 0,
     "locator": "issue28158 OP + comment 2",
     "quote": "init: invalid token[1] = 248320"
    },
    {
     "claim_index": 1,
     "locator": "issue28158 tczank 2026-09-22",
     "quote": "**6/6 are exactly 248320, deterministic**"
    },
    {
     "claim_index": 3,
     "locator": "issue28158 tczank 2026-10-22",
     "quote": "1. No OOB here: greedy 128-token sample"
    }
   ],
   "claim_corrections": [],
   "depends_on": [],
   "dive_corrections": "Stage-1 record created from the API; issue verified. Stage-2 correction to the title framing: this is not a confirmed 'MTP/DFlash emits out-of-bounds id' logic bug; evidence points to a Vulkan-backend NaN-logits producer plus a sentinel n_vocab fill, and CPU is clean. No relevance to HIP/CPU serving was found.",
   "reader_should_conclude": "Cite as an OPEN Vulkan-only report; no fix exists. Do NOT carry 'off-by-one in draft sampling' (OP hypothesis, contradicted by constant id) or the OP's suggested silent clamp (would convert a crash into silent garbage per tczank). Not a risk for our CPU/HIP serving on current evidence.",
   "not_read": "Full thread read; the linked #27812, #28097 not read."
  }
 ],
 "ledger": [
  {
   "row": "W3SPEC-1",
   "entries": [
    "intake-2591"
   ],
   "action": "Bounded probe (own scratch server, GPU correctness window, no region-lock needed per CORRECTNESS rule): on the production 27B shape (Q8_0, DFlash2 n-max 7, np 4, kv-unified, q8 KV, ROCm0) and on the frontdoor shape (Qwen3.6-35B-A3B-MTP Q8_0, draft-mtp n 4, np 4) run 12 distinct complex prompts (code + prose, >=300 tokens each, temp 0, top_k 1, cache_prompt false, 384 tokens). Arm A = each prompt solo (c=1). Arm B = same prompts at c=2,3,4,5 (with c=5 exceeding slots to force queueing), interleaved starts. Compare token-for-token (sha256 of token ids) to arm A. Six controls: (1) spec off (--spec-type none) at c=4, same binary; (2) spec on, np 1 serial; (3) -np 4 server carrying ONE request (np inert, per DF2 handoff line ~408); (4) low-entropy ROCKET/BANANA pair (expected clean); (5) repeat arm B twice for run-to-run determinism and a no-spec repeat to separate batch-shape numeric splits (DF2-2) from state corruption; (6) a cross-content canary: plant a unique rare string in prompt k and grep every other response for it.",
   "grounding": "dflash2-block-drafter-experimental-build.md:551 (DF2-12 np>1 GDN parity arm, unticked, says np>1 is untested); :777 (DF2-LB1 census already ran the same np4 n-max-7 shape, 3.47% ragged verify calls); common/common.h:390 need_n_rs_seq covers MTP and DFlash; src/models/delta-net-base.cpp:596 'trailing slots are left unwritten'",
   "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
   "posture": "cheap-screen-now",
   "benefit": "Settles whether any live np>1 speculative role can mix slot content; must stay correct: identical text to solo for greedy decode (divergence classified near-tie vs content-from-other-slot via the canary, per DF2-12).",
   "decision_rule": "Any response containing another request's planted string, or a divergence that is not a near-tie, on arm B but not on controls 1-3 = CONFIRMED contamination: stop np>1 spec on that role (set slots 1 or spec none) and open a fix lane on experimental. Zero divergences beyond the control-5 numeric floor over >=48 request-pairs per shape = not reproduced on this tree.",
   "reason": "Upstream never fixed or root-caused it and our roles are np 4 + rollback-spec, so the check is the only evidence."
  },
  {
   "row": "W3SPEC-2",
   "entries": [
    "intake-2591"
   ],
   "action": "Fold the DF2-12 row and W3SPEC-1 into one run; add the frontdoor :8070 MTP np4 shape (not covered by DF2-12, which names only Qwen3.8-27B DFlash2) and the cross-content canary.",
   "grounding": "orchestration/model_registry.yaml:1787-1796 (frontdoor port 8070 slots 4 full / 1 half) and :1831 draft_model MTP-Q8_0, acceleration draft-mtp draft_max 4",
   "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
   "posture": "cheap-screen-now",
   "benefit": "Closes the only live MTP+np>1 role (frontdoor) left outside the DF2-12 scope.",
   "decision_rule": "Same as W3SPEC-1.",
   "reason": "Frontdoor is Qwen3.6-35B-A3B (hybrid GDN) with MTP at np 4: nearest analogue to the qwen4exp report; not checked here whether it has an earlier np>1 identity record."
  },
  {
   "row": "W3SPEC-3",
   "entries": [
    "intake-2591"
   ],
   "action": "If W3SPEC-1 shows divergence: reproduce on the experimental branch and try the PR #29454 approach (copy pre-ubatch state into unwritten snapshot slots every ubatch) as the candidate fix; it was never merged, so it must be carried as our own patch on a llama.cpp-experimental branch, not expected from upstream.",
   "grounding": "pr29454.txt (PR body, closed unmerged 2026-09-27); delta-net-base.cpp:595-596 comment and n_written = min(n_seq_tokens, K)",
   "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
   "posture": "monitor",
   "benefit": "Conditional on W3SPEC-1; frozen v10 must not be touched.",
   "decision_rule": "Only start if W3SPEC-1 confirms divergence.",
   "reason": "Gap exists in code, harm unproven."
  },
  {
   "row": "W3SPEC-4",
   "entries": [
    "intake-2592"
   ],
   "action": "No action on our CPU/HIP stack; note in the speculative handoff that the n_vocab-sentinel failure is Vulkan-specific and fails loudly at src/llama-batch.cpp:52 (token validation), which our tree retains.",
   "grounding": "src/llama-batch.cpp:52 in /mnt/raid0/llm/llama.cpp; all reports Vulkan (issue28158.txt)",
   "owner": "handoffs/active/qwen-mtp-llamacpp-port.md",
   "posture": "knowledge-only",
   "benefit": "Prevents a future agent adopting the OP's silent clamp suggestion.",
   "decision_rule": "n/a",
   "reason": "No HIP/CPU reproduction in the thread."
  },
  {
   "row": "W3SPEC-x",
   "entries": [
    "intake-297"
   ],
   "action": "DF2-DRAFTER-CAPABILITY input: z-lab/dflash @ 07ebd93db9f4 (2026-08-18, remote HEAD identical today) contains NO training code. 659-line dflash/model.py has only inference: CandidateSelector (selector_top_k=16 candidates per position via topk of the draft logits, selector_rank from config; score = unary logit + einsum(predecessor_codebook[prev token] * hidden_projection(hidden), successor_codebook[candidate]); greedy argmax or sampled walk over precomputed scores). Selector is a low-rank bilinear form with two vocab x rank embedding tables plus a hidden projection; rank 256 comes from the inco.ai blog ('compact 256-dimensional embedding', context gate H(h_t)). Loss and data are NOT published: the blog says only 'All drafters are trained under the same setup'/'matched setups'; the README lists no train script, dataset or loss. Training the selector means re-deriving a pairwise-transition objective ourselves (natural choice, unverified: cross-entropy of the accepted path against target tokens), so DF2-DRAFTER-CAPABILITY must budget the training recipe as research, not a port.",
   "grounding": "dflash2-block-drafter-experimental-build.md:196 (DF2-DRAFTER-CAPABILITY); dflash_repo/dflash/model.py:515-547; blog.txt",
   "owner": "handoffs/active/dflash2-block-drafter-experimental-build.md",
   "posture": "knowledge-only",
   "benefit": "Sets honest scope: inference reference and architecture are public, training recipe is not.",
   "decision_rule": "If an Inco/z-lab training release appears, re-open; otherwise first drafter-training probe must include an ablation of selector vs unary-only.",
   "reason": "Answers the capability question; no new entry."
  }
 ],
 "dive_surfaced_sources": [
  {
   "source": "https://github.com/ggml-org/llama.cpp/pull/29454",
   "settles": "candidate fix for short-ubatch unwritten rollback snapshot slot; mechanism unconfirmed for #28286; closed unmerged",
   "bears_on": "intake-2591",
   "recommend": "decline: closed unmerged, content captured in this dive; use only as a patch template if W3SPEC-1 diverges"
  },
  {
   "source": "https://github.com/ggml-org/llama.cpp/issues/28019",
   "settles": "qwen4exp multi-seq rs-rollback logits corruption (sibling report; resolved for the arch-support enum by #28123)",
   "bears_on": "intake-2591",
   "recommend": "ingest-and-dive"
  },
  {
   "source": "https://github.com/ggml-org/llama.cpp/issues/26695",
   "settles": "maintainer argument that the server never rolls back the anchor token (why #29454 was declined)",
   "bears_on": "intake-2591",
   "recommend": "ingest-and-dive"
  }
 ],
 "artifact_audit": "clean"
}
```
