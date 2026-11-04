# S8-c HTTP validation cases

`api_cases.py` exercises the actual HTTP endpoint on a **caller-owned isolated
CPU server**. The caller must start the content-identified experimental
candidate with one slot, a compatible small model, loopback binding and a
private `--slot-save-path`; prepare the model and verify its identity before
the row. Supply the owned server PID, exact executable SHA-256, and a JSON
map of real mapped ggml/llama library paths to their SHA-256 digests:

```text
python3 api_cases.py --port PORT --server-pid PID --server-sha256 SHA256 \
  --dso-hashes /path/to/pinned-dsos.json --output /path/to/RESULT.json
```

The script refuses production-tree binaries, checks the listener belongs to
the supplied PID, checks the executable and mapped libraries, and checks PID
identity again before each case. Each case erases and repopulates slot 0;
do not point it at a shared or serving instance. A caller-owned process
supervisor must stop and verify the server after the test.

The cases cover absent/default values, explicit zeros, accepted boundaries,
presence-based mutual exclusion, integer overflow and wraparound, negatives,
non-integral or wrong-typed values, non-finite numbers, malformed JSON and
non-object bodies. Invalid requests must return HTTP 400 with
`invalid_request_error`. Valid requests must return a structured compact
result. The default comparison checks *response-level* equivalence across
fresh slots; it does not inspect internal parsed values or establish physical
KV continuity. The JSONL sidecar is flushed after each case so interrupted
work remains visible. A pass is only an API validation result; it does not
establish real-cache eviction correctness, quality or speed.

This packet is a test interface, not a row launcher. Build and seal the fixed
experimental server, bind its model and library identities, and let the
owning session arrange an appropriate row before executing it.
