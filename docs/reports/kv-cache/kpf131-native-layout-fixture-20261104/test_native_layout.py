import unittest

from native_layout import InvalidLayout, UnknownLayout, compare_bound, first_debug_grid, parse_grid


def grid(owner):
    return {"owners": owner * 2 + "." * 6,
            "positions": [0, 1, None, None, None, None, None, None],
            "size": 8, "stream": 0, "used_max_p1": 2, "used": 2,
            "head": 2, "n_swa": 0}


def mapping():
    return [{"path": "/opt/llama/lib/libggml.so", "device": "08:01",
             "inode": 1234, "sha256": "a" * 64}]


def binding(request, task, slot):
    return {"request_id": request, "task_id": task, "slot": slot, "pid": 900,
            "image_sha256": "b" * 64, "binary_sha256": "c" * 64,
            "mappings": mapping(), "event_start": 10, "event_end": 20}


def matched(*, fork_grid=None, control_grid=None, **changes):
    fb, cb = binding("fork-1", 77, 1), binding("control-1", 88, 2)
    receipt = {"http": 200, "n_fork_tokens": 2, "fork_src_slot": 0,
               "task_id": 77, "request_id": "fork-1"}
    args = {"child_slot": 1, "control_slot": 2, "fork_receipt": receipt,
            "prefix": 2, "batch_partition_fork": [66],
            "batch_partition_control": [66], "fork_binding": fb,
            "control_binding": cb}
    args.update(changes)
    return compare_bound(fork_grid or grid("1"), control_grid or grid("2"), **args)


class GridParsing(unittest.TestCase):
    def test_grid_parses_exact_occupancy(self):
        result = parse_grid("11......", "0 1 . . . . . .", 8)
        self.assertEqual(result["positions"], [0, 1, None, None, None, None, None, None])

    def test_bad_grid_size_and_character_are_invalid(self):
        for owners, positions, size in [("11", "0 1", True), ("11x.....", "0 1 . . . . . .", 8)]:
            with self.subTest(owners=owners), self.assertRaises(InvalidLayout):
                parse_grid(owners, positions, size)

    def test_occupancy_contradiction_is_invalid(self):
        with self.assertRaises(InvalidLayout):
            parse_grid("1.......", "0 1 . . . . . .", 8)

    def test_negative_occupied_position_is_invalid(self):
        with self.assertRaises(InvalidLayout):
            parse_grid("1.......", "-1 . . . . . . .", 8)

    def test_grid_above_local_cap_is_unknown(self):
        with self.assertRaises(UnknownLayout):
            parse_grid("1", "0", 262145)

    def test_multioverflow_owner_marker_is_preserved(self):
        self.assertEqual(parse_grid("M.......", "0 . . . . . . .", 8)["owners"], "M.......")

    def test_known_header_framing_decodes(self):
        lines = ["find_slot: stream[0], n = 2, used = 2, head = 2, size = 8, n_swa = 0",
                 "11......", "", "0 1 . . . . . .", "", "find_slot: min[0]=0"]
        result = first_debug_grid(lines)
        self.assertEqual((result["stream"], result["used"], result["size"]), (0, 2, 8))

    def test_malformed_header_abi_is_invalid(self):
        lines = ["find_slot: stream[0], n = 2, used = 3, head = 2, size = 8, n_swa = 0",
                 "11......", "", "0 1 . . . . . .", ""]
        with self.assertRaises(InvalidLayout):
            first_debug_grid(lines)

    @staticmethod
    def log_grid(*, n=2, used=2, head=2, size=8, owners="11......",
                 positions="0 1 . . . . . ."):
        return [f"find_slot: stream[0], n = {n}, used = {used}, head = {head}, size = {size}, n_swa = 0",
                owners, "", positions, "", "find_slot: min[0]=0"]

    def test_header_bounds_are_invalid(self):
        for kwargs in ({"head": 9}, {"n": 9}):
            with self.subTest(kwargs=kwargs), self.assertRaises(InvalidLayout):
                first_debug_grid(self.log_grid(**kwargs))

    def test_header_above_local_grid_cap_is_unknown(self):
        with self.assertRaises(UnknownLayout):
            first_debug_grid(["find_slot: stream[0], n = 262145, used = 0, head = 0, size = 262145, n_swa = 0"])

    def test_used_count_must_match_occupied_grid_cells(self):
        with self.assertRaises(InvalidLayout):
            first_debug_grid(self.log_grid(used=1))

    def test_used_max_p1_must_match_last_occupied_cell_plus_one(self):
        with self.assertRaises(InvalidLayout):
            first_debug_grid(self.log_grid(n=3))

    def test_sparse_occupancy_matches_native_counter_semantics(self):
        decoded = first_debug_grid(self.log_grid(
            n=8, used=1, head=8, owners=".......1",
            positions=". . . . . . . 7"))
        self.assertEqual((decoded["used"], decoded["used_max_p1"], decoded["head"]), (1, 8, 8))

    def test_missing_or_truncated_grid_is_unknown(self):
        with self.assertRaises(UnknownLayout):
            first_debug_grid(["unrelated log"])
        with self.assertRaises(UnknownLayout):
            first_debug_grid(["find_slot: stream[0], n = 2, used = 2, head = 2, size = 8, n_swa = 0",
                              "11......", ""])


