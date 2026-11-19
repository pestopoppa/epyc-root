# SR-7 proposer counter preparation

`proposer_stats.py` parses production v10 (`ffc1bac82eeca6f9099e1ccd9ba49703c460a115`) trace-format per-implementation statistics and cross-checks their totals with native response counters. `common/speculative.cpp` records generated and accepted tokens for the selected implementation; `common_speculative_print_stats` emits those totals at trace level. Aggregate acceptance is the generated-token-share-weighted mean of proposer-specific acceptance rates. Rates for a proposer with no generated tokens are undefined.

This is a model-free parsing component, not a runnable row or a result. A future worker must prove a fresh single-request server and capture exactly one complete statistics snapshot; these lifetime properties cannot be inferred by this parser. It must confirm its actual binary/source and trace format, preserve native logs and response, audit distinct prompts and repeated-5-gram fractions, use a non-context-reading control, predeclare comparisons across widths and quantify uncertainty. Match failures invalidate the observation rather than justify dropping a proposer. Correlation of branch mix and aggregate acceptance alone does not prove causation.

Run bounded parser controls with `python3 -m unittest discover -s docs/reports/sr7-proposer-preparation -p 'test_*.py' -v`.
