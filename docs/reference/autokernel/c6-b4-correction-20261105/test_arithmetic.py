#!/usr/bin/env python3
"""Host model of b4 q8 dot/min arithmetic, not a GPU or native-kernel test."""
import random
import struct


def half(x):
    return struct.unpack('<e', struct.pack('<e', x))[0]


def signed_byte(x):
    return x if x < 128 else x - 256


def dp4a_ones(bs):
    assert len(bs) == 4
    return sum(signed_byte(x & 255) for x in bs)


def model(q8, q4, d8, scale, minimum, dm, original_sum):
    assert len(q8) == len(q4) == 32
    d8 = half(d8)
    # Each q4_K group is split across four lanes: two 4-byte dots per lane.
    dots = []
    mins = []
    for lane in range(4):
        idx = list(range(4*lane, 4*lane+4)) + list(range(16+4*lane, 20+4*lane))
        dots.append(sum(q4[j]*q8[j] for j in idx))
        iqs = lane*2
        if iqs % 8 == 0:
            packed_sum = sum(dp4a_ones(q8[4*k:4*k+4]) for k in range(8))
            mins.append(d8 * packed_sum * minimum)
        else:
            mins.append(0.0)
    got = dm[0] * (d8 * sum(dots) * scale) - dm[1] * sum(mins)
    expected = dm[0] * (d8 * sum(a*b for a, b in zip(q4, q8)) * scale) - dm[1] * (d8 * sum(q8) * minimum)
    old = dm[0] * (d8 * sum(dots) * scale) - dm[1] * (half(original_sum) * minimum)
    assert abs(got-expected) <= 1e-11 * max(1.0, abs(expected))
    return got, old


def main():
    crafted = [
        ('zero', [0]*32, [0]*32, 0.0, 0, 0, (1.0, 1.0), 0.0),
        ('extremes', [-128,127]*16, list(range(16))*2, 0.019531, 63, 63, (0.5, 0.25), -0.4),
        ('mixed-cancellation', [-127,127, -1,1]*8, [15,0,7,8]*8, 0.007874, 11, 27, (0.25, 0.125), 0.27),
        ('half-rounding', [1]*31+[-1], [0]*32, 0.10001, 3, 63, (1.0, 1.0), 3.14),
        ('signed-byte', [-128, -127, -1, 0, 1, 126, 127, 0]*4, [15]*32, 0.03125, 63, 1, (1.0, 1.0), -0.25),
    ]
    for name, *args in crafted:
        got, old = model(*args)
        if name == 'half-rounding':
            assert abs(got-old) > 1.0, (got, old)
    rng = random.Random(61105)
    for _ in range(1000):
        q8 = [rng.randint(-127,127) for _ in range(32)]
        q4 = [rng.randint(0,15) for _ in range(32)]
        model(q8, q4, rng.uniform(0, 0.2), rng.randint(0,63), rng.randint(0,63),
              (half(rng.uniform(0,2)), half(rng.uniform(0,2))), rng.uniform(-5,5))
    # Across all four q8 block pairs, exactly one lane owns each min term.
    for base in (0, 8, 16, 24):
        assert [base+2*j for j in range(4) if (base+2*j) % 8 == 0] == [base]
    print('PASS: 5 crafted blocks, 1000 deterministic random blocks, 4 sum-lane groups; old/new discrepancy demonstrated')
    print('LIMIT: arithmetic model only; no HIP execution, lane broadcast, FP32/FMA ordering, or native tolerance validated')


def test_arithmetic():
    assert main() is None


if __name__ == '__main__':
    main()
