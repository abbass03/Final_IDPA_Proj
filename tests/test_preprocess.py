from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from models import Node
from preprocess import parse_date_components, parse_measurement, preprocess_tree


class PreprocessTests(unittest.TestCase):
    def test_parse_year_only_date(self) -> None:
        self.assertEqual(parse_date_components("2024"), {"year": "2024"})

    def test_parse_full_date(self) -> None:
        self.assertEqual(
            parse_date_components("14 May 2026"),
            {"year": "2026", "month": "05", "day": "14"},
        )

    def test_parse_measurement(self) -> None:
        self.assertEqual(
            parse_measurement("10,452 km2"),
            {"number": "10452", "unit": "km2"},
        )

    def test_preprocess_adds_structured_children_for_dates(self) -> None:
        node = Node(label="#text", node_type="text", value="14 May 2026")
        preprocess_tree(node)

        self.assertEqual(node.value, "2026-05-14")
        self.assertTrue(any(child.label == "parsed_date" for child in node.children))

    def test_preprocess_adds_structured_children_for_measurements(self) -> None:
        node = Node(label="#text", node_type="text", value="10,452 km2")
        preprocess_tree(node)

        self.assertEqual(node.value, "10452 km2")
        self.assertTrue(any(child.label == "parsed_measurement" for child in node.children))

    def test_simple_single_word_value_is_not_overexpanded(self) -> None:
        node = Node(label="#text", node_type="text", value="Lebanon")
        preprocess_tree(node)

        self.assertEqual(node.value, "Lebanon")
        self.assertEqual(node.children, [])


if __name__ == "__main__":
    unittest.main()
