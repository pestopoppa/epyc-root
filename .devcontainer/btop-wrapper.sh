#!/bin/sh
# Pick a compact btop layout on short terminals (e.g. SSH 80x24/143x33).
# The full layout (cpu mem net proc gpu0) needs 35 rows; the compact one
# (cpu mem gpu0) fits and still shows MI210 power.
lines=$(tput lines 2>/dev/null || true)
if [ -z "$lines" ]; then
    lines=$(stty size 2>/dev/null | cut -d' ' -f1)
fi
if [ -n "$lines" ] && [ "$lines" -gt 0 ] && [ "$lines" -lt 35 ]; then
    XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}/btop-small"
    export XDG_CONFIG_HOME
fi
exec /usr/local/bin/btop-bin "$@"
