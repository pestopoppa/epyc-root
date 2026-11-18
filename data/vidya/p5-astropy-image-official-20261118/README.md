# Official Astropy scorer image build custody

The official offline build recorded exit code `0` and completion at `2026-11-18T19:55:46.005380+00:00`. Its image ID is `sha256:3dcf849904aa1395cff121684a80332a134cd4b34d806514f97c082bdb83b337`. This bundle documents offline image build custody only. Native scorer correctness requires separate execution evidence.

- `RESULT.json` is the original receipt from `/mnt/raid0/llm/tmp/vidya-belief-substrate/p5-astropy-scorer-r1-20261118/official/RESULT.json`.
- `build.log`, `rowflow.grant`, `image.iid`, and `receipt.json` come from the original attempt at `/mnt/raid0/llm/tmp/vidya-belief-substrate/p5-astropy-scorer-r1-20261118/official/build-vj_kqts8/`.
- The source manifest, launch scripts, and base-pull records come from `/mnt/raid0/llm/tmp/vidya-belief-substrate/p5-astropy-scorer-r1-20261118/`.
- The Dockerfile, requirements, and context and wheelhouse manifests come from `/mnt/raid0/llm/tmp/vidya-belief-substrate/p5-astropy-scorer-r1-20261118/context/`. The wheel archives remain in that context's `wheelhouse/` directory.

Run `sha256sum -c SHA256SUMS` from this directory to verify the retained bytes and this README.
