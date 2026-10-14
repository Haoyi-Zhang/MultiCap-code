import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.bag_output import encode_bag_output
from src.residual import synthesize, execute
from src.residual_check import check_residual


class BagOutputTests(unittest.TestCase):
    def test_permuted_occurrences_have_one_residual(self):
        first = encode_bag_output([[None], [0], [0]], ['int?'])
        second = encode_bag_output([[0], [None], [0]], ['int?'])
        self.assertEqual(first, second)
        for capacity in range(4):
            packet = json.loads(json.dumps(synthesize([[first], [second]], capacity)))
            self.assertEqual(check_residual(packet)['residual_classes'], 1)
            self.assertEqual(packet['temporary_bit_transfers'], 0)
            self.assertEqual(execute(packet, 0, 0), first)
            self.assertEqual(execute(packet, 1, 0), first)

    def test_duplicate_counts_and_null_values_remain_observable(self):
        values = [encode_bag_output(rows, ['int?'])
                  for rows in ([[None], [0], [0]], [[None], [0]], [[0], [0]], [])]
        packet = json.loads(json.dumps(synthesize([[value] for value in values], 0)))
        self.assertEqual(check_residual(packet)['residual_classes'], 4)
        self.assertEqual(values[0]['counts'], [[[None], 1], [[0], 2]])

    def test_unit_tuple_multiplicity_and_tuple_order(self):
        self.assertEqual(encode_bag_output([[], [], []], []),
                         {'schema': [], 'counts': [[[], 3]]})
        self.assertNotEqual(encode_bag_output([[]], []), encode_bag_output([], []))
        self.assertNotEqual(encode_bag_output([[1, 2]], ['int', 'int']),
                            encode_bag_output([[2, 1]], ['int', 'int']))
        self.assertEqual(encode_bag_output([[0, None], [-2, 1]], ['int', 'int?'])['counts'],
                         [[[-2, 1], 1], [[0, None], 1]])

    def test_invalid_types_schemas_and_arities_are_rejected(self):
        for rows, schema in (([[True]], ['int']), ([[1.0]], ['int']),
                             ([[None]], ['int']), ([[0, 1]], ['int']),
                             ([[0]], ['text']), ([[]], 'int'), ('[]', [])):
            with self.assertRaises(ValueError):
                encode_bag_output(rows, schema)


if __name__ == '__main__':
    unittest.main()
