"""Test patch correctness for 12 representative country pairs."""
from __future__ import annotations
import sys
sys.path.insert(0, "src")

from pathlib import Path
from parser import parse_xml_file
from preprocess import preprocess_tree
from ted import ted_with_ops, patch_with_ops
from utils import first_tree_difference, trees_equal

DATA = Path("data/normalized_xml")

PAIRS = [
    ("afghanistan", "albania"),
    ("lebanon",     "syria"),
    ("france",      "germany"),
    ("el_salvador", "guatemala"),
    ("algeria",     "morocco"),
    ("japan",       "south_korea"),
    ("brazil",      "argentina"),
    ("india",       "pakistan"),
    ("australia",   "new_zealand"),
    ("nigeria",     "ghana"),
    ("china",       "russia"),
    ("sweden",      "norway"),
]


def run(method="custom"):
    passed = 0
    for src_name, tgt_name in PAIRS:
        src_path = DATA / f"{src_name}.xml"
        tgt_path = DATA / f"{tgt_name}.xml"

        if not src_path.exists() or not tgt_path.exists():
            print(f"{src_name:20s} vs {tgt_name:20s} : SKIP (file missing)")
            continue

        tree1 = preprocess_tree(parse_xml_file(str(src_path)))
        tree2 = preprocess_tree(parse_xml_file(str(tgt_path)))

        distance, ops = ted_with_ops(tree1, tree2, "/country[1]", method=method)
        patched = patch_with_ops(tree1, ops, method=method)

        diff = first_tree_difference(patched, tree2)
        if diff is None:
            status = "OK"
            passed += 1
        else:
            status = f"FAIL: {diff[:80]}"

        print(f"{src_name:20s} vs {tgt_name:20s} : dist={distance:5d}  {status}")

    print(f"\nPatch success: {passed}/{len(PAIRS)}\n")


if __name__ == "__main__":
    run()
