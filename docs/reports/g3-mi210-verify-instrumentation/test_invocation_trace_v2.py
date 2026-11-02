import unittest

from invocation_trace_v2 import parse_invocation_trace_v2


BEGIN = ("G3_TARGET_BEGIN_V2 invocation=12 class=parallel_verify_candidate slot=0 "
         "off=7 tokens=2 drafts=1 correlation=host_scope")
END = "G3_TARGET_END_V2 invocation=12 rc=0 correlation=host_scope"
DISPATCH = ("G3_FATTN_DISPATCH_V2 invocation=12 correlation=host_scope device=0 kernel=100 "
            "tensor=0x123 q=128,2,32,1 k_type=q8_0 k=128,100,8,1 "
            "v_type=q8_0 v=128,100,8,1")
WORKER_DISPATCH = DISPATCH.replace("invocation=12 correlation=host_scope", "invocation=0 correlation=unknown")


class InvocationTraceV2Test(unittest.TestCase):
    def test_correlates_dispatches_by_explicit_id(self):
        out = parse_invocation_trace_v2("server ready\n" + "\n".join((BEGIN, DISPATCH, END)))
        call = out["calls"][0]
        self.assertEqual(call["status"], "CORRELATED_CANDIDATE")
        self.assertTrue(call["complete"])
        self.assertEqual(call["dispatches"][0]["q"], (128, 2, 32, 1))
        self.assertEqual(out["correlated_dispatch_records"], 1)

    def test_worker_thread_dispatch_stays_uncorrelated(self):
        out = parse_invocation_trace_v2("\n".join((BEGIN, WORKER_DISPATCH, END)))
        self.assertEqual(out["calls"][0]["status"], "UNKNOWN")
        self.assertEqual(out["calls"][0]["dispatches"], [])
        self.assertEqual(out["uncorrelated_dispatch_counts"], {100: 1})

    def test_any_uncorrelated_event_makes_aggregate_unknown(self):
        out = parse_invocation_trace_v2("\n".join((BEGIN, DISPATCH, WORKER_DISPATCH, END)))
        self.assertEqual(out["calls"][0]["status"], "CORRELATED_CANDIDATE")
        self.assertEqual(out["overall_status"], "UNKNOWN")

    def test_non_candidate_and_failed_decode_stay_unknown(self):
        for begin, end, reason in (
            (BEGIN.replace("parallel_verify_candidate", "unclassified"), END,
             "target call was not classified as a verify candidate"),
            (BEGIN, END.replace("rc=0", "rc=-1"), "target decode returned nonzero"),
        ):
            out = parse_invocation_trace_v2("\n".join((begin, DISPATCH, end)))
            self.assertEqual(out["calls"][0]["status"], "UNKNOWN")
            self.assertEqual(out["calls"][0]["reason"], reason)

    def test_incomplete_call_and_no_dispatch_are_unknown(self):
        incomplete = parse_invocation_trace_v2("\n".join((BEGIN, DISPATCH)))
        self.assertFalse(incomplete["calls"][0]["complete"])
        self.assertEqual(incomplete["calls"][0]["status"], "UNKNOWN")
        absent = parse_invocation_trace_v2("\n".join((BEGIN, END)))
        self.assertEqual(absent["calls"][0]["status"], "UNKNOWN")

    def test_fail_closed_on_wrong_order_identity_or_payload(self):
        malformed = (
            (END,),
            (BEGIN, BEGIN),
            (BEGIN, END, END),
            (BEGIN, DISPATCH.replace("invocation=12", "invocation=99"), END),
            (BEGIN, END, DISPATCH),
            (BEGIN, DISPATCH.replace("correlation=host_scope", "correlation=maybe"), END),
            (BEGIN, DISPATCH.replace("invocation=12 correlation=host_scope", "invocation=4 correlation=host_scope"), END),
            (BEGIN, DISPATCH.replace("q=128,2,32,1", "q=128,0,32,1"), END),
            (BEGIN, DISPATCH.replace("kernel=100", "kernel=999"), END),
            (BEGIN.replace("tokens=2", "tokens=2 tokens=3"), END),
            (BEGIN.replace("tokens=2", "tokens=3"), DISPATCH, END),
            (BEGIN.replace("slot=0", "slot=-1"), DISPATCH, END),
            ("G3_TARGET_BEGIN_V1 id=12",),
        )
        for lines in malformed:
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                parse_invocation_trace_v2("\n".join(lines))

    def test_input_size_is_bounded(self):
        from invocation_trace_v2 import MAX_TRACE_BYTES
        with self.assertRaises(ValueError):
            parse_invocation_trace_v2("x" * (MAX_TRACE_BYTES + 1))


if __name__ == "__main__":
    unittest.main()
