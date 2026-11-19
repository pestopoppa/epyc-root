# IFBench pinned corpus

The selected upstream root `data/IFBench_test.jsonl` is preserved byte-for-byte from allenai/IFBench commit `1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d`. `PROVENANCE.json` records upstream URLs, source Git blob IDs, byte counts, SHA-256 digests, attribution and license information; `LICENSE` and `UPSTREAM-README.md` are unchanged upstream files. The prepared scorer/venv and NLTK data are separate, and this corpus is not itself an inference result.

The corpus has 300 rows with unique prompts, 344 instruction instances, and 58 distinct instruction IDs. The different upstream `ifbench/data/IFBench_test.jsonl` is not substituted for the selected root file. All results must retain exact prompt identity; report a cross-arm delta only from paired outcomes on the same prompts.

See [RUN-CONTRACT.md](RUN-CONTRACT.md) for the pre-run coverage, uncertainty and pairing rules.

[questions-manifest.json](questions-manifest.json) was materialized by `proposed/cj567/ifbench_fixture.py` (SHA-256 `008ec4926cd0aee271534ed5cbde329c83146ac27cf29a6553baf7a21bb4e878`). It pins 300 original prompt IDs and the prospective `ifbench_prompt_loose` and `ifbench_prompt_strict` keys; `ifbench_external` is generation-only and never substitutes for official scoring.

**Runner limitation:** The current V7 runner skips items whose `expected` field is empty, so this manifest does not by itself execute IFBench generation in V7. Treat it as pinned identity and preregistration metadata. The prepared IFBench worker consumes the original corpus directly and passes generated prompt/response records to the official offline scorer; do not substitute a placeholder expected answer or treat generation-only runner scores as official results.

Data attribution: `allenai/IFBench` at the pinned commit; data license [ODC-BY 1.0](https://opendatacommons.org/licenses/by/1-0/). Upstream code license is Apache-2.0; its retained `LICENSE` is not a substitute for the data license.
