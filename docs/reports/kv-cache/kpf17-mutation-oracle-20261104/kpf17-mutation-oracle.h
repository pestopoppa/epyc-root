#pragma once

// Require a valid same-destination control. Generic attention-copy refusal is
// INVALID; conditional stale set/decode refusal remains a distinct detection.
enum class kpf17_mutation_result {
    valid_restore_failed, valid_witness_failed, reset_failed,
    stale_attention_copy_failed, stale_state_set_rejected,
    stale_decode_failed, stale_nonfinite, stale_within_floor, stale_diverged
};

inline const char * kpf17_mutation_result_name(kpf17_mutation_result result) {
    switch (result) {
        case kpf17_mutation_result::valid_restore_failed:       return "invalid_valid_restore";
        case kpf17_mutation_result::valid_witness_failed:       return "invalid_valid_witness";
        case kpf17_mutation_result::reset_failed:               return "invalid_reset";
        case kpf17_mutation_result::stale_attention_copy_failed:return "invalid_stale_attention_copy";
        case kpf17_mutation_result::stale_state_set_rejected:   return "detected_stale_set_refused_after_valid_control";
        case kpf17_mutation_result::stale_decode_failed:        return "detected_stale_decode_refused_after_valid_control";
        case kpf17_mutation_result::stale_nonfinite:            return "invalid_stale_nonfinite";
        case kpf17_mutation_result::stale_within_floor:         return "invalid_stale_within_floor";
        case kpf17_mutation_result::stale_diverged:             return "detected_stale_logits_above_aa_floor";
    }
    return "invalid_unknown";
}

inline bool kpf17_mutation_detected(kpf17_mutation_result result) {
    return result == kpf17_mutation_result::stale_state_set_rejected ||
           result == kpf17_mutation_result::stale_decode_failed ||
           result == kpf17_mutation_result::stale_diverged;
}

template<class ValidRestore, class ValidWitness, class Reset, class StaleCopy, class StaleSet, class StaleWitness>
static kpf17_mutation_result kpf17_mutation_oracle(ValidRestore valid_restore, ValidWitness valid_witness,
        Reset reset, StaleCopy stale_copy, StaleSet stale_set, StaleWitness stale_witness) {
    if (!valid_restore()) return kpf17_mutation_result::valid_restore_failed;
    if (!valid_witness()) return kpf17_mutation_result::valid_witness_failed;
    if (!reset()) return kpf17_mutation_result::reset_failed;
    if (!stale_copy()) return kpf17_mutation_result::stale_attention_copy_failed;
    if (!stale_set()) return kpf17_mutation_result::stale_state_set_rejected;
    return stale_witness();
}
