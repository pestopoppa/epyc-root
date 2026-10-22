# 2026-10-22: Italian TTS text normalizer (CS-8.L1/L2), subagent of 3c4ca599

This is the operator's directive "dispatch the TTS normalization fixes now", working from the CS-8.L
listen check. No model was executed (no TTS, ASR or LLM). The frozen speech kernels were only read.

## Landed

| Repo | Commit | What |
|---|---|---|
| epyc-orchestrator | `df9d2eca` | `src/voice/tts_text_normalize.py` (Italian-only, pure and idempotent; cardinals and years, decimals, units with agreement, ordinals, dates, times, decades, a letter-name acronym table with pH → "pi acca"). `CascadeBackend(tts_text_normalization=False, tts_language=None)`: default off and byte-identical, with a TODO(operator) to enable it on the live path. `tests/unit/test_tts_text_normalize.py`: 126 tests; the voice suites pass 183/183 |
| epyc-inference-research | `95550d294` | `scripts/speech/g1_cascade/g1_cascade_language.py`: the tracked copy of the never-committed SPQ-03 G1 script, with `--tts-normalize` on by default (eval path) and the normalizer sha recorded in `config_echo.json`. 3 tests |
| epyc-root | this commit | [`docs/reference/speech/tts-italian-text-prep.md`](../../docs/reference/speech/tts-italian-text-prep.md): the text-path map, the normalizer scope, the lexicon/stress audit and the respelling proposal |

## Findings

- **Text path**: no normalization existed anywhere between the cascade or LLM text and qwentts. Raw
  FLEURS text went to `qwen-tts` stdin (G1), and the raw answer went to `POST :9002 {"input"}`
  (orchestrator cascade). qwentts.cpp only strips the BOM and validates UTF-8 before BPE.
- **60-sentence run** (diff at `/mnt/raid0/llm/tmp/cs8l-italian-listen-kit/normalizer-diff.md`, not
  in git): 10 of the 60 sentences change. All 5 operator-flagged normalizable clips are among them
  (it_09, it_20, it_23, it_26, it_55). The other 5 changed clips (it_04, it_08, it_49, it_53, it_60)
  were rated 4–5, so the re-listen also covers them for regressions. The 6 model-side notes are
  unchanged.
- **No lexicon or stress hook in qwentts.** Input is plain text into BPE, `instructions` is rejected
  for the Base model, and `--lang` is one codec token. This confirms the CS-8.L3 filer, now with a
  full audit of the input surface. Orthographic respelling (àtomi, idiozìe, anàloga, Ghiza, Mariànne)
  is the only lever. It is proposed in the reference doc, not enabled, and has an opt-in probe arm in
  the re-synthesis job.
- **Cross-check**: the new cardinals agree with the research STT-side Italian table
  (`stt_norm._build_it_table`) on all 101 values.

## Re-synthesis filler (main arms it)

- Job `/mnt/raid0/llm/tmp/fillers-3c4ca599/jobs/cs8l_retts_job.sh`. It re-synthesizes only the 10
  changed sentences with the frozen qwen-tts (sha `1781c49c` = SPQ-03), using the same seed, reference
  wav and 1-thread shim. It uses its own `LD_LIBRARY_PATH`, runs `verify_ggml_linkage` and
  `ram_admit`, and pins the texts in `texts.json` (sha `cd4fd331`). Outputs go to
  `/mnt/raid0/llm/tmp/cs8l-retts-20261022/` in the page format (`clips/`, `clips.normalized.json`).
  The dry run and a fake-TTS plumbing run passed.
- Proposed row `s5-cs8l-retts`: `/mnt/raid0/llm/tmp/fillers-3c4ca599/s5-cs8l-retts.row-proposed.md`
  (block-correctness, cpu, 27 GiB, 15 min). It validated `--for-grant` on a scratch copy with a
  live-PID stand-in. Arm steps: `/mnt/raid0/llm/tmp/fillers-3c4ca599/arm_cs8l_retts.sh.txt`.

## Open (each names its own blocker)

- CS-8.L1 and CS-8.L2 are done by their stated criterion (unit fixtures pass). Main ticks them in
  `conversation-stack.md`; this lane did not edit that file.
- Enabling normalization on the live voice path is the operator's call after the re-listen
  (TODO(operator) in `CascadeBackend`).
- The G1 default normalizer path is the shared orchestrator clone. It has the file only after that
  clone is fast-forwarded to `df9d2eca`; until then G1 preflight fails with MISSING (loud). The
  retts job does not depend on the clone.
- Belief kernel: the re-listen is covered by the source row *Human speech listen/rating checks*
  (VB-SPEECH-LISTEN-1), which has no write side yet, so it produces zero tuples until that task
  lands. The record must carry the normalizer and `texts.json` sha256.
