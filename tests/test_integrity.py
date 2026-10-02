#!/usr/bin/env python3
"""Exhaustive tiny-model and malformed-packet regression tests."""
from __future__ import annotations

import copy
import itertools
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "formal"))

from bags import check_program, denote, predicate
from replay import Replay
from cache_search import solve as solve_cache
from cache_check import check as check_cache
from residual import all_boolean_tables, execute, synthesize
from residual_check import check_residual
from integer_rank import bilinear, compile_fragments, solve_rank
from integer_rank_check import check_rank
from positive_source import canonical_source, const, probe_extract, xvar
from positive_source_check import quotient_extract
from logic_kernel import Assumption, Eq, Forall, ForallElim, Var, check
from semiring_kernel import Add, Const, Mul, Var as SVar, normalize


class ExhaustiveTinyModels(unittest.TestCase):
    def test_all_boolean_residual_tables_and_capacities(self):
        for table in all_boolean_tables(2, 2):
            zero = synthesize(table, 0)
            for fast in range(zero["code_bits"] + 2):
                packet = synthesize(table, fast)
                checked = check_residual(packet)
                self.assertEqual(checked["temporary_bit_transfers"],
                                 2 * max(0, packet["code_bits"] - fast))
                self.assertEqual([[execute(packet, x, y) for y in range(2)] for x in range(2)], table)

    def test_single_residual_class_needs_zero_bits(self):
        packet = synthesize([[7, 8], [7, 8], [7, 8]], 0)
        self.assertEqual(check_residual(packet)["code_bits"], 0)
        self.assertEqual(packet["temporary_bit_transfers"], 0)

    def test_ragged_residual_table_rejected(self):
        with self.assertRaises(ValueError):
            synthesize([[0, 1], [1]], 0)

    def test_malformed_residual_code_rejected(self):
        packet = synthesize([[0, 1], [1, 0]], 0)
        packet["codes"][1] = packet["codes"][0]
        with self.assertRaises(ValueError):
            check_residual(packet)

    def test_zero_integer_rank(self):
        packet = solve_rank([[0, 0], [0, 0]])
        self.assertEqual(check_rank(packet)["rank"], 0)
        self.assertEqual(compile_fragments(packet, [2, 3], [4, 5], 0)["value"], 0)

    def test_all_binary_two_by_two_factor_schedules(self):
        vectors = list(itertools.product(range(2), repeat=2))
        for cells in itertools.product(range(2), repeat=4):
            matrix = [list(cells[:2]), list(cells[2:])]
            packet = solve_rank(matrix)
            check_rank(packet)
            for x in vectors:
                for y in vectors:
                    for fast in range(packet["rank"] + 1):
                        compiled = compile_fragments(packet, list(x), list(y), fast)
                        self.assertEqual(compiled["value"], bilinear(matrix, list(x), list(y)))
                        self.assertEqual(compiled["temporary_word_transfers"],
                                         2 * max(0, packet["rank"] - fast))

    def test_negative_integer_rank_entry_rejected(self):
        with self.assertRaises(ValueError):
            solve_rank([[1, -1]])

    def test_rank_dimension_mutation_rejected(self):
        packet = solve_rank([[1, 0], [0, 1]])
        packet["rows"] += 1
        with self.assertRaises(ValueError):
            check_rank(packet)

    def test_two_slot_cache_formula_on_all_supported_rectangles(self):
        for n, m in ((1, 1), (1, 2), (1, 3), (2, 2), (2, 3), (3, 3)):
            packet = solve_cache(n, m, 2)
            checked = check_cache(packet)
            self.assertEqual(packet["optimum"], n * m + 1)
            self.assertEqual(checked["upper_reads"], n * m + 1)

    def test_cache_trace_mutation_rejected(self):
        packet = solve_cache(2, 2, 2)
        packet["trace"][0]["load"] = 99
        with self.assertRaises(ValueError):
            check_cache(packet)

    def test_cache_potential_mutation_rejected(self):
        packet = solve_cache(2, 2, 2)
        first = next(item for item in packet["potential"] if item["cache"] == 0 and item["done"] == 0)
        first["h"] -= 1
        with self.assertRaises(ValueError):
            check_cache(packet)


