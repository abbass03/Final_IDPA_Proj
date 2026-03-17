import copy
import re
from urllib.parse import quote, unquote

from models import Node
from diff import EditOp


def encode_label(label: str) -> str:
    return quote(label, safe="")


def decode_label(label: str) -> str:
    return unquote(label)


def clone_tree(root: Node) -> Node:
    return copy.deepcopy(root)


def parse_path(path: str) -> list[tuple[str, int]]:
    parts = [p for p in path.strip("/").split("/") if p]
    parsed = []

    for part in parts:
        match = re.match(r"(.+)\[(\d+)\]$", part)
        if not match:
            raise ValueError(f"Invalid path segment: {part}")
        raw_label = match.group(1)
        label = decode_label(raw_label)
        index = int(match.group(2))
        parsed.append((label, index))

    return parsed


def find_node_by_path(root: Node, path: str) -> Node:
    parts = parse_path(path)

    root_label, root_index = parts[0]
    if root.label != root_label or root_index != 1:
        raise ValueError(f"Root mismatch: expected {root.label}[1], got {root_label}[{root_index}]")

    current = root

    for label, index in parts[1:]:
        matching_children = [child for child in current.children if child.label == label]
        if index < 1 or index > len(matching_children):
            raise ValueError(f"Path not found: {path}")
        current = matching_children[index - 1]

    return current


def find_parent_and_target(path_root: Node, path: str) -> tuple[Node, Node]:
    parts = parse_path(path)
    if len(parts) < 2:
        raise ValueError("Cannot get parent of root")

    parent_path = "/" + "/".join(f"{encode_label(label)}[{index}]" for label, index in parts[:-1])
    parent = find_node_by_path(path_root, parent_path)
    target = find_node_by_path(path_root, path)
    return parent, target


def find_child_position(parent: Node, target: Node) -> int:
    for i, child in enumerate(parent.children):
        if child is target:
            return i
    raise ValueError("Target child not found in parent")


def apply_update(node: Node, op: EditOp) -> None:
    if op.new_label is not None:
        node.label = op.new_label
    if op.new_value is not None or op.old_value is not None:
        node.value = op.new_value


def apply_delete(root: Node, op: EditOp) -> None:
    parent, target = find_parent_and_target(root, op.path)
    pos = find_child_position(parent, target)
    del parent.children[pos]


def build_node_from_op(op: EditOp) -> Node:
    if op.new_node is not None:
        return Node.from_dict(op.new_node)

    return Node(
        label=op.new_label if op.new_label is not None else "unknown",
        value=op.new_value,
        node_type="text" if (op.new_label == "#text") else "element"
    )


def apply_insert(root: Node, op: EditOp) -> None:
    parts = parse_path(op.path)
    if len(parts) < 2:
        raise ValueError("Cannot insert at root level in this version")

    parent_path = "/" + "/".join(f"{encode_label(label)}[{index}]" for label, index in parts[:-1])
    parent = find_node_by_path(root, parent_path)

    new_node = build_node_from_op(op)

    if op.insert_pos is None or op.insert_pos < 0 or op.insert_pos > len(parent.children):
        parent.add_child(new_node)
    else:
        parent.children.insert(op.insert_pos, new_node)


def path_depth(path: str) -> int:
    return len([p for p in path.strip("/").split("/") if p])


def parsed_last_index(path: str) -> int:
    parts = parse_path(path)
    if not parts:
        return 0
    return parts[-1][1]


def apply_edit_script(root: Node, ops: list[EditOp]) -> Node:
    patched = clone_tree(root)

    visible_ops = [op for op in ops if op.op != "match"]

    delete_ops = [op for op in visible_ops if op.op == "delete"]
    update_ops = [op for op in visible_ops if op.op == "update"]
    insert_ops = [op for op in visible_ops if op.op == "insert"]

    update_ops.sort(
        key=lambda op: (path_depth(op.path), parsed_last_index(op.path)),
        reverse=True
    )

    delete_ops.sort(
        key=lambda op: (path_depth(op.path), parsed_last_index(op.path)),
        reverse=True
    )

    insert_ops.sort(
        key=lambda op: (
            path_depth(op.path),
            op.insert_pos if op.insert_pos is not None else 10**9
        )
    )

    for op in update_ops:
        try:
            target = find_node_by_path(patched, op.path)
            apply_update(target, op)
        except ValueError:
            continue

    for op in delete_ops:
        try:
            apply_delete(patched, op)
        except ValueError:
            continue

    for op in insert_ops:
        try:
            apply_insert(patched, op)
        except ValueError:
            continue

    return patched