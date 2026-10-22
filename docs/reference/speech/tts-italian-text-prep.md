# TTS text preparation: Italian normalizer and the lexicon/stress question

Origin: the CS-8.L Italian listen check (operator, 2026-10-22, 60 qwentts G1 cascade clips of FLEURS
it_it). The operator flagged two kinds of error. **Normalizable** errors are tokens the model reads
wrongly because it gets raw symbols: "1963", "150", "802.11n … 2.4Ghz … 5.0Ghz" (rated 2), and "pH"
with a French/Spanish "hache" (twice, once rated 2). **Model-side** errors are lexical stress on
*atomi*, *idiozie* and *analoga*, and proper nouns (*Giza* with a soft G, *Marianne* read as "Marian").
Conversation-stack tasks: CS-8.L1 (numbers and units), CS-8.L2 (abbreviations) and CS-8.L3 (the
stress, proper-noun and accent monitor). The owner task is CS-8.G1B.

## Where the text goes today (2026-10-22)

| Path | Text route to qwentts | Normalization before this change |
|---|---|---|
| Eval cascade, SPQ-03 G1 (`/mnt/raid0/llm/tmp/speech-queue-20261020/scripts/g1_cascade_language.py`, untracked) | FLEURS `test.tsv` sentence → `p["text"] + "\n"` on the stdin of `qwen-tts --lang Italian` | none |
| Production cascade (epyc-orchestrator `src/voice/cascade.py`) | voice-turn `text_delta` events → `answer` → `QwenTtsHttpSynthesizer.stream_pcm(answer)` → `POST :9002/v1/audio/speech {"input": answer}` | none. The pinned HTTP contract has no language field, and the `:9002` server runs with `--lang auto` |
| Research turn-taking renderer (`scripts/voice/turn_taking/tt_render_pipeline.py`) | job text → `qwen-tts --lang English` stdin | none (English only) |
| qwentts.cpp itself (frozen, `production-speech-v1` @ `2c1b518`) | `utf8_normalize` (BOM and encoding only) → Qwen BPE (151 676 vocab) → talker | none: no number, unit or abbreviation front end |

The research STT normalizer (`scripts/speech/stt_bakeoff/stt_norm.py`) runs on the ASR **output**, for
scoring, and never touches TTS input. Its Italian 0..100 table agrees exactly with the new TTS
cardinals: all 101 values were cross-checked.

## What changed

