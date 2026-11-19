# LSA final HIP compile receipt

The CPU-hosted build completed rc=0, from source commit `fd25848a11cb165bddf49673a534e83d117a1c50` and the preserved reviewed source manifest. The second unit is named `graph-cpu-wip-compile-complete`, but the bound job explicitly builds `ggml-cpu`, `ggml-hip`, `llama`, `llama-server`, and three LSA test executables under the gfx90a C5 configuration. The first unit is the ggml-base checkpoint. See `build-manifest.json` and `artifact-sha256.txt` for artifact identities. This is build evidence only: no test execution, GPU residency, model inference, quality, or performance claim.

The original terminal record says `reason=direct-run` and `regions=q1`. Paths embedded in receipts remain original producer paths; SHA256SUMS binds the preserved copies.
