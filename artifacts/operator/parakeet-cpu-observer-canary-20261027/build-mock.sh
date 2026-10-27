#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-parakeet-cpu-v2
I=/mnt/raid0/llm/whisper.cpp/ggml/include
cc -shared -fPIC -Wall -Wextra -Werror -I"$I" -o "$D/observer.so" "$D/observer.c" -ldl
cc -shared -fPIC -Wall -Wextra -Werror -I"$I" -o "$D/mock.so" "$D/mock.c"
cc -Wall -Wextra -Werror -I"$I" -o "$D/mock_cli" "$D/mock_cli.c" "$D/mock.so" -Wl,-rpath,"$D"
for type in 0 1 3; do
 MOCK_DEVICE=$type LD_PRELOAD="$D/observer.so" "$D/mock_cli" > "$D/mock-$type.out" 2> "$D/mock-$type.err"
 rg -q '^mock forwarding PASS$' "$D/mock-$type.out"
 rg -q "device index=0 type=$type" "$D/mock-$type.err"
 for event in 'buffer pid=' 'usage pid=' 'sched_new pid=' 'graph pid=' 'direct_graph pid='; do rg -q "$event" "$D/mock-$type.err"; done
done
printf 'mock forwarding and native event coverage PASS\n'
