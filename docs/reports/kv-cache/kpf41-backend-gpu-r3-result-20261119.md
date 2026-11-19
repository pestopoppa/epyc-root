# KPF-41 backend GPU r3: PASS

The corrected full FLASH_ATTN_EXT corpus completed on gfx90a (ROCm0): 5,207 selected cases reconcile to 2,978 OK and 2,229 unsupported. All 25 required shared-trunk cases are OK, with zero failed cases. The final log reports 2978/2978 tests passed, ROCm0 OK and 2/2 backends passed (CPU skipped). Wrapper and child rc are 0. The parser reconciles 207 interleaved graph diagnostics.

Owned PID 3514610 was sampled during execution: 5,279 of 5,282 samples contain both positive VRAM under that PID's KFD directory and the expected HIP library mapping. Peak sampled VRAM is 3,637,227,520 bytes. No cleanup signals were needed.

The launcher reaches QUALIFICATION_PASS only after its before/after check() calls verify all five build-receipt artifact hashes, detached source commit `15caecbbf4cb27452dbd87fa1a68a0e75098388e`, clean tracked source state and local ggml loader paths. Both linkage records are present. These are recorded execution checks; no new benchmark was run during filing.

This answers the scoped backend-corpus qualification question at one complete corpus. Unsupported cases retain their unsupported status; the result does not establish their correctness, CPU qualification, production deployment, throughput improvement or a formal statistical gate. Prior r2 remains INCONCLUSIVE.

Evidence stays in place; no logs, binaries or source trees are copied. Base path: `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf41-backend-gpu-qualification-r3-20261119/`.

| Relative evidence path | SHA-256 |
|---|---|
| `out/RESULT.json` | `a340e8d9548ad1032a0c467292cc1c1922eaaa4aa1b43342c548f5a06d0672d7` |
| `out/corpus.log` | `fc1be8b486233ac6f25f7da5d57efd6b6e194408bb08733245e6e35a975bbe60` |
| `job.py` | `c5b689b5b16f09809c73bd06086f0dcbbf1f4e720536569c8999e4c60718b980` |
| `receipt.json` | `4b08e349541a0b6eb3ceedd61ec7c16be34858a065dbb8a81441d43bb736423c` |
| `corpus_parser.py` | `3bf112be8214b2e2be9a91af79153d3b4f990e1febef9ac801286f4019afc185` |

Filing preserves scratch with `--no-reclaim` to retain all case logs and unsupported-case identities required by the decision rule. This conclusion is captured as a committed observation (`[belief: cc]`).
