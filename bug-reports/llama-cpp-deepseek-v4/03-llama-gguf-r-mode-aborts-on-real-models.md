# Bug / UX: `llama-gguf <file> r` always aborts on real model files (validates against hardcoded test pattern)

**Target repo**: [`antirez/llama.cpp-deepseek-v4-flash`](https://github.com/antirez/llama.cpp-deepseek-v4-flash) — but this is upstream-inherited behavior; same applies to mainstream `ggml-org/llama.cpp`'s `examples/gguf/`
**Tip tested**: `2f2d44052`
**Severity**: LOW (UX / documentation) — example utility, not a runtime bug; metadata-read pass works correctly before the abort
**Component**: `examples/gguf/gguf.cpp:269`
**Filed by**: EPYC inference research project, 2026-05-30

## Summary

`llama-gguf <file> r` is the most obvious-looking utility for inspecting a GGUF's metadata + tensor layout. The `r` mode runs two passes:

- `gguf_ex_read_0`: dumps kv pairs + tensor metadata (works on any GGUF)
- `gguf_ex_read_1`: re-reads tensor DATA and validates each value against a hardcoded test pattern (`100.0` in every position)

The second pass is meant for round-trip testing of `gguf_ex_write_0`'s synthetic output (which writes `100.0` everywhere). Real model files have actual weights, so `gguf_ex_read_1` aborts with:

```
.../examples/gguf/gguf.cpp:269: GGML_ASSERT(gguf_ex_read_1(fname, check_data) && "failed to read gguf file") failed
```

Anyone using `llama-gguf <file> r` to inspect metadata sees a confusing assert + core dump, even though the kv + tensor-metadata pass before it succeeded.

This bit our V4 smoke test on 2026-05-28: we trusted the assert as evidence of a corrupt GGUF and chased a phantom "V4 GGUF download failed" hypothesis for several minutes before realizing the assert is structural.

## Reproduction

```bash
# Any real GGUF, V4 or otherwise:
LD_LIBRARY_PATH=build/bin ./build/bin/llama-gguf model.gguf r
# → dumps kv pairs (success), starts gguf_ex_read_1 (tensor data check),
#   aborts on first tensor: "data[0]: found <real_value>, expected 100.000000"
# → exit code 134 (SIGABRT), core dumped if ulimit -c is unlimited
```

## Expected behavior

For a utility named `llama-gguf <file> r`, naive users (us) expect "read metadata from this file". The assert on real models contradicts that expectation.

Better behaviors (any):

1. **Default to metadata-only**: `r` runs only `gguf_ex_read_0`. Add a `-k`/`--check-data` flag to opt into `gguf_ex_read_1`.
2. **Detect synthetic pattern**: `gguf_ex_read_1` skips the data check if the file's tensor data isn't all-`100.0`. Print "skipping data validation: tensors don't match test pattern" and exit 0.
3. **Rename + document**: rename the mode (`rt` for "read + test"?) and add `--help` text clarifying that `r` is for round-tripping the example writer's output, not for inspecting real models. Point users at a different tool (or stdlib gguf reader) for general metadata inspection.

## Actual behavior

```
gguf_ex_read_0: kv[0]: key = general.architecture
...all 62 kv pairs printed correctly...
gguf_ex_read_0: kv[61]: key = ...
gguf_ex_read_0: n_tensors: 1328
gguf_ex_read_0: tensor[0]: name = ..., size = ..., offset = ...
...all 1328 tensors printed correctly...
gguf_ex_read_1: reading tensor 0 data
gguf_ex_read_1: tensor[0], data[0]: found <real_value>, expected 100.000000
gguf.cpp:269: GGML_ASSERT(gguf_ex_read_1(fname, check_data) && "failed to read gguf file") failed
```

## Root cause

`examples/gguf/gguf.cpp:269` (the line that fires):

```cpp
GGML_ASSERT(gguf_ex_read_1(fname, check_data) && "failed to read gguf file");
```

`gguf_ex_read_1` calls into the data-validation loop that expects every fp32 element to be `100.0` (matches what `gguf_ex_write_0` produces in this same example). On a real model the very first value fails the check and the function returns false → `GGML_ASSERT` aborts.

This is upstream-inherited from `ggml-org/llama.cpp/examples/gguf/`, where the example is designed as a self-contained round-trip test. The fork doesn't add new behavior here.

## Suggested fix

Option 1 above is the smallest change. Minimal diff:

```cpp
int main(int argc, char ** argv) {
    if (argc < 3) { usage(); return 1; }
    const std::string mode = argv[2];
    if (mode == "w") return gguf_ex_write_0(argv[1]) ? 0 : 1;
    if (mode == "r") return gguf_ex_read_0(argv[1]) ? 0 : 1;
    if (mode == "rt" || mode == "test") {
        // Round-trip test: write the synthetic pattern, then read it back
        // with data validation. ONLY use on a fresh GGUF written by this
        // utility, not on real model files (real tensor data will fail
        // the 100.0 pattern check and abort).
        GGML_ASSERT(gguf_ex_write_0(argv[1]));
        GGML_ASSERT(gguf_ex_read_0(argv[1]));
        GGML_ASSERT(gguf_ex_read_1(argv[1], true));
        return 0;
    }
    usage();
    return 1;
}
```

The `--help` should call out `rt` as "round-trip test mode (writes + reads + data validates with a test pattern; do not use on real model files)".

## Workaround in use downstream

EPYC inference research project (2026-05-30): the V4 smoke test (`scripts/benchmark/v4_smoke_test.sh`) captures `llama-gguf <file> r` output to a file, IGNORES the eventual abort exit code, and greps the captured output for the required `deepseek4.*` kv keys + tensor counts. The comment in the script explains the rationale:

> `llama-gguf`'s `r` mode also runs `gguf_ex_read_1` which validates that tensor data matches a hardcoded test pattern (100.0 in every position) — meant for round-trip testing of the gguf example, NOT for inspecting real model files. Real GGUFs ALWAYS abort on that check. But the kv + tensor-metadata pass (`gguf_ex_read_0`) runs first and prints everything we need.

## Environment

(same as bug 01)

## Upstream cross-reference

Same behavior in `ggml-org/llama.cpp` at the corresponding `examples/gguf/gguf.cpp`. Worth filing both places — antirez's fork inherits it but the upstream example is the source.
