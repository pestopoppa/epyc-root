import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout_witness as w
import layout_witness_conservative as c

def snapshot(batch, layout, row_pos, used):
    lines=[f'KPF_ITEM4_BEGIN id={batch} off=0 rows=1 decode_prefix=0',
           f'KPF_ITEM4_ROW id={batch} row=0 owner=1 task=10 nseq=1 pos={row_pos} output=0 phase=prefill',
           f'KPF_LAYOUT_BEGIN id={layout} streams=1 swa=0 nseq=1 tokens=1',
           f'KPF_LAYOUT_STREAM id={layout} stream=0 size=8 used={used} head={used}']
    for i in range(used):
        lines.append(f'KPF_LAYOUT_CELL id={layout} stream=0 cell={i} pos={i} mask=2 owners=1')
    lines += [f'KPF_LAYOUT_END id={layout}',f'KPF_ITEM4_END id={batch} ret=0']
    return '\n'.join(lines)

def ambiguous_multi_ubatch_trace():
    # Source semantics: item4 describes the whole llama_decode server batch;
    # the two layout calls are successive ubatches. The target row is first,
    # but the trace has no row-range key joining either layout ID to that row.
    lines=['KPF_ITEM4_BEGIN id=7 off=0 rows=2 decode_prefix=0',
           'KPF_ITEM4_ROW id=7 row=0 owner=1 task=10 nseq=1 pos=2 output=0 phase=prefill',
           'KPF_ITEM4_ROW id=7 row=1 owner=0 task=11 nseq=1 pos=40 output=0 phase=prefill']
    for layout, mask in ((20,1),(21,2)):
        lines += [f'KPF_LAYOUT_BEGIN id={layout} streams=1 swa=0 nseq=1 tokens=1',
                  f'KPF_LAYOUT_STREAM id={layout} stream=0 size=8 used=2 head=2',
                  f'KPF_LAYOUT_CELL id={layout} stream=0 cell=0 pos=0 mask={mask} owners=1',
                  f'KPF_LAYOUT_CELL id={layout} stream=0 cell=1 pos=1 mask={mask} owners=1',
                  f'KPF_LAYOUT_END id={layout}']
    lines.append('KPF_ITEM4_END id=7 ret=0')
    return ('\n'.join(lines)+'\n').encode()

class PrefixBoundaryTests(unittest.TestCase):
    def test_later_snapshot_containing_same_prefix_is_excluded(self):
        raw=(snapshot(1,2,2,2)+'\n'+snapshot(3,4,3,3)).encode()
        got=w.witness(raw,task=10,slot=1,prefix=2)
        self.assertEqual(got['batch'],1)
        self.assertEqual(got['layout'],2)
        self.assertEqual(got['head'],2)
        self.assertEqual(got['mapping'],[(0,0),(1,1)])

    def test_duplicate_boundary_snapshots_remain_invalid(self):
        raw=(snapshot(1,2,2,2)+'\n'+snapshot(3,4,2,2)).encode()
        with self.assertRaisesRegex(w.Invalid,'expected exactly one bound prefix snapshot'):
            w.witness(raw,task=10,slot=1,prefix=2)

    def test_current_candidate_can_bind_non_target_ubatch_layout(self):
        raw=ambiguous_multi_ubatch_trace()
        got=w.witness(raw,task=10,slot=1,prefix=2)
        self.assertEqual((got['batch'],got['layout']),(7,21))

    def test_conservative_candidate_rejects_multilayout_target_batch_first(self):
        raw=ambiguous_multi_ubatch_trace()
        with self.assertRaisesRegex(c.Invalid,'ambiguous multi-layout target batch'):
            c.witness(raw,task=10,slot=1,prefix=2)

    def test_conservative_candidate_keeps_single_layout_boundary(self):
        raw=snapshot(1,2,2,2).encode()
        got=c.witness(raw,task=10,slot=1,prefix=2)
        self.assertEqual((got['batch'],got['layout']),(1,2))

if __name__=='__main__':unittest.main()
