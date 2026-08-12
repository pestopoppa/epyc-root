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

# ---------------------------------------------------------------------------
# Canonicalize PROJECT_ROOT to the ONE epyc-root spelling.
#
# B1, fixed 2026-08-12 (worktree adoption, phase 3). This repo is reachable
# from several distinct filesystem paths that are all the SAME repository:
#   * /workspace                                  — bind-mount alias (same inode)
#   * /mnt/raid0/llm/epyc-root                    — the canonical checkout
#   * /mnt/raid0/llm/worktrees/mains/<agent>      — a linked LANE worktree
# `realpath`/`pwd -P` do NOT collapse the bind mount, and a linked worktree is a
# genuinely different directory, so neither a string test nor an inode test on
# the working tree can recognise all three.
#
# The previous guard remapped only when the path was NOT under /mnt/raid0/*.
# A lane worktree at /mnt/raid0/llm/worktrees/mains/mainA IS under that prefix,
# so the remap never fired and LOG_DIR + XDG_{CACHE,DATA,STATE}_HOME forked one
# copy per worktree — five mains writing five audit logs and five caches.
#
# The identity that IS stable across all three is the git COMMON dir (shared by
# the main working tree and every linked worktree of one clone), compared by
# device+inode so the bind-mount alias matches too. Same primitive
# `serialized_push.py:repo_key()` derives its lock key from, for the same reason.
# ---------------------------------------------------------------------------
_CANON_ROOT="${ORCHESTRATOR_PATHS_LLM_ROOT:-/mnt/raid0/llm}/epyc-root"

_epyc_common_dir_id() {
  # dev:inode of a checkout's git COMMON dir, or nothing if that is unresolvable.
  local _d
  _d="$(git -C "$1" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || return 1
  [[ -n "${_d}" ]] || return 1
  stat -c '%d:%i' "${_d}" 2>/dev/null || return 1
}

if [[ "${_PROJECT_ROOT}" != "${_CANON_ROOT}" && -d "${_CANON_ROOT}" ]]; then
  _EPYC_ID_HERE="$(_epyc_common_dir_id "${_PROJECT_ROOT}" 2>/dev/null || true)"
  _EPYC_ID_CANON="$(_epyc_common_dir_id "${_CANON_ROOT}" 2>/dev/null || true)"
  if [[ -n "${_EPYC_ID_HERE}" && "${_EPYC_ID_HERE}" == "${_EPYC_ID_CANON}" ]]; then
    # Same repository, reached by an alias or a linked worktree.
    _PROJECT_ROOT="${_CANON_ROOT}"
  elif [[ "$(stat -c '%d:%i' "${_CANON_ROOT}" 2>/dev/null)" \
          == "$(stat -c '%d:%i' "${_PROJECT_ROOT}" 2>/dev/null)" ]]; then
    # Fallback for a git-less environment (no git binary, or a tarball copy):
    # the pre-B1 inode test, which still catches the bind-mount alias.
    _PROJECT_ROOT="${_CANON_ROOT}"
  fi
  unset _EPYC_ID_HERE _EPYC_ID_CANON
fi
unset -f _epyc_common_dir_id
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

# =============================================================================
# Canonical roots for the coordination plane — ONE spelling, sourced not retyped
# =============================================================================
#
# B2/B3/B7, 2026-08-12. Before this block every watchdog carried its own literal:
# `fleet_watch.sh` hardcoded its lock under /mnt/raid0/llm/epyc-root, three
# supervisors defaulted EPYC_ROOT to /workspace, and `nudge_retry.sh` baked a
# /workspace adapter path — four spellings of two directories. Under the
# worktree-per-main model a fifth spelling (the lane worktree's own path) appears
# for free, so "which /logs did that watchdog write to" stops being answerable.
# Every one of those scripts now sources this file and reads these variables.

# The epyc-root checkout everything shares (canonicalized above).
export EPYC_ROOT="${EPYC_ROOT:-${PROJECT_ROOT}}"

# The coordination RUNTIME plane. Deliberately the /workspace spelling and the
# same EPYC_BUS_ROOT override name: this MUST resolve byte-identically to
# session_bus.py's get_bus_root(), because agents and shell watchdogs address the
# same queue, cursors and heartbeats. Do not "canonicalize" it to the raid path —
# that would make the two halves of the fleet disagree by a string compare.
# Covered by scripts/coordination/tests/test_bus_root_resolution.py.
export EPYC_BUS_ROOT="${EPYC_BUS_ROOT:-/workspace/coordination/session-bus}"

# The one delivery-plane adapter (never a per-worktree copy: a lane worktree's
# checkout may be behind main, and a stale adapter mis-delivers silently).
export EPYC_TMUX_ADAPTER="${EPYC_TMUX_ADAPTER:-${EPYC_ROOT}/scripts/coordination/tmux_adapter.py}"

epyc_bus_root() { printf '%s\n' "${EPYC_BUS_ROOT}"; }
epyc_log_dir()  { printf '%s\n' "${LOG_DIR}"; }

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
