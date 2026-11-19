import unittest
from scan_policy import analysis_env, impact_args, validate_impact
class ScanPolicyTests(unittest.TestCase):
    def test_single_worker_keeps_scope_and_inherited_environment(self):
        env = analysis_env({"PATH": "/bin", "GITNEXUS_WORKER_POOL_SIZE": "16"})
        self.assertEqual(env["GITNEXUS_WORKER_POOL_SIZE"], "1")
        self.assertEqual(env["GITNEXUS_PARSE_CHUNK_CONCURRENCY"], "1")
        self.assertEqual(env["PATH"], "/bin")
        self.assertGreater(int(env["GITNEXUS_WORKER_MAX_CUMULATIVE_TIMEOUT_MS"]), int(env["GITNEXUS_WORKER_SUB_BATCH_TIMEOUT_MS"]))
        self.assertNotIn("GITNEXUS_NO_GITIGNORE", env)
    def test_exact_worktree_and_file_binding(self):
        args = impact_args("/private/p3", "find_slot", "src/llama-kv-cache.cpp")
        self.assertEqual(args[args.index("--repo") + 1], "/private/p3")
        self.assertEqual(args[args.index("--file") + 1], "src/llama-kv-cache.cpp")
        self.assertEqual(args[args.index("--direction") + 1], "upstream")
    def test_missing_partial_ambiguous_or_unknown_refused(self):
        for record in ({}, {"risk":"UNKNOWN"}, {"risk":"LOW","partial":True}, {"risk":"LOW","truncated":True}, {"risk":"LOW","status":"ambiguous"}, {"risk":"LOW","error":"bad"}):
            with self.subTest(record=record), self.assertRaises(ValueError):
                validate_impact("find_slot", record)
    def test_high_risk_is_preserved_for_owner_warning(self):
        for risk in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            validate_impact("find_slot", {"risk":risk})
if __name__ == "__main__": unittest.main()
