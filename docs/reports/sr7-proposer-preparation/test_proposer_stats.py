import unittest
from proposer_stats import parse_proposer_stats


def line(name, generated, accepted, drafts=3, accepted_drafts=2, accepts=3):
    return (f'spec print_stats: statistics {name}: #calls(b,g,a) = 1 4 {accepts}, '
            f'#gen drafts = {drafts}, #acc drafts = {accepted_drafts}, '
            f'#gen tokens = {generated}, #acc tokens = {accepted}, #mean acc len = 1.50')


class ProposerStatsTest(unittest.TestCase):
    def test_weighted_mix_and_zero_proposer(self):
        text = '\n'.join((line('ngram-mod', 10, 8), line('draft-mtp', 30, 12)))
        result = parse_proposer_stats(text, ['ngram-mod', 'draft-mtp'], 40, 20)
        self.assertEqual(result['acceptance'], .5)
        self.assertEqual(result['proposers']['ngram-mod']['token_share'], .25)
        self.assertEqual(result['proposers']['draft-mtp']['acceptance'], .4)
        text = line('ngram-mod', 0, 0, 0, 0, 0) + '\n' + line('draft-mtp', 30, 12)
        self.assertIsNone(parse_proposer_stats(text, ['ngram-mod', 'draft-mtp'], 30, 12)['proposers']['ngram-mod']['acceptance'])

    def test_reject_missing_duplicate_malformed_and_mismatch(self):
        good = line('ngram-mod', 10, 8) + '\n' + line('draft-mtp', 30, 12)
        for text, generated, accepted in [(line('ngram-mod', 10, 8), 40, 20),
                (good + '\n' + line('ngram-mod', 10, 8), 40, 20),
                (good.replace('#acc tokens = 8', '#acc tokens = nope'), 40, 20),
                (good, 41, 20), (good, 40, 21),
                (line('ngram-mod', 10, 11) + '\n' + line('draft-mtp', 30, 12), 40, 23)]:
            with self.subTest(text=text, generated=generated, accepted=accepted):
                with self.assertRaises(ValueError):
                    parse_proposer_stats(text, ['ngram-mod', 'draft-mtp'], generated, accepted)


if __name__ == '__main__':
    unittest.main()
