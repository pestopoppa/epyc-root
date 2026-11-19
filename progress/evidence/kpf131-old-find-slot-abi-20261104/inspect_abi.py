"""Inspect selected x86-64 find_slot instruction bytes, not a layout decoder."""
import hashlib
import json
from pathlib import Path
import struct
import sys

PIN = '33bf73eaedfee5a52aa07312d0d12431133e23c54d411744e7bd51bccf375f64'
# Instruction bytes are tied to this build's virtual addresses and digest.
SITES = {
    0x15a295: '448b4670',             # read 32-bit [rsi+0x70]
    0x15a299: '48897c2470',           # save incoming rdi
    0x15a29e: '4889742438',           # save incoming rsi
    0x15a2a3: '4889542448',           # save incoming rdx
    0x15a2a8: '894c242c',             # save incoming ecx
    0x15a2c8: '8b7a10',               # 32-bit [rdx+0x10]
    0x15a2e6: '488b4040',             # pointer [rdx+0x40], after spill reload
    0x15a2f3: '488b86c8000000',       # pointer [rsi+0xc8], after spill reload
    0x15a304: '488b96c0000000',       # pointer [rsi+0xc0]
    0x15a30b: '4869d898300000',       # imul 0x3098 stream stride
    0x15a318: '488b9690000000',       # pointer [rsi+0x90]
    0x15a4aa: '488b442470',           # reload saved incoming rdi
    0x15a4bf: '660fd600',             # movq xmm0,(rax), after reload
    0x15a4f4: '488b442470',           # return saved incoming rdi in rax
}

class Invalid(ValueError):
    pass


def offset_for_vaddr(blob, address, length):
    if len(blob) < 64 or blob[:6] != b'\x7fELF\x02\x01':
        raise Invalid('not little-endian ELF64')
    try:
        if struct.unpack_from('<H', blob, 18)[0] != 62:
            raise Invalid('not x86-64')
        phoff = struct.unpack_from('<Q', blob, 32)[0]
        entsize, count = struct.unpack_from('<HH', blob, 54)
        if entsize < 56 or count == 0 or phoff + entsize * count > len(blob):
            raise Invalid('invalid program headers')
        matches = []
        for i in range(count):
            ptype, flags, off, va, _, filesz, _, _ = struct.unpack_from('<IIQQQQQQ', blob, phoff + i * entsize)
            if ptype == 1 and flags & 1 and va <= address and address + length <= va + filesz:
                mapped = off + address - va
                if mapped + length > len(blob): raise Invalid('segment outside file')
                matches.append(mapped)
        if len(matches) != 1: raise Invalid('ambiguous or absent executable segment')
        return matches[0]
    except (struct.error, OverflowError):
        raise Invalid('malformed ELF') from None


def inspect(blob, pin=PIN):
    digest = hashlib.sha256(blob).hexdigest()
    if digest != pin: raise Invalid('image digest mismatch')
    for va, signature in SITES.items():
        expected = bytes.fromhex(signature)
        off = offset_for_vaddr(blob, va, len(expected))
        if blob[off:off+len(expected)] != expected: raise Invalid(f'instruction mismatch at {va:#x}')
    return {'sha256': digest, 'checked_sites': len(SITES), 'function_va': '0x15a280',
            'scope': 'machine-code dataflow signatures only; no live objects or batch attribution'}

if __name__ == '__main__':
    try:
        if len(sys.argv) != 2: raise Invalid('one explicit image path required')
        print(json.dumps(inspect(Path(sys.argv[1]).read_bytes()), sort_keys=True))
    except (OSError, Invalid) as exc:
        print(f'INVALID: {exc}', file=sys.stderr)
        raise SystemExit(1)
