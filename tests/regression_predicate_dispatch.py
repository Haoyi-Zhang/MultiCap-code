"""Independent finite bag/predicate reference and exact replay-record regression."""
from collections import Counter
from dataclasses import asdict
from itertools import product
import csv
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from bags import cardinality_bounds, frame_bound
from replay import Replay


def truth(kind, left, right):
    if left is None or right is None:
        return False
    relation = (left > right) - (left < right)
    return relation in {"eq": (0,), "eq_const": (0,), "lt": (-1,), "ne": (-1, 1)}[kind]


def literal_bag(program, database):
    """Multiplicity equations, not cursor/rank replay or a saved implementation."""
    values = []
    widths = []
    for node in program["nodes"]:
        op = node["op"]
        result = Counter()
        if op in ("input", "empty"):
            width = len(node["schema"])
            if op == "input": result.update(map(tuple, database[node["name"]]))
        elif op in ("filter", "project"):
            source = values[node["arg"]]
            width = widths[node["arg"]] if op == "filter" else len(node["cols"])
            for row, count in source.items():
                if op == "project": result[tuple(row[index] for index in node["cols"])] += count
                elif matches(node["pred"], row): result[row] += count
        else:
            left, right = values[node["left"]], values[node["right"]]
            a, b = widths[node["left"]], widths[node["right"]]
            width = a if op in ("sum", "diff", "inter", "union") else a + b
            if width == a and op in ("sum", "diff", "inter", "union"):
                for row in left.keys() | right.keys():
                    counts = {"sum": left[row] + right[row], "diff": max(left[row] - right[row], 0),
                              "inter": min(left[row], right[row]), "union": max(left[row], right[row])}
                    if counts[op]: result[row] = counts[op]
            else:
                edges = [(x, y) for x in left for y in right
                         if op == "product" or matches(node["pred"], x + y)]
                for x, y in edges: result[x + y] += left[x] * right[y]
                if op in ("left", "full"):
                    for x in left:
                        if not any(x == edge[0] for edge in edges): result[x + (None,) * b] += left[x]
                if op == "full":
                    for y in right:
                        if not any(y == edge[1] for edge in edges): result[(None,) * a + y] += right[y]
        values.append(result); widths.append(width)
    return values[program["root"]]


def matches(predicate, row):
    right = predicate["value"] if predicate["kind"] == "eq_const" else row[predicate["j"]]
    return truth(predicate["kind"], row[predicate["i"]], right)


def tiny_cases():
    sources = ([], [[None]], [[0]], [[0], [0]], [[-1], [1]], [[None], [0], [1]])
    for left, right in product(sources, repeat=2):
        base = [{"op": "input", "name": "R", "schema": ["int?"]},
                {"op": "input", "name": "S", "schema": ["int?"]}]
        for op in ("sum", "diff", "inter", "union", "product", "left", "full"):
            for kind in (("eq", "eq_const", "lt", "ne") if op in ("left", "full") else ("eq",)):
                node = {"op": op, "left": 0, "right": 1,
                        "pred": {"kind": kind, "i": 0, "j": 1, "value": 0}}
                yield {"nodes": base + [node], "root": 2}, {"R": left, "S": right}


def record(program, database, limit=1000000, prefix=None):
    replay = Replay(program, database, read_limit=limit)
    rows, error = [], None
    cursor = replay.rows()
    try:
        for row in cursor:
            rows.append(list(row))
            if prefix is not None and len(rows) >= prefix: break
    except (RuntimeError, ValueError) as failure:
        error = {"type": type(failure).__name__, "message": str(failure)}
    finally:
        cursor.close()
    assert replay.stats.active_frames == 0
    return {"rows": rows, "metrics": asdict(replay.stats), "error": error}


