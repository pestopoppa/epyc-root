# DF2-18 Step 2 per-width table (champion HIP build gpu-20261006-4348de400, Qwen3.8-27B Q8_0, f16 KV, rowexact batch mode)

| prefix | width | rows | first differing node (layer, op, type) | differing/compared nodes (per row, min-max) | top differing ops (row-summed share) | final-logit max abs delta (min-max) | ref top1-top2 margin (min) | argmax flips | nocap logit delta (identical to cap) |
|---|---|---|---|---|---|---|---|---|---|
| code | 2 | 2 | node_13 (L0, MUL_MAT, f32) all rows | 2335-2338 / 2341 | MUL_MAT 994, MUL 639, RESHAPE 448, VIEW 416, RMS_NORM 416, UNARY 415 | 0.137-0.156 | 5.721 | 0 | True |
| code | 3 | 3 | node_13 (L0, MUL_MAT, f32) all rows | 2335-2338 / 2341 | MUL_MAT 1491, MUL 959, RESHAPE 672, VIEW 624, RMS_NORM 624, UNARY 623 | 0.158-0.63 | 5.721 | 0 | True |
| code | 4 | 4 | node_13 (L0, MUL_MAT, f32) all rows | 2335-2338 / 2341 | MUL_MAT 1988, MUL 1279, RESHAPE 896, VIEW 832, RMS_NORM 832, UNARY 831 | 0.149-0.63 | 5.721 | 0 | True |
| code | 5 | 5 | node_13 (L0, MUL_MAT, f32) all rows | 2338-2338 / 2341 | MUL_MAT 2485, MUL 1600, RESHAPE 1120, UNARY 1040, VIEW 1040, RMS_NORM 1040 | 0.142-2.46 | 5.721 | 0 | True |
| code | 8 | 8 | node_13 (L0, MUL_MAT, f32) all rows | 2338-2338 / 2341 | MUL_MAT 3976, MUL 2560, RESHAPE 1792, UNARY 1664, VIEW 1664, RMS_NORM 1664 | 0.111-2.46 | 1.915 | 0 | True |
| code | 9 | 9 | node_13 (L0, MUL_MAT, f32) all rows | 2338-2338 / 2341 | MUL_MAT 4473, MUL 2880, RESHAPE 2016, UNARY 1872, VIEW 1872, RMS_NORM 1872 | 0.111-2.46 | 1.774 | 0 | True |
| prose | 2 | 2 | node_13 (L0, MUL_MAT, f32) all rows | 2338-2338 / 2341 | MUL_MAT 994, MUL 640, RESHAPE 448, UNARY 416, VIEW 416, RMS_NORM 416 | 0.148-0.174 | 0.541 | 0 | True |
| prose | 3 | 3 | node_13 (L0, MUL_MAT, f32) all rows | 2338-2338 / 2341 | MUL_MAT 1491, MUL 960, RESHAPE 672, UNARY 624, VIEW 624, RMS_NORM 624 | 0.169-0.21 | 0.316 | 0 | True |
| prose | 4 | 4 | node_13 (L0, MUL_MAT, f32) all rows | 2338-2338 / 2341 | MUL_MAT 1988, MUL 1280, RESHAPE 896, UNARY 832, VIEW 832, RMS_NORM 832 | 0.157-0.21 | 0.316 | 0 | True |
| prose | 5 | 5 | node_13 (L0, MUL_MAT, f32) all rows | 2338-2338 / 2341 | MUL_MAT 2485, MUL 1600, RESHAPE 1120, UNARY 1040, VIEW 1040, RMS_NORM 1040 | 0.164-0.208 | 0.316 | 0 | True |
| prose | 8 | 8 | node_13 (L0, MUL_MAT, f32) all rows | 2338-2338 / 2341 | MUL_MAT 3976, MUL 2560, RESHAPE 1792, UNARY 1664, VIEW 1664, RMS_NORM 1664 | 0.146-0.208 | 0.316 | 0 | True |
| prose | 9 | 9 | node_13 (L0, MUL_MAT, f32) all rows | 2338-2338 / 2341 | MUL_MAT 4473, MUL 2880, RESHAPE 2016, UNARY 1872, VIEW 1872, RMS_NORM 1872 | 0.146-0.208 | 0.316 | 0 | True |

A/A: 24/24 config pairs bitwise identical (node digests, ref digests, logits digests), capture and nocap modes.
