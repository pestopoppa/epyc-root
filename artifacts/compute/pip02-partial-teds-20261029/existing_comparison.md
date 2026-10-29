# Existing ODL/PaddleOCR Comparison

Schema: `odl_bench.existing_comparison.v1`
GT: `/mnt/raid0/llm/datasets/omnidocbench/OmniDocBench.json`

| engine | structural Edit_dist (lower) | table TEDS (higher) | reading-order Edit_dist (lower) | latency_ms median (lower) | intrinsic chunk quality (informational) | sources |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| odl |  |  |  |  |  | 1 |
| paddle |  |  |  |  |  | 1 |

## Sources

1. `row_set` `odl,paddle` `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/scoring-prep/native-partial-2221/row_set.json`

## Notes

- duplicate metric row for engine=odl family=table_fidelity; later rows win in the comparison table
- duplicate metric row for engine=paddle family=table_fidelity; later rows win in the comparison table
