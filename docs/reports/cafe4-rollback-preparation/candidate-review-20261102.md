# CAFE-4 candidate source review — 2026-11-02

CAFE-4 independent source review — candidate NOT READY

Reviewed /mnt/raid0/llm/tmp/speculative-decoding-mtp/cafe4finish/rs-rollback.cpp and exact v10 source interfaces, without compilation, inference, or production edits. Findings:

1. The candidate allows accept == 0 (lines 264-282) and can declare PASS after any rollback (lines 391-401). Thus it does not ensure a genuinely partial acceptance of 0 < accepted < D. Require and report at least one strict partial acceptance; retain UNKNOWN where none occurred.
2. The normal path removes from replay_pos = start + accept and re-decodes the last retained token (lines 283-307), rolling back one extra token. The v10 server keeps the sampled boundary and accepted draft tokens, sets the newly sampled token aside, and removes from prompt.tokens.pos_next() (server-context.cpp:4210-4234); it processes the new sampled token in the next pass. The candidate can be a distinct replay stress test but must add the server-equivalent path before claiming server semantics.
3. The extra-removal fault removes one more position but replays at the original replay_pos (lines 286-306). This intentionally makes a position gap, so a resulting logits difference is not shown to come from recurrent state rather than positional/KV behavior. A decode error happens before FAULT_DETECTED; rc!=0 is not proof the state-specific fault was caught. Require a paired native control demonstrating state-specific detection, and distinguish UNKNOWN from the detected marker.
4. The program accepts an arbitrary -m and only checks llama_n_rs_seq; it does not establish that the chosen model executes recurrent snapshot operations. A KV-only model with partial removal could pass. Bind the runtime candidate to a verified recurrent/MTP target and collect native evidence that the recurrent snapshot/restore path was exercised.
5. Reference logits retain n_predict * n_vocab float values (lines 142,188-192,352-355), while -n is bounded only by INT_MAX and there is no allocation/error budget. A large valid input may exhaust host memory. Bound/estimate it before loading or stream the oracle. The fixed 1e-5 batched-vs-serial threshold remains an explicitly uncalibrated fail-closed diagnostic, not an established equivalence threshold.

The D+1 batch construction is present (lines 235-255) and checked against effective batch/ubatch capacity; syntax-only and structural checks cannot establish recurrent snapshot correctness, actual kernel residency, native fault behavior, or row readiness.