class SourceAndReplayBoundaries(unittest.TestCase):
    def test_replay_matches_oracle_for_every_declared_operator(self):
        base = [
            {"op": "input", "name": "R", "schema": ["int"]},
            {"op": "input", "name": "S", "schema": ["int"]},
        ]
        binary = ["sum", "diff", "inter", "union", "product", "left", "full"]
        programs = []
        for op in binary:
            node = {"op": op, "left": 0, "right": 1}
            if op in {"left", "full"}:
                node["pred"] = {"kind": "lt", "i": 0, "j": 1}
            programs.append({"nodes": base + [node], "root": 2})
        programs += [
            {"nodes": base + [{"op": "filter", "arg": 0,
                               "pred": {"kind": "eq_const", "i": 0, "value": 1}}], "root": 2},
            {"nodes": base + [{"op": "product", "left": 0, "right": 1},
                               {"op": "project", "arg": 2, "cols": [0]}], "root": 3},
            {"nodes": [{"op": "empty", "schema": ["int"]}], "root": 0},
        ]
        database = {"R": [[0], [1], [1]], "S": [[1], [2], [2]]}
        for program in programs:
            self.assertEqual(Counter(Replay(program, database).rows()), denote(program, database))

    def test_program_cycle_rejected(self):
        program = {"nodes": [{"op": "input", "name": "R", "schema": ["int"]},
                             {"op": "project", "arg": 1, "cols": [0]}], "root": 1}
        with self.assertRaises(ValueError):
            check_program(program)

    def test_source_schema_disagreement_rejected(self):
        program = {"nodes": [{"op": "input", "name": "R", "schema": ["int"]},
                             {"op": "input", "name": "R", "schema": ["int", "int"]},
                             {"op": "product", "left": 0, "right": 1}], "root": 2}
        with self.assertRaises(ValueError):
            check_program(program)

    def test_nullable_predicate_is_explicitly_two_valued(self):
        self.assertFalse(predicate({"kind": "eq", "i": 0, "j": 1}, (None, None)))
        self.assertFalse(predicate({"kind": "ne", "i": 0, "j": 1}, (None, 1)))

    def test_positive_source_variable_bounds_rejected(self):
        source = {"left_tags": 1, "right_tags": 1, "expression": xvar(1)}
        for checker in (probe_extract, quotient_extract):
            with self.assertRaises(ValueError):
                checker(source)

    def test_positive_source_constant_term_rejected(self):
        source = {"left_tags": 1, "right_tags": 1, "expression": const(1)}
        for checker in (probe_extract, quotient_extract):
            with self.assertRaises(ValueError):
                checker(source)

    def test_canonical_positive_source_admission_agrees_for_all_binary_two_by_two_matrices(self):
        for cells in itertools.product(range(2), repeat=4):
            matrix = [list(cells[:2]), list(cells[2:])]
            source = canonical_source(matrix)
            self.assertEqual(probe_extract(source)["matrix"], matrix)
            self.assertEqual(quotient_extract(source)["matrix"], matrix)


class KernelBoundaries(unittest.TestCase):
    def test_logic_kernel_rejects_undeclared_assumption(self):
        x = Var("x", "T")
        with self.assertRaises(ValueError):
            check(Assumption(Eq(x, x)))

    def test_logic_kernel_rejects_variable_capture(self):
        x = Var("x", "T")
        y = Var("y", "T")
        formula = Forall(x, Forall(y, Eq(x, y)))
        with self.assertRaises(ValueError):
            check(ForallElim(Assumption(formula), y), (formula,))

    def test_logic_kernel_rejects_sort_mismatch(self):
        x = Var("x", "T")
        z = Var("z", "U")
        formula = Forall(x, Eq(x, x))
        with self.assertRaises(TypeError):
            check(ForallElim(Assumption(formula), z), (formula,))

    def test_semiring_distributivity_normalizes(self):
        x, y, z = SVar("x"), SVar("y"), SVar("z")
        left = Mul(x, Add(y, z))
        right = Add(Mul(x, y), Mul(x, z))
        self.assertEqual(normalize(left), normalize(right))

    def test_semiring_negative_constant_rejected(self):
        with self.assertRaises(ValueError):
            normalize(Const(-1))


if __name__ == "__main__":
    unittest.main()