class BoundComparison(unittest.TestCase):
    def test_exact_synthetic_layout_returns_bound_digest(self):
        result = matched()
        self.assertEqual(result["status"], "MATCHED")
        self.assertEqual(len(result["layout_sha256"]), 64)

    def test_missing_binding_is_unknown_without_digest(self):
        result = matched(fork_binding=None)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertNotIn("layout_sha256", result)

    def test_missing_fork_receipt_is_unknown_without_digest(self):
        result = matched(fork_receipt=None)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertNotIn("layout_sha256", result)

    def test_incomplete_fork_receipt_is_unknown_without_digest(self):
        receipt = {"http": 200, "n_fork_tokens": 2, "fork_src_slot": 0,
                   "task_id": 77}
        result = matched(fork_receipt=receipt)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertNotIn("layout_sha256", result)

    def test_missing_batch_partition_is_unknown_without_digest(self):
        result = matched(batch_partition_control=None)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertNotIn("layout_sha256", result)

    def test_different_present_batch_partition_is_invalid(self):
        self.assertEqual(matched(batch_partition_control=[65])["status"], "INVALID")

    def test_incomplete_mapping_is_unknown_without_digest(self):
        fb = binding("fork-1", 77, 1); fb["mappings"] = []
        result = matched(fork_binding=fb)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertNotIn("layout_sha256", result)

    def test_malformed_mapping_is_invalid(self):
        fb = binding("fork-1", 77, 1); fb["mappings"][0]["path"] = "relative.so"
        result = matched(fork_binding=fb)
        self.assertEqual(result["status"], "INVALID")
        self.assertNotIn("layout_sha256", result)

    def test_changed_mapping_or_process_custody_is_invalid(self):
        fb = binding("fork-1", 77, 1); fb["mappings"][0]["sha256"] = "d" * 64
        self.assertEqual(matched(fork_binding=fb)["status"], "INVALID")
        fb = binding("fork-1", 77, 1); fb["pid"] += 1
        self.assertEqual(matched(fork_binding=fb)["status"], "INVALID")

    def test_task_and_request_cross_binding_is_invalid(self):
        receipt = {"http": 200, "n_fork_tokens": 2, "fork_src_slot": 0,
                   "task_id": 78, "request_id": "fork-1"}
        self.assertEqual(matched(fork_receipt=receipt)["status"], "INVALID")
        receipt["task_id"] = 77; receipt["request_id"] = "other"
        self.assertEqual(matched(fork_receipt=receipt)["status"], "INVALID")

    def test_wrong_slot_prefix_or_partition_is_invalid(self):
        fb = binding("fork-1", 77, 2)
        self.assertEqual(matched(fork_binding=fb)["status"], "INVALID")
        self.assertEqual(matched(prefix=3)["status"], "INVALID")
        self.assertEqual(matched(batch_partition_control=[65])["status"], "INVALID")

    def test_multiowner_and_missing_prefix_are_unknown(self):
        f = grid("1"); f["owners"] = "M1......"
        args = {"child_slot": 1, "control_slot": 2,
                "fork_receipt": {"http": 200, "n_fork_tokens": 2, "fork_src_slot": 0,
                                 "task_id": 77, "request_id": "fork-1"},
                "prefix": 2, "batch_partition_fork": [66], "batch_partition_control": [66],
                "fork_binding": binding("fork-1", 77, 1),
                "control_binding": binding("control-1", 88, 2)}
        self.assertEqual(compare_bound(f, grid("2"), **args)["status"], "UNKNOWN")
        self.assertEqual(matched(fork_grid=grid("0"))["status"], "UNKNOWN")

    def test_grid_metadata_and_fork_receipt_mutations_do_not_pass(self):
        fork = grid("1"); fork["head"] = 7
        self.assertEqual(matched(fork_grid=fork)["status"], "INVALID")
        receipt = {"http": 200, "n_fork_tokens": 2, "fork_src_slot": 0,
                   "task_id": 77, "request_id": "fork-1"}
        receipt["http"] = 500
        self.assertEqual(matched(fork_receipt=receipt)["status"], "INVALID")

    def test_malformed_decoded_grid_is_invalid(self):
        fork = grid("1"); fork["owners"] = "1"
        self.assertEqual(matched(fork_grid=fork)["status"], "INVALID")

    def test_equal_but_malformed_direct_grids_are_invalid(self):
        mutations = [
            lambda g: g.update(used=1),
            lambda g: g.update(used_max_p1=3),
            lambda g: g.update(head=9),
            lambda g: g.update(stream=-1),
            lambda g: g.update(n_swa="0"),
            lambda g: g["positions"].__setitem__(0, -1),
            lambda g: g.update(size=True),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                fork, control = grid("1"), grid("2")
                mutate(fork)
                # Make the same defect in both dictionaries: equality must not
                # let malformed caller-provided data bypass parser validation.
                if fork.get("used") == 1:
                    control["used"] = 1
                elif fork.get("used_max_p1") == 3:
                    control["used_max_p1"] = 3
                elif fork.get("head") == 9:
                    control["head"] = 9
                elif fork.get("stream") == -1:
                    control["stream"] = -1
                elif fork.get("n_swa") == "0":
                    control["n_swa"] = "0"
                elif fork.get("size") is True:
                    control["size"] = True
                elif fork["positions"][0] == -1:
                    control["positions"][0] = -1
                self.assertEqual(matched(fork_grid=fork, control_grid=control)["status"], "INVALID")


if __name__ == "__main__":
    unittest.main()
