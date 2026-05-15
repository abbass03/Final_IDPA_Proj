from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from models import Node
from semantic_values import semantic_value_distance
from ted_custom import update_cost


class SemanticTedTests(unittest.TestCase):
    def test_close_measurements_have_low_distance(self) -> None:
        self.assertEqual(semantic_value_distance("10452 km2", "10450 km2"), 0)

    def test_different_measurements_have_higher_distance(self) -> None:
        self.assertGreaterEqual(semantic_value_distance("10452 km2", "30000 km2"), 2)

    def test_same_year_dates_are_closer_than_different_years(self) -> None:
        same_year = semantic_value_distance("14 May 2026", "20 August 2026")
        different_year = semantic_value_distance("14 May 2026", "20 August 2024")
        self.assertLess(same_year, different_year)

    def test_text_overlap_affects_distance(self) -> None:
        similar = semantic_value_distance("Lebanese Republic", "Republic of Lebanon")
        different = semantic_value_distance("Lebanese Republic", "Swiss Confederation")
        self.assertLess(similar, different)

    def test_update_cost_uses_semantic_value_distance(self) -> None:
        left = Node(label="#text", node_type="text", value="10452 km2")
        right = Node(label="#text", node_type="text", value="10450 km2")
        far = Node(label="#text", node_type="text", value="30000 km2")

        self.assertLess(update_cost(left, right), update_cost(left, far))


if __name__ == "__main__":
    unittest.main()
