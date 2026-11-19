# Existing ODL/PaddleOCR Comparison

Schema: `odl_bench.existing_comparison.v1`
GT: `/mnt/raid0/llm/tmp/pip02-r36-20261107/out/score-final/gt-subset.json`

| engine | structural Edit_dist (lower) | table TEDS (higher) | reading-order Edit_dist (lower) | latency_ms median (lower) | intrinsic chunk quality (informational) | sources |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| odl-docling-fast-hybrid | 0.156645 | 0.265413 | 0.235138 |  |  | 1 |
| paddleocr-vl-1.6 | 0.0400759 | 0.910479 | 0.0962779 |  |  | 2 |

## Sources

1. `metric_result` `odl-docling-fast-hybrid` `artifacts/compute/pip02-r36-65page-20261108/odl-Lfinal_quick_match_metric_result.json`
2. `metric_result` `paddleocr-vl-1.6` `artifacts/compute/pip02-r36-65page-20261108/paddle-Lfinal_quick_match_metric_result.json`
