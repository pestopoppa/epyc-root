# RLM slice-return prompt arm: preparation status

The adjacent `root_lm_system.rlm_slice.md` is an original draft adaptation of
the patterns recorded in intake-537, not a recovered or verified copy of the
open-weight-tuned prompt. The source wording and license have not yet been
verified. The draft omits several documented features, including few-shot
examples and batching. Asking a child to return text still incurs child decode;
this draft does not establish a decode saving.

The S4 Omega runner recognizes only its baseline and Omega arms. A valid third
arm needs a distinct resolver variant and prompt snapshot, an explicitly
three-arm runner, a suitable scored task set, verified serving identity, granted
execution and write-side belief capture. Preserve the original two arm
identities and do not claim fidelity or task completion from this draft.
