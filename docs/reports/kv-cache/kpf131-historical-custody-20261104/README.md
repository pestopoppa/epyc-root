# KPF-13.1b historical image custody inventory

Offline inventory only. This is not a qualified custody receipt and does not authorize a GPU run.

The retained `default_specoff` native record is SHA-256 bound and its recorded llama-server digest matches the currently retained `gpu-20261020-a1f0c8cf9` executable. The retained linkage log resolves the GGML libraries into that image directory. Current binaries in that directory match the offline audit's saved hashes.

This still cannot prove historical mapped DSO contents: the old native record has no run-time mapped-file digest/proc-map manifest. The linkage helper source/version/hash is also absent. The external observer audit says the exact image has no layout trace markers; no qualified same-image observer supplies physical KV layout and task/batch binding. Therefore this inventory is not ready for a same-image matched-control run.

See `HISTORICAL-CUSTODY-INVENTORY.json` for exact paths, hashes, evidence classes, and missing prerequisites. No compute, model access, inference, build, grant, publication, or lane edit was performed.
