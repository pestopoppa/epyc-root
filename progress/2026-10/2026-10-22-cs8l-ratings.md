# 2026-10-22 — CS-8.L Italian listen check recorded (coordinator 3c4ca599, no inference)

- Operator rated all 60 cascade G1 Italian clips: 60/60 intelligible; naturalness mean 4.62, median 5, {5:47, 4:5, 3:6, 2:2}; 11 clips with notes.
- Aggregate artifact: `artifacts/stt-cs8/cs8l-italian-listen-20261022.json` (rating-docs sha256 `db10caef87e62ff45e0b820c247b482a13e0e9d21ad4a6bfe0d4a6b70bc1c905`, kit manifest sha256 `deda0a7852dda2ffd60a4aade1c28e15584041c7c2a1fc31d742533bebbedcf1`). No audio or prompt texts committed.
- Error categories: numbers/units 3 clips, pH as "hache" 2, lexical stress 3, proper nouns 2, accent 1.
- ASR cross-check (existing whisper large-v3-turbo WER, no new inference): low-naturalness (<=3, n=8) mean forced WER 0.039 vs 0.024 for >=4 (n=52); Spearman -0.14; permutation p=0.21. Weak agreement only; 5 of 8 low clips have WER 0, so ASR cannot replace the human ear for stress/pH/prosody errors.
- Handoff: CS-8.L ticked; filed CS-8.L1 (number/unit verbalization) and CS-8.L2 (pH/abbreviations), both text-normalization code, dispatchable immediately; CS-8.L3 (stress, proper nouns, accent) recorded as monitor, not a task. Italian is not rejected, so M17 does not fire for Italian.
- Belief kernel: no listen/rating source existed; added README row and VB-SPEECH-LISTEN-1 (no grading rule invented).
