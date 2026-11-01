#include "chat.h"
#include "common.h"
#include "llama.h"
#include "nlohmann/json.hpp"

#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>

// Metadata-only approximation of frozen server /apply-template followed by
// /tokenize(add_special=true, parse_special=true). Model weights are not loaded.
int main(int argc, char ** argv) {
    if (argc != 3) {
        std::cerr << "usage: metadata_prompt_count MODEL.gguf TEMPLATE.jinja\n";
        return 2;
    }
    std::ifstream template_file(argv[2], std::ios::binary);
    if (!template_file) {
        throw std::runtime_error("cannot read pinned template");
    }
    const std::string source((std::istreambuf_iterator<char>(template_file)), std::istreambuf_iterator<char>());
    llama_backend_init();
    auto params = llama_model_default_params();
    params.vocab_only = true;
    llama_model * model = llama_model_load_from_file(argv[1], params);
    if (!model) {
        throw std::runtime_error("cannot load GGUF vocabulary metadata");
    }
    try {
        auto templates = common_chat_templates_init(model, source);
        const llama_vocab * vocab = llama_model_get_vocab(model);
        for (std::string line; std::getline(std::cin, line); ) {
            auto record = nlohmann::json::parse(line);
            common_chat_templates_inputs inputs;
            inputs.use_jinja = true;
            inputs.enable_thinking = false;
            inputs.chat_template_kwargs["enable_thinking"] = "false";
            common_chat_msg msg;
            msg.role = "user";
            msg.content = record.at("prompt").get<std::string>();
            inputs.messages.push_back(std::move(msg));
            auto rendered = common_chat_templates_apply(templates.get(), inputs).prompt;
            auto tokens = common_tokenize(vocab, rendered, true, true);
            nlohmann::json out = {
                {"id", record.at("id")},
                {"rendered", rendered},
                {"tokens", tokens},
                {"count", tokens.size()},
            };
            std::cout << out.dump() << '\n';
        }
    } catch (...) {
        llama_model_free(model);
        llama_backend_free();
        throw;
    }
    llama_model_free(model);
    llama_backend_free();
    return 0;
}
