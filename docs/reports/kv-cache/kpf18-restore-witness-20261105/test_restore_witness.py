import unittest
from restore_witness import attest

def line(task=19, slot=0, maxpos=1023, tokens=1024, past=1023):
    return f'12345.000 slot   pre_decode: id {slot:2d} | task {task} | restored context checkpoint (pos_min = 0, pos_max = {maxpos}, n_tokens = {tokens}, n_past = {past}, size = 1.000 MiB)\n'

class TestWitness(unittest.TestCase):
    def test_match(self):
        self.assertEqual(attest(line(), task_id=19, slot=0, n_tokens=1024)['task'], 19)
    def test_reject_absent_and_wrong_task(self):
        for log in ('', line(task=20), line(slot=1)):
            with self.subTest(log=log), self.assertRaises(ValueError):
                attest(log, task_id=19, slot=0, n_tokens=1024)
    def test_reject_bad_checkpoint_or_duplicate(self):
        for log in (line(maxpos=1022), line(tokens=1023), line(past=1025), line()+line()):
            with self.subTest(log=log), self.assertRaises(ValueError):
                attest(log, task_id=19, slot=0, n_tokens=1024)
    def test_require_explicit_binding(self):
        for task in (-1, True):
            with self.assertRaises(ValueError): attest(line(), task_id=task, slot=0, n_tokens=1024)

    def test_malformed_attributed_restore_cannot_hide(self):
        for broken in (line().replace('size = 1.000', 'size = BROKEN'),
                       line().replace('1.000 MiB', '1..0 MiB'),
                       line().replace('n_tokens = 1024', 'n_tokens = missing'),
                       line().replace(' MiB)', ' MiB'),
                       line().rstrip() + ' trailing garbage\n'):
            for raw in (broken, line() + broken, broken + line()):
                with self.subTest(raw=raw), self.assertRaises(ValueError):
                    attest(raw, task_id=19, slot=0, n_tokens=1024)

    def test_impossible_position_range(self):
        for minimum in (-1, 1024, 2048):
            with self.subTest(minimum=minimum), self.assertRaises(ValueError):
                attest(line().replace('pos_min = 0', f'pos_min = {minimum}'),
                       task_id=19, slot=0, n_tokens=1024)

    def test_foreign_malformed_restore_is_not_ours(self):
        foreign = line(task=20).replace('size = 1.000', 'size = BROKEN')
        self.assertEqual(attest(foreign + line(), task_id=19, slot=0,
                                n_tokens=1024)['tokens'], 1024)

    def test_valid_sliding_window_range(self):
        self.assertEqual(attest(line().replace('pos_min = 0', 'pos_min = 128'),
                                task_id=19, slot=0, n_tokens=1024)['min'], 128)

if __name__ == '__main__': unittest.main()
