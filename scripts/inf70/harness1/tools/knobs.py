#!/usr/bin/env python3
"""INF-70 HARNESS-1: writer for the ggml live knob control page (see ggml-cpu-knobs.h).

  knobs.py init <path>                    create/zero a 4096-byte page (seq = 0)
  knobs.py set  <path> KEY=VAL [KEY=VAL]  publish a new arm
  knobs.py show <path>                    print seq + the active slot

Layout: [0..8) uint64 seq LE, slot = seq & 1; slot0 at 512, slot1 at 1536, 1024 bytes each.
Double-buffered because the server re-parses the slot the seq selects: the writer fills the
INACTIVE slot first and bumps seq last, so a reader never observes a half-written payload.
An arm's payload is COMPLETE -- a key absent from it reverts to the server's env-derived value.
"""
import mmap, os, struct, sys

SZ, SLOT0, SLOTSZ = 4096, 512, 1024

def _open(path):
    f = open(path, "r+b")
    return f, mmap.mmap(f.fileno(), SZ)

def main():
    if len(sys.argv) < 3: sys.exit(__doc__)
    op, path = sys.argv[1], sys.argv[2]
    if op == "init":
        with open(path, "wb") as f: f.write(b"\0" * SZ)
        os.chmod(path, 0o644); print(f"init {path} seq=0"); return
    f, m = _open(path)
    seq = struct.unpack_from("<Q", m, 0)[0]
    if op == "show":
        blob = m[SLOT0 + (seq & 1)*SLOTSZ : SLOT0 + (seq & 1)*SLOTSZ + SLOTSZ].split(b"\0")[0]
        print(f"seq={seq} slot={seq & 1}\n{blob.decode()}")
    elif op == "set":
        payload = ("\n".join(sys.argv[3:]) + "\n").encode()
        if len(payload) >= SLOTSZ: sys.exit("payload too large")
        nxt = seq + 1
        off = SLOT0 + (nxt & 1)*SLOTSZ                 # write the slot the NEW seq selects
        m[off:off+SLOTSZ] = payload + b"\0"*(SLOTSZ-len(payload))
        m.flush()
        struct.pack_into("<Q", m, 0, nxt)              # publish last
        m.flush()
        print(f"seq={nxt} slot={nxt & 1} {' '.join(sys.argv[3:])}")
    else: sys.exit(__doc__)
    m.close(); f.close()

main()
