# KPF-RS-1 r6 skipped-source reference review

Reviewed 2026-11-05 against exact candidate commit `8952a0f693fb923918157eb25117641b74766230` in `/mnt/raid0/llm/llama.cpp-experimental`. This was a read-only source inspection; no build, inference, benchmark, graph re-index, or native impact rerun was performed.

## Scope and method

The retained `analyze.stdout` explicitly reports 25 skipped files and enumerates them. Four are C++ source files; the remainder are benchmark HTML/JSON and vocabulary GGUF files. `coverage.json` inventories large tracked files more broadly and is not itself the native skipped-file list.

For each of the four source paths below, read the committed blob using:

```sh
git -C /mnt/raid0/llm/llama.cpp-experimental show 8952a0f693fb923918157eb25117641b74766230:<path>
```

The inspection used Python `subprocess.check_output` to retrieve each blob, decoded its text, enumerated lines starting at 1, and applied this case-sensitive whole-identifier regular expression to every line:

```python
r"\b(build_conv_state|build_recurrent_attn|seq_rm|seq_cp|state_write|state_read|s_copy)\b"
```

These are the seven identifiers from the source-bound r6 native upstream impacts: `build_conv_state` and `build_recurrent_attn` in `src/models/delta-net-base.cpp`; `seq_rm`, `seq_cp`, `state_write`, `state_read`, and `s_copy` in `src/llama-memory-recurrent.cpp`.

## Scoped results

| Exact committed source path | Whole-identifier matches |
|---|---|
| `ggml/src/ggml-cpu/arch/x86/repack.cpp` | None of the seven identifiers |
| `ggml/src/ggml-opencl/ggml-opencl.cpp` | None of the seven identifiers |
| `ggml/src/ggml-vulkan/ggml-vulkan.cpp` | None of the seven identifiers |
| `tests/test-backend-ops.cpp` | One `seq_cp` occurrence at line 8884, in a comment; no other target matches |

The matching comment at `8952a0f693fb923918157eb25117641b74766230:tests/test-backend-ops.cpp:8884` is:

```cpp
// each), the cell layout a cross-slot prefix fork produces (KPF-12, zero-copy seq_cp): those blocks are live for
```

No direct textual call to the seven targets was found in these four skipped source files. A separate skipped-source target-reference prerequisite is therefore unnecessary for this scoped concern.

This result does not establish transitive impact completeness, complete native graph coverage, absence of indirect dispatch, or native edit safety. The retained capped native scan remains capped; its zero-impact results must not be generalized to omitted code.
