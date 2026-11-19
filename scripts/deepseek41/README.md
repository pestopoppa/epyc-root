# DeepSeek 4.1 loader contract probe

`test_loader_contract.cpp` runs the experimental native loader on an existing
DeepSeek 4.1 GGUF. Pass the first shard for a split model. It creates no inference
context. `no_alloc=true`, `use_mmap=false`, and `use_mlock=false` keep weight
payloads unread while the real architecture loader validates its expected tensor
shapes and CPU operation/type compatibility. The probe also checks all 29
antirez metadata aliases, canonical-key precedence, type/block layouts for every
tensor, and native rejection of an incorrect shape for every tensor.

Build against headers from the **exact source commit** in the experimental
build's `BUILD-IDENTITY.json`. Verify library hashes against its manifest first;
verify the headers' Git blob IDs against that source commit. Do not use production
kernel headers or libraries. Set `LD_LIBRARY_PATH` explicitly to the tested build.
For example, with `source_dir`, `build_dir`, `scratch_dir` and `first_shard` set:

```bash
g++ -std=c++17 -O0 \
  -I "$source_dir/include" -I "$source_dir/src" -I "$source_dir/ggml/include" \
  scripts/deepseek41/test_loader_contract.cpp \
  -L "$build_dir/bin" -Wl,-rpath,"$build_dir/bin" \
  -lllama -lggml -lggml-base -o "$scratch_dir/test_loader_contract"
env LD_LIBRARY_PATH="$build_dir/bin" OMP_NUM_THREADS=4 \
  timeout 45 "$scratch_dir/test_loader_contract" "$first_shard"
```

The model must already exist. The probe performs no downloads, weight hashing,
weight copies, benchmark runs or inference. A PASS establishes loader metadata
compatibility for that particular model/build pair. It does not establish weight
data integrity, numerical parity, graph correctness, residency or throughput.
The shape rejection checks test the native guard; expected architecture shapes
are checked independently by the initial full metadata-only load.

## DS41-B2 result, 2026-11-19

PASS, rc 0: `arch=deepseek41 aliases=29 canonical_precedence=1 shapes=1046
shape_rejections=1046 type_layouts=1046 no_alloc=1 weight_reads=0`.
Model: `models/antirez/deepseek-v4.1-flash-gguf/DeepSeek-V4.1-Flash-1017-MXFP4-experts-00001-of-00009.gguf`
plus the other eight existing shards. Native loader: experimental source
`eee3da838e3c8306a856f2c72c4b04048fded698`, build
`/mnt/raid0/llm/kernels/builds/cpu-20261118-eee3da838-c14`.
The executable used the build's manifest-verified `libllama.so.0`, `libggml.so.0`,
`libggml-base.so.0` and `libggml-cpu.so`; probe interface header blob IDs matched
the declared source commit. `libllama.so.0` SHA-256:
`997247c31f7edd2d54d91721e7db14947fbaa511ceeca53679cb73a3a8f04c0c`.

Original output remains at
`/mnt/raid0/llm/tmp/deepseek-v41-flash-evaluation/b2/native.log`, SHA-256
`da626d90e3dacb1f567950c22e382b27550515d407d38fe98e40b282e4ed5dcd`.
Probe executable SHA-256:
`1e94eb5d41af6cbc5b125dc037c86cba4410438035281d6acedb670a090eef1b`.
These are references to original files, not copied evidence.
