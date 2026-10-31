# YaRN aggregate final analysis — 2026-10-31

This packet records the accepted offline reanalysis of the immutable 141-pair YaRN aggregate run and the exact prospectively declared original 120-pair subset. The native capture is preserved under `native/`; no model weights, raw prompt blobs, or expanded 141-item prompt manifest are included; the complete 141-item plan metadata and score/output streams are preserved. `A0.jsonl.gz` and `A1.jsonl.gz` are deterministic gzip (`-n`) copies of the native output streams. Their uncompressed SHA-256 and byte counts are recorded in `ARTIFACT-SHA256.json`.

## Result

Under the registered one-sided exact McNemar rule (alpha 0.05; score >= 1.0 counts right; fail if p <= 0.05), both analyses are **NOT-FAIL**: full 141 pairs has 7 A0-right/A1-wrong and 11 A0-wrong/A1-right, p=0.8810577392578125, mean A1−A0=0.03667996453900709; the exact registered 120 has 5 and 10, p=0.940765380859375, mean difference=0.051432291666666664. Both meet the 10-new-discordant-pair power target. NOT-FAIL means no harm detected at this sample size; it is not an equivalence, safety, or adoption claim. The historical 3-discordant extension remains separate and excluded.

The corrected extractor applies `real_n == prompt_n + cache_n` and retains the existing plan, pin, hash, pairing, zone, and status checks. The missing-pair, prompt-hash, and served-count negative controls reject. The exact r11 supersession comparison is in `R11-SUPERSESSION-EQUALITY.json`; do not rerun the duplicate GPU measurement. The original postprocessor exit status remains failed and is retained as historical evidence; this is a separate offline quality verdict.

## Provenance and checks

`SOURCE-ARTIFACTS.sha256.json` is the original source packet manifest. Its native paths and hashes were verified before copying. `archive/scripts/benchmark/yarn_gate/` contains the four original source modules listed by `ARCHIVE.sha256`; the large source haystacks and bundle are not duplicated. Transfer source: `refs/ni-transfer/yarnagg-analysis-20261031` (commit `26e8f3b31b520f9bb5387f07708b88f9f22db33e`). `ARCHIVE.sha256` is the immutable original packet's internal file manifest. `ARTIFACT-SHA256.json` inventories every file in this published artifact directory (excluding itself), including the uncompressed native stream digests. Verify with:

```bash
python3 - <<'PY'
import gzip, hashlib, json
from pathlib import Path
root = Path('artifacts/compute/ni-yarnagg-final-20261031')
manifest = json.loads((root / 'ARTIFACT-SHA256.json').read_text())
for name, row in manifest.items():
    data = (root / name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == row['sha256']
    assert len(data) == row['size_bytes']
for arm in ('A0', 'A1'):
    data = gzip.decompress((root / 'native' / f'{arm}.jsonl.gz').read_bytes())
    row = manifest[f'native/{arm}.jsonl.gz']['uncompressed']
    assert hashlib.sha256(data).hexdigest() == row['sha256']
    assert len(data) == row['size_bytes']
print(f"verified {len(manifest)} files and both native streams")
PY
```

The root progress/handoff/source-table semantics and checkbox application belong to the owning main session and are intentionally not edited in this evidence packet.
