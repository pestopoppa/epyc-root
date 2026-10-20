#!/bin/bash
# CPU test-backend-ops (all ops) under each barrier mode; HIP hidden. Sequential.
export HIP_VISIBLE_DEVICES=-1 LD_LIBRARY_PATH=/mnt/raid0/llm/worktrees/qwentts-threadpool-20261020/build:/opt/rocm/lib
cd /mnt/raid0/llm/worktrees/qwentts-threadpool-20261020/build
for cfg in "spin" "yield" "futex" "futex:1"; do
  mode=${cfg%%:*}; sp=${cfg##*:}; [ "$sp" = "$cfg" ] && sp=2000
  echo "== mode=$mode spin=$sp $(date -u +%T)"
  GGML_CPU_BARRIER=$mode GGML_CPU_BARRIER_SPIN=$sp nice -n 10 taskset -c 24-47 ./test-backend-ops test -b CPU -o ADD,SUB,MUL,DIV,SCALE,CLAMP,SQR,SQRT,SUM_ROWS,MEAN,RMS_NORM,NORM,ROPE,CONCAT,CPY,CONT,DUP,GET_ROWS,SET_ROWS,SOFT_MAX,FLASH_ATTN_EXT,MUL_MAT,SWIGLU,GLU,UNARY,ELU,RELU,GELU,GELU_ERF,SILU,SIGMOID,TANH,STEP,SIN,REPEAT,IM2COL,COL2IM_1D,PAD,PAD_REFLECT_1D,ARGSORT,CUMSUM,CONV_TRANSPOSE_1D,CONV_2D_DW > /mnt/raid0/llm/tmp/qwentts_threadpool_20261020/logs/tbo_${mode}_${sp}.log 2>&1
  echo "rc=$? $(tail -n 3 /mnt/raid0/llm/tmp/qwentts_threadpool_20261020/logs/tbo_${mode}_${sp}.log | tr '\n' ' ' | cut -c1-200)"
done
