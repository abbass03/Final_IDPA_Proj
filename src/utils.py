from __future__ import annotations

from models import Node


def count_nodes(root: Node) -> int:
    return 1 + sum(count_nodes(child) for child in root.children)


def subtree_size(node: Node) -> int:
    return 1 + sum(subtree_size(child) for child in node.children)


def similarity_score(distance: int, n1: int, n2: int) -> float:
    """
    Shared similarity formula for all pipelines.
    """
    denom = max(n1 + n2, 1)
    score = 1.0 - (distance / denom)
    return max(0.0, score)


def trees_equal(a: Node, b: Node) -> bool:
    if a.label != b.label:
        return False
    if a.node_type != b.node_type:
        return False
    if a.value != b.value:
        return False
    if len(a.children) != len(b.children):
        return False
    return all(trees_equal(c1, c2) for c1, c2 in zip(a.children, b.children))


def node_path(parent_path: str, node: Node, index: int) -> str:
    return f"{parent_path}/{node.label}[{index}]"


def summarize_edit_ops(ops: list) -> dict:
    summary = {
        "insert": 0,
        "delete": 0,
        "update": 0,
        "total_visible": 0,
    }

    for op in ops:
        kind = op.op if hasattr(op, "op") else str(op.get("op", ""))

        if kind == "match":
            continue

        if kind in ("insert", "insert_tree"):
            summary["insert"] += 1
        elif kind in ("delete", "delete_tree"):
            summary["delete"] += 1
        elif kind == "update":
            summary["update"] += 1

        summary["total_visible"] += 1

    return summary


def print_edit_script(ops: list) -> None:
    visible_ops = [op for op in ops if op.op != "match"]

    if not visible_ops:
        print("No changes.")
        return

    summary = summarize_edit_ops(ops)
    print("Edit Script Summary:")
    print(f"  Inserts: {summary['insert']}")
    print(f"  Deletes: {summary['delete']}")
    print(f"  Updates: {summary['update']}")
    print(f"  Total visible operations: {summary['total_visible']}")
    print()

    for i, op in enumerate(visible_ops, start=1):
        print(f"{i}. {op.op.upper()} | {op.path}")
        if op.old_label != op.new_label:
            print(f"   label: {op.old_label} -> {op.new_label}")
        if op.old_value != op.new_value:
            print(f"   value: {op.old_value} -> {op.new_value}")


def first_tree_difference(a, b, path="root"):
    if a.label != b.label:
        return f"{path}: label mismatch ({a.label} != {b.label})"

    if a.node_type != b.node_type:
        return f"{path}: node_type mismatch ({a.node_type} != {b.node_type})"

    if (a.value or "") != (b.value or ""):
        return f"{path}: value mismatch ({a.value!r} != {b.value!r})"

    if len(a.children) != len(b.children):
        return f"{path}: child count mismatch ({len(a.children)} != {len(b.children)})"

    for i, (ca, cb) in enumerate(zip(a.children, b.children), start=1):
        diff = first_tree_difference(ca, cb, f"{path}/{ca.label}[{i}]")
        if diff:
            return diff

    return None


from models import Node


def format_tree(node: Node, prefix: str = "", is_last: bool = True, show_root: bool = True) -> str:
    """
    Return a tree as a box-drawing string.

    Example:
    country
    ├── name
    │   └── #text = Lebanon
    └── capital
        └── #text = Beirut
    """
    lines = []

    def node_text(n: Node) -> str:
        if n.value is not None:
            return f"{n.label} = {n.value}"
        return n.label

    def walk(n: Node, pfx: str, last: bool, is_root: bool = False) -> None:
        if is_root and show_root:
            lines.append(node_text(n))
        else:
            branch = "└── " if last else "├── "
            lines.append(pfx + branch + node_text(n))

        child_prefix = pfx + ("    " if last else "│   ")

        for i, child in enumerate(n.children):
            walk(child, child_prefix if not is_root else "", i == len(n.children) - 1)

    walk(node, prefix, is_last, is_root=True)
    return "\n".join(lines)


def print_tree(node: Node) -> None:
    print(format_tree(node))