- **Normalizer**: epyc-orchestrator `src/voice/tts_text_normalize.py`, `normalize_for_tts(text, language)`.
  It is pure, stdlib-only and idempotent. Only Italian is normalized (`it`, `it-IT`, `Italian`, …).
  Any other language gets the input object back unchanged. It covers:
  - cardinals up to 10¹²−1, with the compound accent (ventitré, centotré, millenovecentosessantatré),
    elision (ventuno, centottanta) and apocope (ventunmila, ventun milioni);
  - grouped thousands (40.000), decimal comma, a dot decimal before a unit (2.4Ghz → "due virgola
    quattro gigahertz") and dotted identifiers (802.11n → "ottocentodue punto undici enne");
  - units with agreement (un chilometro, un'ora, un milione di chilometri);
  - º/ª ordinals, "1 maggio" → primo, d/m/y dates, hh:mm times and decades ('20 → venti);
  - an extendable letter-name table (pH → "pi acca", DNA, TV, …) and "lettera H" → "lettera acca".

  Unknown tokens pass through: M16, FT-IR, 4K, zero-padded codes, bare runs of 7 or more digits, a bare
  "1" before a noun (the gender is unknown), and acronyms that are not in the table.
- **Production wiring**: `CascadeBackend(..., tts_text_normalization=False, tts_language=None)`. It is
  off by default, and off is byte-identical: the synthesizer receives the same answer object. When it
  is on, only the synthesizer text changes. `must_preserve` and the displayed text stay the route's
  own. **TODO(operator)**: enable it on the live path (`True`, `tts_language="it"` for an Italian
  server) after the re-listen is rated.
- **Eval wiring**: research `scripts/speech/g1_cascade/g1_cascade_language.py` is the tracked copy of
  the SPQ-03 G1 script, which was never committed. It adds `--tts-normalize` (on by default) and
  `--no-tts-normalize`, which gives the SPQ-03 raw text. `config_echo.json` records the normalizer
  path and sha256, and each item row records `tts_text`. The ASR reference is still the raw FLEURS
  text.
- **Effect on the 60 CS-8.L sentences**: 10 change, and all 5 flagged normalizable clips are among
  them. The other 5 changed clips were rated 4–5 (years, 40.000, '20), so the re-listen covers them
  for regressions. The diff is not in git because it contains corpus text:
  `/mnt/raid0/llm/tmp/cs8l-italian-listen-kit/normalizer-diff.md`.

## Lexicon / stress override: there is no hook

I audited the frozen tree read-only (`tools/qwen-tts.cpp`, `tools/tts-server.cpp`,
`src/tts-server.h`, `src/prompt-builder.h`, `src/bpe.h`, `src/utf8.h`):

- **Input is plain text only.** Text goes through BPE into the talker's text embedding. There is no
  phoneme, IPA, SSML, stress-mark or lexicon input. Apart from the chat-frame `<|im_start|>` and
  `<|im_end|>` markers, there are no special tokens, and no grapheme-to-phoneme step exists anywhere in
  the tree.
- **Only text-side request fields.** `tts_request` holds `input`, `voice`, `instructions`, `format`,
  `speed` (parsed, then ignored) and sampling overrides. `--instruct`/`instructions` is **rejected
  for the Base model**, which is what production serves (`qwen-talker-0.6b-base`). In
  VoiceDesign/CustomVoice it is a free-text style prompt, not a pronunciation control.
- **The language tag is one codec token.** `--lang` (the server pins it at launch, `auto` by default)
  selects a language id. It does not change how words are pronounced.

This **confirms** the CS-8.L3 filer's finding, now with a full audit of the input surface. Stress and
proper nouns can only be influenced by **orthographic respelling** in the text-preparation layer.
Italian allows an optional written stress accent on non-final syllables (the àncora/ancòra
convention). Whether this BPE model honours that accent is unknown. It is untested, so it is **not
enabled** and is not part of the normalizer.

Proposed respelling table, for operator review only:

| word (clip) | operator note | respelling | rationale |
|---|---|---|---|
| atomi (it_06) | stress on the a | `àtomi` | graphic accent on the stressed vowel (proparoxytone) |
| idiozie (it_54) | stress on the second i | `idiozìe` | graphic accent on the stressed vowel |
| analoga (it_57) | stress on the second a | `anàloga` | graphic accent on the stressed vowel (proparoxytone) |
| Giza (it_31) | hard G | `Ghiza` | Italian spelling of a hard g before i |
| Marianne (it_38) | "Mariànne", not "Marian" | `Mariànne` | forces the Italian reading and the final vowel |

The re-synthesis filler (`s5-cs8l-retts`) has an **opt-in** probe arm for exactly these five
sentences, `CS8L_RESPELL_PROBE=1`. It is off in the proposed row. If the operator approves it, the
same re-listen also tests the respellings. If the probe shows that the model honours the accents, the
table becomes a language-gated, opt-in override file beside the acronym table. It must never change
display text, and it must never be on by default without a rated re-listen. If the model ignores the
accents, CS-8.L3 stays a model-side monitor item (candidate model or fine-tune), with no text fix.

## Belief kernel

The re-listen ratings are a human-listen measurement. They fall under the existing source-table row
*Human speech listen/rating checks* (schema `epyc.cs8l_italian_listen.v1`, capture task
VB-SPEECH-LISTEN-1, projected through the `conversation-stack-measurement` adapter as an observation).
That row has **no write-side hook yet**, so the re-listen produces zero tuples until VB-SPEECH-LISTEN-1
lands. When it is wired, the re-listen record must also carry the normalizer sha256 and the
re-synthesis `texts.json` sha256 (both are in `/mnt/raid0/llm/tmp/cs8l-retts-20261022/manifest.json`).
Without them a rating cannot be tied to the text the model actually read.
