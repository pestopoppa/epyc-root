#!/bin/bash
# Launch guard for TUI mains. Ignore terminal job-control stop signals before
# exec'ing the real command, so a mis-aimed stop (a Ctrl-Z byte from a stale
# tmux client, or a fleet guard) cannot SIGTSTP a main dead.
#
# Why this exists: opencode installs no SIGTSTP/SIGTTIN/SIGTTOU handler, so
# any of those signals stops it with no recovery (observed 2026-08-13: mains
# and coordinator sessions wedged in T state with SIGTSTP pending). SIG_IGN is
# inherited across exec, so a process launched through this guard starts
# immune to those three signals. claude is unaffected (it handles them).
#
# Note: this must run under bash, not fish. fish's `trap "" SIG` does NOT set
# SIG_IGN (verified), so the tmux default-shell (fish) would drop the guard.
trap '' TSTP TTIN TTOU
exec /bin/bash -c "$1"
