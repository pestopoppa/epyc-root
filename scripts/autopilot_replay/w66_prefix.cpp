// Offline W66 prompt comparison using C22's actual chat API and the GGUF vocabulary.
#include "server-common.h"

#include <algorithm>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <fstream>

static json read_wire_body(const char *path) {
    std::ifstream file(path);
    if (!file) throw std::runtime_error("cannot open wire body");
    return json::parse(file);
}

int main(int argc, char **argv) try {
    if (argc != 4) {
        std::cerr << "usage: w66_prefix MODEL.gguf PREVIOUS.json CURRENT.json\n";
        return 2;
    }
    auto params = llama_model_default_params();
    params.vocab_only = true;
    params.n_gpu_layers = 0;
    std::unique_ptr<llama_model, decltype(&llama_model_free)> model(
        llama_model_load_from_file(argv[1], params), llama_model_free);
    if (!model) throw std::runtime_error("cannot load vocabulary");
    server_chat_params options{};
    options.use_jinja = true;
    options.prefill_assistant = true;
    options.reasoning_format = COMMON_REASONING_FORMAT_DEEPSEEK;
    options.tmpls = common_chat_templates_init(model.get(), "");

    const auto previous = read_wire_body(argv[2]);
    const auto current = read_wire_body(argv[3]);
    auto tokens = [&](json body) {
        std::vector<raw_buffer> media;
        auto parsed = oaicompat_chat_params_parse(body, options, media);
        return common_tokenize(llama_model_get_vocab(model.get()),
                               parsed.at("prompt").get<std::string>(), true, true);
    };
    auto compare = [&](const json &before, const json &after) {
        auto a = tokens(before);
        auto b = tokens(after);
        auto diff = std::mismatch(a.begin(), a.end(), b.begin(), b.end());
        return json{{"previous_prompt_tokens", a.size()}, {"current_prompt_tokens", b.size()},
                    {"common_leading_tokens", diff.first - a.begin()}};
    };
    const auto &a = previous.at("messages");
    const auto &b = current.at("messages");
    auto shared = std::mismatch(a.begin(), a.end(), b.begin(), b.end());
    json result{{"previous_messages", a.size()}, {"current_messages", b.size()},
                {"common_leading_messages", shared.first - a.begin()}, {"recorded", compare(previous, current)}};
    if (b.size() > a.size() && b.back().at("role") == "user") {
        auto control = current;
        control.at("messages").erase(control.at("messages").end() - 1);
        result["omit_appended_user_for_diagnosis"] = compare(previous, control);
    }
    auto old_stable = previous, new_stable = current;
    for (auto *body : {&old_stable, &new_stable})
        (*body)["chat_template_kwargs"]["preserve_thinking"] = true;
    result["preserve_thinking_on_both_for_diagnosis"] = compare(old_stable, new_stable);
    std::cout << result.dump(2) << '\n';
    return 0;
} catch (const std::exception &ex) {
    std::cerr << ex.what() << '\n';
    return 1;
}
