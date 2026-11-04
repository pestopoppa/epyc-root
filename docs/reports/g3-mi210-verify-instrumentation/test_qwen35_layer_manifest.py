import unittest
from qwen35_layer_manifest import derive_layers


def names(ids):
    return [f'blk.{i}.{n}.weight' for i in ids for n in ('attn_q', 'attn_k', 'attn_v', 'attn_output')]


class LayerManifestTest(unittest.TestCase):
    def test_interval_and_mtp_separate(self):
        ids = list(range(3, 40, 4))
        m = derive_layers({'general.architecture': 'qwen35moe', 'qwen35moe.block_count': 41,
                           'qwen35moe.nextn_predict_layers': 1, 'qwen35moe.full_attention_interval': 4}, names(ids + [40]))
        self.assertEqual(m['verify_attention_layer_ids'], ids)
        self.assertEqual(m['mtp_attention_layer_ids'], [40])

    def test_array_overrides_interval(self):
        m = derive_layers({'general.architecture': 'qwen35moe', 'qwen35moe.block_count': 4,
                           'qwen35moe.nextn_predict_layers': 1,
                           'qwen35moe.attention.recurrent_layers': [True, False, True, False]}, names([1, 3]))
        self.assertEqual(m['verify_attention_layer_ids'], [1])

    def test_bad_metadata_or_missing_weights_fail(self):
        base = {'general.architecture': 'qwen35moe', 'qwen35moe.block_count': 5, 'qwen35moe.nextn_predict_layers': 1}
        for changes in ({'qwen35moe.nextn_predict_layers': 2}, {'qwen35moe.full_attention_interval': 0},
                        {'qwen35moe.attention.recurrent_layers': [True]}, {'general.architecture': 'other'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                derive_layers(dict(base, **changes), names([3, 4]))
        with self.assertRaises(ValueError):
            derive_layers(base, names([3]))
