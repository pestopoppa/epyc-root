# Source for the experimental RLM slice-return arm

`prompt.ts` is the unmodified source from [avbiswas/fast-rlm, commit
`781b0f63189e14286118ed3fe13f7763682ef558`](https://github.com/avbiswas/fast-rlm/blob/781b0f63189e14286118ed3fe13f7763682ef558/src/prompt.ts).
Its SHA-256 is `31eba719f632c2f3caa0b451a94e739cbdab9abfb6e19de3ba56aa7b8f39d747`.
The adjacent MIT license is from the same commit and attributes copyright to
Avishek Biswas. The older historical file is byte-identical but had no license
at that revision.

This is source evidence for an adaptation, not a runnable EPYC prompt. The
source assumes `llm_query`, Python-object child returns and async behavior that
must be translated to the actual EPYC tool contract. The existing EPYC draft
and the remaining three-arm runner requirements are described in
[the arm status](../rlm-slice-arm-status.md). No model evaluation or decode
saving is established by retaining this source.
