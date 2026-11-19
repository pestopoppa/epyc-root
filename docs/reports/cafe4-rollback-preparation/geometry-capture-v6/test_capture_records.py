import unittest
from capture_records import CaptureError, parse_native_arms

def make_arm(mode):
    selected=0 if mode==0 else 1; faulted=1 if mode==2 else 0
    return (f'CAFE4_CAPTURE mode={mode} phase=begin\n'
      f'CAFE4_CAPTURE mode={mode} field=prompt count=2 tokens=10,11\n'
      f'CAFE4_CAPTURE mode={mode} field=boundary token=12\n'
      f'CAFE4_CAPTURE mode={mode} field=draft count=3 tokens=13,14,15\n'
      f'CAFE4_CAPTURE mode={mode} field=partial natural=3 accepted=1 width=3 keep=4 sampled=20\n'
      f'CAFE4_CAPTURE mode={mode} field=seq_rm target=1 draft=1 keep=4\n'
      f'CAFE4_CAPTURE mode={mode} field=replay token=20 pos=4 rc=0\n'
      f'CAFE4_CAPTURE mode={mode} phase=complete selected={selected} faulted={faulted}\n')

class CaptureTest(unittest.TestCase):
    def test_complete_and_fault_seal(self):
        raw=''.join(make_arm(i) for i in range(3)).encode(); arms=parse_native_arms(raw)
        self.assertEqual([a['arm'] for a in arms],['off','observe','fault'])
        self.assertEqual(arms[2]['faulted'],1);self.assertEqual(len(arms[2]['native_segment_sha256']),64)
        for changed in [raw.replace(b'faulted=1',b'faulted=0'),raw.replace(b'keep=4',b'keep=5',1),raw.replace(b'count=3 tokens=13',b'count=4 tokens=13'),raw[:-3],raw.replace(b'mode=2 field=replay',b'mode=1 field=replay')]:
            with self.subTest(changed=changed[-40:]):
                with self.assertRaises(CaptureError):parse_native_arms(changed)

if __name__=='__main__':unittest.main()
