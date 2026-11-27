#!/bin/bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
PREFIX=/opt/rocm/lib/rocblas/library/TensileLibrary_Type_SS_Contraction_l_Alik_Bljk_Cijk_Dijk
OBJDUMP=/opt/rocm/llvm/bin/llvm-objdump
{
  for tensile in "${PREFIX}_CU104_gfx90a.co" "${PREFIX}_gfx90a.co"; do
    sha256sum "$tensile"
    mapfile -t symbols < <("$OBJDUMP" -t "$tensile" | awk '$4 == ".text" && $3 == "F" {print $1,$NF}' | sort -u)
    jq -r '[.native[].f32_bins[] | select(.backend == "rocBLAS Tensile") |
        .symbol | sub("\\.kd$";"")] | unique[]' dispatch-census.json |
    while IFS= read -r symbol; do
      printf '\n%s\n' "$symbol"
      start=
      for entry in "${symbols[@]}"; do
        read -r addr name <<< "$entry"
        if [[ -n "$start" && "$start" != "$addr" ]]; then
          "$OBJDUMP" -d --start-address="0x$start" --stop-address="0x$addr" "$tensile" |
            awk '$1 ~ /^(global|buffer|flat)_(atomic|store)_/ {count[$1]++}END{for(i in count) print count[i],i}' |
            sort -k2
          break
        fi
        if [[ "$name" == "$symbol" ]]; then
          start=$addr
        fi
      done
      if [[ -z "$start" ]]; then
        printf 'Symbol unavailable\n'
      fi
    done
  done
} > tensile-store-isa.txt
