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
    if (!prefill_at(0) || !probe_logits(&tst, 64)) die("wrong probe control failed");
    emit("negctl_probe_offset_64", compare("negctl_probe_offset_64", base, tst, n_vocab, a.n_probe), "");
    reset();
    if (!decode(ctx, probe, a.n_prefix, a.n_probe, n_vocab, &tst)) die("drop prefix failed");
    emit("negctl_drop_prefix", compare("negctl_drop_prefix", base, tst, n_vocab, a.n_probe), "");

''' + anchor, 1)
    return source


if __name__ == '__main__':
    import sys
    Path(sys.argv[2]).write_text(instrument(Path(sys.argv[1]).read_text()))
