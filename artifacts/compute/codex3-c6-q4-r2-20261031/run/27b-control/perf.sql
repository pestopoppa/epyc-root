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

INSERT INTO test_backend_ops (test_time, build_commit, backend_name, op_name, op_params, test_mode, supported, passed, hard_failure, error_message, layout_receipt, value_receipt, sensitivity_receipt, hostile_receipt, state_receipt, property_receipt, reference_receipt, checker_receipt, time_us, flops, bandwidth_gb_s, memory_kb, n_runs, device_description, backend_reg_name) VALUES ('2026-10-31T02:41:10Z', '3dbca8f4f', 'CPU', 'MUL_MAT', 'name=served_q4km_27b_blk_3_ffn_gate_weight_n1,type=f32,ne=[17408,1,1,1],op_params=[],sources=q4_K[5120,17408,1,1],f32[5120,1,1,1]', 'perf', '1', '1', '0', '', '', '', '', '', '', '', '', '', '99.056366', '0.000000', '472.214153', '49048', '10148', '', '');
INSERT INTO test_backend_ops (test_time, build_commit, backend_name, op_name, op_params, test_mode, supported, passed, hard_failure, error_message, layout_receipt, value_receipt, sensitivity_receipt, hostile_receipt, state_receipt, property_receipt, reference_receipt, checker_receipt, time_us, flops, bandwidth_gb_s, memory_kb, n_runs, device_description, backend_reg_name) VALUES ('2026-10-31T02:41:11Z', '3dbca8f4f', 'CPU', 'MUL_MAT', 'name=served_q4km_27b_blk_3_ffn_gate_weight_n8,type=f32,ne=[17408,8,1,1],op_params=[],sources=q4_K[5120,17408,1,1],f32[5120,8,1,1]', 'perf', '1', '1', '0', '', '', '', '', '', '', '', '', '', '506.769231', '0.000000', '93.461241', '49664', '2028', '', '');
INSERT INTO test_backend_ops (test_time, build_commit, backend_name, op_name, op_params, test_mode, supported, passed, hard_failure, error_message, layout_receipt, value_receipt, sensitivity_receipt, hostile_receipt, state_receipt, property_receipt, reference_receipt, checker_receipt, time_us, flops, bandwidth_gb_s, memory_kb, n_runs, device_description, backend_reg_name) VALUES ('2026-10-31T02:41:12Z', '3dbca8f4f', 'CPU', 'MUL_MAT', 'name=served_q4km_27b_blk_3_ffn_gate_weight_n16,type=f32,ne=[17408,16,1,1],op_params=[],sources=q4_K[5120,17408,1,1],f32[5120,16,1,1]', 'perf', '1', '1', '0', '', '', '', '', '', '', '', '', '', '933.681779', '0.000000', '51.446509', '50368', '1169', '', '');
INSERT INTO test_backend_ops (test_time, build_commit, backend_name, op_name, op_params, test_mode, supported, passed, hard_failure, error_message, layout_receipt, value_receipt, sensitivity_receipt, hostile_receipt, state_receipt, property_receipt, reference_receipt, checker_receipt, time_us, flops, bandwidth_gb_s, memory_kb, n_runs, device_description, backend_reg_name) VALUES ('2026-10-31T02:41:14Z', '3dbca8f4f', 'CPU', 'MUL_MAT', 'name=served_q4km_27b_blk_3_ffn_up_weight_n1,type=f32,ne=[17408,1,1,1],op_params=[],sources=q4_K[5120,17408,1,1],f32[5120,1,1,1]', 'perf', '1', '1', '0', '', '', '', '', '', '', '', '', '', '98.932203', '0.000000', '472.806794', '49048', '10148', '', '');
INSERT INTO test_backend_ops (test_time, build_commit, backend_name, op_name, op_params, test_mode, supported, passed, hard_failure, error_message, layout_receipt, value_receipt, sensitivity_receipt, hostile_receipt, state_receipt, property_receipt, reference_receipt, checker_receipt, time_us, flops, bandwidth_gb_s, memory_kb, n_runs, device_description, backend_reg_name) VALUES ('2026-10-31T02:41:15Z', '3dbca8f4f', 'CPU', 'MUL_MAT', 'name=served_q4km_27b_blk_3_ffn_up_weight_n8,type=f32,ne=[17408,8,1,1],op_params=[],sources=q4_K[5120,17408,1,1],f32[5120,8,1,1]', 'perf', '1', '1', '0', '', '', '', '', '', '', '', '', '', '471.243059', '0.000000', '100.507117', '49664', '2197', '', '');
INSERT INTO test_backend_ops (test_time, build_commit, backend_name, op_name, op_params, test_mode, supported, passed, hard_failure, error_message, layout_receipt, value_receipt, sensitivity_receipt, hostile_receipt, state_receipt, property_receipt, reference_receipt, checker_receipt, time_us, flops, bandwidth_gb_s, memory_kb, n_runs, device_description, backend_reg_name) VALUES ('2026-10-31T02:41:17Z', '3dbca8f4f', 'CPU', 'MUL_MAT', 'name=served_q4km_27b_blk_3_ffn_up_weight_n16,type=f32,ne=[17408,16,1,1],op_params=[],sources=q4_K[5120,17408,1,1],f32[5120,16,1,1]', 'perf', '1', '1', '0', '', '', '', '', '', '', '', '', '', '1253.370060', '0.000000', '38.324410', '50368', '835', '', '');
INSERT INTO test_backend_ops (test_time, build_commit, backend_name, op_name, op_params, test_mode, supported, passed, hard_failure, error_message, layout_receipt, value_receipt, sensitivity_receipt, hostile_receipt, state_receipt, property_receipt, reference_receipt, checker_receipt, time_us, flops, bandwidth_gb_s, memory_kb, n_runs, device_description, backend_reg_name) VALUES ('2026-10-31T02:41:18Z', '3dbca8f4f', 'CPU', 'MUL_MAT', 'name=served_q4km_27b_blk_4_ffn_down_weight_n1,type=f32,ne=[5120,1,1,1],op_params=[],sources=q4_K[17408,5120,1,1],f32[17408,1,1,1]', 'perf', '1', '1', '0', '', '', '', '', '', '', '', '', '', '127.859960', '0.000000', '365.836326', '49048', '7912', '', '');
INSERT INTO test_backend_ops (test_time, build_commit, backend_name, op_name, op_params, test_mode, supported, passed, hard_failure, error_message, layout_receipt, value_receipt, sensitivity_receipt, hostile_receipt, state_receipt, property_receipt, reference_receipt, checker_receipt, time_us, flops, bandwidth_gb_s, memory_kb, n_runs, device_description, backend_reg_name) VALUES ('2026-10-31T02:41:19Z', '3dbca8f4f', 'CPU', 'MUL_MAT', 'name=served_q4km_27b_blk_4_ffn_down_weight_n8,type=f32,ne=[5120,8,1,1],op_params=[],sources=q4_K[17408,5120,1,1],f32[17408,8,1,1]', 'perf', '1', '1', '0', '', '', '', '', '', '', '', '', '', '486.098771', '0.000000', '97.435509', '49664', '2197', '', '');
INSERT INTO test_backend_ops (test_time, build_commit, backend_name, op_name, op_params, test_mode, supported, passed, hard_failure, error_message, layout_receipt, value_receipt, sensitivity_receipt, hostile_receipt, state_receipt, property_receipt, reference_receipt, checker_receipt, time_us, flops, bandwidth_gb_s, memory_kb, n_runs, device_description, backend_reg_name) VALUES ('2026-10-31T02:41:21Z', '3dbca8f4f', 'CPU', 'MUL_MAT', 'name=served_q4km_27b_blk_4_ffn_down_weight_n16,type=f32,ne=[5120,16,1,1],op_params=[],sources=q4_K[17408,5120,1,1],f32[17408,16,1,1]', 'perf', '1', '1', '0', '', '', '', '', '', '', '', '', '', '1030.424152', '0.000000', '46.616403', '50368', '1002', '', '');
