# RLM slice-return prompt arm: preparation status

The adjacent `root_lm_system.rlm_slice.md` is an original draft adaptation of
the patterns recorded in intake-537, not a recovered or verified copy of the
open-weight-tuned prompt. The source wording and license have not yet been
verified. The original article was unavailable, but a [secondary mirror](https://ainewstoday.co/recursive-language-models-an-all-in-one-deep-dive/)
contains the reported prompt. The author's [historical repository prompt](https://github.com/avbiswas/fast-rlm/blob/14b2f20676b13844a17bc498c745c519e7783a93/src/prompt.ts)
matches the mirror after whitespace and backtick normalization. That historical
revision has no license file. The later [MIT-licensed revision](https://github.com/avbiswas/fast-rlm/blob/781b0f63189e14286118ed3fe13f7763682ef558/src/prompt.ts)
has a byte-identical prompt file; preserve its license and attribution when
adapting it. The original publisher and the article's own license remain unverified. The
draft omits several documented features, including few-shot
examples and batching. Asking a child to return text still incurs child decode;
this draft does not establish a decode saving.

The S4 Omega runner recognizes only its baseline and Omega arms. A valid third
arm needs a distinct resolver variant and prompt snapshot, an explicitly
three-arm runner, a suitable scored task set, verified serving identity, granted
execution and write-side belief capture. Preserve the original two arm
identities and do not claim fidelity or task completion from this draft.
