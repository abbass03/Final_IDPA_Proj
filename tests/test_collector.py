from __future__ import annotations

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from collector import dict_to_xml, extract_infobox_normalized, structure_normalized_data


SAMPLE_HTML = """
<table class="infobox">
    <tr><th>Area</th></tr>
    <tr><th>Total</th><td>10,452 km2</td></tr>
    <tr><th>Water (%)</th><td>1.8</td></tr>
    <tr><th>Population (2024 estimate)</th><td>5,364,482</td></tr>
    <tr><th>Density</th><td>513/km2</td></tr>
    <tr><th>GDP (PPP)</th><td>2022 estimate</td></tr>
    <tr><th>Total</th><td>$78.233 billion</td></tr>
    <tr><th>Per capita</th><td>$11,793</td></tr>
    <tr><th>GDP (nominal)</th><td>2022 estimate</td></tr>
    <tr><th>Total</th><td>$21.780 billion</td></tr>
    <tr><th>Per capita</th><td>$3,283</td></tr>
    <tr><th>Gini (2011)</th><td>31.8</td></tr>
</table>
"""


class CollectorTests(unittest.TestCase):
    def test_extract_infobox_normalized_uses_context(self) -> None:
        data = extract_infobox_normalized(SAMPLE_HTML)

        self.assertEqual(data["area_total"], "10,452 km2")
        self.assertEqual(data["population_estimate"], "5,364,482")
        self.assertEqual(data["population_estimate_year"], "2024")
        self.assertEqual(data["gdp_ppp_total"], "$78.233 billion")
        self.assertEqual(data["gdp_nominal_total"], "$21.780 billion")
        self.assertEqual(data["gdp_ppp_year"], "2022")
        self.assertEqual(data["gini"], "31.8")
        self.assertEqual(data["gini_year"], "2011")

    def test_structure_normalized_data_builds_nested_sections(self) -> None:
        structured = structure_normalized_data(
            {
                "area_total": "10,452 km2",
                "area_water": "1.8",
                "population_estimate": "5,364,482",
                "population_density": "513/km2",
            }
        )

        self.assertEqual(structured["area"]["total"], "10,452 km2")
        self.assertEqual(structured["population"]["estimate"], "5,364,482")

    def test_dict_to_xml_preserves_nested_structure(self) -> None:
        root = dict_to_xml(
            "Lebanon",
            {
                "area": {"total": "10,452 km2", "water": "1.8"},
                "population": {"estimate": "5,364,482"},
            },
        )

        xml_text = ET.tostring(root, encoding="unicode")
        self.assertIn("<area><total>10,452 km2</total><water>1.8</water></area>", xml_text)
        self.assertIn("<population><estimate>5,364,482</estimate></population>", xml_text)


if __name__ == "__main__":
    unittest.main()
