#pragma once

// this is a staging header for new llama.cpp API
// breaking changes and C++ are allowed. everything here should be considered WIP
// try as much as possible to not include this header in the rest of the codebase

#include "llama.h"

#include <cstdint>
#include <map>

// Reserve a new compute graph. It is valid until the next call to llama_graph_reserve.
LLAMA_API struct ggml_cgraph * llama_graph_reserve(
        struct llama_context * ctx,
        uint32_t n_tokens,
        uint32_t n_seqs,
        uint32_t n_outputs);

// Number of ubatches this context served through the model's fused decode
// path (no graph). Lets tests prove the fused path actually ran.
LLAMA_API int64_t llama_n_fused_decode(const struct llama_context * ctx);

// Whether the environment opts in to the fused single-token decode path
// (read on every decode). The fused path is OFF by default: it runs only with
// GGML_FUSED_DECODE_ON set to a non-empty value other than "0", and
// GGML_FUSED_DECODE_OFF (any value, kept for back-compat) forces the graph path
// and wins when both are set.
LLAMA_API bool llama_fused_decode_env_enabled(void);

//
// chunk-KV reuse (experimental, phase P1: attention-only memory)
//
// A chunk is the K/V of a contiguous position range of one sequence, exported once and injected later at a
// different position offset (K is re-rotated by the offset through the ordinary K-shift graph). Nothing here runs
// unless a caller invokes it. Hybrid / recurrent / SWA memory is refused (return 0 / false and a log line).
//

// true when the context's memory can export/inject chunks; otherwise `why` (if given) is filled
LLAMA_API bool llama_chunk_kv_supported(const struct llama_context * ctx, char * why, size_t why_size);

// write the K/V of seq_id positions [p0, p1) (p1 < 0: to the sequence end; all positions must be present).
// dst == NULL: returns the size the blob needs. Returns the blob size, or 0 on refusal.
LLAMA_API size_t llama_chunk_kv_export(
        struct llama_context * ctx,
                     uint8_t * dst,
                      size_t   size,
                llama_seq_id   seq_id,
                   llama_pos   p0,
                   llama_pos   p1);

// place a blob into seq_id with every position moved by pos_delta; existing cells of the sequence are kept.
// Returns the bytes consumed, or 0 on refusal (cache unchanged).
LLAMA_API size_t llama_chunk_kv_inject(
        struct llama_context * ctx,
               const uint8_t * src,
                      size_t   size,
                llama_seq_id   seq_id,
                   llama_pos   pos_delta);

// diagnostic read-back (tests): K and V of seq_id positions [p0, p1) as f32, layer-major [layer][pos][n_embd_gqa].
// Returns the number of K floats written (V count is returned through *n_v_out when given); NULL outputs only count.
// A pending K re-rotation is applied first.
LLAMA_API size_t llama_chunk_kv_read_f32(
        struct llama_context * ctx,
                llama_seq_id   seq_id,
                   llama_pos   p0,
                   llama_pos   p1,
                       float * k_out,
                       float * v_out,
                      size_t * n_v_out);

// apply any pending K re-rotation now (a decode does it anyway); returns true if work was done
LLAMA_API bool llama_chunk_kv_apply_shift(struct llama_context * ctx);

// startup self-check of the K re-rotation: rotate +d then -d with the model's actual rope parameters; nmse_out = worst NMSE
// over the model's distinct rope configurations. Returns false when it could not run.
LLAMA_API bool llama_chunk_kv_rope_selfcheck(struct llama_context * ctx, llama_pos delta, double * nmse_out);

// Get the default ggml_type for a given ftype.
LLAMA_API ggml_type llama_ftype_get_default_type(llama_ftype ftype);

struct quantize_state_impl;

LLAMA_API quantize_state_impl * llama_quant_init(
        const llama_model * model,
        const llama_model_quantize_params * params);

LLAMA_API void llama_quant_free(quantize_state_impl * qs);

// Descriptor for constructing a mock model for quantization testing.
struct llama_quant_model_desc {
    const char * architecture;
    uint32_t n_embd;
    uint32_t n_ff;
    uint32_t n_layer;
    uint32_t n_head;
    uint32_t n_head_kv;
    uint32_t n_expert;
    uint32_t n_embd_head_k;
    uint32_t n_embd_head_v;
};

// Create a mock model from a metadata descriptor (for testing).
// The returned model must be freed with llama_model_free().
LLAMA_API llama_model * llama_quant_model_from_metadata(const llama_quant_model_desc * desc);

