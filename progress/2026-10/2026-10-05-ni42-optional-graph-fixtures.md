# NI42 optional graph module fixtures — 2026-10-05

MAIN accepted the bounded off-host run [37339553198](https://github.com/pestopoppa/epyc-root/actions/runs/37339553198) after independently reopening all five original native receipts, source readsets, and shared projections. The selected modules collected and passed 65 cases total, with zero skips, failures, or errors:

| Module | Passed | Receipt file SHA-256 | Original JUnit SHA-256 |
| --- | ---: | --- | --- |
| `test_failure_graph.py` | 17 | `7f489016dadfde3fec4e735a6a94fb00c471d26071facdb17da7b254861c532c` | `9e373467ea81581e9962d5f7733ba61a4cb8bed2c27b08e707bda76d971206c4` |
| `test_graph_integration.py` | 17 | `fdab5177825742725e43763b167630db3321ae012b12d6862af463ca4cfb26c4` | `8aeb04e5140234c363ea4fc37a8c42faaf2c2fea4fa0e181e63a2926e5a71916` |
| `test_graph_router_cold_start.py` | 4 | `daa3e4bc7892d657d083c0c235d591ff6d23439211a271632298f2ed57a20c14` | `469f90c93d65c84d471830a3f841335b13c3d2655aba0e463578ab01d7957c7e` |
| `test_hypothesis_graph.py` | 18 | `63b82a51fbbe44af4f38ebeb403d359b33b2cf914f2cdff295125427f30f34ed` | `30daf13c64d26ae94bb208a00d0baa47d9f1f9bf689a1d9b299686dde69a9084` |
| `test_routing_graph.py` | 9 | `d4149ceed205a3c3920831f15b19ac4c1b63e54d579838556307a37045dda1a4` | `3585fdc2aa2d36b699a9f43a031654bcf409216b2800392c8c02ff56d8a1431e` |

The source pins are orchestrator `db38737d63363a059212820aaac40b4026f82b51`, root producer `fccbb76350f91e428f9f19c731b588eca5f5df01`, and workflow `6c0a2e55889c030156fb53763848d4f1bbc7ece1`. Untouched original bundles are retained under `/mnt/raid0/llm/artifacts/ci/ni42-graph-fixtures-37339553198-original-download/`; per-module native files are beneath `ni42-graph-37339553198-1-<module-id>/artifacts/ni42-graph-fixtures/37339553198/1/<module-id>/native/`. Each original receipt binds its command log and JUnit; all five independent postchecks have SHA-256 `7565d45ecb0e342309dc84be38f08872b46e75bcbefcdcf8ceb1ca1e273d70f8`, with all three explicit CPP_BIN, MTMD, and LLAMA_SERVER targets absent and non-symlink. The second direct GitHub download was byte-identical to the first retained bundle.

The run used the locked `dev` and `graph` extras, actual runner memory (no synthetic-capacity bootstrap), temporary test databases, and mocked or deterministic embedding providers; no live corpus, embedding service, or inference was involved. The sub-100ms assertion in the graph integration module is recorded only as an ordinary test result, not as a performance measurement. This closes the named optional-graph fixture scope, not graph behavior against production data or the wider unit suite.
