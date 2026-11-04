import unittest

from openai_tool_calls import adapt_openai_tool_calls


def response(tool_calls, finish_reason="tool_calls"):
    return {
        "finish_reason": finish_reason,
        "message": {"tool_calls": tool_calls},
    }


def call(name, arguments):
    return {"type": "function", "function": {"name": name, "arguments": arguments}}


class AdapterTests(unittest.TestCase):
    def test_valid_object_arguments(self):
        result = adapt_openai_tool_calls(response([call("sum", '{"a":1,"b":2}')]))
        self.assertTrue(result.ok)
        self.assertEqual(result.calls, [{"sum": {"a": 1, "b": 2}}])
        self.assertIsNone(result.error)

    def test_preserves_call_order(self):
        result = adapt_openai_tool_calls(response([
            call("first", '{"x":1}'), call("second", '{"y":2}')
        ]))
        self.assertTrue(result.ok)
        self.assertEqual(result.calls, [{"first": {"x": 1}}, {"second": {"y": 2}}])

    def test_requires_tool_calls_finish_reason(self):
        result = adapt_openai_tool_calls(response([call("f", "{}")], "stop"))
        self.assertFalse(result.ok)
        self.assertIn("finish_reason", result.error)
        self.assertIsNone(result.calls)

    def test_rejects_missing_or_empty_calls(self):
        for message in ({}, {"tool_calls": []}):
            result = adapt_openai_tool_calls({"finish_reason": "tool_calls", "message": message})
            self.assertFalse(result.ok)
            self.assertIn("tool_calls", result.error)
            self.assertIsNone(result.calls)

    def test_rejects_malformed_json(self):
        result = adapt_openai_tool_calls(response([call("f", '{"x":')]))
        self.assertFalse(result.ok)
        self.assertIn("invalid JSON", result.error)

    def test_rejects_non_object_json(self):
        result = adapt_openai_tool_calls(response([call("f", '[1,2]')]))
        self.assertFalse(result.ok)
        self.assertIn("not an object", result.error)

    def test_requires_function_tool_type(self):
        entry = call("f", "{}")
        entry["type"] = "custom"
        result = adapt_openai_tool_calls(response([entry]))
        self.assertFalse(result.ok)
        self.assertIn("type is not 'function'", result.error)

    def test_rejects_empty_function_name(self):
        for name in ("", "   "):
            result = adapt_openai_tool_calls(response([call(name, "{}")]))
            self.assertFalse(result.ok)
            self.assertIn("nonempty string", result.error)

    def test_rejects_duplicate_json_object_keys(self):
        result = adapt_openai_tool_calls(response([call("f", '{"x":1,"x":2}')]))
        self.assertFalse(result.ok)
        self.assertIn("duplicate JSON object key", result.error)

    def test_rejects_out_of_range_finite_json_number(self):
        result = adapt_openai_tool_calls(response([call("f", '{"x":1e9999}')]))
        self.assertFalse(result.ok)
        self.assertIn("supported finite range", result.error)

    def test_rejects_excessively_nested_arguments(self):
        nested = '{"x":' + '[' * 12000 + '0' + ']' * 12000 + '}'
        result = adapt_openai_tool_calls(response([call("f", nested)]))
        self.assertFalse(result.ok)
        self.assertIn("invalid JSON", result.error)

    def test_rejects_nonstandard_nan_constant(self):
        result = adapt_openai_tool_calls(response([call("f", '{"x":NaN}')]))
        self.assertFalse(result.ok)
        self.assertIn("non-standard JSON constant", result.error)


if __name__ == "__main__":
    unittest.main()
