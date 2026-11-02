"""Source-contract checks for the unbuilt v10 correlation patch artifact."""
from pathlib import Path
import unittest

PATCH = Path(__file__).with_name('v10-invocation-correlation-v2.patch')


class InvocationPatchContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()

    def test_host_thread_scope_is_fail_closed(self):
        self.assertIn('static thread_local uint64_t ggml_g3_trace_invocation_id = 0;', self.patch)
        self.assertIn('invocation_id ? "host_scope" : "unknown"', self.patch)
        self.assertNotIn('static uint64_t ggml_g3_trace_invocation_id', self.patch)

    def test_scope_brackets_target_decode_and_restores_on_exception(self):
        start = self.patch.index('g3_previous = ggml_g3_trace_set_invocation(g3_id)')
        begin = self.patch.index('G3_TARGET_BEGIN_V2', start)
        decode = self.patch.index('ret = llama_decode(ctx_tgt, batch_view)', begin)
        restore = self.patch.index('ggml_g3_trace_set_invocation(g3_previous)', decode)
        end = self.patch.index('G3_TARGET_END_V2', restore)
        self.assertLess(start, begin)
        self.assertLess(begin, decode)
        self.assertLess(decode, restore)
        self.assertLess(restore, end)
        self.assertIn('catch (...)', self.patch)

    def test_candidate_label_requires_single_complete_parallel_view(self):
        for gate in ('slots.size() == 1', 'slot.can_speculate()',
                     '!use_serial_speculative_verify(slot)',
                     'slot.spec_i_batch.size() == g3_drafts + 1',
                     'batch_view.n_tokens == (int32_t) slot.spec_i_batch.size()',
                     'slot.spec_i_batch[i] == off + (int32_t) i'):
            self.assertIn(gate, self.patch)

    def test_backend_event_has_explicit_invocation_field(self):
        self.assertIn('G3_FATTN_DISPATCH_V2 invocation=%llu correlation=%s', self.patch)
        self.assertIn('ggml_g3_trace_get_invocation()', self.patch)


if __name__ == '__main__':
    unittest.main()
