#!/usr/bin/env python3
"""Reproduce KPF-60's attention-only *estimated*, not measured, load comparison."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = {
    'bench-ub512.json': '6a5071a41f8b6af0fc5d20a0d57f3df8c1f2c2ad99f22d4e278ebcd951e219c5',
    'bench-ub2048.json': '16caa1103f41fc82a300dbb4a92154bee8babee7536dff8e45d349409d1764e5',
    'pcie.json': 'c513cfabb2b2530012b6756a6bd6db1a225790d6e6a39406d33cbcf7a733f675',
    'nvme-1024m.txt': 'dc6c223971dc5c3609664051ff4cc0f5ca8c5cfe2babb9f118739fcc9dd91d30',
}
for name, expected in EXPECTED.items():
    assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == expected, name

# Metadata: (65 total blocks - 1 NextN)/4 = 16 attention layers;
# 4 KV heads per layer, 256 elements per head for each of K and V, f16=2 bytes.
BYTES_PER_TOKEN = 16 * 4 * (256 + 256) * 2
assert BYTES_PER_TOKEN == 65536
PCI_BYTES_S = 28.9e9
# Representative 4.5 GB/s per KPF-60 P0 note, not a measured chunk-read rate.
NVME_BYTES_S = 4.5e9
print('| ubatch | prompt tokens | measured pp tok/s | f16 KV MiB | PCIe ms | NVMe ms | NVMe + PCIe ms | recompute ms |')
print('|---:|---:|---:|---:|---:|---:|---:|---:|')
for ub in (512, 2048):
    data = json.loads((HERE / f'bench-ub{ub}.json').read_text())
    assert {row['n_prompt'] for row in data} == {512, 2048, 8192}
    for row in data:
        assert row['n_ubatch'] == ub and row['type_k'] == row['type_v'] == 'f16'
        assert row['model_type'] == 'qwen35 27B Q8_0' and row['avg_ts'] > 0
        n, rate = row['n_prompt'], row['avg_ts']
        size = n * BYTES_PER_TOKEN
        pcie_ms = size / PCI_BYTES_S * 1000
        nvme_ms = size / NVME_BYTES_S * 1000
        print(f'| {ub} | {n} | {rate:.2f} | {size / 2**20:.0f} | {pcie_ms:.2f} | {nvme_ms:.2f} | {pcie_ms + nvme_ms:.2f} | {n / rate * 1000:.2f} |')
