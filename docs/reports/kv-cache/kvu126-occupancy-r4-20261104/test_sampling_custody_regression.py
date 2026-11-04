"""Review-only regression fixture; synthetic records and no inference."""
import json
from test_kvu126_compare import ComparisonTest
import kvu126_compare as compare

class SamplingCustodyRegression(ComparisonTest):
    def test_snapshot_after_request_start_before_response_refuses(self):
        plan, records = self.prospective()
        ref = records["arms"]["np8_48k"][0]["runtime_receipt"]
        receipt = json.loads((self.root / ref["path"]).read_bytes())
        receipt["before"]["captured_monotonic_s"] = 10.95
        records["arms"]["np8_48k"][0]["runtime_receipt"] = self.write_json(ref["path"], receipt)
        with self.assertRaisesRegex(ValueError, "do not span samples"):
            compare.analyze_prospective(plan, records, self.root, "9" * 64)

    def test_snapshot_at_request_start_refuses(self):
        plan, records = self.prospective()
        ref = records["arms"]["np8_48k"][0]["runtime_receipt"]
        receipt = json.loads((self.root / ref["path"]).read_bytes())
        receipt["before"]["captured_monotonic_s"] = 10.9
        records["arms"]["np8_48k"][0]["runtime_receipt"] = self.write_json(ref["path"], receipt)
        with self.assertRaisesRegex(ValueError, "do not span samples"):
            compare.analyze_prospective(plan, records, self.root, "9" * 64)