def snapshot():
    probe = Replay({"nodes": [{"op": "empty", "schema": ["int?"]}], "root": 0}, {})
    predicates = []
    for kind, left, right in product(("eq", "eq_const", "lt", "ne"), (None, -1, 0, 1, 2), (None, -1, 0, 1, 2)):
        value = probe.test({"kind": kind, "i": 0, "j": 1, "value": right}, (left, right))
        assert value is truth(kind, left, right)
        predicates.append(value)
    tiny = []
    for program, database in tiny_cases():
        result = record(program, database)
        assert Counter(map(tuple, result["rows"])) == literal_bag(program, database)
        assert result["error"] is None
        tiny.append(result)
    archived = []
    for case in json.loads((ROOT / "inputs" / "semantic_cases.json").read_text()):
        result = record(case["program"], case["database"])
        assert Counter(map(tuple, result["rows"])) == literal_bag(case["program"], case["database"])
        bounds = cardinality_bounds(case["program"], case["database"])
        result.update({"id": case["id"], "family": case["family"],
                       "input_occurrences": sum(map(len, case["database"].values())),
                       "frame_bound": frame_bound(case["program"]),
                       "maximum_cardinality_bound": max(bounds)})
        archived.append(result)
    program, database = next((p, d) for p, d in tiny_cases() if len(d["R"]) == len(d["S"]) == 3)
    caps = [record(program, database, limit=limit) for limit in range(8)]
    prefixes = [record(program, database, prefix=prefix) for prefix in range(1, 7)]
    return {"predicates": predicates, "tiny": tiny, "archived": archived, "caps": caps, "prefixes": prefixes}


class PredicateDispatchRegression(unittest.TestCase):
    def test_literal_predicates_and_unsupported_failures(self):
        replay = Replay({"nodes": [{"op": "empty", "schema": ["int?"]}], "root": 0}, {})
        for kind, left, right in product(("eq", "eq_const", "lt", "ne"), (None, -1, 0, 1, 2), (None, -1, 0, 1, 2)):
            predicate = {"kind": kind, "i": 0, "j": 1, "value": right}
            self.assertIs(replay.test(predicate, (left, right)), truth(kind, left, right))
        for kind, exception in (("unsupported", KeyError), (False, KeyError), ([], TypeError)):
            with self.assertRaises(exception): replay.test({"kind": kind, "i": 0, "j": 1}, (0, 1))
            self.assertFalse(replay.test({"kind": kind, "i": 0, "j": 1}, (None, 1)))

    def test_independent_bags_and_exact_frozen_semantic_fields(self):
        result = snapshot()
        with (ROOT / "results" / "semantic.csv").open(newline="") as handle:
            retained = list(csv.DictReader(handle))
        self.assertEqual(len(result["archived"]), 896)
        self.assertEqual(len(retained), 896)
        for current, old in zip(result["archived"], retained):
            actual = {"id": current["id"], "family": current["family"],
                      "input_occurrences": current["input_occurrences"], "output_occurrences": len(current["rows"]),
                      "base_reads": current["metrics"]["base_reads"],
                      "peak_logical_frames": current["metrics"]["peak_frames"], "frame_bound": current["frame_bound"],
                      "maximum_counter": current["metrics"]["max_counter"],
                      "maximum_cardinality_bound": current["maximum_cardinality_bound"], "equivalent": True}
            self.assertEqual({key: str(value) for key, value in actual.items()}, old)
        self.assertEqual(sum(row["metrics"]["base_reads"] for row in result["archived"]), 9416)
        self.assertEqual(max(row["metrics"]["base_reads"] for row in result["archived"]), 76)

    def test_caps_close_and_duplicate_null_padding(self):
        result = snapshot()
        self.assertTrue(any(row["error"] for row in result["caps"]))
        for row in result["caps"] + result["prefixes"]:
            self.assertEqual(row["metrics"]["active_frames"], 0)
        p = {"nodes": [{"op": "input", "name": "R", "schema": ["int?"]},
                       {"op": "input", "name": "S", "schema": ["int?"]},
                       {"op": "full", "left": 0, "right": 1, "pred": {"kind": "eq", "i": 0, "j": 1}}], "root": 2}
        self.assertEqual(record(p, {"R": [[None]], "S": [[None]]})["rows"], [[None, None], [None, None]])


if __name__ == "__main__":
    unittest.main()
