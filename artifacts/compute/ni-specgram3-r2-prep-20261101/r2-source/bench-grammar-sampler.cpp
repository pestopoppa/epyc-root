// SPEC-GRAM.1 part (1): grammar cost microbenchmark (EXPERIMENTAL measurement tool; built with the tests, never installed).
//
// Times, on a vocab-only model and SYNTHETIC logits (no weights, no llama_context, no decode):
//   apply_ms   one llama_sampler_apply(grammar) over the FULL vocabulary at the current grammar state; this is the thin wrapper around
//              llama_grammar_apply_impl, the call SPEC-GRAM.1 names
//   step_ms    one full sampler step, mirroring common_sampler_sample() + common_sampler_accept() (common/sampling.cpp:553, :455):
//                set_logits (fill n_vocab llama_token_data) -> chain (top-k 40, top-p 0.95, min-p 0.05, temp 0.8, dist)
//                -> grammar rejection check on the one sampled token -> [invalid: refill, grammar over the full vocab, chain again]
//                -> grammar accept + chain accept
//   batch_ms   verify batch of B=5 positions: clone(grammar)+clone(chain) (the server snapshots the sampler before a verify batch,
//              server-context.cpp smpl_save = common_sampler_clone) + 5 steps + free of the snapshot
//   a baseline with NO grammar (same chain, same logits) so delta = grammar cost.
// The token stream is SCRIPTED (text tokenized by the vocab; every token is checked against the grammar before it is accepted), so the grammar
// walks real states (thought text, tool-name alternation, quoted strings; JSON object states for the schema) instead of random garbage.
// Profiles: "peaked" = the scripted token carries +15 logits (a model that follows the format: the unconstrained sample is valid, the cheap
// check passes; this is the production-representative path and feeds the predeclared rule); "random" = no boost (the unconstrained sample is
// almost never valid: every step takes the full-vocab slow path; upper bound).
// Output: one JSON object per config appended to --out (JSONL; configs already present are skipped, so a cut run resumes).
//
// SPEC-GRAM.2 window part (2026-10-22): profile "real" (needs --logits-model FULL_GGUF): the logits at every scripted position come from the
// real model, teacher-forced through a chat-formatted prompt (one llama_decode per script, logits for every position, cached before timing).
// The timed sampler step is unchanged; slow_path_frac is then the REAL grammar rejection rate and reject_resample_ms the extra cost of a
// rejected step (slow-step mean minus fast-step mean). --temp sets the chain temperature (default 0.8 = the SPEC-GRAM.1 chain).
// Usage: bench-grammar-sampler --model GGUF --label NAME --grammar-file F.gbnf --schema-file S.json --step-ms X [--reps 30] [--out F.jsonl]
//        [--seed 1] [--max-seconds 900] [--kinds toolcall-eager,toolcall-lazy,schema-eager] [--profiles peaked,random] [--batches 1,5]
//        [--logits-model FULL_GGUF --threads 24 --temp 0.8]   (adds profile "real")
#include "llama.h"
#include "sampling.h"
#include "json-schema-to-grammar.h"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <unistd.h>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
#include <random>
#include <set>
#include <sstream>
#include <string>
#include <vector>

static bool use_llg = false; static bool llg_requested = false;
static std::string llg_tool, llg_schema, original_tool;
using clk = std::chrono::steady_clock;
using json = nlohmann::ordered_json;

static double ms_since(clk::time_point t0) {
    return std::chrono::duration<double, std::milli>(clk::now() - t0).count();
}

struct bench_args {
    std::string greedy_out; int greedy_cap=256;
    int max_scripts = 0; bool paired = false;
    std::string model;
    std::string label = "model";
    std::string grammar_file;
    std::string schema_file;
    std::string out = "bench-grammar-sampler.jsonl";
    std::string kinds = "toolcall-eager,toolcall-lazy,schema-eager";
    std::string profiles = "peaked,random";
    std::string batches = "1,5";
    double step_ms = 0.0;       // decode step of the model on its serving device (ms/token), for the share; 0 = report absolute ms only
    int    reps = 30;           // passes over the script set per config (2 warm-up passes are extra and dropped)
    int    seed = 1;
    double max_seconds = 900.0; // do not start a new config after this much wall time
    std::string logits_model;   // SPEC-GRAM.2: full model whose real logits drive profile "real" (empty = synthetic profiles only)
    int    threads = 8;
    float  temp = 0.8f;
};

