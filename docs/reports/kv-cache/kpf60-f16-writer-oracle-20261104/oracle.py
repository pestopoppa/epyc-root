"""Byte-exact oracle for one declared synthetic state_write_data fixture.

The expected bytes are independently fixed from the fixture's selected
physical rows and byte pattern. They are not a parser for arbitrary GGML data.
"""
import argparse
from pathlib import Path
import sys

# Source 8952a0f: GGML_TYPE_F16 == 1. 2 layers, 8 bytes per K/V row,
# selected physical cells {1, 2, 5}, non-transposed V. Each tensor byte i
# equals (i + 31*layer + (79 if V else 0)) & 255 in the proposed C++ fixture.
# These literals intentionally do not invoke the producer or its parser.
EXPECTED = bytes.fromhex('''
    00000000 02000000
    01000000 08000000 00000000
    08090a0b 0c0d0e0f 10111213 14151617 28292a2b 2c2d2e2f
    01000000 08000000 00000000
    2728292a 2b2c2d2e 2f303132 33343536 4748494a 4b4c4d4e
    01000000 08000000 00000000
    5758595a 5b5c5d5e 5f606162 63646566 7778797a 7b7c7d7e
    01000000 08000000 00000000
    76777879 7a7b7c7d 7e7f8081 82838485 96979899 9a9b9c9d
''')


def compare(blob: bytes) -> tuple[bool, str]:
    if type(blob) is not bytes:
        raise TypeError('blob must be bytes')
    if len(blob) != len(EXPECTED):
        return False, f'length: expected {len(EXPECTED)}, got {len(blob)}'
    for offset, (actual, expected) in enumerate(zip(blob, EXPECTED)):
        if actual != expected:
            return False, f'byte {offset}: expected 0x{expected:02x}, got 0x{actual:02x}'
    return True, 'all 152 bytes match the fixed fixture oracle'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('data_blob', type=Path, help='captured raw state_write_data bytes')
    args = parser.parse_args(argv)
    try:
        ok, message = compare(args.data_blob.read_bytes())
    except OSError as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2
    print(('MATCH: ' if ok else 'MISMATCH: ') + message)
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
