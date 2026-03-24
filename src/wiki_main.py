from __future__ import annotations

import json
import os
import sys

from wiki_parser import load_infobox_tree
from ted import ted_with_ops, patch_with_ops
from diff import save_edit_script, load_edit_script
from wiki_serializer import save_infobox_wikitext
from utils import (
    count_nodes,
    trees_equal,
    first_tree_difference,
    similarity_score,
    summarize_edit_ops,
)
from postprocess import save_comparison_report


def print_ops(ops: list, method: str) -> None:
    """
    Print edit operations for both:
    - custom EditOp objects
    - Chawathe/NJ dict operations
    """
    method = (method or "custom").lower()

    if method == "custom":
        visible_ops = [op for op in ops if op.op != "match"]

        if not visible_ops:
            print("No changes.")
            return

        for i, op in enumerate(visible_ops, start=1):
            print(f"{i}. {op.op.upper()} | {op.path}")
            if op.old_label != op.new_label:
                print(f"   label: {op.old_label} -> {op.new_label}")
            if op.old_value != op.new_value:
                print(f"   value: {op.old_value} -> {op.new_value}")
        return

    visible_ops = [op for op in ops if str(op.get("op", "")).lower() != "match"]

    if not visible_ops:
        print("No changes.")
        return

    for i, op in enumerate(visible_ops[:50], start=1):
        kind = str(op.get("op", "")).upper()
        print(f"{i}. {kind}")

        if "position" in op and op.get("position") is not None:
            print(f"   position: {op.get('position')}")

        if op.get("source_ref"):
            print(f"   source_ref: {op.get('source_ref')}")
        if op.get("parent_ref"):
            print(f"   parent_ref: {op.get('parent_ref')}")

        if op.get("old_label") != op.get("new_label"):
            if op.get("old_label") is not None or op.get("new_label") is not None:
                print(f"   label: {op.get('old_label')} -> {op.get('new_label')}")

        if op.get("old_value") != op.get("new_value"):
            if op.get("old_value") is not None or op.get("new_value") is not None:
                print(f"   value: {op.get('old_value')} -> {op.get('new_value')}")

        if op.get("note"):
            print(f"   note: {op.get('note')}")

    if len(visible_ops) > 50:
        print(f"... ({len(visible_ops) - 50} more operations not shown)")


def main() -> None:
    print("Wiki pipeline started.")

    if len(sys.argv) not in (3, 4):
        print("Usage: python src/wiki_main.py <file1.wiki> <file2.wiki> [custom|chawathe|nj]")
        print("Received arguments:", sys.argv)
        return

    file1 = sys.argv[1]
    file2 = sys.argv[2]
    method = sys.argv[3].lower() if len(sys.argv) == 4 else "custom"

    print("File 1:", file1)
    print("File 2:", file2)
    print("TED method:", method)

    if not os.path.exists(file1):
        print(f"Error: file not found -> {file1}")
        return

    if not os.path.exists(file2):
        print(f"Error: file not found -> {file2}")
        return

    tree1 = load_infobox_tree(file1)
    tree2 = load_infobox_tree(file2)

    n1 = count_nodes(tree1)
    n2 = count_nodes(tree2)

    distance, ops = ted_with_ops(tree1, tree2, f"/{tree1.label}[1]", method=method)
    similarity = similarity_score(distance, n1, n2)
    summary = summarize_edit_ops(ops)

    print("\n=== TREE STATS ===")
    print("Tree 1 nodes:", n1)
    print("Tree 2 nodes:", n2)

    print("\n=== TED RESULT ===")
    print("Tree Edit Distance:", distance)
    print("Similarity score:", round(similarity, 4))

    print("\n=== EDIT SCRIPT SUMMARY ===")
    print("Inserts:", summary["insert"])
    print("Deletes:", summary["delete"])
    print("Updates:", summary["update"])
    print("Total visible operations:", summary["total_visible"])

    print("\n=== EDIT SCRIPT ===\n")
    print_ops(ops, method)

    os.makedirs("data/output", exist_ok=True)

    edit_script_path = "data/output/wiki_edit_script.json"

    if method == "custom":
        save_edit_script(ops, edit_script_path)
        loaded_ops = load_edit_script(edit_script_path)
    else:
        with open(edit_script_path, "w", encoding="utf-8") as f:
            json.dump(ops, f, indent=4, ensure_ascii=False)
        with open(edit_script_path, "r", encoding="utf-8") as f:
            loaded_ops = json.load(f)

    patched_tree = patch_with_ops(tree1, loaded_ops, method=method)
    patch_success = trees_equal(patched_tree, tree2)
    patch_difference = None if patch_success else first_tree_difference(patched_tree, tree2)

    print("\n=== PATCH RESULT ===")
    print("Patched tree equals Tree 2:", patch_success)
    if patch_difference:
        print("First difference:", patch_difference)

    tree1_out = "data/output/tree1_infobox.wiki"
    tree2_out = "data/output/tree2_infobox.wiki"
    patched_out = "data/output/patched_infobox.wiki"
    report_path = "data/output/comparison_report.txt"

    save_infobox_wikitext(tree1, tree1_out)
    save_infobox_wikitext(tree2, tree2_out)
    save_infobox_wikitext(patched_tree, patched_out)

    save_comparison_report(
        report_path,
        file1,
        file2,
        n1,
        n2,
        distance,
        similarity,
        summary,
        patch_success,
        patch_difference,
    )

    print("\n=== OUTPUT FILES ===")
    print("Saved edit script:", edit_script_path)
    print("Saved Tree 1 infobox:", tree1_out)
    print("Saved Tree 2 infobox:", tree2_out)
    print("Saved patched infobox:", patched_out)
    print("Saved comparison report:", report_path)


if __name__ == "__main__":
    main()