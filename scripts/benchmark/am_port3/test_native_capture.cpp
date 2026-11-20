#include "native_capture.h"
#include "ggml-cpu.h"

#include <iostream>

static void check(bool ok, const char * message) {
    if (!ok) throw std::runtime_error(message);
}

int main(int argc, char ** argv) {
    try {
        check(argc >= 2 && argc <= 5,
              "usage: test_native_capture OUTPUT_PARENT [--head-mask] [--scheduler-copy] [--single-query]");
        int mask_heads = 1;
        bool scheduler_copy = false;
        int queries = 2;
        for (int i = 2; i < argc; ++i) {
            const std::string arg = argv[i];
            if (arg == "--head-mask") mask_heads = 4;
            else if (arg == "--scheduler-copy") scheduler_copy = true;
            else if (arg == "--single-query") queries = 1;
            else throw std::runtime_error("unknown test option");
        }
        const std::filesystem::path root = argv[1];
        const auto backend = ggml_backend_cpu_init();
        check(backend != nullptr, "CPU backend unavailable");
        ggml_backend_cpu_set_n_threads(backend, 1);
        const auto ctx = ggml_init({2*1024*1024, nullptr, true});
        check(ctx != nullptr, "ggml context unavailable");
        // Q storage is [width,heads,queries]; FA consumes its permuted view.
        auto * original_q = ggml_new_tensor_3d(ctx, GGML_TYPE_F32, 64, 4, queries);
        ggml_set_name(original_q, "Qcur-3");
        auto * q = ggml_permute(ctx, original_q, 0, 2, 1, 3);
        if (scheduler_copy) {
            // Match ggml_backend_sched_split_graph: a cross-backend input
            // copy has the original layout/name, but no op/src ancestry.
            auto * copy = ggml_dup_tensor(ctx, q);
            for (int d = 0; d < GGML_MAX_DIMS; ++d) copy->nb[d] = q->nb[d];
            q = copy;
            ggml_format_name(q, "CPU#Qcur-3 (permuted)#0");
            check(q->op == GGML_OP_NONE && !q->src[0], "copy unexpectedly kept ancestry");
        }
        // Copies must retain exact post-RoPE identity, not a guessed layer
        // from any tensor name ending in a number. Test the actual public
        // tensor metadata representation the scheduler creates.
        if (scheduler_copy) {
            for (const char * name : {"CPU#Qcur-3#0", "ROCm0#Qcur-3 (view) (permuted)#1",
                                     "CPU#Qcur-3 (reshaped) (cont) (transposed) (copy)#0"}) {
                ggml_set_name(q, name);
                check(am_capture::query_layer(q) == 3, "scheduler copy lost valid Q identity");
            }
            for (const char * name : {"CPU#Qcur_full-3#0", "CPU#Qcur_normed-3#0",
                                     "CPU#Qcur-3junk#0", "CPU#Qcur-3 (add)#0",
                                     "CPU#Qcur-3 (copy of Kcur-7)#0", "CPU#Qcur-#0",
                                     "CPU#Qcur-2147483648#0", "CPU#Qcur-3#",
                                     "CPU#Qcur-3#0x", "CPU#Qcur-3#0#1", "#Qcur-3#0",
                                     "Qcur-3 (permuted)", "Qcur--3"}) {
                ggml_set_name(q, name);
                check(am_capture::query_layer(q) == -1, "malformed copy/projection identity accepted");
            }
            ggml_set_name(q, "CPU#Qcur-3 (permuted)#0");
            q->op = GGML_OP_ADD;
            check(am_capture::query_layer(q) == -1, "copy grammar accepted on arithmetic node");
            q->op = GGML_OP_NONE;
        }
        auto * k = ggml_new_tensor_3d(ctx, GGML_TYPE_Q8_0, 64, 3, 2);
        auto * v = ggml_new_tensor_3d(ctx, GGML_TYPE_Q8_0, 64, 3, 2);
        auto * mask = ggml_new_tensor_3d(ctx, GGML_TYPE_F16, 3, 32, mask_heads);
        auto * output = ggml_flash_attn_ext(ctx, q, k, v, mask, 0.125f, 0., 0.);
        ggml_flash_attn_ext_set_prec(output, GGML_PREC_F32);
        for (auto * x : {scheduler_copy ? q : original_q, k, v, mask}) ggml_set_input(x);
        ggml_set_output(output);
        auto * graph = ggml_new_graph(ctx);
        ggml_build_forward_expand(graph, output);
        ggml_backend_t backends[] = {backend};
        auto sched = ggml_backend_sched_new(backends, nullptr, 1, 2048, false, false);
        check(ggml_backend_sched_alloc_graph(sched, graph), "graph allocation failed");

        std::vector<float> qdata(64*4*queries);
        for (size_t i = 0; i < qdata.size(); ++i) qdata[i] = float(int(i%13)-6)*0.1f;
        if (scheduler_copy) {
            for (int t = 0; t < queries; ++t) {
                for (int h = 0; h < 4; ++h) {
                    ggml_backend_tensor_set(q, qdata.data() + (t*4+h)*64,
                                            t*q->nb[1] + h*q->nb[2], 64*sizeof(float));
                }
            }
        } else {
            ggml_backend_tensor_set(original_q, qdata.data(), 0, qdata.size()*sizeof(float));
        }
        for (auto * x : {k, v}) {
            std::vector<float> data(64*3*2);
            for (size_t i = 0; i < data.size(); ++i) {
                data[i] = x == k ? float(int(i%17)-8)*0.1f : float(int(i%23)-11)*0.2f;
            }
            std::vector<uint8_t> packed(ggml_nbytes(x));
            const auto * traits = ggml_get_type_traits(GGML_TYPE_Q8_0);
            traits->from_float_ref(data.data(), packed.data(), data.size());
            ggml_backend_tensor_set(x, packed.data(), 0, packed.size());
        }
        std::vector<ggml_fp16_t> mask_data(3*32*mask_heads, ggml_fp32_to_fp16(-INFINITY));
        // First query attends rows 0,1; second sees all three. Other query rows
        // are padding and must survive capture as masked, not become zeros.
        for (int h = 0; h < mask_heads; ++h) {
            const int offset = h*3*32;
            mask_data[offset] = ggml_fp32_to_fp16(0.2f*h);
            mask_data[offset+1] = ggml_fp32_to_fp16(-0.3f*h);
            for (int i = 3; i < 3*queries; ++i) mask_data[offset+i] = ggml_fp32_to_fp16(0.1f*h*i);
        }
        ggml_backend_tensor_set(mask, mask_data.data(), 0, mask_data.size()*sizeof(ggml_fp16_t));

        am_capture::state s;
        ggml_backend_sched_set_eval_callback(sched, am_capture::callback, &s);
        check(!am_capture::callback(output, true, &s), "disabled callback requested capture");
        check(ggml_backend_sched_graph_compute(sched, graph) == GGML_STATUS_SUCCESS, "default evaluation failed");
        std::vector<float> before(ggml_nelements(output));
        ggml_backend_tensor_get(output, before.data(), 0, before.size()*sizeof(float));
        s.begin(root / "valid", {3});
        check(ggml_backend_sched_graph_compute(sched, graph) == GGML_STATUS_SUCCESS, "captured evaluation failed");
        s.finish();
        std::vector<float> after(before.size());
        ggml_backend_tensor_get(output, after.data(), 0, after.size()*sizeof(float));
        check(before == after, "callback changed native attention output");

        // A second ubatch must not silently replace the original cache snapshot.
        s.begin(root / "duplicate", {3});
        am_capture::callback(output, false, &s);
        am_capture::callback(output, false, &s);
        check(s.error.find("duplicate") != std::string::npos, "duplicate layer not refused");
        bool refused = false;
        try { s.finish(); } catch (const std::runtime_error &) { refused = true; }
        check(refused, "failed capture was completed");
        check(!std::filesystem::exists(root / "duplicate/COMPLETE.json"), "failure got completion marker");

        s.max_bytes = 64;
        s.begin(root / "budget", {3});
        am_capture::callback(output, false, &s);
        check(!s.error.empty() && s.seen.empty(), "budget not enforced before dumping");
        refused = false;
        try { s.finish(); } catch (const std::runtime_error &) { refused = true; }
        check(refused, "over-budget capture was completed");
        s.max_bytes = size_t(4) << 30;
        s.begin(root / "missing", {3, 7});
        am_capture::callback(output, false, &s);
        refused = false;
        try { s.finish(); } catch (const std::runtime_error &) { refused = true; }
        check(refused, "missing layer was completed");

        s.begin(root / "unknown", {7});
        am_capture::callback(output, true, &s);
        check(!s.error.empty(), "unexpected layer not refused");
        try { s.finish(); } catch (const std::runtime_error &) {}

        s.begin(root / "no-query", {3});
        auto * saved_q = output->src[0];
        output->src[0] = nullptr;
        am_capture::callback(output, true, &s);
        output->src[0] = saved_q;
        check(s.error.find("<null>") != std::string::npos, "missing Q diagnostic absent");
        refused = false;
        try { s.finish(); } catch (const std::runtime_error &) { refused = true; }
        check(refused && !std::filesystem::exists(root / "no-query/COMPLETE.json"),
              "missing Q got completion marker");

        ggml_backend_sched_free(sched);
        ggml_free(ctx);
        ggml_backend_free(backend);
        std::cout << "PASS native scheduler capture, quantized rows, disabled parity and failure guards\n";
        return 0;
    } catch (const std::exception & e) {
        std::cerr << "FAIL " << e.what() << '\n';
        return 1;
    }
}
