#!/bin/bash
# =============================================================================
# Environment Library for epyc-root Shell Scripts
# =============================================================================
#
# Reconstructed 2026-05-27: this file is sourced by 10+ session/governance
# scripts (agent_log.sh, session_init.sh, verify_llama_cpp.sh, claude_safe_start.sh,
# monitor_storage.sh, ...) but was never carried into epyc-root during the
# 2026-02-25 monorepo split, so every one of those scripts failed at
# `source ../lib/env.sh` (e.g. agent_log.sh wrote no audit entry). Modeled on the
# orchestrator/research env.sh, with one fix: PROJECT_ROOT is SELF-LOCATED to this
# repo (epyc-root) rather than defaulting to the archived monorepo `${LLM_ROOT}/claude`,
# so LOG_DIR resolves to epyc-root/logs (the documented agent_audit.log home).
#
# Usage:
#   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#   source "${SCRIPT_DIR}/../lib/env.sh"
#
# Provides: LLM_ROOT/PROJECT_ROOT + ORCHESTRATOR_PATHS_* aliases, model/llama/cache
# paths, LOG_DIR, HF/XDG/TMPDIR exports, and path helpers.
# =============================================================================

# Determine script location to find the repo root (epyc-root).
_ENV_SH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_PROJECT_ROOT="$(cd "${_ENV_SH_DIR}/../.." && pwd)"
# If sourced via a bind alias OUTSIDE the raid prefix (e.g. /workspace, a bind mount of epyc-root —
# same inode, so realpath/pwd -P do NOT resolve it to the source), prefer the canonical /mnt/raid0
# spelling so prefix-guarded helpers (check_path_prefix/ensure_dir) and downstream tooling see a
# consistent path. Inode-verified: only remaps when it is genuinely the same directory.
_CANON_ROOT="${ORCHESTRATOR_PATHS_LLM_ROOT:-/mnt/raid0/llm}/epyc-root"
if [[ "${_PROJECT_ROOT}" != /mnt/raid0/* && -d "${_CANON_ROOT}" \
      && "$(stat -c '%d:%i' "${_CANON_ROOT}" 2>/dev/null)" == "$(stat -c '%d:%i' "${_PROJECT_ROOT}" 2>/dev/null)" ]]; then
  _PROJECT_ROOT="${_CANON_ROOT}"
fi
unset _CANON_ROOT

# Load .env file if present (repo-local overrides).
if [[ -f "${_PROJECT_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${_PROJECT_ROOT}/.env" 2>/dev/null || true
  set +a
fi

# =============================================================================
# Base Paths
# =============================================================================

# LLM root - machine-wide (models, cache, llama.cpp). Overridable.
export ORCHESTRATOR_PATHS_LLM_ROOT="${ORCHESTRATOR_PATHS_LLM_ROOT:-/mnt/raid0/llm}"
export LLM_ROOT="${ORCHESTRATOR_PATHS_LLM_ROOT}"

# Project root - SELF-LOCATED to this repository (epyc-root), NOT the archived monorepo.
export ORCHESTRATOR_PATHS_PROJECT_ROOT="${_PROJECT_ROOT}"
export PROJECT_ROOT="${_PROJECT_ROOT}"

# =============================================================================
# Derived Paths (machine-wide model/binary locations)
# =============================================================================

export ORCHESTRATOR_PATHS_MODELS_DIR="${ORCHESTRATOR_PATHS_MODELS_DIR:-${LLM_ROOT}/models}"
export MODELS_DIR="${ORCHESTRATOR_PATHS_MODELS_DIR}"

export ORCHESTRATOR_PATHS_MODEL_BASE="${ORCHESTRATOR_PATHS_MODEL_BASE:-${LLM_ROOT}/lmstudio/models}"
export MODEL_BASE="${ORCHESTRATOR_PATHS_MODEL_BASE}"

export ORCHESTRATOR_PATHS_LLAMA_CPP_BIN="${ORCHESTRATOR_PATHS_LLAMA_CPP_BIN:-${LLM_ROOT}/llama.cpp/build/bin}"
export LLAMA_CPP_BIN="${ORCHESTRATOR_PATHS_LLAMA_CPP_BIN}"

export ORCHESTRATOR_PATHS_LLAMA_SERVER="${ORCHESTRATOR_PATHS_LLAMA_SERVER:-${LLAMA_CPP_BIN}/llama-server}"
export LLAMA_SERVER="${ORCHESTRATOR_PATHS_LLAMA_SERVER}"

export ORCHESTRATOR_PATHS_CACHE_DIR="${ORCHESTRATOR_PATHS_CACHE_DIR:-${LLM_ROOT}/cache}"
export CACHE_DIR="${ORCHESTRATOR_PATHS_CACHE_DIR}"

export ORCHESTRATOR_PATHS_TMP_DIR="${ORCHESTRATOR_PATHS_TMP_DIR:-${LLM_ROOT}/tmp}"
export TMP_DIR="${ORCHESTRATOR_PATHS_TMP_DIR}"

# =============================================================================
# Project-relative paths (epyc-root)
# =============================================================================

export ORCHESTRATOR_PATHS_LOG_DIR="${ORCHESTRATOR_PATHS_LOG_DIR:-${PROJECT_ROOT}/logs}"
export LOG_DIR="${ORCHESTRATOR_PATHS_LOG_DIR}"

# Path security prefix (empty to disable check)
export ORCHESTRATOR_PATHS_RAID_PREFIX="${ORCHESTRATOR_PATHS_RAID_PREFIX:-/mnt/raid0/}"

# =============================================================================
# HuggingFace & Cache Directories (machine-wide; keep off the root SSD)
# =============================================================================

export HF_HOME="${HF_HOME:-${CACHE_DIR}/huggingface}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-${HF_HOME}}"
export HF_DATASETS_CACHE="${HF_DATASETS_CACHE:-${HF_HOME}/datasets}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-${CACHE_DIR}/pip}"

export XDG_CACHE_HOME="${XDG_CACHE_HOME:-${PROJECT_ROOT}/cache}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-${PROJECT_ROOT}/share}"
export XDG_STATE_HOME="${XDG_STATE_HOME:-${PROJECT_ROOT}/state}"

# Temp directory (critical: avoid the 120GB root SSD)
export TMPDIR="${TMPDIR:-${TMP_DIR}}"

# =============================================================================
# Convenience Functions
# =============================================================================

check_path_prefix() {
  local path="$1"
  local prefix="${ORCHESTRATOR_PATHS_RAID_PREFIX}"
  [[ -z "$prefix" ]] && return 0
  if [[ "$path" == "$prefix"* ]]; then
    return 0
  else
    echo "ERROR: Path '$path' is not under required prefix '$prefix'" >&2
    return 1
  fi
}

llama_bin() { echo "${LLAMA_CPP_BIN}/$1"; }

model_path() { echo "${MODEL_BASE}/$1"; }

ensure_dir() {
  local dir="$1"
  if check_path_prefix "$dir"; then mkdir -p "$dir"; fi
}

# Cleanup temporary variables
unset _ENV_SH_DIR
unset _PROJECT_ROOT
