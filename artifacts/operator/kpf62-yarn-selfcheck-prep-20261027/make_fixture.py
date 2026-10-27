#!/usr/bin/env python3
"""Create a YaRN tiny fixture using the accepted source's GGUF writer.

Run only under the prospective native capture grant; input is newly generated
Qwen3 GGUF in the same run. This script performs no inference.
"""
import sys
from pathlib import Path
source = Path('/mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-fixed-build/candidate')
sys.path.insert(0, str(source / 'gguf-py'))
import gguf
from gguf.scripts.gguf_new_metadata import MetadataDetails, copy_with_new_metadata
src, dst = map(Path, sys.argv[1:])
if dst.exists() or src.resolve() == dst.resolve():
    raise SystemExit('destination exists or aliases input')
r = gguf.GGUFReader(src)
if r.get_field('general.architecture').contents() != 'qwen3':
    raise SystemExit('expected generated qwen3')
new = {
    'qwen3.rope.scaling.type': MetadataDetails(gguf.GGUFValueType.STRING, 'yarn'),
    'qwen3.rope.scaling.factor': MetadataDetails(gguf.GGUFValueType.FLOAT32, 4.0),
    'qwen3.rope.scaling.original_context_length': MetadataDetails(gguf.GGUFValueType.UINT32, 512),
    'qwen3.rope.scaling.attn_factor': MetadataDetails(gguf.GGUFValueType.FLOAT32, 1.25),
}
w = gguf.GGUFWriter(dst, 'qwen3', endianess=r.endianess)
copy_with_new_metadata(r, w, new, ["tokenizer.ggml.merges", "qwen3.classifier.output_labels"])
check = gguf.GGUFReader(dst)
for key, expected in [('qwen3.rope.scaling.type', 'yarn'), ('qwen3.rope.scaling.factor', 4.0), ('qwen3.rope.scaling.original_context_length', 512), ('qwen3.rope.scaling.attn_factor', 1.25)]:
    if check.get_field(key).contents() != expected:
        raise SystemExit(f'metadata mismatch: {key}')
print('YaRN fixture metadata verified')
