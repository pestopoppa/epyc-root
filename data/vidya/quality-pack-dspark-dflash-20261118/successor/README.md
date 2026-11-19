# DFlash2 successor replay

The [first full grant](../first-full-attempt/scheduler.ended) ended with rc=1 before server launch. The [successor receipt](receipt.json) records the genuine CPU publisher smoke PASS and preserves the readiness disposition. The full paired capture has its own terminal evidence.

Run the [offline controls](offline_controls.py) from the repository root. They reconstruct the published bytes in a temporary directory under `/mnt/raid0/llm/tmp/vidya-belief-substrate`, verify every entry in [SOURCE.sha256](SOURCE.sha256), and replay the copied-witness, request-pair and response-telemetry controls. They use local external asset pins from the plan and do not launch a server. [Recorded output](offline-controls.txt)

```bash
python3 -B data/vidya/quality-pack-dspark-dflash-20261118/successor/offline_controls.py
```

To reconstruct the exact packet for inspection, supply a new directory. The reconstruction reads raw files from this directory or the parent packet, decodes `*.original-bytes.json` files to their original names, verifies each envelope digest against the decoded bytes, and checks the published source manifest.

```bash
python3 -B data/vidya/quality-pack-dspark-dflash-20261118/successor/offline_controls.py \
    --reconstruct /mnt/raid0/llm/tmp/vidya-belief-substrate/dflash2-successor-packet
(cd /mnt/raid0/llm/tmp/vidya-belief-substrate/dflash2-successor-packet && sha256sum --check --strict SOURCE.sha256)
```

The reconstructed archive retains original absolute paths. Use it to inspect the source bytes and provenance.
