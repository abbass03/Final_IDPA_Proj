from __future__ import annotations

import os
import sys

from comparison_service import compare_documents


def print_ops(ops: list, method: str) -> None:
    """
    Print edit operations for both:
    - custom EditOp objects
    - Chawathe/NJ dict operations
    """
    method = (method or "custom").lower()

    if method == "custom":
        visible_ops = [
            op for op in ops
            if (op.op if hasattr(op, "op") else str(op.get("op", ""))) != "match"
        ]

        if not visible_ops:
            print("No changes.")
            return

        for i, op in enumerate(visible_ops, start=1):
            kind = op.op if hasattr(op, "op") else op.get("op", "")
            path = op.path if hasattr(op, "path") else op.get("path")
            old_label = op.old_label if hasattr(op, "old_label") else op.get("old_label")
            new_label = op.new_label if hasattr(op, "new_label") else op.get("new_label")
            old_value = op.old_value if hasattr(op, "old_value") else op.get("old_value")
            new_value = op.new_value if hasattr(op, "new_value") else op.get("new_value")

            print(f"{i}. {str(kind).upper()} | {path}")
            if old_label != new_label:
                print(f"   label: {old_label} -> {new_label}")
            if old_value != new_value:
                print(f"   value: {old_value} -> {new_value}")
        return

    # literature-based TED ops are dicts
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
    print("XML pipeline started.")

    if len(sys.argv) not in (3, 4):
        print("Usage: python src/main.py <file1.xml> <file2.xml> [custom|chawathe|nj]")
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

    result = compare_documents("xml", file1, file2, method=method)

    print("\n=== TREE STATS ===")
    print("Tree 1 nodes:", result["stats"]["tree1_nodes"])
    print("Tree 2 nodes:", result["stats"]["tree2_nodes"])

    print("\n=== TED RESULT ===")
    print("Tree Edit Distance:", result["stats"]["distance"])
    print("Similarity score:", result["stats"]["similarity"])

    print("\n=== EDIT SCRIPT SUMMARY ===")
    print("Inserts:", result["summary"]["insert"])
    print("Deletes:", result["summary"]["delete"])
    print("Updates:", result["summary"]["update"])
    print("Total visible operations:", result["summary"]["total_visible"])

    print("\n=== EDIT SCRIPT ===\n")
    print_ops(result["ops"]["all"], method)

    print("\n=== PATCH RESULT ===")
    print("Patched tree equals Tree 2:", result["patch"]["success"])
    if result["patch"]["difference"]:
        print("First difference:", result["patch"]["difference"])

    print("\n=== OUTPUT FILES ===")
    print("Saved edit script:", result["output_paths"]["edit_script"])
    print("Saved normalized Tree 1 XML:", result["output_paths"]["tree1_xml"])
    print("Saved normalized Tree 2 XML:", result["output_paths"]["tree2_xml"])
    print("Saved patched tree XML:", result["output_paths"]["patched_xml"])
    print("Saved normalized Tree 1 JSON:", result["output_paths"]["tree1_json"])
    print("Saved normalized Tree 2 JSON:", result["output_paths"]["tree2_json"])
    print("Saved patched tree JSON:", result["output_paths"]["patched_json"])
    print("Saved Tree 1 infobox text:", result["output_paths"]["tree1_infobox"])
    print("Saved Tree 2 infobox text:", result["output_paths"]["tree2_infobox"])
    print("Saved patched infobox text:", result["output_paths"]["patched_infobox"])
    print("Saved comparison report:", result["output_paths"]["report"])


if __name__ == "__main__":
    main()
