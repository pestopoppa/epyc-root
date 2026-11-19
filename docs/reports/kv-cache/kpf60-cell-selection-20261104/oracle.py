"""Independent simple-layout byte oracle; does not inspect a model or native data."""
from dataclasses import dataclass

MAX_U64 = (1 << 64) - 1

@dataclass(frozen=True)
class Layer:
    key_row_bytes: int
    value_row_bytes: int | None


def expected_bytes(cells: int, layers: list[Layer]) -> tuple[list[tuple[int, int]], int, int]:
    """Calculate non-transposed, already-aligned rows, rejecting non-u64 input.

    Row byte sizes are independently established fixture constants, not inferred
    from a GGML dtype. This cannot validate quantization or transfer I/O.
    """
    def valid(x):
        return type(x) is int and 0 < x <= MAX_U64
    if not valid(cells) or not layers:
        raise ValueError('positive cells and layers required')
    totals = []
    sum_k = sum_v = 0
    for layer in layers:
        if not isinstance(layer, Layer) or not valid(layer.key_row_bytes):
            raise ValueError('invalid K row')
        if layer.value_row_bytes is not None and not valid(layer.value_row_bytes):
            raise ValueError('invalid V row')
        k = cells * layer.key_row_bytes
        v = cells * (layer.value_row_bytes or 0)
        sum_k += k
        sum_v += v
        if max(k, v, sum_k, sum_v, sum_k + sum_v) > MAX_U64:
            raise OverflowError('payload exceeds u64')
        totals.append((k, v))
    return totals, sum_k, sum_v
