#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-cs8-stt5-accuracy-20261030/nemo-traced-v2
S=/mnt/raid0/llm/tmp/dive-transcribe-cpp/tc
B=/mnt/raid0/llm/tmp/codex3-cs8-stt2-transcribe-20261030/build
/usr/bin/c++ -I"$S/examples/cli" -I"$S/include" -I"$S/examples/common" -O3 -DNDEBUG -std=c++17 -fvisibility=hidden -fvisibility-inlines-hidden -Wall -Wextra -Wshadow -Wpedantic -Wno-unused-parameter -Wno-missing-field-initializers -o "$D/asr.traced.o" -c "$D/asr.traced.cpp"
cd "$B/examples/cli"
/usr/bin/c++ -O3 -DNDEBUG CMakeFiles/transcribe-cli.dir/main.cpp.o "$D/asr.traced.o" CMakeFiles/transcribe-cli.dir/diarize.cpp.o CMakeFiles/transcribe-cli.dir/langid.cpp.o CMakeFiles/transcribe-cli.dir/vad.cpp.o -o "$D/transcribe-cli" -Wl,-rpath,"$B/src:$B/ggml/src" ../../src/libtranscribe.so.0.4.0 ../common/libtranscribe-common-example.a -Wl,-rpath-link,"$B/ggml/src"
