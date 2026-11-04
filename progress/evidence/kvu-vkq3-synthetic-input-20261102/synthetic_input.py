#!/usr/bin/env python3
"""Generate the fixed VKQ3 diagnostic input; stdout contains only input bytes.

This is synthetic structured text, not a transcript. Its fixed parameters are
part of the input identity. It is not a tokenizer or a rowflow worker.
"""
import sys

RECORDS = 70_000


def generate(stream):
    for i in range(RECORDS):
        stream.write(
            (f"sample={i:05d} value={(i * 7919 + 104729) % 1000003:06d} "
             f"category={i % 17:02d} synthetic diagnostic text.\n").encode('ascii')
        )


if __name__ == '__main__':
    generate(sys.stdout.buffer)
