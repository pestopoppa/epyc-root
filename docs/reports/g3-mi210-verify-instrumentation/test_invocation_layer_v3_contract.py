"""Static patch contracts only; these do not prove compiled or runtime behavior."""
from pathlib import Path
import unittest

PATCH = Path(__file__).with_name("v10-invocation-layer-v3.patch")


def additions(patch):
    return "\n".join(line[1:] for line in patch.splitlines()
                     if line.startswith("+") and not line.startswith("+++"))


def require(text, *parts):
    for part in parts:
        if part not in text:
            raise AssertionError(f"missing contract: {part}")


def check_indices(s):
    require(s, 'slots.size() == 1', 'g3_drafts > 0 && !use_serial_speculative_verify(slot)',
            'slot.spec_i_batch.size() == g3_drafts + 1',
            'batch_view.n_tokens == (int32_t) slot.spec_i_batch.size()',
            'slot.spec_i_batch[i] == off + (int32_t) i',
            'for (const auto index : slots.front().spec_i_batch)',
            'g3_indices += std::to_string(index)', 'indices=%s correlation=host_scope',
            'g3_drafts, g3_indices.c_str()')


def check_scope(s):
    require(s, 'static thread_local uint64_t ggml_g3_trace_invocation_id = 0;',
            'invocation_id ? "host_scope" : "unknown"',
            'g3_previous = ggml_g3_trace_set_invocation(g3_id)',
            'if (g3_enabled) ggml_g3_trace_set_invocation(g3_previous);',
            'catch (...)', 'G3_TARGET_END_V3')
    ordered = ('g3_previous = ggml_g3_trace_set_invocation(g3_id)', 'G3_TARGET_BEGIN_V3',
               'ret = llama_decode(ctx_tgt, batch_view)', 'catch (...)',
               'if (g3_enabled) ggml_g3_trace_set_invocation(g3_previous);',
               'ggml_g3_trace_set_invocation(g3_previous);\n            std::fprintf',
               'G3_TARGET_END_V3')
    positions = [s.index(piece) for piece in ordered]
    if positions != sorted(positions) or len(set(positions)) != len(positions):
        raise AssertionError('scope does not bracket decode and restore on both exits')


def check_graph(s):
    require(s, 'std::getenv("GGML_G3_FATTN_TRACE")',
            "value && value[0] == '1' && value[1] == '\\0'",
            'if (ggml_g3_trace_direct_dispatch()) {\n        use_cuda_graph = false;\n        cuda_graph_update_required = false;',
            '!ggml_g3_trace_direct_dispatch() && ggml_cuda_graph_set_enabled(cuda_ctx, graph_key)')


def check_dispatch(s):
    require(s, 'ggml_format_name(cur, "g3_fattn_layer_%d", il)',
            'const char * name = ggml_get_name(dst)',
            'const char * prefix = "g3_fattn_layer_"', 'int layer = -1;',
            "end && *end == '\\0' && parsed >= 0 && parsed <= INT_MAX",
            'const auto selected = ggml_cuda_get_best_fattn_kernel(ggml_cuda_get_device(), dst)',
            'G3_FATTN_DISPATCH_V3 invocation=%llu correlation=%s device=%d kernel=%d layer=%d',
            'ctx.device, (int) selected, layer, (void *) dst', 'switch (selected)')
    if s.index('G3_FATTN_DISPATCH_V3') > s.index('switch (selected)'):
        raise AssertionError('dispatch record must precede selected switch')


class InvocationLayerContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = additions(PATCH.read_text())

    def test_contracts(self):
        for check in (check_indices, check_scope, check_graph, check_dispatch):
            with self.subTest(check=check.__name__):
                check(self.source)

    def test_negative_controls(self):
        mutations = (
            (check_indices, 'g3_indices += std::to_string(index)', 'g3_indices += "0"'),
            (check_indices, 'slot.spec_i_batch[i] == off + (int32_t) i', 'true'),
            (check_scope, 'static thread_local uint64_t', 'static uint64_t'),
            (check_scope, 'invocation_id ? "host_scope" : "unknown"', '"host_scope"'),
            (check_scope, 'if (g3_enabled) ggml_g3_trace_set_invocation(g3_previous);', ''),
            (check_graph, 'use_cuda_graph = false;\n        cuda_graph_update_required = false;', 'use_cuda_graph = true;'),
            (check_graph, '!ggml_g3_trace_direct_dispatch() && ggml_cuda_graph_set_enabled', 'ggml_cuda_graph_set_enabled'),
            (check_dispatch, 'ggml_format_name(cur, "g3_fattn_layer_%d", il)', 'ggml_set_name(cur, "unknown")'),
            (check_dispatch, 'int layer = -1;', 'int layer = 0;'),
            (check_dispatch, 'switch (selected)', 'switch (other)'),
        )
        for check, before, after in mutations:
            with self.subTest(check=check.__name__, mutation=before):
                self.assertIn(before, self.source)
                with self.assertRaises((AssertionError, ValueError)):
                    check(self.source.replace(before, after, 1))


if __name__ == '__main__':
    unittest.main()
