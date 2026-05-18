"""Diagnose patch failures by dumping the edit script and tracing execution."""
from __future__ import annotations
import sys
sys.path.insert(0, "src")

from pathlib import Path
from parser import parse_xml_file
from preprocess import preprocess_tree
from ted import ted_with_ops
from patch import (
    apply_edit_script, clone_tree, parse_path, find_node_by_path,
    apply_delete, apply_update, apply_insert,
    path_depth, parsed_last_index, build_node_from_op
)
from diff import EditOp
from utils import first_tree_difference, trees_equal

DATA = Path("data/normalized_xml")

PAIRS = [
    ("sweden",      "norway"),
    ("india",       "pakistan"),
    ("china",       "russia"),
    ("afghanistan", "albania"),
]


def _touches_semantic(path: str) -> bool:
    _SEMANTIC_LABELS = {"tokenized_value", "parsed_date", "parsed_measurement",
                        "number_token", "word_token", "symbol_token",
                        "direction_token", "month_token", "unit_token",
                        "year", "month", "day", "number", "unit", "currency"}
    return any(seg.split("[")[0] in _SEMANTIC_LABELS
               for seg in path.lstrip("/").split("/"))


def trace_patch(source, target, ops_list: list[EditOp], verbose=True):
    """Apply edit script with verbose tracing and return patched tree."""
    from preprocess import build_date_analysis, build_measurement_analysis, build_token_analysis, normalize_text
    from models import Node

    patched = clone_tree(source)

    visible_ops = [op for op in ops_list if op.op != "match"]
    delete_ops = [op for op in visible_ops if op.op == "delete"]
    update_ops = [op for op in visible_ops if op.op == "update"]
    insert_ops = [op for op in visible_ops if op.op == "insert"]

    # Promote DELETE+INSERT pairs at the same path to UPDATE
    delete_by_path = {op.path: op for op in delete_ops}
    promoted = []
    consumed = set()
    remaining_inserts = []
    for ins in insert_ops:
        if ins.path in delete_by_path:
            del_op = delete_by_path[ins.path]
            promoted.append(EditOp(
                op="update",
                path=ins.path,
                old_label=del_op.old_label,
                new_label=ins.new_label if ins.new_label is not None else del_op.old_label,
                old_value=del_op.old_value,
                new_value=ins.new_value,
                new_node=ins.new_node,
            ))
            consumed.add(ins.path)
        else:
            remaining_inserts.append(ins)

    def _is_descendant(child_path, parent_path):
        return child_path.startswith(parent_path + "/")

    delete_ops = [op for op in delete_ops if op.path not in consumed
                  and not any(_is_descendant(op.path, pp) for pp in consumed)]
    remaining_inserts = [op for op in remaining_inserts
                         if not any(_is_descendant(op.path, pp) for pp in consumed)]
    update_ops = update_ops + promoted
    insert_ops = remaining_inserts

    update_ops.sort(key=lambda op: (path_depth(op.path), parsed_last_index(op.path)), reverse=True)
    delete_ops.sort(key=lambda op: (path_depth(op.path), parsed_last_index(op.path)), reverse=True)
    insert_ops.sort(key=lambda op: (path_depth(op.path), op.insert_pos if op.insert_pos is not None else 10**9))

    if verbose:
        print(f"  DELETEs ({len(delete_ops)}), UPDATEs ({len(update_ops)}), INSERTs ({len(insert_ops)})")
        print(f"  Promoted {len(promoted)} DELETE+INSERT pairs to UPDATE")
        print(f"  Consumed paths: {consumed}")

    # DELETEs
    failed_deletes = []
    for op in delete_ops:
        if _touches_semantic(op.path):
            continue
        try:
            apply_delete(patched, op)
        except ValueError as e:
            failed_deletes.append((op.path, str(e)))
            if verbose:
                print(f"  [DELETE FAIL] {op.path}: {e}")

    # Root children after deletes
    if verbose:
        root_labels = [c.label for c in patched.children]
        print(f"  Root children after DELETEs ({len(root_labels)}): {root_labels[:20]}")

    # UPDATEs
    failed_updates = []
    for op in update_ops:
        try:
            tgt = find_node_by_path(patched, op.path)
            apply_update(tgt, op)
        except ValueError as e:
            failed_updates.append((op.path, str(e)))
            if verbose and not _touches_semantic(op.path):
                print(f"  [UPDATE FAIL] {op.path}: {e}")

    # Root children after updates
    if verbose:
        root_labels = [c.label for c in patched.children]
        print(f"  Root children after UPDATEs ({len(root_labels)}): {root_labels[:20]}")

    # INSERTs
    failed_inserts = []
    for op in insert_ops:
        if _touches_semantic(op.path):
            continue
        try:
            apply_insert(patched, op)
        except ValueError as e:
            failed_inserts.append((op.path, str(e)))
            if verbose:
                print(f"  [INSERT FAIL] {op.path}: {e}")

    # Rebuild semantic children
    def _rebuild_text_node(node):
        if node.node_type == "text" and node.value is not None:
            node.value = normalize_text(node.value)
            children = []
            d = build_date_analysis(node.value)
            if d: children.append(d)
            m = build_measurement_analysis(node.value)
            if m: children.append(m)
            t = build_token_analysis(node.value)
            if t: children.append(t)
            node.children = children
            return
        for child in node.children:
            _rebuild_text_node(child)
    _rebuild_text_node(patched)

    if verbose:
        root_labels = [c.label for c in patched.children]
        print(f"  Root children after INSERTs ({len(root_labels)}): {root_labels[:20]}")

    return patched, failed_deletes, failed_updates, failed_inserts


def main():
    for src_name, tgt_name in PAIRS:
        src_path = DATA / f"{src_name}.xml"
        tgt_path = DATA / f"{tgt_name}.xml"

        if not src_path.exists() or not tgt_path.exists():
            print(f"  SKIP {src_name} vs {tgt_name}: files not found")
            continue

        tree1 = preprocess_tree(parse_xml_file(str(src_path)))
        tree2 = preprocess_tree(parse_xml_file(str(tgt_path)))

        distance, ops = ted_with_ops(tree1, tree2, "/country[1]", method="custom")
        print(f"\n{'='*70}")
        print(f"{src_name} vs {tgt_name}  dist={distance}")

        # Show root-level ops only
        root_ops = [op for op in ops if op.op != "match" and len(parse_path(op.path)) == 2]
        print(f"  Root-level ops ({len(root_ops)}):")
        for op in root_ops:
            if op.op == "delete":
                print(f"    DELETE {op.path} (label={op.old_label})")
            elif op.op == "insert":
                print(f"    INSERT {op.path} (label={op.new_label}, pos={op.insert_pos})")
            elif op.op == "update":
                print(f"    UPDATE {op.path} ({op.old_label} -> {op.new_label})")

        print(f"\n  Source root children ({len(tree1.children)}): {[c.label for c in tree1.children][:25]}")
        print(f"  Target root children ({len(tree2.children)}): {[c.label for c in tree2.children][:25]}")

        patched, fd, fu, fi = trace_patch(tree1, tree2, ops, verbose=True)
        diff = first_tree_difference(patched, tree2)
        status = "OK" if diff is None else f"FAIL: {diff}"
        print(f"  Result: {status}")

if __name__ == "__main__":
    main()
