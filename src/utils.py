from models import Node


def count_nodes(root: Node) -> int:
    return 1 + sum(count_nodes(child) for child in root.children)


def subtree_size(node: Node) -> int:
    return 1 + sum(subtree_size(child) for child in node.children)


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


def print_edit_script(ops: list) -> None:
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