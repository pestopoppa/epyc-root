CREATE TABLE IF NOT EXISTS test_backend_ops (
  test_time TEXT,
  build_commit TEXT,
  backend_name TEXT,
  op_name TEXT,
  op_params TEXT,
  test_mode TEXT,
  supported INTEGER,
  passed INTEGER,
  hard_failure INTEGER,
  error_message TEXT,
  layout_receipt TEXT,
  value_receipt TEXT,
  sensitivity_receipt TEXT,
  hostile_receipt TEXT,
  state_receipt TEXT,
  property_receipt TEXT,
  reference_receipt TEXT,
  checker_receipt TEXT,
  time_us REAL,
  flops REAL,
  bandwidth_gb_s REAL,
  memory_kb INTEGER,
  n_runs INTEGER,
  device_description TEXT,
  backend_reg_name TEXT
);

INSERT INTO test_backend_ops (test_time, build_commit, backend_name, op_name, op_params, test_mode, supported, passed, hard_failure, error_message, layout_receipt, value_receipt, sensitivity_receipt, hostile_receipt, state_receipt, property_receipt, reference_receipt, checker_receipt, time_us, flops, bandwidth_gb_s, memory_kb, n_runs, device_description, backend_reg_name) VALUES ('2026-10-31T02:40:57Z', '729599d69', 'CPU', 'MUL_MAT', 'name=served_q4km_27b_blk_3_ffn_gate_weight_n1,type=f32,ne=[17408,1,1,1],op_params=[],sources=q4_K[5120,17408,1,1],f32[5120,1,1,1]', 'perf', '1', '1', '0', '', '', '', '', '', '', '', '', '', '107.281184', '0.000000', '436.011388', '49048', '9460', '', '');
INSERT INTO test_backend_ops (test_time, build_commit, backend_name, op_name, op_params, test_mode, supported, passed, hard_failure, error_message, layout_receipt, value_receipt, sensitivity_receipt, hostile_receipt, state_receipt, property_receipt, reference_receipt, checker_receipt, time_us, flops, bandwidth_gb_s, memory_kb, n_runs, device_description, backend_reg_name) VALUES ('2026-10-31T02:40:59Z', '729599d69', 'CPU', 'MUL_MAT', 'name=served_q4km_27b_blk_3_ffn_gate_weight_n8,type=f32,ne=[17408,8,1,1],op_params=[],sources=q4_K[5120,17408,1,1],f32[5120,8,1,1]', 'perf', '1', '1', '0', '', '', '', '', '', '', '', '', '', '473.691853', '0.000000', '99.987536', '49664', '2197', '', '');
INSERT INTO test_backend_ops (test_time, build_commit, backend_name, op_name, op_params, test_mode, supported, passed, hard_failure, error_message, layout_receipt, value_receipt, sensitivity_receipt, hostile_receipt, state_receipt, property_receipt, reference_receipt, checker_receipt, time_us, flops, bandwidth_gb_s, memory_kb, n_runs, device_description, backend_reg_name) VALUES ('2026-10-31T02:41:00Z', '729599d69', 'CPU', 'MUL_MAT', 'name=served_q4km_27b_blk_3_ffn_gate_weight_n16,type=f32,ne=[17408,16,1,1],op_params=[],sources=q4_K[5120,17408,1,1],f32[5120,16,1,1]', 'perf', '1', '1', '0', '', '', '', '', '', '', '', '', '', '974.597092', '0.000000', '49.286693', '50368', '1169', '', '');
INSERT INTO test_backend_ops (test_time, build_commit, backend_name, op_name, op_params, test_mode, supported, passed, hard_failure, error_message, layout_receipt, value_receipt, sensitivity_receipt, hostile_receipt, state_receipt, property_receipt, reference_receipt, checker_receipt, time_us, flops, bandwidth_gb_s, memory_kb, n_runs, device_description, backend_reg_name) VALUES ('2026-10-31T02:41:01Z', '729599d69', 'CPU', 'MUL_MAT', 'name=served_q4km_27b_blk_3_ffn_up_weight_n1,type=f32,ne=[17408,1,1,1],op_params=[],sources=q4_K[5120,17408,1,1],f32[5120,1,1,1]', 'perf', '1', '1', '0', '', '', '', '', '', '', '', '', '', '114.569425', '0.000000', '408.274875', '49048', '8772', '', '');
INSERT INTO test_backend_ops (test_time, build_commit, backend_name, op_name, op_params, test_mode, supported, passed, hard_failure, error_message, layout_receipt, value_receipt, sensitivity_receipt, hostile_receipt, state_receipt, property_receipt, reference_receipt, checker_receipt, time_us, flops, bandwidth_gb_s, memory_kb, n_runs, device_description, backend_reg_name) VALUES ('2026-10-31T02:41:03Z', '729599d69', 'CPU', 'MUL_MAT', 'name=served_q4km_27b_blk_3_ffn_up_weight_n8,type=f32,ne=[17408,8,1,1],op_params=[],sources=q4_K[5120,17408,1,1],f32[5120,8,1,1]', 'perf', '1', '1', '0', '', '', '', '', '', '', '', '', '', '490.445608', '0.000000', '96.571935', '49664', '2197', '', '');
INSERT INTO test_backend_ops (test_time, build_commit, backend_name, op_name, op_params, test_mode, supported, passed, hard_failure, error_message, layout_receipt, value_receipt, sensitivity_receipt, hostile_receipt, state_receipt, property_receipt, reference_receipt, checker_receipt, time_us, flops, bandwidth_gb_s, memory_kb, n_runs, device_description, backend_reg_name) VALUES ('2026-10-31T02:41:04Z', '729599d69', 'CPU', 'MUL_MAT', 'name=served_q4km_27b_blk_3_ffn_up_weight_n16,type=f32,ne=[17408,16,1,1],op_params=[],sources=q4_K[5120,17408,1,1],f32[5120,16,1,1]', 'perf', '1', '1', '0', '', '', '', '', '', '', '', '', '', '960.871685', '0.000000', '49.990721', '50368', '1169', '', '');
INSERT INTO test_backend_ops (test_time, build_commit, backend_name, op_name, op_params, test_mode, supported, passed, hard_failure, error_message, layout_receipt, value_receipt, sensitivity_receipt, hostile_receipt, state_receipt, property_receipt, reference_receipt, checker_receipt, time_us, flops, bandwidth_gb_s, memory_kb, n_runs, device_description, backend_reg_name) VALUES ('2026-10-31T02:41:05Z', '729599d69', 'CPU', 'MUL_MAT', 'name=served_q4km_27b_blk_4_ffn_down_weight_n1,type=f32,ne=[5120,1,1,1],op_params=[],sources=q4_K[17408,5120,1,1],f32[17408,1,1,1]', 'perf', '1', '1', '0', '', '', '', '', '', '', '', '', '', '109.720272', '0.000000', '426.318829', '49048', '9116', '', '');
INSERT INTO test_backend_ops (test_time, build_commit, backend_name, op_name, op_params, test_mode, supported, passed, hard_failure, error_message, layout_receipt, value_receipt, sensitivity_receipt, hostile_receipt, state_receipt, property_receipt, reference_receipt, checker_receipt, time_us, flops, bandwidth_gb_s, memory_kb, n_runs, device_description, backend_reg_name) VALUES ('2026-10-31T02:41:07Z', '729599d69', 'CPU', 'MUL_MAT', 'name=served_q4km_27b_blk_4_ffn_down_weight_n8,type=f32,ne=[5120,8,1,1],op_params=[],sources=q4_K[17408,5120,1,1],f32[17408,8,1,1]', 'perf', '1', '1', '0', '', '', '', '', '', '', '', '', '', '461.735093', '0.000000', '102.576741', '49664', '2197', '', '');
INSERT INTO test_backend_ops (test_time, build_commit, backend_name, op_name, op_params, test_mode, supported, passed, hard_failure, error_message, layout_receipt, value_receipt, sensitivity_receipt, hostile_receipt, state_receipt, property_receipt, reference_receipt, checker_receipt, time_us, flops, bandwidth_gb_s, memory_kb, n_runs, device_description, backend_reg_name) VALUES ('2026-10-31T02:41:08Z', '729599d69', 'CPU', 'MUL_MAT', 'name=served_q4km_27b_blk_4_ffn_down_weight_n16,type=f32,ne=[5120,16,1,1],op_params=[],sources=q4_K[17408,5120,1,1],f32[17408,16,1,1]', 'perf', '1', '1', '0', '', '', '', '', '', '', '', '', '', '923.359281', '0.000000', '52.021644', '50368', '1169', '', '');
