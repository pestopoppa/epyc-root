#include "server-common.h"

#include <iostream>
#include <memory>
#include <stdexcept>

int main(int argc, char **argv) try {
    if (argc != 2) {
        std::cerr << "usage: native-prefix-ids MODEL.gguf < inputs.json\n";
        return 2;
    }

    auto model_options = llama_model_default_params();
    model_options.vocab_only = true;
    model_options.n_gpu_layers = 0;
    std::unique_ptr<llama_model, decltype(&llama_model_free)> model(
        llama_model_load_from_file(argv[1], model_options), llama_model_free);
    if (!model) {
        throw std::runtime_error("could not load the C22 model vocabulary");
    }

    server_chat_params chat_options{};
    chat_options.use_jinja = true;
    chat_options.prefill_assistant = true;
    chat_options.reasoning_format = COMMON_REASONING_FORMAT_DEEPSEEK;
    chat_options.tmpls = common_chat_templates_init(model.get(), "");
    chat_options.enable_thinking = common_chat_templates_support_enable_thinking(chat_options.tmpls.get());
    const auto *vocab = llama_model_get_vocab(model.get());
    json inputs = json::parse(std::cin);
    json results = json::array();

    for (auto &entry : inputs) {
        std::vector<raw_buffer> files;
        auto parsed = oaicompat_chat_params_parse(entry.at("body"), chat_options, files);
        if (!files.empty()) {
            throw std::runtime_error("the C22 W66 runner expects text-only chat requests");
        }
        const auto prompt = parsed.at("prompt").get<std::string>();
        const auto spans = chat_input_spans_from_json(parsed);
        auto plain = tokenize_mixed(vocab, parsed.at("prompt"), true, true);
        auto native = spans.empty() ? plain : tokenize_chat_prompt(vocab, nullptr, prompt, spans, files).get_text_tokens();
        const auto expected_count = entry.at("expected_total").get<size_t>();
        const auto prefix_count = entry.at("depth").get<size_t>();
        if (native.size() != expected_count || prefix_count >= native.size()) {
            throw std::runtime_error("prompt/token-depth disagreement for " + entry.at("label").get<std::string>()
                                     + ": got " + std::to_string(native.size()) + " tokens");
        }
        const auto control_spellings = find_control_spellings_in_spans(vocab, prompt, spans);
        results.push_back({
            {"label", entry.at("label")},
            {"chat_input_spans", spans.size()},
            {"control_spellings_in_input", control_spellings.size()},
            {"plain_matches_native_ids", plain == native},
            {"prompt_bytes", prompt.size()},
            {"prompt_ids", native},
            {"prefix_ids", llama_tokens(native.begin(), native.begin() + prefix_count)},
        });
    }
    std::cout << results.dump() << '\n';
    return 0;
} catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
}
