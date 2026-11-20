# DTREE-A3: bounded KEEP_CANDIDATE

Row `ak-dtree-a-argmax-gpu-20261120-r3` ended 2026-11-20T10:27:11Z,
scheduled rc0. The native verdict is **KEEP_CANDIDATE** and the retained owner
filing is **pass**. The df2 filing call returned NOOP because the owner had
already filed; its receipt was preserved and alert `06bcddce608027ce3b068356`
was acknowledged. No repeat measurement or successor row was issued.

The question was whether device argmax (`LLAMA_DEVICE_ARGMAX=1`) improves
27B np1 fixed-tree decode beyond the declared 0.84% GPU W2 floor without
triggering the sampled fresh-prefill oracle gate. Higher decode tok/s is better.
All arms use the H15-fixed experimental fork `f1d8f383f`, Qwen3.8-27B Q8_0
and DFlash2, draft max 4 and tree nodes 13. L and L2 are identical env-unset
controls; X enables argmax. This compares argmax within that candidate, rather
than comparing the whole tree implementation with production.

Seven complete interleaved pairs, three prompts per arm and 256 generated tokens
per prompt produced the following native summaries:

| Statistic | Result |
| --- | --- |
| X / mean(L,L2), mean pair ratio | 1.015414743619731 (+1.5415%) |
| Reported 95% t interval | [1.0088438242101887, 1.0219856630292732] |
| L2 / L, mean pair ratio | 0.997517620341982 |
| Reported L2/L interval | [0.9850678925651014, 1.0099673481188625] |
| Oracle disagreements, L / L2 / X | 0/336 / 0/336 / 0/336 |
| Arm records with start/end residency and reaped child | 21/21 |

The pair ratios were independently recomputed from recorded tok/s and reproduce
the native mean and interval (native seven-pair t multiplier 2.447). Its lower
endpoint 1.008843824 exceeds the predeclared 1.0084 threshold by only
0.000443824 (0.0444 percentage points). The >=5-pair stop-on-answer rule fires
at seven pairs, before the eight-pair cap. Neither the oracle futility rule nor
the below-baseline/residency rules fires. No further samples are required by
this packet's stopping rule.

This is a row-specific candidate verdict. The reported interval follows the
packet's repeated-look rule; it is not a new sequentially adjusted significance
or promotion claim. Oracle coverage is 16 positions per prompt, not every
position. Exact output identity was recorded rather than gated; native summary
records nine nondeterministic prompt runs. Neither zero sampled oracle errors
nor a control interval spanning 1 establishes exact identity, general model
quality, or absence of a correctness defect. This run does not isolate the
cause of the earlier pre-H15 identity failures. Production deployment and DTREE-P5
remain subject to their existing separate gates. Keep the argmax feature as an
experimental candidate for that broader evaluation; do not extend this packet.

Original evidence remains at its existing paths; no source, logs, weights or
binary payloads were copied into the repository:

- `/mnt/raid0/llm/tmp/ak-dtree-a-argmax-gpu-20261120-r3/out/results.jsonl`, SHA-256
  `24d67c11cd3d40207de3ca60c3dc0d56d0d4c4ed6feb592f3e22c550d734df6b`.
- Adjacent `RESULT.json`, SHA-256
  `1f28ee7a453fa4004e2c87edc511b99acde9390ef52bebe93bf75f455682b96f`.
- Row `job.py`, SHA-256
  `cb3b4592e84d27970f84a023da534caa9a5cca27794daf18bd72f2e152558859`.
- Row `SOURCE.sha256`, SHA-256
  `06a1e4f5ef053c6ef293c7673cf39184f9ca9ed8e400c468acf8af7a658e7afb`.
- Row `launch.sh`, SHA-256
  `bf53ff453130790accb25a7e103b02dcb0f8b60afa43bd3ca03d4b2aaeb2800c`.
- `/mnt/raid0/llm/tmp/compute-flags/filing-done/ak-dtree-a-argmax-gpu-20261120-r3.verdict.json`, SHA-256
  `55b2e50cb21a60c3516fde2a948f5a3a9e3229b2d5c2a543cb43fba391aa548d`.

[belief: cc]
