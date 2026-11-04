"""Parse a known-geometry, little-endian plain F16 state_write_data fixture.

Diagnostic calibration aid, not a general llama state-file or model parser.
Caller supplies independent fixture geometry and declared F16 GGML type ID.
"""
from dataclasses import dataclass
import struct

MAX_U64 = (1 << 64) - 1

@dataclass(frozen=True)
class Layer:
    k_row_bytes: int
    v_row_bytes: int | None


def parse_plain_f16(blob: bytes, cells: int, layers: tuple[Layer, ...], f16_type: int):
    if type(blob) is not bytes or type(cells) is not int or not (0 < cells <= MAX_U64):
        raise ValueError('invalid blob or cell count')
    if not isinstance(layers, tuple) or not layers or type(f16_type) is not int or not (0 <= f16_type < 2**31):
        raise ValueError('invalid declared fixture')
    for layer in layers:
        if not isinstance(layer, Layer):
            raise ValueError('invalid layer')
        for row in (layer.k_row_bytes, layer.v_row_bytes):
            if row is not None and (type(row) is not int or row <= 0 or row % 2 or row > MAX_U64 // cells):
                raise ValueError('invalid or overflowing F16 row')
        if layer.k_row_bytes is None:
            raise ValueError('missing key')
    offset = 0
    metadata = 0
    outputs = []
    totals = {'K': 0, 'V': 0}
    def read(n):
        nonlocal offset
        if n < 0 or n > len(blob)-offset:
            raise ValueError('truncated blob')
        result = blob[offset:offset+n]
        offset += n
        return result
    def u32():
        nonlocal metadata
        metadata += 4
        return struct.unpack('<I', read(4))[0]
    def u64():
        nonlocal metadata
        metadata += 8
        return struct.unpack('<Q', read(8))[0]
    trans, count = u32(), u32()
    if trans != 0 or count != len(layers):
        raise ValueError('unsupported transpose or layer count')
    for role in ('K', 'V'):
        for index, layer in enumerate(layers):
            row = layer.k_row_bytes if role == 'K' else layer.v_row_bytes
            if row is None:
                continue
            if u32() != f16_type or u64() != row:
                raise ValueError('dtype or row-size mismatch')
            n = row * cells
            if totals[role] > MAX_U64 - n:
                raise ValueError('payload overflow')
            payload_offset = offset
            read(n)
            totals[role] += n
            outputs.append({'layer': index, 'role': role, 'offset': payload_offset, 'length': n})
    if offset != len(blob) or metadata > MAX_U64 - totals['K'] or metadata + totals['K'] > MAX_U64 - totals['V']:
        raise ValueError('trailing bytes or total overflow')
    return {'metadata_bytes': metadata, 'k_bytes': totals['K'], 'v_bytes': totals['V'],
            'total_bytes': offset, 'payloads': outputs}