// Returns true if this tensor should be quantized (based on name, dims, params).
LLAMA_API bool llama_quant_tensor_allows_quantization(
        const quantize_state_impl * qs,
        const ggml_tensor * tensor);

// Compute quantization type assignments for a list of tensors.
// All tensors should be quantizable (use llama_quant_tensor_allows_quantization to filter).
// result_types: caller-allocated array of n_tensors elements, filled with assigned types.
LLAMA_API void llama_quant_compute_types(
        quantize_state_impl * qs,
        llama_ftype ftype,
        ggml_tensor ** tensors,
        ggml_type * result_types,
        size_t n_tensors);

//
// device memory querying
//

// "memory" as in physical memory for a buffer type, in bytes
struct llama_memory_breakdown_data {
    size_t model   = 0; // memory allocated for the model
    size_t context = 0; // memory allocated for the context
    size_t compute = 0; // memory allocated for temporary compute buffers

    size_t total() const {
        return model + context + compute;
    }
};

struct llama_device_memory_data {
    int64_t total;
    int64_t free;
    llama_memory_breakdown_data mb;
};

// TODO: convert to C-style data structure
using llama_memory_breakdown = std::map<ggml_backend_buffer_type_t, llama_memory_breakdown_data>;

LLAMA_API int32_t llama_model_n_expert (const struct llama_model * model);
LLAMA_API int32_t llama_model_n_devices(const struct llama_model * model);

LLAMA_API ggml_backend_dev_t llama_model_get_device(const struct llama_model * model, int i);

LLAMA_API llama_memory_breakdown llama_get_memory_breakdown(const struct llama_context * ctx);

// Set whether the context outputs nextn embeddings or not
// If masked == true,  output the embeddings only for the tokens with batch.logits != 0
// If masked == false, output the embeddings for all tokens in the batch regardless of batch.logits
LLAMA_API void llama_set_embeddings_nextn(struct llama_context * ctx, bool value, bool masked);

// Select which appended NextN block the DECODER_MTP graph runs (offset past
// the trunk: il = n_layer() + offset). Used by the speculative NextN driver to
// chain multiple trained NextN heads. Default 0 (first head).
LLAMA_API void llama_set_nextn_layer_offset(struct llama_context * ctx, int32_t offset);

// mirrors:
// LLAMA_API float * llama_get_embeddings(struct llama_context * ctx);
LLAMA_API float * llama_get_embeddings_nextn(struct llama_context * ctx);

// LLAMA_API float * llama_get_embeddings_ith(struct llama_context * ctx, int32_t i);
LLAMA_API float * llama_get_embeddings_nextn_ith(struct llama_context * ctx, int32_t i);

// Set whether the context outputs the input embeddings of a specific layer
LLAMA_API void llama_set_embeddings_layer_inp(struct llama_context * ctx, uint32_t lid, bool value);

// mirrors:
// LLAMA_API float * llama_get_embeddings(struct llama_context * ctx);
LLAMA_API float * llama_get_embeddings_layer_inp(struct llama_context * ctx, uint32_t lid);

LLAMA_API llama_context * llama_get_ctx_other(struct llama_context * ctx);

//
// model/context data extraction
//

// returns pointer to the target-model layer indices
LLAMA_API const int32_t * llama_model_target_layer_ids  (const struct llama_model * model);
// returns the number of extracted layers from target model
LLAMA_API uint32_t        llama_model_target_layer_ids_n(const struct llama_model * model);

// DSpark draft-block filler token (DeepSeek-V4.1 dspark_noise_token_id, model.py:131).
// Returns -1 when the GGUF declares none, in which case the caller falls back to the
// vocabulary's MASK token -- DeepSeek's tokenizer has no MASK, so a V4.1 DSpark GGUF must
// declare it (INF-77 DS41-B13).
LLAMA_API int32_t llama_model_dspark_noise_token(const struct llama_model * model);

// trained DSpark/DFlash block size, or 0 when the GGUF declares none
LLAMA_API int32_t llama_model_dspark_block_size(const struct llama_model * model);

// true for a DeepSeek-V4.1-Flash DSpark drafter. Such a model has NO encoder graph: main_proj and
// main_norm are stage-0 tensors applied inside the decoder's embd branch, so the caller feeds the
// concatenated target features straight to llama_decode at width n_embd_inp_enc.
LLAMA_API bool llama_model_dspark_is_v41(const struct llama_model * model);

// The TARGET hidden size a DSpark drafter's own main_proj implies, or 0 when this is not a DSpark
// v41 drafter. Use it in preference to assuming the draft and target hidden sizes are equal.
LLAMA_API int32_t llama_model_dspark_target_hidden_size(const struct llama_model * model);