static std::string read_file(const std::string & path) {
    std::ifstream f(path);
    if (!f) {
        fprintf(stderr, "cannot read %s\n", path.c_str());
        exit(2);
    }
    std::stringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

static std::vector<std::string> split(const std::string & s, char sep) {
    std::vector<std::string> out;
    std::string cur;
    for (char c : s) {
        if (c == sep) { if (!cur.empty()) { out.push_back(cur); } cur.clear(); } else { cur.push_back(c); }
    }
    if (!cur.empty()) { out.push_back(cur); }
    return out;
}

static std::vector<llama_token> tokenize(const llama_vocab * vocab, const std::string & text) {
    int32_t n = -llama_tokenize(vocab, text.c_str(), (int32_t) text.size(), nullptr, 0, false, false);
    if (n <= 0) {
        return {};
    }
    std::vector<llama_token> toks((size_t) n);
    n = llama_tokenize(vocab, text.c_str(), (int32_t) text.size(), toks.data(), (int32_t) toks.size(), false, false);
    if (n < 0) {
        return {};
    }
    toks.resize((size_t) n);
    return toks;
}

// ---------------------------------------------------------------------------------------------------------------------------------
// the sampler under test

static llama_sampler * make_chain(uint32_t seed, float temp) {
    llama_sampler_chain_params cp = llama_sampler_chain_default_params();
    cp.no_perf = true;
    llama_sampler * chain = llama_sampler_chain_init(cp);
    llama_sampler_chain_add(chain, llama_sampler_init_top_k(40));
    llama_sampler_chain_add(chain, llama_sampler_init_top_p(0.95f, 1));
    llama_sampler_chain_add(chain, llama_sampler_init_min_p(0.05f, 1));
    llama_sampler_chain_add(chain, llama_sampler_init_temp(temp));
    llama_sampler_chain_add(chain, llama_sampler_init_dist(seed));
    return chain;
}

static llama_sampler * make_grammar(const llama_vocab * vocab, const std::string & gbnf, const char * root, bool lazy) {
    if (use_llg && !lazy) {
        return llama_sampler_init_llg(vocab, "lark", (gbnf==original_tool ? llg_tool : llg_schema).c_str());
    }
    if (!lazy) {
        return llama_sampler_init_grammar(vocab, gbnf.c_str(), root);
    }
    // lazy: inactive until the generated text matches; fed from the first match group on (the tool-call rule starts with TOOL(")
    const char * patterns[] = { "[\\s\\S]*?(TOOL\\(\")" };
    return llama_sampler_init_grammar_lazy_patterns(vocab, gbnf.c_str(), root, patterns, 1, nullptr, 0);
}

struct step_ctx {
    int32_t n_vocab = 0;
    std::vector<std::vector<float>> pool;   // precomputed synthetic logits, rotated (generating 150k normals per step would dominate the timing)
    std::vector<llama_token_data> cur;
    size_t pool_i = 0;
    const float * real = nullptr;           // profile "real": the model's logits at the current scripted position (no boost)
};

static void fill_logits(step_ctx & c, llama_token target, bool peaked) {
    // = common_sampler::set_logits: one pass writing n_vocab llama_token_data
    if (c.real) {
        for (int32_t i = 0; i < c.n_vocab; ++i) {
            c.cur[(size_t) i] = { i, c.real[i], 0.0f };
        }
        return;
    }
    const std::vector<float> & lg = c.pool[c.pool_i % c.pool.size()];
    for (int32_t i = 0; i < c.n_vocab; ++i) {
        c.cur[(size_t) i] = { i, lg[(size_t) i], 0.0f };
    }
    if (peaked) {
        c.cur[(size_t) target].logit += 15.0f;
    }
}

struct step_result {
    double step_ms = 0.0;
    double accept_ms = 0.0;
    bool   slow = false;
};

// one sampler step as the server runs it; the ACCEPTED token is the scripted one (the walk stays on real grammar states)
static step_result do_step(step_ctx & c, llama_sampler * grmr, llama_sampler * chain, llama_token target, bool peaked) {
    step_result r;
    const auto t0 = clk::now();

    fill_logits(c, target, peaked);
    llama_token_data_array cur_p = { c.cur.data(), c.cur.size(), -1, false };
    if (grmr && use_llg) { llama_sampler_apply(grmr, &cur_p); }
    llama_sampler_apply(chain, &cur_p);
    llama_token id = cur_p.data[cur_p.selected].id;

    if (grmr && !use_llg) {
        llama_token_data       one   = { id, 1.0f, 0.0f };
        llama_token_data_array one_p = { &one, 1, -1, false };
        llama_sampler_apply(grmr, &one_p);
        if (one.logit == -INFINITY) {        // grammar-based rejection sampling: resample, grammar first
            r.slow = true;
            fill_logits(c, target, peaked);
            cur_p = { c.cur.data(), c.cur.size(), -1, false };
            llama_sampler_apply(grmr, &cur_p);
            llama_sampler_apply(chain, &cur_p);
            id = cur_p.data[cur_p.selected].id;
        }
    }
    (void) id;

    const auto ta = clk::now();
    if (grmr) {
        llama_sampler_accept(grmr, target);
    }
    llama_sampler_accept(chain, target);
    r.accept_ms = ms_since(ta);

    r.step_ms = ms_since(t0);
    c.pool_i++;
    return r;
}

// is the scripted token acceptable to the grammar right now? (untimed; accepting an invalid token would abort the grammar)
static bool script_token_valid(llama_sampler * grmr, llama_token t) {
    if (!grmr) {
        return true;
    }
    llama_sampler * probe = use_llg ? llama_sampler_clone(grmr) : grmr;
    llama_token_data       one   = { t, 1.0f, 0.0f };
    llama_token_data_array one_p = { &one, 1, -1, false };
    llama_sampler_apply(probe, &one_p);
    if (use_llg) { llama_sampler_free(probe); }
    return one.logit != -INFINITY;
}

static double percentile(std::vector<double> v, double p) {
    if (v.empty()) { return 0.0; }
    std::sort(v.begin(), v.end());
    const double k = p * (double) (v.size() - 1);
    const size_t lo = (size_t) std::floor(k), hi = (size_t) std::ceil(k);
    return v[lo] + (v[hi] - v[lo]) * (k - (double) lo);
}
static double mean(const std::vector<double> & v) {
    double s = 0.0;
    for (double x : v) { s += x; }
    return v.empty() ? 0.0 : s / (double) v.size();
}

struct config_stats {
    std::vector<double> unit_ms;      // per step (B=1) or per verify batch (B>1)
    std::vector<double> apply_ms;     // full-vocab grammar apply at the state before each step (grammar runs only)
    std::vector<double> accept_ms;
    std::vector<double> clone_ms;     // B>1: snapshot + free per batch
    std::vector<double> slow_ms, fast_ms;   // per-step time split by the grammar rejection outcome
    long n_steps = 0, n_slow = 0, n_script_invalid = 0, n_passes_aborted = 0;
};

// walk the scripted token streams through grammar+chain (grmr may be null = baseline)
static config_stats run_config(step_ctx & c, const llama_vocab * vocab, const std::string & gbnf, const char * root, bool lazy, bool with_grammar,
                               const std::vector<std::vector<llama_token>> & scripts, bool peaked, int batch, int reps, uint32_t seed,
                               float temp, const std::vector<std::vector<std::vector<float>>> * real) {
    config_stats st;
    llama_sampler * grmr  = with_grammar ? make_grammar(vocab, gbnf, root, lazy) : nullptr;
    if (with_grammar && !grmr) {
        fprintf(stderr, "grammar failed to parse\n");
        exit(3);
    }
    llama_sampler * chain = make_chain(seed, temp);

    const int warmup = 2;
    for (int pass = 0; pass < reps + warmup; ++pass) {
        const bool record = pass >= warmup;
        for (size_t si = 0; si < scripts.size(); ++si) {
            const auto & script = scripts[si];
            if (grmr) { llama_sampler_reset(grmr); }
            llama_sampler_reset(chain);
            size_t i = 0;
            bool aborted = false;
            while (i < script.size() && !aborted) {
                const size_t nb = std::min((size_t) batch, script.size() - i);
                llama_sampler * g2 = nullptr;
                llama_sampler * c2 = nullptr;
                double clone_ms = 0.0, batch_ms = 0.0;
                if (batch > 1) {
                    const auto tc = clk::now();                // verify-batch snapshot: smpl_save = clone(slot.smpl)
                    g2 = grmr ? llama_sampler_clone(grmr) : nullptr;
                    c2 = llama_sampler_clone(chain);
                    clone_ms = ms_since(tc);
                }
                for (size_t k = 0; k < nb; ++k) {
                    const llama_token t = script[i + k];
                    c.real = real ? (*real)[si][i + k].data() : nullptr;
                    if (!script_token_valid(grmr, t)) {
                        if (record) { st.n_script_invalid++; st.n_passes_aborted++; }
                        aborted = true;
                        break;
                    }
                    if (grmr && record) {                      // full-vocab grammar apply at this state (llama_grammar_apply_impl)
                        fill_logits(c, t, peaked);
                        llama_token_data_array full = { c.cur.data(), c.cur.size(), -1, false };
                        const auto ta = clk::now();
                        llama_sampler * probe = use_llg ? llama_sampler_clone(grmr) : grmr;
                        llama_sampler_apply(probe, &full);
                        if (use_llg) { llama_sampler_free(probe); }
                        st.apply_ms.push_back(ms_since(ta));
                    }
                    const step_result r = do_step(c, grmr, chain, t, peaked);
                    batch_ms += r.step_ms;
                    if (record) {
                        st.n_steps++;
                        if (r.slow) { st.n_slow++; st.slow_ms.push_back(r.step_ms); } else { st.fast_ms.push_back(r.step_ms); }
                        st.accept_ms.push_back(r.accept_ms);
                        if (batch == 1) { st.unit_ms.push_back(r.step_ms); }
                    }
                }
                if (batch > 1) {
                    const auto tf = clk::now();
                    if (g2) { llama_sampler_free(g2); }
                    llama_sampler_free(c2);
                    clone_ms += ms_since(tf);
                    if (record) {
                        st.clone_ms.push_back(clone_ms);
                        st.unit_ms.push_back(batch_ms + clone_ms);
                    }
                }
                i += nb;
            }
        }
    }
    c.real = nullptr;
    if (grmr) { llama_sampler_free(grmr); }
    llama_sampler_free(chain);
    return st;
}

// ---------------------------------------------------------------------------------------------------------------------------------

static void quiet_log(enum ggml_log_level, const char *, void *) {}

int main(int argc, char ** argv) {
    bench_args a;
    for (int i = 1; i < argc; ++i) {
        const std::string k = argv[i];
        auto next = [&]() -> std::string {
            if (i + 1 >= argc) { fprintf(stderr, "missing value for %s\n", k.c_str()); exit(2); }
            return argv[++i];
        };
        if (k == "--greedy-out") { a.greedy_out=next(); }
        else if (k == "--greedy-cap") { a.greedy_cap=atoi(next().c_str()); }
        else if (k == "--max-scripts") { a.max_scripts=atoi(next().c_str()); }
        else if (k == "--paired") { a.paired=true; }
        else if (k == "--llguidance-file") { llg_requested=true; use_llg=true; llg_tool=read_file(next()); }
        else if (k == "--model")        { a.model = next(); }
        else if (k == "--label")        { a.label = next(); }
        else if (k == "--grammar-file") { a.grammar_file = next(); }
        else if (k == "--schema-file")  { a.schema_file = next(); }
        else if (k == "--out")          { a.out = next(); }
        else if (k == "--kinds")        { a.kinds = next(); }
        else if (k == "--profiles")     { a.profiles = next(); }
        else if (k == "--batches")      { a.batches = next(); }
        else if (k == "--step-ms")      { a.step_ms = atof(next().c_str()); }
        else if (k == "--reps")         { a.reps = atoi(next().c_str()); }
        else if (k == "--seed")         { a.seed = atoi(next().c_str()); }
        else if (k == "--max-seconds")  { a.max_seconds = atof(next().c_str()); }
        else if (k == "--logits-model") { a.logits_model = next(); }
        else if (k == "--threads")      { a.threads = atoi(next().c_str()); }
        else if (k == "--temp")         { a.temp = (float) atof(next().c_str()); }
        else { fprintf(stderr, "unknown arg %s\n", k.c_str()); return 2; }
    }
    if (a.model.empty() || a.grammar_file.empty()) {
        fprintf(stderr, "usage: %s --model GGUF --grammar-file F.gbnf [--schema-file S.json] [--label L] [--step-ms X] [--reps N] [--out F.jsonl]\n", argv[0]);
        return 2;
    }

    // configs already done (resume)
    std::set<std::string> done;
    {
        std::ifstream f(a.out);
        std::string line;
        while (std::getline(f, line)) {
            if (line.empty()) { continue; }
            try {
                const json j = json::parse(line);
                done.insert(j.value("key", ""));
            } catch (...) {}
        }
    }

    llama_backend_init();
    llama_log_set(quiet_log, nullptr);
    llama_model_params mp = llama_model_default_params();
    const bool want_real = !a.logits_model.empty();
    mp.vocab_only = !want_real; // synthetic profiles: metadata + vocabulary only, no weights are read or mapped
    mp.use_mmap   = want_real;  // real profile: the weights are mapped read-only (page cache), never copied
    llama_model * model = llama_model_load_from_file((want_real ? a.logits_model : a.model).c_str(), mp);
    if (!model) {
        fprintf(stderr, "failed to load vocab from %s\n", a.model.c_str());
        return 3;
    }
    const llama_vocab * vocab = llama_model_get_vocab(model);
    step_ctx c;
    c.n_vocab = llama_vocab_n_tokens(vocab);
    c.cur.resize((size_t) c.n_vocab);
    {
        std::mt19937 rng((uint32_t) a.seed);
        std::normal_distribution<float> nd(0.0f, 2.0f);
        c.pool.resize(8);
        for (auto & v : c.pool) {
            v.resize((size_t) c.n_vocab);
            for (auto & x : v) { x = nd(rng); }
        }
    }
    printf("vocab %s: n_vocab=%d (%s)\n", a.label.c_str(), c.n_vocab, want_real ? "full load: real logits" : "vocab-only load");

    const std::string gbnf_tool = read_file(a.grammar_file); original_tool=gbnf_tool;
    std::string gbnf_schema;
    if (!a.schema_file.empty()) {
        llg_schema = "%llguidance {}\nstart: %json " + read_file(a.schema_file);
        gbnf_schema = json_schema_to_grammar(json::parse(read_file(a.schema_file)));
    }

    const std::vector<std::string> tool_scripts = {
        "# read the page\nTOOL(\"http_get\", url=\"https://example.org/a\", timeout=30)\n",
        "# the answer\nFINAL(\"42\")\n",
        "# compute it\nTOOL(\"calculate\", expr=\"3*7+2\")\n",
        "# just code\nprint(1)\n",
    };
    const std::string lazy_free = "Sure, I will check that for you first. Let me think about the options for a moment. ";
    const std::vector<std::string> lazy_scripts = {
        lazy_free + "TOOL(\"http_get\", url=\"https://example.org/a\", timeout=30)\n",
        lazy_free + "TOOL(\"calculate\", expr=\"3*7+2\")\n",
    };
    const std::vector<std::string> schema_scripts = {
        "{\"name\": \"http_get\", \"arguments\": {\"url\": \"https://example.org/a\", \"timeout\": 30}}",
        "{\"name\": \"calculate\", \"arguments\": {}}",
    };

    // ---- SPEC-GRAM.2: real logits per scripted position (teacher-forced, chat-formatted, Qwen chatml with thinking disabled)
    const std::string sys_tool = "You are an agent. Answer with ONE line in exactly one of these forms: TOOL(\"name\", key=value, ...) to call a tool "
                                 "(tools: http_get(url, timeout), calculate(expr)); FINAL(\"answer\") to give the final answer; or plain Python code. "
                                 "You may put one '# comment' line first.";
    const std::string sys_lazy = "You are a helpful agent. Briefly say what you will do, then call a tool in the form TOOL(\"name\", key=value, ...) "
                                 "(tools: http_get(url, timeout), calculate(expr)).";
    const std::string sys_schema = "You are an agent. Reply with a single JSON object {\"name\": <tool>, \"arguments\": {...}} and nothing else. "
                                   "Tools: http_get(url, timeout), calculate(expr).";
    const std::vector<std::string> tool_users   = { "Fetch https://example.org/a with a 30 second timeout.", "What is six times seven? Give the final answer.",
                                                    "Compute 3*7+2 with the calculator.", "Write code that prints 1." };
    const std::vector<std::string> lazy_users   = { "Can you fetch https://example.org/a for me (30 s timeout)?", "Can you work out 3*7+2?" };
    const std::vector<std::string> schema_users = { "Fetch https://example.org/a with a 30 second timeout.", "Call the calculator with no arguments." };
    auto chat_prefix = [](const std::string & sys, const std::string & user) {
        return "<|im_start|>system\n" + sys + "<|im_end|>\n<|im_start|>user\n" + user + "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n";
    };
    std::map<std::string, std::vector<std::vector<std::vector<float>>>> real_logits;   // kind -> script -> position -> n_vocab logits
    if (!a.greedy_out.empty()) {
        if (!want_real) { fprintf(stderr,"greedy oracle requires full --logits-model\n"); return 3; }
        llama_context_params cp=llama_context_default_params(); cp.n_ctx=4096;cp.n_batch=4096;cp.n_ubatch=512;
        cp.n_threads=a.threads;cp.n_threads_batch=a.threads;cp.no_perf=true;
        llama_context *ctx=llama_init_from_model(model,cp); if(!ctx)return 3;
        std::set<std::string> greedy_done;
        {std::ifstream prior(a.greedy_out);std::string line;while(std::getline(prior,line)){try{auto j=json::parse(line);greedy_done.insert(j["kind"].get<std::string>()+"|"+std::to_string(j["case"].get<int>()));}catch(...){}}}
        for(const auto &kind:split(a.kinds,',')) {
            bool lazy=kind=="toolcall-lazy",schema=kind=="schema-eager";
            const auto &texts=schema?schema_scripts:(lazy?lazy_scripts:tool_scripts);
            const auto &users=schema?schema_users:(lazy?lazy_users:tool_users);
            const std::string &sys=schema?sys_schema:(lazy?sys_lazy:sys_tool);
            const std::string &gbnf=schema?gbnf_schema:gbnf_tool;
            for(size_t si=0;si<texts.size() && (a.max_scripts==0 || si<(size_t)a.max_scripts);++si) {
                if(greedy_done.count(kind+"|"+std::to_string(si)))continue;
                json result; result["native_pid"]=getpid();result["kind"]=kind;result["case"]=si;result["cap"]=a.greedy_cap;
                result["lazy_is_stock_control"]=lazy; result["teacher_forced"]=false;
                std::vector<std::vector<llama_token>> arm_tokens;
                for(int arm=0;arm<2;arm++) {
                    const auto t_arm=clk::now();
                    use_llg=arm==1 && !lazy;
                    llama_memory_clear(llama_get_memory(ctx),true);
                    std::string pre=chat_prefix(sys,users[si%users.size()]);
                    int np=-llama_tokenize(vocab,pre.data(),pre.size(),nullptr,0,false,true);
                    std::vector<llama_token> pt(np);llama_tokenize(vocab,pre.data(),pre.size(),pt.data(),np,false,true);
                    llama_batch b=llama_batch_init(np,0,1);
                    for(int i=0;i<np;i++){b.token[i]=pt[i];b.pos[i]=i;b.n_seq_id[i]=1;b.seq_id[i][0]=0;b.logits[i]=i==np-1;}
                    b.n_tokens=np;if(llama_decode(ctx,b)){return 3;}llama_batch_free(b);
                    auto *g=make_grammar(vocab,gbnf,lazy?"tool-call":"root",lazy); if(!g)return 3;
                    double prefill_ms=ms_since(t_arm);const auto t_decode=clk::now();
                    auto *greedy=llama_sampler_init_greedy();std::vector<llama_token> generated;bool eog=false;
                    for(int step=0;step<a.greedy_cap;step++) {
                        const float *lg=llama_get_logits_ith(ctx,-1);if(!lg)return 3;
                        for(int i=0;i<c.n_vocab;i++)c.cur[i]={i,lg[i],0};
                        llama_token_data_array arr={c.cur.data(),c.cur.size(),-1,false};
                        if(use_llg)llama_sampler_apply(g,&arr);
                        llama_sampler_apply(greedy,&arr);llama_token tok=arr.data[arr.selected].id;
                        if(!use_llg){
                            llama_token_data one={tok,1,0};llama_token_data_array oa={&one,1,-1,false};llama_sampler_apply(g,&oa);
                            if(one.logit==-INFINITY){
                                for(int i=0;i<c.n_vocab;i++)c.cur[i]={i,lg[i],0};
                                arr={c.cur.data(),c.cur.size(),-1,false};llama_sampler_apply(g,&arr);llama_sampler_apply(greedy,&arr);tok=arr.data[arr.selected].id;
                            }
                        }
                        std::ofstream(a.greedy_out+".native.jsonl",std::ios::app)<<json({{"native_pid",getpid()},{"kind",kind},{"case",si},{"arm",arm},{"step",step},{"token",tok},{"autoregressive_feedback",true}}).dump()<<"\n";
                        generated.push_back(tok);llama_sampler_accept(g,tok);
                        if(llama_vocab_is_eog(vocab,tok)){eog=true;break;}
                        llama_batch next=llama_batch_init(1,0,1);next.n_tokens=1;next.token[0]=tok;next.pos[0]=np+step;next.n_seq_id[0]=1;next.seq_id[0][0]=0;next.logits[0]=1;
                        int rc=llama_decode(ctx,next);llama_batch_free(next);if(rc)return 3;
                    }
                    std::vector<char> bytes(generated.size()*128+1024);
                    int n=llama_detokenize(vocab,generated.data(),generated.size(),bytes.data(),bytes.size(),false,true);if(n<0)return 3;
                    std::string hexbytes;const char *hex="0123456789abcdef";for(int bi=0;bi<n;bi++){unsigned char bc=bytes[bi];hexbytes+=hex[bc>>4];hexbytes+=hex[bc&15];}
                    result[arm==0?"stock":"llg101"]={{"tokens",generated},{"bytes_hex",hexbytes},{"eog",eog},{"prefill_ms",prefill_ms},{"decode_loop_ms",ms_since(t_decode)},{"tokens_n",generated.size()},{"autoregressive_feedback",true}};
                    arm_tokens.push_back(generated);llama_sampler_free(g);llama_sampler_free(greedy);
                }
                result["token_identical"]=arm_tokens[0]==arm_tokens[1];result["byte_identical"]=result["stock"]["bytes_hex"]==result["llg101"]["bytes_hex"];
                result["complete_output"]=result["stock"]["eog"].get<bool>()&&result["llg101"]["eog"].get<bool>();
                std::ofstream(a.greedy_out,std::ios::app)<<result.dump()<<"\n";
                printf("autoregressive greedy %s case %zu token_identical=%d complete=%d\n",kind.c_str(),si,(int)result["token_identical"].get<bool>(),(int)result["complete_output"].get<bool>());fflush(stdout);
            }
        }
        llama_free(ctx);llama_model_free(model);return 0;
    }
    if (want_real) {
        llama_context_params cp = llama_context_default_params();
        cp.n_ctx = 4096; cp.n_batch = 4096; cp.n_ubatch = 512; cp.n_seq_max = 1;
        cp.n_threads = a.threads; cp.n_threads_batch = a.threads; cp.no_perf = true;
        llama_context * lctx = llama_init_from_model(model, cp);
        if (!lctx) { fprintf(stderr, "failed to create a context on %s\n", a.logits_model.c_str()); return 3; }
        const auto t_real = clk::now();
        for (const std::string & kind : split(a.kinds, ',')) {
            const bool lazy = kind == "toolcall-lazy", schema = kind == "schema-eager";
        use_llg = llg_requested && !lazy;
            const auto & texts = schema ? schema_scripts : (lazy ? lazy_scripts : tool_scripts);
            const auto & users = schema ? schema_users : (lazy ? lazy_users : tool_users);
            const std::string & sys = schema ? sys_schema : (lazy ? sys_lazy : sys_tool);
            auto & per_script = real_logits[kind];
            for (size_t si = 0; si < texts.size() && (a.max_scripts==0 || si<(size_t)a.max_scripts); ++si) {
                const std::string pre = chat_prefix(sys, users[si % users.size()]);
                std::vector<llama_token> ptoks((size_t) pre.size() + 16);
                int32_t np = llama_tokenize(vocab, pre.c_str(), (int32_t) pre.size(), ptoks.data(), (int32_t) ptoks.size(), false, true);
                if (np < 0) { fprintf(stderr, "prefix tokenize failed\n"); return 3; }
                ptoks.resize((size_t) np);
                const std::vector<llama_token> stoks = tokenize(vocab, texts[si]);
                std::vector<llama_token> all = ptoks;
                all.insert(all.end(), stoks.begin(), stoks.end());
                llama_memory_clear(llama_get_memory(lctx), true);
                llama_batch b = llama_batch_init((int32_t) all.size(), 0, 1);
                for (size_t i = 0; i < all.size(); ++i) {
                    b.token[i] = all[i]; b.pos[i] = (llama_pos) i; b.n_seq_id[i] = 1; b.seq_id[i][0] = 0;
                    b.logits[i] = i + 1 >= ptoks.size() ? 1 : 0;          // positions that predict a scripted token
                }
                b.n_tokens = (int32_t) all.size();
                if (llama_decode(lctx, b) != 0) { fprintf(stderr, "llama_decode failed (%s script %zu)\n", kind.c_str(), si); return 3; }
                std::vector<std::vector<float>> pos;
                for (size_t k = 0; k < stoks.size(); ++k) {
                    const float * lg = llama_get_logits_ith(lctx, (int32_t) (ptoks.size() + k - 1));
                    if (!lg) { fprintf(stderr, "no logits at %zu\n", ptoks.size() + k - 1); return 3; }
                    pos.emplace_back(lg, lg + c.n_vocab);
                }
                llama_batch_free(b);
                per_script.push_back(std::move(pos));
                printf("real logits %s script %zu: prefix %zu + script %zu tokens\n", kind.c_str(), si, ptoks.size(), stoks.size());
            }
        }
        printf("real logits computed in %.1f s\n", ms_since(t_real) / 1000.0);
        llama_free(lctx);
    }

    const auto t_start = clk::now();
    for (const std::string & kind : split(a.kinds, ',')) {
        const bool lazy = kind == "toolcall-lazy";
        const bool schema = kind == "schema-eager";
        use_llg = llg_requested && !lazy;
        if (schema && gbnf_schema.empty()) { printf("skip %s: no --schema-file\n", kind.c_str()); continue; }
        const std::string & gbnf = schema ? gbnf_schema : gbnf_tool;
        const char * root = lazy ? "tool-call" : "root";
        std::vector<std::vector<llama_token>> scripts;
        for (const auto & s : (schema ? schema_scripts : (lazy ? lazy_scripts : tool_scripts))) {
            if (a.max_scripts==0 || scripts.size()<(size_t)a.max_scripts) { scripts.push_back(tokenize(vocab, s)); }
        }
        for (const std::string & prof : split(a.profiles, ',')) {
            const bool peaked = prof == "peaked";
            const bool real = prof == "real";
            if (real && !real_logits.count(kind)) { printf("skip %s|real: no --logits-model\n", kind.c_str()); continue; }
            const auto * rl = real ? &real_logits.at(kind) : nullptr;
            for (const std::string & bs : split(a.batches, ',')) {
                for(int arm=0; arm<(a.paired ? 2:1); ++arm) {
                use_llg = llg_requested && !lazy && (!a.paired || arm==1);
                const bool candidate_arm=llg_requested && (!a.paired || arm==1);
                const int batch = atoi(bs.c_str());
                const std::string key = a.label + "|" + (candidate_arm ? "llg101" : "stock") + "|" + kind + "|" + prof + "|B" + bs;
                if (done.count(key)) { printf("skip (done) %s\n", key.c_str()); continue; }
                if (ms_since(t_start) / 1000.0 > a.max_seconds) { printf("time budget reached: not starting %s\n", key.c_str()); continue; }

                const config_stats g = run_config(c, vocab, gbnf, root, lazy, true,  scripts, peaked, batch, a.reps, (uint32_t) a.seed, a.temp, rl);
                const config_stats b = run_config(c, vocab, gbnf, root, lazy, false, scripts, peaked, batch, a.reps, (uint32_t) a.seed, a.temp, rl);

                const double g_unit = mean(g.unit_ms), b_unit = mean(b.unit_ms);
                const double per_tok_g = g_unit / (double) batch, per_tok_b = b_unit / (double) batch;
                const double delta_tok = per_tok_g - per_tok_b;         // grammar cost per generated token (ms)
                const double share = a.step_ms > 0.0 ? 100.0 * delta_tok / a.step_ms : -1.0;
                std::string cls = "UNDECIDED_NO_STEP_MS";
                if (a.step_ms > 0.0) {
                    cls = (share >= 5.0 || delta_tok >= 2.0) ? "OPENS_DI110" : (share < 2.0 ? "CLOSES" : "BETWEEN");
                } else if (delta_tok >= 2.0) {
                    cls = "OPENS_DI110";
                }
                json j;
                j["key"] = key;
                j["arm"] = candidate_arm ? "llguidance-1.0.1-mask-first" : "stock-reject-resample";
                j["teacher_forced_not_autoregressive_oracle"] = true;
                j["llg_lazy_control_uses_legacy"] = kind=="toolcall-lazy";
                j["label"] = a.label; j["n_vocab"] = c.n_vocab; j["model"] = a.model;
                j["kind"] = kind; j["profile"] = prof; j["batch"] = batch; j["reps"] = a.reps; j["seed"] = a.seed;
                j["grammar_bytes"] = gbnf.size(); j["scripts"] = scripts.size();
                j["n_steps"] = g.n_steps; j["slow_path_frac"] = g.n_steps ? (double) g.n_slow / (double) g.n_steps : 0.0;
                j["script_invalid"] = g.n_script_invalid; j["passes_aborted"] = g.n_passes_aborted;
                j["unit"] = batch == 1 ? "ms_per_step" : "ms_per_verify_batch";
                j["grammar_unit_ms"] = { {"mean", g_unit}, {"p50", percentile(g.unit_ms, 0.5)}, {"p95", percentile(g.unit_ms, 0.95)}, {"max", percentile(g.unit_ms, 1.0)} };
                j["baseline_unit_ms"] = { {"mean", b_unit}, {"p50", percentile(b.unit_ms, 0.5)}, {"p95", percentile(b.unit_ms, 0.95)} };
                j["apply_full_vocab_ms"] = { {"mean", mean(g.apply_ms)}, {"p50", percentile(g.apply_ms, 0.5)}, {"p95", percentile(g.apply_ms, 0.95)} };
                j["accept_ms_mean"] = mean(g.accept_ms);
                j["temp"] = a.temp; j["logits_source"] = real ? a.logits_model : std::string("synthetic");
                j["n_slow"] = g.n_slow;
                j["raw_grammar_unit_ms"] = g.unit_ms; j["raw_baseline_unit_ms"] = b.unit_ms;
                j["raw_apply_ms"] = g.apply_ms; j["raw_accept_ms"] = g.accept_ms;
                j["raw_clone_ms"] = g.clone_ms; j["raw_slow_ms"] = g.slow_ms; j["raw_fast_ms"] = g.fast_ms;
                j["reject_resample_ms"] = { {"slow_step_mean", mean(g.slow_ms)}, {"fast_step_mean", mean(g.fast_ms)},
                                            {"delta", g.slow_ms.empty() ? 0.0 : mean(g.slow_ms) - mean(g.fast_ms)}, {"slow_step_p95", percentile(g.slow_ms, 0.95)} };
                j["clone_free_ms_mean"] = mean(g.clone_ms);
                j["grammar_delta_ms_per_token"] = delta_tok;
                j["decode_step_ms_assumed"] = a.step_ms;
                j["grammar_share_pct"] = share;
                j["rule_class"] = cls;
                j["rule"] = "share>=5% or >=2 ms/step opens DI-110; share<2% closes engine work (speculative-decoding-mtp-refresh.md SPEC-GRAM.1)";
                j["valid"] = g.n_script_invalid == 0 && g.n_steps > 0;
                std::ofstream(a.out, std::ios::app) << j.dump() << "\n";
                printf("%-52s unit %.4f ms (base %.4f) delta/tok %.4f ms share %.2f%% slow %.2f invalid %ld -> %s\n", key.c_str(), g_unit, b_unit,
                       delta_tok, share, j["slow_path_frac"].get<double>(), g.n_script_invalid, cls.c_str());
                fflush(stdout);
                }
            }
        }
    }
    llama_model_free(model);
    return 0;
}
