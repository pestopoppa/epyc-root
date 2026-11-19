#!/bin/bash
set -euo pipefail
F=/mnt/raid0/llm/tmp/kpf-coverage-fix-20261105/make_successor.py
T=/mnt/raid0/llm/tmp
H=$T/heterogeneous-slot-fabric-residency
python3 $F kpf131-native-binding-impact-a1f0-r4-20261105 $T/kvu/kpf131-impact-r4-20261105 kpf131-native-binding-impact-a1f0-r5-20261105 $T/kvu/kpf131-impact-r5-20261105
python3 $F kpf17-oracle-impact-8952-20261105 $T/kvfork/kpf17-oracle-impact-8952-20261105 kpf17-oracle-impact-8952-20261105-r2 $T/kvfork/kpf17-oracle-impact-8952-20261105-r2
python3 $F kpf182-component-impact-8952-20261105-r2 $H/kpf182-component-impact-8952-20261105-r2 kpf182-component-impact-8952-20261105-r3 $H/kpf182-component-impact-8952-20261105-r3
for i in kpf26-attestation-impact-8682-20261105 kpf27d-impact-326f-successor-20261105 kpf625-server-impact-8952-20261105 kpf191-drafter-impact-8952-20261105; do python3 $F $i $H/$i $i-r2 $H/$i-r2; done
