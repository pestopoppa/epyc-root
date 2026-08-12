#!/usr/bin/env python3
"""Disposable composer-TUI stub — reproduces the composer semantics tmux_adapter.py
calibrated against real Codex / Claude Code panes (see its C6 block):

  * the terminal cursor sits at exactly the end of pending (typed-unsubmitted) input
  * a SUBMITTED message is echoed into the transcript above and the composer clears
  * an empty composer renders a bare prompt glyph alone

Three Enter behaviours, selected with --mode, so the adapter's submit path can be
driven through success AND through each observed failure without a real TUI:

  submit   Enter submits: transcript gains "<glyph> <text>", composer clears.
  swallow  Enter is dropped on the floor: the composer keeps the text. This is the
           observed 2026-08-12 standing condition (text pending, never submitted).
  picker   Enter is consumed by an in-composer completion overlay: it REPLACES the
           composer tail with a completion and submits nothing (Codex '@' picker /
           either TUI's '/' menu). Nothing reaches the transcript.
  cancel   Enter CLEARS the composer without submitting anything — a '/' menu that
           runs a command, or a modal dismissed on Enter. This is the one shape in
           which "the buffer was consumed" is true and the message was still never
           delivered, so it is what forces the transcript-echo conjunct (and its
           pre-Enter occurrence anchor) to carry its own weight.

Ctrl-U clears the composer (the only sanctioned clear — Ctrl-C is never sent to a
Codex pane). Ctrl-D quits, so the harness can stop it without killing by name.
"""
from __future__ import annotations

import argparse
import sys
import termios
import tty

GLYPHS = {"codex": "›", "claude": "❱"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("submit", "swallow", "picker", "cancel"),
                    default="submit")
    ap.add_argument("--glyph", choices=tuple(GLYPHS), default="codex")
    ap.add_argument("--seed", action="append", default=[],
                    help="transcript line present before anything is typed (repeatable)")
    ap.add_argument("--ignore-clear", action="store_true",
                    help="drop Ctrl-U on the floor, so a clear that cannot take can be "
                         "distinguished from one that did")
    ap.add_argument("--completion", default="src/completed_path.py",
                    help="what --mode picker rewrites the composer to")
    args = ap.parse_args()

    glyph = GLYPHS[args.glyph]
    transcript: list[str] = list(args.seed)
    composer = ""

    def draw() -> None:
        out = ["\033[2J\033[H"]
        for line in transcript[-30:]:
            out.append(line + "\r\n")
        out.append(glyph + " " + composer)
        sys.stdout.write("".join(out))
        sys.stdout.flush()

    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        draw()
        while True:
            ch = sys.stdin.read(1)
            if ch == "":
                break
            if ch == "\x04":                      # Ctrl-D: quit
                break
            if ch == "\x15":                      # Ctrl-U: clear composer
                if not args.ignore_clear:
                    composer = ""
            elif ch == "\x7f":                    # backspace
                composer = composer[:-1]
            elif ch in ("\r", "\n"):
                if args.mode == "submit":
                    if composer:
                        transcript.append(f"{glyph} {composer}")
                    composer = ""
                elif args.mode == "picker":
                    composer = args.completion
                elif args.mode == "cancel":
                    composer = ""          # consumed, but nothing was submitted
                # swallow: nothing happens at all
            elif ch >= " ":
                composer += ch
            draw()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
    return 0


if __name__ == "__main__":
    sys.exit(main())
