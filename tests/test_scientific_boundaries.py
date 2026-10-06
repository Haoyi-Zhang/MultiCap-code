"""Narrow arithmetic, sorted-kernel, and reproduction-comparison regressions."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "formal")]
from residual import bit_width, synthesize
from residual_check import check_residual
from logic_kernel import App, Assumption, Eq, Forall, ForallElim, Refl, Var, check
from validation.check_all import compare_results, directory_bytes_equal, run


class ExactResidualArithmetic(unittest.TestCase):
    def test_width_at_large_power_boundaries(self):
        self.assertEqual(bit_width(1), 0)
        for k in (1, 10, 49, 53, 100, 1023, 4096):
            with self.subTest(k=k):
                self.assertEqual(bit_width(2**k), k)
                self.assertEqual(bit_width(2**k + 1), k + 1)

    def test_class_count_requires_positive_integer(self):
        for value in (0, -1, True, 1.0):
            with self.subTest(value=value), self.assertRaises(ValueError): bit_width(value)

    def test_packet_numeric_metadata_requires_natural_integers(self):
        original = synthesize([[0, 1], [1, 0]], 0)
        for field in ("x_size", "y_size", "residual_classes", "code_bits", "fast_bits", "slow_bits", "temporary_bit_transfers"):
            for value in (True, float(original[field]), -1):
                packet = deepcopy(original)
                packet[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError): check_residual(packet)

    def test_class_indices_reject_boolean_aliases(self):
        packet = synthesize([[0, 1], [1, 0]], 0)
        packet["class_of_x"][0] = False
        with self.assertRaises(ValueError): check_residual(packet)


class SortedKernelContracts(unittest.TestCase):
    def test_context_cannot_assert_cross_sort_equality(self):
        invalid = Eq(Var("x", "X"), Var("y", "Y"))
        with self.assertRaises(TypeError): check(Assumption(invalid), (invalid,))

    def test_function_symbol_has_one_signature(self):
        x, y = Var("x", "X"), Var("y", "Y")
        first = Eq(App("f", (x,), "X"), x)
        for second in (Eq(App("f", (y,), "Y"), y),
                       Eq(App("f", (x, x), "X"), x),
                       Eq(App("f", (x,), "Y"), y)):
            with self.subTest(second=second), self.assertRaises(TypeError):
                check(Assumption(first), (first, second))

    def test_unused_shadowed_binder_still_checks_instantiation_sort(self):
        x, y = Var("x", "X"), Var("y", "Y")
        formula = Forall(x, Forall(x, Eq(x, x)))
        with self.assertRaises(TypeError): check(ForallElim(Assumption(formula), y), (formula,))
        signature = Eq(App("f", (x,), "X"), x)
        for term in (Var("", "X"), App("f", (y,), "X"), App("f", [x], "X")):
            with self.subTest(term=term), self.assertRaises(TypeError):
                check(ForallElim(Assumption(formula), term), (formula, signature))

    def test_well_sorted_shadowing_remains_valid(self):
        x, z = Var("x", "X"), Var("z", "X")
        formula = Forall(x, Forall(x, Eq(x, x)))
        self.assertEqual(check(ForallElim(Assumption(formula), z), (formula,)), formula.body)
        self.assertEqual(check(Refl(App("g", (x,), "X"))), Eq(App("g", (x,), "X"), App("g", (x,), "X")))


class ReproductionComparisons(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.left, self.right = Path(self.temp.name) / "retained", Path(self.temp.name) / "reproduced"
        for root in (self.left, self.right):
            (root / "certificates").mkdir(parents=True)
            for name in ("semantic.csv", "cache.csv", "integer_rank.csv", "residual.csv", "capability_separations.csv"):
                (root / name).write_bytes(b"id,value\ncase,1\n")
            for name in ("negative_controls.json", "rectangle_negative.json", "certificates/rank-000.json"):
                (root / name).write_text('{"value": 1}\n', encoding="utf-8")
            (root / "summary.json").write_text(json.dumps({"semantic_cases": 896, "cpu_seconds": 1, "wall_seconds": 1, "peak_rss_kib": 2}), encoding="utf-8")
            (root / "pilot.json").write_text(json.dumps({"reads": 8, "cpu_seconds": 1, "max_rss_kib": 2}), encoding="utf-8")

    def test_documented_measurements_may_change(self):
        for name in ("summary.json", "pilot.json"):
            path = self.right / name
            value = json.loads(path.read_text(encoding="utf-8"))
            value["cpu_seconds"] = 99
            value["peak_rss_kib" if name == "summary.json" else "max_rss_kib"] = None
            if name == "summary.json": value["wall_seconds"] = 100
            path.write_text(json.dumps(value), encoding="utf-8")
        self.assertTrue(compare_results(self.left, self.right)[0])

    def test_scientific_summary_change_fails_comparison(self):
        (self.right / "summary.json").write_text('{"semantic_cases": 895}', encoding="utf-8")
        self.assertFalse(compare_results(self.left, self.right)[0])

    def test_certificate_change_fails_comparison(self):
        (self.right / "certificates/rank-000.json").write_text('{"value": 2}\n', encoding="utf-8")
        self.assertFalse(compare_results(self.left, self.right)[0])

    def test_missing_or_extra_result_fails_comparison(self):
        self.assertFalse(compare_results(self.left, self.right / "absent")[0])
        (self.right / "unexpected.json").write_text("{}", encoding="utf-8")
        self.assertFalse(compare_results(self.left, self.right)[0])

    def test_missing_input_directory_is_not_empty_success(self):
        self.assertFalse(directory_bytes_equal(self.left / "absent", self.right / "absent")[0])

    def test_timeout_retains_failure_and_raw_log(self):
        logs = Path(self.temp.name) / "logs"
        logs.mkdir()
        with patch("validation.check_all.subprocess.run", side_effect=subprocess.TimeoutExpired("owned-test", 1)):
            result = run("timeout", [sys.executable, "owned-test.py"], logs, timeout=1)
        self.assertEqual(result["returncode"], 124)
        self.assertTrue(Path(result["raw_log"]).is_file())
        self.assertIn("exceeded 1 seconds", result["output_tail"])


if __name__ == "__main__": unittest.main()
