import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout_witness as w

def snapshot(batch, layout, row_pos, used):
    lines=[f'KPF_ITEM4_BEGIN id={batch} off=0 rows=1 decode_prefix=0',
           f'KPF_ITEM4_ROW id={batch} row=0 owner=1 task=10 nseq=1 pos={row_pos} output=0 phase=prefill',
           f'KPF_LAYOUT_BEGIN id={layout} streams=1 swa=0 nseq=1 tokens=1',
           f'KPF_LAYOUT_STREAM id={layout} stream=0 size=8 used={used} head={used}']
    for i in range(used):
        lines.append(f'KPF_LAYOUT_CELL id={layout} stream=0 cell={i} pos={i} mask=2 owners=1')
    lines += [f'KPF_LAYOUT_END id={layout}',f'KPF_ITEM4_END id={batch} ret=0']
    return '\n'.join(lines)

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

if __name__=='__main__':unittest.main()
