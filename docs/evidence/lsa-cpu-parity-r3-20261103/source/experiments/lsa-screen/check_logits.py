"""Strict predeclared all-keys parity check; refuses missing or malformed evidence."""
import array
import json
import math
import sys
from pathlib import Path


def floats(path):
    raw = Path(path).read_bytes()
    if not raw or len(raw) % 4:
        raise ValueError("empty or malformed logits")
    values = array.array("f")
    values.frombytes(raw)
    if not all(map(math.isfinite, values)):
        raise ValueError("non-finite logits")
    return values


def metadata(path, arm, affinity):
    lines = [line for line in Path(path).read_text().splitlines() if line.startswith("LSA_LOGITS ")]
    if len(lines) != 1:
        raise ValueError("missing or duplicate native logits metadata")
    fields = dict(part.split("=", 1) for part in lines[0].split()[1:])
    expected = {"model": "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf", "arm": arm,
                "input_sha256": "209249faab8ffb4bfe2e966b85b9caaa6628a427da237e0e158a76f31fb495ef",
                "tokens": "45", "configured_type_k": "bf16", "configured_type_v": "bf16",
                "ctx": "1024", "threads": "4", "threads_batch": "4", "affinity": affinity, "configured_gpu_layers": "0"}
    if any(fields.get(k) != v for k, v in expected.items()) or int(fields.get("vocab", "0")) < 1:
        raise ValueError("native metadata does not match frozen parity recipe")
    return int(fields["vocab"])


def main():
    dense, oracle, trace, dense_log, oracle_log, affinity, output = sys.argv[1:]
    if affinity not in ("0,1,2,3", "24,25,26,27", "48,49,50,51", "72,73,74,75"):
        raise ValueError("expected affinity must be a publisher four-core mask")
    expected_vocab = metadata(dense_log, "dense", affinity)
    if metadata(oracle_log, "all", affinity) != expected_vocab:
        raise ValueError("native vocabulary dimensions differ")
    if Path(dense).stat().st_size != 4 * expected_vocab or Path(oracle).stat().st_size != 4 * expected_vocab:
        raise ValueError("logit byte length does not match native vocabulary")
    a, b = floats(dense), floats(oracle)
    if len(a) != expected_vocab or len(b) != expected_vocab:
        raise ValueError("incomplete vocabulary")
    records = [json.loads(line) for line in Path(trace).read_text().splitlines()]
    layers = list(range(3, 64, 4))
    if sorted(r["layer"] for r in records) != layers:
        raise ValueError("expected exactly one executed callback for each global layer")
    if any(r["queries"] != 45 or r["changed"] != 0 or r["allowed_before"] != r["allowed_after"] for r in records):
        raise ValueError("unexpected query count or modified all-keys mask")
    delta = max(abs(x-y) for x, y in zip(a, b))
    arg_a = max(range(len(a)), key=a.__getitem__)
    arg_b = max(range(len(b)), key=b.__getitem__)
    result = {"passed": delta <= 1e-5 and arg_a == arg_b, "vocab": len(a), "max_abs": delta,
              "threshold": 1e-5, "dense_argmax": arg_a, "oracle_argmax": arg_b,
              "callback_layers": layers, "callbacks": len(records)}
    Path(output).write_text(json.dumps(result, indent=2) + "\n")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
