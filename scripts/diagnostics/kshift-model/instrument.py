"""Instrument the pinned r1 harness without changing its historical metrics."""
import hashlib
from pathlib import Path

SOURCE_SHA = '73748c6be895d4728ffeca07b5e8f48d3c295166f70336397be35f2b24da088a'


def instrument(source):
    if hashlib.sha256(source.encode()).hexdigest() != SOURCE_SHA:
        raise ValueError('unexpected r1 harness source')
    source = source.replace('#include "llama.h"', '#include "llama.h"\n#include "fixture_bounds.h"', 1)
    source = source.replace('const int need = a.n_prefix + a.n_probe + 8;\n    if ((int) all.size() < need) die("corpus too short");',
                            'if (!kshift_fixture_fits(all.size(), a.n_prefix, a.n_probe)) die("invalid corpus slice");', 1)
    source = source.replace('static cmp_t compare(const std::vector<float>', 'static cmp_t compare(const char * scenario, const std::vector<float>', 1)
    # Keep the original KLD accumulation; append position-level evidence only.
    anchor = '        c.kld_mean += kld / n;'
    detail = '''        double second_a = -1e300, second_b = -1e300;
        for (int v = 0; v < n_vocab; v++) {
            if (v != ia) second_a = std::max(second_a, (double) a[v]);
            if (v != ib) second_b = std::max(second_b, (double) b[v]);
        }
        printf("{\\"scenario\\":\\"position\\",\\"comparison\\":\\"%s\\",\\"index\\":%d,\\"kld\\":%.9e,"
               "\\"ref_top1\\":%d,\\"test_top1\\":%d,\\"ref_margin\\":%.9e,\\"test_margin\\":%.9e}\\n",
               scenario, j, kld, ia, ib, ma - second_a, mb - second_b);
'''
    source = source.replace(anchor, detail + anchor, 1)
    import re
    source = re.sub(r'emit\("([^"]+)", compare\(', lambda m: m[0] + '"' + m[1] + '", ', source)
    anchor = '    if (!prefill_at(0)) die("prefill failed");\n    llama_memory_seq_add(mem, 0, -1, -1, d);'
    source = source.replace(anchor, '''    emit("control_offset_d", compare("control_offset_d", base, ref_d, n_vocab, a.n_probe), "");
    if (!prefill_at(0) || !probe_logits(&tst, 0)) die("repeat control failed");
    emit("control_repeat_0", compare("control_repeat_0", base, tst, n_vocab, a.n_probe), "");
''' + anchor, 1)
    anchor = '    // div: seq_div(G)'
    source = source.replace(anchor, '''    // Diagnostic controls, never used to retroactively qualify r1.
    // A query-only position gap is refused by llama_decode. Move the tail key
    // too, preserving consecutive probe positions; this is a different control.
    if (!prefill_at(0)) die("tail shift prefill failed");
    llama_memory_seq_add(mem, 0, a.n_prefix - 1, a.n_prefix, 64);
    if (!probe_logits(&tst, 0)) die("tail shift control failed");
    emit("negctl_tail_key_shift_64", compare("negctl_tail_key_shift_64", base, tst, n_vocab, a.n_probe), "");
    reset();
    if (!decode(ctx, probe, a.n_prefix, a.n_probe, n_vocab, &tst)) die("drop prefix failed");
    emit("negctl_drop_prefix", compare("negctl_drop_prefix", base, tst, n_vocab, a.n_probe), "");

''' + anchor, 1)
    return source


def instrument_calibration(source):
    """Opt-in prospective controls; default/r1 instrumentation stays unchanged."""
    source = instrument(source)
    for scenario, name in [('translate_x1', 'shift_d'), ('translate_x4', 'shift_4d'),
                           ('roundtrip', 'shift_0')]:
        anchor = next(line for line in source.splitlines()
                      if line.startswith('    emit("' + scenario + '",'))
        source = source.replace(anchor, anchor + '\n    const std::vector<float> ' + name + ' = tst;', 1)
    # Insert after historical measurements, so extra prefills cannot affect them.
    anchor = '    // div vs undivided'
    if source.count(anchor) != 1:
        raise ValueError('missing calibration insertion point')
    block = '    // Offset-matched calibration v1: diagnostic only, no acceptance gate.\n'
    for label, off, ref, shifted in [('0', '0', 'base', 'shift_0'),
                                     ('d', 'd', 'ref_d', 'shift_d'),
                                     ('4d', '4 * d', 'ref_off', 'shift_4d')]:
        block += '    {\n        std::vector<float> r1, r2;\n'
        for repeat in (1, 2):
            block += (f'        if (!prefill_at({off}) || !probe_logits(&r{repeat}, 0)) '
                      f'die("calibration {label} repeat {repeat} failed");\n')
        for pair, left, right in [('01', ref, 'r1'), ('02', ref, 'r2'), ('12', 'r1', 'r2'),
                                   ('shift1', 'r1', shifted), ('shift2', 'r2', shifted)]:
            name = f'cal_{label}_{pair}'
            block += f'        emit("{name}", compare("{name}", {left}, {right}, n_vocab, a.n_probe), "");\n'
        block += '    }\n'
    return source.replace(anchor, block + '\n' + anchor, 1)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--offset-calibration', action='store_true')
    args = parser.parse_args()
    transform = instrument_calibration if args.offset_calibration else instrument
    args.output.write_text(transform(args.source.read_text()))
